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

The root-level Python scripts are an offline data pipeline around the search app — they are **not** part of the web app and run independently. Three distinct groups:

### 1. Publication downloaders (web scrapers)

`osha_downloader.py`, `kosha_downloader.py`, `niosh_downloader.py`, `eu_osha_downloader.py`, `safework_au_downloader.py` — each scrapes one occupational-safety agency's publication list and bulk-downloads PDFs. They share a common shape:

- **Resumable**: each writes a `_download_progress.json` (`{downloaded, failed, articles}`) into its `SAVE_DIR`; rerunning skips completed items.
- **`SAVE_DIR` comes from the `DOWNLOAD_ROOT` env var** — `export DOWNLOAD_ROOT="/path/to/안전보건공단"` once, and each script appends its own agency subdirectory. Unset, it falls back to `downloads/` inside the repo (gitignored). Previously each script hardcoded an absolute local path.
- Spoof a desktop `User-Agent`, throttle with a `DELAY` constant, and `sanitize_filename()` for filesystem-safe names.
- Year/count filters via `MIN_YEAR`, `TOTAL_PAGES`, `ARTICLE_LIMIT` constants near the top.

### 2. Page-mapping & Excel utilities

These bridge the PDF→markdown→Excel workflow and mirror the HTML app's page logic in Python:

