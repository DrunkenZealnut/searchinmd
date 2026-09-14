# 설계-구현 갭 분석 — semantic-recount-remediation

> **Feature**: semantic-recount-remediation
> **분석일**: 2026-09-14 · **분석자**: bkit gap-detector (Claude) · 설계 v1.1 · 계획 v1.1
> **설계 항목 구현률 (Match Rate)**: **96%** (99항목 중 일치 91, 부분 7, 설계와 다름 1)
> 하니스 실측: `python3.13 -m unittest test_semantic_keyword_recount` **39 OK** · `outputs/test-recount-grades.py` **385/385** · `outputs/test-dashboard-data.js` **62/62** · `test-search-equivalence.js` 24/24 · `run-core-logic-tests.js` 32/32 · `test-sri.js` 38/38

## 1. 요약

| 항목 | 값 |
|---|---|
| 설계 항목 구현률 | **96%** |
| 갭 | **11건** — High 0 · Medium 2 · Low 9 |
| 계획 §4 성공 기준 12항 | 충족 10 · 부분 2 (8항 grep 문맥, 11항 잔존 문구) |
| 판정 | 설계와 구현이 잘 일치한다. Medium 2건은 모두 CLAUDE.md 문서 표류(수치 1·서술 1)이며 코드·산출물 갭은 없다. |

핵심 사실: 정본 실행(`git 6021edd`, `2026-09-14T07:56:12+09:00`)이 xlsx·report md·`semantic_recount_data.js`·`semantic_summary.json`·분리 HTML 3건에 같은 manifest 를 남겼고, `EXPECTED` 는 `None` 없이 고정(NCS 12,506 / 교과서 1,293 / 미확정 0 / `unpaged-context` 1), 가드 통과 실행(`expected: true, force: false, mismatch []`)이 커밋 대상이다. `data_source/markdown` 에 `<!-- page: 0 -->` 0곳, 새 2권 마커 120·119, 첫 마커 1 — 직접 grep 으로 확인.

## 2. FR 별 대조표

| FR | 설계 항목 | 구현 위치 | 상태 | 근거 |
|---|---|---|---|---|
| FR-01 | LM 코드 필수·중복 제거·`REPORT_PATH_RE` 삭제, 문서 86 | `semantic_keyword_recount.py` `select_ncs_documents`, `run_census` | 일치 | `_NCS_CODE_RE` 없으면 ValueError; dedup 키 `(-마커수, " " in path, path)`; `grep REPORT_PATH_RE` 코드 0곳(테스트만); `meta.run.dedup` = LM1903060205 1건; S3e 86/9 |
| FR-01a | 마커 1-based 통일, 최솟값 1 | `shift_page_markers.py`, `check_marker_base` | 일치 | 두 파일 마커 120/119, 3행째 `<!-- page: 1 -->`; 코퍼스 전체 `page: 0` 0건; R8k~R8p 통과 |
| FR-01b | `/data_source/` gitignore | `.gitignore:43` | 일치 | `git status` 에 data_source 0건 |
| FR-02 | 미확정 → 문맥/등급1, `grade_unpaged`=0 | `assign_match_grades`(docstring 승인 근거), `EXPECTED["grades"][*]["unpaged"]=0` | 일치 | summary `unpaged-context` 1 / fallback 0; S3b·S3g |
| FR-03 | `EXPECTED`+`check_expected`+`--force` | `EXPECTED`, `check_expected`, `run_census` | 일치 | `None` 0개(`test_expected_block_is_fully_pinned`); 불일치 시 `SystemExit(1)` 전 파일 부재 확인; documents 검증은 force 우회 불가 |
| FR-04 | manifest 5곳 기록 + 결정론 테스트 | `run_manifest`, `public_path`, `write_workbook`, `write_report`, `write_dashboard_data` | 일치(부분 1) | xlsx 입력정보·report `## 실행 정보`·summary `meta.run`·data.js 1행 모두 `07:56:12`/`6021edd`; 결정론 테스트에 `write_workbook` 2회 비교 없음(G4) |
| FR-05 | 7종 한 실행 | `run_census`, `main` `--summary-out/--analysis-dir/--previous-basis/--force` | 일치 | `write_analysis_pages` 가 `export_keyword_outputs.py` 흡수(파일 삭제 확인); S2a deep-equal; S6a~e |
| FR-06 | 구 수치 "이전 값" 문맥 밖 0 | 발표면·semantic PDCA 8문서 | 부분 | 발표면·semantic 문서는 0회(S5f·S7c); hwpx-* 문서 5건·`docs/superpowers/specs/2026-09-08-…md:22`·evidence.json 잔존(G11); CLAUDE.md `20.6%`(G1) |
| FR-07 | 이전 기준 병기 + 브리지 표 | `semantic_grade_dashboard.js` `bridge()`, `index.html`, `textbook.html`, README, report §브리지 | 일치 | S1p·S4a~d·S5c·S5e·S7b; 고정 문장 렌더러·보고서 양쪽 존재 |
| FR-08 | CLAUDE.md 예외 승인 | `CLAUDE.md` Safety Grading Scheme | 일치(수치 1 stale) | 예외 문단 존재; 예시 수치 20.6% 는 폐기 실행값(G1) |
| FR-09 | 하니스 교차검증, 하드코딩 단언 0 | `outputs/test-dashboard-data.js` S1~S9 | 일치(부분 1) | 모든 단언이 `S`/`R` JSON 기준; `known()` 미복원(G9) |
| FR-10 | 구산출물 정리·analysis 해시 | `data/archive/2026-09-semantic-pre-remediation/`, `git status` `D` 3건 | 일치 | `semantic-keyword-recount.analysis.md` 해시 4종 = `EXPECTED` |
| FR-11 | m1·m2·m3·m5 | `write_report`, `write_analysis_pages`, 렌더러; index.html dead script 삭제(S5h); plan 1.1 승인자; 두 analysis "설계 항목 구현률" | 일치(부분 1) | occurrence-grades plan 은 버전 이력 절 없이 표 안 표기(G8) |

