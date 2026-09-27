"""Assistant retrieval stays inside structured results."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

client = TestClient(create_app(settings=Settings()))


@pytest.fixture(autouse=True)
def _no_live_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRIDSYNC_LLM_API_KEY", raising=False)


ASSISTANT_SOURCE = (
    Path(__file__).resolve().parents[1] / "app" / "assistant.py"
).read_text(encoding="utf-8")


def test_assistant_module_does_not_calculate_features() -> None:
    for forbidden in (
        "haversine",
        "compare_schedules",
        "cosine_similarity",
        "from app.geographic",
        "from app.temporal",
        "from app.scoring",
        "from app.resources",
    ):
        assert forbidden not in ASSISTANT_SOURCE


def test_assistant_answers_from_structured_results() -> None:
    strongest = client.post(
        "/assistant/query",
        json={"query": "Show me the strongest opportunities."},
    )
    assert strongest.status_code == 200
    body = strongest.json()
    assert body["dataset_status"] == "demo"
    assert body["llm_used"] is False
    assert body["assistant_mode"] == "structured_retrieval"
    assert body["opportunities"]
    assert len(body["opportunities"]) <= 5
    scores = [item["coordination_score"] for item in body["opportunities"]]
    assert scores == sorted(scores, reverse=True)

    nearby = client.post(
        "/assistant/query",
        json={"query": "Show projects within 25 miles."},
    )
    for opportunity in nearby.json()["opportunities"]:
        assert opportunity["features"]["distance_miles"] <= 25

    year = client.post(
        "/assistant/query",
        json={"query": "Which projects overlap in 2028?"},
    )
    assert year.json()["opportunities"]
    for opportunity in year.json()["opportunities"]:
        assert 2028 in opportunity["features"]["overlapping_years"]

    why = client.post(
        "/assistant/query",
        json={"query": "Why did GridSync match these projects?"},
    )
    top_reason = why.json()["opportunities"][0]["reasons"][0]
    answer = why.json()["answer"]
    assert "Why it matched" in answer
    assert "What's missing" in answer
    assert top_reason.replace("_", " ") in answer or "Both projects involve" in answer

    resources = client.post(
        "/assistant/query",
        json={"query": "What resources could these projects potentially coordinate?"},
    )
    package = resources.json()["opportunities"][0]["coordination_package"]
    if package["shared_resources"]:
        assert package["shared_resources"][0]["label"] in resources.json()["answer"]
    else:
        assert package["evidence_note"] in resources.json()["answer"]

    transmission = client.post(
        "/assistant/query",
        json={
            "query": "Show me the strongest transmission coordination opportunities before 2030."
        },
    )
    assert transmission.json()["opportunities"]
    for opportunity in transmission.json()["opportunities"]:
        types = (
            opportunity["project_a"]["project_type"],
            opportunity["project_b"]["project_type"],
        )
        assert any(value and "transmission" in value for value in types)
        assert int(opportunity["project_a"]["end_date"][:4]) < 2030
        assert int(opportunity["project_b"]["end_date"][:4]) < 2030


def test_assistant_does_not_invent_savings_and_core_api_ignores_llm_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRIDSYNC_LLM_API_KEY", "test-key")
    refused = client.post(
        "/assistant/query",
        json={"query": "What savings and ROI should we expect?"},
    )
    body = refused.json()
    assert body["opportunities"] == []
    assert body["llm_used"] is False
    assert body["llm_configured"] is True
    assert "does not calculate savings" in body["answer"]
    assert "$" not in body["answer"]
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["dataset_status"] == "demo"
