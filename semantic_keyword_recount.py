#!/usr/bin/env python3
"""Meaning-aware recount of 30 independent safety keywords in Markdown corpora."""

import argparse
from dataclasses import asdict, dataclass, replace
from collections import defaultdict
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import unicodedata

import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from page_utils import GRADE_LABEL, PAGE_MARKER_RE as _MARKER_ANYWHERE_RE


HERE = Path(__file__).resolve().parent
# 마커만 있는 줄. page_utils.PAGE_MARKER_RE 는 줄 안 어디든 찾는 패턴이라 fullmatch 로 감싼다.
PAGE_MARKER_RE = re.compile(r"^\s*" + _MARKER_ANYWHERE_RE.pattern + r"\s*$", re.IGNORECASE)

# 회귀 가드 — 정본 실행(2026-09-13, 86권)의 수치. 재실행이 어긋나면 --force 없이는 산출물을 쓰지 않는다
# (resegment.py·recount_grades.py 의 EXPECTED 와 같은 규약). None 은 아직 고정 전 — 비교하지 않는다.
# documents 는 --force 로도 우회하지 않는다: 코퍼스가 다르면 정본이 아니다. grades.*.unpaged 0 은
# 연구책임자 결정(2026-09-13, 미배정을 두지 않는다)을 코드가 지키는 자리다.
DICTIONARY_VERSIONS = ("v1", "v1fix", "v2")      # 사전 버전 — v1 2026-09-09 원본, v1fix 결함 2건 수정(정본), v2 도메인 점검 반영 변형
DEFAULT_DICTIONARY = "v1fix"                       # 연구책임자 결정 2026-09-14: 결함 2건(영문 단어 경계·보류 표현 계수)은 정본에 반영
V1_RULE_CONTENT_SHA256 = "6fc926de45d9ca584d3c470e77caca316f65d3d83d45da10cf3322f487b857e3"   # v1(2026-09-09) 규칙 내용 지문 — 영향표의 기준선이 은근히 바뀌지 않게
SAFETY_COMPANIONS = (r"착용", r"보호", r"노출", r"피폭", r"화상", r"부상", r"위험", r"유해", r"안전", r"보건", r"재해", r"사고")   # 조건부 포함의 동반어 초기 가설 — 점검 결과로 귀납·갱신
_V2_OVERRIDES: dict[tuple[str, str], dict[str, object]] = {}   # (키워드, 표현) → {"decision": "held"} 또는 {"require_patterns": (...)} — 점검 결과를 보고 손으로 채운다
HELD_INSIDE_REASON = "보류 표현 내부"
NO_COMPANION_REASON = "안전 문맥 동반어 없음"

GRADE_SOURCES = ("existing", "new", "unpaged-context", "unpaged-fallback")   # 등급 출처 — EXPECTED·payload·워크북 라벨·하니스가 같은 집합을 쓴다
GRADE_SOURCE_LABEL = {"existing": "기존 판정", "new": "신규 판정", "unpaged-context": "문맥 판정(마커 없음)", "unpaged-fallback": "등급1 배정(본문 없음)"}
STRICT_GROUPS = ("documents", "grade_sources", "candidates", "dedup")         # 이 그룹은 EXPECTED 에 없는 키가 실측에 끼어들어도 불일치다 (적대적 리뷰)

EXPECTED = {
    "dictionary": DEFAULT_DICTIONARY,                                                     # v1fix (2026-09-14): 결함 2건 반영 — v1 정본(12,506/1,293)에서 NCS −196·교과서 −21
    "documents": {"NCS": 86, "교과서": 9},
    "totals": {"NCS": 12310, "교과서": 1272},
    "grades": {
        "NCS": {"1": 4946, "2": 4795, "3": 2569, "unpaged": 0},
        "교과서": {"1": 691, "2": 464, "3": 117, "unpaged": 0},
    },
    "grade_sources": {"existing": 7777, "new": 5804, "unpaged-context": 1, "unpaged-fallback": 0},
    "candidates": {"included": 75, "held": 19, "excluded": 2, "not-found": 4},
    "dedup": {"LM1903060205": 1},                                                        # MI 장비 운영 공백 경로(마커 0) 1개를 버린다
    "rule_sha256": "1ffd26c633f7ce67b72e62e86e21a4a535f083a87b6109c918de839a61a95cf3",    # v1fix — PSM·MSDS 단어 경계, 안전 안의 보류 표현 제외 (v1: 2da5dbf4…)
    "source_sha256": "2721f0f98f799272a0e411cfea5e0cfc0e48858763b8b1a58fe282f732d2fae5",  # 워크북 3종 + 마크다운 95개(86+9) 본문 — 사전과 무관, 불변
    "detail_sha256": "ae142454ed94c2e509f4da0dd5916bcb069305e9a7e1b103c86d80c2f3269ffb",  # 상세 전체의 지문 — 총계가 같아도 재배정을 잡는다
    "summary_sha256": "f26f8e869902870bfe63e580ba0928264b248a8b2df3c12655f703d45f0c0817",
}
HEADER_NAMES = {
    "number",
    "번호",
    "영역",
    "filename",
    "파일명",
    "contents",
    "검색결과",
    "page",
    "페이지",
    "페이지전체내용",
    "사고사례여부",
    "등급",
    "등급사유",
}

EXPECTED_KEYWORDS = (
    "안전",
    "사망",
    "부상",
    "끼임",
    "추락",
    "감전",
    "폭발",
    "화재",
    "인화",
    "누출",
    "PSM",
    "공정안전관리",
    "안전보건",
    "작업환경",
    "위험",
    "유해인자",
    "보건",
    "질병",
    "직업병",
    "화학물질",
    "중독",
    "소음",
    "진동",
    "방사선",
    "먼지",
    "분진",
    "보호구",
    "물질안전보건자료",
    "MSDS",
    "산업안전보건법",
)


@dataclass(frozen=True)
class KeywordSource:
    keyword: str
    search_rows: int
    has_header: bool


@dataclass(frozen=True)
class Document:
    corpus: str
    path: Path
    relative_path: str
    text: str


@dataclass(frozen=True)
class DedupRecord:
    """같은 LM 코드의 파일이 여럿일 때 무엇을 남기고 무엇을 버렸는지 — manifest 에 실린다."""

    code: str
    kept: str
    dropped: tuple[str, ...]


@dataclass(frozen=True)
class PageBlock:
    page: int | None
    start_line: int
    lines: tuple[str, ...]


@dataclass(frozen=True)
class ExpressionRule:
    keyword: str
    expression: str
    tier: str
    rationale: str
    pattern: str | None = None
    exclude_patterns: tuple[str, ...] = ()
    held_patterns: tuple[str, ...] = ()        # 보류 표현이 이 규칙 안에서 계수되지 않게 — 겹치면 excluded(보류 표현 내부)
    require_patterns: tuple[str, ...] = ()     # 조건부 포함 — 같은 줄·앞뒤 1줄(블록 안)에 하나라도 없으면 excluded(동반어 없음)


@dataclass(frozen=True)
class MatchRecord:
    corpus: str
    relative_path: str
    keyword: str
    expression: str
    tier: str
    matched_text: str
    line: int
    page: int | None
    context: str
    decision: str
    reason: str
    grade: int | None = None                  # 아래 세 필드는 판정 전 기본값 — assign_match_grades 가 모든 레코드에 1~3 과 GRADE_SOURCES 값을 덮어쓴다
    grade_label: str = "등급 미확정"
    grade_reason: str = "페이지 마커 없음"
    grade_source: str = "unpaged"


@dataclass(frozen=True)
class GradeAssignment:
    grade: int | None
    label: str
    reason: str
    source: str


@dataclass(frozen=True)
class CandidateDecision:
    keyword: str
    expression: str
    decision: str
    tier: str
    rationale: str
    pattern: str | None = None
    exclude_patterns: tuple[str, ...] = ()
    require_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class SummaryRow:
    corpus: str
    keyword: str
    original_search_rows: int | None
    raw_exact: int
    excluded_exact: int
    valid_exact: int
    equivalent_added: int
    specific_added: int
    semantic_total: int
    file_count: int
    page_count: int
    unpaged_file_count: int
    grade_1: int = 0
    grade_2: int = 0
    grade_3: int = 0
    grade_unpaged: int = 0


@dataclass(frozen=True)
class CandidateAudit:
    keyword: str
    expression: str
    decision: str
    tier: str
    rationale: str
    ncs_count: int
    school_count: int
    excluded_count: int
    example_corpus: str | None
    example_path: str | None
    example_line: int | None
    example_page: int | None
    example_context: str | None


@dataclass(frozen=True)
class InputArtifact:
    kind: str
    path: str
    file_count: int
    sha256: str


@dataclass(frozen=True)
class AnalysisResult:
    sources: tuple[KeywordSource, ...]
    documents: tuple[Document, ...]
    rules: tuple[ExpressionRule, ...]
    candidates: tuple[CandidateDecision, ...]
    matches: tuple[MatchRecord, ...]
    summary: tuple[SummaryRow, ...]
    input_artifacts: tuple[InputArtifact, ...] = ()
    dedup: tuple[DedupRecord, ...] = ()


def read_keyword_workbook(path: Path) -> list[KeywordSource]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sources = []
    try:
        for worksheet in workbook.worksheets:
            rows = [
                tuple(row)
                for row in worksheet.iter_rows(values_only=True)
                if row is not None and any(value is not None for value in row)
            ]
            has_header = bool(rows and _is_header_row(rows[0]))
            sources.append(
                KeywordSource(
                    keyword=unicodedata.normalize("NFC", worksheet.title),
                    search_rows=max(0, len(rows) - int(has_header)),
                    has_header=has_header,
                )
            )
    finally:
        workbook.close()
    return sources


def _is_header_row(row: tuple[object, ...]) -> bool:
    values = {
        unicodedata.normalize("NFC", str(value).strip()).lower()
        for value in row
        if value is not None and str(value).strip()
    }
    normalized_headers = {name.lower() for name in HEADER_NAMES}
    return "number" in values or len(values & normalized_headers) >= 2


def load_documents(root: Path, corpus: str) -> list[Document]:
    root = Path(root)
    documents = []
    paths = sorted(
        root.rglob("*.md"),
        key=lambda path: unicodedata.normalize("NFC", path.relative_to(root).as_posix()),
    )
    for path in paths:
        relative_path = unicodedata.normalize("NFC", path.relative_to(root).as_posix())
        text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8", errors="replace"))
        documents.append(Document(corpus=corpus, path=path, relative_path=relative_path, text=text))
    return documents


def _marker_values(document: Document) -> list[int]:
    return [int(m.group(1)) for line in document.text.splitlines() if (m := PAGE_MARKER_RE.match(line))]


def select_ncs_documents(documents: list[Document]) -> tuple[list[Document], list[DedupRecord]]:
    """NCS 코퍼스 규칙 (2026-09-13 감사 C1 시정).

    LM 코드(LM + 10자리)가 경로에 없는 파일은 교재가 아니므로 ValueError — 조용히 버리지 않는다
    (report 요약본 같은 비교재는 디스크에서 지우는 것이 규칙). 같은 코드가 여럿이면
    (마커 수 내림차순, 밑줄 경로 우선, 경로 사전순) 으로 하나만 남기고 나머지를 DedupRecord 로 돌려준다.
    """
    missing = [doc.relative_path for doc in documents if not _NCS_CODE_RE.search(doc.relative_path)]
    if missing:
        raise ValueError("LM 코드가 없는 NCS 파일 — 교재가 아니면 코퍼스에서 지우십시오: " + ", ".join(missing))
    by_code: dict[str, list[Document]] = defaultdict(list)
    for doc in documents:
        by_code[_NCS_CODE_RE.search(doc.relative_path).group(0).upper()].append(doc)
    kept, dedup = [], []
    for code in sorted(by_code):
        group = sorted(
            by_code[code],
            key=lambda d: (-len(_marker_values(d)), " " in d.relative_path, d.relative_path),
        )
        kept.append(group[0])
        if len(group) > 1:
            dedup.append(DedupRecord(code, group[0].relative_path, tuple(d.relative_path for d in group[1:])))
    kept.sort(key=lambda d: d.relative_path)
    return kept, dedup


