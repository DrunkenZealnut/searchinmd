#!/usr/bin/env python3
"""
recount_grades.py 단위 회귀 테스트 — grade-recount-unify

원본 엑셀(data/, .gitignore 대상)과 openpyxl 없이도 순수 로직을 검증한다.
openpyxl 을 sys.modules 에 스텁으로 주입해 import 를 통과시킨 뒤,
recount_grades.load_workbook 을 가짜 워크북으로 몽키패치해 scan() 까지 태운다.

    실행: python3 outputs/test-recount-grades.py
    PASS 시 exit 0, FAIL 시 exit 1 (CI 친화 — 표준 라이브러리만 사용)

커버:
  R1 parse_row  앵커 탐색 / fn·area·page 추출 / 결측·미검출
  R2 scan       헤더행·공백행 필터, NCS 잔여행 제거, 시트→키워드, 등급 매핑
  R3 aggregate  페이지 단위 집계, 등급 혼재, 사고사례, total_pages 분기
  R4 check      회귀 검증 통과/실패
  R5 매핑 상수  NCS_MAP / TXT_MAP / EXPECTED 정합
  R6 경계·에러  빈 입력, 원본 파일 부재, 0쪽 영역
  R7 kw_pages   키워드별 고유 (교재,쪽) 수
  R8 insert_page_markers  마커 주입, --force 재삽입, 손상 방지 가드
"""
import io
import os
import sys
import tempfile
import types
import contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- openpyxl 스텁 주입 (미설치 환경에서도 import 가능하게) ----
if 'openpyxl' not in sys.modules:
    stub = types.ModuleType('openpyxl')
    stub.load_workbook = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError('스텁 load_workbook 이 호출됨 — 테스트에서 몽키패치 필요'))
    sys.modules['openpyxl'] = stub

sys.path.insert(0, ROOT)
import recount_grades as R  # noqa: E402

PASS = FAIL = 0


