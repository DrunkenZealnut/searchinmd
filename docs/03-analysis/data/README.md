# docs/03-analysis/data — 산출물 계보

| 파일 | 쓴 스크립트 | 뜻 | 발표 여부 |
|---|---|---|---|
| `semantic_summary.json` | `semantic_keyword_recount.py` (`EXPECTED` 가드, 2026-09-14 정본 실행) | 30개 키워드 의미 단위 재검산 + 출현별 등급 — NCS 86권 11,517건(등급 1/2/3 = 4,378/4,614/2,525), 교과서 9권 1,207건(633/459/115) — 사전 v2(2026-09-14 결정 3), 키워드·그룹별, `meta.run`(git commit·명령·입력 sha256), `meta.previous_basis`(reseg 복사). `docs/semantic_recount_data.js` 와 같은 JSON | **발표 정본** (대시보드 KPI·분리 분석 페이지·README, 2026-09-13 부터; 분모 = 출현건수, 연구책임자 결정) |
| `ncs_pages_reseg.csv`, `reseg_summary.json` | `resegment.py` (`EXPECTED` 가드) | NCS 검출 행을 원본 PDF 실제 쪽에 재배치한 (교재, 쪽) 단위 결과 — 2,189쪽, 등급 1/2/3 = 1,519/525/145 | **이전 기준 (페이지 단위)** — 2026-09-06~09-12 발표 정본, 지금은 대시보드·README 에 병기(브리지 표); `semantic_summary.json.meta.previous_basis` 가 이 값을 복사하고 하니스 S4 가 대조 |
| `ncs_pages.csv`, `summary.json` `ncs.pages/page_g/kw_pages/cases_pages` | `recount_grades.py` | 워크북 '페이지' 라벨(목차 블록) 기준 1,847쪽 — 2026-09-06 이전 발표 | **계보 확인용, 발표하지 않음** (`ncs.rows/row_g/cases_rows` 행 단위 수치는 현재도 씀) |
| `txt_pages.csv`, `summary.json` `textbook` | `recount_grades.py` | 반도체고 교과서 9권 | 발표 정본 |
| `regrade_impact.json` | `regrade.py` | 채점 규칙 변형별 영향 (라벨 기준) | 연구용 |
| `recoding_scores*.json` | `score_coding.py` | AI 코더 재코딩 채점 | 연구용, 미발표 |
| `accident_case_pages.json` | 손으로 옮김 (`resegment-results.analysis.md` §3.4) | 사고사례 자동 판정 13쪽·5권의 원문 확인 판정 — 실제 사고 서술 3쪽(반도체 산업재해 구미 불산 1건·2권 중복, 산업재해 아님 1), 오탐 10(지침 6·정의 1·물성 3). `ncs_pages_reseg.csv` 사고사례=예 13쪽과 일치(테스트) | 연구용 — 기초보고서 3절·대시보드 사고사례 절의 근거 |
| `hwpx_results_refresh_20260914.json` | `hwpx_results_refresh.py` | 기초보고서 HWPX 제3장 1~3절 재작성의 변경 대조 — 문단 45(구/신 숫자 목록·정본 키 경로 `keys`·서술 조건 결과 `conditions`)·표 7(바뀐 셀 수)·그림 3(형식·크기·비트·sha256)·숫자 감사(토큰 715, 미일치 0, 2장 5절 범위 밖 stale 0). 새 HWPX 는 `data/`(비추적) | 연구용 — 보고서 문장은 담지 않음 |
| `expression_review_key.json`, `expression_review_{A,B,adj}.json`, `expression_review_scores.json`, `expression_review_impact.json` | `expression_review.py` (+ `code_pages.py`) | 의미 재검산 사전의 도메인 점검 — 표본 키(618건, 본문 없음), 코더 2계열 라벨(A `claude-opus-5`·B `gpt-5.6-sol`)과 연구책임자 재정, 표현별 정밀도·CP 95% 구간·κ(하한 < 0.8 후보), 사전 v1/v1fix/v2 영향표. 시트(본문)는 `data/` 비추적 | 연구용, 미발표 — 정본은 `semantic_summary.json`(사전 `v2`, 결정 3); 영향표의 `v2` 열이 정본과 같음(`test_impact_canonical_column_equals_canonical_summary`) |

대시보드 하니스(`outputs/test-dashboard-data.js`)가 발표면(대시보드·분리 분석 페이지·README·CLAUDE.md)의 수치를 `semantic_summary.json` 과, 이전 기준(페이지 단위)을 `reseg_summary.json` 과 대조한다(S2~S8).

`ncs_pages_reseg.csv` 의 `마커오프셋` 열(12번째, `구라벨` 앞)과 `reseg_summary.json` 의 `marker_offset`·`per_book.marker_offset` 은 2026-09-07 부터 실리는 **마커 오프셋 진단**이다(marker-offset): 마커 교재 23권에서 마커 쪽 P 의 마크다운 본문을 PDF P−3..P+3 쪽과 3-gram 포함률로 대조한 분류 — `0` 같은 쪽, `1`/`-1` 인접 쪽이 뚜렷이 더 맞음(포함률 ≥ 0.5, 마진 ≥ 0.10), `amb` 모호, `other` ±2 이상, `short` 30자 미만·PDF 밖. 마커가 없는 쪽(정렬 교재·결손 구간)은 빈 칸. 발표 수치는 보정 없는 진단 실행이며(`marker_offset.moved` 0, `meta.marker_correct` null — 대시보드 하니스 S4d 가 지킨다), 보정 변형(`resegment.py --marker-correct`)의 영향표는 `../resegment-results.analysis.md` §3.7 에 있고 채택은 연구 책임자 결정 대기다.