def check_marker_base(documents: list[Document]) -> list[str]:
    """어느 자리든 1 미만 마커(0-based)가 있는 파일 목록. 비어 있어야 정상 — docs/howto-page-markers.md 의 page_id+1 규약.

    첫 마커만 보면 `<!-- page: 1 --> … <!-- page: 0 -->` 이 통과한다(적대적 리뷰) — 전수 검사.
    """
    problems = []
    for doc in documents:
        values = _marker_values(doc)
        if values and min(values) < 1:
            problems.append(f"{doc.relative_path}: 마커 {min(values)}")
    return problems


def nonmonotone_markers(documents: list[Document]) -> list[str]:
    """마커 값이 감소하는 파일 목록 — 거부하지 않고 manifest 에 기록한다.

    목차에서 유도한 레거시 마커(insert_page_markers.py Strategy 2)는 같은 제목이 되풀이될 때 앞 쪽으로 되돌아갈 수 있고
    (정본 코퍼스에 1권), 그 구간의 출현은 되돌아간 쪽 번호로 집계된다. 재유도는 별도 결정.
    """
    out = []
    for doc in documents:
        values = _marker_values(doc)
        if any(b < a for a, b in zip(values, values[1:])):
            out.append(doc.relative_path)
    return out


def split_pages(document: Document) -> list[PageBlock]:
    blocks = []
    current_page = None
    current_lines: list[str] = []
    current_start = 1

    def flush() -> None:
        if current_lines:
            blocks.append(
                PageBlock(
                    page=current_page,
                    start_line=current_start,
                    lines=tuple(current_lines),
                )
            )

    for line_number, line in enumerate(document.text.splitlines(), start=1):
        marker = PAGE_MARKER_RE.match(line)
        if marker:
            flush()
            current_page = int(marker.group(1))
            current_lines = []
            current_start = line_number + 1
            continue
        current_lines.append(line)
    flush()
    return blocks


_TIMESTAMP_PREFIX_RE = re.compile(r"^\d{8}_\d{6}_")
_NCS_CODE_RE = re.compile(r"(?<![A-Za-z])LM\d{10}", re.IGNORECASE)       # 글자 뒤에 붙은 PLM… 은 코드가 아니다


def _canonical_document(corpus: str, value: str) -> str:
    normalized = unicodedata.normalize("NFC", str(value or "").strip())
    name = normalized.replace("\\", "/").rsplit("/", 1)[-1]
    if name.casefold().endswith(".md"):
        name = name[:-3]
    name = _TIMESTAMP_PREFIX_RE.sub("", name)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", name).casefold()


def grade_lookup_key(corpus: str, relative_path: str, page: int | str) -> tuple[str, str, int]:
    return (corpus, _canonical_document(corpus, relative_path), int(page))


def grade_alias_key(
    corpus: str,
    relative_path: str,
    page: int | str,
) -> tuple[str, str, int] | None:
    if corpus != "NCS":
        return None
    code = _NCS_CODE_RE.search(unicodedata.normalize("NFC", str(relative_path or "")))
    if code is None:
        return None
    return (corpus, f"@lm:{code.group(0).casefold()}", int(page))


def load_existing_grades(
    ncs_workbook: Path,
    school_workbook: Path,
) -> dict[tuple[str, str, int], GradeAssignment]:
    """Load legacy page grades and normalize both corpora to the public 1→3 scale."""
    from recount_grades import NCS_MAP, TXT_MAP, scan

    grouped: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    alias_grouped: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    alias_documents: dict[str, set[str]] = defaultdict(set)
    for corpus, path, grade_map, drop_residue in (
        ("NCS", ncs_workbook, NCS_MAP, False),
        ("교과서", school_workbook, TXT_MAP, True),
    ):
        for row in scan(str(path), grade_map, drop_ncs_residue=drop_residue):
            if row["fn"] is None or row["page"] is None:
                continue
            filename = str(row["fn"])
            grouped[grade_lookup_key(corpus, filename, int(row["page"]))].append(row)
            alias_key = grade_alias_key(corpus, filename, int(row["page"]))
            if alias_key is not None:
                alias_grouped[alias_key].append(row)
                alias_documents[alias_key[1]].add(_canonical_document(corpus, filename))

    assignments = {}
    unambiguous_aliases = {
        key: rows
        for key, rows in alias_grouped.items()
        if len(alias_documents[key[1]]) == 1
    }
    for key, rows in list(grouped.items()) + list(unambiguous_aliases.items()):
        grade = min(int(row["g"]) for row in rows)
        representative = next(row for row in rows if int(row["g"]) == grade)
        assignments[key] = GradeAssignment(
            grade=grade,
            label=GRADE_LABEL[grade],
            reason=str(representative.get("reason") or "기존 페이지 판정"),
            source="existing",
        )
    return assignments


def assign_match_grades(
    result: AnalysisResult,
    existing_grades: dict[tuple[str, str, int], GradeAssignment],
) -> AnalysisResult:
    """Attach a grade to every semantic occurrence, including unpaged records.

    페이지 마커가 없는 출현은 그 줄의 문맥으로 판정(unpaged-context)하고, 문맥이 비면 등급1(unpaged-fallback).
    연구책임자 결정(2026-09-13): 미배정을 두지 않는다. 정본 코퍼스(86권, 마커 1-based)에서는 대상이 수 건뿐이다.
    """
    from regrade import grade_page

    page_lines: dict[tuple[str, str, int], list[str]] = defaultdict(list)
    paged_canonical_documents: dict[tuple[str, str], set[str]] = defaultdict(set)
    paged_alias_documents: dict[str, set[str]] = defaultdict(set)
    for document in result.documents:
        for block in split_pages(document):
            if block.page is None:
                continue
            page_lines[(document.corpus, document.relative_path, block.page)].extend(block.lines)
            paged_canonical_documents[
                (document.corpus, _canonical_document(document.corpus, document.relative_path))
            ].add(document.relative_path)
            alias_key = grade_alias_key(document.corpus, document.relative_path, block.page)
            if alias_key is not None:
                paged_alias_documents[alias_key[1]].add(document.relative_path)

    newly_graded: dict[tuple[str, str, int], GradeAssignment] = {}
    graded_matches = []
    for record in result.matches:
        if record.page is None:
            if record.context.strip():
                grade, _, _, reason = grade_page(
                    record.context,
                    word_boundary=False,
                    normalize=False,
                )
                assignment = GradeAssignment(
                    grade,
                    GRADE_LABEL[grade],
                    f"페이지 마커 없는 출현의 문맥 기준: {reason}",
                    "unpaged-context",
                )
            else:
                assignment = GradeAssignment(
                    1,
                    GRADE_LABEL[1],
                    "페이지·문맥 정보 없음으로 보수적 등급 1 배정",
                    "unpaged-fallback",
                )
        else:
            legacy_key = grade_lookup_key(record.corpus, record.relative_path, record.page)
            page_key = (record.corpus, record.relative_path, record.page)
            assignment = newly_graded.get(page_key)
            if (
                assignment is None
                and len(paged_canonical_documents[(record.corpus, legacy_key[1])]) == 1
            ):
                assignment = existing_grades.get(legacy_key)
            alias_key = grade_alias_key(record.corpus, record.relative_path, record.page)
            if (
                assignment is None
                and alias_key is not None
                and len(paged_alias_documents[alias_key[1]]) == 1
            ):
                assignment = existing_grades.get(alias_key)
            if assignment is None:
                text = "\n".join(page_lines.get(page_key, ()))
                if text:
                    grade, _, _, reason = grade_page(text, word_boundary=False, normalize=False)
                    assignment = GradeAssignment(grade, GRADE_LABEL[grade], reason, "new")
                else:                                     # 마커는 있는데 본문 블록이 없다 — 미배정을 두지 않는다 (2026-09-13)
                    assignment = GradeAssignment(1, GRADE_LABEL[1], "페이지 본문 없음으로 보수적 등급 1 배정", "unpaged-fallback")
                newly_graded[page_key] = assignment
        graded_matches.append(
            replace(
                record,
                grade=assignment.grade,
                grade_label=assignment.label,
                grade_reason=assignment.reason,
                grade_source=assignment.source,
            )
        )

    included = [record for record in graded_matches if record.decision == "included"]
    graded_summary = []
    for row in result.summary:
        records = [
            record
            for record in included
            if (row.corpus == "전체" or record.corpus == row.corpus)
            and record.keyword == row.keyword
        ]
        counts = Counter(record.grade for record in records)
        graded_summary.append(
            replace(
                row,
                grade_1=counts[1],
                grade_2=counts[2],
                grade_3=counts[3],
                grade_unpaged=counts[None],
            )
        )

    return replace(result, matches=tuple(graded_matches), summary=tuple(graded_summary))


def validate_rules(keywords: list[str], rules: list[ExpressionRule]) -> None:
    keyword_set = {unicodedata.normalize("NFC", keyword) for keyword in keywords}
    owners: dict[str, str] = {}
    allowed_tiers = {"exact", "equivalent", "specific"}
    for rule in rules:
        if rule.keyword not in keyword_set:
            raise ValueError(f"목록에 없는 키워드: {rule.keyword}")
        if rule.tier not in allowed_tiers:
            raise ValueError(f"알 수 없는 표현 계층: {rule.tier}")
        if not rule.expression.strip() or not rule.rationale.strip():
            raise ValueError(f"표현과 근거는 비어 있을 수 없습니다: {rule.keyword}")
        try:
            compiled = _compile_rule(rule)
            for pattern in rule.exclude_patterns:
                re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise ValueError(f"잘못된 정규식: {rule.keyword}/{rule.expression}: {exc}") from exc

        if rule.tier != "exact":
            for other in keyword_set - {rule.keyword}:
                if (
                    unicodedata.normalize("NFC", rule.expression).casefold() == other.casefold()
                    or compiled.fullmatch(other)
                ):
                    raise ValueError(
                        f"기존 키워드 상호 확장 금지: {rule.keyword} <- {other}"
                    )
            owner_key = unicodedata.normalize("NFC", rule.expression).casefold()
            previous = owners.setdefault(owner_key, rule.keyword)
            if previous != rule.keyword:
                raise ValueError(
                    f"신규 표현 다중 귀속 금지: {rule.expression} ({previous}, {rule.keyword})"
                )


def _compile_rule(rule: ExpressionRule) -> re.Pattern[str]:
    source = rule.pattern if rule.pattern is not None else re.escape(rule.expression)
    return re.compile(source, re.IGNORECASE)


def _overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def scan_document(document: Document, rules: list[ExpressionRule]) -> list[MatchRecord]:
    by_keyword: dict[str, list[tuple[int, ExpressionRule, re.Pattern[str]]]] = defaultdict(list)
    for index, rule in enumerate(rules):
        by_keyword[rule.keyword].append((index, rule, _compile_rule(rule)))

    records: list[MatchRecord] = []
    for block in split_pages(document):
        for line_offset, line in enumerate(block.lines):
            if not line or re.fullmatch(r"\s*!\[[^]]*]\([^)]*\)\s*", line):
                continue
            line_number = block.start_line + line_offset
            context = line.strip()
            window = "\n".join(block.lines[max(0, line_offset - 1):line_offset + 2])   # 같은 줄 ± 1줄, 페이지 블록 안
            for keyword, compiled_rules in by_keyword.items():
                included_candidates = []
                excluded_candidates = []          # (start, end, index, rule, text, reason)
                for rule_index, rule, pattern in compiled_rules:
                    exclusion_spans = []
                    for exclusion in rule.exclude_patterns:
                        exclusion_spans.extend(
                            (match.start(), match.end())
                            for match in re.finditer(exclusion, line, re.IGNORECASE)
                        )
                    held_spans = [(m.start(), m.end()) for held in rule.held_patterns for m in re.finditer(held, line, re.IGNORECASE)]
                    companion = not rule.require_patterns or any(re.search(req, window, re.IGNORECASE) for req in rule.require_patterns)
                    for match in pattern.finditer(line):
                        item = (match.start(), match.end(), rule_index, rule, match.group(0))
                        span = (match.start(), match.end())
                        if any(_overlaps(span, held) for held in held_spans):
                            excluded_candidates.append(item + (HELD_INSIDE_REASON,))
                        elif any(_overlaps(span, ex) for ex in exclusion_spans):
                            excluded_candidates.append(item + ("동음이의 또는 비대상 문맥 제외",))
                        elif not companion:
                            excluded_candidates.append(item + (NO_COMPANION_REASON,))
                        else:
                            included_candidates.append(item)

                included_candidates.sort(
                    key=lambda item: (item[0], -(item[1] - item[0]), item[2])
                )
                cursor = -1
                for start, end, _, rule, matched_text in included_candidates:
                    if start < cursor:
                        continue
                    records.append(
                        MatchRecord(
                            corpus=document.corpus,
                            relative_path=document.relative_path,
                            keyword=keyword,
                            expression=rule.expression,
                            tier=rule.tier,
                            matched_text=matched_text,
                            line=line_number,
                            page=block.page,
                            context=context,
                            decision="included",
                            reason=rule.rationale,
                        )
                    )
                    cursor = end

                for start, end, _, rule, matched_text, reason in sorted(excluded_candidates, key=lambda item: item[:3]):
                    records.append(
                        MatchRecord(
                            corpus=document.corpus,
                            relative_path=document.relative_path,
                            keyword=keyword,
                            expression=rule.expression,
                            tier=rule.tier,
                            matched_text=matched_text,
                            line=line_number,
                            page=block.page,
                            context=context,
                            decision="excluded",
                            reason=reason,
                        )
                    )
    records.sort(
        key=lambda record: (
            record.corpus,
            record.relative_path,
            record.line,
            record.keyword,
            record.decision,
            record.expression,
        )
    )
    return records


