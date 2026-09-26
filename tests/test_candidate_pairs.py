# Aaron Green
# Checks the Duke projects and the Duke x TECO candidate pairs are built correctly.

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DUKE = ROOT / "data" / "processed" / "duke_projects_normalized.csv"
TECO = ROOT / "data" / "processed" / "teco_projects_geocoded.csv"
PAIRS = ROOT / "data" / "processed" / "duke_teco_candidate_pairs.csv"
EXCLUSIONS = ROOT / "data" / "interim" / "duke_project_exclusions.csv"

DUKE_UTILITY = "Duke Energy Florida"
TECO_UTILITY = "Tampa Electric"
VALID_CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
VALID_TYPES = {"transmission_upgrade", "transmission_line", "substation_upgrade",
               "reliability_upgrade", "substation_hardening", "unknown"}

LAT_COLUMNS = ["project_a_from_lat", "project_a_to_lat", "project_a_mid_lat",
               "project_b_from_lat", "project_b_to_lat", "project_b_mid_lat"]
LON_COLUMNS = [c.replace("_lat", "_lon") for c in LAT_COLUMNS]

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def test_duke_filtering(duke, exclusions):
    check("every Duke project is labelled Duke Energy Florida",
          set(duke["utility"]) == {DUKE_UTILITY}, str(set(duke["utility"])))

    # A completed project must never reach the future/active set.
    completed = duke[duke["status"].astype(str).str.strip().str.lower() == "complete"]
    check("no completed project is in the future set", completed.empty,
          str(list(completed["project_id"])))

    check("project types come from the shared vocabulary",
          set(duke["project_type"]) <= VALID_TYPES,
          str(set(duke["project_type"]) - VALID_TYPES))

    # Ambiguous records are kept, not filtered away.
    check("records with no status are preserved rather than dropped",
          duke["status"].isna().any(),
          "expected at least one preserved record with a blank status")

    check("every exclusion has a reason",
          exclusions["exclusion_reason"].notna().all()
          and (exclusions["exclusion_reason"].astype(str).str.strip() != "").all(),
          "an excluded record has no reason")

    reasons = set(exclusions["exclusion_reason"])
    check("completed projects were excluded for being completed",
          "completed_historical_project" in reasons, str(reasons))

    # An excluded project must not also appear in the included set.
    included_sources = set(duke["source_project_id"].dropna())
    overlap = included_sources & set(exclusions["project_id"].dropna())
    check("no project is both included and excluded", not overlap, str(overlap))

    flagged = duke[duke["ownership_confidence"] != "HIGH"]
    check("any owner disagreement carries a note and the original owner",
          flagged.empty or (flagged["ownership_note"].notna().all()
                            and flagged["owner_original"].notna().all()),
          str(list(flagged["project_id"])))


def test_teco_loads(teco):
    check("TECO dataset loaded", not teco.empty)
    check("every TECO project is labelled Tampa Electric",
          set(teco["utility"]) == {TECO_UTILITY}, str(set(teco["utility"])))
    required = {"project_id", "project_name", "project_type", "mid_lat", "mid_lon",
                "location_confidence", "date_precision"}
    check("TECO dataset has the fields pairing needs",
          required <= set(teco.columns), str(required - set(teco.columns)))


def test_pair_membership(pairs, duke, teco):
    check("side A is always Duke", set(pairs["project_a_utility"]) == {DUKE_UTILITY},
          str(set(pairs["project_a_utility"])))
    check("side B is always TECO", set(pairs["project_b_utility"]) == {TECO_UTILITY},
          str(set(pairs["project_b_utility"])))

    same = pairs[pairs["project_a_utility"] == pairs["project_b_utility"]]
    check("no same-utility pairs exist", same.empty, f"{len(same)} pairs")

    duke_ids, teco_ids = set(duke["project_id"]), set(teco["project_id"])
    check("no Duke x Duke pairs", not (set(pairs["project_b_id"]) & duke_ids),
          str(set(pairs["project_b_id"]) & duke_ids))
    check("no TECO x TECO pairs", not (set(pairs["project_a_id"]) & teco_ids),
          str(set(pairs["project_a_id"]) & teco_ids))

    check("every side A id is a known Duke project",
          set(pairs["project_a_id"]) <= duke_ids)
    check("every side B id is a known TECO project",
          set(pairs["project_b_id"]) <= teco_ids)


