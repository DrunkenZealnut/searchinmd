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
- **Why**: `인화` and similar sheets report a keyword total that disagrees with their own itemised list (`안전 9건 [폭발(1)]`), which is what makes 12 pages disagree with themselves. `safety_count <= 5` uses raw frequency with no length normalisation, so long pages get promoted. No word-boundary matching, so domain homonyms (장비 진동, 파티클 먼지) count as safety content.
- **Context**: `recount_grades.py` works around this with a conservative lowest-grade rule, but the source data stays wrong. See `docs/03-analysis/grade-recount.analysis.md` §6.
- **Depends on**: Access to the original grading script (not in this repo).

## P2 — Dashboard design system pass
- **Why**: Deferred from the /ship design review. Type scale is fragmented into 6 steps below 16px (`.65rem` labels are below the legibility floor for Hangul). No `:focus-visible` anywhere, and sortable `<th>` are not keyboard reachable. Chart `c4` hardcodes a palette that collides with the grade tokens. Explanatory footnotes repeat the same denominator sentence six times, burying the ones that carry unique information.
- **Context**: Colour ramp direction (grade 1 = grey rather than red) was reviewed and deliberately kept — grey reads as "not safety-related", and red stays reserved for accident cases.
- **Depends on**: Nothing.

## Completed

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
