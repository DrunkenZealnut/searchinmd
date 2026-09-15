"""expression_review.py 단위 테스트 — 표본·키·정밀도·최종 라벨·영향표. 실데이터 없이 fixture 로 돈다."""

import json
import math
import tempfile
import unittest
from pathlib import Path

import expression_review as ER
import semantic_keyword_recount as SKR
from semantic_keyword_recount import Document


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
        self.assertIsNone(scores["meta"]["adopted"])                                   # 채택은 손으로 적는다 (설계 §1 원칙 4)
        self.assertEqual("v2", ER.score(key, a, b, adj=None, adopted="v2")["meta"]["adopted"])
        with self.assertRaises(ValueError):
            ER.score(key, a, b, adopted="v9")

    def test_score_carries_tier_and_family_warning(self):
        key = {"sample_digest": "d", "items": [{"id": "E1", "keyword": "보호구", "expression": "방진복"}, {"id": "E2", "keyword": "인화", "expression": "가연성"}, {"id": "E3", "keyword": "PSM", "expression": "PSM"}]}
        a = {"grades": {"E1": 1, "E2": 1, "E3": 2}, "meta": {"model": "claude-opus-5", "base_url": "claude-cli://anthropic"}}
        b = {"grades": {"E1": 1, "E2": 1, "E3": 2}, "meta": {"model": "gpt-5.6-sol", "base_url": "https://api.openai.com/v1"}}
        scores = ER.score(key, a, b)
        self.assertEqual({"방진복": "specific", "가연성": "equivalent", "PSM": "exact"}, {r["expression"]: r["tier"] for r in scores["expressions"]})
        self.assertIsNone(scores["meta"]["family_warning"])
        same = ER.score(key, a, {"grades": b["grades"], "meta": a["meta"]})
        self.assertIn("FR-1", same["meta"]["family_warning"])

    def test_companion_stats_count_contexts_and_conditional_precision(self):
        key = {"sample_digest": "d", "items": [{"id": f"E{i}", "keyword": "보호구", "expression": "방진복"} for i in range(4)]
                                             + [{"id": "F0", "keyword": "인화", "expression": "가연성"}]}
        texts = {"E0": "방진복을 착용한다", "E1": "방진복 규격은 보호 등급별", "E2": "방진복 세탁 주기", "E3": "방진복 재고", "F0": "가연성 가스 위험"}
        labels = {"E0": 1, "E1": 1, "E2": 2, "E3": "?", "F0": 1}
        stats = ER.companion_stats(key, texts, labels, companions=("착용", "보호", "위험"))
        self.assertEqual({"o": 1, "x": 0}, stats["companions"]["착용"])            # E0 만 (라벨 1)
        self.assertEqual({"o": 1, "x": 0}, stats["companions"]["보호"])
        self.assertEqual({"o": 1, "x": 0}, stats["companions"]["위험"])
        cond = {r["expression"]: r for r in stats["expressions"]}
        self.assertEqual({"n": 2, "k": 2, "precision": 1.0, "kept_of_1": 1.0}, {k: cond["방진복"][k] for k in ("n", "k", "precision", "kept_of_1")})   # 동반어 창: E0·E1 / 라벨 1 두 건 모두 유지
        self.assertEqual(1, cond["방진복"]["dropped_x"])                                                                                            # 동반어 없는 X 문맥 1건(E2) 은 떨어진다
        self.assertNotIn("방진복을", json.dumps(stats, ensure_ascii=False))                                                                          # 본문 없음
        scores = ER.score(key, {"grades": labels, "meta": {}}, {"grades": labels, "meta": {}}, texts=texts)
        self.assertEqual(2, next(r for r in scores["expressions"] if r["expression"] == "방진복")["conditional"]["n"])
        self.assertIn("companions", scores["meta"])

    def test_score_refuses_incomplete_coder_file(self):
        """중단된 코더 실행(항목이 grades 에도 errors 에도 없음)은 ? 로 조용히 세지 않고 멈춘다 (score_coding.check_complete 규약)."""
        key = {"sample_digest": "d", "items": [{"id": "E1", "keyword": "k", "expression": "e"}, {"id": "E2", "keyword": "k", "expression": "e"}]}
        full = {"grades": {"E1": 1, "E2": 2}, "meta": {}}
        partial = {"grades": {"E1": 1}, "errors": {}, "meta": {}}
        with self.assertRaises(ValueError) as ctx:
            ER.score(key, full, partial)
        self.assertIn("E2", str(ctx.exception))
        ER.score(key, full, {"grades": {"E1": 1}, "errors": {"E2": "timeout"}, "meta": {}})            # errors 에 있으면 완료된 실행

    def test_score_refuses_coder_labels_from_another_sample_or_prompt(self):
        import hashlib
        p1 = hashlib.sha256(ER.coder_prompt().encode("utf-8")).hexdigest()
        key = {"sample_digest": "d", "items": [{"id": "E1", "keyword": "k", "expression": "e"}]}
        a = {"grades": {"E1": 1}, "meta": {"prompt_sha256": p1}, "sample_digest": "d"}
        with self.assertRaises(ValueError):
            ER.score(key, a, {"grades": {"E1": 1}, "meta": {"prompt_sha256": p1}, "sample_digest": "other"})     # 다른 표본의 라벨
        with self.assertRaises(ValueError):
            ER.score(key, a, {"grades": {"E1": 1}, "meta": {"prompt_sha256": "p2"}, "sample_digest": "d"})         # 두 코더의 질문이 다름
        with self.assertRaises(ValueError):
            ER.score(key, {**a, "meta": {"prompt_sha256": "old"}}, {"grades": {"E1": 1}, "meta": {"prompt_sha256": "old"}, "sample_digest": "d"})   # 지금 질문과 다름
        ER.score(key, a, {"grades": {"E1": 1}, "meta": {"prompt_sha256": p1}, "sample_digest": "d"})

    def test_score_recomputes_key_digest_and_checks_sheet_text_hashes(self):
        records = ER.collect_records(FIXTURE_DOCS, TARGETS)
        items = ER.build_sample(records, TARGETS, seed=1, per_expression=3)
        sheet, key = ER.sheet_and_key(items, FIXTURE_DOCS)
        ids = [i["id"] for i in key["items"]]
        import hashlib
        meta = {"prompt_sha256": hashlib.sha256(ER.coder_prompt().encode("utf-8")).hexdigest()}
        a = {"grades": {i: 1 for i in ids}, "meta": meta, "sample_digest": key["sample_digest"]}; b = {"grades": {i: 1 for i in ids}, "meta": meta, "sample_digest": key["sample_digest"]}
        texts = {i["id"]: i["text"] for i in sheet["items"]}
        ER.score(key, a, b, texts=texts)
        with self.assertRaisesRegex(ValueError, "sample_digest"):
            ER.score(key, a, {"grades": {i: 1 for i in ids}, "meta": meta}, texts=texts)                      # 실제 키에는 digest 없는 코더 파일을 받지 않는다 (F13)
        with self.assertRaisesRegex(ValueError, "prompt_sha256"):
            ER.score(key, a, {**b, "meta": {}}, texts=texts)                                                  # 실제 키에는 prompt_sha256 없는 코더 파일도 받지 않는다 (CodeRabbit PR #16)
        tampered = json.loads(json.dumps(key)); tampered["items"][0]["keyword"] = "건강"                    # digest 는 그대로 두고 항목만 바꿈
        with self.assertRaises(ValueError):
            ER.score(tampered, a, b)
        with self.assertRaises(ValueError):
            ER.score(key, a, b, texts={**texts, ids[0]: texts[ids[0]] + " 변조"})                              # 시트 본문이 키 해시와 다름
        dup = json.loads(json.dumps(key)); dup["items"].append(dict(dup["items"][0]))
        with self.assertRaises(ValueError):
            ER.score(dup, a, b)

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
        self.assertEqual({"PSM_substring": 1, "held_inside": 1, "안전성": 1, "안전_마진류": 0}, report["excluded_by_fix"]["NCS"])
        self.assertTrue(all(set(report["grades"][v]["NCS"]) == {"1", "2", "3"} for v in ("v1", "v1fix", "v2")))
        row = next(k for k in report["keywords"] if k["name"] == "안전")
        self.assertEqual((2, 1), (row["v1"]["NCS"], row["v1fix"]["NCS"]))
        self.assertEqual(SKR._document_set_sha256(docs), report["meta"]["corpus_sha256"])

    def test_impact_splits_held_inside_by_pattern(self):
        docs = [_doc("반도체제조/LM1903060101_a/a.md", "<!-- page: 1 -->\n안전성 검토\n안전 마진 확보와 안전 재고\n작업 안전\n안전성 검토와 안전 마진\n")]
        report = ER.impact(docs, ["안전"], existing_grades={}, versions=("v1", "v1fix"))
        self.assertEqual({"PSM_substring": 0, "held_inside": 5, "안전성": 2, "안전_마진류": 3}, report["excluded_by_fix"]["NCS"])   # 한 줄에 둘 다 있어도 출현마다 제 패턴

    def test_impact_counts_what_v2_removes(self):
        docs = [_doc("반도체제조/LM1903060101_a/a.md", "<!-- page: 1 -->\nPSM 마스크 종류\n감광제 종류\n\nPSM 위험성 평가\n기록 보관\n\n방진복 규격\n세탁 주기\n\n방진복 착용\n방진화 착용\n케미컬 펌프\n")]   # 창은 ±1줄이라 항목 사이를 띄운다
        report = ER.impact(docs, ["PSM", "보호구", "화학물질"], existing_grades={}, versions=("v1fix", "v2"))
        self.assertEqual((6, 2), (report["totals"]["v1fix"]["NCS"], report["totals"]["v2"]["NCS"]))      # v2: PSM 위험성 · 방진복 착용
        self.assertEqual({"held": 2, "no_companion": 2}, report["excluded_by_v2"]["NCS"])               # 방진화·케미컬 보류 / PSM 마스크·방진복 규격 동반어 없음
        self.assertEqual([("PSM", "PSM", 2, 1), ("보호구", "방진복", 2, 1), ("보호구", "방진화", 1, 0), ("화학물질", "케미컬", 1, 0)],
                         [(e["keyword"], e["expression"], e["v1fix"], e["v2"]) for e in report["expressions"]])


