"""Shared project builder for engine tests."""

from __future__ import annotations

from app.fixtures import DEMO_SOURCE_NAME, DEMO_SOURCE_URL, DUKE
from app.models import Project


def make_project(**overrides: object) -> Project:
    payload: dict[str, object] = {
        "id": "DUKE-DEMO-TEST",
        "utility": DUKE,
        "project_name": "DEMO test project",
        "project_type": "transmission_upgrade",
        "description": None,
        "voltage_kv": 230,
        "latitude": 28.0,
        "longitude": -82.0,
        "geometry": None,
        "start_date": "2027-01-01",
        "end_date": "2027-12-31",
        "status": "planned",
        "capital_cost": None,
        "customers_impacted": None,
        "source_name": DEMO_SOURCE_NAME,
        "source_url": DEMO_SOURCE_URL,
        "source_document": None,
        "source_page": None,
        "retrieved_date": None,
        "data_type": "demo",
    }
    payload.update(overrides)
    return Project.model_validate(payload)
