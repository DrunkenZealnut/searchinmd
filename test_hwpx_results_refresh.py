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
    """실문서 실행의 대조 JSON — 숫자 감사 통과, 문단 45·표 7·그림 3, 본문·절대 경로 없음."""

    def test_committed_diff_json(self):
        path = DATA / "hwpx_results_refresh_20260914.json"
        if not path.exists():
            self.skipTest("대조 JSON 없음")
        diff = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual({"tokens": diff["audit"]["tokens"], "unmatched": [], "status": "ok"}, diff["audit"])
        self.assertEqual((7, 3), (len(diff["tables"]), len(diff["figures"])))
        self.assertEqual({"PNG": 1, "BMP": 2}, Counter(f["format"] for f in diff["figures"]))
        self.assertTrue(all(len(f["sha256"]) == 64 for f in diff["figures"]))
        self.assertEqual("v2", diff["source"]["summary_run"]["dictionary"])
        self.assertTrue(diff["source"]["summary_run"]["expected"])
        self.assertNotIn("/Users/", path.read_text(encoding="utf-8"))
        self.assertTrue(all(len(p["locator"]) <= 50 for p in diff["paragraphs"]))          # 문단 식별용 첫머리만, 본문 없음


# ---------------------------------------------------------------- fixture HWPX
import io
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


def table(rows, tid="1"):
    trs = []
    for r, row in enumerate(rows):
        tcs = "".join(
            f'<hp:tc name="" header="0" borderFillIDRef="2"><hp:subList id="" textDirection="HORIZONTAL">{para(cell, "17")}</hp:subList>'
            f'<hp:cellAddr colAddr="{c}" rowAddr="{r}"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="100" height="10"/></hp:tc>'
            for c, cell in enumerate(row))
        trs.append(f"<hp:tr>{tcs}</hp:tr>")
    tbl = f'<hp:tbl id="{tid}" rowCnt="{len(rows)}" colCnt="{len(rows[0])}" borderFillIDRef="7">' + "".join(trs) + "</hp:tbl>"
    return f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13">{tbl}</hp:run></hp:p>'


def pic(item):
    return (f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13">'
            f'<hp:pic id="9" zOrder="1"><hc:img binaryItemIDRef="{item}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/></hp:pic></hp:run></hp:p>')


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


def build_fixture_hwpx(path, body_paragraphs):
    """목차(제목 중복) + 본문. body_paragraphs 는 절 이름 → 문단 XML 목록."""
    toc = "".join(para(t) for t in FIXTURE_SECTION_TITLES)
    body = para("제3장 연구 결과")
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
    def test_set_text_keeps_first_run_format_and_collapses_extra_runs(self):
        p = ET.fromstring(f'<hp:p {NS}>' + '<hp:run charPrIDRef="13"><hp:t>앞</hp:t></hp:run><hp:run charPrIDRef="9"><hp:t>뒤</hp:t></hp:run></hp:p>'.replace("<hp:p ", "<hp:p ") if False else
                          f'<hp:p {NS}><hp:run charPrIDRef="13"><hp:t>앞</hp:t></hp:run><hp:run charPrIDRef="9"><hp:t>뒤</hp:t></hp:run><hp:linesegarray/></hp:p>')
        info = HR.set_text(p, "새 글")
        runs = p.findall(HP + "run")
        self.assertEqual(1, len(runs)); self.assertEqual("13", runs[0].get("charPrIDRef")); self.assertEqual("새 글", HR.direct_text(p))
        self.assertTrue(info["format_collapsed"])
        self.assertIsNotNone(p.find(HP + "linesegarray"))                       # 글 아닌 자식은 그대로

    def test_resize_table_grows_by_cloning_last_row_and_renumbers(self):
        root = ET.fromstring(f'<hs:sec {NS}>' + table([["h1", "h2"], ["a", "1"], ["b", "2"]]) + "</hs:sec>")
        tbl = root.find(f".//{HP}tbl")
        HR.resize_table(tbl, 1, 4)
        rows = HR.table_rows(tbl)
        self.assertEqual(5, len(rows)); self.assertEqual("5", tbl.get("rowCnt"))
        self.assertEqual([str(i) for i in range(5)], [r[0].find(HP + "cellAddr").get("rowAddr") for r in rows])
        HR.resize_table(tbl, 1, 1)
        self.assertEqual(2, len(HR.table_rows(tbl))); self.assertEqual("2", tbl.get("rowCnt"))
        with self.assertRaises(ValueError):
            HR.fill_table(tbl, [["x", "1"], ["y", "2"]], 1)                     # 행 수 불일치는 실패


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


