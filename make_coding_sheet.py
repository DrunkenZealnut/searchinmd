#!/usr/bin/env python3
"""
수기 코딩 시트 생성 — 등급 판정을 사람(또는 독립 코더)이 눈으로 매기기 위한 것.

    pip install openpyxl
    python3 make_coding_sheet.py                 # coding_sheet.json / .md / coding_key.json

## 표본 — 4층, 두 어휘 정의의 합집합 (docs/02-design/features/recoding.design.md §3)

규칙은 현행 / 수정본(D1+D2) 두 쌍이고, 각 쌍은 어휘 두 벌(현재 사전 / +21종, V)로
다시 갈린다. 어느 어휘를 채택할지 라벨 없이 먼저 정하면 순환이므로, **두 어휘 정의의
합집합**으로 층을 뽑아 같은 라벨로 변형 전부를 채점한다 — 어휘 채택도 라벨이 판정한다.

  분쟁군   어느 규칙쌍에서든 현행=3, 수정본≠3                  → 전수
  합의군   어느 변형이든 등급3인 쪽 가운데 분쟁군이 아닌 것      → 전수 (기준선)
  경계층   등급3이 아닌 쪽 가운데 어느 쌍에서든 현행=2, 수정본=1  → 전수 (가장 많이 움직인 경계)
  재현율층 나머지(현행이 등급1·2)에서 무작위 N_RECALL            → 여기서 나온 등급3이 누락 추정

앞의 세 층은 전수라 표집오차가 0이다. "69쪽으로는 판별력이 없었다" 의 해법은 더
뽑는 것이 아니라 다 하는 것이었다 — 어느 변형이든 등급3인 쪽이 130쪽 안팎이라 가능하다.
재현율층만 표본이고, 채점기(score_coding.py)가 유한모집단 구간을 낸다. 합의군은
기준선이다 — 분쟁군만 보면 "코더가 원래 등급3에 인색한가" 와 "수정본이 옳은가" 를
구분할 수 없다.

변형별 예측 등급은 **키 파일**에 싣는다(`pred`). 채점기가 원본 엑셀 없이 변형별
정밀도를 낼 수 있고, 어느 변형의 등급3이든 표본에 전수로 들어 있으므로 표본 수치를
모집단으로 환산하는 가중치가 필요 없다.

## 코더는 규칙의 판정을 보지 못한다

시트에는 등급도, 안전어/조치어 카운트도, 사유도, 군도 넣지 않는다. 보면 그쪽으로
끌려간다(앵커링). 코더는 본문과 등급 정의만 보고 매긴다. 정답은 별도 키 파일에
두고 채점할 때만 붙인다.

## 지시문이 규칙을 누출했다 (외부감사 C-1, 수정함)

판정을 감추는 것만으로는 부족했다. 이전 지시문은 두 가지를 흘렸다.

1. `반도체 공정 설명에 나오는 "진동", "먼지(파티클)" 처럼…` — 이것은
   `regrade.py` 의 `HOMONYM_CONTEXTS` 키(`진동`, `먼지`)와 대표 문맥어(`파티클`)
   를 그대로 옮긴 것이다. **D1 의 핵심 가정을 코더에게 알려준 셈이다.**
2. `판단이 갈리면 낮은 등급을 택합니다` — 분쟁군 실험의 질문은 "이 페이지가
   진짜 등급3인가" 이고, 낮은 쪽으로 기울이는 동점 규칙은 **수정본이 이기는
   방향**이다. 두 코더가 모두 수정본을 지지한 결과가 본문 때문인지 이 문장
   때문인지 구분할 수 없게 된다.

둘 다 **두 코더가 공유한 도구**에서 일어났으므로, 코더를 교체해도 같은
스크립트로 시트를 만들면 그대로 재발한다. 그래서 지시문을 고쳤다 —
동음이의 예시를 지우고, 동점 규칙을 방향 없는 `?`(판단 불가) 코드로 바꾸고,
"사전에 없을 법한 표현도 조치로 센다" 는 상향 지침을 대칭으로 넣었다.

지시문은 `coder_prompt()` 한 곳에만 있다. 사람용 `.md` 와 API 코더(`code_pages.py`)가
**같은 문자열**을 본다 — 호출기는 이것을 시트 JSON 에서 읽고 자기 문자열을 갖지 않는다.
`?` 를 도입했으므로 `score_coding.py` 는 1·2·3 외의 값을 받을 수 있어야 한다.

## 본문을 자르지 않는다 (외부감사 C-1, 수정함)

이전에는 `MAX_CHARS = 6000` 으로 본문을 잘라 시트에 실었다. 그런데 채점기
(`regrade.py`)는 엑셀에 담긴 32,767자를 보므로, **두 쪽이 서로 다른 텍스트를 보고
있었다.** F1·κ 가 "규칙이 맞나" 대신 절단 길이 차이를 재고 있을 수 있다.

실측: NCS 1,847쪽 중 6,000자를 넘는 쪽이 41쪽인데 등급별로 고르지 않다 —
등급1 은 0.7%, 등급3 은 15.7% 다. 자르면 등급3 후보만 골라 깎는 셈이다.

그래서 자르지 않고 `CHUNK_CHARS` 단위로 **나눠서** 싣는다. 이어붙이면 원문과
같아야 한다(무손실).

## 원본 절단은 되돌릴 수 없다

그 위층 절단은 남는다. 워크북의 `페이지전체내용` 자체가 엑셀 셀 한도 32,767자에서
잘려 있고(NCS 16쪽), 원본은 이 엑셀뿐이라 복구가 불가능하다. 해당 항목에는 고지를
붙인다 — 고지하지 않으면 코더가 잘린 뒷부분의 부재를 "조치 없음" 으로 읽게 되고,
그것이 C-1 이 지적한 오염 그 자체다. 전문을 실으면 말미의 '...' 로 어차피 드러난다.

## 산출물

`coding_sheet.json` / `.md` 는 교재 본문이 그대로 들어가므로 커밋하지 않는다(.gitignore).
`coding_key.json` 은 본문이 없어(교재·쪽·군·변형별 예측 등급) 추적한다 — 라벨을
페이지에 붙이는 유일한 결합 정보이자 표본 지문의 원천이다.
"""
import hashlib
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# openpyxl 가드는 여기 두지 않는다 — regrade 를 불러오는 순간 같은 문구로 걸린다.
# 두 벌을 두면 어느 쪽이 먼저 걸리느냐에 따라 메시지 출처가 달라진다.
import regrade as RG  # noqa: E402
from page_utils import CODING_GROUPS, BASELINE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20260904          # 표본이 바뀌었으므로 시드도 새로 둔다. 옛 시드(20260903)는 옛
                         # 표본의 것이고, 재사용하면 두 표본이 같은 것처럼 보인다
