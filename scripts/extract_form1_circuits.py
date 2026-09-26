# Aaron Green
# Builds a circuit -> from/to substation lookup from TECO's FERC Form 1 schedules.

import csv
import re
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
FORM1_PDF = ROOT / "data" / "EI806-24-AR(GEO).pdf"
OUT_CSV = ROOT / "data" / "interim" / "teco_circuit_lookup.csv"

# Page numbers inside the PDF, located by their FERC footers.
LINE_STATISTICS_PAGES = range(125, 130)   # FERC page 422-423
LINES_ADDED_PAGES = [130]                 # FERC page 424-425

SOURCE_BASE = (
    "Tampa Electric Company FPSC Annual Report 2024 (FERC Form 1 schedules), "
    "filed 2025-04-30"
)

CIRCUIT_ID = r"\d{5,6}"

# "78 Big Bend Sub 230010 Davis Sub 230010 230 STDC 1.558332 ... " — the
# substation name is sometimes glued to the circuit number, so \s* not \s+.
STATISTICS_ROW = re.compile(
    rf"^(?P<line_no>\d+)\s+(?P<from>.+?)\s*(?P<circuit>{CIRCUIT_ID})\s+"
    rf"(?P<to>.+?)\s*(?P<circuit_repeat>{CIRCUIT_ID})\s+(?P<kv>\d+)\s+"
    rf"(?P<structure>[A-Z]+)\s+(?P<length>[\d.]+)"
)


def clean_name(text):
    """Trim the trailing 'Sub'/'Substation' word Form 1 adds inconsistently."""
    name = re.sub(r"\s+", " ", text).strip(" .,-")
    name = re.sub(r"\s+(Substation|Sub\.?)$", "", name, flags=re.IGNORECASE)
    return name.strip()


def page_lines(pdf, page_number):
    return (pdf.pages[page_number - 1].extract_text() or "").split("\n")


def parse_line_statistics(pdf):
    """FERC page 422-423. One row per physical segment; 69 kV is not itemized here."""
    segments = []
    for page_number in LINE_STATISTICS_PAGES:
        for line in page_lines(pdf, page_number):
            match = STATISTICS_ROW.match(line.strip())
            if not match:
                continue
            if match.group("circuit") != match.group("circuit_repeat"):
                continue  # both columns must agree before we trust the row
            segments.append({
                "circuit_id": match.group("circuit"),
                "from_substation": clean_name(match.group("from")),
                "to_substation": clean_name(match.group("to")),
                "voltage_kv": int(match.group("kv")),
                "segment_length_miles": float(match.group("length")),
                "form1_schedule": "Transmission Line Statistics (FERC page 422-423)",
                "pdf_page": page_number,
            })
    return segments


def parse_lines_added(pdf):
    """FERC page 424-425. Lower-voltage circuits show up here with endpoints."""
    segments = []
    skipped = []
    for page_number in LINES_ADDED_PAGES:
        for line in page_lines(pdf, page_number):
            line = line.strip()
            stripped = re.sub(r"^\d+\s+", "", line, count=1)
            if stripped == line:
                continue  # every data row starts with a line number

            ids = re.findall(rf"\b{CIRCUIT_ID}\b", stripped)
            if len(ids) != 2 or ids[0] != ids[1]:
                skipped.append(line)
                continue

            circuit = ids[0]
            parts = re.split(rf"\b{circuit}\b", stripped)
            if len(parts) != 3:
                skipped.append(line)
                continue

            # This schedule prints the circuit number before the name on some
            # rows and after it on others; the empty leading part tells us which.
            if parts[0].strip():
                from_text, to_text = parts[0], parts[1]
            else:
                from_text, to_text = parts[1], parts[2]

            # Trim a trailing length value such as "0.12" or "(7.14)".
            to_text = re.sub(r"\s*\(?-?[\d.]+\)?\s*$", "", to_text)

            from_name, to_name = clean_name(from_text), clean_name(to_text)
            if not from_name or not to_name:
                skipped.append(line)
                continue

            segments.append({
                "circuit_id": circuit,
                "from_substation": from_name,
                "to_substation": to_name,
                "voltage_kv": None,   # this schedule does not restate voltage
                "segment_length_miles": None,
                "form1_schedule": "Transmission Lines Added During Year (FERC page 424-425)",
                "pdf_page": page_number,
            })
    return segments, skipped


FIELDS = [
    "circuit_id", "from_substation", "to_substation", "voltage_kv",
    "line_length_miles", "segment_count", "form1_schedule", "source",
]


def collapse_to_circuits(segments):
    """One row per circuit. Segment lengths are summed; endpoints must agree."""
    by_circuit = {}
    conflicts = []
    for segment in segments:
        key = segment["circuit_id"]
        record = by_circuit.get(key)
        if record is None:
            by_circuit[key] = {
                "circuit_id": key,
                "from_substation": segment["from_substation"],
                "to_substation": segment["to_substation"],
                "voltage_kv": segment["voltage_kv"],
                "lengths": [segment["segment_length_miles"]],
                "segment_count": 1,
                "form1_schedule": segment["form1_schedule"],
            }
            continue

        endpoints = {record["from_substation"], record["to_substation"]}
        if {segment["from_substation"], segment["to_substation"]} != endpoints:
            conflicts.append((key, endpoints, segment))
            continue

        record["lengths"].append(segment["segment_length_miles"])
        record["segment_count"] += 1
        if record["voltage_kv"] is None:
            record["voltage_kv"] = segment["voltage_kv"]

    rows = []
    for record in by_circuit.values():
        lengths = [x for x in record.pop("lengths") if x is not None]
        # No lengths reported stays blank rather than becoming 0.0.
        record["line_length_miles"] = round(sum(lengths), 4) if lengths else None
        record["source"] = SOURCE_BASE
        rows.append(record)
    return rows, conflicts


def main():
    with pdfplumber.open(FORM1_PDF) as pdf:
        statistics = parse_line_statistics(pdf)
        added, skipped = parse_lines_added(pdf)

    rows, conflicts = collapse_to_circuits(statistics + added)
    rows.sort(key=lambda r: r["circuit_id"])

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} circuits to {OUT_CSV.relative_to(ROOT)}")
    print(f"  segments parsed: {len(statistics)} line-statistics, {len(added)} lines-added")
    if conflicts:
        print(f"  endpoint disagreements not merged: {len(conflicts)}")
        for circuit, endpoints, segment in conflicts[:5]:
            print(f"    {circuit}: {endpoints} vs "
                  f"{segment['from_substation']} / {segment['to_substation']}")
    if skipped:
        print(f"  lines-added rows skipped (no usable circuit/endpoints): {len(skipped)}")
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
