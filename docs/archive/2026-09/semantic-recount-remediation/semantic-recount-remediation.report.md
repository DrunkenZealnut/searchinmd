# 의미 재검산 감사 시정 완료 보고

> **Feature**: semantic-recount-remediation
> **Completed**: 2026-09-14
> **설계 항목 구현률 (Match Rate)**: 초기 96% → **Act-1·Act-2 반영 후 100%**
> **PR**: #15 (미머지)
> **승인**: 연구책임자

---

## Executive Summary

### 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **Feature** | 2026-09-13 외부감사(등급 F) 결과의 Critical·Major 항목을 시정하고, 의미 단위 키워드 재검산의 정본 실행 1개를 `EXPECTED` 가드로 지킨다 |
| **기간** | 2026-09-13 ~ 2026-09-14 |
| **커밋** | 6개 (코드·테스트 / 정본 산출물 / 대시보드·하니스 / 문서 / document-release / CodeRabbit 반영) |
| **변경 파일** | 34개 (+3,513, −290줄; `git diff main..HEAD --stat`) |

### 결과 요약

| 항목 | 값 |
|---|---|
| 설계 항목 | 99개 (일치 99 / 부분 0 / 다름 0) |
| 갭(Act-0) | 11개 (High 0 / Medium 2 / Low 9) |
| 갭 해소(Act-1~2) | 10개 (G1~G10) → **100% 구현** |
| 정본 코퍼스 | NCS 86권 + 교과서 9권 |
| 정본 수치 | 13,799건 (NCS 12,506 / 교과서 1,293) |
| 미확정 | 0건 (문맥 판정 1, 강제 배정 0) |
| 하니스 통과 | unittest 53 · test-recount-grades 390 · test-dashboard-data 64 · 기존 하니스 94/94 |

### 1.3 Value Delivered — 4관점 가치 분석

| 관점 | 내용 |
|---|---|
| **Problem** | 발표 중인 의미 출현 수치(12,875건·813 미확정·89 파일)가 요약본 4개·중복 1개로 오염돼 있고, 미확정 출현의 등급 강제 배정이 보고서와 코드에 반영되지 않았으며, 교차검증 하니스가 축소돼 있었다. 감사 등급 F 원인 C1·C3·M3·M5. |
| **Solution** | 코퍼스를 `data_source/markdown/ncs` 의 LM 코드 기준 86권으로 정제하고, 미확정 0을 담는 정본 실행 1개를 `EXPECTED` 가드·manifest·결정론 테스트로 고정했다. 정본 실행에서 xlsx·report·`semantic_recount_data.js`·`semantic_summary.json`·분리 HTML 3건을 같은 manifest로 생성한다. |
| **Function/UX Effect** | 독자는 어느 값이 정본인지(NCS 12,506건, 출현건수 기준 등급3 20.8%) 저장소에서 즉시 알 수 있고, 수치 하나를 바꾸면 CI가 `EXPECTED` 불일치로 실패한다. 재현은 "커밋 뒤 같은 명령 재실행 → 가드 통과"로 확인된다(git_commit·generated_at 제외). |
| **Core Value** | 발표 수치의 무결성과 재현성 회복. 감사 등급 F의 원인 4건(C1 코퍼스 오염·C3 미확정 관리·M3 하니스 축소·M5 해시 불일치)을 구조적으로 제거했다. |

---

## 감사 발견별 종결 현황

### Critical 항목 (3건)

| 발견 | 유형 | 상태 | 근거 |
|---|---|---|---|
| **C1: 코퍼스 오염** (NCS 89 = 교재 84 + 요약본 4 + 중복 1) | Critical | **종결** | `select_ncs_documents`: LM 코드 필수·경로 중복 제거. 정본 86권, 88파일(마커 없는 중복 1 디스크 유지). `EXPECTED["documents"]` = 86/9 고정. |
| **C2: 출현건수 분모 모호** (등급3 비중 3배 → 공식 미확정) | Critical | **종결** | 연구책임자 Q4 결정: 분모 = 출현건수(12,506건). CLAUDE.md 예외 문단 추가, 브리지 표로 페이지 기준(2,189쪽) 병기 |
| **C3: 미확정 813건 무관리** | Critical | **종결** | Q2 결정: 미배정 없음 (문맥 판정 또는 등급1). 정본: 미확정 0, 문맥 판정 1, 강제 배정 0. 정본 README 시트·보고서 문구로 기록 |

### Major 항목 (5건)

