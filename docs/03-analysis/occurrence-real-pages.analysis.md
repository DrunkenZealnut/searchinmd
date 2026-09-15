# occurrence-real-pages — 설계 대비 구현 갭 분석

> 분석일: 2026-09-15 · 브랜치 feat/occurrence-real-pages (커밋 e653132·ac6fa42·99838cd·c5325df) · 설계 대비 구현 갭 분석 (bkit Check)
>
> **Feature**: occurrence-real-pages
> **Plan**: `occurrence-real-pages.plan.md` (Approved 2026-09-15 — 연구책임자 결정 D1~D6 전부 A, §1.3 실측, FR-01~FR-10, 성공 기준 6항)
> **Design**: `occurrence-real-pages.design.md` (§1 목표 5, §2 아키텍처, §3.1~3.9 상세, §4 테스트 설계, §5 구현 순서, §6 결정 기록 7행)
> **Date**: 2026-09-15
> **Match Rate**: **90.8%** (설계 항목 76개: 일치 62 · 부분 14 · 불일치 0) → **Act-1 반영 후 100%**
> **구현**: `semantic_keyword_recount.py` · `occurrence_real_pages_impact.py`(신규) · `hwpx_results_refresh.py` · `docs/semantic_grade_dashboard.js` · `docs/index.html` · `test_semantic_keyword_recount.py`(`RealPageTests` 8·`ImpactScriptTests` 3) · `test_hwpx_results_refresh.py`(`RealPageBasisTests` 2·`CommittedDiffTests`) · `test_expression_review.py` · `outputs/test-dashboard-data.js`(S1e·S2d·S3n, 68 → 71)
> **산출물**: `docs/03-analysis/data/semantic_summary.json` · `docs/semantic_recount_data.js` · 분리 HTML 3건 · `docs/03-analysis/data/occurrence_real_pages_impact.json` · `docs/03-analysis/data/hwpx_results_refresh_20260915.json` · `docs/03-analysis/hwpx-results-refresh/review.html` · 비추적 `data/반도체 기초보고서_20260915_정본.hwpx`·`data/semantic_keyword_recount_20260915.xlsx` · README · CLAUDE.md · `docs/03-analysis/data/README.md` · `docs/04-report/features/semantic-occurrence-grades.report.md` · `docs/03-analysis/semantic-keyword-recount.analysis.md` · `TODOS.md`
> **Author**: Claude (Opus 5, bkit gap-detector) — 결정: 연구책임자

---

## 설계 항목 구현률: 90.8% → Act-1 100%

## 1. 요약

| 항목 | 값 |
|---|---|
| **Match Rate** | **90.8%** (설계 항목 76개: 일치 62 · 부분 14 · 불일치 0 → (62 + 14×0.5 + 0) / 76 = 69 / 76) |
| 갭 | 🔴 High 1 (G-1 줄 번호 규약 불일치 — `split_pages` 는 `splitlines()`, 대응은 `split("\n")`; 정본 코퍼스 1권에서 실제로 어긋남) · 🟡 Low 10 (설계 갱신 4 · 문서 2 · 테스트 보강 1 · 구현 소폭 보강 3) · 🔵 설계 외 추가 9 (`AnalysisResult.run`, 영향표 `grade3_share`·3분류·순서 검증, 2절 "주" 문단 분기 등) |
| 판정 | Match Rate ≥ 90% 이나 **G-1 은 발표값(쪽 배정)에 닿는 결함**이므로 Act-1 로 먼저 닫고(정본 재실행·`EXPECTED` 재고정 수반) 보고서로 갈 것을 권고. 나머지 갭은 설계·문서·테스트 수준 |
| 정본 결과 | NCS 86권 11,517건 → 등급 3,788 / 5,227 / 2,502 (등급3 21.7%), `grade_sources` NCS `real-page` 11,517 · `existing` 0 · `new` 0; 교과서 1,207건 불변(633/459/115, `existing` 1,149 · `new` 58); `meta.page_basis {NCS: real, 교과서: marker}`; `meta.run.page_maps` 84권 sha256 `36de1bff…`; `meta.run.reseg_agreement` 2,035 / 2,035; NCS 분야 쪽수 합 3,435 + 1,780 + 2,522 + 1,363 = **9,100**; `meta.run.expected true · force false · variant false` |
| 영향표 | 블록 기준 4,378 / 4,614 / 2,525 → 실제 쪽 3,788 / 5,227 / 2,502 · 이동 4,016건(1→2 1,296 · 1→3 398 · 2→1 727 · 2→3 587 · 3→1 377 · 3→2 631) · `by_source` existing 52.8% / new 79.9% 불변 · `by_book_kind` real-marker 25 · toc-block 59 · real-marker-nomap 2 · 검출 쪽 1,785 → 2,492 · 블록 폭 3,718 / 2,335 / 3,024 / 2,027 — 계획 §1.3 실측과 전부 일치 |
| HWPX | 대조 JSON `source.page_basis {NCS: real}` · `source.hwpx_sha256 ad5167ea…`(2026-09-14 실행과 같음 → 원본 불변) · `output` `…_20260915_정본.hwpx` · 숫자 토큰 724 · 미일치 0 · status ok |

**하니스 (코디네이터가 직접 실행한 결과를 인용 — 이 분석은 테스트를 실행하지 않았다)**

| 명령 | 결과 | 상태 |
|---|---|---|
| `python3.13 -m unittest test_semantic_keyword_recount test_expression_review test_hwpx_results_refresh` | 150 tests OK | ✅ |
| `PATH=/usr/bin:/bin python3 -m unittest test_hwpx_results_refresh` | OK (skipped 1 — magick 없는 인터프리터) | ✅ |
| `node outputs/test-dashboard-data.js` | 71/71 PASS | ✅ |
| `python3 outputs/test-recount-grades.py` | 390/390 PASS | ✅ |
| `test-search-equivalence.js` · `run-core-logic-tests.js` · `test-sri.js` | 24 · 32 · 38 통과 | ✅ |
| 정본 재실행 | 가드 통과(`expected true`), 두 번 돌려 해시 동일 | ✅ |
| 원본 PDF 86권 쪽수 검증 | 84권 `per_book.pdf_pages` 일치, 새 2권 120·119, 합 9,100 | ✅ |

git: 이 분석은 git 명령을 쓰지 않았다. `semantic_summary.json` `meta.run.git_commit` 은 `f28d496`(정본 실행이 올라탄 부모 커밋, `git_dirty true` — 산출물이 다음 커밋에 들어가는 저장소 규약).

## 2. FR-01~FR-10 — 설계 항목 ↔ 구현 ↔ 테스트 ↔ 상태

