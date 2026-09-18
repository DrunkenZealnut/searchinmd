# NCS 교재별 등급 3 집중·편차 분석 보강

> **Feature**: ncs-book-concentration
> **Completed**: 2026-09-17
> **Match Rate**: 1차 89.8% → **100% (Act-1 완료)**
> **Author**: Claude (Opus 5) — 결정: 연구책임자
> **Date**: 2026-09-17
> **Status**: Completed
> **Duration**: 2026-09-17 (계획→설계→구현→분석→Act-1→보고, 동일 일자)

---

## Executive Summary

### 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **Feature** | 정본 데이터에 교재별 집계 `corpora.*.books[]` 추가(정본 재실행 2026-09-17, NCS 86권·교과서 9권) → 기초보고서 제3장 2절에 " 5) 교재별 집중과 편차"(표 12-3·12-4, 소결→6)) 3단계 삽입 + 대시보드(NCS) "교재별 현황" 절 추가 |
| **방식** | `semantic_keyword_recount.py` payload 확장(`books[]` 규칙·가드·`EXPECTED` 고정) + `hwpx_methods_bridge.py` 3단계(ConcentrationFacts·템플릿·감사) + `hwpx_results_refresh.py` 2·3단계 호출 + `semantic_grade_dashboard.js` 대시보드 절 |
| **확인** | `test_semantic_keyword_recount` 112 + `test_hwpx_methods_bridge` 55 + `test_hwpx_results_refresh` 48 + 기존 하니스(24·83·390·32·38) + 실문서 실행(정본 재실행 HWPX 바이트 동일) |
| **산출물** | 정본 재실행 JSON·data.js·분석 페이지·HWPX(비추적), 대조 JSON·검토 HTML·대시보드(추적) |

### 결과 요약

| 항목 | 값 |
|---|---|
| 설계 항목 | 118개 (계획 FR·설계·테스트·연쇄) |
| 갭 분석(1차) | 89.8% (일치 96 · 변경 10 · 부분 12 · 불일치 0) |
| 갭 해소(Act-1) | 10건 → **100%** |
| 코드 변경 | 12파일 +632/−53줄(테스트·문서 포함) |
| 정본 수치 | NCS 11,517건·2,502건(21.7%) · 교과서 1,207건·115건(9.5%) |
| 교재 행 | NCS 86·교과서 9(매칭 0건 교재도 포함) |
| 집중도 값 | 안전관리 전용 2권 2,238건 중 등급 3 965건(NCS 등급 3 의 38.6%) · 제외 84권 16.6% · 장비 분야 32.5→16.9%(전용 1권이 분야의 74.1%) · 재료 21.4→20.3% · 교재별 평균 8.5%·중앙값 0.0%·0건 57권(66.3%) |
| 표 12-3 | 집중도(NCS 전체·안전관리 전용·전용 제외·분야별) 7행 |
| 표 12-4 | 등급 3 상위 10권(2,015건·80.5%) |
| HWPX | 신규 `data/반도체 기초보고서_20260917_정본.hwpx`(비추적, 원본 2026-09-11 에서 1·2·3단계 한 번에: 문단 45·표 14·그림 3, 3단계 삽입 15·목차 삽입 2·소결 6), 토큰 1,168·미일치 0, `--force` 재실행 바이트 동일) |
| 정본 기준 | 사전 v2 · 출현건수 분모 · NCS 실제 PDF 쪽(교과서 쪽 표식) — 수치·해시 4종은 2026-09-15 정본과 동일, `books[]` 만 추가 |

### 1.3 Value Delivered — 4관점 가치 분석

