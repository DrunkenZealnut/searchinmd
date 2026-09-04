#!/usr/bin/env python3
"""
교차 판정 채점 — 두 코더의 판정을 서로, 그리고 두 규칙과 대조한다.

    python3 score_coding.py --coders C,B          # 주 결과: coding_C.json vs coding_B.json (FR-1 쌍)
    python3 score_coding.py --coders A,B --out docs/03-analysis/data/recoding_scores_AB.json
    python3 score_coding.py                       # 기본 A,B — 구형식 키면 예전 경로

## 이게 무엇이 아닌지 먼저

**AI 두 코더의 일치는 사람 이중코딩이 아니다.** 같은 계열 모델은 오류가 상관되므로
높은 일치율이 정확도가 아니라 공통 편향을 보여줄 수 있다. 이 결과는 규칙이 명백히
틀린 페이지를 싸게 찾아내는 **선별(triage)** 이지 발표 수치의 근거가 아니다.

## 무엇을 재는가 — 4층 전수 + 재현율층 (recoding.design.md §4)

키가 새 형식(`population` + 항목별 `pred`)이면 전수 채점 경로로 간다.

  분쟁군   어느 규칙쌍에서든 현행=3, 수정본≠3 — 코더가 어느 쪽 손을 드느냐가 우열을 가른다
  합의군   어느 변형이든 등급3인 나머지 — 코더가 원래 등급3에 인색한지 보는 기준선
  경계층   현행=2, 수정본=1 — 재채점이 가장 많이 움직인 경계. 여기서 코더가 3 이라 하면
           두 규칙이 **모두** 놓친 것이다
  재현율층 현행이 등급1·2인 나머지에서 무작위 — **재현율이 처음 측정되는 곳.** 적중 h 건에
           유한모집단 정확(초기하) 구간을 붙이고, 0 건이면 점추정 없이 상한만 낸다

앞의 세 층은 전수라 변형별 정밀도에 표집오차가 없다. 남는 불확실성은 (a) 재현율층의
표집오차 — 구간으로 낸다, (b) 코더 신뢰도 — 두 코더의 값을 따로 내고 "양쪽 모두 3 ≤
한쪽이라도 3" 폭을 병기한다. 정밀도 표에서 최고값을 골라 채택하면 이 표본에 과적합하는
것이다 — 이 표는 결함을 **발견**하는 데 쓰고 변형을 **고르는** 데 쓰지 않는다.

구형식 키(분쟁군·대조군 2층, `pred` 없음)는 예전 경로(main_legacy)로 간다.
"""
import json
import math
import os
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from page_utils import CODING_GROUPS, BASELINE  # noqa: E402