| FR | 설계 항목 (§) | 구현 위치 (파일:함수:줄) | 테스트 | 상태 |
|---|---|---|---|---|
| FR-01 대응 로딩·덧씌우기 | §3.1 `load_page_maps` — 코드→`<LM코드>.pages.json`, 검증 (a) `md` 이름 (b) 줄 수 `split("\n")` (c) 값 ≥ 1, `PageMapsInfo{dir, files, sha256}`, 교과서 무시; §3.2 `apply_page_maps` — NCS ∧ 대응 있음 → `page = line_pages[line-1]`, `scan_document` 직후·요약 전, `with_summary=False` 에서도, 제외 레코드도 | `semantic_keyword_recount.py:_document_code` 419-421, `PageMapsInfo` 410-416, `load_page_maps` 424-463 (md 451-453, 줄 수 455-457, 값 458-459, 지문 462), `apply_page_maps` 495-506, `aggregate_matches` 1149·1155 (`apply_page_maps` 가 요약 계산 전에 호출, `page_count` 1184-1188 은 실제 쪽) | T `test_load_page_maps_validates_and_requires_map_or_listed_book`(md·길이·0값 거부, sha256 결정론), `test_apply_page_maps_overlays_pages_after_matching`(블록 2 → 쪽 12·13, `page_count` 5 vs 4, 총계 불변) | 부분 — 줄 번호 규약: `split_pages` 는 `splitlines()`(393) 로 줄을 세고 대응·`load_page_maps`·`assign_match_grades` 는 `split("\n")` — 정본 코퍼스 `LM1903060128` 430행에 `\x0c` 1건이 있어 그 뒤 출현의 줄 번호가 대응보다 1 크다 (**G-1**); `page is None` 레코드도 덧씌움(설계 "그대로", 정본 영향 0) |
| FR-02 대응 없는 문서 규칙 | §3.1 없으면 `REAL_PAGE_MARKER_BOOKS` 에 있어야, 메시지; 목록 교재는 표식 결손 검사; 목록에 있어도 대응이 있으면 대응 사용 (§6-3 자동 판별 없음) | `REAL_PAGE_MARKER_BOOKS` 61 (`LM1903060408`·`LM1903060424`), `load_page_maps` 443-446 (거부·메시지), 447-448 (표식 1..N 연속·중복 없음 — 설계의 "블록 수 == 최댓값" 보다 엄격), `is_file` 검사가 먼저라 목록 교재도 대응이 있으면 대응 사용 | T 같은 테스트 (`LM1903060499` 거부, 목록 교재 통과, 표식 2 빠진 목록 교재 거부); `test_run_census_wires_…` (목록 규칙을 census 경로에서) | 일치 (목록+대응 조합·표식 없는 NCS 문서 skip 438-439 은 미검증 — G-6·G-9) |
| FR-03 실제 쪽 판정·출처 | §3.3 대응 문서 `page_lines[(NCS, rel, 실제 쪽)]` ← 대응된 줄(표식 줄 제외), `grade_page(word_boundary=False, normalize=False)`, `existing_grades` 무시, source `real-page`, 빈 본문 → `unpaged-fallback`, `GRADE_SOURCES`·`GRADE_SOURCE_LABEL`, `STRICT_GROUPS` 마찰, 캐시 유지; 대응 없는 문서는 현행 `new`/`existing` | `GRADE_SOURCES` 59, `GRADE_SOURCE_LABEL["real-page"]="실제 쪽 판정"` 60, `assign_match_grades` 577-684 — `real_docs` 593-596 (대응 문서 ∪ 목록 교재), `page_lines` 600-606, real-page 분기 641-651, `newly_graded` 643·651; `EXPECTED["grade_sources"]` 75 | T `test_real_page_grading_uses_page_text_and_ignores_workbook_labels`(쪽 12 → 3, 쪽 13 → 1, 라벨 무시, 대응 없이 부르면 현행); `test_run_census_wires_…`(NCS `grade_sources` 전부 `real-page`, `unpaged` 0) | 부분 — D2 목록 교재가 설계의 `new`/`existing` 이 아니라 표식 블록 본문의 `real-page` 판정(워크북 라벨 무시). 계획 §4 성공 기준 1 의 첫 선택지(`real-page 11,517 / existing 0 / new 0`)와 일치하고 근거가 타당하나 설계 §2·§3.3·§4 와 어긋남 (**G-2**) |
| FR-04 이전 기준 결속 | §3.4 `reseg_agreement(result, csv) -> {pages, agree, disagree≤20}`, `utf-8-sig`, (코드, 쪽) 교집합, manifest·`summary_metrics`·`EXPECTED {2035, 2035}`, 일반 규칙으로 불일치, 원인 안내 | `DEFAULT_RESEG_CSV_NAME` 466, `reseg_agreement` 469-492 (`label` 출처 행 제외 480-481, `included` ∧ `real-page` 486), `run_manifest` 1389, `summary_metrics` 1407, `EXPECTED["reseg_agreement"]` 68, `run_census` 2299·2301 | T `test_reseg_agreement_counts_shared_pages`(100% / 1건 불일치·`label` 제외), `test_manifest_and_metrics_carry_page_maps_and_agreement`(`check_expected` 가 `reseg_agreement.agree: 3 != 4` 보고); S `S2d` (2,035 = 2,035) | 일치 — `label` 행 제외는 설계 외(정당, **G-3** 설계 갱신); "원인은 둘뿐" 안내는 docstring 에만 (**G-8**) |
| FR-05 분야 쪽수·page_basis | §3.5 `dashboard_payload(pdf_pages=)` — NCS 그룹 pages = Σ `pdf_pages[코드]`, D2 교재는 표식 최댓값, 교과서 현행; `run_census` 가 `reseg_summary.json per_book.pdf_pages` 에서; `meta.page_basis`·`meta.run.page_maps`; 하니스 S3n | `dashboard_payload` 1685-1798 (pages 1736-1748 — 대응 교재인데 `pdf_pages` 에 없으면 ValueError 1744-1745, `page_basis` 1787-1792), `pdf_pages_from_previous_basis` 1448-1457, `run_census` 2286-2291 (`previous_basis` 필수 2288-2289), `summary_payload(pdf_pages=)` 1482-1495 | T `test_group_pages_use_pdf_pages_when_given`(40 / 표식 2, `page_basis` 양쪽, 모르는 교재 오류); S `S3n`(합 == reseg `per_book.pdf_pages` 합 + 239) · `S3m`(교과서 합 2,055 불변); 산출물 groups pages 합 9,100 | 일치 |
| FR-06 manifest·EXPECTED·metrics | §3.6 `run_manifest(page_maps=)` → `page_maps`·`real_page_marker_books`·`reseg_agreement`; `summary_metrics` 에 `page_basis`·`reseg_agreement`·`page_maps_sha256`; `EXPECTED` 재고정(totals 불변, grades, sources, agreement, `page_maps_sha256`, detail/summary 해시; rule/source 불변); 커밋 산출물 테스트가 새 키를 봄; 변형 실행도 대응; `--no-page-maps` 없음 | `run_manifest` 1361-1362·1387-1389, `summary_metrics` 1393-1424, `EXPECTED` 64-82 (`page_basis` 66, `page_maps_sha256` 67, `reseg_agreement` 68, totals 70, grades 72-73, sources 75, detail 80·summary 81 재고정, rule 78·source 79 주석 "불변"), `check_expected` 1427-1440, `run_census` 2287 (변형과 무관하게 대응 로딩), CLI 에 `--no-page-maps` 없음 | T `test_manifest_and_metrics_carry_page_maps_and_agreement`, `test_committed_summary_json_matches_expected`(1029-1031 에 세 키 추가 — "자동" 이 아니라 손으로 확장, 결과 동일), `test_run_census_wires_…`(대응 없는 실행은 `page_basis marker` 로 `SystemExit`); S `S2b`·`S2d` | 일치 |
| FR-07 영향표 | §3.7 (A) 블록 기준 / (B) 실제 쪽 기준 두 번 집계, 상속은 (A)만; totals·grades·transition·by_source·by_book_kind·keywords·groups·pages·meta; 본문·절대 경로 없음; (A) == 현 정본 검증 | `occurrence_real_pages_impact.py:compute_impact` 49-115 (A/B 54-55, `_key` 순서·집합 검증 58-59, 계보 `BLOCK_BASIS_V2` 23-26·64-67, `book_kind` 39-46 3분류·`REAL_MARKER_RATIO` 0.8, 블록 폭 85-99), `main` 118-145; 산출물 `occurrence_real_pages_impact.json`(§3.2) | T `ImpactScriptTests` 3건(이동 행렬·총계 불변·`by_source`·`by_book_kind`·쪽 4→5·블록 폭; 계보 불일치 거부; `main` 산출물에 절대 경로 없음); `test_impact_canonical_column_equals_canonical_summary`(block 열 == `expression_review_impact` v2 == 4,378/4,614/2,525, real 열 == 정본) | 일치 — 계보 검증이 파일 대신 상수(정본 파일이 이미 실제 쪽 기준이라 상수가 맞음), `write_text` 직접 쓰기, 설계 외 필드 (**G-7**); 정렬 자기 검증 수치 미병기 (**G-10**) |
| FR-08 대시보드 브리지·정적값 | §3.8 `page_basis real` 이면 "같은 실제 PDF 쪽 … 집계 단위·가중 차이" 문구(설계 결정 12 — 출고 전 리뷰에서 "분모뿐" 을 고침), `index.html` 정적 `.ctn` 갱신 | `docs/semantic_grade_dashboard.js` (`realNote` 제 문단: 같은 실제 PDF 쪽 + "공유 쪽 등급 일치 2,035/2,035 (100.0%)" + 집계 단위·가중; `dataNote` 는 0건 출처 생략); `docs/index.html` 122 (3,788 / 5,227 / 2,502, "실제 PDF 쪽에 놓고 … 공유 쪽 등급 일치 2,035/2,035 (100.0%)") | S `S1t`(브리지 문구·결속 수치) · `S1v`(데이터 주) · `S5a`·`S5h`(정적값 == summary) · `S7a`·`S7h`·`S8a`·`S8c`(README·CLAUDE.md 수치) | 일치 (신설 `S1e` 가 기존 `S1e` 와 ID 중복 — G-6, `S1t` 로 개명) |
| FR-09 HWPX 재생성 | §3.8 `Facts` 에 `page_basis`(`load_facts` 필수), 2절 도입·3절 문구 분기, 산출물 날짜 접미를 정본 실행일에서(하드코딩 20260914 제거), 옛 대조 JSON 유지 + data README 계보 | `hwpx_results_refresh.py:Facts.page_basis` 119, `load_facts` 201-203·261, `run_day`/`default_out_path`/`default_diff_path` 264-273 (`DEFAULT_OUT_DIR` 45·`DEFAULT_DIFF_DIR` 49 만 남음), 2절 도입 677·694, 2절 "주" 742-743(설계 외), 3절 765, 대조 JSON `source.page_basis` 1057, CLI 1218-1241; 산출물 `hwpx_results_refresh_20260915.json`(§3.3) · `review.html` · 비추적 `…_20260915_정본.hwpx`; `docs/03-analysis/data/README.md` 12-13행 | T `RealPageBasisTests` 2건(양 분기·`page_basis` 없는 정본 거부·날짜 접미), `CommittedDiffTests.test_committed_diff_json`(최신 날짜 파일, `source.page_basis`, 토큰 724·미일치 0, 날짜 = 정본 실행일) | 일치 |
| FR-10 문서 | §3.8 README 재생성 절 `--page-maps`, 예외 문단 수치, CLAUDE.md 그룹 4, data README 계보 행; 계획: `TODOS.md` 2·3·1(d) 종결 | README 78-85 (명령·설명), 17 (21.7%·2,502/11,517·영향표), 138·165·182; CLAUDE.md 147 (그룹 4 — 대응·결속·D2·`real-page`·9,100), 172 (예외 문단 21.7%), 182 (71 assertions), 214 (테스트 라우팅); `docs/03-analysis/data/README.md` 5·12·13·14; `semantic-occurrence-grades.report.md` 54-65 브리지 표; `TODOS.md` 16 (1(d) 닫힘)·17 (2 닫힘)·18 (3 닫힘)·22 (④ 대기) | S `S7a`·`S7d`·`S7f`·`S8a`·`S8b`; R17/S9 인용 단언 수 | 부분 — README 9행 "정본 실행(2026-09-14, `…_20260914.xlsx`)"·87행 "새 파일 `…_20260914_정본.hwpx`", 보고서 브리지 절 제목 "(정본, 2026-09-14)", data README 15행 "영향표의 `v2` 열이 정본과 같음"(총계만 같고 등급은 블록 기준 — §6-6 의 "기준 차이" 미기재) (**G-5**) |

