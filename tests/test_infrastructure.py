# Aaron Green
# Checks the structured project-type and voltage similarity in analysis/infrastructure.py.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.infrastructure import (  # noqa: E402
    calculate_infrastructure_similarity, calculate_project_type_similarity,
    calculate_voltage_similarity, similarity_confidence, weighted_available_average,
)

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def test_project_type_same():
    check("same project type scores 100",
          calculate_project_type_similarity("transmission_upgrade", "transmission_upgrade") == 100)


def test_project_type_different():
    check("different project types score 0",
          calculate_project_type_similarity("transmission_upgrade", "substation_hardening") == 0)


def test_project_type_missing():
    check("missing type A gives null", calculate_project_type_similarity(None, "transmission_line") is None)
    check("missing type B gives null", calculate_project_type_similarity("transmission_line", None) is None)
    check("'unknown' type gives null", calculate_project_type_similarity("unknown", "transmission_line") is None)
    check("both missing gives null", calculate_project_type_similarity(None, None) is None)


def test_voltage_same():
    check("identical single voltage scores 100",
          calculate_voltage_similarity(230, 230, 230, 230) == 100)


def test_voltage_different():
    score = calculate_voltage_similarity(69, 69, 230, 230)
    check("a large voltage gap scores low", score is not None and score <= 20, f"got {score}")


def test_voltage_range_overlap():
    # Duke 115-230 kV range vs TECO fixed 230 kV: the ranges overlap at 230.
    score = calculate_voltage_similarity(115, 230, 230, 230)
    check("overlapping voltage ranges score 100", score == 100, f"got {score}")
    # Duke 230 kV vs TECO 138-230 kV: also overlaps.
    score = calculate_voltage_similarity(230, 230, 138, 230)
    check("a range overlapping a single point scores 100", score == 100, f"got {score}")


def test_voltage_missing():
    check("missing voltage on side A gives null",
          calculate_voltage_similarity(None, None, 230, 230) is None)
    check("missing voltage on side B gives null",
          calculate_voltage_similarity(230, 230, None, None) is None)
    check("missing voltage on both sides gives null",
          calculate_voltage_similarity(None, None, None, None) is None)


def test_voltage_gap_boundaries():
    # 69 vs 138: gap = 69, within the <=75 band -> 70.
    check("a 69 kV gap scores in the close band",
          calculate_voltage_similarity(69, 69, 138, 138) == 70)
    # 69 vs 230: gap = 161, beyond every threshold -> the floor score.
    check("a 161 kV gap scores the far-apart floor",
          calculate_voltage_similarity(69, 69, 230, 230) == 15)


def test_weighted_rebalancing_when_one_missing():
    scores = {"project_type": 100, "voltage": None}
    weights = {"project_type": 50, "voltage": 35}
    result = weighted_available_average(scores, weights)
    check("a missing component is excluded, not zeroed",
          result == 100, f"got {result}")


def test_weighted_average_both_present():
    scores = {"project_type": 100, "voltage": 0}
    weights = {"project_type": 50, "voltage": 35}
    result = weighted_available_average(scores, weights)
    expected = (100 * 50) / (50 + 35)
    check("weighted average matches hand-calculated value",
          abs(result - expected) < 1e-9, f"got {result}, expected {expected}")


def test_all_components_missing():
    scores = {"project_type": None, "voltage": None}
    weights = {"project_type": 50, "voltage": 35}
    check("all components missing gives null, not 0",
          weighted_available_average(scores, weights) is None)


def test_infrastructure_similarity_missing_voltage():
    project_a = {"project_type": "transmission_upgrade", "voltage_min_kv": 230, "voltage_max_kv": 230}
    project_b = {"project_type": "transmission_upgrade", "voltage_min_kv": None, "voltage_max_kv": None}
    features = calculate_infrastructure_similarity(project_a, project_b)
    check("infrastructure_similarity is still available when only voltage is missing",
          features["infrastructure_similarity_available"] is True)
    check("infrastructure_similarity uses only project type when voltage is missing",
          features["infrastructure_similarity"] == 100, str(features))


def test_infrastructure_similarity_all_missing():
    project_a = {"project_type": None, "voltage_min_kv": None, "voltage_max_kv": None}
    project_b = {"project_type": None, "voltage_min_kv": None, "voltage_max_kv": None}
    features = calculate_infrastructure_similarity(project_a, project_b)
    check("infrastructure_similarity_available is False with no comparable data",
          features["infrastructure_similarity_available"] is False)
    check("infrastructure_similarity is null, not 0, with no comparable data",
          features["infrastructure_similarity"] is None)


def test_similarity_confidence_levels():
    check("text+type+voltage available -> HIGH",
          similarity_confidence(True, 100, 100) == "HIGH")
    check("text+type only -> MEDIUM",
          similarity_confidence(True, 100, None) == "MEDIUM")
    check("type only -> LOW",
          similarity_confidence(False, 100, None) == "LOW")
    check("nothing available -> UNKNOWN",
          similarity_confidence(False, None, None) == "UNKNOWN")
    check("confidence is a label, not similarity strength",
          isinstance(similarity_confidence(True, 20, 20), str))


def main():
    test_project_type_same()
    test_project_type_different()
    test_project_type_missing()
    test_voltage_same()
    test_voltage_different()
    test_voltage_range_overlap()
    test_voltage_missing()
    test_voltage_gap_boundaries()
    test_weighted_rebalancing_when_one_missing()
    test_weighted_average_both_present()
    test_all_components_missing()
    test_infrastructure_similarity_missing_voltage()
    test_infrastructure_similarity_all_missing()
    test_similarity_confidence_levels()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
