"""Repeatable scores and the 40/30/20/10 weights."""

from __future__ import annotations

from app.config import Settings
from app.scoring import ScoreInputs, coordination_score

SETTINGS = Settings()


def _inputs(**overrides: float | None) -> ScoreInputs:
    payload: dict[str, float | None] = {
        "distance_similarity": 1,
        "schedule_similarity": 1,
        "project_type_similarity": 1,
        "voltage_similarity": 1,
        "status_similarity": None,
        "text_similarity": None,
    }
    payload.update(overrides)
    return ScoreInputs(**payload)  # type: ignore[arg-type]


def test_weights_match_the_prototype_split() -> None:
    assert coordination_score(_inputs(), SETTINGS).coordination_score == 100
    assert (
        coordination_score(
            _inputs(
                schedule_similarity=0,
                project_type_similarity=0,
                voltage_similarity=0,
            ),
            SETTINGS,
        ).coordination_score
        == 40
    )
    assert (
        coordination_score(
            _inputs(
                distance_similarity=0,
                project_type_similarity=0,
                voltage_similarity=0,
            ),
            SETTINGS,
        ).coordination_score
        == 30
    )
    assert (
        coordination_score(
            _inputs(distance_similarity=0, schedule_similarity=0, voltage_similarity=0),
            SETTINGS,
        ).coordination_score
        == 20
    )
    assert (
        coordination_score(
            _inputs(
                distance_similarity=0,
                schedule_similarity=0,
                project_type_similarity=0,
            ),
            SETTINGS,
        ).coordination_score
        == 10
    )


def test_identical_inputs_repeat() -> None:
    inputs = ScoreInputs(0.91, 0.82, 1.0, 0.9, 0.4, 0.76)
    assert coordination_score(inputs, SETTINGS) == coordination_score(inputs, SETTINGS)


def test_missing_component_is_renormalized_instead_of_zero() -> None:
    score = coordination_score(
        _inputs(distance_similarity=None),
        SETTINGS,
    )
    assert score.coordination_score == 100
    assert any("not treated as zero" in gap for gap in score.evidence_gaps)


def test_missing_text_does_not_lower_project_similarity() -> None:
    without_text = coordination_score(_inputs(text_similarity=None), SETTINGS)
    with_low_text = coordination_score(_inputs(text_similarity=0), SETTINGS)
    assert without_text.project_similarity == 1
    assert with_low_text.project_similarity == 0.5
    assert without_text.coordination_score == 100
    assert with_low_text.coordination_score is not None
    assert with_low_text.coordination_score < 100


def test_all_missing_evidence_has_null_score() -> None:
    score = coordination_score(
        ScoreInputs(None, None, None, None, None, None),
        SETTINGS,
    )
    assert score.coordination_score is None
    assert "null rather than zero" in score.evidence_gaps[0]
