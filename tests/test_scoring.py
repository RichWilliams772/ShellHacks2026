# Aaron Green
# Checks the Coordination Score math, eligibility, and ranking in analysis/scoring.py.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.scoring import (  # noqa: E402
    calculate_coordination_score, components_available, is_score_eligible,
    rank_opportunities, score_weight_coverage,
)

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def test_all_four_available():
    score = calculate_coordination_score(80, 100, 82, 84)
    expected = 0.40 * 80 + 0.30 * 100 + 0.20 * 82 + 0.10 * 84
    check("weighted score matches hand calculation with all 4 present",
          abs(score - round(expected, 1)) < 0.05, f"got {score}, expected ~{expected:.1f}")


def test_score_within_range():
    for combo in [(100, 100, 100, 100), (0, 0, 0, 0), (50, 20, 90, 10)]:
        score = calculate_coordination_score(*combo)
        check(f"score for {combo} is within 0-100", 0 <= score <= 100, f"got {score}")


def test_missing_component_is_not_zero():
    with_infra = calculate_coordination_score(80, 90, 70, 84)
    without_infra = calculate_coordination_score(80, 90, 70, None)
    check("dropping a component reweights rather than pulling the score toward 0",
          without_infra > with_infra - 20, f"{without_infra} vs {with_infra}")
    # A perfect score on the 3 remaining components should not collapse just
    # because one is missing.
    check("missing infrastructure with strong remaining evidence still scores high",
          calculate_coordination_score(100, 100, 100, None) > 90)


def test_available_weight_rebalancing_matches_hand_calc():
    # geographic=40%, temporal=30%, text=20% available; infrastructure missing.
    # Renormalized: 40/90, 30/90, 20/90.
    score = calculate_coordination_score(80, 90, 70, None)
    expected = (0.40 * 80 + 0.30 * 90 + 0.20 * 70) / 0.90
    check("rebalanced weights match hand calculation",
          abs(score - round(expected, 1)) < 0.05, f"got {score}, expected ~{expected:.1f}")


def test_insufficient_evidence_returns_null_score():
    # Only geography - the exact "over-rewarding sparse pairs" trap.
    check("geography alone (1 of 4) is not eligible",
          not is_score_eligible(100, None, None, None))
    check("geography alone gives a null score, not 100",
          calculate_coordination_score(100, None, None, None) is None)


def test_geography_missing_makes_pair_ineligible():
    """The selected rule: geography must be present, even with 3 other components."""
    check("3 of 4 without geography is still ineligible",
          not is_score_eligible(None, 90, 80, 84))
    check("a pair with no geography gets a null score no matter how strong the rest is",
          calculate_coordination_score(None, 100, 100, 100) is None)


def test_geography_present_with_three_is_eligible():
    check("geography + 2 others (3 of 4) is eligible",
          is_score_eligible(80, 90, 70, None))
    check("geography + 2 others produces a real score",
          calculate_coordination_score(80, 90, 70, None) is not None)


def test_two_components_is_ineligible_even_with_geography():
    check("geography + only 1 other (2 of 4) is not eligible",
          not is_score_eligible(80, None, None, 84))


def test_components_available_count():
    check("all 4 present counts as 4", components_available(1, 1, 1, 1) == 4)
    check("3 present counts as 3", components_available(1, None, 1, 1) == 3)
    check("0 present counts as 0", components_available(None, None, None, None) == 0)


def test_score_weight_coverage():
    check("full coverage is 1.0", score_weight_coverage(1, 1, 1, 1) == 1.0)
    check("missing infrastructure (10%) gives 0.90",
          abs(score_weight_coverage(1, 1, 1, None) - 0.90) < 1e-9)
    check("missing geography (40%) gives 0.60",
          abs(score_weight_coverage(None, 1, 1, 1) - 0.60) < 1e-9)


def test_score_is_deterministic():
    a = calculate_coordination_score(63.2, 41.7, 12.9, 88.0)
    b = calculate_coordination_score(63.2, 41.7, 12.9, 88.0)
    check("identical inputs always give an identical score", a == b, f"{a} vs {b}")


def test_rounding_happens_only_at_output():
    # Two different unrounded inputs that would round to the same displayed
    # value must still be computed from full precision internally - checked
    # indirectly by confirming the function itself returns a rounded value
    # matching a full-precision hand calculation, not a pre-rounded one.
    score = calculate_coordination_score(83.33, 66.67, 41.41, 90.0)
    expected = 0.40 * 83.33 + 0.30 * 66.67 + 0.20 * 41.41 + 0.10 * 90.0
    check("output matches full-precision calculation rounded once",
          abs(score - round(expected, 1)) < 0.05, f"got {score}, expected ~{round(expected,1)}")


def _row(pair_id, score, geo, temporal, eligible=True):
    return {"pair_id": pair_id, "coordination_score": score, "geographic_score": geo,
            "temporal_score": temporal, "coordination_score_eligible": eligible}


def test_ranking_orders_by_score_descending():
    rows = [_row("A", 50, 10, 10), _row("B", 90, 10, 10), _row("C", 70, 10, 10)]
    ranked = rank_opportunities(rows)
    order = sorted(ranked, key=lambda r: r["opportunity_rank"])
    check("higher score gets a better (lower) rank",
          [r["pair_id"] for r in order] == ["B", "C", "A"], str([r["pair_id"] for r in order]))


def test_ranking_tie_break_is_deterministic():
    rows = [_row("Z", 80, 10, 90), _row("A", 80, 10, 90), _row("M", 80, 20, 90)]
    ranked = rank_opportunities(rows)
    order = sorted(ranked, key=lambda r: r["opportunity_rank"])
    # M wins on geographic_score, then Z/A tie on everything and fall to pair_id.
    check("ties break on geographic_score then pair_id",
          [r["pair_id"] for r in order] == ["M", "A", "Z"], str([r["pair_id"] for r in order]))


def test_ineligible_rows_get_null_rank():
    rows = [_row("A", 90, 10, 10), _row("B", None, None, None, eligible=False)]
    ranked = rank_opportunities(rows)
    ineligible = [r for r in ranked if r["pair_id"] == "B"][0]
    check("an ineligible row is not deleted", any(r["pair_id"] == "B" for r in ranked))
    check("an ineligible row gets a null rank", ineligible["opportunity_rank"] is None)


def test_ranking_is_stable_across_repeated_runs():
    rows = [_row("A", 50, 10, 10), _row("B", 90, 10, 10), _row("C", 70, 10, 10)]
    first = [r["opportunity_rank"] for r in rank_opportunities([dict(r) for r in rows])]
    second = [r["opportunity_rank"] for r in rank_opportunities([dict(r) for r in rows])]
    check("ranking is identical across repeated runs", first == second)


def main():
    test_all_four_available()
    test_score_within_range()
    test_missing_component_is_not_zero()
    test_available_weight_rebalancing_matches_hand_calc()
    test_insufficient_evidence_returns_null_score()
    test_geography_missing_makes_pair_ineligible()
    test_geography_present_with_three_is_eligible()
    test_two_components_is_ineligible_even_with_geography()
    test_components_available_count()
    test_score_weight_coverage()
    test_score_is_deterministic()
    test_rounding_happens_only_at_output()
    test_ranking_orders_by_score_descending()
    test_ranking_tie_break_is_deterministic()
    test_ineligible_rows_get_null_rank()
    test_ranking_is_stable_across_repeated_runs()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
