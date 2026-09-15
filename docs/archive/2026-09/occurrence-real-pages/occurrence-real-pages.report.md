# 의미 출현을 실제 PDF 쪽에 얹기 — 완료 보고

> **Feature**: occurrence-real-pages
> **Completed**: 2026-09-15
> **설계 항목 구현률 (Match Rate)**: 초기 90.8% → **Act-1 반영 후 100%**
> **PR**: #17 (미머지, https://github.com/DrunkenZealnut/searchinmd/pull/17)
> **승인**: 연구책임자 (D1~D6 전부 A, 2026-09-15)

---

## Executive Summary

### 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **Feature** | 정본 의미 재검산(사전 v2, NCS 11,517건)의 "페이지"는 마크다운 쪽 표식이었다 — 86권 중 23권만 실제 쪽이고 63권은 목차에서 유도한 블록이라 한 "페이지"가 실제 1쪽이기도 41쪽이기도 했고(외부감사 M2), 등급도 2026-04 워크북 라벨 상속(6,292건)과 현재 블록 판정(5,225건)이 섞여 있었다. `resegment.py`가 이미 만든 줄→실제 쪽 대응(84권)을 재사용해 모든 NCS 출현을 실제 PDF 쪽에 놓고 등급을 하나의 기준선 규칙으로 다시 낸다. |
| **기간** | 2026-09-15 (계획~ship 1일) |
| **커밋** | 기능 3개(핵심·HWPX·문서) + 갭 분석/Act-1 + 커버리지 + ship 리뷰 수정 3개(pre-landing·adversarial·문서 동기화) + CodeRabbit 수정 1개 — PR #17 10 커밋 |
| **변경 파일** | `semantic_keyword_recount.py` · `occurrence_real_pages_impact.py`(신규) · `hwpx_results_refresh.py` · `page_utils.py`/`resegment.py`(상수 공유) · `docs/semantic_grade_dashboard.js` · `docs/index.html` · `test_semantic_keyword_recount.py` · `test_hwpx_results_refresh.py` · `outputs/test-dashboard-data.js` · README·CLAUDE.md·`docs/03-analysis/data/README.md`·`docs/04-report/features/semantic-occurrence-grades.report.md`·`docs/03-analysis/expression-review.analysis.md`·`TODOS.md` |

### 결과 요약

```
┌─────────────────────────────────────────────┐
│  설계 항목 구현률: 90.8% → Act-1 100%        │
├─────────────────────────────────────────────┤
│  ✅ 일치:  62 → 76 / 76 항목                  │
│  🟡 부분:  14 → 0 / 76 항목                   │
│  🔴 불일치: 0 / 76 항목                       │
└─────────────────────────────────────────────┘
```

| 항목 | 값 |
|---|---|
| **설계 항목** | 76개 (일치 62 / 부분 14 / 불일치 0) → Act-1 후 76 / 0 / 0 |
| **갭(Check)** | 11건 (G-1 High 1 · Low 10) |
| **Act-1 처리** | 11건 전부 닫힘 |
| **연구책임자 결정** | D1~D6 전부 A(2026-09-15) |
| **테스트 커버리지 (Step 7 감사)** | 69.5% → 96.6% |
| **하니스** | unittest 137 → 175(이 기능 몫 38건 신설: `RealPageTests` 19·`ImpactScriptTests` 7·`CommittedImpactTests` 1·`LineConventionTests` 7·`RealPageBasisTests` 4) · `test-dashboard-data.js` 68 → 79(신설 11) · `test-recount-grades.py` 390 · `test-search-equivalence.js` 24 · `run-core-logic-tests.js` 32 · `test-sri.js` 38 — 모두 통과 |
| **정본 결과** | NCS 11,517건 → 등급 3,788 / 5,227 / 2,502 (등급3 21.7%, `grade_sources` 전부 `real-page`); 교과서 1,207건 불변; 공유 쪽 2,035/2,035 등급 100% 일치 |

