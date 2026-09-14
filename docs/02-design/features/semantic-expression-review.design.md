# 의미 표현 사전 도메인 점검 설계

> **Feature**: semantic-expression-review
> **Plan**: [semantic-expression-review.plan.md](../../01-plan/features/semantic-expression-review.plan.md) (Approved 2026-09-14 — 결함 2건 정본 반영 / 코더 2계열 / 하한 0.8)
> **Author**: Claude (Opus 5)
> **Date**: 2026-09-14
> **Status**: Draft
> **Level**: Starter

---

## 1. 설계 목표

세 갈래를 한 파이프라인으로 잇는다: **결함 수정(정본 반영) → 표본·판정·정밀도 → 사전 변형·영향표**. 원칙:

1. **사전은 버전이 있다.** `v1`(2026-09-09 원본)·`v1fix`(결함 2건 수정 = 승인된 새 정본)·`v2`(점검 반영 변형). 정본이 아닌 버전은 추적 산출물 경로를 거부한다(`resegment.py --marker-correct` 규약).
2. **판정 인프라는 재사용한다.** 시트·키·digest는 `make_coding_sheet.py` 규약, 호출은 `code_pages.py` 그대로(라벨 `1`/`2`/`?`), 구간·κ는 `score_coding.py`의 `ALPHA`·`kappa`.
3. **본문은 비추적, 수치·라벨·키만 추적.** 시트는 `data/`(gitignore) 아래, 키·라벨·점수·영향표는 `docs/03-analysis/data/`.
4. **연구책임자 결정은 파일로 남긴다.** 재정 라벨 `expression_review_adj.json`, 채택 결정은 `expression_review_scores.json.meta.adopted`.

---

## 2. 아키텍처

```
semantic_keyword_recount.py                       expression_review.py (신설, stdlib + openpyxl 불필요)
  default_candidate_decisions(version)              ├─ sample   : 정본 스캔(v1fix) → 대상 표현 22개 × 30건 층화 표본
  build_default_rules(keywords, version)            │            → data/expression_review_sheet.{json,md} (본문, gitignore)
  scan_document(require_patterns 지원)              │            → docs/03-analysis/data/expression_review_key.json (추적)
  run_census(--dictionary v1|v1fix|v2)              ├─ (코딩)   : code_pages.py --sheet … --coder A --backend claude-cli
        │                                            │             code_pages.py --sheet … --coder B --provider-env …  (OpenAI 계열)
        │                                            │            → docs/03-analysis/data/expression_review_{A,B}.json
        │                                            ├─ score    : A·B (+ adj) → 표현별 정밀도·CP 95% 구간·κ, 하한<0.8 후보
        │                                            │            → docs/03-analysis/data/expression_review_scores.json
        ▼                                            └─ impact   : v1 / v1fix / v2 를 메모리에서 집계 → 총계·키워드·등급 영향표
  정본(v1fix) 산출물 7종 (재고정된 EXPECTED)                       → docs/03-analysis/data/expression_review_impact.json
                                                    docs/03-analysis/expression-review.analysis.md (연구 결과, 표는 위 JSON 인용)
```

---

## 3. 상세 설계

### 3.1 사전 버전 — FR-01·02·06·09 (`semantic_keyword_recount.py`)

```python
DICTIONARY_VERSIONS = ("v1", "v1fix", "v2")
DEFAULT_DICTIONARY = "v1fix"          # 연구책임자 결정 2026-09-14: 결함 2건은 정본에 반영 → 결정 3 이후 "v2" (§6)
```

- `default_candidate_decisions(version=DEFAULT_DICTIONARY)` — `v1`·`v1fix`는 같은 후보 목록(결함은 정확 규칙 쪽), `v2`는 §3.5의 변경을 덧씌운다(`_V2_OVERRIDES`: 표현 → `decision`/`require_patterns`).
- `build_default_rules(keywords, version=DEFAULT_DICTIONARY)`:
  - **(a) 영문 정확 키워드 단어 경계** (`v1fix`, `v2`): 키워드가 ASCII만이면 `pattern=_ascii_term(keyword)`. 대상 `PSM`·`MSDS`. `re.IGNORECASE`는 그대로.
  - **(b) 보류 표현의 정확 규칙 내 계수 차단** (`v1fix`, `v2`): `exclusions["안전"]` 에 `r"안전성"`, `r"안전\s*(?:마진|여유|재고|율|계수)"` 추가. 제외 스팬과 겹치는 `안전` 매칭은 `decision="excluded"`, `reason` 을 `"보류 표현 내부"` 로 구분(기존 "동음이의 또는 비대상 문맥 제외"와 별도 계수 — 요약 시트 `동음이의 제외` 열에는 합산).
