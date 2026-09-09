#!/usr/bin/env python3
"""Meaning-aware recount of 30 independent safety keywords in Markdown corpora."""

import argparse
from dataclasses import asdict, dataclass
from collections import defaultdict
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


PAGE_MARKER_RE = re.compile(r"^\s*<!--\s*page:\s*(\d+)\s*-->\s*$", re.IGNORECASE)
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


@dataclass(frozen=True)
class CandidateDecision:
    keyword: str
    expression: str
    decision: str
    tier: str
    rationale: str
    pattern: str | None = None
    exclude_patterns: tuple[str, ...] = ()


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
            for keyword, compiled_rules in by_keyword.items():
                included_candidates = []
                excluded_candidates = []
                for rule_index, rule, pattern in compiled_rules:
                    exclusion_spans = []
                    for exclusion in rule.exclude_patterns:
                        exclusion_spans.extend(
                            (match.start(), match.end())
                            for match in re.finditer(exclusion, line, re.IGNORECASE)
                        )
                    for match in pattern.finditer(line):
                        item = (match.start(), match.end(), rule_index, rule, match.group(0))
                        if any(_overlaps((match.start(), match.end()), span) for span in exclusion_spans):
                            excluded_candidates.append(item)
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

                for start, end, _, rule, matched_text in sorted(excluded_candidates):
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
                            reason="동음이의 또는 비대상 문맥 제외",
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


def default_candidate_decisions() -> list[CandidateDecision]:
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


def build_default_rules(keywords: list[str]) -> list[ExpressionRule]:
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
            exclude_patterns=exclusions.get(keyword, ()),
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
        )
        for candidate in default_candidate_decisions()
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
            yield (
                document.relative_path,
                keyword,
                counts["exact"],
                counts["equivalent"],
                counts["specific"],
                len(records),
                len({record.page for record in records if record.page is not None}),
                int(any(record.page is None for record in records)),
            )


