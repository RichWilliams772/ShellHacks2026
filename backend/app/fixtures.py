"""Explicitly labeled demo projects.

These records are not Duke Energy Florida or Tampa Electric public filings.
Each one uses data_type='demo' and a demo source label. Do not change those
fields to public when real filings are still unavailable.
"""

from __future__ import annotations

from app.models import Project

DEMO_SOURCE_NAME = "GridSync demo fixture (not a public utility record)"
DEMO_SOURCE_URL = "https://example.invalid/gridsync/demo-fixtures"

DUKE = "Duke Energy Florida"
TECO = "Tampa Electric"

DUKE_CLOSE_ID = "DUKE-DEMO-001"
TECO_CLOSE_ID = "TECO-DEMO-001"
DUKE_FAR_ID = "DUKE-DEMO-004"


def _demo_project(**overrides: object) -> Project:
    payload: dict[str, object] = {
        "description": None,
        "voltage_kv": None,
        "latitude": None,
        "longitude": None,
        "geometry": None,
        "start_date": None,
        "end_date": None,
        "status": None,
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


def demo_projects() -> list[Project]:
    """Return fresh copies so callers cannot mutate the catalog."""
    projects = [
        _demo_project(
            id=DUKE_CLOSE_ID,
            utility=DUKE,
            project_name="DEMO North Corridor Reconductor",
            project_type="transmission_upgrade",
            description="Reconductor existing 230 kV transmission corridor.",
            voltage_kv=230,
            latitude=28.05,
            longitude=-82.45,
            start_date="2027-03-01",
            end_date="2028-10-31",
            status="planned",
        ),
        _demo_project(
            id="DUKE-DEMO-002",
            utility=DUKE,
            project_name="DEMO East Substation Upgrade",
            project_type="substation_upgrade",
            voltage_kv=115,
            latitude=28.50,
            longitude=-82.10,
            start_date="2028-01-01",
            end_date="2029-06-01",
            status="planned",
        ),
        _demo_project(
            id="DUKE-DEMO-003",
            utility=DUKE,
            project_name="DEMO Inland Transmission Year Window",
            project_type="transmission_upgrade",
            start_date="2027",
            end_date="2028",
            status="planned",
        ),
        _demo_project(
            id=DUKE_FAR_ID,
            utility=DUKE,
            project_name="DEMO Far South Undergrounding",
            project_type="undergrounding",
            description="Open-cut underground cable installation along an urban arterial.",
            voltage_kv=138,
            latitude=25.7617,
            longitude=-80.1918,
            start_date="2031-01-01",
            end_date="2032-06-01",
            status="planned",
        ),
        _demo_project(
            id=TECO_CLOSE_ID,
            utility=TECO,
            project_name="DEMO South Corridor Conductor Replacement",
            project_type="transmission_upgrade",
            description="Replace conductors along existing 230 kV transmission line.",
            voltage_kv=230,
            latitude=28.02,
            longitude=-82.47,
            start_date="2027-06-01",
            end_date="2028-12-31",
            status="planned",
        ),
        _demo_project(
            id="TECO-DEMO-002",
            utility=TECO,
            project_name="DEMO East Substation Expansion",
            project_type="substation_upgrade",
            voltage_kv=230,
            latitude=28.35,
            longitude=-82.00,
            start_date="2029",
            end_date="2030",
            status="planned",
        ),
        _demo_project(
            id="TECO-DEMO-003",
            utility=TECO,
            project_name="DEMO Coastal Hardening",
            project_type="hardening",
            latitude=28.03,
            longitude=-82.44,
            status="planned",
        ),
        _demo_project(
            id="TECO-DEMO-004",
            utility=TECO,
            project_name="DEMO Billing Portal Migration",
            project_type="distribution_upgrade",
            description="Migrate the customer billing portal and account software.",
            status="proposed",
        ),
    ]
    for project in projects:
        if project.data_type != "demo":
            raise RuntimeError("Demo fixtures must keep data_type='demo'")
        if project.source_url != DEMO_SOURCE_URL:
            raise RuntimeError("Demo fixtures must not use a utility filing URL")
    return projects
