# TODOS

## Add page markers to PDF-to-markdown pipeline
- **Why**: Eliminates the 200-line DP page mapping heuristic. Strategy 1 (`<!-- page: N -->` markers) already handles this perfectly.
- **Context**: User controls the upstream converter. Once all documents have markers, `buildPageMapping` Strategy 2 (TOC matching + DP) becomes dead code and can be removed.
- **Depends on**: Access to the PDF-to-markdown converter codebase (separate repo).

## Add LLM fallback indicator to search results
- **Why**: When `extractSentencesWithLLM` fails and falls back to rule-based, the user sees no indication. Mixed-quality results are a data integrity issue.
- **Context**: Currently the fallback is `console.warn` only. Add a visual badge or file-level indicator showing which analysis method was used.
- **Depends on**: Nothing.

## P2 — Rewrite the safety grading algorithm
- **Why**: The published grades come from a keyword-count rule that (a) matches substrings, so one `산업안전보건법` counts three times and semiconductor homonyms (`진동자`, `파티클 먼지`) count as safety content, and (b) applies a flat threshold regardless of page length, so long pages are promoted. Measured: 등급3 pages average 5,855 chars against 등급1's 1,220 — 4.8x — while their medians differ by only 250.
- **Context**: The old blocker ("no access to the original grading script") turned out not to bind. The script is not needed: the source workbook carries `페이지전체내용` on 100% of rows, so the grade can be recomputed from the page text directly. The rule itself was reverse-engineered from the 4,000+ committed `등급사유` strings and agrees with the **first-seen row's** grade on 99.6% (1,839/1,847) of pages. That is **not** the same as reproducing the published grades, but the reason stated here was wrong and is corrected: `load_pages()` keeps the first row it meets while `recount_grades.py` takes the lowest grade on conflict, and 12 NCS pages are mixed — but **only 1 of those 12 has a first-row grade that differs from the minimum** (`LM1903060425…p.28`, first=2 min=1), measured 2026-09-04. The earlier text blamed all 9 pages of the gap on that divergence, overstating it 9×. The real gap is that the 1,270/469/108 baseline is recount's min-based distribution while `agree`=1,839/1,847 is measured against first-row grades — the table compares two different baselines. Rename and re-measure before citing this number as delta attribution; folding `load_pages()` with `min()` would make the two agree.
  One claim in the earlier version of this entry was wrong: the "total disagrees with its own itemised list" is **not** a scoring bug. 168 of the 171 mismatches list exactly five terms — the reason string truncates to the top five. Only 3 pages (0.16%) are genuinely off, each by one.
- **Status**: `regrade.py` reproduces the rule and fixes the two real defects; per-defect impact is in `docs/03-analysis/data/regrade_impact.json`. **The dashboards still publish the old numbers** — applying the correction is a research-facing decision, not a code one.

  C-2(차감 산술) 수정 후 수치다. F1 열은 무효 라벨에서 나온 **폐기 예정 탐색값**이며 발행 근거가 아니다. 어느 행도 채택되지 않았다.

  | | 등급1 | 등급2 | 등급3 | 등급3 비율 | F1 (폐기 예정) |
  |---|---:|---:|---:|---:|---:|
  | 발표 중 (원본) | 1,270 | 469 | 108 | 5.8% | 0.803 / 0.810 |
  | 재현 (규칙 확인용) | 1,261 | 478 | 108 | 5.8% | — |
  | + 단어 경계 (D1) | 1,274 | 465 | 108 | 5.8% | — |
  | + 길이 정규화 (D2) | 1,371 | 404 | 72 | 3.9% | — |
  | D1+D2 | 1,386 | 389 | 72 | 3.9% | — |
  | D1+D2 + 조건부면제 (D5, 기각) | 1,386 | 384 | 77 | 4.2% | — |
  | D1+D2 + 이산화 (D4 round) | 1,359 | 409 | 79 | 4.3% | — |
  | D1+D2 + 이산화 (D4 floor) | 1,338 | 424 | 85 | 4.6% | — |

  **C-2 수정이 D1을 지웠다.** 이전에 D1 단독이 등급3을 108→101로 줄였던 것은 전부 차감 산술 버그였고, 단어 경계의 실제 효과가 아니었다. 고친 뒤 D1 단독은 baseline과 같은 108이다(변동 쪽수도 43→13). 이전 표의 3.7%는 이 버그 위에 있었다.

  F1은 C-2 수정 전 값이라 위 표에서 뺐다. 재산출하지 않는다 — 라벨 자체가 무효이므로 정밀화가 오염을 가릴 뿐이다.