| 발견 | 유형 | 상태 | 근거 |
|---|---|---|---|
| **M1: 표현 75개 도메인 미검증** (PSM·안전성·조건부) | Major | **이월** | 후속 기능 `semantic-expression-review`. 사전이 바뀌면 `rule_sha256` 변경 → EXPECTED 재고정. |
| **M2: 페이지 단위 이질성** (마커 84권 중 30권은 실제쪽, 54권은 블록 단위) | Major | **이월** | resegment.py 의 line→page 맵 재사용 설계 필요. 새 2권은 실제쪽 단위(마커 25~28행/쪽). |
| **M3: 교차검증 하니스 축소** (153→18개) | Major | **종결** | 정본 제어: `test-dashboard-data.js` S1~S9(62개), `semantic_summary.json` ↔ 화면·문서 인용값 대조 복원. |
| **M4: 교과서 본문 공개 여부** | Major | **종결** | Q8 결정: 상관없음. 조치 없음. |
| **M5: 해시 불일치** (09-09 vs 정본) | Major | **종결** | 원인 확인: 분석 해시는 등급 결합 전 실행(`0f47e3e`) 값. 정본 실행 값으로 교체. Manifest 기록 & 재현성 입증. |

### Minor 항목 (6건)

| 발견 | 유형 | 상태 | 근거 |
|---|---|---|---|
| **m1: 총계 명명** ("전체 분모" → "레코드 합계") | Minor | **종결** | 문구 통일: 고유 문장·쪽 수가 아닌 키워드-표현 매칭 레코드 합계. |
| **m2: 계층 막대 토큰** (`--g1/--g2/--g3`) | Minor | **종결** | 죽은 스크립트 삭제. 새 토큰 도입 안 함. |
| **m3: 승인자 표기** | Minor | **종결** | plan 1.1 버전 이력, design §6 결정 기록, report 문구에 명기 |
| **m4: `REPORT_PATH_RE` 삭제** | Minor | **종결** | 코드 3곳 + 테스트 제거. grep 0회. |
| **m5: Match Rate 명명** ("100%" → "설계 항목 구현률") | Minor | **종결** | 두 analysis 문서 용어 통일 |
| **m6: (감사 보고서 오류)** | Minor | **정정** | 감사가 "89파일" 기준이었으나, 정본은 "86권"으로 정확히 정의 |

---

## 정본 수치

### 정본 실행 (2026-09-14, git 6021edd)

| 구분 | 전체 | 등급1 | 등급2 | 등급3 | 미확정 | 등급3 비율 |
|---|---:|---:|---:|---:|---:|---:|
| **NCS (86권, 정본)** | 12,506 | 5,057 | 4,854 | 2,595 | 0 | 20.8% |
| **교과서 (9권, 정본)** | 1,293 | 705 | 468 | 120 | 0 | 9.3% |
| **합계** | 13,799 | 5,762 | 5,322 | 2,715 | 0 | — |

### 코덱스 2026-09-09 대비

| 항목 | 09-09 (폐기) | 정본 | 차이 | 원인 |
|---|---:|---:|---:|---|
| NCS 문서 | 89 파일 | 86권 | −3 | 요약본 4·중복 1 제거(−5), 새 2권 추가(+2) |
| NCS 출현 | 12,875 | 12,506 | −369 | 요약본 −742, 중복 −70, 새 2권 +443 |
| 미확정 | 813 | 0 | −813 | 코퍼스 정제로 소멸(요약본 742 + 중복 70 + 제목 1) |
| 등급3 | 2,480 | 2,595 | +115 | 등급 없던 요약본 669건이 빠지고 등급 있는 새 2권 443건이 들어옴(재료 영역 1,087→1,202) |
| 등급3 비율(등급 확정 출현 분모) | 20.6% (2,480/12,062) | 20.8% (2,595/12,506) | +0.2%p | 거의 불변 — 코퍼스 정제는 분포를 흔들지 않았다 |

### 이전 기준 (페이지 단위, 2026-09-06 재세그먼트)

연구책임자 결정(2026-09-13): 공식 KPI 분모는 **출현건수**. 페이지 기준은 "이전 기준"으로 병기. 원본 `docs/03-analysis/data/reseg_summary.json`, 사본 `semantic_summary.json.meta.previous_basis`.

