#!/usr/bin/env python3
"""occurrence_real_pages_impact.py — 블록 기준(사전 v2, 2026-09-14 정본) vs 실제 쪽 기준(2026-09-15 정본) 영향표.

같은 코퍼스·같은 사전으로 두 번 집계한다: (A) 표식 블록 기준 = 줄→쪽 대응 없이 워크북 라벨 상속 + 블록 텍스트 판정(옛 정본 방식),
(B) 실제 쪽 기준 = 대응 적용 + 실제 쪽 본문 판정. 총계는 같아야 하고(매칭은 표식 블록 위에서), 등급만 옮겨 간다.
(A) 가 옛 정본(BLOCK_BASIS_V2)과 다르면 계보가 끊긴 것이므로 멈춘다. 산출물은 docs/03-analysis/data/occurrence_real_pages_impact.json —
본문·절대 경로 없음. 정본 산출물은 쓰지 않는다(semantic_keyword_recount.py 의 몫).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import semantic_keyword_recount as SKR
from page_utils import DENSE_MARKER_RATIO

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "docs" / "03-analysis" / "data" / "occurrence_real_pages_impact.json"
BLOCK_BASIS_V2 = {                                             # 2026-09-14 정본(블록 기준, summary_sha256 834a8aa5…) — (A) 가 이 값과 같아야 계보가 선다
    "NCS": {"1": 4378, "2": 4614, "3": 2525},
    "교과서": {"1": 633, "2": 459, "3": 115},
}
REAL_MARKER_RATIO = DENSE_MARKER_RATIO                         # 블록 수 / 실제 쪽 수 ≥ 0.8 이면 "표식이 실제 쪽" 교재 (계획 §1.3) — resegment.py 의 마커 밀도 문턱과 같은 값 (page_utils)
WIDTH_BUCKETS = ((1, "1"), (3, "2-3"), (9, "4-9"), (math.inf, "10+"))   # 출현이 놓인 블록이 걸친 실제 쪽 폭 → 구간 — 판정과 출력 순서가 같은 표


def _width_bucket(width: int) -> str:
    return next(label for limit, label in WIDTH_BUCKETS if width <= limit)


def _key(record: SKR.MatchRecord) -> tuple:
    return (record.corpus, record.relative_path, record.line, record.keyword, record.expression, record.matched_text)


def _grade_counts(records) -> dict[str, int]:
    counts = Counter(record.grade for record in records)
    return {"1": counts[1], "2": counts[2], "3": counts[3]}


def book_methods(reseg: dict) -> dict[str, str]:
    """이전 기준 per_book.method (markers / alignment) → {LM 코드: method} — 대응을 표식으로 만들었는지 DP 정렬로 만들었는지의 출처."""
    out: dict[str, str] = {}
    for name, info in (reseg.get("per_book") or {}).items():
        match = SKR._NCS_CODE_RE.search(name)
        method = (info or {}).get("method")
        if match and isinstance(method, str):
            out[match.group(0).upper()] = method
    return out


def book_kind(document: SKR.Document, page_maps: dict[str, tuple[int, ...]], methods: dict[str, str] | None = None) -> str:
    """real-marker(표식이 실제 쪽) / toc-block(목차 블록) / real-marker-nomap(대응 없는 목록 교재).

    대응을 만든 이전 기준이 그 교재의 방법(per_book.method: markers / alignment)을 말하면 그것이 분류다 — 비율(블록 수 / 대응의 실제 쪽 수 ≥ 0.8)은
    method 를 모르는 교재의 대체 규칙 (적대적 리뷰 1: 비율은 DP 정렬 교재 2권을 "표식이 실제 쪽" 에 넣었다)."""
    line_pages = page_maps.get(document.relative_path)
    if line_pages is None:
        return "real-marker-nomap"
    method = (methods or {}).get(SKR._document_code(document) or "")
    if method in ("markers", "alignment"):
        return "real-marker" if method == "markers" else "toc-block"
    blocks = sum(1 for block in SKR.split_pages(document) if block.page is not None)
    real_pages = len(set(line_pages))
    return "real-marker" if real_pages and blocks / real_pages >= REAL_MARKER_RATIO else "toc-block"


def compute_impact(documents: list[SKR.Document], keywords: list[str], existing_grades: dict, page_maps: dict[str, tuple[int, ...]],
                   block_reference: dict | None = BLOCK_BASIS_V2, dictionary: str = SKR.DEFAULT_DICTIONARY, methods: dict[str, str] | None = None) -> dict:
    sources = [SKR.KeywordSource(k, 0, True) for k in keywords]
    rules = SKR.build_default_rules(keywords, version=dictionary)
    candidates = SKR.default_candidate_decisions(version=dictionary)
    ungraded = SKR.aggregate_matches(sources, documents, rules, candidates, with_summary=False)      # 스캔은 한 번(7.9 s) — 대응은 page 만 덧씌운다 (리뷰 performance)
    block = SKR.assign_match_grades(ungraded, existing_grades)
    real = SKR.assign_match_grades(replace(ungraded, matches=tuple(SKR.apply_page_maps(list(ungraded.matches), page_maps))), existing_grades, page_maps=page_maps)
    a_list = [r for r in block.matches if r.decision == "included"]
    b_list = [r for r in real.matches if r.decision == "included"]
    if len(a_list) != len(b_list) or any(_key(x) != _key(y) for x, y in zip(a_list, b_list)):     # 불변식: apply_page_maps 는 매칭을 바꾸지 않는다 — 같은 줄의 같은 표현이 여럿이라 위치로 짝짓는다
        raise ValueError(f"두 집계의 매칭 순서·집합이 다릅니다 (블록 {len(a_list)} vs 실제 쪽 {len(b_list)}) — 대응은 매칭을 바꾸면 안 된다")
    corpora = ("NCS", "교과서")
    grades_a = {c: _grade_counts(r for r in a_list if r.corpus == c) for c in corpora}
    grades_b = {c: _grade_counts(r for r in b_list if r.corpus == c) for c in corpora}
    if block_reference is not None:
        bad = [c for c in corpora if grades_a[c] != block_reference[c]]
        if bad:
            raise ValueError(f"블록 기준 집계가 옛 정본과 다릅니다({', '.join(bad)}): {grades_a} ≠ {block_reference} — 계보가 끊겼다(사전·코퍼스·워크북을 확인)")
    kinds = {d.relative_path: book_kind(d, page_maps, methods) for d in documents if d.corpus == "NCS"}
    transition = Counter(); by_source = defaultdict(Counter); by_kind = defaultdict(lambda: {"block": Counter(), "real": Counter(), "occurrences": 0})
    per_keyword = defaultdict(lambda: {"block": Counter(), "real": Counter()}); per_group = defaultdict(lambda: {"block": Counter(), "real": Counter()})
    pages_a, pages_b = set(), set()
    occ_by_doc: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))   # 문서 → 블록 쪽 → 출현 줄 (블록 폭 표, 한 번만 모은다)
    for ra, rb in zip(a_list, b_list):
        if ra.corpus != "NCS":
            continue
        transition[(ra.grade, rb.grade)] += 1
        by_source[ra.grade_source][rb.grade == ra.grade] += 1
        kind = kinds[ra.relative_path]
        by_kind[kind]["block"][ra.grade] += 1; by_kind[kind]["real"][rb.grade] += 1; by_kind[kind]["occurrences"] += 1
        per_keyword[ra.keyword]["block"][ra.grade] += 1; per_keyword[ra.keyword]["real"][rb.grade] += 1
        group = SKR._dashboard_group("NCS", ra.relative_path)
        per_group[group]["block"][ra.grade] += 1; per_group[group]["real"][rb.grade] += 1
        pages_a.add((ra.relative_path, ra.page)); pages_b.add((rb.relative_path, rb.page))
        occ_by_doc[ra.relative_path][ra.page].append(ra.line)
    # 출현이 놓인 블록의 실제 쪽 폭
    span = Counter()
    for document in documents:
        line_pages = page_maps.get(document.relative_path) if document.corpus == "NCS" else None
        if line_pages is None:
            continue
        occ_lines = occ_by_doc.get(document.relative_path, {})
        for block in SKR.split_pages(document):
            if block.page is None or block.page not in occ_lines:
                continue
            width = len({line_pages[i - 1] for i in range(block.start_line, block.start_line + len(block.lines)) if i - 1 < len(line_pages)})
            span[_width_bucket(width)] += len(occ_lines[block.page])
    ncs_total = sum(grades_a["NCS"].values())
    moved = sum(v for (x, y), v in transition.items() if x != y)
    return {
        "meta": {"dictionary": dictionary, "unit": "occurrences", "corpus_note": "NCS 만 이동 — 교과서는 표식이 실제 쪽이라 불변",
                 "block_reference": block_reference,
                 "book_kind_rule": f"previous basis per_book.method (markers → real-marker, alignment → toc-block); fallback blocks / distinct real pages >= {REAL_MARKER_RATIO}; no map → real-marker-nomap"},
        "totals": {c: sum(grades_b[c].values()) for c in corpora},
        "grades": {"block": grades_a, "real": grades_b},
        "grade3_share": {c: {"block": round(100 * grades_a[c]["3"] / max(1, sum(grades_a[c].values())), 1), "real": round(100 * grades_b[c]["3"] / max(1, sum(grades_b[c].values())), 1)} for c in corpora},
        "transition": {"unchanged": ncs_total - moved, "moved": moved, "matrix": {f"{x}->{y}": transition[(x, y)] for x in (1, 2, 3) for y in (1, 2, 3) if x != y}},
        "by_source": {src: {"occurrences": sum(c.values()), "unchanged": c[True], "unchanged_pct": round(100 * c[True] / sum(c.values()), 1)} for src, c in sorted(by_source.items())},
        "by_book_kind": {kind: {"books": sum(1 for k in kinds.values() if k == kind), "occurrences": v["occurrences"],
                                "block": {str(g): v["block"][g] for g in (1, 2, 3)}, "real": {str(g): v["real"][g] for g in (1, 2, 3)}} for kind, v in sorted(by_kind.items())},
        "keywords": [{"name": k, "block": {str(g): per_keyword[k]["block"][g] for g in (1, 2, 3)}, "real": {str(g): per_keyword[k]["real"][g] for g in (1, 2, 3)}} for k in keywords],
        "groups": {g: {"block": {str(x): v["block"][x] for x in (1, 2, 3)}, "real": {str(x): v["real"][x] for x in (1, 2, 3)}} for g, v in sorted(per_group.items())},
        "pages": {"block_pages": len(pages_a), "real_pages": len(pages_b), "block_width_of_occurrences": {label: span[label] for _, label in WIDTH_BUCKETS}},
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-workbook", type=Path, required=True)
    parser.add_argument("--ncs-root", type=Path, required=True)
    parser.add_argument("--school-root", type=Path, required=True)
    parser.add_argument("--school-grade-workbook", type=Path)
    parser.add_argument("--page-maps", type=Path, required=True)
    parser.add_argument("--previous-basis", type=Path, default=SKR.HERE / SKR.PREVIOUS_BASIS_SOURCE, help="reseg_summary.json — 대응의 결속(마크다운 판·PDF 쪽수)·교재 분류(per_book.method)·정렬 자기 검증 수치의 출처 (기본: 추적 파일)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    sources = SKR.read_keyword_workbook(args.source_workbook)
    keywords = [s.keyword for s in sources]
    ncs, _ = SKR.select_ncs_documents(SKR.load_documents(args.ncs_root, "NCS"))
    documents = ncs + SKR.load_documents(args.school_root, "교과서")
    school = args.school_grade_workbook or args.source_workbook.parent / SKR.DEFAULT_SCHOOL_GRADE_WORKBOOK_NAME
    existing = SKR.load_existing_grades(args.source_workbook, school)
    page_maps, info = SKR.load_page_maps(args.page_maps, ncs)
    if not Path(args.previous_basis).is_file():                                            # 잘못 적은 경로가 결속을 조용히 건너뛰지 않는다 (적대적 리뷰 12)
        raise FileNotFoundError(f"이전 기준 reseg_summary.json 이 없습니다: {SKR.public_path(args.previous_basis)} — 대응의 결속·교재 분류·정렬 자기 검증의 출처")
    reseg = json.loads(Path(args.previous_basis).read_text(encoding="utf-8"))
    SKR.check_page_maps_against_previous_basis(Path(args.previous_basis), ncs, page_maps, SKR.pdf_pages_from_previous_basis(Path(args.previous_basis)))   # 정본 실행과 같은 결속 (Codex 구조 리뷰 P2)
    out = compute_impact(documents, keywords, existing, page_maps, block_reference=BLOCK_BASIS_V2, methods=book_methods(reseg))
    out["meta"].update({
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "git": SKR._git_info(),
        "inputs": {"source_workbook": SKR._file_sha256(args.source_workbook), "school_grade_workbook": SKR._file_sha256(school),
                   "ncs_markdown": SKR._document_set_sha256(ncs), "page_maps": info.as_manifest()},
    })
    if reseg.get("alignment_check"):                                                       # 정렬 오차는 이전 기준과 같은 대응의 것 — 그 자기 검증 수치를 병기 (계획 §5)
        check = (reseg.get("alignment_check") or {}).get("overall") or {}
        out["meta"]["alignment_self_check"] = {"source": SKR.public_path(args.previous_basis), "books": (reseg.get("alignment_check") or {}).get("books"),
                                               **{k: check.get(k) for k in ("lines", "exact", "near", "all_lines", "all_exact", "all_near", "nogap_lines", "nogap_exact", "nogap_near")},
                                               "hybrid_lines": reseg.get("hybrid_lines"), "note": "DP 후보 줄 exact/near(±1쪽) — 대응의 정확도, 이 영향표의 실제 쪽 배정도 같은 오차를 가진다"}
    SKR._write_text_atomic(args.out, json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    g = out["grades"]; t = out["transition"]
    print(f"NCS 블록 기준 {g['block']['NCS']} → 실제 쪽 기준 {g['real']['NCS']} · 등급3 비율 {out['grade3_share']['NCS']['block']}% → {out['grade3_share']['NCS']['real']}% · 이동 {t['moved']:,}건 {t['matrix']}")
    print(f"→ {SKR.public_path(args.out)}")


if __name__ == "__main__":
    main()