### 1.3 Value Delivered — 4관점 가치 분석

| 관점 | 내용 |
|---|---|
| **Problem** | 발표 중인 출현 기준 등급 분포는 두 종류의 "페이지"(실제 쪽 23권 + 대응 없는 2권 / 목차 블록 61권 — 블록 하나가 실제 1~41쪽)와 두 종류의 등급(워크북 라벨 상속 / 블록 텍스트 판정)이 섞인 값이었다(외부감사 M2). 같은 규칙으로 실제 쪽에 다시 판정하면 출현 4,016건(34.9%)의 등급이 이동한다는 것이 실측으로 확인됐다. |
| **Solution** | `resegment.py`의 줄→실제 쪽 대응(84권, 정렬 자기 검증 ±1쪽 94.9%)을 `--page-maps` 로 입력해 NCS 출현마다 실제 쪽을 붙이고, 등급은 실제 쪽 본문에 `regrade.grade_page` 기준선 하나로 판정했다(이전 기준과 공유 쪽 2,035개에서 100% 일치 — 같은 규칙임을 `EXPECTED`가 고정). 표식이 실제 쪽인 2권은 표식을 그대로 쓴다. 정본 재실행 → `EXPECTED` 재고정 → 대시보드·README·CLAUDE.md·기초보고서(HWPX) 재생성까지 한 기능에서 끝냈다. |
| **Function/UX Effect** | 독자는 "페이지"가 어느 교재에서나 PDF 한 쪽임을 전제로 등급 분포·분야별 쪽수(마커 최댓값 합 8,914 → PDF 쪽수 9,100)를 읽을 수 있다. 대시보드 브리지 절은 "같은 실제 PDF 쪽 기준·같은 규칙이지만 검출 쪽 집합은 다르다(닿은 실제 쪽 2,492개 vs 이전 기준 2,189쪽, 공유 2,035개 전부 일치)"로 두 KPI의 관계를 데이터에서 그린다(리뷰에서 "분모만 다르다"는 느슨한 문구를 이렇게 고쳤다). |
| **Core Value** | 등급 모집단의 동질성 확보 — 감사 M2 종결. 비단조 마커 1권(TODOS 3)과 분야별 쪽수 기준(TODOS 1(d))도 같은 변경으로 닫혔다. 발표값의 등급3 비율은 거의 그대로(21.9 → 21.7%)지만 이제 "실제 쪽에 하나의 규칙"이라는 말로 설명된다. `/ship` 리뷰 3단계(전문가 6 + 레드팀 + Codex, Codex 적대적, CodeRabbit)를 거치며 대응↔이전 기준 결속 검증·영향표 성능(21.7 → 14.0 s)·블록 폭 표 정확도(이중 계수 제거) 등 정본 수치 밖의 견고성도 함께 올라갔다. |

---

## 2. 관련 문서

| 단계 | 문서 | 상태 |
|---|---|---|
| Plan | [occurrence-real-pages.plan.md](../../01-plan/features/occurrence-real-pages.plan.md) | ✅ Approved (연구책임자 D1~D6 전부 A) |
| Design | [occurrence-real-pages.design.md](../../02-design/features/occurrence-real-pages.design.md) | ✅ Implemented (결정 기록 12행) |
| Check | [occurrence-real-pages.analysis.md](../../03-analysis/occurrence-real-pages.analysis.md) | ✅ Complete (90.8% → Act-1 100%) |
| Act | 이 문서 | ✅ 완료 |

---

## 연구책임자 결정 기록 (2026-09-15, 전부 A)