- **Validation — 이 라벨은 무효다.** 69쪽 이중코딩(분쟁군 39 전수 + 대조군 30)을 했고 두 AI 코더 일치 88.4%, Cohen κ 0.796이 나왔지만, **맹검이 아니었다.** 코더 A는 규칙 작성 당사자였고, `make_coding_sheet.py`의 코더 지시문(당시 `22ce57f:106-108`, `e37cbce` 에서 제거)이 D1의 동음이의 가정(`진동`·`먼지(파티클)`)과 "판단이 갈리면 낮은 등급"이라는 방향성 동점 규칙을 **두 코더 모두에게** 주입했다. 후자는 분쟁군 실험에서 수정본이 이기는 방향이다. 아래 F1 열은 **폐기 예정 탐색값**이며 발행 근거가 아니다. 통합 κ도 층 구성의 산물이다(전체 0.796 > 분쟁군 0.769 > 대조군 0.760).
- **D5 조건부 정규화는 기각.** "안전 전담 페이지는 길고 조치가 많으니 정규화가 부당하게 깎는다"는 가설이었으나, 현 라벨상 등급3인 쪽이 오히려 짧았다(조치어 중앙 5건·길이 중앙 1,268자 대 8건·6,436자). 기각 근거가 무효 라벨에 의존하므로 **재코딩 후 재검정 대상**이다. 다만 기각 방향이라 과적합 이득은 없고, 코드는 재현을 위해 남기되 기본값은 꺼 둔다.
- **D4 이산화 결함은 라벨과 무관하게 실재한다.** 카운트는 정수인데 임계는 연속값이라 `an >= 5*배율` 비교가 사실상 `ceil()` 로 동작한다. 중앙값보다 1자 긴 페이지가 조치어 5건이 아니라 6건을 요구받는다 — 길이 0.1% 차이에 요구치 20% 증가로, 코드를 읽으면 증명되는 산술이다. **결함의 존재는 순환이 아니지만 방식 선택은 순환이다**(위 1번).
- **C-2 차감 산술 오류는 수정 완료** (커밋 `5704c88`). 총계 뺄셈을 구간 매칭으로 바꿨다. 되살아난 3쪽은 두 코더가 모두 등급3이라 한 쪽이었다(3/3) — 라벨을 쓰지 않고 산술만으로 도출한 수정이라 이 일치는 순환이 아닌 방증이다.
- **절단 무결성 — 하위 절단 제거, 상위 절단은 복구 불가로 확정** (2026-09-04). 원본이 엑셀뿐이라 셀 한도 32,767자 절단은 되돌릴 수 없다. Q4 의 답은 "하지 않음"(미이행)이 아니라 **"원본 부재로 불가"**(영구 한계)이며 공개문에 들어가야 한다. 코딩 시트의 6,000자 절단은 제거했다(전문을 나눠 싣는다) — 채점기와 코더가 같은 텍스트를 본다.
  전수 실측: NCS 1,847쪽 중 **16쪽**(행으로는 1,376건), 교과서 362쪽 중 **0쪽**. 등급별로 고르지 않다 — 등급1 0/1,270, 등급2 4/469, **등급3 12/108(11.1%)**. 표본 9항목은 이 16쪽의 부분집합이다.
  **영향 상한이 원본 없이 닫힌다.** 발표 규칙은 임계가 고정이라 등급이 `(sn, an)` 에 단조 비감소이므로 절단쪽 등급은 하한이고, 등급3 12쪽은 이미 최대라 복원해도 변하지 않는다. 움직일 수 있는 것은 등급2 4쪽뿐 → **등급3 108~112쪽(5.8~6.1%)**. 어휘 목록 고정 시에만 성립한다(아래 4번이 깨뜨린다). D1+D2 에서는 정규화가 분자와 분모를 함께 줄여 방향이 확정되지 않는다.
  남은 것: 절단층 라벨의 처리 방식(제외/층화/각주)은 연구 책임자 판단. 계획·설계는 `docs/01-plan/features/truncation-integrity.plan.md`, `docs/02-design/features/truncation-integrity.design.md`.