def _ascii_term(term: str) -> str:
    return rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])"


def _check_version(version: str) -> str:
    if version not in DICTIONARY_VERSIONS:
        raise ValueError(f"사전 버전은 {DICTIONARY_VERSIONS} 중 하나여야 합니다: {version}")
    return version


def default_candidate_decisions(version: str = DEFAULT_DICTIONARY) -> list[CandidateDecision]:
    """후보 100개의 판정. v1·v1fix 는 같은 목록(결함은 정확 규칙 쪽), v2 는 _V2_OVERRIDES 를 덧씌운다."""
    _check_version(version)
    decisions = _v1_candidate_decisions()
    if version != "v2":
        return decisions
    out = []
    for candidate in decisions:
        override = _V2_OVERRIDES.get((candidate.keyword, candidate.expression))
        out.append(replace(candidate, **override) if override else candidate)
    return out


def _v1_candidate_decisions() -> list[CandidateDecision]:
    """Return the reviewed, corpus-derived expression registry.

    Included expressions become matching rules. Held, excluded, and not-found
    entries remain visible audit decisions and never affect counts.
    """
    candidates = [
        CandidateDecision("안전", "safety", "held", "equivalent", "복합 법규·자료명과 일반 품질 문맥이 혼재", pattern=_ascii_term("safety")),
        CandidateDecision("안전", "안전성", "held", "equivalent", "제품 성능·품질의 안전성 문맥이 혼재"),
        CandidateDecision("사망", "death", "included", "equivalent", "사망을 직접 지칭하는 영문 표현", pattern=_ascii_term("death")),
        CandidateDecision("사망", "fatality", "not-found", "equivalent", "사망을 뜻하지만 조사 원문에서 확인되지 않음", pattern=r"(?<![A-Za-z])fatalit(?:y|ies)(?![A-Za-z])"),
        CandidateDecision("부상", "상해", "included", "equivalent", "사고로 인한 신체 손상을 직접 지칭", pattern=r"(?<!향)상해"),
        CandidateDecision("부상", "injury", "included", "equivalent", "부상을 직접 지칭하는 영문 표현", pattern=r"(?<![A-Za-z])injur(?:y|ies)(?![A-Za-z])"),
        CandidateDecision("부상", "다치다", "included", "equivalent", "사람이 다치는 사고 결과를 직접 지칭", pattern=r"다치(?:다|고|거나|면|는|어|었|게|지|도록|기)"),
        CandidateDecision(
            "부상",
            "화상",
            "included",
            "specific",
            "열·화학물질 등에 의한 구체적인 신체 부상",
            exclude_patterns=(
                r"열\s*화상",
                r"(?:디지털|의료)\s*화상",
                r"(?:비디오(?:\([^)]*\))?)\s*화상",
                r"(?:포화|초기화|변화)\s*상태",
                r"화상\s*(?:\([^)]*이미지[^)]*\)|소자|처리|데이터|정보|인식|카메라|분석|센서|신호|표시|이미지|시스템|장치)",
            ),
        ),
        CandidateDecision(
            "끼임",
            "협착",
            "included",
            "equivalent",
            "설비 사이에 신체가 끼이는 사고를 직접 지칭하되 화학흡착·제품불량 문맥은 제외",
            exclude_patterns=(
                r"화학\s*협착",
                r"(?:package|substrate|이물질|이물이|mold\s*flash|card\s*holder).{0,100}협착",
                r"협착.{0,100}(?:package|substrate|이물질|이물이|mold\s*flash|card\s*holder)",
            ),
        ),
        CandidateDecision("끼임", "말림", "included", "specific", "회전체에 말려 들어가는 구체적인 끼임 사고"),
        CandidateDecision("끼임", "끼이다", "included", "equivalent", "끼임의 서술형 표현", pattern=r"끼이(?:다|어|었|는|고|거나|면|게|지|기)"),
        CandidateDecision("추락", "떨어짐", "held", "equivalent", "제품 낙하·박리와 사람 추락 문맥이 혼재"),
        CandidateDecision("추락", "fall", "held", "equivalent", "일반 영문 및 제품 낙하 문맥과 혼재", pattern=_ascii_term("fall")),
        CandidateDecision("감전", "electric shock", "included", "equivalent", "인체 감전을 직접 지칭하는 영문 표현", pattern=r"(?<![A-Za-z])electric\s+shock(?:s)?(?![A-Za-z])"),
        CandidateDecision(
            "감전",
            "전기 충격",
            "included",
            "equivalent",
            "인체에 가해지는 전기 충격을 지칭하되 공정 자극 문맥은 제외",
            pattern=r"전기\s*충격",
            exclude_patterns=(
                r"전기\s*충격.{0,50}(?:가스|분해|반응|플라즈마)",
                r"(?:가스|분해|반응|플라즈마).{0,50}전기\s*충격",
            ),
        ),
        CandidateDecision("폭발", "explosion", "included", "equivalent", "폭발을 직접 지칭하는 영문 표현", pattern=r"(?<![A-Za-z])explosion(?:s)?(?![A-Za-z])"),
        CandidateDecision("화재", "fire", "included", "equivalent", "화재·발화를 직접 지칭하는 영문 표현", pattern=r"(?<![A-Za-z])fires?(?![A-Za-z])"),
        CandidateDecision("화재", "불이 붙다", "included", "equivalent", "화재 발생을 서술하는 표현", pattern=r"불이\s*붙(?:다|는|어|었|을|으면|으며|도록|기)"),
        CandidateDecision("화재", "발화", "held", "equivalent", "화재 발생과 물질의 인화 특성에 함께 쓰여 단일 귀속이 어려움"),
        CandidateDecision("인화", "가연성", "included", "equivalent", "불이 붙을 수 있는 물질 특성을 직접 지칭"),
        CandidateDecision("인화", "flammable", "included", "equivalent", "인화성을 직접 지칭하는 영문 표현", pattern=_ascii_term("flammable")),
        CandidateDecision("인화", "combustible", "included", "equivalent", "가연·인화 특성을 직접 지칭하는 영문 표현", pattern=_ascii_term("combustible")),
        CandidateDecision("인화", "발화성", "held", "equivalent", "자연발화성 등 발화 원인이 섞여 인화와 완전히 같지 않음"),
        CandidateDecision(
            "누출",
            "누설",
            "included",
            "equivalent",
            "가스·액체·진공의 새어 나옴을 지칭하되 전기 누설은 제외",
            exclude_patterns=(
                r"누설\s*전류",
                r"전류\s*누설",
                r"(?:전기|전류|회로|소자|신호|트랜지스터|게이트|산화막|핀|절연|정전기|디바이스|device|레이아웃|open/short|impurity).{0,100}누설",
                r"누설.{0,100}(?:전기|전류|회로|소자|신호|트랜지스터|게이트|산화막|핀|절연|정전기|디바이스|device|레이아웃|open/short|impurity)",
            ),
        ),
        CandidateDecision("누출", "gas leak", "included", "equivalent", "가스 누출을 직접 지칭하는 영문 표현", pattern=r"(?<![A-Za-z])gas\s+leaks?(?![A-Za-z])"),
        CandidateDecision("누출", "유출", "held", "equivalent", "인력·정보·기술 유출 문맥이 섞여 안정적 자동 판정이 어려움"),
        CandidateDecision("누출", "leakage", "held", "equivalent", "누설전류 등 전기 특성 문맥이 다수 혼재", pattern=r"(?<![A-Za-z])leakage(?![A-Za-z])"),
        CandidateDecision("PSM", "Process Safety Management", "included", "equivalent", "PSM의 영문 풀네임", pattern=r"(?<![A-Za-z])process\s+safety\s+management(?![A-Za-z])"),
        CandidateDecision("공정안전관리", "공정 안전 관리", "included", "equivalent", "동일 용어의 띄어쓰기·기호 변형", pattern=r"공정(?:\s+|[·ㆍ-]\s*)안전(?:\s+|[·ㆍ-]\s*)관리"),
        CandidateDecision(
            "안전보건",
            "안전 보건",
            "included",
            "equivalent",
            "동일 병렬 개념의 띄어쓰기·기호 변형",
            pattern=r"안전(?:\s+|[·ㆍ/&]\s*|\s+및\s+)보건",
            exclude_patterns=(r"물질\s*안전\s*보건\s*자료", r"산업\s*안전\s*보건\s*법"),
        ),
        CandidateDecision("안전보건", "safety and health", "held", "equivalent", "산업안전보건법 영문명 내부 출현과 일반 병렬 표현이 혼재", pattern=r"(?<![A-Za-z])safety\s+and\s+health(?![A-Za-z])"),
        CandidateDecision("작업환경", "작업 환경", "included", "equivalent", "동일 용어의 띄어쓰기·기호 변형", pattern=r"작업(?:\s+|[·ㆍ-]\s*)환경"),
        CandidateDecision("작업환경", "작업장 환경", "included", "equivalent", "작업이 수행되는 장소의 환경을 직접 지칭", pattern=r"작업장(?:\s+|[·ㆍ-]\s*)환경"),
        CandidateDecision("작업환경", "근로환경", "included", "equivalent", "근로자가 일하는 환경을 직접 지칭"),
        CandidateDecision("위험", "위해성", "included", "equivalent", "유해 영향 가능성의 평가 개념을 직접 지칭"),
        CandidateDecision("위험", "hazard", "included", "equivalent", "위험원·위험을 직접 지칭하는 영문 표현", pattern=r"(?<![A-Za-z])hazards?(?![A-Za-z])"),
        CandidateDecision("위험", "risk", "held", "equivalent", "금융·통계·프로젝트 일반 문맥이 혼재", pattern=r"(?<![A-Za-z])risks?(?![A-Za-z])"),
        CandidateDecision("유해인자", "유해 인자", "included", "equivalent", "동일 용어의 띄어쓰기 변형", pattern=r"유해\s+인자"),
        CandidateDecision("유해인자", "유해요인", "included", "equivalent", "건강에 해를 주는 요인을 직접 지칭", pattern=r"유해\s*요인"),
        CandidateDecision("유해인자", "유해요소", "included", "equivalent", "건강에 해를 주는 요소를 직접 지칭", pattern=r"유해\s*요소"),
        CandidateDecision("보건", "건강", "included", "specific", "보건이 보호·증진하려는 건강 상태를 명시적으로 지칭"),
        CandidateDecision("보건", "위생", "included", "specific", "작업장 보건의 구체적인 위생 관리 개념"),
        CandidateDecision("보건", "health", "held", "equivalent", "설비 상태와 복합 법규명 등 비보건 문맥이 혼재", pattern=_ascii_term("health")),
        CandidateDecision("질병", "질환", "included", "equivalent", "질병을 직접 지칭하는 동의 표현"),
        CandidateDecision("직업병", "직업성 질환", "not-found", "equivalent", "직업으로 생긴 질환을 뜻하지만 조사 원문에서 미출현"),
        CandidateDecision("직업병", "업무상 질병", "not-found", "equivalent", "업무로 생긴 질병을 뜻하지만 조사 원문에서 미출현"),
        CandidateDecision("직업병", "occupational disease", "not-found", "equivalent", "직업병 영문 표현이지만 조사 원문에서 미출현", pattern=r"(?<![A-Za-z])occupational\s+diseases?(?![A-Za-z])"),
        CandidateDecision("화학물질", "화학 물질", "included", "equivalent", "동일 용어의 띄어쓰기 변형", pattern=r"화학\s+물질"),
        CandidateDecision("화학물질", "화학약품", "included", "equivalent", "공정에서 사용하는 화학 물질을 직접 지칭", pattern=r"화학\s*약품"),
        CandidateDecision("화학물질", "케미컬", "included", "equivalent", "화학물질을 뜻하는 현장 외래어"),
        CandidateDecision("화학물질", "chemical", "held", "equivalent", "화학적 성질을 뜻하는 형용사 용법이 광범위", pattern=r"(?<![A-Za-z])chemicals?(?![A-Za-z])"),
        CandidateDecision("중독", "poisoning", "excluded", "equivalent", "확인된 출현이 스퍼터링 타깃 포이즈닝 공정 현상", pattern=_ascii_term("poisoning")),
        CandidateDecision("중독", "급성독성", "held", "specific", "중독 가능성을 나타내지만 중독 발생 자체와는 다름"),
        CandidateDecision("소음", "noise", "excluded", "equivalent", "확인된 출현 대부분이 신호·회로 잡음", pattern=_ascii_term("noise")),
        CandidateDecision("소음", "난청", "held", "specific", "소음의 결과일 수 있으나 원인이 소음으로 한정되지 않음"),
        CandidateDecision("진동", "vibration", "held", "equivalent", "공정·부품의 물리 진동과 안전 유해 진동 문맥이 혼재", pattern=r"(?<![A-Za-z])vibrations?(?![A-Za-z])"),
        CandidateDecision("방사선", "radiation", "included", "equivalent", "방사선을 직접 지칭하는 영문 표현", pattern=_ascii_term("radiation")),
        CandidateDecision("방사선", "X선", "included", "specific", "방사선의 구체 유형", pattern=r"(?<![A-Za-z])X\s*-?\s*선"),
        CandidateDecision("방사선", "엑스선", "included", "specific", "X선의 한글 표기"),
        CandidateDecision("방사선", "감마선", "included", "specific", "방사선의 구체 유형"),
        CandidateDecision("방사선", "자외선", "held", "specific", "광범위한 비전리 방사 영역으로 원 키워드 해석과 차이 가능"),
        CandidateDecision("방사선", "방사능", "held", "equivalent", "방사선을 내는 성질로서 방사선 자체와 구별됨"),
        CandidateDecision("먼지", "dust", "included", "equivalent", "먼지를 직접 지칭하는 영문 표현", pattern=r"(?<![A-Za-z])dusts?(?![A-Za-z])"),
        CandidateDecision("분진", "dust", "held", "equivalent", "신규 표현 단일 귀속 원칙에 따라 '먼지'에만 배정"),
        CandidateDecision("분진", "비산 입자", "held", "equivalent", "공정 파티클과 작업환경 분진 문맥이 혼재"),
    ]

    ppe_terms = (
        ("PPE", r"(?<![A-Za-z])PPE(?![A-Za-z])", "개인보호구의 영문 약어"),
        ("개인 보호 장비", r"개인\s+보호\s+장비", "개인보호구를 풀어 쓴 표현"),
        ("장갑", None, "손을 보호하는 구체 보호구"),
        ("절연 장갑", r"절연\s+장갑", "감전 방지용 구체 보호구"),
        ("고무장갑", r"고무\s*장갑", "화학·전기 위험에 쓰는 구체 보호구"),
        ("고글", None, "눈을 보호하는 구체 보호구"),
        ("보호안경", r"보호\s*안경", "눈을 보호하는 구체 보호구"),
        ("보안경", None, "눈을 보호하는 구체 보호구"),
        ("보호경", None, "눈을 보호하는 구체 보호구"),
        ("귀마개", None, "청력을 보호하는 구체 보호구"),
        ("귀덮개", None, "청력을 보호하는 구체 보호구"),
        ("보호복", None, "신체를 보호하는 구체 보호구"),
        ("방진복", None, "분진 노출 방지용 구체 보호구"),
        ("방열복", None, "고열 노출 방지용 구체 보호구"),
        ("케미컬복", None, "화학물질 노출 방지용 구체 보호구"),
        ("가스복", None, "유해가스 노출 방지용 구체 보호구"),
        ("방진화", None, "분진·오염 방지용 구체 보호구"),
        ("안전화", None, "발을 보호하는 구체 보호구"),
        ("장화", None, "발과 하지를 보호하는 구체 보호구"),
        ("안전모", r"안전모(?!드)", "머리를 보호하는 구체 보호구"),
        ("헬멧", None, "머리를 보호하는 구체 보호구"),
        ("방독면", None, "유해가스 흡입 방지용 구체 보호구"),
        ("공기호흡기", r"공기\s*호흡기", "유해 공기 환경의 구체 호흡 보호구"),
        ("산소호흡기", r"산소\s*호흡기", "산소 공급식 구체 호흡 보호구"),
        ("보호마스크", r"(?:방진|방독|보호|안전)\s*마스크", "호흡기를 보호하는 구체 보호구"),
        ("앞치마", None, "비산·화학물질로부터 몸을 보호하는 구체 보호구"),
        ("보호장구", r"보호\s*장구", "보호구를 뜻하는 일반 현장 표현"),
        ("안전벨트", r"안전\s*벨트", "추락을 막는 구체 보호구"),
    )
    candidates.extend(
        CandidateDecision("보호구", expression, "included", "specific", rationale, pattern=pattern)
        for expression, pattern, rationale in ppe_terms
    )
    candidates.append(
        CandidateDecision(
            "보호구",
            "보호의",
            "included",
            "specific",
            "신체를 보호하는 의복형 보호구이며 소유격 표현은 제외",
            exclude_patterns=(r"(?:수신단|환경)\s*보호의",),
        )
    )
    candidates.extend(
        [
            CandidateDecision("물질안전보건자료", "물질 안전 보건 자료", "included", "equivalent", "동일 용어의 띄어쓰기·기호 변형", pattern=r"(?:물질\s+안전\s*보건\s*자료|물질\s*안전\s+보건\s*자료|물질\s*안전\s*보건\s+자료|물질[·ㆍ-]\s*안전\s*보건\s*자료|물질\s*안전[·ㆍ-]\s*보건\s*자료|물질\s*안전\s*보건[·ㆍ-]\s*자료)"),
            CandidateDecision("MSDS", "Material Safety Data Sheet", "included", "equivalent", "MSDS의 영문 풀네임", pattern=r"(?<![A-Za-z])material\s+safety\s+data\s+sheets?(?![A-Za-z])"),
            CandidateDecision("MSDS", "Safety Data Sheet", "included", "equivalent", "현재 통용되는 안전자료 영문명", pattern=r"(?<![A-Za-z])safety\s+data\s+sheets?(?![A-Za-z])"),
            CandidateDecision("MSDS", "SDS", "included", "equivalent", "Safety Data Sheet의 약어", pattern=_ascii_term("SDS")),
            CandidateDecision("산업안전보건법", "산업 안전 보건법", "included", "equivalent", "동일 법률명의 띄어쓰기·기호 변형", pattern=r"(?:산업\s+안전\s*보건\s*법|산업\s*안전\s+보건\s*법|산업\s*안전\s*보건\s+법|산업[·ㆍ-]\s*안전\s*보건\s*법|산업\s*안전[·ㆍ-]\s*보건\s*법|산업\s*안전\s*보건[·ㆍ-]\s*법)"),
            CandidateDecision("산업안전보건법", "산안법", "included", "equivalent", "산업안전보건법의 현장 약칭"),
        ]
    )
    return candidates


