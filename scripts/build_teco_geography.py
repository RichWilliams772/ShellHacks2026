# Aaron Green
# Joins TECO projects to circuit endpoints and coordinates, then writes the final CSV.

import csv
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT / "data" / "interim" / "teco_spp_2026_projects.csv"
LOOKUP_CSV = ROOT / "data" / "interim" / "teco_circuit_lookup.csv"
COORDS_CSV = ROOT / "data" / "interim" / "teco_substation_coords.csv"
OUT_CSV = ROOT / "data" / "processed" / "teco_projects_geocoded.csv"

EARTH_RADIUS_MILES = 3958.7613

# How location_confidence is decided. Nothing else sets these values.
#
#   HIGH     the project's location is fully pinned down by public records:
#            both corridor endpoints located, or a point project whose named
#            substation is located.
#   MEDIUM   corridor project with only one of its two endpoints located.
#   LOW      only approximate geography such as a service area is known.
#   UNKNOWN  no defensible geography was found.
#
# A straight line between two located endpoints is an approximate corridor, not
# the physical route of the line.
CORRIDOR = "approximate_corridor"
POINT = "point"


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance. Deterministic; no model involved."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def clean(value):
    """Keep missing values missing instead of letting pandas NaN leak out."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def load_coords():
    frame = pd.read_csv(COORDS_CSV)
    located = {}
    for row in frame.itertuples():
        if clean(row.latitude) is None or clean(row.longitude) is None:
            continue
        located[str(row.substation_name).strip().lower()] = {
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
            "geography_source": clean(row.geography_source),
            "record_source": clean(row.record_source),
            "hifld_id": clean(row.hifld_id),
        }
    return located


def coordinate_citation(entries):
    """Name the source behind each coordinate actually used."""
    citations = []
    for entry in entries:
        for part in (entry["geography_source"], entry["record_source"]):
            if part and part not in citations:
                citations.append(part)
    return " | ".join(citations) if citations else None


def circuit_geography(project, lookup, coords):
    """Corridor geography for a circuit project, via Form 1 endpoints."""
    circuit = clean(project["circuit_id"])
    match = lookup[lookup["circuit_id"] == circuit]
    if match.empty:
        # 69 kV circuits are reported in aggregate as "Various" in Form 1, so
        # most of them have no endpoint row to join to.
        return {
            "location_method": "unknown",
            "location_confidence": "UNKNOWN",
            "unresolved_reason": "circuit_id not itemized in FERC Form 1 schedules",
        }

    row = match.iloc[0]
    from_name, to_name = clean(row["from_substation"]), clean(row["to_substation"])
    from_entry = coords.get(str(from_name).strip().lower()) if from_name else None
    to_entry = coords.get(str(to_name).strip().lower()) if to_name else None

    geography = {
        "from_substation": from_name,
        "to_substation": to_name,
        "line_length_miles": clean(row["line_length_miles"]),
        # Guards against anyone reading the summed conductor length as the
        # distance between the two endpoints. They are not the same number.
        "line_length_basis": (
            "sum of all FERC Form 1 segment lengths reported for this circuit; "
            "not a point-to-point distance"
        ) if clean(row["line_length_miles"]) is not None else None,
        "form1_schedule": clean(row["form1_schedule"]),
        "circuit_endpoint_source": clean(row["source"]),
    }

    if from_entry and to_entry:
        geography.update({
            "from_lat": from_entry["latitude"], "from_lon": from_entry["longitude"],
            "to_lat": to_entry["latitude"], "to_lon": to_entry["longitude"],
            "mid_lat": (from_entry["latitude"] + to_entry["latitude"]) / 2,
            "mid_lon": (from_entry["longitude"] + to_entry["longitude"]) / 2,
            "endpoint_distance_miles": round(haversine_miles(
                from_entry["latitude"], from_entry["longitude"],
                to_entry["latitude"], to_entry["longitude"]), 4),
            "geometry_type": CORRIDOR,
            "location_method": "exact_substation_endpoints",
            "location_confidence": "HIGH",
            "geography_source": coordinate_citation([from_entry, to_entry]),
        })
        return geography

    single = from_entry or to_entry
    if single:
        missing = to_name if from_entry else from_name
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
            "geography_source": coordinate_citation([single]),
            "unresolved_reason": f"no coordinates found for endpoint {missing!r}",
        })
        return geography

    geography.update({
        "location_method": "unknown",
        "location_confidence": "UNKNOWN",
        "unresolved_reason": "no coordinates found for either named endpoint",
    })
    return geography


def substation_geography(project, coords):
    """Point geography for a substation project. The SPP states 'Project = Substation'."""
    name = clean(project["substation_name"])
    entry = coords.get(str(name).strip().lower()) if name else None
    if not entry:
        return {
            "from_substation": name,
            "location_method": "unknown",
            "location_confidence": "UNKNOWN",
            "unresolved_reason": f"no coordinates found for substation {name!r}",
        }
    return {
        "from_substation": name,
        "from_lat": entry["latitude"],
        "from_lon": entry["longitude"],
        "mid_lat": entry["latitude"],
        "mid_lon": entry["longitude"],
        "geometry_type": POINT,
        "location_method": "single_substation",
        "location_confidence": "HIGH",
        "geography_source": coordinate_citation([entry]),
    }


FIELDS = [
    "project_id", "utility", "project_name", "circuit_id", "project_type",
    "voltage_kv", "voltage_label", "pole_count", "project_start",
    "construction_start", "project_end", "date_precision", "project_cost",
    "from_substation", "to_substation", "from_lat", "from_lon", "to_lat",
    "to_lon", "mid_lat", "mid_lon", "line_length_miles",
    "line_length_basis", "endpoint_distance_miles", "geometry_type",
    "location_method",
    "location_confidence", "unresolved_reason", "project_source",
    "circuit_endpoint_source", "form1_schedule", "geography_source", "data_type",
]


def main():
    projects = pd.read_csv(PROJECTS_CSV, dtype={"circuit_id": "string"})
    lookup = pd.read_csv(LOOKUP_CSV, dtype={"circuit_id": "string"})
    coords = load_coords()

    rows = []
    for project in projects.to_dict("records"):
        if project["project_type"] == "substation_hardening":
            geography = substation_geography(project, coords)
        else:
            geography = circuit_geography(project, lookup, coords)

        row = {field: None for field in FIELDS}
        row.update({key: clean(value) for key, value in project.items()
                    if key in FIELDS})
        row.update({key: value for key, value in geography.items()
                    if key in FIELDS})
        row["data_type"] = "public"
        rows.append(row)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    counts = {}
    for row in rows:
        counts[row["location_confidence"]] = counts.get(row["location_confidence"], 0) + 1

    print(f"wrote {len(rows)} projects to {OUT_CSV.relative_to(ROOT)}")
    for level in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
        if level in counts:
            print(f"  {level:<8} {counts[level]}")
    unresolved = [r["circuit_id"] or r["project_id"] for r in rows
                  if r["location_confidence"] == "UNKNOWN"]
    if unresolved:
        print("  unresolved: " + ", ".join(str(u) for u in unresolved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