| ID | 질문 | 채택 | 근거 |
|---|---|---|---|
| **D1** | NCS 등급 규칙 | 실제 쪽 본문에 regrade 기준선 하나(워크북 라벨 상속 없음) | 라벨은 목차 블록이라 실제 쪽에 대응되지 않는다; 이전 기준과 100% 같은 규칙 |
| **D2** | 대응 없는 새 2권 | 표식(실제 쪽)을 그대로 쓰고 명시 목록(`REAL_PAGE_MARKER_BOOKS`)으로 허용 | `resegment.py` 재실행(D2-B)은 `NCS_PDF_ROOT` 확보 뒤 별개 결정으로 미룸 |
| **D3** | 발표 | 새 정본으로 교체(대시보드·README·CLAUDE.md), 블록 기준 v2는 영향표 열로 보존 | 감사 M2 종결 |
| **D4** | 분야별 쪽수 | PDF 쪽수(9,100) | `TODOS.md` 1(d) 종결 |
| **D5** | 비단조 마커 1권 | 대응으로 대체되므로 재유도 없이 종결 | `LM1903060113`도 정렬 대응으로 실제 쪽이 붙어 표식 순서가 더는 쓰이지 않는다 |
| **D6** | 기초보고서 HWPX | 정본 재실행 뒤 원본(20260911)에서 재생성 | `…_20260915_정본.hwpx` |

---

## 3. 완료 항목

### 3.1 기능 요구사항 (FR-01~FR-10)

| ID | 요구사항 | 상태 | 비고 |
|---|---|---|---|
| FR-01 | `--page-maps DIR`로 NCS 출현에 실제 쪽 덧씌우기(`apply_page_maps`) | ✅ 완료 | Act-1에서 줄 규약(`splitlines` vs `split("\n")`) 통일(G-1) — 정본 코퍼스 87건 재검사, 쪽 경계 영향 0건 |
| FR-02 | 대응 없는 문서는 명시 목록(D2)만 허용 | ✅ 완료 | 표식 1..N 연속 검사; 리뷰에서 `--marker-correct` 변형 대응 거부 추가 |
| FR-03 | 실제 쪽 본문에 기준선 하나(`real-page` 출처), 워크북 상속 폐기 | ✅ 완료 | 목록 교재(대응 없는 2권)도 `real-page` — 설계 §2·§3.3 갱신(G-2) |
| FR-04 | 이전 기준(`ncs_pages_reseg.csv`)과 공유 쪽 등급 일치율을 `EXPECTED`로 고정 | ✅ 완료 | 2,035/2,035 = 100%; `label` 출처 행 제외(G-3); 대응은 `meta.md_corpus_sha256`·PDF 쪽수 상한에 결속(레드팀) |
| FR-05 | 분야별 쪽수 = PDF 쪽수(D4), `meta.page_basis` | ✅ 완료 | 9,100 = 대시보드·README·CLAUDE.md·HWPX 동일값(하니스 S3n) |
| FR-06 | manifest·`EXPECTED` 재고정 | ✅ 완료 | `page_maps`·`real_page_marker_books`(`[{code,pages}]`)·`reseg_agreement`·`page_maps_sha256`; `--reseg-csv`도 입력 7번째로 지문 기록(리뷰) |
| FR-07 | 영향표(`occurrence_real_pages_impact.json`, 신규) | ✅ 완료 | 이동 4,016건, `by_source` existing 52.8%/new 79.9%, 교재 3분류(23/61/2, `per_book.method` 기준 — 적대적 리뷰로 비율 규칙에서 전환), 블록 폭 표(CodeRabbit로 이중 계수 제거) |
| FR-08 | 대시보드 브리지 절·정적값 | ✅ 완료 | "같은 실제 PDF 쪽 기준·같은 규칙, 검출 쪽 집합은 다르다"로 수정(리뷰+CodeRabbit) |
| FR-09 | HWPX 재생성(`page_basis` 분기, 날짜 접미) | ✅ 완료 | 출력 sha `aa06344b…` 최종 재확인 |
| FR-10 | 문서(README·CLAUDE.md·data README·TODOS) | ✅ 완료 | 문서 동기화 서브에이전트가 4곳 추가 정정(등급 결합 보고서 계보 표, 표현 점검 §6 등) |

### 3.2 비기능 요구사항