class AuditTests(unittest.TestCase):
    def test_audit_flags_stale_numbers_and_accepts_canonical_ones(self):
        f = fixture_facts()
        self.assertEqual([], HR.audit_numbers([f"총 {HR.fmt(f.ncs.total)}건, 등급 3 {HR.pct(f.ncs.grades[3], f.ncs.total)}, 33쪽, 2014년"], f))
        self.assertEqual(["12,875", "4,259"], HR.audit_numbers(["‘안전’ 4,259건 중 12,875"], f))

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
    def test_korean_particles(self):
        self.assertEqual(("정의로", "지침으로", "관리와", "지침과", "PSM로"), (HR.ro("정의"), HR.ro("지침"), HR.wa("관리"), HR.wa("지침"), HR.ro("PSM")))
        self.assertEqual("『반도체 장비 안전관리』와", HR.wa("『반도체 장비 안전관리』"))

    def test_templates_branch_on_data(self):
        f = fixture_facts()
        texts = {k: v for k, v in HR.ncs_paragraphs(f)}
        psm = f.ncs.keywords["공정안전관리"]
        all3 = psm["grades"][3] == psm["total"]
        self.assertEqual(all3, "모두 등급 3" in texts["한편 ‘공정안전관리’는 총"])
        ppe = f.ncs.keywords["보호구"]
        self.assertEqual((ppe["grades"][2] + ppe["grades"][3]) / ppe["total"] >= 0.6, "60%를 넘었다" in texts["‘보호구’는"])
        self.assertIn(HR.fmt(f.ncs.keywords["안전"]["total"]), texts["교과서의 전체 키워드 중 ‘안전’이"])
        self.assertNotIn("643", texts["화학물질 관련 키워드는"]); self.assertIn("독립 집계", texts["화학물질 관련 키워드는"])   # D3
        school = {k: v for k, v in HR.textbook_paragraphs(f)}
        self.assertIn("전혀 검출되지 않았고", school["따라서 제조 분야는 안전보건교육이 가장 적극적으로"])
        cases = {k: v for k, v in HR.case_paragraphs(f)}
        self.assertIn("13쪽", cases["본 연구에서는 NCS 반도체 교과서에 수록된 사고, 부상, 질병 관련 사례를"])
        for name, template in HR.PARAGRAPH_TEMPLATES.items():
            for prefix, text in template(f):
                self.assertEqual([], HR.audit_numbers([text], f), (name, prefix))                    # 템플릿이 내는 숫자는 전부 정본 값


