"""Configurable coordination-opportunity score.

Weights default to geographic 40%, schedule 30%, project 20%, and
infrastructure 10%. Components that cannot be measured are omitted and the
remaining weights are renormalized. They are not replaced with zero.

Project similarity blends project type with text similarity only when text
exists. Infrastructure similarity blends voltage and status the same way.
Cost similarity is reported elsewhere and never enters this score.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.config import SCORE_INTERPRETATION, Settings

ComponentName = Literal[
    "geographic_proximity",
    "schedule_overlap",
    "project_similarity",
    "infrastructure_similarity",
]

_COMPONENT_ORDER: tuple[ComponentName, ...] = (
    "geographic_proximity",
    "schedule_overlap",
    "project_similarity",
    "infrastructure_similarity",
)


@dataclass(frozen=True)
class ScoreInputs:
    distance_similarity: float | None
    schedule_similarity: float | None
    project_type_similarity: float | None
    voltage_similarity: float | None
    status_similarity: float | None
    text_similarity: float | None


@dataclass(frozen=True)
class ComponentResult:
    name: ComponentName
    value: float | None
    base_weight: float
    effective_weight: float
    available: bool
    features_used: tuple[str, ...]


@dataclass(frozen=True)
class ScoreResult:
    coordination_score: float | None
    score_interpretation: str
    components: tuple[ComponentResult, ...]
    features_used: tuple[str, ...]
    reasons: tuple[str, ...]
    evidence_gaps: tuple[str, ...]
    project_similarity: float | None
    infrastructure_similarity: float | None

    @property
    def base_weights(self) -> dict[str, float]:
        return {component.name: component.base_weight for component in self.components}

    @property
    def effective_weights(self) -> dict[str, float]:
        return {component.name: component.effective_weight for component in self.components}


def coordination_score(inputs: ScoreInputs, settings: Settings) -> ScoreResult:
    project_value, project_features = _blend(
        (
            (
                settings.project_type_share,
                inputs.project_type_similarity,
                "project_type_similarity",
            ),
            (settings.project_text_share, inputs.text_similarity, "text_similarity"),
        )
    )
    infrastructure_value, infrastructure_features = _blend(
        (
            (
                settings.infrastructure_voltage_share,
                inputs.voltage_similarity,
                "voltage_similarity",
            ),
            (
                settings.infrastructure_status_share,
                inputs.status_similarity,
                "status_similarity",
            ),
        )
    )
    raw_components = {
        "geographic_proximity": (inputs.distance_similarity, ("distance_similarity",)),
        "schedule_overlap": (inputs.schedule_similarity, ("schedule_similarity",)),
        "project_similarity": (project_value, project_features),
        "infrastructure_similarity": (infrastructure_value, infrastructure_features),
    }
    base_weights = settings.base_weights()
    available_weight = sum(
        base_weights[name] for name, (value, _) in raw_components.items() if value is not None
    )
    components: list[ComponentResult] = []
    weighted_sum = Decimal("0")
    features: list[str] = []
    for name in _COMPONENT_ORDER:
        value, used = raw_components[name]
        base_weight = base_weights[name]
        available = value is not None
        if available and available_weight > 0:
            effective = base_weight / available_weight
            weighted_sum += effective * _decimal(value)
            features.extend(used)
        else:
            effective = Decimal("0")
        components.append(
            ComponentResult(
                name=name,
                value=None if value is None else float(_decimal(value)),
                base_weight=float(base_weight),
                effective_weight=float(
                    effective.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                ),
                available=available,
                features_used=used if available else (),
            )
        )
    score: float | None
    reasons: tuple[str, ...]
    gaps: tuple[str, ...]
    if available_weight == 0:
        score = None
        reasons = (
            "The coordination score was not calculated because geographic, schedule, "
            "project, and infrastructure evidence are all unavailable.",
        )
        gaps = (
            "No core evidence was available, so the score is null rather than zero.",
        )
    else:
        hundred = (weighted_sum * Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        score = float(hundred)
        reasons_list = [
            _component_reason(component) for component in components if component.available
        ]
        gaps_list: list[str] = []
        excluded = [component.name for component in components if not component.available]
        if excluded:
            names = ", ".join(excluded)
            gaps_list.append(
                f"{names} could not be measured, so those weights were removed and the "
                "remaining weights were renormalized. Missing evidence was not treated as zero."
            )
        reasons = tuple(reasons_list)
        gaps = tuple(gaps_list)
    return ScoreResult(
        coordination_score=score,
        score_interpretation=SCORE_INTERPRETATION,
        components=tuple(components),
        features_used=tuple(features),
        reasons=reasons,
        evidence_gaps=gaps,
        project_similarity=project_value,
        infrastructure_similarity=infrastructure_value,
    )


def _blend(
    parts: tuple[tuple[Decimal, float | None, str], ...],
) -> tuple[float | None, tuple[str, ...]]:
    present = [(weight, value, name) for weight, value, name in parts if value is not None]
    if not present:
        return None, ()
    weight_sum = sum((weight for weight, _, _ in present), Decimal("0"))
    if weight_sum == 0:
        return None, ()
    blended = sum(
        ((weight / weight_sum) * _decimal(value) for weight, value, _ in present),
        Decimal("0"),
    )
    return float(blended), tuple(name for _, _, name in present)


def _component_reason(component: ComponentResult) -> str:
    value = component.value
    if value is None:
        raise ValueError("an available score component is missing its similarity")
    label = component.name.replace("_", " ")
    return (
        f"{label.capitalize()} contributed similarity {value:.2f} "
        f"at a base weight of {component.base_weight:.0%} "
        f"(effective weight {component.effective_weight:.0%} after available evidence)."
    )


def _decimal(value: float | None) -> Decimal:
    if value is None:
        raise ValueError("cannot convert missing similarity to a number")
    return Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
