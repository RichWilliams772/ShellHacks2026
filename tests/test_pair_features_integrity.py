# Aaron Green
# Confirms Task 3's output didn't quietly change or corrupt what Task 2 built.

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "processed" / "duke_teco_candidate_pairs.csv"
FEATURES = ROOT / "data" / "processed" / "duke_teco_pair_features.csv"

# Fields that must be byte-identical between Task 2's output and Task 3's
# output - Task 3 only adds columns, it never edits an existing one.
CARRIED_FROM_TASK_2 = [
    "pair_id", "project_a_id", "project_b_id", "project_a_name", "project_b_name",
    "project_a_from_lat", "project_a_from_lon", "project_b_from_lat",
    "project_b_from_lon", "project_a_location_confidence",
    "project_b_location_confidence",
]

# Columns Task 4/5/6 own. If any of these appear, Task 3 has overstepped.
FORBIDDEN_LATER_TASK_COLUMNS = [
    "text_similarity", "cosine_similarity", "infrastructure_similarity",
    "coordination_score", "shared_resources", "opportunity_rank", "rank",
]

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def main():
    candidates = pd.read_csv(CANDIDATES)
    features = pd.read_csv(FEATURES)

    check("pair count is unchanged from Task 2",
          len(features) == len(candidates), f"{len(features)} vs {len(candidates)}")
    check("pair ids are still unique", features["pair_id"].is_unique)
    check("the set of pair ids is identical to Task 2's",
          set(features["pair_id"]) == set(candidates["pair_id"]))

    merged = candidates.merge(features, on="pair_id", suffixes=("_task2", "_task3"))
    for field in CARRIED_FROM_TASK_2:
        left, right = f"{field}_task2", f"{field}_task3"
        if left not in merged.columns:
            # field had no naming collision (only one copy) - compare directly
            check(f"{field} is unchanged from Task 2", features[field].equals(candidates[field]))
            continue
        unchanged = (merged[left] == merged[right]) | (merged[left].isna() & merged[right].isna())
        check(f"{field} is unchanged from Task 2", unchanged.all(),
              f"{(~unchanged).sum()} rows differ")

    check("project ids are still unique per row",
          not features[["project_a_id", "project_b_id"]].duplicated().any())

    numeric_new = ["minimum_endpoint_distance_miles", "geographic_score",
                  "schedule_overlap_months", "year_difference", "temporal_score"]
    zero_when_unavailable = features[~features["geography_available"]]
    check("distance is null (not 0) when geography is unavailable",
          zero_when_unavailable["minimum_endpoint_distance_miles"].isna().all())
    check("geographic_score is null (not 0) when geography is unavailable",
          zero_when_unavailable["geographic_score"].isna().all())

    zero_when_no_temporal = features[~features["temporal_data_available"]]
    check("temporal_score is null (not 0) when temporal data is unavailable",
          zero_when_no_temporal["temporal_score"].isna().all())
    check("year_difference is null (not 0) when temporal data is unavailable",
          zero_when_no_temporal["year_difference"].isna().all())

    present = [c for c in FORBIDDEN_LATER_TASK_COLUMNS if c in features.columns]
    check("no Task 4/5/6 columns were accidentally created", not present, str(present))

    for field in ("project_a_project_source", "project_a_source_url"):
        if field in candidates.columns:
            check(f"{field} survived from earlier tasks", field in features.columns)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
