# hwpx-methods-bridge-refresh — 설계·구현 갭 분석 (Check → Act-1)

> **Feature**: hwpx-methods-bridge-refresh · **Design**: `docs/02-design/features/hwpx-methods-bridge-refresh.design.md` (D1~D6 (a)) · **Plan**: `docs/01-plan/features/hwpx-methods-bridge-refresh.plan.md`
> **Date**: 2026-09-16 · **Analyst**: gap-detector 에이전트(대조표) + Claude (Opus 5) (Act-1 반영·재평가)
> **결과**: 초회 **98.2 %** (109항목: 일치 105 · 부분 4 · 불일치 0, 갭 Medium 1 · Low 8) → Act-1 뒤 **100 %** (갭 9건 전부 닫힘)

## 1. 대조 범위

| 구분 | 항목 수 | 근거 문서 |
|---|---:|---|
| 설계 §3.1~§3.11 (데이터 확장·사실·XML 능력·A/B3 절차·템플릿·감사·대조 JSON·백업·문서) | 73 | design §3 |
| 설계 §4 테스트 설계 | 15 | design §4 |
| 계획 FR-01~FR-14 | 14 | plan §3.1 |
| 계획 §4 성공 기준 | 7 | plan §4 |
| **합계** | **109** | |

비교 대상: `hwpx_methods_bridge.py`(신규), `hwpx_results_refresh.py` 2단계·XML 능력·장부 검사·백업, `occurrence_real_pages_impact.py` `pages` 확장, 테스트 4모듈(`test_hwpx_methods_bridge.py` 신규), 추적 산출물 3건, 문서 5종.

## 2. 항목별 결과 (요약)

| 설계 절 | 일치 | 부분 | 불일치 | 비고 |
|---|---:|---:|---:|---|
| §3.1 데이터 출처 확장 (FR-12) | 5 | 0 | 0 | `pages.real_page_grades` 1,825/524/143 · `pages.교과서` 388(335/45/8), 합 불변식, `S3o` 확장(79 유지) |
| §3.2 사실 | 8 | 0 | 0 | 필드·출처 키·파생값 모두 정본 값과 일치(58·618/612/17·80~84%·13~21%·7·84·2·6/5·1,847/1,839·538/238/300/1,609·1,785/2,492/4,016·6,292/52.8·2,189/7,769/2,035); 계보 가드 6+1종 |
| §3.3 XML 능력·장부 검사 | 10 | 0 | 0 | 순번 검사는 `check_untouched` 로 대체됨(옛 `inside` 검사 0건) |
| §3.4 A 절차 | 10 | 1 | 0 | 목차 5절 소제목 수 가드가 "8개 정확" 이 아니라 "6개 이상" (G1) |
| §3.5 A 템플릿 | 12 | 0 | 0 | 문안·분기·범위 표기·계열 라벨 일치 |
| §3.6·§3.7 B3 절차·템플릿 | 11 | 0 | 0 | 피스 15개 순서, 동사 ±0.5pp, 표 12-1·12-2 4열×6행(+헤더), 소결 5), ctrl 문단 뒤 새 문단(+빈 문단) |
| §3.8 감사 | 5 | 0 | 0 | STRIP 확장, 감사 범위(1~3절 재탐지 + 5절 + 표 4 + 목차), `out_of_scope` 제거 |
| §3.9 대조 JSON·검토 HTML | 5 | 0 | 0 | 스키마 일치(+`table_id`·`caption_changed`·`real_pages_vs_block` 추가) |
| §3.10 출력·백업 | 2 | 0 | 0 | `.<sha8>.bak`, `--no-render` 무백업 |
| §3.11 문서 | 4 | 0 | 0 | data README·CLAUDE.md·README·TODOS |
| §4 테스트 설계 | 12 | 3 | 0 | 계보 불일치 3종 테스트 없음(G2), 목차 8개 오류 테스트 없음(G1), 감사 심기 1종·STRIP 직접 단언 없음(G3) |
| FR-01~14 | 14 | 0 | 0 | |
| 성공 기준 | 7 | 0 | 0 | 정본 실행 감사 1,048 토큰·미일치 0(ship 리뷰 뒤 제2장 1절 편입으로 1,052), 하니스 24/79/390/32/38 |
| **합계** | **105** | **4** | **0** | **98.2 %** |

## 3. 갭 목록과 Act-1 처리