## 3. 설계 §3.x 세부 대조

- **§3.1 코퍼스 규칙 — 6/6 일치.** `select_ncs_documents`(ValueError·DedupRecord), `check_marker_base`, 89 하드코딩 → `EXPECTED["documents"]`(force 비우회), `PAGE_MARKER_RE` = `page_utils` 패턴을 `^\s*…\s*$` 로 감싼 것.
- **§3.2 마커 시프트 — 7/8 (설계와 다름 1, G3).** CLI·바이트 보존·거부 3종·출력·절차 기록 일치. 설계의 "마커가 줄 중간에 있음 → 거부"는 구현에서 "inline 마커는 세지도 바꾸지도 않고 standalone 만 시프트"로 달라졌다(R8k 가 고정).
- **§3.3 EXPECTED — 5/6 (G6).** 키·값 전부 고정(`None` 0). `candidates` 하위 키가 설계 `absent` 대신 `not-found`(기존 명명 유지, 합 100 = 75+19+2+4).
- **§3.4 manifest — 4/5 (G4).** `run` 키 11개 전부 + `xlsx` 추가. 결정론 테스트에 `write_workbook` 2회 시트 비교 없음.
- **§3.5 summary — 4/5 (G5).** 스키마 일치, S2a deep-equal, S3i 로 절대 경로·본문 부재. `previous_basis` 에 `date` 없음, `unit` 추가; 렌더러가 "2026-09-06" 하드코딩.
- **§3.6 산출물 7종 — 7/7.** 정본 명령 README = `meta.run.command`(20260914). 옛 날짜 HTML 2건 `git rm`.
- **§3.7 발표면 — 16/19 (G1, G7, G8).** index.html `.ctn`·template·출처·dead script 삭제, textbook 비교표 라벨, README 6곳, CLAUDE.md 예외·절·트랩·Testing·Coverage, PDCA 정본값·승인·해시 — 일치. 잔여: CLAUDE.md 20.6%(G1), index.html 산문 절 제목 라벨(G7), occurrence-grades plan 제외 항목·버전 이력·design §8 문구(G8).
- **§3.8 하니스 — 10/11 (G9).** S1 17 · S2 3 · S3 15 · S4 4 · S5 10 · S6 5 · S7 5 · S8 2 · S9 1 = 62. `known()` 미복원.
- **§3.9 브리지 표 — 3/3.** 렌더러·보고서 7행 + 등급1·2 행(9행), 고정 문장 동일.
- **§3.10 정리 — 5/5 · §3.11 미커밋 diff — 4/4.**

## 4. 계획 §4 성공 기준 실측

