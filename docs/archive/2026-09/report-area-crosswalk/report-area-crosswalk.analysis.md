# Gap Analysis: report-area-crosswalk

> **Date**: 2026-09-22 | **Design**: `docs/02-design/features/report-area-crosswalk.design.md` (1.1 — §3.2a 장부 이동) | **Plan**: `docs/01-plan/features/report-area-crosswalk.plan.md` (D1 (b)·D2 (b)·D3 W1·D4 무시·D5 (a))
> **Analyst**: gap-detector 에이전트(설계 항목 77건, 파일:행 근거) + Claude 검토 | **Branch**: `feat/report-area-crosswalk`

---

## Match Rate: 93.5% (72.0 / 77) → Act-1 뒤 **97.4%** (75.0 / 77)

| 구분 | 항목 | Check | Act-1 |
|---|:---:|:---:|:---:|
| §1 목표 G1–G7 | 7 | 6.5 | 6.5 |
| §2.1 변경 파일 | 8 | 7.5 | 7.5 |
| §3.1 · §3.2a · §3.3 · §3.4 · §3.5 | 27 | 27 | 27 |
| §3.6 보관 | 4 | 3.5 | 3.5 |
| §3.7 문서 | 9 | 7.0 | 9.0 |
| §4 테스트 T1–T9 | 9 | 9 | 9 |
| 계획 FR-01~FR-11 | 11 | 10 | 11 |
| 절차(재실행 결정론 · Polaris 확인) | 2 | 1.5 | 1.5 |
| **합계** | **77** | **72.0** | **75.0** |

남은 2.0 은 (i) 메모리 갱신(Report 단계 몫) 1.0, (ii) `_INDEX.md` 의 이 기능 절·표 행과 상호 링크(archive 단계 몫) 0.5, (iii) Polaris/한글 렌더 확인(계획된 `[→E2E]` 이월, TODOS 5) 0.5.

## 요약

- 설계 1.1(§3.2a: 본문 소제목 "(4)" 재작성 + `_Ledger` 이동)과 연구책임자 결정 D1~D5 가 코드·산출물·테스트에 그대로 반영됐다. **결정과 충돌하는 구현 없음.**
- 정본 데이터(`semantic_summary.json`·`semantic_recount_data.js`·XLSX·`reseg_summary.json`)와 대시보드(`index.html`·`textbook.html`)는 무변경. 대조 JSON 은 교과서 절 7문단·표 8·`relocation` 블록만 실질 변경, NCS·사고·2·3단계 블록은 `keys`(값 출처 경로)만 재료 → 장비로 이동.
- 정본 HWPX sha `1b46474225e03233` = 대조 JSON `output_sha256` = 재실행본(결정론). 백업 `….9ef93187cd38f10e.bak`(Polaris 재저장본, D4).
- 검증: 하니스 24/84/390/32/38, unittest 257 OK.

## 항목별 결과 (요약)

| 영역 | 결과 | 근거(파일:행) |
|---|---|---|
| G1 권수 분기·"0권, 총 0쪽" 불출현 | ✅ | `hwpx_results_refresh.py:708-719`; `test_hwpx_results_refresh.py:493-494` |
| G2 사고·SDS 문단 장비 블록 뒤, (4) 한 문장 | ✅ | `relocate_accident_paragraph` `:1014-1028`; E2E 순서 `:839-843`; 정본 top-level 406~418 |
| G3 영역명 `AREA_LABEL`, "재료·인프라" 는 locator 4곳뿐 | ✅ | `:704,:782`; grep 단언 `:514-517` |
| G4 옛 값 197·501 감사 탈락(9.6% 는 NCS 개발 비중과 충돌 — 키 고정) | ✅ | `:424-432` |
| G5 정본·해시·XLSX·대시보드 무변경, 재실행 동일 | ✅ | `git status`; sha 비교 |
| G6 대조 JSON·review.html 새 대응, mock 제거 | ✅ | `CommittedDiffTests:36-90`; JSON `relocation`·layout 126/914/126 |
| §3.1 `titles`(대응표 선언 순) | ✅ | `:236-243`(설계 "등장 순" 문구는 Act-1 로 정정) |
| §3.2a 소제목·0권 문장·사고·SDS 공통 텍스트·장부 이동·`located` | ✅ | `:744-800`, `:1595` |
| §3.3 조건 6행 | ✅ | `:755-762`; JSON `:277-463` |
| §3.4 표 8·감사·`largest_area`·타 절 동일 | ✅ | review.html 재료 0 행; audit ok 1,167 토큰 |
| §3.5 이름·계보 | ✅ | data README `:12` |
| §3.6 09-19 문서 4건 보관·재저장본 주석·상태 | ✅ / `_INDEX.md` 상호 참조는 archive 몫 ⚠️ | `docs/archive/2026-09/semantic-report-area-symmetry/` |
| §3.7 CLAUDE.md (a)~(e)·README·data README·TODOS | ✅ (Act-1 후) | (e) "slot swap" 표현·data README layout 계보는 Act-1 |
| §3.7 메모리 | ❌ → Report 단계 | |
| T1~T9 | ✅ 9/9 | T1 은 `test_facts_from_canonical_files` 에 흡수; T4 는 §3.4 조정 |
| FR-01~FR-11 | ✅ 10 + ⚠️ FR-10(메모리)·FR-11(상호 참조) | FR-06 "문단 45" 는 1.1 로 46 — Act-1 로 계획 문구 정정 |