- `ExpressionRule.require_patterns: tuple[str, ...] = ()` 신설 — `scan_document` 가 규칙 매칭 뒤 **같은 줄 또는 앞뒤 1줄**(`block.lines[i-1:i+2]`, 페이지 블록 경계 안)에 하나라도 없으면 `decision="excluded"`, `reason="안전 문맥 동반어 없음"`. `v1`·`v1fix` 에서는 빈 튜플이라 동작 불변.
- `rule_sha256` 은 `asdict(rule)` 이므로 `require_patterns` 필드 추가만으로 바뀐다 → **v1fix 정본 재고정은 필드 추가와 결함 수정을 한 번에** 한다(두 번 고정하지 않는다). 영향표의 `v1` 열은 새 필드가 있어도 값이 같으므로 `v1` 규칙 목록의 내용 지문(`pattern`·`exclude_patterns`·`require_patterns`)으로 "v1 = 2026-09-09 사전과 동일"을 테스트로 보인다.
- `run_census(..., dictionary=DEFAULT_DICTIONARY)` / CLI `--dictionary`: 정본이 아닌 버전이면 `xlsx_out`·`report_out`·`dashboard_data_out`·`summary_out`·`analysis_dir` 가 저장소 `docs/` 또는 `data/semantic_keyword_recount_*.xlsx` 기본 이름을 가리킬 때 **거부**(`ValueError`), `EXPECTED` 불일치는 `meta.run.expected_mismatch` 에 기록만(`force` 없이도 쓴다, `meta.run.dictionary` 에 버전).
- `summary_metrics`·`EXPECTED` 에 `"dictionary": "v1fix"` 키 추가 — 정본 버전이 바뀌면 가드가 잡는다.

### 3.2 표본 — FR-03 (`expression_review.py sample`)

- 입력: 정본 코퍼스(`--ncs-root data_source/markdown/ncs --school-root …`), 사전 `v1fix`, 대상 표현 목록.
- 대상 표현 `REVIEW_TARGETS` (코드 상수, 22개): 비정확 표현 중 정본 출현 ≥ 50 인 18개(계획 §1.3) + `PSM`(정확, 단어 경계 적용 후 남는 것) + `combustible` + 보류 2개(`발화성`, `자외선` — 보류 표현은 **매칭만 시키고 계수하지 않는 스캔**으로 문맥을 뽑는다: `scan_document` 에 `probe_rules` 인자, 결과는 표본 전용). 상수는 테스트가 정본 xlsx 없이도 검증하도록 `(keyword, expression)` 튜플만 담는다.
- 추출: 표현별 `included` 레코드(보류는 probe 레코드)를 `(corpus, relative_path, line)` 로 정렬 → `random.Random(SEED).sample`, SEED = 20260914. 30건 미만이면 전수. 층화: NCS/교과서 비례(`round(30 * n_ncs / n)` 씩, 최소 1).
- 시트 항목: `{"id": "E001", "keyword", "expression", "text": <앞줄 + 매칭 줄 + 뒷줄, 매칭 표현을 «…» 로 표시>}` — **계층·근거·판정·페이지 등급 없음**. `coder_prompt()` 는 시트 JSON 안에만 있고 질문은 하나:

  > 각 항목은 반도체 교재 본문 세 줄이며 «…» 안이 판정 대상 표현이다. 이 문맥에서 그 표현이 **노동자의 안전·보건(사람의 위해·보호·건강)** 을 뜻하면 `1`, 제품·공정·품질·계측·오염관리 등 **사람 안전이 아닌** 뜻이면 `2`, 판단할 수 없으면 `?` 만 답한다.

- 키(추적): `{"sample_digest", "seed", "targets", "items": [{"id","keyword","expression","corpus","path"(public_path),"line","text_sha256"}]}`. 시트 `sample_digest` = 키 items 의 정규화 JSON sha256 앞 16자(`make_coding_sheet.sample_digest` 와 같은 방식).
- 시트 `.md` 는 사람이 볼 사본(같은 내용). 둘 다 `data/` 아래라 gitignore.
- `--force` 없이는 기존 키를 덮어쓰지 않는다(키가 라벨과 표본을 묶는 유일한 끈 — `make_coding_sheet.py` 규약).

