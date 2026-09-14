# semantic-expression-review — 설계 대비 구현 갭 분석

> 분석일: 2026-09-14 · 브랜치 feat/semantic-expression-review · 설계 대비 구현 갭 분석 (bkit Check)
> 설계: `docs/02-design/features/semantic-expression-review.design.md` (§3.1~3.8 상세, §4 테스트 대응표, §5 구현 순서, §6 결정 기록 — 결정 2·3 포함) · 계획: `docs/01-plan/features/semantic-expression-review.plan.md` (FR-01~FR-10, §4 성공 기준)
> 구현: `semantic_keyword_recount.py`, `expression_review.py`, `test_semantic_keyword_recount.py` (`DictionaryVersionTests`), `test_expression_review.py`, `.github/workflows/test.yml`, 산출물 `docs/03-analysis/data/expression_review_{key,A,B,adj,scores,impact}.json`, `semantic_summary.json`, `docs/03-analysis/data/README.md`, `CLAUDE.md` 그룹 4, `docs/superpowers/specs/2026-09-08-semantic-keyword-recount-design.md` "보류 정책" 절
> **연구 결과(정밀도·κ·영향표)는 별도 문서 `expression-review.analysis.md` 다.** 이 문서는 설계 항목이 구현·테스트·산출물에 어떻게 대응하는지만 본다.

---

## 1. 요약

| 항목 | 값 |
|---|---|
| **Match Rate** | **96.0 %** (60.5 / 63 설계 항목) |
| 산식 | (일치 × 1 + 부분 × 0.5 + 불일치 × 0) ÷ 설계 항목 수 = (58 + 5 × 0.5 + 0) ÷ 63 |
| 상태 분포 | 일치 58 · 부분 5 · 불일치 0 |
| Gap | 설계 항목 갭 5건 (Medium 1 · Low 4) + 설계 항목 외 문서 정합 3건 (Low 2 · Info 1) — §6 |
| 하니스 | `python3.13 -m unittest test_semantic_keyword_recount test_expression_review` → **Ran 77 tests, OK** (62 + 15) · `node outputs/test-dashboard-data.js` → **64/64 PASS** · `python3 outputs/test-recount-grades.py` → **390/390 PASS** (§8) |
| 판정 | ≥ 90 % — Report 단계 진행 가능. **Act-1 (2026-09-14): G-1~G-8 전부 닫힘** (§10) — 재분석 시 부분 5 → 0, Match Rate 100 % (63/63) |

설계와 다르게 구현된 점 중 **결정 기록(§6)으로 정당화되는 것 4건**(`DEFAULT_DICTIONARY` v2, `SAMPLE_DICTIONARY` v1fix, 정확 키워드 `PSM` 조건부, 영향표의 정본 열 = v2)은 갭으로 세지 않았다(§5). 결정 없이 달라진 것만 부분(0.5)으로 셌다.

---

## 2. FR 별 대응표 — 설계 ↔ 구현 ↔ 테스트