- **미이행 (외부감사 지적).** ① 등급2↔1 경계 미검증: 재채점이 가장 많이 움직인 쪽이 등급2→1(102쪽)인데 표본에 한 쪽도 없다 → **2026-09-04 재코딩 표본에 경계층 109쪽 전수로 포함**, 라벨 완료: 109쪽 중 Claude 28 / GPT 52 쪽이 등급3이고 Claude 의 28쪽은 전부 GPT 도 3 (`recoding-results.analysis.md` §4.1). ② 산출물에 `git_commit`·`source_sha256`·`generated_at` 없음 — 2026-09-04 `recoding_scores*.json` 에는 `generated_at`·`sample_digest`·`seed` 가 생겼고, `git_commit`·`source_sha256` 은 어느 산출물에도 아직 없다(`summary.json`·`regrade_impact.json`·`coding_key.json` 은 셋 다 없음). (③ `score_coding.py`·`make_coding_sheet.py` 어서션 0건은 해소 — R12k-R12o7·R13n-R13w 로 커버리지가 생겼다.)
- **커밋된 코딩 라벨은 지금 채점기로 다시 돌릴 수 없다** (2026-09-04, 문서화 감사에서 확인). `score_coding.py` 는 `coding_key.json` 에 `sample_digest` 를 요구하는데(커밋 `9773312`), 저장소에 든 키는 그 가드보다 먼저 생성돼 필드가 없다. 실행하면 "구버전 산출물" 로 멈춘다. 가드 자체는 옳다 — 시트를 다시 만들면 항목 번호가 섞여 옛 라벨이 엉뚱한 페이지에 붙는다. 다만 `.gitignore` 주석은 이 세 파일을 "κ 0.796 / 88.4% 의 유일한 원자료" 라고 적고 있으므로, 지금 상태는 **재현 가능한 입력이 아니라 보존용 기록**이다. 어차피 위 Validation 항목대로 라벨이 무효라 재코딩이 필요하니 같이 처리한다. → 2026-09-04 삼종을 `docs/archive/2026-09/coding-v1/` 로 옮겼다(추적 유지). 루트의 `coding_key.json` 은 새 표본의 키다.
- **재코딩 완료, FR-1 충족 (2026-09-04) — `docs/03-analysis/recoding-results.analysis.md`.** 두 어휘 정의의 **합집합**으로 4층 표본 538쪽(분쟁 44 / 합의 85 / 경계 109 / 재현율 300, 지문 `68a4575ffff0def9`)을 뽑아 세 코더가 전수 코딩했다(`code_pages.py`, 각 538/538, 오류 0): C = `claude-opus-5`(Anthropic, `claude -p`), B·A = `gpt-5.6-sol`(OpenAI, 같은 모델 재시행). 주 결과 C·B: **현행 규칙은 정밀도 80~84%, 재현율 13~21%.** 코더 기준 진짜 등급3은 **Claude 408쪽(22%) ~ GPT 689쪽(37%)** — 어느 계열로 봐도 5.8% 의 4~6배. 분쟁군은 두 계열 모두 **현행 지지 과반**(둘 다 현행 59%, 둘 다 수정본 26%). D1+D2 는 정밀도 +8~9pt, 재현율 −4~5pt; 어휘 21종(V)은 두 계열 모두 F1 1위(0.39 / 0.27)이나 어느 변형도 F1 0.4 미만. 계열 간 κ 0.685(같은 모델 재시행 0.914) — 불일치의 64%는 GPT 가 3, Claude 가 2. Claude 의 등급3은 GPT 의 부분집합에 가깝다(반대 방향 3쪽). 사람 코딩 판별점: 두 계열이 합의한 누락 79쪽(재현율층 51 + 경계층 28). 어느 변형도 채택하지 않았다.
- **감사 권고 중 거부한 것 1건.** 대시보드 경고 배너 게시 — 연구 책임자 판단으로 **달지 않기로 결정**. `docs/index.html:179`의 "108쪽(5.8%)"은 경고 없이 공개 상태를 유지한다.
- **Depends on**: A decision on whether to republish, and at which number. 열려 있는 것 넷:
  1. **라벨이 무효라 어느 변형도 채택할 수 없다.** 이산화 방식(`ceil`/`round`/`floor`) 선택은 이 69쪽으로 결정할 수 없다 — 과적합이기도 하고, 애초에 F1 신뢰구간 폭(±0.06~0.08)이 변형 간 차이(0.02~0.04)보다 커서 판별력이 없다. D4 **결함의 존재** 는 라벨과 무관하게 코드로 증명되지만 방식 선택은 신규 표본이 필요하다. → **2026-09-04 538쪽 유효 라벨로 재측정** (`recoding-results.analysis.md` §5): Claude 기준 F1 은 D1+D2 0.266 / D4 round 0.284 / D4 floor 0.297 로 차이가 여전히 작고, 어느 변형도 F1 0.4 미만이다. 결과는 변형 선택이 아니라 규칙이 재현율을 잃는 자리(안전어 ≤5 관문, 조치어 사전)를 가리키며, 채택은 연구 책임자 판단으로 열려 있다.
  2. **재현율은 어느 규칙에서도 측정된 적이 없다.** 표본이 현행의 등급3 108쪽 안에서만 뽑혀서, 등급1·2로 떨어진 1,739쪽에 진짜 등급3이 얼마나 묻혀 있는지 모른다. → **2026-09-04 처음 측정: Claude 기준 20.8% [17.8, 24.4], GPT 기준 13.2% [11.8, 14.9]** (경계층 109쪽 전수 + 재현율층 300쪽, 정확 초기하 구간). 계열이 달라도 규칙은 등급3의 8할 안팎을 놓친다 — `recoding-results.analysis.md` §4·§7.
  3. AI 두 코더의 일치는 사람 이중코딩이 아니다. 사람 코딩 30~40쪽으로만 갈린다. → 재코딩 후 판별점이 구체화됐다: 두 계열(Claude·GPT)이 모두 등급3이라 한 누락 79쪽 — 재현율층 51(현행 등급1 24 / 등급2 27) + 경계층 28(`recoding-results.analysis.md` §4). 여기서 사람이 코더와 갈리면 두 AI 가 함께 관대한 것이고, 같으면 규칙의 안전어 관문(≤5 → 등급1)이 틀린 것이다. GPT 만 3 이라 한 77쪽은 계열 차이의 방향을 본다.
  4. **어휘 누락 탐색 완료 (2026-09-04)** — `docs/03-analysis/vocab-search.analysis.md`. **등급3을 5.8% → 7.0%(108→129쪽) 올린다.** 거의 전부 조치어 효과다(조치어만 +20, 안전어만 +1) — 등급3이 조치어 ≥5를 요구하므로 예측대로였다. 채택 후보 21종(조치 12 / 안전 9), 보류 6종(`접지`·`정전기`·`감지기`·`노출`·`취급`·`인체` — 동음이의), 기각 2종(`LOTO`·`산소결핍`은 본문에 아예 없다). 사전 역설계 자체는 정확했다 — 원본 채점기가 `등급사유`에 이름 붙인 용어는 **0종 누락**이고, 빠진 것은 원본 채점기의 어휘 자체다. **채택 여부는 연구 책임자 판단**이며, 다만 재코딩 표본은 어휘가 확정돼야 뽑을 수 있다(확장 시 분쟁군 36→39, 교집합 31쪽뿐). → **2026-09-04 두 어휘 정의의 합집합으로 표본을 뽑아 어휘 확정 없이 진행했다**(분쟁군 44 = 36 ∪ 39). 라벨 결과 V 어휘 확장은 Claude·GPT 두 계열 모두 F1 1위(0.39 / 0.27)이나 채택은 여전히 열려 있다 — `recoding-results.analysis.md` §5.

