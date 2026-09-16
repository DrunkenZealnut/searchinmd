"""hwpx_methods_bridge.py — 기초보고서 HWPX 2단계(제2장 5절 연구 방법 · 제3장 2절 4) 집계 기준 연결)의 **사실과 문장**.

`hwpx_results_refresh.py` 가 1단계(제3장 1~3절) 뒤 같은 XML 트리에서 이 모듈의 사실(`MethodsFacts`·`BridgeFacts`)과
템플릿(`methods_paragraphs`·`bridge_paragraphs`·표 행·목차 항목)으로 문단·표를 만든다. 여기에는 XML 이 없다 — 숫자를 어디서
읽고 문장을 어떻게 만드는지만 있다(feature hwpx-methods-bridge-refresh, 설계 §3.2·§3.5·§3.7).

규칙: 보고서에 들어가는 숫자는 전부 추적 파일에서 읽는다(손으로 적는 숫자 0). 추적 파일에 없는 값은 문장에서 뺀다(D3).
날짜는 정본 manifest 의 ISO 문자열만 쓴다. 이 모듈은 `hwpx_results_refresh` 를 import 하지 않는다(순환 방지) — 그쪽이
`fmt`/`pct` 를 여기서 가져간다.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from page_utils import BASELINE, EXCEL_MAX_CHARS

HERE = Path(__file__).resolve().parent
DATA = HERE / "docs" / "03-analysis" / "data"
REPO_URL = "github.com/DrunkenZealnut/searchinmd"          # 6) 재현성 — 숫자가 없는 상수
CODER_FAMILY = {"claude": "Claude", "gpt": "GPT"}          # 코더 id 접두 → 계열 라벨. 모르는 접두는 id 그대로 — 두 자리 이상 숫자가 들어가면 숫자 감사가 멈춰 눈에 띈다(한 자리는 허용 토큰이라 못 잡는다: 새 계열은 여기에 등록한다)
BRIDGE_SAME_PP = 0.5                                       # 등급 비율 변화가 이 이하(%p)면 "거의 같았다"
BRIDGE_LEVEL_PP = 1.0                                      # 쪽 단위 등급 3 비율이 이전 기준과 이 이하로 다르면 "같은 수준"
CONSERVATIVE_RECALL = 50                                   # 재현율 상한(%)이 이 미만이면 "등급 3 은 보수적 판정" 문장
METHODS_HEADINGS = (" 1) 자료 정제", " 2) 의미 표현 사전", " 3) 쪽 배치: 실제 PDF 쪽 대응", " 4) 쪽 등급 판정", " 5) 집계 단위", " 6) 재현성과 한계")
BRIDGE_HEADING = " 4) 집계 기준의 변경과 이전 결과와의 관계"
CONCLUSION_HEADING_OLD, CONCLUSION_HEADING_NEW = " 4) 소결", " 5) 소결"
NCS_GROUP_TO_AREA = {"반도체개발": "개발", "반도체제조": "제조", "반도체장비": "장비", "반도체재료": "재료"}   # 정본 그룹명 → 보고서 분야명 (hwpx_results_refresh 가 여기서 가져간다 — 한 정의)
NCS_GROUP_ORDER = tuple(NCS_GROUP_TO_AREA)                  # 보고서의 분야 순서 = 대응표의 삽입 순서
KOREAN_COUNT = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯"}   # "N 차례" 의 우리말 수사 (그 밖은 숫자)


def fmt(n: int) -> str:
    return f"{n:,}"


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "0.0%"


def range_text(lo_hi: tuple[int, int]) -> str:
    lo, hi = lo_hi
    return f"{lo}%" if lo == hi else f"{lo}~{hi}%"


@dataclass(frozen=True)
class MethodsPaths:
    summary: Path = DATA / "semantic_summary.json"
    impact: Path = DATA / "occurrence_real_pages_impact.json"
    reseg_summary: Path = DATA / "reseg_summary.json"
    reseg_csv: Path = DATA / "ncs_pages_reseg.csv"
    regrade_impact: Path = DATA / "regrade_impact.json"
    recoding_scores: Path = DATA / "recoding_scores.json"
    review_key: Path = DATA / "expression_review_key.json"
    review_scores: Path = DATA / "expression_review_scores.json"
    review_impact: Path = DATA / "expression_review_impact.json"
    recount_summary: Path = DATA / "summary.json"
    coding_key: Path = HERE / "coding_key.json"               # 규칙 검증 표본의 키 — recoding_scores 의 sample_digest 를 여기에 묶는다


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


NEW_FIELDS_HINT = " — 2026-09-16 이후 산출물(hwpx-methods-bridge-refresh)이 필요합니다"   # 이 기능이 새로 넣은 키(영향표 pages.*, 정본 grade_sources 등)에만 붙이는 힌트


def _get(obj, dotted: str, file: Path, hint: str = ""):
    """중첩 키를 읽는다 — 없으면 어느 파일의 어느 키인지 말한다(hint 는 새 필드일 때만: 다른 파일의 키 누락은 파일이 잘못된 것이지 오래된 것이 아니다)."""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise ValueError(f"{Path(file).name} 에 {dotted} 가 없습니다{hint}")
    return cur


def _grades(d: dict, file: Path, key: str) -> dict[int, int]:
    g = _get(d, key, file)
    return {k: int(g[str(k)]) for k in (1, 2, 3)}


def coder_family(coder_id: str) -> str:
    return CODER_FAMILY.get(str(coder_id).split("-")[0].lower(), str(coder_id))


@dataclass(frozen=True)
class MethodsFacts:
    """제2장 5절이 말하는 사실 — 필드 주석은 출처 키(설계 §3.2)."""
    dedup_books: int                      # summary meta.run.dedup (len)
    keyword_names: tuple                  # summary keywords[].name
    marker_books: int                     # summary meta.run.real_page_marker_books (len)
    page_maps: int                        # summary meta.run.page_maps.files
    inputs: int                           # summary meta.run.inputs (len)
    review_targets: int                   # expression_review_key targets (len)
    review_per_expression: int            # expression_review_key per_expression
    review_items: int                     # expression_review_key items (len)
    review_n: int                         # expression_review_scores overall.n
    review_agree: int                     # overall.n − overall.disagreements
    review_disagreements: int             # overall.disagreements
    review_kappa: float                   # overall.kappa
    review_alpha: float                   # meta.alpha
    review_floor: float                   # meta.floor
    review_coders: tuple                  # meta.coders A, B
    review_adjudicated: int               # overall.adjudicated — 재정된 불일치 수 (disagreements 와 다르면 문장이 갈린다)
    review_family_warning: str | None     # meta.family_warning — 두 코더가 같은 계열이면 문자열 (FR-1)
    review_versions: tuple                # expression_review_impact meta.versions — 사전 판 계보 (v1 → v1fix → v2)
    recoding_family_warning: str | None   # recoding_scores family_warning — 규칙 검증 코더 계열 (FR-1)
    held: tuple                           # expression_review_impact meta.v2_overrides == held (표현)
    conditional: tuple                    # … == conditional (표현)
    totals_v1fix: dict                    # expression_review_impact totals.v1fix
    totals_v2: dict                       # totals.v2
    max_label_width: int                  # ncs_pages_reseg.csv — 한 (교재, 구라벨) 이 덮은 실제 쪽 수의 최댓값
    truncated_pages: int                  # summary.json ncs.truncated_pages
    excel_max_chars: int                  # page_utils.EXCEL_MAX_CHARS
    align_books: int                      # reseg alignment_check.books
    align_lines: int                      # reseg alignment_check.overall.lines
    align_exact: int                      # …overall.exact
    align_near: int                       # …overall.near
    safety_min: int                       # regrade_impact rule.safety_min
    action_min: int                       # rule.action_min
    repro_pages: int                      # regrade_impact reproduction.total
    repro_agree: int                      # reproduction.agree
    sample_pages: int                     # recoding_scores population.strata (sum)
    census_pages: int                     # strata disputed + control + boundary
    recall_pages: int                     # strata.recall
    recall_pool: int                      # population.recall_pool
    precision: tuple                      # recoding_scores <coder>.variants.baseline.precision (코더 순)
    recall: tuple                         # … .recall
    repo_url: str = REPO_URL

    def precision_range(self) -> tuple[int, int]:
        vals = sorted(round(100 * p) for p in self.precision)
        return vals[0], vals[-1]

    def recall_range(self) -> tuple[int, int]:
        vals = sorted(round(100 * r) for r in self.recall)
        return vals[0], vals[-1]

    def value_pairs(self) -> list[tuple[str, str]]:
        m = self
        pairs = [
            (str(m.dedup_books), "run.dedup(count)"), (str(len(m.keyword_names)), "keywords(count)"), (str(m.marker_books), "run.real_page_marker_books(count)"),
            (str(m.page_maps), "run.page_maps.files"), (str(m.inputs), "run.inputs(count)"),
            (str(m.review_targets), "expression_review_key.targets(count)"), (str(m.review_per_expression), "expression_review_key.per_expression"), (fmt(m.review_items), "expression_review_key.items(count)"),
            (fmt(m.review_n), "expression_review_scores.overall.n"), (fmt(m.review_agree), "expression_review_scores.overall.n-disagreements"), (pct(m.review_agree, m.review_n), "expression_review_scores.overall.(n-disagreements)/n"),
            (f"{m.review_kappa:.3f}", "expression_review_scores.overall.kappa"), (str(m.review_disagreements), "expression_review_scores.overall.disagreements"),
            (str(m.review_adjudicated), "expression_review_scores.overall.adjudicated"), (str(len(m.review_versions) - 1), "expression_review_impact.meta.versions(count-1)"),
            (str(round(100 * (1 - m.review_alpha))), "expression_review_scores.meta.alpha(ci%)"), (f"{m.review_floor:g}", "expression_review_scores.meta.floor"),
            (str(len(m.held)), "expression_review_impact.meta.v2_overrides(held count)"), (str(len(m.conditional)), "expression_review_impact.meta.v2_overrides(conditional count)"),
            (fmt(m.max_label_width), "ncs_pages_reseg.csv(구라벨 max pages)"), (fmt(m.truncated_pages), "summary.json ncs.truncated_pages"), (fmt(m.excel_max_chars), "page_utils.EXCEL_MAX_CHARS"),
            (str(m.align_books), "reseg alignment_check.books"), (fmt(m.align_lines), "reseg alignment_check.overall.lines"),
            (pct(m.align_exact, m.align_lines), "reseg alignment_check.overall.exact/lines"), (pct(m.align_near, m.align_lines), "reseg alignment_check.overall.near/lines"),
            (pct(m.align_lines - m.align_near, m.align_lines), "reseg alignment_check.overall.(lines-near)/lines"),
            (str(m.safety_min), "regrade_impact.rule.safety_min"), (str(m.safety_min - 1), "regrade_impact.rule.safety_min-1"), (str(m.action_min), "regrade_impact.rule.action_min"), (str(m.action_min - 1), "regrade_impact.rule.action_min-1"),
            (fmt(m.repro_pages), "regrade_impact.reproduction.total"), (fmt(m.repro_agree), "regrade_impact.reproduction.agree"), (pct(m.repro_agree, m.repro_pages), "regrade_impact.reproduction.agree/total"),
            (fmt(m.sample_pages), "recoding_scores.population.strata(sum)"), (fmt(m.census_pages), "recoding_scores.population.strata(disputed+control+boundary)"),
            (fmt(m.recall_pages), "recoding_scores.population.strata.recall"), (fmt(m.recall_pool), "recoding_scores.population.recall_pool"),
        ]
        for v in m.precision_range():
            pairs.append((str(v), f"recoding_scores.*.variants.{BASELINE}.precision(round%)"))
        for v in m.recall_range():
            pairs.append((str(v), f"recoding_scores.*.variants.{BASELINE}.recall(round%)"))
        for version, totals in (("v1fix", m.totals_v1fix), ("v2", m.totals_v2)):
            for corpus, value in totals.items():
                pairs.append((fmt(value), f"expression_review_impact.totals.{version}.{corpus}"))
        return pairs


@dataclass(frozen=True)
class BridgeFacts:
    """제3장 2절 4) 이 말하는 사실 — 블록 기준 ↔ 실제 쪽 기준 ↔ 쪽 단위 이전 기준."""
    run_date: str                         # summary meta.run.generated_at[:10]
    total: int                            # impact totals.NCS
    block_grades: dict                    # impact grades.block.NCS
    real_grades: dict                     # impact grades.real.NCS
    block_pages: int                      # impact pages.block_pages
    real_pages: int                       # impact pages.real_pages
    moved: int                            # impact transition.moved
    unchanged: int                        # transition.unchanged
    matrix: dict                          # transition.matrix
    groups: dict                          # impact groups[name] → (block 등급3, real 등급3)
    existing_occurrences: int             # impact by_source.existing.occurrences
    existing_kept_pct: float              # by_source.existing.unchanged_pct
    real_page_grades: dict                # impact pages.real_page_grades
    school_detected: int                  # impact pages.교과서.detected_pages
    school_page_grades: dict              # pages.교과서.page_grades
    prev_date: str                        # summary meta.previous_basis.date
    prev_pages: int                       # previous_basis.pages (== reseg pages)
    prev_page_g: dict                     # previous_basis.page_g (== reseg page_g)
    prev_rows: int                        # reseg meta.rows
    shared_pages: int                     # summary meta.run.reseg_agreement.pages
    shared_agree: int                     # reseg_agreement.agree

    def value_pairs(self) -> list[tuple[str, str]]:
        b = self
        pairs = [(fmt(b.total), "impact.totals.NCS"), (fmt(b.block_pages), "impact.pages.block_pages"), (fmt(b.real_pages), "impact.pages.real_pages"),
                 (fmt(b.moved), "impact.transition.moved"), (pct(b.moved, b.total), "impact.transition.moved/total"), (fmt(b.unchanged), "impact.transition.unchanged"),
                 (fmt(b.existing_occurrences), "impact.by_source.existing.occurrences"), (f"{b.existing_kept_pct:.1f}%", "impact.by_source.existing.unchanged_pct"),
                 (fmt(b.school_detected), "impact.pages.교과서.detected_pages"), (fmt(b.prev_pages), "previous_basis.pages"), (fmt(b.prev_rows), "reseg.meta.rows"),
                 (fmt(b.shared_pages), "run.reseg_agreement.pages"), (fmt(b.shared_agree), "run.reseg_agreement.agree"), (pct(b.shared_agree, b.shared_pages), "run.reseg_agreement.agree/pages")]
        for g in (1, 2, 3):
            pairs += [(fmt(b.block_grades[g]), f"impact.grades.block.NCS.{g}"), (pct(b.block_grades[g], b.total), f"impact.grades.block.NCS.{g}/total"),
                      (fmt(b.real_grades[g]), f"impact.grades.real.NCS.{g}"), (pct(b.real_grades[g], b.total), f"impact.grades.real.NCS.{g}/total"),
                      (fmt(abs(b.real_grades[g] - b.block_grades[g])), f"impact.grades.real-block.NCS.{g}"),
                      (fmt(b.real_page_grades[g]), f"impact.pages.real_page_grades.{g}"), (pct(b.real_page_grades[g], b.real_pages), f"impact.pages.real_page_grades.{g}/real_pages"),
                      (fmt(b.school_page_grades[g]), f"impact.pages.교과서.page_grades.{g}"),
                      (fmt(b.prev_page_g[g]), f"previous_basis.page_g.{g}"), (pct(b.prev_page_g[g], b.prev_pages), f"previous_basis.page_g.{g}/pages")]
        for key, value in b.matrix.items():
            pairs.append((fmt(value), f"impact.transition.matrix.{key}"))
        for name, (block3, real3) in b.groups.items():
            pairs += [(fmt(block3), f"impact.groups.{name}.block.3"), (fmt(real3), f"impact.groups.{name}.real.3")]
        return pairs


def load_methods_facts(paths: MethodsPaths = MethodsPaths(), summary: dict | None = None) -> MethodsFacts:
    summary = summary if summary is not None else _load(paths.summary)
    run = _get(summary, "meta.run", paths.summary)
    key = _load(paths.review_key); scores = _load(paths.review_scores); review_impact = _load(paths.review_impact)
    reseg = _load(paths.reseg_summary); regrade = _load(paths.regrade_impact); recoding = _load(paths.recoding_scores); recount = _load(paths.recount_summary)
    overrides = _get(review_impact, "meta.v2_overrides", paths.review_impact)
    held = tuple(k.split(":", 1)[1] for k, v in overrides.items() if v == "held")
    conditional = tuple(k.split(":", 1)[1] for k, v in overrides.items() if v == "conditional")
    strata = _get(recoding, "population.strata", paths.recoding_scores)
    coders = _get(recoding, "coder_names", paths.recoding_scores)
    baseline = [_get(recoding, f"{c}.variants.{BASELINE}", paths.recoding_scores) for c in coders]
    overall = _get(scores, "overall", paths.review_scores)
    n, disagreements = int(_get(overall, "n", paths.review_scores)), int(_get(overall, "disagreements", paths.review_scores))
    # 계보 가드 — 5절이 인용하는 다른 실행의 산출물이 지금의 정본과 같은 계보인지 (레드팀: 문장 하나가 두 실행을 섞으면 감사도 못 잡는다)
    corpora_totals = {c: int(_get(summary, f"corpora.{c}.total", paths.summary)) for c in ("NCS", "교과서")}
    totals_v2 = {c: int(v) for c, v in _get(review_impact, "totals.v2", paths.review_impact).items()}
    if totals_v2 != corpora_totals:
        raise ValueError(f"{Path(paths.review_impact).name} 의 totals.v2({totals_v2}) 가 정본 corpora.*.total({corpora_totals}) 과 다릅니다 — 같은 실행의 파일이 아닙니다")
    if _get(scores, "meta.sample_digest", paths.review_scores) != _get(key, "sample_digest", paths.review_key):
        raise ValueError(f"{Path(paths.review_scores).name} 의 meta.sample_digest 가 {Path(paths.review_key).name} 의 sample_digest 와 다릅니다 — 다른 표본의 점수")
    if _get(scores, "meta.adopted", paths.review_scores) != _get(run, "dictionary", paths.summary):
        raise ValueError(f"{Path(paths.review_scores).name} 의 meta.adopted({scores['meta']['adopted']}) 가 정본 사전({run.get('dictionary')}) 과 다릅니다")
    if int(_get(recoding, "population.pages", paths.recoding_scores)) != int(_get(regrade, "reproduction.total", paths.regrade_impact)):
        raise ValueError(f"{Path(paths.recoding_scores).name} 의 population.pages 가 {Path(paths.regrade_impact).name} 의 reproduction.total 과 다릅니다 — 다른 워크북의 검증")
    versions = tuple(_get(review_impact, "meta.versions", paths.review_impact))
    if len(versions) < 2 or versions[-1] != _get(run, "dictionary", paths.summary):
        raise ValueError(f"{Path(paths.review_impact).name} 의 meta.versions({versions}) 가 개정 계보가 아니거나 마지막 판이 정본 사전({run.get('dictionary')})이 아닙니다")
    coding_key = _load(paths.coding_key)
    if _get(recoding, "sample_digest", paths.recoding_scores) != _get(coding_key, "sample_digest", paths.coding_key):
        raise ValueError(f"{Path(paths.recoding_scores).name} 의 sample_digest 가 {Path(paths.coding_key).name} 과 다릅니다 — 다른 표본의 점수 (Codex 적대적 리뷰: 쪽 수만으로는 못 묶는다)")
    widths = Counter()
    csv_rows = 0
    with open(paths.reseg_csv, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "구라벨" not in reader.fieldnames or "교재" not in reader.fieldnames:
            raise ValueError(f"{Path(paths.reseg_csv).name} 에 구라벨/교재 열이 없습니다")
        for row in reader:
            csv_rows += 1
            for label in (row["구라벨"] or "").split(";"):
                if label.strip():
                    widths[(row["교재"], label.strip())] += 1
    if not widths:
        raise ValueError(f"{Path(paths.reseg_csv).name} 에 구라벨 값이 없습니다")
    if csv_rows != int(_get(reseg, "pages", paths.reseg_summary)):
        raise ValueError(f"{Path(paths.reseg_csv).name} 의 행 수({csv_rows})가 {Path(paths.reseg_summary).name} 의 pages({reseg.get('pages')}) 와 다릅니다 — 다른 실행의 CSV")
    return MethodsFacts(
        dedup_books=len(_get(run, "dedup", paths.summary) or []), keyword_names=tuple(_get(k, "name", paths.summary) for k in _get(summary, "keywords", paths.summary)),
        marker_books=len(_get(run, "real_page_marker_books", paths.summary) or []), page_maps=int(_get(run, "page_maps.files", paths.summary)), inputs=len(_get(run, "inputs", paths.summary)),
        review_targets=len(_get(key, "targets", paths.review_key)), review_per_expression=int(_get(key, "per_expression", paths.review_key)), review_items=len(_get(key, "items", paths.review_key)),
        review_n=n, review_agree=n - disagreements, review_disagreements=disagreements, review_kappa=float(_get(overall, "kappa", paths.review_scores)),
        review_alpha=float(_get(scores, "meta.alpha", paths.review_scores)), review_floor=float(_get(scores, "meta.floor", paths.review_scores)),
        review_coders=(str(_get(scores, "meta.coders.A", paths.review_scores)), str(_get(scores, "meta.coders.B", paths.review_scores))),
        review_adjudicated=int(_get(overall, "adjudicated", paths.review_scores)), review_family_warning=_get(scores, "meta.family_warning", paths.review_scores),
        review_versions=versions, recoding_family_warning=_get(recoding, "family_warning", paths.recoding_scores),
        held=held, conditional=conditional, totals_v1fix=dict(_get(review_impact, "totals.v1fix", paths.review_impact)), totals_v2=totals_v2,
        max_label_width=max(widths.values()), truncated_pages=int(_get(recount, "ncs.truncated_pages", paths.recount_summary)), excel_max_chars=EXCEL_MAX_CHARS,
        align_books=int(_get(reseg, "alignment_check.books", paths.reseg_summary)), align_lines=int(_get(reseg, "alignment_check.overall.lines", paths.reseg_summary)),
        align_exact=int(_get(reseg, "alignment_check.overall.exact", paths.reseg_summary)), align_near=int(_get(reseg, "alignment_check.overall.near", paths.reseg_summary)),
        safety_min=int(_get(regrade, "rule.safety_min", paths.regrade_impact)), action_min=int(_get(regrade, "rule.action_min", paths.regrade_impact)),
        repro_pages=int(_get(regrade, "reproduction.total", paths.regrade_impact)), repro_agree=int(_get(regrade, "reproduction.agree", paths.regrade_impact)),
        sample_pages=sum(int(v) for v in strata.values()), census_pages=sum(int(strata[k]) for k in strata if k != "recall"), recall_pages=int(_get(strata, "recall", paths.recoding_scores)),
        recall_pool=int(_get(recoding, "population.recall_pool", paths.recoding_scores)),
        precision=tuple(float(_get(v, "precision", paths.recoding_scores)) for v in baseline), recall=tuple(float(_get(v, "recall", paths.recoding_scores)) for v in baseline),
    )


def load_bridge_facts(paths: MethodsPaths = MethodsPaths(), summary: dict | None = None) -> BridgeFacts:
    summary = summary if summary is not None else _load(paths.summary)
    impact = _load(paths.impact); reseg = _load(paths.reseg_summary)
    run = _get(summary, "meta.run", paths.summary); prev = _get(summary, "meta.previous_basis", paths.summary)
    ncs = _get(summary, "corpora.NCS", paths.summary); school = _get(summary, "corpora.교과서", paths.summary)
    # 계보 가드 — 다른 실행의 영향표·이전 기준을 섞지 않는다
    if int(_get(impact, "totals.NCS", paths.impact)) != int(ncs["total"]):
        raise ValueError(f"영향표 totals.NCS({impact['totals']['NCS']}) ≠ 정본 corpora.NCS.total({ncs['total']}) — 같은 실행의 파일이 아닙니다")
    if _grades(impact, paths.impact, "grades.real.NCS") != {k: int(ncs["grades"][str(k)]) for k in (1, 2, 3)}:
        raise ValueError("영향표 grades.real.NCS 가 정본 corpora.NCS.grades 와 다릅니다")
    if _get(impact, "meta.inputs.page_maps.sha256", paths.impact) != _get(run, "page_maps.sha256", paths.summary):
        raise ValueError("영향표의 대응표 지문(meta.inputs.page_maps.sha256)이 정본 run.page_maps.sha256 과 다릅니다")
    if int(_get(impact, "pages.real_pages", paths.impact)) != int(_get(ncs, "detected_pages", paths.summary)):
        raise ValueError("영향표 pages.real_pages 가 정본 corpora.NCS.detected_pages 와 다릅니다")
    if int(_get(impact, "pages.교과서.detected_pages", paths.impact)) != int(_get(school, "detected_pages", paths.summary)):
        raise ValueError("영향표 pages.교과서.detected_pages 가 정본 corpora.교과서.detected_pages 와 다릅니다")
    school_page_grades = _grades(impact, paths.impact, "pages.교과서.page_grades")
    if sum(school_page_grades.values()) != int(impact["pages"]["교과서"]["detected_pages"]):
        raise ValueError("영향표 pages.교과서.page_grades 합이 detected_pages 와 다릅니다 (Codex 구조 리뷰 P2)")
    if "real_page_grades" not in impact.get("pages", {}) or "교과서" not in impact.get("pages", {}):
        raise ValueError(f"{Path(paths.impact).name} 에 pages.real_page_grades / pages.교과서 가 없습니다{NEW_FIELDS_HINT}")
    real_page_grades = _grades(impact, paths.impact, "pages.real_page_grades")
    if sum(real_page_grades.values()) != int(impact["pages"]["real_pages"]):
        raise ValueError("영향표 pages.real_page_grades 합이 real_pages 와 다릅니다")
    total = int(impact["totals"]["NCS"])
    block_grades, real_grades = _grades(impact, paths.impact, "grades.block.NCS"), _grades(impact, paths.impact, "grades.real.NCS")
    transition = _get(impact, "transition", paths.impact)
    matrix = {k: int(v) for k, v in _get(transition, "matrix", paths.impact).items()}
    if sum(block_grades.values()) != total or sum(real_grades.values()) != total:
        raise ValueError(f"영향표 등급 합(블록 {sum(block_grades.values())} / 실제 {sum(real_grades.values())})이 totals.NCS({total}) 와 다릅니다")
    if int(transition["moved"]) + int(transition["unchanged"]) != total or sum(matrix.values()) != int(transition["moved"]):
        raise ValueError("영향표 transition(moved + unchanged = total, 행렬 합 = moved)이 맞지 않습니다")
    groups = _get(impact, "groups", paths.impact)
    if set(groups) != set(NCS_GROUP_ORDER):
        raise ValueError(f"영향표 groups({sorted(groups)}) 가 보고서 분야 대응표({list(NCS_GROUP_ORDER)}) 와 다릅니다 — 분야가 빠지거나 이름이 바뀌었다")
    for basis, grades in (("block", block_grades), ("real", real_grades)):
        for g in (1, 2, 3):
            if sum(int(_get(v, f"{basis}.{g}", paths.impact)) for v in groups.values()) != grades[g]:
                raise ValueError(f"영향표 groups 의 {basis} 등급 {g} 합이 grades.{basis}.NCS 와 다릅니다")
    prev_pages, prev_page_g = int(_get(prev, "pages", paths.summary)), _grades(prev, paths.summary, "page_g")
    if prev_pages != int(_get(reseg, "pages", paths.reseg_summary)) or prev_page_g != _grades(reseg, paths.reseg_summary, "page_g"):
        raise ValueError("정본 meta.previous_basis(pages·page_g)가 reseg_summary.json 과 다릅니다 — 이전 기준 파일이 바뀐 것")
    agreement = _get(run, "reseg_agreement", paths.summary)
    shared_pages, shared_agree = int(_get(agreement, "pages", paths.summary)), int(_get(agreement, "agree", paths.summary))
    if not (0 < shared_agree <= shared_pages <= min(int(impact["pages"]["real_pages"]), prev_pages)):      # 공유 쪽이 0 이면 "모두 일치" 가 참이 되어 버린다 (레드팀)
        raise ValueError(f"정본 meta.run.reseg_agreement({agreement}) 가 0 < agree ≤ pages ≤ min(검출 쪽 {impact['pages']['real_pages']}, 이전 기준 {prev_pages}) 를 어깁니다 — --reseg-csv 없이 만든 정본인가")
    generated = str(_get(run, "generated_at", paths.summary))
    return BridgeFacts(
        run_date=generated[:10], total=int(impact["totals"]["NCS"]),
        block_grades=block_grades, real_grades=real_grades,
        block_pages=int(_get(impact, "pages.block_pages", paths.impact)), real_pages=int(impact["pages"]["real_pages"]),
        moved=int(transition["moved"]), unchanged=int(transition["unchanged"]), matrix=matrix,
        groups={name: (int(_get(v, "block.3", paths.impact)), int(_get(v, "real.3", paths.impact))) for name, v in groups.items()},
        existing_occurrences=int(_get(impact, "by_source.existing.occurrences", paths.impact)), existing_kept_pct=float(_get(impact, "by_source.existing.unchanged_pct", paths.impact)),
        real_page_grades=real_page_grades, school_detected=int(impact["pages"]["교과서"]["detected_pages"]), school_page_grades=school_page_grades,
        prev_date=str(_get(prev, "date", paths.summary)), prev_pages=prev_pages, prev_page_g=prev_page_g, prev_rows=int(_get(reseg, "meta.rows", paths.reseg_summary)),
        shared_pages=shared_pages, shared_agree=shared_agree,
    )


# ---------------------------------------------------------------- 템플릿 (설계 §3.5 · §3.7)
@dataclass(frozen=True)
class Piece:
    """삽입할 문단 하나 — kind: H 소제목 · P 본문 · B 빈 문단 · C 표 캡션 · T 표 · N 표의 주 · L 기존 등급 정의 목록의 자리(삽입하지 않음)."""
    kind: str
    text: str = ""
    rows: tuple = ()                       # T: 데이터 행
    header: tuple = ()                     # T: 헤더 행
    conditions: dict = field(default_factory=dict)   # 데이터로 갈린 서술의 결과 (대조 JSON)


TABLE4_CAPTION = "표 4. 국내 반도체고등학교 교과서({school}종)와 한국산업인력공단 NCS 교과서({ncs}종)"
TABLE5_CAPTION = "표 5. 키워드 기반 분석의 이해하기 쉬운 {steps}단계"   # 단계 수는 methods_table5_rows 의 행 수에서 (Claude 적대적 리뷰 3)
TABLE6_CAPTION = "표 6. 검색·쪽 배치·등급 판정 기준"
TABLE12_1_CAPTION = "표 12-1. 쪽 배치 기준에 따른 NCS 출현 등급 분포"
TABLE12_2_CAPTION = "표 12-2. 쪽 단위로 본 이전 기준과 정본의 관계"
TABLE12_1_LABEL, TABLE12_2_LABEL = "표 12-1.", "표 12-2."          # 대조 JSON·검토 HTML 의 표 라벨 (캡션 앞머리)
TABLE12_2_NOTE = "주: 쪽 비율의 분모는 각 열의 단위 수. 쪽 배치와 판정 규칙은 세 열이 같고 검출 방식만 다르다."
METHODS_REWRITE_LOCATORS = ("안전보건 수준은 각 출현이 속한", "이 등급은 문장 하나의 완성도를")


def _ncs_group_documents(f) -> dict[str, int]:
    """분야(그룹) → 권수 — CorpusFacts.areas 는 보고서 분야명(개발·제조·…)이라 그룹명으로 되돌린다."""
    return {g: int(f.ncs.areas[NCS_GROUP_TO_AREA[g]]["documents"]) for g in NCS_GROUP_ORDER}


def _pages_total(corpus) -> int:
    return sum(int(a["pages"]) for a in corpus.areas.values())


def table4_caption(f) -> str:
    return TABLE4_CAPTION.format(school=f.school.documents, ncs=f.ncs.documents)


def table4_group_lines(f) -> list[tuple[str, str]]:
    return [(g, f"{g} {n}종") for g, n in _ncs_group_documents(f).items()]


def table5_caption(f) -> str:
    return TABLE5_CAPTION.format(steps=len(methods_table5_rows(f)))


def methods_table5_rows(f) -> list[list[str]]:
    m = f.methods
    return [
        ["1. 자료 수집", f"NCS 학습모듈 {f.ncs.documents}권과 교과서 {f.school.documents}권의 PDF와 변환 마크다운, 파일 정보를 모은다", "분석 자료"],
        ["2. 내용 정리", "문장·표·제목을 구분하고, 같은 자료는 한 파일만 남긴다", "검색 가능한 본문"],
        ["3. 키워드 검색", f"{len(m.keyword_names)}개 주제어와 그 동등·구체 표현(의미 표현 사전 v2)을 찾는다", "출현 목록"],
        ["4. 문맥 확인", "동음이의어는 제외하고, 조건부 표현은 앞뒤 문맥으로 판정한다. 표현 사전 자체를 외부 코더가 검토한다", "근거 문맥"],
        ["5. 쪽 배치", "출현이 놓인 줄을 실제 PDF 쪽에 대응시킨다", "출현별 실제 쪽"],
        ["6. 등급 부여", "그 쪽의 본문을 규칙으로 1~3등급 판정하고 출현에 연결한다", "등급 연결 결과"],
        ["7. 결과 정리·검증", "파일·분야·주제어별로 집계하고, 실행 기록과 기대값을 대조한다", "비교 가능한 통계"],
    ]


def methods_table6_rows(f) -> list[list[str]]:
    m = f.methods
    return [
        ["검색 표현", "같은 주제의 여러 표현을 함께 찾는다", "화재–fire / 보호구–장갑·보호안경·안전화"],
        ["문맥 확인", "단어가 아니라 실제 의미를 확인한다", f"‘안전성’·‘안전 마진’은 ‘안전’에서 제외, {'·'.join(m.conditional)}은 같은 줄 ±1줄에 안전 동반어가 있을 때만 집계"],
        ["쪽 기준", "출현이 놓인 실제 PDF 쪽", f"NCS {m.page_maps}권은 줄→쪽 대응표, NCS {m.marker_books}권과 교과서 {f.school.documents}권은 쪽 표식"],
        ["등급 1", "관련 내용이 없거나 매우 부족하다", f"쪽 본문의 안전 용어 {m.safety_min - 1}건 이하"],
        ["등급 2", "위험은 언급하지만 예방 방법이 불충분하다", f"안전 용어 {m.safety_min}건 이상, 조치 용어 {m.action_min - 1}건 이하"],
        ["등급 3", "위험과 구체적인 예방 방법·대응 절차를 제시한다", f"안전 용어 {m.safety_min}건 이상, 조치 용어 {m.action_min}건 이상"],
        ["집계 단위", "출현건수", "한 쪽에 출현이 여럿이면 그 수만큼 센다. 쪽 단위 값은 제3장 2절 4) 참조"],
    ]


def methods_rewrites(f) -> list[tuple[str, str]]:
    """기존 등급 정의 목록의 두 문장 — '페이지·구역'(블록) 을 실제 쪽으로."""
    return [
        (METHODS_REWRITE_LOCATORS[0], "안전보건 수준은 각 출현이 놓인 실제 PDF 쪽(교과서는 쪽 표식이 가리키는 쪽)의 본문을 기준으로 세 등급으로 나누었다."),
        (METHODS_REWRITE_LOCATORS[1], "이 등급은 문장 하나의 완성도를 직접 평가한 값이 아니라 해당 출현이 놓인 쪽의 판정값이며, 같은 쪽의 모든 출현이 같은 등급을 갖는다."),
    ]


def _grade3_shares(f) -> tuple[bool, str, str]:
    """(출현 비율 > 쪽 비율 인가, 출현 기준 등급 3 비율, 쪽 기준 등급 3 비율) — 5절 5)·2절 4) 가 같은 값으로 갈린다."""
    b = f.bridge
    return b.real_grades[3] / b.total > b.real_page_grades[3] / b.real_pages, pct(b.real_grades[3], b.total), pct(b.real_page_grades[3], b.real_pages)


def methods_paragraphs(f) -> list[Piece]:
    m, b, n, s = f.methods, f.bridge, f.ncs, f.school
    groups = _ncs_group_documents(f)
    H = [Piece("H", h) for h in METHODS_HEADINGS]
    B = Piece("B")
    dedup_clause = f" 같은 코드의 파일이 둘인 {m.dedup_books}권은 쪽 표식이 많은 파일만 남겼다." if m.dedup_books > 0 else ""
    p1 = Piece("P", (f"분석 자료는 한국산업인력공단 NCS 학습모듈 {n.documents}권({'·'.join(f'{g} {v}권' for g, v in groups.items())}, 총 {fmt(_pages_total(n))}쪽)과 "
                     f"반도체고등학교 전공교과서 {s.documents}권(총 {fmt(_pages_total(s))}쪽)의 본문이다. PDF를 변환한 마크다운 파일에서 문장·표·제목을 구분하고, 파일 이름의 학습모듈 코드로 같은 자료를 확인하였다. "
                     f"학습모듈 코드가 없는 파일(변환 보고서)은 자료 폴더에서 제외한 뒤 실행하였다(코드 없는 파일이 남아 있으면 실행이 멈춘다).{dedup_clause} 파일과 검색어는 한글의 자모 결합 방식이나 띄어쓰기가 달라도 같은 말로 인식되도록 정규화한 뒤 검색하였으며, 표 안의 글자와 제목도 검색 대상에 포함하였다."),
               conditions={"dedup_clause": m.dedup_books > 0})
    p2a = Piece("P", (f"검색 대상은 {'·'.join(m.keyword_names)}의 {len(m.keyword_names)}개 주제어이다. 각 주제어는 (1) 정확 일치, (2) 동음이의 제외(예: ‘안전’에 포함된 ‘안전성’, ‘안전 마진·여유·재고·율·계수’는 제외), "
                      "(3) 동등 표현(예: ‘화재’–‘fire’), (4) 구체 표현(예: ‘보호구’–‘장갑·보호안경·안전화’)의 네 층으로 정의한 의미 표현 사전으로 찾았다. "
                      "‘MSDS’와 ‘물질안전보건자료’는 워크북의 주제어가 다르므로 각각 집계하였다. 영문 약어(PSM, MSDS)는 단어 경계에서만 일치시켰다."))
    decreased = all(m.totals_v2[c] < m.totals_v1fix[c] for c in m.totals_v1fix)
    revisions = len(m.review_versions) - 1
    chain = " → ".join(m.review_versions)
    latest = m.review_versions[-1]
    review_pair = "서로 다른 계열의 AI 코더 둘" if m.review_family_warning is None else "같은 계열의 AI 코더 둘"     # FR-1 — 계열 경고가 있으면 "서로 다른 계열" 을 말하지 않는다 (레드팀)
    adjudicated = (f"불일치 {m.review_disagreements}건은 연구책임자가 재정하였다" if m.review_adjudicated == m.review_disagreements
                   else f"불일치 {m.review_disagreements}건 중 {m.review_adjudicated}건을 연구책임자가 재정하였다")
    p2b = Piece("P", (f"사전은 {KOREAN_COUNT.get(revisions, str(revisions))} 차례 개정하였다({chain}). {latest}는 도메인 검토의 결과이다. 출현이 많은 비정확 표현과 외부 감사가 지목한 표현을 합한 {m.review_targets}개 표현에서 "
                      f"표현당 최대 {m.review_per_expression}건, {fmt(m.review_items)}건의 문맥을 층화 추출하고, {review_pair}({coder_family(m.review_coders[0])}, {coder_family(m.review_coders[1])})이 "
                      f"각 문맥에서 그 표현이 노동자 안전·보건을 뜻하는지를 판정하였다. 유효 판정 {fmt(m.review_n)}건 중 두 코더가 일치한 것은 {fmt(m.review_agree)}건({pct(m.review_agree, m.review_n)}, κ {m.review_kappa:.3f})이었고, "
                      f"{adjudicated}. 표현별 정밀도의 {round(100 * (1 - m.review_alpha))}% 신뢰구간 하한이 {m.review_floor:g} 미만인 표현은 "
                      f"보류({'·'.join(m.held)}) 또는 조건부 포함({'·'.join(m.conditional)}: 같은 줄이나 앞뒤 한 줄에 안전 동반어가 있을 때만 집계)으로 처리하였다. "
                      f"이 개정으로 NCS 출현은 {fmt(m.totals_v1fix['NCS'])}건에서 {fmt(m.totals_v2['NCS'])}건으로, 교과서는 {fmt(m.totals_v1fix['교과서'])}건에서 {fmt(m.totals_v2['교과서'])}건으로 "
                      f"{'줄었다' if decreased else '바뀌었다'}."),
                conditions={"totals_decreased": decreased, "revisions": revisions, "all_adjudicated": m.review_adjudicated == m.review_disagreements, "review_two_families": m.review_family_warning is None})
    p3 = Piece("P", (f"2026-04 검색에 쓴 마크다운의 쪽 표식은 대부분 목차에서 유도한 값이어서 한 표식이 실제 여러 쪽을 덮었고, 넓게는 {m.max_label_width}쪽에 이르렀다"
                     f"(워크북 셀의 {fmt(m.excel_max_chars)}자 한도에 걸린 쪽 {m.truncated_pages}개가 그 예이다). 이를 바로잡기 위해 마크다운의 각 줄을 PDF 각 쪽의 본문과 문자 3-gram 포함도로 비교하고, "
                     f"쪽 순서가 뒤바뀌지 않도록 동적 계획법으로 대응시켜 NCS {m.page_maps}권의 줄→쪽 대응표를 만들었다. 쪽마다 표식이 있는 {m.align_books}권은 표식을 우선 쓰고 대응표는 검증에 썼는데, "
                     f"대응 후보 {fmt(m.align_lines)}줄 중 정확히 같은 쪽이 {pct(m.align_exact, m.align_lines)}, ±1쪽 이내가 {pct(m.align_near, m.align_lines)}였다. "
                     f"변환 시 쪽 표식이 실제 쪽인 나머지 {m.marker_books}권과 교과서 {s.documents}권은 표식을 그대로 썼다. 모든 NCS 출현은 이 대응으로 실제 PDF 쪽에 놓였으며, 그 효과는 제3장 2절 4)에 정리하였다."))
    conservative = m.recall_range()[1] < CONSERVATIVE_RECALL
    conservative_sentence = " 즉 이 규칙의 등급 3은 보수적인 판정이며, 규칙이 등급 3으로 잡지 않은 쪽에도 구체적 대책이 있을 수 있다." if conservative else ""
    recoding_pair = "서로 다른 계열의 AI 코더가" if m.recoding_family_warning is None else "AI 코더가"
    p4 = Piece("P", (f"이 규칙(안전 용어 {m.safety_min - 1}건 이하 → 등급 1, {m.safety_min}건 이상이면서 조치 용어 {m.action_min}건 이상 → 등급 3, 그 사이 → 등급 2)은 2026-04 워크북에 기록된 등급 사유에서 복원한 것으로, "
                     f"워크북 {fmt(m.repro_pages)}쪽의 원 판정을 {pct(m.repro_agree, m.repro_pages)}({fmt(m.repro_agree)}쪽) 재현한다. 규칙의 타당성은 워크북 쪽 {fmt(m.sample_pages)}쪽(규칙 변형 간 판정이 갈린 쪽과 등급 3 후보 전수 {fmt(m.census_pages)}쪽, "
                     f"나머지 {fmt(m.recall_pool)}쪽에서 무작위 {fmt(m.recall_pages)}쪽)을 {recoding_pair} 독립 판정한 결과로 확인하였다. 규칙이 등급 3이라 한 쪽은 {range_text(m.precision_range())}가 코더도 등급 3이었고(정밀도), "
                     f"코더가 등급 3이라 한 쪽 가운데 규칙이 등급 3으로 잡은 비율은 {range_text(m.recall_range())}였다(재현율).{conservative_sentence} "
                     f"교과서는 2026-04 판정이 있는 쪽은 그 등급을 쓰고({fmt(s.grade_sources['existing'])}건), 없는 쪽은 같은 규칙으로 판정하였다({fmt(s.grade_sources['new'])}건)."),
               conditions={"conservative": conservative, "recoding_two_families": m.recoding_family_warning is None})
    exceeds, occ_share, page_share = _grade3_shares(f)
    share_sentence = (f"등급 3 쪽은 정의상 안전·조치 용어가 많은 쪽이어서 출현이 몰리므로, 출현 기준 등급 3 비율(NCS {occ_share})은 쪽 기준 비율({page_share})보다 크다." if exceeds
                      else f"출현 기준 등급 3 비율(NCS {occ_share})과 쪽 기준 비율({page_share})은 분모가 다른 값이다.")
    p5 = Piece("P", (f"제3장의 등급 비율은 출현건수를 분모로 한다. 하나의 출현이 하나의 등급을 가지며, 같은 쪽에 출현이 여럿이면 그 수만큼 센다. {share_sentence} "
                     f"두 값은 같은 판정의 두 분모이며, 쪽 기준 값과 {b.prev_date}에 먼저 발표한 쪽 단위 이전 기준({fmt(b.prev_pages)}쪽, 등급 3 {pct(b.prev_page_g[3], b.prev_pages)})과의 관계는 제3장 2절 4)에 정리하였다. "
                     "본 보고서의 모든 비율에는 분모를 함께 적었다."),
               conditions={"occurrence_share_exceeds_page_share": exceeds})
    limits = [f"줄→쪽 대응의 오차(±1쪽 밖 {pct(m.align_lines - m.align_near, m.align_lines)})는 등급에 그대로 전해진다.",
              "등급은 쪽의 용어 밀도 규칙이므로 문장 하나의 완성도를 뜻하지 않으며, 표나 목록으로 용어를 나열한 쪽은 출현이 많아진다."]
    if conservative:
        limits.append("규칙의 재현율이 낮아 등급 3 건수는 하한에 가깝다.")
    limits.append("사고사례 자동 판정은 원문 확인이 필요하다(3절).")
    ordinals = ("첫째", "둘째", "셋째", "넷째", "다섯째")
    p6 = Piece("P", (f"모든 수치는 공개 저장소({m.repo_url})의 스크립트가 같은 입력에서 다시 만든다. 실행 기록에는 입력 파일 {m.inputs}종의 해시, 줄→쪽 대응표 {m.page_maps}개의 해시, 사전 버전, 코드 커밋이 남으며, "
                     f"재실행 결과가 기록된 기대값과 다르면 산출물을 쓰지 않는다. 한계는 다음과 같다. " + " ".join(f"{o}, {t}" for o, t in zip(ordinals, limits))),
               conditions={"conservative": conservative, "limits": len(limits)})
    return [H[0], p1, B, H[1], p2a, B, p2b, B, H[2], p3, B, H[3], Piece("L"), B, p4, B, H[4], p5, B, H[5], p6]


# ---------------------------------------------------------------- B3 — 제3장 2절 4)
def _trend(delta_pp: float) -> str:
    if abs(delta_pp) <= BRIDGE_SAME_PP:
        return "거의 같았다"
    return "줄었다" if delta_pp < 0 else "늘었다"


_CONJ = {"거의 같았다": ("거의 같고", "거의 같았으며"), "줄었다": ("줄고", "줄었으며"), "늘었다": ("늘고", "늘었으며")}


def _delta_text(delta: int) -> str:
    return "0" if delta == 0 else f"{'+' if delta > 0 else '−'}{fmt(abs(delta))}"


def bridge_table1_header(f) -> list[str]:
    return ["구분", "목차 블록 기준", f"실제 PDF 쪽 기준({f.bridge.run_date} 정본)", "차이"]


def bridge_table1_rows(f) -> list[list[str]]:
    b = f.bridge
    rows = [["출현 총계", fmt(b.total), fmt(b.total), "0"]]
    for g in (1, 2, 3):
        rows.append([f"등급 {g}", f"{fmt(b.block_grades[g])} ({pct(b.block_grades[g], b.total)})", f"{fmt(b.real_grades[g])} ({pct(b.real_grades[g], b.total)})", _delta_text(b.real_grades[g] - b.block_grades[g])])
    rows.append(["출현이 놓인 단위", f"{fmt(b.block_pages)} 블록", f"{fmt(b.real_pages)} 쪽", "—"])
    rows.append(["등급이 바뀐 출현", "—", f"{fmt(b.moved)} ({pct(b.moved, b.total)})", "—"])
    return rows


def bridge_table1_note(f) -> str:
    b = f.bridge
    order = ("1->2", "1->3", "2->1", "2->3", "3->1", "3->2")
    detail = ", ".join(f"{k.replace('->', '→')} {fmt(b.matrix[k])}건" for k in order if k in b.matrix)
    return f"주: 단위: 건. 비율의 분모는 {fmt(b.total)}건. 등급 변화의 내역: {detail}, 불변 {fmt(b.unchanged)}건."


def bridge_table2_header(f) -> list[str]:
    b = f.bridge
    return ["구분", f"이전 기준(쪽 단위, {b.prev_date})", f"정본(쪽 단위, {b.run_date})", "정본(출현 단위)"]


def _shared_clause(b) -> tuple[str, str, bool]:
    """(본문 절, 표 셀, 모두 일치 여부). 공유 쪽 0 은 load_bridge_facts 가 이미 거부한다 — 여기서도 "모두 일치" 로 읽히지 않게 막는다."""
    if b.shared_pages <= 0:
        raise ValueError("공유 쪽이 0 이면 등급 일치를 말할 수 없습니다")
    if b.shared_agree == b.shared_pages:
        return "모두 일치한다", f"{fmt(b.shared_pages)} (등급 일치 {fmt(b.shared_agree)}, {pct(b.shared_agree, b.shared_pages)})", True
    return (f"{fmt(b.shared_pages)}쪽 중 {fmt(b.shared_agree)}쪽에서 일치한다({pct(b.shared_agree, b.shared_pages)})",
            f"{fmt(b.shared_pages)} (등급 일치 {fmt(b.shared_agree)}, {pct(b.shared_agree, b.shared_pages)})", False)


def bridge_table2_rows(f) -> list[list[str]]:
    b = f.bridge
    _, cell, _ = _shared_clause(b)
    rows = [["검출 방식", f"문자열 검색(2026-04 워크북 {fmt(b.prev_rows)}행)", "의미 표현 사전 v2", "의미 표현 사전 v2"],
            ["단위 수", f"{fmt(b.prev_pages)}쪽", f"{fmt(b.real_pages)}쪽", f"{fmt(b.total)}건"]]
    for g in (1, 2, 3):
        rows.append([f"등급 {g}", f"{fmt(b.prev_page_g[g])} ({pct(b.prev_page_g[g], b.prev_pages)})", f"{fmt(b.real_page_grades[g])} ({pct(b.real_page_grades[g], b.real_pages)})",
                     f"{fmt(b.real_grades[g])} ({pct(b.real_grades[g], b.total)})"])
    rows.append(["두 집계가 공유하는 쪽", fmt(b.shared_pages), cell, "—"])
    return rows


def bridge_table2_note(f) -> str:
    return TABLE12_2_NOTE


def bridge_paragraphs(f) -> list[Piece]:
    b = f.bridge
    B = Piece("B")
    verbs = [_trend(100 * (b.real_grades[g] - b.block_grades[g]) / b.total) for g in (1, 2, 3)]
    v1, v2, v3 = _CONJ[verbs[0]][0], _CONJ[verbs[1]][1], verbs[2]
    pages_verb = "늘었으며" if b.real_pages > b.block_pages else ("줄었으며" if b.real_pages < b.block_pages else "그대로였으며")   # 같으면 "늘었다" 고 하지 않는다 (Codex 구조 리뷰 P2)
    groups = ", ".join(f"{name} {fmt(b.groups[name][0])}건→{fmt(b.groups[name][1])}건" for name in NCS_GROUP_ORDER)      # 그룹 집합은 load_bridge_facts 가 대응표와 같음을 보장한다
    q1 = Piece("P", (f"본 절의 수치는 모든 NCS 출현을 실제 PDF 쪽에 놓고 그 쪽의 본문으로 등급을 판정한 {b.run_date} 정본이다. 그 이전의 집계는 같은 사전과 같은 판정 규칙을 쓰되 출현의 위치를 마크다운의 쪽 표식 블록으로 잡았는데, "
                     f"이 표식은 대부분 목차에서 유도한 값이어서 한 블록이 여러 쪽을 덮었다. 두 집계의 차이는 표 12-1과 같다. 출현 총계 {fmt(b.total)}건은 변하지 않았고, 출현이 놓인 단위는 {fmt(b.block_pages)}개 블록에서 {fmt(b.real_pages)}쪽으로 {pages_verb}, "
                     f"등급이 바뀐 출현은 {fmt(b.moved)}건({pct(b.moved, b.total)})이었다. "
                     f"등급 1은 {fmt(b.block_grades[1])}건({pct(b.block_grades[1], b.total)})에서 {fmt(b.real_grades[1])}건({pct(b.real_grades[1], b.total)})으로 {v1}, "
                     f"등급 2는 {fmt(b.block_grades[2])}건({pct(b.block_grades[2], b.total)})에서 {fmt(b.real_grades[2])}건({pct(b.real_grades[2], b.total)})으로 {v2}, "
                     f"등급 3은 {fmt(b.block_grades[3])}건({pct(b.block_grades[3], b.total)})에서 {fmt(b.real_grades[3])}건({pct(b.real_grades[3], b.total)})으로 {v3}. "
                     f"여러 쪽을 덮던 블록이 실제 쪽으로 나뉘면서, 용어가 없는 쪽에 있던 출현은 등급 1로, 용어가 모인 쪽의 출현은 등급 2·3으로 다시 판정된 결과이다. 분야별 등급 3 출현은 {groups}이다. "
                     f"워크북의 2026-04 판정을 승계하던 출현 {fmt(b.existing_occurrences)}건은 실제 쪽에서 다시 판정했을 때 {b.existing_kept_pct:.1f}%만 같은 등급이었으므로, 본 정본은 NCS의 등급을 승계하지 않고 모두 실제 쪽에서 판정하였다."),
               conditions={"grade_verbs": [v1, v2, v3], "real_pages_vs_block": pages_verb})
    clause, _, all_agree = _shared_clause(b)
    exceeds, occ_share, page_share = _grade3_shares(f)
    share_sentence = " 등급 3 쪽은 정의상 안전·조치 용어가 많은 쪽이어서 출현이 몰리므로, 출현을 세면 쪽을 셀 때보다 등급 3의 몫이 커진다." if exceeds else ""
    q2 = Piece("P", (f"쪽 단위로 보면 정본의 출현은 {fmt(b.real_pages)}쪽에 놓이고 그 가운데 등급 3은 {fmt(b.real_page_grades[3])}쪽({page_share})이다. "
                     f"{b.prev_date}에 먼저 발표한 쪽 단위 이전 기준은 2026-04 검색 결과 {fmt(b.prev_rows)}행을 같은 방법으로 실제 쪽에 재배치한 값으로, {fmt(b.prev_pages)}쪽 가운데 등급 3이 {fmt(b.prev_page_g[3])}쪽({pct(b.prev_page_g[3], b.prev_pages)})이었다(표 12-2). "
                     f"두 집계는 같은 줄→쪽 대응과 같은 판정 규칙을 쓰므로, 둘 다 검출한 {fmt(b.shared_pages)}쪽의 등급은 {clause}. "
                     f"쪽의 집합이 다른 것은 검출 방식의 차이(문자열 검색 대 의미 표현 사전) 때문이고, 등급 3 비율이 출현 기준 {occ_share}와 쪽 기준 {page_share}로 다른 것은 분모 때문이다.{share_sentence} "
                     "따라서 출현 기준 비율을 쪽 기준 비율의 개선으로 읽어서는 안 되며, 본 보고서는 두 값을 분모와 함께 제시한다."),
               conditions={"shared_all_agree": all_agree, "occurrence_share_exceeds_page_share": exceeds})
    t1 = Piece("T", rows=tuple(tuple(r) for r in bridge_table1_rows(f)), header=tuple(bridge_table1_header(f)))
    t2 = Piece("T", rows=tuple(tuple(r) for r in bridge_table2_rows(f)), header=tuple(bridge_table2_header(f)))
    return [B, Piece("H", BRIDGE_HEADING), B, q1, B, Piece("C", TABLE12_1_CAPTION), t1, Piece("N", bridge_table1_note(f)), B, q2, B, Piece("C", TABLE12_2_CAPTION), t2, Piece("N", bridge_table2_note(f)), B]


def conclusion_sentence(f) -> tuple[str, dict]:
    b = f.bridge
    now_pct, prev_pct = 100 * b.real_page_grades[3] / b.real_pages, 100 * b.prev_page_g[3] / b.prev_pages
    same = abs(now_pct - prev_pct) <= BRIDGE_LEVEL_PP
    return (f"이상의 수치는 출현건수를 분모로 한 값이며, 쪽 단위로 보면 등급 3은 검출 {fmt(b.real_pages)}쪽 중 {fmt(b.real_page_grades[3])}쪽({pct(b.real_page_grades[3], b.real_pages)})으로 "
            f"이전 기준({fmt(b.prev_pages)}쪽 중 {fmt(b.prev_page_g[3])}쪽, {pct(b.prev_page_g[3], b.prev_pages)})과 {'같은 수준이다' if same else '차이가 있다'}(4) 참조).",
            {"level_same": same})


def textbook_basis_sentence(f) -> str:
    b = f.bridge
    return f"교과서는 변환 시 쪽 표식이 실제 쪽이어서 쪽 배치 기준의 변경에 영향을 받지 않았다({fmt(f.school.total)}건; {fmt(b.school_detected)}쪽 가운데 등급 3 {fmt(b.school_page_grades[3])}쪽)."