N_RECALL = 300           # 재현율층 크기 (Plan §4.3-A). 적중 0건이어도 누락률 상한을 말할 수 있다
CHUNK_CHARS = 6000       # 자르는 길이가 아니라 **나누는** 단위다

# 층을 가르는 규칙쌍 (현행, 수정본). 어휘가 두 벌이므로 쌍도 둘이다.
RULE_PAIRS = [(BASELINE, RG.ADOPTED_VARIANT),
              (RG.VOCAB_VARIANT, RG.ADOPTED_VOCAB_VARIANT)]
GROUPS = CODING_GROUPS

# 절단 고지 — .md 는 인용 블록으로, 시트 JSON 은 `notice` 로 싣는다. 한 곳에만 둔다.
TRUNCATION_NOTICE = [
    '⚠️ **이 본문은 원본 수집 단계에서 잘렸습니다** (엑셀 셀 한도 32,767자).',
    '뒷부분은 존재하지 않으며 복구할 수 없습니다. 뒤에 조치가 더 있었는지',
    '알 수 없으므로, 판단이 서지 않으면 `?` 로 표시하십시오.',
]

GRADE_GUIDE = [
    '## 등급 정의',
    '',
    '| 등급 | 뜻 | 판정 기준 |',
    '|:---:|---|---|',
    '| 1 | 미흡·없음 | 안전보건 내용이 없거나, 있어도 스쳐 지나가는 수준 |',
    '| 2 | 형식적 언급 | 안전·위험을 언급하지만 **무엇을 어떻게 하라는 조치가 없다** |',
    '| 3 | 구체적 대책 | 실제 안전 조치·보호구·대응절차를 **구체적으로 제시**한다 |',
    '',
    '**등급을 정하기 어려우면 `?` 로 표시하고 넘어갑니다.** 어느 쪽으로도',
    '기울이지 마십시오 — 불확실성을 등급으로 바꾸면 그 방향이 결과에 실립니다.',
    '',
    '본문이 길면 `(본문 1/3)` 처럼 나눠서 싣습니다. **나뉘어도 한 항목이고 판정도',
    '하나입니다.** 끝까지 읽고 나서 매기십시오.',
    '',
    '판정 대상은 **작업자의 안전보건**입니다. 공정·품질·설비 관리 문맥의 서술은',
    '해당하지 않습니다. 반대로 사전에 없을 법한 표현(예: 특정 보호구 이름을',
    '직접 지목하거나, 환기·격리 같은 방법을 풀어 쓴 경우)도 조치로 셉니다.',
    '',
    '## 응답 형식',
    '',
    '판정은 `1`, `2`, `3`, `?` 넷 중 **하나만** 적습니다. 설명·근거·다른 문자는 붙이지',
    '않습니다.',
]