### 3.3 판정 — FR-04

- 코더 A: `python3 code_pages.py --sheet data/expression_review_sheet.json --coder A --backend claude-cli --out docs/03-analysis/data/expression_review_A.json`
- 코더 B: `python3 code_pages.py --sheet … --coder B --provider-env ~/.config/auditagent/.env --out docs/03-analysis/data/expression_review_B.json` (OpenAI 계열; `family_guard` 로 두 코더가 다른 벤더인지 확인).
- 라벨 파싱은 `code_pages.parse_grade` 그대로(`1`/`2`/`?`; `3` 이 오면 `errors`). 산출물은 라벨·모델·프롬프트 sha256만(본문 없음) — 기존 규약.
- 불일치 목록: `expression_review.py score --list-disagreements` 가 `id·keyword·expression·A·B` 를 표로 출력(본문은 시트에서 id 로 찾는다). 연구책임자 재정은 `docs/03-analysis/data/expression_review_adj.json`: `{"sample_digest", "labels": {"E017": 1, …}, "note"}` — 손으로 쓰는 파일, 스키마는 `score` 가 검증(digest 일치, 라벨 ∈ {1,2,?}, id 가 키에 있음).

### 3.4 정밀도 — FR-05 (`expression_review.py score`)

- 최종 라벨: A == B → 그 값; A ≠ B → `adj` 에 있으면 그 값, 없으면 `?`. `?` 는 분자·분모에서 뺀다(`score_coding` 규약).
- 표현별 `n`(유효 라벨 수), `k`(1의 수), 정밀도 `k/n`, **Clopper-Pearson 정확 이항 구간**(`ALPHA` = `score_coding.ALPHA`):
  ```python
  def precision_interval(k, n, alpha=ALPHA):
      # stdlib 만: 이항 CDF 를 math.comb 로 계산하고 p 를 이분 탐색
      lo = 0.0 if k == 0 else bisect(lambda p: binom_sf(k - 1, n, p) - alpha / 2)
      hi = 1.0 if k == n else bisect(lambda p: binom_cdf(k, n, p) - alpha / 2)
  ```
- κ: `score_coding.kappa(a, b, cats=(1, 2))` (`?` 제외), 전체와 표현별.
- 판정: `lower < 0.8` → `"candidate": "hold_or_conditional"`, 아니면 `"keep"`. 0.8 은 `PRECISION_FLOOR` 상수 하나.
- 출력 `expression_review_scores.json`: `{"meta": {"sample_digest", "coders": {A: model, B: model}, "family_warning", "alpha", "floor", "adopted": null}, "expressions": [{"keyword","expression","tier","n","k","precision","lower","upper","kappa","candidate","disagreements","adjudicated"}], "overall": {"n","precision","kappa"}}`. NaN 없음.

### 3.5 사전 v2 — FR-06·07

- `_V2_OVERRIDES` 는 §3.4 결과에서 **손으로** 옮긴다(자동 반영 아님 — 연구책임자가 표를 보고 정한다). 형식:
  ```python
  _V2_OVERRIDES = {
      ("보호구", "방진복"): {"require_patterns": SAFETY_COMPANIONS},   # 조건부
      ("방사선", "X선"):   {"require_patterns": SAFETY_COMPANIONS},
      ("인화", "combustible"): {"decision": "held"},                    # 보류 전환
  }
  SAFETY_COMPANIONS = (r"착용", r"보호", r"노출", r"피폭", r"화상", r"부상", r"위험", r"유해", r"안전", r"보건", r"재해", r"사고")
  ```
  초기 동반어 목록은 위 12개(가설). 판정 O 문맥에서 빈출하는 동반어로 **귀납해 갱신**하고, 갱신 근거(각 동반어의 O 문맥 출현 수 / X 문맥 출현 수)를 `scores.json.meta.companions` 에 기록한다.
