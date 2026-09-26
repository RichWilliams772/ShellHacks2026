"""Missing optional values do not crash analysis or become zero."""

from __future__ import annotations

from app.analysis import analyze_pair
from app.config import Settings
from app.fixtures import TECO
from tests.helpers import make_project

SETTINGS = Settings()


def test_empty_projects_still_produce_an_opportunity() -> None:
    left = make_project(
        id="DUKE-DEMO-EMPTY",
        project_type=None,
        description=None,
        voltage_kv=None,
        latitude=None,
        longitude=None,
        start_date=None,
        end_date=None,
        status=None,
        capital_cost=None,
    )
    right = make_project(
        id="TECO-DEMO-EMPTY",
        utility=TECO,
        project_type=None,
        description=None,
        voltage_kv=None,
        latitude=None,
        longitude=None,
        start_date=None,
        end_date=None,
        status=None,
        capital_cost=None,
    )
    opportunity = analyze_pair(left, right, SETTINGS)
    assert opportunity.coordination_score is None
    assert opportunity.features.distance_miles is None
    assert opportunity.features.schedule_overlap_months is None
    assert opportunity.features.text_similarity is None
    assert opportunity.features.voltage_similarity is None
    assert opportunity.features.cost_similarity is None
    assert opportunity.evidence_gaps
    assert opportunity.data_type == "demo"


def test_scores_repeat_and_ignore_missing_cost() -> None:
    base_left = make_project(id="DUKE-DEMO-COST")
    base_right = make_project(id="TECO-DEMO-COST", utility=TECO)
    with_cost_left = make_project(id="DUKE-DEMO-COST", capital_cost=1_000_000)
    with_cost_right = make_project(id="TECO-DEMO-COST", utility=TECO, capital_cost=2_000_000)
    first = analyze_pair(base_left, base_right, SETTINGS)
    second = analyze_pair(base_left, base_right, SETTINGS)
    priced = analyze_pair(with_cost_left, with_cost_right, SETTINGS)
    assert first.coordination_score == second.coordination_score
    assert first.id == second.id
    assert priced.coordination_score == first.coordination_score
    assert priced.features.cost_similarity is not None
    assert "cost_similarity" not in priced.features_used
    swapped = analyze_pair(base_right, base_left, SETTINGS)
    assert swapped.coordination_score == first.coordination_score
    assert swapped.id == first.id