| # | 기준 | 결과 | 근거 |
|---|---|---|---|
| 1 | 문서 86, 중복 0, `REPORT_PATH_RE` 0, 마커 없는 파일은 중복 1뿐 | 충족 | `meta.run.inputs` NCS 86, dedup 1; grep 코드 0곳 |
| 2 | `page: 0` 0곳, 마커 120·119 | 충족 | `data_source/markdown` grep 0건(`.bak` 제외) |
| 3 | `git status` 에 data_source 없음 | 충족 | 0건 |
| 4 | 미확정 ≤5, 전부 unpaged-* 출처, `grade_unpaged`=0 | 충족 | context 1 / fallback 0 / unpaged 0 |
| 5 | `EXPECTED` 변경 → exit 1, 무기록 | 충족 | `test_run_census_refuses_to_write_on_expected_mismatch` |
| 6 | 결정론 테스트 + 실제 2회 동일 | 충족 | 단위 테스트 OK; 2차 가드 실행이 1차(`--force`) 해시를 재현 |
| 7 | 5종 manifest `git_commit`·`generated_at` 동일 | 충족 | 전부 `6021edd`/`07:56:12`; HTML 은 일자 |
| 8 | grep 히트 전부 "이전 값·감사·폐기" 문맥 | **부분** | 발표면·semantic 문서 0건. hwpx-* 5문서·superpowers spec·evidence.json 에 사실 서술로 잔존(G11) |
| 9 | 하니스가 summary.json 기준 검증, README 2,189/145 ↔ reseg, 단언 수 일치 | 충족 | S2~S8, S7b, S9(62)·R17(385) |
| 10 | CLAUDE.md 예외 승인 + 브리지 참조 | 충족 | Safety Grading Scheme 예외 문단 |
| 11 | occurrence-grades plan/design/report 에 "미확정 보존" 없음 | **부분** | plan 은 "폐기" 문맥; design §8 "페이지 미확정 레코드 분리"·plan 제외 항목 잔존(G8) |
| 12 | 기존 하니스 전부 통과 | 충족 | 385 · 24 · 32 · 38 · 62 · 39 OK |

## 5. 갭 목록

| # | 심각도 | 위치 | 설계 원문 | 실제 | 권고 |
|---|---|---|---|---|---|
| G1 | Medium | `CLAUDE.md` 예외 문단 | "(20.6% vs 6.6% on the 2026-09 data)" | 정본은 2,595/12,506 = **20.8%**. 20.6% 는 폐기된 09-09 실행값. S8a 는 문자열만 검사 | 20.8% 로 교체하고 S8 에 `pct(N.grades['3'], N.graded)` 대조 추가 |
| G2 | Medium | `CLAUDE.md` resegment 절·Testing·Coverage·Other Artifacts; `docs/03-analysis/data/README.md` | Testing·Coverage·Artifacts 를 새 S 그룹으로 | "docs/*.html publish resegment.py's page-level numbers", "dashboards read reseg_summary.json … and nothing else", "D14 (dashboard)", "All five … last step", 대시보드 하니스에 `known()` 있다고 기술, `D13q` 참조 잔존 | `semantic_summary.json`·S4d·S9 기준으로 문장 갱신 |
| G3 | Low(설계와 다름) | `shift_page_markers.py`, R8k | 거부 조건 "마커가 줄 중간에 있음" | inline 마커를 건드리지 않고 나머지만 시프트. 혼재 파일에선 inline 값이 어긋난 채 남을 수 있음(실제 2권엔 inline 0건) | 설계대로 혼재 시 거부(`refuse_inline_marker`) + R8k 수정, 또는 설계 §3.2·§6 을 구현대로 정정 |
| G4 | Low | `test_two_runs_on_same_fixture_are_identical` | "`write_workbook` 2회의 시트 내용 동일" | manifest·payload 만 비교 | `write_workbook` 2회 시트별 값 비교 추가 |
| G5 | Low | `load_previous_basis`, 렌더러 `bridge()` | `previous_basis{…, date:"2026-09-06"}` | `date` 없음, `unit` 추가; 렌더러가 날짜 하드코딩 | `date` 를 데이터로 옮기거나 설계 갱신 |
| G6 | Low | `EXPECTED["candidates"]`, `dashboard_payload` | `candidates.absent`, `status.absent` | 키 `not-found` | 설계 문서를 `not-found` 로 정정 |
| G7 | Low | `docs/index.html` template 산문 절 | "이전 기준 문맥임을 절 제목에 명시" | 라벨은 KPI 앞 한 곳뿐 | "문제점과 시사점"·"개선 권고안" `<h2>` 에 "(이전 기준 — 페이지 단위)" |
| G8 | Low | `semantic-occurrence-grades.plan.md`, `.design.md` §8 | plan §2 제외 항목 삭제, 버전 이력 1.1(m3) | 제외 항목 "문서 단위 등급을 강제 부여" 잔존; 버전 이력 절 없음; `20260909.xlsx` 참조; design §8 "페이지 미확정 레코드 분리" 잔존 | 제외 항목 삭제, 버전 이력 절 신설, 입력 자료 20260914, design §8 갱신 |
| G9 | Low | `outputs/test-dashboard-data.js` | "옛 `check()/known()/fmt()/pct()` 헬퍼 복원" | `known()` 없음 | 복원(0건이어도 규약 유지) |
| G10 | Low | `write_workbook` README 시트, `write_report` | m1·FR-02 문구 통일 | xlsx README 시트 "등급 미확정 … 분모에서 제외", "페이지 미확정 파일 수로 별도 표시"; report md "98개 조사 원문" | README 행을 승인 문구로, `98개` 를 문서 수 계산값으로 |
| G11 | Low | hwpx-* 5문서, `docs/superpowers/specs/2026-09-08-…md`, `hwpx-refresh-audit-20260910/evidence.json` | 계획 성공 기준 8 | 구 수치가 사실 서술로 잔존. 계획 §2.2 가 hwpx 수치 갱신을 범위 밖으로 둠 | hwpx 4문서와 spec 에 폐기 배너 한 줄(수치 수정은 `hwpx-report-data-refresh` 후속) |

