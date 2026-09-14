#!/usr/bin/env python3
"""hwpx_results_refresh.py — 기초보고서(HWPX) 제3장 연구 결과 1~3절을 정본 수치로 다시 쓴다.

기능 hwpx-ncs-section-refresh (2026-09-14, 연구책임자 결정 D1~D5). 숫자는 전부 추적 파일에서 온다:
  docs/03-analysis/data/semantic_summary.json   — 총계·등급·분야(groups, pages)·키워드(×그룹)   (정본 실행, 사전 v2)
  docs/03-analysis/data/accident_case_pages.json — 사고사례 자동 판정 13쪽과 원문 확인 판정
  docs/03-analysis/data/summary.json             — 교과서 사고사례 쪽 수(0)만 (recount_grades)
스크립트 상수는 문장 틀과 교과서→분야 대응표뿐이다.

동작: 절은 제목 텍스트로 찾고(목차의 같은 제목은 건너뛴다), 문단은 원문 첫머리로 찾아 템플릿으로 다시 쓰며(서술 조건은 데이터로
분기), 표 7~12 는 셀 텍스트만 바꾸고(표 13 만 행 증감), 그림 2~4 는 SVG → 원본 형식·크기로 다시 그려 BinData 바이트를 바꾼다.
1~3절 밖의 노드와 나머지 ZIP 항목은 바이트 그대로. 원본은 읽기만 하고 새 파일로 쓴다.
산출물: 새 HWPX(data/, 비추적), 변경 대조 JSON(추적, 본문 문장 없음), 검토 HTML(표·그림만, 추적), 구/신 문장 병기본 review_text.html(본문 포함 — data/, 비추적).
숫자 감사: 다시 쓴 1~3절의 모든 숫자 토큰이 정본 값·비율·쪽 번호 중 하나여야 한다 — 아니면 exit 1.
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
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
HC = "{http://www.hancom.co.kr/hwpml/2011/core}"
SECTION_ENTRY = "Contents/section0.xml"
XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

DEFAULT_HWPX = HERE / "data" / "반도체 기초보고서_20260911.hwpx"
DEFAULT_OUT = HERE / "data" / "반도체 기초보고서_20260914_정본.hwpx"
DEFAULT_SUMMARY = HERE / "docs" / "03-analysis" / "data" / "semantic_summary.json"
DEFAULT_CASES = HERE / "docs" / "03-analysis" / "data" / "accident_case_pages.json"
DEFAULT_RECOUNT = HERE / "docs" / "03-analysis" / "data" / "summary.json"
DEFAULT_DIFF = HERE / "docs" / "03-analysis" / "data" / "hwpx_results_refresh_20260914.json"
DEFAULT_REVIEW_DIR = HERE / "docs" / "03-analysis" / "hwpx-results-refresh"
FONT = os.environ.get("HWPX_FONT", "/System/Library/Fonts/Supplemental/AppleGothic.ttf")   # 없으면 -font 없이 렌더 (다른 OS) — 결정론은 같은 폰트일 때만

CHAPTER_HEADING = "제3장 연구 결과"
HEADINGS = {                                   # 절 이름 → (시작 제목, 끝 제목) — 본문 제목 텍스트와 정확히 일치해야 한다
    "textbook": ("1. 반도체고등학교 전공교과서의 안전보건 키워드 분석 주요 결과", "2. NCS 반도체 자료의 안전보건 키워드 분석 주요 결과"),
    "ncs": ("2. NCS 반도체 자료의 안전보건 키워드 분석 주요 결과", "3. NCS 반도체 교과서의 사고, 부상, 질병 사례 분석"),
    "cases": ("3. NCS 반도체 교과서의 사고, 부상, 질병 사례 분석", "4. 학생 대상 화학물질·안전보건 교육의 필요성과 효과"),
}
AREA_ORDER = ("개발", "제조", "장비", "재료")
NCS_GROUP_TO_AREA = {"반도체개발": "개발", "반도체제조": "제조", "반도체장비": "장비", "반도체재료": "재료"}
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

    def value_index(self) -> dict[str, set[str]]:
        """정본 값(콤마·소수 1자리 % 문자열) → 그 값이 나오는 정본 키 경로들. 숫자 감사의 허용 집합이자 대조 JSON 의 출처(keys) 근거."""
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
        for value, key in ((c.flagged, "cases.pages(count)"), (c.books, "cases.books"), (c.top_book_pages, "cases.top_book_pages"), (c.narrative, "cases.narrative"),
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


def fmt(n: int) -> str:
    return f"{n:,}"


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "0.0%"


def load_facts(summary_path: Path = DEFAULT_SUMMARY, cases_path: Path = DEFAULT_CASES, recount_path: Path | None = DEFAULT_RECOUNT) -> Facts:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
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
            areas[area]["documents"] += g["documents"]
            areas[area]["pages"] += g.get("pages", 0)
            areas[area]["total"] += g["total"]
            for grade in (1, 2, 3):
                areas[area]["grades"][grade] += g["grades"][str(grade)]
        keywords = {}
        for k in summary["keywords"]:
            kc = k["corpora"][corpus]
            kw_areas = {a: {"total": 0, "grades": {1: 0, 2: 0, 3: 0}} for a in AREA_ORDER}
            for g in kc.get("groups", []):
                area = group_to_area(g["name"])
                kw_areas[area]["total"] += g["total"]
                for grade in (1, 2, 3):
                    kw_areas[area]["grades"][grade] += g["grades"][str(grade)]
            keywords[k["name"]] = {"total": kc["total"], "grades": {1: kc["grades"]["1"], 2: kc["grades"]["2"], 3: kc["grades"]["3"]}, "areas": kw_areas}
        return CorpusFacts(documents=c["documents"], total=c["total"], grades={1: c["grades"]["1"], 2: c["grades"]["2"], 3: c["grades"]["3"]},
                           areas=areas, keywords=keywords, order=order)

    ncs = corpus_facts("NCS", NCS_GROUP_TO_AREA.get)
    school = corpus_facts("교과서", TEXTBOOK_AREA.get)
    pages = cases["pages"]
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
    return Facts(ncs=ncs, school=school, cases=case_facts, run=summary.get("meta", {}).get("run", {}), cases_date=cases.get("date"))


# ---------------------------------------------------------------- XML 도우미
def direct_text(p: ET.Element) -> str:
    return "".join(t.text or "" for run in p.findall(HP + "run") for t in run.findall(HP + "t"))


def set_text(p: ET.Element, text: str) -> dict:
    """문단의 글을 통째로 바꾼다 — 첫 run 의 charPrIDRef 를 승계해 hp:t 하나로. 글만 있던 다른 run 은 지운다."""
    runs = p.findall(HP + "run")
    if not runs:
        raise ValueError("run 이 없는 문단에는 글을 쓸 수 없습니다")
    text_runs = [r for r in runs if any(c.tag == HP + "t" for c in r) and all(c.tag == HP + "t" for c in r)]
    first = text_runs[0] if text_runs else runs[0]
    collapsed = len(text_runs) > 1
    for t in list(first.findall(HP + "t")):
        first.remove(t)
    node = ET.SubElement(first, HP + "t")
    node.text = text
    for r in text_runs[1:]:
        p.remove(r)
    return {"format_collapsed": collapsed}


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


def resize_table(tbl: ET.Element, first_data_row: int, data_rows: int) -> None:
    """데이터 행(첫 데이터 행부터 끝까지)을 data_rows 개로 맞춘다 — 마지막 데이터 행을 복제하거나 뒤에서부터 지운다."""
    trs = tbl.findall(HP + "tr")
    current = len(trs) - first_data_row
    if current <= 0:
        raise ValueError("복제할 데이터 행이 없습니다")
    template = trs[-1]
    while current < data_rows:
        tbl.append(copy.deepcopy(template))
        current += 1
    while current > data_rows:
        tbl.remove(tbl.findall(HP + "tr")[-1])
        current -= 1
    renumber_table(tbl)


def top_paragraphs(root: ET.Element) -> list[ET.Element]:
    return root.findall(HP + "p")


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
        end = min(e for e in ends if e > starts[0])
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
    def zero_or_count(name, label):                       # "‘X’는 전혀 검출되지 않았고" / "‘X’는 N건에 그쳤고" — 0 주장은 데이터로만
        return f"{eun(q(label))} 전혀 검출되지 않았고" if k(name) == 0 else f"{eun(q(label))} {fmt(k(name))}건에 그쳤고"
    conditions = {
        "키워드 분석 결과": {"top_keyword": top6[0][0], "zero_keywords": zero},
        "반도체 제조 분야는": {"manufacturing_has_most_pages": largest_area == "제조"},
        "따라서 제조 분야는 안전보건교육이 가장 적극적으로": {"zero_keywords_in_sentence": [n for n in ("직업병", "물질안전보건자료") if k(n) == 0]},
        "따라서 장비 분야에서는 전기, 기계, 압력": {"textbook_accident_pages": f.cases.textbook_cases, "fall_is_zero": k("추락") == 0},
        "또한 공정안전관리, 직업병, 물질안전보건자료": {"zero_keywords": zero, "textbook_accident_pages": f.cases.textbook_cases},
    }
    return _with_conditions([
        ("본 연구에서는 반도체고등학교의 전공교과서를 대상으로",
         f"본 연구에서는 반도체고등학교의 전공교과서를 대상으로 안전보건교육 내용의 실태를 분석하였다. 분석 대상은 교과서 {s.documents}권, 총 {fmt(pages_total)}페이지이며, ‘사망, 부상, 화학물질, 폭발, 감전, 직업병’ 등 {len(s.order)}개의 안전보건 관련 주요 키워드를 중심으로 AI 기반 텍스트 분석과 수기 검토를 병행하였다. 수치는 2026-09-14 정본 재검산(의미 표현 사전 v2, 출현건수 기준) 값이다."),
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
         f"본 연구에서는 {s.documents}권의 반도체 교과서를 교육 내용에 따라 반도체 개발, 반도체 제조, 반도체 장비, 반도체 재료·인프라 분야로 재분류하였다. 이 분류는 교과서 제목과 주요 교육 내용을 기준으로 한 연구상 분류이며, 대시보드 자체에서 4개 분야별 수치를 별도로 제시한 것은 아니다. 분야별 쪽수는 각 교재 마크다운의 쪽 표식 최댓값을 합한 값이다. 분야별로 설명하면 다음과 같다."),
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
    top_area_book = c.top_book
    equip_pages = [p for p in c.pages if p["area"] == "장비"]
    equip_narrative = [p for p in equip_pages if p["verdict"] in ("case", "case_other")]
    equip_fp_kinds = Counter(p["kind"] for p in equip_pages if p["verdict"] == "false_positive")
    kind_label = FP_KIND_LABEL
    conditions = {
        "교과서의 전체 키워드 중 ‘안전’이": {"safety_top_grade": gmax},
        "사고 관련 주요 키워드 검출 건수는": {"accident_keyword_order": [n for n, _ in sorted(((x, k(x)["total"]) for x in accident_kw), key=lambda kv: (-kv[1], n.order.index(kv[0])))]},
        "‘보호구’는": {"ppe_over_60pct": ppe_majority},
        "한편 ‘공정안전관리’는": {"psm_all_grade3": psm_all3},
        "한편 ‘공정안전관리’는 총": {"psm_all_grade3": psm_all3},
        "반도체 제조 분야는 총": {"safety_share_vs_pages": _compare_share(safety["areas"]["제조"]["total"] / safety["total"], n.areas["제조"]["pages"] / pages_total).strip()},
        "반도체 장비 분야는 총": {"equipment_safety_rank": equip_rank, "equipment_narrative_pages": len(equip_narrative)},
        "반도체 재료 분야는 총": {"materials_is_top": safety_rank[0] == "재료", "near_half": near_half},
        "등급 2는 안전보건 관련 키워드가 확인되지만": {"largest_grade": _grade_max(n.grades)},
    }
    return _with_conditions([
        ("NCS 기반 반도체 자료를 대상으로",
         f"NCS 기반 반도체 자료를 대상으로 안전보건교육 내용의 실태를 분석하였다. 분석 대상은 자료 {n.documents}권, 총 {fmt(pages_total)}쪽(교재 마크다운의 쪽 표식 최댓값 합)이며, ’사망, 부상, 화학물질, 폭발, 감전, 직업병’ 등 {len(n.order)}개의 안전보건 관련 주요 키워드를 중심으로 AI 기반 텍스트 분석과 수기 검토를 병행하였다. 수치는 2026-09-14 정본 재검산(의미 표현 사전 v2, 출현건수 기준, 총 {fmt(n.total)}건) 값이다."),
        ("교과서의 전체 키워드 중 ‘안전’이",
         f"교과서의 전체 키워드 중 ‘안전’이 총 {fmt(safety['total'])}건으로 검출 건수가 가장 많았다. 그러나 이 중 등급 {gmax}이 {fmt(safety['grades'][gmax])}건({pct(safety['grades'][gmax], safety['total'])})으로 가장 많았고, 등급 2도 {fmt(safety['grades'][2])}건({pct(safety['grades'][2], safety['total'])})에 달했다. 반면 등급 3은 {fmt(safety['grades'][3])}건({pct(safety['grades'][3], safety['total'])})으로 상대적으로 낮았다. ‘안전’이라는 단어 자체는 자주 등장하지만, 실제로는 ‘안전에 유의한다.’ 수준의 일반적 표현이 많고, 구체적 예방 행동으로 연결되는 교육은 상대적으로 부족하다고 해석할 수 있다."),
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
         f"‘작업환경’은 {fmt(k('작업환경')['total'])}건, ‘중독’은 {fmt(k('중독')['total'])}건으로 검출 건수 자체는 많지 않았다. 하지만 ‘작업환경’의 등급 3 비율은 {fmt(k('작업환경')['grades'][3])}건({pct(k('작업환경')['grades'][3], k('작업환경')['total'])}), ‘중독’의 등급 3 비율은 {fmt(k('중독')['grades'][3])}건({pct(k('중독')['grades'][3], k('중독')['total'])})으로 나타나 전체 등급 3 비율({pct(n.grades[3], n.total)})과 비슷하거나 그보다 높았다. 이는 해당 키워드가 나올 때 단순 언급보다 구체적 상황 설명이나 예방·관리 내용까지 포함된 경우가 적지 않았다는 뜻이다. 다만 절대 건수가 적기 때문에 교과서 전반에서 작업환경 관리와 건강위험 예방이 충분히 체계화되었다고 보기는 어렵다."),
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
         area_intro("장비", "반도체 장비 분야는") + f" 이는 {equip_rel}, 안전보건교육이 비교적 많이 포함된 분야이다. 이 분야의 가장 큰 특징은 사고 사례 집중이다. 사고 사례로 자동 판정된 {c.flagged}쪽 중 {c.by_area_flagged.get('장비', 0)}쪽({pct(c.by_area_flagged.get('장비', 0), c.flagged)})이 이 분야의 『{top_area_book}』 한 권에 몰려 있어, 반도체 교과서에서 사고 교육이 장비 중심으로 이루어지고 있음을 알 수 있다. 다만 원문을 확인하면 그중 실제 사고 서술은 {len(equip_narrative)}쪽({', '.join(p['gist'].split(' (')[0] for p in equip_narrative)})이고 나머지 {len(equip_pages) - len(equip_narrative)}쪽은 {ro('·'.join(kind_label[k] for k, _ in equip_fp_kinds.most_common()))}, 사고 사례 자체는 이 분야에서도 매우 적다(3절 참조)."),
        ("반도체 재료 분야는 총",
         area_intro("재료", "반도체 재료 분야는").replace("차지하였다.", f"차지하여 분야 중 {'가장 높은' if safety_rank[0] == '재료' else str(safety_rank.index('재료') + 1) + '번째'} 비중을 보였다.")
         + (" 전체 안전보건교육 내용의 절반 가까이가 이 분야에 집중된 셈이다." if near_half else "")),
        ("실제로 전체적으로 가장 많이 검출된 키워드인 ‘안전’의 경우에도",
         f"실제로 전체적으로 가장 많이 검출된 키워드인 ‘안전’의 경우에도 총 {fmt(safety['total'])}건 중 {fmt(safety['grades'][1])}건({pct(safety['grades'][1], safety['total'])})이 등급 1로 분류되었다. 교과서 내에서 안전 관련 용어가 부분적으로 사용되더라도 실제로는 공정 설명, 설비 설명, 제품 설명에 부수적으로 언급된 것에 불과한 경우가 적지 않다는 점을 보여준다. 이러한 결과는 현재 반도체 교과서에서 안전보건이 독립적 교육 내용으로 충분히 자리 잡지 못하고 있음을 시사한다."),
        ("등급 2는 안전보건 관련 키워드가 확인되지만",
         f"등급 2는 안전보건 관련 키워드가 확인되지만, 내용이 대체로 선언적·추상적 수준에 머무는 경우를 의미한다. 대표적으로 “안전에 유의한다”, “작업 시 주의한다”, “보호구를 착용한다”, “화학물질 취급에 주의가 필요하다”와 같은 표현이 여기에 해당한다. 이러한 내용은 안전보건의 중요성을 암시하거나 기본적인 경각심을 주는 데는 의미가 있으나, 어떤 위험 요인이 존재하며, 그 위험을 줄이기 위해 어떤 조치를 어떻게 취해야 하는지까지는 충분히 설명하지 못한다. 실제로 본 연구에서 가장 두드러진 결과는 등급 2의 비중이 가장 높다는 점이었다. 전체 분석 결과, 등급 1(미흡·없음)은 {fmt(n.grades[1])}건, 등급 2(형식적 언급)는 {fmt(n.grades[2])}건, 등급 3(구체적 대책)은 {fmt(n.grades[3])}건으로 나타나 등급 {_grade_max(n.grades)}가 가장 많았으며, 이는 전체의 약 {pct(n.grades[_grade_max(n.grades)], n.total)}를 차지하였다. 특히 ‘안전’ 키워드는 총 {fmt(safety['total'])}건 중 {fmt(safety['grades'][2])}건({pct(safety['grades'][2], safety['total'])})이 등급 2였다. 이 결과는 현재 반도체 교과서의 안전보건교육이 “안전은 중요하다”는 메시지를 전달하는 수준에는 도달했지만, 학생이 실제 현장에서 위험을 식별하고 예방 행동을 수행할 수 있도록 돕는 수준까지는 충분히 발전하지 못했다는 점을 보여준다."),
        ("등급 3은 위험 요인, 사고 유형, 건강 영향",
         f"등급 3은 위험 요인, 사고 유형, 건강 영향, 예방 대책, 작업 절차, 보호구 사용법, 비상 대응 등이 구체적으로 제시되어 실제 행동과 연결 가능한 수준의 교육 내용을 의미한다. 이 등급은 단순히 “주의하라”는 수준을 넘어, 예를 들어 “불산 취급 시 보호장갑과 보호안경을 착용해야 하며 피부 접촉 시 즉시 세척하고 응급조치를 시행한다”와 같이 위험 요인–예방조치–대응 방법이 연계되어 설명되는 경우를 포함한다. 전체적으로 등급 3은 {fmt(n.grades[3])}건으로 전체의 약 {pct(n.grades[3], n.total)}를 차지하였다. 이는 교과서 내에 구체적 안전보건 내용이 일정 부분 존재함을 보여주지만, 여전히 형식적 언급(등급 2)에 비해 적은 수준이다. 즉, 현재 교과서는 구체적이고 실천 가능한 안전교육을 일부 포함하고 있으나, 전체 교육 구조를 대표할 정도로 충분한 비중은 아니라고 볼 수 있다. 키워드별로 보면, 등급 3의 비율이 상대적으로 높은 항목도 확인되었다. 예를 들어 ‘보호구’는 총 {fmt(ppe['total'])}건 중 {fmt(ppe['grades'][3])}건({pct(ppe['grades'][3], ppe['total'])})이 등급 3으로 분류되었다. 이는 보호구 관련 내용이 등장하는 경우에는 비교적 구체적으로 설명되는 비율이 높다는 뜻이다. 즉, 안전화, 헬멧, 보호안경, 장갑 등 보호구의 종류나 착용 필요성이 실제 작업과 연결되어 설명되는 경우가 많았음을 의미한다."),
        ("또한 ‘작업환경’은 총",
         f"또한 ‘작업환경’은 총 {fmt(k('작업환경')['total'])}건 중 {pct(k('작업환경')['grades'][3], k('작업환경')['total'])}, ‘중독’은 총 {fmt(k('중독')['total'])}건 중 {pct(k('중독')['grades'][3], k('중독')['total'])}가 등급 3에 해당하였다. 이 결과는 해당 키워드가 교과서에 자주 등장하지는 않더라도, 일단 등장하는 경우에는 전체 평균({pct(n.grades[3], n.total)}) 수준 이상의 구체적인 설명이 수반되는 경향이 있음을 보여준다. 다시 말하면, 작업환경이나 중독 관련 내용은 양적으로는 부족하지만 질적으로는 상대적으로 충실한 편으로 해석할 수 있다."),
        ("한편 ‘공정안전관리’는 총",
         f"한편 ‘공정안전관리’는 총 {fmt(k('공정안전관리')['total'])}건, ‘PSM’은 총 {fmt(k('PSM')['total'])}건으로 절대 빈도는 매우 낮았으나, "
         + ("특히 공정안전관리의 경우 검출된 내용이 모두 등급 3에 해당하였다. " if psm_all3 else f"공정안전관리의 경우 {fmt(k('공정안전관리')['grades'][3])}건({pct(k('공정안전관리')['grades'][3], k('공정안전관리')['total'])})이 등급 3에 해당하였다. ")
         + "이는 해당 개념이 교과서에 거의 포함되어 있지 않지만, 포함되는 경우에는 비교적 구체적이고 전문적인 내용으로 제시되고 있음을 의미한다. 그러나 빈도 자체가 매우 적기 때문에 이를 근거로 교과서 전반의 공정안전교육 수준이 충분하다고 평가하기는 어렵다."),
        ("주: 단위: 건.",
         f"주: 단위: 건. 등급 비율의 분모: {fmt(n.total)}건(2026-09-14 정본, 의미 표현 사전 v2, 등급 미확정 0건). 등급은 출현이 놓인 페이지의 판정값을 출현별로 연결한 값임."),
    ], conditions)


def case_paragraphs(f: Facts) -> list[tuple[str, str, dict]]:
    c = f.cases
    industrial_books = [p["title"] for p in c.pages if p["verdict"] == "case"]
    other = [p for p in c.pages if p["verdict"] == "case_other"]
    kinds = c.fp_kinds
    conditions = {
        "본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를": {"flagged": c.flagged, "narrative": c.narrative, "industrial_events": c.industrial_events, "false_positive": c.false_positive},
        "사례의 분포를 보면": {"areas_without_cases": [a for a in AREA_ORDER if c.by_area_flagged.get(a, 0) == 0]},
    }
    return _with_conditions([
        ("본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를",
         f"본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를 체계적으로 수집·정리하고, 내용 수준과 구성 특성을 분석하였다. 키워드 검색 결과의 ‘사고사례여부’ 자동 판정은 {c.books}권 {c.flagged}쪽을 사례로 잡았으나, 해당 쪽의 원문을 확인한 결과 실제로 사고를 서술한 쪽은 {c.narrative}쪽뿐이었고, 그중 반도체 산업재해는 구미 불산 가스 누출 사고 {c.industrial_events}건({' '.join(wa('『' + b + '』') if i < len(dict.fromkeys(industrial_books)) - 1 else '『' + b + '』' for i, b in enumerate(dict.fromkeys(industrial_books)))} {c.industrial_books}권에 중복 게재)이었으며, 나머지 {len(other)}쪽은 반도체 산업재해가 아닌 사고({', '.join(p['gist'].split(' (')[0] for p in other)})였다(표 13 참조). 이러한 결과는 반도체산업이 화학물질, 특수 가스, 고에너지 장비 등을 활용하는 대표적인 고위험 산업임을 감안할 때, 교과서에 수록된 사고 사례의 양적 수준이 매우 제한적임을 보여 준다."),
        ("사례의 분포를 보면",
         f"사례의 분포를 보면, 자동 판정 {c.flagged}쪽 중 {c.top_book_pages}쪽이 『{c.top_book}』에 몰려 있어, 현재 교과서에서 사고 관련 내용이 주로 장비 유지보수와 점검 작업 중심으로 구성되어 있다. 반면 {', '.join(a for a in AREA_ORDER if c.by_area_flagged.get(a, 0) == 0)} 분야에서는 사고 사례가 전혀 제시되지 않아, 공정과 직무 전반을 반영한 균형 있는 교육 구성은 부족한 것으로 나타났다."),
        ("사고 유형 측면에서는",
         f"사고 유형 측면에서는 실제 사고 서술 {c.narrative}쪽이 화학물질(불산) 누출 사고와 시설물(환풍구) 붕괴 사고였다. 자동 판정이 사례로 잡은 나머지 {c.false_positive}쪽은 {', '.join(f"{FP_KIND_LABEL[kind]}({n}쪽)" for kind, n in kinds.most_common())}으로, TMAH·아르신 노출이나 이온주입 장비의 방사선 노출은 사고 사례가 아니라 취급 지침과 유해성 설명의 맥락에서 언급된 것이었다. 즉, 반도체산업의 주요 위험 요인 자체는 교과서에 등장하지만, 그것이 실제 사고 사례로 제시되는 경우는 불산 누출 사고 {c.industrial_events}건에 그친다."),
        ("사례의 서술 방식 또한 중요한 특징이다",
         "사례의 서술 방식 또한 중요한 특징이다. 실제 사고 서술은 한두 문장으로 매우 간략하게 제시되어, 사고의 발생 원인, 작업조건, 진행 경과, 피해 규모, 재발 방지 대책 등 교육적으로 중요한 정보가 거의 포함되지 않았다. 즉, 학습자가 해당 사례를 통해 위험 요인을 분석하거나 예방 행동을 학습하기에는 충분한 정보가 제공되지 않는 구조이다."),
        ("또한 사고 사례는 대부분 위험 상황을 단순히 언급하는 수준에",
         "또한 사고 사례는 위험 상황을 단순히 언급하는 수준에 머물러 있으며, 위험 요인 분석이나 예방조치와 연계성이 부족하였다. 이는 사고 사례가 교육적 학습 자료로 활용되기보다는 참고 수준의 정보로 제시되고 있음을 의미한다. 결과적으로 현재 교과서는 사고가 있음을 알리는 기능은 수행하고 있으나, 사고를 통한 위험 인식 강화나 예방 행동 유도 측면에서는 제한적인 역할에 머무르고 있다."),
        ("이러한 분석 결과를 종합하면, NCS 반도체 교과서에 수록된 사고 사례는",
         f"이러한 분석 결과를 종합하면, NCS 반도체 교과서에 수록된 사고 사례는 양적·질적 측면에서 모두 제한적인 수준이며, 반도체산업의 실제 위험 구조를 충분히 반영하지 못한다고 판단된다. 특히 실제 사고 서술이 {c.narrative}쪽·{c.industrial_events}건에 불과하고, 그마저 장비 분야 한 권과 재료 분야 한 권에 중복 게재된 화학물질 급성 사고 위주이며, 사고 원인과 예방 대책이 충분히 제시되지 않는다는 점은 교육적 활용도를 저해하는 주요 요인이다. 아울러 자동 판정 {c.flagged}쪽 중 {c.false_positive}쪽이 오탐이었다는 점은 키워드 기반 자동 판정만으로 사고 사례를 세어서는 안 되며 원문 확인이 필요함을 보여준다."),
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
    if len(data) != len(rows):
        raise ValueError(f"표 행 수 {len(data)} ≠ 값 행 수 {len(rows)}")
    changed = 0
    if header is not None:
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
        w, h = struct.unpack(">II", data[16:24]); return w, h, "PNG"
    if data[:2] == b"BM":
        w, h = struct.unpack("<ii", data[18:26]); return w, abs(h), "BMP"
    raise ValueError("PNG 또는 BMP 가 아닙니다")


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
    return f'<text x="{x}" y="{y}" font-family="AppleGothic, sans-serif" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{text}</text>'


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
    """ImageMagick — PNG24 또는 BMP3(24bit). 폰트 경로를 고정해 결정론을 유지한다."""
    if shutil.which("magick") is None:
        raise RuntimeError("ImageMagick(magick)이 없어 그림을 그릴 수 없습니다")
    with tempfile.TemporaryDirectory() as td:
        svg_path = Path(td) / "chart.svg"
        svg_path.write_text(svg, encoding="utf-8")
        target = "PNG24:-" if fmt_ == "PNG" else "BMP3:-"
        font_args = ["-font", FONT] if Path(FONT).exists() else []
        out = subprocess.run(["magick", "-density", "96", "-background", "white", *font_args, str(svg_path), "-resize", f"{width}x{height}!", "-type", "TrueColor", target],
                             check=True, capture_output=True).stdout
    w, h, kind = image_dimensions(out)
    if (w, h, kind) != (width, height, fmt_):
        raise RuntimeError(f"렌더 결과 {kind} {w}×{h} ≠ 요청 {fmt_} {width}×{height}")
    if kind == "BMP" and image_bits(out) != 24:
        raise RuntimeError(f"BMP 비트 깊이 {image_bits(out)} ≠ 24")
    return out


def figure_specs(f: Facts) -> list[dict]:
    """(절, 캡션 접두, svg 함수) — 그림 2 교과서 등급별, 그림 3 NCS 분야별, 그림 4 NCS 등급별."""
    stamp = "정본 2026-09-14 · 의미 표현 사전 v2 · 출현건수 기준"
    return [
        {"section": "textbook", "caption": None, "item": "image1", "label": "그림 2", "svg": lambda w, h: grade_bars_svg(w, h, "교과서 안전보건 등급별 출현건수", f"등급 판정 {fmt(f.school.total)}건 · 출현건수 기준", f.school.grades, f.school.total, f"{stamp}\n교과서 {f.school.documents}권 · 등급 미확정 0건")},
        {"section": "ncs", "caption": "그림 3.", "item": None, "label": "그림 3", "svg": lambda w, h: area_bars_svg(w, h, "NCS 분야별 등급 출현건수", f.ncs.areas, f"원자료 폴더 기준 · NCS {f.ncs.documents}권 {fmt(f.ncs.total)}건에 등급 1~3 배정\n{stamp}")},
        {"section": "ncs", "caption": "그림 4.", "item": None, "label": "그림 4", "svg": lambda w, h: grade_bars_svg(w, h, "NCS 안전보건 등급별 출현건수", f"등급 판정 {fmt(f.ncs.total)}건 · 출현건수 기준", f.ncs.grades, f.ncs.total, f"등급: 출현이 놓인 페이지의 판정값을 각 키워드 출현에 연결 · 미확정 0건\n{stamp}")},
    ]


# ---------------------------------------------------------------- ZIP
def read_section(hwpx: Path) -> tuple[bytes, ET.Element, str]:
    with zipfile.ZipFile(hwpx) as z:
        raw = z.read(SECTION_ENTRY)
    text = raw.decode("utf-8")
    m = re.search(r"<hs:sec\b[^>]*>", text)
    if not m:
        raise ValueError("section0.xml 의 hs:sec 루트를 찾지 못했습니다")
    for prefix, uri in re.findall(r'xmlns:([A-Za-z0-9]+)="([^"]+)"', m.group(0)):
        ET.register_namespace(prefix, uri)
    return raw, ET.fromstring(raw), m.group(0)


def serialize_section(root: ET.Element, root_tag: str) -> bytes:
    body = ET.tostring(root, encoding="unicode")
    body = re.sub(r"^<hs:sec\b[^>]*>", lambda _: root_tag, body, count=1)
    return (XML_DECL + body).encode("utf-8")


def write_hwpx(src: Path, out: Path, section_xml: bytes, bindata: dict[str, bytes], force: bool = False) -> None:
    src, out = Path(src), Path(out)
    if src.resolve() == out.resolve():
        raise ValueError("출력이 입력과 같은 파일입니다 — 원본은 덮어쓰지 않습니다")
    if out.exists() and not force:
        raise FileExistsError(f"{out.name} 이 이미 있습니다 (--force 로 덮어쓰기)")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == SECTION_ENTRY:
                data = section_xml
            elif info.filename in bindata:
                data = bindata[info.filename]
            new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr
            zout.writestr(new_info, data)
    os.replace(tmp, out)


# ---------------------------------------------------------------- 감사·대조
def numbers_in(text: str) -> list[str]:
    return NUMBER_TOKEN.findall(text)


ALLOWED_TOKENS = {"0", "1", "2", "3", "4", "30", "100.0%", "60%"}      # 등급·분야 번호, 30개 키워드, 합계 비율, 60% 기준 (사고 연도는 cases.gist 에서 온다)
STRIP_BEFORE_AUDIT = re.compile(r"\d{4}-\d{2}-\d{2}|(?:표|그림)\s*\d+\.?|\d+\)\s|\(\d+\)|등급\s*1~3")   # 날짜·표/그림 번호·목차 번호는 수치가 아니다


def audit_numbers(texts: list[str], facts: Facts) -> list[str]:
    """정본 값(총계·등급·분야·키워드·쪽수·비율·쪽 번호)이 아닌 숫자 토큰 — 남아 있으면 구 수치다."""
    allowed = facts.all_numbers() | ALLOWED_TOKENS
    unmatched = []
    for text in texts:
        for token in numbers_in(STRIP_BEFORE_AUDIT.sub(" ", text)):
            if token not in allowed and token.rstrip("%") not in allowed:
                unmatched.append(token)
    return sorted(set(unmatched))


def section_texts(section: Section) -> list[str]:
    out = []
    for p in section.paragraphs:
        if has_object(p, "tbl"):
            for tbl in p.findall(f".//{HP}tbl"):
                for tcs in table_rows(tbl):
                    out.extend(cell_text(tc) for tc in tcs)
        else:
            out.append(direct_text(p))
    return out


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _under_tracked_docs(path: Path) -> bool:
    return os.path.realpath(str(path)).startswith(os.path.realpath(str(HERE / "docs")) + os.sep)


def public(path: Path) -> str:
    """저장소 상대 경로 (메시지·도움말용 — 절대 경로를 찍지 않는다)."""
    try:
        return str(Path(path).resolve().relative_to(HERE))
    except ValueError:
        return Path(path).name


# ---------------------------------------------------------------- 실행
DEFAULT_TEXT_REVIEW_DIR = HERE / "data" / "hwpx-results-refresh"


def refresh(hwpx: Path, facts: Facts, out: Path, diff_out: Path | None, review_dir: Path | None, force: bool = False, render: bool = True,
            text_review_dir: Path | None = None) -> dict:
    raw, root, root_tag = read_section(hwpx)
    original_xml = ET.fromstring(raw)
    sections = locate_sections(root)
    diff: dict = {"source": {"hwpx": hwpx.name, "hwpx_sha256": sha256(hwpx.read_bytes()), "summary_run": {k: facts.run.get(k) for k in ("generated_at", "git_commit", "dictionary", "expected")},
                             "cases_date": facts.cases_date},
                  "output": out.name, "paragraphs": [], "tables": [], "figures": [], "audit": {}}
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
            new_numbers = numbers_in(STRIP_BEFORE_AUDIT.sub(" ", new_text))
            diff["paragraphs"].append({"section": name, "locator": prefix, "old_numbers": numbers_in(old), "new_numbers": new_numbers,
                                       "keys": facts.keys_for(new_numbers), "conditions": conditions, **info})
            text_pairs.append((name, old, new_text))

    # 표
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
        diff["tables"].append({"section": name, "caption": caption, "rows": len(table_rows(tbl)), "cols": len(table_rows(tbl)[first]), "changed_cells": changed})
    tbl13 = find_table_by_first_cell(sections["cases"], "표 13.")
    rows13 = case_table_rows(facts.cases)
    resize_table(tbl13, 2, len(rows13))
    changed = fill_table(tbl13, rows13, 2, ["교과서 이름", "교과서 분야", "사고/부상 등 주요 내용", "페이지", "판정"])
    diff["tables"].append({"section": "cases", "caption": "표 13.", "rows": len(table_rows(tbl13)), "cols": len(table_rows(tbl13)[2]), "changed_cells": changed})

    # 그림
    bindata: dict[str, bytes] = {}
    review_images: list[tuple[str, bytes, str]] = []
    with zipfile.ZipFile(hwpx) as z:
        names = z.namelist()
        for spec in figure_specs(facts):
            pic = find_picture(sections[spec["section"]], spec["caption"], spec["item"])
            item = pic.find(f".//{HC}img").get("binaryItemIDRef")
            entry = next((n for n in names if n.startswith("BinData/") and Path(n).stem == item), None)
            if entry is None:
                raise ValueError(f"BinData/{item}.* 항목이 HWPX 에 없습니다 (binaryItemIDRef={item})")
            width, height, kind = image_dimensions(z.read(entry))
            svg = spec["svg"](width, height)
            record = {"label": spec["label"], "caption": spec["caption"], "item": item, "entry": entry, "format": kind, "width": width, "height": height, "svg_sha256": sha256(svg.encode("utf-8"))}
            if render:
                data = render_svg(svg, kind, width, height)
                bindata[entry] = data
                record["sha256"] = sha256(data)
                record["bits"] = image_bits(data)
                review_images.append((spec["label"], data, kind))
            diff["figures"].append(record)

    # 감사 — 다시 쓴 1~3절의 숫자 토큰 전부가 정본 값이어야 한다
    texts = [t for name in sections for t in section_texts(sections[name])]
    unmatched = audit_numbers(texts, facts)
    diff["audit"] = {"tokens": sum(len(numbers_in(t)) for t in texts), "unmatched": unmatched,
                     "out_of_scope": out_of_scope_numbers(root, facts)}          # 2장 5절(방법론)의 정본 밖 숫자 — 기록만, 실패 아님

    # 1~3절 밖 불변 검사
    old_tops = top_paragraphs(original_xml); new_tops = top_paragraphs(root)
    inside = set()
    for s in sections.values():
        inside.update(range(s.start, s.end))
    if len(old_tops) != len(new_tops) or any(ET.tostring(old_tops[i]) != ET.tostring(new_tops[i]) for i in range(len(old_tops)) if i not in inside):
        raise RuntimeError("1~3절 밖의 문단이 바뀌었습니다 — 중단")

    if unmatched:
        diff["audit"]["status"] = "failed"
        diff["output"] = None
    elif render:
        diff["audit"]["status"] = "ok"
        write_hwpx(hwpx, out, serialize_section(root, root_tag), bindata, force=force)
        diff["output_sha256"] = sha256(out.read_bytes())
    else:
        diff["audit"]["status"] = "ok"                        # 점검 실행 — HWPX 는 쓰지 않는다
        diff["output"] = None
    if diff_out:
        if unmatched and _under_tracked_docs(diff_out):     # 실패 기록이 추적 정본 대조를 덮어쓰지 않게
            diff_out = Path(tempfile.mkdtemp(prefix="hwpx_refresh_failed_")) / diff_out.name
            print(f"숫자 감사 실패 — 대조 JSON 은 {diff_out} 에 씁니다 (추적 파일은 그대로)")
        diff_out.parent.mkdir(parents=True, exist_ok=True)
        diff_out.write_text(json.dumps(diff, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if review_dir and not unmatched:
        write_review(review_dir, facts, table_specs + [("cases", "표 13.", rows13, 2, None)], review_images)
    if text_review_dir and not unmatched:
        write_text_review(text_review_dir, text_pairs)
    return diff


OUT_OF_SCOPE_HEADINGS = ("5. 키워드 기반 문서 분류·분석 방법론", "제3장 연구 결과")    # 2장 5절 본문 ~ 3장 시작


def out_of_scope_numbers(root: ET.Element, facts: Facts) -> dict:
    """계획 §2.2 — 2장 5절(방법론)에 남은 정본 밖 숫자를 기록만 한다(범위 밖, 갱신하지 않음)."""
    tops = top_paragraphs(root)
    texts = [direct_text(p).strip() for p in tops]
    start_hits = [i for i, t in enumerate(texts) if t == OUT_OF_SCOPE_HEADINGS[0]]
    end_hits = [i for i, t in enumerate(texts) if t == OUT_OF_SCOPE_HEADINGS[1]]
    if len(start_hits) < 2 or len(end_hits) < 2:
        return {"section": OUT_OF_SCOPE_HEADINGS[0], "found": False}
    start, end = start_hits[1], end_hits[1]                 # 첫 번째는 목차
    if end <= start:
        return {"section": OUT_OF_SCOPE_HEADINGS[0], "found": False}
    section = Section("methodology", start, end, tops[start:end])
    stale = audit_numbers(section_texts(section), facts)
    return {"section": OUT_OF_SCOPE_HEADINGS[0], "found": True, "stale_numbers": stale}


def write_text_review(text_review_dir: Path, pairs: list[tuple[str, str, str]]) -> None:
    """구/신 문장 병기본 — 보고서 본문을 담으므로 data/ 아래(비추적)에만 쓴다."""
    import html
    text_review_dir.mkdir(parents=True, exist_ok=True)
    parts = ["<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><title>HWPX 제3장 문단 구/신 대조 (비추적)</title>",
             "<style>body{font-family:-apple-system,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.5}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.4rem .6rem;vertical-align:top;width:50%}th{background:#f3f4f6}h2{margin-top:2rem}</style></head><body>",
             "<h1>HWPX 제3장 문단 구/신 대조</h1><p>보고서 본문을 담으므로 이 파일은 <code>data/</code> 아래(비추적)에만 둔다.</p>"]
    current = None
    for name, old, new in pairs:
        if name != current:
            if current is not None:
                parts.append("</table>")
            parts.append(f"<h2>{html.escape(name)}</h2><table><tr><th>구 문장</th><th>새 문장</th></tr>")
            current = name
        parts.append(f"<tr><td>{html.escape(old)}</td><td>{html.escape(new)}</td></tr>")
    parts.append("</table></body></html>")
    (text_review_dir / "review_text.html").write_text("".join(parts), encoding="utf-8")


def write_review(review_dir: Path, facts: Facts, table_specs, images) -> None:
    import base64, html
    review_dir.mkdir(parents=True, exist_ok=True)
    numeric = re.compile(r"[\d,.%]+")
    parts = ["<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>HWPX 제3장 표·그림 검토본</title>",
             "<style>body{font-family:-apple-system,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem}.scroll-x{overflow-x:auto}table{border-collapse:collapse;margin:1rem 0}td,th{border:1px solid #ccc;padding:.25rem .6rem;font-size:.875rem}th{background:#f3f4f6}td.n{text-align:right;font-variant-numeric:tabular-nums}img{max-width:100%;border:1px solid #ddd;margin:.5rem 0}</style></head><body>",
             f"<h1>HWPX 제3장 표·그림 검토본</h1><p>정본 {html.escape(str(facts.run.get('generated_at')))} · git {html.escape(str(facts.run.get('git_commit')))} · 사전 {html.escape(str(facts.run.get('dictionary')))}. 본문 문장은 담지 않는다(표·그림만).</p>"]
    for name, caption, rows, first, header in table_specs:
        parts.append(f"<h2>{html.escape(caption)} ({name})</h2><div class=\"scroll-x\"><table>")
        for row in rows:
            parts.append("<tr>" + "".join(f"<td class=\"n\">{html.escape(c)}</td>" if numeric.fullmatch(c) else f"<td>{html.escape(c)}</td>" for c in row) + "</tr>")
        parts.append("</table></div>")
    for caption, data, kind in images:
        if kind == "BMP":
            data = subprocess.run(["magick", "BMP:-", "PNG:-"], input=data, check=True, capture_output=True).stdout
        parts.append(f"<h2>{html.escape(caption)}</h2><img alt=\"{html.escape(caption)}\" src=\"data:image/png;base64,{base64.b64encode(data).decode()}\">")
    parts.append("</body></html>")
    (review_dir / "review.html").write_text("".join(parts), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="기초보고서 HWPX 제3장 1~3절을 정본 수치로 다시 쓴다")
    ap.add_argument("--hwpx", type=Path, default=DEFAULT_HWPX)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--recount-summary", type=Path, default=DEFAULT_RECOUNT)
    ap.add_argument("--diff-out", type=Path, default=None, help=f"변경 대조 JSON (기본 {public(DEFAULT_DIFF)})")
    ap.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="그림을 그리지 않는 점검 실행 — 출력 HWPX·추적 대조 JSON 을 쓰지 않는다 (--diff-out 은 docs/ 밖 경로만)")
    ap.add_argument("--text-review-dir", type=Path, default=DEFAULT_TEXT_REVIEW_DIR, help="구/신 문장 병기본 (본문 포함 — data/ 아래, 비추적)")
    args = ap.parse_args(argv)
    facts = load_facts(args.summary, args.cases, args.recount_summary)
    if _under_tracked_docs(args.text_review_dir):
        sys.exit(f"구/신 문장 병기본은 보고서 본문을 담으므로 추적 경로(docs/)에 쓸 수 없습니다: {public(args.text_review_dir)}")
    if args.no_render:
        if args.diff_out is None:
            diff_out = Path(tempfile.mkdtemp(prefix="hwpx_refresh_dry_")) / "hwpx_results_refresh_dry.json"
        elif _under_tracked_docs(args.diff_out):
            sys.exit(f"--no-render 점검 실행은 추적 경로에 대조 JSON 을 쓰지 않습니다: {public(args.diff_out)}")
        else:
            diff_out = args.diff_out
        diff = refresh(args.hwpx, facts, args.out, diff_out, None, force=True, render=False)   # render=False → HWPX 는 쓰지 않는다
        print(f"(점검 실행 — 대조 JSON: {diff_out})")
    else:
        diff = refresh(args.hwpx, facts, args.out, args.diff_out or DEFAULT_DIFF, args.review_dir, force=args.force, text_review_dir=args.text_review_dir)
    print(f"문단 {len(diff['paragraphs'])}개 · 표 {len(diff['tables'])}개 · 그림 {len(diff['figures'])}개 · 숫자 토큰 {diff['audit']['tokens']}개 · 미일치 {len(diff['audit']['unmatched'])}개")
    if diff["audit"]["unmatched"]:
        print("정본에 없는 숫자:", ", ".join(diff["audit"]["unmatched"]))
        return 1
    if not args.no_render:
        print(f"→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