## 3. 스키마 대조 — 설계 §3.5~3.8 vs 실제 파일

### 3.1 `docs/03-analysis/data/semantic_summary.json` (설계 §3.5·§3.6)

| 키 | 설계 | 실제 | 판정 |
|---|---|---|---|
| `meta.page_basis` | `{"NCS": "real", "교과서": "marker"}` | 있음 (5-8행), `EXPECTED["page_basis"]` 와 동일 | 일치 |
| `meta.run.page_maps` | `{dir, files, sha256}` | `dir data/markdown/ncs_paged` · `files 84` · `sha256 36de1bff…` (76-80행) = `EXPECTED["page_maps_sha256"]` | 일치 |
| `meta.run.real_page_marker_books` | 목록 | `[LM1903060408, LM1903060424]` (81-84행) | 일치 |
| `meta.run.reseg_agreement` | `{pages, agree}` (disagree 는 manifest 에 없음) | `{2035, 2035}` (85-88행) | 일치 |
| `meta.run.inputs` | 6종 + 이전 기준 | 워크북 3 · 마크다운 86/9 · 이전 기준 1 (28-59행), 절대 경로 없음 | 일치 |
| `meta.run.expected / force / variant / dictionary` | `true / false / false / v2` | 72-75·89행 | 일치 |
| `meta.manifest` 4 해시 | `EXPECTED` 와 동일 | rule `c08e6353…` · source `2721f0f9…` · detail `229e9a79…` · summary `282d6c22…` (15-18행) — rule·source 는 `EXPECTED` 주석대로 불변, detail·summary 재고정 | 일치 |
| `corpora.NCS.grade_sources` | `real-page` 11,517 · `existing` 0 · `new` 0 | 112-118행 동일, `unpaged-*` 0 | 일치 |
| `corpora.교과서.grade_sources` | 현행 | `real-page` 0 · `existing` 1,149 · `new` 58 (180-186행) | 일치 |
| `corpora.NCS.grades` | 3,788 / 5,227 / 2,502 / unpaged 0 | 119-124행 | 일치 |
| `corpora.NCS.groups[].pages` | PDF 쪽수 합 9,100 | 반도체개발 3,435 · 반도체장비 1,780 · 반도체재료 2,522 · 반도체제조 1,363 = 9,100 (125-174행) | 일치 |
| `meta.previous_basis` | reseg 복사 | 2,189 / 1,519·525·145 / 86 / 13 / 51 (91-105행) | 일치 |

