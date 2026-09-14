# hwpx-ncs-section-refresh — 설계 대비 구현 갭 분석

> 분석일: 2026-09-14 · 브랜치 feat/semantic-expression-review · 설계 대비 구현 갭 분석 (bkit Check)
>
> **Feature**: hwpx-ncs-section-refresh
> **Plan**: `docs/01-plan/features/hwpx-ncs-section-refresh.plan.md` (Approved, FR-01~FR-12, 성공 기준 8항, 결정 D1~D5)
> **Design**: `docs/02-design/features/hwpx-ncs-section-refresh.design.md` (§3.1~3.9, §4 테스트 설계, §5 구현 순서, §6 결정 기록)
> **구현**: `hwpx_results_refresh.py` · `semantic_keyword_recount.py`(`dashboard_payload`) · `test_hwpx_results_refresh.py` · `test_semantic_keyword_recount.py` · `outputs/test-dashboard-data.js`(S3j·S3k) · `.github/workflows/test.yml`
> **산출물**: `docs/03-analysis/data/accident_case_pages.json` · `docs/03-analysis/data/hwpx_results_refresh_20260914.json` · `docs/03-analysis/hwpx-results-refresh/review.html` · `docs/03-analysis/data/semantic_summary.json`(`corpora.*.groups[].pages`, `keywords[].corpora.*.groups`) · `docs/03-analysis/data/README.md` · `CLAUDE.md` 그룹 4 · `README.md` · `TODOS.md` 5번
> **Author**: Claude (Opus 5, bkit gap-detector) — 결정: 연구책임자

---

## 1. 요약

| 항목 | 값 |
|---|---|
| **Match Rate** | **92.0%** (설계 항목 56개: 일치 48 · 부분 7 · 불일치 1 → (48 + 7×0.5 + 0) / 56 = 51.5 / 56) |
| 갭 | 🔴 누락 1 (`review_text.html`) · 🟡 부분 7 (대조 JSON `keys`·`conditions`·`cases_date`, `accident_case_pages.json` `date`, 그림 비트 깊이·magick 부재 처리, 테스트 설계 3건) · 🔵 설계 외 추가 4 (문단 45개, `--no-render`, `svg_sha256`·`output_sha256`, `event`·`kind`) |
| 판정 | Match Rate ≥ 90% → **Report 단계 진행 가능**. 갭은 전부 대조 JSON 의 기록 항목·테스트 보강·결정 기록 추가 수준이며 산출물 숫자에 영향이 없다 |
| 실문서 결과 | 문단 45 · 표 7 · 그림 3 · 숫자 토큰 715 · 미일치 0 (`hwpx_results_refresh_20260914.json` `audit.status: ok`; `source.hwpx_sha256 ad5167ea…` 가 dry run 과 같아 원본 불변) |

**하니스 (포그라운드 실행, 마지막 줄 인용)**

| 명령 | 마지막 줄 (exit) | 상태 |
|---|---|---|
| `python3 -m unittest test_hwpx_results_refresh` | `Ran 11 tests in 0.252s` / `OK` (exit 0) | ✅ |
| `python3.13 -m unittest test_semantic_keyword_recount test_expression_review` | `Ran 80 tests in 2.556s` / `OK` (exit 0) | ✅ |
| `node outputs/test-dashboard-data.js` | `결과: 67/67 PASS` (exit 0) | ✅ |
| `python3 outputs/test-recount-grades.py` | `결과: 390/390 PASS` (exit 0) | ✅ |
| `python3 hwpx_results_refresh.py --no-render --diff-out /tmp/gap_dry.json` (실문서 dry run) | `문단 45개 · 표 7개 · 그림 3개 · 숫자 토큰 715개 · 미일치 0개` (exit 0) | ✅ |

git: `git status --short` 출력 없음 — 8개 파일 모두 추적됨(변경 없음): `hwpx_results_refresh.py` · `test_hwpx_results_refresh.py` · `docs/03-analysis/data/accident_case_pages.json` · `docs/03-analysis/data/hwpx_results_refresh_20260914.json` · `docs/03-analysis/hwpx-results-refresh/review.html` · `semantic_keyword_recount.py` · `test_semantic_keyword_recount.py` · `outputs/test-dashboard-data.js`; HEAD `445d637` (docs: hwpx_results_refresh 계보 — CLAUDE.md 그룹 4·README·data README·TODOS 5번·CI); `review.html` 233,968 B (Sep 14 17:35) · 원본 `data/반도체 기초보고서_20260911.hwpx` 1,579,035 B (Sep 14 16:38, 비추적 `data/`)