| 항목 | 목표 | 달성 | 상태 |
|---|---|---|---|
| 실행 시간 | 2배 이내 | 34.7 s(대응) vs 34.8 s(대응 없음) — 변화 없음 | ✅ |
| 테스트 커버리지 | 60%(최소)/80%(목표) | 96.6% | ✅ |
| 결정론 | 같은 입력 → 같은 해시 | `test_two_runs_on_same_fixture_are_identical` 확장, 정본 2회 실행 해시 동일 | ✅ |
| 추적 산출물 | 절대 경로·본문 없음 | `public_path()` 전면 적용, 스캔으로 확인 | ✅ |
| 보안 | Critical 0 | 리뷰 아미 security 전문가 NO FINDINGS | ✅ |

### 3.3 산출물

| 산출물 | 위치 | 상태 |
|---|---|---|
| 정본 요약 | `docs/03-analysis/data/semantic_summary.json` | ✅ |
| 대시보드 데이터 | `docs/semantic_recount_data.js` + 분리 HTML 3건 | ✅ |
| 영향표(신규) | `docs/03-analysis/data/occurrence_real_pages_impact.json` | ✅ |
| HWPX 정본(비추적) | `data/반도체 기초보고서_20260915_정본.hwpx` (sha `aa06344b…`) | ✅ |
| HWPX 대조 JSON | `docs/03-analysis/data/hwpx_results_refresh_20260915.json` | ✅ |
| 테스트 | `test_semantic_keyword_recount.py`(`RealPageTests`·`LineConventionTests`·`CommittedImpactTests`) · `test_hwpx_results_refresh.py`(`RealPageBasisTests`) | ✅ |
| 문서 | README·CLAUDE.md·`docs/03-analysis/data/README.md`·`docs/04-report/features/semantic-occurrence-grades.report.md`·`docs/03-analysis/expression-review.analysis.md`·`TODOS.md` | ✅ |

---

## 4. 미완료·이월 항목

### 4.1 다음 사이클로 이월

| 항목 | 사유 | 우선순위 | 근거 |
|---|---|---|---|
| ④ `--marker-correct` 채택(D2-B) — 마커 ±1 보정, 새 2권 대응 생성 | `NCS_PDF_ROOT=data/markdown/ncs/pdf` 로 로컬 재실행이 가능해졌으나 채택은 연구책임자 결정 | Medium | `TODOS.md` ④ |
| ④ 적대적 리뷰 INVESTIGATE 3건 | LM 코드 규약 2종 통일, `resegment.py` 실행 id로 결속 강화, `expression_review impact` JSON `page_basis` 표기 | Low | 수치 영향 없음 |
| ④ 단순화 자문 1건(`run_census`/`main()` metrics 중복 계산 ~1 s) | 연구책임자: 이번 PR에서는 보류 | Low | D3 (ship 자문) |
| ⑥ F11(조건부 규칙 겹친 짧은 매칭) | 정본 워크북이 `data/` 로 복귀해 재실행 가능해졌으나 시점은 연구책임자 결정 | Medium | `EXPECTED` 재고정 수반 |
| 한글(HWP) E2E 확인 | 표 너비·쪽 나눔·목차 쪽수 — 자동 검증 밖 | Medium | `TODOS.md` 5(c), `[→E2E]` |
| Codex 적대적 패스 재실행 | 9분 초과로 이번 ship에서는 결과 없음(누락 커버리지로 PR 본문에 명시) | Low | 다음 리뷰에서 재시도 |

### 4.2 취소·보류 항목

| 항목 | 사유 | 대안 |
|---|---|---|
| gstack 업그레이드 | ship 결정에서 "지금 아님"(스누즈) | 다음 세션에서 재문의 |
| `--no-page-maps` CLI 옵션 | 정본은 대응 없이 만들 수 없다는 설계 결정(§6-3) — 옵션 자체를 두지 않음 | 블록 기준은 영향표 스크립트 내부에서만 |

