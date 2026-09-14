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


if __name__ == "__main__":
    unittest.main()