_HELD_INSIDE = {                                   # 보류 표현이 정확 규칙 내부에서 세어지던 결함 (감사 M1(b)) — v1fix 부터
    "안전": (r"안전성", r"안전\s*(?:마진|여유|재고|율|계수)"),
}


def rule_content_sha256(rules: list[ExpressionRule]) -> str:
    """규칙 '내용'의 지문 — 필드가 늘어도 값이 같으면 같은 사전이다 (rule_sha256 은 asdict 라 필드 추가에 바뀐다)."""
    payload = [(r.keyword, r.expression, r.tier, r.pattern, list(r.exclude_patterns), list(r.held_patterns), list(r.require_patterns)) for r in rules]
    return _canonical_hash(payload)


def build_default_rules(keywords: list[str], version: str = DEFAULT_DICTIONARY) -> list[ExpressionRule]:
    _check_version(version)
    fixed = version in ("v1fix", "v2")
    exclusions = {
        "부상": (r"부상(?:하|했|해|하여|하고|하는|한|할|했다|한다)",),
        "진동": (
            r"진동(?:자|수|식|주파수|모드|스펙트럼)",
            r"(?:초음파|격자|분자)\s*진동",
        ),
        "소음": (r"소음\s*지수", r"열\s*소음", r"양자화\s*소음"),
        "분진": (r"분진\s*입자\s*수",),
        "안전": (
            r"공정\s*안전\s*관리",
            r"안전\s*(?:[·ㆍ/&]|및)?\s*보건",
            r"물질\s*안전\s*보건\s*자료",
            r"산업\s*안전\s*보건\s*법",
        ),
        "보건": (
            r"안전\s*(?:[·ㆍ/&]|및)?\s*보건",
            r"물질\s*안전\s*보건\s*자료",
            r"산업\s*안전\s*보건\s*법",
        ),
        "안전보건": (
            r"물질\s*안전\s*보건\s*자료",
            r"산업\s*안전\s*보건\s*법",
        ),
    }
    rules = [
        ExpressionRule(
            keyword=keyword,
            expression=keyword,
            tier="exact",
            rationale="기존 키워드의 정확 문자열",
            # (a) 영문 정확 키워드(PSM·MSDS)는 단어 경계 — EAPSM·Htpsm 내부 문자열을 세지 않는다 (감사 M1(a)), v1fix 부터
            pattern=_ascii_term(keyword) if fixed and re.fullmatch(r"[A-Za-z0-9 ]+", keyword) else None,
            exclude_patterns=exclusions.get(keyword, ()),
            held_patterns=_HELD_INSIDE.get(keyword, ()) if fixed else (),
        )
        for keyword in keywords
    ]
    selected = set(keywords)
    rules.extend(
        ExpressionRule(
            keyword=candidate.keyword,
            expression=candidate.expression,
            tier=candidate.tier,
            rationale=candidate.rationale,
            pattern=candidate.pattern,
            exclude_patterns=candidate.exclude_patterns,
            require_patterns=candidate.require_patterns,
        )
        for candidate in default_candidate_decisions(version)
        if candidate.decision == "included" and candidate.keyword in selected
    )
    validate_rules(keywords, rules)
    return rules


def _raw_exact_count(documents: list[Document], keyword: str) -> int:
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    count = 0
    for document in documents:
        for line in document.text.splitlines():
            if PAGE_MARKER_RE.match(line) or re.fullmatch(r"\s*!\[[^]]*]\([^)]*\)\s*", line):
                continue
            count += sum(1 for _ in pattern.finditer(line))
    return count


def aggregate_matches(
    sources: list[KeywordSource],
    documents: list[Document],
    rules: list[ExpressionRule],
    candidates: list[CandidateDecision],
    input_artifacts: list[InputArtifact] | None = None,
) -> AnalysisResult:
    keywords = [source.keyword for source in sources]
    validate_rules(keywords, rules)
    matches = [record for document in documents for record in scan_document(document, rules)]
    source_rows = {source.keyword: source.search_rows for source in sources}
    corpora = []
    for preferred in ("NCS", "교과서"):
        if any(document.corpus == preferred for document in documents):
            corpora.append(preferred)
    corpora.extend(
        sorted({document.corpus for document in documents} - set(corpora))
    )
    corpora.append("전체")

    summary = []
    for corpus in corpora:
        corpus_documents = (
            documents if corpus == "전체" else [doc for doc in documents if doc.corpus == corpus]
        )
        corpus_paths = {doc.relative_path for doc in corpus_documents}
        for keyword in keywords:
            keyword_records = [
                record
                for record in matches
                if record.keyword == keyword
                and (corpus == "전체" or record.corpus == corpus)
            ]
            included = [record for record in keyword_records if record.decision == "included"]
            counts = Counter(record.tier for record in included)
            files = {record.relative_path for record in included}
            pages = {
                (record.relative_path, record.page)
                for record in included
                if record.page is not None
            }
            unpaged = {
                record.relative_path
                for record in included
                if record.page is None
            }
            summary.append(
                SummaryRow(
                    corpus=corpus,
                    keyword=keyword,
                    original_search_rows=(
                        source_rows[keyword] if corpus in {"NCS", "전체"} else None
                    ),
                    raw_exact=_raw_exact_count(corpus_documents, keyword),
                    excluded_exact=sum(
                        1
                        for record in keyword_records
                        if record.decision == "excluded" and record.tier == "exact"
                    ),
                    valid_exact=counts["exact"],
                    equivalent_added=counts["equivalent"],
                    specific_added=counts["specific"],
                    semantic_total=len(included),
                    file_count=len(files),
                    page_count=len(pages),
                    unpaged_file_count=len(unpaged),
                )
            )
    return AnalysisResult(
        tuple(sources),
        tuple(documents),
        tuple(rules),
        tuple(candidates),
        tuple(matches),
        tuple(summary),
        tuple(input_artifacts or ()),
    )


