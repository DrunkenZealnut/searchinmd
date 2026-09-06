# docs/03-analysis/data — 산출물 계보

| 파일 | 쓴 스크립트 | 뜻 | 발표 여부 |
|---|---|---|---|
| `ncs_pages_reseg.csv`, `reseg_summary.json` | `resegment.py` (`EXPECTED` 가드) | NCS 검출 행을 원본 PDF 실제 쪽에 재배치한 (교재, 쪽) 단위 결과 — 2,189쪽, 등급 1/2/3 = 1,519/525/145 | **발표 정본** (대시보드·README·보고서, 2026-09-06 부터) |
| `ncs_pages.csv`, `summary.json` `ncs.pages/page_g/kw_pages/cases_pages` | `recount_grades.py` | 워크북 '페이지' 라벨(목차 블록) 기준 1,847쪽 — 2026-09-06 이전 발표 | **계보 확인용, 발표하지 않음** (`ncs.rows/row_g/cases_rows` 행 단위 수치는 현재도 씀) |
| `txt_pages.csv`, `summary.json` `textbook` | `recount_grades.py` | 반도체고 교과서 9권 | 발표 정본 |
| `regrade_impact.json` | `regrade.py` | 채점 규칙 변형별 영향 (라벨 기준) | 연구용 |
| `recoding_scores*.json` | `score_coding.py` | AI 코더 재코딩 채점 | 연구용, 미발표 |

대시보드 하니스(`outputs/test-dashboard-data.js`)가 NCS 쪽 단위 수치를 `reseg_summary.json` 과, 행 단위 수치·교과서를 `summary.json` 과 대조한다.