| 관점 | 내용 |
|---|---|
| **Problem** | 정본 대시보드와 보고서는 NCS 등급 3을 "11,517건 중 2,502건(21.7%)" 합산값만 제시하며, 그 중 38.6%(965건)가 안전관리 전용 2권에 집중되어 있고, 86권 중 57권은 등급 3이 0건임을 보이지 않는다 — 합산값이 다수 교재의 분포를 가린다(후속 B1, 지난 세션 제안). 교재별 집계는 비추적 워크북의 `NCS_파일별` 시트를 세션에서 다시 센 값(계획 §1.2)뿐이라 보고서·대시보드가 인용할 추적 근거가 없었다. |
| **Solution** | (1) 정본 JSON에 `corpora.*.books[]` 추가(교재 단위 출현·등급·검출 쪽·쪽수, NCS/교과서 동일 규칙), (2) 3단계 스크립트로 제3장 2절 " 5) 교재별 집중과 편차"(문단 2 + 표 12-3 집중도 + 표 12-4 상위 10권) 생성·삽입, (3) 대시보드(NCS) "교재별 현황" 절(86행, 등급 3 내림차순), (4) 숫자 감사·가드·테스트·하니스·문서 통합. |
| **Function/UX Effect** | 보고서와 대시보드가 "합산 21.7%" 옆에 "안전관리 2권 제외 16.6%, 장비 분야 32.5→16.9%, 교재별 평균 8.5%·중앙값 0.0%·0건 57권, 상위 10권 80.5%" 을 같은 정본 숫자로 제시 — 교재 개선 대상을 '전체 평균'이 아니라 '개별 교재 분포'로 읽게 한다. |
| **Core Value** | 교재별 수치를 **정본 한 파일**(`semantic_summary.json`)에 두어 보고서·대시보드·후속(B2 보조 분모, C 교과서)이 모두 같은 출처를 인용하고, 정본 재실행 한 번으로 모든 산출물(HWPX·분석 페이지·대시보드)이 자동 동기화되게 한다. |

---

## PDCA 사이클 요약

### Plan
- **문서**: `docs/01-plan/features/ncs-book-concentration.plan.md` (v1.1 Approved)
- **목표**: 교재별 집계를 정본에 추가하고, 기초보고서와 대시보드에서 집중·편차를 명시
- **결정**: D1~D6 모두 연구책임자 2026-09-17 승인
  - D1 (b) `books[]` 정본 payload 추가
  - D2 (a) 제3장 2절 " 5) 교재별 집중과 편차", 소결 → 6)
  - D3 (b) 표 12-3(집중도) + 표 12-4(상위 10권)
  - D4 (a) 제목 "안전관리" 규칙 + 기대 집합 고정
  - D5 (a) 교과서는 JSON 행만, 보고서 문안 NCS만
  - D6 (b) 대시보드 NCS 표만(차트 제외)
- **소요**: 계획 13:07 시작 → v1.1 승인(결정 6건) → 설계 20:34 (2026-09-17)

### Design
- **문서**: `docs/02-design/features/ncs-book-concentration.design.md` (v1.0)
- **설계 항목**: 63개 (payload·파생 사실·템플릿·3단계·감사·대시보드·하니스·대조 JSON·문서·연쇄)
- **주요 설계**:
  - `_book_title` 규칙: LM 코드·판 토큰·목록 접두 제거
  - `books_digest` 해시: 교재 간 재배분 탐지(총계 같아도 행 배분 변화 포착)
  - `ConcentrationFacts` 파생: 안전관리 전용·제외 집계·분야·평균·중앙값·상위 10권(templates 15피스)
  - 3단계 삽입: 2단계 `_Ledger.last_inserted` 로 원소 받아서(파일 재탐지 금지), " 5) 교재별 집중과 편차" 블록 삽입

### Do
- **구현**: 2026-09-17 설계 승인 뒤 → Do 완료 20:56 (TDD 5회전: RED → GREEN); Check·Act-1 은 23:12
- **구현 파일**:
  - 확장: `semantic_keyword_recount.py`(`_book_title`·`books[]`·`check_books`·`_books_digest`·`EXPECTED`)
  - 확장: `hwpx_methods_bridge.py`(2단계 모듈에 `BookRow`·`GroupConcentration`·`ConcentrationFacts`·`load_concentration_facts`·템플릿 추가, +214줄)
  - 확장: `hwpx_results_refresh.py`(3단계 블록·`_Ledger.last_inserted`·목차·`SECTION_LABEL`)
  - 확장: `docs/semantic_grade_dashboard.js`(`books()` 함수·"교재별 현황" 절)
  - 테스트: `test_semantic_keyword_recount.py`(+5)·`test_hwpx_methods_bridge.py`(`ConcentrationFactsTests` 2·`ConcentrationTemplateTests` 3·E2E 확장)·`test_hwpx_results_refresh.py`(`CommittedDiffTests`)·`outputs/test-dashboard-data.js`(S3q·S3r·S1w·S1x)

