# Aaron Green
# Builds the final Coordination Package per opportunity and the one function the backend calls.

import json
import math
from pathlib import Path

import pandas as pd

from analysis.resource_rules import build_shared_resources

ROOT = Path(__file__).resolve().parents[1]
SCORED_CSV = ROOT / "data" / "processed" / "duke_teco_scored_opportunities.csv"
PACKAGES_JSON = ROOT / "data" / "processed" / "gridsync_opportunities.json"


def clean(value):
    """NaN/None -> None. JSON has no NaN literal, so this must happen before dumping."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _project_view(row, side):
    prefix = f"project_{side}_"
    return {
        "id": clean(row[f"{prefix}id"]),
        "utility": clean(row[f"{prefix}utility"]),
        "name": clean(row[f"{prefix}name"]),
        "project_type": clean(row[f"{prefix}type"]),
        "voltage_label": clean(row.get(f"{prefix}voltage_label")),
    }


def build_opportunity_evidence(row):
    """Task 5's own evidence column, split and deduplicated - not regenerated.

    Task 5 already produced these sentences from real Task 3/4 fields; Task 6's
    job is to package them, not recompute or embellish them.
    """
    raw = clean(row.get("evidence"))
    if not raw:
        return []
    seen, evidence = set(), []
    for sentence in raw.split(" | "):
        sentence = sentence.strip()
        if sentence and sentence not in seen:
            seen.add(sentence)
            evidence.append(sentence)
    return evidence


def build_coordination_package(row):
    """One eligible pair -> one structured, JSON-serializable opportunity object.

    Every number here is read from Task 3/4/5 output as-is. Nothing is
    recalculated: not distance, not schedule overlap, not similarity, not the
    Coordination Score, not the rank.
    """
    project_a, project_b = _project_view(row, "a"), _project_view(row, "b")

    resources = build_shared_resources(
        project_a["project_type"], project_b["project_type"],
        clean(row.get("project_type_similarity")), clean(row.get("voltage_similarity")),
        project_a["voltage_label"], project_b["voltage_label"])

    return {
        "opportunity_id": row["pair_id"],
        "project_a": project_a,
        "project_b": project_b,
        "analysis": {
            "distance_miles": clean(row.get("minimum_endpoint_distance_miles")),
            "geography_available": bool(row.get("geography_available")),
            "schedule_overlap_months": clean(row.get("schedule_overlap_months")),
            "temporal_precision": clean(row.get("temporal_precision")),
            "geographic_score": clean(row.get("geographic_score")),
            "temporal_score": clean(row.get("temporal_score")),
            "text_similarity_score": clean(row.get("text_similarity_score")),
            "infrastructure_similarity": clean(row.get("infrastructure_similarity")),
            "coordination_score": clean(row.get("coordination_score")),
            "score_confidence": clean(row.get("score_confidence")),
            "opportunity_rank": int(row["opportunity_rank"]),
        },
        "evidence": build_opportunity_evidence(row),
        "potential_shared_resources": resources,
        # Carries forward the categorical evidence-quality fields Tasks 1-5
        # already produced. Nothing here is a new statistical confidence -
        # "temporal" uses Task 3's own precision vocabulary (mixed/unknown),
        # which is intentionally a different vocabulary than the HIGH/MEDIUM/
        # UNKNOWN used for geography and similarity; forcing them into one
        # shared vocabulary would either lose information or invent a mapping
        # nobody asked for.
        "data_confidence": {
            "geography": clean(row.get("pair_geography_confidence")),
            "temporal": clean(row.get("temporal_precision")),
            "similarity": clean(row.get("similarity_confidence")),
            "overall_score": clean(row.get("score_confidence")),
        },
    }


def build_all_packages(scored):
    """Coordination Packages for every score-eligible pair, already in rank order."""
    eligible = scored[scored["coordination_score_eligible"]].sort_values("opportunity_rank")
    return [build_coordination_package(row) for row in eligible.to_dict("records")]


def _matches_utility_pair(row, utility_a, utility_b):
    pair = {row["project_a_utility"], row["project_b_utility"]}
    return pair == {utility_a, utility_b}


def analyze_projects(utility_a, utility_b, min_score=None, top_n=None):
    """The one function a backend needs. No pandas, no TF-IDF, no CSV
    structure, no resource-rule internals required to call this.

    Returns precomputed results - the pipeline does not rerun on every call
    (PROJECT_SPEC section 37: precomputed analysis is acceptable for the
    hackathon). An unrecognized utility pair returns an empty, valid result
    rather than raising - this is decision support, not a strict API.
    """
    scored = pd.read_csv(SCORED_CSV)
    with PACKAGES_JSON.open() as handle:
        all_packages = json.load(handle)

    scope = scored[scored.apply(lambda r: _matches_utility_pair(r, utility_a, utility_b), axis=1)]
    opportunities = [p for p in all_packages
                     if {p["project_a"]["utility"], p["project_b"]["utility"]} == {utility_a, utility_b}]

    if min_score is not None:
        opportunities = [o for o in opportunities if o["analysis"]["coordination_score"] >= min_score]
    opportunities.sort(key=lambda o: o["analysis"]["opportunity_rank"])
    if top_n is not None:
        opportunities = opportunities[:top_n]

    projects_analyzed = len(set(scope["project_a_id"]) | set(scope["project_b_id"])) if len(scope) else 0

    return {
        "summary": {
            "utilities": sorted({utility_a, utility_b}),
            "projects_analyzed": projects_analyzed,
            "pairs_analyzed": int(len(scope)),
            "eligible_opportunities": int(scope["coordination_score_eligible"].sum()) if len(scope) else 0,
            "opportunities_returned": len(opportunities),
        },
        "opportunities": opportunities,
    }
