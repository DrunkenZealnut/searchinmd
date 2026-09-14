#!/usr/bin/env python3
"""의미 재검산 사전의 도메인 점검 — 표본·판정·정밀도·영향표 (semantic-expression-review).

사용법:
  python3 expression_review.py sample --ncs-root data_source/markdown/ncs --school-root data_source/markdown/school-text
  python3 code_pages.py --sheet data/expression_review_sheet.json --coder A --backend claude-cli --out docs/03-analysis/data/expression_review_A.json
  python3 code_pages.py --sheet data/expression_review_sheet.json --coder B --provider-env ~/.config/auditagent/.env --out docs/03-analysis/data/expression_review_B.json
  python3 expression_review.py score [--list-disagreements]
  python3 expression_review.py impact --ncs-root … --school-root … --source-workbook … [--school-grade-workbook …]

왜 있나: 재검산 사전(포함 75·보류 19)은 LLM 이 혼자 정했다(감사 M1·m3). 이 스크립트는 (1) 고빈도·의심 표현의 문맥
표본을 뽑아 코더 2계열이 "사람 안전·보건 뜻인가"를 판정하게 하고(시트는 본문이라 비추적, 키만 추적),
(2) 표현별 정밀도와 Clopper-Pearson 95% 구간을 계산해 하한 < PRECISION_FLOOR 를 보류/조건부 후보로 표시하며,
(3) 사전 v1 / v1fix / v2 의 총계·키워드·등급 영향표를 낸다. 정본(semantic_summary.json)은 건드리지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import score_coding
import semantic_keyword_recount as SKR
from semantic_keyword_recount import (
    Document, ExpressionRule, aggregate_matches, assign_match_grades, build_default_rules,
    default_candidate_decisions, load_documents, public_path, scan_document, select_ncs_documents,
)

HERE = Path(__file__).resolve().parent
SEED = 20260914
PER_EXPRESSION = 30
PRECISION_FLOOR = 0.8            # 연구책임자 결정 2026-09-14 — CP 95% 하한이 이 값 미만이면 보류/조건부 후보
SAMPLE_DICTIONARY = "v1fix"      # 표본은 점검 **전** 사전에서 뽑는다 — 점검 대상이 v1fix 의 포함 표현이고, 키 digest 9713a337… 는 이 버전으로 재현된다 (v2 채택 뒤에도 바뀌지 않는다)
ALPHA = score_coding.ALPHA       # 한 값 — 여기서 "95%" 가 나온다
LABELS = (1, 2, "?")             # 1 = 사람 안전·보건 뜻, 2 = 아님, ? = 판단 불가 (code_pages.parse_grade 가 읽는 값) — _norm 이 쓴다

# 점검 대상 (키워드, 표현) — 비정확 표현 중 정본 출현 ≥ 50 인 18개 + 감사 지목 4개 (계획 §1.3). 보류 표현은 계수 없이 probe 만.
REVIEW_TARGETS = (
    ("화학물질", "화학 물질"), ("화학물질", "케미컬"), ("인화", "가연성"), ("보호구", "장갑"), ("화학물질", "화학약품"),
    ("보건", "건강"), ("보호구", "방진복"), ("누출", "누설"), ("작업환경", "작업 환경"), ("물질안전보건자료", "물질 안전 보건 자료"),
    ("방사선", "X선"), ("부상", "화상"), ("보호구", "방진화"), ("유해인자", "유해요인"), ("보호구", "개인 보호 장비"),
    ("보호구", "보호안경"), ("보호구", "안전화"), ("보호구", "보호장구"),
    ("PSM", "PSM"), ("인화", "combustible"), ("인화", "발화성"), ("방사선", "자외선"),
)

DEFAULT_SHEET = HERE / "data" / "expression_review_sheet.json"
DEFAULT_KEY = HERE / "docs" / "03-analysis" / "data" / "expression_review_key.json"
DEFAULT_A = HERE / "docs" / "03-analysis" / "data" / "expression_review_A.json"
DEFAULT_B = HERE / "docs" / "03-analysis" / "data" / "expression_review_B.json"
DEFAULT_ADJ = HERE / "docs" / "03-analysis" / "data" / "expression_review_adj.json"
DEFAULT_SCORES = HERE / "docs" / "03-analysis" / "data" / "expression_review_scores.json"
DEFAULT_IMPACT = HERE / "docs" / "03-analysis" / "data" / "expression_review_impact.json"


# ---------------------------------------------------------------- 표본
@dataclass(frozen=True)
class ReviewRecord:
    """표본 후보 한 건 — MatchRecord 에 probe(보류 표현을 계수 없이 찾은 것) 표시를 얹은 것."""

    corpus: str
    relative_path: str
    keyword: str
    expression: str
    line: int
    matched_text: str
    probe: bool


def coder_prompt() -> str:
    """코더가 보는 지시문 전문. 판정 기준은 여기에만 있다 (시트에는 계층·근거·등급이 없다)."""
    return "\n".join([
        "각 항목은 반도체 교재 본문 세 줄(앞줄·해당 줄·뒷줄)이고, «…» 안이 판정 대상 표현입니다.",
        "이 문맥에서 그 표현이 **노동자의 안전·보건(사람의 위해·보호·건강)** 을 뜻하면 `1`,",
        "제품·공정·품질·계측·오염관리 등 **사람 안전이 아닌** 뜻이면 `2`, 판단할 수 없으면 `?` 만 답합니다.",
        "숫자나 물음표 하나만 답하고 설명은 붙이지 마십시오.",
    ])


def collect_records(documents: list[Document], targets=REVIEW_TARGETS, version: str = SAMPLE_DICTIONARY) -> list[ReviewRecord]:
    """대상 표현의 문맥 후보 전수. 포함 표현은 점검 대상 사전(version, 기본 v1fix)의 included 레코드, 보류 표현은 probe 규칙으로만 찾는다."""
    keywords = sorted({k for k, _ in targets})
    rules = build_default_rules(keywords, version=version)
    wanted = set(targets)
    candidates = {(c.keyword, c.expression): c for c in default_candidate_decisions(version=version)}
    probe_rules = [
        ExpressionRule(c.keyword, c.expression, c.tier, "probe", pattern=c.pattern, exclude_patterns=c.exclude_patterns)
        for (k, e), c in candidates.items() if (k, e) in wanted and c.decision != "included"
    ]
    out: list[ReviewRecord] = []
    for doc in documents:
        for r in scan_document(doc, rules):
            if r.decision == "included" and (r.keyword, r.expression) in wanted:
                out.append(ReviewRecord(r.corpus, r.relative_path, r.keyword, r.expression, r.line, r.matched_text, False))
        for rule in probe_rules:
            for r in scan_document(doc, [rule]):
                if r.decision == "included":
                    out.append(ReviewRecord(r.corpus, r.relative_path, r.keyword, r.expression, r.line, r.matched_text, True))
    out.sort(key=lambda r: (r.keyword, r.expression, r.corpus, r.relative_path, r.line))
    return out


def _allocate(per: int, counts: dict[str, int]) -> dict[str, int]:
    """말뭉치 비례 배분(최소 1, 합 = min(per, 전체))."""
    total = sum(counts.values())
    if total <= per:
        return dict(counts)
    alloc = {c: max(1, round(per * n / total)) if n else 0 for c, n in counts.items()}
    while sum(alloc.values()) > per:                       # 반올림으로 넘치면 가장 큰 층에서 뺀다
        big = max(alloc, key=lambda c: alloc[c]); alloc[big] -= 1
    while sum(alloc.values()) < per:
        big = max(counts, key=lambda c: counts[c] - alloc[c]); alloc[big] += 1
    return alloc


def build_sample(records: list[ReviewRecord], targets=REVIEW_TARGETS, seed: int = SEED, per_expression: int = PER_EXPRESSION) -> list[dict]:
    """표현별 층화 무작위 표본 — 결정론(seed). 표현당 per_expression 건, 그보다 적으면 전수."""
    rng = random.Random(seed)
    by_expr: dict[tuple[str, str], list[ReviewRecord]] = defaultdict(list)
    for r in records:
        by_expr[(r.keyword, r.expression)].append(r)
    items: list[dict] = []
    for target in targets:
        pool = by_expr.get(target, [])
        counts = Counter(r.corpus for r in pool)
        alloc = _allocate(per_expression, dict(counts))
        chosen: list[ReviewRecord] = []
        for corpus in sorted(counts):
            stratum = [r for r in pool if r.corpus == corpus]
            chosen.extend(stratum if alloc[corpus] >= len(stratum) else rng.sample(stratum, alloc[corpus]))
        chosen.sort(key=lambda r: (r.corpus, r.relative_path, r.line))
        for r in chosen:
            items.append({"keyword": r.keyword, "expression": r.expression, "corpus": r.corpus, "path": r.relative_path,
                          "line": r.line, "matched_text": r.matched_text, "probe": r.probe})
    for index, item in enumerate(items, start=1):
        item["id"] = f"E{index:03d}"
    return items


def window_text(document: Document, record, mark: str = "«{}»") -> str:
    """앞줄 + 매칭 줄(표현을 «…» 로 표시) + 뒷줄. 마커 줄·빈 줄은 뺀다."""
    lines = document.text.splitlines()
    line_no = record.line if hasattr(record, "line") else record["line"]                  # ReviewRecord 또는 표본 dict
    index = line_no - 1
    matched = record.matched_text if hasattr(record, "matched_text") else record["matched_text"]
    line = lines[index]
    pos = line.lower().find(matched.lower())
    marked = line[:pos] + mark.format(line[pos:pos + len(matched)]) + line[pos + len(matched):] if pos >= 0 else line
    out = []
    for i in (index - 1, index, index + 1):
        if i < 0 or i >= len(lines):
            continue
        text = marked if i == index else lines[i]
        if not text.strip() or SKR.PAGE_MARKER_RE.match(text):
            continue
        out.append(text.strip())
    return "\n".join(out)


def _under_tracked_docs(path: Path) -> bool:
    """docs/ 아래(추적) 인가 — 본문을 담는 파일의 경로 거부에 쓴다 (run_census 의 변형 경로 거부와 같은 규칙)."""
    return os.path.realpath(str(path)).startswith(os.path.realpath(str(HERE / "docs")) + os.sep)


def sample_digest(key_items: list[dict]) -> str:
    payload = [(i["id"], i["keyword"], i["expression"], i["corpus"], i["path"], i["line"], i["text_sha256"]) for i in key_items]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def sheet_and_key(items: list[dict], documents: list[Document] | None = None, seed: int = SEED, per_expression: int = PER_EXPRESSION, targets=REVIEW_TARGETS) -> tuple[dict, dict]:
    """시트(본문, 비추적)와 키(본문 없음, 추적). items 에 text 가 없으면 documents 에서 만든다."""
    doc_index = {(d.corpus, d.relative_path): d for d in (documents or [])}
    sheet_items, key_items = [], []
    for item in items:
        text = item.get("text")
        if text is None:
            doc = doc_index[(item["corpus"], item["path"])]
            text = window_text(doc, item)
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        sheet_items.append({"id": item["id"], "keyword": item["keyword"], "expression": item["expression"], "text": text})
        key_items.append({"id": item["id"], "keyword": item["keyword"], "expression": item["expression"], "corpus": item["corpus"],
                          "path": public_path(item["path"]) if os.path.isabs(item["path"]) else item["path"], "line": item["line"], "text_sha256": sha})
    digest = sample_digest(key_items)
    sheet = {"sample_digest": digest, "coder_prompt": coder_prompt(), "items": sheet_items}
    key = {"sample_digest": digest, "seed": seed, "per_expression": per_expression, "targets": [list(t) for t in targets], "items": key_items}   # 실제 사용한 값 (CLI --seed/--per-expression, 대상 표현)
    return sheet, key


def write_sample(items: list[dict], sheet_path: Path, key_path: Path, documents: list[Document] | None = None, force: bool = False,
                 seed: int = SEED, per_expression: int = PER_EXPRESSION, targets=REVIEW_TARGETS) -> dict:
    if _under_tracked_docs(sheet_path):
        raise ValueError(f"시트는 교재 본문을 담으므로 추적 경로(docs/)에 쓸 수 없습니다: {sheet_path.name}")
    """시트 json/md 와 키를 쓴다. 키는 라벨과 표본을 묶는 유일한 끈이라 --force 없이는 덮어쓰지 않는다."""
    sheet_path, key_path = Path(sheet_path), Path(key_path)
    if key_path.exists() and not force:
        raise FileExistsError(f"키가 이미 있습니다 — 표본을 다시 뽑으려면 --force: {public_path(key_path)}")
    if any("text" not in i for i in items) and documents is None:
        raise ValueError("documents 가 없으면 text 가 있는 items 만 쓸 수 있습니다")
    sheet, key = sheet_and_key(items, documents, seed=seed, per_expression=per_expression, targets=targets)
    sheet_path.parent.mkdir(parents=True, exist_ok=True); key_path.parent.mkdir(parents=True, exist_ok=True)
    sheet_path.write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = ["# 의미 표현 점검 시트", "", sheet["coder_prompt"], "", f"sample_digest: `{sheet['sample_digest']}` · 항목 {len(sheet['items'])}", ""]
    for it in sheet["items"]:
        md += [f"## {it['id']} — {it['keyword']} / {it['expression']}", "", it["text"], ""]
    sheet_path.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    key_path.write_text(json.dumps(key, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return key


# ---------------------------------------------------------------- 정밀도
def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def _bisect(f, lo: float = 0.0, hi: float = 1.0, iters: int = 60) -> float:
    for _ in range(iters):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def precision_interval(k: int, n: int, alpha: float = ALPHA) -> tuple[float, float]:
    """Clopper-Pearson 정확 이항 구간 (stdlib 만). k=0 → 하한 0, k=n → 상한 1."""
    if n <= 0 or not 0 <= k <= n:
        raise ValueError(f"k={k}, n={n}")
    # _bisect 는 p 에 대해 감소하는 f 의 영점을 찾는다: P(X ≥ k | p) 는 증가, P(X ≤ k | p) 는 감소
    lo = 0.0 if k == 0 else _bisect(lambda p: alpha / 2 - (1 - _binom_cdf(k - 1, n, p)))   # P(X ≥ k | p) = α/2 인 p
    hi = 1.0 if k == n else _bisect(lambda p: _binom_cdf(k, n, p) - alpha / 2)             # P(X ≤ k | p) = α/2 인 p
    return round(lo, 4), round(hi, 4)


def kappa(a: list, b: list, cats=(1, 2)) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def _norm(label):
    if label in LABELS:
        return label
    if label in ("1", "2"):
        return int(label)
    raise ValueError(f"라벨은 1·2·? 만 허용: {label!r}")


def final_labels(ids: list[str], a: dict, b: dict, adj: dict | None = None) -> dict:
    """일치 → 그 값; 불일치 → 재정 라벨이 있으면 그 값, 없으면 ?; 한쪽이 ? 면 ?."""
    adj = adj or {}
    out = {}
    for i in ids:
        la, lb = _norm(a.get(i, "?")), _norm(b.get(i, "?"))
        if la == lb:
            out[i] = la
        elif i in adj:
            out[i] = _norm(adj[i])
        else:
            out[i] = "?"
    return out


def validate_adj(adj: dict, key: dict) -> None:
    if adj.get("sample_digest") != key.get("sample_digest"):
        raise ValueError("재정 파일의 sample_digest 가 키와 다릅니다")
    ids = {i["id"] for i in key["items"]}
    for i, label in (adj.get("labels") or {}).items():
        if i not in ids:
            raise ValueError(f"키에 없는 항목: {i}")
        _norm(label)


def companion_stats(key: dict, texts: dict, labels: dict, companions=SKR.SAFETY_COMPANIONS) -> dict:
    """조건부 규칙(동반어)의 근거 — 동반어별 O/X 문맥 출현 수와, 표현별로 "동반어가 있는 창만 계수했을 때" 의 정밀도·유지율.
    시트 본문(texts) 은 계수에만 쓰이고 출력에는 숫자만 남는다. 창은 시트 문맥(앞줄·해당 줄·뒷줄) = 조건부 판정 창."""
    pats = {c: re.compile(c) for c in companions}
    per_comp = {c: {"o": 0, "x": 0} for c in companions}
    by_expr: dict[tuple[str, str], dict] = {}
    for item in key["items"]:
        text = texts.get(item["id"], "")
        label = _norm(labels.get(item["id"], "?"))
        hit = any(p.search(text) for p in pats.values())
        for c, p in pats.items():
            if label in (1, 2) and p.search(text):
                per_comp[c]["o" if label == 1 else "x"] += 1
        row = by_expr.setdefault((item["keyword"], item["expression"]), {"keyword": item["keyword"], "expression": item["expression"], "n": 0, "k": 0, "total_1": 0, "dropped_x": 0})
        if label == "?":
            continue
        row["total_1"] += label == 1
        if hit:
            row["n"] += 1
            row["k"] += label == 1
        elif label == 2:
            row["dropped_x"] += 1
    rows = []
    for row in by_expr.values():
        row["precision"] = round(row["k"] / row["n"], 4) if row["n"] else None
        row["kept_of_1"] = round(row["k"] / row["total_1"], 4) if row["total_1"] else None
        rows.append(row)
    return {"companions": per_comp, "expressions": rows}


def check_complete(coder: dict, ids: list[str], name: str) -> None:
    """코더 파일은 모든 항목을 grades 또는 errors 에 가져야 한다 — 중단된 실행은 ? 가 아니다 (score_coding.check_complete 규약)."""
    covered = set((coder.get("grades") or {})) | set((coder.get("errors") or {}))
    missing = [i for i in ids if i not in covered]
    if missing:
        raise ValueError(f"코더 {name} 파일에 항목 {len(missing)}개가 없습니다 (grades/errors 어디에도 없음): {', '.join(missing[:5])} — 중단된 실행이면 --resume 으로 마저 돌리십시오")


def score(key: dict, a: dict, b: dict, adj: dict | None = None, floor: float = PRECISION_FLOOR, alpha: float = ALPHA, texts: dict | None = None,
          adopted: str | None = None) -> dict:
    """표현별 정밀도·구간·κ·후보 표시. NaN 없음. texts(시트 id→본문) 가 있으면 조건부 규칙 근거(meta.companions, expressions[].conditional) 를 붙인다.
    adopted 는 연구책임자의 채택 결정(사전 버전) — 자동으로 정하지 않고 손으로 적는다(설계 §1 원칙 4)."""
    if adopted is not None and adopted not in SKR.DICTIONARY_VERSIONS:
        raise ValueError(f"adopted 는 {SKR.DICTIONARY_VERSIONS} 중 하나여야 합니다: {adopted!r}")
    tiers = {(c.keyword, c.expression): c.tier for c in SKR.default_candidate_decisions()}
    if adj:
        validate_adj(adj, key)
    adj_labels = (adj or {}).get("labels") or {}
    ids = [i["id"] for i in key["items"]]
    for name, coder in (("A", a), ("B", b)):
        if coder.get("sample_digest") is not None and coder.get("sample_digest") != key.get("sample_digest"):
            raise ValueError(f"코더 {name} 라벨의 sample_digest {coder.get('sample_digest')} 가 키 {key.get('sample_digest')} 와 다릅니다 — 다른 표본의 라벨")
    pa, pb = (a.get("meta") or {}).get("prompt_sha256"), (b.get("meta") or {}).get("prompt_sha256")
    if pa and pb and pa != pb:
        raise ValueError("두 코더의 prompt_sha256 이 다릅니다 — 같은 질문으로 판정한 라벨만 채점합니다")
    want = hashlib.sha256(coder_prompt().encode("utf-8")).hexdigest()
    if (pa or pb) and (pa or pb) != want:
        raise ValueError(f"코더 라벨의 질문(prompt_sha256 {(pa or pb)[:16]}…)이 지금의 coder_prompt()({want[:16]}…)와 다릅니다 — 질문이 바뀌었으면 다시 판정하십시오")
    check_complete(a, ids, "A"); check_complete(b, ids, "B")
    ga, gb = a.get("grades", {}), b.get("grades", {})
    final = final_labels(ids, ga, gb, adj_labels)
    by_expr: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in key["items"]:
        by_expr[(item["keyword"], item["expression"])].append(item)
    rows = []
    pairs_all = []
    for (keyword, expression), items in by_expr.items():
        labels = [final[i["id"]] for i in items]
        valid = [l for l in labels if l != "?"]
        n, k = len(valid), sum(1 for l in valid if l == 1)
        pa = [_norm(ga.get(i["id"], "?")) for i in items]; pb = [_norm(gb.get(i["id"], "?")) for i in items]
        both = [(x, y) for x, y in zip(pa, pb) if x != "?" and y != "?"]
        pairs_all.extend(both)
        disagreements = sum(1 for x, y in zip(pa, pb) if x != y)
        adjudicated = sum(1 for i in items if i["id"] in adj_labels)
        if n:
            lower, upper = precision_interval(k, n, alpha)
            precision = round(k / n, 4)
        else:
            lower = upper = precision = None
        candidate = None if n == 0 else ("keep" if lower >= floor else "hold_or_conditional")
        rows.append({"keyword": keyword, "expression": expression, "tier": tiers.get((keyword, expression), "exact" if keyword == expression else None), "n": n, "k": k, "precision": precision, "lower": lower, "upper": upper,
                     "kappa": kappa([x for x, _ in both], [y for _, y in both]), "candidate": candidate,
                     "disagreements": disagreements, "adjudicated": adjudicated, "unknown": len(labels) - n})
    rows.sort(key=lambda r: (r["candidate"] != "hold_or_conditional", r["lower"] if r["lower"] is not None else 2, r["expression"]))
    valid_all = [l for l in final.values() if l != "?"]
    overall = {"n": len(valid_all), "k": sum(1 for l in valid_all if l == 1),
               "precision": round(sum(1 for l in valid_all if l == 1) / len(valid_all), 4) if valid_all else None,
               "kappa": kappa([x for x, _ in pairs_all], [y for _, y in pairs_all]),
               "disagreements": sum(r["disagreements"] for r in rows), "adjudicated": len(adj_labels)}
    meta = {"sample_digest": key.get("sample_digest"), "coders": {"A": (a.get("meta") or {}).get("model"), "B": (b.get("meta") or {}).get("model")},
            "family_warning": score_coding.family_guard(a.get("meta"), b.get("meta")), "alpha": alpha, "floor": floor, "adopted": adopted}
    if texts is not None:
        stats = companion_stats(key, texts, final)
        meta["companions"] = {"patterns": list(SKR.SAFETY_COMPANIONS), "counts": stats["companions"]}
        cond = {(r["keyword"], r["expression"]): r for r in stats["expressions"]}
        for row in rows:
            c = cond[(row["keyword"], row["expression"])]
            row["conditional"] = {k: c[k] for k in ("n", "k", "precision", "kept_of_1", "dropped_x")}
    return {"meta": meta, "expressions": rows, "overall": overall}


# ---------------------------------------------------------------- 영향표
def impact(documents: list[Document], keywords: list[str], existing_grades: dict, versions=SKR.DICTIONARY_VERSIONS) -> dict:
    """세 사전 버전을 메모리에서 집계 — 총계·등급·키워드·표현별, 결함 수정이 걷어낸 건수. 쓰지 않는다."""
    sources = [SKR.KeywordSource(k, 0, True) for k in keywords]
    totals, grades, per_kw, per_expr, excluded_by_fix, excluded_by_v2 = {}, {}, defaultdict(dict), defaultdict(dict), {}, {}
    ascii_kw = {k for k in keywords if re.fullmatch(r"[A-Za-z0-9 ]+", k)}
    v_included = {}
    for v in versions:
        rules = build_default_rules(keywords, version=v)
        result = assign_match_grades(aggregate_matches(sources, documents, rules, default_candidate_decisions(version=v), with_summary=False), existing_grades)   # 요약 불필요 — 매칭만 (실행 시간 −40%)
        included = [r for r in result.matches if r.decision == "included"]
        v_included[v] = included
        totals[v] = {c: sum(1 for r in included if r.corpus == c) for c in ("NCS", "교과서")}
        grades[v] = {c: {g: sum(1 for r in included if r.corpus == c and r.grade == int(g)) for g in ("1", "2", "3")} for c in ("NCS", "교과서")}
        for k in keywords:
            per_kw[k][v] = {c: sum(1 for r in included if r.corpus == c and r.keyword == k) for c in ("NCS", "교과서")}
        for (k, e), n in Counter((r.keyword, r.expression) for r in included).items():
            per_expr[(k, e)][v] = n
        held_records = [r for r in result.matches if r.decision == "excluded" and r.reason == SKR.HELD_INSIDE_REASON]
        held_inside = Counter(r.corpus for r in held_records)
        # 보류 표현별 분리(계획 성공 기준: 안전성 / 안전 마진류 각각) — 제외 레코드의 문맥에서 _HELD_INSIDE 패턴을 순서대로 찾는다
        held_split = {c: Counter() for c in ("NCS", "교과서")}
        for r in held_records:
            for label, pat in zip(SKR.HELD_INSIDE_LABELS.get(r.keyword, ()), SKR._HELD_INSIDE.get(r.keyword, ())):
                if re.search(pat, r.context, re.IGNORECASE):
                    held_split[r.corpus][label] += 1
                    break
        if v == "v1fix" and "v1" in v_included:
            sub = {c: sum(1 for r in v_included["v1"] if r.corpus == c and r.keyword in ascii_kw and r.tier == "exact")
                      - sum(1 for r in included if r.corpus == c and r.keyword in ascii_kw and r.tier == "exact") for c in ("NCS", "교과서")}
            excluded_by_fix = {c: {"PSM_substring": sub[c], "held_inside": held_inside.get(c, 0),
                                   "안전성": held_split[c]["안전성"], "안전_마진류": held_split[c]["안전_마진류"]} for c in ("NCS", "교과서")}
        if v == "v2" and "v1fix" in v_included:
            # v2 가 걷어낸 것: 보류 전환된 표현의 v1fix 출현(held) + 조건부 표현에서 동반어 없이 떨어진 출현(no_companion).
            # no_companion 은 조건부 표현의 v1fix 포함 − v2 포함(실효 감소) — 제외 레코드 수는 v1fix 에서 더 긴 표현에 가려졌던 매칭까지 세어 몇 건 더 나온다.
            held_keys = {k for k, o in SKR._V2_OVERRIDES.items() if o.get("decision") == "held"}
            cond_keys = {k for k, o in SKR._V2_OVERRIDES.items() if o.get("require_patterns")}
            def _n(rows, c, keys):
                return sum(1 for r in rows if r.corpus == c and (r.keyword, r.expression) in keys)
            excluded_by_v2 = {c: {"held": _n(v_included["v1fix"], c, held_keys),
                                  "no_companion": _n(v_included["v1fix"], c, cond_keys) - _n(included, c, cond_keys)} for c in ("NCS", "교과서")}
    return {
        "meta": {"versions": list(versions), "documents": len(documents), "keywords": len(keywords), "corpus_sha256": SKR._document_set_sha256(documents),
                 "v2_overrides": {f"{k}:{e}": ("held" if o.get("decision") == "held" else "conditional") for (k, e), o in SKR._V2_OVERRIDES.items()}},
        "totals": totals, "grades": grades,
        "keywords": [{"name": k, **{v: per_kw[k].get(v, {"NCS": 0, "교과서": 0}) for v in versions}} for k in keywords],
        "expressions": [{"keyword": k, "expression": e, **{v: per_expr[(k, e)].get(v, 0) for v in versions}} for (k, e) in sorted(per_expr)],
        "excluded_by_fix": excluded_by_fix,
        "excluded_by_v2": excluded_by_v2,
    }


# ---------------------------------------------------------------- CLI
def _load_corpus(args) -> list[Document]:
    ncs, _ = select_ncs_documents(load_documents(Path(args.ncs_root), "NCS"))
    return ncs + load_documents(Path(args.school_root), "교과서")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="표본 시트(비추적)·키(추적) 생성")
    s.add_argument("--ncs-root", type=Path, required=True); s.add_argument("--school-root", type=Path, required=True)
    s.add_argument("--sheet", type=Path, default=DEFAULT_SHEET); s.add_argument("--key", type=Path, default=DEFAULT_KEY)
    s.add_argument("--seed", type=int, default=SEED); s.add_argument("--per-expression", type=int, default=PER_EXPRESSION)
    s.add_argument("--force", action="store_true")
    c = sub.add_parser("score", help="코더 A·B(+재정) → 정밀도·구간·κ")
    c.add_argument("--key", type=Path, default=DEFAULT_KEY); c.add_argument("--a", type=Path, default=DEFAULT_A); c.add_argument("--b", type=Path, default=DEFAULT_B)
    c.add_argument("--adj", type=Path, default=DEFAULT_ADJ); c.add_argument("--out", type=Path, default=DEFAULT_SCORES)
    c.add_argument("--floor", type=float, default=PRECISION_FLOOR); c.add_argument("--list-disagreements", action="store_true")
    c.add_argument("--sheet", type=Path, default=DEFAULT_SHEET, help="시트(본문) — 있으면 조건부 규칙 근거(동반어 O/X 계수) 를 붙인다. 출력에 본문은 남지 않는다")
    c.add_argument("--adopted", choices=SKR.DICTIONARY_VERSIONS, default=None, help="연구책임자가 채택한 사전 버전 — meta.adopted 에 기록 (결정 3: v2)")
    i = sub.add_parser("impact", help="사전 v1/v1fix/v2 영향표")
    i.add_argument("--ncs-root", type=Path, required=True); i.add_argument("--school-root", type=Path, required=True)
    i.add_argument("--source-workbook", type=Path, required=True); i.add_argument("--school-grade-workbook", type=Path)
    i.add_argument("--out", type=Path, default=DEFAULT_IMPACT)
    args = ap.parse_args()

    if args.cmd == "sample":
        docs = _load_corpus(args)
        records = collect_records(docs, REVIEW_TARGETS)
        items = build_sample(records, REVIEW_TARGETS, seed=args.seed, per_expression=args.per_expression)
        key = write_sample(items, args.sheet, args.key, documents=docs, force=args.force, seed=args.seed, per_expression=args.per_expression, targets=REVIEW_TARGETS)
        counts = Counter((it["keyword"], it["expression"]) for it in items)
        print(f"표본 {len(items)}건, 표현 {len(counts)}개, digest {key['sample_digest']}")
        for (k, e), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {k}:{e} {n}")
    elif args.cmd == "score":
        key = json.loads(args.key.read_text(encoding="utf-8"))
        a = json.loads(args.a.read_text(encoding="utf-8")); b = json.loads(args.b.read_text(encoding="utf-8"))
        adj = json.loads(args.adj.read_text(encoding="utf-8")) if args.adj.exists() else None
        if args.list_disagreements:
            ga, gb = a.get("grades", {}), b.get("grades", {})
            adj_labels = (adj or {}).get("labels") or {}
            print("id\tkeyword\texpression\tA\tB\tadj")
            for it in key["items"]:
                la, lb = ga.get(it["id"], "?"), gb.get(it["id"], "?")
                if str(la) != str(lb):
                    print(f"{it['id']}\t{it['keyword']}\t{it['expression']}\t{la}\t{lb}\t{adj_labels.get(it['id'], '')}")
            return
        texts = None
        if args.sheet.exists():
            sheet = json.loads(args.sheet.read_text(encoding="utf-8"))
            if sheet.get("sample_digest") != key.get("sample_digest"):
                sys.exit(f"시트 digest {sheet.get('sample_digest')} 가 키 {key.get('sample_digest')} 와 다릅니다 — 동반어 계수를 붙일 수 없습니다")
            texts = {it["id"]: it["text"] for it in sheet["items"]}
        out = score(key, a, b, adj, floor=args.floor, texts=texts, adopted=args.adopted)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"전체 정밀도 {out['overall']['precision']} (n={out['overall']['n']}), κ {out['overall']['kappa']}, 불일치 {out['overall']['disagreements']}")
        if out["meta"].get("family_warning"):
            print(out["meta"]["family_warning"])
        for r in out["expressions"]:
            cond = r.get("conditional")
            extra = f"  조건부 {cond['k']}/{cond['n']} (O 유지 {cond['kept_of_1']}, X 탈락 {cond['dropped_x']})" if cond else ""
            print(f"  {r['candidate'] or '-':20} {r['keyword']}:{r['expression']} {r['k']}/{r['n']} [{r['lower']}, {r['upper']}] κ={r['kappa']}{extra}")
        if texts is None:
            print("(시트가 없어 조건부 규칙 근거는 붙이지 않았습니다)")
    elif args.cmd == "impact":
        docs = _load_corpus(args)
        keywords = list(SKR.EXPECTED_KEYWORDS)
        school = args.school_grade_workbook or args.source_workbook.parent / SKR.DEFAULT_SCHOOL_GRADE_WORKBOOK_NAME
        existing = SKR.load_existing_grades(args.source_workbook, school)
        out = impact(docs, keywords, existing)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for v in out["meta"]["versions"]:
            g = out["grades"][v]["NCS"]; tot = sum(g.values())
            print(f"{v:6} NCS {out['totals'][v]['NCS']:,} (등급3 {g['3']:,} = {g['3'] / tot * 100:.1f}%) · 교과서 {out['totals'][v]['교과서']:,}")
        print("결함 수정이 걷어낸 것:", out["excluded_by_fix"])


if __name__ == "__main__":
    main()