### Check
- **분석 문서**: `docs/03-analysis/ncs-book-concentration.analysis.md`
- **초회 결과**: 89.8% (118항목: 일치 96 · 변경 10 · 부분 12 · 불일치 0)
- **갭**: 10건 (G1~G10: Medium 1 · Low 9)
  - G1: data README 대조 JSON 행 내용(layout·토큰·concentration 블록·표 12-3/12-4)
  - G2~G9: 분야별 등급 합 가드·항등식·테스트 강도·문서 문구·EXPECTED 주석·TODOS·메모리

### Act (Act-1)
- **처리**: 10건 갭 모두 닫힘(같은 세션 23:12~)
- **변경 내용**:
  - G1: data README 행을 20260917 실행값으로 재작성
  - G2: 분야별 등급 합 가드 3곳(TDD, RED→GREEN 확인)
  - G3: `detected_pages <= pages` 항등식 교정
  - G4: 테스트 보강(3권 수사·E2E 캡션·review_text)
  - G5: Σ`detected_pages` 등식 가드 추가
  - G6: CLAUDE.md·README 문구 수정(3곳)
  - G7: `hwpx_results_refresh.py` 문자열(docstring — 추적 파일 11종 정정 포함·argparse·h1 2곳·거부 문구 "이미 2·3단계 산출물") 3단계 반영, `--force` 재실행으로 `review.html` 재생성(HWPX·대조 JSON 바이트 동일)
  - G8: `EXPECTED` 주석 재정렬
  - G9: TODOS 5·Polaris 확인 기록 갱신
  - G10: 메모리 기록(정본 실행일·결정·HWPX 이름)
- **검증**: unittest 242 OK · 하니스 83/83 · 대조 JSON 바이트 동일 · 정본 재실행 HWPX sha 일치
- **결과 Match Rate**: **100%**

---

## 산출물 & 검증

### 추적 산출물

| 파일 | 형식 | 내용 | 비고 |
|---|---|---|---|
| `docs/03-analysis/data/semantic_summary.json` | JSON | `corpora.*.books[]` (NCS 86 / 교과서 9행) 추가 | `meta.run.generated_at` 2026-09-17, `expected` true · `force` false |
| `docs/semantic_recount_data.js` | JS | 위와 동일(렌더용) | +18.8 KB (48 → 67 KB) |
| `keyword-analysis.html` · `NCS_키워드검색결과.html` · `교과서_키워드검색결과.html` | HTML | 정본 재실행 산출 | 실행일 2026-09-17, xlsx 이름 `…_20260917.xlsx` |
| `docs/03-analysis/data/hwpx_results_refresh_20260917.json` | JSON | 3단계 산출: `concentration` 블록(삽입 15·표 12-3/12-4·conditions·dedicated), `bridge.toc` 1/2, `renumbered` 4)→6) | 신규 추적, 20260915 판은 계보로 남음 |
| `docs/03-analysis/hwpx-results-refresh/review.html` | HTML | 표 12-3·12-4 절 추가(헤더 행 포함), h1 에 3단계 표기(Act-1 G7) | 표·그림만, 본문 문장 없음 |

### 비추적 산출물

| 파일 | 형식 | 내용 | 용도 |
|---|---|---|---|
| `data/반도체 기초보고서_20260917_정본.hwpx` | ZIP | 원본 + 정본 1·2·3단계 갱신 | 발표 문서 |
| `data/semantic_keyword_recount_20260917.xlsx` · `_20260917_report.md` | XLSX · MD | 정본 재실행 산출(본문 포함, 비추적) | xlsx 10시트(`NCS_파일별`·`교과서_파일별` 포함) — 20260915 판은 그대로 보존 |

### 검증 항목

