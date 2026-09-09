import tempfile
import unicodedata
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

from semantic_keyword_recount import (
    CandidateDecision,
    Document,
    EXPECTED_KEYWORDS,
    ExpressionRule,
    GradeAssignment,
    InputArtifact,
    KeywordSource,
    aggregate_matches,
    assign_match_grades,
    build_default_rules,
    dashboard_payload,
    grade_alias_key,
    grade_lookup_key,
    default_candidate_decisions,
    load_documents,
    load_existing_grades,
    read_keyword_workbook,
    run_census,
    scan_document,
    split_pages,
    artifact_manifest,
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

        self.assertIsNone(by_page[None].grade)
        self.assertEqual("unpaged", by_page[None].grade_source)
        self.assertEqual(2, by_page[1].grade)
        self.assertEqual("기존 판정 사유", by_page[1].grade_reason)
        self.assertEqual("existing", by_page[1].grade_source)
        self.assertEqual(3, by_page[2].grade)
        self.assertEqual("new", by_page[2].grade_source)
        summary = next(row for row in graded.summary if row.corpus == "NCS")
        self.assertEqual(1, summary.grade_2)
        self.assertEqual(6, summary.grade_3)
        self.assertEqual(1, summary.grade_unpaged)
        self.assertEqual(summary.semantic_total, summary.grade_1 + summary.grade_2 + summary.grade_3 + summary.grade_unpaged)

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
            for index in range(1, 89):
                (ncs_root / f"book-{index}.md").write_text("", encoding="utf-8")
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
        self.assertEqual({"1": 0, "2": 2, "3": 0, "unpaged": 0}, payload["corpora"]["NCS"]["grades"])
        self.assertEqual(2, payload["keywords"][0]["corpora"]["NCS"]["grades"]["2"])
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "dashboard.js"
            write_dashboard_data(result, output)
            text = output.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("/* Generated"))
        self.assertIn('"denominator":"occurrences"', text.replace(" ", "").replace("\n", ""))


if __name__ == "__main__":
    unittest.main()