설계 문서 자체 모순(구현 갭 아님): §6 결정 기록 "계층 토큰 `--t1/--t2/--t3` 추가"와 §4 FR-11 행 "S5 토큰(`--t1` 사용)"이 v1.1 §3.7(죽은 스크립트 삭제, 토큰 두지 않음)과 충돌 — 구현은 §3.7 을 따랐다. §6·§4 두 줄 정정 권고.

## 6. 설계에 없는 추가 구현

- CI: `.github/workflows/test.yml` unittest 스텝.
- 하니스 추가 단언: S1n·S1o·S1q·S2c·S3h·S3j·S3k·S5h(`docs/ncs_semantic_dashboard.js` 부재 + `docs/*.js` 목록 고정)·S7e.
- `run_manifest` `xlsx` 키, `previous_basis.unit`, `shift_page_markers.py` 다중 파일 인자, R8p(`--backup`).
- 테스트: `test_report_path_regex_is_gone`, `test_select_ncs_documents_tie_prefers_underscore_path`, `test_run_census_refuses_zero_based_markers`.
- 브리지 표 등급1·2 행(7→9행). `.ctn` 정본 값 프리렌더 + S5a/S5b 대조.

## 7. Match Rate 산정 근거

| 절 | 항목 | 일치 | 부분/다름 |
|---|---:|---:|---:|
| §3.1 | 6 | 6 | 0 |
| §3.2 | 8 | 7 | 1 (G3) |
| §3.3 | 6 | 5 | 1 (G6) |
| §3.4 | 5 | 4 | 1 (G4) |
| §3.5 | 5 | 4 | 1 (G5) |
| §3.6 | 7 | 7 | 0 |
| §3.7 | 19 | 16 | 3 (G1, G7, G8) |
| §3.8 | 11 | 10 | 1 (G9) |
| §3.9 | 3 | 3 | 0 |
| §3.10 | 5 | 5 | 0 |
| §3.11 | 4 | 4 | 0 |
| §4 대응표 | 13 | 13 | 0 |
| §5/§6 결정 | 7 | 7 | 0 |
| **합계** | **99** | **91** | **8** |

부분·설계와 다름을 0.5 로 계수: (91 + 8×0.5) / 99 = **96.0%**. G2·G10·G11 은 설계 항목 밖의 잔존물이라 분모에 넣지 않고 갭 목록에만 실었다.

## 8. 다음 단계

