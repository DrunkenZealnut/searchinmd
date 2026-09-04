#!/usr/bin/env python3
"""엑셀 셀 한도 절단 실측 — 원본 워크북에서 잘린 본문을 전수 조사한다.

    python3 truncation_audit.py                 # data/ 의 두 워크북
    python3 truncation_audit.py --data /path     # 다른 경로
    python3 truncation_audit.py --cells-only     # 페이지 접기 없이 셀만 (빠름)

## 왜 별도 스크립트인가

`recount_grades.py` 는 절단 집계를 산출물에 싣지만 **openpyxl 이 있어야 돈다.**
이 스크립트는 xlsx 를 zip+XML 로 직접 읽어 pip 패키지 없이 같은 수치를 낸다.
`recount_grades.py` 의 `EXPECTED` 에 박힌 절단 실측치(NCS 16쪽 / 교과서 0쪽)를
새 클론에서도 확인할 수 있어야 하기 때문이다.

## 무엇을 세는가

절단 판정은 `page_utils.is_cell_truncated()` 하나뿐이다 — 길이가 정확히
32,767자이고 '...' 로 끝나는 셀. 여기서 술어를 다시 정의하지 않는다.

**열 위치를 쓰지 않는다.** 워크북마다 열 배치가 다르고(교과서 파일은 NCS 와
다르다) 절단 마커는 자기 식별적이므로, 행의 모든 셀을 훑으면 된다.

행 수와 페이지 수는 크게 다르다 — 절단쪽은 길어서 키워드가 많이 걸린다.
NCS 실측은 1,376행 대 16쪽으로 86배다. **등급은 페이지 속성이므로 페이지 수를
보라.** 페이지 접기는 `recount_grades.py` 의 `parse_row`·`aggregate` 를 그대로
빌려 쓴다(openpyxl 은 스텁으로 우회). 여기서 다시 구현하면 두 벌이 어긋난다.
"""
import argparse
import os
import sys
import types
import zipfile
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from page_utils import is_cell_truncated  # noqa: E402

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def _shared_strings(z):
    """sharedStrings.xml 을 읽어 인덱스→문자열 목록으로 돌려준다.

    현재 두 워크북은 inlineStr 이라 이 표가 비어 있지만, openpyxl 로 다시 쓰면
    공유 문자열이 기본이 된다. 그때 `t="s"` 셀의 `<v>` 는 **본문이 아니라 색인**이라,
    표를 안 읽으면 모든 셀이 짧은 숫자 문자열로 보여 절단 0건·페이지 0쪽 이라는
    조용히 틀린 결과가 나온다.
    """
    names = [n for n in z.namelist() if n.endswith('sharedStrings.xml')]
    if not names:
        return []
    out = []
    with z.open(names[0]) as f:
        for _, si in ET.iterparse(f, events=('end',)):
            if si.tag == NS + 'si':
                out.append(''.join(t.text or '' for t in si.iter(NS + 't')))
                si.clear()
    return out


def _cell_value(c, shared):
    """셀의 문자열을 뽑는다. inlineStr · 공유 문자열 · 일반 값 세 가지."""
    e = c.find(NS + 'is')
    if e is not None:
        return ''.join(t.text or '' for t in e.iter(NS + 't'))
    v = c.find(NS + 'v')
    if v is None or v.text is None:
        return None
    if c.get('t') == 's':                    # <v> 는 sharedStrings 색인이다
        try:
            return shared[int(v.text)]
        except (ValueError, IndexError):
            return None
    return v.text


def _col_index(ref):
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def iter_rows(path):
    """워크북의 모든 행을 (열 위치를 보존한) 튜플로 흘려보낸다."""
    with zipfile.ZipFile(path) as z:
        shared = _shared_strings(z)
        names = sorted((n for n in z.namelist()
                        if n.startswith('xl/worksheets/sheet')),
                       key=lambda n: int(''.join(c for c in n if c.isdigit())))
        for name in names:
            with z.open(name) as f:
                for _, row in ET.iterparse(f, events=('end',)):
                    if row.tag != NS + 'row':
                        continue
                    cells = {}
                    for c in row.findall(NS + 'c'):
                        cells[_col_index(c.get('r', 'A1'))] = _cell_value(c, shared)
                    row.clear()
                    if cells:
                        yield tuple(cells.get(i) for i in range(max(cells) + 1))