| FR | 설계 항목 | 구현 위치 | 테스트 | 상태 |
|---|---|---|---|:-:|
| FR-01 영문 정확 키워드 단어 경계 | §3.1 (a) | `semantic_keyword_recount.py: build_default_rules` — `pattern=_ascii_term(keyword) if fixed and re.fullmatch(r"[A-Za-z0-9 ]+", keyword)`; `_ascii_term` | T `test_v1fix_english_exact_keywords_need_word_boundary` (v1 부분 문자열 2건 → v1fix 0건, `PSM` 단독 1건, `MSDSX` 제외). 설계의 `v1_keeps_substring_behaviour` 는 이 테스트 안에 합쳐짐 | 일치 |
| FR-02 보류 표현의 정확 규칙 내 계수 차단 | §3.1 (b) | `_HELD_INSIDE["안전"]` (`안전성`, `안전\s*(?:마진\|여유\|재고\|율\|계수)`), `ExpressionRule.held_patterns`, `HELD_INSIDE_REASON = "보류 표현 내부"`, `scan_document` 의 `held_spans` 우선 판정; 요약 `SummaryRow.excluded_exact` 가 exact 제외 전부(사유 불문)를 합산 → "동음이의 제외" 열에 합산 | T `test_v1fix_excludes_held_expressions_inside_안전` | 일치 (설계는 `exclusions["안전"]` 추가, 구현은 별도 필드 — 사유 분리 요구를 만족하기 위한 선택) |
| FR-03 층화 표본 + 시트(비추적)·키(추적) | §3.2 | `expression_review.py: REVIEW_TARGETS`(22 튜플), `SAMPLE_DICTIONARY="v1fix"`, `collect_records`(보류는 probe 규칙), `_allocate`(비례·최소 1), `build_sample`(`SEED` 20260914, `PER_EXPRESSION` 30, 미만이면 전수), `window_text`(앞줄·«매칭»줄·뒷줄, 마커·빈 줄 제외), `sheet_and_key`, `sample_digest`(정규화 JSON sha256 앞 16자), `write_sample`(`--force` 없이는 키 보호, `.md` 사본) | E `test_collect_records_probes_held_targets_without_counting_them`, `test_sample_is_deterministic_and_stratified_and_takes_all_below_cap`, `test_window_marks_expression_and_keeps_neighbours`, `test_sheet_has_no_anchoring_fields_and_key_has_no_text`, `test_write_sample_refuses_to_overwrite_key_without_force` (설계 6개 → 5개, 두 쌍 합침 + 창 테스트 추가) | 일치 |
| FR-04 코더 2계열 + 불일치 목록 + 재정 | §3.3 | `code_pages.py` 무변경 (A `--backend claude-cli`, B `--provider-env`), `score_coding.family_guard` → `scores.meta.family_warning`; `expression_review.py main` `score --list-disagreements`(id·keyword·expression·A·B·adj 표), `validate_adj`(digest·라벨 ∈ {1,2,?}·id 존재); 산출 `expression_review_A.json`(claude-opus-5) / `_B.json`(gpt-5.6-sol) / `_adj.json`(17건, 연구책임자) | E `test_adj_file_is_validated`, `test_score_carries_tier_and_family_warning`; `code_pages` 는 기존 R15 | 부분 — `code_pages.parse_grade` 는 `3` 을 `errors` 가 아닌 `grades` 에 넣는다(설계 §3.3 "`3` 이 오면 `errors`" 와 다름). 실제 라벨엔 `3` 이 없고, 채점 시 `_norm` 이 `ValueError` 로 막는다 (G-2) |
| FR-05 정밀도·CP 95 % 구간·κ·후보 표시 | §3.4 | `precision_interval`(`_binom_cdf` + `_bisect`, stdlib), `kappa`, `final_labels`, `score`(`PRECISION_FLOOR` 0.8, `ALPHA` 0.05, `candidate` keep / hold_or_conditional), `companion_stats` → `meta.companions`·`expressions[].conditional`; 산출 `expression_review_scores.json`(22행, 후보 13) | E `test_precision_interval_matches_known_values`, `test_final_label_rules`, `test_score_flags_candidates_below_floor_and_has_no_nan`, `test_companion_stats_count_contexts_and_conditional_precision` | 부분 — `ALPHA`·`kappa` 를 `score_coding` 에서 재사용하지 않고 재정의(G-3); `meta.adopted` 가 결정 3 뒤에도 `null`(G-1) |
| FR-06 사전 v2 변형 + `--dictionary` 거부·기록 | §3.1·§3.5 | `DICTIONARY_VERSIONS`, `DEFAULT_DICTIONARY="v2"`, `_check_version`, `default_candidate_decisions(version)`(`replace(candidate, **override)`), `_V2_OVERRIDES`(보류 `방진화`·`케미컬`, 조건부 `방진복`·`장갑`·`X선`·`PSM`), `SAFETY_COMPANIONS`(12), `ExpressionRule.require_patterns` / `CandidateDecision.require_patterns`, `scan_document` 창 `block.lines[max(0, i-1):i+2]` + `NO_COMPANION_REASON`, `run_census` — 비정본이면 `docs/` 아래·`semantic_keyword_recount_\d{8}(_report)?.(xlsx\|md)` 거부, 불일치는 `meta.run.expected_mismatch` 기록·`meta.run.dictionary`; CLI `--dictionary` | T `test_dictionary_versions_and_default`, `test_require_patterns_exclude_without_companion_in_window`, `test_v2_overrides_apply_held_and_require`, `test_v2_decision_2_contents`, `test_v2_exact_psm_counts_only_with_companion`, `test_non_default_dictionary_refuses_tracked_outputs_and_records_mismatch` | 일치 (결정 3 으로 변형은 이제 `v1`·`v1fix`) |
| FR-07 v1 / v1fix / v2 영향표 | §3.5 | `expression_review.py: impact`(세 버전 메모리 집계, 쓰기 없음), `main impact`; 산출 `expression_review_impact.json` — v1 12,506 / 1,293 · v1fix 12,310 / 1,272 · v2 11,517 / 1,207, `excluded_by_fix`, `excluded_by_v2`; `expression-review.analysis.md` §6 (등급3 비율 세 버전 명시) | E `test_impact_has_three_versions_and_counts_fix_exclusions`, `test_impact_counts_what_v2_removes`, `test_impact_canonical_column_equals_canonical_summary` | 부분 — `excluded_by_fix` 가 `안전성` / `안전_마진류` 를 `held_inside` 하나로 합침(G-4). 말뭉치별 분리·`excluded_by_v2` 는 설계 초과 |
| FR-08 보류 정책 명문화 | §3.7 | `docs/superpowers/specs/2026-09-08-semantic-keyword-recount-design.md` "보류 정책 (2026-09-14, `semantic-expression-review` FR-08)" — 영문 일반어 / 계측·물성 문맥어 / 오염관리 장비어 / 가연성·발화성·인화성 4항 | — (문서) | 일치 |
| FR-09 v1 지문 불변 · 정본 버전 고정 | §3.1 | `V1_RULE_CONTENT_SHA256`, `rule_content_sha256`(keyword·expression·tier·pattern·exclude·held·require), `EXPECTED["dictionary"]` | T `test_v1_rule_content_digest_is_unchanged`, `test_dictionary_versions_and_default`(`EXPECTED["dictionary"] == "v2"`), `test_expected_block_is_fully_pinned`, `test_committed_summary_json_matches_expected` | 일치 (계획의 "v1 `rule_sha256` 불변" 은 결정 3 채택으로 "v1 규칙 내용 지문 고정" 으로 재해석 — 설계 §3.1 이 예고) |
| FR-10 채택 시 재실행·재고정·발표면 갱신 | §3.6 | `EXPECTED`(v2: 11,517 / 1,207, `rule_sha256` c08e6353…, `candidates` included 73 · held 21), `semantic_summary.json meta.run.dictionary = "v2"`, `expected` 통과; README(11,517 · 21.9 % · v2 설명), `CLAUDE.md` 그룹 4 + 등급 예외 문단, `index.html` 템플릿, `semantic-occurrence-grades.report.md`(v2 한 단락), `docs/03-analysis/data/README.md` 계보표 | 하니스 S1~S9 (64/64), R17 (390/390), unittest 77 | 일치 |