## 2. FR-01~FR-12 — 설계 항목 ↔ 구현 ↔ 테스트 ↔ 상태

| FR | 설계 항목 (§) | 구현 위치 (파일:함수) | 테스트 | 상태 |
|---|---|---|---|---|
| FR-01 절 탐지 | §3.3 제목 텍스트로 절 경계, 목차 중복 건너뜀, 문단 locator 0/2+ 이면 실패 | `hwpx_results_refresh.py:locate_sections` (두 번째 "제3장 연구 결과" 이후, `HEADINGS` 시작·끝 제목, 시작 1회가 아니면 ValueError), `find_paragraph` (첫머리 prefix, 더 긴 locator 우선, 0/2+ → ValueError) | H `test_locate_sections_skips_toc_and_bounds_each_section`, `test_refresh_refuses_when_a_paragraph_is_missing` | 일치 |
| FR-02 정본 단일 출처 | §1 상수는 문장 틀·교재→분야 대응표뿐 | `load_facts` → `Facts`/`CorpusFacts`/`CaseFacts` (`semantic_summary.json`·`accident_case_pages.json`·recount `summary.json` `textbook.cases_pages`); 상수 `TEXTBOOK_AREA`, `NCS_GROUP_TO_AREA` | H `test_facts_from_canonical_files` (86/9, 2,055, 분야 권수, 13/5/3/1/2/10) | 일치 |
| FR-03 문단 템플릿·조건 분기 | §3.4 `set_text` 서식 승계, 템플릿 함수, 분기 903·913·917/1229·1139·561, 3절 재구성, D3 | `set_text` (첫 텍스트 run 의 `charPrIDRef` 승계, 텍스트 run 정리, `format_collapsed`), `textbook_paragraphs`(20)·`ncs_paragraphs`(19)·`case_paragraphs`(6), `_grade_max`·`_compare_share`·`_area_rank`·`ro`/`wa` | H `test_set_text_keeps_first_run_format_and_collapses_extra_runs`, `test_templates_branch_on_data`, `test_korean_particles` | 일치 (문단 45개 — 설계 37개보다 8개 많음, §4.5) |
| FR-04 표 7~13 | §3.5 캡션 다음 `hp:tbl`/표 13 첫 셀, 셀 텍스트만, 행·열 검사, 표 7·10 내림차순, 표 13 행 증감·renumber·판정 열 | `find_table_after_caption`, `find_table_by_first_cell`, `set_cell`, `fill_table` (행·열 불일치 ValueError), `keyword_table_rows` (`ranked()`), `area_table_rows`, `grade_table_rows`, `case_table_rows`, `resize_table`/`renumber_table` | H `test_resize_table_grows_by_cloning_last_row_and_renumbers`, e2e (표 10 첫 행 안전·합계, 표 13 2+13행·"판정") | 일치 |
| FR-05 그림 2~4 | §3.6 SVG → magick PNG24/BMP3, 크기는 BinData 헤더, 색 고정, sha256 기록 | `image_dimensions`, `grade_bars_svg`, `area_bars_svg`, `render_svg` (`-font` AppleGothic 고정, 결과 크기·형식 검증), `figure_specs`, `find_picture` (그림 3·4 캡션 앞, 그림 2 `binaryItemIDRef=image1`) | H e2e (magick 있을 때 70×39 PNG·116×75 BMP 교체 확인) | 부분 (비트 깊이 미검사·미기록, magick 부재 시 자동 skip 대신 예외 + `--no-render`; `svg_has_all_values` 없음) |
| FR-06 원본 보존 | §3.7 새 이름, 임시 파일 + `os.replace`, 같은 경로·기존 파일 거부 | `write_hwpx` (`.tmp` → `os.replace`, 같은 경로 ValueError, 존재 시 `--force` 없으면 FileExistsError), `DEFAULT_OUT` `…_20260914_정본.hwpx` | H e2e (FileExistsError·ValueError) | 일치 |
| FR-07 부수 손상 방지 | §3.7 1~3절 밖 노드·ZIP 항목 바이트 동일 | `refresh` (절 밖 최상위 문단 `ET.tostring` 비교 → 다르면 RuntimeError, 쓰기 전), `write_hwpx` (교체 항목 외 `zin.read` 그대로, 순서·압축 방식 유지) | H e2e (namelist·header.xml·mimetype 압축 방식, 서론·4절 문장 보존) | 일치 (fixture 에 content.hpf·image4~6 은 없음 — 구조상 바이트 복사) |
| FR-08 변경 대조 JSON | §3.8 문단/셀 구 값·새 값·정본 키·조건 결과, 본문 없음 | `refresh` → `diff` (`source`, `output`, `paragraphs[]{section, locator, old_numbers, new_numbers, format_collapsed}`, `tables[]`, `figures[]`, `audit`, `output_sha256`) | H `CommittedDiffTests.test_committed_diff_json`, e2e (본문·절대 경로 없음) | 부분 (`keys`·`conditions`·`source.cases_date` 없음, §3) |
| FR-09 숫자 감사 | §3.8 토큰 정규식, 정본 값 집합, 허용 목록, 미일치 시 exit 1 | `NUMBER_TOKEN`, `Facts.all_numbers`, `ALLOWED_TOKENS`, `STRIP_BEFORE_AUDIT`, `audit_numbers`, `section_texts`; `refresh` 는 미일치면 HWPX 를 쓰지 않고 `main` 이 1 반환 | H `test_audit_flags_stale_numbers_and_accepts_canonical_ones`, `test_templates_branch_on_data` (템플릿 출력 전부 정본 값) | 일치 |
| FR-10 D1·D2 정본 확장 | §3.1 `groups[].pages`·`keywords[].corpora.*.groups`, 가드 통과 재실행, S3 대조 | `semantic_keyword_recount.py:dashboard_payload` (`pages_by_group` = 문서별 `max(block.page)` 합, 키워드×그룹 목록 — 그룹 순서 동일); `summary_payload` 가 포함 | T `test_summary_payload_has_keyword_groups_and_group_pages`; S `S3j`(키워드×그룹 합)·`S3k`(pages > 0, 교과서 합 = recount 2,055) | 일치 (신설 단언 ID 가 기존 S3j·S3k 와 중복 — G-9) |
| FR-11 검토 HTML | §3.8 `docs/03-analysis/hwpx-results-refresh/review.html` 표 7~13·그림 3장, 본문 없음 | `write_review` (표 7행 세트 + BMP→PNG data URI), 감사 통과 시에만 | — (파일 존재·크기만 확인; 내용은 표·그림) | 일치 (계획 FR-11 의 경로 `hwpx-ncs-section-refresh/` 는 설계 §3.8 이 바꿈; 구/신 병기본은 §3 참조) |
| FR-12 사고사례 | §3.2 13행 == CSV 13쪽, 집계 2/1/10, 파생 수치가 3절·표 13·2절 장비 문단에 사용 | `accident_case_pages.json` (13행), `load_facts` → `CaseFacts` (flagged 13, books 5, top_book 8쪽, narrative 3, industrial_events 1, industrial_books 2, false_positive 10, `fp_kinds` 6/1/3), `case_paragraphs`, `case_table_rows`, `ncs_paragraphs` 장비 문단 | H `test_pages_match_reseg_csv_and_verdict_counts`, `test_facts_from_canonical_files` | 일치 |

