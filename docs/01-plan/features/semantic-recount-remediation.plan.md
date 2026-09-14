# 의미 재검산 감사 시정 계획

> **Summary**: 2026-09-13 외부감사(등급 F)의 Critical 3건·Major 3건을 연구책임자 결정에 따라 시정하고, 의미 단위 키워드 재검산의 정본 실행 1개와 그것을 지키는 가드를 세운다.
>
> **Project**: SearchInMD
> **Feature**: semantic-recount-remediation
> **Author**: Claude (Opus 5) — 결정: 연구책임자
> **Date**: 2026-09-13
> **Status**: Approved (연구책임자, 2026-09-13)
> **Level**: Starter

---

## Executive Summary

| 관점 | 내용 |
|---|---|
| **Problem** | 발표 중인 의미 출현 수치(NCS 12,875건·미확정 813건·문서 89개)가 요약본 4개와 중복 교재 1개로 오염돼 있고, 같은 기능에 대해 4세대 수치가 README·대시보드·`keyword-analysis.html`·미커밋 데이터에 병존하며, 이를 잡을 교차검증 하니스가 153→18개로 축소돼 있다. 미확정 출현의 등급 강제 배정과 출현건수 분모 채택은 승인됐지만 계획·보고서·CLAUDE.md에 반영되지 않았다. |
| **Solution** | 코퍼스를 `data_source/markdown/ncs`의 LM 코드 기준 86권(2026-09-13 추가 2권 포함, 마커 1-based 통일)으로 정제하고 `EXPECTED` 가드·실행 manifest·결정론 테스트를 갖춘 정본 실행 1개를 만든 뒤, 그 산출물 하나에서 xlsx·보고서·대시보드 데이터·분리 분석 페이지를 같은 실행으로 생성한다. 대시보드·README·CLAUDE.md·PDCA 문서를 정본 수치와 승인된 기준(출현건수 분모, 미확정 등급 배정)으로 갱신하고, 대시보드 ↔ 추적 요약 파일 ↔ 문서 인용값 교차검증을 복원한다. |
| **Function/UX Effect** | 독자는 어느 값이 정본인지 저장소에서 즉시 알 수 있고(페이지 기준 2,189쪽·145는 "이전 기준"으로 병기), 수치 하나만 바꾸면 CI가 실패한다. 재실행은 같은 입력에서 같은 해시를 낸다. |
| **Core Value** | 발표 수치의 무결성과 재현성 회복 — 감사 등급 F의 원인(C1·C3·M3·M5)을 구조적으로 제거한다. |

---

## 1. 개요

### 1.1 목적

2026-09-13 외부감사 보고서(Claude 선행 + gpt-5.6-sol 교차검증, 종합 F)가 지적한 결함 중 연구책임자가 시정을 결정한 항목을 한 번의 정본 재실행과 문서·가드 갱신으로 해소한다.

### 1.2 배경 — 연구책임자 결정 (2026-09-13)

| 감사 질문 | 결정 | 이 계획의 반영 |
|---|---|---|
| Q1 `report` 4개 파일의 정체 | 요약본, 사용할 이유가 없어 삭제함 | 코퍼스 정제 확정(C1). `report` 정규식 임시 제외는 삭제하고 교재 판별 규칙으로 교체 |
| Q2 미확정 813건 등급 강제 배정 | 승인. 미배정을 두면 안 됨 | 유지(C3 종결). 정제 후 대상이 소수임을 확인하고 계획·보고서 문구를 승인 내용으로 갱신 |
| Q3 2,189쪽·145(6.6%)의 지위 | 모름 | Q4에 따라 "이전 기준(페이지 단위)"로 병기, 브리지 표로 관계 설명 |
| Q4 분모 | 페이지 → 출현건수로 변경함 | 출현건수를 공식 KPI로 확정. CLAUDE.md 등급 규칙에 예외 승인 기록(C2) |
| Q5 포함 표현 75개 | 확인함. 포함 범위는 LLM이 결정, 점검 필요 | **범위 외** — 후속 기능 `semantic-expression-review`(M1) |
| Q6 해시 불일치 원인 | 모름 | 원인 확인됨: `analysis.md` 해시는 등급 결합 전 실행(`0f47e3e`) 값. 정본 재실행 값으로 교체(M5) |
| Q7 교차검증 하니스 축소 | 정확성을 위한 것이면 승인 | 대시보드 ↔ 추적 요약 파일 ↔ 문서 인용값 교차검증 복원(M3) |
| Q8 교과서 본문 공개 | 상관없음 | M4 종결, 조치 없음 |