def audit_candidates(result: AnalysisResult) -> list[CandidateAudit]:
    audits = []
    for candidate in result.candidates:
        accepted = [
            record
            for record in result.matches
            if record.keyword == candidate.keyword
            and record.expression == candidate.expression
            and record.decision == "included"
        ]
        excluded = [
            record
            for record in result.matches
            if record.keyword == candidate.keyword
            and record.expression == candidate.expression
            and record.decision == "excluded"
        ]
        raw_records = []
        if candidate.decision != "included":
            rule = ExpressionRule(
                candidate.keyword,
                candidate.expression,
                candidate.tier,
                candidate.rationale,
                candidate.pattern,
            )
            for document in result.documents:
                raw_records.extend(scan_document(document, [rule]))
        evidence = accepted or excluded or raw_records
        audits.append(
            CandidateAudit(
                keyword=candidate.keyword,
                expression=candidate.expression,
                decision=candidate.decision,
                tier=candidate.tier,
                rationale=candidate.rationale,
                ncs_count=sum(1 for record in (accepted or raw_records) if record.corpus == "NCS"),
                school_count=sum(1 for record in (accepted or raw_records) if record.corpus == "교과서"),
                excluded_count=len(excluded),
                example_corpus=evidence[0].corpus if evidence else None,
                example_path=evidence[0].relative_path if evidence else None,
                example_line=evidence[0].line if evidence else None,
                example_page=evidence[0].page if evidence else None,
                example_context=evidence[0].context if evidence else None,
            )
        )
    return audits


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def artifact_manifest(result: AnalysisResult) -> dict[str, str]:
    source_payload = {
        "keywords": [asdict(source) for source in result.sources],
        "input_artifacts": [
            {
                "kind": artifact.kind,
                "file_count": artifact.file_count,
                "sha256": artifact.sha256,
            }
            for artifact in result.input_artifacts
        ],
        "documents": [
            {
                "corpus": document.corpus,
                "relative_path": document.relative_path,
                "text_sha256": hashlib.sha256(document.text.encode("utf-8")).hexdigest(),
            }
            for document in result.documents
        ],
    }
    return {
        "source_sha256": _canonical_hash(source_payload),
        "rule_sha256": _canonical_hash(
            {
                "rules": [asdict(rule) for rule in result.rules],
                "candidates": [asdict(candidate) for candidate in result.candidates],
            }
        ),
        "detail_sha256": _canonical_hash([asdict(match) for match in result.matches]),
        "summary_sha256": _canonical_hash([asdict(row) for row in result.summary]),
    }


def public_path(p: Path | str, here: Path | None = None, home: Path | None = None) -> str:
    """추적 산출물에 싣는 경로. 저장소 안이면 상대 경로, 홈 아래면 `~/…`, 그 밖은 마지막 이름만 (resegment.public_path 와 같은 규칙).

    문자열 접두가 아니라 realpath 로 견주므로 `/private/var` 같은 별칭도 걸린다. 공개 저장소라 절대 경로는 실리지 않는다.
    """
    rp = os.path.realpath(str(p))
    for base, prefix in (
        (os.path.realpath(str(HERE if here is None else here)), ""),
        (os.path.realpath(os.path.expanduser("~") if home is None else str(home)), "~/"),
    ):
        if rp == base:
            return prefix.rstrip("/") or "."
        if rp.startswith(base.rstrip(os.sep) + os.sep):
            return prefix + os.path.relpath(rp, base).replace(os.sep, "/")
    return os.path.basename(rp)


def _git_info() -> dict[str, object]:
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "unknown", "dirty": None}
    return {"commit": commit, "dirty": dirty}


_PATHISH_RE = re.compile(r"[/\\]|\.(?:xlsx|md|js|json|html)$")


def _scrub_argv_token(token: str) -> str:
    """argv 토큰의 경로를 public_path 로. `--opt=value` 도 값 부분만 걷어낸다 (보안 리뷰: 통째로 realpath 하면 그대로 남는다)."""
    key, sep, value = token.partition("=")
    if sep and key.startswith("--"):
        return key + sep + (public_path(value) if _PATHISH_RE.search(value) else value)
    return public_path(token) if _PATHISH_RE.search(token) else token


def run_manifest(
    result: AnalysisResult,
    argv: list[str],
    force: bool,
    expected_mismatch: list[str],
    git: dict[str, object] | None = None,
    xlsx_out: Path | None = None,
    extra_inputs: list[dict[str, object]] | None = None,
    marker_nonmonotone: list[str] | None = None,
) -> dict[str, object]:
    """실행 정보 — 어느 실행이 정본인지 저장소가 답하게 하는 블록. 경로는 public_path 로만.

    `git_commit` 은 실행이 올라탄 커밋이고 `git_dirty` 는 그 위에 미커밋 변경이 있었는지다. 산출물은 실행 뒤에 커밋되므로
    커밋된 정본 산출물의 manifest 는 언제나 "부모 커밋 + dirty" 를 가리킨다 — 재현은 커밋 뒤 같은 명령을 다시 돌려 가드가 통과하는 것으로 확인한다.
    """
    git = _git_info() if git is None else git
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "git_commit": git["commit"],
        "git_dirty": git["dirty"],
        "command": " ".join(_scrub_argv_token(token) for token in argv),
        "xlsx": os.path.basename(str(xlsx_out)) if xlsx_out else None,
        "python": platform.python_version(),
        "openpyxl": openpyxl.__version__,
        "inputs": [{"kind": a.kind, "count": a.file_count, "sha256": a.sha256} for a in result.input_artifacts] + list(extra_inputs or []),
        "dedup": [{"code": d.code, "kept": d.kept, "dropped": list(d.dropped)} for d in result.dedup],
        "marker_nonmonotone": list(marker_nonmonotone or []),
        "expected": None if force else True,
        "expected_mismatch": list(expected_mismatch),
        "force": force,
    }


def summary_metrics(result: AnalysisResult, manifest: dict[str, str], dictionary: str = DEFAULT_DICTIONARY) -> dict[str, object]:
    """EXPECTED 와 견주는 수치 — 사전 버전·문서 수·총계·등급·등급 출처·후보 판정·중복 제거·해시 4종."""
    rows = [row for row in result.summary if row.corpus in ("NCS", "교과서")]
    included = [record for record in result.matches if record.decision == "included"]
    sources = Counter(record.grade_source for record in included)
    metrics: dict[str, object] = {
        "dictionary": dictionary,
        "documents": {corpus: sum(1 for d in result.documents if d.corpus == corpus) for corpus in ("NCS", "교과서")},
        "totals": {corpus: sum(row.semantic_total for row in rows if row.corpus == corpus) for corpus in ("NCS", "교과서")},
        "grades": {
            corpus: {
                "1": sum(row.grade_1 for row in rows if row.corpus == corpus),
                "2": sum(row.grade_2 for row in rows if row.corpus == corpus),
                "3": sum(row.grade_3 for row in rows if row.corpus == corpus),
                "unpaged": sum(row.grade_unpaged for row in rows if row.corpus == corpus),
            }
            for corpus in ("NCS", "교과서")
        },
        "grade_sources": {key: sources.get(key, 0) for key in GRADE_SOURCES},
        "candidates": dict(Counter(candidate.decision for candidate in result.candidates)),
        "dedup": {record.code: len(record.dropped) for record in result.dedup},
    }
    metrics.update(manifest)
    return metrics


def check_expected(metrics: dict[str, object], expected: dict[str, object] | None = None, prefix: str = "") -> list[str]:
    """EXPECTED 와의 불일치 목록. 비어 있으면 통과. 기대값 None 은 아직 미고정 — 비교하지 않는다."""
    expected = EXPECTED if expected is None else expected
    bad = []
    for key, want in expected.items():
        path = f"{prefix}{key}"
        have = metrics.get(key) if isinstance(metrics, dict) else None
        if isinstance(want, dict):
            bad.extend(check_expected(have if isinstance(have, dict) else {}, want, path + "."))
            if not prefix and key in STRICT_GROUPS and isinstance(have, dict):      # 실측에만 있는 키 — 새 중복 코드·새 판정 상태
                bad.extend(f"{path}.{extra}: {have[extra]} != (absent)" for extra in have if extra not in want)
        elif want is not None and have != want:
            bad.append(f"{path}: {have} != {want}")
    return bad


PREVIOUS_BASIS_SOURCE = "docs/03-analysis/data/reseg_summary.json"
PREVIOUS_BASIS_DATE = "2026-09-06"      # 이전 기준의 채택일(resegment Act-3, 2,189쪽·145 가 확정된 실행). reseg_summary.json 의 meta.run_at 은
                                        # 그 뒤 수치 변화 없이 다시 돈 진단 실행(2026-09-07 marker-offset)이라 별도로 source_run_at 에 싣는다.


def load_previous_basis(path: Path) -> dict[str, object]:
    """이전 기준(페이지 단위, 2026-09-06 재세그먼트)을 payload 에 복사한다 — 렌더러가 브리지 표를 데이터만으로 그리게.

    원본과 어긋나면 하니스(S4)가 잡는다. 여기서는 필요한 키만 옮긴다.
    """
    reseg = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [key for key in ("pages", "page_g", "books", "cases_pages") if key not in reseg]
    if missing:
        raise ValueError(f"이전 기준 파일에 키가 없습니다 ({public_path(path)}): {', '.join(missing)}")
    return {
        "source": public_path(path),
        "date": PREVIOUS_BASIS_DATE,
        "source_run_at": (reseg.get("meta") or {}).get("run_at"),
        "unit": "pages",
        "pages": reseg["pages"],
        "page_g": reseg["page_g"],
        "books": reseg["books"],
        "cases_pages": reseg["cases_pages"],
        "unresolved_pages": (reseg.get("unresolved") or {}).get("pages"),
    }


def summary_payload(
    result: AnalysisResult,
    run: dict[str, object] | None = None,
    previous_basis: dict[str, object] | None = None,
) -> dict[str, object]:
    """dashboard_payload + meta.run + meta.manifest + meta.previous_basis. semantic_recount_data.js 와 semantic_summary.json 이 같은 JSON 을 싣는다."""
    payload = dashboard_payload(result)
    payload["meta"]["manifest"] = artifact_manifest(result)
    if run is not None:
        payload["meta"]["run"] = run
    if previous_basis is not None:
        payload["meta"]["previous_basis"] = previous_basis
    return payload