## 3. 스키마 대조 — 설계 §3.2 · §3.8 vs 실제 파일

### 3.1 `docs/03-analysis/data/accident_case_pages.json` (설계 §3.2)

| 키 | 설계 | 실제 | 판정 |
|---|---|---|---|
| `source` | 있음 | 있음 (판정 출처 + CSV, 날짜 "2026-09-06" 은 이 문자열 안에) | 일치 |
| `date` | `"2026-09-06"` | **없음** | 누락 (G-5) |
| `unit` | — | 추가 ("재세그먼트 실제 PDF 쪽 …") | 추가 (유용) |
| `verdicts` | case / case_other / false_positive | 같음 (설명 문구만 다름) | 일치 |
| `pages[].book/title/area/page/old_label/gist/verdict` | 있음 | 있음 (13행) | 일치 |
| `pages[].event` | — | 추가 (`gumi-hf-2012`·`pangyo-vent-2014`) — `industrial_events` 계산 근거 | 추가 (파생 수치에 필요) |
| `pages[].kind` | — | 추가 (`definition`/`guideline`/`property`) — 오탐 6·1·3 계산 근거 | 추가 (파생 수치에 필요) |
| `gist` 길이 | 10~15자 | 최대 28자 (테스트 상한 30), 본문 인용 없음 | 일치 (상한만 완화 — G-10 에 기록) |

