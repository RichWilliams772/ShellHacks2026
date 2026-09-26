"""API contract, demo labeling, filters, and stable ids."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.config import Settings
from app.fixtures import DUKE_CLOSE_ID, DUKE_FAR_ID, TECO_CLOSE_ID
from app.main import create_app

client = TestClient(create_app(settings=Settings()))


def test_health_and_utilities_are_labeled_demo() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["dataset_status"] == "demo"
    assert body["contains_demo_data"] is True
    assert body["contains_verified_public_data"] is False
    assert "not verified" in body["data_notice"]

    utilities = client.get("/utilities").json()
    assert [item["name"] for item in utilities["utilities"]] == [
        "Duke Energy Florida",
        "Tampa Electric",
    ]
    assert utilities["dataset_status"] == "demo"


def test_projects_keep_demo_provenance_and_nulls() -> None:
    response = client.get("/projects")
    assert response.status_code == 200
    projects = response.json()["projects"]
    assert len(projects) == 8
    for project in projects:
        assert project["data_type"] == "demo"
        assert "demo" in project["source_name"].lower()
        assert project["source_url"] == "https://example.invalid/gridsync/demo-fixtures"
        assert "psc.state.fl.us" not in project["source_url"]
        assert project["capital_cost"] is None
        assert project["customers_impacted"] is None
    missing = client.get("/projects/DUKE-DEMO-003").json()["project"]
    assert missing["latitude"] is None
    assert missing["voltage_kv"] is None
    assert missing["description"] is None
    assert missing["start_date"] == "2027"
    assert client.get("/projects/NO-SUCH").status_code == 404


def test_analyze_is_cross_utility_and_explainable() -> None:
    response = client.post(
        "/analyze",
        json={"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dataset_status"] == "demo"
    assert body["projects_analyzed"] == 8
    assert body["pairs_evaluated"] == 16
    assert body["pairs_discarded"] == 3
    assert body["weights"] == {
        "geographic_proximity": 0.4,
        "schedule_overlap": 0.3,
        "project_similarity": 0.2,
        "infrastructure_similarity": 0.1,
    }
    assert "not a probability" in body["score_interpretation"]
    assert body["opportunity_count"] == len(body["opportunities"])
    ids = [item["id"] for item in body["opportunities"]]
    scores = [item["coordination_score"] for item in body["opportunities"]]
    numeric_scores = [score for score in scores if score is not None]
    assert numeric_scores == sorted(numeric_scores, reverse=True)
    assert len(ids) == len(set(ids))
    for opportunity in body["opportunities"]:
        assert opportunity["project_a"]["utility"] != opportunity["project_b"]["utility"]
        assert opportunity["data_type"] == "demo"
        assert opportunity["coarse_filter_excluded"] is False
        assert "features_used" in opportunity
        assert "evidence_gaps" in opportunity
        assert "coordination_package" in opportunity
        distance = opportunity["features"]["distance_miles"]
        assert distance is None or distance <= 100
    hero = _pair(body["opportunities"], DUKE_CLOSE_ID, TECO_CLOSE_ID)
    assert hero["features"]["temporal_precision"] == "day"
    assert hero["features"]["schedule_overlap_months"] is not None
    assert hero["features"]["text_similarity"] is not None
    assert hero["features"]["distance_miles"] < 10
    year_pair = _pair(body["opportunities"], "DUKE-DEMO-002", "TECO-DEMO-002")
    assert year_pair["features"]["temporal_precision"] == "year"
    assert year_pair["features"]["schedule_overlap_months"] is None
    assert year_pair["features"]["overlap_days"] is None
    assert not re.search(r"\d+(?:\.\d+)? months", " ".join(year_pair["reasons"]))

    swapped = client.post(
        "/analyze",
        json={"utility_a": "TECO", "utility_b": "Duke Energy Florida"},
    )
    swapped_ids = {item["id"] for item in swapped.json()["opportunities"]}
    assert swapped_ids == set(ids)
    same = client.post(
        "/analyze",
        json={"utility_a": "Duke Energy Florida", "utility_b": "Duke Energy Florida"},
    )
    assert same.status_code == 400


def test_filters_and_stable_detail_lookup() -> None:
    listed = client.get("/opportunities").json()
    far_lookup = client.get(
        "/opportunities/duke-energy-florida:DUKE-DEMO-004__tampa-electric:TECO-DEMO-001"
    )
    assert far_lookup.status_code == 200
    assert far_lookup.json()["opportunity"]["coarse_filter_excluded"] is True
    assert DUKE_FAR_ID not in {
        item["project_a"]["id"]
        for item in listed["opportunities"]
        if item["project_b"]["id"] == TECO_CLOSE_ID
    }
    nearby = client.get("/opportunities", params={"max_distance_miles": 25})
    for opportunity in nearby.json()["opportunities"]:
        assert opportunity["features"]["distance_miles"] is not None
        assert opportunity["features"]["distance_miles"] <= 25
    year = client.get("/opportunities", params={"year": 2028})
    for opportunity in year.json()["opportunities"]:
        assert 2028 in opportunity["features"]["overlapping_years"]
    typed = client.get("/opportunities", params={"project_type": "transmission_upgrade"})
    assert typed.json()["opportunities"]
    for opportunity in typed.json()["opportunities"]:
        types = {
            opportunity["project_a"]["project_type"],
            opportunity["project_b"]["project_type"],
        }
        assert "transmission_upgrade" in types or any(
            value and "transmission" in value for value in types
        )
    empty = client.get("/opportunities", params={"min_coordination_score": 100})
    assert empty.json()["opportunities"] == [] or all(
        item["coordination_score"] >= 100 for item in empty.json()["opportunities"]
    )
    detail_id = listed["opportunities"][0]["id"]
    detail = client.get(f"/opportunities/{detail_id}")
    assert detail.status_code == 200
    assert detail.json()["dataset_status"] == "demo"
    assert detail.json()["opportunity"]["id"] == detail_id
    assert client.get("/opportunities/not-an-id").status_code == 404


def _pair(opportunities: list[dict[str, object]], left_id: str, right_id: str) -> dict[str, object]:
    expected = {left_id, right_id}
    for opportunity in opportunities:
        project_a = opportunity["project_a"]
        project_b = opportunity["project_b"]
        assert isinstance(project_a, dict)
        assert isinstance(project_b, dict)
        if {project_a["id"], project_b["id"]} == expected:
            return opportunity
    raise AssertionError(f"missing pair {left_id} {right_id}")
