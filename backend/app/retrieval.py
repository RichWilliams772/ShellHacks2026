"""Lightweight TF-IDF retrieval over the two source PDFs the pipeline already cites.

scripts/build_assistant_index.py extracts one chunk per PDF page, with page-level
provenance, into data/processed/assistant_document_chunks.json. This module only
reads that file and ranks it against a question - it never opens a PDF and never
touches the GridSync analysis pipeline. If the file is missing, retrieval is simply
unavailable and callers get an empty result, not an error.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.processed_loader import processed_directory

CHUNKS_FILENAME = "assistant_document_chunks.json"

# Below this cosine similarity, a match is too weak to hand to the model as
# evidence - the assistant says the source material isn't available instead of
# guessing from a barely-related page. Not a tuned threshold, just "not zero."
_MIN_SCORE = 0.08
_TOP_K = 4


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    document_title: str
    page: int
    text: str
    score: float


class DocumentIndex:
    """Fits one TF-IDF matrix over the precomputed chunks at construction time."""

    def __init__(self, chunks: list[dict[str, object]] | None = None) -> None:
        if chunks is None:
            chunks = _load_chunks()
        self._chunks = chunks
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        if self._chunks:
            self._vectorizer = TfidfVectorizer(stop_words="english", max_df=0.9)
            self._matrix = self._vectorizer.fit_transform([str(c["text"]) for c in self._chunks])

    @property
    def is_available(self) -> bool:
        return self._vectorizer is not None

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = _TOP_K,
        min_score: float = _MIN_SCORE,
    ) -> list[DocumentChunk]:
        if not self.is_available or not query.strip():
            return []
        query_vector = self._vectorizer.transform([query])  # type: ignore[union-attr]
        scores = cosine_similarity(query_vector, self._matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results: list[DocumentChunk] = []
        for i in ranked[:top_k]:
            if scores[i] < min_score:
                break
            chunk = self._chunks[i]
            results.append(
                DocumentChunk(
                    chunk_id=str(chunk["chunk_id"]),
                    document_id=str(chunk["document_id"]),
                    document_title=str(chunk["document_title"]),
                    page=int(chunk["page"]),  # type: ignore[arg-type]
                    text=str(chunk["text"]),
                    score=float(scores[i]),
                )
            )
        return results


def _load_chunks() -> list[dict[str, object]]:
    path = processed_directory() / CHUNKS_FILENAME
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


_default_index: DocumentIndex | None = None


def default_index() -> DocumentIndex:
    """Built once per process on first use, not on import - keeps a missing or
    absent chunk file from slowing down every backend startup that doesn't need it."""
    global _default_index
    if _default_index is None:
        _default_index = DocumentIndex()
    return _default_index