- **"5.8%는 상한"이 아니다 — 이제 실측 근거가 있다.** 결함들이 서로 상쇄한다: D2 정규화 **-36쪽**, 셀 한도 절단 **0~-4쪽**(유계), D1 단어 경계 **0**(C-2 수정 후), 그리고 **어휘 누락 +21쪽**. 어느 하나만 고치고 발표하면 방향이 편향된다. 알려진 결함은 **절단과 어휘를 빼면** 과대계상 축(정밀도)이고, 재현율은 2026-09-04 에 처음 측정됐다(Claude 21% / GPT 13%, 두 계열 독립). **절단은 과소계상 축이다** — 텍스트를 지우므로 등급을 내리는 방향으로만 작용하고(발표 규칙 기준), 그 영향은 등급3 +0~4쪽으로 유계다. 4번을 수행하면 비율이 **올라갈** 수 있다. 발행 가능한 진술은 "5.8%는 결함이 확인된 현행 규칙의 출력값이며, 두 계열의 AI 코더 기준 재현율이 13~21%(진짜 등급3 22~37%)라 참값의 상한으로 해석할 수 없다. 사람 코딩은 아직 없다" 까지다.
- **다만 구간은 연역된다.** C-2는 과다 차감이었으므로 수정 시 `sn`·`an`이 단조 증가하고 `grade_page`는 `(sn, an)`에 단조 비감소다 — 등급은 내려갈 수 없다. 실측으로 확인됐다: D1+D2 등급3이 69→72로 올랐고, 새 분쟁군 36쪽은 옛 39쪽의 **부분집합**(새로 생긴 쪽 0)이다. 이 구간은 **어휘 목록을 고정했을 때만** 성립한다(위 4번이 깨뜨린다).
- **Base sensitivity**: 길이 정규화는 `sqrt(len / median)` 이고 형태와 기준값 모두 선택이다. 기준값 1,000~3,000자 범위에서 등급3 비율은 2.9~5.2% 에 걸친다. 발행하는 곳마다 이 폭을 함께 적어야 한다.

