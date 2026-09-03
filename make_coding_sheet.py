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
        '판단이 갈리면 **낮은 등급**을 택합니다(보수적 규칙).',
        '반도체 공정 설명에 나오는 "진동", "먼지(파티클)" 처럼 **안전과 무관한 문맥의**',
        '단어는 안전보건 내용으로 세지 않습니다.',
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
