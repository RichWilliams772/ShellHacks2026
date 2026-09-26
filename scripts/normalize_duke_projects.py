# Aaron Green
# Turns Duke Energy Florida projects from Our Grid Future into a clean CSV with coordinates.

import csv
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "OurGridFuture_PlannedTransmissionProjects_Jun2026.xlsx"
OUT_CSV = ROOT / "data" / "processed" / "duke_projects_normalized.csv"
EXCLUSIONS_CSV = ROOT / "data" / "interim" / "duke_project_exclusions.csv"

PROJECTS_SHEET = "Planned Transmission Projects"
SUBSTATIONS_SHEET = "Substations in Planned Projects"

PROJECT_SOURCE = (
    "Our Grid Future Planned Transmission Projects National Database, June 2026, "
    "'Planned Transmission Projects' sheet"
)
GEOGRAPHY_SOURCE = (
    "Our Grid Future Planned Transmission Projects National Database, June 2026, "
    "'Substations in Planned Projects' sheet"
)

UTILITY = "Duke Energy Florida"

# Owner text that identifies a Duke record, and the domain that overrides a
# disagreeing Owner value. See the Archer note in classify() below.
DUKE_OWNER = "duke energy"
DUKE_DOMAIN = "duke-energy.com"

# Only completed work is filtered out. In-service year is left alone on purpose:
# a past year sitting next to a "Construction" status is ambiguous, and judging
# schedule relevance belongs to the temporal analysis, not to this script.
COMPLETED_STATUS = "complete"

# Our Grid Future's "Change type" mapped to the project vocabulary shared with
# the TECO dataset. Anything unlisted becomes "unknown" rather than a guess.
PROJECT_TYPES = {
    "upgrade": "transmission_upgrade",
    "rebuild": "transmission_upgrade",
    "rebuild; upgrade": "transmission_upgrade",
    "new circuit, greenfield": "transmission_line",
    "new circuit, existing row": "transmission_line",
}

# Substation placeholders that name no real substation.
NOT_A_SUBSTATION = re.compile(r"^na\b", re.IGNORECASE)

# How location_confidence is decided, matching the rule used for TECO:
#   HIGH     both endpoints matched to substations with coordinates
#   MEDIUM   one endpoint matched
#   UNKNOWN  neither endpoint matched
# A straight line between two endpoints is an approximate corridor, never the
# physical route of the line.
CORRIDOR = "approximate_corridor"
POINT = "point"