### 3.2 `docs/03-analysis/data/hwpx_results_refresh_20260914.json` (설계 §3.8)

| 키 | 설계 | 실제 | 판정 |
|---|---|---|---|
| `source.hwpx_sha256` | 있음 | 있음 (`ad5167ea…`) | 일치 |
| `source.summary_run` | meta.run 요약 | `generated_at`·`git_commit`(ff56366)·`dictionary`(v2)·`expected`(true) | 일치 |
| `source.cases_date` | 있음 | **없음** | 누락 (G-5) |
| `source.hwpx`, `output`, `output_sha256` | — | 추가 (입력 파일명, 출력 파일명, 출력 sha256) | 추가 |
| `paragraphs[].section/locator/old_numbers/new_numbers/format_collapsed` | 있음 | 있음 (45건; locator ≤ 50자, 본문 없음) | 일치 |
| `paragraphs[].keys` | `["corpora.NCS.total", …]` | **없음** | 누락 (G-2) |
| `paragraphs[].conditions` | `{"psm_all_grade3": false}` 등 | **없음** | 누락 (G-1) |
| `tables[].caption/rows/cols/changed_cells` | 있음 | 있음 (+`section`); 표 13 `cols: 2` 는 병합된 캡션 행 기준 오기록 (데이터 행 5열) | 일치 (G-8) |
| `figures[].item/size/sha256` | 있음 | `item`·`width`·`height`·`sha256` (+`label`·`caption`·`entry`·`format`·`svg_sha256`) | 일치 (`size` → `width`/`height`) |
| `audit.tokens/unmatched` | 있음 | 있음 (+`status`) — 715 / [] / ok | 일치 |

## 4. 설계와 다르게 구현된 점 — 판단

| # | 차이 | 근거 (구현·산출물) | §6 결정 기록으로 정당화되는가 | 판정 |
|---|---|---|---|---|
| 4.1 | 그림 2 를 캡션이 아니라 `binaryItemIDRef=image1` 로 탐지 | `figure_specs` 첫 항목 `caption: None, item: "image1"`; `find_picture` 의 item 분기; 대조 JSON `figures[0].caption: null` — 1절에는 "그림 2." 캡션 문단이 없다 | §2 아키텍처가 `FIGURES: [binaryItemIDRef → …]` 로 이미 item 기반을 명시 — 정당화됨 (§6 행은 없음) | 일치 |
| 4.2 | 구/신 문장 병기본 `data/hwpx-results-refresh/review_text.html`(비추적) 미생성 | `write_review` 는 표·그림만; `data/hwpx-results-refresh/` 디렉터리 없음 | §6 에 없음. 계획 §5 위험표("문장 템플릿이 원문 뉘앙스를 바꿈")의 완화책이었다 | 불일치 (G-3) |
| 4.3 | 표 13 마지막 열 "문장 수(글자 수)" → "판정", 13행 | `fill_table(tbl13, rows13, 2, header=[…, "판정"])`, `VERDICT_LABEL`; 대조 JSON 표 13 rows 15 | §6 "표 13 판정 열" — 정당화됨 | 일치 |
| 4.4 | `--no-render` 옵션 (magick 없는 환경의 점검용; 그림·검토 HTML·실출력 HWPX 를 쓰지 않음) — 설계 §3.6 은 "magick 없으면 그림 단계 skip + 경고" | `main` 의 `--no-render` 분기 (temp 출력, `render=False`); `render_svg` 는 magick 부재 시 RuntimeError | §6 에 없음. 조용한 부분 출력 대신 명시적 옵션 — 의도(실문서 실행에는 필수)는 지켜지고 더 엄격 | 일치 (결정 기록 추가 권고 G-10; 기본 `--diff-out` 덮어쓰기 위험은 G-4) |
| 4.5 | 문단 45개 (1절 20 · 2절 19 · 3절 6) — 설계 §5 는 37개(13·18·6) | `textbook_paragraphs` 20건·`ncs_paragraphs` 19건; 대조 JSON 45건. 추가 8건은 계획 실측표에 없던 숫자 문단(교과서 "따라서 제조 분야는…" 의 작업환경 20→28 등, NCS "그러나 등급별 분석에서는…" 의 제조 사고사례 14→0) | §6 에 없음. FR-09(1~3절 숫자 토큰 전수 감사)를 지키려면 필요했던 확장 | 추가 (설계 갱신 권고 G-10) |
| 4.6 | 렌더 결정론은 sha256 기록만 (두 번 실행 동일성 테스트 없음) | `figures[].svg_sha256`(SVG 문자열, magick 무관)·`sha256`(렌더 결과)·`output_sha256` 기록; `FONT` 고정 | §3.6 자체가 "테스트는 크기·형식·비트 깊이만, sha256 은 기록" 으로 한정 — 정당화됨 | 일치 (선택: fixture 2회 실행 동일성 테스트, G-7) |
| 4.7 | 검토 HTML 경로 `docs/03-analysis/hwpx-results-refresh/` (계획 FR-11 은 `hwpx-ncs-section-refresh/`) · 출력 파일명 `_20260914_정본.hwpx` (계획 FR-06 은 `_20260914_NCS정본.hwpx`) | `DEFAULT_REVIEW_DIR`, `DEFAULT_OUT` | 설계 §3.8·§6 "출력 파일명" 이 계획을 갱신 — 정당화됨 (계획 문구만 구식) | 일치 |
| 4.8 | 표 13 행 내 순서: 판정군 안에서 교재명·쪽 순 정렬 (설계 "JSON 순서") | `case_table_rows` 의 `sorted(key=(verdict, title, page))` — 오탐군에서 리소그래피 69 → 트랙 78 → 포토 67 | 판정군 순서(실제 사고 → 산업재해 아님 → 오탐)는 지켜짐; 군 내 정렬은 재현 가능 | 일치 (메모) |
| 4.9 | 하니스 신설 단언 ID `S3j`·`S3k` 가 기존 `S3j`(manifest 해시)·`S3k`(명령) 와 중복; 설계 §3.1·§4 는 `S3h`(이미 "중복 제거" 가 사용) | `outputs/test-dashboard-data.js` 118~123행 | — | 부분 (G-9) |

