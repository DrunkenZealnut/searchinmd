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
- **Context**: The old blocker ("no access to the original grading script") turned out not to bind. The script is not needed: the source workbook carries `페이지전체내용` on 100% of rows, so the grade can be recomputed from the page text directly. The rule itself was reverse-engineered from the 4,000+ committed `등급사유` strings and reproduces at **99.6%** (1,839/1,847), which is what makes the deltas attributable.
  One claim in the earlier version of this entry was wrong: the "total disagrees with its own itemised list" is **not** a scoring bug. 168 of the 171 mismatches list exactly five terms — the reason string truncates to the top five. Only 3 pages (0.16%) are genuinely off, each by one.
- **Status**: `regrade.py` reproduces the rule and fixes the two real defects; per-defect impact is in `docs/03-analysis/data/regrade_impact.json`. **The dashboards still publish the old numbers** — applying the correction is a research-facing decision, not a code one.

  | | 등급1 | 등급2 | 등급3 | 등급3 비율 | F1 (코더 A / B) |
  |---|---:|---:|---:|---:|---:|
  | 발표 중 (원본) | 1,270 | 469 | 108 | 5.8% | 0.803 / 0.810 |
  | 재현 (규칙 확인용) | 1,261 | 478 | 108 | 5.8% | — |
  | + 단어 경계 (D1) | 1,304 | 442 | 101 | 5.5% | — |
  | + 길이 정규화 (D2) | 1,371 | 404 | 72 | 3.9% | — |
  | D1+D2 | 1,407 | 371 | 69 | 3.7% | 0.813 / 0.807 |
  | D1+D2 + 조건부면제 (D5) | 1,407 | 367 | 73 | 4.0% | 0.790 / 0.785 |
  | **D1+D2 + 이산화 (D4 round)** | **1,386** | **386** | **75** | **4.1%** | **0.834 / 0.828** |
  | D1+D2 + 이산화 (D4 floor) | 1,367 | 401 | 79 | 4.3% | 0.851 / 0.846 |

- **Validation**: 69쪽 맹검 이중코딩(분쟁군 39 전수 + 대조군 30). 두 AI 코더 일치 88.4%, Cohen κ 0.796. F1 은 모집단 비중으로 보정한 값 — 표본에서 분쟁군이 과대표집돼 있어 그냥 세면 안 된다. `score_coding.py` 5번 섹션.
- **D5 조건부 정규화는 기각.** "안전 전담 페이지는 길고 조치가 많으니 정규화가 부당하게 깎는다"는 가설이 데이터와 반대였다. 코더가 진짜 등급3이라 한 쪽은 조치어 중앙 5건·길이 중앙 1,268자로 **짧았고**, 강등이 정당한 쪽이 조치어 중앙 8건·길이 중앙 6,436자로 **길었다**. 면제가 되살린 4쪽은 코더가 전부 등급3이 아니라고 했다.
- **D4 이산화가 진짜 원인.** 카운트는 정수인데 임계는 연속값이라 비교가 사실상 `ceil()` 로 동작한다. 중앙값보다 1자 긴 페이지가 조치어 5건이 아니라 6건을 요구받는다. 분쟁군 11쪽이 임계 차이 -2.3 이내에서 떨어졌고 그중 7쪽을 코더 둘 다 진짜 등급3이라 판정했다.
- **Depends on**: A decision on whether to republish, and at which number. 열려 있는 것 셋:
  1. `floor` 가 F1 은 가장 높지만 **이 69쪽에서 골라 채택하면 과적합**이다. `round` 는 라벨을 보기 전에 중립적 이산화로 고른 값이라 그 문제가 없다. floor 채택은 별도 홀드아웃이 필요하다.
  2. **현행의 재현율은 측정된 적이 없다.** 표본이 현행의 등급3 108쪽 안에서만 뽑혀서, 등급1·2로 떨어진 1,739쪽에 진짜 등급3이 얼마나 묻혀 있는지 모른다. 위 F1 은 전부 상한이다.
  3. AI 두 코더의 일치는 사람 이중코딩이 아니다. κ 0.796 이 정확도인지 공통 편향인지 사람 코딩 30~40쪽으로만 갈린다.
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
