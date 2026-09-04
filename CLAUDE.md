# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`README.md` is the human-facing entry point (what the project is, how to run it, how to reproduce the analysis). This file carries the details an agent needs and the rules that are easy to get wrong.

## Project Overview

SearchInMD (마크다운 키워드 검색기) is a client-side web application that searches for keywords across markdown files in a selected directory. It reads keyword lists from Excel sheet names, scans markdown files recursively, and exports results back to Excel while preserving the original workbook structure.

- **UI Language**: Korean (한국어)
- **Browser requirement**: Chrome or Edge (uses File System Access API `showDirectoryPicker`)

## Running the Application

```bash
python3 outputs/server.py          # starts on port 3008 (Caddy proxy default)
python3 outputs/server.py 9000     # specify port explicitly

# Access at: http://searchinmd.localhost:2026/search_in_md  (via Caddy)
# Or direct: http://localhost:3008/search_in_md
```

The server sets its working directory to `outputs/` automatically via `os.chdir`. It also proxies `/api/llm/*` requests to LM Studio at `localhost:1234` to bypass CORS for the optional LLM hybrid search feature.

## Architecture

The entire application lives in a single file: `outputs/markdown-search-app.html` (~2,040 lines of embedded HTML + CSS + JavaScript). There is no build system, bundler, or package manager.

### Key Data Flow

1. **Excel Upload** → XLSX.js parses workbook; each **sheet name** becomes a search keyword; column headers are preserved in `sheetColumnMappings`
2. **Folder Selection** → File System Access API recursively scans for `.md` files and paired `_meta.json` files
3. **Search** → For each keyword × file, extracts matching sentences, tables, and images with line numbers. Search options: case sensitivity, content type toggles (sentences/tables/images), optional LLM hybrid mode
4. **Export** → Results written back into the original workbook structure as new rows per sheet

### Important Functions

| Function | Purpose |
|----------|---------|
| `scanForMarkdownFiles()` | Recursive directory walk collecting `.md` content and `_meta.json` metadata |
| `buildPageMapping()` | Maps line numbers to PDF page numbers via 2-strategy resolution (see below) |
| `extractSentencesWithLineNumbers()` | Parses markdown into sentences; tracks heading context; detects standalone titles |
| `extractSentencesWithLLM()` | Optional LLM-powered sentence extraction via LM Studio; falls back to rule-based on failure |
| `extractTablesWithLineNumbers()` | Extracts markdown table rows preserving structure |
| `extractImagesWithLineNumbers()` | Finds image references (`![alt](url)`) with surrounding context |
| `performSearch()` | Main search loop; heading matches include up to 5 sub-content lines |
| `exportToExcel()` | Merges results into original workbook and triggers download |

### Page Mapping Algorithm (`buildPageMapping`)

Resolves markdown line numbers to PDF page numbers using two strategies in priority order:

1. **Page markers** (highest priority): `<!-- page: N -->` HTML comments embedded in markdown
2. **TOC-based 3-stage matching** (fallback using `_meta.json`):
   - **Stage 1**: Match heading lines to TOC entries by normalized text; unique 1:1 matches become position anchors
   - **Stage 2**: For duplicate titles, use anchor-interpolated DP (dynamic programming) to find optimal TOC↔heading assignment minimizing position cost
   - **Stage 3**: Propagate each matched heading's page number to all lines below it until the next mapped heading

### Heading Detection Logic (`extractSentencesWithLineNumbers`)

- **Structural headings**: `#` markdown, `○●◆◇■□▶▷` markers, `(가)` or `1.` numbered patterns
- **Standalone titles**: Short lines (≤25 chars) after blank line, containing Korean, no sentence-ending
- **Bullets** (`•·-*`): Treated as regular content, NOT headings
- All content lines get `headingContext` from the most recent heading above them

### LLM Hybrid Search

Optional feature that uses a local LM Studio model to analyze markdown document structure. When enabled:
- Sends document content to `/api/llm/chat/completions` (proxied by `server.py` to LM Studio `localhost:1234`)
- Tries proxy first, then direct connection as fallback
- Returns structured JSON: `[{"h":"heading","s":"sentence","l":lineNumber}]`
- Strips `<think>` blocks from reasoning models; handles markdown code block wrapping
- Caches results per filename within the session
- Falls back to `extractSentencesWithLineNumbers()` on any error

### Metadata Format (`_meta.json`)

```json
{
  "table_of_contents": [
    { "title": "□ 적용범위", "page_id": 2, "polygon": [...] },
    { "title": "안전 · 유의 사항", "page_id": 5, ... }
  ]
}
```