## 5. Gap 목록

| ID | 심각도 | 갭 | 조치 제안 |
|---|:---:|---|---|
| G-1 | 중 | 대조 JSON 에 `paragraphs[].conditions`(서술 조건 참/거짓) 없음 — FR-08·성공 기준 8 의 전반부 미충족. 조건은 템플릿 안 지역 변수(`psm_all3`, `ppe23`, `gmax`, `equip_rel`, `safety_rank`)로만 존재 | 템플릿이 `(prefix, text, conditions)` 를 돌려주게 하고 `refresh` 가 `conditions` 로 기록; `CommittedDiffTests` 에 `psm_all_grade3 == False`·`ppe_grade23_over_60 == True` 단언 |
| G-2 | 중 | `paragraphs[].keys`(정본 키 경로) 없음 — `docs/03-analysis/data/README.md` 는 "구/신 숫자 목록·출처" 라고 적어 실제보다 넓게 서술 | (a) 템플릿마다 사용 키 목록을 함께 돌려줘 기록, 또는 (b) 설계 §3.8·README 문구를 "구/신 숫자 목록" 으로 낮춤 — 연구책임자 선택 |
| G-3 | 중 | 구/신 문장 병기본 `data/hwpx-results-refresh/review_text.html`(비추적) 미생성 — 계획 위험표의 완화책 | `--review-text PATH` 옵션으로 `data/` 아래에 쓰거나(추적 금지, `data/` 는 이미 gitignore), §6 에 "미생성 — 원본/신규 HWPX 를 한글에서 직접 대조" 로 결정 기록 |
| G-4 | 중 | `--no-render` 가 `--diff-out` 을 안 주면 기본값(추적 `hwpx_results_refresh_20260914.json`)에 `sha256` 없는 dry-run 대조를 덮어쓴다 → `CommittedDiffTests` 실패·정본 대조 손상. 저장소 관례(`resegment.py --limit`, 변형 사전 실행은 추적 경로 거부)와 어긋남 | `--no-render` 이면 `--diff-out == DEFAULT_DIFF` 를 거부하거나 temp 로 우회; 대조 JSON 도 `_write_text_atomic` 식 임시 파일 + `os.replace` 로 쓰기; 테스트 추가 |
| G-5 | 하 | `accident_case_pages.json` 에 `date` 키 없음(문자열 안에만) · 대조 JSON `source.cases_date` 없음 | `"date": "2026-09-06"` 추가, `refresh` 가 `source.cases_date` 로 복사 |
| G-6 | 하 | BMP 24bit 미검사·미기록 (`image_dimensions` 가 `biBitCount` 를 읽지 않음; `-type TrueColor` 로 24bit 가 기대될 뿐) — 성공 기준 4 의 "24bit" | BMP 헤더 offset 28 의 `<H` 를 읽어 24 확인, `figures[].bits` 기록, e2e 단언 |
| G-7 | 하 | 설계 §4 테스트 3건 미충족: 조건 분기 양쪽 문장(현재는 데이터와 일치하는 한 분기만), `borderFillIDRef` 불변 단언, `svg_has_all_values` | `Facts` 사본의 공정안전관리 등급3·보호구 등급을 바꿔 양 분기 실행; `fill_table` 전후 `borderFillIDRef`·`cellSpan` 목록 비교; SVG 문자열에 `fmt(값)` 전부 포함 단언 (선택: fixture 2회 실행 `section0.xml` 동일성) |
| G-8 | 하 | 대조 JSON 표 13 `cols: 2` — 병합된 캡션 행 기준 (데이터 행은 5열) | `cols` 를 첫 데이터 행 기준으로 기록 |
| G-9 | 하 | 하니스 단언 ID 중복 (`S3j`·`S3k` 각 2회) | 신설 두 건을 `S3l`·`S3m` 으로 개명, 설계 §3.1·§4 와 `CLAUDE.md` 의 "S3j/S3k" 인용 갱신 |
| G-10 | 하 | 결정 기록(§6) 누락: `--no-render` 도입, 그림 2 item 탐지, 문단 37→45, `review_text.html` 미생성 여부, `gist` 상한 30자, `event`·`kind` 키 | 설계 §6 에 행 추가 (문서 갱신만) |
| G-11 | 하 | 계획 §2.2 "2장 5절 방법론의 수치는 대조 JSON 에 '범위 밖 구 수치' 로 기록" 미구현 — `TODOS.md` 5(a) 로 이월됨 | 계획 문구를 "TODOS 5(a) 이월" 로 정합화하거나 `audit` 에 `out_of_scope` 목록 추가 |

