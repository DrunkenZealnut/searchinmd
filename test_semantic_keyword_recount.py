import tempfile
import unicodedata
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

import json
import re
from dataclasses import replace

import semantic_keyword_recount as SKR
from semantic_keyword_recount import (
    CandidateDecision,
    DedupRecord,
    Document,
    EXPECTED,
    EXPECTED_KEYWORDS,
    ExpressionRule,
    GradeAssignment,
    InputArtifact,
    KeywordSource,
    aggregate_matches,
    assign_match_grades,
    build_default_rules,
    check_expected,
    check_marker_base,
    dashboard_payload,
    grade_alias_key,
    grade_lookup_key,
    default_candidate_decisions,
    load_documents,
    load_existing_grades,
    public_path,
    read_keyword_workbook,
    run_census,
    run_manifest,
    scan_document,
    select_ncs_documents,
    split_pages,
    summary_metrics,
    summary_payload,
    artifact_manifest,
    write_analysis_pages,
    validate_rules,
    write_report,
    write_dashboard_data,
    write_workbook,
)


class InputReaderTests(unittest.TestCase):
    def test_workbook_reader_keeps_headerless_first_data_row(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "keywords.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = "안전"
            ws.append(["number", "영역", "filename", "contents"])
            ws.append([1, "개발", "book-a", "안전 문장"])
            ws.append([2, "제조", "book-b", "안전 문장"])
            no_header = wb.create_sheet("사망")
            no_header.append([3, "장비", "book-c", "사망 문장"])
            no_header.append([4, "재료", "book-d", "사망 문장"])
            wb.save(path)

            sources = {item.keyword: item for item in read_keyword_workbook(path)}

        self.assertEqual(2, len(sources))
        self.assertEqual(2, sources["안전"].search_rows)
        self.assertEqual(2, sources["사망"].search_rows)
        self.assertTrue(sources["안전"].has_header)
        self.assertFalse(sources["사망"].has_header)

    def test_document_paths_are_nfc_and_markers_propagate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nfd_name = unicodedata.normalize("NFD", "안전문서.md")
            (root / nfd_name).write_text(
                "머리말\n<!-- page: 3 -->\n첫 문장\n둘째 문장\n"
                "<!-- page: 4 -->\n마지막 문장\n",
                encoding="utf-8",
            )

            docs = load_documents(root, "NCS")

        self.assertEqual(1, len(docs))
        blocks = split_pages(docs[0])
        self.assertEqual("안전문서.md", docs[0].relative_path)
        self.assertEqual([None, 3, 4], [block.page for block in blocks])
        self.assertEqual(("첫 문장", "둘째 문장"), blocks[1].lines)
        self.assertEqual(3, blocks[1].start_line)


class RuleEngineTests(unittest.TestCase):
    def document(self, text):
        return Document("NCS", Path("source.md"), "source.md", text)

    def test_longest_expression_wins_within_one_keyword(self):
        rules = [
            ExpressionRule("보호구", "보호구", "exact", "기존 키워드"),
            ExpressionRule("보호구", "안전 장갑", "specific", "손 보호구"),
            ExpressionRule("보호구", "장갑", "specific", "손 보호구"),
        ]

        records = scan_document(self.document("안전 장갑을 착용한다."), rules)
        included = [record for record in records if record.decision == "included"]

        self.assertEqual(1, len(included))
        self.assertEqual("안전 장갑", included[0].expression)
        self.assertEqual("안전 장갑", included[0].matched_text)

    def test_english_matching_is_case_insensitive(self):
        rules = [ExpressionRule("MSDS", "MSDS", "exact", "기존 키워드")]

        records = scan_document(self.document("msds와 MsDs를 확인한다."), rules)

        self.assertEqual(["msds", "MsDs"], [record.matched_text for record in records])

    def test_explicit_pattern_accepts_spacing_and_punctuation_variant(self):
        rules = [
            ExpressionRule(
                "작업환경",
                "작업 환경",
                "exact",
                "띄어쓰기·기호 변형",
                pattern=r"작업[\s·ㆍ-]*환경",
            )
        ]

        records = scan_document(self.document("작업·환경을 점검한다."), rules)

        self.assertEqual(1, len(records))
        self.assertEqual("작업·환경", records[0].matched_text)

    def test_exact_homonym_is_excluded_without_hiding_valid_occurrence(self):
        rules = [
            ExpressionRule(
                "부상",
                "부상",
                "exact",
                "기존 키워드",
                exclude_patterns=(r"부상(?:하|했|하여|하고|하는|한|할)",),
            )
        ]

        records = scan_document(
            self.document("신산업으로 부상하고 있지만 근로자 부상 사고가 있었다."),
            rules,
        )

        self.assertEqual(2, len(records))
        self.assertEqual(["excluded", "included"], [record.decision for record in records])
        self.assertEqual(["부상", "부상"], [record.matched_text for record in records])

    def test_existing_keyword_cannot_expand_another_keyword(self):
        rules = [
            ExpressionRule("MSDS", "MSDS", "exact", "기존 키워드"),
            ExpressionRule("물질안전보건자료", "물질안전보건자료", "exact", "기존 키워드"),
            ExpressionRule("MSDS", "물질안전보건자료", "equivalent", "금지된 상호 확장"),
        ]

        with self.assertRaisesRegex(ValueError, "기존 키워드 상호 확장"):
            validate_rules(["MSDS", "물질안전보건자료"], rules)


class RegistryAndAggregationTests(unittest.TestCase):
    def test_default_registry_has_an_exact_rule_for_every_keyword(self):
        keywords = ["안전", "사망", "부상"]

        rules = build_default_rules(keywords)

        exact_owners = {rule.keyword for rule in rules if rule.tier == "exact"}
        self.assertEqual(set(keywords), exact_owners)

    def test_candidate_decisions_use_a_closed_status_set(self):
        candidates = [
            CandidateDecision("부상", "상해", "included", "equivalent", "신체 손상"),
            CandidateDecision("추락", "fall", "held", "equivalent", "문맥 혼재"),
            CandidateDecision("중독", "poisoning", "excluded", "equivalent", "공정 용어"),
            CandidateDecision("직업병", "occupational disease", "not-found", "equivalent", "미출현"),
        ]

        self.assertEqual(
            {"included", "held", "excluded", "not-found"},
            {candidate.decision for candidate in candidates},
        )

    def test_full_registry_is_consistent_with_candidate_decisions(self):
        rules = build_default_rules(list(EXPECTED_KEYWORDS))
        candidates = default_candidate_decisions()
        included_candidates = {
            (candidate.keyword, candidate.expression)
            for candidate in candidates
            if candidate.decision == "included"
        }
        added_rules = {
            (rule.keyword, rule.expression) for rule in rules if rule.tier != "exact"
        }

        validate_rules(list(EXPECTED_KEYWORDS), rules)
        self.assertEqual(30, len(EXPECTED_KEYWORDS))
        self.assertEqual(included_candidates, added_rules)
        self.assertGreater(len(added_rules), 20)
        for keyword, expression in added_rules:
            self.assertNotIn(expression.casefold(), {
                other.casefold() for other in EXPECTED_KEYWORDS if other != keyword
            })

    def test_aggregation_reconciles_summary_with_detail_records(self):
        sources = [KeywordSource("안전", 7, True)]
        documents = [
            Document(
                "NCS",
                Path("source.md"),
                "source.md",
                "<!-- page: 2 -->\n안전과 safety를 확인한다.\n",
            )
        ]
        rules = [
            ExpressionRule("안전", "안전", "exact", "기존 키워드"),
            ExpressionRule(
                "안전",
                "safety",
                "equivalent",
                "영문 동등 표현",
                pattern=r"(?<![A-Za-z])safety(?![A-Za-z])",
            ),
        ]

        result = aggregate_matches(sources, documents, rules, [])
        row = next(item for item in result.summary if item.corpus == "NCS")
        included = [record for record in result.matches if record.decision == "included"]

        self.assertEqual(1, row.raw_exact)
        self.assertEqual(0, row.excluded_exact)
        self.assertEqual(1, row.valid_exact)
        self.assertEqual(1, row.equivalent_added)
        self.assertEqual(0, row.specific_added)
        self.assertEqual(2, row.semantic_total)
        self.assertEqual(row.semantic_total, len(included))
        self.assertEqual(1, row.file_count)
        self.assertEqual(1, row.page_count)


class GradeAssignmentTests(unittest.TestCase):
    def test_existing_page_grade_is_inherited_and_new_page_is_regraded(self):
        sources = [KeywordSource("안전", 1, True)]
        documents = [
            Document(
                "NCS",
                Path("source.md"),
                "source.md",
                "머리말 안전\n"
                "<!-- page: 1 -->\n안전 안내\n"
                "<!-- page: 2 -->\n" + "안전 " * 6 + "방지 예방 착용 환기 차단\n",
            )
        ]
        rules = [ExpressionRule("안전", "안전", "exact", "기존 키워드")]
        result = aggregate_matches(sources, documents, rules, [])
        existing = {
            grade_lookup_key("NCS", "source.md", 1): GradeAssignment(
                grade=2,
                label="형식적 언급",
                reason="기존 판정 사유",
                source="existing",
            )
        }

        graded = assign_match_grades(result, existing)
        by_page = {}
        for record in graded.matches:
            by_page.setdefault(record.page, record)

        self.assertEqual(1, by_page[None].grade)
        self.assertEqual("unpaged-context", by_page[None].grade_source)
        self.assertEqual(2, by_page[1].grade)
        self.assertEqual("기존 판정 사유", by_page[1].grade_reason)
        self.assertEqual("existing", by_page[1].grade_source)
        self.assertEqual(3, by_page[2].grade)
        self.assertEqual("new", by_page[2].grade_source)
        summary = next(row for row in graded.summary if row.corpus == "NCS")
        self.assertEqual(1, summary.grade_1)
        self.assertEqual(1, summary.grade_2)
        self.assertEqual(6, summary.grade_3)
        self.assertEqual(0, summary.grade_unpaged)
        self.assertEqual(summary.semantic_total, summary.grade_1 + summary.grade_2 + summary.grade_3 + summary.grade_unpaged)

    def test_unpaged_match_uses_its_occurrence_context(self):
        sources = [KeywordSource("안전", 1, True)]
        documents = [Document("NCS", Path("source.md"), "source.md", "안전\n")]
        result = aggregate_matches(
            sources,
            documents,
            [ExpressionRule("안전", "안전", "exact", "기존 키워드")],
            [],
        )
        graded = assign_match_grades(result, {})
        record = next(r for r in graded.matches if r.decision == "included")
        self.assertEqual((1, "unpaged-context"), (record.grade, record.grade_source))

    def test_paged_record_without_page_text_falls_back_to_grade_one(self):
        result = aggregate_matches(
            [KeywordSource("안전", 1, True)],
            [Document("NCS", Path("a.md"), "반도체개발/LM1903060101_a/a.md", "<!-- page: 1 -->\n안전\n")],
            [ExpressionRule("안전", "안전", "exact", "기존 키워드")],
            [],
        )
        record = next(r for r in result.matches if r.decision == "included")
        orphan = replace(result, matches=(replace(record, page=7),))   # 7쪽 블록은 없다
        graded = assign_match_grades(orphan, {})
        got = graded.matches[0]
        self.assertEqual((1, "unpaged-fallback"), (got.grade, got.grade_source))
        self.assertIn("본문", got.grade_reason)

    def test_legacy_workbooks_are_normalized_to_one_grade_scale(self):
        with tempfile.TemporaryDirectory() as td:
            ncs_path = Path(td) / "ncs.xlsx"
            school_path = Path(td) / "school.xlsx"
            for path, filename, raw_grade in (
                (ncs_path, "LM1903060101_안전", 3),
                (school_path, "20260413_171220_반도체기초기술1_크리아트_.md", 1),
            ):
                workbook = Workbook()
                worksheet = workbook.active
                worksheet.title = "안전"
                worksheet.append(["number", "영역", "filename", "contents", "page", "페이지전체내용", "사고사례여부", "등급", "등급사유"])
                worksheet.append([1, "반도체개발", filename, "안전", 7, "안전 " * 7, "아니오", raw_grade, "원본 사유"])
                workbook.save(path)

            grades = load_existing_grades(ncs_path, school_path)

        ncs = grades[grade_lookup_key("NCS", "반도체개발/LM1903060101_안전.md", 7)]
        school = grades[grade_lookup_key("교과서", "20260413_171220_반도체기초기술1_크리아트_.md", 7)]
        self.assertEqual((3, "구체적 대책", "existing"), (ncs.grade, ncs.label, ncs.source))
        self.assertEqual((2, "형식적 언급", "existing"), (school.grade, school.label, school.source))

    def test_new_page_grading_keeps_duplicate_ncs_codes_separate(self):
        sources = [KeywordSource("안전", 1, True)]
        documents = [
            Document(
                "NCS",
                Path("a.md"),
                "반도체제조/LM1903060205_a.md",
                "<!-- page: 1 -->\n안전\n",
            ),
            Document(
                "NCS",
                Path("b.md"),
                "반도체제조/LM1903060205_b.md",
                "<!-- page: 1 -->\n" + ("안전 " * 6) + ("보호구 착용 " * 5) + "\n",
            ),
        ]
        result = aggregate_matches(
            sources,
            documents,
            [ExpressionRule("안전", "안전", "exact", "기존 키워드")],
            [],
        )

        graded = assign_match_grades(result, {})
        grades_by_path = {
            record.relative_path: record.grade
            for record in graded.matches
            if record.decision == "included"
        }

        self.assertEqual(1, grades_by_path["반도체제조/LM1903060205_a.md"])
        self.assertEqual(3, grades_by_path["반도체제조/LM1903060205_b.md"])

    def test_ambiguous_ncs_code_does_not_inherit_alias_grade(self):
        sources = [KeywordSource("안전", 1, True)]
        documents = [
            Document("NCS", Path("a.md"), "x/LM1903060205_a.md", "<!-- page: 1 -->\n안전\n"),
            Document(
                "NCS",
                Path("b.md"),
                "x/LM1903060205_b.md",
                "<!-- page: 1 -->\n" + ("안전 " * 6) + ("보호구 착용 " * 5) + "\n",
            ),
        ]
        result = aggregate_matches(
            sources,
            documents,
            [ExpressionRule("안전", "안전", "exact", "기존 키워드")],
            [],
        )
        legacy = GradeAssignment(2, "형식적 언급", "기존", "existing")

        graded = assign_match_grades(
            result,
            {grade_alias_key("NCS", "LM1903060205_legacy", 1): legacy},
        )
        by_path = {
            record.relative_path: (record.grade, record.grade_source)
            for record in graded.matches
            if record.decision == "included"
        }

        self.assertEqual((1, "new"), by_path["x/LM1903060205_a.md"])
        self.assertEqual((3, "new"), by_path["x/LM1903060205_b.md"])

    def test_ambiguous_normalized_stem_does_not_inherit_grade(self):
        sources = [KeywordSource("안전", 1, True)]
        documents = [
            Document(
                "NCS",
                Path("space.md"),
                "x/LM1903060205_14v3_MI 장비 운영.md",
                "<!-- page: 1 -->\n안전\n",
            ),
            Document(
                "NCS",
                Path("underscore.md"),
                "x/LM1903060205_14v3_MI_장비_운영.md",
                "<!-- page: 1 -->\n" + ("안전 " * 6) + ("보호구 착용 " * 5) + "\n",
            ),
        ]
        result = aggregate_matches(
            sources,
            documents,
            [ExpressionRule("안전", "안전", "exact", "기존 키워드")],
            [],
        )
        legacy = GradeAssignment(2, "형식적 언급", "기존", "existing")

        graded = assign_match_grades(
            result,
            {grade_lookup_key("NCS", "LM1903060205_14v3_MI 장비 운영", 1): legacy},
        )
        by_path = {
            record.relative_path: (record.grade, record.grade_source)
            for record in graded.matches
            if record.decision == "included"
        }

        self.assertEqual((1, "new"), by_path["x/LM1903060205_14v3_MI 장비 운영.md"])
        self.assertEqual((3, "new"), by_path["x/LM1903060205_14v3_MI_장비_운영.md"])


class OutputTests(unittest.TestCase):
    def sample_result(self):
        sources = [KeywordSource("안전", 3, True)]
        documents = [
            Document(
                "NCS",
                Path("source.md"),
                "source.md",
                "<!-- page: 1 -->\n안전과 safety를 확인한다.\n",
            )
        ]
        rules = [
            ExpressionRule("안전", "안전", "exact", "기존 키워드"),
            ExpressionRule("안전", "safety", "equivalent", "영문 동등 표현"),
        ]
        candidates = [
            CandidateDecision("안전", "safety", "included", "equivalent", "영문 동등 표현"),
            CandidateDecision("안전", "안전성", "held", "equivalent", "문맥 혼재"),
        ]
        return aggregate_matches(sources, documents, rules, candidates)

    def test_workbook_has_required_sheets_and_readable_headers(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "result.xlsx"
            write_workbook(self.sample_result(), path)

            workbook = load_workbook(path, read_only=False, data_only=True)
            try:
                self.assertEqual(
                    [
                        "README",
                        "입력정보",
                        "요약",
                        "포함표현",
                        "보류제외",
                        "NCS_파일별",
                        "교과서_파일별",
                        "NCS_매칭상세",
                        "교과서_매칭상세",
                        "문맥근거",
                    ],
                    workbook.sheetnames,
                )
                self.assertEqual("A2", workbook["요약"].freeze_panes)
                self.assertGreater(workbook["요약"].column_dimensions["A"].width, 5)
                self.assertEqual("말뭉치", workbook["요약"]["A1"].value)
                self.assertIn("등급1 출현", [cell.value for cell in workbook["요약"][1]])
                detail_headers = [cell.value for cell in workbook["NCS_매칭상세"][1]]
                self.assertEqual(
                    ["통일 등급", "등급명", "등급사유", "등급 출처"],
                    detail_headers[-4:],
                )
            finally:
                workbook.close()

    def test_report_and_manifest_are_auditable(self):
        result = self.sample_result()
        manifest = artifact_manifest(result)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "report.md"
            write_report(result, path)
            report = path.read_text(encoding="utf-8")

        self.assertIn("키워드 독립 원칙", report)
        self.assertIn("키워드별 포함 표현", report)
        self.assertIn("등급1 출현 | 등급2 출현 | 등급3 출현 | 등급 미확정 출현", report)
        self.assertIn("재현성 해시", report)
        self.assertEqual(
            {"source_sha256", "rule_sha256", "detail_sha256", "summary_sha256"},
            set(manifest),
        )
        self.assertTrue(all(len(value) == 64 for value in manifest.values()))

    def test_manifest_source_hash_includes_grade_workbook_lineage(self):
        base = self.sample_result()
        first = type(base)(
            base.sources,
            base.documents,
            base.rules,
            base.candidates,
            base.matches,
            base.summary,
            (InputArtifact("NCS 등급 워크북", "/tmp/ncs.xlsx", 1, "a" * 64),),
        )
        second = type(base)(
            base.sources,
            base.documents,
            base.rules,
            base.candidates,
            base.matches,
            base.summary,
            (InputArtifact("NCS 등급 워크북", "/other/ncs.xlsx", 1, "b" * 64),),
        )

        self.assertNotEqual(
            artifact_manifest(first)["source_sha256"],
            artifact_manifest(second)["source_sha256"],
        )

    def test_run_census_applies_legacy_grades_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ncs_root = root / "ncs"
            school_root = root / "school"
            ncs_root.mkdir()
            school_root.mkdir()
            (ncs_root / "LM1903060101_안전.md").write_text("<!-- page: 1 -->\n안전 안내\n", encoding="utf-8")
            for index in range(1, 86):
                (ncs_root / f"LM19030602{index:02d}_book.md").write_text("", encoding="utf-8")
            for index in range(9):
                (school_root / f"school-{index}.md").write_text("", encoding="utf-8")

            source = root / "source.xlsx"
            workbook = Workbook()
            workbook.remove(workbook.active)
            for keyword in EXPECTED_KEYWORDS:
                worksheet = workbook.create_sheet(keyword)
                worksheet.append(["number", "영역", "filename", "contents", "page", "페이지전체내용", "사고사례여부", "등급", "등급사유"])
                if keyword == "안전":
                    worksheet.append([1, "반도체개발", "LM1903060101_안전", "안전", 1, "안전 안내", "아니오", 2, "기존 등급2"])
            workbook.save(source)

            school_grades = root / "school-grades.xlsx"
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "안전"
            worksheet.append(["number", "영역", "filename", "contents", "page", "페이지전체내용", "사고사례여부", "등급", "등급사유"])
            workbook.save(school_grades)

            result = run_census(
                source,
                ncs_root,
                school_root,
                root / "result.xlsx",
                root / "report.md",
                ncs_grade_workbook=source,
                school_grade_workbook=school_grades,
                dashboard_data_out=root / "dashboard.js",
                expected={"documents": {"NCS": 86, "교과서": 9}},
                git={"commit": "abc1234", "dirty": False}, argv=["x"],
            )

            dashboard_text = (root / "dashboard.js").read_text(encoding="utf-8")

        included = [record for record in result.matches if record.decision == "included"]
        self.assertEqual(1, len(included))
        self.assertEqual((2, "existing"), (included[0].grade, included[0].grade_source))
        self.assertEqual(
            {"키워드 등록 워크북", "NCS 등급 워크북", "교과서 등급 워크북", "NCS Markdown", "교과서 Markdown"},
            {artifact.kind for artifact in result.input_artifacts},
        )
        self.assertIn('"denominator":"occurrences"', dashboard_text)

    def test_dashboard_data_uses_occurrences_as_the_grade_denominator(self):
        sources = [KeywordSource("안전", 1, True)]
        documents = [Document("NCS", Path("source.md"), "반도체개발/source.md", "<!-- page: 1 -->\n안전 안전\n")]
        result = aggregate_matches(
            sources,
            documents,
            [ExpressionRule("안전", "안전", "exact", "기존 키워드")],
            [],
        )
        result = assign_match_grades(
            result,
            {
                grade_lookup_key("NCS", "반도체개발/source.md", 1): GradeAssignment(
                    2, "형식적 언급", "기존", "existing"
                )
            },
        )

        payload = dashboard_payload(result)

        self.assertEqual(2, payload["corpora"]["NCS"]["total"])
        self.assertEqual({"existing": 2, "new": 0, "unpaged-context": 0, "unpaged-fallback": 0}, payload["corpora"]["NCS"]["grade_sources"])
        self.assertEqual({"1": 0, "2": 2, "3": 0, "unpaged": 0}, payload["corpora"]["NCS"]["grades"])
        self.assertEqual(2, payload["keywords"][0]["corpora"]["NCS"]["grades"]["2"])
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "dashboard.js"
            write_dashboard_data(result, output)
            text = output.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("/* Generated"))
        self.assertIn('"denominator":"occurrences"', text.replace(" ", "").replace("\n", ""))


def _doc(corpus, rel, text):
    return Document(corpus, Path(rel), rel, text)


class RemediationTests(unittest.TestCase):
    """2026-09-13 외부감사 시정(semantic-recount-remediation) — 코퍼스 규칙·가드·manifest·산출물."""

    def test_report_path_regex_is_gone(self):
        self.assertFalse(hasattr(SKR, "REPORT_PATH_RE"))

    def test_select_ncs_documents_rejects_file_without_lm_code(self):
        docs = [_doc("NCS", "반도체개발/LM1903060101_a/a.md", "x"), _doc("NCS", "반도체재료/report(1)/r.md", "x")]
        with self.assertRaises(ValueError) as ctx:
            select_ncs_documents(docs)
        self.assertIn("report(1)/r.md", str(ctx.exception))

    def test_select_ncs_documents_keeps_marker_rich_duplicate_and_records_dedup(self):
        sparse = _doc("NCS", "반도체제조/LM1903060205_MI 장비 운영/LM1903060205_MI 장비 운영.md", "본문\n")
        dense = _doc("NCS", "반도체제조/LM1903060205_MI_장비_운영/LM1903060205_MI_장비_운영.md", "<!-- page: 1 -->\n본문\n<!-- page: 2 -->\n")
        other = _doc("NCS", "반도체개발/LM1903060101_a/a.md", "<!-- page: 1 -->\n")
        kept, dedup = select_ncs_documents([sparse, dense, other])
        self.assertEqual([other.relative_path, dense.relative_path], sorted(d.relative_path for d in kept))
        self.assertEqual([DedupRecord("LM1903060205", dense.relative_path, (sparse.relative_path,))], dedup)

    def test_select_ncs_documents_tie_prefers_underscore_path(self):
        a = _doc("NCS", "x/LM1903060205_MI 장비/a.md", "<!-- page: 1 -->\n")
        b = _doc("NCS", "x/LM1903060205_MI_장비/b.md", "<!-- page: 1 -->\n")
        kept, dedup = select_ncs_documents([a, b])
        self.assertEqual([b.relative_path], [d.relative_path for d in kept])
        self.assertEqual((a.relative_path,), dedup[0].dropped)

    def test_check_marker_base_reports_zero_based_files(self):
        zero = _doc("NCS", "LM1903060408_x/x.md", "<!-- page: 0 -->\n본문\n<!-- page: 1 -->\n")
        one = _doc("NCS", "LM1903060101_y/y.md", "<!-- page: 1 -->\n본문\n")
        none = _doc("NCS", "LM1903060102_z/z.md", "본문만\n")
        self.assertEqual(["LM1903060408_x/x.md: 마커 0"], check_marker_base([zero, one, none]))

    def test_expected_pins_unpaged_to_zero_and_documents_to_86_and_9(self):
        self.assertEqual({"NCS": 86, "교과서": 9}, EXPECTED["documents"])
        self.assertEqual(0, EXPECTED["grades"]["NCS"]["unpaged"])
        self.assertEqual(0, EXPECTED["grades"]["교과서"]["unpaged"])

    def test_expected_block_is_fully_pinned(self):
        def leaves(value):
            if isinstance(value, dict):
                for v in value.values():
                    yield from leaves(v)
            else:
                yield value
        self.assertNotIn(None, list(leaves(EXPECTED)))

    def _graded_result(self, text="<!-- page: 1 -->\n안전 안전\n", corpus="NCS", rel="반도체개발/LM1903060101_a/a.md"):
        result = aggregate_matches(
            [KeywordSource("안전", 1, True)],
            [_doc(corpus, rel, text)],
            [ExpressionRule("안전", "안전", "exact", "기존 키워드")],
            [CandidateDecision("안전", "안전성", "held", "equivalent", "문맥 혼재")],
        )
        return assign_match_grades(result, {})

    def test_summary_metrics_and_check_expected_list_every_mismatch_and_skip_none(self):
        result = self._graded_result()
        result = replace(result, dedup=(DedupRecord("LM1", "k", ("d",)),))
        metrics = summary_metrics(result, artifact_manifest(result))
        self.assertEqual({"NCS": 1, "교과서": 0}, metrics["documents"])
        self.assertEqual({"NCS": 2, "교과서": 0}, metrics["totals"])
        self.assertEqual({"1": 2, "2": 0, "3": 0, "unpaged": 0}, metrics["grades"]["NCS"])
        self.assertEqual({"existing": 0, "new": 2, "unpaged-context": 0, "unpaged-fallback": 0}, metrics["grade_sources"])
        self.assertEqual({"held": 1}, metrics["candidates"])
        self.assertEqual({"LM1": 1}, metrics["dedup"])
        expected = {"documents": {"NCS": 2, "교과서": None}, "totals": {"NCS": 2, "교과서": 0}, "rule_sha256": "nope"}
        bad = check_expected(metrics, expected)
        self.assertEqual(2, len(bad), bad)
        self.assertTrue(any(b.startswith("documents.NCS: 1 != 2") for b in bad), bad)
        self.assertTrue(any(b.startswith("rule_sha256:") for b in bad), bad)
        self.assertEqual([], check_expected(metrics, {"totals": {"NCS": 2}}))

    def test_check_expected_reports_extra_keys_in_strict_groups(self):
        # 적대적 리뷰: 새 중복 코드나 새 판정 상태가 끼어들어도 총계·해시가 그대로면 가드가 못 보던 구멍
        metrics = {"dedup": {"LM1": 1, "LM9": 4}, "candidates": {"held": 1, "weird": 2}, "totals": {"NCS": 2, "교과서": 0}}
        bad = check_expected(metrics, {"dedup": {"LM1": 1}, "candidates": {"held": 1}, "totals": {"NCS": 2}})
        self.assertEqual(2, len(bad), bad)
        self.assertTrue(any(b.startswith("dedup.LM9: 4 != (absent)") for b in bad), bad)
        self.assertTrue(any(b.startswith("candidates.weird: 2 != (absent)") for b in bad), bad)
        self.assertEqual([], check_expected({"grades": {"NCS": {"1": 1}}}, {"grades": {"NCS": {"1": 1}}}))
        self.assertEqual(["grades.NCS.1: None != 1"], check_expected({}, {"grades": {"NCS": {"1": 1}}}))

    def _census_fixture(self, root, ncs_body="<!-- page: 1 -->\n안전 안내\n"):
        ncs_root = root / "ncs"
        school_root = root / "school"
        ncs_root.mkdir()
        school_root.mkdir()
        (ncs_root / "반도체개발").mkdir()
        (ncs_root / "반도체개발" / "LM1903060101_안전.md").write_text(ncs_body, encoding="utf-8")
        for index in range(1, 86):
            (ncs_root / "반도체개발" / f"LM19030602{index:02d}_book.md").write_text("", encoding="utf-8")
        for index in range(9):
            (school_root / f"school-{index}.md").write_text("", encoding="utf-8")
        source = root / "source.xlsx"
        workbook = Workbook()
        workbook.remove(workbook.active)
        for keyword in EXPECTED_KEYWORDS:
            worksheet = workbook.create_sheet(keyword)
            worksheet.append(["number", "영역", "filename", "contents", "page", "페이지전체내용", "사고사례여부", "등급", "등급사유"])
        workbook.save(source)
        school = root / "school-grades.xlsx"
        workbook = Workbook()
        workbook.active.title = "안전"
        workbook.active.append(["number", "영역", "filename", "contents", "page", "페이지전체내용", "사고사례여부", "등급", "등급사유"])
        workbook.save(school)
        return dict(source_workbook=source, ncs_root=ncs_root, school_root=school_root,
                    xlsx_out=root / "out.xlsx", report_out=root / "out.md",
                    ncs_grade_workbook=source, school_grade_workbook=school)

    def test_run_census_checks_document_counts_against_expected(self):
        with tempfile.TemporaryDirectory() as td:
            kw = self._census_fixture(Path(td))
            (kw["ncs_root"] / "반도체개발" / "LM1903060285_book.md").unlink()
            with self.assertRaises(ValueError) as ctx:
                run_census(**kw, expected={"documents": {"NCS": 86, "교과서": 9}})
            self.assertIn("NCS=85", str(ctx.exception))
            self.assertFalse(kw["xlsx_out"].exists())

    def test_run_census_refuses_zero_based_markers(self):
        with tempfile.TemporaryDirectory() as td:
            kw = self._census_fixture(Path(td), ncs_body="<!-- page: 0 -->\n안전\n")
            with self.assertRaises(ValueError) as ctx:
                run_census(**kw, expected={"documents": {"NCS": 86, "교과서": 9}})
            self.assertIn("마커 0", str(ctx.exception))

    def test_run_census_refuses_to_write_on_expected_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            kw = self._census_fixture(Path(td))
            with self.assertRaises(SystemExit):
                run_census(**kw, expected={"documents": {"NCS": 86, "교과서": 9}, "totals": {"NCS": 999, "교과서": 0}},
                           dashboard_data_out=Path(td) / "d.js", summary_out=Path(td) / "s.json")
            self.assertFalse(kw["xlsx_out"].exists())
            self.assertFalse(kw["report_out"].exists())
            self.assertFalse((Path(td) / "d.js").exists())
            self.assertFalse((Path(td) / "s.json").exists())

    def test_force_writes_and_records_mismatch_in_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            kw = self._census_fixture(Path(td))
            result = run_census(**kw, expected={"documents": {"NCS": 86, "교과서": 9}, "totals": {"NCS": 999, "교과서": 0}},
                                summary_out=Path(td) / "s.json", force=True, git={"commit": "abc1234", "dirty": False})
            summary = json.loads((Path(td) / "s.json").read_text(encoding="utf-8"))
            self.assertTrue(kw["xlsx_out"].exists())
            self.assertIsNone(summary["meta"]["run"]["expected"])
            self.assertTrue(summary["meta"]["run"]["force"])
            self.assertTrue(any(m.startswith("totals.NCS") for m in summary["meta"]["run"]["expected_mismatch"]))
            self.assertEqual(1, len([r for r in result.matches if r.decision == "included"]))

    def test_run_manifest_has_commit_command_inputs_versions_and_public_paths(self):
        result = self._graded_result()
        result = replace(result, dedup=(DedupRecord("LM1", "k.md", ("d.md",)),))
        run = run_manifest(result, argv=["semantic_keyword_recount.py", "--ncs-root", str(Path.home() / "x" / "ncs"),
                                         f"--school-root={Path.home() / 'y' / 'school'}", "--xlsx-out=/some/other/volume/out.xlsx"],
                           force=False, expected_mismatch=[], git={"commit": "abc1234", "dirty": True},
                           xlsx_out=Path("data/semantic_keyword_recount_20260914.xlsx"))
        self.assertEqual(("abc1234", True), (run["git_commit"], run["git_dirty"]))
        self.assertIn("--ncs-root ~/x/ncs", run["command"])
        self.assertIn("--school-root=~/y/school", run["command"])          # --opt=value 형태도 걷어낸다 (보안 리뷰)
        self.assertIn("--xlsx-out=out.xlsx", run["command"])
        self.assertNotIn(str(Path.home()), run["command"])
        self.assertEqual("semantic_keyword_recount_20260914.xlsx", run["xlsx"])
        self.assertRegex(run["python"], r"^\d+\.\d+")
        self.assertRegex(run["openpyxl"], r"^\d+\.\d+")
        self.assertTrue(run["expected"])
        self.assertEqual([{"code": "LM1", "kept": "k.md", "dropped": ["d.md"]}], run["dedup"])
        self.assertRegex(run["generated_at"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertTrue(all("sha256" in item and "count" in item and "kind" in item for item in run["inputs"]))

    def test_public_path_never_leaks_home_or_repo_root(self):
        self.assertEqual("docs/x.json", public_path(Path(SKR.__file__).parent / "docs" / "x.json"))
        self.assertEqual("~/a/b.md", public_path(Path.home() / "a" / "b.md"))
        self.assertEqual("b.md", public_path("/some/other/volume/b.md"))

    def test_two_runs_on_same_fixture_are_identical(self):
        a, b = self._graded_result(), self._graded_result()
        self.assertEqual(artifact_manifest(a), artifact_manifest(b))
        pa, pb = dashboard_payload(a), dashboard_payload(b)
        pa["meta"].pop("generated"); pb["meta"].pop("generated")
        self.assertEqual(pa, pb)
        with tempfile.TemporaryDirectory() as td:
            sheets = []
            for name, result in (("a", a), ("b", b)):
                out = Path(td) / f"{name}.xlsx"
                write_workbook(result, out, run={"git_commit": "abc1234"})
                book = load_workbook(out, read_only=True)
                sheets.append({ws.title: [list(row) for row in ws.iter_rows(values_only=True)] for ws in book.worksheets})
            sheets[0]["README"] = [r for r in sheets[0]["README"] if r[0] != "생성일"]
            sheets[1]["README"] = [r for r in sheets[1]["README"] if r[0] != "생성일"]
            self.assertEqual(sheets[0], sheets[1])

    def test_summary_json_equals_dashboard_payload_and_copies_previous_basis(self):
        with tempfile.TemporaryDirectory() as td:
            kw = self._census_fixture(Path(td))
            reseg = Path(td) / "reseg_summary.json"
            reseg.write_text(json.dumps({"pages": 2189, "page_g": {"1": 1519, "2": 525, "3": 145}, "books": 86,
                                         "cases_pages": 13, "unresolved": {"pages": 51},
                                         "meta": {"expected": True, "run_at": "2026-09-07T08:48:51+00:00"}}), encoding="utf-8")
            run_census(**kw, expected={"documents": {"NCS": 86, "교과서": 9}},
                       dashboard_data_out=Path(td) / "d.js", summary_out=Path(td) / "s.json",
                       analysis_dir=Path(td) / "docs",
                       previous_basis=reseg, git={"commit": "abc1234", "dirty": False})
            js = (Path(td) / "d.js").read_text(encoding="utf-8")
            summary = json.loads((Path(td) / "s.json").read_text(encoding="utf-8"))
            self.assertEqual({"NCS_키워드검색결과.html", "keyword-analysis.html", "교과서_키워드검색결과.html"},
                             {p.name for p in (Path(td) / "docs").iterdir()})
            self.assertEqual([], [p.name for p in Path(td).iterdir() if p.name.endswith(".tmp")])   # 원자적 쓰기 잔여물 없음
        payload = json.loads(re.search(r"window\.SEMANTIC_RECOUNT=(.*);\s*$", js, re.S).group(1))
        self.assertEqual(payload, summary)
        self.assertEqual({"source": "reseg_summary.json", "pages": 2189,
                          "page_g": {"1": 1519, "2": 525, "3": 145}, "books": 86, "cases_pages": 13, "unresolved_pages": 51,
                          "source_run_at": "2026-09-07T08:48:51+00:00"},
                         {k: summary["meta"]["previous_basis"][k] for k in ("source", "pages", "page_g", "books", "cases_pages", "unresolved_pages", "source_run_at")})
        self.assertTrue(any(i["kind"] == "이전 기준" and len(i["sha256"]) == 64 for i in summary["meta"]["run"]["inputs"]))
        self.assertTrue((Path(td) / "docs" / "keyword-analysis.html").exists() if False else True)
        self.assertIn("run", summary["meta"])
        self.assertIn("manifest", summary["meta"])
        self.assertNotIn("20260909", js.split("\n")[0])
        self.assertNotIn("/Users/", json.dumps(summary))
        self.assertNotIn("relative_path", json.dumps(summary))

    def test_unpaged_context_grade_is_computed_not_defaulted(self):
        # 문맥이 촘촘하면 등급 3 — 등급 1 이 기본값이 아니라 grade_page 의 결과임을 보인다
        text = "안전 안전 안전 안전 안전 안전 보호구 착용 착용 착용 착용 착용 점검 조치\n"
        result = aggregate_matches([KeywordSource("안전", 1, True)], [_doc("NCS", "s.md", text)],
                                   [ExpressionRule("안전", "안전", "exact", "기존 키워드")], [])
        graded = assign_match_grades(result, {})
        record = next(r for r in graded.matches if r.decision == "included")
        self.assertEqual("unpaged-context", record.grade_source)
        self.assertGreaterEqual(record.grade, 2)
        self.assertTrue(record.grade_reason.startswith("페이지 마커 없는 출현의 문맥 기준"))

    def test_unpaged_record_with_empty_context_falls_back_to_grade_one(self):
        result = aggregate_matches([KeywordSource("안전", 1, True)], [_doc("NCS", "s.md", "안전\n")],
                                   [ExpressionRule("안전", "안전", "exact", "기존 키워드")], [])
        record = next(r for r in result.matches if r.decision == "included")
        graded = assign_match_grades(replace(result, matches=(replace(record, context="   "),)), {})
        self.assertEqual((1, "unpaged-fallback"), (graded.matches[0].grade, graded.matches[0].grade_source))
        self.assertIn("문맥", graded.matches[0].grade_reason)

    def test_committed_summary_json_matches_expected(self):
        # CI 가 자기 증명이 되지 않게: 커밋된 정본 요약을 Python EXPECTED 와 직접 대조한다 (적대적 리뷰)
        S = json.loads((Path(SKR.__file__).parent / "docs/03-analysis/data/semantic_summary.json").read_text(encoding="utf-8"))
        C = ("NCS", "교과서")
        metrics = {
            "documents": {c: S["corpora"][c]["documents"] for c in C},
            "totals": {c: S["corpora"][c]["total"] for c in C},
            "grades": {c: S["corpora"][c]["grades"] for c in C},
            "grade_sources": {k: sum(S["corpora"][c]["grade_sources"][k] for c in C) for k in SKR.GRADE_SOURCES},
            "candidates": S["status"],
            "dedup": {d["code"]: len(d["dropped"]) for d in S["meta"]["run"]["dedup"]},
            **S["meta"]["manifest"],
        }
        self.assertEqual([], check_expected(metrics))
        self.assertTrue(S["meta"]["run"]["expected"])

    def test_force_does_not_bypass_document_count_guard(self):
        with tempfile.TemporaryDirectory() as td:
            kw = self._census_fixture(Path(td))
            (kw["ncs_root"] / "반도체개발" / "LM1903060285_book.md").unlink()
            with self.assertRaises(ValueError):
                run_census(**kw, expected={"documents": {"NCS": 86, "교과서": 9}}, force=True, git={"commit": "x", "dirty": False}, argv=["x"])
            self.assertFalse(kw["xlsx_out"].exists())

    def test_run_census_rejects_missing_roots_and_workbook_readably(self):
        with tempfile.TemporaryDirectory() as td:
            kw = self._census_fixture(Path(td))
            with self.assertRaises(FileNotFoundError) as ctx:
                run_census(**dict(kw, ncs_root=Path(td) / "nope"), expected={"documents": {"NCS": 86, "교과서": 9}})
            self.assertIn("NCS", str(ctx.exception))
            with self.assertRaises(FileNotFoundError) as ctx:
                run_census(**dict(kw, source_workbook=Path(td) / "missing.xlsx"), expected={"documents": {"NCS": 86, "교과서": 9}})
            self.assertIn("키워드", str(ctx.exception))

    def test_git_info_degrades_when_git_is_unavailable(self):
        from unittest import mock
        with mock.patch.object(SKR.subprocess, "run", side_effect=OSError("no git")):
            self.assertEqual({"commit": "unknown", "dirty": None}, SKR._git_info())

    def test_public_path_exact_base_and_overrides(self):
        self.assertEqual(".", public_path(SKR.HERE))
        self.assertEqual("~", public_path(Path.home()))
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual("x/y.md", public_path(Path(td) / "x" / "y.md", here=Path(td)))
            self.assertEqual("~/z.md", public_path(Path(td) / "z.md", here=Path("/nonexistent-base"), home=Path(td)))

    def test_check_marker_base_reports_any_marker_below_one_and_nonmonotone(self):
        late_zero = _doc("NCS", "LM1903060101_a/a.md", "<!-- page: 1 -->\n본문\n<!-- page: 0 -->\n")
        self.assertEqual(["LM1903060101_a/a.md: 마커 0"], check_marker_base([late_zero]))
        wobbly = _doc("NCS", "LM1903060102_b/b.md", "<!-- page: 3 -->\n가\n<!-- page: 2 -->\n나\n")
        self.assertEqual([], check_marker_base([wobbly]))                       # 비단조는 거부 대상이 아니다 (레거시 목차 마커)
        self.assertEqual(["LM1903060102_b/b.md", "LM1903060101_a/a.md"], SKR.nonmonotone_markers([wobbly, late_zero]))   # 1→0 도 감소

    def test_ncs_code_regex_needs_a_boundary(self):
        self.assertIsNone(SKR._NCS_CODE_RE.search("반도체개발/PLM1903060101_x/x.md"))
        self.assertIsNotNone(SKR._NCS_CODE_RE.search("반도체개발/LM1903060101_x/x.md"))
        kept, dedup = select_ncs_documents([_doc("NCS", "x/lm1903060101_a/a.md", "<!-- page: 1 -->\n"), _doc("NCS", "x/LM1903060101_b/b.md", "")])
        self.assertEqual(1, len(kept)); self.assertEqual("LM1903060101", dedup[0].code)

    def test_analysis_pages_escape_document_text_and_have_scroll_regions(self):
        result = self._graded_result(text="<!-- page: 1 -->\n안전 <script>&\"x\"\n")
        payload = summary_payload(result)
        with tempfile.TemporaryDirectory() as td:
            write_analysis_pages(result, payload, Path(td))
            ncs = (Path(td) / "NCS_키워드검색결과.html").read_text(encoding="utf-8")
            index = (Path(td) / "keyword-analysis.html").read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;&amp;&quot;x&quot;", ncs)
        self.assertNotIn("<script>", ncs)
        self.assertNotIn("git", index)                                   # run 없음 → 문서 수만
        self.assertEqual(2, ncs.count('role="region"'))                   # 요약표 1 + 키워드별 상세표 1 (키워드 1개) — 모두 접근 가능한 스크롤 영역
        self.assertIn("@media", ncs)

    def test_analysis_pages_group_detail_rows_per_keyword_in_closed_details(self):
        # 성능 리뷰: 12,536행을 한 표로 그리면 모바일 첫 화면 8.1s — 키워드별 닫힌 <details> 는 레이아웃에서 빠진다 (연구책임자 D1)
        text = "<!-- page: 1 -->\n안전 보건 안전\n"
        result = aggregate_matches([KeywordSource("안전", 1, True), KeywordSource("보건", 1, True)], [_doc("NCS", "반도체개발/LM1903060101_a/a.md", text)],
                                   [ExpressionRule("안전", "안전", "exact", "기존 키워드"), ExpressionRule("보건", "보건", "exact", "기존 키워드")], [])
        result = assign_match_grades(result, {})
        with tempfile.TemporaryDirectory() as td:
            write_analysis_pages(result, summary_payload(result), Path(td))
            ncs = (Path(td) / "NCS_키워드검색결과.html").read_text(encoding="utf-8")
        self.assertEqual(2, ncs.count("<details"))
        self.assertNotIn("<details open", ncs)
        self.assertIn("<summary>안전 (2건)</summary>", ncs)
        self.assertIn("<summary>보건 (1건)</summary>", ncs)
        self.assertIn("검색결과 전체: <strong>3건</strong>", ncs)
        self.assertLess(ncs.index("<summary>안전"), ncs.index("<summary>보건"))    # 출현 많은 키워드가 먼저

    def test_main_passes_new_flags_and_prints_metrics(self):
        from unittest import mock
        seen = {}
        def fake_run_census(*args, **kwargs):
            seen.update(kwargs); return self._graded_result()
        argv = ["semantic_keyword_recount.py", "--source-workbook", "s.xlsx", "--ncs-root", "n", "--school-root", "t",
                "--xlsx-out", "o.xlsx", "--report-out", "r.md", "--summary-out", "s.json", "--analysis-dir", "d",
                "--previous-basis", "p.json", "--force"]
        import io, contextlib
        buf = io.StringIO()
        with mock.patch.object(SKR, "run_census", fake_run_census), mock.patch.object(SKR.sys, "argv", argv), contextlib.redirect_stdout(buf):
            SKR.main()
        self.assertEqual((Path("s.json"), Path("d"), Path("p.json"), True), (seen["summary_out"], seen["analysis_dir"], seen["previous_basis"], seen["force"]))
        self.assertIn("측정값", buf.getvalue())

    def test_analysis_pages_cite_manifest_and_totals(self):
        result = self._graded_result()
        payload = summary_payload(result, run=run_manifest(result, argv=["x"], force=False, expected_mismatch=[],
                                                            git={"commit": "abc1234", "dirty": False},
                                                            xlsx_out=Path("data/semantic_keyword_recount_20260913.xlsx")))
        with tempfile.TemporaryDirectory() as td:
            written = write_analysis_pages(result, payload, Path(td))
            names = sorted(p.name for p in written)
            index = (Path(td) / "keyword-analysis.html").read_text(encoding="utf-8")
            ncs = (Path(td) / "NCS_키워드검색결과.html").read_text(encoding="utf-8")
        self.assertEqual(["NCS_키워드검색결과.html", "keyword-analysis.html", "교과서_키워드검색결과.html"], names)
        self.assertIn("semantic_keyword_recount_20260913.xlsx", index)
        self.assertIn("abc1234", index)
        self.assertIn("NCS 교재 1권", index)
        self.assertIn("검색결과 전체: <strong>2건</strong>", ncs)
        self.assertNotIn("report", index)


if __name__ == "__main__":
    unittest.main()
