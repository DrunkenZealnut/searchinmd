# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

The entire application lives in a single file: `outputs/markdown-search-app.html` (~1960 lines of embedded HTML + CSS + JavaScript). There is no build system, bundler, or package manager.

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

- **XLSX (SheetJS) 0.18.5** loaded via CDN — the only external dependency
- **Python 3 standard library** for the dev server (no pip packages)
- **LM Studio** (optional) — local LLM server on port 1234 for hybrid search

## Testing

```bash
# Open in browser to run core logic unit tests (isHeadingLine, isStandaloneTitle, normalizeHeading, NFC)
open outputs/test-core-logic.html
# Check browser title: "PASS: N/N tests passed" or "FAIL: ..."
```

`test-core-logic.html` copies shared helper functions from the main app and runs assertions in-browser. When adding or changing heading detection / normalization logic, update both files and verify tests pass.

For manual E2E testing, use `outputs/test-samples/` with sample `.md` files. For real-world testing with `_meta.json` files, use NCS 반도체 documents in `/Users/zealnutkim/Documents/개발/pinecone_agent/documents/ncs/`.

## Other Artifacts

- `docs/index.html` — NCS 반도체 안전보건 분석 대시보드 (GitHub Pages로 배포, Chart.js + XLSX.js 사용). 검색 앱과 별도의 독립 HTML 파일.
- `docs/01-plan/`, `docs/02-design/`, `docs/03-analysis/`, `docs/04-report/` — feature PDCA documents

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