---

## 3. 설계 항목별 대조 (63 항목)

상태: **일치** = 기능·산출이 설계와 같음(구현 위치·이름 차이는 주석으로만) · **부분** = 일부 키/동작이 다르거나 빠짐 · **불일치** = 미구현 또는 모순.

| ID | 설계 (절) | 구현 | 상태 |
|---|---|---|:-:|
| D-01 | §2 `expression_review.py` "stdlib + openpyxl 불필요" | `import semantic_keyword_recount` 가 최상위에서 `openpyxl` 을 import 하고, `impact` 는 `SKR.load_existing_grades`(워크북) 를 읽는다 — openpyxl 필요 | 부분 |
| D-02 | §3.1 `DICTIONARY_VERSIONS = ("v1","v1fix","v2")` | 동일 | 일치 |
| D-03 | §3.1 `DEFAULT_DICTIONARY` — "v1fix", 결정 3 이후 "v2" | `"v2"` (결정 3 주석) | 일치 |
| D-04 | §3.1 `default_candidate_decisions(version)` — v1·v1fix 동일, v2 는 `_V2_OVERRIDES`(decision / require_patterns) 덧씌움 | `_v1_candidate_decisions()` + `replace(candidate, **override)` | 일치 |
| D-05 | §3.1 (a) ASCII 정확 키워드 단어 경계(`PSM`·`MSDS`), `re.IGNORECASE` 유지 | `build_default_rules` `fixed` 분기 | 일치 |
| D-06 | §3.1 (b) `안전` 안의 `안전성`·`안전 마진…` 제외, 사유 "보류 표현 내부" 별도 계수, 요약 열엔 합산 | `held_patterns`/`_HELD_INSIDE`/`HELD_INSIDE_REASON`; `excluded_exact` 합산 | 일치 (별도 필드) |
| D-07 | §3.1 `ExpressionRule.require_patterns`, 창 = 같은 줄 ± 1줄·블록 안, 사유 "안전 문맥 동반어 없음", v1·v1fix 는 빈 튜플 | `scan_document` `window` + `companion`; `NO_COMPANION_REASON` | 일치 |
| D-08 | §3.1 `rule_sha256` 변경 인지, v1 규칙 내용 지문을 테스트로 고정 | `rule_content_sha256`, `V1_RULE_CONTENT_SHA256` 6fc926de… | 일치 |
| D-09 | §3.1 `run_census --dictionary` 비정본 → `docs/`·기본 이름 경로 거부(`ValueError`) | `variant` 분기, 5개 출력 경로 검사 | 일치 |
| D-10 | §3.1 비정본은 `EXPECTED` 불일치 기록만, `meta.run.dictionary` | `force or variant` → `run_manifest`; `run["dictionary"]` | 일치 |
| D-11 | §3.1 `summary_metrics`·`EXPECTED` 에 `"dictionary"` | 둘 다 있음, 값 `"v2"` | 일치 |
| D-12 | §3.2 입력: 정본 코퍼스, 사전 v1fix | `SAMPLE_DICTIONARY = "v1fix"`, `_load_corpus`(`select_ncs_documents`) | 일치 |
| D-13 | §3.2 `REVIEW_TARGETS` 22개 `(keyword, expression)` 튜플 | 22개, 튜플만 | 일치 |
| D-14 | §3.2 보류 표현은 계수 없는 probe 스캔(`scan_document` 에 `probe_rules` 인자) | `collect_records` 가 probe `ExpressionRule` 을 만들어 `scan_document(doc, [rule])` 로 따로 스캔 — 기능 동일 | 일치 (구현 위치 상이) |
| D-15 | §3.2 정렬 → `random.Random(SEED).sample`, SEED 20260914, 30 미만 전수 | `build_sample`, `_allocate` | 일치 |
| D-16 | §3.2 층화 NCS/교과서 비례, 최소 1 | `_allocate`(반올림 보정) | 일치 |
| D-17 | §3.2 시트 항목 `{id, keyword, expression, text}` — 계층·근거·판정·등급 없음, 표현 «…» | `sheet_and_key`, `window_text` | 일치 |
| D-18 | §3.2 `coder_prompt()` 는 시트 JSON 안에만, 질문 하나 | `coder_prompt`, `sheet["coder_prompt"]` | 일치 |
| D-19 | §3.2 키 `{sample_digest, seed, targets, items[id,keyword,expression,corpus,path,line,text_sha256]}` | 동일 + `per_expression` 추가 | 일치 |
| D-20 | §3.2 `sample_digest` = 키 items 정규화 JSON sha256 앞 16자 | `sample_digest` | 일치 |
| D-21 | §3.2 `.md` 사본, 둘 다 `data/` 아래 gitignore | `write_sample`; `.gitignore` `/data/` | 일치 |
| D-22 | §3.2 `--force` 없이 키 덮어쓰기 금지 | `FileExistsError` | 일치 |
| D-23 | §3.3 코더 A `code_pages.py --backend claude-cli` | 모듈 docstring 명령, `expression_review_A.json` meta claude-opus-5 | 일치 |
| D-24 | §3.3 코더 B OpenAI 계열 + `family_guard` | `expression_review_B.json` gpt-5.6-sol; `meta.family_warning` null | 일치 |
| D-25 | §3.3 `parse_grade` 그대로, `1`/`2`/`?`; "`3` 이 오면 `errors`" | `_TOKEN = [123?]` — `3` 은 라벨로 저장됨; 채점 시 `_norm` 이 거부 | 부분 |
| D-26 | §3.3 `score --list-disagreements` 표 | `main` | 일치 |
| D-27 | §3.3 `adj.json` `{sample_digest, labels, note}` 스키마 검증 | `validate_adj`; 파일에 `adjudicator`·`date` 추가 | 일치 |
| D-28 | §3.4 최종 라벨: A == B → 값; ≠ → adj 또는 `?`; `?` 는 분자·분모 제외 | `final_labels`, `score` | 일치 |
| D-29 | §3.4 CP 정확 구간 stdlib, `ALPHA = score_coding.ALPHA`; κ = `score_coding.kappa(cats=(1,2))` | `precision_interval` stdlib ✓; `ALPHA = 0.05` 재정의, `kappa` 자체 구현(NaN 대신 None) | 부분 |
| D-30 | §3.4 `lower < 0.8` → `hold_or_conditional`, 상수 `PRECISION_FLOOR` | `score` | 일치 |
| D-31 | §3.4 `meta {sample_digest, coders, family_warning, alpha, floor, adopted}` | 모두 있음 + `companions`; `adopted` 는 결정 3 뒤에도 `null`, 설정 경로 없음 | 부분 |
| D-32 | §3.4 `expressions[] {keyword, expression, tier, n, k, precision, lower, upper, kappa, candidate, disagreements, adjudicated}` | 12키 모두 + `unknown`, `conditional` | 일치 |
| D-33 | §3.4 `overall {n, precision, kappa}` | 있음 + `k`, `disagreements`, `adjudicated` | 일치 |
| D-34 | §3.4 NaN 없음 | κ 미정의 → `null`; 테스트·산출물 확인 | 일치 |
| D-35 | §3.5 `_V2_OVERRIDES` 손으로 작성, 형식 `{"decision": "held"}` / `{"require_patterns": SAFETY_COMPANIONS}` | 6항목, 결정 2 주석 | 일치 |
| D-36 | §3.5 `SAFETY_COMPANIONS` 초기 12개 | 동일 12개 | 일치 |
| D-37 | §3.5 동반어 귀납 갱신 + 근거(O/X 출현 수)를 `scores.meta.companions` | `companion_stats` → `meta.companions.counts`; 갱신 불필요 판단이 `expression-review.analysis.md` §4·§6 에 기록 | 일치 |
| D-38 | §3.5 `impact` 는 코퍼스 1회 읽고 세 버전 메모리 집계, 쓰기 없음 | `impact()`; `main` 이 `--out` 에만 씀 | 일치 |
| D-39 | §3.5 `impact.json` `meta{corpus_sha256, versions}`, `totals`, `grades`, `keywords`, `expressions` | 동일 + `meta.documents`·`meta.keywords`·`meta.v2_overrides` | 일치 |
| D-40 | §3.5 `excluded_by_fix {PSM_substring, 안전성, 안전_마진류}` | `{NCS: {PSM_substring, held_inside}, 교과서: {…}}` — 말뭉치 분리는 초과, 안전성/마진류 미분리 | 부분 |
| D-41 | §3.5 등급3 비율(확정 분모) 세 버전 각각 명시 | JSON 엔 등급 수만(비율 유도 가능); CLI 출력·`expression-review.analysis.md` §6 표에 명시 | 일치 |
| D-42 | §3.5 정본 열 = `semantic_summary.json` (테스트 대조) | `test_impact_canonical_column_equals_canonical_summary` — `DEFAULT_DICTIONARY`(v2) 열 | 일치 (결정 3) |
| D-43 | §3.6 정본 실행 `--force` → `EXPECTED` 재고정(`dictionary` 포함) → 가드 통과 | `EXPECTED` v2 값, `semantic_summary.json meta.run.expected` 통과 | 일치 |
| D-44 | §3.6 README·CLAUDE.md·`index.html` 템플릿·이전 report 브리지 인용 갱신(S5·S7·S8) | 64/64 통과 | 일치 |
| D-45 | §3.6 `semantic-occurrence-grades.report.md` 에 재고정 한 줄 | 결과 표 아래 v2·v1fix·v1 계보 단락 | 일치 |
| D-46 | §3.6 v2 채택 시 같은 절차 반복 | 반복됨(결정 3) | 일치 |
| D-47 | §3.7 보류 정책 4항 명문화 | spec "보류 정책" 절 | 일치 |
| D-48 | §3.8 `data/README.md` 계보표에 파일 6종, 미발표 | 행 추가됨 | 일치 |
| D-49 | §3.8 `CLAUDE.md` 그룹 4 — `expression_review.py` 항목, 사전 버전 규약, `DEFAULT_DICTIONARY` | "Dictionary versions" + `expression_review.py` 항목 | 일치 |
| D-50 | §3.8 `.gitignore` — 시트는 `data/` 로 제외, 키·라벨 추적, 와일드카드 금지 | `/data/` 만; `expression_review_*` 패턴 없음 | 일치 |
| D-51 | §4 FR-01 T 2건 | 1건에 합침 | 일치 |
| D-52 | §4 FR-02 T 1건 | 있음 | 일치 |
| D-53 | §4 FR-03 E 6건 | 5건(합침) + 창 테스트 | 일치 |
| D-54 | §4 FR-04 E 1건 (+R15) | 있음 | 일치 |
| D-55 | §4 FR-05 E 4건 | 3건(합침) + 동반어·계열 테스트 | 일치 |
| D-56 | §4 FR-06 T 3건 | 2건(합침) + v2 테스트 3건 | 일치 |
| D-57 | §4 FR-07 E 2건 | 3건 | 일치 |
| D-58 | §4 FR-09 T 2건 | `expected_pins_dictionary_version` 은 `test_dictionary_versions_and_default` 안 | 일치 |
| D-59 | §4 FR-10 하니스 S1~S9·R17 | 64/64, 390/390 | 일치 |
| D-60 | §4 fixture 원칙 — 실데이터 없이, `post=` 가짜만 | E 는 fixture 2문서; `code_pages` 미호출 | 일치 |
| D-61 | §2/§4 CI 가 두 unittest 모듈을 돌림 | `test.yml` 마지막 단계 `test_semantic_keyword_recount test_expression_review` | 일치 |
| D-62 | §5 구현 순서 1~8 (결정 2·3 포함) 완료 | 산출물·결정 기록으로 확인 | 일치 |
| D-63 | §6 결정 기록 — 재정 17건, 결정 2, 결정 3 | 표에 있음 | 일치 |