def coder_prompt():
    """코더가 보는 지시문 전문. 규칙 지식은 여기에만 있다 (설계 원칙 1)."""
    return '\n'.join([
        '각 항목의 본문을 읽고 등급 1/2/3 중 하나를 매깁니다.',
        '**규칙이 매긴 등급은 이 문서에 없습니다.** 본문만 보고 판단하세요.',
        '',
    ] + GRADE_GUIDE)


def chunk_text(text, size=CHUNK_CHARS):
    """긴 본문을 읽을 만한 덩어리로 나눈다. 이어붙이면 원문과 같아야 한다.

    문단 경계를 우선하고, 없으면 줄 경계, 그것도 없으면 그냥 끊는다. 경계 문자는
    앞 덩어리 끝에 **통째로** 남긴다 — 어느 쪽에도 넣지 않으면 개행이 사라지고,
    반만 넣으면 문단 경계가 두 덩어리에 걸쳐 쪼개진다.

    탐색 상한이 `size - 1` 인 것은 두 글자짜리 '\\n\\n' 이 경계를 넘어가지 않게
    하기 위해서다. 그래야 모든 덩어리가 size 이하로 유지된다.
    """
    if len(text) <= size:
        return [text]
    out, rest = [], text
    while len(rest) > size:
        cut = rest.rfind('\n\n', size // 2, size - 1)
        if cut != -1:
            cut += 2
        else:
            cut = rest.rfind('\n', size // 2, size)
            cut = size if cut == -1 else cut + 1
        out.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        out.append(rest)
    return out


def fence_for(text):
    """본문 안의 백틱 연속보다 긴 펜스를 고른다.

    전문을 싣게 되면서 본문이 5배 길어졌다. 안에 ``` 가 하나라도 있으면 코드
    블록이 거기서 닫혀 코더가 보는 화면이 조용히 망가진다.
    """
    runs = re.findall(r'`+', text)
    return '`' * max([3] + [len(m) + 1 for m in runs])


def sample_digest(key):
    """표본의 정체성 해시 — (교재, 페이지, 군) 전체.

    코더 라벨(coding_A/B.json)은 **항목 번호로만** 페이지에 붙는다. 이 스크립트를
    다시 돌리면 rng.shuffle 로 번호가 전부 바뀌는데, score_coding 의 예전 가드는
    분쟁군 **개수**만 비교했다 — 개수가 우연히 맞으면 엉뚱한 페이지의 라벨로
    κ 와 F1 이 그럴듯하게 찍힌다. 번호가 아니라 표본 자체를 지문으로 묶는다.

    페이지 순서로 정렬해 shuffle 결과와 무관하게 만든다. 같은 표본이면 몇 번을
    다시 만들어도 같은 지문이 나오고, 표본이 바뀌면 반드시 달라진다.
    """
    body = '\n'.join('%s|%s|%s' % (r['file'], r['page'], r['group'])
                      for r in sorted(key, key=lambda r: (str(r['file']), r['page'])))
    return hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]


def strata(preds, pairs=None):
    """변형별 예측에서 4층을 가른다. 반환: {군: 정렬된 키 목록} (재현율층은 모집단).

    preds: {변형: {(교재,쪽): {'g': 등급}}}, 'baseline' 포함.

    합집합이다 — 어느 규칙쌍에서든 갈리면 분쟁군이고, 어느 변형이든 등급3이면
    전수 대상이다. 단조성("수정본 등급3 ⊆ 현행 등급3")은 실측으로 성립하지만
    여기서 기대지 않는다: 그 논증이 어느 변형에서 깨져도 층은 그대로 옳다.
    """
    pairs = pairs or RULE_PAIRS
    keys = set(preds[BASELINE])
    g3 = {k for g in preds.values() for k in keys if g[k]['g'] == 3}
    disputed = {k for cur, new in pairs for k in keys
                if preds[cur][k]['g'] == 3 and preds[new][k]['g'] != 3}
    boundary = {k for cur, new in pairs for k in keys - g3
                if preds[cur][k]['g'] == 2 and preds[new][k]['g'] == 1}
    return {'disputed': sorted(disputed), 'control': sorted(g3 - disputed),
            'boundary': sorted(boundary), 'recall_pool': sorted(keys - g3 - boundary)}


def draw(st, seed=SEED, n_recall=N_RECALL):
    """전수 3층 + 재현율 무작위층 → [(키, 군)]. 시드에 결정적이다."""
    rng = random.Random(seed)
    pool = list(st['recall_pool'])
    recall = rng.sample(pool, min(n_recall, len(pool)))
    items = ([(k, 'disputed') for k in st['disputed']]
             + [(k, 'control') for k in st['control']]
             + [(k, 'boundary') for k in st['boundary']]
             + [(k, 'recall') for k in recall])
    rng.shuffle(items)                       # 군이 섞여야 코더가 눈치채지 못한다
    return items


def build_sheet(pages, items, preds):
    """표본 항목들을 (코더용 시트, 정답 키) 두 목록으로 만든다.

    **본문은 어떤 경우에도 자르지 않는다.** 채점기(`regrade.py`)가 보는 텍스트와
    코더가 보는 텍스트가 같아야 F1·κ 가 규칙을 재는 값이 된다. 길이가 문제면
    자르지 말고 `chunk_text()` 로 나눠 보여준다.

    시트에는 등급·카운트·군이 없고(앵커링), 키에는 변형별 예측 등급 `pred` 가 실린다.
    'cell_truncated' 는 **원본이** 엑셀 셀 한도에서 잘렸다는 뜻이다.
    """
    sheet, key = [], []
    for i, (k, grp) in enumerate(items, 1):
        fn, pg = k
        text = pages[k]['text']
        it = {'id': i, 'text': text, 'chars': len(text),
              'cell_truncated': pages[k]['truncated']}
        if pages[k]['truncated']:
            it['notice'] = ' '.join(TRUNCATION_NOTICE)   # API 코더도 같은 고지를 본다
        sheet.append(it)
        key.append({
            'id': i, 'group': grp, 'file': fn, 'page': pg,
            'cell_truncated': pages[k]['truncated'],
            'pred': {name: g[k]['g'] for name, g in preds.items()},
        })
    return sheet, key


def render_item(it):
    """항목 하나를 코딩 시트 마크다운 줄 목록으로 렌더한다."""
    md = ['### %d' % it['id'], '']
    if it['cell_truncated']:
        md += ['> ' + line for line in TRUNCATION_NOTICE] + ['']
    parts = chunk_text(it['text'])
    fence = fence_for(it['text'])
    for j, part in enumerate(parts, 1):
        if len(parts) > 1:                       # 항목은 하나다. 판정도 하나만 받는다
            md += ['**(본문 %d/%d)**' % (j, len(parts)), '']
        md += [fence + 'text', part, fence, '']
    return md + ['판정: ____', '', '---', '']


def main():
    import argparse
    ap = argparse.ArgumentParser(description='수기 코딩 시트 생성')
    ap.add_argument('--force', action='store_true',
                    help='기존 coding_key.json 을 덮어쓴다 (라벨 삼종의 결합 정보가 바뀐다)')
    args = ap.parse_args()

    src = os.path.join(RG.DATA_DIR, RG.NCS_FILE)
    if not os.path.exists(src):
        sys.exit('원본 엑셀을 찾을 수 없습니다: %s' % src)
    key_path = os.path.join(HERE, 'coding_key.json')
    if os.path.exists(key_path) and not args.force:
        # 키는 coding_A/B/C.json 을 페이지에 붙이는 유일한 결합 정보다. 지문 가드는 어긋난
        # 라벨의 **채점**을 막지 이 파일의 **덮어쓰기**를 막지 않는다 — 기본 실행이 기존
        # 코딩 기록의 결합을 끊어서는 안 된다 (PR #12 리뷰 지적).
        sys.exit('coding_key.json 이 이미 있습니다 — 기존 라벨(coding_A/B/C.json)의 결합 정보입니다.\n'
                 '  다시 뽑으려면 --force 를 주십시오 (그 뒤에는 새 시트로 다시 코딩해야 합니다).')

    print('원본 읽는 중…')
    pages = RG.load_pages(src)
    med = RG.median_length(pages)
    preds = {BASELINE: RG.run(pages, word_boundary=False, normalize=False)}
    for name, kw in RG.variant_grid():
        preds[name] = RG.run(pages, base=med, **kw)

    st = strata(preds)
    items = draw(st)
    sheet, key = build_sheet(pages, items, preds)
    digest = sample_digest(key)
    counts = {g: sum(1 for _, gg in items if gg == g) for g in GROUPS}

    key_doc = {
        'sample_digest': digest, 'seed': SEED, 'n_recall': N_RECALL,
        'variants': list(preds), 'rule_pairs': RULE_PAIRS,
        'population': {'pages': len(pages), 'recall_pool': len(st['recall_pool']),
                       'strata': counts},
        'items': key,
    }
    sheet_doc = {'sample_digest': digest, 'coder_prompt': coder_prompt(), 'items': sheet}
    for name, obj in (('coding_sheet.json', sheet_doc), ('coding_key.json', key_doc)):
        p = os.path.join(HERE, name)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        print('  %s (%d항목)' % (name, len(obj['items'])))

    md = [
        '# 안전등급 수기 코딩 시트',
        '',
        '## 표본 지문',
        '',
        '```',
        digest,
        '```',
        '',
        '답안 파일(`coding_A.json`)에 이 값을 **그대로** 적으십시오:',
        '`{"coder": "A", "sample_digest": "' + digest + '", "grades": {...}}`',
        '',
        '항목 번호는 시트를 다시 만들 때마다 바뀝니다. 지문이 없거나 다르면 채점기가',
        '거부합니다 — 엉뚱한 페이지의 라벨로 수치가 찍히는 것을 막기 위해서입니다.',
        '',
        coder_prompt(),
        '',
        '## 항목',
        '',
    ]
    for it in sheet:
        md += render_item(it)
    p = os.path.join(HERE, 'coding_sheet.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print('  coding_sheet.md')

    chars = {g: sum(len(pages[k]['text']) for k, gg in items if gg == g) for g in GROUPS}
    print('\n층별 쪽수 / 글자 수 (재현율 모집단 %d쪽, 전체 %d쪽):'
          % (len(st['recall_pool']), len(pages)))
    for g in GROUPS:
        print('  %-9s %4d쪽  %9s자' % (g, counts[g], format(chars[g], ',')))
    print('  %-9s %4d쪽  %9s자' % ('합계', len(items), format(sum(chars.values()), ',')))
    print('원본이 잘린 항목 %d개 (복구 불가, 고지 부착) / 분할 제시 항목 %d개'
          % (sum(1 for it in sheet if it['cell_truncated']),
             sum(1 for it in sheet if it['chars'] > CHUNK_CHARS)))
    print('키(정답)는 coding_key.json 에 별도로 있습니다. 코딩 중에는 열지 마세요.')


if __name__ == '__main__':
    main()
