# Aaron Green
# Pairs every Duke project with every TECO project so later tasks can score them.

import csv
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DUKE_CSV = ROOT / "data" / "processed" / "duke_projects_normalized.csv"
TECO_CSV = ROOT / "data" / "processed" / "teco_projects_geocoded.csv"
OUT_CSV = ROOT / "data" / "processed" / "duke_teco_candidate_pairs.csv"

# Side A is always Duke, side B is always TECO. Nothing here filters, ranks or
# scores a pair; this file is only the list of comparisons worth making.
SIDES = ("a", "b")

# Fields copied from each side onto the pair row. Everything a later task needs
# to compute distance, schedule overlap or similarity, and nothing computed.
CARRIED = [
    "project_id", "utility", "project_name", "project_type", "status",
    "voltage_min_kv", "voltage_max_kv", "voltage_label", "project_start",
    "construction_start",
    "project_end", "date_precision", "estimated_in_service_year",
    "from_substation", "to_substation", "from_lat", "from_lon", "to_lat",
    "to_lon", "mid_lat", "mid_lon", "geometry_type", "location_method",
    "location_confidence",
]

# A project can be placed on a map if it has a representative point.
LOCATED = ("HIGH", "MEDIUM")

# Only field that does not read well after the prefix rule below.
SHORTER_NAMES = {"estimated_in_service_year": "in_service_year"}


def clean(value):
    """Keep pandas NaN out of the output; missing stays missing."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def voltage_range(label):
    """'138/230 kV' -> (138, 230). A single value or unreadable text -> (None, None)."""
    if not isinstance(label, str):
        return (None, None)
    numbers = [int(n) for n in re.findall(r"\d+", label)]
    return (min(numbers), max(numbers)) if len(numbers) > 1 else (None, None)


def load(path, label):
    frame = pd.read_csv(path, dtype={"circuit_id": "string"})
    if frame.empty:
        raise SystemExit(f"{label} dataset is empty: {path}")

    # TECO carries one voltage figure plus the label as filed; Duke carries a min
    # and a max. Give both sides the same shape, reading the range out of the
    # label so a "138/230 kV" project is not flattened to 230 alone.
    if "voltage_kv" in frame.columns and "voltage_min_kv" not in frame.columns:
        ranges = frame.get("voltage_label", pd.Series(dtype=object)).map(voltage_range)
        frame["voltage_min_kv"] = [
            low if low is not None else clean(fallback)
            for (low, _), fallback in zip(ranges.reindex(frame.index, fill_value=(None, None)),
                                          frame["voltage_kv"])
        ]
        frame["voltage_max_kv"] = [
            high if high is not None else clean(fallback)
            for (_, high), fallback in zip(ranges.reindex(frame.index, fill_value=(None, None)),
                                           frame["voltage_kv"])
        ]

    missing = [column for column in CARRIED if column not in frame.columns]
    for column in missing:
        frame[column] = None
    if missing:
        print(f"note: {label} has no {', '.join(missing)}; left empty")
    return frame


def pair_id(duke_id, teco_id):
    """Deterministic and readable, so the same inputs always give the same id."""
    return f"{duke_id}__{teco_id}"


def column_name(side, field):
    """project_id -> project_a_id, utility -> project_a_utility."""
    short = SHORTER_NAMES.get(field, field)
    short = short[len("project_"):] if short.startswith("project_") else short
    return f"project_{side}_{short}"


def build(duke, teco):
    rows = []
    for duke_row in duke.to_dict("records"):
        for teco_row in teco.to_dict("records"):
            row = {"pair_id": pair_id(duke_row["project_id"], teco_row["project_id"])}
            for side, source in zip(SIDES, (duke_row, teco_row)):
                for field in CARRIED:
                    row[column_name(side, field)] = clean(source.get(field))
            row["geography_available_both"] = (
                row["project_a_location_confidence"] in LOCATED
                and row["project_b_location_confidence"] in LOCATED
            )
            rows.append(row)
    return rows


def main():
    duke = load(DUKE_CSV, "Duke")
    teco = load(TECO_CSV, "TECO")

    rows = build(duke, teco)
    expected = len(duke) * len(teco)

    fields = list(rows[0].keys())
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    mappable = sum(1 for row in rows if row["geography_available_both"])
    print(f"Duke projects: {len(duke)}")
    print(f"TECO projects: {len(teco)}")
    print(f"expected pairs: {len(duke)} x {len(teco)} = {expected}")
    print(f"actual pairs:   {len(rows)}")
    print(f"unique pair ids: {len({row['pair_id'] for row in rows})}")
    print(f"pairs with geography on both sides: {mappable}")
    print(f"wrote {OUT_CSV.relative_to(ROOT)}")

    if len(rows) != expected:
        print("WARNING: pair count does not match the expected product")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