- `page_utils.py` — shared lib: `nfc()`, `find_md_and_meta()`, `build_page_map()`, `extract_page_content()`, `is_cell_truncated()`. `build_page_map()` is the Python counterpart of the app's `buildPageMapping`. `is_cell_truncated()` decides whether a workbook cell was cut at Excel's 32,767-char limit — it requires **both** the exact length and the trailing `...` that `add_fullpage.py` appends, because either condition alone misfires (see the truncation rule below). It also owns the constants the regrade/coding scripts share — `EXCEL_MAX_CHARS`, `CODING_GROUPS` (the four strata: `disputed`, `control`, `boundary`, `recall`) and `BASELINE` (the 현행 rule's variant label) — so `make_coding_sheet.py` and `score_coding.py` import one definition instead of retyping it (`score_coding.py` cannot import `regrade.py` because of the openpyxl guard, which is why the constants live here). `GRADE_LABEL` (the shipped 등급 names) and `PAGE_MARKER_RE` (the `<!-- page: N -->` pattern, number captured) live here for the same reason — `build_page_map()`, `recount_grades.py`, `insert_page_markers.py` and `resegment.py` share one copy.
- `insert_page_markers.py` — walks NCS markdown dirs and injects `<!-- page: N -->` comments from `_meta.json`. **This is what produces the Strategy-1 markers** that `buildPageMapping` prefers (see `TODOS.md` — once all docs have markers, the app's DP fallback becomes dead code). Supports `--dry-run`, `--backup`, and an explicit dir arg.
- `add_fullpage.py` — reads page numbers from an Excel column, then writes each row's full page content back into the next column (`EXCEL_MAX_CHARS = 32767` cell cap).
- `outputs/reclassify_accident_cases.py` — re-judges "사고사례여부" per-row from cell contents rather than whole-page text.
- `truncation_audit.py` — transcript of the Excel cell-limit truncation, run against the raw workbooks. It reads the `.xlsx` as zip+XML so it needs **no pip packages**, which matters because it exists to let a fresh clone confirm the truncation figures baked into `recount_grades.py`'s `EXPECTED`. Page folding is borrowed from `recount_grades.parse_row`/`aggregate` (openpyxl stubbed out) rather than reimplemented, and the run ends by diffing its own output against `EXPECTED` — exit 1 on mismatch. `--cells-only` skips the fold. Truncation is detected by column-independent scan, not a fixed column, because the two workbooks disagree on layout. Zip entries are opened through a size/ratio cap (`MAX_ENTRY_BYTES`, `MAX_ZIP_RATIO`) so a crafted workbook cannot balloon on decompression; the real workbooks peak at 36.7× and 81 MB, well under the caps.
- `resegment.py` — re-places every NCS keyword hit onto the **real PDF page**. The 2026-04 search ran on markdown whose page markers were TOC-derived, so one workbook "page" label often spans many pages (16 labels hit the 32,767-char cell cap; the equipment-safety module has 945 hits under 20 labels — audit finding C1). Only 23 of 89 markdown files carry per-page markers, so re-searching does not fix it. The script aligns markdown lines to PyMuPDF page text (character 3-gram containment + monotone DP; `align_lines`), maps each hit sentence to its line (`match_rows`, duplicates resolved in document order), regrades each real page with `regrade.grade_page`'s baseline, and aggregates per (book, page). Books whose markdown already has dense markers use them (`marker_pages`); alignment is still run there as a self-check (`alignment_check` in the output, 23 books: 83.6% exact / 94.9% ±1 page on the DP-candidate lines, 77.6% / 90.3% on every text line including the propagated ones — `all_*`, and 88.6% / 98.5% once the marker-gap segments — whose 'truth' is the propagated marker value — are excluded, `nogap_*`). Needs `NCS_PDF_ROOT` (private PDFs) plus `pymupdf`/`openpyxl`; ~30 s. Flags: `--pdf-root` (defaults to `$NCS_PDF_ROOT`), `--md-root`, `--workbook`, `--out`, `--paged-dir`, `--limit`, `--force`. Writes `docs/03-analysis/data/ncs_pages_reseg.csv` (12 columns; `출처` is `text` for a page that holds matched rows, `text-fallback` for a page reached only through an unmatched row's old label but graded from its markdown text, `label` when there is no text and the row grades are used; `md자수`/`pdf자수` are normalized text lengths, so a page where several PDF pages collapsed into one markdown block shows as `md자수` ≫ `pdf자수`) + `reseg_summary.json` (tracked, no body text, paths written repo-relative or with `~` via `public_path()`, never absolute) and per-book line→page maps plus `rows_map.csv` under `data/markdown/ncs_paged/` (gitignored). Like `regrade.py`, it carries an `EXPECTED` block and refuses to write when a rerun disagrees unless `--force` — the report quotes these numbers. Since Act-3 the block has 16 keys: the totals, `page_grade_digest` (`20855b3bc05d906b`), the quoted case/moved/unmatched/fallback counts the digest alone cannot see, `kw_pages_digest` / `case_pages_digest` (which pages each keyword and each accident case landed on — a hit can move page without changing any grade), `hybrid_lines` (1,575) and `hybrid_emptied_marker_pages` (must stay 0), and `nogap_*` inside `alignment_overall`. `check_expected()` compares every key outside the structured ones verbatim, so a key added to `EXPECTED` is guarded without touching the checker. `--limit` (debug) refuses to write into the tracked output or the default map directory. Since 2026-09-06 marker books also get `hybrid_pages()`: where two consecutive markers are ≥ 2 pages apart (the converter skipped a marker) the lines in between take the DP page instead of collapsing onto the previous marker page, monotone within the gap. The gap's DP values are first shifted down by however far the first body line's DP runs ahead of the marker page (anchor correction): the marker is direct evidence that its line sits on page N, and without the shift 17 marker pages ended up with zero lines (pre-ship review F1) — `hybrid_emptied_marker_pages` counts exactly that. `meta` also records `md_corpus_sha256` (name + sha256 of the 84 markdown files used) and the `python` / `pymupdf` versions, so a rerun that disagrees can be traced to its inputs. Result (Act-3): 1,847 → 2,189 pages, 등급3 108 (5.8%) → 145 (6.6%); the dashboards, README and the researcher's report publish these numbers, and `summary.json`'s `ncs` page-level block plus `ncs_pages.csv` stay as the label-based provenance — see `docs/03-analysis/resegment-results.analysis.md` §3.6/§6 and `docs/02-design/features/resegment-publish.design.md` §2.
- `recount_grades.py` — reads the two source workbooks in `data/`, remaps both to the unified grade scheme, aggregates **per unique page** (not per keyword hit), and writes `docs/03-analysis/data/{ncs_pages.csv, txt_pages.csv, summary.json}`. Flags: `--data`, `--out`, `--force`. It refuses to write when its built-in regression check fails; `--force` overrides that (use it only when the source data legitimately changed and you are about to update `EXPECTED`). Unlike the scripts above it takes no hardcoded absolute path — `--data` defaults to `data/` next to the script.

These still have **hardcoded absolute paths** (`EXCEL_PATH`, `NCS_BASES`, `DEFAULT_NCS_DIRS`) — edit the constants before running. (The downloaders no longer do; see `DOWNLOAD_ROOT` above.)

### 3. Regrade & coding validation (research track, nothing published)

`recount_grades.py` re-maps the grades the source workbook already carries. This group throws that column away and recomputes the grade from the page text, then tries to check the result against independent coding. The re-coding results are in `docs/03-analysis/recoding-results.analysis.md` (538 pages, three coders: `claude-opus-5` via `claude -p`, and `gpt-5.6-sol` twice; the headline pair is Claude vs OpenAI, so FR-1 is met; the gap analysis is `recoding.analysis.md`). **None of it feeds the dashboards.** `docs/*.html` publish `resegment.py`'s page-level numbers (since 2026-09-06) and `recount_grades.py`'s row-level counts; the regrade/coding variants below are research-facing — see `TODOS.md` P2 before touching any of this.

- `regrade.py` — recomputes the safety grade from the `페이지전체내용` column instead of trusting the workbook's 등급. The rule was reverse-engineered from the 4,000+ committed `등급사유` strings and reproduces the first-seen row's grade on 99.6% (1,839/1,847) of pages — this whole track counts the workbook's 1,847 label pages, not the 2,189 re-segmented ones, so its page figures are not comparable to the dashboards' without saying so. The defect fixes toggle independently so each one's impact can be read alone: D1 word boundaries (`HOMONYM_CONTEXTS`, `CONTAINING`), D2 length normalisation, D4 threshold discretisation (`DISCRETIZE`), D5 conditional exemption (`ACTION_EXEMPT`, hypothesis rejected — code kept for reproduction, default off). Flags: `--data`, `--validate` (reproduction rate only, writes nothing), `--force`. Writes `docs/03-analysis/data/regrade_impact.json` and, like `recount_grades.py`, refuses to write when its `EXPECTED` check misses. `EXPECTED` pins `baseline_digest` as well as the totals, so a page-to-page reassignment that leaves the distribution flat still fails. `V 어휘 확장` / `D1+D2+V` are the 21-term vocabulary extension (`EXTRA_SAFETY_TERMS` / `EXTRA_ACTION_TERMS`, `extra_vocab=True`) — a **variant only**; putting the terms into the base lists would break the 99.6% reproduction. The search that produced the 21 terms and their measured effect (등급3 108 → 129 pages) is `docs/03-analysis/vocab-search.analysis.md`. `variant_grid()` owns every variant label; the other scripts import it rather than retyping labels. Real-data runs need an interpreter with `openpyxl` installed (the harness does not — it stubs the module).
- `make_coding_sheet.py` — builds the 538-page, four-stratum coding sample as the **union** of two vocabulary definitions (current dictionary and +21 terms), so one set of labels scores every rule variant and the vocabulary decision itself: `disputed` 44 (either rule pair disagrees, census), `control` 85 (any variant says 등급3, census — the baseline without which you cannot tell "the coder is stingy about 등급3" from "the corrected rule is right"), `boundary` 109 (현행 2 → D1+D2 1, census), `recall` 300 random from the remaining 1,609 pages. Writes `coding_sheet.json` / `coding_sheet.md` (coder-facing, gitignored) and `coding_key.json` (answer key, tracked; carries per-item `pred` for every variant plus `population`, `rule_pairs`, `seed`). Rules the file enforces: the sheet carries **no** grade, count, group, or reason (anchoring); the coder instructions live only in `coder_prompt()` and are shipped inside the sheet JSON so the human `.md` and the API coder see the same string; it **never truncates** — long pages are split into `CHUNK_CHARS` pieces that concatenate back to the original, because the scorer reads the full 32,767-char cell. Pages the source workbook already truncated get an explicit notice (also as `notice` in the JSON), otherwise the coder reads the missing tail as "no measures". It refuses to overwrite an existing `coding_key.json` unless `--force` is given: the key is the only thing binding the `coding_A/B/C.json` labels to pages, and the digest guard only blocks *scoring* mismatched labels, not overwriting the key.
- `code_pages.py` — one-item-per-call coder over any OpenAI-compatible `/chat/completions` (stdlib only). Reads key/URL/model from an env file (`--provider-env`: `AUDIT_LLM_*` first, else a preset by key-variable name such as `GEMINI_API_KEY`), never the temperature (default 0, never inherited from `auditagent`'s 1.0). Coder B uses `~/.config/auditagent/.env`, coder A `.env.local`; both are gitignored. Labels are made only when the reply contains exactly one standalone `1`/`2`/`3`/`?` and no stray `?` (a hedged `3?` is not a label); anything else lands in `errors`. Writes `coding_<coder>.json` atomically after every item; `--resume` skips graded items and refuses a different model, prompt, temperature, or seed (one file, one setting). Ten consecutive call failures stop the run (`MAX_CONSECUTIVE_FAILURES`) so a bad key or model name does not burn 538 items of retries; the file on disk stays resumable. Models that reject `temperature`/`seed` are re-asked without the parameter and the fact is recorded in `meta`. Retryable failures (429/5xx/timeouts) wait for the server's `Retry-After` when it sends one, otherwise a backoff plus jitter. `--workers N` consumes completions as they finish and writes after each, so a slow item never holds finished (paid) results off disk. The file holds **no** grade definition — the harness scans its source for one. Everything it writes into the tracked `coding_<coder>.json` is public: error strings are scrubbed (key tokens, home paths) and capped at 200 chars, replies longer than 200 chars are truncated with a sha256 left behind, `provider_env` is recorded with `~` instead of the home directory, and the base URL must be https (plain http only for localhost, i.e. LM Studio). A provider-neutral `AUDIT_LLM_API_KEY` without `AUDIT_LLM_BASE_URL` is refused rather than defaulting to OpenAI. `--backend claude-cli` runs `claude -p` once per item for a Claude-family coder with no API key (it uses the logged-in Claude Code's OAuth); it forces `--setting-sources ""`, `--tools ""`, `--strict-mcp-config`, `--no-chrome` and a cwd outside the repo. Without `--strict-mcp-config` the user's MCP tool definitions (48k–118k tokens, measured) were injected into the coder's context, and without `--setting-sources ""` this file (which states the grading rule) would be. Claude Code adds one Haiku side call per item that also sees the item text; it is stored under `raw[id].side_calls` and never counted as the coder.
- `score_coding.py` — scores the two coders against each other and against every rule variant. With the new key format (`population` + per-item `pred`) it takes the census path: per-variant precision with no sample weighting (every page any variant calls 등급3 is in the sample — `check_population()` verifies that against `regrade_impact.json` and stops otherwise), recall measured for the first time from the `recall` stratum with an exact hypergeometric interval (`missed_interval`, exact combinatorics via `math.comb`; 0 hits → upper bound only; `ALPHA = 0.05` is the single source of every "95%" string), a coder-disagreement band on precision, input guards that refuse rather than mis-score — `normalize_labels()` accepts only `1`/`2`/`3`/`?` in int or string form (a hand-edited `"3"` must never score as neither-3-nor-1), `check_complete()` rejects a coder file with an item in neither `grades` nor `errors` (an interrupted run is not a `?`), both coders must share `prompt_sha256`, and an item whose `group` is outside `CODING_GROUPS` stops the run instead of silently dropping out of every denominator — and `family_guard()` which prints an FR-1 warning when both coders resolve to the same model family (`model_family()`: host → family, `claude-cli://anthropic` counts as Anthropic, and on openrouter the `vendor/` prefix of the model name is the family). Old two-stratum keys still go through `main_legacy()`. `--coders C,B` picks which two `coding_<name>.json` files to score (default `A,B`); the census path writes `docs/03-analysis/data/recoding_scores.json` (NaN-free, with `coder_names` / `coder_files` so `R15q` knows which label files to triangulate) — `recoding-results.analysis.md` quotes numbers from that file, never from the console. `?` is a valid coder code (판단 불가) and drops out of numerator and denominator, so anything reading these labels must tolerate a non-1/2/3 value.

Two traps here:

- **`coding_sheet.json` / `.md` are gitignored; `coding_key.json` / `coding_A.json` / `coding_B.json` are tracked on purpose.** The first two carry commercial textbook body text. The key carries only 교재 / 페이지 / 군 / per-variant predicted grades, and the coder files only labels plus call metadata. A `/coding_*.json` wildcard once swept all five under the body-text rationale — do not re-add one. `.env` / `.env.local` (coder API keys) are gitignored too.
- **The 69-page labels behind κ 0.796 / 88.4% live in `docs/archive/2026-09/coding-v1/`, not at the root.** They predate the `sample_digest` guard, so `score_coding.py` stops on them with "구버전 산출물" — the guard is correct (re-running `make_coding_sheet.py` reshuffles item ids), and `TODOS.md` P2 rules those labels invalid anyway (the sheet leaked D1's homonym assumption to both coders). The root `coding_key.json` is the new 538-page key (digest `68a4575ffff0def9`); `coding_A.json` / `coding_B.json` / `coding_C.json` at the root are the three coder runs on that key (A·B `gpt-5.6-sol`, C `claude-opus-5`) and are tracked like the key.

## Safety Grading Scheme

Every page in the analysis corpus carries a grade. **The shipped scheme is:**

| 등급 | 뜻 | 원본 판정 근거 |
|:---:|---|---|
| **1** | 미흡·없음 | 안전 키워드 5건 이하 |
| **2** | 형식적 언급 | 안전 키워드 다수, 구체적 조치 없음 |
| **3** | 구체적 대책 | 안전 키워드 + 조치·대책 제시 |

The two source workbooks in `data/` disagree: the NCS one already uses this numbering, the textbook one is rotated by one (not reversed — `{1→2, 2→3, 3→1}` is a cycle). `recount_grades.py` remaps the textbook side so both land on the scheme above. `docs/03-analysis/grade-recount.analysis.md` §2 shows the evidence (grade-reason strings, 100% consistent per dataset).

Two rules that are easy to get wrong:

- **Grade is a page property, not a keyword-hit property.** Counting rows double-counts pages that many keywords land on, which systematically inflates the top grade — NCS 등급3 is 2,228 hits but only 145 real pages (label-based: 108). Always aggregate per unique (교재, 페이지).
- **When a page's rows disagree, take the lowest grade.** Majority voting loses: a buggy sheet records the same wrong verdict on several rows, and the duplicate count becomes votes. 12 NCS pages hit this.
- **16 NCS workbook "pages" hit Excel's 32,767-char cell limit — and they are not truncated pages, they are multi-page blocks.** The April search ran on markdown whose page markers were TOC-derived, so a workbook page label can cover 10–58 real pages; the 16 capped cells (등급3 12, 등급2 4) are the visible tip of that. `page_utils.is_cell_truncated()` still detects the cap (length **and** the trailing `...`) and `truncation_audit.py` still measures it, but the old reading — "an under-counting defect bounded to 등급3 ∈ [108, 112]" — is retired (audit C1, 2026-09-04). `resegment.py` re-places every hit on its real PDF page: 1,847 → 2,189 pages, 등급3 108 (5.8%) → 145 (6.6%) (Act-3, 2026-09-06). Never fold the cap per row: 1,376 rows carry a capped cell, 86× the label count.

⚠️ `docs/01-plan/features/safety-grading.plan.md` describes **older, conflicting** numbering (1 기본언급 / 2 구체적대책 / 3 관련없음). `feature-proposals.plan.md` has the same numbering as shipped but an old label for grade 2 ("기본 언급" → now "형식적 언급"). Both carry a banner and are kept for provenance. This section is authoritative.

## Testing

There is no test framework (no `package.json` / `pyproject.toml`). The project ships its own harnesses — all exit 0/1 and depend only on Node and the Python standard library.

```bash
node   outputs/test-search-equivalence.js   # 24 assertions — search equivalence, chunked render, lazy parse cache
node   outputs/test-dashboard-data.js       # 152 assertions — docs/ dashboard data + table render/sort
python3 outputs/test-recount-grades.py      # 372 assertions — recount_grades / regrade / coding-sheet / code_pages / scoring / truncation / resegment logic

python3 truncation_audit.py                 # not a test — re-measures truncation and checks it against EXPECTED (needs data/)

node   outputs/run-core-logic-tests.js       # 32 assertions — headless runner for test-core-logic.html
node   outputs/test-sri.js                  # 38 assertions — SRI on external scripts (--online to verify against the CDN)

# Or open it in a browser and read the tab title: "PASS: N/N tests passed"
open outputs/test-core-logic.html
```

All five run in CI on every push and pull request (`.github/workflows/test.yml`). The workflow installs nothing for the harnesses themselves; it installs `openpyxl` only for the last step, which checks that `recount_grades.py` exits with a readable message instead of a traceback when `data/` is absent (the default state of a fresh clone).

`test-core-logic.html` copies shared helper functions from the main app and runs assertions in-browser. When adding or changing heading detection / normalization logic, update both files and verify tests pass. `run-core-logic-tests.js` runs that same HTML headlessly (minimal DOM + `vm`, reads `document.title`) so CI can gate on it — it holds no copy of the assertions.

`test-search-equivalence.js` and `test-dashboard-data.js` load the real `<script>` blocks out of the HTML files via `vm` + a DOM mock, so they carry no copy-paste debt. `test-recount-grades.py` stubs `openpyxl` in `sys.modules` and monkeypatches `load_workbook` with a fake workbook, so it runs without pip packages and without the gitignored `data/` originals.

`test-dashboard-data.js` and `test-recount-grades.py` carry a `known()` helper for **known issues**: an assertion that documents a real defect, prints `⚠ KNOWN ISSUE` on every run, but does not fail the suite. Use it when you find a defect you are not fixing in the same change; promote the call back to `check()` once fixed. Currently zero known issues are outstanding.

The assertion counts in the block above are checked by the harnesses themselves: `D14` (dashboard) and `R17` (recount) read README's 테스트 block and this file's Testing block and fail when the cited number differs from the live count. Never edit those two numbers by hand — run the harness and copy what it prints, in both files.

For manual E2E testing, use `outputs/test-samples/` with sample `.md` files. For real-world testing with `_meta.json` files, use NCS 반도체 documents in `~/Documents/개발/pinecone_agent/documents/ncs/`.

## Test Coverage

**Minimum 60% / target 80%** of changed code paths must be covered by an automated harness before landing.

- New logic in `outputs/*.html` (search app) → extend `test-search-equivalence.js` or `test-core-logic.html`.
- New data or table/sort logic in `docs/*.html` (dashboards) → extend `test-dashboard-data.js`. Hardcoded data arrays must be cross-validated against `docs/03-analysis/data/summary.json` (row-level NCS counts, textbook) and `docs/03-analysis/data/reseg_summary.json` (NCS page-level: pages, grade distribution, per-area, per-keyword `pg`, accident-case pages), never asserted against themselves. `D13` is the reseg ↔ `index.html` / `textbook.html` 비교표 / `osha.html` / README / `ncs_pages_reseg.csv` block (per-area and per-book derived prose numbers included, plus a guard that the retired label-based 1,847 / 108 survive only inside a "no longer published" sentence); `D14` is the doc-cited assertion count.
- New logic in `recount_grades.py`, the regrade/coding-validation scripts (`regrade.py`, `make_coding_sheet.py`, `code_pages.py`, `score_coding.py`, `truncation_audit.py`, `resegment.py`), or the page-mapping utilities → extend `test-recount-grades.py`. `code_pages.py` takes its HTTP function as a parameter (`post=`) so the harness drives it with a fake; never add a real network call to the harness. Its groups are `R1`-`R7` recount, `R8` page markers, `R9`-`R11` regrade rules, `R12` truncation integrity, `R13` I/O and `main()` boundaries, `R14` sample fingerprint + regrade regression guards, `R15` recoding (vocab variant, 4-stratum union sample, `code_pages.py`, census + recall scoring), `R16` resegment (alignment DP, propagation, row→line matching, marker preference, marker-gap hybrid placement with the anchor correction — `R16z15`-`R16z21` — aggregation, I/O boundaries, `EXPECTED` guard, an end-to-end `main()` run on a fake `fitz` — fixtures only, no PDF), `R17` doc-cited assertion count.
- Paths that genuinely cannot be automated here (browser chart rendering, File System Access API, real `.xlsx` parsing) are documented as `[→E2E]` gaps in the PR body rather than silently skipped.

## Other Artifacts

- **Analysis dashboards** (`docs/`, GitHub Pages) — standalone single-file HTML dashboards using Chart.js 4.4.7 via CDN, independent of the search app:
  - `docs/index.html` — NCS 반도체 교재 안전보건 분석 (page-level numbers come from `reseg_summary.json` since 2026-09-06; row-level counts from `summary.json`)
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
- `docs/03-analysis/data/` — machine-readable outputs. `ncs_pages_reseg.csv` / `reseg_summary.json` are written by `resegment.py` (`EXPECTED`-guarded) and are the NCS page-level truth the dashboards publish since 2026-09-06 — the dashboards' `pg` column is validated against `reseg_summary.json.kw_pages`, and `per_book` carries each book's `hybrid_lines`. The rest is `recount_grades.py` output (label-based provenance for NCS, current for the textbook): `ncs_pages.csv` and `txt_pages.csv` are one row per unique (교재, 페이지) with its grade, grade reason, accident-case flag, and a `절단` flag (last column — keep it last so index-based readers do not shift); `summary.json` carries the aggregate counts plus `truncated_pages` / `truncated_page_g`, `kw_pages` (unique detected pages per keyword; for NCS this is the label-based value, provenance only) and `page_grade_digest` (a hash of the whole page→grade assignment, so a reassignment that leaves the totals unchanged still fails the regression check). `regrade_impact.json` is written by `regrade.py`, not `recount_grades.py`: it carries the reproduction rate, the per-variant grade distributions (including the `V 어휘 확장` / `D1+D2+V` rows), `adopted_variant`, and `baseline_digest`. `recoding_scores.json` is written by `score_coding.py`'s census path: coder metadata, per-stratum agreement, per-variant precision/recall with intervals, and the FR-1 family warning; `recoding_scores_AB.json` / `recoding_scores_CA.json` are the two secondary coder pairs written with `--out`, the headline file is C·B. **Neither `regrade_impact.json` nor `recoding_scores*.json` is published** — the dashboards read `reseg_summary.json` (NCS page level) and `summary.json` (row level, textbook) and nothing else. `score_coding.population()` (legacy two-stratum path) reads `regrade_impact.json` so the population figures are never typed in by hand; the census path cross-checks the same file through `check_population()`. `ncs_pages_reseg.csv` is one row per unique (교재, real PDF 쪽) with `상태` resolved/unresolved, `출처` (`text` / `text-fallback` / `label`), `md자수` / `pdf자수`, and `구라벨` as the last column; `reseg_summary.json` carries `alignment_check` (with the `nogap_*` self-check), `match_stats`, `label_fallback_pages`, `hybrid_lines`, `hybrid_emptied_marker_pages`, the three digests (`page_grade_digest`, `kw_pages_digest`, `case_pages_digest`) and `meta` (`expected` is `null` after a `--force` or `--limit` run; `md_corpus_sha256`, `python`, `pymupdf` say what produced it). The folder's own `README.md` is the provenance table — which file is the published truth and which is lineage.
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