---

## 4. 출력 스키마 대조

### 4.1 `expression_review_scores.json` (설계 §3.4)

| 키 | 설계 | 실제 | 비고 |
|---|---|---|---|
| `meta.sample_digest` | ○ | `9713a337b4d94bac` | 키·adj 와 일치 |
| `meta.coders` | `{A: model, B: model}` | `{"A": "claude-opus-5", "B": "gpt-5.6-sol"}` | |
| `meta.family_warning` | ○ | `null` | 2계열 확인 |
| `meta.alpha` / `meta.floor` | ○ | `0.05` / `0.8` | |
| `meta.adopted` | `null` (채택 결정을 여기에 — §1 원칙 4) | `null` | **결정 3(v2 채택) 뒤에도 null.** `score()` 가 상수 `None` 을 쓰고 CLI 에 설정 옵션이 없다 → G-1 |
| `meta.companions` | (§3.5 가 요구, §3.4 스키마엔 없음) | `{patterns: [12], counts: {동반어: {o, x}}}` | 추가 — 설계 §3.5 의 "갱신 근거 기록" 구현 |
| `expressions[]` 12 키 | keyword, expression, tier, n, k, precision, lower, upper, kappa, candidate, disagreements, adjudicated | 12 키 모두 | 22행, 후보 13 |
| `expressions[].unknown` | — | `?` 로 빠진 수 | 추가 (`CommittedArtifactsTests` 가 `n + unknown` 합 = 키 항목 수 검증) |
| `expressions[].conditional` | — | `{n, k, precision, kept_of_1, dropped_x}` | 추가 — 조건부 규칙 근거 |
| `overall` | `{n, precision, kappa}` | + `k`, `disagreements`, `adjudicated` | 추가 |
| NaN | 없음 | 없음(κ 미정의 → `null`) | |

