# TODOS

## Add page markers to PDF-to-markdown pipeline
- **Why**: Eliminates the 200-line DP page mapping heuristic. Strategy 1 (`<!-- page: N -->` markers) already handles this perfectly.
- **Context**: User controls the upstream converter. Once all documents have markers, `buildPageMapping` Strategy 2 (TOC matching + DP) becomes dead code and can be removed.
- **Depends on**: Access to the PDF-to-markdown converter codebase (separate repo).

## Add LLM fallback indicator to search results
- **Why**: When `extractSentencesWithLLM` fails and falls back to rule-based, the user sees no indication. Mixed-quality results are a data integrity issue.
- **Context**: Currently the fallback is `console.warn` only. Add a visual badge or file-level indicator showing which analysis method was used.
- **Depends on**: Nothing.