### 3.2 `docs/03-analysis/data/occurrence_real_pages_impact.json` (설계 §3.7)

| 키 | 설계 | 실제 | 판정 |
|---|---|---|---|
| `totals` | 같아야 함 | NCS 11,517 · 교과서 1,207 (35-38행) | 일치 |
| `grades.block / real` | A/B 말뭉치별 | NCS 4,378/4,614/2,525 → 3,788/5,227/2,502; 교과서 633/459/115 불변 (39-64행) | 일치 |
| `grade3_share` | — | NCS 21.9 → 21.7, 교과서 9.5 → 9.5 (65-74행) | 추가 |
| `transition` | 6칸 + 불변 | unchanged 7,501 · moved 4,016 · 1→2 1,296 · 1→3 398 · 2→1 727 · 2→3 587 · 3→1 377 · 3→2 631 (75-86행) = 계획 §1.3 | 일치 |
| `by_source` | A 의 existing/new 불변율 | existing 6,292 → 52.8% · new 5,225 → 79.9% (87-98행) | 일치 |
| `by_book_kind` | 실제 쪽 / 목차 블록 | real-marker 25권 3,821건 · toc-block 59권 7,281건 · real-marker-nomap 2권 415건, 각 block/real 등급 (99-142행) — 계획 §1.3 의 25 / 59 / 2 | 일치 (3분류, `book_kind_rule` 을 meta 에 기록) |
| `keywords` / `groups` | 키워드별·분야별 A/B | 30건 / 4 그룹 (143행~·535행~) | 일치 |
| `pages` | 검출 쪽 A/B, 블록 폭 | 1,785 → 2,492 · 폭 1쪽 3,718 · 2~3쪽 2,335 · 4~9쪽 3,024 · 10쪽+ 2,027 (585-594행) | 일치 |
| `meta` | 입력 sha256·실행 시각·git | `dictionary v2`·`unit`·`corpus_note`·`block_reference`·`book_kind_rule`·`generated_at`·`git {f28d496, dirty}`·`inputs {source_workbook, school_grade_workbook, ncs_markdown, page_maps{dir, files 84, sha256}}` (2-34행) | 일치 |
| 정렬 자기 검증(±1쪽 94.9% 등) | 계획 §4-2·§5 "영향표에 병기" | 없음 | 누락 (G-10) |
| 본문·절대 경로 | 없음 | 없음(`test_impact_main_writes_json_without_absolute_paths`) | 일치 |

### 3.3 `docs/03-analysis/data/hwpx_results_refresh_20260915.json` (설계 §3.8)

| 키 | 설계 | 실제 | 판정 |
|---|---|---|---|
| `source.page_basis` | 있음 | `{"NCS": "real", "교과서": "marker"}` (11-14행) | 일치 |
| `source.summary_run` | 정본 run | `generated_at 2026-09-15T11:45:01+09:00` · `git_commit f28d496` · `dictionary v2` · `expected true` (5-10행) = `semantic_summary.json meta.run` | 일치 |
| `source.hwpx / hwpx_sha256` | 원본 20260911 에서 | `반도체 기초보고서_20260911.hwpx` · `ad5167ea…` (2026-09-14 대조 JSON 과 같은 값 → 원본 불변) | 일치 |
| `output` | 날짜 접미 = 정본 실행일 | `반도체 기초보고서_20260915_정본.hwpx` (17행) | 일치 |
| `paragraphs[].conditions.page_basis` | — | "NCS 기반 반도체 자료를 대상으로" 문단에 `page_basis: real` (601행) | 추가 |
| `audit` | 토큰·미일치 | 724 · `[]` · ok (1594-1601행) | 일치 |
| 옛 대조 JSON | 유지 + 계보 | `hwpx_results_refresh_20260914.json` 유지, data README 13행 "계보(토큰 723)" | 일치 |

## 4. 설계와 다르게 구현된 점 — 판단