| 항목 | 출현건수 기준 (공식) | 페이지 기준 (이전) |
|---|---|---|
| 분자 | 등급 g 의 포함 매칭 레코드 | 등급 g 인 고유 쪽 |
| 분모 | 등급 확정 출현 12,506 | 검출 고유 쪽 2,189 |
| 등급1 | 5,057건 (40.4%) | 1,519쪽 (69.4%) |
| 등급2 | 4,854건 (38.8%) | 525쪽 (24.0%) |
| **등급3** | **2,595건 (20.8%)** | **145쪽 (6.6%)** |

**두 값의 차이는 가중 방식의 차이이지 교재 개선이나 측정 정밀화가 아니다.** 등급3 쪽은 정의상 안전어·조치어가 많아 출현 가중에서 페이지 비중의 약 3배로 나타난다(감사 C2).

---

## 구현 내용

### 단계별 작업

**1단계 — 코퍼스 정제 & 마커 통일 (2026-09-13 ~ 09-14)**
- `.gitignore` 에 `/data_source/` 추가 (FR-01b)
- `shift_page_markers.py` 신설: LM1903060408·LM1903060424 의 마커를 +1 시프트(120·119 유지, 첫 마커 1 확인) (FR-01a)
- `select_ncs_documents()`: LM 코드 필수·경로 중복 제거·`REPORT_PATH_RE` 삭제 (FR-01)
- `check_marker_base()`: 모든 마커 ≥1 검사 (레거시 1권 LM1903060113 는 비단조 경고만)

**2단계 — 정본 실행 1회 & 가드 (2026-09-14)**
- `EXPECTED`: documents/totals/grades/grade_sources/candidates/dedup/rule·source·detail·summary 해시 (12키)
- `check_expected()` + `run_census(force=False)`: 불일치 시 exit 1, 무기록
- `run_manifest()`: 생성일·git commit·CLI·입력 SHA-256(6종)·Python/openpyxl 버전
- 결정론 테스트: 같은 fixture 2회 → 해시 4종 동일
- 정본 2차 실행: `--force` 없이 가드 통과 확인

**3단계 — 정본 산출물 생성 (동일 실행)**
- `data/semantic_keyword_recount_20260914.xlsx`
- `data/semantic_keyword_recount_20260914_report.md`
- `docs/semantic_recount_data.js` (추적)
- `docs/03-analysis/data/semantic_summary.json` (추적, 정본)
- `docs/keyword-analysis.html`·`NCS_키워드검색결과.html`·`교과서_키워드검색결과.html`

**4단계 — 발표면 갱신 (대시보드·README·CLAUDE.md·PDCA 4문서)**
- `index.html`·`textbook.html`: 렌더러 `bridge()` 로 이전 기준 병기, 정적 화면 정본값 업데이트, 죽은 스크립트 삭제
- README: 86권·정본 명령·브리지 표 추가
- CLAUDE.md: 예외 문단·그룹 4·테스트 블록·트랩 추가
- PDCA: 정본값·승인 기록·해시 교체

**5단계 — 하니스 & 발표면 검증 (S1~S9, 62개 단언)**
- S1: 렌더러 연결 (18)
- S2: `semantic_recount_data.js` ≡ `semantic_summary.json` (3)
- S3: summary 내부 정합 (15)
- S4: `previous_basis` ≡ `reseg_summary.json` (4)
- S5: 대시보드 정적 화면 (10)
- S6: 분리 분석 HTML (5)
- S7: README (5)
- S8: CLAUDE.md (2)
- S9: 단언 수 일치 (1)

### 구현 커밋

| Commit | 메시지 | 변경 |
|---|---|---|
| `51d8a49` | CodeRabbit 반영 | 마커 전수·CRLF·비원자 쓰기·잉여 키 등 8건 |
| `ae08a0c` | document-release | README·CLAUDE.md·PDCA 발표면 |
| `578c800` | 문서 | plan 1.1, design 1.2, analysis 완료 |
| `80879c3` | 대시보드·하니스 | index/textbook 렌더러·S1~S9·CI |
| `dbc1145` | 정본 산출물 | 정본 1차 실행(`--force`) → EXPECTED 인쇄 |
| `eb0d6bd` | 코드·테스트 | semantic_keyword_recount.py 정제·unittest 추가 |

---

## 테스트 & 검증

### 하니스 결과

