"""Cross-utility pair generation.

Duke projects are compared with TECO projects. A utility is never compared
with itself.
"""

from __future__ import annotations

import re

from app.errors import SameUtilityError, UnknownUtilityError
from app.models import Project

_ALIASES = {
    "duke": "Duke Energy Florida",
    "duke energy florida": "Duke Energy Florida",
    "teco": "Tampa Electric",
    "tampa electric": "Tampa Electric",
    "tampa electric / teco": "Tampa Electric",
}


def utility_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")


def canonicalize_utility(name: str, known: set[str]) -> str:
    cleaned = " ".join(name.split())
    for candidate in known:
        if candidate == cleaned or candidate.casefold() == cleaned.casefold():
            return candidate
    alias = _ALIASES.get(cleaned.casefold())
    if alias is not None:
        for candidate in known:
            if candidate.casefold() == alias.casefold():
                return candidate
        return alias
    return cleaned


def opportunity_id(project_a: Project, project_b: Project) -> str:
    """Stable id that does not change if the request swaps utility order."""
    first, second = sorted(
        (project_a, project_b),
        key=lambda project: (project.utility.casefold(), project.id),
    )
    return (
        f"{utility_slug(first.utility)}:{first.id}__{utility_slug(second.utility)}:{second.id}"
    )


def parse_opportunity_id(opportunity_id_value: str) -> tuple[str, str]:
    parts = opportunity_id_value.split("__")
    if len(parts) != 2:
        raise ValueError("opportunity id must contain two project references")
    return _project_id(parts[0]), _project_id(parts[1])


def generate_cross_pairs(
    projects: list[Project],
    utility_a: str,
    utility_b: str,
) -> list[tuple[Project, Project]]:
    known = {project.utility for project in projects}
    left_name = canonicalize_utility(utility_a, known)
    right_name = canonicalize_utility(utility_b, known)
    if left_name.casefold() == right_name.casefold():
        raise SameUtilityError("GridSync only compares projects from different utilities.")
    left = [project for project in projects if project.utility == left_name]
    right = [project for project in projects if project.utility == right_name]
    missing = [
        name
        for name, group in ((left_name, left), (right_name, right))
        if not group
    ]
    if missing:
        available = ", ".join(sorted(known)) or "none"
        raise UnknownUtilityError(
            f"Unknown utility: {', '.join(missing)}. Loaded utilities: {available}."
        )
    return [(project_a, project_b) for project_a in left for project_b in right]


def _project_id(reference: str) -> str:
    pieces = reference.split(":", 1)
    if len(pieces) != 2 or not pieces[1]:
        raise ValueError("opportunity id is missing a project id")
    return pieces[1]