### 4.2 `expression_review_impact.json` (설계 §3.5)

| 키 | 설계 | 실제 | 비고 |
|---|---|---|---|
| `meta.corpus_sha256` / `meta.versions` | ○ | `3be0908a…` / `["v1","v1fix","v2"]` | |
| `meta.documents` / `meta.keywords` / `meta.v2_overrides` | — | 95 / 30 / 6항목(held·conditional) | 추가 |
| `totals` | `{v: {NCS, 교과서}}` | v1 12,506/1,293 · v1fix 12,310/1,272 · v2 11,517/1,207 | v2 = `semantic_summary.json` |
| `grades` | `{v: {NCS: {1,2,3}, 교과서}}` | ○ | 등급3 비율은 유도값(§3.5 "명시" 는 analysis §6·CLI) |
| `keywords[]` | `{name, v1, v1fix, v2}` | 30행 | |
| `expressions[]` | `{keyword, expression, v1, v1fix, v2}` | ○ | |
| `excluded_by_fix` | `{PSM_substring, 안전성, 안전_마진류}` | `{NCS: {PSM_substring 6, held_inside 190}, 교과서: {4, 17}}` | 말뭉치 분리는 설계 초과; **`안전성` / `안전_마진류` 미분리** → G-4 |
| `excluded_by_v2` | — | `{NCS: {held 551, no_companion 242}, 교과서: {24, 41}}` | 추가 — `test_impact_canonical_column_equals_canonical_summary` 가 합 = v1fix − v2 검증 |

### 4.3 키 · 시트 · 재정 파일

| 파일 | 설계 | 실제 |
|---|---|---|
| `expression_review_key.json` | `{sample_digest, seed, targets, items[id,keyword,expression,corpus,path,line,text_sha256]}` | 동일 + `per_expression: 30`; 618 항목, 본문 없음 |
| `data/expression_review_sheet.json` (비추적) | `{sample_digest, coder_prompt, items[id,keyword,expression,text]}` | 동일; `/data/` 로 gitignore |
| `expression_review_adj.json` | `{sample_digest, labels, note}` | 동일 + `adjudicator`, `date`; 17건 (1×9, 2×6, ?×2) |

