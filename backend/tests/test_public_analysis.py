"""Processed /analyze uses Aaron's precomputed opportunities."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

processed = TestClient(create_app(settings=Settings(project_catalog="processed")))
demo = TestClient(create_app(settings=Settings(project_catalog="demo")))


def _analyze(**extra: object) -> dict[str, object]:
    body = {"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"}
    body.update(extra)
    response = processed.post("/analyze", json=body)
    assert response.status_code == 200
    payload: dict[str, object] = response.json()
    return payload


def test_analyze_returns_ranked_public_opportunities() -> None:
    body = _analyze()
    opportunities = body["opportunities"]
    assert isinstance(opportunities, list)
    assert body["dataset_status"] == "verified_public"
    assert body["contains_demo_data"] is False
    assert body["contains_verified_public_data"] is True
    assert body["pairs_evaluated"] == 160
    assert body["pairs_discarded"] == 110
    assert body["opportunity_count"] == 50
    assert len(opportunities) == 50
    top = opportunities[0]
    assert isinstance(top, dict)
    assert top["id"] == "DUKE-P0132__TECO-138005"
    assert top["coordination_score"] == 63.3
    assert top["data_type"] == "public"
    assert top["reasons"][0].startswith("Known project endpoints")
    components = top["published_components"]
    assert isinstance(components, dict)
    assert components["opportunity_rank"] == 1
    assert components["geographic_score"] == 80
    assert components["temporal_score"] == 50
    assert components["text_similarity_score"] == 31.6
    assert components["infrastructure_similarity"] == 100
    assert components["score_confidence"] == "HIGH"
    assert components["scale"] == "0_to_100"
    ranks = [item["published_components"]["opportunity_rank"] for item in opportunities]
    assert ranks == sorted(ranks)

    listed = processed.get(
        "/opportunities",
        params={"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"},
    )
    assert listed.status_code == 200
    assert listed.json()["opportunities"][0]["id"] == top["id"]

    detail = processed.get("/opportunities/DUKE-P0132__TECO-138005")
    assert detail.status_code == 200
    found = detail.json()
    assert found["dataset_status"] == "verified_public"
    assert found["opportunity"]["coordination_score"] == 63.3
    assert processed.get("/opportunities/DUKE-DEMO-001__TECO-DEMO-001").status_code == 404


def test_public_projects_keep_geometry_provenance_and_nulls() -> None:
    opportunity = _analyze()["opportunities"][0]
    assert isinstance(opportunity, dict)
    duke = opportunity["project_a"]
    teco = opportunity["project_b"]
    assert isinstance(duke, dict)
    assert isinstance(teco, dict)
    assert duke["id"] == "DUKE-P0132"
    assert duke["geometry"]["type"] == "LineString"
    assert duke["location_confidence"] == "HIGH"
    assert duke["date_precision"] == "year"
    assert duke["estimated_in_service_year"] == 2027
    assert duke["start_date"] is None
    assert duke["source_url"].startswith("https://www.duke-energy.com/")
    assert duke["provenance_gaps"] == []
    assert duke["customers_impacted"] is None
    assert teco["id"] == "TECO-138005"
    assert teco["geometry"]["type"] == "LineString"
    assert teco["source_url"] is None
    assert teco["provenance_gaps"] == ["source_url"]
    assert teco["source_url_note"] is not None
    assert teco["capital_cost"] != 0
    detail = processed.get("/opportunities/DUKE-P0132__TECO-138005").text
    assert '"nan"' not in detail.lower()


def test_mixed_precision_resources_and_unit_conversion() -> None:
    top = _analyze()["opportunities"][0]
    assert isinstance(top, dict)
    features = top["features"]
    components = top["published_components"]
    assert isinstance(features, dict)
    assert isinstance(components, dict)
    assert features["distance_miles"] == 15.05
    assert features["distance_label"] == "minimum distance between known endpoints"
    assert features["distance_similarity"] is None
    assert features["schedule_similarity"] is None
    assert features["temporal_precision"] == "mixed"
    assert features["schedule_overlap_months"] is None
    assert features["year_difference"] == 1
    assert features["same_active_year"] is False
    assert features["text_similarity"] == pytest.approx(0.316)
    assert features["infrastructure_similarity"] == pytest.approx(1.0)
    assert components["text_similarity_score"] == 31.6
    assert components["infrastructure_similarity"] == 100
    package = top["coordination_package"]
    assert isinstance(package, dict)
    resources = package["resources"]
    assert isinstance(resources, list)
    assert resources
    assert {item["name"] for item in resources} >= {"specialized_line_crews", "heavy_equipment"}
    assert all(item["strength"] == "HIGH" and item["potential"] == "HIGH" for item in resources)
    assert package["shared_resources"][0]["resource"] == resources[0]["name"]

    missing_timing = next(
        item
        for item in _analyze()["opportunities"]
        if isinstance(item, dict) and item["id"] == "DUKE-P0017__TECO-138005"
    )
    assert isinstance(missing_timing, dict)
    published = missing_timing["published_components"]
    timing = missing_timing["features"]
    assert isinstance(published, dict)
    assert isinstance(timing, dict)
    assert published["temporal_score"] is None
    assert published["geographic_score"] == 0
    assert timing["temporal_precision"] == "unknown"
    assert timing["schedule_overlap_months"] is None
    assert timing["year_difference"] is None
    assert missing_timing["coordination_score"] == 20.5
    far_resources = missing_timing["coordination_package"]["resources"]
    assert far_resources
    assert all(item["potential"] == "MEDIUM" for item in far_resources)


def test_public_filters_and_explicit_demo_mode() -> None:
    near = _analyze(max_distance_miles=16)
    near_rows = near["opportunities"]
    assert isinstance(near_rows, list)
    assert near_rows[0]["id"] == "DUKE-P0132__TECO-138005"
    assert all(item["features"]["distance_miles"] <= 16 for item in near_rows)

    far_only = _analyze(max_distance_miles=10)
    assert all(item["id"] != "DUKE-P0132__TECO-138005" for item in far_only["opportunities"])

    high_score = _analyze(min_coordination_score=63.3)
    assert high_score["opportunities"][0]["id"] == "DUKE-P0132__TECO-138005"
    assert all(item["coordination_score"] >= 63.3 for item in high_score["opportunities"])
    above = _analyze(min_coordination_score=64)
    assert above["opportunity_count"] < high_score["opportunity_count"]

    typed = _analyze(project_type="transmission_upgrade")
    assert any(item["id"] == "DUKE-P0132__TECO-138005" for item in typed["opportunities"])
    assert _analyze(project_type="not-a-real-type")["opportunity_count"] == 0

    year = _analyze(year=2027)
    assert any(item["id"] == "DUKE-P0132__TECO-138005" for item in year["opportunities"])
    assert _analyze(year=1999)["opportunity_count"] == 0

    demo_response = demo.post(
        "/analyze",
        json={"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"},
    )
    assert demo_response.status_code == 200
    demo_body = demo_response.json()
    assert demo_body["dataset_status"] == "demo"
    assert demo_body["contains_demo_data"] is True
    assert demo_body["opportunities"][0]["data_type"] == "demo"
    assert demo_body["opportunities"][0]["project_a"]["id"].startswith("DUKE-DEMO-")
    assert demo_body["opportunities"][0]["coordination_package"]["resources"]


def test_public_adapter_does_not_call_backend_calculations() -> None:
    source = Path(__file__).resolve().parents[1].joinpath("app", "public_analysis.py").read_text()
    assert "analyze_projects" in source
    for blocked in (
        "app.geographic",
        "app.temporal",
        "app.scoring",
        "app.similarity",
        "app.resources",
        "app.analysis",
        "analyze_pair",
        "haversine",
        "cosine_similarity",
    ):
        assert blocked not in source
