"""Insight generation utilities using TF-IDF retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .storage import DocumentStorage, SectionRecord


@dataclass
class Insight:
    """Represents an insight derived from document sections."""

    answer: str
    citation: str
    snippet: str
    score: float


class InsightEngine:
    """Generates insights backed by primary-source quotes."""

    def __init__(self, storage: DocumentStorage, max_results: int = 3) -> None:
        self.storage = storage
        self.max_results = max_results
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._matrix = None
        self._sections: List[SectionRecord] = []

    def refresh_index(self) -> None:
        self._sections = self.storage.fetch_all_sections()
        corpus = [section.content for section in self._sections]
        if corpus:
            self._vectorizer = TfidfVectorizer(stop_words="english")
            self._matrix = self._vectorizer.fit_transform(corpus)
        else:
            self._vectorizer = None
            self._matrix = None

    def answer_query(self, query: str) -> List[Insight]:
        if not query.strip():
            return []
        if not self._vectorizer or self._matrix is None or not self._sections:
            self.refresh_index()
        if not self._vectorizer or self._matrix is None or not self._sections:
            return []
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        ranked = sorted(
            zip(self._sections, scores), key=lambda item: item[1], reverse=True
        )
        insights: List[Insight] = []
        for section, score in ranked[: self.max_results]:
            if score < 0.05:
                continue
            citation = self._build_citation(section)
            snippet = section.content.strip()
            answer = f"Source: {citation}\nExtract: {snippet}"
            insights.append(Insight(answer=answer, citation=citation, snippet=snippet, score=float(score)))
        return insights

    def _build_citation(self, section: SectionRecord) -> str:
        heading = f" | {section.heading}" if section.heading else ""
        return f"{section.document_title}{heading} ({section.document_path})"