def clean(value):
    """Blank, 'Unknown' and NaN all mean missing. Zero is never a substitute."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() == "unknown":
            return None
        return text
    return value


def as_number(value):
    value = clean(value)
    if value is None:
        return None
    try:
        number = float(str(value).replace(",", ""))
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def normalize_name(name):
    name = clean(name)
    return re.sub(r"\s+", " ", str(name)).strip().lower() if name else None


def load_sheet(sheet_name):
    frame = pd.read_excel(WORKBOOK, sheet_name=sheet_name, dtype=object)
    return frame.to_dict("records")


def florida_records(records):
    return [r for r in records
            if "FL" in str(r.get("States intersected (abbreviated)") or "")]


def source_links(record):
    return " ".join(str(record.get(key) or "") for key in ("Link 1", "Link 2")).lower()


def classify(record):
    """Decide whether a record is a Duke project, and how sure we are."""
    owner = clean(record.get("Owner"))
    owner_text = (owner or "").lower()

    if DUKE_OWNER in owner_text:
        return True, "HIGH", None

    # The Owner column is not always right. Record P-0017 "Archer Reliability
    # Upgrade Projects" is filed as Dominion Energy, but its only source link is
    # a duke-energy.com project map and its Archer substation is also an
    # endpoint of Duke project P-0246. The original owner is kept as filed and
    # the disagreement is flagged rather than quietly corrected.
    if DUKE_DOMAIN in source_links(record):
        note = (f"Owner column reads {owner!r} but the source link is hosted on "
                f"{DUKE_DOMAIN}; treated as Duke on that evidence, original "
                f"owner preserved. Needs manual review.")
        return True, "MEDIUM", note

    return False, None, None


def substation_index(records):
    """Normalized substation name -> coordinates, Florida rows only."""
    index = {}
    for record in florida_records_by_state(records):
        name = normalize_name(record.get("Substation name"))
        latitude, longitude = as_number(record.get("Latitude")), as_number(record.get("Longitude"))
        if not name or latitude is None or longitude is None:
            continue
        index.setdefault(name, {
            "substation_id": clean(record.get("Substation ID")),
            "name": clean(record.get("Substation name")),
            "latitude": float(latitude),
            "longitude": float(longitude),
        })
    return index


def florida_records_by_state(records):
    return [r for r in records if str(r.get("State (abbrv.)") or "").strip() == "FL"]


def attach_geography(record, substations):
    """Endpoint coordinates from the substation sheet. No coordinate is invented."""
    origin_raw = clean(record.get("Origin substation"))
    destination_raw = clean(record.get("Destination substation"))

    # "NA - none listed" and "NA - Interconnects line" are placeholders.
    origin = None if origin_raw and NOT_A_SUBSTATION.match(origin_raw) else origin_raw
    destination = (None if destination_raw and NOT_A_SUBSTATION.match(destination_raw)
                   else destination_raw)

    from_entry = substations.get(normalize_name(origin)) if origin else None
    to_entry = substations.get(normalize_name(destination)) if destination else None

    geography = {
        "from_substation": origin,
        "to_substation": destination,
        "origin_substation_raw": origin_raw,
        "destination_substation_raw": destination_raw,
    }

    def cite(entries):
        ids = ", ".join(e["substation_id"] for e in entries if e["substation_id"])
        return f"{GEOGRAPHY_SOURCE} ({ids})" if ids else GEOGRAPHY_SOURCE

    if from_entry and to_entry:
        geography.update({
            "from_lat": from_entry["latitude"], "from_lon": from_entry["longitude"],
            "to_lat": to_entry["latitude"], "to_lon": to_entry["longitude"],
            "mid_lat": (from_entry["latitude"] + to_entry["latitude"]) / 2,
            "mid_lon": (from_entry["longitude"] + to_entry["longitude"]) / 2,
            "geometry_type": CORRIDOR,
            "location_method": "exact_substation_endpoints",
            "location_confidence": "HIGH",
            "geography_source": cite([from_entry, to_entry]),
        })
        return geography

    single = from_entry or to_entry
    if single:
        missing = destination if from_entry else origin
        geography.update({
            "from_lat": from_entry["latitude"] if from_entry else None,
            "from_lon": from_entry["longitude"] if from_entry else None,
            "to_lat": to_entry["latitude"] if to_entry else None,
            "to_lon": to_entry["longitude"] if to_entry else None,
            "mid_lat": single["latitude"],
            "mid_lon": single["longitude"],
            "geometry_type": POINT,
            "location_method": "single_substation",
            "location_confidence": "MEDIUM",
            "geography_source": cite([single]),
            "unresolved_reason": (f"no substation coordinates for {missing!r}"
                                  if missing else "only one endpoint is named"),
        })
        return geography

    geography.update({
        "location_method": "unknown",
        "location_confidence": "UNKNOWN",
        "unresolved_reason": "neither endpoint matched a substation with coordinates",
    })
    return geography


def project_id(record):
    source_id = clean(record.get("Project ID")) or clean(record.get("Record ID"))
    return "DUKE-" + str(source_id).replace("-", "")


def project_type_of(change_type):
    """Map Our Grid Future's change type into the shared project vocabulary."""
    if not change_type:
        return "unknown"
    return PROJECT_TYPES.get(str(change_type).strip().lower(), "unknown")


