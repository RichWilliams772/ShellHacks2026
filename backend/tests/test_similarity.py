"""Project, voltage, and text similarity."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.similarity import (
    compare_projects,
    project_type_similarity,
    text_similarity,
    voltage_similarity,
)
from tests.helpers import make_project

SETTINGS = Settings()
SIMILAR = "Reconductor existing 230 kV transmission corridor."
RELATED = "Replace conductors along existing 230 kV transmission line."
UNRELATED = "Migrate the customer billing portal and account software."


def test_project_type_and_voltage_similarity() -> None:
    assert project_type_similarity("transmission_upgrade", "transmission_upgrade") == 1
    assert project_type_similarity("transmission_upgrade", "reconductoring") == 0.5
    assert project_type_similarity("transmission_upgrade", "undergrounding") == 0
    assert project_type_similarity("transmission_upgrade", None) is None
    assert voltage_similarity(230, 230) == 1
    assert voltage_similarity(230, 115) == 0.5
    assert voltage_similarity(230, None) is None
    assert voltage_similarity(None, None) is None


def test_similar_descriptions_score_higher_than_unrelated_text() -> None:
    similar = text_similarity(SIMILAR, RELATED, min_tokens=3)
    unrelated = text_similarity(SIMILAR, UNRELATED, min_tokens=3)
    identical = text_similarity(SIMILAR, SIMILAR, min_tokens=3)
    assert similar is not None
    assert unrelated is not None
    assert identical == pytest.approx(1)
    assert similar > unrelated


def test_missing_description_skips_text_similarity() -> None:
    left = make_project(description=None)
    right = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        description=None,
    )
    result = compare_projects(left, right, SETTINGS)
    assert result.text_similarity is None
    assert any("not treated as zero" in gap for gap in result.evidence_gaps)


def test_missing_voltage_does_not_become_zero() -> None:
    result = compare_projects(
        make_project(voltage_kv=None),
        make_project(id="TECO-DEMO-B", utility="Tampa Electric", voltage_kv=230),
        SETTINGS,
    )
    assert result.voltage_similarity is None
    assert result.voltage_similarity != 0
