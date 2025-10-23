"""Document parsing utilities for the e-discovery platform."""

from __future__ import annotations

import email
import re
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.message import Message
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import PyPDF2


@dataclass
class ParsedSection:
    """Represents a section/paragraph of extracted text."""

    heading: Optional[str]
    content: str
    order_index: int


@dataclass
class ParsedDocument:
    """Container for parsed document data."""

    source_path: Path
    title: str
    author: Optional[str]
    created_at: Optional[datetime]
    sections: List[ParsedSection]
    metadata: Dict[str, str]


class DocumentParser:
    """Parses collected documents into structured text."""

    PARAGRAPH_BREAK = re.compile(r"\n{2,}")

    def parse_documents(self, documents: Iterable[Path]) -> List[ParsedDocument]:
        parsed: List[ParsedDocument] = []
        for path in documents:
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                result = self._parse_pdf(path)
            elif suffix in {".txt", ".md", ".rtf"}:
                result = self._parse_text(path)
            elif suffix in {".eml"}:
                result = self._parse_email(path)
            else:
                print(f"Unsupported format for parsing: {path}")
                continue
            if result:
                parsed.append(result)
        return parsed

    def _parse_pdf(self, path: Path) -> Optional[ParsedDocument]:
        with open(path, "rb") as pdf_file:
            try:
                reader = PyPDF2.PdfReader(pdf_file)
            except Exception as exc:  # pragma: no cover
                print(f"Failed to read PDF {path}: {exc}")
                return None
            metadata = {}
            if reader.metadata:
                metadata = {k[1:]: str(v) for k, v in reader.metadata.items() if k}
            text_sections: List[ParsedSection] = []
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                for order, paragraph in enumerate(self._split_paragraphs(text)):
                    text_sections.append(
                        ParsedSection(
                            heading=f"Page {idx + 1}",
                            content=paragraph.strip(),
                            order_index=idx * 1000 + order,
                        )
                    )
            return ParsedDocument(
                source_path=path,
                title=metadata.get("Title") or path.stem,
                author=metadata.get("Author"),
                created_at=self._parse_date(metadata.get("CreationDate")),
                sections=text_sections,
                metadata=metadata,
            )

    def _parse_text(self, path: Path) -> Optional[ParsedDocument]:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")
        sections = [
            ParsedSection(heading=None, content=paragraph.strip(), order_index=index)
            for index, paragraph in enumerate(self._split_paragraphs(content))
            if paragraph.strip()
        ]
        return ParsedDocument(
            source_path=path,
            title=path.stem,
            author=None,
            created_at=self._infer_file_date(path),
            sections=sections,
            metadata={},
        )

    def _parse_email(self, path: Path) -> Optional[ParsedDocument]:
        raw = path.read_text(encoding="utf-8", errors="replace")
        msg: Message = email.message_from_string(raw, policy=policy.default)
        body_parts: List[str] = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body_parts.append(part.get_content())
        else:
            body_parts.append(msg.get_content())
        body = "\n".join(body_parts)
        sections = [
            ParsedSection(
                heading="Email Body",
                content=paragraph.strip(),
                order_index=index,
            )
            for index, paragraph in enumerate(self._split_paragraphs(body))
            if paragraph.strip()
        ]
        metadata = {
            "From": msg.get("From", ""),
            "To": msg.get("To", ""),
            "Subject": msg.get("Subject", ""),
        }
        return ParsedDocument(
            source_path=path,
            title=msg.get("Subject") or path.stem,
            author=msg.get("From"),
            created_at=self._parse_email_date(msg.get("Date")),
            sections=sections,
            metadata=metadata,
        )

    def _split_paragraphs(self, text: str) -> List[str]:
        return [paragraph for paragraph in self.PARAGRAPH_BREAK.split(text) if paragraph.strip()]

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            cleaned = value.replace("D:", "").strip("'")
            return datetime.strptime(cleaned[:14], "%Y%m%d%H%M%S")
        except Exception:
            return None

    def _parse_email_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return email.utils.parsedate_to_datetime(value)
        except Exception:
            return None

    def _infer_file_date(self, path: Path) -> Optional[datetime]:
        try:
            stat = path.stat()
            return datetime.fromtimestamp(stat.st_mtime)
        except OSError:
            return None