| ID | 심각도 | 갭 | 처리 (2026-09-16) |
|---|:-:|---|---|
| G1 | Medium | 목차 5절 소제목 수 가드가 `< 6` 만 거부(설계: 8개가 아니면 오류) | `OLD_METHODS_TOC_ENTRIES = 8`, `!= 8 → ValueError`; 테스트 `test_toc_with_other_than_eight_old_entries_is_refused`(항목 하나 지운 fixture) |
| G2 | Low | 계보 가드 중 `grades.real`·`pages.real_pages`·`page_maps.sha256` 불일치 테스트 없음 | `test_refuses_each_lineage_mismatch` (subTest 4종: + `pages.교과서.detected_pages`) |
| G3 | Low | 감사 테스트가 "813" 만 심고 STRIP 확장 5패턴 직접 단언 없음 | `test_audit_strips_stage2_notations_and_flags_stale_numbers` — 표 12-1·2026-04·v1fix·3-gram·±1쪽·(4) 참조 = 미일치 0, 12,875·813 은 미일치. **알려진 한계**: "85종" 의 85 는 코딩 표본 control 층(85쪽)과 겹쳐 통과한다 — 숫자 감사는 문맥을 모른다 |
| G4 | Low | 소결 문장 S1 의 숫자·출처 키가 대조 JSON 에 없음 | `bridge.conclusion` 기록(numbers·keys·conditions); 추적 diff JSON 재생성(HWPX 바이트 동일 — sha e9856fad…) |
| G5 | Low | 교과서 `grade_sources` 부재 시 P4 가 "0건" 을 조용히 출력 | `load_facts` 가 ValueError("0 으로 채우지 않는다"); 테스트 `test_load_facts_refuses_summary_without_grade_sources` |
| G6 | Low | 정본 산출물을 입력하면 1단계 locator 실패 메시지만 나옴 | `refresh()` 시작에서 5절 소제목/2절 새 소절 제목이 이미 있으면 "이미 2단계 산출물 … 원본에서 다시" 로 선제 거부; 테스트 갱신 |
| G7 | Low | 경계값(±0.5pp·1.0pp)·표 12-1 차이 합 0·분야 순서 단언 없음 | `test_branches` 에 `_trend(±0.5/±0.51)`, `sum(차이) == 0`, 개발<제조<장비<재료 순, 1.0pp 안 케이스 추가 |
| G8 | Low | §6 결정 기록 미보강(삭제 범위 방식·표 4 셀 탐지·58 산출 규칙), 일부 키 접근이 KeyError | 설계 §6 에 9행 추가; `groups`·`precision/recall`·`keywords[].name` 접근을 `_get` 경유로 |
| G9 | Low | README 인라인 명령 `--force` 누락, docstring·argparse·검토 HTML 제목이 "제3장" 만 언급, `test.yml` 주석 "3종" | 문구 갱신(README `--force`·`.bak`, docstring 2단계, argparse, review/text 제목, 주석 4종) |

재평가: 부분 일치 4건이 모두 일치로 바뀌어 **109/109 = 100 %**. 검증: `test_hwpx_methods_bridge`(36; ship 리뷰 뒤 49) · `test_hwpx_results_refresh`(44) · `test_semantic_keyword_recount` · `test_expression_review` OK; 정본 원본 점검 실행(`--no-render`) 문단 45·표 12·그림 3·토큰 1,048·미일치 0; `--force` 재실행 산출 HWPX 바이트 동일.

## 4. 설계 외 구현·의도적 차이 (기록)

| 항목 | 설계 | 구현 | 판단 |
|---|---|---|---|
| `MethodsFacts.marker_books` | `Facts.marker_books` 사용 | 필드로도 보유(값 동일) | 템플릿 모듈이 HR 을 import 하지 않기 위함 |
| `CorpusFacts.grade_sources` | 미명시 | P4 의 1,149/58 출처 `corpora.교과서.grade_sources` | 출처 명시 — 개선 |
| 계보 가드 7번째(교과서 detected_pages) | 6종 | +1 | 개선 |
| 5절 삭제 범위 | locator 4 + 뒤 빈 문단 | 첫~끝 locator 연속 범위 | 결과 동일(6), §6 기록 |
| 표 4 셀 탐지 | 둘째 열·셋째 행 | "반도체개발" 문단을 가진 셀 1개 | 견고, §6 기록 |
| P1 dedup 절 | "…세지 않았고, ⟨절⟩" | "…세지 않았다.⟨절⟩" | 절이 없어도 문장이 닫힘 |
| Q2 일부 일치 문구 | "{agree}쪽에서 일치" | "{pages}쪽 중 {agree}쪽에서 일치" | 계획 FR-07 문구 |
| `next_object_id` | id·zOrder 각각 | `next_object_ids` → `(id, zOrder)` | 이름·반환형 |
| `table4.changed_cells` | 예시 5 | 실제 바뀐 셀 2 + `caption_changed` | 1단계의 "실제 변경" 의미와 일관 |
| STRIP `\d\)\s*참조` | 추가 | 미추가 — "(4) 참조" 는 `\(\d+\)` 가 덮음 | 등가(테스트 G3 확인) |
| 소결 문장 | S1 | 빈 문단 + S1 | §6 "빈 문단" 결정 |
| 최대 표식 폭 | 초안 53 | 58 (`;` 분리) | 초안의 `|` 분리 오류 — 데이터로 바로잡힘 |
| 이전 기준 날짜 | 초안 "2026년 9월 7일" | `previous_basis.date` 2026-09-06 (ISO) | §6 날짜 결정 |

## 5. 잔여 (자동 검증 밖)

- `[→E2E]` 한글(HWP)에서 5절 길이·2절 표 2개 삽입 뒤 쪽 넘김·표 12-1·12-2 열 너비(표 12 복제) 확인.
- 숫자 감사의 문맥 무지(작은 수의 우연 일치 — 예: 85) 는 1단계부터의 알려진 한계.
- 제안서의 나머지 항목(B1·B2·B4·B5·C·D·E·F)과 Codex 미반영 항목은 TODOS "기초보고서 보강 후속" 절.

## 6. 판단

Match Rate 100 % (초회 98.2 %). `/pdca report hwpx-methods-bridge-refresh` 진행 가능.
