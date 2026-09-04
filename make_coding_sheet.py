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

## 산출물은 커밋하지 않는다

교재 본문이 그대로 들어간다. 비공개 상업 교재에서 뽑은 자료라 .gitignore 대상이다.
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

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20260903          # 재현 가능하게 고정
N_CONTROL = 30
CHUNK_CHARS = 6000       # 자르는 길이가 아니라 **나누는** 단위다


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


def build_sheet(pages, items, old, new):
    """표본 항목들을 (코더용 시트, 정답 키) 두 목록으로 만든다.

    **본문은 어떤 경우에도 자르지 않는다.** 채점기(`regrade.py`)가 보는 텍스트와
    코더가 보는 텍스트가 같아야 F1·κ 가 규칙을 재는 값이 된다. 길이가 문제면
    자르지 말고 `chunk_text()` 로 나눠 보여준다.
    """
    sheet, key = [], []
    for i, (k, grp) in enumerate(items, 1):
        fn, pg = k
        text = pages[k]['text']
        # 'truncated'(6,000자에서 잘랐다) 는 없앴다. 더 이상 자르지 않으므로 뜻이
        # 없어졌고, 같은 이름을 다른 뜻으로 재사용하면 과거 산출물과 조용히 어긋난다.
        # 'cell_truncated' 는 **원본이** 엑셀 셀 한도에서 잘렸다는 뜻이다.
        sheet.append({
            'id': i,
            'text': text,
            'chars': len(text),
            'cell_truncated': pages[k]['truncated'],
        })
        key.append({
            'id': i, 'group': grp, 'file': fn, 'page': pg,
            'cell_truncated': pages[k]['truncated'],
            'old': old[k]['g'], 'new': new[k]['g'],
            'old_safety': old[k]['sn'], 'old_action': old[k]['an'],
            'new_safety': new[k]['sn'], 'new_action': new[k]['an'],
        })
    return sheet, key


def render_item(it):
    """항목 하나를 코딩 시트 마크다운 줄 목록으로 렌더한다."""
    md = ['### %d' % it['id'], '']
    if it['cell_truncated']:
        md += ['> ⚠️ **이 본문은 원본 수집 단계에서 잘렸습니다** (엑셀 셀 한도 32,767자).',
               '> 뒷부분은 존재하지 않으며 복구할 수 없습니다. 뒤에 조치가 더 있었는지',
               '> 알 수 없으므로, 판단이 서지 않으면 `?` 로 표시하십시오.', '']
    parts = chunk_text(it['text'])
    fence = fence_for(it['text'])
    for j, part in enumerate(parts, 1):
        if len(parts) > 1:                       # 항목은 하나다. 판정도 하나만 받는다
            md += ['**(본문 %d/%d)**' % (j, len(parts)), '']
        md += [fence + 'text', part, fence, '']
    return md + ['판정: ____', '', '---', '']


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

    sheet, key = build_sheet(pages, items, old, new)

    digest = sample_digest(key)
    for name, obj in (('coding_sheet.json', sheet), ('coding_key.json', key)):
        p = os.path.join(HERE, name)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump({'sample_digest': digest, 'items': obj}, f,
                      ensure_ascii=False, indent=1)
        print('  %s (%d항목)' % (name, len(obj)))

    md = [
        '# 안전등급 수기 코딩 시트',
        '',
        '각 항목의 본문을 읽고 등급 1/2/3 중 하나를 매깁니다.',
        '**규칙이 매긴 등급은 이 문서에 없습니다.** 본문만 보고 판단하세요.',
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
        '## 항목',
        '',
    ]
    for it in sheet:
        md += render_item(it)
    p = os.path.join(HERE, 'coding_sheet.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print('  coding_sheet.md')

    print('\n분쟁군 %d쪽 / 대조군 %d쪽 = 총 %d항목'
          % (len(disputed), len(control), len(items)))
    print('원본이 잘린 항목 %d개 (복구 불가, 고지 부착) / 분할 제시 항목 %d개'
          % (sum(1 for it in sheet if it['cell_truncated']),
             sum(1 for it in sheet if it['chars'] > CHUNK_CHARS)))
    print('키(정답)는 coding_key.json 에 별도로 있습니다. 코딩 중에는 열지 마세요.')


if __name__ == '__main__':
    main()