class CommittedArtifactsTests(unittest.TestCase):
    """추적 산출물끼리의 일관성 — 영향표의 정본 열(DEFAULT_DICTIONARY, 결정 3 이후 v2)은 semantic_summary.json 과 같아야 한다(설계 §3.5)."""

    DATA = Path(__file__).resolve().parent / "docs" / "03-analysis" / "data"

    def test_impact_canonical_column_equals_canonical_summary(self):
        impact_path, summary_path = self.DATA / "expression_review_impact.json", self.DATA / "semantic_summary.json"
        if not impact_path.exists():
            self.skipTest("expression_review_impact.json 없음")
        impact = json.loads(impact_path.read_text(encoding="utf-8")); summary = json.loads(summary_path.read_text(encoding="utf-8"))
        canon = SKR.DEFAULT_DICTIONARY
        self.assertEqual(canon, summary["meta"]["run"]["dictionary"])
        self.assertEqual({"v1": 12506, "v1fix": 12310}, {v: impact["totals"][v]["NCS"] for v in ("v1", "v1fix")})   # 계보: v1 2026-09-09 · v1fix 결함 2건 반영
        real_pages = json.loads((self.DATA / "occurrence_real_pages_impact.json").read_text(encoding="utf-8"))   # 2026-09-15: 정본 등급은 실제 쪽 기준 — 사전 영향표(블록 기준)의 v2 등급은 그 표의 "block" 열과 같아야 한다
        for corpus in ("NCS", "교과서"):
            self.assertEqual(summary["corpora"][corpus]["total"], impact["totals"][canon][corpus], corpus)
            self.assertEqual(real_pages["grades"]["block"][corpus], impact["grades"][canon][corpus], corpus)                 # 블록 기준 계보 (4,378/4,614/2,525)
            self.assertEqual({g: summary["corpora"][corpus]["grades"][g] for g in ("1", "2", "3")}, real_pages["grades"]["real"][corpus], corpus)   # 실제 쪽 기준 = 정본
            by_name = {k["name"]: k for k in summary["keywords"]}
            for row in impact["keywords"]:
                self.assertEqual(by_name[row["name"]]["corpora"][corpus]["total"], row[canon][corpus], (row["name"], corpus))
        self.assertEqual(sum(impact["excluded_by_v2"]["NCS"].values()), impact["totals"]["v1fix"]["NCS"] - impact["totals"]["v2"]["NCS"])
        self.assertEqual(sum(impact["excluded_by_v2"]["교과서"].values()), impact["totals"]["v1fix"]["교과서"] - impact["totals"]["v2"]["교과서"])
        self.assertNotIn("/Users/", impact_path.read_text(encoding="utf-8"))

    def test_scores_and_adj_bind_to_committed_key(self):
        key = json.loads((self.DATA / "expression_review_key.json").read_text(encoding="utf-8"))
        for name in ("expression_review_scores.json", "expression_review_adj.json"):
            path = self.DATA / name
            if not path.exists():
                self.skipTest(f"{name} 없음")
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(key["sample_digest"], doc.get("sample_digest") or doc["meta"]["sample_digest"], name)   # adj 는 최상위, scores 는 meta
        scores = json.loads((self.DATA / "expression_review_scores.json").read_text(encoding="utf-8"))
        self.assertEqual(len(key["items"]), sum(r["n"] + r["unknown"] for r in scores["expressions"]))
        self.assertEqual(SKR.DEFAULT_DICTIONARY, scores["meta"]["adopted"])                # 결정 3 이 scores 에도 적혀 있다
        self.assertFalse(any(isinstance(v, float) and math.isnan(v) for r in scores["expressions"] for v in r.values() if not isinstance(v, dict)))