class EndToEndTests(unittest.TestCase):
    def _fixture(self, td):
        f = fixture_facts()
        body = {"textbook": [para(prefix + " 옛 문장 1,293건") for prefix, _ in HR.textbook_paragraphs(f)]
                            + [para("표 7. 교과서"), table([["키워드", "전체", "등급 1", "등급 2", "등급 3", "등급 합계"]] + [[k, "0", "0", "0", "0", "0"] for k in f.school.order] + [["합계", "1,293", "0", "0", "0", "0"]]),
                               para("표 8. 교과서 분야별"), table([["분야", "권수", "전체", "등급 1", "등급 2", "등급 3", "출현비율"]] + [[a, "0", "0", "0", "0", "0", "0%"] for a in HR.AREA_ORDER] + [["합계", "9", "1,293", "0", "0", "0", "100.0%"]]),
                               para("표 9. 교과서 등급별"), table([["등급", "의미", "출현건수", "등급 비율"], ["등급 1", "", "0", "0%"], ["등급 2", "", "0", "0%"], ["등급 3", "", "0", "0%"], ["합계", "등급 1~3", "1,293", "100.0%"]]),
                               pic("image1"), para("그림 2. 교과서 등급")],
                "ncs": [para(prefix + " 옛 문장 12,875건") for prefix, _ in HR.ncs_paragraphs(f)]
                       + [para("표 10. NCS"), table([["키워드", "전체", "등급 1", "등급 2", "등급 3", "등급 합계"]] + [[k, "0", "0", "0", "0", "0"] for k in f.ncs.order] + [["합계", "12,875", "0", "0", "0", "0"]]),
                          para("표 11. NCS 분야별"), table([["분야", "파일수", "전체", "등급 1", "등급 2", "등급 3", "등급 합계", "출현비율"]] + [[a, "0", "0", "0", "0", "0", "0", "0%"] for a in HR.AREA_ORDER] + [["합계", "85", "12,875", "0", "0", "0", "0", "100.0%"]]),
                          pic("image2"), para("그림 3. 분야별"),
                          para("표 12. NCS 등급별"), table([["등급", "의미", "출현건수", "등급 비율"], ["등급 1", "", "0", "0%"], ["등급 2", "", "0", "0%"], ["등급 3", "", "0", "0%"], ["합계", "등급 1~3", "12,875", "100.0%"]]),
                          pic("image3"), para("그림 4. 등급별")],
                "cases": [para(prefix + " 옛 문장 9건") for prefix, _ in HR.case_paragraphs(f)]
                         + [table([["표 13. NCS 반도체 교과서 내 사고·부상·질병 사례 분석", "", "", "", ""], ["교과서 이름", "교과서 분야", "사고/부상 등 주요 내용", "페이지", "문장 수(글자 수)"]]
                                  + [["반도체 장비 안전관리", "장비", "옛 사례", "33", "1문장"]] * 9 + [["", "", "", "", ""]])]}
        return build_fixture_hwpx(Path(td) / "src.hwpx", body), f

    def test_refresh_rewrites_sections_keeps_rest_and_audits(self):
        render = shutil.which("magick") is not None
        with tempfile.TemporaryDirectory() as td:
            src, f = self._fixture(td)
            out = Path(td) / "out.hwpx"
            diff = HR.refresh(src, f, out, Path(td) / "diff.json", Path(td) / "review" if render else None, render=render)
            self.assertEqual("ok", diff["audit"]["status"], diff["audit"])
            self.assertEqual(len(HR.textbook_paragraphs(f)) + len(HR.ncs_paragraphs(f)) + len(HR.case_paragraphs(f)), len(diff["paragraphs"]))
            self.assertEqual(7, len(diff["tables"])); self.assertEqual(3, len(diff["figures"]))
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
            self.assertEqual(2 + 13, len(HR.table_rows(tbl13))); self.assertEqual("판정", HR.cell_text(HR.table_rows(tbl13)[1][4]))
            tbl10 = HR.find_table_after_caption(sections["ncs"], "표 10.")
            rows = HR.table_rows(tbl10)
            self.assertEqual(["안전", HR.fmt(f.ncs.keywords["안전"]["total"])], [HR.cell_text(rows[1][0]), HR.cell_text(rows[1][1])])
            self.assertEqual(HR.fmt(f.ncs.total), HR.cell_text(rows[-1][1]))
            body = (Path(td) / "diff.json").read_text(encoding="utf-8")
            self.assertNotIn("옛 문장", body); self.assertNotIn("/Users/", body)                       # 대조 JSON 에 본문·절대 경로 없음
            with self.assertRaises(FileExistsError):
                HR.refresh(src, f, out, None, None, render=False)
            with self.assertRaises(ValueError):
                HR.write_hwpx(src, src, b"", {})

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