class CellStats:
    """행이 흘러가는 동안 셀 단위 수치를 세어 둔다.

    페이지 접기와 같은 패스에서 세므로 워크북을 두 번 읽지 않아도 된다.
    """

    def __init__(self):
        self.rows = self.truncated_rows = self.longest_cell = 0

    def observe(self, vals):
        self.rows += 1
        hit = False
        for v in vals:
            if isinstance(v, str):
                self.longest_cell = max(self.longest_cell, len(v))
                hit |= is_cell_truncated(v)
        self.truncated_rows += hit
        return vals


def scan_cells(path):
    """셀 단위만 센다 (--cells-only). 페이지 접기가 필요 없을 때의 최단 경로."""
    st = CellStats()
    for vals in iter_rows(path):
        st.observe(vals)
    return st


def _import_recount():
    """openpyxl 없이 recount_grades 를 불러온다.

    스텁은 import 통과용일 뿐이고 실제 읽기는 이 파일의 zip 리더가 한다.
    테스트 하네스(outputs/test-recount-grades.py)와 같은 수법이다.
    """
    if 'openpyxl' not in sys.modules:
        stub = types.ModuleType('openpyxl')
        stub.load_workbook = lambda *a, **k: None
        sys.modules['openpyxl'] = stub
    import recount_grades
    return recount_grades


class _Sheet:
    """openpyxl 워크시트 흉내. 행을 모으지 않고 흘려보낸다 — 81MB 워크북이다."""

    def __init__(self, path, stats):
        self._path, self._stats = path, stats

    def iter_rows(self, values_only=True):
        return (self._stats.observe(v) for v in iter_rows(self._path))


class _Book:
    def __init__(self, path, stats):
        self._path, self._stats = path, stats
        self.sheetnames = ['all']          # 시트 구분 없이 한 번만 훑는다

    def __getitem__(self, k):
        return _Sheet(self._path, self._stats)

    def close(self):
        pass


def fold_pages(path, gmap, drop_ncs_residue):
    """recount_grades 의 parse_row/aggregate 로 페이지 단위 집계를 낸다.

    셀 단위 수치도 같은 패스에서 함께 센다. 반환은 (집계, 셀수치).
    """
    R = _import_recount()
    stats = CellStats()
    orig = R.load_workbook
    R.load_workbook = lambda p, **k: _Book(p, stats)
    try:
        rows = R.scan(path, gmap, drop_ncs_residue=drop_ncs_residue)
    finally:
        R.load_workbook = orig
    agg, _ = R.aggregate(rows)
    return agg, stats


def main():
    ap = argparse.ArgumentParser(description='엑셀 셀 한도 절단 전수 조사')
    ap.add_argument('--data', default=os.path.join(HERE, 'data'),
                    help='원본 엑셀 디렉터리 (기본: data/)')
    ap.add_argument('--cells-only', action='store_true',
                    help='페이지 접기를 건너뛰고 셀·행 수만 센다')
    args = ap.parse_args()

    # 파일명과 등급 매핑은 recount_grades 에서 가져온다 — 여기 손으로 적지 않는다.
    R = _import_recount()

    targets = [('NCS', R.NCS_FILE, R.NCS_MAP, False, 'ncs'),
               ('교과서', R.TXT_FILE, R.TXT_MAP, True, 'txt')]
    missing = [f for _, f, _, _, _ in targets
               if not os.path.isfile(os.path.join(args.data, f))]
    if missing:
        sys.exit('원본 엑셀을 찾을 수 없습니다 (%s):\n  %s\n'
                 'data/ 는 .gitignore 대상이라 새로 클론한 환경에는 없습니다.'
                 % (args.data, '\n  '.join(missing)))

    bad = 0
    for label, fname, gmap, drop, key in targets:
        path = os.path.join(args.data, fname)
        print('=== %s  (%s)' % (label, fname))
        if args.cells_only:
            cells = scan_cells(path)
        else:
            agg, cells = fold_pages(path, gmap, drop)   # 셀 수치도 같은 패스에서
        print('   행 %d  |  최장 셀 %d자  |  절단 행 %d'
              % (cells.rows, cells.longest_cell, cells.truncated_rows))
        if args.cells_only:
            print()
            continue

        exp = R.EXPECTED[key]
        print('   고유 페이지 %d  |  절단 페이지 %d  |  등급별 %s'
              % (agg['pages'], agg['truncated_pages'], agg['truncated_page_g']))
        for k in ('pages', 'truncated_pages', 'truncated_page_g',
                  'page_grade_digest'):
            if agg[k] != exp[k]:
                print('   ✗ EXPECTED 불일치 — %s: %s ≠ %s' % (k, agg[k], exp[k]))
                bad += 1
        print()

    if not args.cells_only:
        print('EXPECTED 대조: %s' % ('불일치 %d건' % bad if bad else '전부 일치'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
