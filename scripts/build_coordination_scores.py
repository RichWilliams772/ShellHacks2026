# Aaron Green
# Scores, ranks, and explains every Duke x TECO pair from Task 4 - no new data, no new ML.

import csv
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.confidence import calculate_score_confidence  # noqa: E402
from analysis.scoring import (  # noqa: E402
    build_evidence, calculate_coordination_score, components_available,
    is_score_eligible, rank_opportunities, score_weight_coverage,
)

SIMILARITY_CSV = ROOT / "data" / "processed" / "duke_teco_pair_similarity.csv"
OUT_CSV = ROOT / "data" / "processed" / "duke_teco_scored_opportunities.csv"

COMPONENT_COLUMNS = ["geographic_score", "temporal_score", "text_similarity_score",
                    "infrastructure_similarity"]
NEW_FIELDS = [
    "coordination_score_eligible", "components_available", "score_weight_coverage",
    "coordination_score", "score_confidence", "opportunity_rank", "evidence",
]


def clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def validate_component_ranges(pairs):
    """PROJECT_SPEC section 5: never silently clamp an out-of-range component.
    Fail loudly if Task 4's own output ever violates its own contract.
    """
    problems = []
    for column in COMPONENT_COLUMNS:
        values = pairs[column].dropna()
        bad = values[(values < 0) | (values > 100)]
        if not bad.empty:
            problems.append(f"{column} has {len(bad)} value(s) outside 0-100")
    if problems:
        raise SystemExit("Component range validation failed:\n  " + "\n  ".join(problems))


def score_row(raw_row):
    row = {key: clean(value) for key, value in raw_row.items()}
    geographic = row["geographic_score"]
    temporal = row["temporal_score"]
    text_similarity = row["text_similarity_score"]
    infrastructure = row["infrastructure_similarity"]

    eligible = is_score_eligible(geographic, temporal, text_similarity, infrastructure)
    n_available = components_available(geographic, temporal, text_similarity, infrastructure)
    coverage = score_weight_coverage(geographic, temporal, text_similarity, infrastructure)
    score = calculate_coordination_score(geographic, temporal, text_similarity, infrastructure)
    confidence = calculate_score_confidence(
        eligible, n_available, row["pair_geography_confidence"],
        row["temporal_data_available"], row["similarity_confidence"])
    evidence = build_evidence(row) if eligible else []

    return {
        **row,
        "coordination_score_eligible": eligible,
        "components_available": n_available,
        "score_weight_coverage": coverage,
        "coordination_score": score,
        "score_confidence": confidence,
        "evidence": " | ".join(evidence) if evidence else None,
    }