`page_id` is the actual PDF page number (0-based in JSON, displayed as 1-based). Only lines matching TOC titles get page numbers; others display line numbers prefixed with `L`.

### Global State

All state is held in module-level variables: `selectedFolder`, `markdownFiles`, `keywords`, `searchResults`, `originalWorkbook`, `sheetColumnMappings`, `llmCache`, `llmAvailable`. State is lost on page refresh.

### External Dependencies

- **XLSX (SheetJS) 0.18.5** loaded via CDN — the search app's only runtime dependency
- **CDN scripts carry SRI.** Every external `<script>` pins `integrity` + `crossorigin`; `test-sri.js` checks the attributes offline and the actual CDN bytes with `--online` (CI runs the online form). Google Fonts `<link>` is deliberately excluded — the `css2` response varies by User-Agent, so an `integrity` there would block fonts in some browsers. `docs/*.html` load `chart.umd.js` rather than `chart.umd.min.js`: the minified file is generated by jsDelivr and has no upstream to verify against, while the unminified one is byte-identical to the npm tarball, and the transfer difference is 158 bytes gzipped.
- **Python 3 standard library** for the dev server (`server.py` has no pip dependencies)
- **LM Studio** (optional) — local LLM server on port 1234 for hybrid search

The **data pipeline scripts** (see below) are a separate story: they require pip packages — `requests` + `beautifulsoup4` (downloaders) and `openpyxl` (Excel/page utilities). There is no `requirements.txt`; install ad hoc.

## Data Pipeline (Python, repo root)

The root-level Python scripts are an offline data pipeline that feeds the search app — they are **not** part of the web app and run independently. Two distinct groups:

### 1. Publication downloaders (web scrapers)

`osha_downloader.py`, `kosha_downloader.py`, `niosh_downloader.py`, `eu_osha_downloader.py`, `safework_au_downloader.py` — each scrapes one occupational-safety agency's publication list and bulk-downloads PDFs. They share a common shape:

- **Resumable**: each writes a `_download_progress.json` (`{downloaded, failed, articles}`) into its `SAVE_DIR`; rerunning skips completed items.
- **`SAVE_DIR` comes from the `DOWNLOAD_ROOT` env var** — `export DOWNLOAD_ROOT="/path/to/안전보건공단"` once, and each script appends its own agency subdirectory. Unset, it falls back to `downloads/` inside the repo (gitignored). Previously each script hardcoded an absolute local path.
- Spoof a desktop `User-Agent`, throttle with a `DELAY` constant, and `sanitize_filename()` for filesystem-safe names.
- Year/count filters via `MIN_YEAR`, `TOTAL_PAGES`, `ARTICLE_LIMIT` constants near the top.

### 2. Page-mapping & Excel utilities

These bridge the PDF→markdown→Excel workflow and mirror the HTML app's page logic in Python:

