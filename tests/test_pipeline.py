# Aaron Green
# Checks Coordination Package assembly, evidence pass-through, and the analyze_projects() interface.

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.pipeline import (  # noqa: E402
    PACKAGES_JSON, SCORED_CSV, analyze_projects, build_all_packages, build_coordination_package,
    build_opportunity_evidence, load_source_lookup,
)

# Language that would overstate what public planning data can support -
# checked against the whole package, not just resource evidence.
BANNED_PHRASES = [
    "should coordinate", "recommended", "should share", "can share",
    "will share", "available crews", "spare capacity", "$", "roi",
    "savings", "guaranteed", "confirmed available",
]

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def test_evidence_dedup_and_split():
    row = {"evidence": "First sentence. | Second sentence. | First sentence."}
    evidence = build_opportunity_evidence(row)
    check("evidence is split on the pipe delimiter", len(evidence) == 2, evidence)
    check("duplicate sentences are removed", evidence == ["First sentence.", "Second sentence."], evidence)


def test_missing_evidence_gives_empty_list():
    check("no evidence column gives an empty list, not a crash", build_opportunity_evidence({}) == [])
    check("an empty evidence string gives an empty list",
          build_opportunity_evidence({"evidence": ""}) == [])


def test_evidence_wording_is_passed_through_unaltered():
    """Task 6 must not rephrase Task 3's precision-aware wording."""
    row = {"evidence": "Insufficient location data to estimate distance between these projects. | "
                       "Insufficient schedule information to compare timing."}
    evidence = build_opportunity_evidence(row)
    check("a missing-distance sentence is passed through exactly, not fabricated",
          "Insufficient location data" in evidence[0])
    check("a missing-schedule sentence is passed through exactly, not fabricated",
          "Insufficient schedule information" in evidence[1])


def _sample_row():
    scored = pd.read_csv(SCORED_CSV)
    eligible = scored[scored["coordination_score_eligible"]]
    return eligible.iloc[0].to_dict()


def test_package_matches_source_row_exactly():
    row = _sample_row()
    package = build_coordination_package(row)
    check("opportunity_id matches the source pair_id", package["opportunity_id"] == row["pair_id"])
    check("coordination_score is not recalculated",
          package["analysis"]["coordination_score"] == row["coordination_score"])
    check("opportunity_rank is not recalculated",
          package["analysis"]["opportunity_rank"] == int(row["opportunity_rank"]))
    check("geographic_score is passed through unchanged",
          package["analysis"]["geographic_score"] == row["geographic_score"])


def test_package_is_json_serializable():
    row = _sample_row()
    package = build_coordination_package(row)
    try:
        json.dumps(package)
        ok = True
    except TypeError:
        ok = False
    check("the package serializes to JSON without error", ok)


def test_package_contains_no_overreaching_claims():
    row = _sample_row()
    package = build_coordination_package(row)
    text = json.dumps(package).lower()
    for phrase in BANNED_PHRASES:
        check(f"package does not contain {phrase!r}", phrase not in text)


def test_project_objects_carry_map_and_schedule_fields():
    """A dashboard must be able to plot a project and apply a year filter
    without loading a separate CSV - regression for a real gap: these fields
    used to be missing from the package entirely.
    """
    row = _sample_row()
    package = build_coordination_package(row)
    for side in ("project_a", "project_b"):
        project = package[side]
        for field in ("mid_lat", "mid_lon", "start", "end", "in_service_year",
                     "date_precision", "status"):
            check(f"{side}.{field} is present in the package", field in project, project.keys())
    check("analysis includes year_difference for the year-filter requirement",
          "year_difference" in package["analysis"])
    check("analysis includes same_active_year",
          "same_active_year" in package["analysis"])


def test_project_objects_carry_sources():
    row = _sample_row()
    sources = load_source_lookup()
    package = build_coordination_package(row, sources)
    for side in ("project_a", "project_b"):
        project = package[side]
        check(f"{side} has a non-empty sources dict",
              isinstance(project["sources"], dict) and len(project["sources"]) > 0,
              project["sources"])
        check(f"{side}.sources contains a real citation, not a placeholder",
              any(isinstance(v, str) and len(v) > 10 for v in project["sources"].values()))


def test_voltage_label_fallback_reaches_resource_evidence():
    """Regression: the numeric voltage fallback was fixed in Task 5's own
    evidence text but never reached Task 6's separate resource-evidence path -
    a HIGH-potential resource was silently missing its voltage justification.
    """
    scored = pd.read_csv(SCORED_CSV)
    eligible = scored[scored["coordination_score_eligible"]]
    top = eligible[eligible["opportunity_rank"] == 1].iloc[0].to_dict()
    package = build_coordination_package(top, load_source_lookup())
    check("Duke's voltage_label is never the literal word 'None' in the package",
          package["project_a"]["voltage_label"] != "None"
          and package["project_a"]["voltage_label"] is not None)
    high_resources = [r for r in package["potential_shared_resources"] if r["potential"] == "HIGH"]
    if high_resources:
        for resource in high_resources:
            text = " ".join(resource["evidence"])
            check(f"a HIGH-potential resource ({resource['resource_id']}) states its "
                  f"voltage corroboration, not just the type match",
                  "voltage" in text.lower(), text)