def test_pair_completeness(pairs, duke, teco):
    expected = len(duke) * len(teco)
    check(f"pair count equals {len(duke)} x {len(teco)} = {expected}",
          len(pairs) == expected, f"got {len(pairs)}")
    check("pair ids are unique", pairs["pair_id"].is_unique,
          f"{len(pairs) - pairs['pair_id'].nunique()} duplicates")
    check("pair id is built from both project ids",
          (pairs["pair_id"] == pairs["project_a_id"] + "__" + pairs["project_b_id"]).all())

    # Every Duke project must be paired with every TECO project exactly once.
    per_duke = pairs.groupby("project_a_id").size()
    check("every Duke project is paired with every TECO project",
          (per_duke == len(teco)).all(), str(per_duke[per_duke != len(teco)].to_dict()))


def test_coordinates(pairs):
    bad = []
    for column in LAT_COLUMNS:
        values = pairs[column].dropna()
        if not values.between(-90, 90).all():
            bad.append(column)
    for column in LON_COLUMNS:
        values = pairs[column].dropna()
        if not values.between(-180, 180).all():
            bad.append(column)
    check("all present coordinates are in range", not bad, str(bad))

    located = pairs[pairs["project_a_location_confidence"].isin(["HIGH", "MEDIUM"])]
    check("located side A rows have a representative point",
          located["project_a_mid_lat"].notna().all()
          and located["project_a_mid_lon"].notna().all())


def test_missing_stays_missing(pairs, duke):
    numeric = [c for c in pairs.columns
               if any(k in c for k in ("_lat", "_lon", "voltage", "in_service_year"))]
    zeros = [c for c in numeric if (pairs[c] == 0).any()]
    check("no numeric pair column was filled in with 0", not zeros, str(zeros))

    # Duke has only a year, so month-level dates must stay empty.
    check("Duke start and end dates were not invented",
          duke[["project_start", "construction_start", "project_end"]].isna().all().all(),
          "a Duke date was fabricated")
    check("Duke date precision is year",
          set(duke["date_precision"].dropna()) <= {"year"},
          str(set(duke["date_precision"].dropna())))

    unknown = pairs[pairs["project_b_location_confidence"] == "UNKNOWN"]
    check("UNKNOWN side B rows carry no coordinates",
          unknown[["project_b_from_lat", "project_b_to_lat",
                   "project_b_mid_lat"]].isna().all().all())


def test_no_scoring_columns(pairs):
    """Task 2 must not ship any computed metric."""
    banned = ["distance", "score", "overlap", "similarity", "shared_resource",
              "rank", "coordination"]
    hits = [c for c in pairs.columns if any(word in c.lower() for word in banned)]
    check("no scored or ranked columns are present", not hits, str(hits))


def test_confidence_is_descriptive(pairs):
    for column in ("project_a_location_confidence", "project_b_location_confidence"):
        values = set(pairs[column].dropna())
        check(f"{column} uses only the allowed labels", values <= VALID_CONFIDENCE,
              str(values - VALID_CONFIDENCE))
        check(f"{column} was not turned into a number",
              all(isinstance(v, str) for v in values))


def main():
    duke = pd.read_csv(DUKE)
    teco = pd.read_csv(TECO, dtype={"circuit_id": "string"})
    pairs = pd.read_csv(PAIRS)
    exclusions = pd.read_csv(EXCLUSIONS)

    test_duke_filtering(duke, exclusions)
    test_teco_loads(teco)
    test_pair_membership(pairs, duke, teco)
    test_pair_completeness(pairs, duke, teco)
    test_coordinates(pairs)
    test_missing_stays_missing(pairs, duke)
    test_no_scoring_columns(pairs)
    test_confidence_is_descriptive(pairs)

    mappable = int(pairs["geography_available_both"].sum())
    print(f"\n      {len(duke)} Duke x {len(teco)} TECO = {len(pairs)} pairs, "
          f"{mappable} with geography on both sides")

    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
