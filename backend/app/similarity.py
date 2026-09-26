"""Project, voltage, status, and optional text similarity.

Missing values stay null. Text similarity runs only when both projects have a
description with enough tokens, using TF-IDF cosine similarity on that pair.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import Settings
from app.models import Project

_TOKEN = re.compile(r"[A-Za-z0-9]+")

_FAMILIES: dict[str, str] = {
    "transmission_upgrade": "transmission",
    "transmission_line": "transmission",
    "reconductoring": "transmission",
    "substation_upgrade": "substation",
    "substation": "substation",
    "undergrounding": "underground",
    "hardening": "hardening",
    "storm_hardening": "hardening",
    "distribution_upgrade": "distribution",
}


@dataclass(frozen=True)
class SimilarityComparison:
    project_type_similarity: float | None
    voltage_similarity: float | None
    status_similarity: float | None
    text_similarity: float | None
    cost_similarity: float | None
    reasons: tuple[str, ...]
    evidence_gaps: tuple[str, ...]


def normalize_label(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().casefold().replace("-", "_").replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or None


def family_of(project_type: str | None) -> str | None:
    normalized = normalize_label(project_type)
    if normalized is None:
        return None
    return _FAMILIES.get(normalized, normalized)


def project_type_similarity(type_a: str | None, type_b: str | None) -> float | None:
    left = normalize_label(type_a)
    right = normalize_label(type_b)
    if left is None or right is None:
        return None
    if left == right:
        return 1.0
    if family_of(left) == family_of(right):
        return 0.5
    return 0.0


def voltage_similarity(voltage_a: float | None, voltage_b: float | None) -> float | None:
    if voltage_a is None or voltage_b is None:
        return None
    peak = max(voltage_a, voltage_b)
    if peak == 0:
        return 1.0 if voltage_a == voltage_b else 0.0
    return 1.0 - (abs(voltage_a - voltage_b) / peak)


def status_similarity(status_a: str | None, status_b: str | None) -> float | None:
    left = normalize_label(status_a)
    right = normalize_label(status_b)
    if left is None or right is None:
        return None
    return 1.0 if left == right else 0.0


def relative_similarity(value_a: float | None, value_b: float | None) -> float | None:
    """Shared optional numeric similarity. Missing values stay null."""
    return voltage_similarity(value_a, value_b)


def text_similarity(text_a: str | None, text_b: str | None, *, min_tokens: int) -> float | None:
    if not _enough_text(text_a, min_tokens) or not _enough_text(text_b, min_tokens):
        return None
    try:
        matrix = TfidfVectorizer().fit_transform([text_a, text_b])
        score = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except ValueError:
        return None
    return max(0.0, min(1.0, score))


def compare_projects(
    project_a: Project,
    project_b: Project,
    settings: Settings,
) -> SimilarityComparison:
    type_score = project_type_similarity(project_a.project_type, project_b.project_type)
    voltage_score = voltage_similarity(project_a.voltage_kv, project_b.voltage_kv)
    status_score = status_similarity(project_a.status, project_b.status)
    documents = (_document(project_a), _document(project_b))
    text_score = text_similarity(documents[0], documents[1], min_tokens=settings.min_text_tokens)
    cost_score = relative_similarity(project_a.capital_cost, project_b.capital_cost)
    reasons: list[str] = []
    gaps: list[str] = []

    if type_score is None:
        gaps.append(
            "Project type is missing for one or both projects; project-type similarity "
            "was not calculated and was not treated as zero."
        )
    elif type_score == 1:
        reasons.append(f"Both projects are {normalize_label(project_a.project_type)}.")
    elif type_score == 0.5:
        reasons.append(
            "Project types "
            f"{normalize_label(project_a.project_type)} and "
            f"{normalize_label(project_b.project_type)} are in the same infrastructure family."
        )
    else:
        reasons.append(
            "Project types differ "
            f"({normalize_label(project_a.project_type)} vs "
            f"{normalize_label(project_b.project_type)})."
        )

    if voltage_score is None:
        missing = [
            project.id
            for project in (project_a, project_b)
            if project.voltage_kv is None
        ]
        gaps.append(
            f"Voltage is unavailable for {', '.join(missing)}; voltage similarity was not "
            "calculated and was not treated as zero."
        )
    else:
        reasons.append(
            f"Voltage levels are {_kv(project_a.voltage_kv)} kV and {_kv(project_b.voltage_kv)} kV "
            f"(similarity {voltage_score:.2f})."
        )

    if status_score is None:
        gaps.append(
            "Status is missing for one or both projects; status similarity was not "
            "calculated and was not treated as zero."
        )
    elif status_score == 1:
        reasons.append(f"Both projects have status {normalize_label(project_a.status)}.")
    else:
        reasons.append(
            "Project statuses differ "
            f"({normalize_label(project_a.status)} vs {normalize_label(project_b.status)})."
        )

    if text_score is None:
        gaps.append(
            "Text similarity was not calculated because one or both descriptions are "
            "missing or too short. Missing text was not treated as zero similarity."
        )
    else:
        reasons.append(f"Project descriptions have text similarity {text_score:.2f}.")

    if cost_score is None:
        gaps.append(
            "Capital cost is unavailable for one or both projects; cost similarity was "
            "not calculated, was not treated as zero, and is not part of the score."
        )
    else:
        reasons.append(
            "Both projects report capital cost. Cost similarity is "
            f"{cost_score:.2f} and is not part of the coordination score."
        )

    return SimilarityComparison(
        project_type_similarity=type_score,
        voltage_similarity=voltage_score,
        status_similarity=status_score,
        text_similarity=text_score,
        cost_similarity=cost_score,
        reasons=tuple(reasons),
        evidence_gaps=tuple(gaps),
    )


def type_matches(project_type: str | None, requested: str) -> bool:
    normalized = normalize_label(project_type)
    requested_norm = normalize_label(requested)
    if normalized is None or requested_norm is None:
        return False
    if normalized == requested_norm:
        return True
    return family_of(normalized) == requested_norm


def _document(project: Project) -> str | None:
    if project.description is None or not project.description.strip():
        return None
    parts = [project.project_name, project.project_type or "", project.description]
    return " ".join(part.strip() for part in parts if part and part.strip())


def _enough_text(text: str | None, min_tokens: int) -> bool:
    if text is None or not text.strip():
        return False
    return len(_TOKEN.findall(text)) >= min_tokens


def _kv(value: float | None) -> str:
    if value is None:
        return "unknown"
    if float(value).is_integer():
        return str(int(value))
    return str(value)
