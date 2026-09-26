# Aaron Green
# Looks up coordinates for the TECO substations we need and caches them to CSV.

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT / "data" / "interim" / "teco_spp_2026_projects.csv"
LOOKUP_CSV = ROOT / "data" / "interim" / "teco_circuit_lookup.csv"
OUT_CSV = ROOT / "data" / "interim" / "teco_substation_coords.csv"

# HIFLD Electric Substations. This is the same source Our Grid Future used for
# its own substation table: querying HIFLD ID 148700 (Kathleen) returns the
# identical coordinates the xlsx lists for that substation.
SERVICE_URL = (
    "https://services5.arcgis.com/HDRa0B57OVrv2E1q/arcgis/rest/services/"
    "Electric_Substations/FeatureServer/0/query"
)
GEOGRAPHY_SOURCE = "HIFLD Electric Substations (national layer), queried via ArcGIS REST"

# "The retail territory served comprises an area of about 2,000 square miles in
# West Central Florida, including Hillsborough County and parts of Polk, Pasco
# and Pinellas Counties." — TECO FPSC Annual Report 2024 / Form 10-K Item 1.
# Used only to break ties when one name appears more than once in Florida.
TECO_COUNTIES = {"HILLSBOROUGH", "POLK", "PASCO", "PINELLAS"}

# HIFLD writes unknown numeric values as -999999. Those must stay missing.
HIFLD_NULL = -999999

FIELDS = [
    "substation_name", "matched_name", "hifld_id", "county", "latitude",
    "longitude", "max_voltage_kv", "match_type", "record_source",
    "geography_source", "retrieved_date",
]


def needed_substations():
    """The substation names the geography build will actually ask for."""
    projects = pd.read_csv(PROJECTS_CSV, dtype={"circuit_id": "string"})
    lookup = pd.read_csv(LOOKUP_CSV, dtype={"circuit_id": "string"})

    circuits = set(projects["circuit_id"].dropna())
    matched = lookup[lookup["circuit_id"].isin(circuits)]

    names = set(matched["from_substation"].dropna())
    names |= set(matched["to_substation"].dropna())
    names |= set(projects["substation_name"].dropna())
    return sorted(names)


def query_florida(names):
    """One request for all names, matched on the uppercase substation name."""
    quoted = ",".join("'" + n.upper().replace("'", "''") + "'" for n in names)
    response = requests.get(
        SERVICE_URL,
        params={
            "where": f"STATE='FL' AND NAME IN ({quoted})",
            "outFields": "ID,NAME,COUNTY,STATE,MAX_VOLT,LATITUDE,LONGITUDE,SOURCE",
            "returnGeometry": "false",
            "f": "json",
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"substation query failed: {payload['error']}")
    return [feature["attributes"] for feature in payload.get("features", [])]


def pick(name, candidates):
    """Return the single defensible match, or None if the answer is unclear."""
    if not candidates:
        return None, "not_found"
    if len(candidates) == 1:
        return candidates[0], "exact_name"

    # More than one Florida substation shares the name; keep only those inside
    # TECO's counties. Anything still ambiguous is left for a human to check.
    in_territory = [c for c in candidates
                    if str(c.get("COUNTY", "")).upper() in TECO_COUNTIES]
    if len(in_territory) == 1:
        return in_territory[0], "exact_name_in_teco_county"
    return None, f"ambiguous_{len(candidates)}_candidates"


def build_rows(names, attributes):
    by_name = {}
    for attribute in attributes:
        by_name.setdefault(str(attribute["NAME"]).upper(), []).append(attribute)

    today = dt.date.today().isoformat()
    rows, unresolved = [], []
    for name in names:
        chosen, match_type = pick(name, by_name.get(name.upper(), []))
        if chosen is None:
            unresolved.append((name, match_type))
            rows.append({
                "substation_name": name,
                "matched_name": None,
                "hifld_id": None,
                "county": None,
                "latitude": None,
                "longitude": None,
                "max_voltage_kv": None,
                "match_type": match_type,
                "record_source": None,
                "geography_source": None,
                "retrieved_date": today,
            })
            continue

        voltage = chosen.get("MAX_VOLT")
        rows.append({
            "substation_name": name,
            "matched_name": chosen["NAME"],
            "hifld_id": chosen.get("ID"),
            "county": chosen.get("COUNTY"),
            "latitude": chosen.get("LATITUDE"),
            "longitude": chosen.get("LONGITUDE"),
            "max_voltage_kv": None if voltage in (None, HIFLD_NULL) else voltage,
            "match_type": match_type,
            "record_source": chosen.get("SOURCE"),
            "geography_source": GEOGRAPHY_SOURCE,
            "retrieved_date": today,
        })
    return rows, unresolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true",
                        help="re-query the service even if the cache exists")
    args = parser.parse_args()

    if OUT_CSV.exists() and not args.refresh:
        cached = pd.read_csv(OUT_CSV)
        located = cached["latitude"].notna().sum()
        print(f"using cached {OUT_CSV.relative_to(ROOT)} "
              f"({located}/{len(cached)} located); pass --refresh to re-query")
        return 0

    names = needed_substations()
    rows, unresolved = build_rows(names, query_florida(names))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    located = sum(1 for r in rows if r["latitude"] is not None)
    print(f"wrote {len(rows)} substations to {OUT_CSV.relative_to(ROOT)} "
          f"({located} located)")
    for name, reason in unresolved:
        print(f"  unresolved: {name} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
