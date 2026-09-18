"""hwpx_results_refresh.py 테스트 — 사고사례 판정 데이터, 절 탐지, 문단 템플릿, 표·그림 교체, ZIP 재작성, 숫자 감사. 실문서 없이 fixture HWPX 로 돈다."""

import csv
import json
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "docs" / "03-analysis" / "data"


class AccidentCasePagesTests(unittest.TestCase):
    """FR-12 — accident_case_pages.json 은 ncs_pages_reseg.csv 의 사고사례=예 13쪽과 같은 집합이고 판정 집계가 고정돼 있다."""

    def test_pages_match_reseg_csv_and_verdict_counts(self):
        cases = json.loads((DATA / "accident_case_pages.json").read_text(encoding="utf-8"))
        with (DATA / "ncs_pages_reseg.csv").open(encoding="utf-8-sig", newline="") as fh:
            flagged = {(r["교재"], int(r["페이지"])) for r in csv.DictReader(fh) if r["사고사례"] == "예"}
        self.assertEqual(flagged, {(p["book"], p["page"]) for p in cases["pages"]})
        self.assertEqual(13, len(cases["pages"]))
        self.assertEqual({"case": 2, "case_other": 1, "false_positive": 10}, Counter(p["verdict"] for p in cases["pages"]))
        self.assertEqual(5, len({p["book"] for p in cases["pages"]}))
        reseg = json.loads((DATA / "reseg_summary.json").read_text(encoding="utf-8"))
        self.assertEqual((reseg["cases_pages"], reseg["cases_books"]), (13, 5))
        self.assertEqual(1, len({p["event"] for p in cases["pages"] if p["verdict"] == "case"}))          # 반도체 산업재해 사건 1건 (2권 중복)
        self.assertEqual({"guideline": 6, "definition": 1, "property": 3}, Counter(p["kind"] for p in cases["pages"] if p["verdict"] == "false_positive"))
        self.assertTrue(all(len(p["gist"]) <= 30 for p in cases["pages"]))                                 # 본문 인용 아님 — 요지만
        self.assertNotIn("/Users/", json.dumps(cases))


class CommittedDiffTests(unittest.TestCase):
    """실문서 실행의 대조 JSON — 숫자 감사 통과, 문단 45·표 7+5·그림 3, 2단계(methods·bridge) 기록, 본문·절대 경로 없음."""

    def test_committed_diff_json(self):
        paths = sorted(DATA.glob("hwpx_results_refresh_2*.json"))
        if not paths:
            self.skipTest("대조 JSON 없음")
        path = paths[-1]                                                                                   # 가장 최근 실행(날짜 접미)
        diff = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual({"NCS": "real", "교과서": "marker"}, diff["source"]["page_basis"])                    # occurrence-real-pages 이후의 정본으로 만든 산출물
        self.assertEqual(([], "ok"), (diff["audit"]["unmatched"], diff["audit"]["status"]))
        self.assertNotIn("out_of_scope", diff["audit"])                                                            # 5절은 2단계로 감사 범위에 들어왔다 (hwpx-methods-bridge-refresh FR-14)
        self.assertEqual((14, 3), (len(diff["tables"]), len(diff["figures"])))                                             # 3단계 표 12-3·12-4 포함 (ncs-book-concentration)
        self.assertEqual({"PNG": 1, "BMP": 2}, Counter(f["format"] for f in diff["figures"]))
        self.assertTrue(all(len(f["sha256"]) == 64 for f in diff["figures"]))
        self.assertTrue(all(f["bits"] == 24 for f in diff["figures"] if f["format"] == "BMP"))                      # G-6 24bit
        self.assertTrue(all(f["rendered"] for f in diff["figures"]))                                              # 추적 정본은 그림을 그린 실행
        self.assertEqual("2026-09-06", diff["source"]["cases_date"])                                                # G-5
        conds = {p["locator"]: p["conditions"] for p in diff["paragraphs"] if p.get("conditions")}
        self.assertFalse(conds["한편 ‘공정안전관리’는 총"]["psm_all_grade3"])                                          # G-1 조건 기록 (5/7)
        self.assertTrue(conds["‘보호구’는"]["ppe_over_60pct"])
        self.assertTrue(all(p["keys"] for p in diff["paragraphs"] if set(p["new_numbers"]) - HR.ALLOWED_TOKENS))  # G-2 출처 키 (등급 번호 같은 작은 수만 있는 문단 제외)
        self.assertEqual(5, next(t for t in diff["tables"] if t["caption"] == "표 13.")["cols"])                   # G-8
        m, b = diff["methods"], diff["bridge"]                                                                     # 2단계 — 설계 §3.9
        self.assertEqual(({"rewritten": 6, "removed": 2}, {"caption_changed": True, "changed_cells": 2}, 6, 20, 2), (m["toc"], m["table4"], m["removed_paragraphs"], len(m["inserted"]), len(m["rewritten"])))
        self.assertGreater(m["audited_tokens"], 30)
        self.assertEqual(({"rewritten": 1, "inserted": 2}, 15, {"4) 소결": "6) 소결"}, True), (b["toc"], len(b["inserted"]), b["renumbered"], b["conclusion_inserted"]))
        c = diff["concentration"]                                                                                      # 3단계 — 교재별 집중 (ncs-book-concentration)
        self.assertEqual((14, ["LM1903060329", "LM1903060411"]), (len(c["inserted"]), c["dedicated"]))   # 15 → 14: 선행 중복 빈 문단 제거 (ship 적대적 리뷰)
        self.assertEqual([("표 12-3.", 8, 4), ("표 12-4.", 11, 4)], [(t["caption"], t["rows"], t["cols"]) for t in c["tables"]])
        self.assertEqual({"dedicated_count": 2, "rest_rate_direction": "내려간다", "group_majority": {"반도체장비": True, "반도체재료": False}, "zero_majority": True}, c["conditions"])
        self.assertTrue(all(pc["keys"] for pc in c["inserted"] if pc["kind"] in ("P", "N") and set(pc["numbers"]) - HR.ALLOWED_TOKENS))
        self.assertEqual([("표 12-1.", 7, 4), ("표 12-2.", 7, 4)], [(t["caption"], t["rows"], t["cols"]) for t in b["tables"]])
        self.assertEqual({"grade_verbs": ["줄고", "늘었으며", "거의 같았다"], "real_pages_vs_block": "늘었으며", "shared_all_agree": True, "occurrence_share_exceeds_page_share": True, "level_same": True}, b["conditions"])
        self.assertTrue(all(pc["keys"] for pc in m["inserted"] + b["inserted"] if pc["kind"] in ("P", "N") and set(pc["numbers"]) - HR.ALLOWED_TOKENS))   # 삽입 문단의 숫자는 출처 키가 있다
        self.assertEqual("real", conds["본 연구에서는 9권의 반도체 교과서를"]["page_basis"])                                    # 1절 교과서 불변 문장
        self.assertNotIn("previous_output_identical", diff["source"]); self.assertNotIn("runtime", diff); self.assertNotIn(".bak", path.read_text(encoding="utf-8"))   # 실행 환경(백업 이름·sha·동일 여부)은 추적 JSON 밖 (ship 레드팀·적대적 리뷰)
        self.assertEqual({"paragraphs": 124, "linesegarray_removed": 912, "ledger_paragraphs": 124}, diff["layout"])   # 장부의 최상위 문단 124 전부의 줄 배치 캐시 제거(한글 원본은 문단마다 캐시가 있으므로 paragraphs == ledger_paragraphs), 표 셀까지 912 (선행 중복 빈 문단 제거로 125→124, ship 적대적 리뷰)
        self.assertEqual(64, len(diff["output_sha256"]))
        self.assertEqual("v2", diff["source"]["summary_run"]["dictionary"])
        self.assertTrue(diff["source"]["summary_run"]["expected"])
        self.assertNotIn("/Users/", path.read_text(encoding="utf-8"))
        self.assertTrue(all(len(p["locator"]) <= 50 for p in diff["paragraphs"]))          # 문단 식별용 첫머리만, 본문 없음
        run = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))["meta"]["run"]
        self.assertEqual({k: run.get(k) for k in ("generated_at", "git_commit", "dictionary", "expected")}, diff["source"]["summary_run"])   # 대조 JSON 은 지금의 정본 실행에 묶여 있다 (F4)
        self.assertEqual(path.name, HR.default_diff_path(fixture_facts()).name)                                                          # 날짜 접미 = 정본 실행일
        facts = fixture_facts()
        self.assertEqual([], HR.audit_numbers([" ".join(p["new_numbers"]) for p in diff["paragraphs"]], facts))                    # 기록된 새 숫자는 전부 지금의 정본 값
        self.assertEqual("v2", HR.CANONICAL_DICTIONARY)


# ---------------------------------------------------------------- fixture HWPX
import contextlib
import copy
import io
import re
import shutil
import struct
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import zlib

import hwpx_results_refresh as HR

HP = HR.HP
NS = ('xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
      'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app"')


def para(text, char="13", extra_runs=()):
    runs = f'<hp:run charPrIDRef="{char}"><hp:t>{text}</hp:t></hp:run>' + "".join(f'<hp:run charPrIDRef="{c}"><hp:t>{t}</hp:t></hp:run>' for c, t in extra_runs)
    return f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">{runs}<hp:linesegarray><hp:lineseg textpos="0"/></hp:linesegarray></hp:p>'


def table(rows, tid="1", zorder="1"):
    """셀 값이 list 면 셀 안에 문단 여러 개 (표 4 의 'NCS 교과서' 셀)."""
    trs = []
    for r, row in enumerate(rows):
        tcs = "".join(
            f'<hp:tc name="" header="0" borderFillIDRef="2"><hp:subList id="" textDirection="HORIZONTAL">{"".join(para(t, "17") for t in (cell if isinstance(cell, list) else [cell]))}</hp:subList>'
            f'<hp:cellAddr colAddr="{c}" rowAddr="{r}"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="100" height="10"/></hp:tc>'
            for c, cell in enumerate(row))
        trs.append(f"<hp:tr>{tcs}</hp:tr>")
    tbl = f'<hp:tbl id="{tid}" zOrder="{zorder}" rowCnt="{len(rows)}" colCnt="{len(rows[0])}" borderFillIDRef="7">' + "".join(trs) + "</hp:tbl>"
    return f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13">{tbl}</hp:run><hp:run charPrIDRef="13"><hp:t></hp:t></hp:run><hp:linesegarray><hp:lineseg textpos="0"/></hp:linesegarray></hp:p>'   # 실제 문서의 표 문단도 캐시를 가진다