### 1.3 확인된 사실 (2026-09-13 실측)

- **최종 원본 소스는 `data_source/markdown/ncs`** (연구책임자 지정, 2026-09-13). 2026-09-13 21:09·21:17 에 변환된 2권이 추가돼 NCS 교재 **86권 전부**의 마크다운이 있다. `data/markdown/ncs` 는 같은 내용의 복사본(87파일, 공통 85종 sha256 동일).
- 교재 수 대응표 — 감사 C1 ②가 요구한 것. 정본 산출물의 문서 수는 **86** 으로 표기하고 이 표를 보고서에 싣는다.

  | 수 | 뜻 | 근거 |
  |---:|---|---|
  | 86권 | NCS 반도체 교재 전체 = LM 코드 86종. 2026-09-13 추가 2권: 『반도체 재료 개발』(LM1903060408, 마커 120), 『반도체용 박막 도금 공정 재료 제조』(LM1903060424, 마커 119) | `data_source` 실측, `ncs_pages.csv` 교재 86 |
  | 87파일 | 86권 + `LM1903060205_14v3_MI 장비 운영` 중복 1(공백 경로, 마커 0; 밑줄 경로 쪽은 마커 84) | 디스크 실측 |
  | 84권 | 이전 기준(resegment 2,189쪽)이 마크다운으로 처리한 수. 나머지 2권 51쪽은 라벨 유지(`resegment-results.analysis.md` §1·§2). 이 계획은 이전 기준을 재계산하지 않는다 | |
  | 89파일 | 85 + 삭제된 report 요약본 4 | 감사 전 문서의 "NCS 89개" |

- **새 2권의 페이지 마커는 0-based** (`<!-- page: 0 -->` 부터, `_meta.json page_id` min 0, meta 에 `engine`/`engine_version`/`page_stats` 키 — 기존 84권과 다른 변환기). 기존 84권은 첫 마커가 1(69권) 또는 2(15권)인 1-based (`docs/howto-page-markers.md`: `page_id`+1). 그대로 쓰면 이 2권의 쪽 번호가 전부 1 어긋나므로 정본 실행 전에 두 파일의 마커를 +1 시프트한다(밀도 25~28행/마커는 실제 쪽 단위라 유지 가치가 있음 — TOC 재유도 `--force` 는 쓰지 않는다).
- `data_source/` (659 MB, jpeg 6,758·pdf 32·bak 51 포함)는 **미추적이고 gitignore 되어 있지 않다.** 어떤 커밋보다 먼저 `/data_source/` 를 `.gitignore` 에 넣는다.
- 따라서 정제 후 미확정 출현은 마커 앞 제목 줄 수준(수 건)만 남고, 승인된 강제 배정 규칙은 그 소수에만 적용된다.
- 미커밋 diff(`semantic_keyword_recount.py`)의 `unpaged-context` / `unpaged-fallback` 배정과 그 테스트는 유지 대상이고, `REPORT_PATH_RE` 3곳은 삭제 대상이다.
- 산출물 3세대가 `data/`에 있음: `20260909.xlsx`(발표 대시보드), `20260910_all_graded.xlsx`(`keyword-analysis.html`의 기준 파일), `20260911_report_excluded.xlsx`. 정본은 이 계획의 재실행 1개로 대체한다.

### 1.4 관련 문서

- 감사 보고서: 이 세션 출력(2026-09-13). 발견 번호 C1~C3·M1~M5·m1~m6은 그 보고서 기준.
- 선행 발견: `docs/04-report/features/hwpx-report-recheck-20260910.report.md`
- 대상 기능: `semantic-keyword-recount`, `semantic-occurrence-grades` (PDCA 4문서 각각)
- 규칙: `CLAUDE.md` "Safety Grading Scheme", "Test Coverage"

