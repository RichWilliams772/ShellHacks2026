"""Full, partial, empty, identical, and year-only schedule overlap."""

from __future__ import annotations

from app.temporal import MONTH_DAYS, compare_schedules
from tests.helpers import make_project


def test_identical_dates() -> None:
    left = make_project(start_date="2027-01-01", end_date="2027-01-10")
    right = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        start_date="2027-01-01",
        end_date="2027-01-10",
    )
    result = compare_schedules(left, right)
    assert result.precision == "day"
    assert result.overlap_kind == "identical"
    assert result.overlap_days == 10
    assert result.schedule_overlap_months == 10 / MONTH_DAYS
    assert result.schedule_overlap_ratio == 1
    assert result.start_date_difference == 0
    assert result.end_date_difference == 0
    assert result.overlap_years is None


def test_full_overlap_when_one_schedule_contains_the_other() -> None:
    left = make_project(start_date="2027-01-01", end_date="2027-01-10")
    right = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        start_date="2027-01-01",
        end_date="2027-01-20",
    )
    result = compare_schedules(left, right)
    assert result.precision == "day"
    assert result.overlap_kind == "full"
    assert result.overlap_days == 10
    assert result.schedule_overlap_ratio == 0.5
    assert result.end_date_difference == 10
    assert result.schedule_overlap_months == 10 / MONTH_DAYS


def test_partial_overlap() -> None:
    left = make_project(start_date="2027-01-01", end_date="2027-01-10")
    right = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        start_date="2027-01-05",
        end_date="2027-01-20",
    )
    result = compare_schedules(left, right)
    assert result.precision == "day"
    assert result.overlap_kind == "partial"
    assert result.overlap_days == 6
    assert result.start_date_difference == 4
    assert result.end_date_difference == 10
    assert result.schedule_overlap_ratio == 6 / 20


def test_no_overlap() -> None:
    left = make_project(start_date="2026-01-01", end_date="2026-06-01")
    right = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        start_date="2028-01-01",
        end_date="2028-06-01",
    )
    result = compare_schedules(left, right)
    assert result.precision == "day"
    assert result.overlap_kind == "none"
    assert result.overlap_days == 0
    assert result.schedule_overlap_ratio == 0
    assert result.schedule_overlap_months == 0
    assert result.overlapping_years == ()


def test_year_only_overlap_does_not_invent_months() -> None:
    left = make_project(start_date="2027", end_date="2028")
    right = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        start_date="2027",
        end_date="2029",
    )
    result = compare_schedules(left, right)
    assert result.precision == "year"
    assert result.overlap_kind == "full"
    assert result.overlap_years == 2
    assert result.overlapping_years == (2027, 2028)
    assert result.schedule_overlap_ratio == 2 / 3
    assert result.overlap_days is None
    assert result.schedule_overlap_months is None
    assert result.start_date_difference is None
    assert result.end_date_difference is None
    assert result.start_year_difference == 0
    assert result.end_year_difference == 1
    assert "year-level" in result.reasons[0]
    assert "not calculated" in result.reasons[0]


def test_year_only_partial_and_none() -> None:
    partial_a = make_project(start_date="2026", end_date="2028")
    partial_b = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        start_date="2027",
        end_date="2029",
    )
    partial = compare_schedules(partial_a, partial_b)
    assert partial.precision == "year"
    assert partial.overlap_kind == "partial"
    assert partial.overlap_years == 2
    assert partial.schedule_overlap_ratio == 0.5
    assert partial.schedule_overlap_months is None

    none = compare_schedules(
        make_project(start_date="2025", end_date="2026"),
        make_project(
            id="TECO-DEMO-C",
            utility="Tampa Electric",
            start_date="2028",
            end_date="2029",
        ),
    )
    assert none.overlap_kind == "none"
    assert none.overlap_years == 0
    assert none.schedule_overlap_ratio == 0
    assert none.overlap_days is None
    assert none.schedule_overlap_months is None


def test_mixed_precision_stays_at_year_level() -> None:
    dated = make_project(start_date="2027-03-01", end_date="2028-06-01")
    yearly = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        start_date="2027",
        end_date="2029",
    )
    result = compare_schedules(dated, yearly)
    assert result.precision == "year"
    assert result.schedule_overlap_months is None
    assert result.overlap_days is None
    assert result.overlapping_years == (2027, 2028)


def test_missing_schedule_is_null_not_zero() -> None:
    result = compare_schedules(
        make_project(start_date=None, end_date=None),
        make_project(id="TECO-DEMO-B", utility="Tampa Electric"),
    )
    assert result.precision == "unavailable"
    assert result.overlap_days is None
    assert result.schedule_overlap_months is None
    assert result.schedule_overlap_ratio is None
    assert result.overlap_kind is None
    assert "not treated as zero" in result.evidence_gaps[0]