def blank(para_pr="25", char="22"):
    """글 run 이 없는 빈 문단 — 실제 문서의 간격 문단(5절 paraPr 25 / 제3장 paraPr 10)."""
    return f'<hp:p id="0" paraPrIDRef="{para_pr}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="{char}"/><hp:linesegarray><hp:lineseg textpos="0"/></hp:linesegarray></hp:p>'


def ctrl_para(before, after):
    """글 run 사이에 hp:ctrl run(각주 자리)이 있는 문단 — 2절 소결 마지막 문단의 모양. set_text 를 쓰면 각주가 끝으로 밀리므로 2단계는 이 문단을 손대지 않는다."""
    return (f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13"><hp:t>{before}</hp:t></hp:run>'
            f'<hp:run charPrIDRef="21"><hp:ctrl/></hp:run><hp:run charPrIDRef="13"><hp:t>{after}</hp:t></hp:run></hp:p>')


CH2_HEADINGS = ("제2장 연구 방법", "1. 국내 반도체고등학교 교과서와 한국산업인력공단 NCS 교과서 분석", "2. 해외 기술 고등학교 교과서 비교·분석", "5. 키워드 기반 문서 분류·분석 방법론")
OLD_METHODS_TOC = (" 1) 시스템 구성과 데이터 흐름 ", " 2) 키워드 정의와 정규화", " 3) 문헌수집과 전처리 ", " 4) 콘텐츠 구조 분해 ", " 5) 위치 정합: 행번호의 페이지 사상 ", " 6) 키워드 매칭과 분류 ", " 7) 결과 산출; Excel 내보내기", " 8) 검증과 한계 ")
NCS_TOC_SUB = (" 1) 안전 등 사고, 부상, 질병 관련 30개 키워드 분석  ", "  (1) 키워드 분석", " 2) 반도체 분야별 키워드 분석", " 3) 안전보건 등급별 키워드 분석", " 4) 소결")


def chapter2_fixture_body():
    """제2장 본문 — 1절(표 4)·2절 제목·5절(도입·표 5·표 6·설명 4문단·등급 목록), 2026-09-15 정본의 모양."""
    grade_list = [para("안전보건 수준은 각 출현이 속한 페이지 또는 페이지 구역의 내용을 기준으로 세 등급으로 나누었다. "), para("- 등급 1"), para("관련 내용이 없거나 매우 부족한 경우"), para("- 등급 2"),
                  para("위험을 언급하지만 예방 방법이 충분하지 않은 경우"), para("- 등급 3"), para("위험과 함께 구체적인 예방 방법이나 대응 절차가 제시된 경우이다."),
                  para("이 등급은 문장 하나의 완성도를 직접 평가한 값이 아니라 해당 출현에 연결된 페이지·구역의 판정값이다.")]
    return "".join([
        para(CH2_HEADINGS[0]), blank("10", "13"), para(CH2_HEADINGS[1]), blank("10", "13"), para("국내 반도체고등학교 교과서(9종)와 한국산업인력공단 NCS 교과서(86종)에서 안전보건 관련 내용을 분석하였다(표 4 참조)."), blank("10", "13"),
        para("표 4. 국내 반도체고등학교 교과서(9종)와 한국산업인력공단 NCS 교과서(85종)"),
        table([["구분", "교과서 이름/종류"], ["국내 반도체고등학교 교과서", ["반도체기초기술1 (크리아트)", "반도체 박막확산 (에이치앤지)"]], ["한국산업인력공단 NCS 교과서", ["반도체개발 30종", "반도체제조 14종", "반도체장비 19종", "반도체재료 22종"]]], tid="4"),
        blank("10", "13"), para(CH2_HEADINGS[2]), para("해외 사례 본문 — 바뀌면 안 된다 85종"), blank("10", "13"),
        para(CH2_HEADINGS[3], char="12"), para("반도체 교과서와 NCS 자료에 안전보건 관련 내용이 얼마나, 어떤 맥락으로 포함되어 있는지 일관된 기준으로 확인하기 위한 절차이다."), blank(),
        para("표 5. 키워드 기반 분석의 이해하기 쉬운 6단계"),
        table([["단계", "무엇을 하는가", "주요 결과"]] + [[f"{i}. 단계", "옛 설명", "옛 결과"] for i in range(1, 7)], tid="5"), blank(), blank(),
        para("표 6. 검색과 등급 판정 기준"),
        table([["구분", "쉽게 말하면", "예시·주의사항"], ["검색 표현", "옛", "옛"], ["문맥 확인", "옛", "옛"], ["등급 1", "옛", "옛"], ["등급 2", "옛", "옛"], ["등급 3", "옛", "옛"]], tid="6"), blank(), blank(),
        para("분석 자료는 반도체고등학교 교과서와 NCS 학습자료의 본문이다. "), para("먼저 파일을 읽어 문장·표·제목을 구분하고 … 12,875건 85종"), blank(),
        para("파일과 검색어는 한글의 띄어쓰기나 컴퓨터 저장 방식이 달라도 같은 말로 인식되도록 정리한 뒤 검색하였다."), blank(),
        para("검색 결과는 단순히 단어가 나왔다는 사실만 세지 않고, 해당 표현이 실제 안전보건 내용으로 사용되었는지 문맥을 확인하였다."), blank(),
        *grade_list, blank(),
    ])


def ncs_tail_fixture():
    """2절 꼬리 — 그림 4 캡션 뒤: 빈 문단, ' 4) 소결', 소결 문단 3개(마지막은 각주 ctrl run 포함)."""
    return "".join([blank("10", "13"), para(" 4) 소결"), blank("10", "13"), para("본 연구는 반도체 기술 고등학교 교과서의 안전보건교육 내용을 체계적으로 분석하여 구조적 한계를 확인하였다."), blank("10", "13"),
                    para("반도체고등학교의 안전보건교육이 양적으로 일부 포함되어 있음에도 한계를 가지고 있음을 보여준다."), blank("10", "13"),
                    ctrl_para("본 연구 결과는 반도체산업 특성을 반영한 체계적이고 실천 중심의 안전보건교육 교과서 개발이 필요함을 시사한다.", " 각주 뒤 글.")])


def pic(item):
    return (f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13">'
            f'<hp:pic id="9" zOrder="1"><hc:img binaryItemIDRef="{item}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/></hp:pic></hp:run><hp:linesegarray><hp:lineseg textpos="0"/></hp:linesegarray></hp:p>')   # 그림 문단도 캐시를 가진다


def png_bytes(width, height):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def bmp_bytes(width, height):
    row = (width * 3 + 3) // 4 * 4
    size = 54 + row * height
    header = b"BM" + struct.pack("<IHHI", size, 0, 0, 54) + struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, row * height, 2835, 2835, 0, 0)
    return header + b"\xff" * (row * height)


FIXTURE_SECTION_TITLES = ["제3장 연구 결과", HR.HEADINGS["textbook"][0], HR.HEADINGS["ncs"][0], HR.HEADINGS["cases"][0], HR.HEADINGS["cases"][1]]


def build_fixture_hwpx(path, body_paragraphs, chapter2=True):
    """목차(제목 중복) + 본문. body_paragraphs 는 절 이름 → 문단 XML 목록. chapter2=True 면 제2장 목차(5절 구고 소제목 8개)·2절 목차 소항목·제2장 본문(표 4·5절)도 넣는다 — 2단계가 손대는 곳."""
    toc = "".join(para(t) for t in CH2_HEADINGS[:3]) + para(CH2_HEADINGS[3] + " ") + "".join(para(t) for t in OLD_METHODS_TOC) if chapter2 else ""
    for t in FIXTURE_SECTION_TITLES:
        toc += para(t)
        if chapter2 and t == HR.HEADINGS["textbook"][0]:
            toc += para(" 4) 소결")                                                   # 1절 목차에도 ' 4) 소결' 이 있다 — 2절 블록 탐지가 헷갈리면 안 된다
        if chapter2 and t == HR.HEADINGS["ncs"][0]:
            toc += "".join(para(t2) for t2 in NCS_TOC_SUB)
    body = (chapter2_fixture_body() if chapter2 else "") + para("제3장 연구 결과")
    for name in ("textbook", "ncs", "cases"):
        body += para(HR.HEADINGS[name][0]) + "".join(body_paragraphs.get(name, []))
    body += para(HR.HEADINGS["cases"][1]) + para("4절 본문 — 바뀌면 안 된다 12,875건")
    xml = f'{HR.XML_DECL}<hs:sec {NS}>{para("서론 12,875건 그대로")}{toc}{body}</hs:sec>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("Contents/section0.xml", xml.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("Contents/header.xml", "<hh:head/>")
        z.writestr("BinData/image1.PNG", png_bytes(70, 39))
        z.writestr("BinData/image2.BMP", bmp_bytes(116, 75))
        z.writestr("BinData/image3.BMP", bmp_bytes(116, 72))
    return path


def fixture_facts():
    return HR.load_facts(HR.DEFAULT_SUMMARY, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)