class CliAndEdgeTests(unittest.TestCase):
    """ship 커버리지 감사(2026-09-14) — CLI 세 하위 명령(sample / score / impact)이 연구책임자가 치는 그대로 돌고,
    표본·점수 도우미의 가장자리(라벨 전부 ?, 표현이 줄에 없음, 문서 끝, documents 없는 시트, κ 정의 불가)가 조용히 틀리지 않는다."""

    def _corpus_roots(self, td):
        ncs_root, school_root = Path(td) / "ncs", Path(td) / "school"
        (ncs_root / "반도체제조" / "LM1903060101_a").mkdir(parents=True)
        (ncs_root / "반도체제조" / "LM1903060101_a" / "a.md").write_text(NCS_TEXT, encoding="utf-8")
        school_root.mkdir()
        (school_root / "s.md").write_text(SCHOOL_TEXT, encoding="utf-8")
        return ncs_root, school_root

    def _main(self, argv):
        import contextlib, io, sys
        from unittest import mock
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["expression_review.py"] + argv), contextlib.redirect_stdout(buf):
            ER.main()
        return buf.getvalue()

    def test_sheet_inside_repo_is_allowed_only_under_data(self):                                  # CodeRabbit PR #16 (Major)
        """시트는 교재 본문을 담는다 — 저장소 안에서는 data/ 아래만, 저장소 밖은 그대로 허용."""
        from unittest import mock
        items = [{"id": "E1", "keyword": "k", "expression": "e", "corpus": "NCS", "path": "a.md", "line": 1, "text": "t"}]
        with tempfile.TemporaryDirectory() as td, mock.patch.object(ER, "HERE", Path(td)):
            for bad in (Path(td) / "README_sheet.json", Path(td) / "docs" / "sheet.json", Path(td) / "outputs" / "sheet.json"):
                with self.assertRaisesRegex(ValueError, "data/"):
                    ER.write_sample(items, bad, Path(td) / "k.json")
            self.assertFalse((Path(td) / "k.json").exists())
            with tempfile.TemporaryDirectory() as outside:
                key = ER.write_sample(items, Path(outside) / "sheet.json", Path(outside) / "key.json")        # 저장소 밖 — 허용
                self.assertTrue((Path(outside) / "sheet.json").exists() and key["sample_digest"])
            key = ER.write_sample(items, Path(td) / "data" / "sheet.json", Path(td) / "data" / "key.json")      # data/ 아래 — 허용
            self.assertTrue((Path(td) / "data" / "sheet.md").exists())

    def test_cli_list_disagreements_checks_sample_and_prompt_binding(self):                    # CodeRabbit PR #16 (Major)
        """--list-disagreements 도 score 와 같은 결속 검사를 거친다 — 다른 표본·다른 질문의 라벨을 재정 대상으로 내밀지 않는다."""
        with tempfile.TemporaryDirectory() as td:
            paths, ids, key = self._score_fixture(td)
            other = json.loads(paths["b"].read_text(encoding="utf-8")); other["sample_digest"] = "0" * 16
            paths["b"].write_text(json.dumps(other, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises((SystemExit, ValueError)) as ctx:
                self._main(["score", "--key", str(paths["key"]), "--a", str(paths["a"]), "--b", str(paths["b"]), "--adj", str(paths["adj"]), "--list-disagreements"])
            self.assertIn("sample_digest", str(ctx.exception))

    def test_impact_console_survives_zero_total(self):                                         # CodeRabbit PR #16 (Minor)
        self.assertEqual("0.0", ER._pct(0, 0)); self.assertEqual("25.0", ER._pct(1, 4))

    def test_cli_sample_writes_sheet_and_key_and_refuses_overwrite_without_force(self):
        """sample: 시트 json/md(비추적 경로) + 키를 쓰고 표본 요약을 찍는다; 키가 있으면 --force 없이는 FileExistsError 로 멈춘다."""
        with tempfile.TemporaryDirectory() as td:
            ncs_root, school_root = self._corpus_roots(td)
            sheet, key = Path(td) / "sheet.json", Path(td) / "key.json"
            base = ["sample", "--ncs-root", str(ncs_root), "--school-root", str(school_root), "--sheet", str(sheet), "--key", str(key), "--per-expression", "5", "--seed", "3"]
            out = self._main(base)
            self.assertRegex(out, r"표본 \d+건, 표현 \d+개, digest [0-9a-f]{16}")
            self.assertIn("보호구:방진복 5", out)                                   # 43건 중 5건
            self.assertIn("방사선:자외선 2", out)                                   # 보류 표현은 probe 로 2건 전수
            self.assertTrue(sheet.exists() and sheet.with_suffix(".md").exists() and key.exists())
            key_doc = json.loads(key.read_text(encoding="utf-8"))
            self.assertEqual((3, 5), (key_doc["seed"], key_doc["per_expression"]))            # 키는 실제 사용한 seed/표본 수를 적는다 (ship 커버리지 감사가 잡은 결함)
            self.assertTrue(all(not Path(i["path"]).is_absolute() for i in key_doc["items"]))
            with self.assertRaises(FileExistsError):
                self._main(base)
            digest_before = key_doc["sample_digest"]
            self._main(base + ["--force"])
            self.assertEqual(digest_before, json.loads(key.read_text(encoding="utf-8"))["sample_digest"])   # 같은 seed → 같은 표본

    def _score_fixture(self, td):
        records = ER.collect_records(FIXTURE_DOCS, TARGETS)
        items = ER.build_sample(records, TARGETS, seed=1, per_expression=3)
        sheet, key = ER.sheet_and_key(items, FIXTURE_DOCS)
        ids = [i["id"] for i in key["items"]]
        import hashlib
        prompt = hashlib.sha256(ER.coder_prompt().encode("utf-8")).hexdigest()
        a = {"grades": {i: 1 for i in ids}, "meta": {"model": "claude-opus-5", "base_url": "claude-cli://anthropic", "prompt_sha256": prompt}, "sample_digest": key["sample_digest"]}
        b = {"grades": {**{i: 1 for i in ids}, ids[0]: 2, ids[1]: "?"}, "meta": {"model": "gpt-5.6-sol", "base_url": "https://api.openai.com/v1", "prompt_sha256": prompt}, "sample_digest": key["sample_digest"]}
        adj = {"sample_digest": key["sample_digest"], "labels": {ids[0]: 2}}
        paths = {}
        for name, doc in (("key", key), ("sheet", sheet), ("a", a), ("b", b), ("adj", adj)):
            paths[name] = Path(td) / f"{name}.json"
            paths[name].write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return paths, ids, key

    def test_cli_score_lists_disagreements_then_writes_scores_with_companions(self):
        """score --list-disagreements 는 불일치 행만 찍고 파일을 쓰지 않는다; 본 실행은 시트가 있으면 동반어 근거를 붙이고 --adopted 를 meta 에 적는다."""
        with tempfile.TemporaryDirectory() as td:
            paths, ids, key = self._score_fixture(td)
            out_path = Path(td) / "scores.json"
            common = ["score", "--key", str(paths["key"]), "--a", str(paths["a"]), "--b", str(paths["b"]), "--adj", str(paths["adj"]), "--sheet", str(paths["sheet"]), "--out", str(out_path)]
            listed = self._main(common + ["--list-disagreements"])
            rows = [l.split("\t") for l in listed.strip().splitlines()[1:]]
            self.assertEqual({ids[0], ids[1]}, {r[0] for r in rows})                  # A≠B 인 두 항목만
            self.assertEqual("2", next(r for r in rows if r[0] == ids[0])[5])         # 재정 라벨 열
            self.assertFalse(out_path.exists())
            printed = self._main(common + ["--adopted", "v2"])
            self.assertIn("전체 정밀도", printed); self.assertIn("조건부", printed)
            scores = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual("v2", scores["meta"]["adopted"])
            self.assertEqual(list(SKR.SAFETY_COMPANIONS), scores["meta"]["companions"]["patterns"])
            self.assertTrue(all("conditional" in r for r in scores["expressions"]))
            self.assertEqual(1, scores["overall"]["adjudicated"])
            self.assertNotIn("«", out_path.read_text(encoding="utf-8"))                # 본문은 남지 않는다
            # 시트 digest 가 키와 다르면 동반어 계수를 붙일 수 없어 멈춘다
            wrong = Path(td) / "wrong.json"
            wrong.write_text(json.dumps({"sample_digest": "0" * 16, "items": []}), encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                self._main(common[:-4] + ["--sheet", str(wrong), "--out", str(out_path)])
            self.assertIn("digest", str(ctx.exception))
            # 명시한 --adj 경로가 없으면 조용히 재정 없이 채점하지 않는다 (F13)
            with self.assertRaises(SystemExit) as ctx:
                self._main(["score", "--key", str(paths["key"]), "--a", str(paths["a"]), "--b", str(paths["b"]), "--adj", str(Path(td) / "typo.json"), "--out", str(out_path)])
            self.assertIn("typo.json", str(ctx.exception))
            # 시트가 없으면 근거 없이 쓰고 그 사실을 찍는다
            printed = self._main(common[:-4] + ["--sheet", str(Path(td) / "none.json"), "--out", str(out_path)])
            self.assertIn("시트가 없어", printed)
            self.assertNotIn("companions", json.loads(out_path.read_text(encoding="utf-8"))["meta"])

    def test_cli_impact_writes_three_version_report(self):
        """impact: 말뭉치를 읽어 v1/v1fix/v2 영향표를 쓰고 버전별 한 줄씩 찍는다 (기존 등급은 fixture 로 대체)."""
        from unittest import mock
        with tempfile.TemporaryDirectory() as td, mock.patch.object(ER.SKR, "load_existing_grades", lambda *a, **k: {}):
            ncs_root, school_root = self._corpus_roots(td)
            out_path = Path(td) / "impact.json"
            printed = self._main(["impact", "--ncs-root", str(ncs_root), "--school-root", str(school_root), "--source-workbook", str(Path(td) / "src.xlsx"), "--out", str(out_path)])
            report = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(["v1", "v1fix", "v2"], report["meta"]["versions"])
            self.assertEqual(len(SKR.EXPECTED_KEYWORDS), report["meta"]["keywords"])
            self.assertEqual(2, report["meta"]["documents"])
            self.assertGreaterEqual(report["totals"]["v1fix"]["NCS"], report["totals"]["v2"]["NCS"])   # v2 는 걷어내기만 한다
            self.assertEqual(sum(report["excluded_by_v2"]["NCS"].values()), report["totals"]["v1fix"]["NCS"] - report["totals"]["v2"]["NCS"])
            for v in ("v1", "v1fix", "v2"):
                self.assertRegex(printed, rf"{v}\s+NCS ")
            self.assertIn("결함 수정이 걷어낸 것", printed)

    def test_score_expression_with_only_unknown_labels_has_no_candidate_and_sorts_last(self):
        """라벨이 전부 ? 인 표현: n=0, 정밀도·구간 None, candidate None, unknown=항목 수 — 0 으로 나누지 않고 맨 뒤로 간다."""
        key = {"sample_digest": "d", "items": [{"id": "E1", "keyword": "보호구", "expression": "방진복"}, {"id": "E2", "keyword": "보호구", "expression": "방진복"},
                                             {"id": "F1", "keyword": "인화", "expression": "가연성"}]}
        a = {"grades": {"E1": "?", "E2": 1, "F1": 1}, "meta": {}}
        b = {"grades": {"E1": 2, "E2": "?", "F1": 1}, "meta": {}}
        scores = ER.score(key, a, b)
        rows = {r["expression"]: r for r in scores["expressions"]}
        self.assertEqual((0, 0, None, None, None, None, 2), tuple(rows["방진복"][k] for k in ("n", "k", "precision", "lower", "upper", "candidate", "unknown")))
        self.assertIsNone(rows["방진복"]["kappa"])                                       # 양쪽 다 판정한 쌍이 없다
        self.assertEqual(["가연성", "방진복"], [r["expression"] for r in scores["expressions"]])
        self.assertEqual((1, 1, 1.0), (scores["overall"]["n"], scores["overall"]["k"], scores["overall"]["precision"]))

    def test_window_text_write_sample_and_kappa_edges(self):
        """표현이 줄에 없으면 표시 없이 그대로, 마지막 줄은 뒷줄 없이; documents 없는 시트는 거부; κ 는 빈 목록·단일 범주에서 None; 라벨 정규화."""
        doc = _doc("반도체제조/LM1903060101_a/a.md", "<!-- page: 1 -->\n첫 줄\n마지막 방진복 줄\n")
        self.assertEqual("첫 줄\n마지막 «방진복» 줄", ER.window_text(doc, {"line": 3, "matched_text": "방진복"}))
        self.assertEqual("첫 줄\n마지막 방진복 줄", ER.window_text(doc, {"line": 3, "matched_text": "없는표현"}))
        with tempfile.TemporaryDirectory() as td, self.assertRaises(ValueError):
            ER.write_sample([{"id": "E001", "keyword": "k", "expression": "e", "corpus": "NCS", "path": "p", "line": 1, "matched_text": "e"}], Path(td) / "s.json", Path(td) / "k.json")
        self.assertIsNone(ER.kappa([], []))
        self.assertIsNone(ER.kappa([1, 1], [1, 1]))                                      # pe == 1
        self.assertEqual(1.0, ER.kappa([1, 2], [1, 2]))
        self.assertEqual(-1.0, ER.kappa([1, 2], [2, 1]))
        self.assertEqual((1, 2, "?"), (ER._norm("1"), ER._norm("2"), ER._norm("?")))
        with self.assertRaises(ValueError):
            ER._norm(3)


if __name__ == "__main__":
    unittest.main()
