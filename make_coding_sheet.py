#!/usr/bin/env python3
"""
수기 코딩 시트 생성 — 등급 판정을 사람(또는 독립 코더)이 눈으로 매기기 위한 것.

    pip install openpyxl
    python3 make_coding_sheet.py                 # coding_sheet.json / .md 생성

## 왜 전수가 아니라 이 표본인가

두 규칙(현행 / D1+D2 수정본)이 **갈리는 페이지**가 결정적이다. 둘 다 등급3이라고
하는 페이지를 아무리 코딩해도 어느 규칙이 나은지는 알 수 없다. 갈리는 지점에서
코더가 어느 쪽 손을 들어주느냐가 답이다.

  분쟁군  현행=3, 수정본=1 또는 2   -> 39쪽 (전수)
  대조군  둘 다 3                   -> 30쪽 (무작위)

대조군은 기준선이다. 분쟁군만 보면 "코더가 원래 등급3에 인색한가" 와
"수정본이 옳은가" 를 구분할 수 없다.

## 코더는 규칙의 판정을 보지 못한다

시트에는 등급도, 안전어/조치어 카운트도, 사유도 넣지 않는다. 보면 그쪽으로
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

`?` 를 도입했으므로 `score_coding.py` 는 1·2·3 외의 값을 받을 수 있어야 한다.

## 산출물은 커밋하지 않는다

교재 본문이 그대로 들어간다. 비공개 상업 교재에서 뽑은 자료라 .gitignore 대상이다.
"""
import json
import os
import random
import sys

try:
    from openpyxl import load_workbook  # noqa: F401
except ImportError:
    sys.exit('openpyxl이 필요합니다: pip install openpyxl')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regrade as RG  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20260903          # 재현 가능하게 고정
N_CONTROL = 30
MAX_CHARS = 6000         # 코더가 읽을 수 있는 분량으로 자른다


def main():
    src = os.path.join(RG.DATA_DIR, RG.NCS_FILE)
    if not os.path.exists(src):
        sys.exit('원본 엑셀을 찾을 수 없습니다: %s' % src)

    print('원본 읽는 중…')
    pages = RG.load_pages(src)
    med = RG.median_length(pages)
    old = RG.run(pages, word_boundary=False, normalize=False)
    new = RG.run(pages, word_boundary=True, normalize=True, base=med)

    disputed = [k for k in pages if old[k]['g'] == 3 and new[k]['g'] != 3]
    agreed = [k for k in pages if old[k]['g'] == 3 and new[k]['g'] == 3]

    rng = random.Random(SEED)
    control = rng.sample(agreed, min(N_CONTROL, len(agreed)))
    items = [(k, 'disputed') for k in disputed] + [(k, 'control') for k in control]
    rng.shuffle(items)                       # 군이 섞여야 코더가 눈치채지 못한다

    sheet, key = [], []
    for i, (k, grp) in enumerate(items, 1):
        fn, pg = k
        text = pages[k]['text']
        truncated = len(text) > MAX_CHARS
        sheet.append({
            'id': i,
            'text': text[:MAX_CHARS] + ('\n…(이하 생략)' if truncated else ''),
            'chars': len(text),
            'truncated': truncated,
        })
        key.append({
            'id': i, 'group': grp, 'file': fn, 'page': pg,
            'old': old[k]['g'], 'new': new[k]['g'],
            'old_safety': old[k]['sn'], 'old_action': old[k]['an'],
            'new_safety': new[k]['sn'], 'new_action': new[k]['an'],
        })

    for name, obj in (('coding_sheet.json', sheet), ('coding_key.json', key)):
        p = os.path.join(HERE, name)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        print('  %s (%d항목)' % (name, len(obj)))

    md = [
        '# 안전등급 수기 코딩 시트',
        '',
        '각 항목의 본문을 읽고 등급 1/2/3 중 하나를 매깁니다.',
        '**규칙이 매긴 등급은 이 문서에 없습니다.** 본문만 보고 판단하세요.',
        '',
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
        '판정 대상은 **작업자의 안전보건**입니다. 공정·품질·설비 관리 문맥의 서술은',
        '해당하지 않습니다. 반대로 사전에 없을 법한 표현(예: 특정 보호구 이름을',
        '직접 지목하거나, 환기·격리 같은 방법을 풀어 쓴 경우)도 조치로 셉니다.',
        '',
        '## 항목',
        '',
    ]
    for it in sheet:
        md += ['### %d' % it['id'], '',
               '```text', it['text'], '```', '',
               '판정: ____', '', '---', '']
    p = os.path.join(HERE, 'coding_sheet.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print('  coding_sheet.md')

    print('\n분쟁군 %d쪽 / 대조군 %d쪽 = 총 %d항목'
          % (len(disputed), len(control), len(items)))
    print('키(정답)는 coding_key.json 에 별도로 있습니다. 코딩 중에는 열지 마세요.')


if __name__ == '__main__':
    main()