class XmlHelperTests(unittest.TestCase):
    def test_drop_line_layout_cache_counts_only_touched_paragraphs_with_a_cache(self):
        """장부에 적힌 최상위 문단(표 셀 포함)의 hp:linesegarray 만 지우고 센다 — 캐시가 둘이면 둘 다, 캐시 없는 그림 문단은 세지 않고, 빈 장부는 아무것도 안 지운다."""
        bare = f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13"><hp:t>E</hp:t></hp:run></hp:p>'   # 캐시가 원래 없는 문단
        root = ET.fromstring(f'<hs:sec {NS}>' + para("A") + para("B") + table([["h"], ["c1"], ["c2"]]) + pic("image1") + para("D") + bare + "</hs:sec>")
        a, b, tbl, pc, d, e = list(root)
        b.append(copy.deepcopy(b.find(f"{HP}linesegarray")))                                                          # 한 문단에 캐시 둘 — findall 루프
        self.assertEqual({"paragraphs": 0, "linesegarray_removed": 0, "ledger_paragraphs": 0}, HR.drop_line_layout_cache(root, set(), set()))
        self.assertTrue(all(p.find(f".//{HP}linesegarray") is not None for p in (a, b, tbl, pc, d)))                   # 빈 장부는 무해
        got = HR.drop_line_layout_cache(root, touched={id(b), id(tbl), id(pc), id(e)}, inserted={id(d)})
        self.assertEqual({"paragraphs": 4, "linesegarray_removed": 2 + (1 + 3) + 1 + 1, "ledger_paragraphs": 5}, got)   # b 2 + 표 문단 1·셀 3 + 그림 1 + d 1; 캐시 없던 e 는 장부엔 있지만 세지 않는다
        self.assertIsNotNone(a.find(f"{HP}linesegarray"))                                                              # 손대지 않은 문단은 그대로
        self.assertIsNone(b.find(f"{HP}linesegarray")); self.assertFalse(list(tbl.iter(f"{HP}linesegarray"))); self.assertIsNone(d.find(f"{HP}linesegarray")); self.assertIsNone(pc.find(f"{HP}linesegarray"))

    def test_set_text_keeps_first_run_format_and_collapses_extra_runs(self):
        p = ET.fromstring(f'<hp:p {NS}><hp:run charPrIDRef="13"><hp:t>앞</hp:t></hp:run><hp:run charPrIDRef="9"><hp:t>뒤</hp:t></hp:run><hp:linesegarray/><hp:x/></hp:p>')
        info = HR.set_text(p, "새 글")
        runs = p.findall(HP + "run")
        self.assertEqual(1, len(runs)); self.assertEqual("13", runs[0].get("charPrIDRef")); self.assertEqual("새 글", HR.direct_text(p))
        self.assertTrue(info["format_collapsed"])
        self.assertIsNotNone(p.find(HP + "x")); self.assertIsNotNone(p.find(HP + "linesegarray"))   # 글 아닌 자식은 그대로 — 줄 배치 캐시는 실행의 drop_line_layout_cache 몫 (2026-09-17)

    def test_resize_table_clones_first_data_row_style_keeps_spacer_and_recomputes_height(self):
        xml = table([["h1", "h2"], ["a", "1"], ["b", "2"], ["", ""]])
        root = ET.fromstring(f'<hs:sec {NS}>' + xml + "</hs:sec>")
        tbl = root.find(f".//{HP}tbl")
        ET.SubElement(tbl, HP + "sz", {"width": "100", "height": "40"})
        last = tbl.findall(HP + "tr")[2]
        for tc in last.findall(HP + "tc"):
            tc.set("borderFillIDRef", "6")                                  # 원본처럼 마지막 데이터 행만 다른 테두리
        HR.resize_table(tbl, 1, 4)
        rows = HR.table_rows(tbl)
        self.assertEqual(6, len(rows)); self.assertEqual("6", tbl.get("rowCnt"))                         # 헤더 1 + 데이터 4 + 간격 1
        self.assertEqual([str(i) for i in range(6)], [r[0].find(HP + "cellAddr").get("rowAddr") for r in rows])
        self.assertEqual({"2"}, {tc.get("borderFillIDRef") for r in rows[1:5] for tc in r})              # 첫 데이터 행 서식으로 통일
        self.assertTrue(all(HR.cell_text(tc) == "" for tc in rows[-1]))                                   # 간격 행은 끝에 그대로
        self.assertEqual(str(10 * 6), tbl.find(HP + "sz").get("height"))                                  # 행 높이 합
        HR.resize_table(tbl, 1, 1)
        self.assertEqual(3, len(HR.table_rows(tbl))); self.assertEqual("3", tbl.get("rowCnt"))
        before = [(tc.get("borderFillIDRef"), tc.find(HP + "cellSpan").attrib, tc.find(HP + "cellSz").attrib) for r in HR.table_rows(tbl) for tc in r]
        HR.fill_table(tbl, [["z", "9"]], 1)
        after = [(tc.get("borderFillIDRef"), tc.find(HP + "cellSpan").attrib, tc.find(HP + "cellSz").attrib) for r in HR.table_rows(tbl) for tc in r]
        self.assertEqual(before, after)                                          # 셀 서식·병합·크기 불변
        with self.assertRaises(ValueError):
            HR.fill_table(tbl, [["x", "1"], ["y", "2"], ["z", "3"]], 1)         # 행 수 불일치는 실패


class SectionTests(unittest.TestCase):
    def test_locate_sections_skips_toc_and_bounds_each_section(self):
        with tempfile.TemporaryDirectory() as td:
            path = build_fixture_hwpx(Path(td) / "f.hwpx", {"textbook": [para("교과서 본문")], "ncs": [para("NCS 본문 1"), para("NCS 본문 2")], "cases": [para("사례 본문")]})
            raw, root, tag = HR.read_section(path)
        sections = HR.locate_sections(root)
        self.assertEqual({"textbook", "ncs", "cases"}, set(sections))
        self.assertEqual(["NCS 본문 1", "NCS 본문 2"], [HR.direct_text(p) for p in sections["ncs"].paragraphs[1:]])
        self.assertEqual(HR.HEADINGS["cases"][0], HR.direct_text(sections["cases"].paragraphs[0]))
        self.assertTrue(tag.startswith("<hs:sec ") and 'xmlns:ha=' in tag)
        with self.assertRaises(ValueError):
            HR.find_paragraph(sections["ncs"], "없는 문단")