## Completed

### Dashboard entrance animation hides the headline for ~0.9s
- **Why**: `.ani` uses `animation-fill-mode: both` with `.1s`/`.2s`/`.3s` stagger on a `.6s` fade-up, so the KPI block and area cards sit at `opacity: 0` until ~900ms. Measured: `#areaCardsGrid` is `opacity: 0` at t=91ms and t=126ms after load. On a dashboard whose entire job is "show me the number", the headline is blank for a third of the 3-second first-impression window.
- **Context**: Surfaced during the P2 design pass and left open there, because removing it is a motion-character decision rather than a design-system cleanup — the animation was a deliberate visual choice. Raised with the user, who chose to drop it.
- **Completed:** `design/drop-entrance-animation` (2026-09-03) — 진입 애니메이션을 걷어냈다. `@keyframes fadeInUp`, `.ani`, `.d1`-`.d3` 를 `index.html`·`textbook.html` 에서 제거하고 마크업의 해당 클래스도 지웠다(`osha.html` 에는 원래 없었다). `index.html` 의 `.reveal`/`.reveal.visible` 은 마크업 사용처 0, JS 참조 0 인 데드 코드여서 함께 제거했다.
  실측: `goto` 직후 t=68ms 에 전 섹션 `opacity: 1`, 실행 중 애니메이션 0개. 이전에는 `#areaCardsGrid` 가 t=91ms·t=126ms 에 `opacity: 0` 이었다.
  hover·테마 전환·메뉴 열기 트랜지션은 남겼다 — 사용자 입력에 대한 피드백이라 첫 페인트를 막지 않는다. `prefers-reduced-motion` 블록도 그대로라 세 페이지가 동일하다.
  회귀: `D12a`-`D12c` (애니메이션을 되돌리는 뮤테이션에서 3건 모두 FAIL 확인).

