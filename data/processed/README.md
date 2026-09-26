# Aaron Green
# What is in teco_projects_geocoded.csv and how to use it.

## teco_projects_geocoded.csv

16 real Tampa Electric 2026 projects from the Storm Protection Plan. 5 of them
have usable coordinates; the other 11 are in the file with their geography
columns left blank on purpose.

**Filter on `location_confidence` before doing anything geographic.**

```python
df = pd.read_csv("data/processed/teco_projects_geocoded.csv", dtype={"circuit_id": "string"})
mappable = df[df["location_confidence"].isin(["HIGH", "MEDIUM"])]
```

| project_id | geography | confidence |
|---|---|---|
| `TECO-230037` | Gannon ↔ Juneau corridor | HIGH |
| `TECO-138005` | Ohio ↔ Clearview corridor | HIGH |
| `TECO-SUB-skyway` | Skyway substation point | HIGH |
| `TECO-SUB-lake-agnes` | Lake Agnes substation point | HIGH |
| `TECO-66653` | South Eloise point (Sandhill endpoint not located) | MEDIUM |
| 11 others | none | UNKNOWN |

## Columns that need explaining

- **`mid_lat` / `mid_lon`** — use these for proximity scoring. Midpoint of the
  two endpoints for a corridor, the substation itself for a point project.
  Populated for every HIGH and MEDIUM row, blank otherwise.
- **`geometry_type`** — `approximate_corridor` or `point`.
- **`line_length_miles`** — the sum of every FERC Form 1 segment length for that
  circuit. It is **not** the distance between the two endpoints, and it is about
  2.5x larger. `endpoint_distance_miles` is the straight-line figure.
- **`voltage_kv`** — for `138/230 kV` projects this is the higher value, 230.
  The label as filed is in `voltage_label`.
- **`date_precision`** is `month` for every row. The SPP gives month and year
  only, so starts are the 1st and ends are the last day of the month.
- **`unresolved_reason`** — why a row has no geography. Good text for the UI.

## Rules this data follows

- **A corridor is two endpoints joined by a straight line, not a transmission
  route.** If the map draws it, call it an approximate corridor.
- **Blank means unknown, never zero.** Missing cost, voltage, pole count and
  coordinates are all empty. Do not `fillna(0)`.
- **`location_confidence`** is set only by `scripts/build_teco_geography.py`:
  HIGH = location fully pinned down by public records (both corridor endpoints
  located, or a located point project); MEDIUM = corridor with one endpoint
  located; LOW = approximate geography only (currently unused); UNKNOWN = no
  defensible geography.

## Sources

- Projects: Tampa Electric Modified 2026-2035 Storm Protection Plan, FPSC Docket
  No. 20250016-EI, Exhibit KEP-1, Appendices D and F.
- Circuit endpoints: Tampa Electric FPSC Annual Report 2024, FERC Form 1
  schedules, pages 422-423 and 424-425.
- Coordinates: HIFLD Electric Substations, the same source Our Grid Future used
  for its own substation table.

Per-row citations are in `project_source`, `circuit_endpoint_source`,
`form1_schedule` and `geography_source`.

## Rebuilding

```bash
pip install -r requirements.txt
python scripts/extract_teco_projects.py
python scripts/extract_form1_circuits.py
python scripts/fetch_substation_coords.py   # cached; --refresh to re-query
python scripts/build_teco_geography.py
python tests/test_teco_geography.py
```

---

# Task 2 outputs

## duke_projects_normalized.csv

10 Duke Energy Florida projects, all with both endpoints located. Built from Our
Grid Future's project sheet joined to its substation sheet on substation name.

Started from 16 Florida records and dropped 6, each logged with a reason in
`data/interim/duke_project_exclusions.csv`:

- 3 not owned by Duke (Tampa Electric, OUC, FPL)
- 3 with `Status = Complete` (Crystal River-Bronson, Southern Oaks, Williston-Bronson)

Nothing was dropped for having a past in-service year. `P-0313` has in-service
year 2023 with a `Construction` status, which is ambiguous, so it stays in and
the temporal analysis decides what to do with it.

**`DUKE-P0017` needs a human look.** Our Grid Future lists the Archer Reliability
Upgrade Projects under `Dominion Energy`, but its only source link is a
`duke-energy.com` project map and its Archer substation is also an endpoint of
Duke's `P-0246`. It is included as Duke on that evidence, with `owner_original`
kept as filed and the reasoning in `ownership_note`. Filter on
`ownership_confidence != "HIGH"` to exclude it.

Duke has **no start or end dates** — Our Grid Future gives a year and nothing
finer, so `project_start` / `construction_start` / `project_end` are empty and
`date_precision` is `year`. TECO's are `month`. Do not compare the two as if
they were equally precise.

## duke_teco_candidate_pairs.csv

Every Duke project crossed with every TECO project: 10 x 16 = **160 rows**. No
filtering, ranking or scoring of any kind — this is the list of comparisons
worth making, not a judgement about any of them.

- `pair_id` is `"<duke_id>__<teco_id>"`, e.g. `DUKE-P0288__TECO-66833`. Same
  inputs always give the same id.
- **`project_a_*` is always Duke, `project_b_*` is always TECO.**
- **`geography_available_both`** is True for the **50** pairs where both sides
  have a usable point. Filter on this before measuring distance.
- `project_b_status` and `project_b_in_service_year` are empty: the Storm
  Protection Plan does not state either per project.

Use `project_a_mid_lat/mid_lon` and `project_b_mid_lat/mid_lon` as each side's
representative point.

## Rebuilding Task 2

```bash
python scripts/normalize_duke_projects.py
python scripts/build_candidate_pairs.py
python tests/test_candidate_pairs.py
```