메모(조치 불필요): `find_paragraph`·`locate_sections` 실패는 ValueError 트레이스백으로 종료(exit 1 은 맞으나 안내 문구형은 아님); `render_svg` 는 요청 크기·형식과 다르면 RuntimeError 로 막는다(설계보다 엄격).

**Match Rate 산식** — 설계 §3.1~3.9·§4·§5/§6·비기능 요구를 56개 항목으로 나눠 일치 1 · 부분 0.5 · 불일치 0 으로 채점.

| 구간 | 항목 수 | 일치 | 부분 | 불일치 |
|---|:---:|:---:|:---:|:---:|
| §3.1 D1·D2 (pages, 키워드×그룹, 가드 통과 재실행, S3, T 테스트) | 5 | 5 | 0 | 0 |
| §3.2 사고사례 데이터 (스키마, gist, CSV 대조 테스트, 파생 수치) | 4 | 3 | 1 (스키마 `date`) | 0 |
| §3.3 절 탐지 (경계, locator 실패) | 2 | 2 | 0 | 0 |
| §3.4 문단 (set_text, 템플릿, 분기 5종, 3절 재구성, D3, D2 쪽수) | 6 | 6 | 0 | 0 |
| §3.5 표 (탐지, set_cell 검사, 표 7·10, 8·11, 9·12, 13, 주 1257) | 7 | 7 | 0 | 0 |
| §3.6 그림 (렌더·크기, 내용, 색·sha256·테스트·magick 부재) | 3 | 2 | 1 (비트 깊이·skip) | 0 |
| §3.7 ZIP (재작성, 거부 규칙, 불변 테스트) | 3 | 3 | 0 | 0 |
| §3.8 대조 JSON·검토 HTML·감사 (source, paragraphs, tables, figures, audit, review.html, review_text.html, 감사 규칙) | 8 | 5 | 2 (`source`, `paragraphs`) | 1 (`review_text.html`) |
| §3.9 문서·계보 (data README, CLAUDE.md, TODOS) | 3 | 3 | 0 | 0 |
| §4 테스트 설계 (FR-10, 12, 01, 03, 04, 05, 06·07, 08·09, e2e, 커밋 산출물) | 10 | 7 | 3 (FR-03 양분기, FR-04 borderFill, FR-05 svg) | 0 |
| §5·§6·비기능 (출력 파일명, 표 13 판정 열, CI 등록, 결정론, 의존·보안) | 5 | 5 | 0 | 0 |
| **합계** | **56** | **48** | **7** | **1** |