---

## 2. 범위

### 2.1 포함

- [ ] **원본 소스 고정** — 정본 실행의 NCS 루트는 `data_source/markdown/ncs`(86권). `/data_source/` 를 `.gitignore` 에 추가하고, README `data/` 절에 `data_source` 가 원본이고 `data/markdown` 은 복사본임을 기록.
- [ ] **새 2권 마커 1-based 통일** — LM1903060408·LM1903060424 의 `<!-- page: N -->` 을 N+1 로 시프트(두 파일만, `_meta.json` 은 그대로). 시프트 전후 마커 수 동일·첫 마커 1 을 확인.
- [ ] **코퍼스 정제 규칙** — `load_documents()`에 NCS 교재 판별(LM 코드 필수)과 경로 중복 제거(마커 있는 쪽 우선, 동률이면 밑줄 경로) 도입. `REPORT_PATH_RE` 임시 제외 삭제. 중복 파일 `…MI 장비 운영/`(공백 경로)은 **디스크에 두고** 코드가 버린다(`data_source` 는 지정 원본이라 손대지 않는다 — Do 에서 확정); `EXPECTED["dedup"]` 과 manifest 가 그 사실을 기록.
- [ ] **회귀 가드** — `semantic_keyword_recount.py`에 `resegment.py`와 같은 `EXPECTED` 블록 + `check_expected()` + `--force` 규약. 값이 어긋나면 산출물을 쓰지 않고 exit 1.
- [ ] **재현성** — 실행 manifest(git commit, CLI, 입력별 SHA-256, Python/openpyxl 버전)를 xlsx `입력정보` 시트와 보고서 md에 기록. 결정론 테스트(같은 fixture 2회 → source/rule/detail/summary 4종 해시 동일) 추가.
- [ ] **정본 재실행 1회** — 86개 교재로 실행해 `data/semantic_keyword_recount_<날짜>.xlsx`·`_report.md`·`docs/semantic_recount_data.js`·`docs/03-analysis/data/semantic_summary.json`(추적, 본문 텍스트 없음)·`keyword-analysis.html`과 결과 HTML 2건을 **같은 실행**에서 생성. `export_keyword_outputs.py`를 추적하거나 본 스크립트에 흡수.
- [ ] **발표면 갱신** — `docs/index.html`·`textbook.html`·`keyword-analysis.html`·README·CLAUDE.md의 12,875/813/89 계열을 정본 값으로 교체. 2,189쪽·145(6.6%)는 "이전 기준(페이지 단위, 2026-09-06 resegment)"로 명시해 병기. 두 기준의 브리지 표(분자·분모·중복 처리·미확정 처리·해석 목적)를 `semantic-occurrence-grades.report.md`와 `index.html` 주석에 추가.
- [ ] **규칙 문서 갱신** — CLAUDE.md "Safety Grading Scheme"에 "의미 출현 대시보드는 출현건수 분모를 쓴다(연구책임자 승인 2026-09-13)" 예외와 브리지 참조 추가. `semantic-occurrence-grades` plan/design/report의 "미확정 보존" 문구를 승인된 강제 배정으로 갱신(승인자·일자 명기). 총계 명명을 "키워드-표현 매칭 레코드 합계(고유 문장·쪽 수 아님)"로 정정(m1). 두 analysis 문서의 "Match Rate"를 "설계 항목 구현률"로 명명(m5).
- [ ] **교차검증 하니스 복원** — `outputs/test-dashboard-data.js`: (a) `semantic_recount_data.js` ↔ `semantic_summary.json` 전 항목 일치, (b) `index.html`·`textbook.html`·`keyword-analysis.html`·README 인용 수치 ↔ `semantic_summary.json`, (c) README의 "이전 기준" 2,189/145 ↔ `reseg_summary.json`(기존 D13 복원), (d) 문서 인용 assertion 수 ↔ 실측(D14 복원). 하드코딩 값끼리의 단언은 없앤다. CLAUDE.md·README 테스트 블록 수치를 하니스 출력으로 재동기화.
- [ ] **구산출물 정리** — `data/semantic_keyword_recount_20260909*`, `20260910_all_graded*`, `20260911_report_excluded.xlsx`, 미추적 `docs/semantic_recount_data_20260910_all_graded.js` 를 정본 생성 후 제거하거나 `data/archive/`로 이동. `docs/03-analysis/semantic-keyword-recount.analysis.md` 해시를 정본 값으로 교체.
- [ ] **대시보드 토큰(m2)** — 계층 막대에 등급 토큰을 쓰던 코드는 죽은 스크립트였으므로 삭제한다(설계 §3.7).