class ErrorPathTests(unittest.TestCase):
    """ship 커버리지 감사(2026-09-14) — 조용히 지나가면 안 되는 오류 경로: 모르는 그룹, 제목 없는 문서, 없는 표·그림, 그림 중복, magick 부재, 다중 문단 셀."""

    def test_load_facts_refuses_unknown_group(self):
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        summary["corpora"]["NCS"]["groups"].append({"name": "반도체신규", "documents": 1, "pages": 3, "total": 1, "grades": {"1": 1, "2": 0, "3": 0, "unpaged": 0}})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "summary.json"; path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                HR.load_facts(path, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)
            self.assertIn("반도체신규", str(ctx.exception))

    def test_load_facts_refuses_unknown_keyword_group(self):                                      # CodeRabbit PR #16
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        summary["keywords"][0]["corpora"]["NCS"]["groups"].append({"name": "반도체신규", "documents": 1, "total": 1, "grades": {"1": 1, "2": 0, "3": 0}})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "summary.json"; path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "반도체신규"):                                 # KeyError: None 이 아니라 대응표 갱신 안내
                HR.load_facts(path, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)

    def test_locate_sections_refuses_document_without_body_chapter_heading(self):
        root = ET.fromstring(f'<hs:sec {NS}>' + para("제3장 연구 결과") + para("본문") + "</hs:sec>")      # 목차 1회뿐
        with self.assertRaises(ValueError):
            HR.locate_sections(root)

    def test_missing_table_and_picture_are_errors_and_duplicate_item_is_ambiguous(self):
        root = ET.fromstring(f'<hs:sec {NS}>' + para("표 99. 없는 표") + para("그냥 문단") + pic("image9") + pic("image9") + "</hs:sec>")
        section = HR.Section("x", 0, 4, HR.top_paragraphs(root))
        with self.assertRaises(ValueError):
            HR.find_table_after_caption(section, "표 99.")
        with self.assertRaises(ValueError):
            HR.find_table_by_first_cell(section, "표 99.")
        with self.assertRaises(ValueError):
            HR.find_picture(section, "그림 9.", None)
        with self.assertRaises(ValueError) as ctx:
            HR.find_picture(section, None, "image9")
        self.assertIn("2개", str(ctx.exception))

    def test_render_refuses_without_magick(self):
        from unittest import mock
        with mock.patch.object(HR.shutil, "which", lambda name: None), self.assertRaises(RuntimeError) as ctx:
            HR.render_svg("<svg/>", "PNG", 10, 10)
        self.assertIn("magick", str(ctx.exception))

    def test_small_guards_raise_clear_errors(self):
        with self.assertRaises(ValueError):
            HR.set_text(ET.fromstring(f'<hp:p {NS}/>'), "x")                                     # run 없음
        tbl = ET.fromstring(f'<hs:sec {NS}>' + table([["h1", "h2"]]) + "</hs:sec>").find(f".//{HP}tbl")
        with self.assertRaises(ValueError):
            HR.resize_table(tbl, 1, 2)                                                          # 데이터 행 없음
        tbl3 = ET.fromstring(f'<hs:sec {NS}>' + table([["h1", "h2", "h3"], ["a", "1", "2"]]) + "</hs:sec>").find(f".//{HP}tbl")
        with self.assertRaises(ValueError):
            HR.fill_table(tbl3, [["a", "1"]], 1)                                                # 열 수 불일치
        with self.assertRaises(ValueError):
            HR.image_dimensions(b"GIF89a....")
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.hwpx"
            with zipfile.ZipFile(bad, "w") as z:
                z.writestr("Contents/section0.xml", "<x/>")
            with self.assertRaises(ValueError):
                HR.read_section(bad)                                                            # hs:sec 루트 없음
        self.assertEqual({"guideline", "definition", "property"}, set(HR.FP_KIND_LABEL))
        cases = json.loads(HR.DEFAULT_CASES.read_text(encoding="utf-8"))
        cases["pages"][-1]["kind"] = "mystery"
        with tempfile.TemporaryDirectory() as td:
            cpath = Path(td) / "cases.json"; cpath.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                HR.load_facts(HR.DEFAULT_SUMMARY, cpath, HR.DEFAULT_RECOUNT)                     # 모르는 오탐 유형
            with self.assertRaises(FileNotFoundError):
                HR.load_facts(HR.DEFAULT_SUMMARY, HR.DEFAULT_CASES, Path(td) / "none.json")     # recount summary 없음 → 0 으로 침묵하지 않는다

    def test_docs_directory_itself_is_refused(self):
        self.assertTrue(HR._under_tracked_docs(HR.HERE / "docs")); self.assertTrue(HR._under_tracked_docs(HR.HERE / "docs" / "x.html"))
        self.assertFalse(HR._under_tracked_docs(HR.HERE / "data")); self.assertFalse(HR._under_tracked_docs(HR.HERE / "docs2"))
        with tempfile.TemporaryDirectory() as td:
            src = build_fixture_hwpx(Path(td) / "s.hwpx", {})
            with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
                HR.main(["--hwpx", str(src), "--no-render", "--text-review-dir", str(HR.HERE / "docs")])

    def test_serialize_keeps_namespaces_declared_on_descendants(self):
        xml = (f'{HR.XML_DECL}<hs:sec {NS}>' + para("본문") + '<hp:p><hp:run charPrIDRef="1"><x:extra xmlns:x="urn:x"/></hp:run></hp:p></hs:sec>')
        root_tag = re.search(r"<hs:sec\b[^>]*>", xml).group(0)
        root = ET.fromstring(xml.encode("utf-8"))
        data = HR.serialize_section(root, root_tag)
        reparsed = ET.fromstring(data)                                                    # unbound prefix 면 여기서 죽는다
        self.assertIsNotNone(reparsed.find(".//{urn:x}extra"))
        self.assertTrue(data.decode("utf-8").startswith(HR.XML_DECL + "<hs:sec "))

    def test_set_text_leaves_the_line_layout_cache_to_the_run(self):
        """set_text 는 글만 바꾼다 — 줄 배치 캐시는 실행의 drop_line_layout_cache 가 장부 단위로 지운다(한 줄만 남기던 이전 정리는 캐시를 믿는 뷰어(Polaris)가 긴 글을 한 줄에 눌러 그리게 했다, 2026-09-17)."""
        p = ET.fromstring(f'<hp:p {NS}><hp:run charPrIDRef="13"><hp:t>옛 글</hp:t></hp:run><hp:linesegarray><hp:lineseg textpos="0" vertpos="1"/><hp:lineseg textpos="617" vertpos="2"/></hp:linesegarray></hp:p>')
        HR.set_text(p, "새")
        self.assertEqual(2, len(p.findall(f"{HP}linesegarray/{HP}lineseg"))); self.assertEqual("새", HR.direct_text(p))
        sec = ET.fromstring(f'<hs:sec {NS}></hs:sec>'); sec.append(p)
        self.assertEqual({"paragraphs": 1, "linesegarray_removed": 1, "ledger_paragraphs": 1}, HR.drop_line_layout_cache(sec, {id(p)}, set()))   # 실행의 규칙이 지운다
        self.assertIsNone(p.find(f"{HP}linesegarray"))

    def test_write_hwpx_uses_exclusive_temp_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as td:
            src = build_fixture_hwpx(Path(td) / "s.hwpx", {})
            out = Path(td) / "o.hwpx"
            HR.write_hwpx(src, out, HR.read_section(src)[0], {})
            self.assertEqual([out.name, src.name], sorted(p.name for p in Path(td).iterdir()))          # .tmp 잔재 없음
            (Path(td) / "not.hwpx").write_bytes(b"junk")
            with self.assertRaises(zipfile.BadZipFile):
                HR.write_hwpx(Path(td) / "not.hwpx", Path(td) / "o2.hwpx", b"", {})
            self.assertFalse((Path(td) / "o2.hwpx").exists()); self.assertEqual([], [p.name for p in Path(td).glob("*.tmp")])   # 실패해도 임시 파일이 남지 않는다

    def test_load_facts_refuses_unguarded_summary_and_missing_keyword_groups(self):
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            forced = copy.deepcopy(summary); forced["meta"]["run"]["expected"] = None
            (Path(td) / "forced.json").write_text(json.dumps(forced, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                HR.load_facts(Path(td) / "forced.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)              # --force 실행·변형 실행은 보고서에 못 쓴다
            old = copy.deepcopy(summary); old["keywords"][0]["corpora"]["NCS"].pop("groups")
            (Path(td) / "old.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                HR.load_facts(Path(td) / "old.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)                 # 키워드×그룹이 없는 옛 정본은 0 으로 채우지 않는다

    def test_set_cell_collapses_multi_paragraph_cell(self):
        cell = ET.fromstring(f'<hp:tc {NS}><hp:subList>{para("첫 줄")}{para("둘째 줄")}</hp:subList><hp:cellAddr colAddr="0" rowAddr="0"/></hp:tc>')
        HR.set_cell(cell, "하나")
        self.assertEqual(1, len(HR.cell_paragraphs(cell))); self.assertEqual("하나", HR.cell_text(cell))
        self.assertIsNotNone(cell.find(HP + "cellAddr"))


class AuditTests(unittest.TestCase):
    def test_audit_flags_stale_numbers_and_accepts_canonical_ones(self):
        f = fixture_facts()
        self.assertEqual([], HR.audit_numbers([f"총 {HR.fmt(f.ncs.total)}건, 등급 3 {HR.pct(f.ncs.grades[3], f.ncs.total)}, 33쪽, 2014년"], f))
        self.assertEqual(["12,875", "4,259", "4,259건"], HR.audit_numbers(["‘안전’ 4,259건 중 12,875"], f))          # "4,259건" 은 폐기 문구 목록에도 걸린다 (2단계 STALE_PATTERNS)

    def test_facts_from_canonical_files(self):
        f = fixture_facts()
        self.assertEqual((86, 9), (f.ncs.documents, f.school.documents))
        self.assertEqual(f.ncs.total, sum(a["total"] for a in f.ncs.areas.values()))
        self.assertEqual(2055, sum(a["pages"] for a in f.school.areas.values()))                      # 교과서 4개 분야 쪽수 합 = 2,055
        self.assertEqual({"개발": 3, "제조": 4, "장비": 1, "재료": 1}, {a: v["documents"] for a, v in f.school.areas.items()})
        self.assertEqual(f.ncs.keywords["안전"]["total"], sum(a["total"] for a in f.ncs.keywords["안전"]["areas"].values()))
        self.assertEqual((13, 5, 3, 1, 2, 10), (f.cases.flagged, f.cases.books, f.cases.narrative, f.cases.industrial_events, f.cases.industrial_books, f.cases.false_positive))
        self.assertEqual("안전", f.ncs.ranked()[0][0])


class TemplateTests(unittest.TestCase):
    def test_conditions_branch_both_ways(self):
        f = fixture_facts()
        psm = f.ncs.keywords["공정안전관리"]
        base = {k: (v, c) for k, v, c in HR.ncs_paragraphs(f)}
        self.assertEqual(psm["grades"][3] == psm["total"], base["한편 ‘공정안전관리’는 총"][1]["psm_all_grade3"])
        flipped = copy.deepcopy(f)
        g = flipped.ncs.keywords["공정안전관리"]["grades"]; g[3] = flipped.ncs.keywords["공정안전관리"]["total"]; g[1] = g[2] = 0
        ppe = flipped.ncs.keywords["보호구"]["grades"]; ppe[1] = flipped.ncs.keywords["보호구"]["total"]; ppe[2] = ppe[3] = 0
        alt = {k: (v, c) for k, v, c in HR.ncs_paragraphs(flipped)}
        self.assertIn("모두 등급 3", alt["한편 ‘공정안전관리’는 총"][0]); self.assertTrue(alt["한편 ‘공정안전관리’는 총"][1]["psm_all_grade3"])
        self.assertNotIn("모두 등급 3", base["한편 ‘공정안전관리’는 총"][0]) if psm["grades"][3] != psm["total"] else None
        self.assertNotIn("60%를 넘었다", alt["‘보호구’는"][0]); self.assertFalse(alt["‘보호구’는"][1]["ppe_over_60pct"])
        self.assertIn("60%를 넘었다", base["‘보호구’는"][0])

    def test_zero_claims_track_data(self):
        f = fixture_facts()
        base = {k: v for k, v, _ in HR.textbook_paragraphs(f)}
        self.assertEqual(0, f.school.keywords["직업병"]["total"]); self.assertEqual(0, f.school.keywords["추락"]["total"])
        self.assertIn("‘직업병’은 전혀 검출되지 않았고 ‘물질안전보건자료’는 전혀 검출되지 않았고", base["따라서 제조 분야는 안전보건교육이 가장 적극적으로"])
        flipped = copy.deepcopy(f)
        flipped.school.keywords["직업병"]["total"] = 4; flipped.school.keywords["추락"]["total"] = 2
        flipped.cases.textbook_cases = 3
        alt = {k: (v, c) for k, v, c in HR.textbook_paragraphs(flipped)}
        self.assertIn("‘직업병’은 4건에 그쳤고", alt["따라서 제조 분야는 안전보건교육이 가장 적극적으로"][0])
        self.assertEqual(["물질안전보건자료"], alt["따라서 제조 분야는 안전보건교육이 가장 적극적으로"][1]["zero_keywords_in_sentence"])
        self.assertIn("‘추락’은 2건에 그쳤고", alt["따라서 장비 분야에서는 전기, 기계, 압력"][0])
        self.assertIn("3쪽에서만 확인되었다", alt["또한 공정안전관리, 직업병, 물질안전보건자료"][0])
        self.assertIn("3쪽에서만 발견되었다", alt["9권의 교과서에서 구체적인 사고"][0])

    def test_svg_has_all_values(self):
        f = fixture_facts()
        for spec in HR.figure_specs(f):
            svg = spec["svg"](1160, 750)
            if spec["label"] == "그림 3":
                for a in f.ncs.areas.values():
                    for g in (1, 2, 3):
                        self.assertIn(HR.fmt(a["grades"][g]) + "건", svg)
            else:
                corpus = f.school if spec["label"] == "그림 2" else f.ncs
                for g in (1, 2, 3):
                    self.assertIn(f"{HR.fmt(corpus.grades[g])}건 ({HR.pct(corpus.grades[g], corpus.total)})", svg, spec["label"])

    def test_korean_particles(self):
        self.assertEqual(("정의로", "지침으로", "관리와", "지침과", "PSM로", "직업병은", "자료는"), (HR.ro("정의"), HR.ro("지침"), HR.wa("관리"), HR.wa("지침"), HR.ro("PSM"), HR.eun("직업병"), HR.eun("자료")))
        self.assertEqual("『반도체 장비 안전관리』와", HR.wa("『반도체 장비 안전관리』"))

    def test_templates_branch_on_data(self):
        f = fixture_facts()
        texts = {k: v for k, v, _ in HR.ncs_paragraphs(f)}
        psm = f.ncs.keywords["공정안전관리"]
        all3 = psm["grades"][3] == psm["total"]
        self.assertEqual(all3, "모두 등급 3" in texts["한편 ‘공정안전관리’는 총"])
        ppe = f.ncs.keywords["보호구"]
        self.assertEqual((ppe["grades"][2] + ppe["grades"][3]) / ppe["total"] >= 0.6, "60%를 넘었다" in texts["‘보호구’는"])
        self.assertIn(HR.fmt(f.ncs.keywords["안전"]["total"]), texts["교과서의 전체 키워드 중 ‘안전’이"])
        self.assertNotIn("643", texts["화학물질 관련 키워드는"]); self.assertIn("독립 집계", texts["화학물질 관련 키워드는"])   # D3
        school = {k: v for k, v, _ in HR.textbook_paragraphs(f)}
        self.assertIn("전혀 검출되지 않았고", school["따라서 제조 분야는 안전보건교육이 가장 적극적으로"])
        cases = {k: v for k, v, _ in HR.case_paragraphs(f)}
        self.assertIn("13쪽", cases["본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를"])
        for name, template in HR.PARAGRAPH_TEMPLATES.items():
            for prefix, text, _ in template(f):
                self.assertEqual([], HR.audit_numbers([text], f), (name, prefix))                    # 템플릿이 내는 숫자는 전부 정본 값


class AdversarialReviewTests(unittest.TestCase):
    """Claude 적대적 리뷰(2026-09-14) F1~F9 — 서술 분기·정본 결속·감사 범위·입력 검증·SVG escape·중복 ZIP 항목."""

    def test_workenv_paragraph_compares_each_keyword_with_the_overall_share(self):        # F1
        f = fixture_facts()
        n = f.ncs
        overall = n.grades[3] / n.total
        text, cond = {k: (v, c) for k, v, c in HR.ncs_paragraphs(f)}["또한 ‘작업환경’은 총"]
        for name in ("작업환경", "중독"):
            kw = n.keywords[name]
            self.assertEqual(HR._share_rel(kw["grades"][3] / kw["total"], overall), cond["g3_vs_overall"][name])
        rels = set(cond["g3_vs_overall"].values())
        self.assertEqual("높" in rels and len(rels) == 1, "수준 이상" in text)                 # "수준 이상" 은 둘 다 평균을 웃돌 때만
        if rels == {"비슷"}:
            self.assertIn("과 비슷한 수준", text); self.assertIn("뒤지지 않는", text)
        first = {k: v for k, v, _ in HR.ncs_paragraphs(f)}["‘작업환경’은"]
        self.assertEqual("낮" in rels, "보다 낮았다" in first)
        def flipped(w, p):
            g = copy.deepcopy(f)
            for name, share in (("작업환경", w), ("중독", p)):
                kw = g.ncs.keywords[name]; kw["grades"][3] = int(kw["total"] * share); kw["grades"][1] = kw["total"] - kw["grades"][3]; kw["grades"][2] = 0
            return {k: (v, c) for k, v, c in HR.ncs_paragraphs(g)}["또한 ‘작업환경’은 총"]
        high, _ = flipped(1.0, 1.0)
        self.assertIn("수준 이상", high); self.assertIn("상대적으로 충실한 편", high)
        low, lc = flipped(0.0, 0.0)
        self.assertIn("에 못 미치는", low); self.assertIn("충실하다고 보기는 어렵다", low); self.assertNotIn("수준 이상", low)
        self.assertEqual({"작업환경": "낮", "중독": "낮"}, lc["g3_vs_overall"])
        mixed, mc = flipped(1.0, 0.0)
        self.assertIn("‘작업환경’은 전체 평균", mixed); self.assertIn("‘중독’은 그에 못 미치는", mixed)
        self.assertEqual({"작업환경": "높", "중독": "낮"}, mc["g3_vs_overall"])

    def test_share_rel_uses_the_tolerance(self):
        self.assertEqual(("비슷", "비슷", "높", "낮"), (HR._share_rel(0.216, 0.219), HR._share_rel(0.241, 0.219), HR._share_rel(0.26, 0.219), HR._share_rel(0.18, 0.219)))

    def test_grade2_and_safety_rank_claims_branch(self):                                    # F2
        f = fixture_facts()
        base = {k: (v, c) for k, v, c in HR.ncs_paragraphs(f)}
        self.assertEqual(HR._grade_max(f.ncs.grades) == 2, "등급 2의 비중이 가장 높다는 점" in base["등급 2는 안전보건 관련 키워드가 확인되지만"][0])
        self.assertEqual(f.ncs.ranked()[0][0] == "안전", "검출 건수가 가장 많았다" in base["교과서의 전체 키워드 중 ‘안전’이"][0])
        g = copy.deepcopy(f)
        g.ncs.grades = {1: g.ncs.total - 20, 2: 10, 3: 10}
        g.ncs.keywords["안전"]["grades"] = {1: 5, 2: 5, 3: g.ncs.keywords["안전"]["total"] - 10}
        g.ncs.keywords["위험"]["total"] = g.ncs.keywords["안전"]["total"] + 1
        alt = {k: (v, c) for k, v, c in HR.ncs_paragraphs(g)}
        t, c = alt["등급 2는 안전보건 관련 키워드가 확인되지만"]
        self.assertNotIn("가장 높다는 점", t); self.assertIn("세 등급 중 2번째", t); self.assertEqual((1, 2), (c["largest_grade"], c["grade2_rank"]))
        t, c = alt["교과서의 전체 키워드 중 ‘안전’이"]
        self.assertIn("2번째로 많았다", t); self.assertIn("등급 3이", t); self.assertNotIn("상대적으로 낮았다", t); self.assertNotIn("등급 2도", t)
        self.assertEqual((2, 3), (c["safety_rank"], c["safety_top_grade"]))
        self.assertEqual([], HR.audit_numbers([t], g))

    def test_equipment_case_sentence_branches_on_top_book_area_and_false_positives(self):   # F2
        f = fixture_facts()
        base = {k: (v, c) for k, v, c in HR.ncs_paragraphs(f)}["반도체 장비 분야는 총"]
        self.assertIn(f"『{f.cases.top_book}』 한 권에 몰려 있어", base[0]); self.assertTrue(base[1]["equipment_top_book"])
        g = copy.deepcopy(f)
        g.cases.top_book = next(p["title"] for p in g.cases.pages if p["area"] != "장비")
        alt = {k: (v, c) for k, v, c in HR.ncs_paragraphs(g)}["반도체 장비 분야는 총"]
        self.assertNotIn("『", alt[0]); self.assertFalse(alt[1]["equipment_top_book"])
        h = copy.deepcopy(f)
        for p in h.cases.pages:
            if p["area"] == "장비":
                p["verdict"] = "case_other"
        alt = {k: (v, c) for k, v, c in HR.ncs_paragraphs(h)}["반도체 장비 분야는 총"]
        self.assertNotIn("나머지", alt[0]); self.assertNotIn(" 로,", alt[0]); self.assertIn("모두 실제 사고 서술", alt[0])
        i = copy.deepcopy(f)
        for p in i.cases.pages:
            if p["area"] == "장비":
                p["verdict"] = "false_positive"; p["kind"] = "guideline"
        alt = {k: (v, c) for k, v, c in HR.ncs_paragraphs(i)}["반도체 장비 분야는 총"]
        self.assertIn("실제 사고 서술은 없고", alt[0]); self.assertEqual(0, alt[1]["equipment_narrative_pages"])

    def test_provenance_comes_from_the_summary_run(self):                                   # F3
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            later = copy.deepcopy(summary); later["meta"]["run"]["generated_at"] = "2030-01-02T03:04:05+09:00"
            (Path(td) / "later.json").write_text(json.dumps(later, ensure_ascii=False), encoding="utf-8")
            f = HR.load_facts(Path(td) / "later.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)
            texts = [t for template in HR.PARAGRAPH_TEMPLATES.values() for _, t, _ in template(f)]
            self.assertTrue(any("2030-01-02 정본 재검산(의미 표현 사전 v2" in t for t in texts))
            self.assertFalse(any("2026-09-14" in t for t in texts))                                   # 날짜 리터럴 없음
            self.assertTrue(any("2030-01-02 정본, 의미 표현 사전 v2" in t for t in texts))
            other = copy.deepcopy(summary); other["meta"]["run"]["dictionary"] = "v1fix"
            (Path(td) / "other.json").write_text(json.dumps(other, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "v1fix"):
                HR.load_facts(Path(td) / "other.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)               # 정본 사전이 아니면 거부
            undated = copy.deepcopy(summary); undated["meta"]["run"].pop("generated_at")
            (Path(td) / "undated.json").write_text(json.dumps(undated, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "generated_at"):
                HR.load_facts(Path(td) / "undated.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)
        try:
            import semantic_keyword_recount as SKR
        except ImportError:
            self.skipTest("openpyxl 없음")
        self.assertEqual(SKR.EXPECTED["dictionary"], HR.CANONICAL_DICTIONARY)

    def test_audit_reads_nested_paragraphs_and_keyword_count_is_a_fact(self):               # F5
        inner = para("메모 안의 옛 수치 12,875건")
        outer = f'<hp:p {NS} paraPrIDRef="0"><hp:run charPrIDRef="0"><hp:ctrl><hp:fieldBegin><hp:subList>{inner}</hp:subList></hp:fieldBegin></hp:ctrl><hp:t>본문 1,207건</hp:t></hp:run></hp:p>'
        section = HR.Section("ncs", 0, 1, [ET.fromstring(outer)])
        texts = HR.section_texts(section)
        self.assertTrue(any("12,875" in t for t in texts)); self.assertTrue(any("1,207" in t for t in texts))
        f = fixture_facts()
        self.assertNotIn("30", HR.ALLOWED_TOKENS)
        self.assertIn("keywords(count)", f.value_index()[str(len(f.ncs.order))])

    def test_load_facts_validates_verdicts_and_requires_group_pages(self):                  # F7
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8")); cases = json.loads(HR.DEFAULT_CASES.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            typo = copy.deepcopy(cases); typo["pages"][0]["verdict"] = "case_othr"
            (Path(td) / "typo.json").write_text(json.dumps(typo, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "case_othr"):
                HR.load_facts(HR.DEFAULT_SUMMARY, Path(td) / "typo.json", HR.DEFAULT_RECOUNT)
            nopages = copy.deepcopy(summary); nopages["corpora"]["NCS"]["groups"][0].pop("pages")
            (Path(td) / "nopages.json").write_text(json.dumps(nopages, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pages"):
                HR.load_facts(Path(td) / "nopages.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)

    def test_locate_sections_reports_an_end_heading_before_its_start(self):                 # F7
        h = HR.HEADINGS
        xml = f'{HR.XML_DECL}<hs:sec {NS}>' + "".join(para(t) for t in FIXTURE_SECTION_TITLES) + para("제3장 연구 결과") + para(h["textbook"][0]) + para(h["cases"][0]) + para(h["ncs"][0]) + para(h["cases"][1]) + "</hs:sec>"
        with self.assertRaisesRegex(ValueError, "시작 뒤에 없습니다"):
            HR.locate_sections(ET.fromstring(xml))

    def test_svg_text_is_escaped(self):                                                     # F8
        self.assertIn("a&lt;b&gt; &amp; c", HR._svg_text(0, 0, "a<b> & c"))

    def test_write_hwpx_keeps_duplicate_zip_entries_apart(self):                            # F9
        import warnings
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td) / "src.hwpx", Path(td) / "out.hwpx"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with zipfile.ZipFile(src, "w") as z:
                    z.writestr("Contents/section0.xml", b"<a/>"); z.writestr("BinData/dup.bin", b"one"); z.writestr("BinData/dup.bin", b"two")
                HR.write_hwpx(src, out, b"<b/>", {})
            with zipfile.ZipFile(out) as z:
                dups = [i for i in z.infolist() if i.filename == "BinData/dup.bin"]
                self.assertEqual([b"one", b"two"], [z.read(i) for i in dups])
                self.assertEqual(b"<b/>", z.read("Contents/section0.xml"))


class RealPageBasisTests(unittest.TestCase):
    """occurrence-real-pages: 정본의 meta.page_basis 를 읽어 2·3절 쪽수 문구를 가르고, 산출물 이름은 정본 실행일을 따른다."""

    def test_load_facts_requires_page_basis_and_templates_branch_on_it(self):
        f = fixture_facts()
        self.assertEqual({"NCS": "real", "교과서": "marker"}, f.page_basis)
        ncs = {k: v for k, v, _ in HR.ncs_paragraphs(f)}; cases = {k: v for k, v, _ in HR.case_paragraphs(f)}; school = {k: v for k, v, _ in HR.textbook_paragraphs(f)}
        self.assertIn("PDF 쪽수", ncs["NCS 기반 반도체 자료를 대상으로"]); self.assertNotIn("쪽 표식 최댓값 합", ncs["NCS 기반 반도체 자료를 대상으로"])
        self.assertIn("실제 PDF 쪽", ncs["주: 단위: 건."])
        self.assertIn("모두 실제 PDF 쪽 기준", cases["본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를"])
        self.assertIn("쪽 표식 최댓값", school["본 연구에서는 9권의 반도체 교과서를"])                       # 교과서는 표식 기준 그대로
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            marker = copy.deepcopy(summary); marker["meta"]["page_basis"] = {"NCS": "marker", "교과서": "marker"}
            (Path(td) / "marker.json").write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
            g = HR.load_facts(Path(td) / "marker.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)
            ncs_m = {k: v for k, v, _ in HR.ncs_paragraphs(g)}; cases_m = {k: v for k, v, _ in HR.case_paragraphs(g)}
            self.assertIn("쪽 표식 최댓값 합", ncs_m["NCS 기반 반도체 자료를 대상으로"]); self.assertIn("마크다운 쪽 표식 최댓값", cases_m["본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를"])
            old = copy.deepcopy(summary); old["meta"].pop("page_basis")
            (Path(td) / "old.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "page_basis"):
                HR.load_facts(Path(td) / "old.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)

    def test_output_names_follow_the_run_date(self):
        f = fixture_facts()
        day = str(f.run["generated_at"])[:10].replace("-", "")
        self.assertEqual(f"반도체 기초보고서_{day}_정본.hwpx", HR.default_out_path(f).name); self.assertEqual(f"hwpx_results_refresh_{day}.json", HR.default_diff_path(f).name)
        self.assertTrue(HR._under_tracked_docs(HR.default_diff_path(f))); self.assertFalse(HR._under_tracked_docs(HR.default_out_path(f)))

    def test_load_facts_rejects_unknown_page_basis_and_marker_note_keeps_old_wording(self):
        """출고 전 커버리지 감사 (2026-09-15): page_basis 가 dict 가 아니거나 NCS 값이 real/marker 밖이면 거부; marker 정본에서는 '주' 문단이 옛 문구, 조건 기록은 page_basis 값."""
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            for name, value in (("bogus", {"NCS": "pdf", "교과서": "marker"}), ("notdict", "real"), ("nokey", {"교과서": "marker"})):
                broken = copy.deepcopy(summary); broken["meta"]["page_basis"] = value
                (Path(td) / f"{name}.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "page_basis", msg=name):
                    HR.load_facts(Path(td) / f"{name}.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)
            marker = copy.deepcopy(summary); marker["meta"]["page_basis"] = {"NCS": "marker", "교과서": "marker"}
            (Path(td) / "marker.json").write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
            g = HR.load_facts(Path(td) / "marker.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)
            ncs_m = {k: v for k, v, _ in HR.ncs_paragraphs(g)}
            self.assertIn("등급은 출현이 놓인 페이지의 판정값을 출현별로 연결한 값임.", ncs_m["주: 단위: 건."]); self.assertNotIn("줄→쪽 대응", ncs_m["주: 단위: 건."])
            self.assertEqual({"page_basis": "marker", "marker_books": 2}, next(c for k, _, c in HR.ncs_paragraphs(g) if k == "NCS 기반 반도체 자료를 대상으로"))
            self.assertEqual({"page_basis": "real", "marker_books": 2}, next(c for k, _, c in HR.ncs_paragraphs(fixture_facts()) if k == "NCS 기반 반도체 자료를 대상으로"))
            self.assertEqual(HR.run_day(fixture_facts()), HR.run_day(g))                                                        # 산출물 이름은 page_basis 와 무관 — 실행일만


    def test_page_basis_branches_are_recorded_in_conditions_and_render_defaults_follow_the_run_day(self):   # 리뷰(maintainability·testing)
        """page_basis 로 갈리는 문단 셋(2절 도입·'주'·3절 도입) 모두 conditions 에 page_basis 를 남긴다; 렌더 실행의 기본 --out/--diff-out 은 정본 실행일 이름이다; 잘못된 page_basis 는 값을 말하며 거부."""
        f = fixture_facts(); self.assertTrue(f.ncs_real_pages)
        for key in ("NCS 기반 반도체 자료를 대상으로", "주: 단위: 건."):
            self.assertEqual("real", next(c for k, _, c in HR.ncs_paragraphs(f) if k == key)["page_basis"], key)
        # 대응 없이 표식으로 간 교재 수는 정본 manifest(real_page_marker_books)에서 — "2권" 을 손으로 쓰지 않는다 (리뷰 red-team)
        intro_key = "NCS 기반 반도체 자료를 대상으로"
        intro = {k: (v, c) for k, v, c in HR.ncs_paragraphs(f)}[intro_key]
        self.assertEqual([b["code"] for b in f.run["real_page_marker_books"]], f.marker_books); self.assertEqual(2, len(f.marker_books))
        self.assertIn("줄→쪽 대응이 없는 2권은 쪽 표식 기준", intro[0]); self.assertEqual(2, intro[1]["marker_books"])
        self.assertIn("run.real_page_marker_books(count)", f.value_index()["2"])                                              # 감사가 허용 토큰 '2' 가 아니라 출처로 통과한다
        one = copy.deepcopy(f); one.run = dict(f.run, real_page_marker_books=f.run["real_page_marker_books"][:1])
        v1, c1 = {k: (v, c) for k, v, c in HR.ncs_paragraphs(one)}[intro_key]
        self.assertIn("줄→쪽 대응이 없는 1권은 쪽 표식 기준", v1); self.assertEqual(1, c1["marker_books"])
        none = copy.deepcopy(f); none.run = dict(f.run, real_page_marker_books=[])
        v0, c0 = {k: (v, c) for k, v, c in HR.ncs_paragraphs(none)}[intro_key]
        self.assertIn("총 ", v0); self.assertNotIn("줄→쪽 대응이 없는", v0); self.assertIn("(PDF 쪽수)", v0); self.assertEqual(0, c0["marker_books"])
        self.assertEqual("real", next(c for k, _, c in HR.case_paragraphs(f) if k.startswith("본 연구에서는 NCS 반도체 교과서에 수록된"))["page_basis"])
        from unittest import mock
        seen = {}
        def fake_refresh(hwpx, facts, out, diff_out, review_dir, **kw):
            seen.update(out=out, diff_out=diff_out, review_dir=review_dir, force=kw.get("force"), text_review_dir=kw.get("text_review_dir"))
            return {"paragraphs": [], "tables": [], "figures": [], "audit": {"tokens": 0, "unmatched": []}}
        with tempfile.TemporaryDirectory() as td, mock.patch.object(HR, "refresh", fake_refresh), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, HR.main(["--hwpx", "x.hwpx", "--text-review-dir", td]))
        self.assertEqual((HR.default_out_path(f), HR.default_diff_path(f), HR.DEFAULT_REVIEW_DIR, False), (seen["out"], seen["diff_out"], seen["review_dir"], seen["force"]))
        with tempfile.TemporaryDirectory() as td:
            summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
            broken = copy.deepcopy(summary); broken["meta"]["page_basis"] = {"NCS": "pdf"}
            (Path(td) / "broken.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"page_basis.*'pdf'"):                                # 값이 있는데 틀린 경우도 그 값을 말한다
                HR.load_facts(Path(td) / "broken.json", HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)


def stage1_body(f):
    """1단계 fixture 본문(제3장 1~3절) + 2절 꼬리(2단계 삽입 자리)."""
    return {"textbook": [para(prefix + " 옛 문장 1,293건") for prefix, _, _ in HR.textbook_paragraphs(f)]
                            + [para("표 7. 교과서"), table([["키워드", "전체", "등급 1", "등급 2", "등급 3", "등급 합계"]] + [[k, "0", "0", "0", "0", "0"] for k in f.school.order] + [["합계", "1,293", "0", "0", "0", "0"]], tid="7"),
                               para("표 8. 교과서 분야별"), table([["분야", "권수", "전체", "등급 1", "등급 2", "등급 3", "출현비율"]] + [[a, "0", "0", "0", "0", "0", "0%"] for a in HR.AREA_ORDER] + [["합계", "9", "1,293", "0", "0", "0", "100.0%"]], tid="8"),
                               para("표 9. 교과서 등급별"), table([["등급", "의미", "출현건수", "등급 비율"], ["등급 1", "", "0", "0%"], ["등급 2", "", "0", "0%"], ["등급 3", "", "0", "0%"], ["합계", "등급 1~3", "1,293", "100.0%"]], tid="9"),
                               pic("image1"), para("그림 2. 교과서 등급")],
                "ncs": [para(prefix + " 옛 문장 12,875건") for prefix, _, _ in HR.ncs_paragraphs(f)]
                       + [para("표 10. NCS"), table([["키워드", "전체", "등급 1", "등급 2", "등급 3", "등급 합계"]] + [[k, "0", "0", "0", "0", "0"] for k in f.ncs.order] + [["합계", "12,875", "0", "0", "0", "0"]], tid="10"),
                          para("표 11. NCS 분야별"), table([["분야", "파일수", "전체", "등급 1", "등급 2", "등급 3", "등급 합계", "출현비율"]] + [[a, "0", "0", "0", "0", "0", "0", "0%"] for a in HR.AREA_ORDER] + [["합계", "85", "12,875", "0", "0", "0", "0", "100.0%"]], tid="11"),
                          pic("image2"), para("그림 3. 분야별"),
                          para("표 12. NCS 등급별"), table([["등급", "의미", "출현건수", "등급 비율"], ["등급 1", "", "0", "0%"], ["등급 2", "", "0", "0%"], ["등급 3", "", "0", "0%"], ["합계", "등급 1~3", "12,875", "100.0%"]], tid="12"),
                          pic("image3"), para("그림 4. 등급별"), ncs_tail_fixture()],
                "cases": [para(prefix + " 옛 문장 9건") for prefix, _, _ in HR.case_paragraphs(f)]
                         + [table([["표 13. NCS 반도체 교과서 내 사고·부상·질병 사례 분석", "", "", "", ""], ["교과서 이름", "교과서 분야", "사고/부상 등 주요 내용", "페이지", "문장 수(글자 수)"]]
                                  + [["반도체 장비 안전관리", "장비", "옛 사례", "33", "1문장"]] * 9 + [["", "", "", "", ""]], tid="13")]}


class EndToEndTests(unittest.TestCase):
    def _fixture(self, td):
        f = fixture_facts()
        return build_fixture_hwpx(Path(td) / "src.hwpx", stage1_body(f)), f

    def test_refresh_rewrites_sections_keeps_rest_and_audits(self):
        render = shutil.which("magick") is not None
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            out = Path(td) / "out.hwpx"
            diff = HR.refresh(src, f, out, Path(td) / "diff.json", Path(td) / "review" if render else None, render=render, text_review_dir=Path(td) / "text")
            self.assertTrue((Path(td) / "text" / "review_text.html").exists())                                       # G-3 구/신 문장 병기본 (비추적 경로)
            self.assertIn("옛 문장", (Path(td) / "text" / "review_text.html").read_text(encoding="utf-8"))
            self.assertEqual("ok", diff["audit"]["status"], diff["audit"])
            self.assertEqual(len(HR.textbook_paragraphs(f)) + len(HR.ncs_paragraphs(f)) + len(HR.case_paragraphs(f)), len(diff["paragraphs"]))
            self.assertEqual(7 + 5 + 2, len(diff["tables"])); self.assertEqual(3, len(diff["figures"]))                    # 1단계 표 7 + 2단계 표 4·5·6·12-1·12-2 + 3단계 표 12-3·12-4 (ncs-book-concentration)
            self.assertTrue(out.exists())
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as b:
                self.assertEqual(a.namelist(), b.namelist())
                self.assertEqual(a.read("Contents/header.xml"), b.read("Contents/header.xml"))
                self.assertEqual(a.getinfo("mimetype").compress_type, b.getinfo("mimetype").compress_type)
                new_xml = b.read("Contents/section0.xml").decode("utf-8")
                if render:
                    self.assertEqual((116, 75, "BMP"), HR.image_dimensions(b.read("BinData/image2.BMP")))
                    self.assertEqual((70, 39, "PNG"), HR.image_dimensions(b.read("BinData/image1.PNG")))
                    self.assertNotEqual(a.read("BinData/image2.BMP"), b.read("BinData/image2.BMP"))
                else:
                    self.assertEqual(a.read("BinData/image2.BMP"), b.read("BinData/image2.BMP"))
            self.assertTrue(new_xml.startswith(HR.XML_DECL + "<hs:sec ")); self.assertIn("xmlns:ha=", new_xml[:400])
            self.assertIn("서론 12,875건 그대로", new_xml); self.assertIn("4절 본문 — 바뀌면 안 된다 12,875건", new_xml)     # 절 밖 불변
            root = ET.fromstring(new_xml.encode("utf-8"))
            sections = HR.locate_sections(root)
            texts = [t for s in sections.values() for t in HR.section_texts(s)]
            self.assertFalse(any("12,875" in t or "1,293" in t or "옛 문장" in t for t in texts))
            tbl13 = HR.find_table_by_first_cell(sections["cases"], "표 13.")
            rows13 = HR.table_rows(tbl13)
            self.assertEqual(2 + 13 + 1, len(rows13)); self.assertEqual("판정", HR.cell_text(rows13[1][4]))                      # 데이터 13 + 원본의 빈 간격 행 유지
            self.assertTrue(all(HR.cell_text(tc) == "" for tc in rows13[-1]))
            self.assertEqual({rows13[2][0].get("borderFillIDRef")}, {tc.get("borderFillIDRef") for r in rows13[2:15] for tc in r})   # 데이터 행 서식 통일
            tbl10 = HR.find_table_after_caption(sections["ncs"], "표 10.")
            rows = HR.table_rows(tbl10)
            self.assertEqual(["안전", HR.fmt(f.ncs.keywords["안전"]["total"])], [HR.cell_text(rows[1][0]), HR.cell_text(rows[1][1])])
            self.assertEqual(HR.fmt(f.ncs.total), HR.cell_text(rows[-1][1]))
            body = (Path(td) / "diff.json").read_text(encoding="utf-8")
            self.assertNotIn("옛 문장", body); self.assertNotIn("/Users/", body)                       # 대조 JSON 에 본문·절대 경로 없음
            if render:
                with self.assertRaises(FileExistsError):
                    HR.refresh(src, f, out, None, None, render=True)                                       # --force 없이는 덮어쓰지 않는다
            with self.assertRaises(FileExistsError):
                HR.write_hwpx(src, out, b"", {})
            with self.assertRaises(ValueError):
                HR.write_hwpx(src, src, b"", {})

    def test_touched_paragraphs_drop_their_line_layout_cache(self):
        """손댄 문단(재작성·삽입, 표 셀 포함)에서는 hp:linesegarray 를 지운다 — 옛 글의 줄 배치 캐시를 믿는 뷰어(Polaris)가 긴 새 글을 한 줄에 눌러 그리던 것(한글 E2E 2026-09-17); 손대지 않은 문단은 그대로."""
        from unittest import mock
        def has_cache(p): return p.find(f".//{HP}linesegarray") is not None
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            out = Path(td) / "out.hwpx"
            original, seen = HR.check_untouched, {}
            def spy(root_, *a, **kw):                                                                                  # 검사 시점에 이미 지워져 있어야 한다 — 검사가 이 변경까지 덮는다
                seen["stripped_at_check"] = any(not has_cache(p) and p.find(f".//{HP}ctrl") is None for p in root_)
                return original(root_, *a, **kw)
            with mock.patch.object(HR, "check_untouched", spy):
                diff = HR.refresh(src, f, out, Path(td) / "diff.json", None, render=False, text_review_dir=Path(td) / "text")
            self.assertTrue(seen["stripped_at_check"])
            with zipfile.ZipFile(out) as z:
                root = ET.fromstring(z.read("Contents/section0.xml"))
            tops = list(root)
            untouched = [p for p in tops if HR.direct_text(p).startswith(("서론 12,875건 그대로", "4절 본문 — 바뀌면 안 된다", "해외 사례 본문 — 바뀌면 안 된다", "- 등급 1", "관련 내용이 없거나 매우 부족한 경우"))]
            self.assertEqual(5, len(untouched)); self.assertTrue(all(has_cache(p) for p in untouched))                 # 편집 범위 밖 2 + 편집된 절 안의 손대지 않은 문단 3
            sections = HR.locate_sections(root)
            first_rewritten = HR.find_paragraph(sections["textbook"], HR.textbook_paragraphs(f)[0][0])                 # 1단계 set_text 재작성 문단
            self.assertFalse(has_cache(first_rewritten))
            first_new = next(p for p in tops if HR.direct_text(p).startswith(HR.MB.methods_paragraphs(f)[1].text[:20]))   # 2단계 삽입 문단
            self.assertFalse(has_cache(first_new))
            tbl5 = HR.find_table_after_caption(HR.locate_range(root, HR.METHODS_HEADING, HR.CHAPTER_HEADING, 1), "표 5.")
            self.assertFalse(any(has_cache(p) for p in tbl5.iter(f"{HP}p")))                                          # 손댄 표의 셀 문단까지
            tbl12_1 = HR.find_table_after_caption(sections["ncs"], "표 12-1.")                                          # 2단계 삽입 표 — 복제한 셀의 캐시도
            self.assertFalse(any(has_cache(p) for p in tbl12_1.iter(f"{HP}p")))
            self.assertEqual({"paragraphs": 124, "linesegarray_removed": 908, "ledger_paragraphs": 124}, diff["layout"])   # fixture: 장부의 최상위 문단 124 전부 캐시를 잃는다(표 문단·그림 문단 포함, 3단계 중복 빈 문단 제거 반영); 표 셀만큼 더 많다
            self.assertEqual(diff["layout"], json.loads((Path(td) / "diff.json").read_text(encoding="utf-8"))["layout"])   # 대조 JSON 파일에도 그대로
            with zipfile.ZipFile(src) as z:
                before = sum(1 for p in ET.fromstring(z.read("Contents/section0.xml")) if not has_cache(p))              # fixture 에서 원래 캐시가 없던 최상위 문단(각주 ctrl 문단)
            self.assertEqual(diff["layout"]["paragraphs"], sum(1 for p in tops if not has_cache(p)) - before)         # 캐시가 없어진 문단 = 손댄 문단뿐
            kept = HR.refresh(src, f, Path(td) / "kept.hwpx", Path(td) / "kept.json", None, render=False, text_review_dir=Path(td) / "text2", strip_layout_cache=False)
            self.assertEqual({"paragraphs": 0, "linesegarray_removed": 0, "kept": True}, kept["layout"])               # --keep-line-layout-cache: 캐시를 전부 남긴다
            with zipfile.ZipFile(Path(td) / "kept.hwpx") as z:
                kept_tops = list(ET.fromstring(z.read("Contents/section0.xml")))
            self.assertEqual(before, sum(1 for p in kept_tops if not has_cache(p)))                                     # 원래 없던 문단(ctrl) 말고는 하나도 잃지 않는다
            self.assertTrue(has_cache(next(p for p in kept_tops if HR.direct_text(p).startswith(HR.MB.methods_paragraphs(f)[1].text[:20]))))   # 삽입 문단이 원형의 캐시를 그대로 가진다

    def test_oversized_figure_entry_is_refused_before_decompression(self):
        """그림 BinData 항목도 section0.xml 처럼 읽기 전에 크기·압축 비율 상한을 검사한다 (CodeRabbit PR #18)."""
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            bomb = Path(td) / "bomb.hwpx"
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(bomb, "w") as b:
                for info in a.infolist():
                    if info.filename == "BinData/image1.PNG":
                        b.writestr(info.filename, png_bytes(70, 39) + b"\x00" * (2 * 1024 * 1024), compress_type=zipfile.ZIP_DEFLATED)   # 머리는 멀쩡, 몸통은 비율 수천 배
                    else:
                        b.writestr(info, a.read(info.filename))
            from unittest import mock
            original_read = zipfile.ZipFile.read
            def guarded_read(zf, name, *args, **kwargs):                                                           # 폭탄 항목이 압축 해제되면 그 자체가 실패
                if getattr(name, "filename", name) == "BinData/image1.PNG":
                    raise AssertionError("BinData/image1.PNG 을 상한 검사 전에 읽었다")
                return original_read(zf, name, *args, **kwargs)
            with mock.patch.object(zipfile.ZipFile, "read", guarded_read), self.assertRaisesRegex(ValueError, r"BinData/image1\.PNG.*압축 비율"):
                HR.refresh(bomb, f, Path(td) / "out.hwpx", Path(td) / "diff.json", None, render=False, text_review_dir=Path(td) / "text")
            self.assertFalse((Path(td) / "out.hwpx").exists()); self.assertFalse((Path(td) / "diff.json").exists())

    def test_no_render_never_writes_the_tracked_diff(self):
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            tracked = HR.default_diff_path(f)
            before = tracked.read_bytes() if tracked.exists() else None
            with contextlib.redirect_stdout(io.StringIO()):
                rc = HR.main(["--hwpx", str(src), "--no-render"])
            self.assertEqual(0, rc)
            self.assertEqual(before, tracked.read_bytes() if tracked.exists() else None)   # 기본 대조 경로는 건드리지 않는다
            with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
                HR.main(["--hwpx", str(src), "--no-render", "--diff-out", str(tracked)])  # 명시해도 추적 경로는 거부

    def test_keep_line_layout_cache_flag_reaches_refresh(self):
        """--keep-line-layout-cache 는 점검 실행에서도 캐시를 남기고 대조 JSON 에 kept 를 적는다 (캐시 없는 문단을 그리지 못하는 뷰어용 안전판)."""
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            with contextlib.redirect_stdout(io.StringIO()):
                rc = HR.main(["--hwpx", str(src), "--no-render", "--diff-out", str(Path(td) / "keep.json"), "--keep-line-layout-cache"])
            self.assertEqual(0, rc)
            self.assertEqual({"paragraphs": 0, "linesegarray_removed": 0, "kept": True}, json.loads((Path(td) / "keep.json").read_text(encoding="utf-8"))["layout"])

    def test_refresh_reports_stale_number_and_writes_nothing(self):
        """숫자 감사 실패: status failed, HWPX·검토 HTML 없음, main 은 1 — 실패 기록은 추적 대조 경로를 덮어쓰지 않는다."""
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            raw, root, tag = HR.read_section(src)
            sec = HR.locate_sections(root)["ncs"]
            stale_p = ET.fromstring(f'<hs:sec {NS}>' + para("기타 12,875건 그대로") + "</hs:sec>")[0]
            root.insert(list(root).index(sec.paragraphs[-1]) + 1, stale_p)
            stale = Path(td) / "stale.hwpx"; HR.write_hwpx(src, stale, HR.serialize_section(root, tag), {})
            out = Path(td) / "o.hwpx"
            diff = HR.refresh(stale, f, out, Path(td) / "d.json", Path(td) / "rv", render=False, text_review_dir=Path(td) / "t")
            self.assertEqual("failed", diff["audit"]["status"]); self.assertIn("12,875", diff["audit"]["unmatched"]); self.assertIn("layout", diff)
            self.assertFalse(out.exists()); self.assertFalse((Path(td) / "rv").exists()); self.assertFalse((Path(td) / "t").exists())
            self.assertTrue((Path(td) / "d.json").exists())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(1, HR.main(["--hwpx", str(stale), "--no-render", "--diff-out", str(Path(td) / "d2.json")]))
            # 추적 경로로 지정된 실패 대조는 temp 로 우회한다
            tracked = HR.default_diff_path(f)
            before = tracked.read_bytes() if tracked.exists() else None                        # 정본 실행일의 대조 JSON 이 아직 없는 트리(재실행 직후)에서도 무쓰기 검사가 돈다 (CodeRabbit PR #17)
            with contextlib.redirect_stdout(io.StringIO()):
                HR.refresh(stale, f, out, tracked, None, render=False)
            self.assertEqual(before, tracked.read_bytes() if tracked.exists() else None)

    def test_no_render_writes_no_hwpx(self):
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            out = Path(td) / "never.hwpx"
            diff = HR.refresh(src, f, out, Path(td) / "d.json", None, render=False, write_output=False)
            self.assertEqual("ok", diff["audit"]["status"]); self.assertIsNone(diff["output"]); self.assertFalse(out.exists())
            written = json.loads((Path(td) / "d.json").read_text(encoding="utf-8"))
            self.assertEqual(diff["layout"], written["layout"]); self.assertEqual({"paragraphs", "linesegarray_removed", "ledger_paragraphs"}, set(written["layout"]))   # 점검 실행도 정본 실행과 같은 layout 을 계산·기록
            diff = HR.refresh(src, f, out, Path(td) / "d.json", None, render=False)                  # render=False 만으로는(magick 없는 CI) HWPX 를 쓴다
            self.assertTrue(out.exists()); self.assertEqual(out.name, diff["output"]); self.assertFalse(any(f["rendered"] for f in diff["figures"]))

    def test_text_review_dir_under_docs_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
                HR.main(["--hwpx", str(src), "--no-render", "--text-review-dir", str(HR.HERE / "docs" / "x")])

    def test_refresh_refuses_when_a_paragraph_is_missing(self):
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            raw, root, tag = HR.read_section(src)
            sections = HR.locate_sections(root)
            p = HR.find_paragraph(sections["ncs"], "‘보호구’는")
            root.remove(p)
            broken = Path(td) / "broken.hwpx"
            HR.write_hwpx(src, broken, HR.serialize_section(root, tag), {})
            with self.assertRaises(ValueError):
                HR.refresh(broken, f, Path(td) / "o.hwpx", None, None, render=False)


if __name__ == "__main__":
    unittest.main()
