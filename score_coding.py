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


def main():
    A = load('coding_A.json')['grades']
    B = load('coding_B.json')['grades']
    key = {str(r['id']): r for r in load('coding_key.json')}

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

    print('\n=== 4. 규칙별 정밀도 (코더를 기준으로 봤을 때) ===')
    print('  "규칙이 등급3이라 한 쪽 중 코더도 등급3인 비율"')
    for nm, g in (('A', A), ('B', B)):
        # 현행 규칙의 등급3 = 분쟁군 + 대조군 전체
        cur_p = sum(1 for i in ids if g[i] == 3) / float(len(ids))
        # 수정본의 등급3 = 대조군만
        new_hit = sum(1 for i in ctl if g[i] == 3)
        cur_hit = sum(1 for i in ids if g[i] == 3)
        print('  코더 %s | 현행 %d/%d = %.0f%%   수정본 %d/%d = %.0f%%'
              % (nm, cur_hit, len(ids), cur_hit * 100.0 / len(ids),
                 new_hit, len(ctl), new_hit * 100.0 / len(ctl)))
        del cur_p

    print('\n주의: 코더 둘 다 같은 계열 AI다. 일치율이 높아도 정확도가 아니라')
    print('      공통 편향일 수 있다. 발표 수치의 근거로는 사람 코딩이 필요하다.')


if __name__ == '__main__':
    main()
