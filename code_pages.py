#!/usr/bin/env python3
"""
항목별 독립 호출기 — 코딩 시트의 각 항목을 OpenAI 호환 `/chat/completions` 에 **한 항목당
한 호출**로 보내 등급 라벨을 받는다. (docs/02-design/features/recoding.design.md §2)

    python3 code_pages.py --coder B --provider-env ~/.config/auditagent/.env --model gpt-5.6-sol
    python3 code_pages.py --coder A --provider-env .env.local --model gemini-2.5-pro --resume
    python3 code_pages.py --coder B --provider-env … --model … --limit 3 --dry-run   # 설정·첫 프롬프트 확인

## 이 파일이 지키는 것

1. **규칙을 모른다.** 등급 정의·지시문은 코딩 시트 JSON 의 `coder_prompt` 에서 읽는다.
   이 파일에는 등급이 무엇인지에 대한 문자열이 한 줄도 없다(하니스 R15m 이 소스를
   검사한다). 지난 회차의 오염원 1번(코더 A 가 규칙 작성 당사자)을 코드 수준에서 끊는다.
2. **한 항목 = 한 호출.** 대화 이력을 이어가지 않으므로 항목 간 상대평가가 생기지 않는다.
3. **제공자는 설정으로 바꾼다.** OpenAI 호환 엔드포인트만 쓰고, 키·주소·모델을 env 파일
   한 곳에서 읽는다(`AUDIT_LLM_*` 우선, 없으면 `GEMINI_API_KEY` 같은 키 변수명으로 프리셋).
   **온도는 env 에서 읽지 않는다** — `auditagent` 의 1.0 이 조용히 상속되면 재현이 깨진다.
   모델도 기본값으로 때우지 않는다 — 어느 모델이 코딩했는지가 기록의 핵심이다.
4. **원자료를 남긴다.** 응답 원문·토큰·지연·재시도 횟수를 항목마다, 모델·주소·온도·
   프롬프트 해시·실행 시각을 파일마다(FR-3). 라벨은 1·2·3·`?` 로 **확실히 파싱될 때만**
   만든다 — 애매한 응답은 `errors` 에 남기고 라벨을 만들지 않는다.
5. **중단·재개.** 항목마다 파일을 원자적으로 갱신하고 `--resume` 이 채점된 항목을 건너뛴다.
   진행 상태는 산출물 자체다 — 별도 progress 파일을 두면 두 파일이 어긋나는 실패 모드가
   생긴다. 다른 모델·주소로는 재개할 수 없다(한 파일에 코더가 섞이면 안 된다).

## Claude Code 헤드리스 백엔드 (`--backend claude-cli`, 설계 A1)

API 키 없이 Claude 계열 코더를 쓰는 길이다. `claude -p` 를 항목마다 한 번 띄운다. 세 가지를
강제한다 — `--setting-sources ""`(프로젝트 설정·훅·플러그인·CLAUDE.md 를 싣지 않는다; 실측으로
그 옵션 없이는 7.5만 토큰의 프로젝트 컨텍스트가 코더에게 실렸다), `--tools ""`(도구 없음),
그리고 저장소 **밖**의 작업 디렉터리. 온도·시드는 CLI 가 받지 않으므로 400 으로 돌려 폴백이
`*_honored=False` 를 기록하게 한다. 응답은 OpenAI 응답 모양으로 바꿔 나머지 경로를 그대로 탄다.

## 온도·시드를 거부하는 모델

일부 추론 모델은 temperature(또는 seed)를 받지 않는다(400). 그때는 그 인자 없이 다시
묻되 `meta.temperature_honored=False` 로 **기록**한다 — 재현성 주장을 조용히 잃지 않기
위해서다. 같은 파일 안에서는 그 뒤 항목부터 처음부터 빼고 보낸다.

## 산출물 (coding_<코더>.json)

    { "coder": "A", "sample_digest": "<시트와 동일>",
      "meta": { "model", "base_url", "key_var", "temperature", "seed", "prompt_sha256",
                "run_at", "context_isolated": true, "provider_env", "version",
                "temperature_honored", "seed_honored", "model_reported" },
      "grades": { "1": 3, "2": "?", … },        # score_coding.py 가 읽는 형식 그대로
      "errors": { "5": "응답을 … 읽을 수 없음" },
      "raw":    { "1": { "answer", "tokens_in", "tokens_out", "latency_ms", "retries" }, … } }
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SHEET = os.path.join(HERE, 'coding_sheet.json')
DEFAULT_TEMPERATURE = 0.0     # env 의 온도를 상속하지 않는다. 바꾸려면 --temperature 로 명시
SEED = 20260904               # API seed (best-effort 재현). 표본 시드와 같은 값을 쓴다
MAX_RETRIES = 5
BACKOFF = (1, 2, 4, 8, 16)    # 초. 429·5xx·네트워크 오류에만 적용
TIMEOUT = 180                 # 초. 분쟁군은 평균 11,735자라 추론 모델이 오래 걸릴 수 있다

# 키 변수명 → OpenAI 호환 주소. AUDIT_LLM_BASE_URL / --base-url 이 있으면 그것이 우선.
PRESETS = [
    ('OPENAI_API_KEY', 'https://api.openai.com/v1'),
    ('GEMINI_API_KEY', 'https://generativelanguage.googleapis.com/v1beta/openai'),
    ('GOOGLE_API_KEY', 'https://generativelanguage.googleapis.com/v1beta/openai'),
    ('DEEPSEEK_API_KEY', 'https://api.deepseek.com/v1'),
    ('GROQ_API_KEY', 'https://api.groq.com/openai/v1'),
    ('OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1'),
]


def read_env(path):
    """KEY=VALUE 파일을 읽는다. `export`, 따옴표, 주석, 빈 줄을 처리한다."""
    env = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            if line.startswith('export '):
                line = line[len('export '):].strip()
            k, v = line.split('=', 1)
            k, v = k.strip(), v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                v = v[1:-1]
            elif ' #' in v:
                v = v.split(' #', 1)[0].strip()
            env[k] = v
    return env


def provider_config(env, model=None, base_url=None):
    """키·주소·모델을 한 곳에서 정한다. 온도는 **여기서 읽지 않는다.**"""
    key, key_var = env.get('AUDIT_LLM_API_KEY'), 'AUDIT_LLM_API_KEY'
    url = base_url or env.get('AUDIT_LLM_BASE_URL')
    if not key:
        for var, preset in PRESETS:
            if env.get(var):
                key, key_var = env[var], var
                url = url or preset
                break
    if not key:
        raise ValueError('API 키를 찾을 수 없습니다 — AUDIT_LLM_API_KEY 또는 %s 중 하나가 '
                         'env 파일에 있어야 합니다' % ', '.join(v for v, _ in PRESETS))
    url = url or PRESETS[0][1]
    model = model or env.get('AUDIT_LLM_MODEL')
    if not model:
        raise ValueError('모델을 지정하십시오 (--model 또는 AUDIT_LLM_MODEL). 기본값으로 '
                         '때우지 않습니다 — 어느 모델이 코딩했는지가 기록의 핵심입니다')
    return {'base_url': url.rstrip('/'), 'api_key': key, 'model': model, 'key_var': key_var}


# 1·2·3·? 가 **홀로** 선 자리만 잡는다. '12', '2.5' 같은 숫자의 일부는 잡지 않는다.
_TOKEN = re.compile(r'(?<![\d.])([123?])(?!\d|\.\d)')


def parse_grade(answer):
    """응답에서 라벨을 읽는다. 서로 다른 값이 둘 이상이거나 없으면 None — 라벨을 만들지 않는다."""
    if not isinstance(answer, str):
        return None
    found = set(_TOKEN.findall(answer))
    if len(found) != 1:
        return None
    g = found.pop()
    return '?' if g == '?' else int(g)


def build_messages(coder_prompt, item):
    """system 은 시트의 지시문 그대로, user 는 (고지 +) 본문. 그 밖의 문자열은 붙이지 않는다."""
    body = item['text']
    if item.get('notice'):
        body = item['notice'] + '\n\n' + body
    return [{'role': 'system', 'content': coder_prompt},
            {'role': 'user', 'content': body}]


def post_json(url, headers, payload, timeout):
    """(HTTP 상태, 본문 dict). HTTP 오류도 상태와 본문으로 돌려준다. 네트워크 오류는 예외."""
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST',
                                 headers=dict(headers, **{'Content-Type': 'application/json'}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(body)
        except ValueError:
            return e.code, {'error': {'message': body[:500]}}


CLI_BASE_URL = 'claude-cli://anthropic'   # 호스트가 계열 가드에 쓰인다 (OpenAI 와 다르게)
CLI_UNSUPPORTED = ('temperature', 'seed')  # claude -p 가 받지 않는 인자 — 400 으로 알린다


def _cli_cwd():
    """저장소 밖의 작업 디렉터리. 프로젝트 컨텍스트가 코더에게 실리지 않게 한다."""
    d = os.path.join(tempfile.gettempdir(), 'code_pages_claude_cli')
    os.makedirs(d, exist_ok=True)
    return d


def claude_cli_post(url, headers, payload, timeout, run=None, cwd=None, claude_bin='claude'):
    """post 인터페이스 — `claude -p` 를 한 번 띄우고 OpenAI 응답 모양으로 돌려준다."""
    for param in CLI_UNSUPPORTED:
        if param in payload:
            return 400, {'error': {'message': "claude-cli backend does not support '%s'" % param}}
    system = next((m['content'] for m in payload['messages'] if m['role'] == 'system'), '')
    user = next((m['content'] for m in reversed(payload['messages']) if m['role'] == 'user'), '')
    # --strict-mcp-config 가 핵심이다: 없으면 사용자 MCP 서버의 도구 정의(실측 4.8만~11.8만 토큰)가
    # 코더 컨텍스트에 실린다. --setting-sources "" 는 설정·훅·CLAUDE.md 를, --tools "" 는 도구를 막는다.
    argv = [claude_bin, '-p', '--model', payload['model'], '--system-prompt', system,
            '--tools', '', '--setting-sources', '', '--strict-mcp-config', '--no-chrome',
            '--no-session-persistence', '--output-format', 'json']
    run = run or subprocess.run
    try:
        r = run(argv, input=user, capture_output=True, text=True, timeout=timeout,
                cwd=cwd or _cli_cwd())
    except subprocess.TimeoutExpired:
        return None, {'error': {'message': 'claude -p 시간 초과 (%ss)' % timeout}}
    try:
        body = json.loads(r.stdout)
    except (ValueError, TypeError):
        return 500, {'error': {'message': 'claude -p 출력을 읽을 수 없음 (exit %s): %s'
                                          % (r.returncode, (r.stderr or r.stdout or '')[-300:])}}
    if body.get('is_error'):
        msg = str(body.get('result') or body)
        status = 401 if 'logged in' in msg.lower() or 'login' in msg.lower() else 500
        return status, {'error': {'message': msg}}
    # Claude Code 는 요청 모델 외에 Haiku 보조 호출(실측 922토큰 고정)을 낀다. 토큰·모델은 요청
    # 모델의 modelUsage 로 세고, 나머지는 side_calls 로 남긴다 — 총계 usage 를 쓰면 섞인다.
    mu = body.get('modelUsage') or {}
    main = next((k for k in mu if k.startswith(payload['model'])), None)
    if main is None and mu:
        main = max(mu, key=lambda k: (mu[k].get('inputTokens') or 0) + (mu[k].get('cacheReadInputTokens') or 0)
                   + (mu[k].get('cacheCreationInputTokens') or 0))
    u = mu.get(main) or {}
    usage = body.get('usage') or {}
    prompt_tokens = (sum(u.get(k) or 0 for k in ('inputTokens', 'cacheCreationInputTokens', 'cacheReadInputTokens'))
                     if u else sum(usage.get(k) or 0 for k in ('input_tokens', 'cache_read_input_tokens',
                                                                'cache_creation_input_tokens')))
    completion = u.get('outputTokens') if u else usage.get('output_tokens')
    return 200, {'choices': [{'message': {'content': body.get('result')}}],
                 'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion or 0},
                 'model': main or payload['model'], 'system_fingerprint': None,
                 'cost_usd': body.get('total_cost_usd'),
                 'side_calls': {k: v for k, v in mu.items() if k != main}}


def _err_msg(body):
    if isinstance(body, dict):
        e = body.get('error')
        if isinstance(e, dict):
            return str(e.get('message', e))
        if e:
            return str(e)
    return str(body)[:300]


def call_chat(cfg, messages, temperature, seed, state, post=post_json, sleep=time.sleep,
              timeout=TIMEOUT):
    """한 항목 한 호출. state 는 파일 단위로 공유되는 {'temperature_ok', 'seed_ok'}."""
    url = cfg['base_url'] + '/chat/completions'
    headers = {'Authorization': 'Bearer ' + cfg['api_key']}
    retries = 0
    t0 = time.monotonic()        # 벽시계(time.time)는 NTP 보정으로 뒤로 갈 수 있다 — 음수 지연이 실제로 찍혔다
    while True:
        payload = {'model': cfg['model'], 'messages': messages}
        if temperature is not None and state.get('temperature_ok', True):
            payload['temperature'] = temperature
        if seed is not None and state.get('seed_ok', True):
            payload['seed'] = seed
        try:
            status, body = post(url, headers, payload, timeout)
        except (urllib.error.URLError, OSError) as e:          # 네트워크 — 재시도 대상
            status, body = None, {'error': {'message': repr(e)}}
        if status == 200:
            choice = (body.get('choices') or [{}])[0]
            usage = body.get('usage') or {}
            return {
                'answer': (choice.get('message') or {}).get('content'),
                'tokens_in': usage.get('prompt_tokens'),
                'tokens_out': usage.get('completion_tokens'),
                'latency_ms': int((time.monotonic() - t0) * 1000),
                'retries': retries,
                'fingerprint': body.get('system_fingerprint'),
                'model': body.get('model'),
                'cost_usd': body.get('cost_usd'),
                'side_calls': body.get('side_calls'),
            }
        msg = _err_msg(body)
        if status == 400:
            # 인자를 거부하는 모델 — 그 인자만 빼고 즉시 다시 묻는다. 재시도로 세지 않는다.
            for param in ('temperature', 'seed'):
                if param in payload and param in msg.lower():
                    state[param + '_ok'] = False
                    break
            else:
                raise RuntimeError('HTTP 400: %s' % msg)
            continue
        if status in (None, 408, 409, 429) or status >= 500:
            if retries >= MAX_RETRIES:
                raise RuntimeError('%d회 재시도 후 실패 (HTTP %s): %s' % (retries, status, msg))
            sleep(BACKOFF[min(retries, len(BACKOFF) - 1)])
            retries += 1
            continue
        raise RuntimeError('HTTP %s: %s' % (status, msg))


def write_doc(path, doc):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def code_items(sheet, cfg, coder, out_path, temperature=DEFAULT_TEMPERATURE, seed=SEED,
               limit=None, resume=False, post=post_json, sleep=time.sleep, log=print,
               provider_env='', workers=1):
    """시트의 항목을 하나씩 묻고 산출물을 항목마다 디스크에 반영한다. 반환: 산출물 dict.

    workers > 1 이면 호출만 병렬이고 기록은 항목 순서대로 주 스레드가 한다 — 산출물은 순차
    실행과 같다. 한 항목 한 호출(문맥 격리)은 그대로다.
    """
    prompt = sheet['coder_prompt']
    if resume and os.path.exists(out_path):
        with open(out_path, encoding='utf-8') as f:
            doc = json.load(f)
        if doc.get('sample_digest') != sheet.get('sample_digest'):
            raise ValueError('표본 지문 불일치 — 이 산출물은 다른 시트에서 나왔습니다: %s'
                             % out_path)
        m = doc.get('meta', {})
        if m.get('model') != cfg['model'] or m.get('base_url') != cfg['base_url']:
            raise ValueError('다른 모델·주소로는 재개할 수 없습니다 (파일 %s / 지금 %s @ %s). '
                             '한 파일에 코더가 섞이면 라벨의 출처가 사라집니다.'
                             % (m.get('model'), cfg['model'], cfg['base_url']))
        m.setdefault('resumed_at', []).append(_now())
    else:
        if os.path.exists(out_path):
            raise ValueError('이미 있습니다: %s — --resume 로 이어가거나 다른 --out 을 쓰십시오'
                             % out_path)
        doc = {
            'coder': coder, 'sample_digest': sheet.get('sample_digest'),
            'meta': {
                'model': cfg['model'], 'base_url': cfg['base_url'],
                'key_var': cfg.get('key_var'), 'temperature': temperature, 'seed': seed,
                'prompt_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
                'run_at': _now(), 'context_isolated': True, 'provider_env': provider_env,
                'version': None, 'model_reported': None,
                'temperature_honored': True, 'seed_honored': True,
            },
            'grades': {}, 'errors': {}, 'raw': {},
        }
    meta = doc['meta']
    state = {'temperature_ok': meta.get('temperature_honored', True),
             'seed_ok': meta.get('seed_honored', True)}

    todo = [it for it in sheet['items'] if str(it['id']) not in doc['grades']]
    if limit is not None:
        todo = todo[:limit]
    log('코더 %s: %s @ %s — %d항목 (채점됨 %d, 이번 %d)'
        % (coder, cfg['model'], cfg['base_url'], len(sheet['items']),
           len(doc['grades']), len(todo)))
    def _one(it):
        sid = str(it['id'])
        try:
            return sid, call_chat(cfg, build_messages(prompt, it), temperature, seed, state,
                                  post=post, sleep=sleep), None
        except RuntimeError as e:
            return sid, None, str(e)

    if workers > 1:
        from concurrent.futures import ThreadPoolExecutor
        pool = ThreadPoolExecutor(max_workers=workers)
        results = pool.map(_one, todo)          # 순서 보존 — 기록은 아래서 주 스레드가 한다
    else:
        pool, results = None, map(_one, todo)
    for n, (sid, r, err) in enumerate(results, 1):
        if err is not None:
            doc['errors'][sid] = err
            doc['raw'][sid] = {'answer': None, 'tokens_in': None, 'tokens_out': None,
                               'latency_ms': None, 'retries': None, 'error': err}
            write_doc(out_path, doc)
            log('  [%d/%d] id=%s  실패: %s' % (n, len(todo), sid, err[:100]))
            continue
        g = parse_grade(r['answer'])
        doc['raw'][sid] = {k: r.get(k) for k in ('answer', 'tokens_in', 'tokens_out',
                                                 'latency_ms', 'retries', 'cost_usd')}
        if r.get('side_calls'):
            doc['raw'][sid]['side_calls'] = r['side_calls']
        if g is None:
            doc['errors'][sid] = '응답을 1·2·3·? 로 읽을 수 없음: %r' % (r['answer'] or '')[:80]
        else:
            doc['grades'][sid] = g
            doc['errors'].pop(sid, None)
        if meta['version'] is None and r.get('fingerprint'):
            meta['version'] = r['fingerprint']
        if meta['model_reported'] is None and r.get('model'):
            meta['model_reported'] = r['model']
        meta['temperature_honored'] = state['temperature_ok']
        meta['seed_honored'] = state['seed_ok']
        write_doc(out_path, doc)
        log('  [%d/%d] id=%s → %s  (%s ms, 재시도 %s)'
            % (n, len(todo), sid, g if g is not None else '읽기 실패',
               r['latency_ms'], r['retries']))
    if pool is not None:
        pool.shutdown()
    return doc


def main():
    ap = argparse.ArgumentParser(description='코딩 시트 항목별 독립 호출기')
    ap.add_argument('--sheet', default=DEFAULT_SHEET)
    ap.add_argument('--coder', required=True, help='A 또는 B — 산출물 이름에 쓰인다')
    ap.add_argument('--out', help='기본: 시트 옆 coding_<코더>.json')
    ap.add_argument('--provider-env', help='키·주소·모델이 든 env 파일 (--backend http 에 필요)')
    ap.add_argument('--backend', choices=('http', 'claude-cli'), default='http',
                    help='http = OpenAI 호환 API / claude-cli = `claude -p` 헤드리스 (키 불필요)')
    ap.add_argument('--claude-bin', default='claude', help='claude-cli 백엔드의 실행 파일')
    ap.add_argument('--workers', type=int, default=1, help='동시 호출 수 (기록은 순서대로)')
    ap.add_argument('--model', help='기본: env 의 AUDIT_LLM_MODEL')
    ap.add_argument('--base-url', help='기본: env 의 AUDIT_LLM_BASE_URL 또는 키 변수 프리셋')
    ap.add_argument('--temperature', type=float, default=DEFAULT_TEMPERATURE)
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--limit', type=int, help='이번 실행에서 시도할 항목 수')
    ap.add_argument('--resume', action='store_true', help='기존 산출물의 채점 항목을 건너뛴다')
    ap.add_argument('--dry-run', action='store_true', help='호출 없이 설정과 첫 프롬프트만 보인다')
    args = ap.parse_args()

    if not os.path.exists(args.sheet):
        sys.exit('코딩 시트가 없습니다: %s — 먼저 python3 make_coding_sheet.py' % args.sheet)
    with open(args.sheet, encoding='utf-8') as f:
        sheet = json.load(f)
    if 'coder_prompt' not in sheet:
        sys.exit('시트에 coder_prompt 가 없습니다 (구버전 시트). make_coding_sheet.py 를 다시 돌리세요.')
    if args.backend == 'claude-cli':
        if not args.model:
            sys.exit('--model 을 지정하십시오 (예: claude-opus-5). 기본값으로 때우지 않습니다.')
        cfg = {'base_url': CLI_BASE_URL, 'api_key': '', 'model': args.model, 'key_var': None}
        post = lambda u, h, p, t: claude_cli_post(u, h, p, t, claude_bin=args.claude_bin)  # noqa: E731
        provider_env = 'claude-cli (Claude Code OAuth, %s)' % args.claude_bin
    else:
        if not args.provider_env:
            sys.exit('--provider-env 가 필요합니다 (또는 --backend claude-cli)')
        env_path = os.path.expanduser(args.provider_env)
        if not os.path.exists(env_path):
            sys.exit('env 파일이 없습니다: %s' % env_path)
        try:
            cfg = provider_config(read_env(env_path), model=args.model, base_url=args.base_url)
        except ValueError as e:
            sys.exit(str(e))
        post, provider_env = post_json, args.provider_env
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.sheet)),
                                   'coding_%s.json' % args.coder)

    if args.dry_run:
        print('모델 %s @ %s (키 변수 %s, 온도 %s, 시드 %s)'
              % (cfg['model'], cfg['base_url'], cfg['key_var'], args.temperature, args.seed))
        print('시트 %s: %d항목, 지문 %s, 프롬프트 sha256 %s'
              % (args.sheet, len(sheet['items']), sheet.get('sample_digest'),
                 hashlib.sha256(sheet['coder_prompt'].encode('utf-8')).hexdigest()[:16]))
        print('산출물 %s%s' % (out, ' (있음)' if os.path.exists(out) else ''))
        if sheet['items']:
            m = build_messages(sheet['coder_prompt'], sheet['items'][0])
            print('\n--- system ---\n%s\n--- user (앞 300자) ---\n%s'
                  % (m[0]['content'], m[1]['content'][:300]))
        return

    try:
        doc = code_items(sheet, cfg, args.coder, out, temperature=args.temperature,
                         seed=args.seed, limit=args.limit, resume=args.resume,
                         provider_env=provider_env, post=post, workers=args.workers)
    except ValueError as e:
        sys.exit(str(e))
    print('\n채점 %d / 오류 %d / 전체 %d → %s'
          % (len(doc['grades']), len(doc['errors']), len(sheet['items']), out))
    if not doc['meta']['temperature_honored']:
        print('주의: 이 모델은 temperature 를 거부해 온도 없이 물었습니다 (meta 에 기록됨).')


if __name__ == '__main__':
    main()