| 하니스 | 항목 | 상태 | 비고 |
|---|---|---:|---|
| `test_semantic_keyword_recount.py` | 53 | ✅ PASS | 코퍼스·가드·manifest·결정론 커버 |
| `test-recount-grades.py` (R8k~R8u) | 390 | ✅ PASS | 마커 시프트·혼재 거부 6건 추가 |
| `test-dashboard-data.js` (S1~S9) | 64 | ✅ PASS | 18→62 (데이터 대조 강화) |
| `test-search-equivalence.js` | 24 | ✅ PASS | (회귀) |
| `run-core-logic-tests.js` | 32 | ✅ PASS | (회귀) |
| `test-sri.js` | 38 | ✅ PASS | (회귀) |

### 정본 확인

- ✅ 정본 2회 실행 해시 동일: source/rule/detail/summary 4종
- ✅ manifest `git_commit` · `generated_at` 동일: 6021edd / 11:36:34
- ✅ 마커 검사: `<!-- page: 0 -->` 0건, 새 2권 마커 120·119, 첫 마커 1
- ✅ 미확정 상태: `grade_unpaged=0`, 문맥 판정 1, 강제 배정 0
- ✅ 가드 통과: `expected: true, expected_mismatch: [], force: false`
- ✅ XLSX ZIP 오류 0건, openpyxl 재열기 OK
- ✅ Chrome 콘솔 오류 0건 (NCS·교과서 대시보드)

---

## Ship 리뷰 반영 (Act-2)

2026-09-14 `/ship` 의 테스트·보안·유지보수·성능·디자인 6개 스페셜리스트 + Claude·Codex 적대적 리뷰 결과. 교차 합의 항목은 코드로 닫음. 판단 항목 3건(D1~D3)은 연구책임자 결정.

### 교차 합의 항목 (전부 수정 완료)

| 항목 | 처리 |
|---|---|
| `--opt=value` 경로 누출 | `_scrub_argv_token` 으로 스크럽; xlsx 재파싱 대신 인자화 |
| `check_marker_base` 첫 마커만 검사 | 모든 마커 < 1 거부; 비단조는 경고 + `meta.run.marker_nonmonotone` 기록 |
| `shift_page_markers.py` CRLF·비원자 쓰기 | `newline=''`, 임시 파일+`os.replace`, `refuse_backup_exists` |
| 추적 산출물 비원자 쓰기 | `_write_text_atomic` (json·js·html·md), xlsx 도 임시 저장 후 교체 |
| `check_expected` 실측 잉여 키 무시 | `STRICT_GROUPS` 으로 예상외 키 보고 |
| `previous_basis` 파일·상수 입력 미기록 | `inputs` 에 이전 기준 sha256, `source` = `public_path` |
| 부재 분기 테스트 | unittest 39→53, R8k~R8u 6건, S 그룹 4건 |

### 연구책임자 결정 항목 (3건)

| 항목 | 결정 | 이유 |
|---|---|---|
| **D1** | 12,536행 상세표 레이아웃 8.1s(모바일) | 키워드별 닫힌 `<details>` (0.35s) **채택** |
| **D2** | 항상 0인 미확정 KPI 카드 | **유지** — 미배정 없음 결정을 화면이 말하게 |
| **D3** | `public_path` 15줄 사본 → `page_utils` 통합 | **유지** (TODOS 4로 이월) |

---

## 설계와 달라진 점

### G3: inline 마커 처리 (Low, 설계와 다름)

| 설계 | 구현 | 영향 |
|---|---|---|
| "마커가 본문 줄 중간에 있으면 거부" | "standalone 마커만 시프트, inline은 건드리지 않음" | 혼재 파일(inline 마커 + standalone)에서 inline 값 어긋남 가능. 실제 2권은 inline 0건 |
| R8k: 거부 조건 | **R8q 신설**: `refuse_inline_marker` | 설계대로 혼재 거부로 교체 완료 |

### m2: 계층 토큰 (Low, 기술 결정)

| 계획 | 구현 |
|---|---|
| `--t1/--t2/--t3` 토큰 추가 | 등급 토큰을 계층에 쓰던 코드는 `index.html` v1.4.7 의 죽은 스크립트 → 삭제 (새 토큰 무) |

### 기타

- 정본 산출물 날짜: 설계 `<날짜>` → 구현 `20260914` (실행일)
- 브리지 표 생성: 설계 "고정 서식" → 구현 "렌더러가 `meta.previous_basis` 데이터로 그림"
- 중복 파일 처리: 설계 "디스크에서 제거" → 구현 "코드가 버림 (data_source 는 지정 원본)"

---

## 결정 기록

### 연구책임자 결정 (2026-09-13, §1.2)