| 항목 | 결과 | 근거 |
|---|---|---|
| 설계 항목 구현률 | 100% (118/118) | 갭 분석 Act-1 완료, 불일치 0 |
| 정본 수치 매칭 | 100% | 정본 재실행: 해시 4종·총계·등급·`reseg_agreement` 불변 |
| `books[]` 집계 | 86/9(0건 교재 포함) | NCS 11,517/2,502 · 교과서 1,207/115 |
| 교재별 숫자 | 86권 검증 | `check_books`(행 수·출현·등급 4종·Σ검출 쪽·분야별 4종·교재마다 등급 3 쪽 ≤ 검출 쪽) + `S3q`·`S3r` + 커밋 JSON 재계산 `books_digest` |
| 숫자 감사 | OK (1,168 토큰·미일치 0, 2단계 1,052 에서 +116) | `Facts.value_index()` — 1·2단계 사실(추적 파일 11종) + `ConcentrationFacts.value_pairs()`(`books.*` 키); 손 허용 목록 없음, `STALE_PATTERNS` 검사 포함 |
| 테스트 | unittest 242 OK · 하니스 83/83 | `test_semantic_keyword_recount` 112 · `test_hwpx_methods_bridge` 55 · `test_hwpx_results_refresh` 48 · 대시보드 83 |
| 재현성 | OK (동일 입력 → 동일 해시) | 정본 재실행 `EXPECTED` 통과, HWPX sha 동일 |
| 조건 분기 | 양쪽 테스트 | 전용 1권·2권·3권 수사 · 제외 후 비율 내려감/올라감/거의 같음 · 분야 과반/비과반 · 0건 과반/비과반 |

---

## 연구책임자 결정 기록

### 기본 결정 (D1~D6, 계획 §6 — 연구책임자 2026-09-17)

| 항목 | 선택 | 반영 |
|---|---|---|
| **D1 교재별 집계의 자리** | **(b) `semantic_summary.json` `corpora.*.books[]`** (a 는 별도 추적 파일) | 정본 재실행 2026-09-17 → 연쇄 산출물 갱신, 대시보드·보고서가 한 파일을 본다 |
| **D2 보고서 위치** | **(a) 제3장 2절 신설 " 5) 교재별 집중과 편차"**, 소결 → 6) | 2단계 블록(4)) 뒤에 장부 `last_inserted` 로 삽입, 목차 2항목 삽입 |
| **D3 표 구성** | **(b) 표 12-3(집중도) + 표 12-4(상위 교재 10권)** | 둘 다 4열(표 12 원형 복제), 헤더 포함 8행·11행 |
| **D4 "안전관리 전용" 식별** | **(a) 제목 "안전관리" 규칙 + 기대 집합 고정** | `DEDICATED_TITLE_RULE`·`DEDICATED_EXPECTED_CODES = (LM1903060329, LM1903060411)`, 어긋나면 정지 |
| **D5 교과서** | **(a) JSON 에는 교재 행, 보고서 문안은 NCS 만** | 교과서 9행(`code` null, 표시명 = 분야); 교과서 집중은 제안 C |
| **D6 대시보드** | **(b) NCS 교재별 표 추가** (차트 제외) | "NCS 교재별 현황" 절 86행 + 리드 문단, 교과서 페이지는 절 없음(`S1x`) |

### 구현 결정 기록 (설계 §6)

| 항목 | 결정 |
|---|---|
| 파생값 저장 | 집중도·분포는 저장하지 않고 `books[]` 에서 `load_concentration_facts` 가 매번 파생(출처 하나) |
| `books_digest` | 말뭉치·식별자·출현·등급·검출 쪽·등급 3 쪽 행의 정렬 해시 — `pages`·`title`·`group` 은 제외(쪽수는 입력 sha256 이 고정, 제목 규칙은 `DEDICATED_EXPECTED_CODES`·`S3r` 가 잡는다) |
| 표 원형 | 표 12 의 4열 원형만 복제, 행 수만 조정 |
| 하니스 ID | 설계의 S3p·S1r·S1s 는 기존 ID 와 충돌 → S3q·S1w·S1x, S3r 추가 |

---

## 구현 요약

### 코드 변경 (`git diff --numstat`, 미커밋 작업 트리)

