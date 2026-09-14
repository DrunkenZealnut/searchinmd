"""expression_review.py 단위 테스트 — 표본·키·정밀도·최종 라벨·영향표. 실데이터 없이 fixture 로 돈다."""

import json
import math
import tempfile
import unittest
from pathlib import Path

import expression_review as ER
import semantic_keyword_recount as SKR
from semantic_keyword_recount import Document, GradeAssignment, grade_lookup_key


def _doc(rel, text, corpus="NCS"):
    return Document(corpus, Path(rel), rel, text)


NCS_TEXT = "\n".join(
    ["<!-- page: 1 -->", "클린룸 입장 전 방진복을 착용한다", "방진복 세탁 주기는 주 1회", "", "가연성 가스 누출 시 대피"]
    + [f"방진복 규격 {i}" for i in range(40)]
    + ["<!-- page: 2 -->", "자외선 노출 주의", "X선 회절 분석 장비"]
) + "\n"
SCHOOL_TEXT = "<!-- page: 1 -->\n방진복 착용법\n가연성 물질 보관\n자외선 램프 점검\n"
FIXTURE_DOCS = [_doc("반도체제조/LM1903060101_a/a.md", NCS_TEXT), _doc("book/s.md", SCHOOL_TEXT, corpus="교과서")]
TARGETS = (("보호구", "방진복"), ("인화", "가연성"), ("방사선", "자외선"))


class SampleTests(unittest.TestCase):
    def test_collect_records_probes_held_targets_without_counting_them(self):
        records = ER.collect_records(FIXTURE_DOCS, TARGETS)
        held = [r for r in records if r.expression == "자외선"]
        self.assertEqual(2, len(held))                                       # NCS 1 + 교과서 1
        self.assertTrue(all(r.probe for r in held))                          # 보류 표현은 probe 로만
        self.assertEqual(43, sum(1 for r in records if r.expression == "방진복" and not r.probe))

    def test_sample_is_deterministic_and_stratified_and_takes_all_below_cap(self):
        records = ER.collect_records(FIXTURE_DOCS, TARGETS)
        a = ER.build_sample(records, TARGETS, seed=7, per_expression=10)
        b = ER.build_sample(records, TARGETS, seed=7, per_expression=10)
        self.assertEqual([i["id"] for i in a], [i["id"] for i in b])
        self.assertNotEqual([(i["path"], i["line"]) for i in a], [(i["path"], i["line"]) for i in ER.build_sample(records, TARGETS, seed=8, per_expression=10)])
        by_expr = {}
        for item in a:
            by_expr.setdefault(item["expression"], []).append(item)
        self.assertEqual(10, len(by_expr["방진복"]))
        self.assertEqual({"NCS": 9, "교과서": 1}, {c: sum(1 for i in by_expr["방진복"] if i["corpus"] == c) for c in ("NCS", "교과서")})   # 42:1 비례, 최소 1
        self.assertEqual(2, len(by_expr["가연성"]))                            # 10 미만 → 전수
        self.assertEqual(2, len(by_expr["자외선"]))
        self.assertTrue(all(i["id"].startswith("E") for i in a))

    def test_window_marks_expression_and_keeps_neighbours(self):
        records = ER.collect_records(FIXTURE_DOCS, TARGETS)
        first = next(r for r in records if r.expression == "방진복" and r.line == 2)
        text = ER.window_text(FIXTURE_DOCS[0], first)
        self.assertEqual("클린룸 입장 전 «방진복»을 착용한다\n방진복 세탁 주기는 주 1회", text)   # 앞줄은 마커라 제외, 뒷줄 포함
        second = next(r for r in records if r.expression == "방진복" and r.line == 3)
        self.assertEqual(2, len(ER.window_text(FIXTURE_DOCS[0], second).split("\n")))     # 뒷줄이 빈 줄이라 제외
        middle = next(r for r in records if r.expression == "방진복" and r.line == 7)
        self.assertEqual(3, len(ER.window_text(FIXTURE_DOCS[0], middle).split("\n")))

    def test_sheet_has_no_anchoring_fields_and_key_has_no_text(self):
        records = ER.collect_records(FIXTURE_DOCS, TARGETS)
        items = ER.build_sample(records, TARGETS, seed=1, per_expression=5)
        sheet, key = ER.sheet_and_key(items, FIXTURE_DOCS)
        blob = json.dumps(sheet, ensure_ascii=False)
        for banned in ("계층", "tier", "판정 근거", "rationale", "등급", "grade", "probe", "decision"):
            self.assertNotIn(banned, blob, banned)
        self.assertIn("coder_prompt", sheet)
        self.assertTrue(all(set(i) == {"id", "keyword", "expression", "text"} for i in sheet["items"]))
        self.assertTrue(all("text" not in i and len(i["text_sha256"]) == 64 for i in key["items"]))
        self.assertEqual(sheet["sample_digest"], key["sample_digest"])
        self.assertEqual(ER.sample_digest(key["items"]), key["sample_digest"])
        self.assertNotIn("/Users/", json.dumps(key))

    def test_write_sample_refuses_to_overwrite_key_without_force(self):
        records = ER.collect_records(FIXTURE_DOCS, TARGETS)
        items = ER.build_sample(records, TARGETS, seed=1, per_expression=5)
        with tempfile.TemporaryDirectory() as td:
            sheet_path, key_path = Path(td) / "sheet.json", Path(td) / "key.json"
            ER.write_sample(items, sheet_path, key_path, documents=FIXTURE_DOCS)
            self.assertTrue((Path(td) / "sheet.md").exists())
            with self.assertRaises(FileExistsError):
                ER.write_sample(items, sheet_path, key_path, documents=FIXTURE_DOCS)
            ER.write_sample(items, sheet_path, key_path, documents=FIXTURE_DOCS, force=True)