def summarize(rows):
    eligible = [r for r in rows if r["coordination_score_eligible"]]
    ineligible = [r for r in rows if not r["coordination_score_eligible"]]
    scores = sorted(r["coordination_score"] for r in eligible)

    print("=" * 70)
    print("TASK 5 VALIDATION REPORT")
    print("=" * 70)
    print(f"total candidate pairs:     {len(rows)}")
    print(f"score-eligible:            {len(eligible)}")
    print(f"ineligible:                {len(ineligible)}")
    if scores:
        n = len(scores)
        median = scores[n // 2] if n % 2 else (scores[n // 2 - 1] + scores[n // 2]) / 2
        mean = sum(scores) / n
        print(f"coordination_score min/median/mean/max: "
              f"{scores[0]:.1f} / {median:.1f} / {mean:.1f} / {scores[-1]:.1f}")
    print("score_confidence distribution:")
    counts = {}
    for r in rows:
        counts[r["score_confidence"]] = counts.get(r["score_confidence"], 0) + 1
    for level in ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT"):
        if level in counts:
            print(f"  {level:<13} {counts[level]}")
    print("score_weight_coverage distribution (eligible pairs):")
    coverage_counts = {}
    for r in eligible:
        coverage_counts[r["score_weight_coverage"]] = coverage_counts.get(r["score_weight_coverage"], 0) + 1
    for coverage in sorted(coverage_counts, reverse=True):
        print(f"  {coverage:.2f}          {coverage_counts[coverage]}")
    print("=" * 70)


def print_top(rows, n=10):
    print(f"\nVALIDATION - top {n} ranked opportunities:")
    top = sorted((r for r in rows if r["opportunity_rank"]), key=lambda r: r["opportunity_rank"])[:n]
    for r in top:
        print(f"\n  #{r['opportunity_rank']}  {r['pair_id']}  "
              f"score={r['coordination_score']}  confidence={r['score_confidence']}")
        print(f"      {r['project_a_name'][:40]:<40} <-> {r['project_b_name']}")
        print(f"      geo={r['geographic_score']} temporal={r['temporal_score']} "
              f"text={r['text_similarity_score']} infra={r['infrastructure_similarity']}  "
              f"distance={r['minimum_endpoint_distance_miles']}mi")
        print(f"      evidence: {r['evidence']}")


def print_bottom(rows, n=5):
    print(f"\nVALIDATION - {n} lowest-scoring eligible pairs:")
    eligible = [r for r in rows if r["coordination_score_eligible"]]
    bottom = sorted(eligible, key=lambda r: r["coordination_score"])[:n]
    for r in bottom:
        print(f"  {r['pair_id']:<28} score={r['coordination_score']:>5.1f}  "
              f"geo={r['geographic_score']} temporal={r['temporal_score']} "
              f"text={r['text_similarity_score']} infra={r['infrastructure_similarity']}")


def print_high_score_lower_confidence(rows, n=5):
    print(f"\nVALIDATION - high score with MEDIUM/LOW confidence (up to {n}):")
    candidates = sorted(
        (r for r in rows if r["coordination_score_eligible"]
         and r["score_confidence"] in ("MEDIUM", "LOW")),
        key=lambda r: r["coordination_score"], reverse=True)[:n]
    if not candidates:
        print("  none found in this dataset")
    for r in candidates:
        print(f"  {r['pair_id']:<28} score={r['coordination_score']:>5.1f}  "
              f"confidence={r['score_confidence']}  components={r['components_available']}/4  "
              f"coverage={r['score_weight_coverage']}")


def print_disagreements(rows, n=5):
    print(f"\nVALIDATION - component disagreement cases:")
    eligible = [r for r in rows if r["coordination_score_eligible"]]

    high_geo_low_sim = sorted(
        eligible, key=lambda r: (r["geographic_score"] or 0) - (r["text_similarity_score"] or 0),
        reverse=True)[:n]
    print(f"  high geography, low text similarity:")
    for r in high_geo_low_sim:
        print(f"    {r['pair_id']:<28} geo={r['geographic_score']}  text={r['text_similarity_score']}")

    high_sim_low_geo = sorted(
        (r for r in eligible if r["geographic_score"] is not None),
        key=lambda r: (r["text_similarity_score"] or 0) - r["geographic_score"],
        reverse=True)[:n]
    print(f"  high text similarity relative to geography:")
    for r in high_sim_low_geo:
        print(f"    {r['pair_id']:<28} geo={r['geographic_score']}  text={r['text_similarity_score']}")


def sensitivity_check(rows, n=10):
    """Lightweight, report-only: does the top-N order change under a small,
    reasonable reweighting? Not optimization - just a stability spot check
    (PROJECT_SPEC section 51).
    """
    print(f"\nVALIDATION - light weight-sensitivity check (report only, no optimization):")
    baseline = sorted((r for r in rows if r["opportunity_rank"]),
                      key=lambda r: r["opportunity_rank"])[:n]
    baseline_order = [r["pair_id"] for r in baseline]

    alt_weights = {"geographic": 0.35, "temporal": 0.35, "text_similarity": 0.20, "infrastructure": 0.10}
    alt_scores = []
    for r in rows:
        if not r["coordination_score_eligible"]:
            continue
        scores = {"geographic": r["geographic_score"], "temporal": r["temporal_score"],
                 "text_similarity": r["text_similarity_score"], "infrastructure": r["infrastructure_similarity"]}
        from analysis.infrastructure import weighted_available_average
        alt_score = weighted_available_average(scores, alt_weights)
        alt_scores.append((alt_score, r["pair_id"]))
    alt_scores.sort(key=lambda x: (-x[0], x[1]))
    alt_order = [pair_id for _, pair_id in alt_scores[:n]]

    overlap = len(set(baseline_order) & set(alt_order))
    print(f"  baseline weights (geo=40/temporal=30): top {n} = {baseline_order}")
    print(f"  shifted weights  (geo=35/temporal=35): top {n} = {alt_order}")
    print(f"  overlap in top {n}: {overlap}/{n}")
    if baseline_order and alt_order and baseline_order[0] != alt_order[0]:
        print(f"  NOTE: #1 opportunity changes under this shift "
              f"({baseline_order[0]} -> {alt_order[0]})")


def main():
    pairs = pd.read_csv(SIMILARITY_CSV)
    validate_component_ranges(pairs)

    rows = [score_row(row) for row in pairs.to_dict("records")]
    rows = rank_opportunities(rows)

    out_of_range = [r for r in rows if r["coordination_score"] is not None
                    and not (0 <= r["coordination_score"] <= 100)]
    if out_of_range:
        raise SystemExit(f"{len(out_of_range)} coordination_score values fell outside 0-100")

    fields = list(pairs.columns) + NEW_FIELDS
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} scored pairs to {OUT_CSV.relative_to(ROOT)}\n")
    summarize(rows)
    print_top(rows)
    print_bottom(rows)
    print_high_score_lower_confidence(rows)
    print_disagreements(rows)
    sensitivity_check(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
