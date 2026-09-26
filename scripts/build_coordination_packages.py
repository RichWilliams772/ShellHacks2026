# Aaron Green
# Writes the final Coordination Packages and sanity-checks them - the last step of the pipeline.

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.pipeline import PACKAGES_JSON, SCORED_CSV, analyze_projects, build_all_packages  # noqa: E402


def summarize(packages, scored):
    eligible_count = int(scored["coordination_score_eligible"].sum())
    print("=" * 70)
    print("TASK 6 VALIDATION REPORT")
    print("=" * 70)
    print(f"total scored pairs (Task 5):      {len(scored)}")
    print(f"eligible opportunities:           {eligible_count}")
    print(f"packages produced:                {len(packages)}")

    with_resources = [p for p in packages if p["potential_shared_resources"]]
    without_resources = [p for p in packages if not p["potential_shared_resources"]]
    print(f"opportunities with resources:     {len(with_resources)}")
    print(f"opportunities without resources:  {len(without_resources)}")

    all_resource_ids = {r["resource_id"] for p in packages for r in p["potential_shared_resources"]}
    print(f"distinct resource categories used: {sorted(all_resource_ids)}")

    potential_counts = {}
    for p in packages:
        for r in p["potential_shared_resources"]:
            potential_counts[r["potential"]] = potential_counts.get(r["potential"], 0) + 1
    print(f"resource potential distribution:  {potential_counts}")
    print("=" * 70)


def print_top(packages, n=5):
    print(f"\nVALIDATION - top {n} Coordination Packages:")
    for p in packages[:n]:
        a = p["analysis"]
        print(f"\n  #{a['opportunity_rank']}  {p['opportunity_id']}  "
              f"score={a['coordination_score']}  confidence={a['score_confidence']}")
        print(f"      {p['project_a']['name'][:40]:<40} <-> {p['project_b']['name']}")
        print(f"      distance={a['distance_miles']}mi  geo={a['geographic_score']} "
              f"temporal={a['temporal_score']} text={a['text_similarity_score']} "
              f"infra={a['infrastructure_similarity']}")
        print(f"      evidence: {p['evidence']}")
        if p["potential_shared_resources"]:
            print("      potential shared resources:")
            for r in p["potential_shared_resources"]:
                print(f"        [{r['potential']:<6}] {r['display_name']}: {r['evidence']}")
        else:
            print("      potential shared resources: none (project types share no common category)")


def print_edge_cases(packages):
    print("\nVALIDATION - edge cases:")

    low_score = min(packages, key=lambda p: p["analysis"]["coordination_score"])
    print(f"  lowest-scoring eligible package: {low_score['opportunity_id']} "
          f"score={low_score['analysis']['coordination_score']} "
          f"resources={[r['resource_id'] for r in low_score['potential_shared_resources']]}")

    no_resources = [p for p in packages if not p["potential_shared_resources"]]
    if no_resources:
        p = no_resources[0]
        print(f"  no-shared-resource example: {p['opportunity_id']} "
              f"({p['project_a']['project_type']} vs {p['project_b']['project_type']})")

    medium_confidence = [p for p in packages if p["analysis"]["score_confidence"] == "MEDIUM"]
    if medium_confidence:
        p = medium_confidence[0]
        print(f"  MEDIUM-confidence example: {p['opportunity_id']} "
              f"score={p['analysis']['coordination_score']} "
              f"resources={[r['resource_id'] for r in p['potential_shared_resources']]}")

    cross_type = [p for p in packages if p["project_a"]["project_type"] != p["project_b"]["project_type"]]
    if cross_type:
        p = cross_type[0]
        print(f"  cross-project-type example: {p['opportunity_id']} "
              f"({p['project_a']['project_type']} vs {p['project_b']['project_type']}) "
              f"resources={[r['resource_id'] for r in p['potential_shared_resources']]}")


def verify_no_score_drift(packages, scored):
    """The most important integrity check: Task 6 must not have touched Task 5's numbers."""
    by_id = scored.set_index("pair_id")
    problems = []
    for p in packages:
        row = by_id.loc[p["opportunity_id"]]
        if p["analysis"]["coordination_score"] != row["coordination_score"]:
            problems.append(p["opportunity_id"])
        if p["analysis"]["opportunity_rank"] != row["opportunity_rank"]:
            problems.append(p["opportunity_id"])
    if problems:
        raise SystemExit(f"Coordination Score or rank drifted from Task 5 for: {problems}")
    print("\nverified: every package's score and rank match Task 5 exactly")


def demo_interface_call():
    print("\nVALIDATION - analyze_projects() interface check:")
    result = analyze_projects("Duke Energy Florida", "Tampa Electric", top_n=3)
    print(f"  summary: {result['summary']}")
    print(f"  opportunities returned: {len(result['opportunities'])}")
    json.dumps(result)  # raises if not JSON-serializable
    print("  JSON-serializable: yes")

    empty = analyze_projects("Duke Energy Florida", "Some Unknown Utility")
    print(f"  unsupported utility pair -> {empty['summary']} (no exception raised)")


def main():
    scored = pd.read_csv(SCORED_CSV)
    packages = build_all_packages(scored)

    PACKAGES_JSON.parent.mkdir(parents=True, exist_ok=True)
    with PACKAGES_JSON.open("w") as handle:
        json.dump(packages, handle, indent=2)
    print(f"wrote {len(packages)} Coordination Packages to {PACKAGES_JSON.relative_to(ROOT)}\n")

    summarize(packages, scored)
    print_top(packages)
    print_edge_cases(packages)
    verify_no_score_drift(packages, scored)
    demo_interface_call()
    return 0


if __name__ == "__main__":
    sys.exit(main())