---

## 5. 설계와 다르게 구현된 점 — 결정 기록(§6) 대조

| # | 항목 | 설계 | 구현 | 근거 | 판단 |
|---|---|---|---|---|:-:|
| 1 | `DEFAULT_DICTIONARY` | `"v1fix"` (§3.1 원문) | `"v2"` | §3.1 각주 "결정 3 이후 v2", §6 결정 3 (연구책임자 2026-09-14) | 정당 — 일치 |
| 2 | 표본 사전 | v1fix (§3.2) | `SAMPLE_DICTIONARY = "v1fix"` — 정본이 v2 가 된 뒤에도 유지, 키 digest 재현 | §6 결정 3 "표본은 `SAMPLE_DICTIONARY = "v1fix"` 유지" | 정당 — 일치 |
| 3 | 조건부를 정확 키워드 `PSM` 에 적용 | §3.5 예시는 확장 표현만 | `build_default_rules` 가 `(keyword, keyword)` override 를 정확 규칙에 적용; `test_v2_exact_psm_counts_only_with_companion` | §6 결정 2 "조건부 … `PSM`(정확 규칙)" | 정당 — 일치 |
| 4 | `_V2_OVERRIDES` 의 held | `{"decision": "held"}` | `replace(candidate, decision="held")` — 후보 판정 교체, 규칙 목록에서 빠짐, `candidates.held` 19 → 21 | 설계 형식 그대로 | 일치 |
| 5 | (b) 보류 표현 제외 | `exclusions["안전"]` 에 패턴 추가 | 별도 필드 `held_patterns` + 별도 사유 | 설계가 요구한 "사유 구분 계수" 를 만족하려면 `exclude_patterns` 와 분리해야 함 | 일치 (구현 방식) |
| 6 | 보류 표현 probe | `scan_document(probe_rules=…)` | `collect_records` 가 probe 규칙을 따로 스캔 | 기능 동일, `scan_document` 시그니처 불변 | 일치 (위치) |
| 7 | 동반어 목록 귀납 갱신 | 갱신 + 근거 기록 | 근거 기록(`meta.companions`), 목록은 초기 12개 유지 | X 편향 동반어 없음, 미출현 3개 무해 — `expression-review.analysis.md` §4·§6 | 정당 — 일치 |
| 8 | 영향표 정본 열 테스트 | "v1fix 열 = 정본" | `DEFAULT_DICTIONARY`(v2) 열 = 정본 | §6 결정 3 | 정당 — 일치. 단 `expression-review.analysis.md` §6 본문이 옛 이름 `test_impact_v1fix_column_equals_canonical_summary` 와 "v1fix 열은 정본과 같다" 를 인용 → G-6 |
| 9 | `ALPHA`·κ 재사용 | `score_coding.ALPHA`, `score_coding.kappa` | 재정의 (값 동일; κ 는 빈 입력·pe=1 에서 `None`) | NaN 없음 요구를 위한 선택이나, 재사용 명시를 어김 | 부분 → G-3 |
| 10 | `parse_grade` 와 `3` | `3` → `errors` | `3` → `grades` (실제 발생 0건); 채점 시 `_norm` 거부 | 결정 없음 | 부분 → G-2 |
| 11 | `scores.meta.adopted` | 채택 결정을 기록 | 항상 `null` | 결정 3 은 코드 주석·`EXPECTED`·설계 §6 에만 | 부분 → G-1 |
| 12 | `expression_review.py` 의존성 | "stdlib + openpyxl 불필요" (§2) | `openpyxl` 필요 | 설계 문구 오류 | 부분 → G-5 |

---

## 6. Gap 목록

### 설계 항목 갭

| ID | 심각도 | 갭 | 조치 제안 |
|---|:-:|---|---|
| G-1 | Medium | `expression_review_scores.json meta.adopted` 가 결정 3(v2 채택) 뒤에도 `null`. 설계 §1 원칙 4 "채택 결정은 `scores.json.meta.adopted`" 미이행 — 채택 사실은 `DEFAULT_DICTIONARY` 주석·`EXPECTED["dictionary"]`·설계 §6 에만 있다 | (a) `score --adopted v2 --adopted-note "결정 3 2026-09-14"` 옵션을 추가해 재실행하고 `CommittedArtifactsTests` 에 `scores.meta.adopted == SKR.DEFAULT_DICTIONARY` 단언, 또는 (b) 설계 §1 원칙 4 를 "채택 결정은 `EXPECTED["dictionary"]` + 설계 §6" 로 고치고 `adopted` 키를 스키마에서 뺀다. 연구책임자 결정 파일 원칙(§1)에 맞는 쪽은 (a) |
| G-2 | Low | 설계 §3.3 "`3` 이 오면 `errors`" 와 달리 `code_pages.parse_grade` 는 `3` 을 라벨로 저장한다. 실제 A·B 라벨엔 `3` 이 없고 `_norm` 이 채점을 멈추므로 결과엔 영향 없음 | 설계 §3.3 문구를 "`3` 은 `_norm` 이 채점 시 거부" 로 고치거나, `code_pages.py` 에 `--labels 12?` 옵션을 두어 시트별 허용 라벨을 지정 |
| G-3 | Low | `expression_review.ALPHA`·`kappa` 가 `score_coding` 을 재사용하지 않고 재정의됨(값·수식 동일). "95 %" 의 단일 출처 원칙(`score_coding.ALPHA`) 이 둘로 갈림 | `from score_coding import ALPHA`; `kappa` 는 `score_coding.kappa(a, b, cats=(1, 2))` 를 감싸 NaN → `None` 만 변환 |
| G-4 | Low | `impact.excluded_by_fix` 가 `안전성` / `안전_마진류` 를 `held_inside` 로 합쳐 계획 §4 성공 기준("`안전성` ≈ 140 + `안전 마진…` ≈ 32") 을 개별로 확인할 수 없다(합 207 = NCS 190 + 교과서 17) | `MatchRecord.matched_text` 를 `_HELD_INSIDE` 패턴별로 다시 매칭해 `{PSM_substring, 안전성, 안전_마진류}` 세 키로 나눔(말뭉치 분리는 유지). 테스트 `test_impact_has_three_versions_and_counts_fix_exclusions` 갱신 |
| G-5 | Low | 설계 §2 "`expression_review.py` (신설, stdlib + openpyxl 불필요)" 는 사실과 다름 — `semantic_keyword_recount` 를 import 하는 순간 openpyxl 이 필요하고 `impact` 는 워크북 등급을 읽는다 | 설계 §2 문구 수정("openpyxl 필요 — `semantic_keyword_recount` 의존"). 코드 변경 불필요 |