- `page_utils.py` — shared lib: `nfc()`, `find_md_and_meta()`, `build_page_map()`, `extract_page_content()`, `is_cell_truncated()`. `build_page_map()` is the Python counterpart of the app's `buildPageMapping`. `is_cell_truncated()` decides whether a workbook cell was cut at Excel's 32,767-char limit — it requires **both** the exact length and the trailing `...` that `add_fullpage.py` appends, because either condition alone misfires (see the truncation rule below).
- `insert_page_markers.py` — walks NCS markdown dirs and injects `<!-- page: N -->` comments from `_meta.json`. **This is what produces the Strategy-1 markers** that `buildPageMapping` prefers (see `TODOS.md` — once all docs have markers, the app's DP fallback becomes dead code). Supports `--dry-run`, `--backup`, and an explicit dir arg.
- `add_fullpage.py` — reads page numbers from an Excel column, then writes each row's full page content back into the next column (`EXCEL_MAX_CHARS = 32767` cell cap).
- `outputs/reclassify_accident_cases.py` — re-judges "사고사례여부" per-row from cell contents rather than whole-page text.
- `truncation_audit.py` — transcript of the Excel cell-limit truncation, run against the raw workbooks. It reads the `.xlsx` as zip+XML so it needs **no pip packages**, which matters because it exists to let a fresh clone confirm the truncation figures baked into `recount_grades.py`'s `EXPECTED`. Page folding is borrowed from `recount_grades.parse_row`/`aggregate` (openpyxl stubbed out) rather than reimplemented, and the run ends by diffing its own output against `EXPECTED` — exit 1 on mismatch. `--cells-only` skips the fold. Truncation is detected by column-independent scan, not a fixed column, because the two workbooks disagree on layout.
- `recount_grades.py` — reads the two source workbooks in `data/`, remaps both to the unified grade scheme, aggregates **per unique page** (not per keyword hit), and writes `docs/03-analysis/data/{ncs_pages.csv, txt_pages.csv, summary.json}`. Flags: `--data`, `--out`, `--force`. It refuses to write when its built-in regression check fails; `--force` overrides that (use it only when the source data legitimately changed and you are about to update `EXPECTED`). Unlike the scripts above it takes no hardcoded absolute path — `--data` defaults to `data/` next to the script.

These still have **hardcoded absolute paths** (`EXCEL_PATH`, `NCS_BASES`, `DEFAULT_NCS_DIRS`) — edit the constants before running. (The downloaders no longer do; see `DOWNLOAD_ROOT` above.)

## Safety Grading Scheme

Every page in the analysis corpus carries a grade. **The shipped scheme is:**

| 등급 | 뜻 | 원본 판정 근거 |
|:---:|---|---|
| **1** | 미흡·없음 | 안전 키워드 5건 이하 |
| **2** | 형식적 언급 | 안전 키워드 다수, 구체적 조치 없음 |
| **3** | 구체적 대책 | 안전 키워드 + 조치·대책 제시 |

The two source workbooks in `data/` disagree: the NCS one already uses this numbering, the textbook one is rotated by one (not reversed — `{1→2, 2→3, 3→1}` is a cycle). `recount_grades.py` remaps the textbook side so both land on the scheme above. `docs/03-analysis/grade-recount.analysis.md` §2 shows the evidence (grade-reason strings, 100% consistent per dataset).

Two rules that are easy to get wrong:

- **Grade is a page property, not a keyword-hit property.** Counting rows double-counts pages that many keywords land on, which systematically inflates the top grade — NCS 등급3 is 2,228 hits but only 108 pages. Always aggregate per unique (교재, 페이지).
- **When a page's rows disagree, take the lowest grade.** Majority voting loses: a buggy sheet records the same wrong verdict on several rows, and the duplicate count becomes votes. 12 NCS pages hit this.
- **16 NCS pages were cut at Excel's 32,767-char cell limit, and the original is gone.** The source workbook is the only copy, so this is a permanent limit, not a to-do. Detect it with `page_utils.is_cell_truncated()` — length **and** the trailing `...`, since a page that was genuinely 32,767 chars never gets the marker. Truncation is not random: 0 of 1,270 등급1 pages but **12 of 108 등급3** (11.1%); textbook side is 0. It is an *under*-counting defect (deleting text can only lower a grade), so it pushes the opposite way from every other known defect — and its effect is bounded, since the 12 등급3 pages are already at the maximum and only the 4 등급2 ones can move (등급3 ∈ [108, 112]). Never fold this per row: 1,376 rows carry a truncated cell, 86× the page count.

⚠️ `docs/01-plan/features/safety-grading.plan.md` describes **older, conflicting** numbering (1 기본언급 / 2 구체적대책 / 3 관련없음). `feature-proposals.plan.md` has the same numbering as shipped but an old label for grade 2 ("기본 언급" → now "형식적 언급"). Both carry a banner and are kept for provenance. This section is authoritative.

## Testing

There is no test framework (no `package.json` / `pyproject.toml`). The project ships its own harnesses — all exit 0/1 and depend only on Node and the Python standard library.

```bash
node   outputs/test-search-equivalence.js   # 24 assertions — search equivalence, chunked render, lazy parse cache
node   outputs/test-dashboard-data.js       # 117 assertions — docs/ dashboard data + table render/sort
python3 outputs/test-recount-grades.py      # 181 assertions — recount_grades.py logic

python3 truncation_audit.py                 # not a test — re-measures truncation and checks it against EXPECTED (needs data/)

node   outputs/run-core-logic-tests.js       # 32 assertions — headless runner for test-core-logic.html
node   outputs/test-sri.js                  # 41 assertions — SRI on external scripts (--online to verify against the CDN)

# Or open it in a browser and read the tab title: "PASS: N/N tests passed"
open outputs/test-core-logic.html
```

All four run in CI on every push and pull request (`.github/workflows/test.yml`). The workflow installs nothing for the harnesses themselves; it installs `openpyxl` only for the last step, which checks that `recount_grades.py` exits with a readable message instead of a traceback when `data/` is absent (the default state of a fresh clone).

`test-core-logic.html` copies shared helper functions from the main app and runs assertions in-browser. When adding or changing heading detection / normalization logic, update both files and verify tests pass. `run-core-logic-tests.js` runs that same HTML headlessly (minimal DOM + `vm`, reads `document.title`) so CI can gate on it — it holds no copy of the assertions.

`test-search-equivalence.js` and `test-dashboard-data.js` load the real `<script>` blocks out of the HTML files via `vm` + a DOM mock, so they carry no copy-paste debt. `test-recount-grades.py` stubs `openpyxl` in `sys.modules` and monkeypatches `load_workbook` with a fake workbook, so it runs without pip packages and without the gitignored `data/` originals.

`test-dashboard-data.js` and `test-recount-grades.py` carry a `known()` helper for **known issues**: an assertion that documents a real defect, prints `⚠ KNOWN ISSUE` on every run, but does not fail the suite. Use it when you find a defect you are not fixing in the same change; promote the call back to `check()` once fixed. Currently zero known issues are outstanding.

For manual E2E testing, use `outputs/test-samples/` with sample `.md` files. For real-world testing with `_meta.json` files, use NCS 반도체 documents in `/Users/zealnutkim/Documents/개발/pinecone_agent/documents/ncs/`.

## Test Coverage

**Minimum 60% / target 80%** of changed code paths must be covered by an automated harness before landing.

- New logic in `outputs/*.html` (search app) → extend `test-search-equivalence.js` or `test-core-logic.html`.
- New data or table/sort logic in `docs/*.html` (dashboards) → extend `test-dashboard-data.js`. Hardcoded data arrays must be cross-validated against `docs/03-analysis/data/summary.json`, never asserted against themselves.
- New logic in `recount_grades.py` or the page-mapping utilities → extend `test-recount-grades.py`.
- Paths that genuinely cannot be automated here (browser chart rendering, File System Access API, real `.xlsx` parsing) are documented as `[→E2E]` gaps in the PR body rather than silently skipped.

## Other Artifacts

- **Analysis dashboards** (`docs/`, GitHub Pages) — standalone single-file HTML dashboards using Chart.js 4.4.7 via CDN, independent of the search app:
  - `docs/index.html` — NCS 반도체 교재 안전보건 분석
  - `docs/textbook.html` — 반도체고 교과서 안전보건 분석 (KPI 는 검출 362쪽과 전체 2,055쪽 두 분모를 병기, 비교표는 검출쪽 기준)
  - `docs/osha.html` — OSHA 반도체 화학물질 안전교육 과정 분석

### Dashboard design tokens (`docs/*.html`)

The three dashboards each carry their own copy of the same `<style>` block. When you change one of these, change all three — they are meant to stay byte-identical in the token area.

| Token group | Values | Rule |
|---|---|---|
| Type scale | `--fs-xs .75rem` / `--fs-sm .875rem` / `--fs-md 1rem` / `--fs-lg 1.125rem` | Nothing below 16px may use a literal size. `xs` (12px) is the floor — Hangul falls apart below it. Prose bodies use `md`; tables, captions and buttons use `sm`; only uppercase labels use `xs`. |
| Grade ramp | `--g1` grey / `--g2` amber / `--g3` green | **Grade only.** Never use these for a value that is not a 1/2/3 grade. `--danger` red is reserved for accident cases. These are **fill** values — see the row below before using one as a text colour. |
| Text-safe semantics | `--fg-warn` / `--fg-ok` / `--accent-strong` | The fill colours clear 3:1 (graphical objects) but not 4.5:1 (text) at 14px in the light theme — measured `--warning` 3.19:1, `--g3` 3.77:1, white-on-`--accent` 3.68:1 in dark. Use `--fg-*` whenever the colour lands on glyphs, `--accent-strong` for a filled background under white text. Large numbers (`.kpi-v`, 36px bold) stay on the fill token so the card reads as one block. |
| Area palette | `--a1` 개발 / `--a2` 제조 / `--a3` 장비 / `--a4` 재료 | Blue→purple→pink, per theme. Deliberately disjoint from the grade ramp so the two encodings can sit side by side (`c3` grade-stacked next to `c4` area-stacked). |
| `--scrim` | theme-dependent | Edge shadow for `.scroll-x`. |

Other invariants worth not breaking:

- Interactive controls have `min-height: 44px`. Sortable headers are `th > button.sortbtn`, never `th[onclick]` — the button is what makes them keyboard-reachable, and `sK()` must keep `aria-sort` in sync (the arrow glyph is drawn from that attribute, so the visual and the assistive-tech state cannot diverge).
- Wide tables go in an **inner** `<div class="scroll-x">` inside the card, with `tabindex="0"`, `role="region"` and an `aria-label`. Never put `scroll-x` on the `.card` element itself: `.card` is defined later at equal specificity, so its `background` silently wipes the scroll-shadow gradients. Do not solve narrow viewports by hiding columns — those tables identify a row by 교재 and 쪽. `@media print` and `body.exporting` unclip these regions so Print/PDF and Download PNG do not cut off columns.
- Grid children carry `min-width: 0`. Without it, chart cards refuse to shrink and the page scrolls sideways below 768px.
- No text on top of a coloured fill. Numbers go beside the bar, not inside it.
- **No deferred entrance animation on content.** `.ani{animation:fadeInUp .6s both}` with a `.1s`/`.2s`/`.3s` stagger held the KPI block and area cards at `opacity: 0` for ~0.9s (measured `opacity: 0` at t=91ms), which is a third of the three-second first-impression window on a dashboard whose whole job is showing the number. It also made print and PNG export race the animation. Removed; `D12a`-`D12c` keep it out. Interaction transitions (hover, theme switch, menu open) are unaffected — they respond to input and never block first paint.

- **User-facing guides** (`docs/*.md`, linked from README's `## 문서` table):
  - `docs/tutorial-first-search.md` — the only tutorial. Runs on `outputs/test-samples/` so it needs no private data. If you change the app's step labels, the Excel header aliases in `exportToExcel`, or the sample files, this doc goes stale.
  - `docs/howto-download-publications.md` — the downloaders' `DOWNLOAD_ROOT`, per-agency save dirs, range constants, and resume semantics. Note that `eu_osha_downloader.py` alone has no `DELAY` constant (it hardcodes `time.sleep(2)`).
  - `docs/howto-page-markers.md` — `insert_page_markers.py`. `page_id` in `_meta.json` is 0-based and the marker is written +1. `--force` strips the existing markers before re-deriving from the TOC (leaving them in place would make `build_page_map` read them via Strategy 1 and re-emit the same values, doubling the markers); it refuses to touch a file whose `_meta.json` is missing or whose marker sits mid-line, because neither is recoverable. Covered by `R8a`-`R8j` in `test-recount-grades.py`.
- `docs/01-plan/`, `docs/02-design/`, `docs/03-analysis/`, `docs/04-report/` — feature PDCA documents (`features/` subdirs hold per-feature plan/design/analysis/report `.md`)
- `docs/03-analysis/data/` — machine-readable output of `recount_grades.py`. `ncs_pages.csv` and `txt_pages.csv` are one row per unique (교재, 페이지) with its grade, grade reason, accident-case flag, and a `절단` flag (last column — keep it last so index-based readers do not shift); `summary.json` carries the aggregate counts plus `truncated_pages` / `truncated_page_g`, `kw_pages` (unique detected pages per keyword — the dashboards' `pg` column is validated against this, never against itself) and `page_grade_digest` (a hash of the whole page→grade assignment, so a reassignment that leaves the totals unchanged still fails the regression check).
- `docs/archive/YYYY-MM/` — retired PDCA feature docs, kept for provenance. `_INDEX.md` lists what moved and when.
- `docs/NCS_교재_노동안전_분석보고서.md` — **superseded**. Built on the older 3,552-row dataset with a different grade numbering; carries a deprecation banner. Kept for provenance; cite the dashboards or `grade-recount.analysis.md` instead.
- `키워드기반_문서분류분석_방법론.hwpx` (repo root) — the methodology of record for the search pipeline: the 6 stages, the heading-detection rules, and the line-number→PDF-page alignment algorithm. Read it before changing `extractSentencesWithLineNumbers` or `buildPageMapping`. It does **not** define the grading scheme (see the section above).
- `docs/03-analysis/D2-C2.analysis.md` — gap analysis for the page-marker + dashboard-upload features (100% match).

## Development Notes

- The app is a single HTML file — all CSS, JS, and markup are inline. There is no module system; functions share the global scope.
- `test-core-logic.html` duplicates helper functions rather than importing them. Keep both files in sync when modifying `isHeadingLine`, `isStandaloneTitle`, `normalizeHeading`, or `nfc`.
- `server.py` auto-detects an available port starting from 3008. It uses only Python stdlib — no pip dependencies.
- The File System Access API (`showDirectoryPicker`) only works in Chromium browsers. Safari/Firefox are not supported.

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
