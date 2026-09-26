"""Cross-utility pairing only."""

from __future__ import annotations

import pytest

from app.errors import SameUtilityError, UnknownUtilityError
from app.fixtures import DUKE, TECO
from app.pairing import generate_cross_pairs, opportunity_id
from tests.helpers import make_project


def test_pairs_are_only_cross_utility() -> None:
    projects = [
        make_project(id="DUKE-DEMO-1"),
        make_project(id="DUKE-DEMO-2", project_name="DEMO second"),
        make_project(id="TECO-DEMO-1", utility=TECO),
        make_project(id="OTHER-DEMO-1", utility="Other Utility"),
    ]
    pairs = generate_cross_pairs(projects, DUKE, TECO)
    assert len(pairs) == 2
    assert all(left.utility != right.utility for left, right in pairs)
    assert {right.id for _, right in pairs} == {"TECO-DEMO-1"}


def test_same_utility_is_rejected() -> None:
    projects = [make_project(id="DUKE-DEMO-1"), make_project(id="DUKE-DEMO-2")]
    with pytest.raises(SameUtilityError):
        generate_cross_pairs(projects, DUKE, "duke")


def test_unknown_utility_is_rejected() -> None:
    with pytest.raises(UnknownUtilityError):
        generate_cross_pairs([make_project()], DUKE, "Missing Utility")


def test_opportunity_id_is_stable_when_order_changes() -> None:
    duke = make_project(id="DUKE-DEMO-1")
    teco = make_project(id="TECO-DEMO-1", utility=TECO)
    assert opportunity_id(duke, teco) == opportunity_id(teco, duke)
    assert opportunity_id(duke, teco) == (
        "duke-energy-florida:DUKE-DEMO-1__tampa-electric:TECO-DEMO-1"
    )