Match Rate ≥ 90% → `/pdca report` 가능. G1·G2 는 CLAUDE.md 두 줄, G4~G10 은 각각 수 분 규모라 보고서 전에 처리하는 편이 낫다. G3 는 결정 항목(설계대로 혼재 파일 거부 vs 구현 유지), G11 은 후속 기능(`hwpx-report-data-refresh`) 몫.

## 9. Act-1 — 갭 처리 (2026-09-14, 연구책임자 지시 "G1~G10 정리")

| # | 처리 | 근거 |
|---|---|---|
| G1 | CLAUDE.md 예외 문단 20.6% → **20.8% (2,595/12,506)**; `S8a` 가 `pct(N.grades['3'], N.graded)`·`fmt(N.grades['3'])/fmt(N.graded)` 를 CLAUDE.md 와 대조 | `grep -c 20.6% CLAUDE.md` = 0, S8a 통과 |
| G2 | CLAUDE.md resegment 절("previous basis since 2026-09-13"), 그룹 3 서두, Testing("then `test_semantic_keyword_recount.py`"), `S9`, Other Artifacts(`semantic_summary.json` 이 정본, reseg 는 이전 기준, "dashboards read `semantic_recount_data.js` … and nothing else"), `D13q` → `S4d`; `docs/03-analysis/data/README.md` `D13q` → `S4d` | 잔존 `D13q`/`D14` 는 "(the old …)" 설명 문맥뿐 |
| G3 | **설계대로 거부**: `shift_lines` 가 본문 줄에 낀 마커를 만나면 `(None, [])`, `shift_file` 이 `refuse_inline_marker`; R8k 픽스처에서 inline 마커 제거, **R8q** 신설. 설계 §3.2 문구 정정 | R8k~R8q 통과 (386/386) |
| G4 | `test_two_runs_on_same_fixture_are_identical` 에 `write_workbook` 2회 → 전 시트 값 비교(README `생성일` 행 제외) 추가 | unittest 40 OK |
| G5 | `PREVIOUS_BASIS_DATE = "2026-09-06"` 상수 → `previous_basis.date`; 렌더러 `bridge()` 가 `P.date` 를 그림(하드코딩 제거). reseg_summary.json 은 날짜를 싣지 않으므로 상수가 단일 출처 | `meta.previous_basis.date` = 2026-09-06, 정본 재생성 가드 통과 |
| G6 | 설계 §3.3·§3.5 `absent` → `not-found` | grep 0건 |
| G7 | `index.html` template 의 "문제점과 시사점"·"개선 권고안" `<h2>` 에 "(이전 기준 — 페이지 단위)" | 2곳 |
| G8 | occurrence-grades plan: 제외 항목 "문서 단위 등급 강제 부여" 삭제, 입력 자료 20260914, **버전 이력 절 신설(1.1, 승인자 명기)**; design §8 "페이지 미확정 레코드 분리" → 문맥 판정/등급1 | grep 0건 |
| G9 | 하니스에 `known()` 복원(0건, 결과 줄에 KNOWN ISSUE 수 표기) | `grep -c known` 3 |
| G10 | xlsx README 시트 "페이지"·"마커 없는 출현" 행을 승인 문구로, 상세 시트 등급 출처 라벨에 `unpaged-context`/`unpaged-fallback` 표시명, report md "98개" → `len(result.documents)`; 잔여 `None` 등급 경로(마커는 있으나 본문 블록 없음)도 등급1 `unpaged-fallback` 으로 통일 + `test_paged_record_without_page_text_falls_back_to_grade_one` | unittest 40 OK, 정본 수치 불변(가드 통과) |
| 설계 자체 모순 | §4 FR-11 행·§6 계층 토큰 행을 v1.1 §3.7 과 일치시킴, 버전 1.2 | — |
| G11 | **이월** — 계획 §2.2 범위 밖(hwpx 문서 수치는 `hwpx-report-data-refresh` 후속) | — |

정본 재생성(`previous_basis.date` 추가분)은 해시 4종 불변으로 가드를 통과했고, README·CLAUDE.md 인용 단언 수를 386 으로 동기화했다. 재측정: 설계 항목 99 중 G1~G10 해소로 **일치 99 / 99 → 100%** (G11 은 설계 항목이 아닌 계획 성공 기준 8항의 범위 밖 잔존물로, 후속 기능에서 처리). 하니스: 62/62 · 386/386 · 24/24 · 32/32 · 38/38 · unittest 40 OK.