def write_workbook(result: AnalysisResult, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = artifact_manifest(result)
    audits = audit_candidates(result)
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
        ("페이지", "페이지 마커가 없는 파일의 매칭은 페이지 미확정 파일 수로 별도 표시"),
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
    _style_table(inputs)

    summary = workbook.create_sheet("요약")
    _append_row(
        summary,
        (
            "말뭉치", "키워드", "원본 검색행 수", "원문 정확 문자열", "동음이의 제외",
            "유효 정확 표현", "동등 표현 추가", "구체 표현 추가", "최종 의미 출현 수",
            "검출 파일 수", "검출 페이지 수", "페이지 미확정 파일 수",
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

    file_headers = ("파일", "키워드", "유효 정확", "동등 표현", "구체 표현", "최종 의미 출현 수", "검출 페이지 수", "페이지 미확정")
    for corpus, sheet_name in (("NCS", "NCS_파일별"), ("교과서", "교과서_파일별")):
        worksheet = workbook.create_sheet(sheet_name)
        _append_row(worksheet, file_headers)
        for row in _file_rows(result, corpus):
            _append_row(worksheet, row)
        _style_table(worksheet)

    detail_headers = ("파일", "키워드", "등록 표현", "실제 매칭", "계층", "줄", "페이지", "판정 근거", "문맥")
    for corpus, sheet_name in (("NCS", "NCS_매칭상세"), ("교과서", "교과서_매칭상세")):
        worksheet = workbook.create_sheet(sheet_name)
        _append_row(worksheet, detail_headers)
        for record in result.matches:
            if record.corpus != corpus or record.decision != "included":
                continue
            _append_row(
                worksheet,
                (record.relative_path, record.keyword, record.expression, record.matched_text, record.tier, record.line, record.page, record.reason, record.context),
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

    workbook.save(path)


def _markdown_cell(value: object, limit: int = 180) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", " ").replace("|", "\\|")[:limit]


def write_report(result: AnalysisResult, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = artifact_manifest(result)
    audits = audit_candidates(result)
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
        "",
        "## 키워드 독립 원칙",
        "",
        "기존 30개 키워드는 의미가 가까워도 병합하지 않았고 서로의 포함 표현으로 등록하지 않았다. 예를 들어 `MSDS`와 `물질안전보건자료`, `PSM`과 `공정안전관리`는 각각 독립 집계했다. 신규 표현도 하나의 기존 키워드에만 배정했으며, 30개 키워드를 합산한 총계는 만들지 않았다.",
        "",
        "## 포함·제외 기준",
        "",
        "- 포함: 같은 개념을 직접 지칭하는 표기 변형·영문·동의어 또는 개념을 명백히 함의하는 구체 유형",
        "- 제외: 동음이의, 회로·공정·품질상의 비안전 의미, 다른 키워드 자체, 긴 표현 내부의 중복 부분",
        "- 보류: 문맥에 따라 뜻이 갈리지만 안정적인 자동 판정 조건을 만들기 어려운 표현",
        "- 미출현: 사전상 가능하지만 98개 조사 원문에서 확인되지 않은 표현",
        "",
        "## 키워드별 집계",
        "",
        "| 말뭉치 | 키워드 | 원본 검색행 | 원문 정확 | 제외 | 유효 정확 | 동등 추가 | 구체 추가 | 최종 의미 출현 | 파일 | 페이지 | 페이지 미확정 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result.summary:
        lines.append(
            "| " + " | ".join(
                _markdown_cell(value)
                for value in (
                    row.corpus, row.keyword, row.original_search_rows, row.raw_exact,
                    row.excluded_exact, row.valid_exact, row.equivalent_added,
                    row.specific_added, row.semantic_total, row.file_count,
                    row.page_count, row.unpaged_file_count,
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
    lines.extend(
        [
            "",
            "## 한계와 후속 검토",
            "",
            "원본 워크북은 문장·표·제목 행 수이고 새 결과는 실제 표현 출현 수이므로 직접 증감률로 해석할 수 없다. 페이지 마커가 없는 NCS 파일은 페이지 수 대신 페이지 미확정 파일 수로 표시했다. 보류 표현은 향후 사람이 목적별 문맥 범위를 정하면 별도 규칙으로 재검토할 수 있다.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


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
) -> AnalysisResult:
    sources = read_keyword_workbook(source_workbook)
    keywords = [source.keyword for source in sources]
    if tuple(keywords) != EXPECTED_KEYWORDS:
        raise ValueError("원본 워크북의 30개 키워드 또는 순서가 승인 명세와 다릅니다.")
    ncs_documents = load_documents(ncs_root, "NCS")
    school_documents = load_documents(school_root, "교과서")
    if len(ncs_documents) != 89 or len(school_documents) != 9:
        raise ValueError(
            f"입력 Markdown 수가 명세와 다릅니다: NCS={len(ncs_documents)}, 교과서={len(school_documents)}"
        )
    documents = ncs_documents + school_documents
    rules = build_default_rules(keywords)
    candidates = default_candidate_decisions()
    artifacts = [
        InputArtifact("원본 워크북", str(source_workbook.resolve()), 1, _file_sha256(source_workbook)),
        InputArtifact("NCS Markdown", str(ncs_root.resolve()), len(ncs_documents), _document_set_sha256(ncs_documents)),
        InputArtifact("교과서 Markdown", str(school_root.resolve()), len(school_documents), _document_set_sha256(school_documents)),
    ]
    result = aggregate_matches(sources, documents, rules, candidates, artifacts)
    write_workbook(result, xlsx_out)
    write_report(result, report_out)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-workbook", type=Path, required=True)
    parser.add_argument("--ncs-root", type=Path, required=True)
    parser.add_argument("--school-root", type=Path, required=True)
    parser.add_argument("--xlsx-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()
    result = run_census(args.source_workbook, args.ncs_root, args.school_root, args.xlsx_out, args.report_out)
    manifest = artifact_manifest(result)
    print(f"완료: 키워드 {len(result.sources)}개, 문서 {len(result.documents)}개, 상세 {len(result.matches)}건")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