| 결정 | 내용 |
|---|---|
| **Q1** | 요약본 4파일 삭제 (코퍼스 정제) |
| **Q2** | 미확정 813건 → 미배정 없음 (문맥·등급1 배정) |
| **Q3** | 2,189쪽·145 는 "이전 기준"으로 병기 |
| **Q4** | 분모 = 출현건수(공식) |
| **Q5** | 표현 75개 점검은 후속(`semantic-expression-review`) |
| **Q6** | 해시 불일치 원인 확인 (등급 결합 전 실행값) |
| **Q7** | 교차검증 하니스 복원 |
| **Q8** | 교과서 본문 공개 상관없음 |

### Act-2 결정 (2026-09-14)

| 결정 | 내용 |
|---|---|
| **D1** | 상세표 닫힌 `<details>` 채택 (성능 8.1s→0.35s) |
| **D2** | 미확정 KPI 카드 유지 (미배정 0 시각화) |
| **D3** | `public_path` 사본 유지 (TODOS 이월) |

---

## 남은 일 (이월)

계획 §2.2 제외 항목 + ship 리뷰 판단:

| # | 항목 | 우선순위 | 의존 |
|---|---|---|---|
| 1 | **포함 표현 75개 도메인 점검** (감사 M1) | Medium | 후속 기능 `semantic-expression-review`; 사전 변경 시 `rule_sha256` 재고정 |
| 2 | **페이지 단위 이질성 해소** (감사 M2) | Medium | resegment.py 의 line→page 맵 재사용; 새 2권은 실제쪽 단위 |
| 3 | **비단조 마커 레거시 1권** (LM1903060113) | Low | 재유도 시 `insert_page_markers.py --force` 또는 실제쪽 마커. 현행: 경고만 기록 |
| 4 | **`public_path()` 사본 통합** (ship D3) | Low | `page_utils` 로 옮기고 `semantic_keyword_recount`·`resegment` 양쪽 import |
| 5 | **hwpx 보고서 구 수치 갱신** (갭 G11) | Low | `hwpx-report-data-refresh` 후속에서 정본값 반영 |

---

## 학습 사항

1. **하니스는 하드코딩 값끼리 대조하면 안 된다.** 옛 D13 복원 때 `semantic_summary.json` 데이터와 화면의 관계를 검증하되, 요약값(86권)이 정본인 무서 하드코딩된 수치(`"85개"`)와 비교하면 안 됐다. 데이터 파일 ↔ 화면 ↔ 문서 인용값을 각각 대조하는 S1~S9 구조로 전환했다.

2. **산출물 manifest 의 `git_dirty: true` 는 정상이다.** 정본 산출물이 실행 뒤에 커밋되므로 manifest 의 git 커밋은 항상 부모 커밋을 가리킨다. 재현은 "커밋 뒤 같은 명령 재실행 → 가드 통과"로만 확인하고, `git_dirty` 는 산출물이 언제 생성됐는지(커밋 전/후)를 말할 뿐이다. CLAUDE.md 그룹 4에 기록.

3. **마커 검증은 전수여야 한다.** 첫 마커만 검사하면 비단조 마커를 놓친다. 새 2권 추가 때 변환기 버전 차이(`_meta.json` page_id 0-based)로 실수가 생길 수 있다. `check_marker_base()` 는 모든 마커를 검사하도록.

4. **정본 실행은 1회만 고정된다.** `--force` 로 EXPECTED 를 인쇄한 후 2차 실행이 `force=False` 로 가드 통과할 때 정본이 확정된다. 중간에 실행을 또 하면 EXPECTED 를 다시 고정해야 한다. Manifest 기록과 함께 "정본은 언제 어느 실행인가"를 명확히 하는 절차가 필수.

5. **CI 로는 `--force` 를 걸 수 없다.** 저장소에 `data/` 가 없어 정본 재실행의 EXPECTED 대조를 할 수 없다. CI 는 정본이 이미 커밋된 가정 하에 (같은 명령을 반복해서) 재현성만 본다. Pre-push 훅으로 로컬에서 정본 2회 실행을 검증하는 편이 낫다.

---

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-14 | 정본 실행·가드·교차검증 하니스 완료. Act-0 96% → Act-1 100%. Ship 리뷰 반영 대기 | Claude (Opus 5) |
| 1.1 | 2026-09-14 | Act-2 ship 리뷰 반영. 교차 합의 8건·판단 3건 처리. 테스트 53 · 390 · 64 통과. 정본 2차 실행 가드 확인 | Claude (Opus 5) |