| 모듈 | 변경 | +/− |
|---|---|---|
| `semantic_keyword_recount.py` | `_book_title`·`dashboard_payload` books 행·`check_books`·`_books_digest`·`EXPECTED.books/books_digest` | +87/−2 |
| `hwpx_methods_bridge.py` | 상수 6종·`BookRow`·`GroupConcentration`·`ConcentrationFacts`·`load_concentration_facts`·표 12-3/12-4 템플릿·`concentration_paragraphs` | +214/−1 |
| `hwpx_results_refresh.py` | 3단계 블록·`_Ledger.last_inserted`·목차 삽입 2·`diff["concentration"]`·`SECTION_LABEL`·검토 순서·3단계 문구(Act-1) | +36/−17 |
| `docs/semantic_grade_dashboard.js` | `bookRows`·`books` — "NCS 교재별 현황" 절 | +14/−0 |
| `outputs/test-dashboard-data.js` | S3q(books 불변식)·S3r(전용 2권 965·38.6%·0건 57)·S1w·S1x | +31/−0 |
| `test_semantic_keyword_recount.py` | payload 행·제목 규칙·metrics/`EXPECTED`·가드 거부·`check_books` 직접 검사(Act-1)·커밋 JSON 재계산 | +98/−0 |
| `test_hwpx_methods_bridge.py` | `ConcentrationFactsTests`·`ConcentrationTemplateTests`·E2E 확장·거부 문구 | +127/−13 |
| `test_hwpx_results_refresh.py` | `CommittedDiffTests` 14표·layout 125/913/125·목차 2·6) | +10/−5 |
| 문서 4 | CLAUDE.md +6/−6 · README +4/−4 · TODOS +3/−3 · data README +2/−2 | |

**합계**: 12파일 +632/−53줄(테스트·문서 포함). 산출물(`semantic_summary.json`·`data.js`·분석 페이지 3·대조 JSON·review.html)은 별도.

### 데이터 흐름

1. `semantic_keyword_recount.py` → `corpora.*.books[]` (NCS 86·교과서 9)
2. → `semantic_summary.json` 저장 & `dashboard_payload` 포함
3. → `docs/semantic_recount_data.js` 렌더 데이터
4. → `hwpx_methods_bridge.load_concentration_facts()` 파생 사실 적재
5. → `concentration_paragraphs()` 템플릿 생성
6. → `hwpx_results_refresh.refresh_methods_bridge()` 2·3단계 조립
7. → `…_20260917_정본.hwpx` + `hwpx_results_refresh_20260917.json` + `review.html`
8. → `semantic_grade_dashboard.js` 대시보드 렌더

### 가드 & 검증

| 항목 | 규칙 | 실측 |
|---|---|---|
| `books[]` 교재 수 | NCS 86 · 교과서 9 | ✓ |
| `books[]` 합 == 말뭉치 총계 | 각 등급(1/2/3/unpaged)·`detected_pages` | ✓ |
| 분야별 합 == `groups[]` | total·grades·pages·documents | ✓ |
| 안전관리 전용 집합 | `DEDICATED_EXPECTED_CODES` == 2권 | ✓ (LM1903060329, LM1903060411) |
| `books_digest` | 교재 재배분 탐지 | `9c57f39963c6c7cd` 고정 |
| 숫자 감사 | 1,168 토큰 · 모두 `value_pairs` 키 | 미일치 0 |
| HWPX 바이트 | 손댄 문단 밖 불변 | 재실행 동일 |

---

## 교훈 & 이월

### 잘 된 점

1. **갭 분석의 사실 검증**: 에이전트 초안 118항목을 실측(수치·행 번호·파일)으로 다시 확인한 뒤 10건을 Act-1 로 닫음 — 정본 재실행 없이(가드·테스트·문서만)
2. **데이터 주도 가드**: 손으로 넣는 숫자 0건 — 문단·셀의 모든 숫자가 `books[]` 파생 `value_pairs` 키로 해소되고, `check_books`·`books_digest` 가 쓰기 전에 재배분을 잡는다
3. **조건 분기 양쪽 테스트**: 전용 1권/2권/3권 수사, 제외 후 비율 세 방향, 분야·0건 과반 여부를 fixture 로 강제해 정본이 밟지 않는 가지도 검증
4. **정본 재실행의 연쇄**: 실행일 변경이 자동으로 HWPX·분석 페이지·data.js·하니스를 함께 갱신

### 개선 여지