### 2.2 제외

- 포함 표현 75개의 도메인 점검(PSM 단어 경계, `안전성` 제외, 방진복·장갑·X선 조건부 포함, 층화 표본 정밀도) — 후속 기능 `semantic-expression-review`(감사 M1, Q5 결정 "점검 필요"). 이 계획의 정본 실행은 현재 사전 그대로 돌린다.
- 페이지 단위 이질성(실제 쪽 30개 vs TOC 블록 54개) 해소와 resegment line→page 맵 재사용 — 감사 M2, 별도 결정 필요.
- 등급 정의·임계값(`SAFETY_MIN`·`ACTION_MIN`) 변경, `regrade.grade_page` 수정.
- 원본 등급 워크북 2개와 키워드 워크북 수정.
- 교과서 본문 문맥의 GitHub Pages 공개 여부 — Q8 결정으로 종결.
- hwpx 보고서 본문 수치 갱신 — `hwpx-report-data-refresh` 기능에서 정본 확정 후 별도 진행.

---

## 3. 요구사항

### 3.1 기능 요구사항

| ID | 요구사항 | 감사 근거 | 우선순위 | 상태 |
|---|---|---|---|---|
| FR-01 | NCS 문서 집합은 `data_source/markdown/ncs` 에서 LM 코드 필수 + 경로 중복 제거로 정의되어 86권이 되고, `report` 정규식 제외는 코드에서 사라진다 | C1, m4 | High | 대기 |
| FR-01a | 새 2권의 페이지 마커가 1-based 로 통일되고, 코퍼스 전체의 첫 마커 최솟값이 1 이다 | 2026-09-13 실측 | High | 대기 |
| FR-01b | `/data_source/` 가 `.gitignore` 에 있고 어떤 커밋에도 포함되지 않는다 | 2026-09-13 실측 | High | 대기 |
| FR-02 | 미확정(page 없음) 출현은 문맥 판정 또는 등급1 강제 배정을 받아 `grade_unpaged` = 0 이 된다 (승인 Q2) | C3 | High | 대기 |
| FR-03 | `EXPECTED` + `check_expected()` + `--force` 로 값 변경 시 산출물을 쓰지 않는다 | M3 | High | 대기 |
| FR-04 | 실행 manifest가 xlsx·보고서·`semantic_summary.json`에 기록되고, 결정론 테스트가 2회 실행 해시 동일을 검증한다 | M5 | High | 대기 |
| FR-05 | xlsx·보고서 md·`semantic_recount_data.js`·`semantic_summary.json`·분리 분석 HTML 3건이 한 실행에서 생성된다 | M3, C3 | High | 대기 |
| FR-06 | 대시보드·README·CLAUDE.md·PDCA 문서에서 구 수치(12,875·813·89개)는 "이전 값" 문맥 밖에 남지 않는다 | M3 | High | 대기 |
| FR-07 | 2,189쪽·145(6.6%)는 "이전 기준(페이지 단위)"로 병기되고 브리지 표가 두 기준의 관계를 설명한다 | C2, Q3·Q4 | High | 대기 |
| FR-08 | CLAUDE.md 등급 규칙에 출현건수 분모 예외 승인이 기록된다 | C2 | Medium | 대기 |
| FR-09 | `test-dashboard-data.js`가 데이터 파일 ↔ 화면 ↔ 문서 인용값을 교차검증하고 하드코딩 값끼리의 단언을 갖지 않는다 (D13·D14 복원) | M3, Q7 | High | 대기 |
| FR-10 | 구산출물 3세대와 미추적 데이터 js가 정리되고 analysis.md 해시가 정본 값이 된다 | M5, M3 | Medium | 대기 |
| FR-11 | 총계 명명(m1)·Match Rate 명명(m5)·계층 토큰(m2)·승인자 표기(m3)가 반영된다 | m1·m2·m3·m5 | Low | 대기 |

