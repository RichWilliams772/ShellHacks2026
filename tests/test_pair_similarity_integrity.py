# Aaron Green
# Confirms Task 4's output didn't quietly change or corrupt what Task 3 built.

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "data" / "processed" / "duke_teco_pair_features.csv"
SIMILARITY = ROOT / "data" / "processed" / "duke_teco_pair_similarity.csv"

# Every Task 3 column must survive into Task 4's output unchanged. Geographic
# and temporal fields are the ones a scoring bug would most plausibly corrupt.
CARRIED_FROM_TASK_3 = [
    "pair_id", "project_a_id", "project_b_id",
    "minimum_endpoint_distance_miles", "geographic_score",
    "pair_geography_confidence", "temporal_score", "temporal_precision",
    "year_difference", "geography_available", "temporal_data_available",
]

# Columns Task 5/6 own. If any of these appear, Task 4 has overstepped.
FORBIDDEN_LATER_TASK_COLUMNS = [
    "coordination_score", "opportunity_rank", "rank", "shared_resources",
    "coordination_package",
]

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def main():
    features = pd.read_csv(FEATURES)
    similarity = pd.read_csv(SIMILARITY)

    check("pair count is unchanged from Task 3",
          len(similarity) == len(features), f"{len(similarity)} vs {len(features)}")
    check("pair ids are still unique", similarity["pair_id"].is_unique)
    check("the set of pair ids is identical to Task 3's",
          set(similarity["pair_id"]) == set(features["pair_id"]))

    merged = features.merge(similarity, on="pair_id", suffixes=("_task3", "_task4"))
    for field in CARRIED_FROM_TASK_3:
        left, right = f"{field}_task3", f"{field}_task4"
        if left not in merged.columns:
            check(f"{field} is unchanged from Task 3", similarity[field].equals(features[field]))
            continue
        unchanged = (merged[left] == merged[right]) | (merged[left].isna() & merged[right].isna())
        check(f"{field} is unchanged from Task 3", unchanged.all(),
              f"{(~unchanged).sum()} rows differ")

    present = [c for c in FORBIDDEN_LATER_TASK_COLUMNS if c in similarity.columns]
    check("no Task 5/6 columns were accidentally created", not present, str(present))

    # "label" alone is too broad a substring - project_a_voltage_label is a
    # legitimate carried-through field ("138/230 kV"), not an ML artifact.
    check("no supervised model artifact columns exist",
          not any(c.startswith(("predicted_", "probability_", "ml_label"))
                  or c in ("prediction", "class_label")
                  for c in similarity.columns))

    # Missing must stay missing here too.
    no_text = similarity[~similarity["text_similarity_available"]]
    check("text_similarity_score is null (not 0) when text is unavailable",
          no_text["text_similarity_score"].isna().all())
    no_infra = similarity[~similarity["infrastructure_similarity_available"]]
    check("infrastructure_similarity is null (not 0) when unavailable",
          no_infra["infrastructure_similarity"].isna().all())

    for field in ("project_a_project_source", "project_a_source_url"):
        if field in features.columns:
            check(f"{field} survived from earlier tasks", field in similarity.columns)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
