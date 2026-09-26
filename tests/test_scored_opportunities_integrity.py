# Aaron Green
# Confirms Task 5's output didn't quietly change what Task 4 built, and adds no Task 6 fields.

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIMILARITY = ROOT / "data" / "processed" / "duke_teco_pair_similarity.csv"
SCORED = ROOT / "data" / "processed" / "duke_teco_scored_opportunities.csv"

CARRIED_FROM_TASK_4 = [
    "pair_id", "project_a_id", "project_b_id", "geographic_score", "temporal_score",
    "text_similarity_score", "infrastructure_similarity", "minimum_endpoint_distance_miles",
    "pair_geography_confidence", "temporal_precision", "similarity_confidence",
]

FORBIDDEN_LATER_TASK_COLUMNS = [
    "shared_resources", "coordination_package", "specialized_crews", "heavy_equipment",
    "outage_planning", "material_logistics", "savings", "roi", "should_coordinate",
    "recommended", "approve_coordination", "coordination_decision",
]

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def main():
    similarity = pd.read_csv(SIMILARITY)
    scored = pd.read_csv(SCORED)

    check("pair count is unchanged from Task 4",
          len(scored) == len(similarity), f"{len(scored)} vs {len(similarity)}")
    check("pair ids are still unique", scored["pair_id"].is_unique)
    check("the set of pair ids is identical to Task 4's",
          set(scored["pair_id"]) == set(similarity["pair_id"]))

    merged = similarity.merge(scored, on="pair_id", suffixes=("_task4", "_task5"))
    for field in CARRIED_FROM_TASK_4:
        left, right = f"{field}_task4", f"{field}_task5"
        if left not in merged.columns:
            check(f"{field} is unchanged from Task 4", scored[field].equals(similarity[field]))
            continue
        unchanged = (merged[left] == merged[right]) | (merged[left].isna() & merged[right].isna())
        check(f"{field} is unchanged from Task 4", unchanged.all(),
              f"{(~unchanged).sum()} rows differ")

    present = [c for c in FORBIDDEN_LATER_TASK_COLUMNS if c in scored.columns]
    check("no Task 6 (resources/savings/decisions) columns exist", not present, str(present))

    # Component range validation - the exact check the pipeline itself must
    # have already enforced before scoring anything.
    for column in ("geographic_score", "temporal_score", "text_similarity_score",
                   "infrastructure_similarity", "coordination_score"):
        values = scored[column].dropna()
        out_of_range = values[(values < 0) | (values > 100)]
        check(f"{column} stays within 0-100", out_of_range.empty, f"{len(out_of_range)} bad rows")

    ineligible = scored[~scored["coordination_score_eligible"]]
    check("ineligible pairs have a null coordination_score",
          ineligible["coordination_score"].isna().all())
    check("ineligible pairs have a null opportunity_rank",
          ineligible["opportunity_rank"].isna().all())
    check("ineligible pairs are still present, not dropped", len(ineligible) > 0)
    check("ineligible pairs are always INSUFFICIENT confidence",
          (ineligible["score_confidence"] == "INSUFFICIENT").all())

    eligible = scored[scored["coordination_score_eligible"]]
    check("every eligible pair has a coordination_score", eligible["coordination_score"].notna().all())
    check("every eligible pair has an opportunity_rank", eligible["opportunity_rank"].notna().all())
    check("opportunity ranks are unique among eligible pairs",
          eligible["opportunity_rank"].is_unique)
    check("ranks form a contiguous 1..N sequence",
          sorted(eligible["opportunity_rank"]) == list(range(1, len(eligible) + 1)))

    for field in ("project_a_project_source", "project_b_project_source", "project_a_source_url"):
        if field in similarity.columns:
            check(f"{field} survived from earlier tasks", field in scored.columns)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
