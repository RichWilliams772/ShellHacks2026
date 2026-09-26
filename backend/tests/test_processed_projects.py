"""Processed Duke and TECO files on the project retrieval endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.processed_loader import ProcessedProjectLoader

client = TestClient(create_app(settings=Settings(project_catalog="processed")))


def test_both_processed_files_load_without_filling_blanks() -> None:
    projects = ProcessedProjectLoader().load_projects()
    by_id = {project.id: project for project in projects}
    assert len(projects) == 26
    assert {project.data_type for project in projects} == {"public"}

    duke = by_id["DUKE-P0132"]
    assert duke.utility == "Duke Energy Florida"
    assert duke.voltage_kv == 230
    assert duke.voltage_min_kv == 230
    assert duke.latitude == 27.871757000000002
    assert duke.longitude == -82.7384145
    assert duke.start_date is None
    assert duke.end_date is None
    assert duke.capital_cost is None
    assert duke.date_precision == "year"
    assert duke.estimated_in_service_year == 2027
    assert duke.location_confidence == "HIGH"
    assert duke.location_method == "exact_substation_endpoints"
    assert duke.from_latitude == 27.829953
    assert duke.to_longitude == -82.7728
    assert duke.geometry is not None
    assert duke.geometry["type"] == "LineString"
    assert duke.geometry_type == "approximate_corridor"
    assert duke.source_url is not None
    assert duke.source_url.startswith("https://www.duke-energy.com/")
    assert duke.provenance_gaps == []
    assert "Our Grid Future" in duke.source_name
    assert duke.geography_source is not None

    missing_geo = by_id["TECO-66833"]
    assert missing_geo.latitude is None
    assert missing_geo.longitude is None
    assert missing_geo.from_latitude is None
    assert missing_geo.to_latitude is None
    assert missing_geo.capital_cost == 5787530
    assert missing_geo.capital_cost != 0
    assert missing_geo.location_confidence == "UNKNOWN"
    assert missing_geo.date_precision == "month"
    assert missing_geo.start_date == "2026-01-01"
    assert missing_geo.end_date == "2026-12-31"
    assert missing_geo.source_url is None
    assert missing_geo.provenance_gaps == ["source_url"]
    assert missing_geo.source_url_note is not None
    assert "http" not in missing_geo.source_name
    assert "Storm Protection Plan" in missing_geo.source_name

    partial = by_id["TECO-66653"]
    assert partial.location_confidence == "MEDIUM"
    assert partial.from_latitude == 27.98724072400006
    assert partial.to_latitude is None
    assert partial.to_longitude is None
    assert partial.geometry is not None
    assert partial.geometry["type"] == "Point"

    labeled = by_id["TECO-230037"]
    assert labeled.voltage_kv == 230
    assert labeled.voltage_label == "138/230 kV"
    assert labeled.location_method == "exact_substation_endpoints"
    assert labeled.circuit_endpoint_source is not None
    assert labeled.form1_schedule is not None
    assert labeled.source_url is None


def test_retrieval_endpoints_serve_public_records_and_keep_scores_demo() -> None:
    utilities = client.get("/utilities")
    assert utilities.status_code == 200
    body = utilities.json()
    assert body["dataset_status"] == "verified_public"
    assert body["contains_verified_public_data"] is True
    assert body["contains_demo_data"] is False
    assert "source_url" in body["data_notice"]
    assert {item["name"]: item["project_count"] for item in body["utilities"]} == {
        "Duke Energy Florida": 10,
        "Tampa Electric": 16,
    }

    projects = client.get("/projects")
    assert projects.status_code == 200
    listed = projects.json()
    assert listed["count"] == 26
    assert listed["dataset_status"] == "verified_public"
    assert all(project["data_type"] == "public" for project in listed["projects"])
    assert '"nan"' not in projects.text
    assert "NaN" not in projects.text

    detail = client.get("/projects/TECO-66833")
    assert detail.status_code == 200
    project = detail.json()["project"]
    assert project["latitude"] is None
    assert project["capital_cost"] == 5787530
    assert project["source_url"] is None
    assert project["provenance_gaps"] == ["source_url"]
    assert project["customers_impacted"] is None
    assert project["date_precision"] == "month"
    assert project["location_confidence"] == "UNKNOWN"
    assert detail.json()["dataset_status"] == "verified_public"
    assert client.get("/projects/NO-SUCH").status_code == 404

    duke = client.get("/projects/DUKE-P0017").json()["project"]
    assert duke["ownership_confidence"] == "MEDIUM"
    assert duke["source_url"] is not None
    assert duke["start_date"] is None
    assert duke["estimated_in_service_year"] is None
    assert duke["date_precision"] is None

    analyze = client.post(
        "/analyze",
        json={"utility_a": "Duke Energy Florida", "utility_b": "Tampa Electric"},
    )
    assert analyze.status_code == 200
    scored = analyze.json()
    assert scored["dataset_status"] == "demo"
    assert scored["contains_demo_data"] is True
    assert scored["contains_verified_public_data"] is False
    assert "demo" in scored["data_notice"].lower()
    for opportunity in scored["opportunities"]:
        assert opportunity["data_type"] == "demo"
        assert opportunity["project_a"]["id"].startswith("DUKE-DEMO-")
        assert opportunity["project_b"]["id"].startswith("TECO-DEMO-")
