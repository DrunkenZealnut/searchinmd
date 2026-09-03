#!/usr/bin/env python3
"""
교차 판정 채점 — 두 코더의 판정을 서로, 그리고 두 규칙과 대조한다.

    python3 score_coding.py            # coding_A.json / coding_B.json / coding_key.json

## 이게 무엇이 아닌지 먼저

**AI 두 코더의 일치는 사람 이중코딩이 아니다.** 같은 계열 모델은 오류가 상관되므로
높은 일치율이 정확도가 아니라 공통 편향을 보여줄 수 있다. 이 결과는 규칙이 명백히
틀린 페이지를 싸게 찾아내는 **선별(triage)** 이지 발표 수치의 근거가 아니다.

## 무엇을 재는가

분쟁군 = 현행 규칙이 등급3, 수정본(D1+D2)이 등급3 아님. 여기서 코더가 어느 쪽 손을
들어주느냐가 두 규칙의 우열을 가른다.
대조군 = 둘 다 등급3. 코더가 원래 등급3에 인색한지 보는 기준선이다.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        sys.exit('없음: %s' % name)
    return json.load(open(p, encoding='utf-8'))


def kappa(a, b, cats=(1, 2, 3)):
    """Cohen's kappa — 우연 일치를 뺀 일치도."""
    n = len(a)
    if not n:
        return float('nan')
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

    print('\n=== 5. 규칙 변형별 채점 (코더 라벨 기준) ===')
    print('  주의: 이 표에서 최고 F1 을 골라 채택하면 69쪽에 과적합하는 것이다.')
    print('  %-22s %6s %8s %7s %7s %7s' %
          ('변형', '등급3', '전체비율', '정밀도', '재현율', 'F1'))
    for nm, G in (('A', A), ('B', B)):
        # 합집합(현행의 등급3) 안 진짜 등급3 — 변형과 무관한 고정 분모
        agr_pop = len({k for k in old if old[k]['g'] == 3} - dis_keys)
        true_all = (sum(1 for i in dis if G[i] == 3)
                    + sum(1 for i in ctl if G[i] == 3) / float(len(ctl)) * agr_pop)
        print('  --- 코더 %s (진짜 등급3 추정 %.1f쪽) ---' % (nm, true_all))
        for name, kw in variants:
            g = RG.run(pages, base=med, **kw)
            pred = {k for k in g if g[k]['g'] == 3}
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


def population():
    """모집단 수치는 regrade.py 산출물에서 읽는다. 여기 손으로 적지 않는다."""
    p = os.path.join(HERE, 'docs/03-analysis/data/regrade_impact.json')
    if not os.path.exists(p):
        sys.exit('없음: regrade_impact.json — 먼저 python3 regrade.py 를 돌리세요')
    d = json.load(open(p, encoding='utf-8'))
    total = d['pages']
    cur3 = d['dist']['baseline']['3']            # 현행이 등급3이라 한 쪽
    new3 = d['dist']['D1+D2 둘 다']['3']          # 수정본이 등급3이라 한 쪽
    return total, cur3 - new3, new3              # 전체, 분쟁군, 합의군


def main():
    A = load('coding_A.json')['grades']
    B = load('coding_B.json')['grades']
    key = {str(r['id']): r for r in load('coding_key.json')}
    global TOTAL_PAGES, N_DISPUTED, N_AGREED
    TOTAL_PAGES, N_DISPUTED, N_AGREED = population()

    # 분쟁군은 전수 표집이므로 키의 개수와 모집단 수치가 같아야 한다. 어긋나면
    # 4번 섹션의 가중치가 조용히 틀어지므로 여기서 멈춘다.
    n_dis_key = sum(1 for r in key.values() if r['group'] == 'disputed')
    if n_dis_key != N_DISPUTED:
        sys.exit('불일치: 키의 분쟁군 %d쪽 vs regrade_impact.json 기준 %d쪽. '
                 'regrade.py 와 make_coding_sheet.py 를 같은 버전으로 다시 돌리세요.'
                 % (n_dis_key, N_DISPUTED))

    ids = sorted(key, key=int)
    a = [A[i] for i in ids]
    b = [B[i] for i in ids]

    print('=== 1. 두 코더의 일치도 (전체 %d항목) ===' % len(ids))
    agree = sum(x == y for x, y in zip(a, b))
    print('  단순 일치 %d/%d (%.1f%%)  Cohen κ = %.3f'
          % (agree, len(ids), agree * 100.0 / len(ids), kappa(a, b)))
    print('  코더 A 분포 %s' % dict(sorted(Counter(a).items())))
    print('  코더 B 분포 %s' % dict(sorted(Counter(b).items())))
    m = Counter((x, y) for x, y in zip(a, b) if x != y)
    if m:
        print('  불일치 패턴 (A→B): %s'
              % ', '.join('%d→%d:%d' % (x, y, c) for (x, y), c in sorted(m.items())))

    print('\n=== 2. 대조군 — 두 규칙이 모두 등급3이라 한 쪽 ===')
    ctl = [i for i in ids if key[i]['group'] == 'control']
    for nm, g in (('A', A), ('B', B)):
        c = Counter(g[i] for i in ctl)
        ok = c.get(3, 0)
        print('  코더 %s: 등급3 동의 %d/%d (%.0f%%)  분포 %s'
              % (nm, ok, len(ctl), ok * 100.0 / len(ctl), dict(sorted(c.items()))))
    both3 = sum(1 for i in ctl if A[i] == 3 and B[i] == 3)
    print('  두 코더 모두 등급3: %d/%d' % (both3, len(ctl)))

    print('\n=== 3. 분쟁군 — 현행은 등급3, 수정본은 아님 ===')
    dis = [i for i in ids if key[i]['group'] == 'disputed']
    print('  %d쪽. 코더가 등급3 이라 하면 현행 규칙이 옳고, 아니라 하면 수정본이 옳다.' % len(dis))
    for nm, g in (('A', A), ('B', B)):
        c = Counter(g[i] for i in dis)
        cur = c.get(3, 0)
        print('  코더 %s: 현행 지지(등급3) %d  수정본 지지(1·2) %d  분포 %s'
              % (nm, cur, len(dis) - cur, dict(sorted(c.items()))))
    both_new = sum(1 for i in dis if A[i] != 3 and B[i] != 3)
    both_old = sum(1 for i in dis if A[i] == 3 and B[i] == 3)
    print('  두 코더 모두 수정본 지지: %d/%d (%.0f%%)'
          % (both_new, len(dis), both_new * 100.0 / len(dis)))
    print('  두 코더 모두 현행 지지: %d/%d (%.0f%%)'
          % (both_old, len(dis), both_old * 100.0 / len(dis)))

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


if __name__ == '__main__':
    main()