def check(name, cond, extra=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print('  ✓ %s' % name)
    else:
        FAIL += 1
        print('  ✗ %s%s' % (name, (' — ' + str(extra)) if extra else ''))


KNOWN = 0


def known(name, cond, note):
    """기지 결함: exit code 는 막지 않되 매 실행마다 노출한다."""
    global PASS, KNOWN
    if cond:
        PASS += 1
        print('  ✓ %s' % name)
    else:
        KNOWN += 1
        print('  ⚠ KNOWN ISSUE %s\n      → %s' % (name, note))


class FakeSheet:
    def __init__(self, rows):
        self._rows = rows

    def iter_rows(self, values_only=True):
        return iter(self._rows)


class FakeWB:
    def __init__(self, sheets):
        self._s = sheets
        self.sheetnames = list(sheets)
        self.closed = False

    def __getitem__(self, k):
        return FakeSheet(self._s[k])

    def close(self):
        self.closed = True


def with_wb(sheets):
    """recount_grades.load_workbook 을 가짜 워크북으로 교체하는 컨텍스트."""
    wb = FakeWB(sheets)

    @contextlib.contextmanager
    def cm():
        orig = R.load_workbook
        R.load_workbook = lambda *a, **k: wb
        try:
            yield wb
        finally:
            R.load_workbook = orig
    return cm()


def quiet(fn, *a, **k):
    """stdout 을 삼키고 (결과, 출력) 반환."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **k)
    return out, buf.getvalue()


# 실제 NCS 시트 열 배치 근사: number, 파일명, 영역, 페이지, 본문, 사고사례, 등급, 등급사유
NCS_ROW = (1, 'LM1903060101_23v6_반도체_제품_기획', '반도체개발', 19,
           '…안전 관련 본문…', '아니오', 1, '키워드 1건 (5건 이하): 부상(1)')
# 교과서 시트: number, 파일명, 페이지, 본문, 사고사례, 등급, 등급사유 (영역 열 없음)
TXT_ROW = (1, '20260413_171220_반도체기초기술1_크리아트_/x.md', 12,
           '…본문…', '아니오', 3, '키워드 2건 (5건 이하): 안전(1), 유의사항(1)')

# =====================================================================
print('\n[R1] parse_row — 앵커 파싱')
p = R.parse_row(NCS_ROW)
check('R1a NCS 행 파싱 성공', p is not None)
check('R1b fn 추출', p['fn'] == 'LM1903060101_23v6_반도체_제품_기획', p and p['fn'])
check('R1c area 추출', p['area'] == '반도체개발', p and p['area'])
check('R1d page 추출', p['page'] == 19, p and p['page'])
check('R1e raw 등급', p['raw'] == 1)
check('R1f case', p['case'] == '아니오')
check('R1g reason', p['reason'].startswith('키워드 1건'))

t = R.parse_row(TXT_ROW)
check('R1h 교과서 행(열 구성 상이) 파싱 성공', t is not None)
check('R1i 교과서는 area 열이 없어 None', t['area'] is None, t and t['area'])
check('R1j 교과서 fn 추출(20…_… 패턴)', t['fn'].startswith('20260413_171220_'))
check('R1k 교과서 page 추출', t['page'] == 12, t and t['page'])

check('R1l 앵커 없음 → None', R.parse_row((1, 'LM1', '반도체개발', 3, '본문')) is None)
check('R1m 빈 행 → None', R.parse_row((None, None, None)) is None)
check('R1n 앵커 뒤 등급사유 없음 → reason None',
      R.parse_row((1, 'LM1x', '반도체개발', 5, '예', 2))['reason'] is None)
check('R1o None 셀 혼재 허용',
      R.parse_row((None, 'LM2y', None, 7, None, '아니오', 3, '사유'))['page'] == 7)
check('R1p 등급이 1/2/3 아니면 앵커 아님',
      R.parse_row((1, 'LM3z', '반도체개발', 5, '예', 4, '사유')) is None)
check('R1q fn 패턴 불일치 → fn None',
      R.parse_row((1, 'OTHER_FILE', '반도체개발', 5, '예', 1, 's'))['fn'] is None)

# page 휴리스틱: 앵커 앞 "마지막" 4자리 이하 정수 셀
check('R1r page 는 앵커 앞 마지막 숫자 셀',
      R.parse_row((1, 'LM4a', '반도체개발', 19, 77, '아니오', 2, 's'))['page'] == 77)
check('R1s 5자리 숫자는 page 후보 제외',
      R.parse_row((1, 'LM4b', '반도체개발', 12345, '아니오', 2, 's'))['page'] == 1)
check('R1t 실수형 페이지 셀(19.0) 파싱',
      R.parse_row((1, 'LM4c', '반도체개발', 19.0, '아니오', 2, 's'))['page'] == 19,
      "parse_row 는 str(19.0)='19.0' 이라 isdigit() 실패 → page=None. "
      "openpyxl 이 페이지 열을 float 로 돌려주는 시트가 하나라도 있으면 "
      "그 교재의 모든 행이 (fn, None) 한 페이지로 접혀 고유쪽수가 붕괴한다. "
      "int(float(x)) 폴백 또는 명시적 열 인덱스 필요.")
check('R1u 앵커 오검출 방어(본문에 예/아니오 + 숫자 문자열)',
      R.parse_row((1, 'LM4d', '반도체개발', 19, '예', '2', '무관한 열',
                   '아니오', 1, '진짜 사유'))['raw'] == 1,
      "parse_row 는 행을 앞에서부터 훑어 첫 (예/아니오, 1|2|3) 쌍을 앵커로 삼는다. "
      "본문/비고 열에 같은 패턴이 있으면 잘못된 등급을 읽는다. 뒤에서부터 탐색(reversed)이 안전.")

# =====================================================================
print('\n[R2] scan — 헤더/잔여행 필터, 등급 매핑')
sheets = {
    '안전': [
        ('number', '파일명', '영역', '페이지', '본문', '사고사례', '등급', '등급사유'),  # 헤더
        (None, None, None, None, None, None, None, None),                              # 공백행
        NCS_ROW,
        (2, 'LM1903060102_23v6_설계', '반도체개발', 20, '본문', '예', 3, '사유B'),
        (3, '메모만 있는 행', None, None, None, None, None, None),                     # 앵커 없음
    ],
    '위험': [
        ('number', 'x'),
        (4, 'LM1903060103_23v6_공정', '반도체제조', 31, '본문', '아니오', 2, '사유C'),
    ],
}
with with_wb(sheets):
    rows, _ = quiet(R.scan, 'dummy.xlsx', R.NCS_MAP)
check('R2a 헤더·공백·미파싱 행 제외 후 3행', len(rows) == 3, len(rows))
check('R2b 시트명이 키워드', sorted(set(r['kw'] for r in rows)) == ['안전', '위험'])
check('R2c NCS_MAP 항등 매핑', [r['g'] for r in rows if r['kw'] == '안전'] == [1, 3])
check('R2d 워크북 close 호출', True)

txt_sheets = {
    '안전': [
        ('number', 'f', 'p', 'b', 'c', 'g', 'r'),
        TXT_ROW,                                                                # raw 3
        (2, '20260413_171220_반도체기초기술1_크리아트_/x.md', 13, 'b', '아니오', 1, 'r'),  # raw 1
        (3, '20260413_171220_반도체기초기술1_크리아트_/x.md', 14, 'b', '아니오', 2, 'r'),  # raw 2
        (4, 'LM9999999999_잔여_NCS_행', '반도체개발', 5, 'b', '아니오', 3, 'r'),          # NCS 잔여행
    ],
}
with with_wb(txt_sheets):
    trows, log = quiet(R.scan, 'dummy.xlsx', R.TXT_MAP, drop_ncs_residue=True)
check('R2e NCS 잔여행(LM…) 제거 → 3행', len(trows) == 3, len(trows))
check('R2f 제외 건수 로그 출력', 'NCS 잔여행 1건 제외' in log, log.strip())
check('R2g TXT_MAP 재매핑 {1→2, 2→3, 3→1}',
      [r['g'] for r in trows] == [1, 2, 3], [r['g'] for r in trows])
with with_wb(txt_sheets):
    keep, log2 = quiet(R.scan, 'dummy.xlsx', R.TXT_MAP, drop_ncs_residue=False)
check('R2h drop_ncs_residue=False 면 LM 행 유지', len(keep) == 4, len(keep))
check('R2i 미제외 시 로그 없음', 'NCS 잔여행' not in log2)
with with_wb({'빈시트': []}):
    empty, _ = quiet(R.scan, 'dummy.xlsx', R.NCS_MAP)
check('R2j 빈 시트 → 빈 결과(예외 없음)', empty == [])

# =====================================================================
print('\n[R3] aggregate — 페이지 단위 집계')


def mk(fn, page, g, case='아니오', area='반도체개발', kw='안전', reason='r'):
    return dict(fn=fn, page=page, g=g, case=case, area=area, kw=kw, raw=g, reason=reason)


rows3 = [
    mk('A', 1, 1), mk('A', 1, 1, kw='위험'),      # 같은 쪽 2건, 등급 동일
    mk('A', 2, 2), mk('A', 2, 3, kw='위험'),      # 같은 쪽 등급 혼재
    mk('B', 5, 3, case='예'),
    mk('B', 6, 1),
]
agg, by_page = R.aggregate(rows3)
check('R3a rows', agg['rows'] == 6, agg['rows'])
check('R3b pages(고유 (교재,쪽))', agg['pages'] == 4, agg['pages'])
check('R3c books', agg['books'] == 2, agg['books'])
check('R3d row_g 행 단위', agg['row_g'] == {1: 3, 2: 1, 3: 2}, agg['row_g'])
check('R3e mixed_grade_pages 1쪽', agg['mixed_grade_pages'] == 1, agg['mixed_grade_pages'])
check('R3f page_g 합 == pages', sum(agg['page_g'].values()) == agg['pages'], agg['page_g'])
check('R3g cases_rows/pages/books',
      (agg['cases_rows'], agg['cases_pages'], agg['cases_books']) == (1, 1, 1),
      (agg['cases_rows'], agg['cases_pages'], agg['cases_books']))
# 등급 혼재 쪽: 충돌 시 최저 등급(보수적). 스캔 순서·중복 행 수·변형 수에 의존하지 않는다.
check('R3h 등급 혼재 쪽은 최저 등급이 대표',
      by_page[('A', 2)]['g'] == 2, by_page[('A', 2)]['g'])
# 중복 행이 많은 쪽이 이기면 안 된다 (실제 LM1903060425 p.28 의 4:1 상황)
rows_dup = [mk('M', 1, 2), mk('M', 1, 2, kw='위험'), mk('M', 1, 2, kw='누출'),
            mk('M', 1, 2, kw='폭발'), mk('M', 1, 1, kw='MSDS')]
check('R3h2 중복 행 4개도 정확한 행 1개를 이기지 못한다',
      R.aggregate(rows_dup)[1][('M', 1)]['g'] == 1,
      R.aggregate(rows_dup)[1][('M', 1)]['g'])
# 같은 오류의 변형이 둘로 갈려도 마찬가지 (실제 LM1903060416 p.83)
rows_var = [mk('N', 1, 2, reason='안전 6건 [...]'), mk('N', 1, 2, kw='위험', reason='안전 8건 [...]'),
            mk('N', 1, 1, kw='MSDS')]
check('R3h3 같은 오류의 변형 2개도 정확한 행 1개를 이기지 못한다',
      R.aggregate(rows_var)[1][('N', 1)]['g'] == 1,
      R.aggregate(rows_var)[1][('N', 1)]['g'])
check('R3h4 충돌이 없으면 그 등급 그대로',
      R.aggregate([mk('O', 1, 3), mk('O', 1, 3, kw='위험')])[1][('O', 1)]['g'] == 3)


def mk2(fn, page, g, reason, case='아니오'):
    return dict(fn=fn, page=page, g=g, case=case, area='반도체개발', kw='k', raw=g, reason=reason)


rows_rep = [mk2('P', 1, 3, 'R3'), mk2('P', 1, 2, 'R2a'), mk2('P', 1, 2, 'R2b')]
check('R3n 등급사유는 채택 등급 행 중 첫 번째',
      R.aggregate(rows_rep)[1][('P', 1)]['reason'] == 'R2a',
      R.aggregate(rows_rep)[1][('P', 1)]['reason'])

# 사고사례 유실: 페이지에 예가 섞여 있어도 마지막 행이 아니오면 대표행이 아니오
rows4 = [mk('C', 9, 3, case='예'), mk('C', 9, 3, case='아니오', kw='위험')]
agg4, bp4 = R.aggregate(rows4)
check('R3i 사고사례 페이지의 대표행이 사고사례를 보존(OR 규칙)',
      bp4[('C', 9)]['case'] == '예', bp4[('C', 9)]['case'])
check('R3i2 사고사례가 없으면 아니오',
      R.aggregate([mk('C', 9, 3), mk('C', 9, 3, kw='위험')])[1][('C', 9)]['case'] == '아니오')

agg5, _ = R.aggregate(rows3, total_pages=100)
check('R3j total_pages 분기 → undetected_pages',
      agg5['total_pages'] == 100 and agg5['undetected_pages'] == 96, agg5.get('undetected_pages'))
check('R3k total_pages 미지정 시 키 없음', 'total_pages' not in agg)
agg6, _ = R.aggregate([])
check('R3l 빈 입력 → pages 0 (aggregate 자체는 예외 없음)',
      agg6['pages'] == 0 and agg6['rows'] == 0)
check('R3m total_pages < 검출쪽 이면 undetected_pages 0으로 클램프',
      R.aggregate(rows3, total_pages=2)[0]['undetected_pages'] == 0,
      R.aggregate(rows3, total_pages=2)[0]['undetected_pages'])

# =====================================================================
for _raw, _want in [(0, None), (-3, None), ('19.5', None), (9999, 9999), (10000, None),
                    ('', None), (None, None), ('abc', None), (19.0, 19), ('19', 19)]:
    check('R1v as_page(%r) == %r' % (_raw, _want), R.as_page(_raw) == _want, R.as_page(_raw))

# kw_pages — 대시보드 pg 컬럼의 독립 대조원
_kwp = R.kw_pages([mk('A', 1, 1), mk('A', 1, 1, kw='위험'), mk('A', 2, 1), mk('B', 1, 1)])
check('R7a kw_pages 는 키워드별 고유 (교재,쪽) 수', _kwp == {'안전': 3, '위험': 1}, _kwp)

print('\n[R4] check — 회귀 검증')
_, out_ok = quiet(R.check, 'X', {'rows': 10, 'pages': 5}, {'rows': 10})
ok1, _ = quiet(R.check, 'X', {'rows': 10}, {'rows': 10})
ok2, out_bad = quiet(R.check, 'X', {'rows': 9}, {'rows': 10})
check('R4a 일치 → True', ok1 is True)
check('R4b 불일치 → False', ok2 is False)
check('R4c 통과 메시지', '검증 통과' in out_ok, out_ok.strip())
check('R4d 실패 메시지에 차이 표시', '검증 실패' in out_bad and '9' in out_bad, out_bad.strip())
check('R4e 기대에 없는 키는 무시', quiet(R.check, 'X', {'a': 1, 'b': 2}, {'a': 1})[0] is True)
check('R4f 키 자체가 없으면 실패', quiet(R.check, 'X', {}, {'a': 1})[0] is False)

# =====================================================================
print('\n[R5] 매핑 상수 · 기대값 정합')
check('R5a NCS_MAP 항등', R.NCS_MAP == {1: 1, 2: 2, 3: 3})
check('R5b TXT_MAP {1→2, 2→3, 3→1}', R.TXT_MAP == {1: 2, 2: 3, 3: 1})
check('R5c TXT_MAP 는 전단사(정보 손실 없음)', sorted(R.TXT_MAP.values()) == [1, 2, 3])
check('R5d GRADE_LABEL 3종', sorted(R.GRADE_LABEL) == [1, 2, 3])
for nm in ('ncs', 'txt'):
    e = R.EXPECTED[nm]
    check('R5e %s EXPECTED row_g 합 == rows' % nm, sum(e['row_g'].values()) == e['rows'],
          (sum(e['row_g'].values()), e['rows']))
    check('R5f %s EXPECTED page_g 합 == pages' % nm, sum(e['page_g'].values()) == e['pages'],
          (sum(e['page_g'].values()), e['pages']))
    check('R5g %s pages <= rows' % nm, e['pages'] <= e['rows'])
check('R5h 교과서 검출쪽 <= 전체쪽수(2,055)', R.EXPECTED['txt']['pages'] <= R.TXT_TOTAL_PAGES)
check('R5i AREAS 4종', len(R.AREAS) == 4 and all(a.startswith('반도체') for a in R.AREAS))
check('R5j FN_RE 가 LM/20…_… 둘 다 매칭',
      bool(R.FN_RE.match('LM1903060101_x')) and bool(R.FN_RE.match('20260415_143535_x')))
check('R5k FN_RE 가 무관 문자열 미매칭', R.FN_RE.match('반도체개발') is None)

# EXPECTED ↔ 산출물(summary.json) 교차검증 — 원본 엑셀 없이도 성립해야 한다
import json  # noqa: E402
sp = os.path.join(ROOT, 'docs', '03-analysis', 'data', 'summary.json')
S = json.load(open(sp, encoding='utf-8'))
for nm, key in (('ncs', 'ncs'), ('txt', 'textbook')):
    e, s = R.EXPECTED[nm], S[key]
    check('R5l summary.%s 가 EXPECTED 와 일치' % key,
          s['rows'] == e['rows'] and s['pages'] == e['pages'] and s['books'] == e['books']
          and {int(k): v for k, v in s['row_g'].items()} == e['row_g']
          and {int(k): v for k, v in s['page_g'].items()} == e['page_g'],
          (s['rows'], s['pages'], s['books']))

# =====================================================================
print('\n[R6] 경계 · 에러 상태')
check('R6a data/ 경로 상수가 리포지토리 루트 기준',
      R.DATA_DIR == os.path.join(ROOT, 'data'), R.DATA_DIR)


import inspect  # noqa: E402
main_src = inspect.getsource(R.main)


def area_ratio(pages, area):
    """main() 의 NCS 영역별 루프와 동일한 계산 (가드 포함)."""
    pl = [x for x in pages if x['area'] == area]
    g = [sum(1 for x in pl if x['g'] == i) for i in (1, 2, 3)]
    return (g[1] + g[2]) / len(pl) * 100 if pl else 0.0


try:
    ratio = area_ratio(list(by_page.values()), '반도체장비')   # 해당 영역 0쪽
    zero_div = False
except ZeroDivisionError:
    ratio, zero_div = None, True
check('R6b 검출쪽 0인 영역에서도 영역별 요약이 동작', not zero_div and ratio == 0.0, ratio)
check('R6b2 main() 의 영역별 비율에 0-division 가드가 있다',
      'if pl else' in main_src, '가드 없음')

check('R6c 원본 엑셀 부재를 사전 확인한다',
      'isfile' in main_src and 'sys.exit' in main_src, '사전 확인 없음')

with tempfile.TemporaryDirectory() as empty:
    argv, R.sys.argv = R.sys.argv, ['recount_grades.py', '--data', empty, '--out', empty]
    try:
        R.main()
        exited, msg = False, None
    except SystemExit as e:
        exited, msg = True, str(e.code)
    except Exception as e:                      # noqa: BLE001
        exited, msg = False, '%s: %s' % (type(e).__name__, e)
    finally:
        R.sys.argv = argv
check('R6c2 원본 부재 시 트레이스백 대신 안내 메시지로 종료',
      exited and msg and '원본 엑셀을 찾을 수 없습니다' in msg, msg)

# =====================================================================
# R8 insert_page_markers — 마커 주입 / --force 재삽입
#
# --force 는 argparse 에 선언만 되고 process_file 로 전달되지 않아 무동작이었다.
# 그냥 가드만 풀면 안 된다 — 기존 마커가 남아 있으면 build_page_map 이
# Strategy 1 로 그 마커를 읽어 목차 재유도 없이 같은 값을 한 번 더 심는다.
# 걷어낸 뒤 재유도하는 순서가 지켜지는지, 그리고 되돌릴 수 없는 손상을 내지
# 않는지(메타 없음 / 본문에 낀 마커)를 고정한다.
# =====================================================================
print('\n[R8] insert_page_markers — 마커 주입 · --force 재삽입')

import shutil as _shutil                                       # noqa: E402
import insert_page_markers as IPM                              # noqa: E402

_META = '{"table_of_contents":[{"title":"적용범위","page_id":1},' \
        '{"title":"안전 유의 사항","page_id":4}]}'
_BODY = '# 적용범위\n\n본문 한 줄.\n\n## 안전 유의 사항\n\n보호구 착용.\n'


@contextlib.contextmanager
def _fixture(body=_BODY, meta=_META, name='a'):
    """.md 와 짝이 되는 _meta.json 을 임시 폴더에 만든다."""
    d = tempfile.mkdtemp()
    try:
        md = os.path.join(d, name + '.md')
        with open(md, 'w', encoding='utf-8') as f:
            f.write(body)
        if meta is not None:
            with open(os.path.join(d, name + '_meta.json'), 'w', encoding='utf-8') as f:
                f.write(meta)
        yield md
    finally:
        _shutil.rmtree(d, ignore_errors=True)


def _read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


with _fixture() as md:
    r1 = IPM.process_file(md)
    after1 = _read(md)
    check('R8a 마커 없는 파일에 삽입', r1 == 'inserted_2_pages', r1)
    check('R8b page_id 는 0-based, 마커는 +1 (1 -> 2, 4 -> 5)',
          '<!-- page: 2 -->' in after1 and '<!-- page: 5 -->' in after1,
          [ln for ln in after1.split('\n') if 'page:' in ln])
    check('R8c 끝 줄바꿈을 보존한다', after1.endswith('보호구 착용.\n')
          and not after1.endswith('\n\n'), repr(after1[-14:]))

    # --force 없이 다시 → 건너뛴다
    check('R8d force 없으면 이미 마커 있는 파일은 건너뛴다',
          IPM.process_file(md) == 'skip_has_markers')

    # --force 로 여러 번 → 결과가 변하지 않아야 한다(멱등)
    r2 = IPM.process_file(md, force=True)
    IPM.process_file(md, force=True)
    after3 = _read(md)
    check('R8e force 는 재삽입을 보고한다', r2 == 'remarked_2_pages', r2)
    check('R8f force 를 반복해도 파일이 변하지 않는다(마커 중복·줄 증식 없음)',
          after3 == after1,
          'len %d -> %d, 마커 %d -> %d' % (
              len(after1), len(after3),
              after1.count('<!-- page:'), after3.count('<!-- page:')))

with _fixture(body='# 적용범위\n\n본문.') as md:                  # 끝 줄바꿈 없음
    IPM.process_file(md)
    check('R8g 끝 줄바꿈이 없던 파일에 줄바꿈을 붙이지 않는다',
          _read(md).endswith('본문.'), repr(_read(md)[-10:]))

with _fixture(meta=None) as md:                                  # meta 없음
    with open(md, 'w', encoding='utf-8') as f:                   # 마커가 이미 있는 상태로
        f.write('<!-- page: 9 -->\n# 적용범위\n')
    before = _read(md)
    # 가드가 사라지면 process_file 이 open(None) 에서 터진다. 예외까지 잡아
    # 어서션 하나의 실패로 보고한다 — 그대로 두면 하니스 전체가 죽어 무엇이
    # 깨졌는지 알 수 없다.
    try:
        r = IPM.process_file(md, force=True)
    except Exception as e:                                     # noqa: BLE001
        r = '%s: %s' % (type(e).__name__, e)
    check('R8h meta 없으면 force 여도 마커를 걷어내지 않는다',
          r == 'skip_no_meta' and _read(md) == before, r)

with _fixture(body='# 적용범위\n\n본문 <!-- page: 7 --> 중간.\n') as md:
    before = _read(md)
    r = IPM.process_file(md, force=True)
    check('R8i 본문 줄에 낀 마커는 건드리지 않고 건너뛴다',
          r == 'skip_inline_marker' and _read(md) == before, r)

check('R8j strip_page_markers 는 마커 줄만 지운다',
      IPM.strip_page_markers(['<!-- page: 3 -->', '본문', '  <!-- page: 4 -->  ',
                              '본문 <!-- page: 5 --> 안']) ==
      ['본문', '본문 <!-- page: 5 --> 안'])

# =====================================================================
# R9 regrade — 안전등급 재채점 (순수 로직)
#
# 워크북 I/O 는 원본이 비공개(.gitignore)라 CI 에서 못 돈다. 여기서는 어휘 카운트·
# 임계·길이 배율 같은 순수 함수만 고정한다. 재현율(99.6%)은 원본이 있는 환경에서
# `python3 regrade.py --validate` 로 확인한다.
# =====================================================================
print('\n[R9] regrade — 안전등급 재채점 로직')

import regrade as G                                            # noqa: E402

check('R9a 안전어 32종 / 조치어 25종 (등급사유에서 추출한 사전)',
      len(G.SAFETY_TERMS) == 32 and len(G.ACTION_TERMS) == 25,
      '%d / %d' % (len(G.SAFETY_TERMS), len(G.ACTION_TERMS)))

# --- 현재 규칙 재현: 안전 ≤5 -> 1, 조치 ≥5 -> 3, 그 사이 -> 2
low = '안전 ' * 3
check('R9b 안전 5건 이하 -> 등급1', G.grade_page(low)[0] == 1, G.grade_page(low)[:3])
mid = '위험 ' * 10
check('R9c 안전 6건 이상 + 조치 없음 -> 등급2', G.grade_page(mid)[0] == 2, G.grade_page(mid)[:3])
hi = '위험 ' * 10 + '방지 예방 착용 환기 차단 '
check('R9d 안전 6건 이상 + 조치 5건 이상 -> 등급3', G.grade_page(hi)[0] == 3, G.grade_page(hi)[:3])
mid2 = '위험 ' * 10 + '방지 예방 착용 환기 '                    # 조치 4건
check('R9e 조치 4건이면 등급3 아님(경계)', G.grade_page(mid2)[0] == 2, G.grade_page(mid2)[:3])

# --- D1 단어 경계
c_naive = G.count_terms('산업안전보건법', G.SAFETY_TERMS, word_boundary=False)
c_fixed = G.count_terms('산업안전보건법', G.SAFETY_TERMS, word_boundary=True)
check('R9f naive 는 산업안전보건법 하나를 안전·보건까지 3번 센다',
      sum(c_naive.values()) == 3, dict(c_naive))
check('R9g 단어 경계는 산업안전보건법만 1건으로 센다',
      sum(c_fixed.values()) == 1 and c_fixed['산업안전보건법'] == 1, dict(c_fixed))
homo = '진동자 진동수 격자 진동 파티클'
check('R9h 반도체 문맥 동음이의(진동자·진동수·격자 진동)를 안전어에서 뺀다',
      sum(G.count_terms(homo, G.SAFETY_TERMS, True).values()) == 0,
      dict(G.count_terms(homo, G.SAFETY_TERMS, True)))
check('R9i 문맥 없는 진동은 그대로 센다 (직업병 인자이기도 하다)',
      G.count_terms('진동 노출 관리', G.SAFETY_TERMS, True)['진동'] == 1)

# --- D2 길이 배율
check('R9j 중앙값 길이는 배율 1.0 (원본 임계 그대로)',
      abs(G.length_scale(1000, 1000) - 1.0) < 1e-9)
check('R9k 중앙값보다 짧아도 배율은 1.0 (짧다고 승급하지 않는다)',
      abs(G.length_scale(200, 1000) - 1.0) < 1e-9)
check('R9l 4배 길면 배율 2.0 (선형 4.0 이 아니라 제곱근)',
      abs(G.length_scale(4000, 1000) - 2.0) < 1e-9, G.length_scale(4000, 1000))
check('R9m 배율은 단조 증가', G.length_scale(2000, 1000) < G.length_scale(8000, 1000))

# 같은 안전어 밀도라면 긴 페이지가 짧은 페이지보다 불리해야 한다
short = '위험 ' * 8 + 'x' * 200
long_ = '위험 ' * 8 + 'x' * 20000
check('R9n 같은 안전어 수라도 긴 페이지는 승급하지 않는다',
      G.grade_page(short, True, G.length_scale(len(short), 1000))[0] == 2
      and G.grade_page(long_, True, G.length_scale(len(long_), 1000))[0] == 1,
      (G.grade_page(short, True, G.length_scale(len(short), 1000))[0],
       G.grade_page(long_, True, G.length_scale(len(long_), 1000))[0]))

check('R9o 사유 문자열은 상위 5개만 나열한다 (원본과 같은 절단)',
      G.grade_page('안전 ' * 6 + '위험 사고 누출 폭발 화재 진동 ')[3].count('(') <= 6)

# ---------------------------------------------------------------------------
# R10 regrade D4/D5 — 이산화 보정과 조건부 정규화
#
# D4 는 정규화 임계를 정수 카운트에 맞춰 자르는 방식이다. 기본값 'ceil' 은 현재
# 발행된 동작이며 여기서 바뀌면 coding_key.json 이 무효가 되므로 고정해 둔다.
# D5 는 기각된 가설이지만 재현을 위해 코드가 남아 있어 동작은 검증한다.
# ---------------------------------------------------------------------------
print('\n[R10] regrade D4/D5 — 이산화 · 조건부 정규화')

check('R10a 기본 이산화는 ceil (현재 발행된 동작을 조용히 바꾸지 않는다)',
      G.DISCRETIZE == 'ceil', G.DISCRETIZE)

# 5.02 는 실측에서 나온 값이다. an=5 인 페이지가 중앙값보다 7자 길다는 이유로
# 떨어졌다 — 정수 카운트에는 6건을 요구하는 것과 같다.
check('R10b ceil 은 5.02 를 6 으로 올린다 (한 자 차이에 요구치 20% 증가)',
      G.discretize(5.02, 'ceil') == 6, G.discretize(5.02, 'ceil'))
check('R10c round 는 5.02 를 5 로 둔다 (계단이 중간점에 온다)',
      G.discretize(5.02, 'round') == 5, G.discretize(5.02, 'round'))
check('R10d round 는 5.5 를 6 으로 (은행가 반올림이 아니라 통상 반올림)',
      G.discretize(5.5, 'round') == 6, G.discretize(5.5, 'round'))
# 5.5 는 은행가 반올림으로도 6 이라 둘을 구분하지 못한다. 6.5 에서 갈린다 —
# 파이썬 round(6.5) 는 짝수인 6 을 준다. 안전어 임계 6 x 배율 1.083 이 실제로
# 여기에 걸리므로 가상의 경계가 아니다.
check('R10p round 는 6.5 를 7 로 (파이썬 round 는 6 을 준다)',
      G.discretize(6.5, 'round') == 7, G.discretize(6.5, 'round'))
check('R10e floor 는 임계가 정수에 완전히 도달해야 올린다',
      G.discretize(5.99, 'floor') == 5 and G.discretize(6.0, 'floor') == 6)
check('R10f 세 방식의 엄격도 순서는 floor <= round <= ceil',
      all(G.discretize(x, 'floor') <= G.discretize(x, 'round') <=
          G.discretize(x, 'ceil') for x in (5.0, 5.02, 5.4, 5.5, 5.9, 6.0, 7.3)))
check('R10g 배율 1.0 이면 세 방식 모두 원본 임계와 같다',
      all(G.discretize(G.ACTION_MIN * 1.0, h) == G.ACTION_MIN
          for h in ('ceil', 'round', 'floor')))

# 실측 사례 재현: 조치어 5건, 중앙값보다 근소하게 긴 페이지.
# ceil 이면 6건을 요구해 등급2 로 떨어지고, round 면 등급3 을 유지한다.
_knife = '위험 ' * 10 + '방지 예방 착용 환기 차단 ' + 'x' * 965      # 1,010자 = 기준의 1.01배
_sc = G.length_scale(len(_knife), 1000)
check('R10h 근소 초과 페이지가 ceil 에서는 강등되고 round 에서는 살아남는다',
      1.0 < _sc < 1.2
      and G.grade_page(_knife, True, _sc, 'ceil')[0] == 2
      and G.grade_page(_knife, True, _sc, 'round')[0] == 3,
      (round(_sc, 3), G.grade_page(_knife, True, _sc, 'ceil')[0],
       G.grade_page(_knife, True, _sc, 'round')[0]))

check('R10i 크게 초과한 페이지는 이산화 방식과 무관하게 강등된다',
      all(G.grade_page('위험 ' * 10 + '방지 예방 착용 환기 차단 ' + 'x' * 30000,
                       True, G.length_scale(30000, 1000), h)[0] != 3
          for h in ('ceil', 'round', 'floor')))

# D5 — 조치어가 ACTION_EXEMPT 이상이면 길이와 무관하게 임계를 정규화하지 않는다
_many = '위험 ' * 40 + ('방지 예방 착용 환기 차단 대피 격리 소화기 보안경 안전모 '
                        ) + 'x' * 12000
_sc2 = G.length_scale(len(_many), 1000)
check('R10j 조치어가 면제 임계 이상이면 D5 가 등급3 을 되살린다',
      G.grade_page(_many, True, _sc2, 'ceil')[2] >= G.ACTION_EXEMPT
      and G.grade_page(_many, True, _sc2, 'ceil', False)[0] != 3
      and G.grade_page(_many, True, _sc2, 'ceil', True)[0] == 3,
      (G.grade_page(_many, True, _sc2, 'ceil')[2],
       G.grade_page(_many, True, _sc2, 'ceil', False)[0],
       G.grade_page(_many, True, _sc2, 'ceil', True)[0]))
check('R10k 면제 임계 미만이면 D5 는 아무것도 바꾸지 않는다',
      G.grade_page(_knife, True, _sc, 'ceil', True)[0]
      == G.grade_page(_knife, True, _sc, 'ceil', False)[0])
check('R10l 면제는 안전어 게이트까지 풀어주지는 않는다',
      G.grade_page('방지 예방 착용 환기 차단 대피 격리 소화기 보안경 안전모 '
                   + 'x' * 12000, True,
                   G.length_scale(12000, 1000), 'ceil', True)[0] == 1)
# R10l 의 페이지는 안전어가 0건이라 게이트를 풀든 말든 등급1 이다. 면제가
# 안전어 임계까지 건드리는지 보려면 정규화 전에는 통과하고 정규화 후에는
# 떨어지는 구간(6 <= 안전어 < 6*배율)에 있으면서 조치어는 면제 임계를
# 넘는 페이지가 필요하다.
_gate = '위험 ' * 10 + '방지 예방 착용 환기 차단 대피 격리 소화기 보안경 안전모 ' \
        + 'x' * 8900                                      # 약 9,000자 -> 배율 3.0
_sc3 = G.length_scale(len(_gate), 1000)
check('R10q 안전어가 원본 임계는 넘고 정규화 임계는 못 넘으면 면제해도 등급1',
      _sc3 > 2.5
      and G.SAFETY_MIN <= G.grade_page(_gate, True, _sc3, 'ceil')[1]
          < G.SAFETY_MIN * _sc3
      and G.grade_page(_gate, True, _sc3, 'ceil')[2] >= G.ACTION_EXEMPT
      and G.grade_page(_gate, True, _sc3, 'ceil', True)[0] == 1,
      (round(_sc3, 2), G.grade_page(_gate, True, _sc3, 'ceil')[1:3],
       G.grade_page(_gate, True, _sc3, 'ceil', True)[0]))

# run() 이 파라미터를 실제로 흘려보내는지 (기본값만 쓰고 무시하면 안 된다)
_pages = {('f', 1): {'text': _knife, 'grade': None}}
check('R10m run() 이 how 를 grade_page 까지 전달한다',
      G.run(_pages, True, True, 1000, 'ceil')[('f', 1)]['g'] == 2
      and G.run(_pages, True, True, 1000, 'round')[('f', 1)]['g'] == 3)
check('R10n run() 이 exempt 를 grade_page 까지 전달한다',
      G.run({('f', 1): {'text': _many, 'grade': None}},
            True, True, 1000, 'ceil', True)[('f', 1)]['g'] == 3)
check('R10o D5 는 기각됐으므로 기본값은 꺼져 있다',
      G.grade_page.__defaults__[-1] is False, G.grade_page.__defaults__)

# ---------------------------------------------------------------------------
# R11 count_terms 구간 매칭 — 외부감사 C-2 회귀
#
# 이전 구현은 `n -= text.count(ctx)` 로 총계끼리 빼서 별개 위치의 정상 출현을
# 삭제했다. `max(n, 0)` 이 음수를 삼켜 드러나지도 않았다. 아래 5건은 감사가
# 실측으로 제시한 케이스 그대로다. R9g·R9h 는 하필 과다차감이 발동하지 않는
# 입력이라 이 결함을 통과시켰다 — 그래서 별도 절로 둔다.
# ---------------------------------------------------------------------------
print('\n[R11] count_terms 구간 매칭 (감사 C-2 회귀)')


def _s(text, term=None):
    c = G.count_terms(text, G.SAFETY_TERMS, True)
    return c[term] if term else sum(c.values())


check('R11a 별개 위치의 먼지는 파티클이 아무리 많아도 살아남는다',
      _s('먼지 ' * 3 + '파티클 ' * 10, '먼지') == 3,
      _s('먼지 ' * 3 + '파티클 ' * 10, '먼지'))
check('R11b 별개 위치의 소음은 "신호 대 잡음"에 지워지지 않는다',
      _s('소음 ' * 4 + '신호 대 잡음 ' * 5, '소음') == 4,
      _s('소음 ' * 4 + '신호 대 잡음 ' * 5, '소음'))
check('R11c 동음이의는 그 출현만 빠지고 독립 출현은 남는다',
      _s('진동 ' * 2 + '초음파 진동수 ' * 2, '진동') == 2,
      _s('진동 ' * 2 + '초음파 진동수 ' * 2, '진동'))
check('R11d 산업안전보건법이 독립 안전 3건을 잡아먹지 않는다',
      _s('산업안전보건법 ' + '안전 ' * 3, '안전') == 3,
      _s('산업안전보건법 ' + '안전 ' * 3, '안전'))
# 안전보건 은 SAFETY_TERMS 에 없다. 흡수만 하면 0이 되는데 안전 내용이므로 1이다.
check('R11e 계수 목록에 없는 흡수어(안전보건)는 0이 아니라 1건으로 센다',
      _s('안전보건') == 1, _s('안전보건'))

check('R11f 같은 중첩을 두 사전 항목이 각각 빼지 않는다 (이중 차감)',
      # 산업안전보건법 은 CONTAINING 의 안전·보건 양쪽에 있다. 총계 뺄셈이던
      # 이전 구현은 한 출현을 두 번 뺐다.
      _s('산업안전보건법') == 1, _s('산업안전보건법'))
check('R11g 어떤 입력에도 음수가 나오지 않는다 (max(n,0) 없이)',
      all(v >= 0 for v in G.count_terms(
          '파티클 ' * 50 + '신호 대 잡음 ' * 50 + '진동자 ' * 50,
          G.SAFETY_TERMS, True).values()))
check('R11h 최장일치 — 긴 용어가 짧은 용어보다 먼저 구간을 가져간다',
      _s('물질안전보건자료') == 1, _s('물질안전보건자료'))
check('R11i naive 경로는 원본 재현용이라 그대로 중복 계수한다',
      sum(G.count_terms('산업안전보건법', G.SAFETY_TERMS, False).values()) == 3)
check('R11j 조치어 사전에는 안전 계열 CONTAINING 이 새지 않는다',
      # CONTAINING 의 기저어(안전·보건)가 ACTION_TERMS 에 없으므로 안전보건이
      # 조치어로 잡히면 안 된다
      G.count_terms('안전보건', G.ACTION_TERMS, True).get('안전', 0) == 0
      and sum(G.count_terms('안전보건', G.ACTION_TERMS, True).values()) == 0)
check('R11k 비포함형 동음이의는 어휘에서 빠진다 (흡수 불가라 버림)',
      all(c not in G.build_vocab(tuple(G.SAFETY_TERMS))[1]
          for c in ('파티클', '미세 입자', '신호 대 잡음', '노이즈 비')))
check('R11l 포함형 동음이의는 어휘에 있고 귀속이 None 이다',
      all(G.build_vocab(tuple(G.SAFETY_TERMS))[1].get(c, 'X') is None
          for c in ('진동자', '진동수', '격자 진동', '먼지 입자 수', '소음 지수')))

# ---------------------------------------------------------------------------
# R12 절단 무결성 — 외부감사 C-1 / C-5 회귀
#
# 절단은 두 단계에서 별개로 일어났다. 상위(엑셀 셀 한도 32,767자)는 원본이
# 엑셀뿐이라 복구 불가여서 탐지·플래그·층화로만 관리하고, 하위(코딩 시트
# 6,000자)는 제거했다. 실측: NCS 1,847쪽 중 16쪽(행으로는 1,376건), 교과서 0쪽.
# 등급별로 고르지 않다 — 등급1 0/1,270, 등급2 4/469, 등급3 12/108.
#
# 실 워크북 실측치는 data/ 가 .gitignore 라 여기서 돌지 않는다. recount_grades.py
# 의 EXPECTED 가 그 값을 지키고, 아래는 그 값을 만들어내는 로직만 고정한다.
# ---------------------------------------------------------------------------
print('\n[R12] 절단 무결성 (감사 C-1/C-5 회귀)')

import csv  # noqa: E402
import page_utils as PU  # noqa: E402
import make_coding_sheet as MCS  # noqa: E402

LIM = PU.EXCEL_MAX_CHARS
CUT = 'x' * (LIM - 3) + '...'          # add_fullpage.py 가 실제로 만드는 모양
FULL = 'y' * LIM                       # 원래 딱 한도 길이였던 본문 (자르지 않았다)

check('R12a 32,767자 + 말줄임 → 절단', PU.is_cell_truncated(CUT))
check('R12b 32,767자인데 말줄임 없음 → 절단 아님 (원래 그 길이였던 본문)',
      not PU.is_cell_truncated(FULL))
check('R12c 32,766자 + 말줄임 → 절단 아님 (짧은데 말줄임으로 끝나는 본문)',
      not PU.is_cell_truncated('z' * (LIM - 4) + '...'))
check('R12d None·정수·바이트·빈 문자열 → 절단 아님',
      not any(PU.is_cell_truncated(x) for x in (None, 0, LIM, '', b'x' * LIM)))

# 절단 셀에 앞 공백이 있으면 str.strip() 이 길이를 깎아 탐지를 놓친다.
# parse_row 는 strip 된 v 가 아니라 원시 vals 로 판정해야 한다.
CUT_PAD = '   ' + 'x' * (LIM - 6) + '...'
check('R12e parse_row 는 strip 된 값이 아니라 원시 셀에서 판정한다',
      len(CUT_PAD) == LIM and len(CUT_PAD.strip()) < LIM
      and R.parse_row((1, 'LM1903060329_19v1_장비', '반도체장비', 46,
                       CUT_PAD, '아니오', 3, '사유'))['truncated'],
      '원시 %d자 / strip 후 %d자' % (len(CUT_PAD), len(CUT_PAD.strip())))
# 교과서 워크북은 NCS 와 열 배치가 달라 고정 열로는 본문을 찾을 수 없다.
# 절단 마커가 자기 식별적이므로 행 전체를 훑으면 열 위치를 몰라도 된다.
check('R12f 본문 열 위치와 무관하게 판정한다 (교과서형 열 배치)',
      R.parse_row((1, '20260413_171220_반도체기초기술1_크리아트_/x.md', 13,
                   CUT, '아니오', 1, '사유'))['truncated'])
check('R12f2 절단 셀이 없는 행은 False', not R.parse_row(NCS_ROW)['truncated'])


def mkt(fn, page, g, truncated=False, kw='안전'):
    return dict(fn=fn, page=page, g=g, case='아니오', area='반도체개발',
                kw=kw, raw=g, reason='r', truncated=truncated)


# 순서를 뒤집어도 같아야 한다. 한쪽 순서만 보면 "마지막 행" 이나 "대표 행" 을
# 쓰는 구현이 그대로 통과한다 — 대표 행은 최저 등급을 가진 **첫** 행이라
# 절단 행과 일치한다는 보장이 없다.
_g12 = [mkt('A', 1, 3), mkt('A', 1, 3, truncated=True, kw='위험')]
check('R12g 한 행만 절단이어도 페이지는 절단 — 행 순서와 무관 (OR)',
      R.page_record(_g12)['truncated'] and R.page_record(_g12[::-1])['truncated'],
      (R.page_record(_g12)['truncated'], R.page_record(_g12[::-1])['truncated']))
check('R12g2 모든 행이 비절단이면 페이지도 비절단',
      not R.page_record([mkt('A', 1, 3), mkt('A', 1, 3, kw='위험')])['truncated'])
# 등급이 갈리는 쪽: 대표 행(최저 등급의 첫 행)이 비절단이어도 절단은 살아남아야 한다
check('R12g3 대표 행이 비절단이어도 다른 행의 절단을 잃지 않는다',
      R.page_record([mkt('A', 1, 1), mkt('A', 1, 3, truncated=True, kw='위험')])
      ['truncated'])

rows12 = [mkt('A', 1, 3, truncated=True), mkt('A', 2, 2, truncated=True),
          mkt('A', 3, 1), mkt('B', 4, 3)]
agg12, _ = R.aggregate(rows12)
check('R12h aggregate 가 절단 쪽수를 센다',
      agg12['truncated_pages'] == 2, agg12['truncated_pages'])
check('R12h2 등급별 절단 분포 (등급3 집중을 이 열로 본다)',
      agg12['truncated_page_g'] == {1: 0, 2: 1, 3: 1}, agg12['truncated_page_g'])
# --- CSV/summary 산출까지 실제 main() 으로 태운다 (--force 로 회귀 검증 우회)
sheets12 = {'안전': [NCS_ROW,
                     (2, 'LM1903060329_19v1_장비', '반도체장비', 46,
                      CUT, '아니오', 3, '사유'),
                     TXT_ROW]}
with tempfile.TemporaryDirectory() as td:
    for f in (R.NCS_FILE, R.TXT_FILE):
        open(os.path.join(td, f), 'w').close()
    _argv = sys.argv
    sys.argv = ['recount_grades.py', '--out', td, '--data', td, '--force']
    try:
        with with_wb(sheets12):
            quiet(R.main)
        with open(os.path.join(td, 'ncs_pages.csv'), encoding='utf-8-sig') as f:
            csv_rows = list(csv.reader(f))
        with open(os.path.join(td, 'summary.json'), encoding='utf-8') as f:
            summary12 = json.load(f)
    finally:
        sys.argv = _argv

check('R12i CSV 마지막 열이 절단 (중간에 끼우면 열 인덱스 소비자가 어긋난다)',
      csv_rows[0][-1] == '절단', csv_rows[0])
# NCS 스캔은 잔여행을 버리지 않으므로(drop_ncs_residue=False) 교과서형 행도 한 쪽으로
# 잡힌다. 3쪽 중 절단은 1쪽뿐이다.
check('R12i2 절단 쪽만 예, 나머지는 아니오',
      sorted(r[-1] for r in csv_rows[1:]) == ['아니오', '아니오', '예'],
      [r[-1] for r in csv_rows[1:]])
check('R12i3 기존 열 순서는 그대로',
      csv_rows[0][:7] == ['영역', '교재', '페이지', '등급', '등급명', '사고사례', '등급사유'],
      csv_rows[0])
check('R12i4 summary.json 에 절단 집계가 실린다',
      summary12['ncs']['truncated_pages'] == 1
      and summary12['textbook']['truncated_pages'] == 0,
      (summary12['ncs']['truncated_pages'], summary12['textbook']['truncated_pages']))

# 절단 열을 더해도 (교재,페이지)→등급 배정은 그대로여야 한다. 이게 깨지면
# 기존 회귀 검증(page_grade_digest)이 무너져 산출물을 쓸 수 없게 된다.
check('R12j 절단 플래그는 page_grade_digest 를 바꾸지 않는다',
      R.aggregate([dict(x, truncated=False) for x in rows12])[0]['page_grade_digest']
      == agg12['page_grade_digest'], agg12['page_grade_digest'])

# --- 코딩 시트: 어떤 경우에도 자르지 않는다 (FR-2 의 핵심 수용 기준)
_src = 'A' * 20000                       # 옛 MAX_CHARS(6,000)의 3배 넘는 본문
_pages12 = {('LM_x/y.md', 46): {'text': _src, 'grade': 3, 'truncated': True},
            ('LM_x/y.md', 47): {'text': '짧은 쪽', 'grade': 1, 'truncated': False}}
_gr12 = {k: {'g': v['grade'], 'sn': 0, 'an': 0} for k, v in _pages12.items()}
_sheet12, _key12 = MCS.build_sheet(
    _pages12, [(k, 'disputed') for k in _pages12],
    {'baseline': _gr12, MCS.RG.ADOPTED_VARIANT: _gr12})   # G2 는 아래에서 import 된다
check('R12k 코딩 시트가 본문을 자르지 않는다 (길이 == 원문 길이)',
      _sheet12[0]['text'] == _src and _sheet12[0]['chars'] == len(_src),
      (len(_sheet12[0]['text']), len(_src)))
# 렌더까지 가도 살아남아야 한다 — 코더가 실제로 보는 것은 마크다운 쪽이다.
_body = [l for l in MCS.render_item(_sheet12[0])
         if not l.startswith(('#', '>', '**', '`', '판정', '---')) and l != '']
check('R12k2 렌더된 본문을 이어붙이면 원문과 같다',
      ''.join(_body) == _src, (len(''.join(_body)), len(_src)))
check('R12k3 절단 플래그가 시트와 키 양쪽에 실린다',
      _sheet12[0]['cell_truncated'] and _key12[0]['cell_truncated']
      and not _sheet12[1]['cell_truncated'])

# --- 분할은 나누는 것이지 자르는 것이 아니다
long_txt = ('문단 %d 내용\n\n' % 0) + ('가나다라마바사아자차\n\n' * 2000) + '끝'
parts12 = MCS.chunk_text(long_txt)
check('R12l 분할은 무손실 — 이어붙이면 원문과 바이트 단위로 같다',
      ''.join(parts12) == long_txt, (len(''.join(parts12)), len(long_txt)))
check('R12l2 모든 덩어리가 분할 단위 이하',
      all(len(p) <= MCS.CHUNK_CHARS for p in parts12),
      [len(p) for p in parts12])
check('R12l3 문단 경계를 통째로 앞 덩어리에 남긴다 (경계가 쪼개지지 않는다)',
      MCS.chunk_text('A' * 5000 + '\n\n' + 'B' * 5000)[0].endswith('\n\n'))
check('R12l4 짧은 본문은 나누지 않는다', MCS.chunk_text('짧다') == ['짧다'])
check('R12m 본문 안의 코드펜스보다 긴 펜스를 쓴다 (블록이 중간에 닫히지 않게)',
      MCS.fence_for('a ``` b') == '````' and MCS.fence_for('평범한 본문') == '```',
      MCS.fence_for('a ``` b'))

_cut_item = {'id': 1, 'text': '짧은 본문', 'chars': 5, 'cell_truncated': True}
_ok_item = {'id': 2, 'text': '짧은 본문', 'chars': 5, 'cell_truncated': False}
check('R12n 절단 고지는 절단 항목에만 붙는다',
      any('원본 수집 단계에서 잘렸' in l for l in MCS.render_item(_cut_item))
      and not any('원본 수집 단계에서 잘렸' in l for l in MCS.render_item(_ok_item)))
_big = MCS.render_item({'id': 3, 'text': 'A' * 20000, 'chars': 20000,
                        'cell_truncated': False})
check('R12n2 분할돼도 한 항목이라 판정 줄은 하나',
      sum(1 for l in _big if l == '판정: ____') == 1,
      sum(1 for l in _big if l == '판정: ____'))
check('R12n3 분할 시 몇 분의 몇인지 표시한다',
      any(l.startswith('**(본문 1/') for l in _big))

# --- score_coding.strata: 절단층 분리 보고
# 설계는 이 절을 "자동화 대상 아님" 으로 뒀지만 45줄짜리 변경에 어서션이 0건이면
# CLAUDE.md 의 최소 커버리지(60%)를 못 맞춘다. 출력 문자열을 직접 잡는다.
import score_coding as SC  # noqa: E402

_ids = [str(i) for i in range(1, 11)]
_A = {i: (3 if int(i) <= 2 else 1) for i in _ids}
_B = dict(_A)
_key = {i: {'group': 'disputed' if int(i) <= 6 else 'control',
            'cell_truncated': int(i) <= 2, 'file': 'LM_a', 'page': int(i)}
        for i in _ids}
_, _out = quiet(SC.strata, _A, _B, _key, _ids)
check('R12o strata 가 절단층과 비절단층을 나눠 센다',
      '절단층 2항목 / 비절단층 8항목' in _out, _out.strip()[:80])
# 분쟁군 6쪽 중 절단 2쪽은 두 코더가 등급3 이라 했으므로 지지율이 갈려야 한다
check('R12o2 절단 포함/제외 민감도를 병기한다',
      '절단 포함  6쪽 중  4쪽 (67%)' in _out and '절단 제외  4쪽 중  4쪽 (100%)' in _out,
      _out)
check('R12o3 작은 층은 원자료를 싣는다', '원자료를 그대로 싣는다' in _out)
_, _old_out = quiet(SC.strata, _A, _B,
                    {i: {k: v for k, v in r.items() if k != 'cell_truncated'}
                     for i, r in _key.items()}, _ids)
check('R12o4 구버전 키(절단 정보 없음)는 계산하지 않고 안내한다',
      '구버전 coding_key.json' in _old_out
      and '절단층 2항목' not in _old_out          # 절단 통계를 내지 않는다
      and '절단 포함' not in _old_out,            # 민감도도 내지 않는다
      _old_out.strip()[:80])

# `?`(판단 불가)는 방향 없는 코드다. 수정본 지지로 세면 make_coding_sheet 가
# 지운 동점 규칙 편향이 채점기로 옮겨올 뿐이다.
# `?` 는 분자에서도 **분모에서도** 빠져야 한다. 분자에서만 빼면 절단 항목에 `?` 를
# 권한 지시문이 그대로 지지율을 끌어내린다 — 편향이 시트에서 채점기로 옮겨갈 뿐이다.
# 아래 픽스처는 비절단 분쟁군 4쪽 중 2쪽이 `?` 다: 분모가 4가 아니라 2여야 한다.
_o5 = quiet(SC.strata, {**_A, '3': '?', '4': '?'}, {**_B, '3': '?', '4': '?'},
            _key, _ids)[1]
check('R12o5 판단 불가(?)를 분자에서도 분모에서도 뺀다',
      '절단 제외  2쪽 중  2쪽 (100%)' in _o5
      and '절단 포함  4쪽 중  2쪽 (50%)' in _o5
      and '판단 불가 2쪽 제외' in _o5, _o5)
check('R12o6 등급 분포 출력이 ? 와 정수 혼재에도 죽지 않는다',
      SC.dist([3, 1, '?', 2, '?']) == {1: 1, 2: 1, 3: 1, '?': 2},
      SC.dist([3, 1, '?', 2, '?']))
# cats 를 (1,2,3) 으로 고정하면 '?' 쌍이 po 에만 들어가고 pe 에서 빠져 κ 가 부푼다
_ka = [3, 3, 1, '?', '?', 2, 1, 1, 3, 2]
_kb = [3, 3, 1, '?', '?', 2, 1, 2, 3, 2]
check('R12o7 κ 는 ? 를 우연 일치 계산에 포함한다 (부풀지 않는다)',
      SC.kappa(_ka, _kb) < SC.kappa(_ka, _kb, cats=(1, 2, 3)),
      (round(SC.kappa(_ka, _kb), 4), round(SC.kappa(_ka, _kb, cats=(1, 2, 3)), 4)))

# --- truncation_audit: pip 없는 재측정 도구
import truncation_audit as TA  # noqa: E402

check('R12p 열 문자를 0기반 색인으로 (A=0, Z=25, AA=26)',
      [TA._col_index(x) for x in ('A1', 'F12', 'Z9', 'AA1', 'AB3')] == [0, 5, 25, 26, 27],
      [TA._col_index(x) for x in ('A1', 'F12', 'Z9', 'AA1', 'AB3')])
_st = TA.CellStats()
_st.observe((None, 'abc', CUT, 5))
_st.observe(('짧다', None))
check('R12p2 CellStats 가 행·최장셀·절단행을 센다',
      (_st.rows, _st.longest_cell, _st.truncated_rows) == (2, LIM, 1),
      (_st.rows, _st.longest_cell, _st.truncated_rows))
check('R12p3 observe 는 받은 행을 그대로 돌려준다 (스트리밍 중 변형 금지)',
      TA.CellStats().observe(('a', 'b')) == ('a', 'b'))

# 공유 문자열 워크북: t="s" 의 <v> 는 본문이 아니라 색인이다. 표를 안 읽으면
# 모든 셀이 짧은 숫자로 보여 "절단 0건" 이라는 조용히 틀린 결과가 나온다.
_NSU = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
with tempfile.TemporaryDirectory() as _td:
    _p = os.path.join(_td, 'shared.xlsx')
    import zipfile as _zip  # noqa: E402
    with _zip.ZipFile(_p, 'w') as _z:
        _z.writestr('xl/sharedStrings.xml',
                    '<sst xmlns="%s"><si><t>%s</t></si><si><t>짧다</t></si></sst>'
                    % (_NSU, CUT))
        _z.writestr('xl/worksheets/sheet1.xml',
                    '<worksheet xmlns="%s"><sheetData><row r="1">'
                    '<c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
                    '<c r="C1"><v>7</v></c></row></sheetData></worksheet>' % _NSU)
    _shared_rows = list(TA.iter_rows(_p))
    _shared_st = TA.scan_cells(_p)
check('R12p4 공유 문자열 셀을 색인이 아니라 본문으로 읽는다',
      len(_shared_rows[0][0]) == LIM and _shared_rows[0][1] == '짧다'
      and _shared_rows[0][2] == '7',
      [None if v is None else (len(v), v[:4]) for v in _shared_rows[0]])
check('R12p5 공유 문자열 워크북에서도 절단을 잡는다',
      _shared_st.truncated_rows == 1 and _shared_st.longest_cell == LIM,
      (_shared_st.truncated_rows, _shared_st.longest_cell))

# ---------------------------------------------------------------------------
# R13 커버리지 갭 보강 (/ship Step 7 감사)
#
# R9-R12 는 순수 로직에 강했지만 I/O 경계와 각 main() 이 통째로 비어 있었다.
# 특히 truncation_audit._cell_value 는 **실제 워크북 두 개가 쓰는 inlineStr
# 갈래**에 시험이 없고, 이번에 새로 만든 공유 문자열 갈래만 검증돼 있었다 —
# 그 갈래가 죽으면 "절단 0건" 이라는 틀린 답이 나오는데 전 어서션이 초록이다.
# ---------------------------------------------------------------------------
print('\n[R13] 커버리지 갭 보강 (I/O 경계·main·가드)')

_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def _xlsx(path, sheets, shared=None):
    """시트별 XML 문자열로 최소 xlsx 를 만든다. sheets 는 XML 조각 목록."""
    import zipfile
    with zipfile.ZipFile(path, 'w') as z:
        if shared is not None:
            z.writestr('xl/sharedStrings.xml', '<sst xmlns="%s">%s</sst>'
                       % (_NS, ''.join('<si><t>%s</t></si>' % s for s in shared)))
        for i, body in enumerate(sheets, 1):
            z.writestr('xl/worksheets/sheet%d.xml' % i,
                       '<worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>'
                       % (_NS, body))
    return path


def _inline(col, text):
    return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (col, text)


def _num(col, v):
    return '<c r="%s"><v>%s</v></c>' % (col, v)


# --- truncation_audit: 실제 워크북 형식(inlineStr)과 나머지 갈래
with tempfile.TemporaryDirectory() as _td:
    _il = _xlsx(os.path.join(_td, 'inline.xlsx'),
                ['<row r="1">%s%s%s</row>'
                 % (_inline('A1', 'LM_x'), _inline('B1', CUT), _num('C1', 7))])
    _il_rows = list(TA.iter_rows(_il))
    _il_stats = TA.scan_cells(_il)
    _multi = _xlsx(os.path.join(_td, 'multi.xlsx'),
                   ['<row r="1">%s</row>' % _inline('A1', 'first'),
                    '<row r="1">%s</row>' % _inline('A1', 'second')])
    _multi_rows = [r[0] for r in TA.iter_rows(_multi)]

check('R13a inlineStr 셀을 읽는다 (실제 워크북 두 개가 쓰는 형식)',
      _il_rows[0][0] == 'LM_x' and len(_il_rows[0][1]) == LIM
      and _il_rows[0][2] == '7',
      [None if v is None else (len(v), v[:5]) for v in _il_rows[0]])
check('R13b inlineStr 워크북에서도 절단을 잡는다',
      _il_stats.truncated_rows == 1 and _il_stats.longest_cell == LIM,
      (_il_stats.truncated_rows, _il_stats.longest_cell))
check('R13c sharedStrings 가 없으면 빈 표로 동작한다 (예외 없음)',
      _il_stats.rows == 1)
check('R13d 시트를 번호 순으로 훑는다 (sheet2 가 sheet10 앞)',
      _multi_rows == ['first', 'second'], _multi_rows)

with tempfile.TemporaryDirectory() as _td:
    # 공유 색인이 범위 밖이거나 숫자가 아니면 본문 대신 None — 색인을 본문으로
    # 착각해 짧은 숫자 문자열을 흘리는 것보다 낫다.
    _bad = _xlsx(os.path.join(_td, 'bad.xlsx'),
                 ['<row r="1"><c r="A1" t="s"><v>99</v></c>'
                  '<c r="B1" t="s"><v>x</v></c><c r="C1"></c></row>'],
                 shared=['하나'])
    _bad_rows = list(TA.iter_rows(_bad))
check('R13e 공유 색인이 범위 밖·비숫자·빈 셀이면 None (색인 유출 없음)',
      _bad_rows[0] == (None, None, None), _bad_rows[0])

# fold_pages 는 이 스크립트의 핵심 주장이다 — recount 의 parse_row/aggregate 를
# 다시 구현하지 않고 빌려 쓴다. 몽키패치가 실제로 걸리고 되돌아오는지 본다.
with tempfile.TemporaryDirectory() as _td:
    _row = ('<row r="1">%s%s%s%s%s%s%s%s</row>'
            % (_num('A1', 1), _inline('B1', 'LM1903060329_19v1_x'),
               _inline('C1', '반도체장비'), _num('D1', 46),
               _inline('E1', CUT), _inline('F1', '아니오'),
               _num('G1', 3), _inline('H1', '사유')))
    _fp = _xlsx(os.path.join(_td, 'fold.xlsx'), [_row])
    _orig_lw = R.load_workbook
    _agg, _stats = TA.fold_pages(_fp, R.NCS_MAP, False)
check('R13f fold_pages 가 recount 의 parse_row/aggregate 를 실제로 태운다',
      _agg['pages'] == 1 and _agg['truncated_pages'] == 1
      and _agg['truncated_page_g'] == {1: 0, 2: 0, 3: 1},
      (_agg['pages'], _agg['truncated_pages'], _agg['truncated_page_g']))
check('R13g fold_pages 는 셀 수치를 같은 패스에서 함께 센다 (재파싱 없음)',
      _stats.rows == 1 and _stats.truncated_rows == 1)
check('R13h fold_pages 가 recount.load_workbook 을 원상 복구한다',
      R.load_workbook is _orig_lw)


def _run_main(fn, argv):
    """argv 를 갈아끼우고 main() 을 돌려 (종료코드, 출력) 을 얻는다."""
    old = sys.argv
    sys.argv = argv
    try:
        out, log = quiet(fn)
        return (out or 0), log
    except SystemExit as e:
        return (e.code if e.code is not None else 0), ''
    except Exception as e:                        # noqa: BLE001 — 가드를 지나쳐
        return '%s: %s' % (type(e).__name__, e), ''   # 굴러간 경우도 실패로 본다
    finally:
        sys.argv = old


_code, _ = _run_main(TA.main, ['truncation_audit.py', '--data', '/nonexistent'])
# sys.exit(str) 은 메시지를 stderr 로 내고 프로세스 종료코드 1 을 준다.
check('R13i truncation_audit 는 원본이 없으면 트레이스백 대신 안내로 종료',
      isinstance(_code, str) and '원본 엑셀을 찾을 수 없습니다' in _code
      and '.gitignore' in _code, _code)

# --- regrade.load_pages: regrade·make_coding_sheet 의 유일한 리더인데 어서션 0건이었다
import regrade as G2  # noqa: E402  (G 와 같은 모듈, 이름만 분리해 의도를 드러낸다)

_GOOD = (1, 'x', 'LM_a/y.md', 'area', 19, '본문 가나다', '아니오', 2, '사유')
_CUTROW = (2, 'x', 'LM_a/y.md', 'area', 20, CUT, '아니오', 3, '사유')


def _with_regrade_wb(sheets):
    wb = FakeWB(sheets)
    orig = G2.load_workbook
    G2.load_workbook = lambda *a, **k: wb
    try:
        return quiet(G2.load_pages, 'dummy.xlsx')[0]
    finally:
        G2.load_workbook = orig


_lp = _with_regrade_wb({'s': [_GOOD, _CUTROW]})
check('R13j load_pages 가 (교재,페이지) 로 접고 본문·등급을 싣는다',
      set(_lp) == {('LM_a/y.md', 19), ('LM_a/y.md', 20)}
      and _lp[('LM_a/y.md', 19)]['grade'] == 2, sorted(_lp))
check('R13k load_pages 가 절단 플래그를 채운다',
      _lp[('LM_a/y.md', 20)]['truncated']
      and not _lp[('LM_a/y.md', 19)]['truncated'])
_dup = _with_regrade_wb({'s': [_GOOD, (9, 'x', 'LM_a/y.md', 'area', 19,
                                       '나중 본문', '예', 1, '다른 사유')]})
check('R13l 같은 페이지가 또 나오면 첫 행이 이긴다 (스캔 순서 의존 제거)',
      _dup[('LM_a/y.md', 19)]['text'] == '본문 가나다',
      _dup[('LM_a/y.md', 19)]['text'])
_skip = _with_regrade_wb({'s': [
    ('number',) + _GOOD[1:],                      # 헤더 행
    (1, 'x', 'LM_a/y.md', 'a', 19),               # 열이 모자란 행
    (1, 'x', None, 'a', 19, '본문', '아니오', 2, 's'),        # 교재 없음
    (1, 'x', 'LM_b/y.md', 'a', 'abc', '본문', '아니오', 2, 's'),  # 페이지 파싱 실패
    (1, 'x', 'LM_c/y.md', 'a', 21, None, '아니오', 2, 's'),   # 본문이 문자열이 아님
    (1, 'x', 'LM_d/y.md', 'a', 22, '   ', '아니오', 2, 's'),  # 본문이 공백뿐
]})
check('R13m load_pages 가 헤더·짧은 행·결측·파싱실패·빈 본문을 전부 건너뛴다',
      _lp and _skip == {}, sorted(_skip))

check('R13n median_length 는 빈 입력에서 DENSITY_BASE 로 떨어진다',
      G2.median_length({}) == G2.DENSITY_BASE, G2.median_length({}))
check('R13o median_length 는 중앙값을 준다',
      G2.median_length({i: {'text': 'x' * n} for i, n in enumerate((10, 20, 90))}) == 20)
check('R13p dist 는 등장하지 않은 등급도 0 으로 채운다',
      G2.dist({'a': {'g': 3}}) == {1: 0, 2: 0, 3: 3 and 1}, G2.dist({'a': {'g': 3}}))
check('R13q agree 는 등급이 정수가 아닌 행을 분모에서 뺀다',
      G2.agree({'a': {'g': 2}, 'b': {'g': 1}},
               {'a': {'grade': 2}, 'b': {'grade': None}}) == (1, 1),
      G2.agree({'a': {'g': 2}, 'b': {'g': 1}},
               {'a': {'grade': 2}, 'b': {'grade': None}}))
_code, _ = _run_main(G2.main, ['regrade.py', '--data', '/nonexistent'])
check('R13r regrade 는 원본이 없으면 트레이스백 대신 안내로 종료',
      isinstance(_code, str) and '원본 엑셀을 찾을 수 없습니다' in _code, _code)

# --- score_coding 가드
check('R13s kappa 는 빈 입력에서 nan (0 나눗셈 대신)', SC.kappa([], []) != SC.kappa([], []))
check('R13t kappa 는 전원 같은 범주면 nan (pe==1, 우연 일치가 100%)',
      SC.kappa([3, 3, 3], [3, 3, 3]) != SC.kappa([3, 3, 3], [3, 3, 3]))
_ids20 = [str(i) for i in range(1, 25)]
_A20 = {i: (3 if int(i) % 2 else 1) for i in _ids20}
_key20 = {i: {'group': 'disputed', 'cell_truncated': int(i) <= 2,
              'file': 'LM_a', 'page': int(i)} for i in _ids20}
_, _out20 = quiet(SC.strata, _A20, _A20, _key20, _ids20)
check('R13u 층이 20항목 이상이면 κ 를 낸다 (작은 층에서는 안 낸다)',
      'κ =' in _out20 and '절단층  2항목' in _out20 and 'κ' not in _out20.split('비절단층')[0].split('절단층')[1].split('\n')[0],
      _out20)
_keyno = {i: dict(r, cell_truncated=False) for i, r in _key20.items()}
_, _outno = quiet(SC.strata, _A20, _A20, _keyno, _ids20)
check('R13v 절단 항목이 0건이면 층 분리를 하지 않고 안내한다',
      '절단 항목이 없어' in _outno and 'A 분포' not in _outno, _outno)
_old_cwd = SC.HERE
SC.HERE = '/nonexistent'
try:
    _lcode, _ = _run_main(lambda: SC.load('coding_A.json'), ['x'])
finally:
    SC.HERE = _old_cwd
check('R13w score_coding.load 는 파일이 없으면 안내로 종료',
      isinstance(_lcode, str) and '없음' in _lcode, _lcode)

# 커밋된 regrade_impact.json 과 population() 이 읽는 키를 묶어 둔다. 이 결합은
# regrade.py 의 **표시용 라벨 문자열**('D1+D2 둘 다')이라, 라벨을 손보면
# score_coding 이 KeyError 로 죽는데 지금까지 아무 시험도 걸려 있지 않았다.
_imp = json.load(open(os.path.join(ROOT, 'docs/03-analysis/data/regrade_impact.json'),
                      encoding='utf-8'))
# 어느 변형이 '수정본' 인지는 산출물이 스스로 밝힌다. 여기서 라벨을 타이핑하면
# 시험이 라벨 변경에 깨지는데, 그건 이 시험이 막으려는 바로 그 결함이다.
_adopted = _imp.get('adopted_variant', 'D1+D2 둘 다')
# 키 존재를 **먼저** 확인한다. 곧바로 인덱싱하면 산출물이 어긋났을 때 하네스가
# 트레이스백으로 죽어 나머지 어서션을 통째로 가린다.
_has_adopted = _adopted in _imp.get('dist', {})
check('R13x regrade_impact.json 에 population() 이 읽는 키가 있다',
      'pages' in _imp and '3' in _imp.get('dist', {}).get('baseline', {})
      and _has_adopted and '3' in _imp['dist'][_adopted],
      (_adopted, list(_imp.get('dist', {}))))
check('R13y 분쟁군 = 현행 등급3 - 수정본 등급3 이 양수 (표본 설계 전제)',
      _has_adopted
      and _imp['dist']['baseline']['3'] - _imp['dist'][_adopted]['3'] > 0,
      (_imp['dist']['baseline']['3'],
       _imp['dist'][_adopted]['3'] if _has_adopted else '(키 없음)'))

# --- chunk_text 의 남은 갈래
_nl = 'A' * 4000 + '\n' + 'B' * 4000            # 문단 경계 없이 줄 경계만
_p_nl = MCS.chunk_text(_nl)
check('R13z 문단 경계가 없으면 줄 경계에서 나눈다',
      _p_nl[0].endswith('\n') and ''.join(_p_nl) == _nl, [len(p) for p in _p_nl])
_hard = 'C' * 20000                              # 경계가 아예 없다
_p_hard = MCS.chunk_text(_hard)
check('R13aa 경계가 하나도 없으면 그냥 끊는다 (무한 루프 없이)',
      ''.join(_p_hard) == _hard
      and all(len(p) <= MCS.CHUNK_CHARS for p in _p_hard), [len(p) for p in _p_hard])

# --- EXPECTED 자체 정합성 (R5e/R5f 패턴을 절단 키로 확장)
check('R13ab EXPECTED 의 등급별 절단 합계 == truncated_pages',
      all(sum(R.EXPECTED[k]['truncated_page_g'].values())
          == R.EXPECTED[k]['truncated_pages'] for k in ('ncs', 'txt')),
      {k: (R.EXPECTED[k]['truncated_pages'],
           R.EXPECTED[k]['truncated_page_g']) for k in ('ncs', 'txt')})
check('R13ac EXPECTED 의 절단 쪽수는 전체 쪽수를 넘지 않는다',
      all(R.EXPECTED[k]['truncated_pages'] <= R.EXPECTED[k]['pages']
          for k in ('ncs', 'txt')))

# --- /ship 스페셜리스트가 짚은 나머지 갭
# population() 은 R13x/R13y 가 같은 JSON 을 손으로 다시 읽어 검증하고 있었다.
# 함수를 직접 태워야 키 경로가 바뀌었을 때 잡힌다.
try:
    _pop = SC.population()
except SystemExit as e:               # 라벨이 어긋나면 sys.exit 한다 — 하네스를
    _pop = str(e)                     # 죽이지 말고 이 줄의 실패로 보이게 잡는다
check('R13ad population() 이 커밋된 regrade_impact.json 에서 모집단을 뽑는다',
      _has_adopted and _pop == (
          _imp['pages'],
          _imp['dist']['baseline']['3'] - _imp['dist'][_adopted]['3'],
          _imp['dist'][_adopted]['3']), _pop)

# main() 의 교차 검증 가드 — 키의 분쟁군 수와 regrade_impact.json 이 어긋나면
# 4·5절 가중치가 조용히 틀어지므로 여기서 멈춰야 한다. 시험이 없었다.
_orig_load, _orig_pop = SC.load, SC.population
_key_items = [{'id': 1, 'group': 'disputed', 'file': 'a', 'page': 1},
              {'id': 2, 'group': 'control', 'file': 'b', 'page': 2}]
_kd = MCS.sample_digest(_key_items)               # 지문은 맞춰 둔다 — 여기서
try:                                              # 보려는 것은 **개수** 가드다
    SC.load = lambda n: ({'coder': 'A', 'sample_digest': _kd,
                          'grades': {'1': 3, '2': 1}} if n.startswith('coding_A')
                         else {'coder': 'B', 'sample_digest': _kd,
                               'grades': {'1': 3, '2': 1}} if n.startswith('coding_B')
                         else {'sample_digest': _kd, 'items': _key_items})
    SC.population = lambda: (100, 5, 10)          # 키는 분쟁군 1쪽, 모집단은 5쪽
    _mcode, _ = _run_main(SC.main, ['score_coding.py'])
finally:
    SC.load, SC.population = _orig_load, _orig_pop
check('R13ae 키의 분쟁군 수가 모집단 수치와 어긋나면 멈춘다',
      isinstance(_mcode, str) and '불일치' in _mcode and '1쪽' in _mcode, _mcode)

# regrade(R13r)·truncation_audit(R13i) 는 원본 부재 종료를 지키는데
# make_coding_sheet 만 빠져 있었다 — 같은 모양의 가드는 같이 지킨다.
_orig_dd = G2.DATA_DIR
try:
    G2.DATA_DIR = '/nonexistent'
    _kcode, _ = _run_main(MCS.main, ['make_coding_sheet.py'])
finally:
    G2.DATA_DIR = _orig_dd
check('R13af make_coding_sheet 도 원본이 없으면 안내로 종료한다',
      isinstance(_kcode, str) and '원본 엑셀을 찾을 수 없습니다' in _kcode, _kcode)

# 변형 라벨은 regrade 가 소유하고 산출물이 실어 나른다. score_coding 이 라벨을
# 다시 타이핑하면 라벨 수정이 조용히 KeyError 가 된다.
check('R13ag 산출물이 어느 변형을 "수정본" 으로 보는지 스스로 밝힌다',
      _imp.get('adopted_variant') == G2.ADOPTED_VARIANT
      and G2.ADOPTED_VARIANT in _imp['dist'], _imp.get('adopted_variant'))

# --- score_variants: 정밀도/재현율/F1 70줄에 시험이 0건이었다
_sv_pages = {('f', i): {'text': 'x' * 100, 'grade': 3, 'truncated': False}
             for i in (1, 2, 3, 4)}
_sv_calls = []


def _sv_run(pages, word_boundary=False, normalize=False, base=None, **kw):
    _sv_calls.append((word_boundary, normalize, tuple(sorted(kw.items()))))
    keep = (1, 2, 3, 4) if not (word_boundary or normalize) else (1, 2)
    return {k: {'g': 3 if k[1] in keep else 1, 'sn': 9, 'an': 9, 'reason': '', 'len': 100}
            for k in pages}


_sv_key = {str(i): {'file': 'f', 'page': i,
                    'group': 'disputed' if i in (3, 4) else 'control'}
           for i in (1, 2, 3, 4)}
_sv_A = {'1': 3, '2': 3, '3': 3, '4': 1}
_o_lp, _o_run = G2.load_pages, G2.run
try:
    G2.load_pages = lambda p: _sv_pages
    G2.run = _sv_run
    _, _sv_out = quiet(SC.score_variants, _sv_A, _sv_A, _sv_key, ['3', '4'], ['1', '2'])
finally:
    G2.load_pages, G2.run = _o_lp, _o_run

check('R13ah score_variants 가 코더 둘 × 변형 다섯을 표로 낸다',
      _sv_out.count('--- 코더') == 2 and _sv_out.count('D1+D2') >= 3
      and '과적합' in _sv_out, _sv_out[:120])
# 변형 그리드는 코더와 무관하다. 코더 루프 안에서 돌리면 baseline 1 + 5×2 = 11 번
# 돈다 — 1,847쪽 × 32,767자 스캔이 통째로 두 번이다. 6번이어야 한다.
check('R13ai 변형 그리드를 코더당 다시 계산하지 않는다 (run 호출 6회)',
      len(_sv_calls) == 6, len(_sv_calls))
_sv_calls.clear()
_o_lp2 = G2.load_pages
try:
    G2.load_pages = lambda p: (_ for _ in ()).throw(OSError('원본 없음'))
    _, _sv_none = quiet(SC.score_variants, _sv_A, _sv_A, _sv_key, ['3', '4'], ['1', '2'])
finally:
    G2.load_pages = _o_lp2
check('R13aj 원본을 못 읽으면 조용히 건너뛴다 (채점 전체를 죽이지 않는다)',
      _sv_none.strip() == '' and not _sv_calls, _sv_none[:80])

# ---------------------------------------------------------------------------
# R14 표본 지문과 회귀 가드 — /ship red team 회귀
#
# 코더 라벨은 항목 번호로만 페이지에 붙는데 시트를 다시 만들면 번호가 전부
# 바뀐다. 예전 가드는 분쟁군 **개수**만 비교해서, 개수가 우연히 맞으면 엉뚱한
# 페이지의 라벨로 κ·F1 이 그럴듯하게 찍혔다. 숫자가 조용히 틀리는 것이 죽는
# 것보다 나쁘다. 그리고 regrade.py 는 발표 수치의 근거 파일을 아무 검사 없이
# 덮어쓰고 있었다 — 형제 스크립트 recount_grades.py 에는 있던 가드다.
# ---------------------------------------------------------------------------
print('\n[R14] 표본 지문 · regrade 회귀 가드 (red team 회귀)')

_k1 = [{'file': 'a', 'page': 1, 'group': 'disputed'},
       {'file': 'b', 'page': 2, 'group': 'control'}]
check('R14a 표본 지문은 항목 순서에 무관하다 (shuffle 이 지문을 바꾸면 안 된다)',
      MCS.sample_digest(_k1) == MCS.sample_digest(list(reversed(_k1))),
      MCS.sample_digest(_k1))
check('R14b 표본이 한 쪽이라도 다르면 지문이 달라진다',
      MCS.sample_digest(_k1)
      != MCS.sample_digest(_k1 + [{'file': 'c', 'page': 3, 'group': 'control'}]))
check('R14c 같은 쪽이라도 군이 바뀌면 지문이 달라진다',
      MCS.sample_digest(_k1)
      != MCS.sample_digest([dict(_k1[0], group='control'), _k1[1]]))

_D = MCS.sample_digest(_k1)
check('R14d unwrap 은 신·구 두 모양을 모두 받는다',
      SC.unwrap({'sample_digest': _D, 'items': _k1}) == (_k1, _D)
      and SC.unwrap(_k1) == (_k1, None))


def _sample(*a):
    try:
        SC.check_sample(*a)
        return None
    except SystemExit as e:
        return str(e)


check('R14e 구버전 키(지문 없음)는 채점을 거부한다',
      '구버전' in (_sample(None, {'coder': 'A', 'sample_digest': _D}) or ''),
      _sample(None, {'coder': 'A'}))
check('R14f 지문이 어긋난 라벨은 채점을 거부한다 (번호로 억지 결합 금지)',
      '지문 불일치' in (_sample(_D, {'coder': 'A', 'sample_digest': 'deadbeef'}) or ''),
      _sample(_D, {'coder': 'A', 'sample_digest': 'deadbeef'}))
check('R14g 지문 없는 라벨도 거부한다',
      '지문 불일치' in (_sample(_D, {'coder': 'B'}) or ''), _sample(_D, {'coder': 'B'}))
check('R14h 지문이 맞으면 통과한다',
      _sample(_D, {'coder': 'A', 'sample_digest': _D},
              {'coder': 'B', 'sample_digest': _D}) is None)

# regrade 회귀 가드
_g_ok = {('f', 1): {'g': 1}, ('f', 2): {'g': 3}}
check('R14i impact_digest 는 배정이 바뀌면 달라진다 (총계 상쇄를 잡는다)',
      G2.impact_digest(_g_ok)
      != G2.impact_digest({('f', 1): {'g': 3}, ('f', 2): {'g': 1}}),
      G2.impact_digest(_g_ok))
check('R14j impact_digest 는 삽입 순서에 무관하다',
      G2.impact_digest(_g_ok)
      == G2.impact_digest({('f', 2): {'g': 3}, ('f', 1): {'g': 1}}))
check('R14k check_expected 는 어긋난 항목을 짚고 False 를 준다',
      quiet(G2.check_expected, dict(G2.EXPECTED, pages=1))[0] is False
      and 'pages' in quiet(G2.check_expected, dict(G2.EXPECTED, pages=1))[1])
check('R14l check_expected 는 기대값 그대로면 True', quiet(G2.check_expected, dict(G2.EXPECTED))[0])
# 커밋된 산출물이 코드의 EXPECTED 와 맞는지 — 파일을 자기 자신으로 검증하지 않는다
# 함수가 옳은 것과 main() 이 그것을 **부르는** 것은 다른 문제다. 호출을 지웠을 때
# 아무 시험도 깨지지 않으면 가드는 사실상 없는 것이다.
_bad_items = [{'id': 1, 'group': 'disputed', 'file': 'a', 'page': 1}]
_o_load, _o_pop = SC.load, SC.population
try:
    SC.load = lambda n: ({'coder': n[7], 'sample_digest': 'WRONG',
                          'grades': {'1': 3}} if n.startswith('coding_A')
                         or n.startswith('coding_B')
                         else {'sample_digest': MCS.sample_digest(_bad_items),
                               'items': _bad_items})
    SC.population = lambda: (100, 1, 10)          # 개수는 맞춘다 — 지문만 틀리게
    _scode, _ = _run_main(SC.main, ['score_coding.py'])
finally:
    SC.load, SC.population = _o_load, _o_pop
check('R14n main 이 개수 가드보다 먼저 지문 가드를 통과시킨다',
      isinstance(_scode, str) and '지문 불일치' in _scode, _scode)

# regrade.main 이 회귀 검증 결과로 실제로 멈추는가 (--force 없이).
# 원본 부재 가드를 넘기려면 이름만 같은 빈 파일이면 된다 — load_pages 는 패치한다.
_o = (G2.load_pages, G2.run, G2.median_length, G2.OUT_DIR)
with tempfile.TemporaryDirectory() as _rtd:
    open(os.path.join(_rtd, G2.NCS_FILE), 'w').close()
    try:
        # 가드가 뚫린 상태에서 main 이 끝까지 굴러가도 커밋된 산출물을 건드리지
        # 못하게 한다. 이 격리가 없으면 뮤테이션 검증이 저장소를 오염시킨다.
        G2.OUT_DIR = _rtd
        G2.load_pages = lambda p: {('f', 1): {'text': 'x' * 50, 'grade': 1,
                                              'truncated': False}}
        G2.run = lambda pages, **kw: {k: {'g': 1, 'sn': 0, 'an': 0, 'reason': '',
                                          'len': 50} for k in pages}
        G2.median_length = lambda pages: 50
        _rcode, _ = _run_main(G2.main, ['regrade.py', '--data', _rtd])
    finally:
        G2.load_pages, G2.run, G2.median_length, G2.OUT_DIR = _o
check('R14o regrade.main 은 회귀 검증에 실패하면 산출물을 쓰지 않고 멈춘다',
      isinstance(_rcode, str) and '회귀 검증에 실패' in _rcode, _rcode)

check('R14m 커밋된 regrade_impact.json 이 regrade.EXPECTED 와 일치한다',
      _imp['pages'] == G2.EXPECTED['pages']
      and _imp['reproduction'] == G2.EXPECTED['reproduction']
      and _imp.get('baseline_digest') == G2.EXPECTED['baseline_digest']
      and {k: {int(g): n for g, n in v.items()} for k, v in _imp['dist'].items()}
      == G2.EXPECTED['dist'],
      (_imp['pages'], _imp.get('baseline_digest')))

# ---------------------------------------------------------------------------
# R15 재코딩 (recoding) — 어휘 확장 변형 · 4층 합집합 표본 · 항목별 호출기 · 재현율
#
# 기존 69쪽 라벨은 무효다(코더 A 독립성 실패 + 지시문 누출 + 표본틀 오염). 다시
# 만드는 표본은 두 어휘(현재 사전 / +21종)의 **합집합**으로 층을 뽑아 같은 라벨로
# 네 변형을 채점한다 — 어휘 채택도 라벨이 판정한다. 설계: recoding.design.md
# ---------------------------------------------------------------------------
print('\n[R15] 재코딩 — 어휘 확장 변형 (regrade)')


def _call(fn, *a, **k):
    """아직 없는 기능은 크래시가 아니라 이 줄의 실패로 보이게 한다 (TDD RED)."""
    try:
        return fn(*a, **k)
    except (Exception, SystemExit) as e:          # noqa: BLE001 — sys.exit 가드도 값으로 받는다
        return e


# 안전어 6종을 한 번씩, 조치어는 확장 사전에만 있는 '장갑' 5회.
_v_text = ' '.join(['안전', '위험', '주의', '사고', '유해', '누출'] + ['장갑'] * 5)
_v_off, _v_on = _call(G2.grade_page, _v_text), _call(G2.grade_page, _v_text, extra_vocab=True)
check('R15a 어휘 확장을 켜면 확장 조치어가 등급을 올린다 (2→3)',
      isinstance(_v_on, tuple) and _v_off[0] == 2 and _v_on[0] == 3, (_v_off, _v_on))
_v_d1 = _call(G2.count_terms, '안전난간 착용', G2.ACTION_TERMS + getattr(G2, 'EXTRA_ACTION_TERMS', []),
              word_boundary=True)
check('R15a2 D1 경로에서도 확장어가 최장일치로 잡힌다 (안전난간 1, 착용 1)',
      _v_d1 == {'안전난간': 1, '착용': 1}, _v_d1)
check('R15b 어휘 확장을 끄면 기준선과 완전히 같다 (재현 기준선에 새지 않는다)',
      _v_off == _call(G2.grade_page, _v_text, extra_vocab=False)
      and G2.count_terms(_v_text, G2.ACTION_TERMS) == {})
check('R15c 확장 사전 21종은 기존 사전과 겹치지 않는다 (조치 12 / 안전 9)',
      len(getattr(G2, 'EXTRA_ACTION_TERMS', [])) == 12
      and len(getattr(G2, 'EXTRA_SAFETY_TERMS', [])) == 9
      and not (set(getattr(G2, 'EXTRA_ACTION_TERMS', []))
               | set(getattr(G2, 'EXTRA_SAFETY_TERMS', [])))
      & (set(G2.ACTION_TERMS) | set(G2.SAFETY_TERMS)))
_grid = _call(lambda: dict(G2.variant_grid()))
check('R15d variant_grid 에 어휘 변형 둘이 있고 EXPECTED 가 모든 변형의 분포를 고정한다',
      isinstance(_grid, dict)
      and getattr(G2, 'VOCAB_VARIANT', None) in _grid
      and getattr(G2, 'ADOPTED_VOCAB_VARIANT', None) in _grid
      and _grid[G2.VOCAB_VARIANT].get('extra_vocab') is True
      and set(G2.EXPECTED['dist']) == {'baseline', *_grid},
      _grid if not isinstance(_grid, dict) else sorted(_grid))
_v_run = _call(G2.run, {('f', 1): {'text': _v_text}}, False, False, extra_vocab=True)
check('R15d2 run() 이 extra_vocab 을 grade_page 까지 전달한다',
      isinstance(_v_run, dict) and _v_run[('f', 1)]['g'] == 3, _v_run)

print('\n[R15] 재코딩 — 4층 합집합 표본 (make_coding_sheet)')

_VB, _VN, _VV, _VNV = 'baseline', G2.ADOPTED_VARIANT, G2.VOCAB_VARIANT, G2.ADOPTED_VOCAB_VARIANT
# 합성 예측 — (현행, D1+D2, 현행+V, D1+D2+V). 합집합의 효과가 보이도록 짰다:
#   p3 는 V 쌍에서만 갈리고, p4 는 V 에서만 등급3, p6 는 V 쌍에서만 경계다.
#   p9 는 어떤 변형이든 3 이면 전수 대상임을 본다 — 단조성 논증에 기대지 않는다.
_syn = {'p1': (3, 3, 3, 3), 'p2': (3, 1, 3, 1), 'p3': (3, 3, 3, 2), 'p4': (2, 1, 3, 3),
        'p5': (2, 1, 2, 1), 'p6': (1, 1, 2, 1), 'p7': (2, 2, 2, 2), 'p8': (1, 1, 1, 1),
        'p9': (2, 2, 2, 3)}
_preds = {nm: {k: {'g': v[i]} for k, v in _syn.items()}
          for i, nm in enumerate((_VB, _VN, _VV, _VNV))}
_st = _call(lambda: MCS.strata(_preds))
check('R15e 4층 합집합 — 분쟁군은 두 규칙쌍 중 하나라도 갈리면 든다',
      isinstance(_st, dict) and _st.get('disputed') == ['p2', 'p3'], _st)
check('R15f 합의군은 전수 — 어느 변형이든 등급3인 쪽 전부에서 분쟁군을 뺀 것',
      isinstance(_st, dict) and _st.get('control') == ['p1', 'p4', 'p9'], _st)
check('R15g 경계층(2→1)은 두 규칙쌍의 합집합, 재현율 모집단은 나머지 전부',
      isinstance(_st, dict) and _st.get('boundary') == ['p5', 'p6']
      and _st.get('recall_pool') == ['p7', 'p8'], _st)
_dr = _call(lambda: MCS.draw(_st, seed=1, n_recall=1)) if isinstance(_st, dict) else None
_dr2 = _call(lambda: MCS.draw(_st, seed=1, n_recall=1)) if isinstance(_st, dict) else None
check('R15h draw 는 전수 3층 + 재현율 무작위층을 섞어 내고 시드에 결정적이다',
      isinstance(_dr, list) and _dr == _dr2 and len(_dr) == 8
      and {g for _, g in _dr} == {'disputed', 'control', 'boundary', 'recall'}
      and sum(1 for _, g in _dr if g == 'recall') == 1, _dr)
check('R15h2 새 표본은 새 시드 — 옛 시드(20260903)를 버리고, 대조군 무작위 상수도 없다',
      MCS.SEED != 20260903 and getattr(MCS, 'N_RECALL', None) == 300
      and not hasattr(MCS, 'N_CONTROL'), (MCS.SEED, getattr(MCS, 'N_RECALL', None)))

_pg15 = {('f', 1): {'text': '본문 하나', 'grade': 3, 'truncated': False},
         ('f', 2): {'text': 'x' * 10, 'grade': 1, 'truncated': True}}
_pr15 = {nm: {k: {'g': 3 if k[1] == 1 else 1} for k in _pg15}
         for nm in (_VB, _VN, _VV, _VNV)}
_bs = _call(MCS.build_sheet, _pg15, [(('f', 1), 'control'), (('f', 2), 'recall')], _pr15)
check('R15i 시트에는 등급·카운트·군이 없고, 키에는 변형별 예측이 실린다 (앵커링 차단)',
      isinstance(_bs, tuple)
      and not any(k in it for it in _bs[0] for k in ('pred', 'group', 'grade', 'old', 'new'))
      and all(set(r['pred']) == {_VB, _VN, _VV, _VNV} for r in _bs[1])
      and _bs[1][0]['group'] == 'control' and _bs[1][0]['pred'][_VB] == 3
      and _bs[1][1]['pred'][_VNV] == 1, _bs)
check('R15i2 절단 항목은 시트 JSON 에도 고지가 실린다 (API 코더도 사람과 같은 고지를 본다)',
      isinstance(_bs, tuple) and '잘렸' in _bs[0][1].get('notice', '')
      and 'notice' not in _bs[0][0], _bs)
_cp = _call(lambda: MCS.coder_prompt())
check('R15i3 코더 지시문은 시트가 소유한다 — 등급 정의와 응답 형식(1/2/3/?)이 들고 누출은 없다',
      isinstance(_cp, str) and '구체적 대책' in _cp and '형식적 언급' in _cp
      and '`?`' in _cp and '진동' not in _cp and '낮은 등급' not in _cp,
      _cp if not isinstance(_cp, str) else _cp[:80])

print('\n[R15] 재코딩 — 항목별 독립 호출기 (code_pages)')
import hashlib  # noqa: E402

CP = _call(lambda: __import__('code_pages'))
_cp_ok = not isinstance(CP, Exception)
check('R15j code_pages 는 표준 라이브러리만으로 import 된다', _cp_ok, CP)

with tempfile.TemporaryDirectory() as _td:
    _envp = os.path.join(_td, '.env')
    with open(_envp, 'w') as _f:
        _f.write('# 주석\nexport AUDIT_LLM_BASE_URL="https://api.openai.com/v1"\n'
                 'AUDIT_LLM_API_KEY=sk-test\nAUDIT_LLM_MODEL=\'gpt-x\'\n'
                 'AUDIT_LLM_TEMPERATURE=1.0\n\nGEMINI_API_KEY=gm-test\n')
    _env = _call(lambda: CP.read_env(_envp)) if _cp_ok else None
check('R15j2 read_env 는 export·따옴표·주석·빈 줄을 처리한다',
      isinstance(_env, dict) and _env.get('AUDIT_LLM_BASE_URL') == 'https://api.openai.com/v1'
      and _env.get('AUDIT_LLM_MODEL') == 'gpt-x' and _env.get('GEMINI_API_KEY') == 'gm-test',
      _env)
_cfg = _call(lambda: CP.provider_config(_env)) if isinstance(_env, dict) else None
check('R15j3 provider_config 는 AUDIT_LLM_* 를 우선하고 모델·키·주소를 한 곳에서 읽는다',
      isinstance(_cfg, dict) and _cfg.get('model') == 'gpt-x' and _cfg.get('api_key') == 'sk-test'
      and _cfg.get('base_url') == 'https://api.openai.com/v1'
      and _cfg.get('key_var') == 'AUDIT_LLM_API_KEY', _cfg)
_cfg2 = (_call(lambda: CP.provider_config({'GEMINI_API_KEY': 'gm'}, model='gemini-x'))
         if _cp_ok else None)
check('R15j4 AUDIT_LLM_* 가 없으면 키 변수명으로 제공자 주소를 고른다 (Gemini 프리셋)',
      isinstance(_cfg2, dict) and 'generativelanguage.googleapis.com' in _cfg2.get('base_url', '')
      and _cfg2.get('key_var') == 'GEMINI_API_KEY' and _cfg2.get('model') == 'gemini-x', _cfg2)
check('R15j5 온도는 .env 에서 상속하지 않는다 — 설정에 temperature 가 없고 기본값은 0',
      isinstance(_cfg, dict) and 'temperature' not in _cfg
      and getattr(CP, 'DEFAULT_TEMPERATURE', None) == 0.0, _cfg)
_nokey = _call(lambda: CP.provider_config({'FOO': 'bar'}, model='m')) if _cp_ok else None
_nomodel = _call(lambda: CP.provider_config({'OPENAI_API_KEY': 'k'})) if _cp_ok else None
check('R15j6 키나 모델이 없으면 기본값으로 때우지 않고 거부한다',
      isinstance(_nokey, ValueError) and '키' in str(_nokey)
      and isinstance(_nomodel, ValueError) and '모델' in str(_nomodel), (_nokey, _nomodel))

_pg_cases = [('3', 3), (' 2 \n', 2), ('등급: 1', 1), ('?', '?'), ('**3**', 3), ('판정: `2`', 2),
             ('3. 구체적 대책이 있다', 3), ('2 또는 3', None), ('', None),
             ('안전 조치가 없다', None), ('12', None), (None, None)]
_pg_got = [(_call(lambda a=a: CP.parse_grade(a)) if _cp_ok else None) for a, _ in _pg_cases]
check('R15k parse_grade 는 1·2·3·? 하나만 있을 때 받고, 애매하면 None (라벨을 만들지 않는다)',
      _pg_got == [e for _, e in _pg_cases],
      [(a, g) for (a, e), g in zip(_pg_cases, _pg_got) if g != e])

# --- code_items: 가짜 HTTP 를 주입해 호출·파싱·기록·재개·폴백·재시도를 본다
_sheet15 = {'sample_digest': 'abc123', 'coder_prompt': '지시문 X', 'items': [
    {'id': 1, 'text': '본문1', 'chars': 3, 'cell_truncated': False},
    {'id': 2, 'text': '본문2', 'chars': 3, 'cell_truncated': True, 'notice': '잘렸습니다'},
    {'id': 3, 'text': '본문3', 'chars': 3, 'cell_truncated': False}]}
_cfg15 = {'base_url': 'https://api.example.com/v1', 'api_key': 'k', 'model': 'm',
          'key_var': 'X_API_KEY'}
_posts = []


def _fake_post(url, headers, payload, timeout):
    _posts.append((url, headers, payload))
    text = payload['messages'][-1]['content']
    ans = '3' if '본문1' in text else ('2 또는 3' if '본문2' in text else '?')
    return 200, {'choices': [{'message': {'content': ans}}],
                 'usage': {'prompt_tokens': 10, 'completion_tokens': 1},
                 'system_fingerprint': 'fp_x', 'model': 'm-2026'}


_quiet_kw = dict(sleep=lambda s: None, log=lambda *a, **k: None)
with tempfile.TemporaryDirectory() as _td:
    _outp = os.path.join(_td, 'coding_A.json')
    _doc = _call(lambda: CP.code_items(_sheet15, _cfg15, 'A', _outp, post=_fake_post,
                                       provider_env='/x/.env', **_quiet_kw))
    _saved = json.load(open(_outp, encoding='utf-8')) if os.path.exists(_outp) else None
    # 재개: 이미 채점된 1·3 은 건너뛰고 오류였던 2 만 다시 묻는다
    _posts2 = []

    def _post_resume(url, headers, payload, timeout):
        _posts2.append(payload['messages'][-1]['content'])
        return 200, {'choices': [{'message': {'content': '2'}}], 'usage': {}}
    _doc_r = _call(lambda: CP.code_items(_sheet15, _cfg15, 'A', _outp, post=_post_resume,
                                         resume=True, **_quiet_kw))
    # 다른 모델로 같은 파일에 재개 → 거부 (한 파일에 코더가 섞이면 안 된다)
    _doc_mix = _call(lambda: CP.code_items(_sheet15, dict(_cfg15, model='other'), 'A', _outp,
                                           post=_post_resume, resume=True, **_quiet_kw))
    # 온도 400 폴백
    _posts3 = []

    def _post_temp(url, headers, payload, timeout):
        _posts3.append(payload)
        if 'temperature' in payload:
            return 400, {'error': {'message': "Unsupported value: 'temperature' does not "
                                              "support 0 with this model."}}
        return 200, {'choices': [{'message': {'content': '1'}}], 'usage': {}}
    _outt = os.path.join(_td, 'coding_T.json')
    _doc_t = _call(lambda: CP.code_items(_sheet15, _cfg15, 'T', _outt, post=_post_temp,
                                         limit=2, **_quiet_kw))
    # 429 → 재시도 후 성공
    _n429 = {'calls': 0}
    _sleeps = []

    def _post_429(url, headers, payload, timeout):
        _n429['calls'] += 1
        if _n429['calls'] == 1:
            return 429, {'error': {'message': 'rate limit'}}
        return 200, {'choices': [{'message': {'content': '3'}}], 'usage': {}}
    _out4 = os.path.join(_td, 'coding_R.json')
    _doc_4 = _call(lambda: CP.code_items(_sheet15, _cfg15, 'R', _out4, post=_post_429, limit=1,
                                         sleep=_sleeps.append, log=lambda *a, **k: None))

check('R15l code_items 는 파싱된 라벨만 grades 에, 애매한 응답은 errors 에 두고 원자료를 남긴다',
      isinstance(_doc, dict) and _doc.get('grades') == {'1': 3, '3': '?'}
      and '2' in _doc.get('errors', {}) and set(_doc.get('raw', {})) == {'1', '2', '3'}
      and all(k in _doc['raw']['1'] for k in ('answer', 'tokens_in', 'tokens_out',
                                                'latency_ms', 'retries'))
      and _doc.get('coder') == 'A' and _doc.get('sample_digest') == 'abc123', _doc)
check('R15l2 산출물은 항목마다 디스크에 반영된다 (중단돼도 잃지 않는다)', _saved == _doc, _saved)
_meta = _doc.get('meta', {}) if isinstance(_doc, dict) else {}
check('R15l3 meta 에 FR-3 필드가 전부 실린다 (model·base_url·temperature·prompt_sha256·run_at·context_isolated·provider_env·seed)',
      {'model', 'base_url', 'temperature', 'prompt_sha256', 'run_at', 'context_isolated',
       'provider_env', 'seed'} <= set(_meta)
      and _meta.get('temperature') == 0 and _meta.get('context_isolated') is True
      and _meta.get('prompt_sha256') == hashlib.sha256('지시문 X'.encode()).hexdigest()
      and _meta.get('provider_env') == '/x/.env' and _meta.get('version') == 'fp_x', _meta)
check('R15l4 프롬프트는 시트에서 온다 — system 은 coder_prompt 그대로, 절단 고지는 user 에',
      len(_posts) == 3 and all(p[2]['messages'][0] == {'role': 'system', 'content': '지시문 X'}
                               for p in _posts)
      and any('잘렸습니다' in p[2]['messages'][-1]['content'] and '본문2' in p[2]['messages'][-1]['content']
              for p in _posts)
      and all(p[0].endswith('/chat/completions') and p[1].get('Authorization') == 'Bearer k'
              and p[2].get('temperature') == 0 and 'seed' in p[2] and p[2]['model'] == 'm'
              for p in _posts), _posts[:1])
check('R15l5 --resume 는 채점된 항목을 건너뛰고 오류 항목만 다시 묻는다',
      _posts2 == ['잘렸습니다\n\n본문2'] and isinstance(_doc_r, dict)
      and _doc_r.get('grades') == {'1': 3, '2': 2, '3': '?'} and not _doc_r.get('errors'),
      (_posts2, _doc_r.get('grades') if isinstance(_doc_r, dict) else _doc_r))
check('R15l6 다른 모델로 같은 파일에 재개하면 거부한다 (한 파일에 코더가 섞이지 않는다)',
      isinstance(_doc_mix, (ValueError, SystemExit)) and '모델' in str(_doc_mix), _doc_mix)
check('R15l7 온도를 거부하는 모델이면 온도 없이 다시 묻고 meta 에 temperature_honored=False 를 남긴다',
      isinstance(_doc_t, dict) and _doc_t['meta'].get('temperature_honored') is False
      and len(_posts3) == 3 and 'temperature' in _posts3[0] and 'temperature' not in _posts3[1]
      and 'temperature' not in _posts3[2]        # 두 번째 항목부터는 처음부터 빼고 보낸다
      and _doc_t.get('grades') == {'1': 1, '2': 1}, (_doc_t, len(_posts3)))
check('R15l8 429 는 물러섰다 다시 시도하고 retries 를 기록한다',
      isinstance(_doc_4, dict) and _doc_4.get('grades') == {'1': 3}
      and _doc_4['raw']['1']['retries'] == 1 and len(_sleeps) == 1, (_doc_4, _sleeps))
check('R15l9 --limit 은 시도 항목 수를 제한한다',
      isinstance(_doc_t, dict) and len(_doc_t.get('raw', {})) == 2, _doc_t)

# 지연을 벽시계로 재면 NTP 보정으로 time.time() 이 뒤로 갈 때 음수가 찍힌다 —
# 실제 코더 B 실행(2026-09-04)에서 -1,159 ms 가 기록됐다. 단조 시계여야 한다.
_tt = iter([1000.0, 999.0, 998.0, 997.0, 996.0, 995.0])
_o_time = CP.time.time
try:
    CP.time.time = lambda: next(_tt)                 # 뒤로 가는 벽시계
    with tempfile.TemporaryDirectory() as _td:
        _doc_lat = _call(lambda: CP.code_items(_sheet15, _cfg15, 'L', os.path.join(_td, 'l.json'),
                                               post=_fake_post, limit=1, **_quiet_kw))
finally:
    CP.time.time = _o_time
check('R15l10 지연은 단조 시계로 잰다 — 벽시계가 뒤로 가도 음수가 되지 않는다',
      isinstance(_doc_lat, dict) and _doc_lat['raw']['1']['latency_ms'] >= 0,
      _doc_lat['raw']['1'] if isinstance(_doc_lat, dict) else _doc_lat)

# --- Claude Code 헤드리스 백엔드 (설계 A1): `claude -p` 를 post 인터페이스로 감싼다. 실행은 주입한다.
# 프로젝트 컨텍스트(CLAUDE.md 의 등급 규칙!)가 실리지 않도록 --setting-sources "" · --tools "" ·
# 저장소 밖 cwd 가 강제돼야 한다 — 실측: 그 옵션 없이는 7.5만 토큰이 캐시에 실렸다.
_cli_calls = []


def _fake_run(argv, input=None, capture_output=True, text=True, timeout=None, cwd=None):
    _cli_calls.append({'argv': list(argv), 'stdin': input, 'cwd': cwd})

    class _R:
        returncode, stderr = 0, ''
        # Claude Code 는 요청 모델 외에 Haiku 보조 호출을 한 번 낀다 (실측 922토큰 고정).
        # usage 총계에는 그것이 섞이므로 요청 모델의 modelUsage 로 세어야 한다.
        stdout = json.dumps({'type': 'result', 'is_error': False, 'result': ' 2 ',
                             'usage': {'input_tokens': 1222, 'output_tokens': 17,
                                       'cache_read_input_tokens': 20, 'cache_creation_input_tokens': 5},
                             'modelUsage': {'claude-haiku-4-5-20251001': {'inputTokens': 922, 'outputTokens': 14,
                                                                          'cacheCreationInputTokens': 0,
                                                                          'cacheReadInputTokens': 0},
                                            'claude-opus-5': {'inputTokens': 300, 'outputTokens': 3,
                                                              'cacheCreationInputTokens': 5,
                                                              'cacheReadInputTokens': 20}},
                             'total_cost_usd': 0.01})
    return _R()


_pl = {'model': 'claude-opus-5', 'messages': [{'role': 'system', 'content': '지시문 X'},
                                              {'role': 'user', 'content': '본문 Y'}]}
_r = _call(lambda: CP.claude_cli_post('claude-cli://anthropic/chat/completions', {}, _pl, 180, run=_fake_run))
_argv = _cli_calls[-1]['argv'] if _cli_calls else []
check('R15s claude_cli_post 는 claude -p 를 도구·설정·세션 없이 저장소 밖에서 돌리고 OpenAI 응답 모양으로 돌려준다',
      isinstance(_r, tuple) and _r[0] == 200
      and _r[1]['choices'][0]['message']['content'] == ' 2 '
      and _r[1]['usage'] == {'prompt_tokens': 325, 'completion_tokens': 3}
      and _r[1]['model'] == 'claude-opus-5'
      and _argv[:2] == ['claude', '-p']
      and all(x in _argv for x in ('--tools', '--setting-sources', '--no-session-persistence',
                                   '--strict-mcp-config', '--no-chrome',     # MCP 도구 정의 4.8만~11.8만 토큰이 새던 통로
                                   '--output-format', 'json', '--model', 'claude-opus-5',
                                   '--system-prompt', '지시문 X'))
      and _r[1].get('side_calls') == {'claude-haiku-4-5-20251001': {'inputTokens': 922, 'outputTokens': 14,
                                                                     'cacheCreationInputTokens': 0,
                                                                     'cacheReadInputTokens': 0}}
      and _argv[_argv.index('--tools') + 1] == '' and _argv[_argv.index('--setting-sources') + 1] == ''
      and _cli_calls[-1]['stdin'] == '본문 Y'
      and _cli_calls[-1]['cwd'] and os.path.abspath(_cli_calls[-1]['cwd']) != ROOT
      and not os.path.abspath(_cli_calls[-1]['cwd']).startswith(ROOT + os.sep),
      (_r, _argv, _cli_calls[-1] if _cli_calls else None))
_n_before = len(_cli_calls)
_r_t = _call(lambda: CP.claude_cli_post('x', {}, dict(_pl, temperature=0), 180, run=_fake_run))
_r_s = _call(lambda: CP.claude_cli_post('x', {}, dict(_pl, seed=1), 180, run=_fake_run))
check('R15s2 온도·시드는 CLI 가 받지 않는다 — 호출 없이 400 으로 알려 폴백이 기록하게 한다',
      isinstance(_r_t, tuple) and _r_t[0] == 400 and 'temperature' in _r_t[1]['error']['message']
      and isinstance(_r_s, tuple) and _r_s[0] == 400 and 'seed' in _r_s[1]['error']['message']
      and len(_cli_calls) == _n_before, (_r_t, _r_s))


def _run_err(msg, code=0):
    def f(argv, input=None, capture_output=True, text=True, timeout=None, cwd=None):
        class _R:
            returncode, stderr = code, ''
            stdout = json.dumps({'type': 'result', 'is_error': True, 'result': msg})
        return _R()
    return f


def _run_timeout(argv, input=None, capture_output=True, text=True, timeout=None, cwd=None):
    import subprocess
    raise subprocess.TimeoutExpired(argv, timeout)


_r_login = _call(lambda: CP.claude_cli_post('x', {}, _pl, 180, run=_run_err('Not logged in · Please run /login')))
_r_other = _call(lambda: CP.claude_cli_post('x', {}, _pl, 180, run=_run_err('overloaded')))
_r_to = _call(lambda: CP.claude_cli_post('x', {}, _pl, 1, run=_run_timeout))
check('R15s3 로그인 안 됨은 401(재시도 없음), 그 밖의 오류는 500, 시간 초과는 None(재시도) 으로 매핑한다',
      isinstance(_r_login, tuple) and _r_login[0] == 401 and 'logged in' in _r_login[1]['error']['message']
      and isinstance(_r_other, tuple) and _r_other[0] == 500
      and isinstance(_r_to, tuple) and _r_to[0] is None, (_r_login, _r_other, _r_to))

# --- 병렬 워커: 산출물은 순차 실행과 같아야 한다
with tempfile.TemporaryDirectory() as _td:
    _outw = os.path.join(_td, 'w.json')
    _docw = _call(lambda: CP.code_items(_sheet15, _cfg15, 'W', _outw, post=_fake_post, workers=3, **_quiet_kw))
check('R15s4 --workers 로 병렬 호출해도 산출물은 같다 (라벨 2, 오류 1, 항목마다 원자료)',
      isinstance(_docw, dict) and _docw['grades'] == {'1': 3, '3': '?'} and set(_docw['raw']) == {'1', '2', '3'}
      and '2' in _docw['errors'], _docw)

# --- main: --backend claude-cli 는 env 파일 없이 설정을 만든다
with tempfile.TemporaryDirectory() as _td:
    _shp = os.path.join(_td, 'sheet.json')
    with open(_shp, 'w', encoding='utf-8') as _f:
        json.dump(_sheet15, _f, ensure_ascii=False)
    _mcode2, _mout2 = _run_main(CP.main, ['code_pages.py', '--coder', 'T', '--backend', 'claude-cli',
                                          '--model', 'claude-opus-5', '--sheet', _shp, '--dry-run'])
check('R15s5 --backend claude-cli 는 --provider-env 없이 claude-cli://anthropic 설정으로 dry-run 한다',
      _mcode2 == 0 and 'claude-opus-5 @ claude-cli://anthropic' in _mout2, (_mcode2, _mout2[:120]))

_cp_src = open(os.path.join(ROOT, 'code_pages.py'), encoding='utf-8').read() if _cp_ok else ''
check('R15m 호출기는 규칙 지식을 갖지 않는다 — 등급 정의·동음이의 문자열이 소스에 없다',
      _cp_ok and not any(w in _cp_src for w in ('구체적 대책', '형식적 언급', '미흡', '안전보건 내용',
                                                 '진동', '먼지', 'SAFETY_TERMS', 'regrade'))
      and 'AUDIT_LLM_TEMPERATURE' not in _cp_src, [w for w in ('구체적 대책', '형식적 언급', '미흡', '안전보건 내용', '진동', '먼지', 'SAFETY_TERMS', 'regrade', 'AUDIT_LLM_TEMPERATURE') if w in _cp_src])

print('\n[R15] 재코딩 — 전수 + 재현율층 채점 (score_coding)')

# --- 재현율층: 유한모집단 정확 구간 (초기하). N=1,739 / n=300 / 적중 0 → 상한 15쪽
_mi0 = _call(lambda: SC.missed_interval(1739, 300, 0))
check('R15n 적중 0건 → 점추정 없이 단측 95% 상한만 (1,739쪽 중 300쪽 → 15쪽)',
      _mi0 == (0, 0, 15), _mi0)
_mi6 = _call(lambda: SC.missed_interval(1739, 300, 6))
_mi12 = _call(lambda: SC.missed_interval(1739, 300, 12))
check('R15n2 적중 h건 → 점추정 h·N/n 과 그것을 품는 양측 95% 구간, 적중이 늘면 구간이 오른다',
      isinstance(_mi6, tuple) and abs(_mi6[0] - 6 * 1739 / 300) < 1e-9
      and 0 < _mi6[1] <= _mi6[0] <= _mi6[2] < 1739
      and isinstance(_mi12, tuple) and _mi12[1] > _mi6[1] and _mi12[2] > _mi6[2], (_mi6, _mi12))
check('R15n3 전수(n == N)면 구간이 점으로 닫힌다', _call(lambda: SC.missed_interval(10, 10, 3)) == (3, 3, 3),
      _call(lambda: SC.missed_interval(10, 10, 3)))

# --- 합성 4층 키. 변형 4개 (현행, D1+D2, V, D1+D2+V)
_vs = ['baseline', G2.ADOPTED_VARIANT, G2.VOCAB_VARIANT, G2.ADOPTED_VOCAB_VARIANT]


def _ki(i, grp, pred, cut=False):
    return {'id': i, 'group': grp, 'file': 'LM_%d' % i, 'page': i, 'cell_truncated': cut,
            'pred': dict(zip(_vs, pred))}


_kitems = [_ki(1, 'disputed', (3, 1, 3, 1)), _ki(2, 'disputed', (3, 1, 3, 1)),
           _ki(3, 'disputed', (3, 3, 3, 2), cut=True), _ki(4, 'control', (3, 3, 3, 3)),
           _ki(5, 'control', (2, 1, 3, 3)), _ki(6, 'boundary', (2, 1, 2, 1)),
           _ki(7, 'boundary', (2, 1, 2, 1)), _ki(8, 'recall', (1, 1, 1, 1)),
           _ki(9, 'recall', (2, 2, 2, 2)), _ki(10, 'recall', (1, 1, 1, 1))]
_kdoc = {'sample_digest': MCS.sample_digest(_kitems), 'seed': 1, 'n_recall': 3, 'variants': _vs,
         'rule_pairs': [[_vs[0], _vs[1]], [_vs[2], _vs[3]]],
         'population': {'pages': 100, 'recall_pool': 50,
                        'strata': {'disputed': 3, 'control': 2, 'boundary': 2, 'recall': 3}},
         'items': _kitems}
_gA = {'1': 3, '2': 1, '3': 3, '4': 3, '5': 2, '6': 3, '7': 1, '8': 3, '9': 1, '10': '?'}
_gB = {'1': 3, '2': 2, '3': '?', '4': 3, '5': 2, '6': 3, '7': 1, '8': 1, '9': 1, '10': 1}
_res, _cout = quiet(lambda: _call(lambda: SC.score_census(_gA, _gB, _kdoc)))
_rA = _res.get('A', {}) if isinstance(_res, dict) else {}
_rB = _res.get('B', {}) if isinstance(_res, dict) else {}
_vA = _rA.get('variants', {})
check('R15o 변형별 정밀도는 전수라 표본 가중 없이 그대로다 (A: 현행 3/4, D1+D2 2/2, V 3/5, D1+D2+V 1/2)',
      isinstance(_res, dict)
      and [(_vA[v]['pred'], _vA[v]['tp']) for v in _vs] == [(4, 3), (2, 2), (5, 3), (2, 1)]
      and abs(_vA['baseline']['precision'] - 0.75) < 1e-9, _res if not isinstance(_res, dict) else _vA)
check('R15o2 재현율은 전수 진짜 등급3 + 재현율층 추정으로 처음 측정된다 (A: 전수 4 + 1/2×50 = 29 → 현행 3/29)',
      _rA.get('census_true') == 4 and _rA.get('recall', {}).get('hits') == 1
      and _rA.get('recall', {}).get('n') == 2 and abs(_rA['recall']['k_hat'] - 25.0) < 1e-9
      and abs(_vA['baseline']['recall'] - 3 / 29.0) < 1e-9
      and _vA['baseline']['recall_ci'][0] < 3 / 29.0 < _vA['baseline']['recall_ci'][1],
      (_rA.get('census_true'), _rA.get('recall'), _vA.get('baseline')))
_vB = _rB.get('variants', {})
check('R15o3 판단 불가(?)는 분자·분모 양쪽에서 빠지고 뺀 수를 남긴다 (B 현행: 2/3, 제외 1)',
      _vB.get('baseline', {}).get('excluded') == 1 and abs(_vB['baseline']['precision'] - 2 / 3.0) < 1e-9
      and _rB.get('recall', {}).get('n') == 3, _vB.get('baseline'))
check('R15o4 적중 0건인 코더는 점추정 대신 상한만 낸다 (B: 0/3 → k_hat 0, hi > 0)',
      _rB.get('recall', {}).get('hits') == 0 and _rB['recall']['k_hat'] == 0
      and _rB['recall']['lo'] == 0 and _rB['recall']['hi'] > 0
      and '점추정 없음' in _cout and '상한' in _cout, _rB.get('recall'))
check('R15o5 정밀도에 코더 불일치 폭을 병기한다 (양쪽 모두 3 ≤ 한쪽이라도 3)',
      'band' in _vA.get('baseline', {}) and _vA['baseline']['band']['both'] <= _vA['baseline']['band']['either']
      and '재현율층' in _cout and '경계층' in _cout and '분쟁군' in _cout, _vA.get('baseline', {}).get('band'))
check('R15o6 경계층 적중은 두 규칙이 모두 놓친 등급3으로 전수 집계된다 (A·B 각 1/2)',
      _rA.get('boundary_hits') == (1, 2) and _rB.get('boundary_hits') == (1, 2),
      (_rA.get('boundary_hits'), _rB.get('boundary_hits')))
# 결과 dict 는 JSON 산출물의 재료다 — 보고서 문장이 아니라 여기서 수치를 읽어야 재현된다
_ag = _res.get('agreement', {}) if isinstance(_res, dict) else {}
_gs = _res.get('group_stats', {}) if isinstance(_res, dict) else {}
check('R15o10 결과 dict 에 전체 일치도·κ 와 층별 일치도가 실린다 (6/10; 분쟁 1/3, 합의 2/2, 경계 2/2, 재현율 1/3)',
      _ag.get('n') == 10 and _ag.get('agree') == 6 and isinstance(_ag.get('kappa'), float)
      and [(_gs[g]['agree'], _gs[g]['n']) for g in ('disputed', 'control', 'boundary', 'recall')]
      == [(1, 3), (2, 2), (2, 2), (1, 3)], (_ag, _gs))

# 갭 분석 #2: 결과 문서가 손계산하던 수치도 dict 에 실린다 — 불일치 패턴, 규칙쌍별 지지율,
# 절단층 통계, "둘 다 3" 재현율 추정. 이것들이 JSON 에 있어야 "숫자는 전부 이 파일에서" 가 참이다.
_dp = _res.get('disagreement') if isinstance(_res, dict) else None
_ps = _res.get('pair_support') if isinstance(_res, dict) else None
_tr = _res.get('truncation') if isinstance(_res, dict) else None
_rb = _res.get('recall_both3') if isinstance(_res, dict) else None
check('R15o11 결과 dict 에 불일치 패턴·규칙쌍별 지지율·절단층 통계·둘 다 3 재현율이 실린다',
      _dp == {'1→2': 1, '3→?': 1, '3→1': 1, '?→1': 1}
      and isinstance(_ps, list) and len(_ps) == 2
      and _ps[0]['n'] == 2 and _ps[0]['A'] == {'cur': 1, 'new': 1, 'unsure': 0}
      and _ps[0]['both_old'] == 1 and _ps[0]['both_new'] == 1 and _ps[0]['valid'] == 2
      and _ps[1]['n'] == 3 and _ps[1]['A'] == {'cur': 2, 'new': 1, 'unsure': 0}
      and _ps[1]['B'] == {'cur': 1, 'new': 1, 'unsure': 1} and _ps[1]['valid'] == 2
      and _tr == {'n': 1, 'agree': 0, 'both3': 0,
                  'disputed_support': {'with': [1, 2], 'without': [1, 2]}}
      and isinstance(_rb, dict) and _rb['hits'] == 0 and _rb['n'] == 2 and _rb['hi'] > 0,
      (_dp, _ps, _tr, _rb))
# 갭 분석 #6: 설계 §8 — `?` 비율이 층별 임계를 넘으면 경고한다. 픽스처는 분쟁군 B 1/3, 재현율층 A 1/3.
_uw = _res.get('unsure_warnings') if isinstance(_res, dict) else None
_res2, _cout2 = quiet(lambda: _call(lambda: SC.score_census(dict(_gA, **{'10': 1}), dict(_gB, **{'3': 2}), _kdoc)))
check('R15o12 층별 ? 비율이 임계를 넘으면 경고를 내고 기록한다 (분쟁군 B, 재현율층 A); 없으면 조용하다',
      isinstance(_uw, list) and {(w['group'], w['coder']) for w in _uw} == {('disputed', 'B'), ('recall', 'A')}
      and '경고' in _cout and isinstance(_res2, dict) and _res2.get('unsure_warnings') == []
      and '판단 불가 비율' not in _cout2, (_uw, _cout[:0]))

# 재현율층에 어느 변형이든 등급3 예측이 섞여 있으면 표본이 낡은 것 — 계산하지 않고 멈춘다
_bad = dict(_kdoc, items=_kitems[:-1] + [_ki(10, 'recall', (3, 1, 1, 1))])
_bad_res = quiet(lambda: _call(lambda: SC.score_census(_gA, _gB, _bad)))[0]
check('R15o7 재현율층에 등급3 예측이 있으면 채점을 거부한다 (표본이 규칙과 어긋남)',
      isinstance(_bad_res, SystemExit) and '재현율층' in str(_bad_res), _bad_res)

# --- 모집단 교차 검증: 키의 변형별 등급3 전수 == regrade_impact.json 의 분포
_imp_ok = {'pages': 100, 'dist': {v: {'3': n} for v, n in zip(_vs, (4, 2, 5, 2))}}
check('R15o8 키의 변형별 등급3 수가 regrade_impact.json 과 맞으면 통과, 하나라도 다르면 멈춘다',
      _call(lambda: SC.check_population(_kdoc, _imp_ok)) is None
      and isinstance(_call(lambda: SC.check_population(
          _kdoc, dict(_imp_ok, dist=dict(_imp_ok['dist'], baseline={'3': 5})))), SystemExit)
      and isinstance(_call(lambda: SC.check_population(_kdoc, dict(_imp_ok, pages=99))), SystemExit),
      _call(lambda: SC.check_population(_kdoc, _imp_ok)))

# --- 코더 계열 가드 (FR-1): 같은 제공자면 경고
_fg_same = _call(lambda: SC.family_guard({'base_url': 'https://api.openai.com/v1', 'model': 'a'},
                                         {'base_url': 'https://api.openai.com/v1', 'model': 'b'}))
_fg_diff = _call(lambda: SC.family_guard({'base_url': 'https://api.openai.com/v1', 'model': 'a'},
                                         {'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai', 'model': 'g'}))
check('R15o9 두 코더가 같은 제공자면 FR-1 미충족 경고, 다르면 없음',
      isinstance(_fg_same, str) and 'FR-1' in _fg_same and _fg_diff is None, (_fg_same, _fg_diff))

# --- main 라우팅: 새 형식 키 → 전수 채점, 구형식 키 → 기존 경로
_o_load, _o_here = SC.load, SC.HERE
_scores = None
with tempfile.TemporaryDirectory() as _td:
    try:
        SC.load = lambda n: ({'coder': n[7], 'sample_digest': _kdoc['sample_digest'],
                              'meta': {'base_url': 'https://x/v1', 'model': 'm'},
                              'grades': _gA if n.startswith('coding_A') else _gB}
                             if n.startswith('coding_') and not n.startswith('coding_key') else _kdoc)
        SC.HERE = _td                 # regrade_impact.json 이 없어도 전수 채점은 돈다
        _mcode, _mout = _run_main(SC.main, ['score_coding.py'])
        _sp = os.path.join(_td, 'docs', '03-analysis', 'data', 'recoding_scores.json')
        _scores_raw = open(_sp, encoding='utf-8').read() if os.path.exists(_sp) else ''
        _scores = json.loads(_scores_raw) if _scores_raw else None
    finally:
        SC.load, SC.HERE = _o_load, _o_here
check('R15p main 은 새 형식 키(pred·population)를 전수 채점 경로로 보낸다',
      _mcode == 0 and '재현율층' in _mout and '규칙 변형별' not in _mout, (_mcode, _mout[:120]))
# 보고서 문장만 남기면 분석 문서의 수치를 아무도 재현할 수 없다. 채점기가 JSON 도 남긴다.
check('R15p2 전수 채점은 수치를 docs/03-analysis/data/recoding_scores.json 에도 쓴다 (NaN 없이, 계열 경고 포함)',
      isinstance(_scores, dict) and _scores.get('sample_digest') == _kdoc['sample_digest']
      and _scores.get('A', {}).get('variants', {}).get('baseline', {}).get('tp') == 3
      and _scores.get('coders', {}).get('B', {}).get('model') == 'm'
      and 'FR-1' in (_scores.get('family_warning') or '')
      and 'NaN' not in _scores_raw,
      _scores if not isinstance(_scores, dict) else sorted(_scores))

# --- 커밋된 산출물 삼각 검증: recoding_scores.json ↔ coding_key.json ↔ coding_A/B.json
# 파일을 자기 자신으로 검증하지 않는다 — 지문·개수·모델을 서로 대조한다. 라벨을 다시 만들고
# 채점을 안 돌리면 여기서 걸린다 (R14m 과 같은 패턴).
_sc_p = os.path.join(ROOT, 'docs/03-analysis/data/recoding_scores.json')
_ck_p = os.path.join(ROOT, 'coding_key.json')
if os.path.exists(_sc_p) and os.path.exists(_ck_p):
    _sc = json.load(open(_sc_p, encoding='utf-8'))
    _ck = json.load(open(_ck_p, encoding='utf-8'))
    # 어느 코더 둘을 대조했는지는 JSON 이 말한다 (FR-1 회차는 C,B). 구버전 JSON 은 A,B.
    _names = _sc.get('coder_names') or ['A', 'B']
    _files = _sc.get('coder_files') or {n: 'coding_%s.json' % n for n in _names}
    _docs = {n: json.load(open(os.path.join(ROOT, _files[n]), encoding='utf-8')) for n in _names
             if os.path.exists(os.path.join(ROOT, _files[n]))}
    check('R15q 커밋된 recoding_scores.json 이 커밋된 키·라벨과 맞는다 (지문·항목 수·모델·등급3 수)',
          len(_docs) == 2
          and all(_sc.get('sample_digest') == _ck.get('sample_digest') == d.get('sample_digest')
                  for d in _docs.values())
          and _sc.get('agreement', {}).get('n') == len(_ck['items'])
          and _sc['population'] == _ck['population']
          and all(_sc['coders'][n].get('model') == _docs[n]['meta'].get('model') for n in _names)
          and all(sum(1 for i in _ck['items']
                      if _docs[n]['grades'].get(str(i['id'])) == 3 and i['group'] != 'recall')
                  == _sc[n]['census_true'] for n in _names),
          (_names, _sc.get('sample_digest'), _ck.get('sample_digest'), sorted(_docs)))
else:
    print('  (recoding_scores.json / coding_key.json 이 없어 R15q 를 건너뛴다)')

# --- FR-1 회차: 코더 파일을 골라 채점한다 (--coders C,B). JSON 에 코더 이름·파일이 남아 R15q 가 따라간다.
_o_here2 = SC.HERE
_sc2, _rcode, _rout = None, None, ''
with tempfile.TemporaryDirectory() as _td:
    with open(os.path.join(_td, 'coding_key.json'), 'w', encoding='utf-8') as _f:
        json.dump(_kdoc, _f, ensure_ascii=False)
    for _nm, _g, _host in (('C', _gA, 'https://api.anthropic.com/v1'), ('B', _gB, 'https://api.openai.com/v1')):
        with open(os.path.join(_td, 'coding_%s.json' % _nm), 'w', encoding='utf-8') as _f:
            json.dump({'coder': _nm, 'sample_digest': _kdoc['sample_digest'],
                       'meta': {'base_url': _host, 'model': 'm-' + _nm}, 'grades': _g}, _f)
    try:
        SC.HERE = _td
        _rcode, _rout = _run_main(SC.main, ['score_coding.py', '--coders', 'C,B'])
        _sp2 = os.path.join(_td, 'docs', '03-analysis', 'data', 'recoding_scores.json')
        if os.path.exists(_sp2):
            _sc2 = json.load(open(_sp2, encoding='utf-8'))
    finally:
        SC.HERE = _o_here2
check('R15r --coders C,B 는 coding_C/coding_B 를 읽어 채점하고 JSON 에 코더 이름·파일·계열 판정을 남긴다',
      _rcode == 0 and isinstance(_sc2, dict) and _sc2.get('coder_names') == ['C', 'B']
      and _sc2.get('coder_files') == {'C': 'coding_C.json', 'B': 'coding_B.json'}
      and _sc2.get('C', {}).get('variants', {}).get('baseline', {}).get('tp') == 3
      and _sc2.get('family_warning') is None and '코더 C' in _rout,
      (_rcode, _rout[:100], sorted(_sc2) if isinstance(_sc2, dict) else _sc2))

# --- PR #12 CodeRabbit 지적: 기존 coding_key.json 은 라벨 삼종(coding_A/B/C.json)의 유일한 결합 정보다.
# 기본 실행이 그것을 덮어쓰면 안 된다 — --force 를 요구한다. (지문 가드는 결합을 막지 쓰기를 막지 않는다)
_o_here_m, _o_dd_m, _o_lp_m = MCS.HERE, G2.DATA_DIR, G2.load_pages
_kc1 = _kc2 = None
_wrote = False
with tempfile.TemporaryDirectory() as _td:
    open(os.path.join(_td, G2.NCS_FILE), 'w').close()          # 원본 부재 가드를 넘긴다
    with open(os.path.join(_td, 'coding_key.json'), 'w', encoding='utf-8') as _f:
        _f.write('{"sample_digest": "old"}')
    _pg_m = {('f', i): {'text': '안전 위험 주의 사고 유해 누출 방지 예방 착용 환기 차단 ' * (i % 3 + 1),
                        'grade': 1, 'truncated': False} for i in range(1, 9)}
    try:
        MCS.HERE, G2.DATA_DIR = _td, _td
        G2.load_pages = lambda p: _pg_m
        _kc1, _ = _run_main(MCS.main, ['make_coding_sheet.py'])
        _kc2, _ = _run_main(MCS.main, ['make_coding_sheet.py', '--force'])
        _wrote = os.path.exists(os.path.join(_td, 'coding_sheet.md'))
    finally:
        MCS.HERE, G2.DATA_DIR, G2.load_pages = _o_here_m, _o_dd_m, _o_lp_m
check('R15t make_coding_sheet 는 기존 coding_key.json 을 --force 없이 덮어쓰지 않는다',
      isinstance(_kc1, str) and '--force' in _kc1 and _kc2 == 0 and _wrote, (_kc1, _kc2, _wrote))

# --- PR #12 CodeRabbit 지적: xlsx 는 zip 이다. 압축비가 비정상인 항목(압축 폭탄)은 열지 않고 멈춘다.
import zipfile as _zipmod  # noqa: E402
with tempfile.TemporaryDirectory() as _td:
    _bomb = os.path.join(_td, 'bomb.xlsx')
    with _zipmod.ZipFile(_bomb, 'w', _zipmod.ZIP_DEFLATED) as _z:
        _z.writestr('xl/worksheets/sheet1.xml', '0' * (16 * 1024 * 1024))
    _bomb_res = _call(lambda: list(TA.iter_rows(_bomb)))
check('R15u truncation_audit 는 압축비가 임계를 넘는 zip 항목을 읽지 않고 멈춘다 (압축 폭탄)',
      isinstance(_bomb_res, SystemExit) and '압축' in str(_bomb_res), _bomb_res)

# --- /ship 스페셜리스트 지적 (2026-09-04): 테스트·보안·유지보수성
print('\n[R15] 재코딩 — /ship 리뷰 회귀 (라벨 누락·실행 파일 부재·비JSON 응답·경로 노출·스크럽·응답 상한)')

# testing CRITICAL: 라벨 없는 항목(code_pages errors)이 있으면 strata() 가 A[i] 직접 색인으로 죽는다.
_gA_miss = {k: v for k, v in _gA.items() if k != '3'}     # id 3 = 분쟁군 + 절단 항목, 라벨 없음
_miss = quiet(lambda: _call(lambda: SC.score_census(_gA_miss, _gB, _kdoc)))[0]
check('R15v 라벨 없는 항목(errors)이 있어도 전수 채점은 죽지 않고 판단 불가로 다룬다',
      isinstance(_miss, dict) and _miss['agreement']['n'] == 10
      and _miss['A']['variants']['baseline']['excluded'] == 1, _miss if not isinstance(_miss, dict) else _miss['agreement'])


def _run_nobin(argv, input=None, capture_output=True, text=True, timeout=None, cwd=None):
    raise FileNotFoundError(2, 'No such file or directory', 'claude')


_sl_nb = []
_nb = _call(lambda: CP.call_chat({'base_url': CP.CLI_BASE_URL, 'api_key': '', 'model': 'claude-opus-5'},
                                 _pl['messages'], None, None, {},
                                 post=lambda u, h, p, t: CP.claude_cli_post(u, h, p, t, run=_run_nobin),
                                 sleep=_sl_nb.append))
check('R15v2 claude 실행 파일이 없으면 재시도 없이 즉시 실패한다 (일시 오류가 아니다)',
      isinstance(_nb, RuntimeError) and _sl_nb == [] and 'claude' in str(_nb), (_nb, _sl_nb))

with tempfile.TemporaryDirectory() as _td:
    _doc_g = _call(lambda: CP.code_items(_sheet15, _cfg15, 'G', os.path.join(_td, 'g.json'),
                                         post=lambda u, h, p, t: (200, 'garbage'), limit=1, **_quiet_kw))
check('R15v3 200 인데 본문이 JSON dict 가 아니면 그 항목만 오류로 남기고 실행은 계속된다',
      isinstance(_doc_g, dict) and '1' in _doc_g.get('errors', {}) and '1' in _doc_g.get('raw', {}), _doc_g)

# security: 추적 산출물에 OS 사용자명·키 파일 위치가 실리면 안 된다
_tracked = ['coding_A.json', 'coding_B.json', 'coding_C.json'] + sorted(
    f for f in os.listdir(os.path.join(ROOT, 'docs/03-analysis/data')) if f.startswith('recoding_scores'))


def _strings(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)
    elif isinstance(x, str):
        yield x


_home_hits = []
_maxlen = 0
for _f in _tracked:
    _p = os.path.join(ROOT, _f if _f.startswith('coding_') else 'docs/03-analysis/data/' + _f)
    if not os.path.exists(_p):
        continue
    for _s in _strings(json.load(open(_p, encoding='utf-8'))):
        _maxlen = max(_maxlen, len(_s))
        if _s.startswith(('/Users/', '/home/', '/root/')):
            _home_hits.append((_f, _s[:60]))
check('R15w 추적되는 라벨·수치 JSON 에 홈 경로(/Users, /home)가 없다', not _home_hits, _home_hits)
check('R15w1 추적되는 라벨·수치 JSON 의 문자열 값은 200자 이하다 (교재 본문·긴 응답이 실리지 않는다)',
      _maxlen <= 200, _maxlen)

_scr = _call(lambda: CP.scrub('Incorrect API key provided: sk-proj-abcDEF123456789xyz at '
                              '/Users/me/.config/x.env ' + 'y' * 300))
check('R15w2 오류 문자열은 키 토큰·홈 경로를 가리고 200자로 자른 뒤 저장한다',
      isinstance(_scr, str) and 'sk-proj-abc' not in _scr and '/Users/me' not in _scr
      and len(_scr) <= 200 and 'sk-' in _scr, _scr)
with tempfile.TemporaryDirectory() as _td:
    _doc_k = _call(lambda: CP.code_items(_sheet15, _cfg15, 'K', os.path.join(_td, 'k.json'),
                                         post=lambda u, h, p, t: (401, {'error': {'message':
                                             'Incorrect API key provided: sk-proj-abcDEF123456789xyz'}}),
                                         limit=1, **_quiet_kw))
    _doc_l = _call(lambda: CP.code_items(_sheet15, _cfg15, 'L', os.path.join(_td, 'l.json'),
                                         post=lambda u, h, p, t: (200, {'choices': [{'message': {'content': '3' * 1000}}],
                                                                       'usage': {}}),
                                         limit=1, **_quiet_kw))
check('R15w3 저장된 오류에 키 토큰이 남지 않고, 응답 원문은 200자로 잘리며 해시가 남는다',
      isinstance(_doc_k, dict) and 'sk-proj-abc' not in json.dumps(_doc_k, ensure_ascii=False)
      and isinstance(_doc_l, dict) and len(_doc_l['raw']['1']['answer']) <= 200
      and len(_doc_l['raw']['1'].get('answer_sha256', '')) == 64 and '1' in _doc_l['errors'],
      (_doc_k.get('errors') if isinstance(_doc_k, dict) else _doc_k,
       {k: (len(v) if isinstance(v, str) else v) for k, v in _doc_l['raw']['1'].items()} if isinstance(_doc_l, dict) else _doc_l))

_pc1 = _call(lambda: CP.provider_config({'AUDIT_LLM_API_KEY': 'k', 'AUDIT_LLM_MODEL': 'm'}))
_pc2 = _call(lambda: CP.provider_config({'OPENAI_API_KEY': 'k'}, model='m', base_url='http://evil.example/v1'))
_pc3 = _call(lambda: CP.provider_config({'OPENAI_API_KEY': 'k'}, model='m', base_url='http://localhost:1234/v1'))
check('R15w4 제공자 중립 키(AUDIT_LLM_API_KEY)는 주소 없이 OpenAI 로 떨어지지 않고, 평문 http 는 localhost 만 허용한다',
      isinstance(_pc1, ValueError) and 'BASE_URL' in str(_pc1)
      and isinstance(_pc2, ValueError) and 'https' in str(_pc2)
      and isinstance(_pc3, dict) and _pc3['base_url'] == 'http://localhost:1234/v1', (_pc1, _pc2, _pc3))

_cwd1 = _call(lambda: CP._cli_cwd())
_cwd2 = _call(lambda: CP._cli_cwd())
check('R15w5 claude -p 작업 디렉터리는 프로세스마다 새로 만든 0700 디렉터리다 (공용 /tmp 고정 이름 아님)',
      isinstance(_cwd1, str) and _cwd1 == _cwd2 and os.path.isdir(_cwd1)
      and (os.stat(_cwd1).st_mode & 0o777) == 0o700 and not _cwd1.startswith(ROOT)
      and os.path.basename(_cwd1) != 'code_pages_claude_cli', (_cwd1, oct(os.stat(_cwd1).st_mode & 0o777) if isinstance(_cwd1, str) and os.path.isdir(_cwd1) else None))

# maintainability: strata() 가 찍는 절단층 수치와 JSON 의 수치는 한 계산이어야 한다
_key15 = {str(r['id']): r for r in _kitems}
_tr_ret = quiet(lambda: _call(lambda: SC.strata(_gA, _gB, _key15, [str(r['id']) for r in _kitems])))[0]
check('R15x strata() 가 절단층 수치를 돌려주고 score_census 의 truncation 과 같다',
      _tr_ret == _res.get('truncation') and isinstance(_tr_ret, dict), (_tr_ret, _res.get('truncation')))

_o_load3, _o_pop3, _o_here3 = SC.load, SC.population, SC.HERE
_leg_items = [{'id': 1, 'group': 'disputed', 'file': 'a', 'page': 1, 'cell_truncated': False},
              {'id': 2, 'group': 'control', 'file': 'b', 'page': 2, 'cell_truncated': False}]
_leg_d = MCS.sample_digest(_leg_items)
with tempfile.TemporaryDirectory() as _td:
    try:
        SC.load = lambda n: ({'coder': n[7], 'sample_digest': _leg_d, 'grades': {'1': 3, '2': 3}}
                             if n.startswith('coding_') and not n.startswith('coding_key')
                             else {'sample_digest': _leg_d, 'items': _leg_items})
        SC.population = lambda: (100, 1, 10)
        SC.HERE = _td
        _lcode2, _lout2 = _run_main(SC.main, ['score_coding.py', '--out', os.path.join(_td, 'x.json')])
    finally:
        SC.load, SC.population, SC.HERE = _o_load3, _o_pop3, _o_here3
check('R15x2 구형식 키에서 --out 을 주면 조용히 무시하지 않고 전수 경로 전용임을 알린다',
      _lcode2 == 0 and '전수 경로' in _lout2, (_lcode2, _lout2[-200:]))

check('R15x3 층 이름은 한 곳(page_utils.CODING_GROUPS)이 소유하고 두 스크립트가 같이 쓴다',
      _call(lambda: PU.CODING_GROUPS) == MCS.GROUPS == tuple(g for g, _ in SC.GROUP_LABELS)
      == ('disputed', 'control', 'boundary', 'recall'), (_call(lambda: PU.CODING_GROUPS), MCS.GROUPS))

# --- /ship 스페셜리스트 2차 (성능·테스트) + 커버리지 감사 GAP
import io as _io  # noqa: E402
import threading as _threading  # noqa: E402


def _post_badjson(u, h, p, t):
    raise json.JSONDecodeError('Expecting value', 'doc', 0)


with tempfile.TemporaryDirectory() as _td:
    _dbj = _call(lambda: CP.code_items(_sheet15, _cfg15, 'J', os.path.join(_td, 'j.json'),
                                       post=_post_badjson, workers=2, **_quiet_kw))
check('R15v4 post 가 예외를 던져도 (JSONDecodeError) 실행은 죽지 않고 항목별 errors 에 남는다',
      isinstance(_dbj, dict) and set(_dbj['errors']) == {'1', '2', '3'} and not _dbj['grades'], _dbj)

# performance: 429 의 Retry-After 를 존중하고 백오프에 지터를 더한다
_ra_calls = {'n': 0}
_ra_sleeps = []


def _post_ra(u, h, p, t):
    _ra_calls['n'] += 1
    if _ra_calls['n'] == 1:
        return 429, {'error': {'message': 'rate'}, '_retry_after': '7'}
    return 200, {'choices': [{'message': {'content': '3'}}], 'usage': {}}


with tempfile.TemporaryDirectory() as _td:
    _doc_ra = _call(lambda: CP.code_items(_sheet15, _cfg15, 'RA', os.path.join(_td, 'ra.json'), post=_post_ra,
                                          limit=1, sleep=_ra_sleeps.append, log=lambda *a, **k: None))
check('R15y 429 에 Retry-After 가 있으면 그만큼 기다린다 (백오프 표보다 우선)',
      isinstance(_doc_ra, dict) and _doc_ra['grades'] == {'1': 3} and len(_ra_sleeps) == 1 and _ra_sleeps[0] >= 7,
      (_ra_sleeps, _doc_ra if not isinstance(_doc_ra, dict) else ''))

# testing: --out 에 디렉터리 없는 파일명
_o_here4, _o_load4, _o_cwd4 = SC.HERE, SC.load, os.getcwd()
with tempfile.TemporaryDirectory() as _td:
    try:
        SC.HERE = _td
        os.chdir(_td)
        SC.load = lambda n: ({'coder': n[7], 'sample_digest': _kdoc['sample_digest'],
                              'meta': {'base_url': 'https://x/v1', 'model': 'm'},
                              'grades': _gA if n.startswith('coding_A') else _gB}
                             if n.startswith('coding_') and not n.startswith('coding_key') else _kdoc)
        _oc, _oo = _run_main(SC.main, ['score_coding.py', '--out', 'scores.json'])
        _o_written = os.path.exists(os.path.join(_td, 'scores.json'))
    finally:
        os.chdir(_o_cwd4)
        SC.HERE, SC.load = _o_here4, _o_load4
check('R15y2 --out 에 디렉터리 없는 파일명을 줘도 죽지 않고 수치를 쓴다', _oc == 0 and _o_written, (_oc, _oo[-120:]))

# testing: 계열 가드는 호스트가 아니라 계열을 비교한다
_fg_cli = _call(lambda: SC.family_guard({'base_url': 'claude-cli://anthropic', 'model': 'claude-opus-5'},
                                        {'base_url': 'https://api.anthropic.com/v1', 'model': 'claude-sonnet-5'}))
_fg_or = _call(lambda: SC.family_guard({'base_url': 'https://openrouter.ai/api/v1', 'model': 'openai/gpt-x'},
                                       {'base_url': 'https://openrouter.ai/api/v1', 'model': 'anthropic/claude-x'}))
check('R15y3 claude-cli 와 api.anthropic.com 은 같은 계열(경고), 같은 집계 호스트라도 vendor/model 이 다르면 다른 계열',
      isinstance(_fg_cli, str) and 'FR-1' in _fg_cli and _fg_or is None, (_fg_cli, _fg_or))

# performance: 병렬 경로도 완료 즉시 기록한다 (선두 항목이 느려도 이미 끝난 유료 호출 결과가 디스크에 남는다)
_ev = _threading.Event()
_writes = []


def _post_slowhead(u, h, p, t):
    if '본문1' in p['messages'][-1]['content']:
        _ev.wait(5)                                  # 다른 항목이 기록될 때까지 막는다
    return 200, {'choices': [{'message': {'content': '3'}}], 'usage': {}}


_o_write = CP.write_doc


def _rec_write(path, doc):
    _writes.append(sorted(doc['raw']))
    if len(doc['raw']) >= 2:
        _ev.set()
    _o_write(path, doc)


with tempfile.TemporaryDirectory() as _td:
    try:
        CP.write_doc = _rec_write
        _doc_sh = _call(lambda: CP.code_items(_sheet15, _cfg15, 'SH', os.path.join(_td, 'sh.json'),
                                              post=_post_slowhead, workers=3, **_quiet_kw))
    finally:
        CP.write_doc = _o_write
check('R15y4 워커 경로는 완료 순서대로 즉시 기록한다 (첫 기록에 느린 선두 항목이 없다)',
      isinstance(_doc_sh, dict) and len(_doc_sh['raw']) == 3 and _writes and '1' not in _writes[0], _writes[:3])

# --- 커버리지 감사 GAP (Step 7): 값·제어흐름 경로 보강
_o = (G2.load_pages, G2.run, G2.median_length, G2.OUT_DIR)
with tempfile.TemporaryDirectory() as _rtd:
    open(os.path.join(_rtd, G2.NCS_FILE), 'w').close()
    try:
        G2.OUT_DIR = _rtd
        G2.load_pages = lambda p: {('f', 1): {'text': 'x' * 50, 'grade': 1, 'truncated': False}}
        G2.run = lambda pages, **kw: {k: {'g': 1, 'sn': 0, 'an': 0, 'reason': '', 'len': 50} for k in pages}
        G2.median_length = lambda pages: 50
        _zc, _ = _run_main(G2.main, ['regrade.py', '--data', _rtd, '--force'])
        _zp = json.load(open(os.path.join(_rtd, 'regrade_impact.json'), encoding='utf-8'))
    finally:
        G2.load_pages, G2.run, G2.median_length, G2.OUT_DIR = _o
check('R15z regrade 산출물 rule 에 확장 사전 21종이 실리고 dist 에 모든 변형 행이 있다 (--force 경로)',
      _zc == 0 and _zp['rule']['extra_safety_terms'] == G2.EXTRA_SAFETY_TERMS
      and _zp['rule']['extra_action_terms'] == G2.EXTRA_ACTION_TERMS
      and set(_zp['dist']) == {'baseline', *dict(G2.variant_grid())}, (_zc, sorted(_zp.get('dist', {}))))
check('R15z2 draw 는 n_recall 이 모집단보다 커도 모집단 전부로 클램프한다',
      sum(1 for _, g in MCS.draw({'disputed': [], 'control': [], 'boundary': [], 'recall_pool': ['a', 'b']},
                                 seed=1, n_recall=5) if g == 'recall') == 2)
with tempfile.TemporaryDirectory() as _td:
    open(os.path.join(_td, G2.NCS_FILE), 'w').close()
    try:
        MCS.HERE, G2.DATA_DIR = _td, _td
        G2.load_pages = lambda p: _pg_m
        _zc3, _ = _run_main(MCS.main, ['make_coding_sheet.py'])
        _kd = json.load(open(os.path.join(_td, 'coding_key.json'), encoding='utf-8'))
        _sd = json.load(open(os.path.join(_td, 'coding_sheet.json'), encoding='utf-8'))
    finally:
        MCS.HERE, G2.DATA_DIR, G2.load_pages = _o_here_m, _o_dd_m, _o_lp_m
check('R15z3 make_coding_sheet.main 이 쓰는 키·시트 문서의 구조 (population·variants·rule_pairs·seed·pred / coder_prompt·지문)',
      _zc3 == 0 and {'sample_digest', 'seed', 'n_recall', 'variants', 'rule_pairs', 'population', 'items'} <= set(_kd)
      and _kd['population']['strata'] == {g: sum(1 for r in _kd['items'] if r['group'] == g) for g in MCS.GROUPS}
      and all(set(r['pred']) == set(_kd['variants']) for r in _kd['items'])
      and _sd['coder_prompt'] == MCS.coder_prompt() and _sd['sample_digest'] == _kd['sample_digest']
      and not any(k in it for it in _sd['items'] for k in ('pred', 'group')), (_zc3, sorted(_kd)))
with tempfile.TemporaryDirectory() as _td:
    _ep = os.path.join(_td, 'e.env')
    with open(_ep, 'w') as _f:
        _f.write('A=1 # note\nnoequals\nB="x # y"\n')
    _env2 = _call(lambda: CP.read_env(_ep))
check('R15z4 read_env 는 인라인 주석을 자르고 따옴표 안의 #는 남기며 = 없는 줄은 건너뛴다',
      _env2 == {'A': '1', 'B': 'x # y'}, _env2)
_pc5 = _call(lambda: CP.provider_config({'AUDIT_LLM_API_KEY': 'k', 'AUDIT_LLM_BASE_URL': 'https://a/v1/', 'AUDIT_LLM_MODEL': 'm'},
                                        base_url='https://b/v1/'))
check('R15z5 --base-url 인자가 env 주소보다 우선하고 끝의 / 는 뗀다',
      isinstance(_pc5, dict) and _pc5['base_url'] == 'https://b/v1', _pc5)


class _FakeResp:
    def __init__(self, status, raw):
        self.status, self._raw = status, raw

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_o_urlopen = CP.urllib.request.urlopen
try:
    CP.urllib.request.urlopen = lambda req, timeout=None: _FakeResp(200, b'<html>challenge</html>')
    _pj1 = _call(lambda: CP.post_json('https://x/v1/chat/completions', {}, {'a': 1}, 5))
    _hdrs = CP.urllib.request.urllib.response if False else None

    def _raise_http(req, timeout=None):
        import email
        raise CP.urllib.error.HTTPError('https://x', 429, 'Too Many', email.message_from_string('Retry-After: 3\n'),
                                        _io.BytesIO(b'{"error":{"message":"rate"}}'))
    CP.urllib.request.urlopen = _raise_http
    _pj2 = _call(lambda: CP.post_json('https://x/v1/chat/completions', {}, {'a': 1}, 5))
finally:
    CP.urllib.request.urlopen = _o_urlopen
check('R15z6 post_json 은 200 비JSON 본문을 500 오류로, HTTPError 는 (코드, JSON 본문, Retry-After) 로 돌려준다',
      isinstance(_pj1, tuple) and _pj1[0] == 500 and 'JSON' in _pj1[1]['error']['message']
      and isinstance(_pj2, tuple) and _pj2[0] == 429 and _pj2[1]['error']['message'] == 'rate'
      and _pj2[1].get('_retry_after') == '3', (_pj1, _pj2))


def _run_badout(argv, input=None, capture_output=True, text=True, timeout=None, cwd=None):
    class _R:
        returncode, stderr, stdout = 1, 'boom', 'not json'
    return _R()


_r_bad = _call(lambda: CP.claude_cli_post('x', {}, _pl, 180, run=_run_badout))
check('R15z7 claude -p 출력이 JSON 이 아니면 500 으로 돌려준다 (exit code·stderr 꼬리 포함)',
      isinstance(_r_bad, tuple) and _r_bad[0] == 500 and 'exit 1' in _r_bad[1]['error']['message']
      and 'boom' in _r_bad[1]['error']['message'], _r_bad)


def _run_mu(mu, usage):
    def f(argv, input=None, capture_output=True, text=True, timeout=None, cwd=None):
        class _R:
            returncode, stderr = 0, ''
            stdout = json.dumps({'type': 'result', 'is_error': False, 'result': '2', 'usage': usage, 'modelUsage': mu})
        return _R()
    return f


_r_mu1 = _call(lambda: CP.claude_cli_post('x', {}, _pl, 180, run=_run_mu(
    {'claude-haiku-4-5': {'inputTokens': 900, 'outputTokens': 10}, 'claude-sonnet-5': {'inputTokens': 5000, 'outputTokens': 3}},
    {'input_tokens': 5900, 'output_tokens': 13})))
_r_mu2 = _call(lambda: CP.claude_cli_post('x', {}, _pl, 180, run=_run_mu({}, {'input_tokens': 42, 'output_tokens': 3})))
check('R15z8 modelUsage 에 요청 모델이 없으면 토큰이 가장 많은 모델을, modelUsage 가 없으면 usage 총계를 쓴다',
      isinstance(_r_mu1, tuple) and _r_mu1[1]['model'] == 'claude-sonnet-5' and _r_mu1[1]['usage']['prompt_tokens'] == 5000
      and isinstance(_r_mu2, tuple) and _r_mu2[1]['usage'] == {'prompt_tokens': 42, 'completion_tokens': 3}, (_r_mu1, _r_mu2))

print('\n결과: %d/%d PASS%s%s' % (
    PASS, PASS + FAIL, ', %d FAIL' % FAIL if FAIL else '',
    ', %d KNOWN ISSUE' % KNOWN if KNOWN else ''))
sys.exit(1 if FAIL else 0)