### 설계 항목 외 — 문서 정합

| ID | 심각도 | 갭 | 조치 제안 |
|---|:-:|---|---|
| G-6 | Low | `docs/03-analysis/expression-review.analysis.md` §6 이 "`v1fix` 열은 정본 `semantic_summary.json` 과 같다, `test_impact_v1fix_column_equals_canonical_summary`" 를 인용 — 결정 3 뒤 실제는 v2 열, 테스트명은 `test_impact_canonical_column_equals_canonical_summary` | 해당 문장을 "정본(`DEFAULT_DICTIONARY`, v2) 열은 … `test_impact_canonical_column_equals_canonical_summary`" 로 갱신 (같은 문서 §6 끝 결정 3 단락과 정합) |
| G-7 | Low | README "테스트" 절(120행)이 `test_semantic_keyword_recount.py` 만 언급 — `test_expression_review.py`(15 tests) 는 CI 가 돌리지만 README 엔 없음 | 120행에 `test_expression_review` 한 줄 추가 (`python3 -m unittest test_semantic_keyword_recount test_expression_review`) |
| G-8 | Info | `docs/.pdca-status.json` 의 `semantic-expression-review` phase 가 `"do"` | Check 완료 후 `check`·matchRate 96 갱신(`/pdca` 가 처리) |

---

## 7. 계획 성공 기준 체크리스트 (plan §4)

| # | 기준 | 실측 | 판정 |
|---|---|---|:-:|
| 1 | 교과서 `PSM` 정확 매칭 13 → 0 (`EAPSM`·`Htpsm` 문맥), NCS `MSDS` 내부 문자열 0 | 내부 문자열: `excluded_by_fix.PSM_substring` NCS 6 · 교과서 4, v1fix 이후 0건 (`test_v1fix_english_exact_keywords_need_word_boundary`). 교과서 `PSM` 은 13 → 9(v1fix, 독립 토큰 잔여) → 1(v2 조건부) | ✅ (내부 문자열 0; 잔여 독립 토큰은 결정 2 조건부로 처리) |
| 2 | `안전` 정확 규칙 제외에 `안전성` ≈ 140 + `안전 마진…` ≈ 32 가 잡히고 총계에서 빠짐 | `held_inside` NCS 190 + 교과서 17 = 207 (`안전` NCS 4,119 → 3,929, 교과서 380 → 363); 개별 분리는 없음(G-4) | ✅ (합계 기준) |
| 3 | 표본 키 digest 고정, 시트에 "계층/근거/등급" 0회, 시트가 `git status` 에 없음 | digest `9713a337b4d94bac`(키·adj·scores 일치); `test_sheet_has_no_anchoring_fields_and_key_has_no_text`; `/data/` gitignore, `data/expression_review_sheet.{json,md}` 존재·비추적 | ✅ |
| 4 | 두 코더 라벨 완료(`?` 허용), 불일치 목록 → 연구책임자 재정 라벨 존재 | A 381/227/10, B 384/229/5, 오류 0; 불일치 17 → `expression_review_adj.json` 17건 | ✅ |
| 5 | 표현별 정밀도 표(하한·상한·n·κ) 22행, 하한 < 0.8 목록 자동 산출 | `scores.expressions` 22행, `hold_or_conditional` 13 · `keep` 9 | ✅ |
| 6 | `--dictionary v2` 를 기본 경로로 돌리면 거부, 변형 경로면 영향표 생성, v1 정본 파일 바이트 불변 | 결정 3 으로 역할이 뒤집힘: `v1`·`v1fix` 가 변형 → 추적 경로 거부(`test_non_default_dictionary_refuses_tracked_outputs_and_records_mismatch`); v1 은 `V1_RULE_CONTENT_SHA256` 으로 규칙 내용 고정, v1 수치는 `impact.json` 계보 열 | ✅ (재해석) |
| 7 | 영향표에 v1 / v1+결함 / v2 세 열, 등급3 비율 변화 명시 | `impact.json` 세 열; 비율 20.8 → 20.9 → 21.9 %(NCS), 9.3 → 9.2 → 9.5 %(교과서) — `expression-review.analysis.md` §6 | ✅ |
| 8 | 연구책임자 결정 기록: 결함 2건 정본 반영, v2 채택 | 설계 §6 결정 1·2·3 + 재정 17건; `scores.meta.adopted` 는 null(G-1) | ✅ (기록 위치만 갭) |
| 9 | 기존 하니스 전부 통과(64/390/24/32/38 + unittest) | 64/64 · 390/390 · unittest 77 OK 확인(§8); 24/32/38 은 이 Check 에서 재실행하지 않음(변경 파일과 무관, CI 가 돌림) | ✅ |