| # | 차이 | 근거 (구현·산출물) | §6 결정 기록으로 정당화되는가 | 판정 |
|---|---|---|---|---|
| 4.1 | 줄 번호 규약: `split_pages`(매칭·`record.line`)는 `splitlines()`, 대응(`resegment.py` 812 `split('\n')`)·`load_page_maps` 455·`assign_match_grades` 603 은 `split("\n")` | `LM1903060128`(반도체 수명 시험, 목차 블록 교재) 430행 수식 `rac{…}` 의 `\x0c`(LaTeX `\frac` 변환 잔재) — `splitlines()` 는 이 문자를 줄 경계로 보므로 431행 이후 `record.line` = 대응 인덱스 + 1 → `apply_page_maps` 가 다음 물리 줄의 쪽을 붙인다(쪽 마지막 줄의 출현은 다음 쪽으로; 파일 마지막 줄은 502행 범위 가드에 걸려 조용히 블록 쪽 유지). 다른 85권·교과서에는 해당 문자 없음(`\r` 도 없음). `reseg_agreement` 는 쪽 등급끼리 비교라 못 잡고, `load_page_maps` 길이 검사는 `split("\n")` 기준이라 통과 | §6 에 없음 — 설계 §3.1(b) 자체가 `split("\n")` 을 명시했으나 기존 스캔의 `splitlines()` 와의 차이를 다루지 않았다 | 부분 (**G-1**, High) |
| 4.2 | D2 목록 교재(`LM1903060408`·`LM1903060424`)의 판정 출처가 설계의 `new`/`existing` 이 아니라 `real-page`(표식 블록 본문 판정, 워크북 라벨 무시) | `assign_match_grades` 593-596 `real_docs = 대응 문서 ∪ 목록 교재`; 정본 `grade_sources` NCS `existing 0`; 영향표 `real-marker-nomap` 165/135/115 → 140/185/90 (라벨 상속분이 실제 쪽 판정과 달랐다 = 그 라벨도 블록 등급) | §6 에 없음. 계획 §4 성공 기준 1 의 첫 선택지와 일치하고, 표식이 실제 쪽인 교재에 블록 라벨을 상속하면 등급 모집단이 다시 섞이므로 판단은 옳다 | 부분 (**G-2** 설계 §2·§3.3·§4 갱신 + §6 행) |
| 4.3 | `reseg_agreement` 가 CSV `출처 == "label"` 행을 뺀다 | 469-492 (480-481); 테스트가 `label` 행 제외를 고정 | §6 에 없음. `label` 쪽은 마크다운이 없던 2권의 워크북 라벨 쪽(실제 쪽 아님)이고 그 2권이 지금은 `real-page` 판정을 받으므로, 빼지 않으면 100% 가 성립할 수 없다 — 정당 | 일치 (**G-3** 설계 갱신) |
| 4.4 | `--no-page-maps` 없음 | CLI 2343-2344 에 없음; 블록 기준은 영향표 스크립트가 내부에서만 만든다 | 설계 §3.6 그대로 | 일치 |
| 4.5 | 영향표가 두 집계를 **순서**로 짝짓는다 (`_key` 로 순서·집합 동일성 검증 뒤 `enumerate`) | `compute_impact` 30-31·58-60 — 같은 줄의 같은 표현이 여럿이라 키만으로는 유일하지 않음 | 설계 §3.7 은 짝짓기 방법을 정하지 않았다; 스캔 순서가 결정론이고 검증이 앞선다 | 일치 (메모) |
| 4.6 | `AnalysisResult.run` 필드 추가 — `run_census` 가 manifest 사본(`reseg_agreement` 의 `disagree` 포함)을 붙여 `main()` 이 metrics 를 다시 찍는다 | 270행, 2325행, `main` 2364-2372 | 설계 외 추가; 해시에 들어가지 않고 산출물에 영향 없음 | 추가 (**G-9** 결정 기록) |
| 4.7 | 영향표 계보 검증이 "현 정본 `semantic_summary.json`" 이 아니라 상수 `BLOCK_BASIS_V2`(4,378/4,614/2,525) | 23-26·64-67행 | 정본 파일이 실제 쪽 기준으로 바뀐 뒤에는 파일과 비교할 수 없다 — 상수가 맞다; `test_impact_canonical_column_…` 이 상수를 `expression_review_impact.json` v2 열과 삼각 대조 | 일치 (**G-7** 설계 문구 갱신) |
| 4.8 | CLI 기본값: `--page-maps`(설계 기본 `data/markdown/ncs_paged`, 디렉터리 없으면 멈춤)·`--reseg-csv`(설계 기본 `ncs_pages_reseg.csv`) 둘 다 기본값 없음 | 2343-2344; 생략하면 `page_basis marker` / `reseg_agreement None` 으로 `EXPECTED` 가드가 막는다(2301-2306); 디렉터리가 없으면 첫 대응 교재에서 "줄→쪽 대응이 없습니다" | §6 에 없음. 정본을 대응 없이 만들 수 없다는 의도는 가드로 지켜지나 안내가 간접적 | 부분 (**G-4**) |
| 4.9 | `Facts.page_basis` 를 `Facts.run` 안이 아니라 별도 필드로 | `hwpx_results_refresh.py` 119·261 | 동등 — 설계 문구 차이 | 일치 |
| 4.10 | `apply_page_maps` 가 대응 문서의 `page is None` 레코드도 덧씌운다 (설계 "그대로") | 501-503 — 첫 표식 앞 줄도 대응에는 쪽이 있다 | §6 에 없음; 정본은 `unpaged 0` 이라 영향 0, 오히려 일관됨 | 부분 (**G-9** 설계 갱신) |
| 4.11 | 표식이 하나도 없는 NCS 문서는 대응 대상에서 제외 | `load_page_maps` 438-439 (fixture 의 빈 교재 85권 때문) | 설계는 교과서만 제외; 정본 86권은 전부 표식이 있어 영향 0 | 추가 (**G-9**) |
| 4.12 | 목록 교재 표식 검사가 "1..N 연속·중복 없음"(설계 "블록 수 == 최댓값") | 447-448 | 설계보다 엄격한 동치 이상 | 일치 (메모) |
| 4.13 | `dashboard_payload` 가 `pdf_pages` 에 없는 대응 교재를 오류로 (설계는 "없으면 표식 최댓값 — D2 교재" 로 읽혀 fallback 처럼 보임) | 1744-1745; D2 교재만 표식 최댓값 | 이전 기준 `per_book` 에 없는 대응 교재는 있을 수 없으므로 오류가 맞다 | 일치 (**G-9** 문구 정리) |
| 4.14 | 2절 "주: 단위: 건." 문단도 `page_basis` 로 분기 | `hwpx_results_refresh.py` 742-743; 테스트 554행 | 설계 §3.8 은 2절 도입·3절만 언급 | 추가 (**G-9**) |
| 4.15 | 영향표 `by_book_kind` 3분류(`real-marker-nomap` 추가)·`REAL_MARKER_RATIO 0.8`·`grade3_share` | 27·39-46·107행 | 계획 §1.3 이 "25 / 59 / 대응 없음 2" 를 명시; 0.8 은 영향표 분류용이고 정본 허용은 명시 목록만(§6-3 유지) | 일치 (**G-7** 설계 갱신) |
| 4.16 | `test_committed_summary_json_matches_expected` 가 "자동으로 새 키를 본다" 가 아니라 손으로 세 키를 더함 | 1029-1031행 | metrics 를 payload 에서 손으로 조립하는 테스트라 자동일 수 없다; 결과는 설계 의도와 같다 | 일치 (메모) |
| 4.17 | 하니스 S3n 의 "D2 교재 표식 최댓값" 이 상수 239 | `test-dashboard-data.js` 122 | 하니스는 비추적 마크다운을 읽지 못한다 — 120·119 는 원본 PDF 로 확인됨 | 일치 (메모) |

## 5. Gap 목록