(48 × 1 + 7 × 0.5 + 1 × 0) / 56 = **91.96% → 92.0%**

## 6. 계획 성공 기준 8항 체크리스트

| # | 기준 | 확인 | 결과 |
|---|---|---|---|
| 1 | 새 HWPX 2절 숫자 = 정본 (86권 · 11,517 · 4,378/4,614/2,525 = 38.0/40.1/21.9% · 분야 30/13/19/24권 · 1,110/1,328/3,239/5,840 · 표 10 합계 11,517 · 안전 3,929 · 위험 1,272 · 화학물질 1,080 · 보호구 965) | 대조 JSON `new_numbers`: "NCS 기반…" 86·11,517; "등급 2는…" 4,378·4,614·2,525·40.1%; "등급 3은…" 21.9%; "사고 관련…" 1,272·1,080·965; 분야 문단 30·13·19·24; "교과서의 전체 키워드 중 ‘안전’이" 3,929. 분야 총계 1,110/1,328/3,239/5,840 과 38.0% 는 표 11·12 셀(대조 JSON 은 셀 값을 담지 않음) — `area_table_rows`/`grade_table_rows` 가 `semantic_summary.json` `corpora.NCS.groups`·`grades` 에서 직접 채우고 감사 미일치 0 | ✅ |
| 2 | 숫자 감사 통과 — 구 수치(12,875 · 4,259 · 85종 · 7,769 · 813 · 3,405 · 5,581 등) 0건 | `audit.tokens 715, unmatched [], status ok`; dry run 재현 동일; `old_numbers` 에만 12,875·4,259·85·7,769·3,405·2,228 등장 | ✅ |
| 3 | 표 10·11·12 행·열·병합 구조 동일, 표 10 내림차순 | rows 32/6/5 · cols 6/8/4 (`fill_table` 이 행·열 불일치면 실패, 병합·`cellSpan` 은 손대지 않음); `ranked()` 내림차순, e2e 첫 행 안전 | ✅ |
| 4 | 그림 3·4 BMP 1160×750 · 1160×724 · 24bit 교체, 캡션 문단 그대로 | `figures[]` BMP 1160×750 · 1160×724, sha256 기록; 캡션 문단은 템플릿 대상이 아니라 불변 (절 밖 가드는 아니지만 `find_picture` 는 읽기만). **24bit 는 기록·검사 없음** (G-6) | ⚠️ 부분 |
| 5 | 2절 밖 모든 노드·ZIP 항목 바이트 동일, 원본 mtime·sha256 불변 | `refresh` 절 밖 문단 `ET.tostring` 가드(쓰기 전 RuntimeError); `write_hwpx` 는 원본을 읽기만; `source.hwpx_sha256 ad5167ea…` 가 커밋 JSON 과 dry run 에서 동일 | ✅ |
| 6 | 테스트 통과 (`test_hwpx_ncs_section_refresh.py` → 실제 이름 `test_hwpx_results_refresh.py`), 기존 하니스 통과, S3 대조 추가 | §1 하니스 표 (11 테스트 OK; S3j·S3k 추가; CI `test.yml` 69행에 등록) | ✅ |
| 7 | 대조 JSON·검토 HTML 추적, 본문 문장·절대 경로 없음 | `git status` (§1); `CommittedDiffTests` (`/Users/` 없음, locator ≤ 50자); `review.html` 은 표·그림만 | ✅ |
| 8 | 서술 조건 분기 결과가 대조 JSON 에 기록되고, 거짓이 된 문장("모두 등급 3")은 새 문장으로 | 교체 ✅ — 공정안전관리 7건 중 등급3 5건 → `psm_all3 False`, "한편 ‘공정안전관리’는 총" `new_numbers` 7·2·5·71.4%; 보호구 75.5% ≥ 60% → "60%를 넘었다" 유지. **기록 ✗** — `conditions` 키 없음 (G-1) | ⚠️ 부분 |

