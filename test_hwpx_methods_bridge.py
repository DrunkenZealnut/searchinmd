"""hwpx-methods-bridge-refresh — 제2장 5절(연구 방법)·제3장 2절 4)(집계 기준 연결) 2단계의 사실·템플릿·XML 능력·조립 테스트.

fixture 도우미(para/table/build_fixture_hwpx)는 test_hwpx_results_refresh 에서 가져온다. openpyxl 불필요.
"""
from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

import xml.etree.ElementTree as ET

import hwpx_methods_bridge as MB
import hwpx_results_refresh as HR
from test_hwpx_results_refresh import NS, para, table, build_fixture_hwpx, stage1_body, OLD_METHODS_TOC
import shutil
import zipfile

HERE = Path(__file__).resolve().parent
DATA = HERE / "docs" / "03-analysis" / "data"


def canonical_facts():
    return HR.load_facts(HR.DEFAULT_SUMMARY, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)


class MethodsFactsTests(unittest.TestCase):
    """제2장 5절의 사실 — 추적 파일 8종에서 읽고, 값은 정본(2026-09-17)과 같다."""

    def test_loads_canonical_values(self):
        m = MB.load_methods_facts(MB.MethodsPaths())
        self.assertEqual(1, m.dedup_books)
        self.assertEqual(30, len(m.keyword_names)); self.assertIn("안전", m.keyword_names)
        self.assertEqual((22, 30, 618), (m.review_targets, m.review_per_expression, m.review_items))
        self.assertEqual((612, 595, 17), (m.review_n, m.review_agree, m.review_disagreements)); self.assertAlmostEqual(0.9648, m.review_kappa, places=4)
        self.assertEqual((0.05, 0.8), (m.review_alpha, m.review_floor)); self.assertEqual(("claude-opus-5", "gpt-5.6-sol"), m.review_coders)
        self.assertEqual(("방진화", "케미컬"), m.held); self.assertEqual(("방진복", "장갑", "X선", "PSM"), m.conditional)
        self.assertEqual({"NCS": 12310, "교과서": 1272}, m.totals_v1fix); self.assertEqual({"NCS": 11517, "교과서": 1207}, m.totals_v2)
        self.assertEqual(58, m.max_label_width); self.assertEqual(16, m.truncated_pages); self.assertEqual(32767, m.excel_max_chars)
        self.assertEqual((84, 2), (m.page_maps, m.marker_books))
        self.assertEqual((23, 21711, 18142, 20613), (m.align_books, m.align_lines, m.align_exact, m.align_near))
        self.assertEqual((6, 5), (m.safety_min, m.action_min)); self.assertEqual((1847, 1839), (m.repro_pages, m.repro_agree))
        self.assertEqual((538, 238, 300, 1609), (m.sample_pages, m.census_pages, m.recall_pages, m.recall_pool))
        self.assertEqual((80, 84), m.precision_range()); self.assertEqual((13, 21), m.recall_range())
        self.assertEqual(7, m.inputs)

    def test_value_pairs_carry_the_derived_strings(self):
        m = MB.load_methods_facts(MB.MethodsPaths())
        values = {v for v, _ in m.value_pairs()}
        for expected in ("22", "30", "618", "612", "595", "97.2%", "0.965", "17", "95", "0.8", "12,310", "11,517", "1,272", "1,207", "58", "16", "32,767", "84", "23", "21,711",
                         "83.6%", "94.9%", "5.1%", "6", "5", "4", "1,847", "1,839", "99.6%", "538", "238", "300", "1,609", "80", "84", "13", "21", "7", "2", "1"):
            self.assertIn(expected, values, expected)
        keys = dict((v, k) for v, k in m.value_pairs())
        self.assertIn("regrade_impact", keys["99.6%"]); self.assertIn("구라벨", keys["58"])

    def test_missing_key_names_the_file_and_key(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "regrade_impact.json"
            bad.write_text(json.dumps({"rule": {"safety_min": 6}, "reproduction": {"agree": 1839, "total": 1847}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "regrade_impact.json.*action_min"):
                MB.load_methods_facts(dataclasses.replace(MB.MethodsPaths(), regrade_impact=bad))

    def test_range_collapses_when_both_coders_round_to_the_same_value(self):
        m = MB.load_methods_facts(MB.MethodsPaths())
        same = dataclasses.replace(m, precision=(0.801, 0.804))
        self.assertEqual((80, 80), same.precision_range()); self.assertEqual("80%", MB.range_text(same.precision_range())); self.assertEqual("80~84%", MB.range_text(m.precision_range()))


class BridgeFactsTests(unittest.TestCase):
    """제3장 2절 4)의 사실 — 영향표·이전 기준·정본 manifest 가 같은 계보인지 확인하며 읽는다."""

    def test_loads_canonical_values(self):
        b = MB.load_bridge_facts(MB.MethodsPaths())
        self.assertEqual("2026-09-17", b.run_date); self.assertEqual(11517, b.total)
        self.assertEqual({1: 4378, 2: 4614, 3: 2525}, b.block_grades); self.assertEqual({1: 3788, 2: 5227, 3: 2502}, b.real_grades)
        self.assertEqual((1785, 2492), (b.block_pages, b.real_pages)); self.assertEqual((4016, 7501), (b.moved, b.unchanged))
        self.assertEqual(6, len(b.matrix)); self.assertEqual(4016, sum(b.matrix.values()))
        self.assertEqual((236, 122), b.groups["반도체개발"]); self.assertEqual((1010, 1052), b.groups["반도체장비"])
        self.assertEqual((6292, 52.8), (b.existing_occurrences, b.existing_kept_pct))
        self.assertEqual({1: 1825, 2: 524, 3: 143}, b.real_page_grades); self.assertEqual((388, {1: 335, 2: 45, 3: 8}), (b.school_detected, b.school_page_grades))
        self.assertEqual(("2026-09-06", 2189, {1: 1519, 2: 525, 3: 145}, 7769), (b.prev_date, b.prev_pages, b.prev_page_g, b.prev_rows))
        self.assertEqual((2035, 2035), (b.shared_pages, b.shared_agree))

    def test_value_pairs_carry_totals_shares_and_deltas(self):
        b = MB.load_bridge_facts(MB.MethodsPaths())
        values = {v for v, _ in b.value_pairs()}
        for expected in ("11,517", "4,378", "38.0%", "3,788", "32.9%", "590", "613", "23", "1,785", "2,492", "4,016", "34.9%", "7,501", "1,296", "631", "236", "122",
                         "6,292", "52.8%", "1,825", "73.2%", "143", "5.7%", "388", "8", "2,189", "1,519", "69.4%", "145", "6.6%", "7,769", "2,035", "100.0%", "21.7%"):
            self.assertIn(expected, values, expected)

    def test_refuses_an_impact_table_from_another_run(self):
        impact = json.loads((DATA / "occurrence_real_pages_impact.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            other = Path(td) / "impact.json"
            impact["totals"]["NCS"] = 11516
            other.write_text(json.dumps(impact, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "totals.NCS"):
                MB.load_bridge_facts(dataclasses.replace(MB.MethodsPaths(), impact=other))

    def test_refuses_each_lineage_mismatch(self):                                                     # 갭 분석 G2
        impact = json.loads((DATA / "occurrence_real_pages_impact.json").read_text(encoding="utf-8"))
        cases = {"grades.real.NCS": (lambda d: d["grades"]["real"]["NCS"].__setitem__("3", 2501)),
                 "pages.real_pages": (lambda d: d["pages"].__setitem__("real_pages", 2491)),
                 "page_maps.sha256": (lambda d: d["meta"]["inputs"]["page_maps"].__setitem__("sha256", "0" * 64)),
                 "pages.교과서.detected_pages": (lambda d: d["pages"]["교과서"].__setitem__("detected_pages", 387))}
        for key, mutate in cases.items():
            with self.subTest(key=key), tempfile.TemporaryDirectory() as td:
                bad = json.loads(json.dumps(impact)); mutate(bad)
                other = Path(td) / "impact.json"; other.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, key.split(".")[-1] if key != "grades.real.NCS" else "grades.real"):
                    MB.load_bridge_facts(dataclasses.replace(MB.MethodsPaths(), impact=other))

    def test_refuses_when_previous_basis_copy_disagrees_with_reseg(self):
        reseg = json.loads((DATA / "reseg_summary.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            other = Path(td) / "reseg_summary.json"
            reseg["page_g"]["3"] = 146
            other.write_text(json.dumps(reseg, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "previous_basis"):
                MB.load_bridge_facts(dataclasses.replace(MB.MethodsPaths(), reseg_summary=other))


def sec(*paragraph_xml: str) -> ET.Element:
    return ET.fromstring(f"<hs:sec {NS}>" + "".join(paragraph_xml) + "</hs:sec>")


class FactsIntegrationTests(unittest.TestCase):
    def test_load_facts_carries_methods_bridge_and_detected_pages(self):
        f = canonical_facts()
        self.assertEqual(2492, f.ncs.detected_pages); self.assertEqual(388, f.school.detected_pages)
        self.assertIsInstance(f.methods, MB.MethodsFacts); self.assertIsInstance(f.bridge, MB.BridgeFacts)
        numbers = f.all_numbers()
        for v in ("58", "0.965", "97.2%", "80", "84", "1,785", "4,016", "590", "1,825", "5.7%", "7,769", "69.4%"):
            self.assertIn(v, numbers, v)
        self.assertTrue(any(k.startswith("impact.") for k in f.keys_for(["4,016"])))
        self.assertTrue(any("regrade_impact" in k for k in f.keys_for(["99.6%"])))

    def test_value_index_is_cached_per_instance_and_not_inherited_by_replace(self):
        f = canonical_facts()
        self.assertIs(f.value_index(), f.value_index())                                                          # 같은 인스턴스는 한 번만 만든다 (성능 리뷰)
        g = dataclasses.replace(f, bridge=dataclasses.replace(f.bridge, moved=4017))
        self.assertIn("4,017", g.all_numbers()); self.assertNotIn("4,017", f.all_numbers())                       # replace 로 만든 사실은 제 값으로 다시 만든다

    def test_fmt_pct_are_shared_with_the_bridge_module(self):
        self.assertIs(HR.fmt, MB.fmt); self.assertIs(HR.pct, MB.pct)


class XmlAbilityTests(unittest.TestCase):
    """설계 §3.3 — 문단 복제·삽입·삭제, 표 복제(고유 id), 범위·목차 탐지, 셀 안 문단 편집."""

    def test_clone_paragraph_inherits_style_and_allows_empty_prototype(self):
        root = sec(para("원형", char="21"), '<hp:p id="0" paraPrIDRef="25" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="22"/></hp:p>')
        proto, blank = HR.top_paragraphs(root)
        c = HR.clone_paragraph(proto, "새 글")
        self.assertEqual("새 글", HR.direct_text(c)); self.assertEqual("21", c.find(HR.HP + "run").get("charPrIDRef")); self.assertIsNot(c, proto); self.assertEqual("원형", HR.direct_text(proto))
        b = HR.clone_paragraph(blank, "")
        self.assertEqual("", HR.direct_text(b)); self.assertEqual("25", b.get("paraPrIDRef")); self.assertIsNone(b.find(f"{HR.HP}run/{HR.HP}t"))

    def test_insert_after_and_remove_paragraphs(self):
        root = sec(para("A"), para("B"), para("C"))
        a, b, c = HR.top_paragraphs(root)
        new = [HR.clone_paragraph(a, "X"), HR.clone_paragraph(a, "Y")]
        HR.insert_after(root, a, new)
        self.assertEqual(["A", "X", "Y", "B", "C"], [HR.direct_text(p) for p in HR.top_paragraphs(root)])
        HR.remove_paragraphs(root, [b])
        self.assertEqual(["A", "X", "Y", "C"], [HR.direct_text(p) for p in HR.top_paragraphs(root)])
        with self.assertRaisesRegex(ValueError, "없"):
            HR.remove_paragraphs(root, [b])

    def test_next_object_id_is_max_plus_one_over_tables_and_pictures(self):
        root = sec(table([["a"]], tid="1096129347"), table([["b"]], tid="99740001"),
                   '<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13"><hp:pic id="2000000000" zOrder="9"><hc:img binaryItemIDRef="image1" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/></hp:pic></hp:run></hp:p>')
        self.assertEqual((2000000001, 10), HR.next_object_ids(root))

    def test_clone_table_paragraph_gets_new_ids_rows_and_header(self):
        root = sec(table([["등급", "의미", "출현건수", "등급 비율"], ["등급 1", "", "0", "0%"], ["합계", "등급 1~3", "0", "100.0%"]], tid="7"))
        proto = HR.top_paragraphs(root)[0]
        rows = [["출현 총계", "1", "1", "0"], ["등급 1", "2", "3", "1"], ["등급 2", "4", "5", "1"]]
        new_p = HR.clone_table_paragraph(proto, rows, 1, ["구분", "블록", "실제", "차이"], (8, 3))
        tbl = new_p.find(f".//{HR.HP}tbl")
        self.assertEqual(("8", "3"), (tbl.get("id"), tbl.get("zOrder"))); self.assertEqual("7", proto.find(f".//{HR.HP}tbl").get("id"))
        got = [[HR.cell_text(tc) for tc in row] for row in HR.table_rows(tbl)]
        self.assertEqual([["구분", "블록", "실제", "차이"]] + rows, got); self.assertEqual("4", tbl.get("rowCnt"))
        self.assertEqual("", "".join(t.text or "" for t in new_p.findall(f"{HR.HP}run/{HR.HP}t")))          # 표 문단의 글 run 은 비운다

    def test_locate_range_distinguishes_toc_copy_from_body(self):
        root = sec(para("5. 방법론"), para("제3장 연구 결과"), para("본문 앞"), para("5. 방법론"), para("본문 1"), para("본문 2"), para("제3장 연구 결과"), para("뒤"))
        body = HR.locate_range(root, "5. 방법론", "제3장 연구 결과", occurrence=1)
        self.assertEqual(["5. 방법론", "본문 1", "본문 2"], [HR.direct_text(p) for p in body.paragraphs])
        toc = HR.locate_range(root, "5. 방법론", "제3장 연구 결과", occurrence=0)
        self.assertEqual(1, len(toc.paragraphs))
        with self.assertRaisesRegex(ValueError, "찾지 못"):
            HR.locate_range(root, "5. 방법론", "제3장 연구 결과", occurrence=2)

    def test_locate_toc_block_takes_the_first_entry_to_the_next_heading(self):
        root = sec(para("2. NCS 반도체 교과서의"), para(" 1) 키워드"), para(" 4) 소결"), para("3. NCS 반도체 교과서의 사고"), para("2. NCS 반도체 자료의"), para(" 4) 소결"))
        block = HR.locate_toc_block(root, "2. NCS", "3. NCS")
        self.assertEqual(["2. NCS 반도체 교과서의", " 1) 키워드", " 4) 소결"], [HR.direct_text(p) for p in block])
        with self.assertRaisesRegex(ValueError, "목차"):
            HR.locate_toc_block(root, "9. 없는", "3. NCS")

    def test_set_cell_paragraph_edits_one_paragraph_in_a_multi_paragraph_cell(self):
        cell = (f'<hp:tc name="" header="0" borderFillIDRef="2"><hp:subList id="" textDirection="HORIZONTAL">{para("한국산업인력공단 NCS 교과서", "17")}{para("반도체개발 30종", "17")}{para("반도체제조 14종", "17")}</hp:subList>'
                f'<hp:cellAddr colAddr="1" rowAddr="2"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="100" height="10"/></hp:tc>')
        root = sec(f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13"><hp:tbl id="1" rowCnt="1" colCnt="1" borderFillIDRef="7"><hp:tr>{cell}</hp:tr></hp:tbl></hp:run></hp:p>')
        tc = root.find(f".//{HR.HP}tc")
        HR.set_cell_paragraph(tc, "반도체제조", "반도체제조 13종")
        self.assertEqual(["한국산업인력공단 NCS 교과서", "반도체개발 30종", "반도체제조 13종"], [HR.direct_text(p) for p in HR.cell_paragraphs(tc)])
        with self.assertRaisesRegex(ValueError, "1개여야"):
            HR.set_cell_paragraph(tc, "반도체", "x")
        with self.assertRaisesRegex(ValueError, "1개여야"):
            HR.set_cell_paragraph(tc, "없는", "x")


class BackupTests(unittest.TestCase):
    def test_force_overwrite_keeps_a_sha_named_backup(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.hwpx"; out = Path(td) / "out.hwpx"
            with zipfile.ZipFile(src, "w") as z:
                z.writestr("mimetype", "application/hwp+zip"); z.writestr(HR.SECTION_ENTRY, "<a/>")
            out.write_bytes(b"old content")
            with self.assertRaises(FileExistsError):
                HR.write_hwpx(src, out, b"<b/>", {})
            backup, written = HR.write_hwpx(src, out, b"<b/>", {}, force=True)
            self.assertIsNotNone(backup); self.assertTrue(backup.exists()); self.assertEqual(b"old content", backup.read_bytes())
            self.assertEqual(out.name + "." + HR.sha256(b"old content")[:16] + ".bak", backup.name); self.assertEqual(HR.sha256(out.read_bytes()), written)   # 쓴 바이트의 sha 를 돌려준다
            fresh_backup, fresh_sha = HR.write_hwpx(src, Path(td) / "fresh.hwpx", b"<b/>", {})
            self.assertIsNone(fresh_backup); self.assertEqual(HR.sha256((Path(td) / "fresh.hwpx").read_bytes()), fresh_sha)   # 없던 파일은 백업 없음
            # 끊긴 반쪽 백업(이름은 같은데 내용이 다름)은 다시 쓰고, 심볼릭 링크 자리는 거부한다 (보안 리뷰)
            out.write_bytes(b"old content"); backup.write_bytes(b"trunc")
            self.assertEqual(backup, HR.write_hwpx(src, out, b"<c/>", {}, force=True)[0]); self.assertEqual(b"old content", backup.read_bytes())
            out.write_bytes(b"other"); link = out.with_name(out.name + "." + HR.sha256(b"other")[:16] + ".bak"); link.symlink_to(Path(td) / "elsewhere")
            with self.assertRaisesRegex(ValueError, "심볼릭"):
                HR.write_hwpx(src, out, b"<d/>", {}, force=True)


def with_concentration(f, **changes):
    return dataclasses.replace(f, concentration=dataclasses.replace(f.concentration, **changes))


def with_bridge(f, **changes):
    return dataclasses.replace(f, bridge=dataclasses.replace(f.bridge, **changes))


def with_methods(f, **changes):
    return dataclasses.replace(f, methods=dataclasses.replace(f.methods, **changes))


def texts(pieces, kind):
    return [pc.text for pc in pieces if pc.kind == kind]


class MethodsTemplateTests(unittest.TestCase):
    """설계 §3.5 — 5절 소제목 6·본문 7·빈 문단 7·목록 자리 1, 재작성 2, 표 5·6, 표 4, 목차."""

    def setUp(self):
        self.f = canonical_facts()

    def test_piece_sequence_and_headings(self):
        pieces = MB.methods_paragraphs(self.f)
        kinds = "".join(pc.kind for pc in pieces)
        self.assertEqual("HPBHPBPBHPBHLBPBHPBHP", kinds)
        self.assertEqual(list(MB.METHODS_HEADINGS), texts(pieces, "H"))

    def test_bodies_carry_the_canonical_numbers(self):
        p1, p2a, p2b, p3, p4, p5, p6 = texts(MB.methods_paragraphs(self.f), "P")
        for needle in ("86권", "반도체개발 30권", "반도체제조 13권", "반도체장비 19권", "반도체재료 24권", "9,100쪽", "9권", "2,055쪽", "같은 코드의 파일이 둘인 1권"):
            self.assertIn(needle, p1, needle)
        self.assertIn("30개 주제어", p2a); self.assertIn("안전·", p2a); self.assertIn("(1) 정확 일치", p2a)
        for needle in ("22개 표현", "최대 30건", "618건", "Claude", "GPT", "612건", "595건(97.2%, κ 0.965)", "17건", "95% 신뢰구간", "0.8 미만", "보류(방진화·케미컬)", "조건부 포함(방진복·장갑·X선·PSM",
                       "12,310건에서 11,517건", "1,272건에서 1,207건", "줄었다"):
            self.assertIn(needle, p2b, needle)
        for needle in ("2026-04", "58쪽", "32,767자", "16개", "3-gram", "84권", "23권", "21,711줄", "83.6%", "94.9%", "나머지 2권", "교과서 9권", "제3장 2절 4)"):
            self.assertIn(needle, p3, needle)
        for needle in ("5건 이하 → 등급 1", "6건 이상이면서 조치 용어 5건 이상 → 등급 3", "1,847쪽", "99.6%(1,839쪽)", "538쪽", "238쪽", "1,609쪽", "무작위 300쪽", "80~84%", "13~21%", "보수적인 판정", "1,149건", "58건"):
            self.assertIn(needle, p4, needle)
        for needle in ("21.7%", "5.7%", "보다 크다", "2026-09-06", "2,189쪽", "6.6%", "분모를 함께"):
            self.assertIn(needle, p5, needle)
        for needle in (MB.REPO_URL, "7종", "84개", "5.1%", "첫째", "둘째", "셋째", "넷째", "하한"):
            self.assertIn(needle, p6, needle)

    def test_branches(self):
        f = self.f
        p1 = texts(MB.methods_paragraphs(with_methods(f, dedup_books=0)), "P")[0]
        self.assertNotIn("같은 코드", p1)
        pieces = MB.methods_paragraphs(with_methods(f, totals_v2={"NCS": 12400, "교과서": 1207}))
        self.assertIn("바뀌었다", texts(pieces, "P")[2]); self.assertFalse([pc for pc in pieces if pc.kind == "P"][2].conditions["totals_decreased"])
        high = with_methods(f, recall=(0.6, 0.7))
        p4, p6 = texts(MB.methods_paragraphs(high), "P")[4], texts(MB.methods_paragraphs(high), "P")[6]
        self.assertNotIn("보수적인 판정", p4); self.assertIn("60~70%", p4); self.assertNotIn("하한", p6); self.assertIn("셋째", p6); self.assertNotIn("넷째", p6)
        low_occ = with_bridge(f, real_grades={1: 3788, 2: 7229, 3: 500})
        self.assertIn("분모가 다른 값이다", texts(MB.methods_paragraphs(low_occ), "P")[5])
        self.assertEqual("Claude", MB.coder_family("claude-opus-5")); self.assertEqual("GPT", MB.coder_family("gpt-5.6-sol")); self.assertEqual("gemini-x", MB.coder_family("gemini-x"))

    def test_rewrites_tables_and_table4(self):
        rewrites = MB.methods_rewrites(self.f)
        self.assertEqual(["안전보건 수준은 각 출현이 속한", "이 등급은 문장 하나의 완성도를"], [loc for loc, _ in rewrites])
        self.assertIn("실제 PDF 쪽", rewrites[0][1]); self.assertIn("같은 쪽의 모든 출현이 같은 등급", rewrites[1][1])
        t5 = MB.methods_table5_rows(self.f)
        self.assertEqual(7, len(t5)); self.assertEqual("1. 자료 수집", t5[0][0]); self.assertEqual("7. 결과 정리·검증", t5[-1][0]); self.assertIn("86권", t5[0][1]); self.assertIn("30개 주제어", t5[2][1])
        self.assertEqual("표 5. 키워드 기반 분석의 이해하기 쉬운 7단계", MB.table5_caption(self.f)); self.assertEqual("표 6. 검색·쪽 배치·등급 판정 기준", MB.TABLE6_CAPTION)
        t6 = MB.methods_table6_rows(self.f)
        self.assertEqual(7, len(t6)); self.assertEqual(["검색 표현", "문맥 확인", "쪽 기준", "등급 1", "등급 2", "등급 3", "집계 단위"], [r[0] for r in t6])
        self.assertIn("5건 이하", t6[3][2]); self.assertIn("조치 용어 4건 이하", t6[4][2]); self.assertIn("84권", t6[2][2]); self.assertIn("2권과 교과서 9권", t6[2][2])
        self.assertEqual("표 4. 국내 반도체고등학교 교과서(9종)와 한국산업인력공단 NCS 교과서(86종)", MB.table4_caption(self.f))
        self.assertEqual([("반도체개발", "반도체개발 30종"), ("반도체제조", "반도체제조 13종"), ("반도체장비", "반도체장비 19종"), ("반도체재료", "반도체재료 24종")], MB.table4_group_lines(self.f))


class BridgeTemplateTests(unittest.TestCase):
    """설계 §3.7 — 2절 4) 문단 2·표 12-1·12-2·주 2, 소결 문장, 1절 교과서 문장, 분기 5종."""

    def setUp(self):
        self.f = canonical_facts()

    def test_piece_sequence_and_texts(self):
        pieces = MB.bridge_paragraphs(self.f)
        self.assertEqual("BHBPBCTNBPBCTNB", "".join(pc.kind for pc in pieces))
        self.assertEqual([MB.BRIDGE_HEADING], texts(pieces, "H"))
        q1, q2 = texts(pieces, "P")
        for needle in ("2026-09-17 정본", "11,517건은 변하지 않았고", "1,785개 블록에서 2,492쪽으로 늘었으며", "4,016건(34.9%)", "4,378건(38.0%)에서 3,788건(32.9%)으로 줄고",
                       "4,614건(40.1%)에서 5,227건(45.4%)으로 늘었으며", "2,525건(21.9%)에서 2,502건(21.7%)으로 거의 같았다", "반도체개발 236건→122건", "반도체재료 1,174건→1,248건", "6,292건", "52.8%", "승계하지 않고"):
            self.assertIn(needle, q1, needle)
        for needle in ("2,492쪽", "143쪽(5.7%)", "2026-09-06", "7,769행", "2,189쪽 가운데 등급 3이 145쪽(6.6%)", "2,035쪽의 등급은 모두 일치한다", "21.7%", "몫이 커진다", "개선으로 읽어서는 안 되며"):
            self.assertIn(needle, q2, needle)
        c1, c2 = texts(pieces, "C"); self.assertTrue(c1.startswith("표 12-1.")); self.assertTrue(c2.startswith("표 12-2."))
        n1, n2 = texts(pieces, "N"); self.assertIn("1→2 1,296건", n1); self.assertIn("불변 7,501건", n1); self.assertIn("검출 방식만 다르다", n2)

    def test_tables(self):
        t1 = MB.bridge_table1_rows(self.f)
        self.assertEqual(["구분", "목차 블록 기준", "실제 PDF 쪽 기준(2026-09-17 정본)", "차이"], MB.bridge_table1_header(self.f))
        self.assertEqual(["출현 총계", "11,517", "11,517", "0"], t1[0])
        self.assertEqual(["등급 1", "4,378 (38.0%)", "3,788 (32.9%)", "−590"], t1[1]); self.assertEqual("+613", t1[2][3]); self.assertEqual("−23", t1[3][3])
        self.assertEqual(["출현이 놓인 단위", "1,785 블록", "2,492 쪽", "—"], t1[4]); self.assertEqual(["등급이 바뀐 출현", "—", "4,016 (34.9%)", "—"], t1[5])
        t2 = MB.bridge_table2_rows(self.f)
        self.assertEqual(["구분", "이전 기준(쪽 단위, 2026-09-06)", "정본(쪽 단위, 2026-09-17)", "정본(출현 단위)"], MB.bridge_table2_header(self.f))
        self.assertEqual(6, len(t2)); self.assertEqual(["단위 수", "2,189쪽", "2,492쪽", "11,517건"], t2[1])
        self.assertEqual(["등급 3", "145 (6.6%)", "143 (5.7%)", "2,502 (21.7%)"], t2[4]); self.assertEqual(["두 집계가 공유하는 쪽", "2,035", "2,035 (등급 일치 2,035, 100.0%)", "—"], t2[5])
        self.assertIn("7,769행", t2[0][1])

    def test_branches(self):
        f = self.f
        # 동사: 등급 1 이 거의 같고, 등급 3 이 크게 늘었을 때
        b = with_bridge(f, real_grades={1: 4360, 2: 3000, 3: 4157})
        q1 = texts(MB.bridge_paragraphs(b), "P")[0]
        self.assertIn("으로 거의 같고", q1); self.assertIn("으로 줄었으며", q1); self.assertIn("으로 늘었다", q1)
        self.assertEqual(["거의 같고", "줄었으며", "늘었다"], [pc for pc in MB.bridge_paragraphs(b) if pc.kind == "P"][0].conditions["grade_verbs"])
        # 블록 → 쪽이 줄어든 경우 · 같은 경우
        self.assertIn("2,492쪽으로 줄었으며", texts(MB.bridge_paragraphs(with_bridge(f, block_pages=3000)), "P")[0])
        self.assertIn("2,492쪽으로 그대로였으며", texts(MB.bridge_paragraphs(with_bridge(f, block_pages=2492)), "P")[0])
        # 공유 쪽 일부 일치
        partial = with_bridge(f, shared_agree=2000)
        self.assertIn("2,035쪽 중 2,000쪽에서 일치한다(98.3%)", texts(MB.bridge_paragraphs(partial), "P")[1])
        self.assertIn("등급 일치 2,000, 98.3%", MB.bridge_table2_rows(partial)[5][2])
        # 출현 비율이 쪽 비율보다 크지 않으면 "몫" 문장 없음
        low = with_bridge(f, real_grades={1: 3788, 2: 7229, 3: 500})
        self.assertNotIn("몫이 커진다", texts(MB.bridge_paragraphs(low), "P")[1]); self.assertFalse([pc for pc in MB.bridge_paragraphs(low) if pc.kind == "P"][1].conditions["occurrence_share_exceeds_page_share"])
        # 소결 문장: 같은 수준 / 차이
        text, cond = MB.conclusion_sentence(f)
        self.assertIn("2,492쪽 중 143쪽(5.7%)", text); self.assertIn("2,189쪽 중 145쪽, 6.6%", text); self.assertIn("같은 수준이다", text); self.assertTrue(cond["level_same"])
        text2, cond2 = MB.conclusion_sentence(with_bridge(f, real_page_grades={1: 1825, 2: 424, 3: 243}))
        self.assertIn("차이가 있다", text2); self.assertFalse(cond2["level_same"])
        # 1절 교과서 문장
        self.assertEqual("교과서는 변환 시 쪽 표식이 실제 쪽이어서 쪽 배치 기준의 변경에 영향을 받지 않았다(1,207건; 388쪽 가운데 등급 3 8쪽).", MB.textbook_basis_sentence(f))
        # 경계값(갭 분석 G7): ±0.5pp 는 "거의 같았다", 그 밖은 방향; 표 12-1 차이 열의 합은 0; 분야 문자열은 개발·제조·장비·재료 순
        self.assertEqual(("거의 같았다", "거의 같았다", "늘었다", "줄었다"), (MB._trend(0.5), MB._trend(-0.5), MB._trend(0.51), MB._trend(-0.51)))
        deltas = [int(r[3].replace("−", "-").replace("+", "").replace(",", "")) for r in MB.bridge_table1_rows(f)[:4]]
        self.assertEqual(0, sum(deltas))
        q1 = texts(MB.bridge_paragraphs(f), "P")[0]
        self.assertLess(q1.index("반도체개발 "), q1.index("반도체제조 ")); self.assertLess(q1.index("반도체제조 "), q1.index("반도체장비 ")); self.assertLess(q1.index("반도체장비 "), q1.index("반도체재료 "))
        text3, cond3 = MB.conclusion_sentence(with_bridge(f, real_page_grades={1: 1825 - 25, 2: 524, 3: 168}))   # 168/2,492 = 6.74% vs 6.62% → 1.0pp 안
        self.assertTrue(cond3["level_same"])


def rezip(src: Path, dst: Path, transform) -> Path:
    """section0.xml 만 transform 으로 바꾼 HWPX 사본."""
    with zipfile.ZipFile(src) as z:
        xml = transform(z.read(HR.SECTION_ENTRY).decode("utf-8"))
        others = {n: z.read(n) for n in z.namelist() if n != HR.SECTION_ENTRY}
    with zipfile.ZipFile(dst, "w") as z:
        for n, data in others.items():
            z.writestr(n, data)
        z.writestr(HR.SECTION_ENTRY, xml)
    return dst


def dup_nth(xml: str, needle: str, n: int) -> str:
    """n번째 needle 을 두 번으로."""
    at = -1
    for _ in range(n):
        at = xml.index(needle, at + 1)
    return xml[:at] + needle + xml[at:]


def section_root(hwpx: Path) -> ET.Element:
    with zipfile.ZipFile(hwpx) as z:
        return ET.fromstring(z.read(HR.SECTION_ENTRY))


def stripped_texts(root: ET.Element) -> list[str]:
    return [HR.direct_text(p).strip() for p in HR.top_paragraphs(root)]


class Stage1TemplateTests(unittest.TestCase):
    def test_textbook_area_paragraph_carries_the_basis_sentence_only_on_real_pages(self):
        f = canonical_facts()
        entry = next(e for e in HR.textbook_paragraphs(f) if e[0] == "본 연구에서는 9권의 반도체 교과서를")
        self.assertIn(" " + MB.textbook_basis_sentence(f) + " 분야별로 설명하면", entry[1]); self.assertEqual("real", entry[2]["page_basis"])
        marker = dataclasses.replace(f, page_basis={"NCS": "marker", "교과서": "marker"})
        entry = next(e for e in HR.textbook_paragraphs(marker) if e[0] == "본 연구에서는 9권의 반도체 교과서를")
        self.assertNotIn("영향을 받지 않았다", entry[1]); self.assertEqual("marker", entry[2]["page_basis"])


class UntouchedCheckTests(unittest.TestCase):
    def test_untouched_paragraph_edit_is_detected_and_bookkept_edits_pass(self):
        root = sec(para("A"), para("B"), para("C"), para("D"))
        a, b, c, d = HR.top_paragraphs(root)
        snapshot = HR.snapshot_paragraphs(root)
        HR.set_text(b, "B2"); new = HR.clone_paragraph(a, "X"); HR.insert_after(root, b, [new]); HR.remove_paragraphs(root, [c])
        HR.check_untouched(root, snapshot, touched={id(b)}, inserted={id(new)}, removed={id(c)})           # 장부에 적힌 편집만 — 통과
        HR.set_text(d, "D2")
        with self.assertRaisesRegex(RuntimeError, "밖의 문단"):
            HR.check_untouched(root, snapshot, touched={id(b)}, inserted={id(new)}, removed={id(c)})
        root2 = sec(para("A")); (a2,) = HR.top_paragraphs(root2); snap2 = HR.snapshot_paragraphs(root2)
        root2.append(HR.clone_paragraph(a2, "몰래"))
        with self.assertRaisesRegex(RuntimeError, "밖의 문단"):
            HR.check_untouched(root2, snap2, touched=set(), inserted=set(), removed=set())


class Stage2EndToEndTests(unittest.TestCase):
    """fixture 전체(제2장 + 제3장)에 1·2단계를 돌린다 — 설계 §4 E2E."""

    def _run(self, td, force=False, src=None):
        f = canonical_facts()
        src = src or build_fixture_hwpx(Path(td) / "src.hwpx", stage1_body(f))
        render = shutil.which("magick") is not None
        out = Path(td) / "out.hwpx"
        diff = HR.refresh(src, f, out, Path(td) / "diff.json", Path(td) / "review" if render else None, render=render, text_review_dir=Path(td) / "text", force=force)
        return f, src, out, diff, render

    def test_refresh_runs_both_stages_and_audits(self):
        with tempfile.TemporaryDirectory() as td:
            f, src, out, diff, render = self._run(td)
            self.assertEqual("ok", diff["audit"]["status"], diff["audit"]); self.assertNotIn("out_of_scope", diff["audit"])
            m, b = diff["methods"], diff["bridge"]
            self.assertEqual({"rewritten": 6, "removed": 2}, m["toc"]); self.assertEqual({"caption_changed": True, "changed_cells": 2}, m["table4"])
            self.assertEqual(6, m["removed_paragraphs"]); self.assertEqual(20, len(m["inserted"])); self.assertEqual(2, len(m["rewritten"]))
            self.assertEqual([("표 5.", 8, 3), ("표 6.", 8, 3)], [(t["caption"], t["rows"], t["cols"]) for t in m["tables"]])
            self.assertEqual(15, len(b["inserted"]))                                                                  # 소결 문장(B+P 2개)은 conclusion_inserted 로 따로 센다
            self.assertEqual([("표 12-1.", 7, 4), ("표 12-2.", 7, 4)], [(t["caption"], t["rows"], t["cols"]) for t in b["tables"]])
            self.assertEqual({"rewritten": 1, "inserted": 2}, b["toc"]); self.assertEqual({"4) 소결": "6) 소결"}, b["renumbered"]); self.assertTrue(b["conclusion_inserted"])
            self.assertEqual("P", b["conclusion"]["kind"]); self.assertIn("2,492", b["conclusion"]["numbers"]); self.assertTrue(b["conclusion"]["keys"]); self.assertIn("level_same", b["conclusion"]["conditions"])
            for key in ("grade_verbs", "real_pages_vs_block", "shared_all_agree", "occurrence_share_exceeds_page_share", "level_same"):
                self.assertIn(key, b["conditions"])
            self.assertTrue(all(pc["numbers"] == [] or pc["keys"] for pc in m["inserted"] if pc["kind"] == "P"))      # 삽입 문단의 숫자는 전부 출처가 있다
            self.assertGreater(m["audited_tokens"], 30)
            # 결과 문서
            root = section_root(out); texts = stripped_texts(root)
            heads = [h.strip() for h in MB.METHODS_HEADINGS]
            self.assertEqual(2, texts.count(heads[0]))                                                                # 목차 + 본문
            body_5 = [HR.direct_text(p).strip() for p in HR.locate_range(root, HR.METHODS_HEADING, HR.CHAPTER_HEADING, 1).paragraphs]   # 본문 5절(목차 사본 아님)
            self.assertEqual(heads, [t for t in body_5 if t in heads]); self.assertEqual(6, sum(1 for t in body_5 if t in heads))
            for old in OLD_METHODS_TOC:
                self.assertNotIn(old.strip(), texts)
            self.assertNotIn("먼저 파일을 읽어 문장·표·제목을 구분하고 … 12,875건 85종", texts)
            self.assertIn("안전보건 수준은 각 출현이 놓인 실제 PDF 쪽(교과서는 쪽 표식이 가리키는 쪽)의 본문을 기준으로 세 등급으로 나누었다.", texts)
            self.assertEqual(1, texts.count("- 등급 1"))                                                             # 등급 목록은 그대로
            toc2 = [HR.direct_text(p) for p in HR.locate_toc_block(root, "2. NCS", "3. NCS")]
            self.assertEqual([MB.BRIDGE_HEADING, MB.CONCENTRATION_HEADING, MB.CONCLUSION_HEADING_NEW], toc2[-3:]); self.assertNotIn(" 4) 소결", toc2)
            self.assertEqual(1, texts.count("4) 소결")); self.assertEqual(2, texts.count("6) 소결"))                 # 1절 목차의 ' 4) 소결' 만 남고, ' 6) 소결' 은 목차 + 본문
            self.assertEqual(2, texts.count(MB.CONCENTRATION_HEADING.strip()))                                       # 3단계 소제목도 목차 + 본문
            ncs = HR.locate_sections(root)["ncs"]
            ncs_texts = [HR.direct_text(p) for p in ncs.paragraphs]
            self.assertIn(MB.BRIDGE_HEADING, ncs_texts); self.assertEqual(" 6) 소결", next(t for t in ncs_texts if t.strip().endswith("소결")))
            body_order = [t for t in ncs_texts if t in (MB.BRIDGE_HEADING, MB.CONCENTRATION_HEADING, MB.CONCLUSION_HEADING_NEW)]
            self.assertEqual([MB.BRIDGE_HEADING, MB.CONCENTRATION_HEADING, MB.CONCLUSION_HEADING_NEW], body_order)    # 4) → 5) → 6) 순서
            conc = diff["concentration"]
            self.assertEqual([MB.TABLE12_3_LABEL, MB.TABLE12_4_LABEL], [t["caption"] for t in conc["tables"]])
            self.assertEqual([(7, 4), (10, 4)], [(t["rows"] - 1, t["cols"]) for t in conc["tables"]])                 # 헤더 행 제외 7·10, 4열(표 12 원형)
            self.assertEqual(["LM1903060329", "LM1903060411"], conc["dedicated"])
            self.assertEqual({"dedicated_count", "rest_rate_direction", "group_majority", "zero_majority"}, set(conc["conditions"]))
            self.assertEqual(14, len(conc["inserted"]))
            ctrl = [p for p in ncs.paragraphs if p.find(f".//{HR.HP}ctrl") is not None]
            self.assertEqual(1, len(ctrl)); self.assertEqual(" 각주 뒤 글.", HR.direct_text(ctrl[0])[-8:])                 # 각주 문단은 손대지 않았다
            after_ctrl = ncs.paragraphs[ncs.paragraphs.index(ctrl[0]) + 1:ncs.paragraphs.index(ctrl[0]) + 3]
            self.assertEqual("", HR.direct_text(after_ctrl[0])); self.assertTrue(HR.direct_text(after_ctrl[1]).startswith("이상의 수치는 출현건수를 분모로"))   # 빈 문단 하나 뒤에 소결 문장
            ids = [t.get("id") for t in root.iter(f"{HR.HP}tbl")]
            self.assertEqual(len(ids), len(set(ids)))
            caps = [t for t in texts if t.startswith("표 12-")]
            self.assertEqual([MB.TABLE12_1_CAPTION, MB.TABLE12_2_CAPTION, MB.TABLE12_3_CAPTION, MB.table12_4_caption(f)], caps)   # 2단계 표 2 + 3단계 표 2
            ch1 = HR.locate_range(root, "1. 국내 반도체고등학교 교과서와 한국산업인력공단 NCS 교과서 분석", "2. 해외 기술 고등학교 교과서 비교·분석", 1)
            self.assertIn("NCS 교과서(86종)", HR.direct_text(HR.find_paragraph(ch1, "표 4.")))
            cells = [HR.direct_text(q) for p in ch1.paragraphs for q in p.iter(f"{HR.HP}p")]
            self.assertIn("반도체제조 13종", cells); self.assertIn("반도체재료 24종", cells); self.assertNotIn("반도체제조 14종", cells)
            for untouched in ("서론 12,875건 그대로", "해외 사례 본문 — 바뀌면 안 된다 85종", "4절 본문 — 바뀌면 안 된다 12,875건"):
                self.assertIn(untouched, texts)
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as z:
                self.assertEqual(a.namelist(), z.namelist())
            text_review = (Path(td) / "text" / "review_text.html").read_text(encoding="utf-8")
            self.assertIn("methods", text_review); self.assertIn("bridge", text_review); self.assertIn("먼저 파일을 읽어", text_review)
            self.assertIn("concentration", text_review); self.assertLess(text_review.index("bridge"), text_review.index("concentration"))   # 3단계 절도 있고 2단계 뒤에 온다
            if render:
                review = (Path(td) / "review" / "review.html").read_text(encoding="utf-8")
                for cap in ("표 4.", "표 5.", "표 6.", "표 12-1.", "표 12-2.", "표 12-3.", "표 12-4."):
                    self.assertIn(cap, review)
                self.assertNotIn("층화 추출", review)                                                                  # 검토본에 본문 문장 없음

    def test_stale_number_in_the_methods_section_stops_the_run(self):
        with tempfile.TemporaryDirectory() as td:
            f = canonical_facts()
            src = build_fixture_hwpx(Path(td) / "src.hwpx", stage1_body(f))
            stale = rezip(src, Path(td) / "stale.hwpx", lambda xml: xml.replace("- 등급 1</hp:t>", "- 등급 1 (813건)</hp:t>", 1))
            out = Path(td) / "out.hwpx"
            diff = HR.refresh(stale, f, out, Path(td) / "diff.json", None, render=False, text_review_dir=Path(td) / "text")
            self.assertEqual("failed", diff["audit"]["status"]); self.assertIn("813", diff["audit"]["unmatched"]); self.assertFalse(out.exists())

    def test_toc_with_other_than_eight_old_entries_is_refused(self):                                   # 갭 분석 G1
        with tempfile.TemporaryDirectory() as td:
            f = canonical_facts()
            src = build_fixture_hwpx(Path(td) / "src.hwpx", stage1_body(f))
            broken = rezip(src, Path(td) / "seven.hwpx", lambda xml: xml.replace(para(" 8) 검증과 한계 "), "", 1))
            with self.assertRaisesRegex(ValueError, "목차 5절 소제목이 7개"):
                HR.refresh(broken, f, Path(td) / "out.hwpx", Path(td) / "d.json", None, render=False, write_output=False)

    def test_audit_strips_stage2_notations_and_flags_stale_numbers(self):                            # 갭 분석 G3
        f = canonical_facts()
        self.assertEqual([], HR.audit_numbers(["표 12-1과 표 12-2, 2026-04 검색, v1 → v1fix → v2, 문자 3-gram 포함도, ±1쪽 이내, (4) 참조"], f))
        self.assertEqual([], HR.audited_numbers("v2는 도메인 검토의 결과이다. v1fix로 고친 뒤 v1과 비교"))                                 # 한글이 붙은 사전 판 표기도 벗긴다 (레드팀: \b 는 한글을 단어로 본다)
        self.assertEqual(["7", "2026"], HR.audited_numbers("v7 은 사전 판이 아니고 2026년은 연도 표기가 아니다"))
        self.assertEqual(["813", "1,847"], HR.audited_numbers("오래된 값 (813) 쪽, 이전 값 1,847) 참조, (4) 참조, 4) 소결"))                        # 두 자리 이상 괄호·번호 표기는 벗기지 않는다 (Claude 적대적 리뷰 1)
        self.assertEqual([], HR.audited_numbers("1. 자료 수집"))                                                                                # 표 5 셀 첫머리 번호는 수치가 아니다
        self.assertEqual(["12,875", "813", "813건", "85종"], HR.audit_numbers(["총 12,875건, 85종, 미확정 813건"], f))   # 85 는 코딩 표본 control 층(85쪽)과 겹치지만 "85종" 은 폐기 문구 목록(STALE_PATTERNS)이 잡는다 (Codex 적대적 리뷰)
        self.assertEqual(["페이지·구역"], HR.audit_numbers(["해당 출현에 연결된 페이지·구역의 판정값이다"], f))

    def test_load_facts_refuses_summary_without_grade_sources(self):                                    # 갭 분석 G5
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        del summary["corpora"]["교과서"]["grade_sources"]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "semantic_summary.json"; path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "grade_sources"):
                HR.load_facts(path, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)

    def test_force_overwrite_records_backup_and_previous_sha(self):
        with tempfile.TemporaryDirectory() as td:
            f, src, out, diff, render = self._run(td)
            self.assertIsNone(diff["runtime"]["backup"]); self.assertIsNone(diff["runtime"]["previous_output_identical"]); self.assertNotIn("previous_output_identical", diff["source"])
            first = out.read_bytes()
            with self.assertRaises(FileExistsError):
                self._run(td, src=src)
            f, src, out, diff, render = self._run(td, force=True, src=src)
            self.assertEqual(HR.sha256(first), diff["runtime"]["previous_hwpx_sha256"]); self.assertTrue(diff["runtime"]["backup"].endswith(".bak"))
            self.assertEqual(first, (out.parent / diff["runtime"]["backup"]).read_bytes())
            self.assertTrue(diff["runtime"]["previous_output_identical"]); self.assertEqual(first, out.read_bytes())           # 같은 입력 → 같은 바이트 (재실행 결정론)
            written = json.loads((Path(td) / "diff.json").read_text(encoding="utf-8"))
            self.assertNotIn("runtime", written); self.assertNotIn(".bak", json.dumps(written)); self.assertNotIn("previous_output_identical", json.dumps(written))   # 추적 JSON 에 실행 환경 없음 — 같은 입력이면 첫 실행이든 재실행이든 같은 파일

    def test_no_render_makes_no_backup(self):
        with tempfile.TemporaryDirectory() as td:
            f, src, out, diff, render = self._run(td)
            diff2 = HR.refresh(src, f, out, Path(td) / "dry.json", None, force=True, render=False, write_output=False)
            self.assertIsNone(diff2["runtime"]["backup"]); self.assertEqual([], [p for p in Path(td).iterdir() if p.name.endswith(".bak")])

    def test_refuses_its_own_output_as_input(self):
        with tempfile.TemporaryDirectory() as td:
            f, src, out, diff, render = self._run(td)
            with self.assertRaisesRegex(ValueError, "이미 2·3단계 산출물"):                                      # 갭 분석 G6 — 1단계 locator 실패보다 앞서 선제 거부
                HR.refresh(out, f, Path(td) / "again.hwpx", Path(td) / "d2.json", None, render=False, write_output=False)


class ConcentrationFactsTests(unittest.TestCase):
    """교재별 집중·편차 사실 — 정본 books[] 에서 파생 (ncs-book-concentration FR-04)."""

    def setUp(self):
        self.f = HR.load_facts(HR.DEFAULT_SUMMARY, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)

    def test_loads_canonical_concentration(self):
        c = self.f.concentration
        self.assertEqual((86, 11517, 2502), (c.books, c.total, c.grade3))
        self.assertEqual(["LM1903060329", "LM1903060411"], [b.code for b in c.dedicated])                 # D4: 제목에 '안전관리'
        self.assertEqual((2238, 965), (c.dedicated_total, c.dedicated_g3))
        self.assertEqual((84, 9279, 1537), (c.rest_books, c.rest_total, c.rest_g3))
        self.assertEqual((8.5, 0.0, 57), (round(c.mean_pct, 1), round(c.median_pct, 1), c.zero_books))
        self.assertEqual(10, len(c.top)); self.assertEqual("반도체 장비 안전관리", c.top[0].title); self.assertEqual(780, c.top[0].g[3])
        self.assertEqual(2015, sum(b.g[3] for b in c.top))
        equip = next(g for g in c.group_rows if g.name == "반도체장비")
        self.assertEqual((19, 3239, 1052, 18, 1608, 272, 780), (equip.books, equip.total, equip.g3, equip.rest_books, equip.rest_total, equip.rest_g3, equip.dedicated_g3))
        self.assertEqual(["반도체장비", "반도체재료"], [g.name for g in c.group_rows])                       # 전용 교재가 있는 분야만, 몫 큰 순

    def test_guards_bind_books_to_the_canonical_totals(self):
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        cases = {"교재 수": lambda s: s["corpora"]["NCS"]["books"].pop(),
                 "출현 합": lambda s: s["corpora"]["NCS"]["books"][0].__setitem__("total", 0),
                 "등급 3 합": lambda s: s["corpora"]["NCS"]["books"][0]["grades"].__setitem__("3", 9999),
                 "분야": lambda s: s["corpora"]["NCS"]["books"][0].__setitem__("group", "반도체제조"),
                 "groups\\[\\] 에 없는 분야": lambda s: s["corpora"]["NCS"]["books"][0].__setitem__("group", "Z"),   # 목록에 없는 분야 — 조용히 빠지는 대신 정지 (ship 적대적 리뷰)
                 "교재 등급 합": lambda s: (s["corpora"]["NCS"]["books"][0]["grades"].update({"1": s["corpora"]["NCS"]["books"][0]["grades"]["1"] + 1, "3": s["corpora"]["NCS"]["books"][0]["grades"]["3"] - 1}),
                                        s["corpora"]["NCS"]["books"][-1]["grades"].update({"1": s["corpora"]["NCS"]["books"][-1]["grades"]["1"] - 1, "3": s["corpora"]["NCS"]["books"][-1]["grades"]["3"] + 1})),   # 분야 사이 재배분 — 말뭉치 합·total 불변
                 "안전관리 전용": lambda s: s["corpora"]["NCS"]["books"][0].__setitem__("title", "반도체 안전관리 무엇")}
        for name, mutate in cases.items():
            with self.subTest(name=name):
                bad = json.loads(json.dumps(summary)); mutate(bad)
                with self.assertRaisesRegex(ValueError, name):
                    MB.load_concentration_facts(bad)
        old = json.loads(json.dumps(summary)); del old["corpora"]["NCS"]["books"]
        with self.assertRaisesRegex(ValueError, "2026-09-17 이후"):
            MB.load_concentration_facts(old)


class ConcentrationTemplateTests(unittest.TestCase):
    """교재별 집중 문단·표 — 값과 분기 (FR-05·FR-06·FR-07)."""

    def setUp(self):
        self.f = HR.load_facts(HR.DEFAULT_SUMMARY, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)

    def test_pieces_and_values(self):
        pieces = MB.concentration_paragraphs(self.f)
        self.assertEqual("HBPBCTNBCTNBPB", "".join(pc.kind for pc in pieces))   # 선행 B 없음 — 삽입 지점(2단계 블록의 끝 빈 문단)이 구분자다 (ship 적대적 리뷰, 중복 빈 문단 수정)
        self.assertEqual(MB.CONCENTRATION_HEADING, texts(pieces, "H")[0])
        p1, p2 = texts(pieces, "P")
        for needle in ("2,502건", "86권", "두 권", "2,238건", "965건", "38.6%", "21.7%", "16.6%", "84권", "반도체 장비 안전관리", "780건", "1,052건", "74.1%", "32.5%", "16.9%"):
            self.assertIn(needle, p1, needle)
        for needle in ("8.5%", "0.0%", "57권", "66.3%", "과반", "21.7%"):
            self.assertIn(needle, p2, needle)
        t3, t4 = [pc for pc in pieces if pc.kind == "T"]
        self.assertEqual(4, len(t3.header)); self.assertEqual(7, len(t3.rows))
        self.assertEqual(["NCS 전체", "86", "11,517 (2,502)", "21.7%"], list(t3.rows[0]))
        self.assertEqual(["안전관리 전용 교재", "2", "2,238 (965)", "43.1%"], list(t3.rows[1]))
        self.assertEqual(["전용 교재 제외", "84", "9,279 (1,537)", "16.6%"], list(t3.rows[2]))
        self.assertEqual((4, 10), (len(t4.header), len(t4.rows)))
        self.assertEqual(["반도체 장비 안전관리 (장비)", "1,631", "780", "47.8%"], list(t4.rows[0]))
        notes = texts(pieces, "N")
        self.assertIn("제목에 ‘안전관리’를 포함하는 두 권", notes[0]); self.assertIn("2,015건", notes[1]); self.assertIn("80.5%", notes[1])
        self.assertTrue(all(pc.text.strip() for pc in pieces if pc.kind in ("H", "P", "C", "N")))

    def test_branches(self):
        f = self.f
        one = with_concentration(f, dedicated=f.concentration.dedicated[:1], dedicated_total=1631, dedicated_g3=780,
                                 rest_books=85, rest_total=9886, rest_g3=1722)
        self.assertIn("한 권", texts(MB.concentration_paragraphs(one), "P")[0])
        third = dataclasses.replace(f.concentration.top[2], title="반도체 공정 안전관리", group="반도체장비")                 # 세 번째 전용 교재를 가정한다
        three = with_concentration(f, dedicated=f.concentration.dedicated + (third,), dedicated_total=2238 + third.total, dedicated_g3=965 + third.g[3],
                                   rest_books=83, rest_total=9279 - third.total, rest_g3=1537 - third.g[3])
        p_three = texts(MB.concentration_paragraphs(three), "P")[0]
        self.assertIn("세 권(", p_three); self.assertIn("이 세 권을 제외한 83권", p_three); self.assertIn("반도체 공정 안전관리", p_three)   # 3권 수사 + 분야 문장의 전용 교재 나열
        self.assertEqual(3, [pc.conditions for pc in MB.concentration_paragraphs(three) if pc.kind == "P"][0]["dedicated_count"])
        self.assertIn("반도체 장비 안전관리·반도체 공정 안전관리의 등급 3", p_three)                                        # 같은 분야의 전용 교재 두 권이 '·' 로 이어진다
        up = with_concentration(f, rest_g3=2400, rest_total=9279)                                          # 제외해도 비율이 오른다
        p_up = texts(MB.concentration_paragraphs(up), "P")[0]
        self.assertIn("올라간다", p_up); self.assertNotIn("내려간다", p_up)
        same = with_concentration(f, rest_g3=int(round(0.217 * 9279)), rest_total=9279)
        self.assertIn("거의 같다", texts(MB.concentration_paragraphs(same), "P")[0])
        # 경계값(커버리지 감사) — _trend 의 ±0.5pp(BRIDGE_SAME_PP) 관행과 같되, 위 fixture 들은 정확히 그 경계를 보장하지 않는다: 직접 호출로 고정한다
        self.assertEqual(("거의 같다", "거의 같다", "내려간다", "올라간다"),
                         (MB._rate_direction(20.0, 20.5), MB._rate_direction(20.5, 20.0), MB._rate_direction(20.0, 20.51), MB._rate_direction(20.51, 20.0)))
        small = with_concentration(f, group_rows=tuple(dataclasses.replace(g, dedicated_g3=100) for g in f.concentration.group_rows))
        p_small = texts(MB.concentration_paragraphs(small), "P")[0]
        self.assertNotIn("과반이며", p_small)
        few = with_concentration(f, zero_books=10)
        self.assertIn("과반에 못 미친다", texts(MB.concentration_paragraphs(few), "P")[1])
        conds = [pc.conditions for pc in MB.concentration_paragraphs(f) if pc.kind == "P"]
        self.assertEqual({"dedicated_count", "rest_rate_direction", "group_majority"}, set(conds[0]))
        self.assertEqual({"zero_majority"}, set(conds[1]))

    def test_group_share_with_zero_grade3_does_not_divide_by_zero(self):
        """분야 등급 3 합이 0 인 경우(실제 정본에는 없는 경로) — share = 100*dedicated_g3/g3 if g3 else 0.0 분기, ZeroDivisionError 없이 비과반으로 (커버리지 감사)."""
        f = self.f
        zeroed = tuple(dataclasses.replace(g, g3=0, dedicated_g3=0, rest_g3=0) for g in f.concentration.group_rows)
        zero = with_concentration(f, group_rows=zeroed)
        pieces = MB.concentration_paragraphs(zero)                     # ZeroDivisionError 를 던지면 여기서 실패한다
        p1 = texts(pieces, "P")[0]
        self.assertNotIn("과반이며", p1)
        conds = [pc.conditions for pc in pieces if pc.kind == "P"][0]
        self.assertEqual({g.name: False for g in f.concentration.group_rows}, conds["group_majority"])

    def test_every_number_has_a_source_key(self):
        f = self.f
        index = f.value_index()
        for pc in MB.concentration_paragraphs(f):
            texts_to_audit = [pc.text] + [cell for row in pc.rows for cell in row] + list(pc.header)
            for text in texts_to_audit:
                for token in HR.audited_numbers(text):
                    self.assertIn(token, index, f"{token} ← {text[:40]}")


class ReviewGuardTests(unittest.TestCase):
    """ship 리뷰(테스트·레드팀·보안)가 지목한 가드·분기 — 사실 적재, XML 능력, 장부, 문서 형태 가드, main 출력."""

    def setUp(self):
        self.f = canonical_facts()

    def test_methods_facts_csv_and_lineage_guards(self):
        with tempfile.TemporaryDirectory() as td:
            for name, header, rows, regex in (("nocols.csv", "교재,쪽\n", ["A,1\n"], "구라벨"), ("empty.csv", "교재,구라벨\n", ["A,\n"], "구라벨 값"), ("short.csv", "교재,구라벨\n", ["A,1\n"], "행 수")):
                with self.subTest(name=name):
                    path = Path(td) / name; path.write_text(header + "".join(rows), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, regex):
                        MB.load_methods_facts(dataclasses.replace(MB.MethodsPaths(), reseg_csv=path))
            impact = json.loads((DATA / "expression_review_impact.json").read_text(encoding="utf-8")); impact["totals"]["v2"]["NCS"] = 11516
            other = Path(td) / "ri.json"; other.write_text(json.dumps(impact, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "totals.v2"):
                MB.load_methods_facts(dataclasses.replace(MB.MethodsPaths(), review_impact=other))
            scores = json.loads((DATA / "expression_review_scores.json").read_text(encoding="utf-8")); scores["meta"]["sample_digest"] = "0000000000000000"
            other = Path(td) / "sc.json"; other.write_text(json.dumps(scores, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sample_digest"):
                MB.load_methods_facts(dataclasses.replace(MB.MethodsPaths(), review_scores=other))
            scores["meta"]["sample_digest"] = json.loads((DATA / "expression_review_key.json").read_text(encoding="utf-8"))["sample_digest"]; scores["meta"]["adopted"] = "v1fix"
            other.write_text(json.dumps(scores, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "adopted"):
                MB.load_methods_facts(dataclasses.replace(MB.MethodsPaths(), review_scores=other))

    def test_bridge_facts_page_grade_sum_and_shared_bounds(self):
        impact = json.loads((DATA / "occurrence_real_pages_impact.json").read_text(encoding="utf-8"))
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            bad = json.loads(json.dumps(impact)); bad["pages"]["real_page_grades"]["3"] = 142
            other = Path(td) / "impact.json"; other.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "real_page_grades"):
                MB.load_bridge_facts(dataclasses.replace(MB.MethodsPaths(), impact=other))
            bad = json.loads(json.dumps(impact)); bad["pages"]["교과서"]["page_grades"]["3"] = 9
            other.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "교과서.page_grades 합"):
                MB.load_bridge_facts(dataclasses.replace(MB.MethodsPaths(), impact=other))
            bad = json.loads(json.dumps(impact)); del bad["pages"]["real_page_grades"]
            other.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "2026-09-16 이후"):
                MB.load_bridge_facts(dataclasses.replace(MB.MethodsPaths(), impact=other))
            for pages, agree in ((0, 0), (2035, 2036), (3000, 3000)):
                with self.subTest(pages=pages, agree=agree):
                    summary["meta"]["run"]["reseg_agreement"] = {"pages": pages, "agree": agree}
                    with self.assertRaisesRegex(ValueError, "reseg_agreement"):
                        MB.load_bridge_facts(MB.MethodsPaths(), summary=summary)

    def test_impact_input_lineage_and_textbook_totals_are_bound_to_the_canonical_run(self):
        """영향표는 대응표 지문만이 아니라 정본 run.inputs 의 지문 4종(워크북 2·마크다운 2)·사전, 그리고 교과서 총계·등급까지 정본과 같아야 한다 (CodeRabbit PR #18)."""
        impact = json.loads((DATA / "occurrence_real_pages_impact.json").read_text(encoding="utf-8"))
        cases = {"meta.inputs.source_workbook": lambda d: d["meta"]["inputs"].__setitem__("source_workbook", "0" * 64),
                 "meta.inputs.school_grade_workbook": lambda d: d["meta"]["inputs"].__setitem__("school_grade_workbook", "0" * 64),
                 "meta.inputs.ncs_markdown": lambda d: d["meta"]["inputs"].__setitem__("ncs_markdown", "0" * 64),
                 "meta.inputs.school_markdown": lambda d: d["meta"]["inputs"].__setitem__("school_markdown", "0" * 64),
                 "meta.inputs.school_markdown 이 없습니다": lambda d: d["meta"]["inputs"].__delitem__("school_markdown"),
                 "meta.dictionary": lambda d: d["meta"].__setitem__("dictionary", "v1fix"),
                 "totals.교과서": lambda d: d["totals"].__setitem__("교과서", d["totals"]["교과서"] + 1),
                 "grades.real.교과서": lambda d: (d["grades"]["real"]["교과서"].__setitem__("1", d["grades"]["real"]["교과서"]["1"] - 1), d["grades"]["real"]["교과서"].__setitem__("2", d["grades"]["real"]["교과서"]["2"] + 1))}
        with tempfile.TemporaryDirectory() as td:
            for name, mutate in cases.items():
                with self.subTest(name=name):
                    bad = json.loads(json.dumps(impact)); mutate(bad)
                    other = Path(td) / "impact.json"; other.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, name.split(" ")[0]):
                        MB.load_bridge_facts(dataclasses.replace(MB.MethodsPaths(), impact=other))
        MB.load_bridge_facts()                                                                                        # 정본 파일끼리는 통과

    def test_impact_invariants_and_coding_key_digest_guards(self):
        impact = json.loads((DATA / "occurrence_real_pages_impact.json").read_text(encoding="utf-8"))
        cases = {"등급 합": lambda d: d["grades"]["real"]["NCS"].__setitem__("2", 5228), "transition": lambda d: d["transition"].__setitem__("moved", 4015), "groups": lambda d: d["groups"]["반도체개발"]["real"].__setitem__("3", 121)}
        with tempfile.TemporaryDirectory() as td:
            for name, mutate in cases.items():
                with self.subTest(name=name):
                    bad = json.loads(json.dumps(impact)); mutate(bad)
                    if name == "등급 합":
                        bad["pages"]["real_page_grades"]["2"] = 524                                                   # real_pages 합 가드가 아니라 등급 합 가드가 잡히게
                    other = Path(td) / "impact.json"; other.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, name if name != "등급 합" else "다릅니다"):
                        MB.load_bridge_facts(dataclasses.replace(MB.MethodsPaths(), impact=other))
            key = json.loads((HERE / "coding_key.json").read_text(encoding="utf-8")); key["sample_digest"] = "ffffffffffffffff"
            other = Path(td) / "coding_key.json"; other.write_text(json.dumps(key), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sample_digest"):
                MB.load_methods_facts(dataclasses.replace(MB.MethodsPaths(), coding_key=other))

    def test_zip_caps_and_image_size_are_refused(self):
        with self.assertRaisesRegex(ValueError, "상한"):
            HR.image_dimensions(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (50000).to_bytes(4, "big") + (10).to_bytes(4, "big"))
        with tempfile.TemporaryDirectory() as td:
            bomb = Path(td) / "bomb.hwpx"
            with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr(HR.SECTION_ENTRY, b"\x00" * (2 * 1024 * 1024))                                            # 2 MB 의 0 → 비율 수천 배
            with self.assertRaisesRegex(ValueError, "압축 비율"):
                HR.read_section(bomb)

    def test_p2b_branches_on_adjudication_versions_and_coder_families(self):
        f = self.f
        p2b = texts(MB.methods_paragraphs(f), "P")[2]
        self.assertIn("두 차례 개정하였다(v1 → v1fix → v2). v2는", p2b); self.assertIn("불일치 17건은 연구책임자가 재정하였다", p2b); self.assertIn("서로 다른 계열의 AI 코더 둘", p2b)
        partial = with_methods(f, review_adjudicated=10, review_versions=("v1", "v2", "v3", "v4"), review_family_warning="same family", recoding_family_warning="same family")
        pieces = MB.methods_paragraphs(partial); p2b2, p4 = texts(pieces, "P")[2], texts(pieces, "P")[4]
        self.assertIn("세 차례 개정하였다(v1 → v2 → v3 → v4). v4는", p2b2); self.assertIn("불일치 17건 중 10건을 연구책임자가 재정하였다", p2b2); self.assertIn("같은 계열의 AI 코더 둘", p2b2)
        self.assertNotIn("서로 다른 계열", p4)
        conds = [pc.conditions for pc in pieces if pc.kind == "P"]
        self.assertEqual((3, False, False), (conds[2]["revisions"], conds[2]["all_adjudicated"], conds[2]["review_two_families"])); self.assertFalse(conds[4]["recoding_two_families"])

    def test_load_facts_guards_and_methods_paths_override(self):
        summary = json.loads(HR.DEFAULT_SUMMARY.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "semantic_summary.json"
            no_pages = json.loads(json.dumps(summary)); del no_pages["corpora"]["NCS"]["detected_pages"]; path.write_text(json.dumps(no_pages, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "detected_pages"):
                HR.load_facts(path, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)
            no_new = json.loads(json.dumps(summary)); del no_new["corpora"]["교과서"]["grade_sources"]["new"]; path.write_text(json.dumps(no_new, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "grade_sources"):
                HR.load_facts(path, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT)
            f = HR.load_facts(HR.DEFAULT_SUMMARY, HR.DEFAULT_CASES, HR.DEFAULT_RECOUNT, methods_paths=dataclasses.replace(MB.MethodsPaths(), summary=Path(td) / "nonexistent.json"))
            self.assertEqual(11517, f.bridge.total)                                                             # summary 경로는 load_facts 의 인자가 이긴다

    def test_xml_helper_error_branches_and_child_elements(self):
        root = sec(para("A"), para("B"))
        a, b = HR.top_paragraphs(root)
        with self.assertRaisesRegex(ValueError, "최상위"):
            HR.insert_after(root, a.find(f"{HR.HP}run"), [])
        with self.assertRaisesRegex(ValueError, "hp:tbl"):
            HR.clone_table_paragraph(a, [["x"]], 1, None, (1, 1))
        with self.assertRaisesRegex(ValueError, "끝 제목"):
            HR.locate_range(sec(para("A"), para("A")), "A", "Z", 1)
        with self.assertRaisesRegex(ValueError, "뒤에"):
            HR.locate_toc_block(sec(para("2. NCS")), "2. NCS", "3. NCS")
        tabbed = ET.fromstring(f"<hs:sec {NS}>" + '<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="1" columnBreak="0" merged="0"><hp:run charPrIDRef="10"><hp:t>제목<hp:tab width="1" leader="0" type="LEFT"/>12</hp:t></hp:run></hp:p>' + "</hs:sec>")
        (tp,) = HR.top_paragraphs(tabbed)
        self.assertEqual("제목12", HR.direct_text(tp))                                                          # 탭 뒤 쪽 번호가 보인다 (감사·locator 에 들어간다)
        with self.assertRaisesRegex(ValueError, "탭"):
            HR.set_text(tp, "새 글")
        clone = HR.clone_paragraph(a, "x"); self.assertEqual(("0", "0"), (clone.get("pageBreak"), clone.get("columnBreak")))
        with_rect = sec(table([["a"]], tid="5", zorder="2") + '<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13"><hp:rect id="77" zOrder="9"/></hp:run></hp:p>')
        self.assertEqual((78, 10), HR.next_object_ids(with_rect))                                                 # 표·그림 아닌 개체(도형)의 id/zOrder 도 센다

    def test_check_untouched_flags_unremoved_and_reordered_paragraphs(self):
        root = sec(para("A"), para("B"), para("C"))
        a, b, c = HR.top_paragraphs(root); snap = HR.snapshot_paragraphs(root)
        with self.assertRaisesRegex(RuntimeError, "삭제했다고"):
            HR.check_untouched(root, snap, touched=set(), inserted=set(), removed={id(c)})
        root.remove(c); root.insert(0, c)
        with self.assertRaisesRegex(RuntimeError, "순서가 다르거나"):
            HR.check_untouched(root, snap, touched=set(), inserted=set(), removed=set())

    def test_ledger_touch_object_covers_inserted_elements_and_refuses_strangers(self):
        root = sec(para("A"), table([["h"], ["v"]], tid="3"))
        a, t = HR.top_paragraphs(root)
        L = HR._Ledger(root, self.f, set(), set(), set(), [])
        L.insert(a, [MB.Piece("T", rows=(("x",),), header=("h",))], {"T": t}, "bridge")
        new_tbl = HR.top_paragraphs(root)[1].find(f".//{HR.HP}tbl")
        L.touch_object(new_tbl)                                                                                   # 삽입한 표는 장부가 안다
        self.assertIn(id(HR.top_paragraphs(root)[1]), L.touched)
        with self.assertRaisesRegex(ValueError, "장부에 없는"):
            L.touch_object(ET.Element("x"))

    def test_document_shape_guards(self):
        f = self.f
        cases = [("표 4 에서", lambda xml: xml.replace(para("반도체개발 30종", "17"), "", 1)),
                 ("목차 2절 블록에", lambda xml: dup_nth(xml, para(" 4) 소결"), 2)),                                 # 목차의 두 번째 ' 4) 소결' = 2절 항목 (첫 번째는 1절)
                 ("빈 문단이 아닙니다", lambda xml: xml.replace("일관된 기준으로 확인하기 위한 절차이다.</hp:t></hp:run><hp:linesegarray><hp:lineseg textpos=\"0\"/></hp:linesegarray></hp:p>" + HR.MB.__name__ * 0 + '<hp:p id="0" paraPrIDRef="25"', "일관된 기준으로 확인하기 위한 절차이다.</hp:t></hp:run><hp:linesegarray><hp:lineseg textpos=\"0\"/></hp:linesegarray></hp:p>" + para("끼어든 글") + '<hp:p id="0" paraPrIDRef="25"', 1)),
                 ("본문 원형", lambda xml: xml.replace(para("본 연구는 반도체 기술 고등학교 교과서의 안전보건교육 내용을 체계적으로 분석하여 구조적 한계를 확인하였다."), "", 1).replace(para("반도체고등학교의 안전보건교육이 양적으로 일부 포함되어 있음에도 한계를 가지고 있음을 보여준다."), "", 1)),
                 ("이미 2·3단계 산출물", lambda xml: xml.replace(para(" 8) 검증과 한계 "), para(" 8) 검증과 한계 ") + para(MB.BRIDGE_HEADING), 1))]
        with tempfile.TemporaryDirectory() as td:
            src = build_fixture_hwpx(Path(td) / "src.hwpx", stage1_body(f))
            for regex, transform in cases:
                with self.subTest(regex=regex):
                    broken = rezip(src, Path(td) / f"{abs(hash(regex))}.hwpx", transform)
                    with self.assertRaisesRegex(ValueError, regex):
                        HR.refresh(broken, f, Path(td) / "out.hwpx", Path(td) / "d.json", None, render=False, write_output=False)
            with self.assertRaisesRegex(ValueError, "2·3단계"):
                HR.refresh(src, dataclasses.replace(f, page_basis={"NCS": "marker", "교과서": "marker"}), Path(td) / "out.hwpx", Path(td) / "d.json", None, render=False, write_output=False)
            with self.assertRaisesRegex(ValueError, "찾지 못"):
                HR.refresh(build_fixture_hwpx(Path(td) / "noch2.hwpx", stage1_body(f), chapter2=False), f, Path(td) / "out.hwpx", Path(td) / "d.json", None, render=False, write_output=False)
            self.assertFalse((Path(td) / "out.hwpx").exists())

    def test_methods_removal_range_blank_and_header_guards(self):
        f = self.f
        with tempfile.TemporaryDirectory() as td:
            src = build_fixture_hwpx(Path(td) / "src.hwpx", stage1_body(f))
            intruder = rezip(src, Path(td) / "intruder.hwpx", lambda xml: xml.replace(para("파일과 검색어는 한글의 띄어쓰기나 컴퓨터 저장 방식이 달라도 같은 말로 인식되도록 정리한 뒤 검색하였다."),
                                                                                         para("끼어든 소제목 12,875건") + para("파일과 검색어는 한글의 띄어쓰기나 컴퓨터 저장 방식이 달라도 같은 말로 인식되도록 정리한 뒤 검색하였다."), 1))
            with self.assertRaisesRegex(ValueError, "예상 밖 문단"):
                HR.refresh(intruder, f, Path(td) / "out.hwpx", Path(td) / "d.json", None, render=False, write_output=False)
        ctrl_only = sec('<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="13"><hp:ctrl><hp:colPr/></hp:ctrl></hp:run></hp:p>', para(""))
        ctrl_p, empty_p = HR.top_paragraphs(ctrl_only)
        self.assertFalse(HR._is_blank(ctrl_p)); self.assertTrue(HR._is_blank(empty_p))                                    # 단 정의만 든 문단은 간격 원형이 아니다 (Claude 적대적 리뷰 4)
        root = sec(table([["h1", "h2"], ["a", "b"]], tid="9"))
        tbl = HR.top_paragraphs(root)[0].find(f".//{HR.HP}tbl")
        with self.assertRaisesRegex(ValueError, "헤더 열 수"):
            HR.fill_table(tbl, [["x", "y"]], 1, ["h1", "h2", "h3"])
        impact = json.loads((DATA / "expression_review_impact.json").read_text(encoding="utf-8")); impact["meta"]["versions"] = ["v2"]
        with tempfile.TemporaryDirectory() as td:
            other = Path(td) / "ri.json"; other.write_text(json.dumps(impact, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "versions"):
                MB.load_methods_facts(dataclasses.replace(MB.MethodsPaths(), review_impact=other))

    def test_main_prints_the_backup_line_on_force(self):
        import contextlib, io
        from unittest import mock
        out = io.StringIO()
        def fake(hwpx, facts, o, d, r, **kw):
            return {"paragraphs": [], "tables": [], "figures": [], "audit": {"tokens": 0, "unmatched": []}, "source": {},
                    "runtime": {"backup": "x.hwpx.deadbeef.bak", "previous_hwpx_sha256": "0" * 64, "previous_output_identical": True}}
        with tempfile.TemporaryDirectory() as td, mock.patch.object(HR, "refresh", fake), contextlib.redirect_stdout(out):
            self.assertEqual(0, HR.main(["--hwpx", "x.hwpx", "--text-review-dir", td, "--out", str(Path(td) / "o.hwpx"), "--diff-out", str(Path(td) / "d.json"), "--review-dir", td]))
        self.assertIn("기존 파일 보존: x.hwpx.deadbeef.bak", out.getvalue()); self.assertIn("같음", out.getvalue())


if __name__ == "__main__":
    unittest.main()