def load(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        sys.exit('없음: %s' % name)
    return json.load(open(p, encoding='utf-8'))


UNSURE = '?'                     # make_coding_sheet.py 가 코더에게 주는 '판단 불가' 코드


def unwrap(doc):
    """{'sample_digest':…, 'items':[…]} 와 구버전 평평한 리스트를 모두 받는다."""
    if isinstance(doc, dict):
        return doc.get('items', []), doc.get('sample_digest')
    return doc, None


def check_sample(key_digest, *coder_docs):
    """코더 라벨이 **이 표본**에서 나온 것인지 지문으로 확인한다.

    라벨은 항목 번호로만 페이지에 붙는데, make_coding_sheet 를 다시 돌리면
    shuffle 로 번호가 전부 바뀐다. 예전 가드는 분쟁군 **개수**만 비교해서,
    개수가 우연히 맞으면 엉뚱한 페이지의 라벨로 κ 와 F1 이 그럴듯하게 찍혔다.
    숫자가 조용히 틀리는 것이 죽는 것보다 나쁘므로 여기서 멈춘다.
    """
    if key_digest is None:
        sys.exit('coding_key.json 에 sample_digest 가 없습니다 (구버전 산출물).\n'
                 '  make_coding_sheet.py 를 다시 돌린 뒤 **그 시트로 다시 코딩**하십시오.\n'
                 '  기존 라벨은 항목 번호가 달라 그대로 재사용할 수 없습니다.')
    for d in coder_docs:
        got = d.get('sample_digest') if isinstance(d, dict) else None
        if got != key_digest:
            sys.exit('표본 지문 불일치 — 코더 %s: %s / 키: %s\n'
                     '  이 라벨은 **다른 표본**에서 나온 것이라 채점할 수 없습니다.\n'
                     '  항목 번호로 억지로 맞추면 엉뚱한 페이지의 라벨이 됩니다.'
                     % (d.get('coder', '?') if isinstance(d, dict) else '?',
                        got or '(없음)', key_digest))


def dist(vals):
    """등급 분포를 정렬해 보여준다. 1·2·3 과 '?' 가 섞여도 깨지지 않는다.

    `sorted(Counter(...).items())` 는 int 와 str 을 비교하려다 TypeError 로 죽는다.
    코더는 `?` 를 쓸 수 있으므로(make_coding_sheet.py) 여기서 막아야 한다.
    """
    return dict(sorted(Counter(vals).items(), key=lambda kv: (str(kv[0]) == UNSURE,
                                                              str(kv[0]))))


def kappa(a, b, cats=None):
    """Cohen's kappa — 우연 일치를 뺀 일치도.

    cats 를 관측값에서 뽑는다. 고정 (1,2,3) 이면 `?` 쌍이 분자(po)에는 들어가고
    분모의 우연 일치(pe)에서는 빠져 **κ 가 부풀려진다.** κ 는 발표에 인용되는
    값이라(TODOS.md 0.796) 조용히 높아지면 안 된다.
    """
    n = len(a)
    if not n:
        return float('nan')
    if cats is None:
        cats = set(a) | set(b)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float('nan')


def score_variants(A, B, key, dis, ctl):
    """규칙 변형들을 코더 라벨로 채점한다. 원본 엑셀이 있을 때만 돈다.

    ## 순환논증 경고

    이 69쪽은 규칙을 **고르는** 데 쓰면 안 된다. 라벨에 맞춰 임계를 조정한 뒤
    같은 라벨로 검증하면 아무것도 검증하지 않은 것이다. 표에서 가장 높은 F1 을
    골라 채택하는 것은 이 표본에 과적합하는 것이다.

    D4 의 'round' 를 "사전 선택" 이라 했던 이전 서술은 철회한다. 저장소에 이를
    입증할 산출물이 없고 커밋 시각은 반대를 가리킨다 — 라벨이 확정된 뒤에
    discretize 가 등장했다. D4 라는 결함 범주 자체가 라벨 검토 중에 착안됐으므로
    엄밀한 사전등록이 아니다. 말할 수 있는 것은 'round' 가 선험적으로 방어
    가능하다는 것과, 점수가 더 높은 'floor' 를 채택하지 않았다는 것까지다.

    ## 이 라벨 자체가 무효다

    코더 A 는 규칙 작성 당사자였고(규칙에 맹검이 아니었다), make_coding_sheet.py
    의 코더 지시문이 D1 의 동음이의 가정과 "판단이 갈리면 낮은 등급" 이라는
    방향성 동점 규칙을 두 코더 모두에게 주입했다. 아래 표는 폐기 예정 탐색값이며
    발행 근거가 아니다.
    """
    sys.path.insert(0, HERE)
    try:
        import regrade as RG
        pages = RG.load_pages(os.path.join(RG.DATA_DIR, RG.NCS_FILE))
    except (ImportError, SystemExit, OSError):
        return                                   # 원본이나 openpyxl이 없으면 조용히 건너뛴다

    med = RG.median_length(pages)
    old = RG.run(pages, word_boundary=False, normalize=False)
    dis_keys = {(key[i]['file'], key[i]['page']) for i in dis}

    variants = [
        ('현행(결함 유지)', dict(word_boundary=False, normalize=False)),
        ('D1+D2 (ceil, 현재)', dict(word_boundary=True, normalize=True)),
        ('D1+D2+D5 조건부면제',
         dict(word_boundary=True, normalize=True, exempt=True)),
        ('D1+D2+D4 round',
         dict(word_boundary=True, normalize=True, how='round')),
        ('D1+D2+D4 floor',
         dict(word_boundary=True, normalize=True, how='floor')),
    ]

    # 변형 그리드는 **코더와 무관하다** — 아래 코더 루프 안에서 돌리면 1,847쪽 ×
    # 5변형의 count_terms 스캔(페이지당 최대 32,767자)이 통째로 두 번 돈다.
    # 코더 라벨은 tp/정밀도 산술에만 쓰인다. 한 번 계산해 재사용한다.
    preds = {}
    for name, kw in variants:
        g = RG.run(pages, base=med, **kw)
        preds[name] = {k for k in g if g[k]['g'] == 3}
    agr_pop = len({k for k in old if old[k]['g'] == 3} - dis_keys)

    print('\n=== 5. 규칙 변형별 채점 (코더 라벨 기준) ===')
    print('  주의: 이 표에서 최고 F1 을 골라 채택하면 69쪽에 과적합하는 것이다.')
    print('  %-22s %6s %8s %7s %7s %7s' %
          ('변형', '등급3', '전체비율', '정밀도', '재현율', 'F1'))
    for nm, G in (('A', A), ('B', B)):
        # 합집합(현행의 등급3) 안 진짜 등급3 — 변형과 무관한 고정 분모
        true_all = (sum(1 for i in dis if G[i] == 3)
                    + sum(1 for i in ctl if G[i] == 3) / float(len(ctl)) * agr_pop)
        print('  --- 코더 %s (진짜 등급3 추정 %.1f쪽) ---' % (nm, true_all))
        for name, kw in variants:
            pred = preds[name]
            if not pred:
                continue
            tp_dis = sum(1 for i in dis
                         if (key[i]['file'], key[i]['page']) in pred and G[i] == 3)
            hit = [i for i in ctl if (key[i]['file'], key[i]['page']) in pred]
            rate = sum(1 for i in hit if G[i] == 3) / float(len(hit)) if hit else 0.0
            tp = tp_dis + rate * len(pred - dis_keys)
            p = tp / len(pred)
            r = tp / true_all if true_all else 0.0
            f1 = 2 * p * r / (p + r) if (p + r) else 0.0
            print('  %-22s %6d %7.1f%% %6.1f%% %6.1f%% %7.3f'
                  % (name, len(pred), len(pred) * 100.0 / len(pages),
                     p * 100, r * 100, f1))


def strata(A, B, key, ids, names=('A', 'B')):
    """절단 여부로 층을 갈라 따로 본다 (외부감사 C-1).

    통합 수치만 내면 절단의 집중도가 가려진다 — 통합 κ 0.796 이 분쟁군 0.769·
    대조군 0.760 보다 높았던 것과 같은 함정이다. 층 구성이 만든 값을 층과 무관한
    값으로 읽게 된다.

    절단쪽은 원본이 엑셀 셀 한도에서 잘려 뒷부분이 존재하지 않는다. 코더가 "조치
    없음" 이라 한 것이 진짜 없어서인지 잘려서 못 본 것인지 구분할 수 없으므로,
    이 층의 라벨은 다른 층과 같은 무게로 다룰 수 없다.
    """
    print('\n=== 3-1. 절단층 분리 (외부감사 C-1) ===')
    if not any('cell_truncated' in key[i] for i in ids):
        print('  키에 절단 정보가 없습니다 (구버전 coding_key.json).')
        print('  python3 make_coding_sheet.py 를 다시 돌린 뒤 재코딩하십시오.')
        return None

    stats = _truncation_stats(A, B, key, ids)      # 콘솔과 JSON 이 같은 계산을 쓴다
    cut = [i for i in ids if key[i].get('cell_truncated')]
    ok = [i for i in ids if not key[i].get('cell_truncated')]
    print('  절단층 %d항목 / 비절단층 %d항목' % (len(cut), len(ok)))
    if not cut:
        print('  절단 항목이 없어 층 분리가 무의미합니다.')
        return stats

    for nm, sub in (('절단층', cut), ('비절단층', ok)):
        if not sub:
            continue
        # 층이 작으면 κ·F1 을 내지 않는다 (SMALL_STRATUM_N) — _agreement_line 이 그 규칙을 갖는다.
        line, a, b, _ = _agreement_line(A, B, sub)
        print('  %s %2d항목  %s' % (nm, len(sub), line))
        print('    %s 분포 %s   %s 분포 %s' % (names[0], dist(a), names[1], dist(b)))

    # 민감도 — 절단 항목을 빼면 분쟁군의 결론이 달라지는가.
    #
    # 층별 F1 은 내지 않는다. 절단층은 한 자릿수라 F1 신뢰구간이 변형 간 차이보다
    # 넓고(감사 M-3), 무엇보다 분쟁군은 **전수** 표집이라 일부를 빼면 모집단 대비
    # 가중이 어긋난다 — 표본 수치를 모집단 예측 수와 나누는 4·5절 계산이 그대로
    # 무너진다. 해석 가능한 것은 분쟁군 안의 '수정본 지지율' 이라는 비율이다.
    dis_all = [i for i in ids if key[i]['group'] == 'disputed']
    dis_ok = [i for i in dis_all if not key[i].get('cell_truncated')]
    if dis_ok and len(dis_ok) < len(dis_all):
        print('  분쟁군 수정본 지지율 (두 코더 모두 등급 1·2):')
        for nm, sub in (('절단 포함', dis_all), ('절단 제외', dis_ok)):
            # `?`(판단 불가)는 분자에서도 분모에서도 뺀다. 분자에서만 빼면 절단
            # 항목에 `?` 를 권한 지시문이 그대로 지지율을 끌어내린다.
            ok = _both_valid(A, B, sub)
            both_new = sum(1 for i in ok if A[i] in (1, 2) and B[i] in (1, 2))
            print('    %s %2d쪽 중 %2d쪽 (%.0f%%)%s'
                  % (nm, len(ok), both_new, both_new * 100.0 / max(len(ok), 1),
                     '  (판단 불가 %d쪽 제외)' % (len(sub) - len(ok))
                     if len(ok) < len(sub) else ''))
        print('    두 값이 크게 벌어지면 수정본 우세가 절단 인공물일 수 있다.')

    if len(cut) < SMALL_STRATUM_N:
        print('  절단층은 표본이 작아 원자료를 그대로 싣는다:')
        print('    %-4s %-9s %-3s %-3s %s' % ('id', '군', names[0], names[1], '교재/쪽'))
        for i in sorted(cut, key=int):
            r = key[i]
            print('    %-4s %-9s %-3s %-3s %s p.%s'
                  % (i, r['group'], A.get(i, UNSURE), B.get(i, UNSURE),
                     str(r['file']).split('/')[-1][:34], r['page']))
    return stats


def population():
    """모집단 수치는 regrade.py 산출물에서 읽는다. 여기 손으로 적지 않는다."""
    p = os.path.join(HERE, IMPACT_JSON)
    if not os.path.exists(p):
        sys.exit('없음: regrade_impact.json — 먼저 python3 regrade.py 를 돌리세요')
    with open(p, encoding='utf-8') as f:
        d = json.load(f)
    total = d['pages']
    cur3 = d['dist'][BASELINE]['3']              # 현행이 등급3이라 한 쪽
    # 어느 변형이 "수정본" 인지는 **산출물에게 묻는다.** 여기서 라벨을 타이핑하면
    # regrade.py 의 표시용 문자열을 두 벌 갖게 되고, 라벨을 손보는 순간 이 줄이
    # KeyError 로 죽는다. 'D1+D2 둘 다' 는 `adopted_variant` 가 없던 구버전
    # 산출물을 위한 폴백이다.
    adopted = d.get('adopted_variant', 'D1+D2 둘 다')
    if adopted not in d['dist']:
        sys.exit('regrade_impact.json 의 adopted_variant(%s)가 dist 에 없습니다. '
                 'python3 regrade.py 를 다시 돌리세요.' % adopted)
    new3 = d['dist'][adopted]['3']               # 수정본이 등급3이라 한 쪽
    return total, cur3 - new3, new3              # 전체, 분쟁군, 합의군


def main_legacy():
    """구형식 키(분쟁군·대조군 2층) 채점. 새 형식은 main_census() 가 맡는다."""
    doc_a, doc_b = load('coding_A.json'), load('coding_B.json')
    A, B = doc_a['grades'], doc_b['grades']
    key_items, key_digest = unwrap(load('coding_key.json'))
    check_sample(key_digest, doc_a, doc_b)      # 번호가 아니라 표본으로 묶는다
    key = {str(r['id']): r for r in key_items}
    global TOTAL_PAGES, N_DISPUTED, N_AGREED
    TOTAL_PAGES, N_DISPUTED, N_AGREED = population()

    # 분쟁군은 전수 표집이므로 키의 개수와 모집단 수치가 같아야 한다. 어긋나면
    # 4번 섹션의 가중치가 조용히 틀어지므로 여기서 멈춘다.
    n_dis_key = sum(1 for r in key.values() if r['group'] == 'disputed')
    if n_dis_key != N_DISPUTED:
        # 예전 안내문은 "다시 돌리세요" 였는데, 그것이 바로 오염시키는 행동이다 —
        # 시트를 다시 만들면 항목 번호가 바뀌므로 기존 라벨을 붙일 수 없다.
        sys.exit('불일치: 키의 분쟁군 %d쪽 vs regrade_impact.json 기준 %d쪽.\n'
                 '  규칙이 바뀌어 표본이 낡았습니다. make_coding_sheet.py 를 다시 돌린 뒤\n'
                 '  **새 시트로 다시 코딩**해야 합니다 — 기존 라벨을 새 키에 붙이면\n'
                 '  항목 번호가 달라 엉뚱한 페이지에 붙습니다.'
                 % (n_dis_key, N_DISPUTED))

    ids = sorted(key, key=int)
    a = [A.get(i, UNSURE) for i in ids]
    b = [B.get(i, UNSURE) for i in ids]

    print('=== 1. 두 코더의 일치도 (전체 %d항목) ===' % len(ids))
    agree = sum(x == y for x, y in zip(a, b))
    print('  단순 일치 %d/%d (%.1f%%)  Cohen κ = %.3f'
          % (agree, len(ids), agree * 100.0 / len(ids), kappa(a, b)))
    print('  코더 A 분포 %s' % dist(a))
    print('  코더 B 분포 %s' % dist(b))
    n_unsure = sum(1 for x in a + b if x == UNSURE)
    if n_unsure:
        print('  판단 불가(%s) %d건 — 지지율의 분모에서 뺀다 (완전응답 분석)' % (UNSURE, n_unsure))
    m = Counter((x, y) for x, y in zip(a, b) if x != y)
    if m:
        print('  불일치 패턴 (A→B): %s'
              % ', '.join('%s→%s:%s' % (x, y, c)
                          for (x, y), c in sorted(m.items(), key=lambda kv: str(kv[0]))))

    print('\n=== 2. 대조군 — 두 규칙이 모두 등급3이라 한 쪽 ===')
    ctl = [i for i in ids if key[i]['group'] == 'control']
    for nm, g in (('A', A), ('B', B)):
        c = Counter(g[i] for i in ctl)
        ok = c.get(3, 0)
        print('  코더 %s: 등급3 동의 %d/%d (%.0f%%)  분포 %s'
              % (nm, ok, len(ctl), ok * 100.0 / len(ctl), dist(g[i] for i in ctl)))
    both3 = sum(1 for i in ctl if A.get(i) == 3 and B.get(i) == 3)
    print('  두 코더 모두 등급3: %d/%d' % (both3, len(ctl)))

    print('\n=== 3. 분쟁군 — 현행은 등급3, 수정본은 아님 ===')
    dis = [i for i in ids if key[i]['group'] == 'disputed']
    print('  %d쪽. 코더가 등급3 이라 하면 현행 규칙이 옳고, 아니라 하면 수정본이 옳다.' % len(dis))
    # `?` 를 "수정본 지지" 로 세면 안 된다. `?` 는 방향 없는 코드로 도입됐는데
    # (make_coding_sheet.py 가 지운 '판단이 갈리면 낮은 등급' 대신), != 3 으로 세면
    # 그 편향이 시트에서 채점기로 옮겨올 뿐이다. 명시적으로 1·2 인 것만 센다.
    for nm, g in (('A', A), ('B', B)):
        c = Counter(g[i] for i in dis)
        cur = c.get(3, 0)
        new = c.get(1, 0) + c.get(2, 0)
        print('  코더 %s: 현행 지지(등급3) %d  수정본 지지(1·2) %d  판단불가 %d  분포 %s'
              % (nm, cur, new, c.get(UNSURE, 0), dist(g[i] for i in dis)))
    # `?` 는 분모에서도 뺀다. 남겨 두면 "확실히 등급3 아님" 으로 채점되는 셈인데,
    # make_coding_sheet 가 **절단 항목에** `?` 를 권하고 절단은 등급3 에 몰려 있어
    # (16쪽 중 12쪽) 그 편향이 한 방향으로 실린다. 뺀 수를 함께 찍어 숨기지 않는다.
    dis_ok = _both_valid(A, B, dis)
    both_new = sum(1 for i in dis_ok if A[i] in (1, 2) and B[i] in (1, 2))
    both_old = sum(1 for i in dis_ok if A[i] == 3 and B[i] == 3)
    n_drop = len(dis) - len(dis_ok)
    tail = '  (판단 불가 %d쪽 제외)' % n_drop if n_drop else ''
    print('  두 코더 모두 수정본 지지: %d/%d (%.0f%%)%s'
          % (both_new, len(dis_ok), both_new * 100.0 / max(len(dis_ok), 1), tail))
    print('  두 코더 모두 현행 지지: %d/%d (%.0f%%)%s'
          % (both_old, len(dis_ok), both_old * 100.0 / max(len(dis_ok), 1), tail))

    strata(A, B, key, ids)

    print('\n=== 4. 규칙별 정밀도·재현율 (모집단 비중으로 보정) ===')
    print('  표본을 그대로 세면 안 된다. 분쟁군은 %d쪽 전수지만 대조군은 %d쪽 중 %d쪽만'
          % (N_DISPUTED, N_AGREED, len(ctl)))
    print('  뽑았다. 표본에서 분쟁군이 과대표집돼 있어 가중치를 되돌려야 한다.')
    print('  현행 등급3 = %d쪽(분쟁 %d + 합의 %d), 수정본 등급3 = 합의 %d쪽.'
          % (N_DISPUTED + N_AGREED, N_DISPUTED, N_AGREED, N_AGREED))
    print()
    for nm, g in (('A', A), ('B', B)):
        # 분쟁군은 전수라 그대로, 대조군은 표본비율을 합의군 전체로 환산
        tp_dis = sum(1 for i in dis if g[i] == 3)
        rate_ctl = sum(1 for i in ctl if g[i] == 3) / float(len(ctl))
        tp_agr = rate_ctl * N_AGREED
        true_total = tp_dis + tp_agr           # 두 규칙의 합집합 안의 진짜 등급3

        cur_p = true_total / float(N_DISPUTED + N_AGREED)
        cur_r = 1.0                            # 합집합 기준. 아래 주의 참조
        new_p = tp_agr / float(N_AGREED)
        new_r = tp_agr / true_total if true_total else float('nan')
        f1 = lambda p, r: 2 * p * r / (p + r) if (p + r) else float('nan')  # noqa: E731

        print('  코더 %s  (합집합 안 진짜 등급3 추정 %.1f쪽)' % (nm, true_total))
        print('    현행   정밀도 %.1f%%  재현율 %.0f%%  F1 %.3f  (%d쪽 예측)'
              % (cur_p * 100, cur_r * 100, f1(cur_p, cur_r), N_DISPUTED + N_AGREED))
        print('    수정본 정밀도 %.1f%%  재현율 %.1f%%  F1 %.3f  (%d쪽 예측)'
              % (new_p * 100, new_r * 100, f1(new_p, new_r), N_AGREED))
        print('    전체 %d쪽 대비 등급3 비율 — 현행 %.1f%%  수정본 %.1f%%  코더추정 %.1f%%'
              % (TOTAL_PAGES,
                 (N_DISPUTED + N_AGREED) * 100.0 / TOTAL_PAGES,
                 N_AGREED * 100.0 / TOTAL_PAGES,
                 true_total * 100.0 / TOTAL_PAGES))

    if os.path.exists(os.path.join(HERE, 'data')):
        score_variants(A, B, key, dis, ctl)

    print('\n주의 1: 현행의 재현율 100%는 측정된 값이 아니라 표본 설계의 산물이다.')
    print('        수정본은 강등만 하므로 그 등급3은 현행 등급3의 부분집합이고,')
    print('        표본은 그 합집합(=현행의 등급3) 안에서만 뽑혔다. 현행이 등급1·2로')
    print('        떨어뜨린 1,739쪽은 아무도 안 봤으므로 진짜 누락은 알 수 없다.')
    print('주의 2: 코더 둘 다 같은 계열 AI다. 일치율이 높아도 정확도가 아니라')
    print('        공통 편향일 수 있다. 발표 수치의 근거로는 사람 코딩이 필요하다.')


# ---------------------------------------------------------------------------
# 전수 + 재현율층 채점 (새 형식 키)
# ---------------------------------------------------------------------------
GROUP_LABELS = tuple(zip(CODING_GROUPS, ('분쟁군', '합의군', '경계층', '재현율층')))
UNSURE_WARN = 0.10   # 층별 `?` 비율이 이걸 넘으면 경고 — 표본이 조용히 줄어든 층이다 (설계 §8)
SMALL_STRATUM_N = 20  # 이보다 작은 층에서는 κ 를 내지 않고 원자료를 싣는다 — 9항목에 소수점 셋째 자리는 없는 정밀도다 (감사 M-3)


def is_census_key(doc):
    return (isinstance(doc, dict) and 'population' in doc
            and bool(doc.get('items')) and all('pred' in r for r in doc['items']))


ALPHA = 0.05                     # 구간의 유의수준 — 아래 문구의 "95%" 는 전부 이 값에서 나온다
CI_PCT = int(round((1 - ALPHA) * 100))


def _hyper_cdf(N, K, n, h):
    """P(X <= h): 모집단 N 에 양성 K, 비복원 n 추출. K 에 대해 단조 감소. 정수 조합수라 정확하다."""
    tot = math.comb(N, n)
    s = sum(math.comb(K, k) * math.comb(N - K, n - k)
            for k in range(max(0, n - (N - K)), min(h, K, n) + 1))
    return min(s / tot, 1.0)


def missed_interval(N, n, h, alpha=ALPHA):
    """재현율층: 모집단 N 에서 n 을 뽑아 h 건 적중 → 모집단의 진짜 등급3 수 K.

    반환 (점추정, 하한, 상한). 유한모집단 **정확** 구간(초기하 분포, Clopper-Pearson 형).
    h == 0 이면 점추정 없이(0) 단측 (1-alpha) 상한만 — "0 건도 결과다" 를 수치로 만든다.
    n == N(전수)이면 구간이 점으로 닫힌다. Wilson+FPC 근사 대신 정확 구간을 쓴 이유:
    n=300 에 h 가 한 자릿수일 때 정규 근사가 하한을 음수로 만든다.
    """
    if n <= 0 or N <= 0:
        return (0, 0, N)                          # 표본이 없으면 아무 것도 말할 수 없다
    n = min(n, N)
    if h == 0:
        hi = 0
        for K in range(0, N - n + 1):             # K > N-n 이면 0 건 적중이 불가능하다
            if _hyper_cdf(N, K, n, 0) >= alpha:
                hi = K
            else:
                break
        return (0, 0, hi)
    k_hat = h * N / float(n)
    kmax = N - (n - h)                            # 음성이 n-h 개는 있어야 한다
    lo = h
    for K in range(h, kmax + 1):
        if 1.0 - _hyper_cdf(N, K, n, h - 1) >= alpha / 2:
            lo = K
            break
    hi = h
    for K in range(h, kmax + 1):
        if _hyper_cdf(N, K, n, h) >= alpha / 2:
            hi = K
        else:
            break
    return (k_hat, lo, hi)


def check_population(key_doc, impact):
    """키의 변형별 등급3 전수가 regrade_impact.json 의 분포와 같아야 한다.

    전수 채점은 "어느 변형의 등급3이든 표본에 다 들어 있다" 에 기댄다. 규칙이 바뀌어
    산출물이 갱신됐는데 표본이 옛것이면 정밀도의 분모가 조용히 틀어진다 — 여기서 멈춘다.
    """
    pages = key_doc['population']['pages']
    if pages != impact['pages']:
        sys.exit('불일치: 키의 전체 %d쪽 vs regrade_impact.json %d쪽 — 표본이 낡았습니다. '
                 'make_coding_sheet.py 를 다시 돌린 뒤 새 시트로 다시 코딩하십시오.'
                 % (pages, impact['pages']))
    counts = Counter(v for r in key_doc['items'] for v, g in r['pred'].items() if g == 3)
    bad = ['%s: 키 %d ≠ 산출물 %s' % (v, counts.get(v, 0), d.get('3'))
           for v, d in impact['dist'].items()
           if v in key_doc.get('variants', counts) and counts.get(v, 0) != int(d.get('3', -1))]
    if bad:
        sys.exit('불일치: 변형별 등급3 전수가 regrade_impact.json 과 다릅니다 — %s.\n'
                 '  규칙이 바뀌어 표본이 낡았습니다. make_coding_sheet.py 를 다시 돌린 뒤\n'
                 '  **새 시트로 다시 코딩**해야 합니다 — 기존 라벨을 새 키에 붙이면 엉뚱한\n'
                 '  페이지에 붙습니다.' % '; '.join(bad))


# 호스트 → 모델 계열. 같은 계열이 API 로도(api.anthropic.com) Claude Code 로도(claude-cli://anthropic)
# 들어올 수 있고, 집계 호스트(openrouter)는 model 의 'vendor/…' 접두가 계열이다.
FAMILY_HOSTS = {'api.openai.com': 'openai', 'generativelanguage.googleapis.com': 'google',
                'api.anthropic.com': 'anthropic', 'anthropic': 'anthropic',
                'api.deepseek.com': 'deepseek', 'api.groq.com': 'groq'}
AGGREGATOR_HOSTS = {'openrouter.ai'}


def model_family(meta):
    host = urllib.parse.urlsplit(meta.get('base_url') or '').hostname or ''
    model = meta.get('model') or ''
    if host in AGGREGATOR_HOSTS:
        return model.split('/')[0] if '/' in model else host
    return FAMILY_HOSTS.get(host, host)


def family_guard(meta_a, meta_b):
    """FR-1: 두 코더의 모델 계열이 달라야 한다. 같은 계열이면 경고문을, 아니면 None."""
    if not meta_a or not meta_b:
        return ('주의 (FR-1 미확인): 코더 산출물에 meta 가 없어 모델 계열을 확인할 수 없습니다. '
                'code_pages.py 로 만든 산출물이 아니면 model·base_url 을 손으로 적으십시오.')
    fa, fb = model_family(meta_a), model_family(meta_b)
    if fa and fa == fb:
        return ('주의 (FR-1 미충족): 두 코더가 같은 계열(%s)입니다 — %s / %s. 같은 계열은 '
                '오류가 상관되므로 일치율이 정확도가 아니라 공통 편향일 수 있습니다. 발표 근거로 '
                '쓰려면 코더 하나를 다른 계열로 바꾸십시오.'
                % (fa, meta_a.get('model'), meta_b.get('model')))
    return None


def _truncation_stats(A, B, key, ids):
    """절단층 수치 — strata() 의 콘솔 출력과 recoding_scores.json 이 같은 계산을 쓴다."""
    cut = [i for i in ids if key[i].get('cell_truncated')]
    dis = [i for i in ids if key[i].get('group') == 'disputed']

    def support(sub):
        ok = _both_valid(A, B, sub)
        return [sum(1 for i in ok if A[i] in (1, 2) and B[i] in (1, 2)), len(ok)]
    return {'n': len(cut),
            'agree': sum(1 for i in cut if A.get(i, UNSURE) == B.get(i, UNSURE)),
            'both3': sum(1 for i in cut if A.get(i) == 3 and B.get(i) == 3),
            'disputed_support': {'with': support(dis),
                                 'without': support([i for i in dis if not key[i].get('cell_truncated')])}}


def _both_valid(A, B, ids):
    """두 코더가 모두 `?` 가 아닌 항목 — 지지율·폭·재현율층 추정의 공통 분모."""
    return [i for i in ids if A.get(i, UNSURE) != UNSURE and B.get(i, UNSURE) != UNSURE]


def _agreement_line(A, B, sub):
    a = [A.get(i, UNSURE) for i in sub]
    b = [B.get(i, UNSURE) for i in sub]
    agree = sum(x == y for x, y in zip(a, b))
    line = '일치 %d/%d (%.0f%%)' % (agree, len(sub), agree * 100.0 / max(len(sub), 1))
    if len(sub) >= SMALL_STRATUM_N:               # 작은 층에서 κ 를 내면 없는 정밀도를 주장한다
        line += '  κ = %.3f' % kappa(a, b)
    return line, a, b, agree


def _recall_est(G, rec_ids, N):
    valid = [i for i in rec_ids if G.get(i, UNSURE) != UNSURE]
    hits = sum(1 for i in valid if G[i] == 3)
    k_hat, lo, hi = missed_interval(N, len(valid), hits)
    return {'n': len(valid), 'hits': hits, 'N': N, 'k_hat': k_hat, 'lo': lo, 'hi': hi,
            'unsure': len(rec_ids) - len(valid)}


def _f1(p, r):
    return 2 * p * r / (p + r) if (p + r) else float('nan')


def score_census(A, B, key_doc, meta_a=None, meta_b=None, names=('A', 'B')):
    """4층 전수 + 재현율층 채점. 보고를 출력하고 수치를 dict 로 돌려준다."""
    items = key_doc['items']
    key = {str(r['id']): r for r in items}
    ids = sorted(key, key=int)
    variants = list(key_doc.get('variants') or items[0]['pred'])
    pop = key_doc['population']
    groups = {g: [i for i in ids if key[i]['group'] == g] for g, _ in GROUP_LABELS}
    census = groups['disputed'] + groups['control'] + groups['boundary']

    # 전수성 가드 — 재현율층에 등급3 예측이 있으면 "어느 변형의 등급3이든 전수" 가 깨진다.
    stale = [i for i in groups['recall'] if any(key[i]['pred'].get(v) == 3 for v in variants)]
    if stale:
        sys.exit('재현율층 %d항목에 등급3 예측이 있습니다 (예: id %s). 규칙이 바뀌어 표본이 '
                 '낡았습니다 — make_coding_sheet.py 를 다시 돌린 뒤 새 시트로 다시 코딩하십시오.'
                 % (len(stale), stale[0]))

    coders = ((names[0], A), (names[1], B))
    print('=== 1. 두 코더의 일치도 (전체 %d항목) ===' % len(ids))
    line, a, b, agree = _agreement_line(A, B, ids)
    print('  단순 %s' % line)
    if len(ids) < SMALL_STRATUM_N:
        print('  Cohen κ = %.3f' % kappa(a, b))
    res = {'groups': {g: len(groups[g]) for g, _ in GROUP_LABELS}, 'variants': variants,
           'agreement': {'n': len(ids), 'agree': agree, 'kappa': kappa(a, b)},
           'group_stats': {}}
    print('  코더 %s 분포 %s\n  코더 %s 분포 %s' % (names[0], dist(a), names[1], dist(b)))
    n_unsure = sum(1 for x in a + b if x == UNSURE)
    if n_unsure:
        print('  판단 불가(%s) %d건 — 분자·분모 양쪽에서 뺀다 (완전응답 분석)' % (UNSURE, n_unsure))
    res['disagreement'] = dict(sorted(Counter('%s→%s' % (x, y) for x, y in zip(a, b)
                                              if x != y).items()))
    if res['disagreement']:
        print('  불일치 패턴 (%s→%s): %s' % (names[0], names[1], ', '.join('%s:%d' % kv for kv in res['disagreement'].items())))
    for nm, meta in ((names[0], meta_a), (names[1], meta_b)):
        if meta:
            print('  코더 %s: %s @ %s  온도 %s%s' % (
                nm, meta.get('model'), meta.get('base_url'), meta.get('temperature'),
                '' if meta.get('temperature_honored', True) else ' (모델이 거부 — 온도 없이 물음)'))

    print('\n=== 2. 층별 — 분포와 일치도 (전수 3층 + 재현율층) ===')
    for g, label in GROUP_LABELS:
        sub = groups[g]
        if not sub:
            print('  %-6s 0항목' % label)
            continue
        line, ga, gb, g_agree = _agreement_line(A, B, sub)
        print('  %-6s %3d항목  %s' % (label, len(sub), line))
        print('         %s 분포 %s   %s 분포 %s' % (names[0], dist(ga), names[1], dist(gb)))
        res['group_stats'][g] = {
            'n': len(sub), 'agree': g_agree,
            'kappa': kappa(ga, gb) if len(sub) >= SMALL_STRATUM_N else None,
            'dist': {names[0]: {str(k): v for k, v in dist(ga).items()},
                     names[1]: {str(k): v for k, v in dist(gb).items()}}}
        for nm, G in coders:
            k = sum(1 for i in sub if G.get(i, UNSURE) == UNSURE)
            if k / float(len(sub)) > UNSURE_WARN:
                res.setdefault('unsure_warnings', []).append(
                    {'group': g, 'coder': nm, 'unsure': k, 'n': len(sub), 'ratio': k / float(len(sub))})
                print('         경고: 코더 %s 의 판단 불가 비율 %d/%d (%.0f%%) 이 임계 %.0f%% 를 넘는다 — '
                      '이 층의 수치는 표본이 조용히 줄어든 값이다'
                      % (nm, k, len(sub), k * 100.0 / len(sub), UNSURE_WARN * 100))
    res.setdefault('unsure_warnings', [])

    pairs = key_doc.get('rule_pairs') or []
    if pairs:
        print('\n=== 3. 분쟁군 — 규칙쌍별 지지율 (현행=3, 수정본≠3 인 쪽) ===')
        print('  코더가 등급3 이라 하면 현행 규칙이 옳고, 1·2 라 하면 수정본이 옳다. `?` 는 양쪽에서 뺀다.')
    res['pair_support'] = []
    for cur, new in pairs:
        dis = [i for i in census if key[i]['pred'].get(cur) == 3 and key[i]['pred'].get(new) != 3]
        print('  [%s → %s] %d쪽' % (cur, new, len(dis)))
        entry = {'cur': cur, 'new': new, 'n': len(dis)}
        for nm, G in coders:
            c = Counter(G.get(i, UNSURE) for i in dis)
            entry[nm] = {'cur': c.get(3, 0), 'new': c.get(1, 0) + c.get(2, 0),
                         'unsure': c.get(UNSURE, 0)}
            print('    코더 %s: 현행 지지(3) %d  수정본 지지(1·2) %d  판단불가 %d'
                  % (nm, entry[nm]['cur'], entry[nm]['new'], entry[nm]['unsure']))
        ok = _both_valid(A, B, dis)
        both_new = sum(1 for i in ok if A[i] in (1, 2) and B[i] in (1, 2))
        both_old = sum(1 for i in ok if A[i] == 3 and B[i] == 3)
        tail = '  (판단 불가 %d쪽 제외)' % (len(dis) - len(ok)) if len(ok) < len(dis) else ''
        print('    두 코더 모두 수정본 지지 %d/%d (%.0f%%), 모두 현행 지지 %d/%d (%.0f%%)%s'
              % (both_new, len(ok), both_new * 100.0 / max(len(ok), 1),
                 both_old, len(ok), both_old * 100.0 / max(len(ok), 1), tail))
        entry.update({'valid': len(ok), 'both_old': both_old, 'both_new': both_new})
        res['pair_support'].append(entry)

    res['truncation'] = strata(A, B, key, ids, names) or _truncation_stats(A, B, key, ids)

    print('\n=== 4. 재현율층 — 처음 측정되는 누락 (모집단 %d쪽, 표본 %d항목) ==='
          % (pop['recall_pool'], len(groups['recall'])))
    print('  경계층은 두 규칙이 모두 등급3이 아니라 한 쪽이라 여기서 3 은 두 규칙 공통의 누락(전수)이다.')
    for nm, G in coders:
        rec = _recall_est(G, groups['recall'], pop['recall_pool'])
        bnd_valid = [i for i in groups['boundary'] if G.get(i, UNSURE) != UNSURE]
        bnd_hits = sum(1 for i in bnd_valid if G[i] == 3)
        census_true = sum(1 for i in census if G.get(i) == 3)
        if rec['hits'] == 0:
            est = '점추정 없음 — %d%% 상한 %d쪽 (모집단의 %.2f%%)' % (CI_PCT,
                rec['hi'], rec['hi'] * 100.0 / max(pop['recall_pool'], 1))
        else:
            est = '놓친 등급3 점추정 %.1f쪽, %d%% 구간 [%d, %d] (모집단의 %.1f%%)' % (
                rec['k_hat'], CI_PCT, rec['lo'], rec['hi'], rec['k_hat'] * 100.0 / max(pop['recall_pool'], 1))
        print('  코더 %s: 재현율층 적중 %d/%d%s → %s' % (
            nm, rec['hits'], rec['n'],
            ' (판단 불가 %d 제외)' % rec['unsure'] if rec['unsure'] else '', est))
        print('         경계층 적중 %d/%d (전수),  전수 3층의 진짜 등급3 %d쪽'
              % (bnd_hits, len(bnd_valid), census_true))
        res[nm] = {'recall': rec, 'boundary_hits': (bnd_hits, len(bnd_valid)),
                   'census_true': census_true, 'variants': {}}
    both_rec = _both_valid(A, B, groups['recall'])
    h3 = sum(1 for i in both_rec if A[i] == 3 and B[i] == 3)
    k3, lo3, hi3 = missed_interval(pop['recall_pool'], len(both_rec), h3)
    res['recall_both3'] = {'hits': h3, 'n': len(both_rec), 'N': pop['recall_pool'],
                           'k_hat': k3, 'lo': lo3, 'hi': hi3}
    print('  두 코더 모두 3: 재현율층 적중 %d/%d → 점추정 %.1f쪽, %d%% 구간 [%d, %d]'
          % (h3, len(both_rec), k3, CI_PCT, lo3, hi3))

    print('\n=== 5. 변형별 정밀도·재현율·F1 — 전수라 표본 가중이 없다 ===')
    print('  정밀도 폭 [양쪽 모두 3, 한쪽이라도 3] 은 코더 불일치가 만드는 범위다. 재현율 구간은 4절의 구간.')
    print('  주의: 이 표에서 최고값을 골라 채택하면 이 표본에 과적합하는 것이다.')
    both_ok = set(_both_valid(A, B, census))
    for nm, G in coders:
        r = res[nm]
        T = r['census_true'] + r['recall']['k_hat']
        T_lo, T_hi = r['census_true'] + r['recall']['lo'], r['census_true'] + r['recall']['hi']
        r['true_total'] = (T, T_lo, T_hi)
        print('  --- 코더 %s (진짜 등급3 추정 %.1f쪽 = 전수 %d + 재현율층 %.1f [%d, %d]; 전체 %d쪽의 %.1f%%) ---'
              % (nm, T, r['census_true'], r['recall']['k_hat'], r['recall']['lo'],
                 r['recall']['hi'], pop['pages'], T * 100.0 / max(pop['pages'], 1)))
        print('  %-20s %5s %7s %13s %7s %15s %6s'
              % ('변형', '예측', '정밀도', '[폭]', '재현율', '[구간]', 'F1'))
        for v in variants:
            P = [i for i in census if key[i]['pred'].get(v) == 3]
            excluded = sum(1 for i in P if G.get(i, UNSURE) == UNSURE)
            tp = sum(1 for i in P if G.get(i) == 3)
            denom = len(P) - excluded
            prec = tp / float(denom) if denom else float('nan')
            recall = tp / float(T) if T else float('nan')
            r_lo = tp / float(T_hi) if T_hi else float('nan')
            r_hi = tp / float(T_lo) if T_lo else float('nan')
            pb = [i for i in P if i in both_ok]
            band = {'both': sum(1 for i in pb if A[i] == 3 and B[i] == 3) / float(len(pb)) if pb else float('nan'),
                    'either': sum(1 for i in pb if A[i] == 3 or B[i] == 3) / float(len(pb)) if pb else float('nan')}
            r['variants'][v] = {'pred': len(P), 'excluded': excluded, 'tp': tp, 'precision': prec,
                                'recall': recall, 'recall_ci': (r_lo, r_hi), 'f1': _f1(prec, recall),
                                'band': band}
            print('  %-20s %5d %6.1f%% [%4.0f%%,%4.0f%%] %6.1f%% [%5.1f%%,%5.1f%%] %6.3f%s'
                  % (v, len(P), prec * 100, band['both'] * 100, band['either'] * 100,
                     recall * 100, r_lo * 100, r_hi * 100, _f1(prec, recall),
                     '  (판단 불가 %d 제외)' % excluded if excluded else ''))
    return res


SCORES_OUT = 'docs/03-analysis/data/recoding_scores.json'
IMPACT_JSON = 'docs/03-analysis/data/regrade_impact.json'   # regrade.py 산출물 — population()·check_population() 이 읽는다


def _no_nan(x):
    """JSON 에 NaN 을 쓰지 않는다 — 표준이 아니라 읽는 쪽이 갈린다. None 으로 바꾼다."""
    if isinstance(x, float) and math.isnan(x):
        return None
    if isinstance(x, dict):
        return {k: _no_nan(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_no_nan(v) for v in x]
    return x


def _public_meta(meta):
    """공개 산출물에 실릴 meta — 문자열 값의 홈 경로 접두를 `~` 로 바꾼다 (사용자명·키 위치 노출 방지)."""
    if not isinstance(meta, dict):
        return meta
    home = os.path.expanduser('~')
    return {k: (('~' + v[len(home):]) if isinstance(v, str) and home and v.startswith(home) else v)
            for k, v in meta.items()}


def main_census(key_doc, names=('A', 'B'), out=None):
    """전수 채점을 출력하고 수치를 JSON 으로도 남긴다 (분석 문서가 여기서 읽는다).

    names 는 채점할 코더 둘 — 파일은 coding_<이름>.json. FR-1 회차처럼 셋 이상의 코더가
    있을 때 어느 둘을 대조했는지가 JSON 의 coder_names / coder_files 에 남는다.
    """
    files = {n: 'coding_%s.json' % n for n in names}
    doc_a, doc_b = load(files[names[0]]), load(files[names[1]])
    check_sample(key_doc.get('sample_digest'), doc_a, doc_b)   # 번호가 아니라 표본으로 묶는다
    imp = os.path.join(HERE, IMPACT_JSON)
    if os.path.exists(imp):
        with open(imp, encoding='utf-8') as f:
            check_population(key_doc, json.load(f))
    else:
        print('  (regrade_impact.json 없음 — 모집단 교차 검증 생략)')
    for nm, d in ((names[0], doc_a), (names[1], doc_b)):
        if d.get('errors'):
            print('  코더 %s: 라벨 없는 항목 %d개 (응답 읽기 실패·호출 오류) — 판단 불가로 취급한다'
                  % (nm, len(d['errors'])))
    res = score_census(doc_a['grades'], doc_b['grades'], key_doc, doc_a.get('meta'), doc_b.get('meta'),
                       names=names)
    warn = family_guard(doc_a.get('meta'), doc_b.get('meta'))
    payload = _no_nan({
        'sample_digest': key_doc.get('sample_digest'),
        'population': key_doc['population'], 'seed': key_doc.get('seed'),
        'rule_pairs': key_doc.get('rule_pairs'),
        'coder_names': list(names), 'coder_files': files,
        'coders': {names[0]: _public_meta(doc_a.get('meta')), names[1]: _public_meta(doc_b.get('meta'))},
        'label_errors': {names[0]: len(doc_a.get('errors') or {}),
                         names[1]: len(doc_b.get('errors') or {})},
        'family_warning': warn,
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        **res,
    })
    out = out or os.path.join(HERE, SCORES_OUT)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, allow_nan=False)
    os.replace(tmp, out)
    print('\n수치를 %s 에 썼습니다.' % os.path.relpath(out, HERE))
    print('\n주의 1: 재현율은 이번 표본에서 **처음** 측정된 값이다. 재현율층 밖(전수 3층)은')
    print('        표집오차가 없고, 남는 불확실성은 재현율층 구간과 코더 불일치 폭뿐이다.')
    print('주의 2: 이 결과는 어느 변형을 채택할지 **정하지 않는다.** 채택은 연구 책임자 판단이다.')
    if warn:
        print(warn)


def main():
    import argparse
    ap = argparse.ArgumentParser(description='교차 판정 채점')
    ap.add_argument('--coders', default='A,B',
                    help='채점할 코더 둘 (coding_<이름>.json), 예: C,B — 전수 경로에서만 뜻이 있다')
    ap.add_argument('--out', help='수치 JSON 경로 (기본 %s) — 전수 경로에서만 뜻이 있다' % SCORES_OUT)
    args = ap.parse_args()
    names = tuple(n.strip() for n in args.coders.split(',') if n.strip())
    if len(names) != 2:
        sys.exit('--coders 는 코더 이름 둘이어야 합니다 (예: C,B)')
    key_doc = load('coding_key.json')
    if is_census_key(key_doc):
        main_census(key_doc, names=names, out=args.out)
    else:
        if args.out or args.coders != 'A,B':
            print('  (--out / --coders 는 전수 경로 전용입니다 — 구형식 키라 예전 경로로 갑니다)')
        main_legacy()


if __name__ == '__main__':
    main()