def test_all_packages_built_and_ranked():
    scored = pd.read_csv(SCORED_CSV)
    packages = build_all_packages(scored)
    eligible_count = int(scored["coordination_score_eligible"].sum())
    check("one package per eligible pair", len(packages) == eligible_count,
          f"{len(packages)} vs {eligible_count}")
    ranks = [p["analysis"]["opportunity_rank"] for p in packages]
    check("packages are already in rank order", ranks == sorted(ranks), ranks)
    check("no ineligible pair produced a package",
          all(r is not None for r in ranks))


def main():
    test_evidence_dedup_and_split()
    test_missing_evidence_gives_empty_list()
    test_evidence_wording_is_passed_through_unaltered()
    test_package_matches_source_row_exactly()
    test_package_is_json_serializable()
    test_package_contains_no_overreaching_claims()
    test_project_objects_carry_map_and_schedule_fields()
    test_project_objects_carry_sources()
    test_voltage_label_fallback_reaches_resource_evidence()
    test_all_packages_built_and_ranked()

    # analyze_projects() interface tests - require the built JSON on disk.
    if not PACKAGES_JSON.exists():
        print(f"SKIP  analyze_projects() tests -- {PACKAGES_JSON} not built yet")
    else:
        test_analyze_projects_valid_pair()
        test_analyze_projects_min_score()
        test_analyze_projects_top_n()
        test_analyze_projects_unsupported_pair()
        test_analyze_projects_deterministic_order()
        test_analyze_projects_json_serializable()
        test_data_integrity_against_task5()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


def test_analyze_projects_valid_pair():
    result = analyze_projects("Duke Energy Florida", "Tampa Electric")
    check("a valid utility pair returns opportunities", len(result["opportunities"]) > 0)
    check("summary counts are calculated, not hard-coded",
          result["summary"]["pairs_analyzed"] > 0
          and result["summary"]["eligible_opportunities"] == len(result["opportunities"]))


def test_analyze_projects_min_score():
    result = analyze_projects("Duke Energy Florida", "Tampa Electric", min_score=50)
    check("min_score filters out lower scores",
          all(o["analysis"]["coordination_score"] >= 50 for o in result["opportunities"]))
    unfiltered = analyze_projects("Duke Energy Florida", "Tampa Electric")
    check("min_score never returns more than the unfiltered result",
          len(result["opportunities"]) <= len(unfiltered["opportunities"]))


def test_analyze_projects_top_n():
    result = analyze_projects("Duke Energy Florida", "Tampa Electric", top_n=3)
    check("top_n limits the returned count", len(result["opportunities"]) == 3)
    ranks = [o["analysis"]["opportunity_rank"] for o in result["opportunities"]]
    check("top_n keeps the best-ranked opportunities", ranks == sorted(ranks) and ranks[0] == 1)


def test_analyze_projects_unsupported_pair():
    result = analyze_projects("Duke Energy Florida", "Some Utility That Does Not Exist")
    check("an unsupported utility pair does not raise, returns empty opportunities",
          result["opportunities"] == [])
    check("an unsupported utility pair reports zero pairs analyzed",
          result["summary"]["pairs_analyzed"] == 0)


def test_analyze_projects_deterministic_order():
    first = analyze_projects("Duke Energy Florida", "Tampa Electric")
    second = analyze_projects("Duke Energy Florida", "Tampa Electric")
    check("repeated calls return identical ordering",
          [o["opportunity_id"] for o in first["opportunities"]]
          == [o["opportunity_id"] for o in second["opportunities"]])


def test_analyze_projects_json_serializable():
    result = analyze_projects("Duke Energy Florida", "Tampa Electric", top_n=5)
    try:
        json.dumps(result)
        ok = True
    except TypeError:
        ok = False
    check("the full analyze_projects() response is JSON-serializable", ok)


def test_data_integrity_against_task5():
    scored = pd.read_csv(SCORED_CSV).set_index("pair_id")
    with PACKAGES_JSON.open() as handle:
        packages = json.load(handle)
    mismatches = [p["opportunity_id"] for p in packages
                 if p["analysis"]["coordination_score"] != scored.loc[p["opportunity_id"], "coordination_score"]
                 or p["analysis"]["opportunity_rank"] != int(scored.loc[p["opportunity_id"], "opportunity_rank"])]
    check("every package's score and rank match Task 5's file exactly on disk",
          not mismatches, mismatches)


if __name__ == "__main__":
    sys.exit(main())