def _write_text_atomic(path: Path, text: str) -> None:
    """임시 파일에 쓰고 os.replace — 중단·디스크 부족 때 반쪽 산출물이 추적 경로에 남지 않게 (docs/…/*.tmp 는 gitignore)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_summary_json(payload: dict[str, object], path: Path) -> None:
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=1) + "\n")


_ANALYSIS_CSS = (
    'body{font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif;color:#172033;margin:32px;background:#f6f8fb}'
    "main{max-width:1500px;margin:auto;background:white;padding:28px 34px;border-radius:12px;box-shadow:0 2px 12px #0001}"
    "h1{margin-top:0}h2{margin-top:34px;color:#1f4e78}.meta{padding:12px 16px;background:#eef5fb;border-left:4px solid #1f4e78;margin:16px 0 24px;line-height:1.7}"
    "table{border-collapse:collapse;width:100%;font-size:.875rem;margin:12px 0 28px}th{background:#1f4e78;color:white;position:sticky;top:0}"
    "td,th{border:1px solid #cbd5e1;padding:7px;vertical-align:top;text-align:left}td:nth-child(2),td:nth-child(3),td:nth-child(4),td:nth-child(5){white-space:nowrap}"
    ".scroll{overflow:auto}.scroll.tall{max-height:min(850px,80vh)}.scroll:focus-visible{outline:2px solid #1f4e78;outline-offset:2px}"
    "small{color:#52606d}a.card{display:block;padding:16px;margin:12px 0;border:1px solid #cbd5e1;border-radius:8px;color:#1f4e78;text-decoration:none}a.card:hover,a.card:focus-visible{background:#eef5fb}"
    "details{margin:8px 0;border:1px solid #cbd5e1;border-radius:8px;padding:0 12px}summary{cursor:pointer;padding:10px 0;font-weight:600;color:#1f4e78;min-height:44px;box-sizing:border-box}summary:focus-visible{outline:2px solid #1f4e78}"
    "@media(max-width:768px){body{margin:12px}main{padding:16px}}"
)
ANALYSIS_PAGE_NAMES = {"index": "keyword-analysis.html", "NCS": "NCS_키워드검색결과.html", "교과서": "교과서_키워드검색결과.html"}


def _table_html(headers: list[str], rows: list[list[object]]) -> str:
    head = "".join(f"<th>{html.escape(str(v))}</th>" for v in headers)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _analysis_meta_line(payload: dict[str, object]) -> str:
    run = payload["meta"].get("run") or {}
    docs = payload["corpora"]
    parts = [f"NCS 교재 {docs['NCS']['documents']}권 · 교과서 {docs['교과서']['documents']}권"]
    if run.get("xlsx"):
        parts.append(f"기준 파일: {run['xlsx']}")
    if run.get("git_commit"):
        parts.append(f"git {run['git_commit']}{'+' if run.get('git_dirty') else ''} · {run.get('generated_at', '')[:10]}")
    return " · ".join(parts)


def write_analysis_pages(result: AnalysisResult, payload: dict[str, object], docs_dir: Path) -> list[Path]:
    """분리 분석 페이지 3건 — 목차 + 말뭉치별 요약표·상세표. 정본 실행과 같은 데이터에서 나온다 (구 export_keyword_outputs.py 흡수)."""
    docs_dir = Path(docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    meta_line = html.escape(_analysis_meta_line(payload))
    written = []
    for corpus in ("NCS", "교과서"):
        records = [r for r in result.matches if r.decision == "included" and r.corpus == corpus]
        total = len(records)
        counts: dict[str, Counter] = defaultdict(Counter)
        for r in records:
            counts[r.keyword]["전체"] += 1
            if r.grade in (1, 2, 3):
                counts[r.keyword][str(r.grade)] += 1
        summary_rows = []
        for keyword in sorted(counts, key=lambda k: (-counts[k]["전체"], k)):
            c = counts[keyword]
            n = c["전체"]
            summary_rows.append([keyword, f"{n:,}", f"{n / total:.1%}" if total else "0.0%"]
                                + [v for g in ("1", "2", "3") for v in (f"{c[g]:,}", f"{c[g] / n:.1%}" if n else "0.0%")])
        # 상세는 키워드별 닫힌 <details> — 12,536행을 한 표로 두면 모바일 첫 화면 8.1 s (성능 리뷰 실측); 닫힌 details 는 레이아웃에서 빠진다.
        by_keyword: dict[str, list[list[object]]] = defaultdict(list)
        for r in records:
            by_keyword[r.keyword].append([r.relative_path, r.keyword, r.matched_text, r.page if r.page is not None else "", r.grade or "",
                                          r.grade_label, r.grade_reason, r.context])
        detail_headers = ["파일", "키워드", "실제 매칭", "페이지", "통일 등급", "등급명", "등급사유", "문맥"]
        detail_html = "".join(
            f"<details><summary>{html.escape(keyword)} ({len(rows):,}건)</summary>"
            f'<div class="scroll tall" tabindex="0" role="region" aria-label="{html.escape(keyword)} 검색결과 표">{_table_html(detail_headers, rows)}</div></details>'
            for keyword, rows in sorted(by_keyword.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        )
        doc = (
            '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{corpus} 키워드 검색·등급 분석</title><style>{_ANALYSIS_CSS}</style></head><body><main>"
            f"<h1>{corpus} 키워드 검색·등급 분석 결과</h1>"
            f'<div class="meta">{meta_line}<br>검색결과 전체: <strong>{total:,}건</strong> (키워드-표현 매칭 레코드 합계 — 고유 문장·쪽 수가 아니다)<br>비율의 분모: 이 말뭉치의 전체 검색결과</div>'
            "<h2>1. 키워드별 검색결과·비율·등급분류</h2>"
            f'<div class="scroll" tabindex="0" role="region" aria-label="키워드별 검색결과 요약 표">{_table_html(["키워드", "전체", "전체 비율", "등급 1", "등급 1 비율", "등급 2", "등급 2 비율", "등급 3", "등급 3 비율"], summary_rows)}</div>'
            "<h2>2. 개별 키워드 검색결과</h2><small>키워드별로 접혀 있습니다 — 제목을 누르면 파일·실제 매칭·페이지·등급·등급사유·문맥이 펼쳐집니다(브라우저 찾기는 접힌 항목도 검색합니다).</small>"
            + detail_html
            + "</main></body></html>"
        )
        out = docs_dir / ANALYSIS_PAGE_NAMES[corpus]
        _write_text_atomic(out, doc)
        written.append(out)
    index = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>반도체 키워드 검색·등급 분석 결과</title><style>{_ANALYSIS_CSS}main{{max-width:900px}}</style></head><body><main>"
        "<h1>반도체 키워드 검색·등급 분석 결과</h1>"
        f'<div class="meta">{meta_line}<br>등급 분모: 의미 출현건수(연구책임자 결정 2026-09-13). 이전 기준(실제 쪽 단위)은 각 대시보드에 병기.</div>'
        "<h2>분석 결과</h2>"
        f'<a class="card" href="{ANALYSIS_PAGE_NAMES["NCS"]}">NCS 키워드 검색결과·비율·등급분류 결과</a>'
        f'<a class="card" href="{ANALYSIS_PAGE_NAMES["교과서"]}">교과서 키워드 검색결과·비율·등급분류 결과</a>'
        '<h2>대시보드</h2><a class="card" href="index.html">NCS 반도체 교재 대시보드</a><a class="card" href="textbook.html">반도체고 교과서 대시보드</a>'
        "</main></body></html>"
    )
    out = docs_dir / ANALYSIS_PAGE_NAMES["index"]
    _write_text_atomic(out, index)
    written.append(out)
    return written


def _safe_cell(value: object, limit: int = 30000) -> object:
    if not isinstance(value, str):
        return value
    value = value[:limit]
    return "'" + value if value.startswith("=") else value


def _append_row(worksheet, values: list[object] | tuple[object, ...]) -> None:
    worksheet.append([_safe_cell(value) for value in values])


def _style_table(worksheet, freeze: str = "A2") -> None:
    worksheet.freeze_panes = freeze
    if worksheet.max_row >= 1 and worksheet.max_column >= 1:
        fill = PatternFill("solid", fgColor="1F4E78")
        for cell in worksheet[1]:
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        worksheet.auto_filter.ref = worksheet.dimensions
    for column in range(1, worksheet.max_column + 1):
        values = [
            len(str(worksheet.cell(row=row, column=column).value or ""))
            for row in range(1, min(worksheet.max_row, 300) + 1)
        ]
        width = min(60, max(10, max(values, default=10) + 2))
        worksheet.column_dimensions[get_column_letter(column)].width = width
    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def _match_index(result: AnalysisResult):
    return Counter(
        (record.keyword, record.expression, record.corpus, record.decision)
        for record in result.matches
    )


def _first_evidence(result: AnalysisResult, keyword: str, expression: str):
    return next(
        (
            record
            for record in result.matches
            if record.keyword == keyword
            and record.expression == expression
            and record.decision == "included"
        ),
        None,
    )


_TEXTBOOK_DISPLAY_NAMES = (
    ("반도체기초기술1크리아트", "반도체 기초기술 1"),
    ("반도체기초기술2크리아트", "반도체 기초기술 2"),
    ("반도체기초렛유인", "반도체 기초"),
    ("반도체공정기초렛유인", "반도체 공정기초"),
    ("반도체장비유지보수충남반도체고", "반도체 장비 유지보수"),
    ("반도체인프라일반서울시교육청", "반도체 인프라 일반"),
    ("반도체포토에칭에이치앤지", "반도체 포토에칭"),
    ("반도체조립검사에이치앤지", "반도체 조립검사"),
    ("반도체박막확산에이치앤지", "반도체 박막확산"),
)


def _dashboard_group(corpus: str, relative_path: str) -> str:
    normalized = unicodedata.normalize("NFC", relative_path)
    if corpus == "NCS":
        return normalized.split("/", 1)[0]
    compact = re.sub(r"[^0-9A-Za-z가-힣]", "", normalized).casefold()
    for fragment, title in _TEXTBOOK_DISPLAY_NAMES:
        if fragment.casefold() in compact:
            return title
    return _TIMESTAMP_PREFIX_RE.sub("", Path(normalized).stem).replace("_", " ").strip()


def dashboard_payload(result: AnalysisResult) -> dict[str, object]:
    included = [record for record in result.matches if record.decision == "included"]
    summary = {(row.corpus, row.keyword): row for row in result.summary}
    expressions = defaultdict(list)
    detected_rules = {(record.keyword, record.expression) for record in included}
    for rule in result.rules:
        if rule.tier != "exact" and (rule.keyword, rule.expression) in detected_rules:
            expressions[rule.keyword].append(rule.expression)

    keywords = []
    for source in result.sources:
        item = {"name": source.keyword, "expressions": expressions[source.keyword], "corpora": {}}
        for corpus in ("NCS", "교과서"):
            row = summary.get((corpus, source.keyword))
            excluded = sum(
                1
                for record in result.matches
                if record.corpus == corpus
                and record.keyword == source.keyword
                and record.decision == "excluded"
                and record.tier == "exact"
            )
            item["corpora"][corpus] = {
                "total": row.semantic_total if row else 0,
                "exact": row.valid_exact if row else 0,
                "equivalent": row.equivalent_added if row else 0,
                "specific": row.specific_added if row else 0,
                "excluded": excluded,
                "grades": {
                    "1": row.grade_1 if row else 0,
                    "2": row.grade_2 if row else 0,
                    "3": row.grade_3 if row else 0,
                    "unpaged": row.grade_unpaged if row else 0,
                },
            }
        keywords.append(item)

    corpora = {}
    for corpus in ("NCS", "교과서"):
        corpus_rows = [
            summary[(corpus, source.keyword)]
            for source in result.sources
            if (corpus, source.keyword) in summary
        ]
        group_records = defaultdict(list)
        for record in included:
            if record.corpus == corpus:
                group_records[_dashboard_group(corpus, record.relative_path)].append(record)
        documents_by_group = defaultdict(set)
        for document in result.documents:
            if document.corpus == corpus:
                documents_by_group[_dashboard_group(corpus, document.relative_path)].add(document.relative_path)
        groups = []
        for name in sorted(group_records):
            records = group_records[name]
            counts = Counter(record.grade for record in records)
            groups.append(
                {
                    "name": name,
                    "documents": len(documents_by_group[name]),
                    "total": len(records),
                    "grades": {"1": counts[1], "2": counts[2], "3": counts[3], "unpaged": counts[None]},
                }
            )
        source_counts = Counter(record.grade_source for record in included if record.corpus == corpus)
        corpora[corpus] = {
            "documents": sum(1 for document in result.documents if document.corpus == corpus),
            "total": sum(row.semantic_total for row in corpus_rows),
            "graded": sum(row.grade_1 + row.grade_2 + row.grade_3 for row in corpus_rows),
            "grade_sources": {key: source_counts.get(key, 0) for key in GRADE_SOURCES},
            "grades": {
                "1": sum(row.grade_1 for row in corpus_rows),
                "2": sum(row.grade_2 for row in corpus_rows),
                "3": sum(row.grade_3 for row in corpus_rows),
                "unpaged": sum(row.grade_unpaged for row in corpus_rows),
            },
            "groups": groups,
        }

    return {
        "meta": {
            "generated": date.today().isoformat(),
            "denominator": "occurrences",
            "gradeLabels": {str(key): value for key, value in GRADE_LABEL.items()},
        },
        "corpora": corpora,
        "keywords": keywords,
        "status": dict(Counter(candidate.decision for candidate in result.candidates)),
    }


def write_dashboard_data(result: AnalysisResult, path: Path, payload: dict[str, object] | None = None) -> None:
    """window.SEMANTIC_RECOUNT — semantic_summary.json 과 같은 JSON. 헤더는 실행 manifest 에서 온다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = summary_payload(result) if payload is None else payload
    run = payload["meta"].get("run") or {}
    stamp = f"git {run['git_commit']}, {run.get('generated_at', '')}" if run.get("git_commit") else date.today().isoformat()
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    _write_text_atomic(
        path,
        f"/* Generated by semantic_keyword_recount.py ({stamp}). Same JSON as docs/03-analysis/data/semantic_summary.json. Grade denominator: occurrences. */\n"
        f"window.SEMANTIC_RECOUNT={body};\n",
    )