---

## 8. 하니스 결과 (인용)

이 세션(코디네이터)에서 실행한 결과를 인용한다. 명령은 `CLAUDE.md` Testing 절 그대로.

```
python3.13 -m unittest test_semantic_keyword_recount test_expression_review   → Ran 77 tests … OK   (test_semantic_keyword_recount 62 + test_expression_review 15)
node   outputs/test-dashboard-data.js                                        → 64/64 PASS   (S1~S9: 정본 v2 11,517/1,207 ↔ data.js ↔ 대시보드·README·CLAUDE.md, previous_basis ↔ reseg)
python3 outputs/test-recount-grades.py                                        → 390/390 PASS (R17 인용 단언 수 포함)
```

`DictionaryVersionTests` 9건과 `test_expression_review.py` 15건(Sample 5 · Score 6 · Impact 2 · CommittedArtifacts 2)이 모두 포함된다. CI(`.github/workflows/test.yml`)는 openpyxl 설치 뒤 두 unittest 모듈을 마지막 단계로 돌린다.

---

## 9. 판정과 다음 단계

- **Match Rate 96.0 % (≥ 90 %)** — 설계와 구현이 잘 맞는다. 불일치 0, 부분 5 는 전부 결정 없이 달라진 소소한 것이고, 발표 수치(대시보드·README·CLAUDE.md)는 하니스가 정본 v2 와 대조해 통과했다.
- 닫기 전 처리 권고: **G-1**(`meta.adopted` — 코드 (a) 또는 설계 (b) 중 택일, 연구책임자 결정 파일 원칙상 (a)), G-6·G-7 문서 한 줄씩. G-2~G-5 는 Report 이후 이월해도 된다.
- 다음: `/pdca report semantic-expression-review` → 보고서에 결정 1·2·3 과 영향표(12,506 → 12,310 → 11,517)를 싣고, `TODOS.md` 이월 (a) `가연성` 60건 2차 패스, (b) 정확 키워드 문맥 정밀도 대조, (c) 동반어 근거 축적을 그대로 둔다.

## 10. Act-1 — 갭 처리 (2026-09-14)

| ID | 처리 | 근거 |
|---|---|---|
| G-1 | **닫힘 (a)** — `score(..., adopted=)` + CLI `--adopted {v1,v1fix,v2}`(`DICTIONARY_VERSIONS` 밖은 `ValueError`), `score --adopted v2` 재실행 → `scores.meta.adopted = "v2"`. 테스트 `test_score_flags_candidates_below_floor_and_has_no_nan`(기본 `None`, 지정 시 값, 잘못된 값 거부), `test_scores_and_adj_bind_to_committed_key`(`adopted == DEFAULT_DICTIONARY`) | 연구책임자 결정 파일 원칙(설계 §1 원칙 4) |
| G-2 | **닫힘 (설계 문구)** — §3.3 을 "`3` 은 `_norm` 이 채점 시 거부" 로 수정 | 코드 변경 불필요 |
| G-3 | **닫힘 (부분)** — `ALPHA = score_coding.ALPHA` 로 단일 출처화. `kappa` 는 `expression_review` 의 정의(κ 미정의 → `None`)를 유지 — `score_coding.kappa` 는 NaN 을 돌려주고 JSON 이 NaN 을 못 담으므로 감싸는 것과 재정의의 차이가 없다 | "95 %" 단일 출처 |
| G-4 | **닫힘** — `excluded_by_fix` 에 `안전성` / `안전_마진류` 분리 계수 추가(제외 레코드 문맥에 `_HELD_INSIDE` 패턴을 순서대로 적용): NCS 146 / 44, 교과서 14 / 3 (합 = `held_inside` 190 / 17). 테스트 `test_impact_splits_held_inside_by_pattern` | 계획 성공 기준 개별 확인 |
| G-5 | **닫힘 (설계 문구)** — §2 "openpyxl 필요 — `semantic_keyword_recount` 의존" | — |
| G-6 | **닫힘** — `expression-review.analysis.md` §6 문장·테스트명 갱신, §8 재현 명령에 `--adopted v2` | — |
| G-7 | **닫힘** — README 테스트 절에 `test_expression_review.py` 한 줄 | — |
| G-8 | **닫힘** — `.pdca-status.json` phase `check`, matchRate 96 | — |

Act-1 뒤 하니스: `python3.13 -m unittest test_semantic_keyword_recount test_expression_review` → 78 OK (62 + 16), `node outputs/test-dashboard-data.js` 64/64, `python3 outputs/test-recount-grades.py` 390/390.

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-14 | 초안 — 설계 63 항목 대조, 스키마 대조, 갭 8건, 성공 기준 9항 | Claude (Opus 5, bkit gap-detector) |
| 1.1 | 2026-09-14 | Act-1 — G-1~G-8 처리 기록(§10) | Claude (Opus 5) |