1. **숫자 감사의 문맥 무지**: 작은 수(3·10·57)가 우연에 일치해도 통과 — 대조 JSON `keys` 로 추적해 보상
2. **산출물 재입력 불가**: 원본 HWPX에서만 출발 가능 → 정본을 입력으로 주면 거부(`"이미 2·3단계 산출물"`)
3. **한글 렌더링 미자동화**: 표 너비·쪽 넘김·목차 쪽수 검증은 HWP 소프트웨어 필요 — `[→E2E]` 항목

### 후속 항목 (TODOS "기초보고서 보강 후속")

| ID | 항목 | 상태 |
|---|---|---|
| **B2** | 보조 분모(100쪽당 출현·검출 쪽 비율·키워드별 출현 교재 수) | 이제 정본 `books[].pages`·`detected_pages` 로 계산 가능 — 연구책임자 선택 시 |
| **B4·B5** | 판정 한계 상자·원문 검토 목록 | 문안 초안 없음 |
| **C** | 교과서 보강(T05·T04, 법·제도 키워드 0/9) | 교과서 `books[]` 행은 있음(D5) — 문안·표는 미착수 |
| **D·E·F** | 자동 판정 검증 부록 · 30 키워드×교육주제 점검표 · 제4장 근거–설계 연결표 | 문안·표 초안 없음 |
| **한글 `[→E2E]`** | 3단계 정본의 둘째 문단·목차 5)·6)·" 6) 소결"·쪽 넘김(표 12-4 가 Polaris 에서 36/37쪽에 갈림), 기존 (0)(a)(b)(c) | 한글 열람 시; Polaris Drive 자동 업로드 설정 확인 먼저 |
| **커밋** | 이 기능은 아직 미커밋(작업 트리) | `/pdca archive` → `/ship`(커밋·PR) |

---

## 재현 절차

### 환경

- 정본 재실행: `openpyxl` 이 깔린 Python(3.13 사용), 비추적 입력 — `data_source/markdown/{ncs,school-text}`, 워크북 2종, `data/markdown/ncs_paged/`(84권 줄→쪽 대응).
- HWPX: 원본 `data/반도체 기초보고서_20260911.hwpx`(비추적) + ImageMagick `magick`(그림 3 재렌더; `--no-render` 는 점검만).

### 실행 (README 산출물 재생성 절의 정본 명령 — 실행일 20260917)

```bash
python3 semantic_keyword_recount.py \
  --source-workbook data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx \
  --ncs-root data_source/markdown/ncs --school-root data_source/markdown/school-text \
  --xlsx-out data/semantic_keyword_recount_20260917.xlsx --report-out data/semantic_keyword_recount_20260917_report.md \
  --dashboard-data-out docs/semantic_recount_data.js --summary-out docs/03-analysis/data/semantic_summary.json \
  --analysis-dir docs --previous-basis docs/03-analysis/data/reseg_summary.json \
  --page-maps data/markdown/ncs_paged --reseg-csv docs/03-analysis/data/ncs_pages_reseg.csv

python3 hwpx_results_refresh.py --force     # 원본 → …_20260917_정본.hwpx (기존 정본은 <이름>.<sha16>.bak), 대조 JSON·review.html 재생성
```

`EXPECTED`(`books` 86/9·`books_digest 9c57f39963c6c7cd` 포함)가 어긋나면 첫 명령은 아무것도 쓰지 않는다. 정본을 입력으로 주면 두 번째 명령은 "이미 2·3단계 산출물" 로 거부한다.

### 테스트

```bash
python3.13 -m unittest test_semantic_keyword_recount test_hwpx_methods_bridge test_hwpx_results_refresh test_expression_review   # 242 OK
node outputs/test-search-equivalence.js; node outputs/test-dashboard-data.js; python3 outputs/test-recount-grades.py
node outputs/run-core-logic-tests.js; node outputs/test-sri.js                                                                   # 24 · 83 · 390 · 32 · 38
```

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-17 | 초안 — 계획·설계·구현·분석(89.8% → Act-1 100%) 통합; report-generator 초안의 사실 오류(결정 선택지·행 수·재현 명령·감사 근거·소제목 표기) 정정 | Claude (Opus 5) |