def _file_rows(result: AnalysisResult, corpus: str):
    keywords = [source.keyword for source in result.sources]
    included = [
        record
        for record in result.matches
        if record.corpus == corpus and record.decision == "included"
    ]
    grouped = defaultdict(list)
    for record in included:
        grouped[(record.relative_path, record.keyword)].append(record)
    documents = sorted(
        (document for document in result.documents if document.corpus == corpus),
        key=lambda document: document.relative_path,
    )
    for document in documents:
        for keyword in keywords:
            records = grouped[(document.relative_path, keyword)]
            counts = Counter(record.tier for record in records)
            grades = Counter(record.grade for record in records)
            yield (
                document.relative_path,
                keyword,
                counts["exact"],
                counts["equivalent"],
                counts["specific"],
                len(records),
                len({record.page for record in records if record.page is not None}),
                int(any(record.page is None for record in records)),
                grades[1],
                grades[2],
                grades[3],
                grades[None],
            )


def write_workbook(result: AnalysisResult, path: Path, run: dict[str, object] | None = None, audits: list[CandidateAudit] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = artifact_manifest(result)
    audits = audit_candidates(result) if audits is None else audits       # 6 s 짜리 전수 재검색 — run_census 가 한 번만 계산해 넘긴다
    counts = _match_index(result)
    workbook = Workbook()
    workbook.remove(workbook.active)

    readme = workbook.create_sheet("README")
    readme_rows = [
        ("항목", "내용"),
        ("문서명", "30개 독립 키워드 의미 단위 재검산"),
        ("생성일", date.today().isoformat()),
        ("핵심 원칙", "기존 30개 키워드는 통합하거나 서로의 확장 표현으로 사용하지 않음"),
        ("계수 단위", "원문 정확 문자열, 동음이의 제외, 유효 정확, 동등 표현, 구체 표현을 분리"),
        ("중복 처리", "같은 키워드 안에서만 왼쪽부터 긴 표현을 우선하며 겹친 구간은 한 번 계수"),
        ("원본 비교", "원본 검색행 수와 새 출현 횟수는 단위가 달라 증감률을 계산하지 않음"),
        ("페이지", "페이지 마커가 없는 출현은 페이지 미확정으로 표시하되 등급은 그 줄의 문맥으로 판정 (요약 시트의 '페이지 미확정 파일 수' 열)"),
        ("등급 단위", "각 의미 출현에 해당 페이지의 통일 등급을 결합하며 등급 비율은 출현건수를 분모로 계산"),
        ("등급 계보", "기존 페이지는 원본 등급을 상속하고 새 검출 페이지는 기존 기준선 규칙으로 판정"),
        ("마커 없는 출현", "그 줄의 문맥으로 판정(unpaged-context), 문맥이 비면 등급1(unpaged-fallback) — 연구책임자 결정 2026-09-13, 미배정을 두지 않는다. 총계는 키워드-표현 매칭 레코드 합계이지 고유 문장·쪽 수가 아님"),
    ]
    for key, value in manifest.items():
        readme_rows.append((key, value))
    for row in readme_rows:
        _append_row(readme, row)
    _style_table(readme)

    inputs = workbook.create_sheet("입력정보")
    _append_row(inputs, ("구분", "경로/키워드", "파일 수/검색행 수", "헤더 여부", "SHA-256"))
    for artifact in result.input_artifacts:
        _append_row(inputs, (artifact.kind, artifact.path, artifact.file_count, "", artifact.sha256))
    for source in result.sources:
        _append_row(inputs, ("원본 시트", source.keyword, source.search_rows, "있음" if source.has_header else "없음", ""))
    for key, value in (run or {}).items():
        _append_row(inputs, ("실행 정보", key, json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value, "", ""))
    _style_table(inputs)

    summary = workbook.create_sheet("요약")
    _append_row(
        summary,
        (
            "말뭉치", "키워드", "원본 검색행 수", "원문 정확 문자열", "동음이의 제외",
            "유효 정확 표현", "동등 표현 추가", "구체 표현 추가", "최종 의미 출현 수",
            "검출 파일 수", "검출 페이지 수", "페이지 미확정 파일 수",
            "등급1 출현", "등급2 출현", "등급3 출현", "등급 미확정 출현",
        ),
    )
    for row in result.summary:
        _append_row(summary, tuple(asdict(row).values()))
    _style_table(summary)

    included_sheet = workbook.create_sheet("포함표현")
    _append_row(
        included_sheet,
        ("키워드", "포함 표현", "계층", "정규식", "제외 조건", "판정 근거", "NCS", "교과서", "전체", "대표 출처", "대표 문맥"),
    )
    for rule in result.rules:
        evidence = _first_evidence(result, rule.keyword, rule.expression)
        ncs = counts[(rule.keyword, rule.expression, "NCS", "included")]
        school = counts[(rule.keyword, rule.expression, "교과서", "included")]
        _append_row(
            included_sheet,
            (
                rule.keyword,
                rule.expression,
                rule.tier,
                rule.pattern or re.escape(rule.expression),
                " | ".join(rule.exclude_patterns),
                rule.rationale,
                ncs,
                school,
                ncs + school,
                f"{evidence.corpus}:{evidence.relative_path}:{evidence.line}" if evidence else "미검출",
                evidence.context if evidence else "",
            ),
        )
    _style_table(included_sheet)

    excluded_sheet = workbook.create_sheet("보류제외")
    _append_row(
        excluded_sheet,
        ("키워드", "후보 표현", "판정", "후보 계층", "판정 근거", "NCS 원문 출현", "교과서 원문 출현", "규칙 제외 건", "대표 출처", "대표 문맥"),
    )
    for audit in audits:
        if audit.decision == "included":
            continue
        _append_row(
            excluded_sheet,
            (
                audit.keyword,
                audit.expression,
                audit.decision,
                audit.tier,
                audit.rationale,
                audit.ncs_count,
                audit.school_count,
                audit.excluded_count,
                f"{audit.example_corpus}:{audit.example_path}:{audit.example_line}" if audit.example_path else "미출현",
                audit.example_context or "",
            ),
        )
    _style_table(excluded_sheet)

    file_headers = (
        "파일", "키워드", "유효 정확", "동등 표현", "구체 표현", "최종 의미 출현 수",
        "검출 페이지 수", "페이지 미확정", "등급1 출현", "등급2 출현", "등급3 출현", "등급 미확정 출현",
    )
    for corpus, sheet_name in (("NCS", "NCS_파일별"), ("교과서", "교과서_파일별")):
        worksheet = workbook.create_sheet(sheet_name)
        _append_row(worksheet, file_headers)
        for row in _file_rows(result, corpus):
            _append_row(worksheet, row)
        _style_table(worksheet)

    detail_headers = (
        "파일", "키워드", "등록 표현", "실제 매칭", "계층", "줄", "페이지", "판정 근거", "문맥",
        "통일 등급", "등급명", "등급사유", "등급 출처",
    )
    for corpus, sheet_name in (("NCS", "NCS_매칭상세"), ("교과서", "교과서_매칭상세")):
        worksheet = workbook.create_sheet(sheet_name)
        _append_row(worksheet, detail_headers)
        for record in result.matches:
            if record.corpus != corpus or record.decision != "included":
                continue
            _append_row(
                worksheet,
                (
                    record.relative_path, record.keyword, record.expression, record.matched_text,
                    record.tier, record.line, record.page, record.reason, record.context,
                    record.grade, record.grade_label, record.grade_reason,
                    GRADE_SOURCE_LABEL.get(record.grade_source, record.grade_source),
                ),
            )
        _style_table(worksheet)

    evidence_sheet = workbook.create_sheet("문맥근거")
    _append_row(evidence_sheet, ("키워드", "표현", "판정", "말뭉치", "파일", "줄", "페이지", "근거", "문맥"))
    for audit in audits:
        _append_row(
            evidence_sheet,
            (audit.keyword, audit.expression, audit.decision, audit.example_corpus, audit.example_path, audit.example_line, audit.example_page, audit.rationale, audit.example_context),
        )
    for record in result.matches:
        if record.decision == "excluded" and record.tier == "exact":
            _append_row(evidence_sheet, (record.keyword, record.expression, "excluded-exact", record.corpus, record.relative_path, record.line, record.page, record.reason, record.context))
    _style_table(evidence_sheet)

    tmp = path.with_name(path.name + ".tmp")
    workbook.save(tmp)
    os.replace(tmp, path)


def _markdown_cell(value: object, limit: int = 180) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("|", "\\|")[:limit]


def write_report(result: AnalysisResult, path: Path, run: dict[str, object] | None = None, audits: list[CandidateAudit] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = artifact_manifest(result)
    audits = audit_candidates(result) if audits is None else audits       # 6 s 짜리 전수 재검색 — run_census 가 한 번만 계산해 넘긴다
    counts = _match_index(result)
    rules_by_keyword = defaultdict(list)
    for rule in result.rules:
        rules_by_keyword[rule.keyword].append(rule)
    candidates_by_keyword = defaultdict(list)
    for audit in audits:
        candidates_by_keyword[audit.keyword].append(audit)

    lines = [
        "# 30개 독립 키워드 의미 단위 재검산 보고서",
        "",
        f"- 생성일: {date.today().isoformat()}",
        f"- 조사 문서: NCS {sum(d.corpus == 'NCS' for d in result.documents)}개, 교과서 {sum(d.corpus == '교과서' for d in result.documents)}개",
        f"- 기준 키워드: {len(result.sources)}개",
        "",
        "## 조사 범위와 방법",
        "",
        "Markdown 본문을 NFC로 정규화해 전수 검색하고, 영문은 대소문자를 구분하지 않았다. 페이지 주석과 이미지 URL만 있는 줄은 계수하지 않았다. 각 매칭에는 파일·줄·페이지·실제 표현·문맥을 남겼다.",
        "기존에 판정된 페이지는 통일 등급 1~3을 승계하고, 새로 검출된 페이지만 같은 기준선 규칙으로 판정했다. 등급별 수치는 페이지 수가 아니라 의미 출현건수다.",
        "",
        "## 키워드 독립 원칙",
        "",
        "기존 30개 키워드는 의미가 가까워도 병합하지 않았고 서로의 포함 표현으로 등록하지 않았다. 예를 들어 `MSDS`와 `물질안전보건자료`, `PSM`과 `공정안전관리`는 각각 독립 집계했다. 신규 표현도 하나의 기존 키워드에만 배정했다. 30개 키워드를 합친 값은 '키워드-표현 매칭 레코드 합계'로만 쓰며 고유 문장·쪽 수가 아니다.",
        "",
        "## 포함·제외 기준",
        "",
        "- 포함: 같은 개념을 직접 지칭하는 표기 변형·영문·동의어 또는 개념을 명백히 함의하는 구체 유형",
        "- 제외: 동음이의, 회로·공정·품질상의 비안전 의미, 다른 키워드 자체, 긴 표현 내부의 중복 부분",
        "- 보류: 문맥에 따라 뜻이 갈리지만 안정적인 자동 판정 조건을 만들기 어려운 표현",
        f"- 미출현: 사전상 가능하지만 {len(result.documents)}개 조사 원문에서 확인되지 않은 표현",
        "",
        "## 키워드별 집계",
        "",
        "| 말뭉치 | 키워드 | 원본 검색행 | 원문 정확 | 제외 | 유효 정확 | 동등 추가 | 구체 추가 | 최종 의미 출현 | 파일 | 페이지 | 페이지 미확정 | 등급1 출현 | 등급2 출현 | 등급3 출현 | 등급 미확정 출현 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result.summary:
        lines.append(
            "| " + " | ".join(
                _markdown_cell(value)
                for value in (
                    row.corpus, row.keyword, row.original_search_rows, row.raw_exact,
                    row.excluded_exact, row.valid_exact, row.equivalent_added,
                    row.specific_added, row.semantic_total, row.file_count,
                    row.page_count, row.unpaged_file_count, row.grade_1,
                    row.grade_2, row.grade_3, row.grade_unpaged,
                )
            ) + " |"
        )

    lines.extend(["", "## 말뭉치별 확장 차이", ""])
    for corpus in ("NCS", "교과서"):
        expanded = sorted(
            (
                (row.equivalent_added + row.specific_added, row.keyword)
                for row in result.summary
                if row.corpus == corpus and row.equivalent_added + row.specific_added > 0
            ),
            reverse=True,
        )[:5]
        lines.append(
            f"- {corpus}: "
            + ", ".join(f"`{keyword}` +{added}건" for added, keyword in expanded)
            + "에서 의미 확장분이 가장 컸다. 말뭉치 크기가 다르므로 두 자료의 절대 건수는 비율처럼 해석하지 않는다."
        )

    lines.extend(["", "## 키워드별 포함 표현", ""])
    for source in result.sources:
        keyword = source.keyword
        accepted = [rule for rule in rules_by_keyword[keyword] if rule.tier != "exact"]
        held = [audit for audit in candidates_by_keyword[keyword] if audit.decision != "included"]
        lines.extend([f"### {keyword}", ""])
        if accepted:
            lines.append(
                "포함: "
                + ", ".join(
                    f"`{rule.expression}`({rule.tier}, NCS {counts[(keyword, rule.expression, 'NCS', 'included')]}건/교과서 {counts[(keyword, rule.expression, '교과서', 'included')]}건)"
                    for rule in accepted
                )
            )
        else:
            lines.append("포함 확장 표현 없음(기존 정확 표현만 집계).")
        lines.append("")
        if held:
            lines.append("보류·제외·미출현: " + ", ".join(f"`{audit.expression}`({audit.decision}: {audit.rationale})" for audit in held))
            lines.append("")

    lines.extend(
        [
            "## 주요 문맥 판정",
            "",
            "- `부상`: ‘부상하다’는 상승·등장 의미로 제외하고, 신체 `상해`, `injury`, `다치다`, 기술 영상 문맥을 뺀 `화상`을 포함했다.",
            "- `누출`: 전류·회로·소자 등의 전기 `누설`은 제외하고 가스·진공·배관·필터 등 물리적 누설을 포함했다.",
            "- `안전`, `보건`, `안전보건`: 다른 기존 키워드인 법률명·자료명 내부의 문자열은 독립 집계를 위해 제외했다.",
            "- `소음`, `진동`: 신호 잡음과 부품·분자 진동처럼 안전 유해 의미가 아닌 명시적 문맥을 제외했다.",
            "",
            "## 재현성 해시",
            "",
        ]
    )
    for key, value in manifest.items():
        lines.append(f"- `{key}`: `{value}`")
    if run:
        lines.extend(["", "## 실행 정보", ""])
        for key, value in run.items():
            lines.append(f"- `{key}`: `{json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value}`")
    lines.extend(
        [
            "",
            "## 한계와 후속 검토",
            "",
            "원본 워크북은 문장·표·제목 행 수이고 새 결과는 실제 표현 출현 수이므로 직접 증감률로 해석할 수 없다. 페이지 마커가 없는 출현은 그 줄의 문맥으로 판정하고 문맥이 비면 등급1을 배정했다(연구책임자 결정 2026-09-13, 미배정을 두지 않는다; 등급 출처 `unpaged-context`/`unpaged-fallback` 로 구분). 보류 표현은 향후 사람이 목적별 문맥 범위를 정하면 별도 규칙으로 재검토할 수 있다.",
            "",
        ]
    )
    _write_text_atomic(path, "\n".join(lines))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _document_set_sha256(documents: list[Document]) -> str:
    return _canonical_hash(
        [
            {
                "corpus": document.corpus,
                "path": document.relative_path,
                "sha256": hashlib.sha256(document.text.encode("utf-8")).hexdigest(),
            }
            for document in documents
        ]
    )


def run_census(
    source_workbook: Path,
    ncs_root: Path,
    school_root: Path,
    xlsx_out: Path,
    report_out: Path,
    ncs_grade_workbook: Path | None = None,
    school_grade_workbook: Path | None = None,
    dashboard_data_out: Path | None = None,
    summary_out: Path | None = None,
    analysis_dir: Path | None = None,
    previous_basis: Path | None = None,
    force: bool = False,
    expected: dict[str, object] | None = None,
    argv: list[str] | None = None,
    git: dict[str, object] | None = None,
    dictionary: str = DEFAULT_DICTIONARY,
) -> AnalysisResult:
    """정본 실행 — 산출물 전부를 한 번에 쓴다. EXPECTED 와 어긋나면 force 없이는 아무것도 쓰지 않는다.

    정본이 아닌 사전 버전(--dictionary v1|v2)은 변형 실행이다: 추적 산출물·기본 이름 경로를 거부하고,
    EXPECTED 불일치는 기록만 한다(resegment --marker-correct 규약).
    """
    _check_version(dictionary)
    expected = EXPECTED if expected is None else expected
    variant = dictionary != DEFAULT_DICTIONARY
    if variant:
        for label, out in (("xlsx_out", xlsx_out), ("report_out", report_out), ("dashboard_data_out", dashboard_data_out), ("summary_out", summary_out), ("analysis_dir", analysis_dir)):
            if out is None:
                continue
            rp = os.path.realpath(str(out))
            under_docs = rp.startswith(os.path.realpath(str(HERE / "docs")) + os.sep)
            default_name = re.fullmatch(r"semantic_keyword_recount_\d{8}(?:_report)?\.(?:xlsx|md)", os.path.basename(rp)) is not None
            if under_docs or default_name:
                raise ValueError(f"사전 변형({dictionary})은 추적 산출물·정본 기본 이름 경로에 쓸 수 없습니다: {label}={public_path(out)}")
    source_workbook, ncs_root, school_root = Path(source_workbook), Path(ncs_root), Path(school_root)
    if not source_workbook.is_file():
        raise FileNotFoundError(f"키워드 등록 워크북을 찾을 수 없습니다: {public_path(source_workbook)}")
    for label, root in (("NCS", ncs_root), ("교과서", school_root)):
        if not root.is_dir():
            raise FileNotFoundError(f"{label} Markdown 루트를 찾을 수 없습니다: {public_path(root)}")
    ncs_grade_workbook = Path(ncs_grade_workbook or source_workbook)
    school_grade_workbook = Path(
        school_grade_workbook
        or Path(source_workbook).parent / "ncs_keywords_in_markdown_results_교과서_results_20260415.xlsx"
    )
    if not school_grade_workbook.is_file():
        raise FileNotFoundError(f"교과서 등급 워크북을 찾을 수 없습니다: {public_path(school_grade_workbook)}")
    sources = read_keyword_workbook(source_workbook)
    keywords = [source.keyword for source in sources]
    if tuple(keywords) != EXPECTED_KEYWORDS:
        raise ValueError("원본 워크북의 30개 키워드 또는 순서가 승인 명세와 다릅니다.")
    ncs_documents, dedup = select_ncs_documents(load_documents(ncs_root, "NCS"))
    school_documents = load_documents(school_root, "교과서")
    zero_based = check_marker_base(ncs_documents + school_documents)
    if zero_based:
        raise ValueError("1 미만 페이지 마커(0-based) — shift_page_markers.py 로 +1 한 뒤 다시 실행하십시오: " + "; ".join(zero_based))
    want_docs = expected.get("documents") if isinstance(expected, dict) else None
    if want_docs and (len(ncs_documents), len(school_documents)) != (want_docs.get("NCS"), want_docs.get("교과서")):
        raise ValueError(
            f"입력 Markdown 수가 정본 코퍼스와 다릅니다: NCS={len(ncs_documents)}, 교과서={len(school_documents)} (기대 {want_docs})"
        )
    documents = ncs_documents + school_documents
    rules = build_default_rules(keywords, version=dictionary)
    candidates = default_candidate_decisions(version=dictionary)
    artifacts = [
        InputArtifact("키워드 등록 워크북", public_path(source_workbook), 1, _file_sha256(source_workbook)),
        InputArtifact("NCS 등급 워크북", public_path(ncs_grade_workbook), 1, _file_sha256(ncs_grade_workbook)),
        InputArtifact("교과서 등급 워크북", public_path(school_grade_workbook), 1, _file_sha256(school_grade_workbook)),
        InputArtifact("NCS Markdown", public_path(ncs_root), len(ncs_documents), _document_set_sha256(ncs_documents)),
        InputArtifact("교과서 Markdown", public_path(school_root), len(school_documents), _document_set_sha256(school_documents)),
    ]
    result = aggregate_matches(sources, documents, rules, candidates, artifacts)
    result = assign_match_grades(
        result,
        load_existing_grades(ncs_grade_workbook, school_grade_workbook),
    )
    result = replace(result, dedup=tuple(dedup))
    manifest = artifact_manifest(result)
    mismatch = check_expected(summary_metrics(result, manifest, dictionary=dictionary), expected)
    if mismatch and not force and not variant:
        print("EXPECTED 불일치 — 산출물을 쓰지 않습니다 (--force 로 강제, 그 뒤 EXPECTED 를 갱신):", file=sys.stderr)
        for line in mismatch:
            print("  " + line, file=sys.stderr)
        raise SystemExit(1)
    basis = load_previous_basis(previous_basis) if previous_basis is not None else None
    extra_inputs = [{"kind": "이전 기준", "count": 1, "sha256": _file_sha256(previous_basis)}] if previous_basis is not None else []
    run = run_manifest(
        result, argv if argv is not None else sys.argv, force or variant, mismatch, git=git, xlsx_out=xlsx_out,
        extra_inputs=extra_inputs, marker_nonmonotone=nonmonotone_markers(documents),
    )
    run["dictionary"] = dictionary
    payload = summary_payload(result, run=run, previous_basis=basis)
    audits = audit_candidates(result)
    write_workbook(result, xlsx_out, run=run, audits=audits)
    write_report(result, report_out, run=run, audits=audits)
    if dashboard_data_out is not None:
        write_dashboard_data(result, dashboard_data_out, payload=payload)
    if summary_out is not None:
        write_summary_json(payload, summary_out)
    if analysis_dir is not None:
        write_analysis_pages(result, payload, analysis_dir)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-workbook", type=Path, required=True)
    parser.add_argument("--ncs-root", type=Path, required=True)
    parser.add_argument("--school-root", type=Path, required=True)
    parser.add_argument("--xlsx-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    parser.add_argument("--ncs-grade-workbook", type=Path, help="기존 NCS 등급 워크북 (기본: --source-workbook)")
    parser.add_argument("--school-grade-workbook", type=Path, help="기존 교과서 등급 워크북")
    parser.add_argument("--dashboard-data-out", type=Path, help="정적 대시보드 JavaScript 데이터 출력 (docs/semantic_recount_data.js)")
    parser.add_argument("--summary-out", type=Path, help="추적 요약 JSON (docs/03-analysis/data/semantic_summary.json)")
    parser.add_argument("--analysis-dir", type=Path, help="분리 분석 HTML 3건을 쓸 폴더 (docs)")
    parser.add_argument("--previous-basis", type=Path, help="이전 기준 reseg_summary.json — payload 에 복사해 브리지 표를 그린다")
    parser.add_argument("--force", action="store_true", help="EXPECTED 불일치여도 쓴다 (manifest 에 기록됨; 그 뒤 EXPECTED 를 갱신할 것)")
    parser.add_argument("--dictionary", choices=DICTIONARY_VERSIONS, default=DEFAULT_DICTIONARY, help="사전 버전 — 정본이 아니면 변형 실행(추적 경로 거부)")
    args = parser.parse_args()
    result = run_census(
        args.source_workbook,
        args.ncs_root,
        args.school_root,
        args.xlsx_out,
        args.report_out,
        ncs_grade_workbook=args.ncs_grade_workbook,
        school_grade_workbook=args.school_grade_workbook,
        dashboard_data_out=args.dashboard_data_out,
        summary_out=args.summary_out,
        analysis_dir=args.analysis_dir,
        previous_basis=args.previous_basis,
        force=args.force,
        dictionary=args.dictionary,
    )
    manifest = artifact_manifest(result)
    metrics = summary_metrics(result, manifest)
    print(f"완료: 키워드 {len(result.sources)}개, 문서 {len(result.documents)}개, 상세 {len(result.matches)}건")
    print("측정값 (EXPECTED 고정용):")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
