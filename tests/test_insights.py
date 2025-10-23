import tempfile
from pathlib import Path
from unittest import TestCase

from app.insights import InsightEngine
from app.parser import DocumentParser
from app.storage import DocumentStorage


class InsightEngineTests(TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "ediscovery.db"
        self.storage = DocumentStorage(self.db_path)
        self.engine = InsightEngine(self.storage, max_results=2)
        self.parser = DocumentParser()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_answer_query_returns_citations(self) -> None:
        doc_path = Path(self.tmp_dir.name) / "doc.txt"
        doc_path.write_text("Claim X is supported by evidence Y.\n\nAnother paragraph.")
        parsed = self.parser.parse_documents([doc_path])
        self.storage.store_documents(parsed)
        self.engine.refresh_index()

        insights = self.engine.answer_query("evidence Y")
        self.assertTrue(insights)
        self.assertIn("doc", insights[0].citation)
        self.assertIn("evidence Y", insights[0].snippet)

    def test_answer_query_no_results(self) -> None:
        insights = self.engine.answer_query("missing term")
        self.assertEqual([], insights)
