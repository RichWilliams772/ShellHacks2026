"""CSV and JSON loaders preserve nulls and require provenance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.errors import LoaderError
from app.loader import (
    EXPECTED_COLUMNS,
    PROVENANCE_COLUMNS,
    FileProjectLoader,
    projects_from_records,
)

PROVENANCE = {
    "source_name": "Example public source",
    "source_url": "https://example.invalid/source",
    "data_type": "public",
}


def test_blank_optional_numbers_stay_null(tmp_path: Path) -> None:
    path = tmp_path / "projects.csv"
    header = ",".join(EXPECTED_COLUMNS)
    row = [
        "DUKE-FILE-1",
        "Duke Energy Florida",
        "Filed project",
        "",
        "",
        "",
        "",
        "",
        "",
        "2027",
        "2028",
        "",
        "",
        "",
        "Example public source",
        "https://example.invalid/source",
        "",
        "",
        "",
        "public",
    ]
    path.write_text(header + "\n" + ",".join(row) + "\n", encoding="utf-8")
    projects = FileProjectLoader(path).load_projects()
    project = projects[0]
    assert project.voltage_kv is None
    assert project.capital_cost is None
    assert project.customers_impacted is None
    assert project.latitude is None
    assert project.description is None
    assert project.data_type == "public"
    assert project.start_date == "2027"


def test_json_list_and_missing_provenance(tmp_path: Path) -> None:
    path = tmp_path / "projects.json"
    path.write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "id": "TECO-FILE-1",
                        "utility": "Tampa Electric",
                        "project_name": "Filed project",
                        "voltage_kv": None,
                        **PROVENANCE,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    projects = FileProjectLoader(path).load_projects()
    assert projects[0].voltage_kv is None
    assert projects[0].data_type == "public"
    with pytest.raises(LoaderError):
        projects_from_records(
            [
                {
                    "id": "DUKE-FILE-2",
                    "utility": "Duke Energy Florida",
                    "project_name": "Missing provenance",
                }
            ]
        )


def test_data_type_is_required_and_pdf_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(LoaderError):
        projects_from_records(
            [
                {
                    "id": "DUKE-FILE-3",
                    "utility": "Duke Energy Florida",
                    "project_name": "No type",
                    "source_name": "Example",
                    "source_url": "https://example.invalid/source",
                }
            ]
        )
    pdf = tmp_path / "filing.pdf"
    pdf.write_text("not a project file", encoding="utf-8")
    with pytest.raises(LoaderError, match="PDF"):
        FileProjectLoader(pdf).load_projects()
    assert "data_type" in PROVENANCE_COLUMNS
