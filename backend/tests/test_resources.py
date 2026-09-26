"""Deterministic resource intersections and strength rules."""

from __future__ import annotations

from app.config import Settings
from app.resources import (
    RESOURCE_RULES,
    ResourceEvidence,
    coordination_package,
    shared_resource_names,
)

SETTINGS = Settings()


def test_known_project_types_intersect_expected_resources() -> None:
    assert shared_resource_names("transmission_upgrade", "substation_upgrade") == (
        "outage_planning",
    )
    assert shared_resource_names("transmission_upgrade", "transmission_line") == tuple(
        sorted(RESOURCE_RULES["transmission_upgrade"])
    )
    assert shared_resource_names("undergrounding", "transmission_upgrade") == (
        "material_logistics",
    )
    assert shared_resource_names(None, "transmission_upgrade") == ()
    assert shared_resource_names("not_a_real_type", "transmission_upgrade") == ()


def test_strength_uses_three_configured_conditions() -> None:
    high = coordination_package(
        "transmission_upgrade",
        "transmission_upgrade",
        ResourceEvidence(1, 10, 0.5, "day"),
        SETTINGS,
    )
    assert high.shared_resources
    assert {item.strength for item in high.shared_resources} == {"HIGH"}

    medium = coordination_package(
        "transmission_upgrade",
        "transmission_upgrade",
        ResourceEvidence(1, None, 0.5, "year"),
        SETTINGS,
    )
    assert {item.strength for item in medium.shared_resources} == {"MEDIUM"}
    assert "year-level" in medium.shared_resources[0].reason

    low = coordination_package(
        "transmission_upgrade",
        "transmission_upgrade",
        ResourceEvidence(1, 80, 0, "day"),
        SETTINGS,
    )
    assert {item.strength for item in low.shared_resources} == {"LOW"}


def test_distance_threshold_is_exclusive() -> None:
    at_threshold = coordination_package(
        "substation_upgrade",
        "substation_upgrade",
        ResourceEvidence(1, 25, 0.25, "day"),
        SETTINGS,
    )
    assert at_threshold.shared_resources[0].strength == "MEDIUM"
    under_threshold = coordination_package(
        "substation_upgrade",
        "substation_upgrade",
        ResourceEvidence(1, 24.9, 0.25, "day"),
        SETTINGS,
    )
    assert under_threshold.shared_resources[0].strength == "HIGH"
