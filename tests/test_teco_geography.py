# Aaron Green
# Checks the TECO geography dataset for the mistakes that would break the demo.

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_teco_geography import haversine_miles  # noqa: E402

PROCESSED = ROOT / "data" / "processed" / "teco_projects_geocoded.csv"
LOOKUP = ROOT / "data" / "interim" / "teco_circuit_lookup.csv"

# The 2026 Transmission Asset Upgrade circuits from SPP Appendix D page 2 of 2.
SPP_2026_CIRCUITS = [
    "66833", "230037", "66653", "66004", "66655", "66831",
    "66651", "66058", "66012", "138005", "66835",
]
VALID_CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
VALID_METHOD = {"exact_substation_endpoints", "single_substation",
                "approximate_service_area", "unknown"}

COORD_COLUMNS = ["from_lat", "from_lon", "to_lat", "to_lon", "mid_lat", "mid_lon"]
NUMERIC_COLUMNS = COORD_COLUMNS + [
    "voltage_kv", "pole_count", "project_cost", "line_length_miles",
    "endpoint_distance_miles",
]

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def load():
    return (
        pd.read_csv(PROCESSED, dtype={"circuit_id": "string"}),
        pd.read_csv(LOOKUP, dtype={"circuit_id": "string"}),
    )


def test_circuit_join_is_exact(projects, lookup):
    """Circuit 66833 must not pick up another circuit's endpoints."""
    # 66833 is not itemized in Form 1, so a fuzzy join is the only way it could
    # ever gain endpoints. Neighbouring ids like 66831/66835 must not leak in.
    row = projects[projects["circuit_id"] == "66833"].iloc[0]
    check("66833 has no invented endpoints",
          pd.isna(row["from_substation"]) and pd.isna(row["to_substation"]),
          f"got {row['from_substation']} / {row['to_substation']}")

    for circuit in SPP_2026_CIRCUITS:
        matches = lookup[lookup["circuit_id"] == circuit]
        check(f"{circuit} matches at most one lookup row", len(matches) <= 1,
              f"matched {len(matches)} rows")

    joined = projects[projects["from_substation"].notna()
                      & projects["circuit_id"].notna()]
    for row in joined.itertuples():
        expected = lookup[lookup["circuit_id"] == row.circuit_id]
        check(f"{row.circuit_id} endpoints came from its own lookup row",
              not expected.empty
              and expected.iloc[0]["from_substation"] == row.from_substation,
              "endpoints do not match the lookup")


def test_coordinates_are_valid(projects):
    bad = []
    for row in projects.itertuples():
        for column in COORD_COLUMNS:
            value = getattr(row, column)
            if pd.isna(value):
                continue
            limit = 90 if column.endswith("lat") else 180
            if not -limit <= value <= limit:
                bad.append((row.project_id, column, value))
    check("all present coordinates are in range", not bad, str(bad))

    # Everything located should land in west central Florida. A sign flip or a
    # bad name match would show up here immediately.
    located = projects[projects["mid_lat"].notna()]
    outside = located[~(located["mid_lat"].between(26.5, 29.5)
                        & located["mid_lon"].between(-83.5, -81.0))]
    check("located projects sit inside west central Florida", outside.empty,
          str(list(outside["project_id"])))


def test_missing_stays_missing(projects):
    """Unknown values must be blank, never zero."""
    unknown = projects[projects["location_confidence"] == "UNKNOWN"]
    check("UNKNOWN rows carry no coordinates",
          unknown[COORD_COLUMNS].isna().all().all(),
          "some UNKNOWN row has coordinates")

    zeros = []
    for column in NUMERIC_COLUMNS:
        if (projects[column] == 0).any():
            zeros.append(column)
    check("no numeric column was filled in with 0", not zeros, str(zeros))

    single = projects[projects["location_method"] == "single_substation"]
    corridor_only = single[single["to_lat"].notna() & single["from_lat"].notna()]
    check("single_substation rows do not claim two endpoints",
          corridor_only.empty, str(list(corridor_only["project_id"])))


def test_provenance(projects):
    located = projects[projects["location_confidence"].isin(["HIGH", "MEDIUM"])]
    missing_geography = located[located["geography_source"].isna()
                                | (located["geography_source"].astype(str).str.strip() == "")]
    check("every located project cites a geography_source",
          missing_geography.empty, str(list(missing_geography["project_id"])))

    missing_project = projects[projects["project_source"].isna()]
    check("every project cites a project_source", missing_project.empty,
          str(list(missing_project["project_id"])))

    check("confidence values are from the allowed set",
          set(projects["location_confidence"]) <= VALID_CONFIDENCE,
          str(set(projects["location_confidence"]) - VALID_CONFIDENCE))
    check("location_method values are from the allowed set",
          set(projects["location_method"]) <= VALID_METHOD,
          str(set(projects["location_method"]) - VALID_METHOD))

    check("every project is marked as public data",
          set(projects["data_type"]) == {"public"},
          str(set(projects["data_type"])))


def test_expected_project_count(projects):
    upgrades = projects[projects["project_type"] == "transmission_upgrade"]
    check("all 11 SPP 2026 transmission upgrade circuits are present",
          sorted(upgrades["circuit_id"]) == sorted(SPP_2026_CIRCUITS),
          f"got {sorted(upgrades['circuit_id'])}")

    hardening = projects[projects["project_type"] == "substation_hardening"]
    check("all 5 SPP 2026 substation hardening projects are present",
          len(hardening) == 5, f"got {len(hardening)}")

    high = (projects["location_confidence"] == "HIGH").sum()
    located = projects["mid_lat"].notna().sum()
    check("at least 4 HIGH-confidence projects for the demo", high >= 4,
          f"got {high}")
    print(f"      {high} HIGH, {located} projects with usable coordinates")


def test_no_route_claims(projects):
    """Endpoint-to-endpoint lines must never be labelled as a real route."""
    banned = ["actual_route", "transmission_geometry", "verified_line_path", "route"]
    text = projects.astype(str).apply(lambda column: column.str.lower())
    hits = [word for word in banned
            if text.apply(lambda c: c.str.contains(word, regex=False)).any().any()]
    check("no column claims verified route geometry", not hits, str(hits))

    corridors = projects[projects["geometry_type"] == "approximate_corridor"]
    check("corridor rows have both endpoints",
          corridors[["from_lat", "from_lon", "to_lat", "to_lon"]].notna().all().all(),
          "a corridor is missing an endpoint")


def test_haversine_is_sane():
    """A known pair, so a broken distance function cannot pass quietly."""
    # Gannon and Juneau, the two endpoints of circuit 230037.
    miles = haversine_miles(27.938069, -82.440138, 28.022843, -82.481015)
    check("haversine returns a sensible distance for Gannon-Juneau",
          6.0 < miles < 6.8, f"got {miles:.3f} miles")
    check("haversine of a point with itself is 0",
          math.isclose(haversine_miles(28.0, -82.0, 28.0, -82.0), 0.0, abs_tol=1e-9))
    check("haversine is symmetric",
          math.isclose(haversine_miles(27.9, -82.4, 28.1, -82.5),
                       haversine_miles(28.1, -82.5, 27.9, -82.4), rel_tol=1e-12))


def main():
    projects, lookup = load()
    test_circuit_join_is_exact(projects, lookup)
    test_coordinates_are_valid(projects)
    test_missing_stays_missing(projects)
    test_provenance(projects)
    test_expected_project_count(projects)
    test_no_route_claims(projects)
    test_haversine_is_sane()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