| ID | 심각도 | 갭 | 조치 제안 |
|---|:---:|---|---|
| G-1 | **High** | **줄 번호 규약 불일치.** `split_pages`(393)·`_marker_values`(321)·`dashboard_payload`(1741)는 `splitlines()`, 줄→쪽 대응·`load_page_maps`(455)·`assign_match_grades` `page_lines`(603)는 `split("\n")`. 정본 코퍼스 `LM1903060128` 430행의 `\x0c` 1건으로 그 뒤 출현의 `record.line` 이 대응보다 1 크다 → 쪽 마지막 줄의 출현이 다음 쪽 등급을 받고(규모 추정: 그 교재 430행 이후 출현 중 쪽 경계 줄 — 소수, 실행으로 확정), 파일 마지막 줄은 `apply_page_maps` 502행 범위 가드가 조용히 블록 쪽에 둔다. `reseg_agreement`(쪽 등급끼리 비교)·`load_page_maps` 길이 검사·하니스 어느 것도 못 잡는다 | 구현 보강: (1) `load_page_maps` 에 `len(text.splitlines()) == len(line_pages)` 검사를 더해 어긋난 교재에서 멈추게; (2) 줄 규약을 `split("\n")` 으로 통일(`split_pages`·`_marker_values`·`dashboard_payload` — `resegment.py` 와 같은 규약; `source_sha256` 불변, `detail_sha256` 변동) 또는 `load_documents` 에서 수직 공백 문자를 정규화(`source_sha256` 변동 주의); (3) `apply_page_maps` 범위 밖 줄은 조용히 두지 말고 오류; (4) 정본 재실행 → `EXPECTED` 재고정 → 영향표·대시보드·HWPX 재생성; 회귀 테스트(`\x0c` 든 fixture) 추가 |
| G-2 | Low | D2 목록 교재의 판정 출처 `real-page`(워크북 라벨 무시) — 설계 §2 도식·§3.3·§4 는 `new`/`existing` | 설계 §2·§3.3·§4 갱신 + §6 에 "목록 교재도 real-page — 표식이 실제 쪽이라 블록 라벨 상속은 모집단을 다시 섞는다(계획 §4 성공 기준 1 첫 선택지)" 행 추가 |
| G-3 | Low | `reseg_agreement` 가 `출처 == label` 행을 제외 — 설계 §3.4 미기재 | 설계 §3.4 갱신 + §6 행("label 쪽은 실제 쪽이 아님; 그 2권은 지금 real-page 판정") |
| G-4 | Low | `--page-maps`·`--reseg-csv` 기본값 없음(설계 §3.9 는 기본값 + 디렉터리 부재 시 멈춤); 생략하면 가드가 "EXPECTED 불일치" 로 막아 안내가 간접적 | 기본값 부여(`HERE / "data/markdown/ncs_paged"`, `DEFAULT_RESEG_CSV_NAME` 경로) + 디렉터리 부재 메시지, 또는 설계를 "옵션 — 생략 시 가드가 막음" 으로 갱신 |
| G-5 | Low | 문서 잔존 구 문구: README 9행 "정본 실행(2026-09-14, `semantic_keyword_recount_20260914.xlsx`)", README 87행 "새 파일 `…_20260914_정본.hwpx`", `semantic-occurrence-grades.report.md` 50행 제목 "(정본, 2026-09-14)", data README 15행 "영향표의 `v2` 열이 정본과 같음"(총계만 같고 등급은 블록 기준 — 설계 §6-6 의 "기준 차이" 미기재). 하니스 S7 은 이 문구를 대조하지 않는다 | 문서 갱신 4곳(2026-09-15 / `…_{정본 실행일}_정본.hwpx` / "정본, 2026-09-15" / "v2 열의 총계는 정본과 같고 등급은 블록 기준 — 실제 쪽 등급은 `occurrence_real_pages_impact.json`") |
| G-6 | Low | 테스트 설계(§4) 미충족·ID 중복: 제외 레코드 쪽 덧씌우기(fixture 에 제외 레코드 없음), `run_census` 수준의 결속 불일치 거부(일반 불일치 테스트로 간접), 같은 fixture 두 번 → 같은 해시에 대응 미적용(`test_two_runs_on_same_fixture_are_identical` 미확장 — 계획 §3.2 비기능), 목록 교재 + 대응 있을 때 대응 사용, 변형 실행 + 대응; 신설 하니스 단언 `S1e`(67행)가 기존 `S1e`(69행)와 중복 | fixture 에 동음이의 제외 규칙 1건 추가, `reseg.csv` 등급을 바꿔 `run_census` `SystemExit` 단언, 두 실행 동일성 테스트에 `page_maps=` 전달, 목록 교재용 `pages.json` 을 두는 케이스, `S1e` → `S1h` 개명(CLAUDE.md 인용 없음) |
| G-7 | Low | 영향표: 추적 산출물을 `write_text` 로 직접 씀(저장소 관례 temp + `os.replace` 아님); 계보 검증이 파일 대신 상수 `BLOCK_BASIS_V2`; `grade3_share`·3분류·`_key` 순서 검증·`--school-grade-workbook` 이 설계 §3.7·§3.9 에 없음 | `SKR._write_text_atomic` 사용; 설계 §3.7 문구를 "상수 `BLOCK_BASIS_V2`(2026-09-14 정본) 와 대조" 로, 필드 목록 갱신 |
| G-8 | Low | 결속 100% 미만의 원인 안내("대응 파일이 바뀌었거나 regrade 규칙이 바뀌었다")가 docstring 에만 있고 런타임은 일반 "EXPECTED 불일치" + `main()` 의 `disagree` 목록(`--force` 실행 때만) | `run_census` 가드 출력에서 `reseg_agreement.*` 불일치면 그 문장을 덧붙이고 `disagree` 상위 몇 건을 함께 찍기 |
| G-9 | Low | 설계 외 추가·차이의 결정 기록 부재: `AnalysisResult.run`, `page is None` 레코드 덧씌움, 표식 없는 NCS 문서 skip, 2절 "주" 문단 분기, 목록 교재 표식 1..N 검사, `pdf_pages` 누락 교재 오류, `Facts.page_basis` 별도 필드 | 설계 §6 행 추가·§3.1/§3.2/§3.5/§3.8 문구 정리(문서만) |
| G-10 | Low | 영향표에 정렬 자기 검증 수치(DP 후보 줄 83.6% / ±1쪽 94.9%, 결손 제외 88.6% / 98.5%) 미병기 — 계획 §4 성공 기준 2 "±정렬 오차 범위는 영향표에 기록"·§5 위험표 | `meta.alignment_check` 로 `reseg_summary.json alignment_overall` 을 복사(입력 sha256 과 함께), 또는 계획 문구를 "TODOS 2 에 기록" 으로 정합화 |
| G-11 | Low | 비기능 "실행 시간 2배 이내" 미측정·미기록 | 정본 실행 시간을 보고서(또는 `meta.run.elapsed_s`)에 남기고 다음 실행과 비교 |

메모(조치 불필요): `reseg_agreement` 의 `included` 필터(설계 "NCS real-page 레코드")는 제외 레코드의 쪽을 빼는 합리적 좁힘; `load_page_maps` 의 `bool` 배제는 설계 (c) 의 강화; 목록 교재 `sorted(markers) == 1..N` 검사는 설계 "블록 수 == 최댓값" 의 상위 호환.

**Match Rate 산식** — 설계 §3.1~3.9·§4·§5/§6·비기능 요구를 76개 항목으로 나눠 일치 1 · 부분 0.5 · 불일치 0 으로 채점.

