"""Document retrieval stays isolated: a real query finds the right page, a weak
or unrelated query returns nothing, and a missing index fails safe (empty, not
an error)."""

from __future__ import annotations

from app.retrieval import DocumentIndex, default_index


def test_relevant_query_finds_a_real_storm_plan_page() -> None:
    index = default_index()
    results = index.retrieve("Total Revenue Requirements by Program Distribution Lateral Undergrounding")
    assert results
    assert results[0].document_title.startswith("Tampa Electric Modified 2026-2035")
    assert all(chunk.page >= 1 for chunk in results)


def test_unrelated_query_returns_nothing() -> None:
    index = default_index()
    assert index.retrieve("kittens playing with a ball of yarn on the moon") == []


def test_empty_query_returns_nothing() -> None:
    index = default_index()
    assert index.retrieve("") == []


def test_missing_index_fails_safe() -> None:
    index = DocumentIndex(chunks=[])
    assert index.is_available is False
    assert index.retrieve("storm protection plan") == []


def test_synthetic_chunks_rank_by_relevance() -> None:
    chunks = [
        {
            "chunk_id": "a",
            "document_id": "doc",
            "document_title": "Doc A",
            "page": 1,
            "text": "Transmission asset upgrades and storm hardening program details.",
        },
        {
            "chunk_id": "b",
            "document_id": "doc",
            "document_title": "Doc A",
            "page": 2,
            "text": "Unrelated financial certification and signature page.",
        },
    ]
    index = DocumentIndex(chunks=chunks)
    results = index.retrieve("transmission asset upgrades storm hardening")
    assert results
    assert results[0].chunk_id == "a"
