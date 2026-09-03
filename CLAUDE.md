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

- `page_utils.py` — shared lib: `nfc()`, `find_md_and_meta()`, `build_page_map()`, `extract_page_content()`. `build_page_map()` is the Python counterpart of the app's `buildPageMapping`.
- `insert_page_markers.py` — walks NCS markdown dirs and injects `<!-- page: N -->` comments from `_meta.json`. **This is what produces the Strategy-1 markers** that `buildPageMapping` prefers (see `TODOS.md` — once all docs have markers, the app's DP fallback becomes dead code). Supports `--dry-run`, `--backup`, and an explicit dir arg.
- `add_fullpage.py` — reads page numbers from an Excel column, then writes each row's full page content back into the next column (`EXCEL_MAX_CHARS = 32767` cell cap).
- `outputs/reclassify_accident_cases.py` — re-judges "사고사례여부" per-row from cell contents rather than whole-page text.
- `recount_grades.py` — reads the two source workbooks in `data/`, remaps both to the unified grade scheme, aggregates **per unique page** (not per keyword hit), and writes `docs/03-analysis/data/{ncs_pages.csv, txt_pages.csv, summary.json}`. Flags: `--data`, `--out`, `--force`. It refuses to write when its built-in regression check fails; `--force` overrides that (use it only when the source data legitimately changed and you are about to update `EXPECTED`). Unlike the scripts above it takes no hardcoded absolute path — `--data` defaults to `data/` next to the script.

These still have **hardcoded absolute paths** (`EXCEL_PATH`, `NCS_BASES`, `DEFAULT_NCS_DIRS`) — edit the constants before running. (The downloaders no longer do; see `DOWNLOAD_ROOT` above.)

## Safety Grading Scheme

Every page in the analysis corpus carries a grade. **The shipped scheme is:**

| 등급 | 뜻 | 원본 판정 근거 |
|:---:|---|---|
| **1** | 미흡·없음 | 안전 키워드 5건 이하 |
| **2** | 형식적 언급 | 안전 키워드 다수, 구체적 조치 없음 |
| **3** | 구체적 대책 | 안전 키워드 + 조치·대책 제시 |

The two source workbooks in `data/` disagree: the NCS one already uses this numbering, the textbook one is reversed. `recount_grades.py` remaps the textbook side `{1→2, 2→3, 3→1}` so both land on the scheme above. `docs/03-analysis/grade-recount.analysis.md` §2 shows the evidence (grade-reason strings, 100% consistent per dataset).

Two rules that are easy to get wrong:

- **Grade is a page property, not a keyword-hit property.** Counting rows double-counts pages that many keywords land on, which systematically inflates the top grade — NCS 등급3 is 2,228 hits but only 108 pages. Always aggregate per unique (교재, 페이지).
- **When a page's rows disagree, take the lowest grade.** Majority voting loses: a buggy sheet records the same wrong verdict on several rows, and the duplicate count becomes votes. 12 NCS pages hit this.

⚠️ `docs/01-plan/features/safety-grading.plan.md` and `feature-proposals.plan.md` describe **older, conflicting** numbering. They are kept for provenance and carry a banner. This section is authoritative.

## Testing

There is no test framework (no `package.json` / `pyproject.toml`). The project ships its own harnesses — all exit 0/1 and depend only on Node and the Python standard library.

```bash
node   outputs/test-search-equivalence.js   # 11 assertions — search routine equivalence
node   outputs/test-dashboard-data.js       # 92 assertions — docs/ dashboard data + table render/sort
python3 outputs/test-recount-grades.py      # 86 assertions — recount_grades.py logic

# Open in browser to run core logic unit tests (isHeadingLine, isStandaloneTitle, normalizeHeading, NFC)
open outputs/test-core-logic.html
# Check browser title: "PASS: N/N tests passed" or "FAIL: ..."
```

`test-core-logic.html` copies shared helper functions from the main app and runs assertions in-browser. When adding or changing heading detection / normalization logic, update both files and verify tests pass.

`test-search-equivalence.js` and `test-dashboard-data.js` load the real `<script>` blocks out of the HTML files via `vm` + a DOM mock, so they carry no copy-paste debt. `test-recount-grades.py` stubs `openpyxl` in `sys.modules` and monkeypatches `load_workbook` with a fake workbook, so it runs without pip packages and without the gitignored `data/` originals.

Both new harnesses carry a `known()` helper for **known issues**: an assertion that documents a real defect, prints `⚠ KNOWN ISSUE` on every run, but does not fail the suite. Use it when you find a defect you are not fixing in the same change; promote the call back to `check()` once fixed. Currently zero known issues are outstanding.

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
- `docs/01-plan/`, `docs/02-design/`, `docs/03-analysis/`, `docs/04-report/` — feature PDCA documents (`features/` subdirs hold per-feature plan/design/analysis/report `.md`)
- `docs/03-analysis/data/` — machine-readable output of `recount_grades.py`. `ncs_pages.csv` and `txt_pages.csv` are one row per unique (교재, 페이지) with its grade, grade reason, and accident-case flag; `summary.json` carries the aggregate counts plus `kw_pages` (unique detected pages per keyword — the dashboards' `pg` column is validated against this, never against itself) and `page_grade_digest` (a hash of the whole page→grade assignment, so a reassignment that leaves the totals unchanged still fails the regression check).
- `docs/archive/YYYY-MM/` — retired PDCA feature docs, kept for provenance. `_INDEX.md` lists what moved and when.
- `docs/NCS_교재_노동안전_분석보고서.md` — **superseded**. Built on the older 3,552-row dataset with a different grade numbering; carries a deprecation banner. Kept for provenance; cite the dashboards or `grade-recount.analysis.md` instead.

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