| 구간 | 항목 수 | 일치 | 부분 | 불일치 |
|---|:---:|:---:|:---:|:---:|
| §3.1 로딩·검증 (상수, 시그니처·반환, 코드→파일, 검증 3종, 대응 없음→목록·메시지, 목록+대응, 표식 결손 검사, `PageMapsInfo`, 교과서 무시) | 9 | 9 | 0 | 0 |
| §3.2 덧씌우기 (규칙, 호출 위치·`page_count`, `with_summary=False`, 그대로 두는 레코드, 제외 레코드) | 5 | 3 | 2 (줄 규약 G-1, `page None`) | 0 |
| §3.3 판정 (`page_lines` 대응 묶기, 나머지 현행, real-page 판정·`existing` 무시, 빈 본문 fallback·unpaged 0, `GRADE_SOURCES`·LABEL, `STRICT_GROUPS`, 캐시, 대응 없는 문서 출처) | 8 | 7 | 1 (D2 출처) | 0 |
| §3.4 결속 (함수·반환, CSV 읽기, 비교 집합, manifest·metrics·`EXPECTED`, `check_expected` 규칙, 원인 안내) | 6 | 5 | 1 (안내) | 0 |
| §3.5 쪽수 (`pdf_pages` 합·D2·교과서, `run_census` 생성, `meta.page_basis`, `meta.run.page_maps`, S3n) | 5 | 5 | 0 | 0 |
| §3.6 manifest·EXPECTED (`run_manifest`, `summary_metrics`, 재고정, 커밋 테스트, 변형 실행 대응, `--no-page-maps` 없음, 대응 없는 실행 가드) | 7 | 7 | 0 | 0 |
| §3.7 영향표 (A/B 집계, 기록 항목, 교재 종류, 본문·경로 없음, 계보 검증, 출력 경로, §1.3 실측 고정) | 7 | 7 | 0 | 0 |
| §3.8 발표면·HWPX (`realNote`, `index.html`, `Facts`·`load_facts`, 2절, 3절, 날짜 접미, 옛 대조 JSON·계보, README·CLAUDE.md·data README) | 8 | 7 | 1 (문서 잔존) | 0 |
| §3.9 CLI (`--page-maps`, `--reseg-csv`, 영향표 CLI) | 3 | 1 | 2 (기본값) | 0 |
| §4 테스트 설계 (3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 하니스, 커밋 산출물) | 10 | 6 | 4 (3.2 제외 레코드, 3.3 D2 행, 3.4 run_census 거부, 3.6 두 번 실행) | 0 |
| §5·§6·비기능 (정본 절차, §6-1 총계 불변, §6-2 상속 폐기, §6-3 명시 목록, §6-6 data README 기준 차이, gitignore·manifest·공개 경로, 결정론 테스트 확장, 실행 시간) | 8 | 5 | 3 (§6-6, 결정론 확장, 실행 시간 미측정) | 0 |
| **합계** | **76** | **62** | **14** | **0** |

(62 × 1 + 14 × 0.5 + 0) / 76 = **90.79% → 90.8%**

## 6. 계획 성공 기준 6항 체크리스트

| # | 기준 | 확인 | 결과 |
|---|---|---|---|
| 1 | 정본 재실행 가드 통과: NCS 86권, 11,517건(사전 v2), `grade_sources.NCS = {real-page: 11,517, existing: 0, new: 0}`(또는 2권 몫만 `new`), 교과서 1,207 불변 | `semantic_summary.json` `meta.run.expected true / force false / expected_mismatch []`, documents 86/9, totals 11,517/1,207, NCS `grade_sources` real-page 11,517 · existing 0 · new 0(첫 선택지), 교과서 633/459/115 불변; 코디네이터: 가드 통과, 두 번 실행 해시 동일. **단서**: G-1 이 닫히면 `LM1903060128` 의 소수 출현이 이웃 쪽으로 옮겨 grades·detail 해시가 바뀔 수 있다 | ✅ (G-1 단서) |
| 2 | 공유 쪽 등급 일치율 100%(`meta.run.reseg_agreement`), 검출 쪽 2,492(±정렬 오차 범위는 영향표에 기록) | `reseg_agreement {2035, 2035}` = `EXPECTED`; 영향표 `pages.real_pages` 2,492(84권 2,415 + 새 2권 77 은 계획 §1.3); 정렬 오차 범위는 영향표에 **없음**(TODOS 2 문장에만) — G-10 | ⚠️ 부분 |
| 3 | `groups[].pages` 합 = 9,100; 대시보드·README·CLAUDE.md·HWPX 가 같은 값 | summary/data.js 9,100(S3n), CLAUDE.md 147행 9,100, HWPX 대조 JSON 에 9,100 1회(2절 도입 "총 9,100쪽"), data README 5행 9,100, 원본 PDF 86권 합 9,100(코디네이터 검증). 대시보드 화면(`groupRows` 에 쪽수 열 없음)과 README 본문은 분야 쪽수를 인용하지 않는다(구 8,914 도 인용한 적 없음) — 인용처는 전부 같은 값 | ✅ (인용처 한정) |
| 4 | 영향표에 §1.3 이동 행렬(4,016)이 고정되고, 보고서 문구가 "21.9 → 21.7% 로 거의 같으나 구성이 바뀐다" 를 개선으로 서술하지 않음 | `transition.moved 4016` + 6칸 = 계획 §1.3; README 17행 "등급3 은 거의 그대로이고 등급1→2 이동이 큽니다", 보고서 브리지 표 67행 "가중 방식의 차이이지 교재가 나아졌거나 측정이 정밀해진 것이 아니다", CLAUDE.md 172행 "Never present … as an improvement" | ✅ |
| 5 | 하니스 전부 통과(unittest·S1~S9·R·SRI·core), `EXPECTED` 손 변경은 CI 가 잡음 | §1 하니스 표(150 OK · 71/71 · 390/390 · 24 · 32 · 38); `test_committed_summary_json_matches_expected` 가 `page_basis`·`page_maps_sha256`·`reseg_agreement` 까지 커밋 파일에서 재조립해 `EXPECTED` 와 대조(1029-1031) | ✅ |
| 6 | `TODOS.md` 2·3·1(d) 닫힘, ④ 는 결정 대기 | 17행(2 닫힘, D1~D6)·18행(3 닫힘, D5)·16행(1(d) 닫힘, D4); 22행 "④ 마커 보정과 새 2권 대응 생성(D2-B)은 그 뒤 결정" | ✅ |

## 7. 동기화 옵션 · 다음 단계

