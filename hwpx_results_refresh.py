#!/usr/bin/env python3
"""hwpx_results_refresh.py — 기초보고서(HWPX) 제3장 연구 결과 1~3절을 정본 수치로 다시 쓰고(1단계), 제2장 5절 연구 방법·표 4·목차와 제3장 2절 " 4) 집계 기준의 변경과 이전 결과와의 관계" 를 데이터에서 만들며(2단계, hwpx-methods-bridge-refresh 2026-09-16), 그 뒤에 " 5) 교재별 집중과 편차"(표 12-3·12-4, 소결 → 6))를 붙인다(3단계, ncs-book-concentration 2026-09-17 — 사실·문장은 모두 hwpx_methods_bridge.py).

1단계 — 기능 hwpx-ncs-section-refresh (2026-09-14, 연구책임자 결정 D1~D5). 숫자는 전부 추적 파일에서 온다:
  docs/03-analysis/data/semantic_summary.json   — 총계·등급·분야(groups, pages)·키워드(×그룹)·grade_sources·detected_pages   (정본 실행, 사전 v2)
  docs/03-analysis/data/accident_case_pages.json — 사고사례 자동 판정 13쪽과 원문 확인 판정
  docs/03-analysis/data/summary.json             — 교과서 사고사례 쪽 수(0)·NCS 절단 16쪽 (recount_grades)
2단계 — 기능 hwpx-methods-bridge-refresh (2026-09-16, D1~D6 (a)): 제2장 5절(연구 방법)·표 4·목차와 제3장 2절 " 4) 집계 기준의 변경과 이전 결과와의 관계".
  사실·문장은 hwpx_methods_bridge.py (MethodsPaths 의 추적 파일 11종 + page_utils.EXCEL_MAX_CHARS; 계보 가드로 다른 실행의 파일을 섞지 않는다).
3단계 — 기능 ncs-book-concentration (2026-09-17, D1 (b)·D2 (a)·D3 (b)·D4 (a)·D5 (a)·D6 (b)): 제3장 2절 " 5) 교재별 집중과 편차"(문단 2·표 12-3·12-4) 를 2단계 블록 뒤에 넣고 소결을 6) 으로 바꾼다.
  사실은 정본 semantic_summary.json 의 corpora.NCS.books[] 에서만 파생한다(hwpx_methods_bridge.load_concentration_facts — 파생값은 저장하지 않는다).
스크립트 상수는 문장 틀, 제목·첫머리 locator, 원본 목차의 구고 소제목 수(OLD_METHODS_TOC_ENTRIES)뿐이다.

동작: 절은 제목 텍스트로 찾고(목차의 같은 제목은 건너뛴다), 문단은 원문 첫머리로 찾아 템플릿으로 다시 쓰며(서술 조건은 데이터로
분기), 표 7~12 는 셀 텍스트만 바꾸고(표 13 만 행 증감), 그림 2~4 는 SVG → 원본 형식·크기로 다시 그려 BinData 바이트를 바꾼다. 손댄 문단(표 셀 포함)의 줄 배치 캐시 hp:linesegarray 는 지운다(drop_line_layout_cache, 대조 JSON layout).
2단계는 같은 트리에서 문단을 원형 복제로 넣고 빼며(clone_paragraph·insert_after·remove_paragraphs), 표 12-1·12-2 는 표 12 를 복제해 고유 id 를 준다.
손대지 않은 문단은 구조·값 그대로 — 편집 전 스냅샷과 손댄 집합 장부(touched·inserted·removed)로 검사한다(check_untouched); 나머지 ZIP 항목은 바이트 그대로.
원본은 읽기만 하고 새 파일로 쓴다(기존 출력은 --force 로만 덮어쓰고 <이름>.<sha16>.bak 로 보존). 산출물에 다시 실행할 수는 없다 — 문단을 원본(2026-09-11)
첫머리로 찾고, 5절 소제목이 이미 있는 파일은 처음부터 거부한다: 수치가 바뀌면 언제나 원본에서 다시 만든다.
산출물: 새 HWPX(data/, 비추적), 변경 대조 JSON(추적, 본문 문장·실행 환경 없음), 검토 HTML(표·그림만, 추적), 구/신 문장 병기본 review_text.html(본문 포함 — data/, 비추적).
숫자 감사: 다시 쓴 제3장 1~3절·제2장 1절(표 4)·5절·목차 항목의 모든 숫자 토큰이 정본 값·비율·쪽 번호 중 하나여야 한다 — 아니면 exit 1.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import hwpx_methods_bridge as MB
from hwpx_methods_bridge import fmt, pct, NCS_GROUP_TO_AREA   # 콤마·소수 1자리 %·정본 그룹→분야 대응표 — 2단계 모듈과 한 정의 (hwpx-methods-bridge-refresh)

HERE = Path(__file__).resolve().parent
HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
HC = "{http://www.hancom.co.kr/hwpml/2011/core}"
SECTION_ENTRY = "Contents/section0.xml"
XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

DEFAULT_HWPX = HERE / "data" / "반도체 기초보고서_20260911.hwpx"
DEFAULT_OUT_DIR = HERE / "data"                                   # 산출물 이름은 정본 실행일을 따른다 — default_out_path(facts) / default_diff_path(facts)
DEFAULT_SUMMARY = HERE / "docs" / "03-analysis" / "data" / "semantic_summary.json"
DEFAULT_CASES = HERE / "docs" / "03-analysis" / "data" / "accident_case_pages.json"
DEFAULT_RECOUNT = HERE / "docs" / "03-analysis" / "data" / "summary.json"
DEFAULT_DIFF_DIR = HERE / "docs" / "03-analysis" / "data"
DEFAULT_REVIEW_DIR = HERE / "docs" / "03-analysis" / "hwpx-results-refresh"
FONT = os.environ.get("HWPX_FONT", "/System/Library/Fonts/Supplemental/AppleGothic.ttf")   # 없으면 -font 없이 렌더 (다른 OS) — 결정론은 같은 폰트일 때만

CANONICAL_DICTIONARY = "v2"                    # 보고서에 쓰는 정본 사전 — semantic_keyword_recount.EXPECTED["dictionary"] 와 같아야 한다 (테스트가 대조)
CHAPTER_HEADING = "제3장 연구 결과"
HEADINGS = {                                   # 절 이름 → (시작 제목, 끝 제목) — 본문 제목 텍스트와 정확히 일치해야 한다
    "textbook": ("1. 반도체고등학교 전공교과서의 안전보건 키워드 분석 주요 결과", "2. NCS 반도체 자료의 안전보건 키워드 분석 주요 결과"),
    "ncs": ("2. NCS 반도체 자료의 안전보건 키워드 분석 주요 결과", "3. NCS 반도체 교과서의 사고, 부상, 질병 사례 분석"),
    "cases": ("3. NCS 반도체 교과서의 사고, 부상, 질병 사례 분석", "4. 학생 대상 화학물질·안전보건 교육의 필요성과 효과"),
}
AREA_ORDER = ("개발", "제조", "장비", "재료")
# 교과서 4개 분야는 연구상 분류 (보고서 1절 2) 의 설명) — 교재(그룹 이름) → 분야
TEXTBOOK_AREA = {
    "반도체 기초기술 1": "개발", "반도체 기초기술 2": "개발", "반도체 기초": "개발",
    "반도체 공정기초": "제조", "반도체 포토에칭": "제조", "반도체 박막확산": "제조", "반도체 조립검사": "제조",
    "반도체 장비 유지보수": "장비",
    "반도체 인프라 일반": "재료",
}
GRADE_LABEL = {1: "미흡·없음", 2: "형식적 언급", 3: "구체적 대책"}
COLORS = {1: "#64748b", 2: "#c87a05", 3: "#087f75"}   # 보고서 원본 그림의 인쇄용 색 — 대시보드 등급 램프(--g1 #6b7280 / --g2 #d97706 / --g3 #059669)보다 한 단계 어둡다, 같은 등급 부호
FP_KIND_LABEL = {"guideline": "보호구 착용 지침", "definition": "무재해운동 정의", "property": "톨루엔의 물성·유해성·인화성 설명"}
VERDICTS = ("case", "case_other", "false_positive")   # accident_case_pages.json 의 판정 어휘 — 오타는 서술 건수에서 조용히 빠지지 않고 멈춘다
PPE_MAJORITY = 0.6                  # 보호구 등급 2+3 비율이 이 이상이면 "60%를 넘었다"
NEAR_HALF = (0.4, 0.6)              # 재료 분야 안전 비중이 이 구간이면 "절반 가까이"
SHARE_TOLERANCE_PP = 3              # 안전 비중 vs 쪽수 비중 차이가 이 이하(%p)면 "비슷한 수준"
NUMBER_TOKEN = re.compile(r"\d(?:[\d,]*\d)?(?:\.\d+)?%?")          # 1,234 · 12.5% · 33 — 뒤에 붙은 쉼표는 토큰이 아니다


# ---------------------------------------------------------------- 사실 (정본에서 읽은 값)
@dataclass
class CorpusFacts:
    documents: int
    total: int
    grades: dict[int, int]
    areas: dict[str, dict]                  # 분야 → {"documents", "pages", "total", "grades"}
    keywords: dict[str, dict]               # 키워드 → {"total", "grades", "areas": {분야: {"total", "grades"}}}
    order: list[str]                        # 원본 키워드 순서
    detected_pages: int = 0                 # corpora.*.detected_pages — 출현이 놓인 (교재, 쪽) 수 (2026-09-14~; 1절 교과서 문장·2절 4) 가 쓴다)
    grade_sources: dict = field(default_factory=dict)   # corpora.*.grade_sources — real-page / existing / new / unpaged-* 건수 (제2장 5절 4) 의 교과서 승계 1,149 / 규칙 58)

    def ranked(self) -> list[tuple[str, dict]]:
        return sorted(self.keywords.items(), key=lambda kv: (-kv[1]["total"], self.order.index(kv[0])))

    def grade_share(self, grade: int) -> float:
        return self.grades[grade] / self.total if self.total else 0.0


@dataclass
class CaseFacts:
    pages: list[dict]
    flagged: int                            # 자동 판정 쪽
    books: int
    top_book: str                           # 가장 많이 걸린 교재
    top_book_pages: int
    narrative: int                          # 실제 사고 서술 쪽 (case + case_other)
    industrial_events: int                  # 반도체 산업재해 사건 수
    industrial_books: int
    false_positive: int
    fp_kinds: Counter
    by_area_flagged: Counter
    textbook_cases: int


@dataclass
class Facts:
    ncs: CorpusFacts
    school: CorpusFacts
    cases: CaseFacts
    run: dict = field(default_factory=dict)
    cases_date: str | None = None
    page_basis: dict = field(default_factory=dict)      # meta.page_basis — NCS "real"(실제 PDF 쪽, 2026-09-15~) / "marker"(표식 블록); 교과서는 "marker"(= 실제 쪽)
    methods: MB.MethodsFacts | None = None              # 2단계 — 제2장 5절 사실 (hwpx_methods_bridge.load_methods_facts)
    bridge: MB.BridgeFacts | None = None                # 2단계 — 제3장 2절 4) 사실 (hwpx_methods_bridge.load_bridge_facts)
    concentration: MB.ConcentrationFacts | None = None   # 3단계 — 제3장 2절 5) 교재별 집중 (hwpx_methods_bridge.load_concentration_facts)
    _index: dict | None = field(default=None, init=False, repr=False, compare=False)   # value_index() 캐시 — 사실은 불변이라 한 번만 만든다 (성능 리뷰); init=False 라 dataclasses.replace() 로 만든 새 Facts 는 캐시를 물려받지 않는다

    @property
    def ncs_real_pages(self) -> bool:
        """NCS 출현이 실제 PDF 쪽에 놓인 정본인가 — 2절 도입·'주'·3절 도입 문단이 이 값 하나로 갈린다."""
        return self.page_basis.get("NCS") == "real"

    @property
    def marker_books(self) -> list[str]:
        """대응 없이 표식이 실제 쪽인 교재 코드 — 정본 manifest real_page_marker_books(2026-09-15~, [{code, pages}]); 2절 도입의 "대응이 없는 N권" 이 여기서 나온다."""
        return [b["code"] for b in (self.run.get("real_page_marker_books") or [])]

    def value_index(self) -> dict[str, set[str]]:
        """정본 값(콤마·소수 1자리 % 문자열) → 그 값이 나오는 정본 키 경로들. 숫자 감사의 허용 집합이자 대조 JSON 의 출처(keys) 근거. 인스턴스마다 한 번 계산(캐시)."""
        if self._index is not None:
            return self._index
        index: dict[str, set[str]] = {}

        def add(value: str, key: str) -> None:
            index.setdefault(value, set()).add(key)

        for label, corpus in (("NCS", self.ncs), ("교과서", self.school)):
            base = f"corpora.{label}"
            pages_total = sum(a["pages"] for a in corpus.areas.values())
            add(fmt(corpus.documents), f"{base}.documents"); add(fmt(corpus.total), f"{base}.total"); add(fmt(pages_total), f"{base}.groups[].pages(sum)")
            for g in (1, 2, 3):
                add(fmt(corpus.grades[g]), f"{base}.grades.{g}"); add(pct(corpus.grades[g], corpus.total), f"{base}.grades.{g}/total")
            add(str(sum(1 for k in corpus.keywords.values() if k["total"] == 0)), f"keywords[].corpora.{label}.total==0(count)")
            add(str(sum(1 for k in corpus.keywords.values() if k["total"] > 0)), f"keywords[].corpora.{label}.total>0(count)")
            add(str(len(corpus.order)), "keywords(count)")
            for name, area in corpus.areas.items():
                ab = f"{base}.groups[{name}]"
                add(fmt(area["documents"]), f"{ab}.documents"); add(fmt(area["pages"]), f"{ab}.pages"); add(fmt(area["total"]), f"{ab}.total")
                add(pct(area["total"], corpus.total), f"{ab}.total/corpus"); add(pct(area["pages"], pages_total), f"{ab}.pages/corpus")
                for g in (1, 2, 3):
                    add(fmt(area["grades"][g]), f"{ab}.grades.{g}"); add(pct(area["grades"][g], area["total"]), f"{ab}.grades.{g}/total")
            for name, kw in corpus.keywords.items():
                kb = f"keywords[{name}].corpora.{label}"
                add(fmt(kw["total"]), f"{kb}.total"); add(pct(kw["total"], corpus.total), f"{kb}.total/corpus")
                for g in (1, 2, 3):
                    add(fmt(kw["grades"][g]), f"{kb}.grades.{g}"); add(pct(kw["grades"][g], kw["total"]), f"{kb}.grades.{g}/total")
                add(pct(kw["grades"][2] + kw["grades"][3], kw["total"]), f"{kb}.grades.2+3/total")
                for aname, area in kw["areas"].items():
                    add(fmt(area["total"]), f"{kb}.groups[{aname}].total"); add(pct(area["total"], kw["total"]), f"{kb}.groups[{aname}].total/keyword")
        c = self.cases
        narrative_events = len({p.get("event", p["gist"]) for p in c.pages if p["verdict"] in ("case", "case_other")})
        for value, key in ((c.flagged, "cases.pages(count)"), (c.books, "cases.books"), (c.top_book_pages, "cases.top_book_pages"), (c.narrative, "cases.narrative"), (narrative_events, "cases.narrative_events"),
                           (c.industrial_events, "cases.industrial_events"), (c.industrial_books, "cases.industrial_books"), (c.false_positive, "cases.false_positive"),
                           (c.textbook_cases, "recount.textbook.cases_pages")):
            add(str(value), key)
        for kind, v in c.fp_kinds.items():
            add(str(v), f"cases.false_positive[{kind}]")
        for area, v in c.by_area_flagged.items():
            add(str(v), f"cases.pages[area={area}](count)")
        for p in c.pages:
            add(str(p["page"]), f"cases.pages[{p['book']}].page")
        add(pct(c.top_book_pages, c.flagged), "cases.top_book_pages/flagged"); add(pct(c.false_positive, c.flagged), "cases.false_positive/flagged"); add(pct(c.narrative, c.flagged), "cases.narrative/flagged")
        for p in c.pages:
            for year in re.findall(r"(\d{4})년", p["gist"]):
                add(year, f"cases.pages[{p['book']}].gist(year)")
        add(str(len(self.marker_books)), "run.real_page_marker_books(count)")       # 2절 "대응이 없는 N권" — 허용 토큰(등급 라벨 2)에 기대지 않고 출처를 댄다 (적대적 리뷰 7)
        for label, corpus in (("NCS", self.ncs), ("교과서", self.school)):
            add(fmt(corpus.detected_pages), f"corpora.{label}.detected_pages")
            for source, count in corpus.grade_sources.items():
                add(fmt(count), f"corpora.{label}.grade_sources.{source}")
        for facts in (self.methods, self.bridge, self.concentration):                # 2·3단계 사실 — 방법론·연결·교재별 집중 소절의 숫자 (hwpx_methods_bridge)
            if facts is not None:
                for value, key in facts.value_pairs():
                    add(value, key)
        self._index = index
        return index

    def all_numbers(self) -> set[str]:
        """숫자 감사의 허용 집합 — 정본 값·비율·쪽 번호·권수·순위. 문자열(콤마·소수 1자리 %) 형태."""
        return set(self.value_index())

    def keys_for(self, numbers: list[str]) -> list[str]:
        """숫자 토큰 목록이 나온 정본 키 경로(합집합, 정렬). 작은 수는 여러 키에 걸릴 수 있다."""
        index = self.value_index()
        keys: set[str] = set()
        for token in numbers:
            if token in ALLOWED_TOKENS:                      # 등급·분야 번호 같은 작은 수는 출처를 특정하지 않는다
                continue
            keys |= index.get(token, set()) | index.get(token.rstrip("%"), set())
        return sorted(keys)


def load_facts(summary_path: Path = DEFAULT_SUMMARY, cases_path: Path = DEFAULT_CASES, recount_path: Path | None = DEFAULT_RECOUNT,
               methods_paths: MB.MethodsPaths | None = None) -> Facts:
    """methods_paths 는 2단계 사실의 파일 묶음(기본: 추적 파일; summary/recount 경로는 여기 인자를 따른다)."""
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    run = summary.get("meta", {}).get("run") or {}
    if run.get("expected") is not True:
        raise ValueError(f"semantic_summary.json 이 가드 통과 정본이 아닙니다 (meta.run.expected={run.get('expected')!r}, force={run.get('force')!r}) — 보고서에 쓸 수 없습니다")
    if run.get("dictionary") != CANONICAL_DICTIONARY:
        raise ValueError(f"semantic_summary.json 의 사전이 정본({CANONICAL_DICTIONARY})이 아닙니다: {run.get('dictionary')!r}")
    if not re.match(r"\d{4}-\d{2}-\d{2}", str(run.get("generated_at", ""))):
        raise ValueError(f"semantic_summary.json 의 meta.run.generated_at 이 없거나 날짜가 아닙니다: {run.get('generated_at')!r} — 보고서 출처 문구에 필요합니다")
    page_basis = summary.get("meta", {}).get("page_basis")
    if not isinstance(page_basis, dict) or page_basis.get("NCS") not in ("real", "marker"):
        raise ValueError(f"semantic_summary.json 의 meta.page_basis 가 없거나 NCS 값이 real/marker 가 아닙니다: {page_basis!r} — 2026-09-15 이후 정본(occurrence-real-pages)이 필요합니다: 쪽수 문구가 이 값으로 갈린다")
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    if not recount_path or not Path(recount_path).exists():
        raise FileNotFoundError(f"recount summary.json 이 없습니다 (교과서 사고사례 쪽 수의 출처): {recount_path}")
    textbook_cases = int(json.loads(Path(recount_path).read_text(encoding="utf-8"))["textbook"]["cases_pages"])
    order = [k["name"] for k in summary["keywords"]]

    def corpus_facts(corpus: str, group_to_area) -> CorpusFacts:
        c = summary["corpora"][corpus]
        areas = {a: {"documents": 0, "pages": 0, "total": 0, "grades": {1: 0, 2: 0, 3: 0}} for a in AREA_ORDER}
        for g in c["groups"]:
            area = group_to_area(g["name"])
            if area is None:
                raise ValueError(f"{corpus} 그룹 '{g['name']}' 의 분야를 모른다 — 대응표를 갱신하십시오")
            if "pages" not in g:
                raise ValueError(f"semantic_summary.json 의 그룹 {corpus}/{g['name']} 에 pages 가 없습니다 — 2026-09-14 이후 정본이 필요합니다 (0 으로 채우지 않는다)")
            areas[area]["documents"] += g["documents"]
            areas[area]["pages"] += g["pages"]
            areas[area]["total"] += g["total"]
            for grade in (1, 2, 3):
                areas[area]["grades"][grade] += g["grades"][str(grade)]
        keywords = {}
        for k in summary["keywords"]:
            kc = k["corpora"][corpus]
            kw_areas = {a: {"total": 0, "grades": {1: 0, 2: 0, 3: 0}} for a in AREA_ORDER}
            if "groups" not in kc:
                raise ValueError(f"semantic_summary.json 에 키워드×그룹({k['name']}/{corpus})이 없습니다 — 2026-09-14 이후 정본이 필요합니다")
            for g in kc["groups"]:
                area = group_to_area(g["name"])
                if area is None:
                    raise ValueError(f"{corpus} 키워드 그룹 '{g['name']}'({k['name']}) 의 분야를 모른다 — 대응표를 갱신하십시오")
                kw_areas[area]["total"] += g["total"]
                for grade in (1, 2, 3):
                    kw_areas[area]["grades"][grade] += g["grades"][str(grade)]
            keywords[k["name"]] = {"total": kc["total"], "grades": {1: kc["grades"]["1"], 2: kc["grades"]["2"], 3: kc["grades"]["3"]}, "areas": kw_areas}
        if "detected_pages" not in c:
            raise ValueError(f"semantic_summary.json 의 corpora.{corpus} 에 detected_pages 가 없습니다 — 2026-09-14 이후 정본이 필요합니다")
        if not isinstance(c.get("grade_sources"), dict) or not {"existing", "new"} <= set(c["grade_sources"]):
            raise ValueError(f"semantic_summary.json 의 corpora.{corpus} 에 grade_sources(existing·new) 가 없습니다 — 2단계 4) 의 승계/규칙 건수 출처라 0 으로 채우지 않는다")
        if any(int(v) for k, v in c["grade_sources"].items() if k.startswith("unpaged")):
            raise ValueError(f"semantic_summary.json 의 corpora.{corpus} 에 쪽 없는 출현(unpaged-*)이 있습니다 — 5절 4) 의 승계/규칙 건수가 총계와 어긋난다 (EXPECTED 는 0 으로 고정)")
        return CorpusFacts(documents=c["documents"], total=c["total"], grades={1: c["grades"]["1"], 2: c["grades"]["2"], 3: c["grades"]["3"]},
                           areas=areas, keywords=keywords, order=order, detected_pages=int(c["detected_pages"]), grade_sources={k: int(v) for k, v in (c.get("grade_sources") or {}).items()})

    ncs = corpus_facts("NCS", NCS_GROUP_TO_AREA.get)
    school = corpus_facts("교과서", TEXTBOOK_AREA.get)
    pages = cases["pages"]
    unknown_verdicts = {p.get("verdict") for p in pages} - set(VERDICTS)
    if unknown_verdicts:
        raise ValueError(f"accident_case_pages.json 의 판정값을 모른다: {sorted(map(str, unknown_verdicts))} — {VERDICTS} 중 하나여야 합니다")
    unknown_kinds = {p["kind"] for p in pages if p["verdict"] == "false_positive" and p["kind"] not in FP_KIND_LABEL}
    if unknown_kinds:
        raise ValueError(f"accident_case_pages.json 의 오탐 유형을 모른다: {sorted(unknown_kinds)} — FP_KIND_LABEL 에 추가하십시오")
    by_book = Counter(p["title"] for p in pages)
    top_book, top_pages = by_book.most_common(1)[0]
    industrial = [p for p in pages if p["verdict"] == "case"]
    case_facts = CaseFacts(
        pages=pages, flagged=len(pages), books=len({p["book"] for p in pages}), top_book=top_book, top_book_pages=top_pages,
        narrative=sum(1 for p in pages if p["verdict"] in ("case", "case_other")),
        industrial_events=len({p["event"] for p in industrial}), industrial_books=len({p["book"] for p in industrial}),
        false_positive=sum(1 for p in pages if p["verdict"] == "false_positive"),
        fp_kinds=Counter(p["kind"] for p in pages if p["verdict"] == "false_positive"),
        by_area_flagged=Counter(p["area"] for p in pages), textbook_cases=textbook_cases,
    )
    mp = methods_paths or MB.MethodsPaths()
    mp = replace(mp, summary=Path(summary_path), recount_summary=Path(recount_path))
    methods = MB.load_methods_facts(mp, summary=summary)
    bridge = MB.load_bridge_facts(mp, summary=summary)
    concentration = MB.load_concentration_facts(summary, mp.summary)
    return Facts(ncs=ncs, school=school, cases=case_facts, run=summary.get("meta", {}).get("run", {}), cases_date=cases.get("date"), page_basis=dict(page_basis),
                 methods=methods, bridge=bridge, concentration=concentration)


def run_day(f: Facts) -> str:
    return str(f.run["generated_at"])[:10].replace("-", "")


def default_out_path(f: Facts) -> Path:
    return DEFAULT_OUT_DIR / f"반도체 기초보고서_{run_day(f)}_정본.hwpx"


def default_diff_path(f: Facts) -> Path:
    return DEFAULT_DIFF_DIR / f"hwpx_results_refresh_{run_day(f)}.json"


# ---------------------------------------------------------------- XML 도우미
def direct_text(p: ET.Element) -> str:
    """문단의 글 — 각 hp:t 의 글과 그 안에 든 요소(hp:tab 등)의 꼬리 글까지(itertext). 탭 뒤의 쪽 번호가 감사·locator 에서 사라지지 않게 (레드팀)."""
    return "".join("".join(t.itertext()) for run in p.findall(HP + "run") for t in run.findall(HP + "t"))


def set_text(p: ET.Element, text: str) -> dict:
    """문단의 글을 통째로 바꾼다 — 첫 run 의 charPrIDRef 를 승계해 hp:t 하나로. 글만 있던 다른 run 은 지운다."""
    runs = p.findall(HP + "run")
    if not runs:
        raise ValueError("run 이 없는 문단에는 글을 쓸 수 없습니다")
    text_runs = [r for r in runs if any(c.tag == HP + "t" for c in r) and all(c.tag == HP + "t" for c in r)]
    if any(len(t) for r in text_runs for t in r.findall(HP + "t")):
        raise ValueError("hp:t 안에 요소(탭·형광펜 등)가 있는 문단은 통째로 바꿀 수 없습니다 — 안의 요소와 꼬리 글이 사라진다")
    first = text_runs[0] if text_runs else runs[0]
    collapsed = len(text_runs) > 1
    for t in list(first.findall(HP + "t")):
        first.remove(t)
    node = ET.SubElement(first, HP + "t")
    node.text = text
    for r in text_runs[1:]:
        p.remove(r)
    if direct_text(p) != text:
        raise ValueError("문단 글 교체가 닫히지 않았습니다 — 글 아닌 자식(hp:ctrl 등)과 섞인 run 이 있습니다")
    return {"format_collapsed": collapsed}                    # 줄 배치 캐시(hp:linesegarray)는 여기서 건드리지 않는다 — 실행의 drop_line_layout_cache 가 장부의 문단(글이 안 바뀐 셀·그림 문단까지) 한 규칙으로 지운다 (2026-09-17; 한 줄만 남기던 이전 정리는 캐시를 믿는 뷰어가 긴 글을 한 줄에 누르게 했다)


def cell_paragraphs(tc: ET.Element) -> list[ET.Element]:
    return tc.findall(f"{HP}subList/{HP}p")


def cell_text(tc: ET.Element) -> str:
    return " ".join(direct_text(p) for p in cell_paragraphs(tc)).strip()


def set_cell(tc: ET.Element, text: str) -> None:
    paragraphs = cell_paragraphs(tc)
    set_text(paragraphs[0], text)
    for extra in paragraphs[1:]:
        tc.find(HP + "subList").remove(extra)


def table_rows(tbl: ET.Element) -> list[list[ET.Element]]:
    return [tr.findall(HP + "tc") for tr in tbl.findall(HP + "tr")]


def renumber_table(tbl: ET.Element) -> None:
    trs = tbl.findall(HP + "tr")
    tbl.set("rowCnt", str(len(trs)))
    for r, tr in enumerate(trs):
        for tc in tr.findall(HP + "tc"):
            addr = tc.find(HP + "cellAddr")
            if addr is not None:
                addr.set("rowAddr", str(r))


def _row_is_empty(tr: ET.Element) -> bool:
    return all(cell_text(tc) == "" for tc in tr.findall(HP + "tc"))


def resize_table(tbl: ET.Element, first_data_row: int, data_rows: int) -> None:
    """데이터 행을 data_rows 개로 맞춘다 — 모든 데이터 행을 첫 데이터 행의 서식(셀 크기·테두리·문단/글자 스타일)으로 통일해 다시 만들고,
    표 끝의 빈 간격 행은 그대로 뒤에 둔다(원본 표 13 은 마지막이 빈 행이라 그 행을 복제하면 데이터가 간격 행 서식을 입는다 — ship 레드팀).
    hp:sz@height 는 행 높이 합으로 다시 계산한다."""
    trs = tbl.findall(HP + "tr")
    if len(trs) <= first_data_row:
        raise ValueError("복제할 데이터 행이 없습니다")
    trailing = []
    while len(trs) > first_data_row and _row_is_empty(trs[-1]):
        trailing.insert(0, trs.pop())
    if len(trs) <= first_data_row:
        raise ValueError("복제할 데이터 행이 없습니다 (빈 행뿐)")
    if _row_is_empty(trs[first_data_row]):
        raise ValueError("첫 데이터 행이 빈 행입니다 — 서식 원본으로 쓸 수 없습니다")
    template = copy.deepcopy(trs[first_data_row])
    for tr in tbl.findall(HP + "tr")[first_data_row:]:
        tbl.remove(tr)
    for _ in range(data_rows):
        tbl.append(copy.deepcopy(template))
    for tr in trailing:
        tbl.append(tr)
    renumber_table(tbl)
    sz = tbl.find(HP + "sz")
    if sz is not None:
        heights = [tr.find(f"{HP}tc/{HP}cellSz") for tr in tbl.findall(HP + "tr")]
        if all(h is not None for h in heights):
            sz.set("height", str(sum(int(h.get("height", 0)) for h in heights)))


def top_paragraphs(root: ET.Element) -> list[ET.Element]:
    return root.findall(HP + "p")


# ---------------------------------------------------------------- 2단계 XML 능력 (hwpx-methods-bridge-refresh 설계 §3.3)
def clone_paragraph(proto: ET.Element, text: str) -> ET.Element:
    """원형 문단을 깊은 복사해 글만 바꾼다 — paraPr·style·charPr 승계. 빈 원형(글 run 없음)에 "" 를 주면 그대로 둔다."""
    p = copy.deepcopy(proto)
    p.set("pageBreak", "0"); p.set("columnBreak", "0")         # 원형이 쪽/단 나눔 문단이어도 복제본은 아니다 (레드팀)
    if text == "" and p.find(f"{HP}run/{HP}t") is None:
        return p
    set_text(p, text)
    return p


def insert_after(root: ET.Element, ref: ET.Element, elements: list[ET.Element]) -> None:
    children = list(root)
    if ref not in children:
        raise ValueError("삽입 기준 문단이 최상위에 없습니다")
    at = children.index(ref) + 1
    for offset, element in enumerate(elements):
        root.insert(at + offset, element)


def remove_paragraphs(root: ET.Element, elements: list[ET.Element]) -> None:
    children = list(root)
    for element in elements:
        if element not in children:
            raise ValueError("삭제할 문단이 최상위에 없습니다")
        root.remove(element)


def next_object_ids(root: ET.Element) -> tuple[int, int]:
    """(새 id, 새 zOrder) — 문서에서 id 와 zOrder 를 함께 가진 모든 개체(표·그림·도형·글상자) 최댓값 + 1 이라 같은 문서면 같은 값(결정론)."""
    ids, orders = [0], [0]
    for obj in root.iter():
        if obj.get("zOrder") is not None and obj.get("id") is not None and str(obj.get("id")).isdigit():
            ids.append(int(obj.get("id"))); orders.append(int(obj.get("zOrder") or 0))
    return max(ids) + 1, max(orders) + 1


def clone_table_paragraph(proto_p: ET.Element, rows: list[list[str]], first_data_row: int, header: list[str] | None, ids: tuple[int, int]) -> ET.Element:
    """표를 담은 문단을 복제해 새 표를 만든다 — hp:tbl 은 새 id·zOrder, 행은 resize_table, 셀은 fill_table; 문단의 글 run 은 비운다."""
    p = copy.deepcopy(proto_p)
    p.set("pageBreak", "0"); p.set("columnBreak", "0")
    tbl = p.find(f".//{HP}tbl")
    if tbl is None:
        raise ValueError("표 원형 문단에 hp:tbl 이 없습니다")
    tbl.set("id", str(ids[0])); tbl.set("zOrder", str(ids[1]))
    resize_table(tbl, first_data_row, len(rows))
    fill_table(tbl, rows, first_data_row, header)
    for run in p.findall(HP + "run"):
        for t in run.findall(HP + "t"):
            t.text = ""
    return p


def locate_range(root: ET.Element, start_text: str, end_text: str, occurrence: int = 1) -> Section:
    """start_text 의 occurrence 번째 일치(0 = 목차 사본, 1 = 본문)부터 그 뒤 첫 end_text 앞까지."""
    tops = top_paragraphs(root)
    texts = [direct_text(p).strip() for p in tops]
    starts = [i for i, t in enumerate(texts) if t == start_text]
    if len(starts) <= occurrence:
        raise ValueError(f"'{start_text}' 제목의 {occurrence + 1}번째 일치를 찾지 못했습니다 ({len(starts)}회)")
    start = starts[occurrence]
    ends = [i for i, t in enumerate(texts) if t == end_text and i > start]
    if not ends:
        raise ValueError(f"'{start_text}' 뒤에 끝 제목 '{end_text}' 이 없습니다")
    return Section(start_text, start, ends[0], tops[start:ends[0]])


def locate_toc_block(root: ET.Element, entry_prefix: str, next_prefix: str) -> list[ET.Element]:
    """목차 블록 — entry_prefix 로 시작하는 첫 최상위 문단(목차 사본)부터 next_prefix 로 시작하는 다음 문단 앞까지."""
    tops = top_paragraphs(root)
    texts = [direct_text(p).strip() for p in tops]
    starts = [i for i, t in enumerate(texts) if t.startswith(entry_prefix)]
    if not starts:
        raise ValueError(f"목차 항목 '{entry_prefix}' 을 찾지 못했습니다")
    start = starts[0]
    ends = [i for i, t in enumerate(texts) if i > start and t.startswith(next_prefix)]
    if not ends:
        raise ValueError(f"목차 항목 '{entry_prefix}' 뒤에 '{next_prefix}' 이 없습니다")
    return tops[start:ends[0]]


def set_cell_paragraph(tc: ET.Element, prefix: str, text: str) -> None:
    """셀 안 여러 문단 중 prefix 로 시작하는 하나의 글만 바꾼다(표 4 의 '반도체제조 14종')."""
    hits = [p for p in cell_paragraphs(tc) if direct_text(p).strip().startswith(prefix)]
    if len(hits) != 1:
        raise ValueError(f"셀 안에 '{prefix}' 로 시작하는 문단이 {len(hits)}개입니다 (1개여야 함)")
    set_text(hits[0], text)


def snapshot_paragraphs(root: ET.Element) -> dict:
    """편집 전 최상위 문단의 (순서, 직렬화) — check_untouched 의 기준. 같은 Element 객체를 id 로 식별한다."""
    tops = top_paragraphs(root)
    return {"order": [id(p) for p in tops], "xml": {id(p): ET.tostring(p) for p in tops}}


def drop_line_layout_cache(root: ET.Element, touched: set, inserted: set) -> dict:
    """장부에 적힌 최상위 문단(touched·inserted — 재작성·삽입, 표 셀 문단 포함)의 hp:linesegarray 를 지운다 — 옛 글의 줄 배치 캐시.
    OWPML 에서 선택 요소라 뷰어가 다시 배치하지만, 캐시를 믿는 뷰어(Polaris Office)는 긴 새 글을 옛 줄 수에 눌러 그렸다(한글 E2E 2026-09-17).
    touched 는 장부의 보수적 집합이라 글은 그대로인 그림 문단(BinData 만 바뀜)도 들어 있다 — 함께 지우며 무해하다.
    손대지 않은 문단은 그대로 둔다 — check_untouched 앞에 호출해 검사가 이 변경까지 덮게 한다."""
    paragraphs = removed = ledger = 0
    for top in list(root):
        if id(top) not in touched and id(top) not in inserted:
            continue
        ledger += 1
        hit = 0
        for p in top.iter(HP + "p"):
            for lsa in p.findall(HP + "linesegarray"):
                p.remove(lsa); hit += 1
        if hit:
            paragraphs += 1; removed += hit
    return {"paragraphs": paragraphs, "linesegarray_removed": removed, "ledger_paragraphs": ledger}   # 한글이 저장한 원본은 문단마다 캐시가 있으므로 paragraphs == ledger_paragraphs 가 정상 (적대적 리뷰 F4)


def check_untouched(root: ET.Element, snapshot: dict, touched: set, inserted: set, removed: set) -> None:
    """손댄 원소 집합 검사 — 장부(touched·inserted·removed)에 없는 문단은 직렬화가 같아야 하고, 순서도 그대로여야 하며, 낯선 문단이 없어야 한다.
    1단계의 순번 기반 검사를 대체한다(2단계는 문단을 넣고 빼므로 순번이 어긋난다)."""
    xml = snapshot["xml"]
    new_tops = top_paragraphs(root)
    expected_kept = [pid for pid in snapshot["order"] if pid not in touched and pid not in removed]
    actual_kept = []
    for p in new_tops:
        pid = id(p)
        if pid in inserted:
            continue
        if pid not in xml:
            raise RuntimeError("손댄 범위 밖의 문단이 바뀌었습니다 — 장부에 없는 낯선 문단이 있습니다: 중단")
        if pid in removed:
            raise RuntimeError("손댄 범위 밖의 문단이 바뀌었습니다 — 삭제했다고 적힌 문단이 남아 있습니다: 중단")
        if pid in touched:
            continue
        if ET.tostring(p) != xml[pid]:
            raise RuntimeError(f"손댄 범위 밖의 문단이 바뀌었습니다: {direct_text(p)[:30]!r} — 중단")
        actual_kept.append(pid)
    if actual_kept != expected_kept:
        raise RuntimeError("손댄 범위 밖의 문단이 바뀌었습니다 — 순서가 다르거나 빠진 문단이 있습니다: 중단")


def owner_map(root: ET.Element) -> dict:
    """모든 자손 원소 id → 그것을 담은 최상위 문단 (표·그림을 고쳤을 때 어느 문단을 손댔는지 장부에 적기 위해)."""
    owners = {}
    for top in top_paragraphs(root):
        for el in top.iter():
            owners[id(el)] = top
    return owners


def _paragraph_after(root: ET.Element, ref: ET.Element) -> ET.Element | None:
    children = list(root)
    at = children.index(ref)
    return children[at + 1] if at + 1 < len(children) else None


def _is_blank(p: ET.Element) -> bool:
    """글도 개체(표·그림·컨트롤·책갈피)도 없는 순수 간격 문단 — 원형으로 복제해도 단 정의·책갈피가 따라오지 않는다 (Claude 적대적 리뷰 4)."""
    runs = p.findall(HP + "run")
    return direct_text(p).strip() == "" and all(all(c.tag == HP + "t" for c in r) for r in runs)


def has_object(p: ET.Element, tag: str) -> bool:
    return p.find(f".//{HP}{tag}") is not None


# ---------------------------------------------------------------- 절 탐지
@dataclass
class Section:
    name: str
    start: int
    end: int
    paragraphs: list[ET.Element]


def locate_sections(root: ET.Element) -> dict[str, Section]:
    tops = top_paragraphs(root)
    texts = [direct_text(p).strip() for p in tops]
    chapter_hits = [i for i, t in enumerate(texts) if t == CHAPTER_HEADING]
    if len(chapter_hits) < 2:
        raise ValueError(f"'{CHAPTER_HEADING}' 본문 제목을 찾지 못했습니다 (목차 포함 {len(chapter_hits)}회)")
    body_start = chapter_hits[1]                       # 첫 번째는 목차
    sections = {}
    for name, (start_heading, end_heading) in HEADINGS.items():
        starts = [i for i in range(body_start, len(texts)) if texts[i] == start_heading]
        ends = [i for i in range(body_start, len(texts)) if texts[i] == end_heading]
        if len(starts) != 1 or not ends:
            raise ValueError(f"절 '{name}' 경계를 찾지 못했습니다: 시작 {len(starts)}회, 끝 {len(ends)}회")
        after = [e for e in ends if e > starts[0]]
        if not after:
            raise ValueError(f"절 '{name}' 끝 제목이 시작 뒤에 없습니다 (시작 {starts[0]}, 끝 {ends})")
        end = min(after)
        sections[name] = Section(name, starts[0], end, tops[starts[0]:end])
    return sections


def find_paragraph(section: Section, prefix: str, other_prefixes: tuple[str, ...] = ()) -> ET.Element:
    """원문 첫머리(prefix)로 문단을 찾는다. 같은 절의 다른 locator 가 더 길게 맞는 문단은 이 locator 의 것이 아니다 (예: '…는' 과 '…는 총')."""
    longer = [o for o in other_prefixes if o != prefix and o.startswith(prefix)]
    hits = [p for p in section.paragraphs
            if direct_text(p).strip().startswith(prefix) and not has_object(p, "tbl") and not any(direct_text(p).strip().startswith(o) for o in longer)]
    if len(hits) != 1:
        raise ValueError(f"[{section.name}] '{prefix}' 로 시작하는 문단이 {len(hits)}개입니다 (1개여야 함)")
    return hits[0]


def find_table_after_caption(section: Section, caption_prefix: str) -> ET.Element:
    for i, p in enumerate(section.paragraphs):
        if direct_text(p).strip().startswith(caption_prefix):
            for q in section.paragraphs[i + 1:i + 3]:
                tbl = q.find(f".//{HP}tbl")
                if tbl is not None:
                    return tbl
    raise ValueError(f"[{section.name}] 캡션 '{caption_prefix}' 다음 표를 찾지 못했습니다")


def find_table_by_first_cell(section: Section, prefix: str) -> ET.Element:
    for p in section.paragraphs:
        for tbl in p.findall(f".//{HP}tbl"):
            rows = table_rows(tbl)
            if rows and rows[0] and cell_text(rows[0][0]).startswith(prefix):
                return tbl
    raise ValueError(f"[{section.name}] 첫 셀이 '{prefix}' 인 표를 찾지 못했습니다")


def find_picture(section: Section, caption_prefix: str | None = None, item: str | None = None) -> ET.Element:
    """캡션 문단 바로 앞의 그림(hp:pic); 캡션이 없는 그림(1절 그림 2)은 절 안에서 binaryItemIDRef 로 찾는다."""
    if caption_prefix:
        for i, p in enumerate(section.paragraphs):
            if direct_text(p).strip().startswith(caption_prefix):
                for q in reversed(section.paragraphs[max(0, i - 3):i]):
                    pic = q.find(f".//{HP}pic")
                    if pic is not None:
                        return pic
    if item:
        hits = [pic for p in section.paragraphs for pic in p.findall(f".//{HP}pic") if pic.find(f".//{HC}img") is not None and pic.find(f".//{HC}img").get("binaryItemIDRef") == item]
        if len(hits) == 1:
            return hits[0]
        raise ValueError(f"[{section.name}] binaryItemIDRef={item} 인 그림이 {len(hits)}개입니다")
    raise ValueError(f"[{section.name}] 캡션 '{caption_prefix}' 앞의 그림을 찾지 못했습니다")


# ---------------------------------------------------------------- 문단 템플릿
def q(s: str) -> str:
    return f"‘{s}’"


def _jong(word: str) -> int:
    """마지막 한글 음절의 종성 인덱스 (0 = 받침 없음, 8 = ㄹ); 한글이 아니면 -1."""
    for ch in reversed(word):
        code = ord(ch) - 0xAC00
        if 0 <= code < 11172:
            return code % 28
    return -1


def ro(word: str) -> str:
    return word + ("로" if _jong(word) in (0, 8, -1) else "으로")


def wa(word: str) -> str:
    return word + ("와" if _jong(word) in (0, -1) else "과")


def eun(word: str) -> str:
    return word + ("는" if _jong(word) in (0, -1) else "은")


_DIGIT_JONG = {"0": 1, "1": 8, "2": 0, "3": 1, "4": 0, "5": 0, "6": 1, "7": 1, "8": 1, "9": 0}   # 영·일·이·삼·사·오·육·칠·팔·구 의 받침 유무


def iga(word: str) -> str:
    """주격 조사 — '등급 1이', '등급 2가', '등급 3이' (숫자는 읽는 소리의 받침으로)."""
    jong = _DIGIT_JONG[word[-1]] if word and word[-1].isdigit() else _jong(word)
    return word + ("가" if jong in (0, -1) else "이")


def _share_rel(share: float, overall: float) -> str:
    """등급 3 비율을 전체 평균과 견준 관계 — SHARE_TOLERANCE_PP 안이면 '비슷', 그 밖은 '높'/'낮' (F1: 문장이 이 값으로 갈라진다)."""
    tol = SHARE_TOLERANCE_PP / 100
    if share >= overall + tol:
        return "높"
    if share < overall - tol:
        return "낮"
    return "비슷"


def provenance(f: "Facts") -> tuple[str, str]:
    """(정본 날짜, 사전 버전) — 문장의 출처 문구는 semantic_summary.json 의 meta.run 에서만 온다 (F3: 리터럴 금지)."""
    return str(f.run["generated_at"])[:10], str(f.run["dictionary"])


def _rank_phrase(corpus: CorpusFacts, names: list[str]) -> str:
    rows = sorted(((n, corpus.keywords[n]["total"]) for n in names), key=lambda kv: (-kv[1], corpus.order.index(kv[0])))
    return ", ".join(f"{q(n)} {fmt(v)}건" for n, v in rows)


def _grade_max(grades: dict[int, int]) -> int:
    return max((1, 2, 3), key=lambda g: (grades[g], -g))


AREA_LABEL = {"개발": "반도체 개발 분야", "제조": "반도체 제조 분야", "장비": "반도체 장비 분야", "재료": "반도체 재료 분야"}


def _compare_share(value: float, reference: float) -> str:
    diff = (value - reference) * 100
    if abs(diff) <= SHARE_TOLERANCE_PP:
        return "과 비슷한 수준으로"
    return "보다 낮은 수준으로" if diff < 0 else "보다 높은 수준으로"


def textbook_paragraphs(f: Facts) -> list[tuple[str, str, dict]]:
    s = f.school
    pages_total = sum(a["pages"] for a in s.areas.values())
    detected = sum(1 for k in s.keywords.values() if k["total"] > 0)
    zero = [n for n in s.order if s.keywords[n]["total"] == 0]
    top6 = s.ranked()[:6]
    k = lambda n: s.keywords[n]["total"]
    g3 = s.grades[3]
    def area_sentence(area, lead):
        a = s.areas[area]
        return f"{lead} {a['documents']}권, 총 {fmt(a['pages'])}쪽으로 전체의 약 {pct(a['pages'], pages_total)}를 차지하였다."
    largest_area = max(AREA_ORDER, key=lambda a: s.areas[a]["pages"])
    run_date, dictionary = provenance(f)
    def zero_or_count(name, label):                       # "‘X’는 전혀 검출되지 않았고" / "‘X’는 N건에 그쳤고" — 0 주장은 데이터로만
        return f"{eun(q(label))} 전혀 검출되지 않았고" if k(name) == 0 else f"{eun(q(label))} {fmt(k(name))}건에 그쳤고"
    conditions = {
        "키워드 분석 결과": {"top_keyword": top6[0][0], "zero_keywords": zero},
        "반도체 제조 분야는": {"manufacturing_has_most_pages": largest_area == "제조"},
        "따라서 제조 분야는 안전보건교육이 가장 적극적으로": {"zero_keywords_in_sentence": [n for n in ("직업병", "물질안전보건자료") if k(n) == 0]},
        "따라서 장비 분야에서는 전기, 기계, 압력": {"textbook_accident_pages": f.cases.textbook_cases, "fall_is_zero": k("추락") == 0},
        "또한 공정안전관리, 직업병, 물질안전보건자료": {"zero_keywords": zero, "textbook_accident_pages": f.cases.textbook_cases},
        "본 연구에서는 9권의 반도체 교과서를": {"page_basis": f.page_basis.get("NCS")},        # 실제 쪽 기준일 때만 "교과서는 … 영향을 받지 않았다" 문장 (2단계, hwpx-methods-bridge-refresh)
    }
    return _with_conditions([
        ("본 연구에서는 반도체고등학교의 전공교과서를 대상으로",
         f"본 연구에서는 반도체고등학교의 전공교과서를 대상으로 안전보건교육 내용의 실태를 분석하였다. 분석 대상은 교과서 {s.documents}권, 총 {fmt(pages_total)}페이지이며, ‘사망, 부상, 화학물질, 폭발, 감전, 직업병’ 등 {len(s.order)}개의 안전보건 관련 주요 키워드를 중심으로 AI 기반 텍스트 분석과 수기 검토를 병행하였다. 수치는 {run_date} 정본 재검산(의미 표현 사전 {dictionary}, 출현건수 기준) 값이다."),
        ("키워드 분석 결과",
         f"키워드 분석 결과 {detected}개 키워드가 검출되었고, {len(zero)}개 키워드는 한 번도 검출되지 않았다. 전체적으로는 {q(top6[0][0])}이 {fmt(top6[0][1]['total'])}건으로 가장 많았으며, "
         + ", ".join(f"{q(n)} {fmt(v['total'])}건" for n, v in top6[1:]) + " 등으로 나타났다. "
         f"특히 {q(top6[0][0])}, {q(top6[1][0])}, {q(top6[2][0])}이 상대적으로 많이 검출되었다는 것은 기본적인 안전 개념은 일정 부분 다루고 있음을 보여 준다. 그러나 {q(top6[0][0])}은 가장 많이 검출되었음에도, 상당수가 일반적인 주의 표현이나 기술적 안전성을 설명하는 내용이었다."),
        ("‘화학물질’은",
         f"‘화학물질’은 {fmt(k('화학물질'))}건에 불과하여, 다양한 산·알칼리·유기용제·특수 가스를 사용하는 반도체산업의 특성에 비해 작업자 중심의 화학물질 위험 교육이 부족한 것으로 드러났다."),
        ("특히 질병 관련 내용의 부족이 두드러졌다",
         f"특히 질병 관련 내용의 부족이 두드러졌다. ‘질병’은 {fmt(k('질병'))}건에 불과하였으며, ‘직업병’ {fmt(k('직업병'))}건, ‘작업환경’ {fmt(k('작업환경'))}건, ‘유해 인자’는 {fmt(k('유해인자'))}건이었다. 이를 통해 현재 교과서가 반도체 기술과 공정의 원리를 중심으로 구성되어 있고, 화학물질·물리적 유해 인자 등에 장기간 노출되어 발생할 수 있는 직업병과 그 예방에 관한 내용은 거의 포함하지 않음을 알 수 있다."),
        ("또한 ‘끼임’",
         f"또한 ‘끼임’ {fmt(k('끼임'))}건과 ‘추락’이 {fmt(k('추락'))}건이었는데, 이는 장비 점검·유지보수와 같은 작업에서 발생할 수 있는 전형적인 산업재해 위험을 충분히 반영하지 않았음을 의미한다. 더욱이 화학물질 안전관리의 기본 정보전달 수단인 ‘물질안전보건자료’가 {fmt(k('물질안전보건자료'))}건, ‘MSDS’는 {fmt(k('MSDS'))}건으로 나타나, 향후 교과서에서는 GHS·SDS/MSDS를 활용하여 화학물질의 유해성, 보호구, 응급조치, 안전한 취급 방법을 학생이 직접 확인할 수 있도록 하는 교육이 필요하다."),
        ("종합하면, 현행 반도체고등학교의 반도체 교과서에는",
         f"종합하면, 현행 반도체고등학교의 반도체 교과서에는 ‘안전’과 ‘위험’에 대한 일반적인 언급이 있긴 하지만, 사고·부상과 직업병의 발생 원인, 작업자의 유해 인자 노출, 구체적인 예방 대책, 안전보건 제도와 연결되는 내용은 매우 부족하다. 특히 0건으로 확인된 {len(zero)}개 키워드({', '.join(zero)})는 향후 안전보건 교재 개발에서 우선적으로 보완해야 할 핵심 교육 영역으로 볼 수 있다."),
        ("9권의 교과서에서 구체적인 사고",
         f"{s.documents}권의 교과서에서 구체적인 사고·부상·직업병 사례가 {'한 건도 발견되지 않았다' if f.cases.textbook_cases == 0 else str(f.cases.textbook_cases) + '쪽에서만 발견되었다'}는 것을 의미하기 때문이다. 단순히 ‘위험’이나 ‘안전’이라는 용어를 소개하는 것과 불산 누출, TMAH 급성중독, 질식, 엑스선 피폭 등의 사고가 어떻게 발생하고 어떻게 예방할 수 있는지를 사례로 학습하는 것은 교육 효과 측면에서 큰 차이가 있다. 따라서 현행 교과서는 위험의 존재를 일부 언급하고 있으나, 학생이 산업현장의 사고와 질병 발생 과정을 이해하고 예방 행동으로 연결하기에는 한계가 있다고 판단된다."),
        ("본 연구에서는 9권의 반도체 교과서를",
         f"본 연구에서는 {s.documents}권의 반도체 교과서를 교육 내용에 따라 반도체 개발, 반도체 제조, 반도체 장비, 반도체 재료·인프라 분야로 재분류하였다. 이 분류는 교과서 제목과 주요 교육 내용을 기준으로 한 연구상 분류이며, 대시보드 자체에서 4개 분야별 수치를 별도로 제시한 것은 아니다. 분야별 쪽수는 각 교재 마크다운의 쪽 표식 최댓값을 합한 값이다."
         + (f" {MB.textbook_basis_sentence(f)}" if f.ncs_real_pages and f.bridge is not None else "") + " 분야별로 설명하면 다음과 같다."),
        ("반도체 개발 분야는",
         area_sentence("개발", "반도체 개발 분야는") + " 『반도체 기초기술』과 『반도체 기초』는 반도체의 원리, 소자, 회로, 기본 기술을 중심으로 구성되기 때문에, 제조 설비나 화학물질을 직접 취급하는 상황에 대한 안전보건 내용은 제조·장비 분야보다 상대적으로 적을 가능성이 높다."),
        ("반도체 제조 분야는",
         area_sentence("제조", "반도체 제조 분야는").replace("차지하였다.", "차지하여 가장 큰 비중을 보였다." if largest_area == "제조" else "차지하였다.")
         + " 공정 기초, 포토에칭, 박막 확산, 조립검사 등은 실제 반도체 생산공정과 직접 연결되는 분야이므로, 화학물질, 고온, 특수 가스, 전기, 설비, 방사선, 자동화 장비 등 다양한 위험 요인을 다룰 수 있는 영역이다."),
        ("따라서 제조 분야는 안전보건교육이 가장 적극적으로",
         f"따라서 제조 분야는 안전보건교육이 가장 적극적으로 통합되어야 하는 분야이다. 하지만 전체 교과서에서 {zero_or_count('직업병', '직업병')} {zero_or_count('물질안전보건자료', '물질안전보건자료')} ‘MSDS’는 {fmt(k('MSDS'))}건, ‘작업환경’은 {fmt(k('작업환경'))}건에 그쳤다는 결과를 고려하면, 제조공정 교육이 공정 기술 중심으로 구성되고, 안전보건과 연결은 매우 부족하다고 판단된다. 특히 포토 공정의 현상액과 유기용제, 식각 공정의 산·알칼리와 부식성 물질, 박막·확산 공정의 특수 가스와 고온 설비, 조립·검사 공정의 기계적 위험과 엑스선 검사장비 등을 공정 원리와 함께 설명할 필요가 있다."),
        ("반도체 장비 분야는",
         area_sentence("장비", "반도체 장비 분야는") + " 장비 유지보수는 정상적인 자동화 생산 작업과 달리 장비 내부 접근, 전원 차단, 잔류 에너지원 제거, 배관 개방, 세정과 부품 교체 등의 작업을 해야 하므로, 사고 위험이 심하게 증가할 수 있다."),
        ("따라서 장비 분야에서는 전기, 기계, 압력",
         f"따라서 장비 분야에서는 전기, 기계, 압력, 진공, 고온, 화학물질과 같은 위험 에너지원과 함께 LOTO(Lockout/Tagout), 인터로크, 작업 허가, 잔류 에너지원 확인, 유지보수 전후 안전 점검을 핵심적으로 교육해야 한다. 그러나 {zero_or_count('추락', '추락')} ‘끼임’은 {fmt(k('끼임'))}건에 그쳤으며, 구체적인 사고 사례도 {f.cases.textbook_cases}건이라는 점을 보았을 때, 장비 유지보수 교육에서 실제 사고 예방 내용이 충분하지 않을 가능성이 있다."),
        ("반도체 재료·인프라 분야는",
         area_sentence("재료", "반도체 재료·인프라 분야는") + " 이 분야는 반도체 생산에 필요한 화학물질, 특수 가스, 전력, 초순수, 폐수처리, 각종 지원설비와 연결되기 때문에 안전보건 측면에서 매우 중요한 교육 영역이다."),
        ("특히 반도체산업의 대형 사고는",
         f"특히 반도체산업의 대형 사고는 생산공정 자체뿐 아니라 화학물질 공급, 가스 공급, 배기, 폐수·폐가스 처리, 시설 유지보수 과정 등에서 발생할 수 있다. 따라서 재료·인프라 분야에서는 GHS, SDS/MSDS, 화학물질 저장과 이송, 특수 가스 관리, 누출·화재·폭발·질식 예방과 비상 대응 등을 체계적으로 다룰 필요가 있다. 그러나 전체 교과서 분석에서 ‘물질안전보건자료’는 {fmt(k('물질안전보건자료'))}건, ‘MSDS’ {fmt(k('MSDS'))}건, ‘작업환경’ {fmt(k('작업환경'))}건, ‘유해 인자’ {fmt(k('유해인자'))}건에 그쳤다는 결과는 이 분야의 화학물질과 작업환경 교육도 상당한 보완이 필요함을 시사한다."),
        ("첫째, 등급 1은",
         f"첫째, 등급 1은 {fmt(s.grades[1])}건(약 {pct(s.grades[1], s.total)})으로 나타났다. 이는 교과서에서 ‘안전’, ‘위험’, ‘주의’ 등의 기본적인 표현은 어느 정도 사용하고 있으나, 대부분 위험 요인을 알리거나 일반적인 주의를 요구하는 수준에 머무른다고 해석할 수 있다."),
        ("둘째, 등급2는",
         f"둘째, 등급 2는 {fmt(s.grades[2])}건({pct(s.grades[2], s.total)})으로 ‘안전’, ‘위험’, ‘가스’, ‘방사선’ 등의 용어가 기술적 설명 과정에서 나타나더라도 실제 작업자의 사고나 건강위험 예방을 설명하는 내용은 아닌 경우가 많음을 의미한다. 따라서 단순한 키워드의 빈도만으로 안전보건교육 수준이 높다고 평가해서는 안 되며, 해당 문장의 내용과 교육적 맥락을 함께 평가하는 것이 중요하다."),
        ("셋째, 가장 중요한 등급 3",
         f"셋째, 가장 중요한 등급 3은 {fmt(g3)}건으로, 전체 {fmt(s.total)}건의 약 {pct(g3, s.total)}에 불과하였다. 등급 3은 구체적인 안전조치, 개인보호구 착용, 화학물질 안전 취급, 사고 시 대응 방법 등 실제 예방 행동으로 연결되는 교육 내용을 의미하므로, 이 비율이 매우 낮다는 것은 현재 교과서의 가장 큰 한계라고 할 수 있다. 즉, 현재 반도체 교과서가 학생이 ‘무엇이 위험한가’를 넘어서 ‘위험할 때 무엇을 해야 하는가’를 배우기 어려운 구조임을 알 수 있다."),
        ("반도체고등학교에서 사용하는 반도체 교과서",
         f"반도체고등학교에서 사용하는 반도체 교과서 {s.documents}권, 총 {fmt(pages_total)}쪽을 대상으로 {len(s.order)}개의 안전보건 관련 키워드를 분석한 결과, {detected}개 키워드에서 총 {fmt(s.total)}건이 검출되었다. 그러나 안전보건교육의 양과 구체성은 전반적으로 부족한 것으로 나타났다. 특히 예방조치와 작업 방법을 제시하는 등급 3은 {fmt(g3)}건({pct(g3, s.total)})에 불과하여, 위험 요인을 학생의 예방 행동으로 연결하는 교육 내용이 매우 적었다."),
        ("또한 공정안전관리, 직업병, 물질안전보건자료",
         f"또한 {', '.join(zero)} 등 {len(zero)}개 키워드가 전혀 검출되지 않았으며, 구체적인 사고 사례도 {s.documents}권 전체에서 {'한 건도 확인되지 않았다' if f.cases.textbook_cases == 0 else str(f.cases.textbook_cases) + '쪽에서만 확인되었다'}. 이를 통해 현재 반도체 교과서가 반도체의 기술과 공정 원리를 교육하는 데 중점을 두고 있지만, 산업현장에서 발생할 수 있는 사고·부상·화학물질 노출·직업병을 예방하기 위한 교육은 충분히 통합하지 못함을 알 수 있다."),
    ], conditions)


def _with_conditions(entries: list[tuple[str, str]], conditions: dict[str, dict]) -> list[tuple[str, str, dict]]:
    return [(prefix, text, conditions.get(prefix, {})) for prefix, text in entries]


def _safety_grade_sentences(safety: dict, gmax: int) -> str:
    """‘안전’ 의 등급 분포 문장 — 최다 등급이 1·2 면 '형식적' 해석, 3 이면 반대 해석 (F2: gmax 가정 없음)."""
    share = lambda g: f"{fmt(safety['grades'][g])}건({pct(safety['grades'][g], safety['total'])})"
    if gmax == 3:
        return (f"이 중 {iga('등급 3')} {share(3)}으로 가장 많았고, 등급 1은 {share(1)}, 등급 2는 {share(2)}였다. "
                "‘안전’이 등장하는 대목의 상당수가 구체적 조치와 함께 제시되었다고 해석할 수 있다.")
    other = 2 if gmax == 1 else 1
    return (f"그러나 이 중 {iga('등급 ' + str(gmax))} {share(gmax)}으로 가장 많았고, 등급 {other}도 {share(other)}에 달했다. 반면 등급 3은 {share(3)}으로 상대적으로 낮았다. "
            "‘안전’이라는 단어 자체는 자주 등장하지만, 실제로는 ‘안전에 유의한다.’ 수준의 일반적 표현이 많고, 구체적 예방 행동으로 연결되는 교육은 상대적으로 부족하다고 해석할 수 있다.")


def _equipment_case_sentences(c: CaseFacts, equip_pages: list[dict], equip_narrative: list[dict]) -> tuple[str, bool]:
    """장비 분야의 사고 사례 집중 문장과, 최다 교재가 장비 분야 책이라 『』 로 부를 수 있는지 (F2: 최다 교재 분야·오탐 0쪽 가정 없음)."""
    equip_flagged = c.by_area_flagged.get("장비", 0)
    if equip_flagged == 0:
        return f"사고 사례로 자동 판정된 {c.flagged}쪽 중 이 분야에 속한 쪽은 없었다(3절 참조).", False
    top_area = next(p["area"] for p in c.pages if p["title"] == c.top_book)
    top_in_equipment = top_area == "장비"
    where = (f"이 분야의 『{c.top_book}』 한 권에 몰려 있어" if top_in_equipment and c.top_book_pages == equip_flagged
             else f"이 분야에 몰려 있고 그중 {c.top_book_pages}쪽이 『{c.top_book}』 한 권에 있어" if top_in_equipment
             else "이 분야에 몰려 있어")
    lead = (f"이 분야의 가장 큰 특징은 사고 사례 집중이다. 사고 사례로 자동 판정된 {c.flagged}쪽 중 {equip_flagged}쪽({pct(equip_flagged, c.flagged)})이 {where}, "
            "반도체 교과서에서 사고 교육이 장비 중심으로 이루어지고 있음을 알 수 있다. ")
    rest = len(equip_pages) - len(equip_narrative)
    kinds = ro("·".join(FP_KIND_LABEL[k] for k, _ in Counter(p["kind"] for p in equip_pages if p["verdict"] == "false_positive").most_common()))
    gists = ", ".join(p["gist"].split(" (")[0] for p in equip_narrative)
    if equip_narrative and rest:
        tail = f"다만 원문을 확인하면 그중 실제 사고 서술은 {len(equip_narrative)}쪽({gists})이고 나머지 {rest}쪽은 {kinds}, 사고 사례 자체는 이 분야에서도 매우 적다(3절 참조)."
    elif equip_narrative:
        tail = f"원문을 확인하면 그중 {len(equip_narrative)}쪽({gists}) 모두 실제 사고 서술이다(3절 참조)."
    else:
        tail = f"다만 원문을 확인하면 그중 실제 사고 서술은 없고 {rest}쪽 모두 {kinds}, 사고 사례 자체는 이 분야에서도 매우 적다(3절 참조)."
    return lead + tail, top_in_equipment


def _g3_vs_overall_sentences(rel: dict[str, str], overall: str) -> str:
    """‘작업환경’·‘중독’ 의 등급 3 비율을 전체 평균과 견준 해석 문장 (F1: '수준 이상' 은 둘 다 평균을 웃돌 때만)."""
    first = {"높": f"전체 평균({overall}) 수준 이상의", "비슷": f"전체 평균({overall})과 비슷한 수준의", "낮": f"전체 평균({overall})에 못 미치는 수준의"}
    again = {"높": "그를 웃도는 수준의", "비슷": "그와 비슷한 수준의", "낮": "그에 못 미치는 수준의"}
    names = list(rel)
    if len(set(rel.values())) == 1:
        degree = first[rel[names[0]]]
    else:
        degree = f"{q(names[0])}은 {first[rel[names[0]]]}, {q(names[1])}은 {again[rel[names[1]]]}"
    lead = f"이 결과는 해당 키워드가 교과서에 자주 등장하지는 않더라도, 일단 등장하는 경우에는 {degree} 구체적인 설명이 수반되는 경향이 있음을 보여준다. "
    if "낮" in rel.values():
        return lead + "다시 말하면, 작업환경이나 중독 관련 내용은 양적으로 부족할 뿐 아니라 질적으로도 충실하다고 보기는 어렵다."
    if set(rel.values()) == {"높"}:
        return lead + "다시 말하면, 작업환경이나 중독 관련 내용은 양적으로는 부족하지만 질적으로는 상대적으로 충실한 편으로 해석할 수 있다."
    return lead + "다시 말하면, 작업환경이나 중독 관련 내용은 양적으로는 부족하지만 질적으로는 전체 평균에 뒤지지 않는 편으로 해석할 수 있다."


def ncs_paragraphs(f: Facts) -> list[tuple[str, str, dict]]:
    n = f.ncs
    c = f.cases
    k = lambda name: n.keywords[name]
    pages_total = sum(a["pages"] for a in n.areas.values())
    safety = k("안전")
    gmax = _grade_max(safety["grades"])
    accident_kw = ["화학물질", "위험", "보호구", "누출", "인화", "MSDS", "폭발", "진동", "화재"]
    ppe = k("보호구")
    ppe23 = ppe["grades"][2] + ppe["grades"][3]
    psm_all3 = k("공정안전관리")["grades"][3] == k("공정안전관리")["total"]
    ppe_majority = ppe23 / ppe["total"] >= PPE_MAJORITY
    materials_share = safety["areas"]["재료"]["total"] / safety["total"]
    near_half = NEAR_HALF[0] <= materials_share < NEAR_HALF[1]
    area_share = lambda area: pct(k("안전")["areas"][area]["total"], safety["total"])
    safety_rank = sorted(AREA_ORDER, key=lambda a: -safety["areas"][a]["total"])
    def area_intro(area, lead):
        a = n.areas[area]; sa = safety["areas"][area]["total"]
        return f"{lead} 총 {a['documents']}권, {fmt(a['pages'])}쪽에서 ‘안전’ 키워드가 {fmt(sa)}건 검출되어, 전체 {fmt(safety['total'])}건 중 약 {area_share(area)}를 차지하였다."
    equip_rank = safety_rank.index("장비") + 1
    equip_rel = "가장 높아" if equip_rank == 1 else f"{AREA_LABEL[safety_rank[0]]} 다음으로 높아" if equip_rank == 2 else f"{equip_rank}번째로 높아"
    equip_pages = [p for p in c.pages if p["area"] == "장비"]
    equip_narrative = [p for p in equip_pages if p["verdict"] in ("case", "case_other")]
    equip_sentences, equip_top_book = _equipment_case_sentences(c, equip_pages, equip_narrative)
    overall_g3 = n.grades[3] / n.total
    g3_rel = {name: _share_rel(k(name)["grades"][3] / k(name)["total"] if k(name)["total"] else 0.0, overall_g3) for name in ("작업환경", "중독")}
    workenv_vs_overall = "보다 낮았다" if "낮" in g3_rel.values() else "과 비슷하거나 그보다 높았다"   # 둘 다 평균 아래가 아닐 때만 "비슷하거나 높았다"
    safety_rank_kw = [name for name, _ in n.ranked()].index("안전") + 1
    grade2_rank = sorted((1, 2, 3), key=lambda g: (-n.grades[g], g)).index(2) + 1
    run_date, dictionary = provenance(f)
    real_pages = f.ncs_real_pages
    marker_books = len(f.marker_books)
    pages_note = (f"PDF 쪽수; 줄→쪽 대응이 없는 {marker_books}권은 쪽 표식 기준" if marker_books else "PDF 쪽수") if real_pages else "교재 마크다운의 쪽 표식 최댓값 합"
    conditions = {
        "NCS 기반 반도체 자료를 대상으로": {"page_basis": f.page_basis.get("NCS"), "marker_books": marker_books},
        "주: 단위: 건.": {"page_basis": f.page_basis.get("NCS")},
        "교과서의 전체 키워드 중 ‘안전’이": {"safety_top_grade": gmax, "safety_rank": safety_rank_kw},
        "‘작업환경’은": {"g3_vs_overall": workenv_vs_overall},
        "사고 관련 주요 키워드 검출 건수는": {"accident_keyword_order": [n for n, _ in sorted(((x, k(x)["total"]) for x in accident_kw), key=lambda kv: (-kv[1], n.order.index(kv[0])))]},
        "‘보호구’는": {"ppe_over_60pct": ppe_majority},
        "한편 ‘공정안전관리’는": {"psm_all_grade3": psm_all3},
        "한편 ‘공정안전관리’는 총": {"psm_all_grade3": psm_all3},
        "반도체 제조 분야는 총": {"safety_share_vs_pages": _compare_share(safety["areas"]["제조"]["total"] / safety["total"], n.areas["제조"]["pages"] / pages_total).strip()},
        "반도체 장비 분야는 총": {"equipment_safety_rank": equip_rank, "equipment_narrative_pages": len(equip_narrative), "equipment_top_book": equip_top_book},
        "반도체 재료 분야는 총": {"materials_is_top": safety_rank[0] == "재료", "near_half": near_half},
        "등급 2는 안전보건 관련 키워드가 확인되지만": {"largest_grade": _grade_max(n.grades), "grade2_rank": grade2_rank},
        "또한 ‘작업환경’은 총": {"g3_vs_overall": g3_rel},
    }
    return _with_conditions([
        ("NCS 기반 반도체 자료를 대상으로",
         f"NCS 기반 반도체 자료를 대상으로 안전보건교육 내용의 실태를 분석하였다. 분석 대상은 자료 {n.documents}권, 총 {fmt(pages_total)}쪽({pages_note})이며, ‘사망, 부상, 화학물질, 폭발, 감전, 직업병’ 등 {len(n.order)}개의 안전보건 관련 주요 키워드를 중심으로 AI 기반 텍스트 분석과 수기 검토를 병행하였다. 수치는 {run_date} 정본 재검산(의미 표현 사전 {dictionary}, 출현건수 기준, 총 {fmt(n.total)}건) 값이다."),
        ("교과서의 전체 키워드 중 ‘안전’이",
         f"교과서의 전체 키워드 중 ‘안전’이 총 {fmt(safety['total'])}건으로 검출 건수가 {'가장 많았다' if safety_rank_kw == 1 else str(safety_rank_kw) + '번째로 많았다'}. "
         + _safety_grade_sentences(safety, gmax)),
        ("사고 관련 주요 키워드 검출 건수는",
         f"사고 관련 주요 키워드 검출 건수는 {_rank_phrase(n, accident_kw)} 순으로 나타났다. ‘누출’, ‘인화’, ‘폭발’, ‘화재’는 비교적 빈도가 높았는데, 이는 화학물질·특수 가스 사용 등 반도체산업의 특성이 교과서에 일정 부분 반영된 결과로 보인다."),
        ("화학물질 관련 키워드는",
         f"화학물질 관련 키워드는 ‘화학물질’ {fmt(k('화학물질')['total'])}건, ‘MSDS’ {fmt(k('MSDS')['total'])}건, ‘물질안전보건자료’ {fmt(k('물질안전보건자료')['total'])}건이었다. ‘MSDS’와 ‘물질안전보건자료’는 같은 개념을 가리키지만 워크북의 키워드가 다르므로 합산하지 않고 독립 집계하였다. 분야별로 보면, ‘MSDS’는 "
         + ", ".join(f"{AREA_LABEL[a]} {fmt(k('MSDS')['areas'][a]['total'])}건" for a in sorted(AREA_ORDER, key=lambda a: -k('MSDS')['areas'][a]['total']))
         + " 순이었다. ‘화학물질’은 "
         + ", ".join(f"{AREA_LABEL[a]}에서 {fmt(k('화학물질')['areas'][a]['total'])}건" for a in sorted(AREA_ORDER, key=lambda a: -k('화학물질')['areas'][a]['total']))
         + "으로 나타났다. 이는 화학물질의 종류, 특성, 취급 주의 사항, 물질안전보건자료 확인 같은 기초 화학 안전교육 요소는 일정 수준 포함되어 있음을 의미한다. 그러나 이 용어나 내용이 곧바로 노출 경로, 만성 건강 영향, 직업병 예방, 작업환경 관리로 연결되지는 않았다."),
        ("건강 영향 관련 키워드는",
         f"건강 영향 관련 키워드는 ‘직업병’ {fmt(k('직업병')['total'])}건, ‘질병’ {fmt(k('질병')['total'])}건, ‘유해 인자’ {fmt(k('유해인자')['total'])}건이었다. 또한 ‘방사선’은 {fmt(k('방사선')['total'])}건, ‘소음’은 {fmt(k('소음')['total'])}건, ‘진동’은 {fmt(k('진동')['total'])}건이었지만, 이들 중 상당수는 장비 특성이나 공정 조건 설명에 그치는 경우가 많았다. 특히 ‘직업병’과 ‘질병’의 검출 건수가 매우 낮다는 점은 현재 교과서가 사고 예방 중심으로 구성되어 있으며, 만성 건강위험이나 장기 노출에 따른 질병 예방 교육은 거의 반영하지 못하고 있음을 시사한다. 반도체산업 현장에서 발생할 수 있는 암, 생식독성, 호흡기질환, 피부질환 등을 예방하기 위한 작업 방법, 유해 인자 관리 등의 내용은 거의 없었다."),
        ("‘보호구’는",
         f"‘보호구’는 {fmt(ppe['total'])}건이었고, 이 중 등급 2가 {fmt(ppe['grades'][2])}건({pct(ppe['grades'][2], ppe['total'])}), 등급 3이 {fmt(ppe['grades'][3])}건({pct(ppe['grades'][3], ppe['total'])})으로 "
         + (f"{int(PPE_MAJORITY * 100)}%를 넘었다." if ppe_majority else f"{pct(ppe23, ppe['total'])}였다.")
         + " 이를 통해 보호구 관련 교육은 비교적 구체적으로 제시되고 있음을 알 수 있다. 실제로 안전화, 헬멧, 보호 장갑, 보호안경, 안전벨트 등 보호구의 종류와 착용 필요성은 상당히 자주 언급된다. 그러나 보호구를 왜 착용해야 하는지, 어떤 위험 요인에 대응하는지, 선택 기준과 한계는 무엇인지까지 확장된 설명은 부족하였다."),
        ("‘작업환경’은",
         f"‘작업환경’은 {fmt(k('작업환경')['total'])}건, ‘중독’은 {fmt(k('중독')['total'])}건으로 검출 건수 자체는 많지 않았다. 하지만 ‘작업환경’의 등급 3 비율은 {fmt(k('작업환경')['grades'][3])}건({pct(k('작업환경')['grades'][3], k('작업환경')['total'])}), ‘중독’의 등급 3 비율은 {fmt(k('중독')['grades'][3])}건({pct(k('중독')['grades'][3], k('중독')['total'])})으로 나타나 전체 등급 3 비율({pct(n.grades[3], n.total)}){workenv_vs_overall}. {'이는 해당 키워드가 나올 때 단순 언급보다 구체적 상황 설명이나 예방·관리 내용까지 포함된 경우가 적지 않았다는 뜻이다.' if not workenv_vs_overall.startswith('보다') else '즉 이 두 키워드도 대부분 단순 언급에 머문다.'} 다만 절대 건수가 적기 때문에 교과서 전반에서 작업환경 관리와 건강위험 예방이 충분히 체계화되었다고 보기는 어렵다."),
        ("한편 ‘공정안전관리’는",
         f"한편 ‘공정안전관리’는 {fmt(k('공정안전관리')['total'])}건, ‘PSM’은 {fmt(k('PSM')['total'])}건, ‘산업안전보건법’은 {fmt(k('산업안전보건법')['total'])}건에 그쳤다. ‘공정안전관리’는 검출 건수는 매우 적지만, "
         + ("검출된 내용이 모두 등급 3으로 분류되어, " if psm_all3 else f"{fmt(k('공정안전관리')['grades'][3])}건이 등급 3으로 분류되어, ")
         + "언급될 때는 상대적으로 구체적인 설명이 있었음을 알 수 있다. 그러나 전체 분량 자체가 너무 적기 때문에 학생이 공정안전관리, 법적 책임, 안전보건 체계, 노동자의 권리와 의무를 체계적으로 배우기에는 한계가 있다."),
        ("반도체 개발 분야는 총",
         area_intro("개발", "반도체 개발 분야는") + " 이는 절대적인 검출 건수 자체가 적을 뿐 아니라, 전체 교과서 구조 내에서도 상대적으로 낮은 비중이다."),
        ("반도체 제조 분야는 총",
         area_intro("제조", "반도체 제조 분야는") + f" 이는 쪽수 비율({pct(n.areas['제조']['pages'], pages_total)}){_compare_share(safety['areas']['제조']['total'] / safety['total'], n.areas['제조']['pages'] / pages_total)}, 안전보건 내용이 일정 수준 포함되어 있으나 크게 강조되지는 않는 중간 수준의 영역으로 평가된다."),
        ("그러나 등급별 분석에서는 등급 2(형식적 언급)의 비중이 높아",
         f"그러나 등급별 분석에서는 등급 2(형식적 언급)의 비중이 높아, 위험 요인과 예방조치가 구체적으로 연결되지 않는 경우가 많았다. 또한 사고 사례로 자동 판정된 쪽은 이 분야에서 {c.by_area_flagged.get('제조', 0)}쪽으로, 실제 공정에서 발생할 수 있는 다양한 재해 유형을 충분히 반영하지 못한다. 즉, 반도체 제조 분야는 안전교육이 있긴 하지만, 대부분이 공정 설명에 부수적으로 포함된 수준이며, 독립적이고 체계적인 안전보건교육으로 보기에는 한계가 있다."),
        ("반도체 장비 분야는 총",
         area_intro("장비", "반도체 장비 분야는") + f" 이는 {equip_rel}, 안전보건교육이 비교적 많이 포함된 분야이다. " + equip_sentences),
        ("반도체 재료 분야는 총",
         area_intro("재료", "반도체 재료 분야는").replace("차지하였다.", f"차지하여 분야 중 {'가장 높은' if safety_rank[0] == '재료' else str(safety_rank.index('재료') + 1) + '번째'} 비중을 보였다.")
         + (" 전체 안전보건교육 내용의 절반 가까이가 이 분야에 집중된 셈이다." if near_half else "")),
        ("실제로 전체적으로 가장 많이 검출된 키워드인 ‘안전’의 경우에도",
         f"실제로 전체적으로 가장 많이 검출된 키워드인 ‘안전’의 경우에도 총 {fmt(safety['total'])}건 중 {fmt(safety['grades'][1])}건({pct(safety['grades'][1], safety['total'])})이 등급 1로 분류되었다. 교과서 내에서 안전 관련 용어가 부분적으로 사용되더라도 실제로는 공정 설명, 설비 설명, 제품 설명에 부수적으로 언급된 것에 불과한 경우가 적지 않다는 점을 보여준다. 이러한 결과는 현재 반도체 교과서에서 안전보건이 독립적 교육 내용으로 충분히 자리 잡지 못하고 있음을 시사한다."),
        ("등급 2는 안전보건 관련 키워드가 확인되지만",
         f"등급 2는 안전보건 관련 키워드가 확인되지만, 내용이 대체로 선언적·추상적 수준에 머무는 경우를 의미한다. 대표적으로 “안전에 유의한다”, “작업 시 주의한다”, “보호구를 착용한다”, “화학물질 취급에 주의가 필요하다”와 같은 표현이 여기에 해당한다. 이러한 내용은 안전보건의 중요성을 암시하거나 기본적인 경각심을 주는 데는 의미가 있으나, 어떤 위험 요인이 존재하며, 그 위험을 줄이기 위해 어떤 조치를 어떻게 취해야 하는지까지는 충분히 설명하지 못한다. {'실제로 본 연구에서 가장 두드러진 결과는 등급 2의 비중이 가장 높다는 점이었다.' if grade2_rank == 1 else f'실제로 본 연구에서 등급 2(형식적 언급)의 비중은 세 등급 중 {grade2_rank}번째였다.'} 전체 분석 결과, 등급 1(미흡·없음)은 {fmt(n.grades[1])}건, 등급 2(형식적 언급)는 {fmt(n.grades[2])}건, 등급 3(구체적 대책)은 {fmt(n.grades[3])}건으로 나타나 {iga('등급 ' + str(_grade_max(n.grades)))} 가장 많았으며, 이는 전체의 약 {pct(n.grades[_grade_max(n.grades)], n.total)}를 차지하였다. 특히 ‘안전’ 키워드는 총 {fmt(safety['total'])}건 중 {fmt(safety['grades'][2])}건({pct(safety['grades'][2], safety['total'])})이 등급 2였다. 이 결과는 현재 반도체 교과서의 안전보건교육이 “안전은 중요하다”는 메시지를 전달하는 수준에는 도달했지만, 학생이 실제 현장에서 위험을 식별하고 예방 행동을 수행할 수 있도록 돕는 수준까지는 충분히 발전하지 못했다는 점을 보여준다."),
        ("등급 3은 위험 요인, 사고 유형, 건강 영향",
         f"등급 3은 위험 요인, 사고 유형, 건강 영향, 예방 대책, 작업 절차, 보호구 사용법, 비상 대응 등이 구체적으로 제시되어 실제 행동과 연결 가능한 수준의 교육 내용을 의미한다. 이 등급은 단순히 “주의하라”는 수준을 넘어, 예를 들어 “불산 취급 시 보호장갑과 보호안경을 착용해야 하며 피부 접촉 시 즉시 세척하고 응급조치를 시행한다”와 같이 위험 요인–예방조치–대응 방법이 연계되어 설명되는 경우를 포함한다. 전체적으로 등급 3은 {fmt(n.grades[3])}건으로 전체의 약 {pct(n.grades[3], n.total)}를 차지하였다. 이는 교과서 내에 구체적 안전보건 내용이 일정 부분 존재함을 보여주지만, 여전히 형식적 언급(등급 2)에 비해 적은 수준이다. 즉, 현재 교과서는 구체적이고 실천 가능한 안전교육을 일부 포함하고 있으나, 전체 교육 구조를 대표할 정도로 충분한 비중은 아니라고 볼 수 있다. 키워드별로 보면, 등급 3의 비율이 상대적으로 높은 항목도 확인되었다. 예를 들어 ‘보호구’는 총 {fmt(ppe['total'])}건 중 {fmt(ppe['grades'][3])}건({pct(ppe['grades'][3], ppe['total'])})이 등급 3으로 분류되었다. 이는 보호구 관련 내용이 등장하는 경우에는 비교적 구체적으로 설명되는 비율이 높다는 뜻이다. 즉, 안전화, 헬멧, 보호안경, 장갑 등 보호구의 종류나 착용 필요성이 실제 작업과 연결되어 설명되는 경우가 많았음을 의미한다."),
        ("또한 ‘작업환경’은 총",
         f"또한 ‘작업환경’은 총 {fmt(k('작업환경')['total'])}건 중 {pct(k('작업환경')['grades'][3], k('작업환경')['total'])}, ‘중독’은 총 {fmt(k('중독')['total'])}건 중 {pct(k('중독')['grades'][3], k('중독')['total'])}가 등급 3에 해당하였다. "
         + _g3_vs_overall_sentences(g3_rel, pct(n.grades[3], n.total))),
        ("한편 ‘공정안전관리’는 총",
         f"한편 ‘공정안전관리’는 총 {fmt(k('공정안전관리')['total'])}건, ‘PSM’은 총 {fmt(k('PSM')['total'])}건으로 절대 빈도는 매우 낮았으나, "
         + ("특히 공정안전관리의 경우 검출된 내용이 모두 등급 3에 해당하였다. " if psm_all3 else f"공정안전관리의 경우 {fmt(k('공정안전관리')['grades'][3])}건({pct(k('공정안전관리')['grades'][3], k('공정안전관리')['total'])})이 등급 3에 해당하였다. ")
         + "이는 해당 개념이 교과서에 거의 포함되어 있지 않지만, 포함되는 경우에는 비교적 구체적이고 전문적인 내용으로 제시되고 있음을 의미한다. 그러나 빈도 자체가 매우 적기 때문에 이를 근거로 교과서 전반의 공정안전교육 수준이 충분하다고 평가하기는 어렵다."),
        ("주: 단위: 건.",
         f"주: 단위: 건. 등급 비율의 분모: {fmt(n.total)}건({run_date} 정본, 의미 표현 사전 {dictionary}, 등급 미확정 0건). {'등급은 출현이 놓인 실제 PDF 쪽(줄→쪽 대응)의 본문을 기준선 규칙으로 판정한 값을 출현별로 연결한 값임.' if real_pages else '등급은 출현이 놓인 페이지의 판정값을 출현별로 연결한 값임.'}"),
    ], conditions)


def case_paragraphs(f: Facts) -> list[tuple[str, str, dict]]:
    c = f.cases
    industrial_books = [p["title"] for p in c.pages if p["verdict"] == "case"]
    other = [p for p in c.pages if p["verdict"] == "case_other"]
    kinds = c.fp_kinds
    areas_without = [a for a in AREA_ORDER if c.by_area_flagged.get(a, 0) == 0]
    top_area = next(p["area"] for p in c.pages if p["title"] == c.top_book)
    top_area_label = {"장비": "장비 유지보수와 점검 작업", "재료": "재료·화학물질 취급", "제조": "제조 공정", "개발": "개발"}[top_area]
    industrial_areas = sorted({p["area"] for p in c.pages if p["verdict"] == "case"}, key=AREA_ORDER.index)
    narrative_events = len({p.get("event", p["gist"]) for p in c.pages if p["verdict"] in ("case", "case_other")})   # 사건 수 — 같은 사건의 중복 게재는 하나
    fp_breakdown = ", ".join(f"{FP_KIND_LABEL[kind]}({n}쪽)" for kind, n in kinds.most_common())
    conditions = {
        "본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를": {"flagged": c.flagged, "narrative": c.narrative, "industrial_events": c.industrial_events, "false_positive": c.false_positive,
                                                          "page_basis": f.page_basis.get("NCS")},
        "사례의 분포를 보면": {"areas_without_cases": areas_without, "top_area": top_area},
        "이러한 분석 결과를 종합하면, NCS 반도체 교과서에 수록된 사고 사례는": {"industrial_areas": industrial_areas, "narrative_events": narrative_events},
    }
    return _with_conditions([
        ("본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를",
         f"본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를 체계적으로 수집·정리하고, 내용 수준과 구성 특성을 분석하였다. 키워드 검색 결과의 ‘사고사례여부’ 자동 판정은 {c.books}권 {c.flagged}쪽을 사례로 잡았으나, 해당 쪽의 원문을 확인한 결과 실제로 사고를 서술한 쪽은 {c.narrative}쪽뿐이었고, 그중 반도체 산업재해는 구미 불산 가스 누출 사고 {c.industrial_events}건({' '.join(wa('『' + b + '』') if i < len(dict.fromkeys(industrial_books)) - 1 else '『' + b + '』' for i, b in enumerate(dict.fromkeys(industrial_books)))} {c.industrial_books}권에 중복 게재)이었으며, 나머지 {len(other)}쪽은 반도체 산업재해가 아닌 사고({', '.join(p['gist'].split(' (')[0] for p in other)})였다(표 13 참조). {'표 13 의 쪽 번호와 1·2절의 분야별 쪽수는 모두 실제 PDF 쪽 기준이다(재세그먼트 줄→쪽 대응).' if f.ncs_real_pages else '표 13 의 쪽 번호는 재세그먼트로 확인한 실제 PDF 쪽이다(1·2절의 분야별 쪽수는 마크다운 쪽 표식 최댓값).'} 이러한 결과는 반도체산업이 화학물질, 특수 가스, 고에너지 장비 등을 활용하는 대표적인 고위험 산업임을 감안할 때, 교과서에 수록된 사고 사례의 양적 수준이 매우 제한적임을 보여 준다."),
        ("사례의 분포를 보면",
         f"사례의 분포를 보면, 자동 판정 {c.flagged}쪽 중 {c.top_book_pages}쪽이 『{c.top_book}』에 몰려 있어, 현재 교과서에서 사고 관련 내용이 주로 {top_area_label} 중심으로 구성되어 있다. "
         + (f"반면 {', '.join(areas_without)} 분야에서는 사고 사례가 전혀 제시되지 않아, 공정과 직무 전반을 반영한 균형 있는 교육 구성은 부족한 것으로 나타났다." if areas_without
            else "네 분야 모두에서 사례가 나오지만 분포가 한 권에 치우쳐, 공정과 직무 전반을 반영한 균형 있는 교육 구성은 부족한 것으로 나타났다.")),
        ("사고 유형 측면에서는",
         f"사고 유형 측면에서는 실제 사고 서술 {c.narrative}쪽이 화학물질(불산) 누출 사고와 시설물(환풍구) 붕괴 사고였다. 자동 판정이 사례로 잡은 나머지 {c.false_positive}쪽은 {fp_breakdown}으로, TMAH·아르신 노출이나 이온주입 장비의 방사선 노출은 사고 사례가 아니라 취급 지침과 유해성 설명의 맥락에서 언급된 것이었다. 즉, 반도체산업의 주요 위험 요인 자체는 교과서에 등장하지만, 그것이 실제 사고 사례로 제시되는 경우는 불산 누출 사고 {c.industrial_events}건에 그친다."),
        ("사례의 서술 방식 또한 중요한 특징이다",
         "사례의 서술 방식 또한 중요한 특징이다. 실제 사고 서술은 한두 문장으로 매우 간략하게 제시되어, 사고의 발생 원인, 작업조건, 진행 경과, 피해 규모, 재발 방지 대책 등 교육적으로 중요한 정보가 거의 포함되지 않았다. 즉, 학습자가 해당 사례를 통해 위험 요인을 분석하거나 예방 행동을 학습하기에는 충분한 정보가 제공되지 않는 구조이다."),
        ("또한 사고 사례는 대부분 위험 상황을 단순히 언급하는 수준에",
         "또한 사고 사례는 위험 상황을 단순히 언급하는 수준에 머물러 있으며, 위험 요인 분석이나 예방조치와 연계성이 부족하였다. 이는 사고 사례가 교육적 학습 자료로 활용되기보다는 참고 수준의 정보로 제시되고 있음을 의미한다. 결과적으로 현재 교과서는 사고가 있음을 알리는 기능은 수행하고 있으나, 사고를 통한 위험 인식 강화나 예방 행동 유도 측면에서는 제한적인 역할에 머무르고 있다."),
        ("이러한 분석 결과를 종합하면, NCS 반도체 교과서에 수록된 사고 사례는",
         f"이러한 분석 결과를 종합하면, NCS 반도체 교과서에 수록된 사고 사례는 양적·질적 측면에서 모두 제한적인 수준이며, 반도체산업의 실제 위험 구조를 충분히 반영하지 못한다고 판단된다. 특히 실제 사고 서술이 {c.narrative}쪽·{narrative_events}건(그중 반도체 산업재해 {c.industrial_events}건)에 불과하고, 그마저 {'·'.join(a + ' 분야' for a in industrial_areas)}의 {c.industrial_books}권에 중복 게재된 화학물질 급성 사고 위주이며, 사고 원인과 예방 대책이 충분히 제시되지 않는다는 점은 교육적 활용도를 저해하는 주요 요인이다. 아울러 자동 판정 {c.flagged}쪽 중 {c.false_positive}쪽이 오탐이었다는 점은 키워드 기반 자동 판정만으로 사고 사례를 세어서는 안 되며 원문 확인이 필요함을 보여준다."),
    ], conditions)


PARAGRAPH_TEMPLATES = {"textbook": textbook_paragraphs, "ncs": ncs_paragraphs, "cases": case_paragraphs}


# ---------------------------------------------------------------- 표
def keyword_table_rows(corpus: CorpusFacts) -> list[list[str]]:
    rows = [[name, fmt(v["total"]), fmt(v["grades"][1]), fmt(v["grades"][2]), fmt(v["grades"][3]), fmt(sum(v["grades"].values()))] for name, v in corpus.ranked()]
    rows.append(["합계", fmt(corpus.total), fmt(corpus.grades[1]), fmt(corpus.grades[2]), fmt(corpus.grades[3]), fmt(sum(corpus.grades.values()))])
    return rows


def area_table_rows(corpus: CorpusFacts, with_grade_sum: bool) -> list[list[str]]:
    rows = []
    for area in AREA_ORDER:
        a = corpus.areas[area]
        row = [area, str(a["documents"]), fmt(a["total"]), fmt(a["grades"][1]), fmt(a["grades"][2]), fmt(a["grades"][3])]
        if with_grade_sum:
            row.append(fmt(sum(a["grades"].values())))
        row.append(pct(a["total"], corpus.total))
        rows.append(row)
    total = ["합계", str(corpus.documents), fmt(corpus.total), fmt(corpus.grades[1]), fmt(corpus.grades[2]), fmt(corpus.grades[3])]
    if with_grade_sum:
        total.append(fmt(sum(corpus.grades.values())))
    total.append("100.0%")
    rows.append(total)
    return rows


def grade_table_rows(corpus: CorpusFacts) -> list[list[str]]:
    rows = [[f"등급 {g}", GRADE_LABEL[g], fmt(corpus.grades[g]), pct(corpus.grades[g], corpus.total)] for g in (1, 2, 3)]
    rows.append(["합계", "등급 1~3", fmt(corpus.total), "100.0%"])
    return rows


VERDICT_LABEL = {"case": "실제 사고 서술 (반도체 산업재해)", "case_other": "실제 사고 서술 (반도체 산업재해 아님)", "false_positive": "오탐 (지침·정의·물성)"}


def case_table_rows(cases: CaseFacts) -> list[list[str]]:
    order = {"case": 0, "case_other": 1, "false_positive": 2}
    pages = sorted(cases.pages, key=lambda p: (order[p["verdict"]], p["title"], p["page"]))
    return [[p["title"], p["area"], p["gist"], str(p["page"]), VERDICT_LABEL[p["verdict"]]] for p in pages]


def fill_table(tbl: ET.Element, rows: list[list[str]], first_data_row: int, header: list[str] | None = None) -> int:
    """데이터 행에 값을 채운다 — 행·열 수는 원본과 같아야 하며(표 13 은 미리 resize), 바뀐 셀 수를 돌려준다."""
    trs = table_rows(tbl)
    data = trs[first_data_row:]
    while len(data) > len(rows) and all(cell_text(tc) == "" for tc in data[-1]):
        data.pop()                                            # 표 끝의 빈 간격 행은 데이터 행이 아니다
    if len(data) != len(rows):
        raise ValueError(f"표 행 수 {len(data)} ≠ 값 행 수 {len(rows)}")
    changed = 0
    if header is not None:
        if len(trs[first_data_row - 1]) != len(header):
            raise ValueError(f"표 헤더 열 수 {len(trs[first_data_row - 1])} ≠ 값 열 수 {len(header)}")
        for tc, value in zip(trs[first_data_row - 1], header):
            if cell_text(tc) != value:
                set_cell(tc, value); changed += 1
    for tcs, values in zip(data, rows):
        if len(tcs) != len(values):
            raise ValueError(f"표 열 수 {len(tcs)} ≠ 값 열 수 {len(values)}")
        for tc, value in zip(tcs, values):
            if cell_text(tc) != value:
                set_cell(tc, value); changed += 1
    return changed


# ---------------------------------------------------------------- 그림
def image_dimensions(data: bytes) -> tuple[int, int, str]:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h, kind = *struct.unpack(">II", data[16:24]), "PNG"
    elif data[:2] == b"BM":
        w, h = struct.unpack("<ii", data[18:26]); h, kind = abs(h), "BMP"
    else:
        raise ValueError("PNG 또는 BMP 가 아닙니다")
    if not (0 < w <= MAX_IMAGE_SIDE and 0 < h <= MAX_IMAGE_SIDE):
        raise ValueError(f"그림 크기 {w}×{h} 가 상한({MAX_IMAGE_SIDE})을 넘거나 0 입니다 — 헤더가 손상됐거나 악성입니다")
    return w, h, kind


def image_bits(data: bytes) -> int:
    """비트 깊이 — BMP 는 biBitCount, PNG 는 IHDR 의 bit depth × 채널 수(색 유형 2 = RGB)."""
    if data[:2] == b"BM":
        return struct.unpack("<H", data[28:30])[0]
    depth, color_type = data[24], data[25]
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    return depth * channels


MIN_GLYPH_PX = 12                   # 한글 하한 (CLAUDE.md 디자인 토큰 --fs-xs) — 작은 래스터(그림 2, 702×391)에서도 지킨다


def _svg_text(x, y, text, size=28, fill="#243244", anchor="start", weight="normal"):
    size = max(MIN_GLYPH_PX, int(size))
    return f'<text x="{x}" y="{y}" font-family="AppleGothic, sans-serif" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(text))}</text>'   # 정본 JSON 의 문자열이라도 SVG 로는 escape 해서 넣는다


def grade_bars_svg(width: int, height: int, title: str, subtitle: str, grades: dict[int, int], total: int, note: str) -> str:
    s = height / 724
    left = int(230 * s); right = width - int(60 * s); top = int(175 * s); step = int(145 * s); bar_h = int(70 * s)
    max_v = max(grades.values()) or 1
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#ffffff"/>',
             _svg_text(width / 2, int(55 * s), title, int(34 * s), anchor="middle"), _svg_text(width / 2, int(100 * s), subtitle, int(22 * s), fill="#5b6675", anchor="middle")]
    for i, g in enumerate((1, 2, 3)):
        y = top + i * step
        w = max(int((right - left - int(300 * s)) * grades[g] / max_v), 4)
        parts.append(_svg_text(left - int(25 * s), y + int(28 * s), f"등급 {g}", int(30 * s), anchor="end"))
        parts.append(_svg_text(left - int(25 * s), y + int(58 * s), GRADE_LABEL[g], int(20 * s), fill="#5b6675", anchor="end"))
        parts.append(f'<rect x="{left}" y="{y}" width="{w}" height="{bar_h}" rx="4" fill="{COLORS[g]}"/>')
        parts.append(_svg_text(left + w + int(18 * s), y + int(45 * s), f"{fmt(grades[g])}건 ({pct(grades[g], total)})", int(30 * s)))
    for j, line in enumerate(note.split("\n")):
        parts.append(_svg_text(width / 2, height - int(60 * s) + j * int(32 * s), line, int(20 * s), fill="#5b6675", anchor="middle"))
    parts.append("</svg>")
    return "".join(parts)


def area_bars_svg(width: int, height: int, title: str, areas: dict[str, dict], note: str) -> str:
    s = height / 750
    left = int(170 * s); top = int(165 * s); group_step = int(120 * s); bar_h = int(24 * s); gap = int(5 * s)
    max_v = max(a["grades"][g] for a in areas.values() for g in (1, 2, 3)) or 1
    scale = (width - left - int(260 * s)) / max_v
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#ffffff"/>',
             _svg_text(width / 2, int(55 * s), title, int(34 * s), anchor="middle")]
    for i, g in enumerate((1, 2, 3)):
        x = int(100 * s) + i * int(350 * s)
        parts.append(f'<rect x="{x}" y="{int(88 * s)}" width="{int(20 * s)}" height="{int(20 * s)}" fill="{COLORS[g]}"/>')
        parts.append(_svg_text(x + int(30 * s), y=int(106 * s), text=f"등급 {g} {GRADE_LABEL[g]}", size=int(22 * s)))
    for i, area in enumerate(AREA_ORDER):
        y0 = top + i * group_step
        parts.append(_svg_text(left - int(25 * s), y0 + int(38 * s), area, int(30 * s), anchor="end"))
        for j, g in enumerate((1, 2, 3)):
            y = y0 + j * (bar_h + gap)
            w = max(int(areas[area]["grades"][g] * scale), 3)
            parts.append(f'<rect x="{left}" y="{y}" width="{w}" height="{bar_h}" fill="{COLORS[g]}"/>')
            parts.append(_svg_text(left + w + int(12 * s), y + int(20 * s), f"{fmt(areas[area]['grades'][g])}건", int(22 * s)))
    for j, line in enumerate(note.split("\n")):
        parts.append(_svg_text(width / 2, height - int(50 * s) + j * int(30 * s), line, int(20 * s), fill="#5b6675", anchor="middle"))
    parts.append("</svg>")
    return "".join(parts)


def render_svg(svg: str, fmt_: str, width: int, height: int) -> bytes:
    """ImageMagick — PNG24 또는 BMP3(24bit). 폰트 경로 고정 + 메타데이터 제거(-strip)로 같은 magick·폰트면 바이트가 같다."""
    if shutil.which("magick") is None:
        raise RuntimeError("ImageMagick(magick)이 없어 그림을 그릴 수 없습니다")
    with tempfile.TemporaryDirectory() as td:
        svg_path = Path(td) / "chart.svg"
        svg_path.write_text(svg, encoding="utf-8")
        target = "PNG24:-" if fmt_ == "PNG" else "BMP3:-"
        font_args = ["-font", FONT] if Path(FONT).exists() else []
        out = subprocess.run(["magick", "-density", "96", "-background", "white", *font_args, str(svg_path), "-resize", f"{width}x{height}!", "-type", "TrueColor", "-strip", target],   # -strip: 날짜 tEXt/tIME 청크 제거 → 같은 입력이면 같은 바이트
                             check=True, capture_output=True).stdout
    w, h, kind = image_dimensions(out)
    if (w, h, kind) != (width, height, fmt_):
        raise RuntimeError(f"렌더 결과 {kind} {w}×{h} ≠ 요청 {fmt_} {width}×{height}")
    if kind == "BMP" and image_bits(out) != 24:
        raise RuntimeError(f"BMP 비트 깊이 {image_bits(out)} ≠ 24")
    return out


def figure_specs(f: Facts) -> list[dict]:
    """(절, 캡션 접두, svg 함수) — 그림 2 교과서 등급별, 그림 3 NCS 분야별, 그림 4 NCS 등급별."""
    stamp = f"정본 {str(f.run.get('generated_at', ''))[:10]} · 의미 표현 사전 {f.run.get('dictionary', '')} · 출현건수 기준"
    return [
        {"section": "textbook", "caption": None, "item": "image1", "label": "그림 2", "alt": "교과서 안전보건 등급별 출현건수 막대 그래프", "svg": lambda w, h: grade_bars_svg(w, h, "교과서 안전보건 등급별 출현건수", f"등급 판정 {fmt(f.school.total)}건 · 출현건수 기준", f.school.grades, f.school.total, f"{stamp}\n교과서 {f.school.documents}권 · 등급 미확정 0건")},
        {"section": "ncs", "caption": "그림 3.", "item": None, "label": "그림 3", "alt": "NCS 분야별 등급 출현건수 막대 그래프", "svg": lambda w, h: area_bars_svg(w, h, "NCS 분야별 등급 출현건수", f.ncs.areas, f"원자료 폴더 기준 · NCS {f.ncs.documents}권 {fmt(f.ncs.total)}건에 등급 1~3 배정\n{stamp}")},
        {"section": "ncs", "caption": "그림 4.", "item": None, "label": "그림 4", "alt": "NCS 안전보건 등급별 출현건수 막대 그래프", "svg": lambda w, h: grade_bars_svg(w, h, "NCS 안전보건 등급별 출현건수", f"등급 판정 {fmt(f.ncs.total)}건 · 출현건수 기준", f.ncs.grades, f.ncs.total, f"등급: 출현이 놓인 페이지의 판정값을 각 키워드 출현에 연결 · 미확정 0건\n{stamp}")},
    ]


# ---------------------------------------------------------------- ZIP
MAX_ENTRY_BYTES = 256 * 1024 ** 2          # HWPX 항목 하나의 압축 해제 상한 (정본 section0.xml 1.7 MB, 그림 수 MB) — 압축 폭탄 방어 (Codex 적대적 리뷰)
MAX_ZIP_RATIO = 200                        # 압축 비율 상한 — truncation_audit.py 와 같은 규칙
MAX_IMAGE_SIDE = 20000                     # 그림 한 변 픽셀 상한 — 헤더의 크기를 그대로 ImageMagick 에 넘기지 않는다


def _check_entry(info: zipfile.ZipInfo) -> None:
    ratio = info.file_size / max(1, info.compress_size)
    if info.file_size > MAX_ENTRY_BYTES or ratio > MAX_ZIP_RATIO:
        raise ValueError(f"HWPX 항목 {info.filename} 이 너무 크거나 압축 비율이 비정상입니다 ({info.file_size} B, {ratio:.0f}×) — 상한 {MAX_ENTRY_BYTES} B / {MAX_ZIP_RATIO}×")


def read_section(hwpx: Path) -> tuple[bytes, ET.Element, str]:
    with zipfile.ZipFile(hwpx) as z:
        _check_entry(z.getinfo(SECTION_ENTRY))
        raw = z.read(SECTION_ENTRY)
    text = raw.decode("utf-8")
    m = re.search(r"<hs:sec\b[^>]*>", text)
    if not m:
        raise ValueError("section0.xml 의 hs:sec 루트를 찾지 못했습니다")
    for prefix, uri in re.findall(r'xmlns:([A-Za-z0-9]+)="([^"]+)"', m.group(0)):
        ET.register_namespace(prefix, uri)
    return raw, ET.fromstring(raw), m.group(0)


def serialize_section(root: ET.Element, root_tag: str) -> bytes:
    """원본 루트 시작 태그(선언 순서·미사용 네임스페이스 보존)로 되돌리되, ElementTree 가 루트로 끌어올린 선언 중 원본 태그에 없는 것은 덧붙인다
    (후손에 선언돼 있던 네임스페이스가 사라져 unbound prefix 가 되던 경우 — Codex 적대적 리뷰). 결과는 다시 파싱해 검증한다."""
    body = ET.tostring(root, encoding="unicode")
    generated = re.match(r"<hs:sec\b[^>]*>", body)
    if not generated:
        raise ValueError("직렬화 결과에 hs:sec 루트가 없습니다")
    original_prefixes = set(re.findall(r'xmlns:([A-Za-z0-9]+)=', root_tag))
    missing = [(pfx, uri) for pfx, uri in re.findall(r'xmlns:([A-Za-z0-9]+)="([^"]+)"', generated.group(0)) if pfx not in original_prefixes]
    tag = root_tag[:-1] + "".join(f' xmlns:{pfx}="{uri}"' for pfx, uri in missing) + ">"
    body = tag + body[generated.end():]
    data = (XML_DECL + body).encode("utf-8")
    ET.fromstring(data)                                       # 잘 만들어지지 않으면 여기서 멈춘다 — 깨진 XML 을 ZIP 에 넣지 않는다
    return data


def write_hwpx(src: Path, out: Path, section_xml: bytes, bindata: dict[str, bytes], force: bool = False) -> tuple[Path | None, str]:
    """새 HWPX 를 쓴다. 기존 출력이 있으면 --force 없이는 거부하고, --force 면 먼저 `<out>.<sha16>.bak` 로 보존한다(같은 내용이면 같은 이름 — 재실행에 안전).
    반환: (백업 경로 또는 None, 쓴 바이트의 sha256 — 다시 읽지 않고 임시 파일에서 잰다: 다른 프로세스가 그 사이에 바꿔치기해도 대조 JSON 은 우리가 쓴 것을 말한다)."""
    src, out = Path(src), Path(out)
    if src.resolve() == out.resolve():
        raise ValueError("출력이 입력과 같은 파일입니다 — 원본은 덮어쓰지 않습니다")
    backup = None
    if out.exists():
        if not force:
            raise FileExistsError(f"{out.name} 이 이미 있습니다 (--force 로 덮어쓰기 — 기존 파일은 .bak 로 남습니다)")
        previous = out.read_bytes()
        digest = sha256(previous)
        backup = out.with_name(f"{out.name}.{digest[:16]}.bak")          # 64비트 접두 — 8자리(32비트)는 충돌을 노릴 수 있다 (Codex 적대적 리뷰)
        if backup.is_symlink():
            raise ValueError(f"백업 자리 {backup.name} 가 심볼릭 링크입니다 — 덮어쓰지 않습니다")
        if not backup.exists() or sha256(backup.read_bytes()) != digest:      # 없거나(또는 끊긴 반쪽 백업이면) 원자적으로 다시 쓴다 (보안 리뷰)
            fd, tmp_name = tempfile.mkstemp(dir=out.parent, prefix=backup.name + ".", suffix=".tmp")
            with os.fdopen(fd, "wb") as fh:
                fh.write(previous)
            os.replace(tmp_name, backup)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=out.parent, prefix=out.name + ".", suffix=".tmp")    # 배타적 생성 — 고정 이름·심볼릭 링크·동시 실행 충돌 없음
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        if tmp.resolve() == src.resolve():
            raise ValueError("임시 파일이 입력과 같습니다")
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w") as zout:
            for info in zin.infolist():
                _check_entry(info)
                data = zin.read(info)                              # 이름이 아니라 항목으로 — 같은 이름이 둘인 ZIP 에서도 각자 바이트
                if info.filename == SECTION_ENTRY:
                    data = section_xml
                elif info.filename in bindata:
                    data = bindata[info.filename]
                new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                zout.writestr(new_info, data)
        written = sha256(tmp.read_bytes())
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink()
    return backup, written


# ---------------------------------------------------------------- 감사·대조
def numbers_in(text: str) -> list[str]:
    return NUMBER_TOKEN.findall(text)


ALLOWED_TOKENS = {"0", "1", "2", "3", "4", "100.0%", "60%"}            # 등급·분야 번호, 합계 비율, 60% 기준 (키워드 수는 value_index 의 keywords(count), 사고 연도는 cases.gist 에서 온다)
STRIP_BEFORE_AUDIT = re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}-\d{2}(?![\d-])|(?:표|그림)\s*\d+(?:-\d+)?\.?|(?<!\d)\d\)\s|\(\d\)|^\d\.\s|등급\s*1~3|(?<![A-Za-z0-9])v(?:1fix|[12])(?![A-Za-z0-9])|3-gram|±1쪽")   # 날짜(연-월 포함)·표/그림 번호(표 12-1)·한 자리 목차 번호(" 4) "·"(1)"·셀 첫머리 "1. ")·사전 판(한글이 붙어도 — \b 는 한글을 단어로 본다)·3-gram·±1쪽 은 수치가 아니다. 두 자리 이상 "(813)" 은 벗기지 않는다 (Claude 적대적 리뷰 1)


def audited_numbers(text: str) -> list[str]:
    """감사·대조 JSON 이 세는 숫자 토큰 — 스트립 뒤의 numbers_in (한 정의)."""
    return numbers_in(STRIP_BEFORE_AUDIT.sub(" ", text))


STALE_PATTERNS = ("85종", "12,875", "813건", "7,769페이지", "4,259건", "9건의 사례", "8,914쪽", "페이지·구역")   # 폐기된 실행·구고의 숫자+단위·문구 — 값만 보는 감사가 우연히 놓치는 것(85 = 코딩 표본 control 층)을 문맥으로 막는다 (Codex 적대적 리뷰)


def audit_numbers(texts: list[str], facts: Facts) -> list[str]:
    """정본 값(총계·등급·분야·키워드·쪽수·비율·쪽 번호)이 아닌 숫자 토큰 — 남아 있으면 구 수치다. 폐기 문구(STALE_PATTERNS)는 값이 허용 집합에 있어도 잡는다."""
    allowed = facts.all_numbers() | ALLOWED_TOKENS
    unmatched = []
    for text in texts:
        for token in audited_numbers(text):
            if token not in allowed and token.rstrip("%") not in allowed:
                unmatched.append(token)
        for pattern in STALE_PATTERNS:
            if pattern in text:
                unmatched.append(pattern)
    return sorted(set(unmatched))


def section_texts(section: Section) -> list[str]:
    """감사 대상 글 — 절의 모든 문단과 그 안에 중첩된 문단(표 셀, 필드·메모 subList) 전부. 다시 쓰는 범위보다 넓게 본다."""
    return [direct_text(q) for p in section.paragraphs for q in p.iter(HP + "p")]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _under_tracked_docs(path: Path) -> bool:
    """docs/ 자체 또는 그 아래 — `--text-review-dir docs` 처럼 디렉터리 자체를 주는 경우도 막는다 (Codex 적대적 리뷰)."""
    rp, docs = os.path.realpath(str(path)), os.path.realpath(str(HERE / "docs"))
    return rp == docs or rp.startswith(docs + os.sep)


def public(path: Path) -> str:
    """저장소 상대 경로 (메시지·도움말용 — 절대 경로를 찍지 않는다)."""
    try:
        return str(Path(path).resolve().relative_to(HERE))
    except ValueError:
        return Path(path).name


# ---------------------------------------------------------------- 실행
DEFAULT_TEXT_REVIEW_DIR = HERE / "data" / "hwpx-results-refresh"

# ---------------------------------------------------------------- 2단계 — 제2장 5절 · 표 4 · 목차 · 제3장 2절 4)  (hwpx-methods-bridge-refresh, 설계 §3.4·§3.6)
CH2_S1_HEADING = "1. 국내 반도체고등학교 교과서와 한국산업인력공단 NCS 교과서 분석"
CH2_S2_HEADING = "2. 해외 기술 고등학교 교과서 비교·분석"
METHODS_HEADING = "5. 키워드 기반 문서 분류·분석 방법론"
METHODS_INTRO = "반도체 교과서와 NCS 자료에"                       # 5절 도입 문단(유지) — 그 다음 빈 문단이 삽입 문단 사이의 간격 원형
METHODS_REMOVE_LOCATORS = ("분석 자료는 반도체고등학교 교과서와", "먼저 파일을 읽어", "파일과 검색어는", "검색 결과는 단순히")   # 삭제할 설명 문단 4개(첫머리) — 1)·2) 본문에 흡수
METHODS_REMOVE_FIRST, METHODS_REMOVE_LAST = METHODS_REMOVE_LOCATORS[0], METHODS_REMOVE_LOCATORS[-1]   # 삭제 범위(포함)
METHODS_PROTO_BODY = "먼저 파일을 읽어"                           # 5절 본문 서식 원형(삭제 전에 복제)
TOC_METHODS_PREFIX, TOC_METHODS_END = "5. 키워드 기반", "제3장"
TOC_NCS_PREFIX, TOC_NCS_END = "2. NCS", "3. NCS"
CONCLUSION_LAST = "본 연구 결과는 반도체산업 특성을 반영한"      # 2절 소결 마지막 문단(ctrl run 있음 — 손대지 않고 뒤에 새 문단)
TOC_ENTRY_RE = re.compile(r"^\s*\d\)\s")
OLD_METHODS_TOC_ENTRIES = 8                                     # 원본 목차 5절의 구고 소제목 수(" 1) 시스템 구성과 데이터 흐름" ~ " 8) 검증과 한계") — 다르면 다른 문서다


class _Ledger:
    """2단계 편집 장부 — 손댄·삽입·삭제 문단, 대조용 숫자·문장. 삭제한 원소는 장부가 붙들어 둔다(id 재사용으로 장부가 헷갈리지 않게 — 레드팀)."""

    def __init__(self, root: ET.Element, facts: Facts, touched: set, inserted: set, removed: set, text_pairs: list):
        self.root, self.facts, self.touched, self.inserted, self.removed, self.text_pairs = root, facts, touched, inserted, removed, text_pairs
        self.owners = owner_map(root)
        self.kept: list[ET.Element] = []                            # 삭제·삽입한 원소의 참조 — check_untouched 가 끝날 때까지 살아 있어야 id 가 유일하다
        self.last_inserted: list[ET.Element] = []                   # 마지막 insert 가 넣은 원소들

    def rewrite(self, p: ET.Element, text: str, section: str) -> dict:
        old = direct_text(p)
        info = set_text(p, text)
        self.touched.add(id(p))
        self.text_pairs.append((section, old, text))
        new_numbers = audited_numbers(text)
        return {"old_numbers": audited_numbers(old), "new_numbers": new_numbers, "keys": self.facts.keys_for(new_numbers), **info}

    def touch_object(self, el: ET.Element) -> None:
        owner = self.owners.get(id(el))
        if owner is None:
            raise ValueError("장부에 없는 원소를 손댔습니다 — 최상위 문단에 속하지 않거나 삽입 뒤 등록되지 않은 표·그림")
        self.touched.add(id(owner))

    def insert(self, ref: ET.Element, pieces: list, protos: dict, section: str) -> list[dict]:
        """Piece 목록을 ref 뒤에 순서대로 삽입 — 원형은 kind 별(H·P·B·C·N·T)."""
        elements, records = [], []
        next_id, next_z = next_object_ids(self.root)                   # 이 호출 안의 표들은 여기서 이어 번호를 매긴다 (삽입 전이라 트리에 없으므로)
        for pc in pieces:
            if pc.kind == "T":
                ids = (next_id, next_z); next_id += 1; next_z += 1
                el = clone_table_paragraph(protos["T"], [list(r) for r in pc.rows], 1, list(pc.header), ids)
                elements.append(el)
                records.append({"kind": "T", "rows": len(table_rows(el.find(f".//{HP}tbl"))), "cols": len(pc.header), "table_id": ids[0]})
                continue
            el = clone_paragraph(protos[pc.kind], pc.text)
            elements.append(el)
            numbers = audited_numbers(pc.text)
            records.append({"kind": pc.kind, "numbers": numbers, "keys": self.facts.keys_for(numbers), "conditions": dict(pc.conditions)})
            if pc.kind != "B":
                self.text_pairs.append((section, "", pc.text))
        insert_after(self.root, ref, elements)
        self.inserted.update(id(el) for el in elements)
        self.kept.extend(elements)
        self.last_inserted = elements                                  # 3단계가 2단계 블록 끝 원소를 장부에서 받는다 (파일 재탐지 금지)
        for el in elements:                                            # 삽입한 문단(과 그 안의 표)도 장부의 소유자 지도에 넣는다
            for sub in el.iter():
                self.owners[id(sub)] = el
        return records

    def remove(self, elements: list[ET.Element], section: str) -> None:
        for el in elements:
            if not _is_blank(el):
                self.text_pairs.append((section, direct_text(el), ""))
        remove_paragraphs(self.root, elements)
        self.removed.update(id(el) for el in elements)
        self.kept.extend(elements)


def refresh_methods_bridge(root: ET.Element, facts: Facts, touched: set, inserted: set, removed: set, text_pairs: list) -> dict:
    """2단계. 반환: {"methods": …, "bridge": …, "tables": [대조 JSON 표 항목], "review_tables": [(절, 캡션, 행, first, 헤더)], "audit_texts": [추가 감사 글]}"""
    if not facts.ncs_real_pages or facts.methods is None or facts.bridge is None or facts.concentration is None:
        raise ValueError("2·3단계(제2장 5절·제3장 2절 4)·5))는 실제 PDF 쪽 기준 정본(meta.page_basis.NCS = real)과 2·3단계 사실이 있어야 만듭니다")
    L = _Ledger(root, facts, touched, inserted, removed, text_pairs)
    out = {"methods": {}, "bridge": {}, "concentration": {}, "tables": [], "review_tables": [], "audit_texts": []}

    # --- 표 4 (제2장 1절)
    ch1 = locate_range(root, CH2_S1_HEADING, CH2_S2_HEADING, 1)
    cap4 = find_paragraph(ch1, "표 4.")
    caption_changed = direct_text(cap4) != MB.table4_caption(facts)
    L.rewrite(cap4, MB.table4_caption(facts), "methods")
    tbl4 = find_table_after_caption(ch1, "표 4.")
    changed4 = 0
    group_cells = [tc for row in table_rows(tbl4) for tc in row if any(direct_text(q).strip().startswith(MB.NCS_GROUP_ORDER[0]) for q in cell_paragraphs(tc))]
    if len(group_cells) != 1:
        raise ValueError(f"표 4 에서 '{MB.NCS_GROUP_ORDER[0]}' 로 시작하는 문단을 가진 셀이 {len(group_cells)}개입니다 (1개여야 함)")
    for prefix, text in MB.table4_group_lines(facts):
        before = [direct_text(q) for q in cell_paragraphs(group_cells[0]) if direct_text(q).strip().startswith(prefix)]
        set_cell_paragraph(group_cells[0], prefix, text)
        if before != [text]:
            changed4 += 1
    L.touch_object(tbl4)
    out["methods"]["table4"] = {"caption_changed": caption_changed, "changed_cells": changed4}
    out["tables"].append({"section": "methods", "caption": "표 4.", "rows": len(table_rows(tbl4)), "cols": len(table_rows(tbl4)[0]), "changed_cells": changed4 + int(caption_changed)})
    out["review_tables"].append(("methods", "표 4.", [[g, t] for g, t in MB.table4_group_lines(facts)], 1, ["분야", "권수"]))
    out["audit_texts"] += section_texts(locate_range(root, CH2_S1_HEADING, CH2_S2_HEADING, 1))     # 1절 전체(표 4 를 소개하는 문장의 "86종" 까지) — 5절과 같은 범위 규칙 (레드팀)

    # --- 목차 5절: 구고 소제목 8 → 6
    block = locate_toc_block(root, TOC_METHODS_PREFIX, TOC_METHODS_END)
    entries = [p for p in block[1:] if TOC_ENTRY_RE.match(direct_text(p))]
    new_entries = list(MB.METHODS_HEADINGS)                            # 목차 항목 = 본문 소제목 (한 상수)
    if len(entries) != OLD_METHODS_TOC_ENTRIES:
        raise ValueError(f"목차 5절 소제목이 {len(entries)}개입니다 — 원본(2026-09-11)은 {OLD_METHODS_TOC_ENTRIES}개: 문서가 바뀌었거나 이미 2·3단계 산출물입니다")
    for p, text in zip(entries, new_entries):
        L.rewrite(p, text, "toc")
    L.remove(entries[len(new_entries):], "toc")
    out["methods"]["toc"] = {"rewritten": len(new_entries), "removed": len(entries) - len(new_entries)}
    out["audit_texts"] += new_entries

    # --- 목차 2절: ' 4) 소결' → 새 소절 + ' 5) 소결'
    block2 = locate_toc_block(root, TOC_NCS_PREFIX, TOC_NCS_END)
    concl_toc = [p for p in block2 if direct_text(p).strip() == MB.CONCLUSION_HEADING_OLD.strip()]
    if len(concl_toc) != 1:
        raise ValueError(f"목차 2절 블록에 '{MB.CONCLUSION_HEADING_OLD.strip()}' 이 {len(concl_toc)}개입니다 (1개여야 함)")
    L.rewrite(concl_toc[0], MB.BRIDGE_HEADING, "toc")
    L.insert(concl_toc[0], [MB.Piece("H", MB.CONCENTRATION_HEADING), MB.Piece("H", MB.CONCLUSION_HEADING_NEW)], {"H": concl_toc[0]}, "toc")
    out["bridge"]["toc"] = {"rewritten": 1, "inserted": 2}
    out["audit_texts"] += [MB.BRIDGE_HEADING, MB.CONCENTRATION_HEADING, MB.CONCLUSION_HEADING_NEW]

    # --- 5절 본문
    sec5 = locate_range(root, METHODS_HEADING, CHAPTER_HEADING, 1)
    ncs_body = locate_sections(root)["ncs"]
    protos = {"H": next(p for p in ncs_body.paragraphs if TOC_ENTRY_RE.match(direct_text(p))),
              "P": find_paragraph(sec5, METHODS_PROTO_BODY),
              "B": _paragraph_after(root, find_paragraph(sec5, METHODS_INTRO))}
    if protos["B"] is None or not _is_blank(protos["B"]):
        raise ValueError("5절 도입 문단 다음이 빈 문단이 아닙니다 — 간격 원형을 찾지 못했습니다")
    protos["P"] = copy.deepcopy(protos["P"])                       # 삭제되기 전에 복제해 둔다
    tables_m = []
    for caption, caption_text, rows, header in (("표 5.", MB.table5_caption(facts), MB.methods_table5_rows(facts), ["단계", "무엇을 하는가", "주요 결과"]),
                                                ("표 6.", MB.TABLE6_CAPTION, MB.methods_table6_rows(facts), ["구분", "쉽게 말하면", "예시·기준"])):
        cap = find_paragraph(sec5, caption)
        L.rewrite(cap, caption_text, "methods")
        tbl = find_table_after_caption(sec5, caption)
        resize_table(tbl, 1, len(rows))
        changed = fill_table(tbl, rows, 1, header)
        L.touch_object(tbl)
        tables_m.append({"section": "methods", "caption": caption, "rows": len(table_rows(tbl)), "cols": len(header), "changed_cells": changed})
        out["review_tables"].append(("methods", caption, rows, 1, header))
    out["methods"]["tables"] = tables_m
    out["tables"] += tables_m
    first, last = find_paragraph(sec5, METHODS_REMOVE_FIRST), find_paragraph(sec5, METHODS_REMOVE_LAST)
    tops = top_paragraphs(root)
    i0, i1 = tops.index(first), tops.index(last)
    if i1 < i0 or i0 == 0 or tops[i0 - 1] not in sec5.paragraphs:
        raise ValueError("5절 삭제 범위의 끝이 시작보다 앞에 있거나, 범위 앞 문단이 5절 밖입니다")
    ref = tops[i0 - 1]
    to_remove = tops[i0:i1 + 1]
    for p in to_remove:                                                          # 지우는 것은 설명 문단 4개와 그 사이 빈 문단뿐 — 표·그림·소제목·다른 글이 끼어 있으면 문서가 바뀐 것 (Claude 적대적 리뷰 2)
        text = direct_text(p).strip()
        if not (_is_blank(p) or any(text.startswith(loc) for loc in METHODS_REMOVE_LOCATORS)):
            raise ValueError(f"5절 삭제 범위에 예상 밖 문단이 있습니다: {text[:20]!r} — 원본(2026-09-11)이 아닙니다")
    pieces = MB.methods_paragraphs(facts)
    split = next(i for i, pc in enumerate(pieces) if pc.kind == "L")
    L.remove(to_remove, "methods")
    out["methods"]["removed_paragraphs"] = len(to_remove)
    inserted_records = L.insert(ref, pieces[:split], protos, "methods")
    rewritten = []
    r_last = None
    for locator, text in MB.methods_rewrites(facts):
        p = find_paragraph(sec5, locator)
        rewritten.append({"locator": locator, **L.rewrite(p, text, "methods")})
        r_last = p
    inserted_records += L.insert(r_last, pieces[split + 1:], protos, "methods")
    out["methods"]["inserted"] = inserted_records
    out["methods"]["rewritten"] = rewritten

    # --- 제3장 2절 4)
    sections = locate_sections(root)
    ncs = sections["ncs"]
    concl = find_paragraph(ncs, MB.CONCLUSION_HEADING_OLD.strip())
    fig4 = find_paragraph(ncs, "그림 4.")
    ref = fig4
    nxt = _paragraph_after(root, fig4)
    blank_proto = nxt if nxt is not None and _is_blank(nxt) else None
    if blank_proto is not None:
        ref = blank_proto
    else:
        blank_proto = next((p for p in ncs.paragraphs if _is_blank(p)), None)
        if blank_proto is None:
            raise ValueError("2절에 빈 문단이 없어 간격 원형을 찾지 못했습니다")
    body_proto = None
    headings = {h for pair in HEADINGS.values() for h in pair}
    for p in ncs.paragraphs[ncs.paragraphs.index(concl) + 1:]:            # 2절 안에서만 — 다음 절 제목이 원형이 되면 안 된다 (레드팀)
        runs = p.findall(HP + "run")
        text = direct_text(p).strip()
        if text and text not in headings and not TOC_ENTRY_RE.match(direct_text(p)) and runs and all(all(c.tag == HP + "t" for c in r) for r in runs) and not has_object(p, "tbl"):
            body_proto = p
            break
    if body_proto is None:
        raise ValueError("2절 소결에서 글 run 만 있는 본문 원형을 찾지 못했습니다")
    tbl12 = find_table_after_caption(ncs, "표 12.")
    protos2 = {"H": concl, "P": body_proto, "B": blank_proto, "C": find_paragraph(ncs, "표 12."), "N": find_paragraph(ncs, "주: 단위: 건."), "T": L.owners[id(tbl12)]}
    bridge_pieces = MB.bridge_paragraphs(facts)
    records = L.insert(ref, bridge_pieces, protos2, "bridge")
    out["bridge"]["inserted"] = records
    out["bridge"]["tables"] = [{"section": "bridge", "caption": cap, "rows": r["rows"], "cols": r["cols"], "table_id": r["table_id"]}
                               for cap, r in zip((MB.TABLE12_1_LABEL, MB.TABLE12_2_LABEL), (r for r in records if r["kind"] == "T"))]
    out["tables"] += [{**t, "changed_cells": t["rows"] * t["cols"]} for t in out["bridge"]["tables"]]
    out["review_tables"] += [("bridge", MB.TABLE12_1_LABEL, MB.bridge_table1_rows(facts), 1, MB.bridge_table1_header(facts)),
                             ("bridge", MB.TABLE12_2_LABEL, MB.bridge_table2_rows(facts), 1, MB.bridge_table2_header(facts))]
    # --- 3단계: 제3장 2절 5) 교재별 집중과 편차 (ncs-book-concentration)
    ref3 = L.last_inserted[-1]                                                     # 2단계 블록의 끝 빈 문단 — 장부에서 받는다
    conc_pieces = MB.concentration_paragraphs(facts)
    records3 = L.insert(ref3, conc_pieces, protos2, "concentration")
    out["concentration"] = {"inserted": records3,
                            "tables": [{"section": "concentration", "caption": cap, "rows": r["rows"], "cols": r["cols"], "table_id": r["table_id"]}
                                       for cap, r in zip((MB.TABLE12_3_LABEL, MB.TABLE12_4_LABEL), (r for r in records3 if r["kind"] == "T"))],
                            "dedicated": [b.code for b in facts.concentration.dedicated],
                            "conditions": {k: v for r in records3 if r["kind"] == "P" for k, v in r["conditions"].items()}}
    out["tables"] += [{**t, "changed_cells": t["rows"] * t["cols"]} for t in out["concentration"]["tables"]]
    out["review_tables"] += [("concentration", MB.TABLE12_3_LABEL, MB.concentration_table1_rows(facts), 1, MB.concentration_table1_header(facts)),
                             ("concentration", MB.TABLE12_4_LABEL, MB.concentration_table2_rows(facts), 1, MB.concentration_table2_header(facts))]

    L.rewrite(concl, MB.CONCLUSION_HEADING_NEW, "bridge")
    out["bridge"]["renumbered"] = {MB.CONCLUSION_HEADING_OLD.strip(): MB.CONCLUSION_HEADING_NEW.strip()}
    last_concl = find_paragraph(ncs, CONCLUSION_LAST)
    sentence, cond = MB.conclusion_sentence(facts)
    concl_records = L.insert(last_concl, [MB.Piece("B"), MB.Piece("P", sentence, conditions=cond)], {"P": body_proto, "B": blank_proto}, "bridge")   # 소결 문단 사이의 간격 규칙대로 빈 문단 하나를 두고
    out["bridge"]["conclusion_inserted"] = True
    out["bridge"]["conclusion"] = next(r for r in concl_records if r["kind"] == "P")           # 숫자·출처 키·조건 (갭 분석 G4)
    out["bridge"]["conditions"] = {**{k: v for r in records if r["kind"] == "P" for k, v in r["conditions"].items()}, **cond}
    out["kept"] = L.kept                                                          # 삭제·삽입 원소의 참조 — refresh() 가 check_untouched 뒤까지 붙든다 (id 재사용 방지)
    return out


def refresh(hwpx: Path, facts: Facts, out: Path, diff_out: Path | None, review_dir: Path | None, force: bool = False, render: bool = True,
            text_review_dir: Path | None = None, write_output: bool = True, strip_layout_cache: bool = True) -> dict:
    """render=False 는 그림을 그리지 않는다(magick 없는 환경 — 원본 그림 바이트 유지); write_output=False 는 HWPX 를 쓰지 않는다(점검 실행);
    strip_layout_cache=False 는 손댄 문단의 줄 배치 캐시를 남긴다(--keep-line-layout-cache — 캐시 없는 문단을 다시 배치하지 못하는 뷰어가 있을 때의 안전판)."""
    raw, root, root_tag = read_section(hwpx)
    already = {direct_text(p).strip() for p in top_paragraphs(root)} & {MB.METHODS_HEADINGS[0].strip(), MB.BRIDGE_HEADING.strip(), MB.CONCENTRATION_HEADING.strip()}
    if already:
        raise ValueError(f"{hwpx.name} 은 이미 2·3단계 산출물입니다({', '.join(sorted(already))}) — 정본은 입력이 아니며, 언제나 원본(2026-09-11)에서 다시 만듭니다")
    snapshot = snapshot_paragraphs(root)
    owners = owner_map(root)
    touched: set[int] = set(); inserted: set[int] = set(); removed: set[int] = set()       # 손댄 원소 장부 — 1·2단계 공용 (check_untouched)
    sections = locate_sections(root)
    diff: dict = {"source": {"hwpx": hwpx.name, "hwpx_sha256": sha256(hwpx.read_bytes()), "summary_run": {k: facts.run.get(k) for k in ("generated_at", "git_commit", "dictionary", "expected")},
                             "page_basis": dict(facts.page_basis), "cases_date": facts.cases_date},
                  "output": out.name, "paragraphs": [], "tables": [], "figures": [], "audit": {},
                  "runtime": {"backup": None, "previous_hwpx_sha256": None, "previous_output_identical": None}}   # runtime(백업 이름·이전 sha·동일 여부)은 실행 환경 — 화면에만 찍고 추적 JSON 에는 쓰지 않는다 (레드팀·Claude 적대적 리뷰 11)
    text_pairs: list[tuple[str, str, str]] = []

    # 문단
    for name, template in PARAGRAPH_TEMPLATES.items():
        section = sections[name]
        entries = template(facts)
        prefixes = tuple(prefix for prefix, _, _ in entries)
        for prefix, new_text, conditions in entries:
            p = find_paragraph(section, prefix, prefixes)
            old = direct_text(p)
            info = set_text(p, new_text)
            touched.add(id(p))
            new_numbers = audited_numbers(new_text)
            diff["paragraphs"].append({"section": name, "locator": prefix, "old_numbers": audited_numbers(old), "new_numbers": new_numbers,
                                       "keys": facts.keys_for(new_numbers), "conditions": conditions, **info})
            text_pairs.append((name, old, new_text))

    # 표
    review_specs: list = []                                              # 검토 HTML 용 (헤더 행 포함)
    table_specs = [
        ("textbook", "표 7.", keyword_table_rows(facts.school), 1, None),
        ("textbook", "표 8.", area_table_rows(facts.school, with_grade_sum=False), 1, None),
        ("textbook", "표 9.", grade_table_rows(facts.school), 1, None),
        ("ncs", "표 10.", keyword_table_rows(facts.ncs), 1, None),
        ("ncs", "표 11.", area_table_rows(facts.ncs, with_grade_sum=True), 1, None),
        ("ncs", "표 12.", grade_table_rows(facts.ncs), 1, None),
    ]
    for name, caption, rows, first, header in table_specs:
        tbl = find_table_after_caption(sections[name], caption)
        changed = fill_table(tbl, rows, first, header)
        touched.add(id(owners[id(tbl)]))
        diff["tables"].append({"section": name, "caption": caption, "rows": len(table_rows(tbl)), "cols": len(table_rows(tbl)[first]), "changed_cells": changed})
        review_specs.append((name, caption, rows, first, header or [cell_text(tc) for tc in table_rows(tbl)[first - 1]]))   # 검토 HTML 은 문서의 헤더 행을 함께 보인다 (디자인 리뷰)
    tbl13 = find_table_by_first_cell(sections["cases"], "표 13.")
    rows13 = case_table_rows(facts.cases)
    resize_table(tbl13, 2, len(rows13))
    changed = fill_table(tbl13, rows13, 2, ["교과서 이름", "교과서 분야", "사고/부상 등 주요 내용", "페이지", "판정"])
    touched.add(id(owners[id(tbl13)]))
    review_specs.append(("cases", "표 13.", rows13, 2, ["교과서 이름", "교과서 분야", "사고/부상 등 주요 내용", "페이지", "판정"]))
    diff["tables"].append({"section": "cases", "caption": "표 13.", "rows": len(table_rows(tbl13)), "cols": len(table_rows(tbl13)[2]), "changed_cells": changed})

    # 그림
    bindata: dict[str, bytes] = {}
    review_images: list[tuple[str, bytes, str]] = []
    with zipfile.ZipFile(hwpx) as z:
        names = z.namelist()
        for spec in figure_specs(facts):
            pic = find_picture(sections[spec["section"]], spec["caption"], spec["item"])
            touched.add(id(owners[id(pic)]))                       # BinData 만 바뀌지만 그림 문단을 손댄 것으로 적는다(장부의 보수적 해석)
            item = pic.find(f".//{HC}img").get("binaryItemIDRef")
            entry = next((n for n in names if n.startswith("BinData/") and Path(n).stem == item), None)
            if entry is None:
                raise ValueError(f"BinData/{item}.* 항목이 HWPX 에 없습니다 (binaryItemIDRef={item})")
            info = z.getinfo(entry)
            _check_entry(info)                                         # 그림 항목도 section0.xml 처럼 압축 해제 전에 크기·비율 상한 (CodeRabbit PR #18)
            width, height, kind = image_dimensions(z.read(info))
            svg = spec["svg"](width, height)
            record = {"label": spec["label"], "caption": spec["caption"], "item": item, "entry": entry, "format": kind, "width": width, "height": height, "svg_sha256": sha256(svg.encode("utf-8")), "rendered": render}
            if render:
                data = render_svg(svg, kind, width, height)
                bindata[entry] = data
                record["sha256"] = sha256(data)
                record["bits"] = image_bits(data)
                review_images.append((spec["label"], data, kind, spec.get("alt") or spec["label"]))
            diff["figures"].append(record)

    # 2단계 — 제2장 5절 · 표 4 · 목차 · 제3장 2절 4)  (hwpx-methods-bridge-refresh)
    stage2 = refresh_methods_bridge(root, facts, touched, inserted, removed, text_pairs)
    kept_alive = stage2["kept"]                                          # noqa: F841 — 장부의 원소 참조를 검사가 끝날 때까지 붙든다
    diff["methods"], diff["bridge"], diff["concentration"] = stage2["methods"], stage2["bridge"], stage2["concentration"]
    diff["tables"] += stage2["tables"]
    review_specs = review_specs + stage2["review_tables"]                # 1단계 표 7~13 뒤에 2단계 표 4·5·6·12-1·12-2 (디자인 리뷰: 번호 순 읽기)

    # 감사 — 다시 쓴 제3장 1~3절(재탐지: 2절에 문단이 늘었다) + 제2장 5절 + 표 4·목차의 숫자 토큰 전부가 정본 값이어야 한다
    sections = locate_sections(root)
    methods_section = locate_range(root, METHODS_HEADING, CHAPTER_HEADING, 1)
    texts = [t for name in sections for t in section_texts(sections[name])] + section_texts(methods_section) + stage2["audit_texts"]
    unmatched = audit_numbers(texts, facts)
    diff["methods"]["audited_tokens"] = sum(len(audited_numbers(t)) for t in section_texts(methods_section))
    diff["audit"] = {"tokens": sum(len(numbers_in(t)) for t in texts), "unmatched": unmatched}

    # 손댄 문단의 줄 배치 캐시 제거 — 뷰어가 새 글 길이로 다시 배치하게 (Polaris 는 캐시를 믿는다). 불변 검사 앞에서 하므로 검사가 이 변경까지 덮는다
    if strip_layout_cache:
        diff["layout"] = drop_line_layout_cache(root, touched, inserted)
    else:
        diff["layout"] = {"paragraphs": 0, "linesegarray_removed": 0, "kept": True}          # --keep-line-layout-cache: 캐시를 하나도 지우지 않는다(set_text 도 건드리지 않는다)
    # 손댄 범위 밖 불변 검사 (1·2단계 장부)
    check_untouched(root, snapshot, touched, inserted, removed)
    del kept_alive

    if unmatched:
        diff["audit"]["status"] = "failed"
        diff["output"] = None
    elif write_output:
        diff["audit"]["status"] = "ok"
        previous = sha256(out.read_bytes()) if out.exists() else None
        backup, written = write_hwpx(hwpx, out, serialize_section(root, root_tag), bindata, force=force)
        diff["output_sha256"] = written
        diff["runtime"] = {"backup": backup.name if backup else None, "previous_hwpx_sha256": previous, "previous_output_identical": (previous == diff["output_sha256"]) if previous else None}
    else:
        diff["audit"]["status"] = "ok"                        # 점검 실행 — HWPX 는 쓰지 않는다
        diff["output"] = None
    if diff_out:
        if unmatched and _under_tracked_docs(diff_out):     # 실패 기록이 추적 정본 대조를 덮어쓰지 않게
            diff_out = Path(tempfile.mkdtemp(prefix="hwpx_refresh_failed_")) / diff_out.name
            print(f"숫자 감사 실패 — 대조 JSON 은 {diff_out} 에 씁니다 (추적 파일은 그대로)")
        diff_out.parent.mkdir(parents=True, exist_ok=True)
        diff_out.write_text(json.dumps({k: v for k, v in diff.items() if k != "runtime"}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")   # runtime(백업 이름·sha)은 실행 환경 — 추적 파일에 넣지 않는다
    if review_dir and not unmatched:
        write_review(review_dir, facts, review_specs, review_images)
    if text_review_dir and not unmatched:
        write_text_review(text_review_dir, text_pairs)
    return diff


def write_text_review(text_review_dir: Path, pairs: list[tuple[str, str, str]]) -> None:
    """구/신 문장 병기본 — 보고서 본문을 담으므로 data/ 아래(비추적)에만 쓴다."""
    import html
    text_review_dir.mkdir(parents=True, exist_ok=True)
    parts = ["<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>HWPX 문단 구/신 대조 (비추적)</title>",
             "<style>body{font-family:-apple-system,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.5}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.4rem .6rem;vertical-align:top;width:50%}th{background:#f3f4f6}h2{margin-top:2rem}</style></head><body>",
             "<h1>HWPX 문단 구/신 대조 — 제3장 1~3절(1단계) · 제2장 5절·목차·제3장 2절 4)(2단계) · 제3장 2절 5)(3단계)</h1><p>보고서 본문을 담으므로 이 파일은 <code>data/</code> 아래(비추적)에만 둔다.</p>"]
    current = None
    order = ("textbook", "ncs", "cases", "methods", "toc", "bridge", "concentration")
    pairs = sorted(pairs, key=lambda pair: order.index(pair[0]) if pair[0] in order else len(order))      # 절 단위로 모아 보인다 (안정 정렬 — 절 안 순서는 편집 순서)
    for name, old, new in pairs:
        if name != current:
            if current is not None:
                parts.append("</table>")
            parts.append(f"<h2>{html.escape(name)}</h2><table><tr><th>구 문장</th><th>새 문장</th></tr>")
            current = name
        parts.append(f"<tr><td>{html.escape(old)}</td><td>{html.escape(new)}</td></tr>")
    parts.append("</table></body></html>")
    (text_review_dir / "review_text.html").write_text("".join(parts), encoding="utf-8")


SECTION_LABEL = {"textbook": "교과서", "ncs": "NCS", "cases": "사고사례", "methods": "연구 방법", "bridge": "집계 기준 연결", "concentration": "교재별 집중", "toc": "목차"}   # 검토 HTML 의 절 이름


def write_review(review_dir: Path, facts: Facts, table_specs, images) -> None:
    import base64, html
    review_dir.mkdir(parents=True, exist_ok=True)
    numeric = re.compile(r"[\d,.%]+")
    parts = ["<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>HWPX 표·그림 검토본</title>",
             "<style>body{font-family:-apple-system,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem}.scroll-x{overflow-x:auto}table{border-collapse:collapse;margin:1rem 0}td,th{border:1px solid #ccc;padding:.25rem .6rem;font-size:.875rem}th{background:#f3f4f6}td.n{text-align:right;font-variant-numeric:tabular-nums}img{max-width:100%;border:1px solid #ddd;margin:.5rem 0}</style></head><body>",
             f"<h1>HWPX 표·그림 검토본 — 제3장 표 7~13·그림 2~4(1단계), 표 4·5·6·12-1·12-2(2단계), 표 12-3·12-4(3단계)</h1><p>정본 {html.escape(str(facts.run.get('generated_at')))} · git {html.escape(str(facts.run.get('git_commit')))} · 사전 {html.escape(str(facts.run.get('dictionary')))}. 본문 문장은 담지 않는다(표·그림만).</p>"]
    for name, caption, rows, first, header in table_specs:
        parts.append(f"<h2>{html.escape(caption)} ({html.escape(SECTION_LABEL.get(name, name))})</h2><div class=\"scroll-x\" tabindex=\"0\" role=\"region\" aria-label=\"{html.escape(caption)}\"><table>")
        if header:
            parts.append("<tr>" + "".join(f"<th scope=\"col\">{html.escape(c)}</th>" for c in header) + "</tr>")
        for row in rows:
            parts.append("<tr>" + "".join(f"<td class=\"n\">{html.escape(c)}</td>" if numeric.fullmatch(c) else f"<td>{html.escape(c)}</td>" for c in row) + "</tr>")
        parts.append("</table></div>")
    for caption, data, kind, alt in images:
        if kind == "BMP":
            data = subprocess.run(["magick", "BMP:-", "-strip", "PNG:-"], input=data, check=True, capture_output=True).stdout   # -strip: 날짜 청크 없이 — 같은 그림이면 review.html 도 같은 바이트
        parts.append(f"<h2>{html.escape(caption)}</h2><img alt=\"{html.escape(alt)}\" src=\"data:image/png;base64,{base64.b64encode(data).decode()}\">")
    parts.append("</body></html>")
    (review_dir / "review.html").write_text("".join(parts), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="기초보고서 HWPX 를 정본 수치로 다시 쓴다 — 1단계 제3장 1~3절, 2단계 제2장 5절·표 4·목차·제3장 2절 4), 3단계 제3장 2절 5) 교재별 집중(표 12-3·12-4)")
    ap.add_argument("--hwpx", type=Path, default=DEFAULT_HWPX)
    ap.add_argument("--out", type=Path, default=None, help="새 HWPX (기본 data/반도체 기초보고서_{정본 실행일}_정본.hwpx)")
    ap.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--recount-summary", type=Path, default=DEFAULT_RECOUNT)
    ap.add_argument("--diff-out", type=Path, default=None, help=f"변경 대조 JSON (기본 {public(DEFAULT_DIFF_DIR)}/hwpx_results_refresh_{{정본 실행일}}.json)")
    ap.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="그림을 그리지 않는 점검 실행 — 출력 HWPX·추적 대조 JSON 을 쓰지 않는다 (--diff-out 은 docs/ 밖 경로만)")
    ap.add_argument("--text-review-dir", type=Path, default=DEFAULT_TEXT_REVIEW_DIR, help="구/신 문장 병기본 (본문 포함 — data/ 아래, 비추적)")
    ap.add_argument("--keep-line-layout-cache", action="store_true", help="손댄 문단의 hp:linesegarray(옛 줄 배치 캐시)를 지우지 않는다 — 캐시 없는 문단을 다시 배치하지 못하는 뷰어용 안전판 (기본은 지운다: Polaris 는 옛 캐시대로 한 줄에 눌러 그렸다)")
    args = ap.parse_args(argv)
    facts = load_facts(args.summary, args.cases, args.recount_summary)
    if args.out is None:
        args.out = default_out_path(facts)
    if _under_tracked_docs(args.out):
        sys.exit(f"보고서 HWPX 는 본문 전체이므로 추적 경로(docs/)에 쓸 수 없습니다: {public(args.out)}")
    if _under_tracked_docs(args.text_review_dir):
        sys.exit(f"구/신 문장 병기본은 보고서 본문을 담으므로 추적 경로(docs/)에 쓸 수 없습니다: {public(args.text_review_dir)}")
    if args.no_render:
        if args.diff_out is None:
            diff_out = Path(tempfile.mkdtemp(prefix="hwpx_refresh_dry_")) / "hwpx_results_refresh_dry.json"
        elif _under_tracked_docs(args.diff_out):
            sys.exit(f"--no-render 점검 실행은 추적 경로에 대조 JSON 을 쓰지 않습니다: {public(args.diff_out)}")
        else:
            diff_out = args.diff_out
        diff = refresh(args.hwpx, facts, args.out, diff_out, None, force=True, render=False, write_output=False, strip_layout_cache=not args.keep_line_layout_cache)   # 점검 실행 — HWPX 를 쓰지 않는다
        print(f"(점검 실행 — 대조 JSON: {diff_out})")
    else:
        diff = refresh(args.hwpx, facts, args.out, args.diff_out or default_diff_path(facts), args.review_dir, force=args.force, text_review_dir=args.text_review_dir, strip_layout_cache=not args.keep_line_layout_cache)
    print(f"문단 {len(diff['paragraphs'])}개 · 표 {len(diff['tables'])}개 · 그림 {len(diff['figures'])}개 · 숫자 토큰 {diff['audit']['tokens']}개 · 미일치 {len(diff['audit']['unmatched'])}개")
    if diff["audit"]["unmatched"]:
        print("정본에 없는 숫자:", ", ".join(diff["audit"]["unmatched"]))
        return 1
    if not args.no_render:
        print(f"→ {public(args.out)}")
        runtime = diff.get("runtime") or {}
        if runtime.get("backup"):
            print(f"   기존 파일 보존: {runtime['backup']} (sha256 {runtime['previous_hwpx_sha256'][:8]}…, 새 출력과 {'같음' if runtime.get('previous_output_identical') else '다름'})")   # --force 로 덮어쓴 정본의 .bak (2단계 D1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