### P2 — Dashboard design system pass
- **Why**: Deferred from the /ship design review. Type scale is fragmented into 6 steps below 16px (`.65rem` labels are below the legibility floor for Hangul). No `:focus-visible` anywhere, and sortable `<th>` are not keyboard reachable. Chart `c4` hardcodes a palette that collides with the grade tokens. Explanatory footnotes repeat the same denominator sentence six times, burying the ones that carry unique information.
- **Context**: Colour ramp direction (grade 1 = grey rather than red) was reviewed and deliberately kept — grey reads as "not safety-related", and red stays reserved for accident cases. That decision was honoured; the area palette added in FINDING-004 is a separate blue→purple→pink family so it cannot be mistaken for a grade.
- **Completed:** `/design-review` on `design/dashboard-system-pass` (2026-09-03), 10 atomic fixes across all three dashboards. Measured before → after:

  | | before | after |
  |---|---|---|
  | sub-16px type steps | 7 (10.4/11.2/12/12.6/13/14/15px) | 2 (12/14) |
  | `:focus-visible` rules | 0 | present on all 3 pages |
  | keyboard-reachable sort headers | 0 of 9 | 9 of 9 (`th > button` + `aria-sort`) |
  | text failing WCAG AA (both themes, alpha-composited) | 29 elements | 0 |
  | white-on-colour bar labels | 12, at 2.15–3.77:1 | 0 (moved beside the bar) |
  | chart colours ∩ grade tokens | 2 (`#f59e0b`, `#10b981`) | 0, both themes |
  | denominator restated | 4× (hero + 3 footnotes) | 1× (hero) |
  | heading-level skips | `h1→h3` on 2 pages | 0 |
  | interactive targets < 44px @375px | 4 kinds | 0 |
  | page horizontal scroll @375/480px | 31px | 0 |

  Also fixed along the way: the skip link was hidden at `left:-9999px` and never restored on focus (invisible to keyboard users on every page); `osha.html` had no skip link or `main` landmark at all; its 41 tables had no scroll wrapper and pushed the page 72px sideways at 375px; `.case-detail` hid the 교재/분야 columns below 480px, which removes each row's identity; a `td { max-width }` that `table-layout: auto` ignores; the `margin:-32px` footnote/grid coupling; `transition: all` in 3 places; and `--g1` drifting to `#9ca3af` in `osha.html` only.

  Two defects in the design work itself were caught by `/ship`'s pre-landing and adversarial passes, after the design commits had already landed on the branch:

  - `.card` and `.scroll-x` were on the **same element**, and `.card` comes later in the stylesheet at equal specificity, so its `background` wiped all four gradient layers. Measured `backgroundImage` layer count: 0. The scroll affordance did not render at all on `index.html` and `textbook.html` — precisely the two pages with the nine-column tables it was built for. Only `osha.html`, which used a separate wrapper `<div>`, worked. Fixed by giving all three pages the same inner-wrapper structure, which removes the ordering dependency instead of fighting it with specificity.
  - `overflow-x: auto` clips columns when printing or exporting a PNG, and all three pages carry **Print / PDF** and **Download PNG** menu items. Pre-existing on `index.html`; newly introduced on `osha.html`'s 41 tables by the wrapping above. Fixed with a print-media rule plus a `body.exporting` class toggled around the html-to-image capture.

  Both are now regression-tested (`D11a`-`D11c`), because neither was visible to any existing assertion — they were CSS-cascade and print-media problems with no JavaScript surface.

  The contrast work needed a token split that is worth knowing about: `--warning` / `--positive` / `--g2` / `--g3` were chosen as **fill** colours, so they clear the 3:1 bar for graphical objects but not the 4.5:1 bar for 14px text. `--fg-warn` / `--fg-ok` are the text-safe counterparts and `--accent-strong` is for filled backgrounds carrying white text; the fill values themselves did not change, so no chart or bar shifted colour.

  Not changed in that pass: the grade colour ramp direction (reviewed and kept), and the entrance animation — the latter was raised as a separate item and removed afterwards on `design/drop-entrance-animation` (see above).

