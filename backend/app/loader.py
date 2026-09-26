"""Project loaders.

The default source is the labeled demo fixture set. A future verified file can
replace it through FileProjectLoader or GRIDSYNC_DATA_FILE. This module does
not scrape PDFs and does not mark rows public on its own.

Expected CSV or JSON columns, in order:

Required:
- id
- utility
- project_name
- source_name
- source_url
- data_type          demo or public. Required on every row. Never defaulted.

Project attributes. Leave blank or JSON null when unknown. Do not write 0 for
an unknown voltage, cost, customer count, or coordinate.
- project_type
- description
- voltage_kv
- latitude
- longitude
- geometry           GeoJSON object, or a JSON string in CSV
- start_date         YYYY-MM-DD, or YYYY when only a year is known
- end_date           YYYY-MM-DD, or YYYY when only a year is known
- status
- capital_cost
- customers_impacted

Provenance:
- source_name        required
- source_url         required
- source_document    optional document title
- source_page        optional page or section
- retrieved_date     optional YYYY-MM-DD
- data_type          required, demo or public

JSON may be a list of objects or an object with a "projects" list.
Unknown columns are ignored. Duplicate ids are rejected.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

import pandas as pd

from app.errors import LoaderError
from app.fixtures import demo_projects
from app.models import Project

EXPECTED_COLUMNS: tuple[str, ...] = (
    "id",
    "utility",
    "project_name",
    "project_type",
    "description",
    "voltage_kv",
    "latitude",
    "longitude",
    "geometry",
    "start_date",
    "end_date",
    "status",
    "capital_cost",
    "customers_impacted",
    "source_name",
    "source_url",
    "source_document",
    "source_page",
    "retrieved_date",
    "data_type",
)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "id",
    "utility",
    "project_name",
    "source_name",
    "source_url",
    "data_type",
)

PROVENANCE_COLUMNS: tuple[str, ...] = (
    "source_name",
    "source_url",
    "source_document",
    "source_page",
    "retrieved_date",
    "data_type",
)

_FLOAT_FIELDS = ("voltage_kv", "latitude", "longitude", "capital_cost")
_INT_FIELDS = ("customers_impacted",)
_TEXT_FIELDS = (
    "id",
    "utility",
    "project_name",
    "project_type",
    "description",
    "start_date",
    "end_date",
    "status",
    "source_name",
    "source_url",
    "source_document",
    "source_page",
    "retrieved_date",
    "data_type",
)


class ProjectSource(Protocol):
    def load_projects(self) -> list[Project]:
        """Return normalized projects."""


class FixtureProjectLoader:
    """Load the in-repo demo fixtures."""

    def load_projects(self) -> list[Project]:
        return demo_projects()


class FileProjectLoader:
    """Load a canonical CSV or JSON file of already normalized projects."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load_projects(self) -> list[Project]:
        if not self.path.is_file():
            raise LoaderError(f"Project file not found: {self.path}")
        suffix = self.path.suffix.casefold()
        if suffix == ".csv":
            records = _read_csv(self.path)
        elif suffix == ".json":
            records = _read_json(self.path)
        else:
            raise LoaderError(
                "Project file must be .csv or .json. PDF ingestion is not implemented."
            )
        return projects_from_records(records)


def projects_from_records(records: Sequence[Mapping[str, object]]) -> list[Project]:
    """Normalize mapping rows into projects. Blank optional fields become null."""
    projects: list[Project] = []
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, Mapping):
            raise LoaderError(f"Row {index}: expected an object")
        missing = [column for column in REQUIRED_COLUMNS if column not in record]
        if missing:
            raise LoaderError(f"Row {index}: missing required columns {', '.join(missing)}")
        payload = _payload_from_record(record, index)
        try:
            project = Project.model_validate(payload)
        except Exception as exc:
            raise LoaderError(f"Row {index}: {exc}") from exc
        if project.id in seen:
            raise LoaderError(f"Row {index}: duplicate project id {project.id}")
        seen.add(project.id)
        projects.append(project)
    return projects


def default_source(data_file: str | None) -> ProjectSource:
    if data_file:
        return FileProjectLoader(data_file)
    return FixtureProjectLoader()


def _read_csv(path: Path) -> list[dict[str, object]]:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.columns = [str(column).strip() for column in frame.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise LoaderError(f"CSV is missing required columns: {', '.join(missing)}")
    records: list[dict[str, object]] = []
    for raw in frame.to_dict(orient="records"):
        records.append({str(key): value for key, value in raw.items()})
    return records


def _read_json(path: Path) -> list[dict[str, object]]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoaderError(f"JSON file could not be parsed: {exc}") from exc
    if isinstance(loaded, dict) and isinstance(loaded.get("projects"), list):
        rows = loaded["projects"]
    elif isinstance(loaded, list):
        rows = loaded
    else:
        raise LoaderError("JSON must be a list of projects or an object with a projects list")
    records: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise LoaderError(f"Row {index}: expected an object")
        records.append(row)
    return records


def _payload_from_record(record: Mapping[str, object], row_number: int) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field in _TEXT_FIELDS:
        if field not in record:
            continue
        payload[field] = _optional_text(record.get(field))
    for field in _FLOAT_FIELDS:
        if field not in record:
            continue
        payload[field] = _optional_float(record.get(field), field, row_number)
    for field in _INT_FIELDS:
        if field not in record:
            continue
        payload[field] = _optional_int(record.get(field), field, row_number)
    if "geometry" in record:
        payload["geometry"] = _optional_geometry(record.get("geometry"), row_number)
    return payload


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object, field: str, row_number: int) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise LoaderError(f"Row {row_number}: {field} must be a number or blank") from exc


def _optional_int(value: object, field: str, row_number: int) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError as exc:
        raise LoaderError(f"Row {row_number}: {field} must be an integer or blank") from exc
    if not number.is_integer():
        raise LoaderError(f"Row {row_number}: {field} must be an integer or blank")
    return int(number)


def _optional_geometry(value: object, row_number: int) -> object:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LoaderError(f"Row {row_number}: geometry must be JSON or blank") from exc
    return parsed
