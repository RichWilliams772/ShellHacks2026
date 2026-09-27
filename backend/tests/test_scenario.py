"""Hypothetical start-date shifts stay off the published catalog."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.scenario import run_scenario

TOP_ID = "DUKE-P0132__TECO-138005"
TECO_ID = "TECO-138005"
DUKE_ID = "DUKE-P0132"
client = TestClient(create_app(settings=Settings(project_catalog="processed")))


class ScriptedLlm:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.messages: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages.append(messages)
        return self.replies.pop(0)


def _scenario(project_id: str, shift_months: int, opportunity_id: str = TOP_ID):
    return client.post(
        f"/opportunities/{opportunity_id}/scenario",
        json={"project_id": project_id, "shift_months": shift_months},
    )


def test_three_month_shift_changes_only_the_temporary_start_date(monkeypatch) -> None:
    import sys
    from pathlib import Path

    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from analysis.scoring import calculate_coordination_score

    calls: list[tuple[object, ...]] = []
    real = calculate_coordination_score

    def spy(*args: object) -> object:
        calls.append(args)
        return real(*args)

    monkeypatch.setattr("analysis.scoring.calculate_coordination_score", spy)
    before = client.post(
        "/analyze",
        json={"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"},
    ).json()
    project_before = client.get(f"/projects/{TECO_ID}").json()["project"]["start_date"]
    calls.clear()

    response = _scenario(TECO_ID, 3)
    assert response.status_code == 200
    scenario = response.json()["scenario"]
    assert scenario["dates"]["original_start_date"] == "2026-01-01"
    assert scenario["dates"]["scenario_start_date"] == "2026-04-01"
    assert scenario["dates"]["end_date"] == "2026-12-31"
    assert scenario["notice"] == "Hypothetical only; published project data was not changed."
    assert "end date stays fixed" in scenario["assumption"].casefold()
    assert scenario["scenario_temporal"]["temporal_precision"] == "mixed"
    assert scenario["scenario_temporal"]["schedule_overlap_months"] is None
    assert scenario["baseline_temporal"]["schedule_overlap_months"] is None
    assert "month-level overlap" in " ".join(scenario["limitations"])
    assert "not confirmed" in scenario["explanation"].casefold()

    opportunity = client.get(f"/opportunities/{TOP_ID}").json()["opportunity"]
    published = opportunity["published_components"]
    assert calls, "the scenario score must call Aaron's coordination score"
    geographic, temporal, text_score, infrastructure = calls[0]
    assert geographic == published["geographic_score"]
    assert text_score == published["text_similarity_score"]
    assert infrastructure == published["infrastructure_similarity"]
    assert temporal == scenario["scenario_temporal"]["temporal_score"]
    assert scenario["scenario_coordination_score"] == calculate_coordination_score(
        published["geographic_score"],
        temporal,
        published["text_similarity_score"],
        published["infrastructure_similarity"],
    )
    assert scenario["baseline_coordination_score"] == opportunity["coordination_score"]
    assert client.get(f"/projects/{TECO_ID}").json()["project"]["start_date"] == project_before
    after = client.post(
        "/analyze",
        json={"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"},
    ).json()
    assert after == before
    assert opportunity["project_b"]["start_date"] == "2026-01-01"
    assert opportunity["project_a"]["start_date"] is None


def test_missing_start_invalid_project_invalid_shift_and_start_after_end() -> None:
    missing = _scenario(DUKE_ID, 3)
    assert missing.status_code == 400
    assert "no known start date" in missing.json()["detail"].casefold()
    assert "invent" in missing.json()["detail"].casefold()

    unknown_project = _scenario("NO-SUCH", 3)
    assert unknown_project.status_code == 400
    assert "not part of this opportunity" in unknown_project.json()["detail"].casefold()

    invalid_shift = _scenario(TECO_ID, 48)
    assert invalid_shift.status_code == 422

    too_late = _scenario(TECO_ID, 13)
    assert too_late.status_code == 400
    assert "after the project's end date" in too_late.json()["detail"].casefold()

    missing_pair = _scenario(TECO_ID, 3, "DUKE-NOPE__TECO-NOPE")
    assert missing_pair.status_code == 404


def test_chat_reports_the_computed_scenario_and_drops_an_invented_increase(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GRIDSYNC_LLM_API_KEY", "test-key")
    fake = ScriptedLlm(
        [
            json.dumps({"project_id": TECO_ID, "shift_months": 3}),
            "The coordination score increases to 90.",
        ]
    )
    client.app.state.llm_client = fake
    response = client.post(
        "/assistant/query",
        json={
            "query": "What if the TECO project started three months later?",
            "opportunity_id": TOP_ID,
        },
    )
    assert response.status_code == 200
    body = response.json()
    scenario = body["scenario"]
    assert scenario["scenario_coordination_score"] == scenario["baseline_coordination_score"]
    assert scenario["scenario_temporal"]["schedule_overlap_months"] is None
    assert "63.3" in body["answer"]
    assert "unchanged" in body["answer"].casefold()
    assert "increases" not in body["answer"].casefold()
    assert "90" not in body["answer"]
    choice = fake.messages[0][-1]["content"]
    assert "coordination_score" not in choice
    assert "distance" not in choice
    explanation = fake.messages[1][-1]["content"]
    assert "63.3" in explanation
    assert "do not calculate" in fake.messages[1][0]["content"].casefold()


def test_ambiguous_scenario_question_does_not_invent_a_score(monkeypatch) -> None:
    monkeypatch.setenv("GRIDSYNC_LLM_API_KEY", "test-key")
    fake = ScriptedLlm(
        ['{"clarify":"Which project should move, and by how many months?"}']
    )
    client.app.state.llm_client = fake
    response = client.post(
        "/assistant/query",
        json={"query": "What if a project started later?", "opportunity_id": TOP_ID},
    )
    body = response.json()
    assert body["scenario"] is None
    assert "Which project" in body["answer"]
    assert "63.3" not in body["answer"]
    assert len(fake.messages) == 1


def test_scenario_controls_remain_when_the_model_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("GRIDSYNC_LLM_API_KEY", raising=False)
    client.app.state.llm_client = None
    response = client.post(
        "/assistant/query",
        json={
            "query": "What if the TECO project started three months later?",
            "opportunity_id": TOP_ID,
        },
    )
    body = response.json()
    assert body["llm_used"] is False
    assert body["scenario"] is None
    assert "What-If controls" in body["answer"]
    assert "increase" not in body["answer"].casefold()
    direct = _scenario(TECO_ID, 3)
    assert direct.status_code == 200
    assert direct.json()["scenario"]["dates"]["scenario_start_date"] == "2026-04-01"


def test_duke_in_service_year_scenario_keeps_the_published_year(monkeypatch) -> None:
    import sys
    from pathlib import Path

    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from analysis.scoring import calculate_coordination_score
    from analysis.temporal import calculate_temporal_features

    calls: list[tuple[object, ...]] = []
    real = calculate_coordination_score

    def spy(*args: object) -> object:
        calls.append(args)
        return real(*args)

    monkeypatch.setattr("analysis.scoring.calculate_coordination_score", spy)
    published_before = client.get(f"/projects/{DUKE_ID}").json()["project"]
    analyzed_before = client.post(
        "/analyze",
        json={"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"},
    ).json()
    calls.clear()

    top_before = next(item for item in analyzed_before["opportunities"] if item["id"] == TOP_ID)
    duke = top_before["project_a"]
    teco = top_before["project_b"]
    response = client.post(
        f"/opportunities/{TOP_ID}/scenario",
        json={"project_id": DUKE_ID, "in_service_year": 2026},
    )
    assert response.status_code == 200
    scenario = response.json()["scenario"]
    features = calculate_temporal_features(
        {
            "start": duke["start_date"],
            "end": duke["end_date"],
            "in_service_year": 2026,
            "date_precision": duke["date_precision"],
        },
        {
            "start": teco["start_date"],
            "end": teco["end_date"],
            "in_service_year": teco["estimated_in_service_year"],
            "date_precision": teco["date_precision"],
        },
    )
    assert scenario["dates"]["published_in_service_year"] == 2027
    assert scenario["dates"]["hypothetical_in_service_year"] == 2026
    assert scenario["dates"]["scenario_start_date"] is None
    assert scenario["scenario_temporal"]["schedule_overlap_months"] is None
    assert features["schedule_overlap_months"] is None
    assert scenario["scenario_temporal"]["temporal_precision"] == "mixed"
    assert scenario["scenario_temporal"]["temporal_score"] == features["temporal_score"]
    assert "year-level estimate" in scenario["assumption"]
    assert "not confirmed construction overlap" in scenario["assumption"]
    assert "stays 2027" in scenario["assumption"]
    assert "uses 2026" in scenario["assumption"]
    published = top_before["published_components"]
    matched = [
        args
        for args in calls
        if args
        == (
            published["geographic_score"],
            features["temporal_score"],
            published["text_similarity_score"],
            published["infrastructure_similarity"],
        )
    ]
    assert matched, "the year scenario must rescore with Aaron's published non-temporal components"
    assert scenario["baseline_coordination_score"] == top_before["coordination_score"]
    assert scenario["scenario_coordination_score"] == calculate_coordination_score(
        published["geographic_score"],
        features["temporal_score"],
        published["text_similarity_score"],
        published["infrastructure_similarity"],
    )
    assert client.get(f"/projects/{DUKE_ID}").json()["project"] == published_before
    assert published_before["estimated_in_service_year"] == 2027
    assert published_before["start_date"] is None
    analyzed_after = client.post(
        "/analyze",
        json={"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"},
    ).json()
    assert analyzed_after == analyzed_before
    detail = client.get(f"/opportunities/{TOP_ID}").json()["opportunity"]
    assert detail["project_a"]["estimated_in_service_year"] == 2027
    assert detail["project_a"]["start_date"] is None

    month_project = client.post(
        f"/opportunities/{TOP_ID}/scenario",
        json={"project_id": TECO_ID, "in_service_year": 2026},
    )
    assert month_project.status_code == 400
    assert "known start date" in month_project.json()["detail"]


def test_run_scenario_leaves_the_opportunity_start_date_in_place() -> None:
    from app.service import AnalysisService

    service = client.app.state.service
    assert isinstance(service, AnalysisService)
    opportunity = service.get_opportunity(TOP_ID)
    original = opportunity.project_b.start_date
    outcome = run_scenario(opportunity, TECO_ID, 3)
    assert outcome.dates.scenario_start_date == "2026-04-01"
    assert opportunity.project_b.start_date == original
