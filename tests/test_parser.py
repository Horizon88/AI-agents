import tempfile
from pathlib import Path
from unittest import TestCase

from app.parser import DocumentParser


class DocumentParserTests(TestCase):
    def setUp(self) -> None:
        self.parser = DocumentParser()

    def test_parse_text_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "evidence.txt"
            path.write_text("Heading\n\nParagraph one.\n\nParagraph two.")
            parsed_documents = self.parser.parse_documents([path])
        self.assertEqual(1, len(parsed_documents))
        document = parsed_documents[0]
        self.assertEqual("evidence", document.title)
        self.assertEqual(3, len(document.sections))
        self.assertIn("Paragraph one", document.sections[1].content)