class ScoreTests(unittest.TestCase):
    def test_precision_interval_matches_known_values(self):
        lo, hi = ER.precision_interval(0, 30)
        self.assertEqual(0.0, lo); self.assertAlmostEqual(0.1157, hi, places=3)
        lo, hi = ER.precision_interval(30, 30)
        self.assertAlmostEqual(0.8843, lo, places=3); self.assertEqual(1.0, hi)
        lo, hi = ER.precision_interval(27, 30)
        self.assertAlmostEqual(0.7347, lo, places=3); self.assertAlmostEqual(0.9789, hi, places=3)
        with self.assertRaises(ValueError):
            ER.precision_interval(0, 0)

    def test_final_label_rules(self):
        ids = ["E1", "E2", "E3", "E4", "E5"]
        a = {"E1": 1, "E2": 1, "E3": 2, "E4": "?", "E5": 1}
        b = {"E1": 1, "E2": 2, "E3": 2, "E4": 1, "E5": 2}
        adj = {"E2": 2}
        got = ER.final_labels(ids, a, b, adj)
        self.assertEqual({"E1": 1, "E2": 2, "E3": 2, "E4": "?", "E5": "?"}, got)     # 일치 / 불일치+재정 / 일치 / ? / 불일치 미재정

    def test_score_flags_candidates_below_floor_and_has_no_nan(self):
        key = {"sample_digest": "d", "items": [{"id": f"E{i}", "keyword": "보호구", "expression": "방진복"} for i in range(10)]
                                             + [{"id": f"F{i}", "keyword": "인화", "expression": "가연성"} for i in range(4)]}
        a = {"grades": {**{f"E{i}": 1 for i in range(10)}, **{f"F{i}": (1 if i < 3 else 2) for i in range(4)}}, "meta": {"model": "claude-x"}}
        b = {"grades": {**{f"E{i}": (1 if i < 6 else 2) for i in range(10)}, **{f"F{i}": (1 if i < 3 else 2) for i in range(4)}}, "meta": {"model": "gpt-y"}}
        scores = ER.score(key, a, b, adj={"labels": {f"E{i}": 2 for i in range(6, 10)}, "sample_digest": "d"}, floor=0.8)
        rows = {r["expression"]: r for r in scores["expressions"]}
        self.assertEqual((10, 6), (rows["방진복"]["n"], rows["방진복"]["k"]))
        self.assertEqual("hold_or_conditional", rows["방진복"]["candidate"])
        self.assertEqual(4, rows["방진복"]["disagreements"])
        self.assertEqual("keep" if rows["가연성"]["lower"] >= 0.8 else "hold_or_conditional", rows["가연성"]["candidate"])
        self.assertFalse(any(isinstance(v, float) and math.isnan(v) for r in scores["expressions"] for v in r.values()))
        self.assertEqual(0.8, scores["meta"]["floor"])
        self.assertIn("kappa", scores["overall"])

    def test_adj_file_is_validated(self):
        key = {"sample_digest": "d", "items": [{"id": "E1", "keyword": "k", "expression": "e"}]}
        with self.assertRaises(ValueError):
            ER.validate_adj({"sample_digest": "x", "labels": {"E1": 1}}, key)
        with self.assertRaises(ValueError):
            ER.validate_adj({"sample_digest": "d", "labels": {"E9": 1}}, key)
        with self.assertRaises(ValueError):
            ER.validate_adj({"sample_digest": "d", "labels": {"E1": 3}}, key)
        ER.validate_adj({"sample_digest": "d", "labels": {"E1": "?"}}, key)


class ImpactTests(unittest.TestCase):
    def test_impact_has_three_versions_and_counts_fix_exclusions(self):
        docs = [_doc("반도체제조/LM1903060101_a/a.md", "<!-- page: 1 -->\nEAPSM 마스크 PSM 점검\n안전성 검토와 작업 안전\n방진복 착용\n"),
                _doc("book/s.md", "<!-- page: 1 -->\n안전 교육\n", corpus="교과서")]
        keywords = ["안전", "PSM", "보호구"]
        report = ER.impact(docs, keywords, existing_grades={}, versions=("v1", "v1fix", "v2"))
        self.assertEqual(["v1", "v1fix", "v2"], report["meta"]["versions"])
        self.assertEqual((5, 3), (report["totals"]["v1"]["NCS"], report["totals"]["v1fix"]["NCS"]))   # v1: EAPSM·PSM·안전성·작업 안전·방진복 / v1fix: PSM·작업 안전·방진복
        self.assertEqual({"PSM_substring": 1, "held_inside": 1}, report["excluded_by_fix"]["NCS"])
        self.assertTrue(all(set(report["grades"][v]["NCS"]) == {"1", "2", "3"} for v in ("v1", "v1fix", "v2")))
        row = next(k for k in report["keywords"] if k["name"] == "안전")
        self.assertEqual((2, 1), (row["v1"]["NCS"], row["v1fix"]["NCS"]))


if __name__ == "__main__":
    unittest.main()