### 3.2 비기능 요구사항

| 분류 | 기준 | 측정 방법 |
|---|---|---|
| 재현성 | 같은 입력·사전으로 2회 실행 시 4종 해시 동일 | 결정론 테스트 + 수동 2회 실행 |
| 무결성 | 정본 재실행 후 xlsx ZIP 오류 0, 요약·표현·파일·상세 집계 일치 | 기존 정합성 검사 유지 |
| 회귀 | 기존 하니스 전부 통과 (`test-recount-grades.py`, `run-core-logic-tests.js`, `test-search-equivalence.js`, `test-sri.js`, `test_semantic_keyword_recount.py`) | CI |
| 커버리지 | 변경 경로의 60% 이상(목표 80%)이 하니스로 덮임 — 코퍼스 규칙·EXPECTED·manifest·결정론은 `test_semantic_keyword_recount.py`, 발표면은 `test-dashboard-data.js` | 변경 함수별 테스트 대응표 |
| 공개 데이터 | `semantic_summary.json`은 집계·해시·manifest만 담고 본문 텍스트·절대 경로를 담지 않는다 | 파일 grep |

---

## 4. 성공 기준

- [ ] NCS 문서 수 86, LM 코드 중복 0, 코드에서 `REPORT_PATH_RE` 0곳, 87 파일 중 마커 없는 파일은 제거된 중복 1개뿐.
- [ ] 코퍼스 전체에서 `<!-- page: 0 -->` 0곳, 새 2권의 마커 수는 시프트 전과 같다(120·119).
- [ ] `git status` 에 `data_source/` 가 나타나지 않는다.
- [ ] 미확정 출현 ≤ 5건이고 전부 `unpaged-context`/`unpaged-fallback` 출처로 등급이 있어 `grade_unpaged` = 0. 5건을 넘으면 원인을 보고하고 진행을 멈춘다(강제 배정이 분포에 영향을 주는 규모가 되면 Q2 재확인).
- [ ] `EXPECTED` 값을 하나 바꾸면 스크립트가 exit 1 하고 산출물을 쓰지 않는다.
- [ ] 결정론 테스트 통과, 실제 2회 실행의 4종 해시 동일.
- [ ] 정본 산출물 5종(xlsx·md·data js·summary json·분리 분석 HTML)의 manifest `git_commit`·`generated_at` 이 서로 같다.
- [ ] `grep -rn "12,875\|12875\|813건\|89개" docs README.md CLAUDE.md` 의 모든 히트가 "이전 값"·"감사"·"폐기" 문맥 안에 있다.
- [ ] `test-dashboard-data.js` 가 `semantic_summary.json` 을 읽어 대시보드·README·`keyword-analysis.html` 인용값을 검증하고, README 의 2,189/145 를 `reseg_summary.json` 과 대조한다. 하니스 출력의 assertion 수가 README·CLAUDE.md 테스트 블록과 일치한다.
- [ ] CLAUDE.md "Safety Grading Scheme"에 예외 승인(2026-09-13, 연구책임자)과 브리지 참조가 있다.
- [ ] `semantic-occurrence-grades` plan/design/report 에 "미확정 보존" 문구가 남아 있지 않고 승인된 강제 배정으로 대체돼 있다.
- [ ] 기존 하니스 전부 통과.

---

## 5. 위험과 대응

