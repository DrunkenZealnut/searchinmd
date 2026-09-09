# 의미 출현 등급 결합 완료 보고

> **Feature**: semantic-occurrence-grades
> **Completed**: 2026-09-09
> **Match Rate**: 100%

## 완료 내용

- `semantic_keyword_recount_20260909.xlsx`를 만드는 재검산 과정에 페이지 등급 결합 단계를 추가했다.
- 기존 NCS·교과서 페이지는 원본 Excel의 등급과 사유를 승계했다.
- 기존 판정에 없는 페이지만 `regrade.grade_page()` 기준선으로 새로 판정했다.
- 페이지 마커가 없는 출현은 `등급 미확정`으로 보존했다.
- NCS와 교과서 대시보드를 공통 렌더러로 통합해 동일한 등급1~3 분석 흐름을 적용했다.
- 등급 비율과 차트의 분모를 페이지 수에서 의미 출현건수로 바꾸었다.

## 등급 출현 결과

| 구분 | 전체 출현 | 등급1 | 등급2 | 등급3 | 미확정 |
|---|---:|---:|---:|---:|---:|
| NCS | 12,875 | 4,869 | 4,713 | 2,480 | 813 |
| 교과서 | 1,293 | 705 | 468 | 120 | 0 |
| 합계 | 14,168 | 5,574 | 5,181 | 2,600 | 813 |

등급1~3 비율의 분모는 등급이 확정된 출현건수다. NCS 미확정 813건은 전체 의미 출현에는 포함하지만 등급 비율에서는 제외했다.

## 등급 계보

| 구분 | 기존 판정 승계 | 신규 페이지 판정 | 미확정 |
|---|---:|---:|---:|
| NCS 출현 | 6,330 | 5,732 | 813 |
| 교과서 출현 | 1,212 | 81 | 0 |

정규화된 문서명이나 LM 코드가 여러 현재 파일에 대응하면 기존 등급을 승계하지 않고 파일별로 신규 판정하도록 방어했다.

## 산출물

- `data/semantic_keyword_recount_20260909.xlsx`
- `data/semantic_keyword_recount_20260909_report.md`
- `docs/semantic_recount_data.js`
- `docs/semantic_grade_dashboard.js`
- `docs/index.html`
- `docs/textbook.html`
- `docs/03-analysis/semantic-occurrence-grades.analysis.md`

## 검증 결과

- 의미 등급 단위·산출물 테스트 21/21 통과
- 대시보드 데이터·흐름·정적 대체 화면 테스트 18/18 통과
- 기존 회귀 하니스 379/379, 32/32, 24/24, 38/38 통과
- Excel 요약과 대시보드 60개 키워드×말뭉치 등급 집계 일치
- XLSX ZIP 무결성 오류 0건
- 로컬 Chrome에서 NCS·교과서 화면 렌더링과 JavaScript 오류 0건 확인

## 주의사항

사용자가 지정한 기존 등급 Excel은 읽기 전용으로 사용했고 수정하지 않았다. 후속 재집계 때는 Excel, Markdown 보고서, `semantic_recount_data.js`를 같은 실행에서 함께 생성해야 한다.