### Chunked result rendering stops at 400 rows (`outputs/markdown-search-app.html`)
- **Why**: Functional regression. The `IntersectionObserver` sentinel is appended to `resultsContent`, outside `.results-table-wrapper` (`max-height:400px; overflow-y:auto`). Appending rows never moves the sentinel, so the observer fires once and never again. A keyword like `안전` (3,405 hits) renders 400 rows while the tab count says 3,405, with no truncation notice. Pre-change behaviour rendered everything.
- **Context**: Found by the /ship adversarial pass. Fix: move the sentinel inside the wrapper and pass `root: wrapper`, or switch to a scroll handler. `test-search-equivalence.js` mocks `IntersectionObserver` as a no-op and never calls `renderResultsTable`, so coverage is zero.
- **Depends on**: Nothing. Lives in the currently-uncommitted `markdown-search-app.html` changes.
- **Completed:** PR #2 (2026-09-03) — sentinel moved inside `.results-table-wrapper`, observer `root` set to the wrapper, cleanup hoisted above the empty-results early return. Regression covered by `test-search-equivalence.js` T8a-T8e (mutation-verified).

### `__parseCache` is effectively a strong cache
- **Why**: The comment claimed GC invalidated entries, but `markdownFiles` holds strong references for the whole session, so nothing was collected. It also computed tables/images with those toggles off, and rule-based sentences in hybrid LLM mode where they are discarded.
- **Completed:** PR #4 (2026-09-03) — `sentences`/`tables`/`images` are now memoising lazy getters; `lines`/`pageMap` stay eager because result rendering always needs them. Call sites needed no change (they already guarded on the search toggles). Measured on a 200-page doc scaled to 86 books: 74 MB with everything on, 30 MB in hybrid mode, 19 MB with sentences-only + hybrid. Comment corrected — the WeakMap does invalidate on re-scan, it just has no bound within a session. Covered by `test-search-equivalence.js` T9a-T9h (mutation-verified).
- **Not done**: no LRU byte cap. Measured worst case is 74 MB for the largest known corpus, which a browser tab handles; a cap would also undo FR-1's "re-search is free" property. Revisit if a corpus grows past a few hundred books.

### No CI
- **Why**: The only defence for the published numbers was four harnesses a human had to remember to run.
- **Completed:** PR #5 (2026-09-03) — `.github/workflows/test.yml` runs all four on push and pull_request. `run-core-logic-tests.js` added so the browser harness can be gated too (mutation-verified: a broken assertion and a mid-run exception both exit 1). Verified against a `git archive` clean clone with no `data/` and no pip packages. The last step installs `openpyxl` on purpose — without it `recount_grades.py` stops at the import guard and never reaches the missing-source branch the step is checking.
- **Not done**: `--force` can still write artifacts that failed the regression check; CI cannot catch that because it has no `data/` to run the recount against.

### Add SRI to CDN scripts on the public dashboards
- **Why**: `docs/*.html` loaded Chart.js and html-to-image with no `integrity`, while the search app already pinned XLSX. A compromised CDN could run arbitrary script on the published pages.
- **Completed:** PR #6 (2026-09-03) — all five external `<script>` tags across the three dashboards now carry `integrity` + `crossorigin` + `referrerpolicy`. Hashes were taken from the npm registry tarball, not just the CDN response, so a CDN that was already tampered with could not be baked in. `test-sri.js` (35 assertions) guards it and CI runs the `--online` form. Mutation-verified: removing `integrity`, removing `crossorigin`, drifting one page's hash, and a wrong hash all fail.
- **Deliberately not done — Google Fonts.** The `css2` response differs per User-Agent (measured: Chrome and Firefox return different sha384), so an `integrity` there would block fonts in some browsers. Pinning it means self-hosting the woff2 files.
- **Note**: `docs/*.html` switched from `chart.umd.min.js` to `chart.umd.js`. The minified file does not exist in the npm package — jsDelivr generates it, so there is no upstream to verify the hash against. The unminified file is byte-identical to the tarball and costs 158 more bytes gzipped.
