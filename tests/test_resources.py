# Aaron Green
# Checks resource matching stays conservative and never derives from score, geography, or schedule.

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.resource_rules import (  # noqa: E402
    build_shared_resources, calculate_resource_potential, get_project_resource_categories,
    match_shared_resources,
)

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def test_same_compatible_type_returns_expected_categories():
    shared = match_shared_resources("transmission_upgrade", "transmission_upgrade")
    check("identical transmission types share all 5 transmission categories",
          shared == {"specialized_line_crews", "heavy_equipment", "material_logistics",
                     "outage_planning", "construction_mobilization"}, shared)


def test_different_types_return_only_defensible_intersection():
    shared = match_shared_resources("transmission_upgrade", "substation_hardening")
    check("transmission vs substation hardening share only the general categories",
          shared == {"material_logistics", "outage_planning", "construction_mobilization"}, shared)
    check("line-specific categories are NOT claimed across incompatible types",
          "specialized_line_crews" not in shared and "electrical_crews" not in shared)


def test_unknown_type_gives_no_speculative_resources():
    check("an unrecognized project type maps to no categories",
          get_project_resource_categories("unknown") == set())
    check("pairing a real type against 'unknown' shares nothing",
          match_shared_resources("transmission_upgrade", "unknown") == set())


def test_missing_type_does_not_crash():
    check("None does not raise", get_project_resource_categories(None) == set())
    check("empty string does not raise", get_project_resource_categories("") == set())
    check("pairing a real type against None shares nothing, and does not crash",
          match_shared_resources("transmission_upgrade", None) == set())


def test_shared_resources_are_deterministic():
    first = match_shared_resources("transmission_upgrade", "transmission_line")
    second = match_shared_resources("transmission_upgrade", "transmission_line")
    check("the same inputs always give the same shared set", first == second)


def test_no_duplicate_resources_in_output():
    resources = build_shared_resources("transmission_upgrade", "transmission_upgrade",
                                       100, 100, "230 kV", "230 kV")
    ids = [r["resource_id"] for r in resources]
    check("no resource_id appears twice", len(ids) == len(set(ids)), ids)


def test_resource_potential_high_requires_both_signals():
    check("same type + compatible voltage -> HIGH",
          calculate_resource_potential(100, 100) == "HIGH")
    check("same type + compatible voltage at the exact threshold -> HIGH",
          calculate_resource_potential(100, 70) == "HIGH")


def test_resource_potential_medium_requires_one_signal():
    check("same type + incompatible voltage -> MEDIUM, not HIGH",
          calculate_resource_potential(100, 15) == "MEDIUM")
    check("same type + unknown voltage -> MEDIUM, not HIGH",
          calculate_resource_potential(100, None) == "MEDIUM")
    check("different type + compatible voltage -> MEDIUM",
          calculate_resource_potential(0, 100) == "MEDIUM")


def test_resource_potential_low_when_neither_signal_present():
    check("different type + incompatible voltage -> LOW",
          calculate_resource_potential(0, 15) == "LOW")
    check("different type + unknown voltage -> LOW",
          calculate_resource_potential(0, None) == "LOW")


def test_resource_potential_never_reaches_high_from_type_match_alone():
    """The core conservatism requirement: matching project type by itself is
    not enough to call a resource category HIGH-potential - PROJECT_SPEC's
    own example rule would allow this; this project deliberately requires a
    second independent signal (voltage) before making that claim.
    """
    check("project-type match alone (voltage unknown) never reaches HIGH",
          calculate_resource_potential(100, None) != "HIGH")
    check("project-type match alone (voltage incompatible) never reaches HIGH",
          calculate_resource_potential(100, 15) != "HIGH")


def test_high_score_alone_does_not_create_resources():
    """calculate_resource_potential and match_shared_resources must not even
    be able to see a Coordination Score - proof, not just a claim.
    """
    for fn in (calculate_resource_potential, match_shared_resources, get_project_resource_categories):
        params = set(inspect.signature(fn).parameters)
        check(f"{fn.__name__} has no coordination_score parameter",
              "coordination_score" not in params and "score" not in params, params)


def test_geography_alone_does_not_create_resources():
    for fn in (calculate_resource_potential, match_shared_resources):
        params = set(inspect.signature(fn).parameters)
        check(f"{fn.__name__} has no distance/geography parameter",
              not params & {"distance", "distance_miles", "geographic_score"}, params)


def test_schedule_alone_does_not_create_resources():
    for fn in (calculate_resource_potential, match_shared_resources):
        params = set(inspect.signature(fn).parameters)
        check(f"{fn.__name__} has no schedule/temporal parameter",
              not params & {"schedule_overlap", "temporal_score", "schedule_overlap_months"}, params)


def test_no_resources_when_intersection_is_empty():
    resources = build_shared_resources("unknown", "unknown", None, None, None, None)
    check("no shared category produces an empty resource list, not a guess", resources == [])


def test_evidence_never_claims_confirmed_sharing():
    """Wording check: never claim two projects CAN share a resource, only that
    the category is worth investigating.
    """
    resources = build_shared_resources("transmission_upgrade", "transmission_upgrade",
                                       100, 100, "230 kV", "230 kV")
    banned_phrases = ["can share", "will share", "available", "confirmed"]
    for resource in resources:
        text = " ".join(resource["evidence"]).lower()
        for phrase in banned_phrases:
            check(f"evidence for {resource['resource_id']} does not say {phrase!r}",
                  phrase not in text, text)


def main():
    test_same_compatible_type_returns_expected_categories()
    test_different_types_return_only_defensible_intersection()
    test_unknown_type_gives_no_speculative_resources()
    test_missing_type_does_not_crash()
    test_shared_resources_are_deterministic()
    test_no_duplicate_resources_in_output()
    test_resource_potential_high_requires_both_signals()
    test_resource_potential_medium_requires_one_signal()
    test_resource_potential_low_when_neither_signal_present()
    test_resource_potential_never_reaches_high_from_type_match_alone()
    test_high_score_alone_does_not_create_resources()
    test_geography_alone_does_not_create_resources()
    test_schedule_alone_does_not_create_resources()
    test_no_resources_when_intersection_is_empty()
    test_evidence_never_claims_confirmed_sharing()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