---

## 5. 품질 지표

### 5.1 최종 분석 결과

| 지표 | 목표 | 최종 | 변화 |
|---|---|---|---|
| 설계 항목 구현률(Match Rate) | 90% | 100% | +9.2%p (Act-1) |
| 테스트 커버리지 | 80% | 96.6% | — |
| 보안 이슈 | Critical 0 | 0 | ✅ |
| 정본 재실행 가드 | 통과 | `expected: true`, 2회 실행 해시 동일 | ✅ |
| Codex 구조 리뷰 P1 | 0 | 0 (P2 1건, 수정 완료) | GATE PASS |

### 5.2 해결된 이슈

리뷰 아미·레드팀·Codex·CodeRabbit을 합쳐 총 **58건** 접수, critical 0, 전부 조치(자동 수정/TDD 수정/근거 있는 보류로 분류):

| 라운드 | 건수 | 해결 |
|---|---|---|
| Pre-landing review (testing·maintainability·security·performance·design·simplification + red team + Codex design voice) | 54건 | 47 자동 수정, 7 보류(TODOS 기록) |
| Claude 적대적 서브에이전트 | 12건 | 6 수정(영향표 교재 분류 `per_book.method` 전환, 대응 결속, 오류 메시지 등), 6 INVESTIGATE 이월 |
| Codex 구조 리뷰(`codex review --base main`) | 1건(P2) | 수정(영향표도 이전 기준 결속 검사) |
| Codex 적대적(9분 초과) | 0건(결과 없음) | 커버리지 누락으로 기록 |
| CodeRabbit(PR #17) | 3건 | 전부 수정 — 블록 폭 표 이중 계수(영향표 4-9쪽 3,024 → 3,022), 브리지 문구, HWPX 테스트 견고성 |

주요 예:

| 이슈 | 해결 | 결과 |
|---|---|---|
| 줄 규약 불일치(`splitlines` vs `split("\n")`, G-1 High) | `_to_matching_lines`로 매칭 규약에 옮겨 싣기 | 정본 87건 재검사, 쪽 경계 영향 0건 — 수치 불변 |
| 영향표 블록 폭 표 이중 계수(CodeRabbit) | 블록을 줄 범위로 식별 | 합 11,104 → 11,102(= 대응 교재 출현 수) |
| 영향표 교재 분류가 비율 규칙으로 2권을 오분류(Claude 적대적 1) | 이전 기준 `per_book.method`로 전환 | 25/59/2 → 23/61/2 |
| `run_census` 대응 결속 없음(레드팀) | `check_page_maps_against_previous_basis` — `md_corpus_sha256`+PDF 쪽수 상한 | 대응이 옛 마크다운 판·다른 교재의 것이면 거부 |
| 대시보드 "분모만 다르다" 과잉 단순화(Codex design·CodeRabbit) | "같은 실제 쪽 기준·같은 규칙, 검출 쪽 집합은 다르다"로 재작성 | README·보고서·대시보드 3곳 일관 |

---

## 6. 갭 분석과 Act-1 처리

### 갭 분석 결과 (Check, 2026-09-15)

| 갭 ID | 심각도 | 내용 |
|---|:---:|---|
| G-1 | **High** | 줄 번호 규약 불일치 — 매칭(`splitlines`)과 대응(`split("\n")`)이 정본 1권(`LM1903060128`)에서 실제로 어긋남 |
| G-2~G-11 | Low (10건) | 설계 문서 미갱신(D2 목록 교재 출처, `label` 행 제외 등), CLI 기본값, 문서 잔존 구 문구, 테스트 설계 미충족·하니스 ID 중복, 영향표 원자적 쓰기·계보 검증, 결속 안내, 설계 외 추가 미기록, 정렬 자기 검증 미병기, 실행 시간 미측정 |

### Act-1 처리 (2026-09-15) — 11건 전부 닫힘

| ID | 처리 |
|---|---|
| G-1 | **닫힘** — `_to_matching_lines`로 대응을 매칭 규약(`splitlines`)으로 옮겨 싣기; `LineConventionTests` 회귀 테스트. 정본 재검사: `LM1903060128` 430행 이후 출현 87건 중 쪽 경계 0건 → **정본 수치·해시 불변** |
| G-2 | **닫힘** — 설계 §2·§3.3에 "목록 교재도 `real-page`" 명시, §6 결정 8 |
| G-3 | **닫힘** — 설계 §3.4에 `label` 출처 제외 명시, §6 결정 9 |
| G-4 | **닫힘** — `--page-maps`·`--reseg-csv` CLI 기본값 부여, 대응 폴더 부재를 `FileNotFoundError`로 |
| G-5 | **닫힘** — README·보고서·data README 4곳의 구 날짜 문구 정정 |
| G-6 | **닫힘** — 제외·보류 레코드 덧씌우기·목록 교재+대응 동시 존재·변형 사전+대응·결속 불일치 거부·두 실행 동일 해시 테스트 추가; 하니스 ID 중복 개명 |
| G-7 | **닫힘** — 영향표 쓰기를 `SKR._write_text_atomic`으로, 설계에 계보 검증 상수·위치 짝짓기 문서화 |
| G-8 | **닫힘** — `run_census` 가드 출력에 결속 불일치 원인 문장 + `disagree` 상위 5건 |
| G-9 | **닫힘** — 설계 §6 결정 11로 설계 외 추가 7건 명문화 |
| G-10 | **닫힘** — 영향표 `meta.alignment_self_check`에 정렬 자기 검증 수치 병기 |
| G-11 | **닫힘** — 실측: 34.7 s vs 34.8 s, 실행 시간 변화 없음 확인 |

Act-1 뒤 재분석: 부분 14 → 0, **Match Rate 100% (76/76)**. 재검사 명령(unittest·대시보드·recount) 전부 통과, 영향표 재생성으로 수치 불변 확인.

### Ship 리뷰(PR #17) 반영 — 설계 결정 12

Pre-landing review(전문가 6 + 레드팀 + Codex design voice), 적대적 리뷰(Claude 12건 + Codex 구조 리뷰 P2 1건), CodeRabbit 3건이 이 갭 분석 이후 추가로 반영됐다(§5.2 표 참고). 설계 문서 결정 기록 12행에 전부 기술; 테스트 154(Act-1 종료 시점) → 175, 하니스 71 → 79. 기능 시작 전 기준선(main `f28d496`)은 unittest 137·하니스 68이었다.

---

## 한계와 이월

### 측정 한계

1. **정렬 오차**: 이전 기준과 같은 대응(DP 후보 줄 ±1쪽 94.9%)을 그대로 쓰므로 새 정본도 같은 수준의 오차를 물려받는다 — 개선(마커 보정 `--marker-correct`)은 별도 결정(TODOS ④).
2. **교재 분류 대체 규칙**: 영향표의 `by_book_kind`는 이전 기준 `per_book.method`를 우선하지만, method를 모르는 경우의 대체 규칙(블록 수/실제 쪽 수 ≥ 0.8)은 여전히 근사치다.
3. **Codex 적대적 패스 미실행**: 9분 제한으로 결과를 받지 못했다 — 이 커버리지는 다음 리뷰 사이클에 다시 시도해야 한다.
4. **LM 코드 규약 2종 병존**: `_document_code`(파일명 우선)와 경로 첫 일치가 4개 함수에서 각각 쓰인다 — 현재 코퍼스(87파일)는 불일치 0이라 영향 없지만, 폴더/파일 코드가 다른 신규 교재가 들어오면 잠재 위험이다.

### 설계 이월

| 항목 | 상태 | 근거 |
|---|---|---|
| `--marker-correct` 채택(D2-B) | 이월(TODOS ④) | `NCS_PDF_ROOT` 확보로 로컬 재실행은 가능해졌으나 연구책임자 결정 대기 |
| LM 코드 규약 통일 | 이월(TODOS ④, INVESTIGATE) | 적대적 리뷰 5 |
| `resegment.py` 실행 id 결속 | 이월(TODOS ④, INVESTIGATE) | 적대적 리뷰 6 |
| `run_census`/`main()` metrics 중복 계산 제거 | 이월(TODOS ④, 자문) | 연구책임자: 이번 PR 보류 |
| 한글 E2E 확인 | 이월(TODOS 5(c)) | 자동 검증 밖 |

### 문서화

- **결속 규약**: `check_page_maps_against_previous_basis`가 대응↔이전 기준의 마크다운 판·PDF 쪽수 상한을 검증 — CLAUDE.md "4. Semantic recount" 그룹에 명문화.
- **집계 단위 문구**: "분모만 다르다"는 표현을 대시보드·README·등급 결합 보고서 3곳에서 "같은 실제 쪽 기준·같은 규칙, 검출 쪽 집합은 다르다"로 통일(리뷰+CodeRabbit).
- **계보 표**: `docs/03-analysis/data/README.md`에 `occurrence_real_pages_impact.json` 추적 목적·연혁 기록.

---

## 재현 절차

### 1. 대응·이전 기준 확인 (이미 있는 산출물)

```bash
ls data/markdown/ncs_paged/*.pages.json | wc -l   # 84
cat docs/03-analysis/data/reseg_summary.json | python3 -c "import json,sys;print(json.load(sys.stdin)['pages'])"   # 2189
```

### 2. 정본 재실행

```bash
python3.13 semantic_keyword_recount.py \
  --source-workbook data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx \
  --ncs-root data_source/markdown/ncs --school-root data_source/markdown/school-text \
  --xlsx-out data/semantic_keyword_recount_20260915.xlsx \
  --report-out data/semantic_keyword_recount_20260915_report.md \
  --dashboard-data-out docs/semantic_recount_data.js \
  --summary-out docs/03-analysis/data/semantic_summary.json \
  --analysis-dir docs \
  --page-maps data/markdown/ncs_paged --reseg-csv docs/03-analysis/data/ncs_pages_reseg.csv
```
→ `semantic_summary.json`(`meta.run.expected true`, `page_basis.NCS = "real"`, `reseg_agreement {2035, 2035}`)

### 3. 영향표

```bash
python3.13 occurrence_real_pages_impact.py \
  --source-workbook data/ncs_keywords_in_markdown_results_20260402_재판정_20260414.xlsx \
  --ncs-root data_source/markdown/ncs --school-root data_source/markdown/school-text \
  --page-maps data/markdown/ncs_paged
```
→ `occurrence_real_pages_impact.json`(블록 기준 vs 실제 쪽 기준, 이동 행렬 4,016건)

### 4. HWPX 재생성

```bash
python3.13 hwpx_results_refresh.py --hwpx "data/반도체 기초보고서_20260911.hwpx" --force
```
→ `data/반도체 기초보고서_20260915_정본.hwpx`(sha `aa06344b…`), `docs/03-analysis/data/hwpx_results_refresh_20260915.json`

### 5. 테스트

```bash
node outputs/test-search-equivalence.js
node outputs/test-dashboard-data.js
python3 outputs/test-recount-grades.py
node outputs/run-core-logic-tests.js
node outputs/test-sri.js
python3.13 -m unittest test_semantic_keyword_recount test_expression_review test_hwpx_results_refresh
PATH=/usr/bin:/bin python3 -m unittest test_hwpx_results_refresh
```
→ 24 · 79 · 390 · 32 · 38 · 175 OK · 44 OK(1 skip) 확인

---

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-15 | 계획·설계·갭분석(90.8%)·Act-1(100%)·ship 리뷰(pre-landing·adversarial·CodeRabbit) 정리 — 완료 보고 최초 작성 | Claude (Opus 5, bkit report-generator) |
