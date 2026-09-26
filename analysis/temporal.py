# Aaron Green
# Compares two project schedules honestly - a year-only estimate is never treated like a real date.

import datetime
import math

# Calendar-month overlap, inclusive on both ends: a project running Jun-Dec
# counts as 7 overlapping months (Jun, Jul, Aug, Sep, Oct, Nov, Dec), not 6.
# This convention is documented once here and used nowhere else.
MONTH_OVERLAP_SCORE_BANDS = [
    (6, 100),
    (3, 80),
    (1, 60),
]
MONTH_OVERLAP_SCORE_NO_OVERLAP_NEAR = 40   # no overlap, but <= 3 months apart
MONTH_OVERLAP_SCORE_NO_OVERLAP_FAR = 0
NEAR_GAP_MONTHS = 3

# Year/mixed-precision scoring is deliberately capped below the month-precision
# ceiling (100). Treating "same estimated year" as equal to a verified 6-month
# overlap would reward uncertainty as if it were precision - see TASK_3 section
# 25. 80 is the best a year-level comparison can ever score.
YEAR_PROXIMITY_SCORE_SAME_YEAR = 80
YEAR_PROXIMITY_SCORE_ONE_YEAR_APART = 50
YEAR_PROXIMITY_SCORE_FAR = 20


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def parse_date(value):
    """'2026-06-01' -> date(2026, 6, 1). Missing or unparsable -> None, never a guess."""
    value = _clean(value)
    if value is None:
        return None
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_year(value):
    value = _clean(value)
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def year_range(project):
    """The calendar year(s) a project is understood to be active, at whatever
    precision the source actually supports.

    A project with real start/end dates uses their years. A project known only
    by an estimated in-service year uses that single year for both ends. A
    project with neither returns None - there is nothing to compare.
    """
    start = parse_date(project.get("start"))
    end = parse_date(project.get("end"))
    if start and end:
        return start.year, end.year

    year = parse_year(project.get("in_service_year"))
    if year is not None:
        return year, year

    return None


def calculate_month_overlap(start_a, end_a, start_b, end_b):
    """Inclusive calendar-month overlap between two exact intervals.

    Returns (schedule_overlap, schedule_overlap_months, gap_months). gap_months
    is only meaningful when schedule_overlap is False.
    """
    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)

    if overlap_start <= overlap_end:
        months = ((overlap_end.year - overlap_start.year) * 12
                  + (overlap_end.month - overlap_start.month) + 1)
        return True, months, None

    # Not overlapping: whichever interval ends first, count the whole months
    # strictly between its end and the other interval's start.
    if end_a < start_b:
        earlier_end, later_start = end_a, start_b
    else:
        earlier_end, later_start = end_b, start_a
    gap = (later_start.year - earlier_end.year) * 12 + (later_start.month - earlier_end.month) - 1
    return False, 0, max(gap, 0)


def calculate_month_overlap_score(schedule_overlap, schedule_overlap_months, gap_months):
    if schedule_overlap:
        for threshold, score in MONTH_OVERLAP_SCORE_BANDS:
            if schedule_overlap_months >= threshold:
                return score
        return MONTH_OVERLAP_SCORE_NO_OVERLAP_FAR
    if gap_months is not None and gap_months <= NEAR_GAP_MONTHS:
        return MONTH_OVERLAP_SCORE_NO_OVERLAP_NEAR
    return MONTH_OVERLAP_SCORE_NO_OVERLAP_FAR


def calculate_year_proximity(range_a, range_b):
    """Distance in years between two active ranges. 0 if they overlap at all."""
    start_a, end_a = range_a
    start_b, end_b = range_b
    if start_a <= end_b and start_b <= end_a:
        return 0
    return start_b - end_a if start_b > end_a else start_a - end_b


def calculate_year_proximity_score(year_difference):
    if year_difference == 0:
        return YEAR_PROXIMITY_SCORE_SAME_YEAR
    if year_difference == 1:
        return YEAR_PROXIMITY_SCORE_ONE_YEAR_APART
    return YEAR_PROXIMITY_SCORE_FAR


def _unknown_result(reason):
    return {
        "temporal_data_available": False,
        "temporal_precision": "unknown",
        "schedule_overlap": None,
        "schedule_overlap_months": None,
        "same_active_year": None,
        "year_difference": None,
        "temporal_score": None,
        "temporal_reason": reason,
    }


def calculate_temporal_features(project_a, project_b):
    """Full temporal feature set for one Duke x TECO row.

    project_a / project_b: dicts with start, end, in_service_year, date_precision.
    Never fabricates a precision level higher than the source data supports.
    """
    precision_a = _clean(project_a.get("date_precision"))
    precision_b = _clean(project_b.get("date_precision"))

    if precision_a is None or precision_b is None:
        return _unknown_result("Insufficient schedule information to compare timing.")

    if precision_a == "month" and precision_b == "month":
        start_a, end_a = parse_date(project_a.get("start")), parse_date(project_a.get("end"))
        start_b, end_b = parse_date(project_b.get("start")), parse_date(project_b.get("end"))
        if not (start_a and end_a and start_b and end_b):
            return _unknown_result("Insufficient schedule information to compare timing.")

        overlap, months, gap = calculate_month_overlap(start_a, end_a, start_b, end_b)
        score = calculate_month_overlap_score(overlap, months, gap)
        if overlap:
            reason = f"Construction schedules overlap for {months} calendar month{'s' if months != 1 else ''}."
        elif gap == 0:
            reason = "Construction schedules do not overlap, but the two periods are adjacent."
        else:
            reason = (f"Construction schedules do not overlap; the gap between them "
                      f"is about {gap} month{'s' if gap != 1 else ''}.")
        return {
            "temporal_data_available": True,
            "temporal_precision": "month",
            "schedule_overlap": overlap,
            "schedule_overlap_months": months,
            "same_active_year": None,
            "year_difference": None,
            "temporal_score": score,
            "temporal_reason": reason,
        }

    # One or both sides are only known to year precision. Never claim a month
    # count here - that would be false precision the source does not support.
    range_a, range_b = year_range(project_a), year_range(project_b)
    if range_a is None or range_b is None:
        return _unknown_result("Insufficient schedule information to compare timing.")

    year_difference = calculate_year_proximity(range_a, range_b)
    same_active_year = year_difference == 0
    score = calculate_year_proximity_score(year_difference)
    precision = "year" if precision_a == "year" and precision_b == "year" else "mixed"

    reason = ("Available project schedules indicate activity in the same year."
              if same_active_year else
              f"Available project schedules differ by about {year_difference} "
              f"year{'s' if year_difference != 1 else ''}.")

    return {
        "temporal_data_available": True,
        "temporal_precision": precision,
        "schedule_overlap": None,
        "schedule_overlap_months": None,
        "same_active_year": same_active_year,
        "year_difference": year_difference,
        "temporal_score": score,
        "temporal_reason": reason,
    }