## 7. 동기화 옵션 · 다음 단계

- 권고: **옵션 1(구현 보강) + 옵션 2(설계 갱신) 병행** — G-1·G-2·G-4·G-5·G-8 은 `hwpx_results_refresh.py` 소폭 수정(대조 JSON 필드 추가·dry-run 경로 가드·원자적 쓰기)과 테스트 보강(G-6·G-7·G-9), G-3·G-10·G-11 은 설계 §6·계획 문구 갱신으로 닫힌다. 산출물 숫자(HWPX·검토 HTML)는 바뀌지 않는다.
- Match Rate 92.0% ≥ 90% → `/pdca report hwpx-ncs-section-refresh` 진행 가능. 보고서에는 §4.5(문단 45개)·§4.2(병기본 미생성)·성공 기준 4·8 의 부분 충족을 그대로 적을 것.
- `[→E2E]` 한글(HWP) 렌더링 — 표 너비·쪽 나눔·목차 쪽수는 자동 검증 밖 (`TODOS.md` 5(c)).

## Act-1 — 갭 처리 (2026-09-14)

| ID | 처리 |
|---|---|
| G-1 | **닫힘** — 템플릿이 `(prefix, text, conditions)` 를 돌려주고 대조 JSON `paragraphs[].conditions` 에 기록(`psm_all_grade3` false, `ppe_over_60pct` true, `safety_top_grade`, `equipment_safety_rank`, `materials_is_top`, `areas_without_cases` …). 테스트 `test_conditions_branch_both_ways`(공정안전관리·보호구 양 분기), `CommittedDiffTests` |
| G-2 | **닫힘** — `Facts.value_index()`(정본 값 → 키 경로 역색인)로 `paragraphs[].keys` 자동 산출; 등급 번호 같은 작은 수는 제외. data README 문구 정합 |
| G-3 | **닫힘** — `write_text_review` → `data/hwpx-results-refresh/review_text.html`(비추적, `--text-review-dir`) |
| G-4 | **닫힘** — `--no-render` 는 기본 대조 경로를 temp 로 우회하고 `docs/` 경로가 명시되면 거부(`SystemExit`). 테스트 `test_no_render_never_writes_the_tracked_diff` |
| G-5 | **닫힘** — `accident_case_pages.json` `date` 2026-09-06, 대조 JSON `source.cases_date` |
| G-6 | **닫힘** — `image_bits()`; BMP 24bit 검사(`render_svg`)·`figures[].bits` 기록 |
| G-7 | **닫힘** — 조건 양 분기·`borderFillIDRef`/`cellSpan`/`cellSz` 불변·`svg_has_all_values` 테스트 추가 (14 tests) |
| G-8 | **닫힘** — 표 `cols` 를 첫 데이터 행 기준으로 기록(표 13: 5) |
| G-9 | **닫힘** — 하니스 신설 단언 `S3l`·`S3m` 으로 개명, CLAUDE.md 인용 갱신 |
| G-10 | **닫힘** — 설계 §6 에 결정 9행 추가(그림 2 탐지·문단 45·`--no-render`·keys/conditions·병기본·JSON 키·범위 밖 기록·렌더 결정론) |
| G-11 | **닫힘** — `audit.out_of_scope` 로 2장 5절 정본 밖 숫자 기록(정본 실행 0건), 계획 §2.2 문구 정합 |

Act-1 뒤: `python3.13 -m unittest test_semantic_keyword_recount test_expression_review test_hwpx_results_refresh` OK(62+16+14), `node outputs/test-dashboard-data.js` 67/67, `python3 outputs/test-recount-grades.py` 390/390, 실문서 재실행 `문단 45개 · 표 7개 · 그림 3개 · 숫자 토큰 715개 · 미일치 0개`. 재분석 시 부분 7·불일치 1 → 0, Match Rate 100 % (56/56).

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-14 | 초안 — 설계 56항목 채점(92.0%), 갭 11건, 성공 기준 8항 대조 | Claude (Opus 5, bkit gap-detector) |
| 1.1 | 2026-09-14 | Act-1 — G-1~G-11 처리 기록 | Claude (Opus 5) |