| 위험 | 대응 |
|---|---|
| 정제 후 미확정이 소수가 아니라 수십 건 이상 | 성공 기준 2항의 5건 상한으로 감지. 원인(마커 결손 파일)을 보고하고 `insert_page_markers.py` 복구를 먼저 제안 |
| 한 줄 문맥 판정은 `SAFETY_MIN=6` 때문에 구조적으로 등급1 | 대상이 소수라 분포 영향 무시 가능. 보고서에 "강제 배정 N건, 전부 등급1·2"를 명시해 독자가 알 수 있게 함 |
| 출현건수 분모가 등급3 비중을 페이지 기준의 약 3배로 보이게 함 (감사 C2) | 연구책임자 결정(Q4)으로 채택. 브리지 표와 "가중 방식 변경이지 교재 개선이 아님" 주석으로 오독 방지. 페이지 기준 값은 병기 유지 |
| 정본 재실행 값이 발표 중인 값과 크게 달라 후속 hwpx 보고서와 어긋남 | 이 계획에서는 저장소 발표면만 갱신하고 hwpx 는 `hwpx-report-data-refresh`에서 정본 확정 후 갱신. 차이표를 보고서에 남김 |
| `EXPECTED` 도입 시 현재 미커밋 diff 와 충돌 | 미커밋 diff 중 `unpaged-*` 배정·테스트는 유지, `REPORT_PATH_RE` 3곳만 제거한 뒤 `EXPECTED` 를 정본 실행 값으로 채움 |
| `data/`·`data_source/` 는 gitignore라 중복 파일 제거·마커 시프트가 다른 클론에 전파되지 않음 | `load_documents()` 의 중복 제거 규칙과 마커 최솟값 검사를 코드로 보장. 시프트 절차는 README `data/` 절과 보고서에 기록 |
| 새 2권은 다른 변환기 산출물(실제 쪽 단위 마커)이라 TOC 블록 단위인 54권과 페이지 단위가 다름 | 감사 M2 와 같은 문제. 이 계획은 마커 단위를 바꾸지 않고 보고서에 단위 차이를 명시. 해소는 M2 후속 |
| 새 2권은 이전 기준(resegment 2,189쪽)에 마크다운 없이 라벨로만 들어 있음 | 이전 기준은 그대로 두고 병기. 새 마크다운으로 재세그먼트하는 것은 별도 결정 |
| 하니스 복원이 옛 116체크를 그대로 되살리면 `legacy-dashboard` 템플릿 기준과 충돌 | 옛 D13/D14 의 "무엇을 무엇과 대조하는가"만 가져오고 단언 대상은 현행 데이터 파일로 다시 씀 |
| 표현 사전 점검(M1) 결과가 나중에 수치를 또 바꿈 | 이 계획의 정본은 "사전 v1 기준 정본"으로 명명. `EXPECTED` 갱신은 `--force` 규약으로 추적 |

---

## 6. 진행 순서

| 단계 | 산출물 | 상태 |
|---|---|---|
| Plan | 이 문서 | 작성 (승인 대기) |
| Design | `docs/02-design/features/semantic-recount-remediation.design.md` — 교재 판별 규칙, `EXPECTED` 키 목록, manifest 스키마, `semantic_summary.json` 스키마, 하니스 D13/D14 대응표, 브리지 표 서식 | 대기 |
| Do | 코드(FR-01~05) → 정본 재실행 → 발표면·문서(FR-06~08, 10, 11) → 하니스(FR-09) 순 | 대기 |
| Check | gap-detector 갭 분석 + 성공 기준 10항 실측 | 대기 |
| Report | 감사 발견별 종결 표(C1~C3·M3·M5·m1·m2·m4·m5 종결, M1·M2 이월) | 대기 |

---

## 7. 입력 자료

- `data_source/markdown/ncs/**/*.md` (87 파일 → 86권), `data_source/markdown/school-text/**/*.md` (9)
- `data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx`, `data/ncs_keywords_in_markdown_results_교과서_results_20260415.xlsx` (읽기 전용)
- 키워드 등록 워크북: `data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx` (연구책임자 결정 2026-09-13; 미커밋 `all_graded` 실행이 쓴 `20260402.xlsx` 는 쓰지 않는다)
- `docs/03-analysis/data/reseg_summary.json` (이전 기준 2,189/145 의 대조 원본)

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-13 | 외부감사 결과와 연구책임자 결정 8건을 반영한 시정 범위 | Claude (Opus 5) |
| 1.1 | 2026-09-13 | 원본 소스 `data_source`(86권)·마커 1-based·gitignore 반영, 키워드 워크북 확정, 승인 | Claude (Opus 5) / 승인: 연구책임자 |