- 권고: **옵션 1(구현 보강) 을 G-1 에 먼저** — `load_page_maps` 에 `splitlines()` 길이 검사(지금 코퍼스에서 `LM1903060128` 을 잡는다) + 줄 규약 `split("\n")` 통일(또는 수직 공백 정규화) + `apply_page_maps` 범위 밖 오류 + `\x0c` fixture 회귀 테스트 → 정본 재실행(`--force` 측정 → `EXPECTED` 재고정 → 가드 실행) → 영향표·대시보드·README·CLAUDE.md·HWPX 재생성(전부 스크립트). 변동은 `LM1903060128`(반도체개발) 430행 이후 출현 중 쪽 경계 줄에 놓인 소수로 예상되며 등급 3,788/5,227/2,502 가 몇 건 움직일 수 있다 — 바뀐 값을 §1 과 성공 기준 1 에 반영할 것.
- G-2·G-3·G-7(문구)·G-9·G-10(문구 택일) 은 **옵션 2(설계 갱신)** — 설계 §2 도식·§3.3·§3.4·§3.7·§4·§6 에 결정 행 추가. G-5 는 README 2곳·보고서 제목·data README 15행 문서 갱신. G-4·G-6·G-7(원자적 쓰기)·G-8 은 소폭 구현·테스트 보강으로 산출물 숫자에 영향 없음.
- Match Rate 90.8% ≥ 90% → 형식상 `/pdca report occurrence-real-pages` 진행 가능하나, **G-1(High) 처리 후 재분석**을 권고 — 보고서의 정본 수치가 재고정 값을 인용해야 한다. 재분석 시 부분 14 → 예상 3 이하(실행 시간·문서·§6-6), Match Rate ≈ 98%.
- 이 분석은 테스트를 실행하지 않았다(코디네이터 실행 결과 인용). G-1 의 영향 건수는 수정 실행에서 확정된다.
- `[→E2E]` 한글(HWP) 렌더링(표 너비·쪽 나눔·목차 쪽수)은 자동 검증 밖(`TODOS.md` 5(c)) — 이 기능도 같다.
- 별개 결정(변경 없음): ④ 마커 ±1 보정·새 2권 대응 생성(D2-B)은 `NCS_PDF_ROOT` 로 `resegment.py` 재실행이 가능해진 뒤의 연구책임자 결정(`TODOS.md` 22행). 채택되면 `page_maps_sha256`·`reseg_agreement`·등급이 함께 바뀌므로 이 기능의 `EXPECTED` 재고정이 따른다.

## Act-1 — 갭 처리 (2026-09-15)

| ID | 처리 |
|---|---|
| G-1 | **닫힘** — 대응을 매칭 줄 규약(`splitlines`)으로 옮겨 싣는 `_to_matching_lines`(같은 쪽을 k 번, 파일 끝 개행 뒤 빈 원소 제외, 결과 길이 ≠ `splitlines` 길이면 오류) + `page_lines` 도 `splitlines` 로. 회귀 테스트 `LineConventionTests`(`\x0c` 든 fixture: 줄 4 의 출현이 쪽 10, 밀리면 20). 정본 코퍼스 실측: `LM1903060128` 430행 뒤 출현 87건 중 쪽 경계에 놓인 것 0건 → **정본 수치·해시 불변**(재실행 확인: detail `229e9a79…`, summary `282d6c22…`, reseg_agreement 2035/2035) — `EXPECTED` 재고정 없음 |
| G-2 | **닫힘** — 설계 §2·§3.3 을 "목록 교재도 `real-page`" 로, §6 결정 8 |
| G-3 | **닫힘** — 설계 §3.4 에 `label` 출처 제외 명시, §6 결정 9 |
| G-4 | **닫힘** — `--page-maps` 기본 `DEFAULT_PAGE_MAPS_DIR`, `--reseg-csv` 기본 `DEFAULT_RESEG_CSV`; `run_census` 가 대응 폴더 부재를 `FileNotFoundError`("정본은 대응 없이 만들 수 없다")로. 테스트 `test_main_defaults_to_the_paged_dir_and_reseg_csv`, 부재 케이스 |
| G-5 | **닫힘** — README 9행·87행, 등급 결합 보고서 브리지 제목, data README 15행 정정 |
| G-6 | **닫힘** — 제외·보류 레코드 덧씌우기, 목록 교재에 대응이 있을 때 대응 사용, 변형 사전(v1fix)+대응, `run_census` 결속 불일치 `SystemExit`(산출물 없음), 대응 적용 두 실행 동일 해시, 대응 폴더 부재 — `LineConventionTests` 3건; 하니스 `S1e`(신설) → `S1f` 개명 |
| G-7 | **닫힘** — 영향표 쓰기 `SKR._write_text_atomic`; 설계 §3.7 에 `BLOCK_BASIS_V2` 상수 대조·위치 짝짓기·추가 필드 기재 |
| G-8 | **닫힘** — `run_census` 가드 출력이 `reseg_agreement` 불일치면 원인 문장 + `disagree` 상위 5건을 덧붙인다 |
| G-9 | **닫힘** — 설계 §6 결정 11(설계 밖 추가 7건), §2 `facts.page_basis`, §3.1 1..N 검사 문구 |
| G-10 | **닫힘** — 영향표 `meta.alignment_self_check`(`--previous-basis` 의 `alignment_check.overall`·`hybrid_lines`: DP 후보 줄 18,142/21,711 exact·20,613 near(±1쪽), 전체 줄 25,219/32,486·29,329, 결손 제외 17,456/19,698·19,397) 병기 |
| G-11 | **닫힘** — 실측: 정본 실행 34.7 s(대응 적용) vs 34.8 s(대응 없음, 같은 입력) — 실행 시간 변화 없음(비기능 "2배 이내" 충족) |

Act-1 뒤: `python3.13 -m unittest test_semantic_keyword_recount test_expression_review test_hwpx_results_refresh` OK(154), `node outputs/test-dashboard-data.js` 71/71, `python3 outputs/test-recount-grades.py` 390/390, 영향표 재생성(수치 불변 + `alignment_self_check`). 재분석 시 부분 14 → 0, **Match Rate 100% (76/76)**.

출고 전 리뷰(2026-09-15, `/ship` Step 9 — 설계 결정 12, 전문가 6 + 레드팀 + Codex) 뒤: 같은 세 명령이 OK(175) · 79/79 · 390/390, 정본 재실행 가드 통과(수치·해시 불변; manifest 는 `real_page_marker_books` `[{code, pages}]` · 입력 7종, payload 는 `corpora.*.detected_pages` 추가 — NCS 2,492 = 영향표 `pages.real_pages`), HWPX 재생성(출력 HWPX sha 동일 `aa06344b…`, 대조 JSON 은 정본 결속·`conditions` 갱신), 영향표 스크립트 21.7 → 14.0 s(산출물 동일). 설계와 구현의 일치율은 그대로 100%.

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-15 | 초안 — 설계 76항목 채점(90.8%), 갭 11건(High 1 · Low 10), 성공 기준 6항 대조, 스키마 3종 대조 | Claude (Opus 5, bkit gap-detector) |
| 1.1 | 2026-09-15 | Act-1 — G-1~G-11 처리(줄 규약 통일·CLI 기본값·결속 안내·영향표 원자적 쓰기·정렬 수치 병기·설계/문서 갱신), Match Rate 100% | Claude (Opus 5) |
