# Aaron Green
# Checks the schedule-overlap and year-proximity logic in analysis/temporal.py.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.temporal import (  # noqa: E402
    calculate_month_overlap, calculate_temporal_features, calculate_year_proximity,
    parse_date, year_range,
)

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def d(text):
    return parse_date(text)


def test_full_overlap():
    # B's interval sits entirely inside A's.
    overlap, months, gap = calculate_month_overlap(
        d("2026-01-01"), d("2026-12-31"), d("2026-06-01"), d("2026-08-31"))
    check("fully-contained interval overlaps", overlap is True)
    check("fully-contained overlap is 3 inclusive months", months == 3, f"got {months}")
    check("gap is None when overlapping", gap is None)


def test_partial_overlap():
    overlap, months, gap = calculate_month_overlap(
        d("2026-01-01"), d("2026-06-30"), d("2026-06-01"), d("2026-12-31"))
    check("partially overlapping intervals overlap", overlap is True)
    check("partial overlap is 1 inclusive month (June)", months == 1, f"got {months}")


def test_adjacent_non_overlapping():
    # A ends May 2026, B starts June 2026: touching but not overlapping.
    overlap, months, gap = calculate_month_overlap(
        d("2026-01-01"), d("2026-05-31"), d("2026-06-01"), d("2026-12-31"))
    check("adjacent intervals do not overlap", overlap is False)
    check("adjacent intervals have zero-month gap", gap == 0, f"got {gap}")
    check("non-overlap reports 0 calculated months, not null",
          months == 0 and months is not None)


def test_completely_separated():
    overlap, months, gap = calculate_month_overlap(
        d("2020-01-01"), d("2020-03-31"), d("2026-01-01"), d("2026-12-31"))
    check("far-apart intervals do not overlap", overlap is False)
    check("gap is large for far-apart intervals", gap > 60, f"got {gap}")


def test_inclusive_month_count():
    # TECO's own 2026 transmission-upgrade window: Jan through Dec.
    overlap, months, _ = calculate_month_overlap(
        d("2026-01-01"), d("2026-12-31"), d("2026-01-01"), d("2026-12-31"))
    check("Jan-Dec counts as 12 inclusive months", months == 12, f"got {months}")

    # A single month against itself must count as 1, not 0.
    overlap, months, _ = calculate_month_overlap(
        d("2026-06-01"), d("2026-06-30"), d("2026-06-01"), d("2026-06-30"))
    check("a single shared month counts as 1", months == 1, f"got {months}")


def test_same_year_comparison():
    difference = calculate_year_proximity((2026, 2026), (2026, 2026))
    check("identical years give zero difference", difference == 0, f"got {difference}")


def test_one_year_difference():
    difference = calculate_year_proximity((2025, 2025), (2026, 2026))
    check("adjacent years give a difference of 1", difference == 1, f"got {difference}")
    difference = calculate_year_proximity((2026, 2026), (2025, 2025))
    check("year difference is order-independent", difference == 1, f"got {difference}")


def test_mixed_precision_never_fabricates_months():
    """The most important test: a year-only estimate must never produce a month count."""
    duke = {"in_service_year": 2027, "date_precision": "year", "start": None, "end": None}
    teco = {"start": "2026-01-01", "end": "2026-12-31", "date_precision": "month",
            "in_service_year": None}
    features = calculate_temporal_features(duke, teco)
    check("mixed precision is reported as 'mixed'", features["temporal_precision"] == "mixed")
    check("mixed precision never sets schedule_overlap_months",
          features["schedule_overlap_months"] is None)
    check("mixed precision never sets schedule_overlap",
          features["schedule_overlap"] is None)
    check("mixed precision uses year_difference instead",
          features["year_difference"] == 1, features["year_difference"])
    check("the reason string does not claim month-level overlap",
          "month" not in features["temporal_reason"].lower())
    check("mixed-precision score never reaches the month-tier ceiling of 100",
          features["temporal_score"] < 100, features["temporal_score"])


def test_mixed_precision_same_year():
    duke = {"in_service_year": 2026, "date_precision": "year", "start": None, "end": None}
    teco = {"start": "2026-01-01", "end": "2026-12-31", "date_precision": "month",
            "in_service_year": None}
    features = calculate_temporal_features(duke, teco)
    check("same-year mixed precision sets same_active_year", features["same_active_year"] is True)
    check("same-year mixed precision gives year_difference 0", features["year_difference"] == 0)
    check("same-year mixed precision scores below month-tier ceiling",
          features["temporal_score"] == 80, features["temporal_score"])


def test_missing_schedule_data():
    duke = {"in_service_year": None, "date_precision": None, "start": None, "end": None}
    teco = {"start": "2026-01-01", "end": "2026-12-31", "date_precision": "month",
            "in_service_year": None}
    features = calculate_temporal_features(duke, teco)
    check("missing Duke schedule gives temporal_data_available False",
          features["temporal_data_available"] is False)
    check("missing schedule gives precision 'unknown'",
          features["temporal_precision"] == "unknown")
    check("missing schedule gives null temporal_score, not zero",
          features["temporal_score"] is None)
    check("missing schedule gives null year_difference", features["year_difference"] is None)


def test_year_range_helper():
    check("year_range prefers real dates over an estimate",
          year_range({"start": "2026-06-01", "end": "2026-08-31",
                     "in_service_year": 2030}) == (2026, 2026))
    check("year_range falls back to in_service_year",
          year_range({"start": None, "end": None, "in_service_year": 2028}) == (2028, 2028))
    check("year_range is None with nothing to go on",
          year_range({"start": None, "end": None, "in_service_year": None}) is None)


def main():
    test_full_overlap()
    test_partial_overlap()
    test_adjacent_non_overlapping()
    test_completely_separated()
    test_inclusive_month_count()
    test_same_year_comparison()
    test_one_year_difference()
    test_mixed_precision_never_fabricates_months()
    test_mixed_precision_same_year()
    test_missing_schedule_data()
    test_year_range_helper()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
