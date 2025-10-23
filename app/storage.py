"""SQLite storage utilities for parsed e-discovery documents."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .parser import ParsedDocument, ParsedSection


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    title TEXT,
    author TEXT,
    created_at TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    heading TEXT,
    content TEXT NOT NULL,
    order_index INTEGER NOT NULL
);
"""


@dataclass
class SectionRecord:
    document_title: str
    document_path: str
    heading: Optional[str]
    content: str
    order_index: int


class DocumentStorage:
    """Handles persistence of parsed documents and sections."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def store_documents(self, documents: Iterable[ParsedDocument]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            for document in documents:
                cursor = conn.execute(
                    "INSERT INTO documents(path, title, author, created_at, metadata) VALUES (?, ?, ?, ?, ?)",
                    (
                        str(document.source_path),
                        document.title,
                        document.author,
                        document.created_at.isoformat() if document.created_at else None,
                        repr(document.metadata),
                    ),
                )
                document_id = cursor.lastrowid
                for section in document.sections:
                    conn.execute(
                        "INSERT INTO sections(document_id, heading, content, order_index) VALUES (?, ?, ?, ?)",
                        (
                            document_id,
                            section.heading,
                            section.content,
                            section.order_index,
                        ),
                    )
            conn.commit()

    def search_sections(self, keywords: str, limit: int = 20) -> List[SectionRecord]:
        like = f"%{keywords.lower()}%"
        query = """
        SELECT d.title, d.path, s.heading, s.content, s.order_index
        FROM sections s
        JOIN documents d ON d.id = s.document_id
        WHERE LOWER(s.content) LIKE ?
        ORDER BY s.order_index
        LIMIT ?
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, (like, limit))
            rows = cursor.fetchall()
        return [
            SectionRecord(
                document_title=row[0],
                document_path=row[1],
                heading=row[2],
                content=row[3],
                order_index=row[4],
            )
            for row in rows
        ]

    def fetch_all_sections(self) -> List[SectionRecord]:
        query = """
        SELECT d.title, d.path, s.heading, s.content, s.order_index
        FROM sections s
        JOIN documents d ON d.id = s.document_id
        ORDER BY d.id, s.order_index
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query).fetchall()
        return [
            SectionRecord(
                document_title=row[0],
                document_path=row[1],
                heading=row[2],
                content=row[3],
                order_index=row[4],
            )
            for row in rows
        ]