## ➕ 설계에 없던 구현 (기록)

- `corpus_facts` 가 `groups[]`(이름순)를 **대응표 선언 순**으로 정렬해 접는다 — 산문의 『』 나열이 분류표 순서(『기초기술 1』·『2』·『기초』)를 따르게. CLAUDE.md 는 이미 그렇게 서술.
- `INFRA_TEXTBOOK`·`ACCIDENT_LOCATOR`·`EQUIPMENT_TAIL_LOCATOR` 상수화.
- `_Ledger.remove` 가 재작성된 사고·SDS 문단을 `text_pairs` 에 (구문, "") 로 넣어 비추적 `review_text.html` 에는 "삭제 + 삽입"으로 보인다 — 무해.

## 갭 목록과 처분

| # | 심각도 | 갭 | 처분 |
|---|---|---|---|
| 1 | 낮음 | 메모리(`ncs-book-concentration.md` 의 정본 sha `aa0f3453…`·124/912/124, 새 `report-area-crosswalk.md` 없음) | Report 단계에서 갱신 |
| 2 | 낮음 | `_INDEX.md` 요약표·서두 목록에 09-19 기능 행 없음, "(아래)" 참조 대상(이 기능 절) 미존재 | archive 단계에서 이 기능 절 + 표 2행 + 상호 링크 |
| 3 | 낮음 | `CLAUDE.md:216` "slot swap" (폐기된 1.0 방식) | **Act-1 완료** — "the 사고·SDS paragraph relocation through the ledger" |
| 4 | 낮음 | data README 한 행에 124·912·124 와 126·914·126 공존 | **Act-1 완료** — "2026-09-17 실행 → 2026-09-21 재생성" 계보 표기 |
| 5 | 낮음 | 설계 §3.1 "등장 순" vs 구현 "대응표 선언 순"; 계획 FR-06 "문단 45" vs 46 | **Act-1 완료** — 설계 §3.1·§2.2 문구, 계획 FR-06 주석 |
| 6 | 정보 | Polaris/한글 렌더 미확인 — 새 정본의 1절 2) 7문단·표 8 | 계획된 이월(TODOS 5 `[→E2E]`), 연구책임자 판단 |

## Act-1 (2026-09-22)

갭 3·4·5 를 문구 수정으로 닫았다(코드·산출물 무변경, 하니스 84/84 재확인). 남은 갭 1·2 는 각각 Report·Archive 단계의 정규 작업이라 거기서 처리한다.

## Verification Evidence

- unittest `python3.13 -m unittest test_semantic_keyword_recount test_hwpx_methods_bridge test_hwpx_results_refresh test_expression_review`: **Ran 257 tests — OK** (09-19 승계 253 + 이 기능 4: T2·T3·T4·T5; T1·T6~T9 는 기존 메서드에 흡수)
- 하니스: `test-search-equivalence` 24/24 · `test-dashboard-data` 84/84 · `test-recount-grades` 390/390 · `run-core-logic-tests` 32/32 · `test-sri` 38/38
- 정본 HWPX `data/반도체 기초보고서_20260917_정본.hwpx` sha256 `1b46474225e03233…` — 문단 46·표 14·그림 3, 감사 1,167 토큰·미일치 0, layout 126/914/126, 재실행 바이트 동일(HWPX·대조 JSON·review.html)
- 대조 JSON HEAD 대비: `paragraphs` locator 집합 동일 + 소제목 locator 1 추가; 실질 변경은 교과서 절 7문단(리드·개발·제조·장비·소제목·재료·사고 SDS)뿐, 다른 절은 `keys` 만 이동; `tables` 는 표 8 만 변경(21 → 24 셀); `relocation {inserted 2, removed 2}`
- `git status`: `semantic_summary.json`·`semantic_recount_data.js`·XLSX·`docs/*.html` 무변경

## Next Steps

- [x] Match rate ≥ 90% → `/pdca report report-area-crosswalk` (메모리 갱신 포함)
- [ ] archive 시 `_INDEX.md` 상호 참조(갭 2)
- [ ] `/ship` 은 연구책임자 지시 뒤
