"""Load Aaron's processed Duke and TECO CSVs into the API project model.

Column names in the files stay different from the API. This adapter maps them.
It does not score pairs, fill blanks with zero, or invent a TECO source URL.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from app.errors import LoaderError
from app.models import Project
from app.provenance import SOURCE_URL_MISSING_NOTE

DUKE_FILENAME = "duke_projects_normalized.csv"
TECO_FILENAME = "teco_projects_geocoded.csv"
_MISSING_TEXT = {"", "nan", "none", "null", "<na>", "nat"}


def processed_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "processed"


def processed_files_available() -> bool:
    directory = processed_directory()
    return (directory / DUKE_FILENAME).is_file() and (directory / TECO_FILENAME).is_file()


class ProcessedProjectLoader:
    """Read the two processed project files and return API projects."""

    def __init__(
        self,
        duke_path: str | Path | None = None,
        teco_path: str | Path | None = None,
    ) -> None:
        directory = processed_directory()
        self.duke_path = Path(duke_path) if duke_path else directory / DUKE_FILENAME
        self.teco_path = Path(teco_path) if teco_path else directory / TECO_FILENAME

    def load_projects(self) -> list[Project]:
        duke_rows, duke_columns = _read_csv(self.duke_path)
        teco_rows, teco_columns = _read_csv(self.teco_path)
        projects = [
            _map_row(row, duke_columns, index, self.duke_path.name)
            for index, row in enumerate(duke_rows, start=1)
        ]
        projects.extend(
            _map_row(row, teco_columns, index, self.teco_path.name)
            for index, row in enumerate(teco_rows, start=1)
        )
        seen: set[str] = set()
        for project in projects:
            if project.id in seen:
                raise LoaderError(f"Duplicate project id {project.id}")
            seen.add(project.id)
        return projects


def _read_csv(path: Path) -> tuple[list[dict[str, str]], set[str]]:
    if not path.is_file():
        raise LoaderError(f"Processed project file not found: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    columns = [str(column).strip() for column in frame.columns]
    frame.columns = columns
    raw_rows = frame.to_dict(orient="records")
    records = [{str(key): value for key, value in row.items()} for row in raw_rows]
    return records, set(columns)


def _map_row(
    row: dict[str, str],
    columns: set[str],
    row_number: int,
    filename: str,
) -> Project:
    project_id = _text(row.get("project_id"))
    utility = _text(row.get("utility"))
    project_name = _text(row.get("project_name"))
    project_source = _text(row.get("project_source"))
    data_type = _text(row.get("data_type"))
    if not project_id or not utility or not project_name or not project_source or not data_type:
        raise LoaderError(
            f"{filename} row {row_number}: project_id, utility, project_name, "
            "project_source, and data_type are required"
        )
    if data_type not in {"demo", "public"}:
        raise LoaderError(f"{filename} row {row_number}: data_type must be demo or public")
    source_url, gaps = _source_url(row, columns)
    from_lat = _number(row.get("from_lat"), filename, row_number, "from_lat")
    from_lon = _number(row.get("from_lon"), filename, row_number, "from_lon")
    to_lat = _number(row.get("to_lat"), filename, row_number, "to_lat")
    to_lon = _number(row.get("to_lon"), filename, row_number, "to_lon")
    mid_lat = _number(row.get("mid_lat"), filename, row_number, "mid_lat")
    mid_lon = _number(row.get("mid_lon"), filename, row_number, "mid_lon")
    geometry_type = _text(row.get("geometry_type"))
    try:
        return Project.model_validate(
            {
                "id": project_id,
                "utility": utility,
                "project_name": project_name,
                "project_type": _text(row.get("project_type")),
                "description": None,
                "voltage_kv": _voltage_kv(row, filename, row_number),
                "voltage_min_kv": _number(
                    row.get("voltage_min_kv"), filename, row_number, "voltage_min_kv"
                ),
                "voltage_label": _text(row.get("voltage_label")),
                "latitude": mid_lat,
                "longitude": mid_lon,
                "geometry": _geometry(
                    geometry_type, from_lat, from_lon, to_lat, to_lon, mid_lat, mid_lon
                ),
                "start_date": _text(row.get("project_start")),
                "end_date": _text(row.get("project_end")),
                "construction_start": _text(row.get("construction_start")),
                "status": _text(row.get("status")),
                "capital_cost": _number(
                    row.get("project_cost"), filename, row_number, "project_cost"
                ),
                "customers_impacted": None,
                "source_name": project_source,
                "source_url": source_url,
                "source_url_note": SOURCE_URL_MISSING_NOTE if "source_url" in gaps else None,
                "source_document": None,
                "source_page": None,
                "retrieved_date": None,
                "data_type": data_type,
                "provenance_gaps": gaps,
                "geography_source": _text(row.get("geography_source")),
                "circuit_endpoint_source": _text(row.get("circuit_endpoint_source")),
                "form1_schedule": _text(row.get("form1_schedule")),
                "date_precision": _text(row.get("date_precision")),
                "estimated_in_service_year": _year(
                    row.get("estimated_in_service_year"), filename, row_number
                ),
                "location_confidence": _text(row.get("location_confidence")),
                "location_method": _text(row.get("location_method")),
                "geometry_type": geometry_type,
                "unresolved_reason": _text(row.get("unresolved_reason")),
                "from_substation": _text(row.get("from_substation")),
                "to_substation": _text(row.get("to_substation")),
                "from_latitude": from_lat,
                "from_longitude": from_lon,
                "to_latitude": to_lat,
                "to_longitude": to_lon,
                "ownership_confidence": _text(row.get("ownership_confidence")),
                "ownership_note": _text(row.get("ownership_note")),
            }
        )
    except Exception as exc:
        raise LoaderError(f"{filename} row {row_number}: {exc}") from exc


def _source_url(row: dict[str, str], columns: set[str]) -> tuple[str | None, list[str]]:
    if "source_url" not in columns:
        return None, ["source_url"]
    url = _text(row.get("source_url"))
    if url is None:
        return None, ["source_url"]
    return url, []


def _voltage_kv(row: dict[str, str], filename: str, row_number: int) -> float | None:
    if _text(row.get("voltage_max_kv")) is not None:
        return _number(row.get("voltage_max_kv"), filename, row_number, "voltage_max_kv")
    return _number(row.get("voltage_kv"), filename, row_number, "voltage_kv")


def _geometry(
    geometry_type: str | None,
    from_lat: float | None,
    from_lon: float | None,
    to_lat: float | None,
    to_lon: float | None,
    mid_lat: float | None,
    mid_lon: float | None,
) -> dict[str, object] | None:
    if (
        geometry_type == "approximate_corridor"
        and None not in (from_lat, from_lon, to_lat, to_lon)
    ):
        return {
            "type": "LineString",
            "coordinates": [[from_lon, from_lat], [to_lon, to_lat]],
        }
    if geometry_type == "point":
        latitude = from_lat if from_lat is not None else mid_lat
        longitude = from_lon if from_lon is not None else mid_lon
        if latitude is not None and longitude is not None:
            return {"type": "Point", "coordinates": [longitude, latitude]}
    return None


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.casefold() in _MISSING_TEXT:
        return None
    return text


def _number(value: object, filename: str, row_number: int, field: str) -> float | None:
    text = _text(value)
    if text is None:
        return None
    try:
        number = float(text)
    except ValueError as exc:
        raise LoaderError(
            f"{filename} row {row_number}: {field} must be a number or blank"
        ) from exc
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _year(value: object, filename: str, row_number: int) -> int | None:
    number = _number(value, filename, row_number, "estimated_in_service_year")
    if number is None:
        return None
    if not number.is_integer():
        raise LoaderError(
            f"{filename} row {row_number}: estimated_in_service_year must be a whole year or blank"
        )
    return int(number)
