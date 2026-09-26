"""Selected-opportunity explanations use a mocked model client."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.assistant import LlmCallError
from app.config import Settings
from app.main import create_app

TOP_ID = "DUKE-P0132__TECO-138005"
NULL_TIMING_ID = "DUKE-P0017__TECO-138005"
client = TestClient(create_app(settings=Settings(project_catalog="processed")))


class FakeLlm:
    def __init__(
        self,
        text: str = "Structured explanation.",
        error: Exception | None = None,
    ) -> None:
        self.text = text
        self.error = error
        self.messages: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages.append(messages)
        if self.error is not None:
            raise self.error
        return self.text


def _ask(opportunity_id: str, query: str = "Explain this opportunity.") -> object:
    response = client.post(
        "/assistant/query",
        json={
            "query": query,
            "utility_a": "Duke Energy Florida",
            "utility_b": "Tampa Electric",
            "opportunity_id": opportunity_id,
        },
    )
    return response


def test_selected_opportunity_sends_one_evidence_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRIDSYNC_LLM_API_KEY", "test-key")
    fake = FakeLlm("The supplied score is 63.3.")
    client.app.state.llm_client = fake
    response = _ask(TOP_ID)
    assert response.status_code == 200
    body = response.json()
    assert body["llm_used"] is True
    assert body["llm_configured"] is True
    assert body["answer"] == "The supplied score is 63.3."
    assert body["opportunities"][0]["id"] == TOP_ID
    assert body["opportunities"][0]["coordination_score"] == 63.3
    assert "test-key" not in response.text
    assert len(fake.messages) == 1
    user = fake.messages[0][1]["content"]
    evidence = json.loads(user)["evidence"]
    assert evidence["opportunity_id"] == TOP_ID
    assert evidence["coordination_score"] == 63.3
    assert evidence["features"]["distance_miles"] == 15.05
    assert evidence["features"]["distance_label"] == "minimum distance between known endpoints"
    assert evidence["features"]["temporal_precision"] == "mixed"
    assert evidence["features"]["schedule_overlap_months"] is None
    assert evidence["project_a"]["location_confidence"] == "HIGH"
    assert evidence["project_a"]["source_url"].startswith("https://www.duke-energy.com/")
    assert evidence["project_b"]["source_url"] is None
    assert evidence["reasons"]
    assert evidence["shared_resources"]
    assert "DUKE-P0313" not in user
    assert "known endpoints" in fake.messages[0][0]["content"]


def test_missing_opportunity_is_not_sent_to_the_model() -> None:
    fake = FakeLlm()
    client.app.state.llm_client = fake
    response = _ask("DUKE-NOPE__TECO-NOPE")
    assert response.status_code == 404
    assert fake.messages == []


def test_missing_key_does_not_claim_a_model_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRIDSYNC_LLM_API_KEY", raising=False)
    fake = FakeLlm("should not be used")
    client.app.state.llm_client = None
    response = _ask(TOP_ID)
    assert response.status_code == 200
    body = response.json()
    assert body["llm_used"] is False
    assert body["llm_configured"] is False
    assert "No language model is configured" in body["answer"]
    assert "63.3" in body["answer"]
    assert fake.messages == []
    assert "should not be used" not in body["answer"]


def test_provider_failure_keeps_llm_used_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRIDSYNC_LLM_API_KEY", "test-key")
    fake = FakeLlm(error=LlmCallError("sk-live-secret"))
    client.app.state.llm_client = fake
    response = _ask(TOP_ID)
    assert response.status_code == 200
    body = response.json()
    assert body["llm_used"] is False
    assert body["llm_configured"] is True
    assert "did not respond" in body["answer"]
    assert "sk-live-secret" not in response.text
    assert body["opportunities"][0]["coordination_score"] == 63.3


def test_null_temporal_evidence_stays_null(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRIDSYNC_LLM_API_KEY", "test-key")
    fake = FakeLlm("Timing was not measured.")
    client.app.state.llm_client = fake
    response = _ask(NULL_TIMING_ID)
    assert response.status_code == 200
    assert response.json()["llm_used"] is True
    evidence = json.loads(fake.messages[0][1]["content"])["evidence"]
    assert evidence["published_components"]["temporal_score"] is None
    assert evidence["published_components"]["geographic_score"] == 0
    assert evidence["features"]["schedule_overlap_months"] is None
    assert evidence["features"]["year_difference"] is None
    assert evidence["project_a"]["estimated_in_service_year"] is None
    assert evidence["project_b"]["source_url"] is None


def test_query_without_opportunity_id_does_not_call_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRIDSYNC_LLM_API_KEY", "test-key")
    fake = FakeLlm("should not be used")
    client.app.state.llm_client = fake
    response = client.post(
        "/assistant/query",
        json={"query": "Show me the strongest opportunities."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["llm_used"] is False
    assert body["llm_configured"] is True
    assert fake.messages == []
    assert body["opportunities"]
