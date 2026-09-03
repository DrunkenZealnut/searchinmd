# TODOS

## Add page markers to PDF-to-markdown pipeline
- **Why**: Eliminates the 200-line DP page mapping heuristic. Strategy 1 (`<!-- page: N -->` markers) already handles this perfectly.
- **Context**: User controls the upstream converter. Once all documents have markers, `buildPageMapping` Strategy 2 (TOC matching + DP) becomes dead code and can be removed.
- **Depends on**: Access to the PDF-to-markdown converter codebase (separate repo).

## Add LLM fallback indicator to search results
- **Why**: When `extractSentencesWithLLM` fails and falls back to rule-based, the user sees no indication. Mixed-quality results are a data integrity issue.
- **Context**: Currently the fallback is `console.warn` only. Add a visual badge or file-level indicator showing which analysis method was used.
- **Depends on**: Nothing.

## P1 — `__parseCache` is effectively a strong cache
- **Why**: The comment says entries are invalidated by GC, but `markdownFiles` holds strong references to the file objects for the whole session, so nothing is ever collected. Peak memory goes from one file's parse to the whole corpus (lines + sentences + tables + images + lowercase copies). OOM risk on the 86-book NCS set.
- **Context**: Also computes tables/images even when those search toggles are off, and computes rule-based sentences even in hybrid LLM mode. Add an LRU byte budget, or at minimum correct the comment.
- **Depends on**: Nothing.

## P2 — Rewrite the safety grading algorithm
- **Why**: `인화` and similar sheets report a keyword total that disagrees with their own itemised list (`안전 9건 [폭발(1)]`), which is what makes 12 pages disagree with themselves. `safety_count <= 5` uses raw frequency with no length normalisation, so long pages get promoted. No word-boundary matching, so domain homonyms (장비 진동, 파티클 먼지) count as safety content.
- **Context**: `recount_grades.py` works around this with a conservative lowest-grade rule, but the source data stays wrong. See `docs/03-analysis/grade-recount.analysis.md` §6.
- **Depends on**: Access to the original grading script (not in this repo).

## P2 — Dashboard design system pass
- **Why**: Deferred from the /ship design review. Type scale is fragmented into 6 steps below 16px (`.65rem` labels are below the legibility floor for Hangul). No `:focus-visible` anywhere, and sortable `<th>` are not keyboard reachable. Chart `c4` hardcodes a palette that collides with the grade tokens. Explanatory footnotes repeat the same denominator sentence six times, burying the ones that carry unique information.
- **Context**: Colour ramp direction (grade 1 = grey rather than red) was reviewed and deliberately kept — grey reads as "not safety-related", and red stays reserved for accident cases.
- **Depends on**: Nothing.

## P3 — No CI
- **Why**: The only defence for the published numbers is four harnesses a human has to remember to run. `recount_grades.py --force` can write artifacts that failed the regression check.
- **Context**: Add `.github/workflows/test.yml` running the three Node/Python harnesses on push and pull_request. `test-core-logic.html` needs a headless shim.
- **Depends on**: Nothing.

## P3 — Add SRI to CDN scripts on the public dashboards
- **Why**: `docs/*.html` load Chart.js, html-to-image, and Google Fonts with no `integrity=`. The search app already pins XLSX with SRI, so the dashboards are the inconsistent ones.
- **Depends on**: Nothing.

## Completed

### Chunked result rendering stops at 400 rows (`outputs/markdown-search-app.html`)
- **Why**: Functional regression. The `IntersectionObserver` sentinel is appended to `resultsContent`, outside `.results-table-wrapper` (`max-height:400px; overflow-y:auto`). Appending rows never moves the sentinel, so the observer fires once and never again. A keyword like `안전` (3,405 hits) renders 400 rows while the tab count says 3,405, with no truncation notice. Pre-change behaviour rendered everything.
- **Context**: Found by the /ship adversarial pass. Fix: move the sentinel inside the wrapper and pass `root: wrapper`, or switch to a scroll handler. `test-search-equivalence.js` mocks `IntersectionObserver` as a no-op and never calls `renderResultsTable`, so coverage is zero.
- **Depends on**: Nothing. Lives in the currently-uncommitted `markdown-search-app.html` changes.
- **Completed:** PR #2 (2026-09-03) — sentinel moved inside `.results-table-wrapper`, observer `root` set to the wrapper, cleanup hoisted above the empty-results early return. Regression covered by `test-search-equivalence.js` T8a-T8e (mutation-verified).
