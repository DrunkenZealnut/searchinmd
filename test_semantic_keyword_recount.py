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
    KeywordSource,
    aggregate_matches,
    build_default_rules,
    default_candidate_decisions,
    load_documents,
    read_keyword_workbook,
    scan_document,
    split_pages,
    artifact_manifest,
    validate_rules,
    write_report,
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
        self.assertIn("재현성 해시", report)
        self.assertEqual(
            {"source_sha256", "rule_sha256", "detail_sha256", "summary_sha256"},
            set(manifest),
        )
        self.assertTrue(all(len(value) == 64 for value in manifest.values()))


if __name__ == "__main__":
    unittest.main()
