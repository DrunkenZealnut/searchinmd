# docs/03-analysis/data — 산출물 계보

| 파일 | 쓴 스크립트 | 뜻 | 발표 여부 |
|---|---|---|---|
| `ncs_pages_reseg.csv`, `reseg_summary.json` | `resegment.py` (`EXPECTED` 가드) | NCS 검출 행을 원본 PDF 실제 쪽에 재배치한 (교재, 쪽) 단위 결과 — 2,189쪽, 등급 1/2/3 = 1,519/525/145 | **발표 정본** (대시보드·README·보고서, 2026-09-06 부터) |
| `ncs_pages.csv`, `summary.json` `ncs.pages/page_g/kw_pages/cases_pages` | `recount_grades.py` | 워크북 '페이지' 라벨(목차 블록) 기준 1,847쪽 — 2026-09-06 이전 발표 | **계보 확인용, 발표하지 않음** (`ncs.rows/row_g/cases_rows` 행 단위 수치는 현재도 씀) |
| `txt_pages.csv`, `summary.json` `textbook` | `recount_grades.py` | 반도체고 교과서 9권 | 발표 정본 |
| `regrade_impact.json` | `regrade.py` | 채점 규칙 변형별 영향 (라벨 기준) | 연구용 |
| `recoding_scores*.json` | `score_coding.py` | AI 코더 재코딩 채점 | 연구용, 미발표 |

대시보드 하니스(`outputs/test-dashboard-data.js`)가 NCS 쪽 단위 수치를 `reseg_summary.json` 과, 행 단위 수치·교과서를 `summary.json` 과 대조한다.

`ncs_pages_reseg.csv` 의 `마커오프셋` 열(12번째, `구라벨` 앞)과 `reseg_summary.json` 의 `marker_offset`·`per_book.marker_offset` 은 2026-09-07 부터 실리는 **마커 오프셋 진단**이다(marker-offset): 마커 교재 23권에서 마커 쪽 P 의 마크다운 본문을 PDF P−3..P+3 쪽과 3-gram 포함률로 대조한 분류 — `0` 같은 쪽, `1`/`-1` 인접 쪽이 뚜렷이 더 맞음(포함률 ≥ 0.5, 마진 ≥ 0.10), `amb` 모호, `other` ±2 이상, `short` 30자 미만·PDF 밖. 마커가 없는 쪽(정렬 교재·결손 구간)은 빈 칸. 발표 수치는 보정 없는 진단 실행이며(`marker_offset.moved` 0, `meta.marker_correct` null — 대시보드 하니스 D13q 가 지킨다), 보정 변형(`resegment.py --marker-correct`)의 영향표는 `../resegment-results.analysis.md` §3.7 에 있고 채택은 연구 책임자 결정 대기다.