## 10. Act-2 — ship 사전 리뷰 반영 (2026-09-14)

`/ship` 의 리뷰 8종(테스트·유지보수·보안·성능·단순화·디자인 스페셜리스트, Claude 적대적, Codex 적대적)과 커버리지 감사(78/97, 80%)·계획 완료 감사(35/40 DONE·3 CHANGED·2 PARTIAL)의 결과. 교차 합의 항목은 전부 코드로 닫았고, 판단 항목 3건은 연구책임자가 결정했다.

| 출처 | 항목 | 처리 |
|---|---|---|
| 보안·Codex·Claude 적대적 | `--opt=value` 인자에서 `public_path` 가 절대 경로를 못 걷어냄 | `_scrub_argv_token` — `=` 뒤 값만 스크럽; `xlsx` 는 argv 재파싱 대신 `xlsx_out` 인자 |
| Codex·Claude 적대적 | `check_marker_base` 가 첫 마커만 검사 | 모든 마커 < 1 거부; 비단조는 `nonmonotone_markers` 로 `meta.run.marker_nonmonotone` 에 기록(레거시 1권 `LM1903060113`) — 거부하면 정본이 막히므로 재유도는 TODOS |
| Codex·Claude 적대적 | `shift_page_markers.py` CRLF→LF 변환, 비원자 쓰기, `.bak` 덮어쓰기 | `newline=''`, 임시 파일+`os.replace`, `refuse_backup_exists` — R8r~R8u |
| Codex·Claude 적대적 | 추적 산출물 비원자 쓰기 | `_write_text_atomic`(json·js·html·md), xlsx 도 임시 저장 후 교체 |
| Claude 적대적 | `check_expected` 가 실측에만 있는 키를 무시 | `STRICT_GROUPS`(documents·grade_sources·candidates·dedup) 잉여 키 보고 |
| Codex·유지보수 | `previous_basis` 파일이 manifest 에 없고 `source`·`date` 가 상수 | `inputs` 에 "이전 기준" sha256, `source` = `public_path(path)`, `source_run_at`·`unresolved_pages` 복사, 누락 키는 읽기 쉬운 오류 |
| 테스트·Codex | CI 가 `meta.run.expected` 자기 증명 | `test_committed_summary_json_matches_expected` — 커밋된 요약을 Python `EXPECTED` 와 직접 대조 |
| 성능 | `audit_candidates` 2회 호출(실행 12%) | `run_census` 가 1회 계산해 writer 두 곳에 전달 |
| 성능·연구책임자 D1 | 12,536행 상세표 레이아웃 8.1 s(모바일) | 키워드별 닫힌 `<details>`(실측 0.35 s) |
| 디자인 | 생성 페이지 스크롤 영역 접근성·반응형, 브리지 문단 각주체 | `role="region"`·`tabindex`·`:focus-visible`·`@media`·14px 표, 브리지 문단 본문체(`.bridge-note`, max-width 860px) |
| 유지보수 | CLAUDE.md 문구 3곳, `GRADE_SOURCES` 상수, `dedup` 인자 중복, dataNote 반복 호출, insight-4 무조건 참조 | 반영 |
| 유지보수·디자인 (연구책임자 D2) | 항상 0인 미확정 KPI 카드 | **유지** — 미배정 없음 결정을 화면이 말하게 |
| 단순화 (연구책임자 D3) | `public_path` 15줄 사본 | **유지**, TODOS 4 |
| 계획 완료 감사 | superpowers 설계 명세의 "89개" 사실 서술 | 폐기 배너 |
| 테스트 | 부재 분기 테스트 10건 | unit 40→53, R8k~R8u, S1r·S1s (하니스 64 · 390) |

Codex 적대적 리뷰의 "CI 자기 증명" 판정은 하니스 S4a(reseg 원본 대조)를 놓친 것이지만, 위 unittest 로 Python `EXPECTED` 와의 직접 대조를 더했다. Codex 의 "git_dirty=true 인 manifest" 지적은 구조적이다 — 산출물이 실행 뒤에 커밋되므로 정본 manifest 는 언제나 부모 커밋+dirty 를 가리키며, 재현은 "커밋 뒤 같은 명령 재실행 → 가드 통과"로 확인한다(CLAUDE.md 그룹 4 에 기록).