- `impact`: 코퍼스를 한 번 읽고 세 버전을 메모리에서 집계(`aggregate_matches` + `assign_match_grades`, 쓰기 없음). 출력 `expression_review_impact.json`:
  ```
  {"meta": {"corpus_sha256", "versions": ["v1","v1fix","v2"]},
   "totals": {v: {"NCS": …, "교과서": …}}, "grades": {v: {"NCS": {1,2,3}, …}},
   "keywords": [{"name", "v1": {"NCS","교과서"}, "v1fix": …, "v2": …}],
   "expressions": [{"keyword","expression","v1","v1fix","v2"}],
   "excluded_by_fix": {"PSM_substring": n, "안전성": n, "안전_마진류": n}}
  ```
  등급3 비율(확정 분모)은 세 버전 각각 명시. `v1fix` 열은 정본 `semantic_summary.json` 과 같아야 한다(테스트로 대조).

### 3.6 정본 재고정 — FR-10 (첫 Act, 결정 1 반영)

순서: (1) §3.1 구현 + 테스트 → (2) `--dictionary v1fix`(기본) 로 정본 실행 `--force` → 측정값으로 `EXPECTED` 재고정(`dictionary` 키 포함) → 가드 실행 통과 → (3) README·CLAUDE.md·`index.html` 템플릿·이전 report 브리지 표의 인용 수치 갱신(하니스 S5·S7·S8 이 잡는다) → (4) `semantic-occurrence-grades.report.md` 등에 "v1fix 재고정(2026-09-xx): 결함 2건 반영, 12,506 → N" 한 줄. **v2 채택은 별도 결정** — 채택되면 같은 절차를 `DEFAULT_DICTIONARY = "v2"` 로 반복.

### 3.7 보류 정책 명문화 — FR-08

`docs/superpowers/specs/2026-09-08-semantic-keyword-recount-design.md` "포함·제외·보류 기준" 에 절 추가: (1) 영문 일반어(`safety`·`health`·`risk`·`chemical`·`dust`·`vibration`·`fall`·`leakage`)는 한국어 교재에서 영문 일반어가 제목·영문 병기에 쓰여 문맥 판정이 불안정하므로 보류; (2) 계측·물성 문맥어(`자외선`·`X선`·`방사능`)는 조건부 또는 보류 — 같은 기준을 `X선` 에도 적용(정밀도 결과에 따라); (3) 오염관리 장비어(`방진복`·`방진화`·`장갑`)는 사람 보호 문맥 동반어가 있을 때만; (4) `가연성`/`발화성`/`인화성` 은 같은 계층 기준으로 재판정(정밀도 결과).

### 3.8 문서·데이터 계보

- `docs/03-analysis/data/README.md` 계보표에 4개 파일(`expression_review_key/A/B/adj/scores/impact`) 추가: 키·라벨·점수·영향표는 연구용, **미발표**; 정본은 여전히 `semantic_summary.json`.
- `CLAUDE.md` 그룹 4에 `expression_review.py` 항목, 사전 버전 규약, `DEFAULT_DICTIONARY`.
- `.gitignore`: `data/` 전체가 이미 비추적 — 시트는 자동으로 제외. 키·라벨은 `docs/03-analysis/data/` 라 추적(`coding_key.json` 과 같은 이유로 와일드카드 금지).

---

## 4. 테스트 설계

| FR | 테스트 (`T` = `test_semantic_keyword_recount.py`, `E` = 신설 `test_expression_review.py`, 둘 다 unittest·fixture) |
|---|---|
| FR-01 | `T v1fix_english_exact_keywords_need_word_boundary` (`EAPSM`·`Htpsm` 0건, `PSM` 단독 1건); `T v1_keeps_substring_behaviour` |
| FR-02 | `T v1fix_excludes_held_expressions_inside_안전` (`안전성`·`안전 마진` → excluded, reason "보류 표현 내부"; `안전 보건` 기존 제외 유지) |
| FR-03 | `E sample_is_deterministic_for_seed`, `E sample_stratifies_by_corpus_and_takes_all_below_30`, `E sheet_has_no_tier_reason_grade_strings`, `E key_has_no_text_and_digest_matches_sheet`, `E sample_refuses_to_overwrite_key_without_force`, `E held_targets_are_probed_not_counted` |
| FR-04 | `E adj_file_is_validated` (digest 불일치·잘못된 라벨·모르는 id 거부); code_pages 는 기존 R15 가 덮는다 |
| FR-05 | `E precision_interval_matches_known_values` (k=0/n=30 → [0, 0.116], k=30/n=30 → [0.884, 1], k=27/n=30 → 하한 ≈ 0.735), `E final_label_rules` (일치/불일치+adj/불일치 → ?), `E floor_flags_candidates`, `E scores_json_has_no_nan` |
| FR-06 | `T require_patterns_exclude_without_companion_in_window` (같은 줄·±1줄·블록 경계), `T non_default_dictionary_refuses_tracked_outputs`, `T non_default_dictionary_records_mismatch_without_force` |
| FR-07 | `E impact_v1fix_column_equals_canonical_summary` (fixture 로 세 버전 집계 → 구조·합), `E impact_counts_excluded_by_fix` |
| FR-09 | `T expected_pins_dictionary_version`, `T v1_rule_content_digest_is_unchanged` (2026-09-09 규칙 지문을 상수로 고정 — `pattern`·`exclude_patterns` 만의 sha) |
| FR-10 | 하니스 S1~S9·R17 (재고정 뒤 인용 수치) |

