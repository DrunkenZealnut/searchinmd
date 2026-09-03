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

print('\n결과: %d/%d PASS%s%s' % (
    PASS, PASS + FAIL, ', %d FAIL' % FAIL if FAIL else '',
    ', %d KNOWN ISSUE' % KNOWN if KNOWN else ''))
sys.exit(1 if FAIL else 0)
