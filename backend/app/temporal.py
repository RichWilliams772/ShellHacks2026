"""Deterministic schedule overlap.

Full dates use inclusive day counts. If either project only has years, the
comparison stays at year precision and does not invent months or days.
A measured overlap of zero stays zero. A missing schedule stays null.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from app.models import Project

MONTH_DAYS = 365.25 / 12
TemporalPrecision = Literal["day", "year", "unavailable"]
OverlapKind = Literal["identical", "full", "partial", "none"]


@dataclass(frozen=True)
class TemporalComparison:
    precision: TemporalPrecision
    start_date_difference: int | None
    end_date_difference: int | None
    start_year_difference: int | None
    end_year_difference: int | None
    overlap_days: int | None
    schedule_overlap_months: float | None
    overlap_years: int | None
    overlapping_years: tuple[int, ...] | None
    schedule_overlap_ratio: float | None
    overlap_kind: OverlapKind | None
    reasons: tuple[str, ...]
    evidence_gaps: tuple[str, ...]

    @property
    def schedule_similarity(self) -> float | None:
        return self.schedule_overlap_ratio


def compare_schedules(project_a: Project, project_b: Project) -> TemporalComparison:
    """Compare schedules. Signed differences are project_b minus project_a."""
    window_a = _window(project_a)
    window_b = _window(project_b)
    if window_a is None or window_b is None:
        return TemporalComparison(
            precision="unavailable",
            start_date_difference=None,
            end_date_difference=None,
            start_year_difference=None,
            end_year_difference=None,
            overlap_days=None,
            schedule_overlap_months=None,
            overlap_years=None,
            overlapping_years=None,
            schedule_overlap_ratio=None,
            overlap_kind=None,
            reasons=(),
            evidence_gaps=(
                "Schedule overlap is unavailable because one or both projects lack both "
                "a start and an end. The missing schedule was not treated as zero overlap.",
            ),
        )
    if window_a.precision == "day" and window_b.precision == "day":
        return _compare_days(window_a, window_b)
    return _compare_years(window_a, window_b)


def active_years(project: Project) -> set[int] | None:
    """Years touched by a known schedule. None when either bound is missing."""
    window = _window(project)
    if window is None:
        return None
    return set(range(window.start_year, window.end_year + 1))


@dataclass(frozen=True)
class _Window:
    precision: Literal["day", "year"]
    start_year: int
    end_year: int
    start_date: date | None = None
    end_date: date | None = None


def _window(project: Project) -> _Window | None:
    if not project.start_date or not project.end_date:
        return None
    start_precision = _bound_precision(project.start_date)
    end_precision = _bound_precision(project.end_date)
    if start_precision is None or end_precision is None:
        return None
    start_year = int(project.start_date[:4])
    end_year = int(project.end_date[:4])
    if end_year < start_year:
        return None
    if start_precision == "day" and end_precision == "day":
        start_on = datetime.strptime(project.start_date, "%Y-%m-%d").date()
        end_on = datetime.strptime(project.end_date, "%Y-%m-%d").date()
        if end_on < start_on:
            return None
        return _Window("day", start_year, end_year, start_on, end_on)
    return _Window("year", start_year, end_year)


def _bound_precision(value: str) -> Literal["day", "year"] | None:
    if len(value) == 4 and value.isdigit():
        return "year"
    if len(value) == 10:
        return "day"
    return None


def _compare_days(window_a: _Window, window_b: _Window) -> TemporalComparison:
    start_a = window_a.start_date
    end_a = window_a.end_date
    start_b = window_b.start_date
    end_b = window_b.end_date
    if start_a is None or end_a is None or start_b is None or end_b is None:
        raise ValueError("day comparison requires concrete dates")
    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)
    if overlap_end < overlap_start:
        overlap_days = 0
        overlapping_years: tuple[int, ...] = ()
    else:
        overlap_days = (overlap_end - overlap_start).days + 1
        overlapping_years = tuple(range(overlap_start.year, overlap_end.year + 1))
    duration_a = (end_a - start_a).days + 1
    duration_b = (end_b - start_b).days + 1
    union_days = duration_a + duration_b - overlap_days
    ratio = overlap_days / union_days if union_days else None
    left_inside = start_a >= start_b and end_a <= end_b
    right_inside = start_b >= start_a and end_b <= end_a
    kind = _kind(
        same=start_a == start_b and end_a == end_b,
        contained=left_inside or right_inside,
        overlap=overlap_days > 0,
    )
    months = overlap_days / MONTH_DAYS
    if kind == "identical":
        reason = (
            f"Construction schedules are identical and overlap for {overlap_days} days "
            f"({months:.1f} months)."
        )
    elif kind == "none":
        reason = "Construction schedules do not overlap."
    else:
        reason = (
            f"Construction schedules overlap for {overlap_days} days "
            f"({months:.1f} months)."
        )
    return TemporalComparison(
        precision="day",
        start_date_difference=(start_b - start_a).days,
        end_date_difference=(end_b - end_a).days,
        start_year_difference=None,
        end_year_difference=None,
        overlap_days=overlap_days,
        schedule_overlap_months=months,
        overlap_years=None,
        overlapping_years=overlapping_years,
        schedule_overlap_ratio=ratio,
        overlap_kind=kind,
        reasons=(reason,),
        evidence_gaps=(),
    )


def _compare_years(window_a: _Window, window_b: _Window) -> TemporalComparison:
    years_a = set(range(window_a.start_year, window_a.end_year + 1))
    years_b = set(range(window_b.start_year, window_b.end_year + 1))
    shared = years_a & years_b
    union = years_a | years_b
    ratio = len(shared) / len(union) if union else None
    kind = _kind(
        same=years_a == years_b,
        contained=years_a <= years_b or years_b <= years_a,
        overlap=bool(shared),
    )
    overlapping_years = tuple(sorted(shared))
    year_count = len(overlapping_years)
    if kind == "none":
        reason = (
            "Construction periods do not overlap at year-level precision. "
            "Exact dates and months were not calculated."
        )
    else:
        noun = "year" if year_count == 1 else "years"
        reason = (
            f"Construction periods overlap for {year_count} {noun} at year-level precision. "
            "Exact dates and months were not calculated."
        )
    return TemporalComparison(
        precision="year",
        start_date_difference=None,
        end_date_difference=None,
        start_year_difference=window_b.start_year - window_a.start_year,
        end_year_difference=window_b.end_year - window_a.end_year,
        overlap_days=None,
        schedule_overlap_months=None,
        overlap_years=year_count,
        overlapping_years=overlapping_years,
        schedule_overlap_ratio=ratio,
        overlap_kind=kind,
        reasons=(reason,),
        evidence_gaps=(
            "At least one schedule has only a year, so overlap is reported in calendar "
            "years. Days and months were not fabricated.",
        ),
    )


def _kind(*, same: bool, contained: bool, overlap: bool) -> OverlapKind:
    if same:
        return "identical"
    if contained and overlap:
        return "full"
    if overlap:
        return "partial"
    return "none"