def normalize(record, substations):
    change_type = clean(record.get("Change type"))
    status = clean(record.get("Status"))
    is_duke, ownership_confidence, ownership_note = classify(record)

    row = {
        "project_id": project_id(record),
        "utility": UTILITY,
        "owner_original": clean(record.get("Owner")),
        "ownership_confidence": ownership_confidence,
        "ownership_note": ownership_note,
        "project_name": clean(record.get("Project name")),
        "project_type": project_type_of(change_type),
        "change_type": change_type,
        "status": status,
        "status_last_updated": None,
        "voltage_min_kv": as_number(record.get("Minimum voltage (kV)")),
        "voltage_max_kv": as_number(record.get("Maximum voltage (kV)")),
        "estimated_in_service_year": as_number(record.get("Estimated in service year")),
        # Our Grid Future gives a year and nothing finer, so start and end dates
        # stay empty rather than becoming an invented Jan 1 / Dec 31.
        "project_start": None,
        "construction_start": None,
        "project_end": None,
        "date_precision": "year" if clean(record.get("Estimated in service year")) else None,
        "related_substations": clean(record.get("Related substations")),
        "length_miles": as_number(record.get("Length (mi)")),
        "length_source": clean(record.get("Length source")),
        "state": clean(record.get("States intersected (abbreviated)")),
        "source_project_id": clean(record.get("Project ID")),
        "source_record_id": clean(record.get("Record ID")),
        "project_source": PROJECT_SOURCE,
        "source_url": clean(record.get("Link 1")),
        "data_type": "public",
    }

    updated = clean(record.get("Status last updated date"))
    if updated is not None:
        row["status_last_updated"] = str(pd.to_datetime(updated).date())

    row.update(attach_geography(record, substations))
    return row


FIELDS = [
    "project_id", "utility", "owner_original", "ownership_confidence",
    "ownership_note", "project_name", "project_type", "change_type", "status",
    "status_last_updated", "voltage_min_kv", "voltage_max_kv",
    "estimated_in_service_year", "project_start", "construction_start",
    "project_end", "date_precision", "from_substation", "to_substation",
    "from_lat", "from_lon", "to_lat", "to_lon", "mid_lat", "mid_lon",
    "geometry_type", "location_method", "location_confidence",
    "unresolved_reason", "related_substations", "length_miles", "length_source",
    "state", "origin_substation_raw", "destination_substation_raw",
    "source_project_id", "source_record_id", "project_source", "source_url",
    "geography_source", "data_type",
]

EXCLUSION_FIELDS = [
    "project_id", "project_name", "owner_original", "status",
    "estimated_in_service_year", "exclusion_reason",
]


def main():
    projects = load_sheet(PROJECTS_SHEET)
    substations = substation_index(load_sheet(SUBSTATIONS_SHEET))
    florida = florida_records(projects)

    included, excluded = [], []
    for record in florida:
        is_duke, _, _ = classify(record)
        row = normalize(record, substations)
        # The exclusion log uses the workbook's own Project ID, so a record that
        # is not Duke's is never labelled with a DUKE- prefix.
        exclusion = {
            "project_id": row["source_project_id"] or row["source_record_id"],
            "project_name": row["project_name"],
            "owner_original": row["owner_original"],
            "status": row["status"],
            "estimated_in_service_year": row["estimated_in_service_year"],
        }

        if not is_duke:
            excluded.append({**exclusion, "exclusion_reason": "not_duke_energy_florida"})
            continue
        if (row["status"] or "").strip().lower() == COMPLETED_STATUS:
            excluded.append({**exclusion, "exclusion_reason": "completed_historical_project"})
            continue
        included.append(row)

    included.sort(key=lambda r: r["project_id"])

    for path, fields, rows in ((OUT_CSV, FIELDS, included),
                               (EXCLUSIONS_CSV, EXCLUSION_FIELDS, excluded)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    counts = {}
    for row in included:
        counts[row["location_confidence"]] = counts.get(row["location_confidence"], 0) + 1

    print(f"Florida records inspected: {len(florida)}")
    print(f"Duke candidates: {len(included) + sum(1 for e in excluded if e['exclusion_reason'] == 'completed_historical_project')}")
    print(f"included: {len(included)} -> {OUT_CSV.relative_to(ROOT)}")
    for level in ("HIGH", "MEDIUM", "UNKNOWN"):
        if level in counts:
            print(f"  geography {level:<8} {counts[level]}")
    print(f"excluded: {len(excluded)} -> {EXCLUSIONS_CSV.relative_to(ROOT)}")
    for reason in sorted({e["exclusion_reason"] for e in excluded}):
        ids = [e["project_id"] for e in excluded if e["exclusion_reason"] == reason]
        print(f"  {reason}: {', '.join(ids)}")
    flagged = [r["project_id"] for r in included if r["ownership_confidence"] != "HIGH"]
    if flagged:
        print(f"needs manual review (ownership): {', '.join(flagged)}")
    return 0 if included else 1


if __name__ == "__main__":
    sys.exit(main())