fixture 원칙: 실제 xlsx·코퍼스 없이 돈다(문서 3~5개, 표현 3개). `code_pages.py` 는 `post=` 가짜로만(기존 규약, 네트워크 호출 없음).

---

## 5. 구현 순서 (Do)

1. `semantic_keyword_recount.py` §3.1 — 버전 인자, 결함 2건, `require_patterns`, `--dictionary` 거부 규칙, `EXPECTED["dictionary"]` (T 테스트 먼저).
2. 정본 재고정(§3.6) — `--force` 측정 → `EXPECTED` 고정 → 가드 통과 → README·CLAUDE.md·정적 화면·이전 report 인용 수치 갱신 → 하니스 전부 통과. **첫 커밋 단위.**
3. `expression_review.py sample` + E 테스트 → 시트·키 생성(정본 코퍼스), 키 커밋.
4. 코더 A(claude-cli)·B(OpenAI) 실행 → 라벨 커밋 → 불일치 목록을 연구책임자에게 → `adj.json`.
5. `score` → `scores.json` + 분석 문서 초안(정밀도 표, κ, 후보 목록).
6. **결정 2(v2 구성)** — 연구책임자가 후보를 보고 보류/조건부 지정 → `_V2_OVERRIDES` 반영 → `impact` → 영향표를 분석 문서에.
7. 보류 정책 명문화(§3.7), 계보 README·CLAUDE.md.
8. **결정 3(v2 채택 여부)** — 채택이면 §3.6 반복. `/pdca analyze` → report.

---

## 6. 결정 기록

| 항목 | 결정 | 근거 |
|---|---|---|
| 결함 2건 정본 반영 | 반영(`v1fix` = 새 정본) | 연구책임자 2026-09-14 |
| 코더 | `claude-cli` + OpenAI 호환 2계열, 불일치만 재정 | 연구책임자 2026-09-14 |
| 정밀도 하한 | 0.8 (CP 95% 하한) | 연구책임자 2026-09-14 |
| 시트 문맥 | 매칭 줄 ± 1줄, 표현 «…» 표시 | 한 줄만으로는 계측/보호 구분이 어려움 |
| 조건부 판정 창 | 같은 줄 ± 1줄, 페이지 블록 안 | 시트 문맥과 동일 창 |
| 사전 버전 이름 | `v1`·`v1fix`·`v2` | 계획의 "v1 / v1+결함 / v2" 열과 대응 |
| SEED | 20260914 | 재현성 |
| 재정 17건 | 제안(문맥 근거) 승인 — 1×9, 2×6, ?×2 | 연구책임자 2026-09-14 (`expression_review_adj.json`) |
| **결정 2** v2 구성 | 계층별 처방 — 뜻이 다른 표현만: 보류 `방진화`·`케미컬`, 조건부 `방진복`·`장갑`·`X선`·`PSM`(정확 규칙). 동의어·`가연성`·`combustible` 유지 | 연구책임자 2026-09-14 (`expression-review.analysis.md` §5·§6) |
| **결정 3** v2 채택 | 채택 — `DEFAULT_DICTIONARY = "v2"`, §3.6 재실행·재고정, 표본은 `SAMPLE_DICTIONARY = "v1fix"` 유지 | 연구책임자 2026-09-14 |

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|---|---|---|---|
| 1.0 | 2026-09-14 | 초안 | Claude (Opus 5) |
