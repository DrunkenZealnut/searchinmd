# Semantic Keyword Recount Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible semantic recount workbook and report for 30 independent keywords across all 98 Markdown files.

**Architecture:** A single Python command reads workbook metadata, loads an explicit expression-rule registry, scans normalized Markdown while preserving source coordinates, aggregates results, and writes XLSX/Markdown artifacts. Pure matching and aggregation functions remain independent from file I/O so they can be tested with the standard library; `openpyxl` is used only at the workbook boundaries.

**Tech Stack:** Python 3.14, standard library (`dataclasses`, `re`, `unicodedata`, `hashlib`, `pathlib`, `zipfile`, `unittest`), `openpyxl` 3.1.x

**Spec:** `docs/superpowers/specs/2026-09-08-semantic-keyword-recount-design.md`

## Global Constraints

- Keep all 30 existing keywords independent; do not merge or cross-expand them.
- Reject any new expression assigned to more than one keyword.
- Scan exactly `data/markdown/ncs/**/*.md` and `data/markdown/school-text/**/*.md`.
- Preserve input files and create new outputs under `data/`.
- Separate raw exact, excluded homonym, valid exact, equivalent, and specific-expression counts.
- Every accepted match must retain corpus, relative path, line, page marker, actual text, tier, and context.

---

### Task 1: Corpus and workbook readers

**Files:**
- Create: `semantic_keyword_recount.py`
- Create: `test_semantic_keyword_recount.py`

**Interfaces:**
- Produces: `read_keyword_workbook(path) -> list[KeywordSource]`, `load_documents(root, corpus) -> list[Document]`, `split_pages(document) -> list[PageBlock]`

- [x] Write failing tests proving that a headerless first row is counted as data, a named header is excluded, Unicode filenames normalize to NFC, and page markers propagate to following lines.
- [x] Run `python3 -m unittest -v test_semantic_keyword_recount.py` and confirm failures are caused by missing interfaces.
- [x] Implement immutable source records and the minimal readers.
- [x] Re-run the focused tests and the existing 32 JavaScript tests.

### Task 2: Independent semantic rule engine

**Files:**
- Modify: `semantic_keyword_recount.py`
- Modify: `test_semantic_keyword_recount.py`

**Interfaces:**
- Produces: `ExpressionRule`, `validate_rules(keywords, rules)`, `scan_document(document, rules) -> list[Match]`

- [x] Write failing tests for longest-match behavior inside one keyword, English case folding, spacing/punctuation variants, exact homonym exclusion (`부상하고 있는`), and rejection of cross-keyword expressions.
- [x] Run focused tests and confirm each fails for the intended missing behavior.
- [x] Implement rule validation and matching with original line/page coordinates.
- [x] Re-run tests; refactor only after green.

### Task 3: Corpus-derived expression registry and aggregation

**Files:**
- Modify: `semantic_keyword_recount.py`
- Modify: `test_semantic_keyword_recount.py`

**Interfaces:**
- Produces: `RULES`, `REVIEW_CANDIDATES`, `aggregate_matches(...)`, `audit_candidates(...)`

- [x] Write failing tests that every keyword has an exact rule, each added expression has one owner and rationale, candidate decisions are one of included/held/excluded/not-found, and summary totals equal detail totals.
- [x] Build candidate-context inventory from all 98 Markdown files and review every ambiguous candidate occurrence.
- [x] Encode accepted, held, excluded, and not-found expressions with corpus evidence.
- [x] Run full unit tests and rule-registry validation.

### Task 4: Workbook and Markdown report writers

**Files:**
- Modify: `semantic_keyword_recount.py`
- Modify: `test_semantic_keyword_recount.py`

**Interfaces:**
- Produces: `write_workbook(result, path)`, `write_report(result, path)`, `artifact_manifest(result)`

- [x] Write failing tests for required sheet names, frozen headers, readable widths, workbook reopenability, report sections, and source/rule/detail hashes.
- [x] Implement styled XLSX sheets and the Korean Markdown report.
- [x] Re-run focused tests and inspect workbook dimensions and formulas programmatically.

### Task 5: Full census and independent verification

**Files:**
- Create: `data/semantic_keyword_recount_20260909.xlsx`
- Create: `data/semantic_keyword_recount_20260909_report.md`
- Create: `docs/03-analysis/semantic-keyword-recount.analysis.md`

**Interfaces:**
- Consumes: CLI `python semantic_keyword_recount.py --source-workbook ... --ncs-root ... --school-root ... --xlsx-out ... --report-out ...`

- [x] Run the full command against 30 keywords, 89 NCS files, and 9 textbook files.
- [x] Generate a second copy in a temporary directory and compare rule/detail/summary hashes.
- [x] Run `python3 -m unittest -v test_semantic_keyword_recount.py`, existing JavaScript tests, `unzip -t` on the XLSX, and an independent workbook reopen/read audit.
- [x] Compare implementation against every approved design requirement and write the analysis note.
- [x] Do not commit automatically; preserve the user's existing dirty branch and report only the new files.
