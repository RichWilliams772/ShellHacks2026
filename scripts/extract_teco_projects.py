# Aaron Green
# Pulls TECO's 2026 projects out of the Storm Protection Plan PDF into a CSV.

import csv
import re
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SPP_PDF = ROOT / "data" / "TECO.pdf"
OUT_CSV = ROOT / "data" / "interim" / "teco_spp_2026_projects.csv"

# Appendix D = Transmission Asset Upgrades, Appendix F = Substation Extreme
# Weather Hardening. Both hold their "Year 2026 Details" table on one page.
TAU_PAGE = 86
SUBSTATION_PAGE = 90

PROJECT_SOURCE = (
    "Tampa Electric Modified 2026-2035 Storm Protection Plan, "
    "FPSC Docket No. 20250016-EI, Exhibit KEP-1"
)

# The filed PDF renders some characters badly: "Jan" comes out as "Uan" and
# "Aug" as "Auq". Only these exact tokens are corrected, so anything new fails
# loudly instead of being guessed at.
MONTH_FIXES = {"uan": "Jan", "auq": "Aug"}
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
MONTH_END_DAY = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

# Substation names in Appendix F also carry OCR damage. Corrections are listed
# explicitly and the raw text is kept in the output for verification.
NAME_FIXES = {"Lake Aqnes": "Lake Agnes"}

MONTH_TOKEN = re.compile(r"[A-Za-z]{2,4}-\d{2}")

# Matches a date cell even when the PDF has split it up, e.g. "Au q - 2 6".
SPACED_MONTH = re.compile(
    r"(?P<month>[A-Za-z]\s?[A-Za-z]\s?[A-Za-z])\s*-\s*(?P<y1>\d)\s?(?P<y2>\d)"
)


def squash(text):
    """Drop the stray spaces the PDF inserts inside numbers and month tokens."""
    return text.replace(" ", "")


def parse_month(token, label):
    """Turn a token like 'Uan-26' into (year, month)."""
    name, _, year = token.partition("-")
    key = name.lower()
    key = MONTH_FIXES.get(key, key).lower()
    if key not in MONTHS:
        raise ValueError(f"unrecognized month {token!r} in {label}")
    return 2000 + int(year), MONTHS[key]


def month_start(token, label):
    year, month = parse_month(token, label)
    return f"{year:04d}-{month:02d}-01"


def month_end(token, label):
    year, month = parse_month(token, label)
    return f"{year:04d}-{month:02d}-{MONTH_END_DAY[month]:02d}"


def parse_cost(text):
    return int(text.replace("$", "").replace(",", ""))


def page_lines(pdf, page_number):
    return (pdf.pages[page_number - 1].extract_text() or "").split("\n")


# Example row: "Transmission Upgrades-69 kV-66833 66833 145 Uan-2 6 ... $5,787,530"
TAU_ROW = re.compile(
    r"^(?P<name>Transmission Upgrades-(?P<voltage>[\d/]+)\s*kV-(?P<circuit>\d+))"
    r"\s+(?P<circuit_repeat>\d+)\s+(?P<rest>.+)$"
)
TAU_REST = re.compile(
    r"^(?P<poles>\d+)(?P<start>[A-Za-z]{2,4}-\d{2})"
    r"(?P<construction>[A-Za-z]{2,4}-\d{2})(?P<end>[A-Za-z]{2,4}-\d{2})"
    r"\$(?P<cost>[\d,]+)$"
)


def extract_transmission_upgrades(pdf):
    """Appendix D: one row per circuit being upgraded."""
    rows = []
    for line in page_lines(pdf, TAU_PAGE):
        match = TAU_ROW.match(line.strip())
        if not match:
            continue
        rest = TAU_REST.match(squash(match.group("rest")))
        if not rest:
            raise ValueError(f"could not parse Appendix D row: {line!r}")

        circuit = match.group("circuit")
        if circuit != match.group("circuit_repeat"):
            raise ValueError(f"circuit id disagrees within row: {line!r}")

        # "138/230" means the project spans both; keep the higher voltage as the
        # numeric value and the filed label as text.
        voltage_label = match.group("voltage")
        voltage_kv = max(int(v) for v in voltage_label.split("/"))

        rows.append({
            "project_id": f"TECO-{circuit}",
            "project_name": match.group("name"),
            "circuit_id": circuit,
            "project_type": "transmission_upgrade",
            "voltage_kv": voltage_kv,
            "voltage_label": f"{voltage_label} kV",
            "pole_count": int(rest.group("poles")),
            "project_start": month_start(rest.group("start"), line),
            "construction_start": month_start(rest.group("construction"), line),
            "project_end": month_end(rest.group("end"), line),
            "project_cost": parse_cost(rest.group("cost")),
            "date_precision": "month",
            "source_name_raw": match.group("name"),
            "project_source": PROJECT_SOURCE + ", Appendix D page 2 of 2",
        })
    return rows


def extract_substation_hardening(pdf):
    """Appendix F: one row per substation. The filing states 'Project = Substation'."""
    rows = []
    for line in page_lines(pdf, SUBSTATION_PAGE):
        line = line.strip()
        if "$" not in line:
            continue

        # Date cells arrive with spaces sprinkled through them ("Jan-2 6",
        # "Au q - 2 6"), so match on the original line and rebuild each token.
        dates = list(SPACED_MONTH.finditer(line))
        if len(dates) != 3:
            continue
        tokens = [
            f"{squash(d.group('month'))}-{d.group('y1')}{d.group('y2')}"
            for d in dates
        ]

        # The substation name is whatever sits left of the first date column.
        raw_name = line[: dates[0].start()].strip()
        name = NAME_FIXES.get(raw_name, raw_name)

        cost = re.search(r"\$([\d,]+)\s*$", line)
        if not cost:
            raise ValueError(f"could not find cost in Appendix F row: {line!r}")

        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        rows.append({
            "project_id": f"TECO-SUB-{slug}",
            "project_name": f"Substation Extreme Weather Hardening - {name}",
            "circuit_id": None,
            "project_type": "substation_hardening",
            "voltage_kv": None,
            "voltage_label": None,
            "pole_count": None,
            "project_start": month_start(tokens[0], line),
            "construction_start": month_start(tokens[1], line),
            "project_end": month_end(tokens[2], line),
            "project_cost": parse_cost(cost.group(1)),
            "date_precision": "month",
            "source_name_raw": raw_name,
            "substation_name": name,
            "project_source": PROJECT_SOURCE + ", Appendix F page 2 of 2",
        })
    return rows


FIELDS = [
    "project_id", "utility", "project_name", "circuit_id", "project_type",
    "voltage_kv", "voltage_label", "pole_count", "project_start",
    "construction_start", "project_end", "project_cost", "date_precision",
    "substation_name", "source_name_raw", "project_source",
]


def main():
    with pdfplumber.open(SPP_PDF) as pdf:
        rows = extract_transmission_upgrades(pdf) + extract_substation_hardening(pdf)

    for row in rows:
        row["utility"] = "Tampa Electric"
        row.setdefault("substation_name", None)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    upgrades = sum(1 for r in rows if r["project_type"] == "transmission_upgrade")
    hardening = len(rows) - upgrades
    print(f"wrote {len(rows)} projects to {OUT_CSV.relative_to(ROOT)}")
    print(f"  transmission upgrades (Appendix D): {upgrades}")
    print(f"  substation hardening  (Appendix F): {hardening}")
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
