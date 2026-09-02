#!/usr/bin/env python3
"""
data/ 원본 엑셀 → 통일 등급체계로 전수 재집계.

배경
----
NCS(7,769행)와 교과서(981행)는 원본 엑셀의 등급 코딩이 서로 반대다.
등급사유 문자열을 전수 분류해 확인한 결과:

  NCS  (ncs_keywords_in_markdown_results_20260402.xlsx)
    1 = "키워드 N건 (5건 이하)"               → 미흡·없음   (2,076행 100%)
    2 = "안전 N건 [...], 구체적 조치 언급 없음"  → 형식적 언급 (3,465행 100%)
    3 = "안전 N건 [...] + 조치 M건 [...]"       → 구체적 대책 (2,228행 100%)

  교과서 (ncs_keywords_in_markdown_results_교과서_results_20260415.xlsx)
    1 = "... (구체적 대책 미흡)"                → 형식적 언급 (360행)
    2 = "... (구체적 대책 포함)"                → 구체적 대책 (64행)
    3 = "키워드 N건 (5건 이하)"                → 미흡·없음   (557행 100%)

따라서 교과서는 {1→2, 2→3, 3→1}로 재매핑해 통일 등급체계
(1 미흡·없음 / 2 형식적 언급 / 3 구체적 대책)로 맞춘다.

집계 단위
--------
등급은 사실상 **페이지 단위** 판정이다(NCS 1,847쪽 중 등급이 갈린 페이지 12쪽 = 0.6%,
교과서 362쪽 중 0쪽). 행 단위 집계는 한 페이지에 걸린 키워드 수만큼 중복 계수되어
상위 등급을 체계적으로 과대평가하므로(NCS 등급3은 쪽당 평균 20.6개 키워드 → 20배 증폭),
주 지표는 고유 페이지 기준으로 산출한다.

사용법
-----
    pip install openpyxl
    python3 recount_grades.py [--out docs/03-analysis/data]
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

try:
    from openpyxl import load_workbook
except ImportError:
    sys.exit('openpyxl이 필요합니다:  pip install openpyxl')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

NCS_FILE = 'ncs_keywords_in_markdown_results_20260402.xlsx'
TXT_FILE = 'ncs_keywords_in_markdown_results_교과서_results_20260415.xlsx'

# 원본 등급 → 통일 등급 (1 미흡·없음 / 2 형식적 언급 / 3 구체적 대책)
NCS_MAP = {1: 1, 2: 2, 3: 3}
TXT_MAP = {1: 2, 2: 3, 3: 1}

GRADE_LABEL = {1: '미흡·없음', 2: '형식적 언급', 3: '구체적 대책'}

TXT_TOTAL_PAGES = 2055           # 교과서 9권 원본 총 쪽수
AREAS = ['반도체개발', '반도체제조', '반도체장비', '반도체재료']

YN = {'예', '아니오'}
FN_RE = re.compile(r'^(LM\d|20\d{6}_\d{6}_)')   # NCS: LM…, 교과서: 20260415_143535_…

# 기대값 (회귀 검증용)
EXPECTED = {
    'ncs': {'rows': 7769, 'pages': 1847, 'books': 86,
            'row_g': {1: 2076, 2: 3465, 3: 2228},
            'page_g': {1: 1267, 2: 472, 3: 108}},
    'txt': {'rows': 981, 'pages': 362, 'books': 9,
            'row_g': {1: 557, 2: 360, 3: 64},
            'page_g': {1: 309, 2: 45, 3: 8}},
}


def parse_row(vals):
    """시트마다 열 구성이 달라, 행 끝의 (사고사례여부, 등급, 등급사유) 3연속을 앵커로 파싱한다."""
    v = [None if x is None else str(x).strip() for x in vals]
    for i, x in enumerate(v):
        if x in YN and i + 1 < len(v) and v[i + 1] in ('1', '2', '3'):
            fn = next((y for y in v[:i] if y and FN_RE.match(y)), None)
            area = next((y for y in v[:i] if y and y.startswith('반도체') and len(y) <= 8), None)
            page = None
            for y in v[:i]:                       # page는 number 뒤에 오므로 마지막 숫자 셀
                if y and y.isdigit() and len(y) <= 4:
                    page = int(y)
            return dict(case=x, raw=int(v[i + 1]),
                        reason=v[i + 2] if i + 2 < len(v) else None,
                        fn=fn, area=area, page=page)
    return None


def scan(path, gmap, drop_ncs_residue=False):
    wb = load_workbook(path, read_only=True, data_only=True)
    rows, skipped = [], 0
    for sheet in wb.sheetnames:
        for r in wb[sheet].iter_rows(values_only=True):
            if r is None or all(x is None for x in r):
                continue
            if r[0] is not None and str(r[0]).strip() == 'number':
                continue                          # 헤더행
            p = parse_row(r)
            if not p:
                continue
            if drop_ncs_residue and p['fn'] and p['fn'].startswith('LM'):
                skipped += 1                      # 교과서 파일에 남은 NCS 잔여행
                continue
            p['kw'] = sheet
            p['g'] = gmap[p['raw']]
            rows.append(p)
    wb.close()
    if skipped:
        print('  · NCS 잔여행 %d건 제외' % skipped)
    return rows


def aggregate(rows, total_pages=None):
    by_page = {}
    for x in rows:
        by_page[(x['fn'], x['page'])] = x
    mixed = 0
    seen = collections.defaultdict(set)
    for x in rows:
        seen[(x['fn'], x['page'])].add(x['g'])
    mixed = sum(1 for v in seen.values() if len(v) > 1)
    out = {
        'rows': len(rows),
        'pages': len(by_page),
        'books': len(set(x['fn'] for x in rows)),
        'mixed_grade_pages': mixed,
        'row_g': {g: sum(1 for x in rows if x['g'] == g) for g in (1, 2, 3)},
        'page_g': {g: sum(1 for x in by_page.values() if x['g'] == g) for g in (1, 2, 3)},
        'cases_rows': sum(1 for x in rows if x['case'] == '예'),
        'cases_pages': len(set((x['fn'], x['page']) for x in rows if x['case'] == '예')),
        'cases_books': len(set(x['fn'] for x in rows if x['case'] == '예')),
    }
    if total_pages:
        out['total_pages'] = total_pages
        out['undetected_pages'] = total_pages - out['pages']
    return out, by_page


def check(name, got, exp):
    bad = []
    for k, v in exp.items():
        if got.get(k) != v:
            bad.append('%s: %s ≠ %s' % (k, got.get(k), v))
    print('  [%s] %s' % (name, '검증 통과' if not bad else '검증 실패 — ' + '; '.join(bad)))
    return not bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join('docs', '03-analysis', 'data'),
                    help='CSV/JSON 출력 디렉터리')
    ap.add_argument('--data', default=DATA_DIR, help='원본 엑셀 디렉터리')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    print('원본 읽는 중...')
    ncs = scan(os.path.join(args.data, NCS_FILE), NCS_MAP)
    txt = scan(os.path.join(args.data, TXT_FILE), TXT_MAP, drop_ncs_residue=True)

    ncs_agg, ncs_pages = aggregate(ncs)
    txt_agg, txt_pages = aggregate(txt, TXT_TOTAL_PAGES)

    print('\n회귀 검증')
    ok = check('NCS', ncs_agg, EXPECTED['ncs']) & check('교과서', txt_agg, EXPECTED['txt'])

    for name, agg in (('NCS 교재 86권', ncs_agg), ('반도체고 교과서 9권', txt_agg)):
        print('\n%s' % name)
        print('  검출 %d쪽 / %d건 / 등급 혼재 페이지 %d쪽'
              % (agg['pages'], agg['rows'], agg['mixed_grade_pages']))
        for g in (1, 2, 3):
            p, r = agg['page_g'][g], agg['row_g'][g]
            line = '  등급%d %-7s %5d쪽 (%5.1f%%)  행 %5d건 (%5.1f%%)  증폭 %4.1f배' % (
                g, GRADE_LABEL[g], p, p / agg['pages'] * 100,
                r, r / agg['rows'] * 100, r / p if p else 0)
            if 'total_pages' in agg:
                line += '  전체대비 %4.1f%%' % (p / agg['total_pages'] * 100)
            print(line)
        print('  사고사례 판정: %d건 / %d쪽 / %d권'
              % (agg['cases_rows'], agg['cases_pages'], agg['cases_books']))

    # 영역별 (NCS)
    print('\nNCS 영역별 (페이지 기준)')
    print('  %-10s %4s %6s %7s %7s %7s %9s' % ('영역', '권', '검출쪽', '등급1', '등급2', '등급3', '안전관련%'))
    for a in AREAS:
        pl = [x for x in ncs_pages.values() if x['area'] == a]
        g = [sum(1 for x in pl if x['g'] == i) for i in (1, 2, 3)]
        bk = len(set(x['fn'] for x in ncs if x['area'] == a))
        print('  %-10s %4d %6d %7d %7d %7d %8.1f%%'
              % (a, bk, len(pl), g[0], g[1], g[2], (g[1] + g[2]) / len(pl) * 100))

    # 교재별 (교과서)
    print('\n교과서 교재별 (페이지 기준)')
    for f in sorted(set(x['fn'] for x in txt)):
        pl = [x for x in txt_pages.values() if x['fn'] == f]
        g = [sum(1 for x in pl if x['g'] == i) for i in (1, 2, 3)]
        nm = '_'.join(f.split('_')[2:]).replace('_', ' ')
        print('  %-34s 검출 %3d쪽  등급1 %3d  등급2 %3d  등급3 %d'
              % (nm[:34], len(pl), g[0], g[1], g[2]))

    # 등급3 0쪽 교재
    for label, rows_, pages_ in (('NCS', ncs, ncs_pages), ('교과서', txt, txt_pages)):
        bybook = collections.defaultdict(collections.Counter)
        for x in pages_.values():
            bybook[x['fn']][x['g']] += 1
        zero = [b for b, c in bybook.items() if c[3] == 0]
        print('\n%s 등급3(구체적 대책) 0쪽 교재: %d / %d권' % (label, len(zero), len(bybook)))

    # 산출물
    for nm, pages_, cols in (('ncs_pages', ncs_pages, ['영역', '교재', '페이지', '등급', '등급명', '사고사례', '등급사유']),
                             ('txt_pages', txt_pages, ['교재', '페이지', '등급', '등급명', '사고사례', '등급사유'])):
        path = os.path.join(args.out, nm + '.csv')
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(cols)
            for (fn, pg), x in sorted(pages_.items(), key=lambda z: (str(z[0][0]), z[0][1] or 0)):
                row = [x['area']] if '영역' in cols else []
                row += [fn, pg, x['g'], GRADE_LABEL[x['g']], x['case'], x['reason']]
                w.writerow(row)
        print('저장: %s (%d행)' % (path, len(pages_)))

    summary = {'unified_grades': GRADE_LABEL, 'ncs': ncs_agg, 'textbook': txt_agg}
    sp = os.path.join(args.out, 'summary.json')
    json.dump(summary, open(sp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('저장: %s' % sp)

    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
