# Gap Analysis: semantic-report-area-symmetry

> Date: 2026-09-19 | Design: `docs/02-design/features/semantic-report-area-symmetry.design.md`

---

## Match Rate: 100%

## Summary

설계의 10개 구현·검증 항목을 모두 반영했다. 확정 통계와 XLSX는 변경하지 않고, Markdown에 NCS·교과서 대칭 4영역 표와 교과서 9권의 연구상 대응 근거를 추가했다. 『반도체 인프라 일반』은 전기설비·공조·유틸리티·설비 운용 중심이라는 근거로 반도체장비에 배정했다.

## Implemented Items

- [x] 4영역 순서·표시명·NCS 대응·교과서 대응을 `semantic_report_areas.py`에 통합
- [x] 알 수 없는 말뭉치·그룹을 `ValueError`로 거부
- [x] HWPX 생성 코드가 공용 NCS·교과서 대응표를 사용
- [x] NCS와 교과서에 같은 열·영역 순서의 분포표 생성
- [x] 영역별 자료 수·전체·등급 1~3·미확정 합계 불변식 검사
- [x] 교과서 9권 대응표와 공식 분류가 아닌 연구상 대응이라는 주석 생성
- [x] 『반도체 인프라 일반』의 반도체장비 배정 근거 생성
- [x] `--skip-xlsx-write` 및 `write_xlsx=False` 구현
- [x] 지정 Markdown 보고서 재생성
- [x] XLSX·요약 JSON·HWPX 불변성과 Python·대시보드 회귀검사 확인

## Missing Items

- 없음

## Changed Items (Deviations from Design)

- 없음. 현재 HWPX 파일과 과거 변경대조 JSON을 재생성하지 않는 것은 설계의 비범위와 일치한다. 과거 대조 JSON 검사는 생성 당시의 `인프라 일반→재료` 대응을 명시적으로 적용하고, 현행 HWPX 생성 로직 검사는 공용 `인프라 일반→장비` 대응을 적용하도록 분리했다.

## Verification Evidence

- Python: `226 tests`, PASS
- Dashboard: `84/84`, PASS
- XLSX SHA-256: `e0c2b9933c66a7ba81bc07cd8d444f971e6ed5ee57630897e9cef0d4626b07a9`, 전후 동일
- XLSX mtime: `1789645678`, 전후 동일
- `semantic_summary.json` SHA-256: `a21eb7fd8cd6b36bfc63497ab1771cf3346f901d8cd16ae39062529167502356`, 전후 동일
- HWPX SHA-256: `9ef93187cd38f10ed21bf51314c8166562ab02193648e63e3f90817d57cfb272`, 전후 동일
  > 주(2026-09-21, `report-area-crosswalk`): 이 sha 는 2026-09-19 13:28 Polaris Office 가 열면서 다시 저장한 파일(`version.xml appVersion` PolarisOffice, 문단 1,425개 전부에 `hp:linesegarray`)이며 스크립트 출력(`aa0f3453…`, 대조 JSON `output_sha256`)이 아니다. "전후 동일" 은 이 세션이 HWPX 를 건드리지 않았다는 뜻으로만 유효하다. HWPX 반영은 `report-area-crosswalk`(2026-09-21, sha `1b464742…`)에서 했다.
- Manifest 4종: source `2721f0f9…`, rule `c08e6353…`, detail `229e9a79…`, summary `282d6c22…`, 기존값 유지

## Recommendations

1. 현재 HWPX 정본도 새 연구상 대응으로 맞추려면 별도 변경 범위로 재생성하고 표·문장·그림 및 변경대조 JSON을 함께 갱신한다.
2. 새 교과서가 추가되면 공용 대응표와 분류 근거를 먼저 검토한 뒤 정본을 재생성한다.

## Next Steps

- [x] Match rate 90% 이상이므로 결과 보고 단계로 진행
