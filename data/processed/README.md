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

## Two things the pair file deliberately does not do

**It does not repeat provenance.** `project_source`, `geography_source`,
`source_url`, `unresolved_reason`, `ownership_note` and `data_type` live in the
two project files, not duplicated 160 times. For the "public sources" and "why
unmatched" parts of the detail panel, join back on id:

```python
pairs = pd.read_csv("data/processed/duke_teco_candidate_pairs.csv")
duke  = pd.read_csv("data/processed/duke_projects_normalized.csv")
teco  = pd.read_csv("data/processed/teco_projects_geocoded.csv")

detail = (pairs
    .merge(duke.add_prefix("a_"), left_on="project_a_id", right_on="a_project_id")
    .merge(teco.add_prefix("b_"), left_on="project_b_id", right_on="b_project_id"))
```

**It does not use the field names in the project spec's JSON examples.** These
files use `project_id`, `project_start`, `project_cost`, `mid_lat` / `mid_lon`.
The spec examples use `id`, `start_date`, `capital_cost`, `latitude` /
`longitude`. A reader looking for the spec names finds nothing and renders an
empty map with no error. The mapping is:

| these files | project spec examples |
|---|---|
| `project_id` | `id` |
| `project_start` | `start_date` |
| `project_end` | `end_date` |
| `project_cost` | `capital_cost` |
| `mid_lat` / `mid_lon` | `latitude` / `longitude` |
| `voltage_max_kv` | `voltage_kv` |

Pick one set of names for the API response and say so — this is a contract,
not something either side should guess at.

---

# Task 3 outputs

## duke_teco_pair_features.csv

The Task 2 candidate-pair file with geographic and temporal features appended.
Same 160 rows, same `pair_id`s, nothing from Task 2 changed - only new columns
added. Built by `scripts/build_pair_features.py` from `analysis/geographic.py`
and `analysis/temporal.py`.

**Raw measurements always sit next to the derived score.** Never read
`geographic_score` or `temporal_score` alone - `minimum_endpoint_distance_miles`
and `schedule_overlap_months` / `year_difference` are what a judge can verify.

### Geographic columns

| column | meaning |
|---|---|
| `geography_available` | can this pair be measured at all |
| `geography_point_count_a/b` | 0, 1, or 2 - how many endpoints each side has |
| `minimum_endpoint_distance_miles` | smallest of up to 4 cross-project endpoint distances |
| `project_a_nearest_endpoint` / `project_b_nearest_endpoint` | which endpoint (`origin`/`destination`) produced that minimum |
| `pair_geography_confidence` | HIGH/MEDIUM/UNKNOWN, derived from both projects' own confidence - never overwrites them |
| `geographic_score` | 0-100 heuristic, `null` when `geography_available` is false |
| `geographic_reason` | one sentence, generated only from the calculated values |

`minimum_endpoint_distance_miles` is the distance between known **endpoints**,
not a transmission route. Read it as "known project endpoints are ~X miles
apart," never "the lines are X miles apart."

Scoring rule (PROJECT_SPEC gives descriptive bands, not 0-100 numbers - this is
Task 3's own prototype heuristic, centralized in
`analysis/geographic.GEOGRAPHIC_SCORE_THRESHOLDS`):

```
<= 10 mi -> 100      <= 25 mi -> 80      <= 50 mi -> 50      <= 100 mi -> 20      > 100 mi -> 0
```

Coverage: 50/160 pairs have geography on both sides (matches Task 2's count).
Of those, distance ranges 6.0-190.5 miles, median ~67. 110 pairs are `null`,
not zero - a TECO project with no located substation was never assumed to be
"far away," it's simply unmeasured.

### Temporal columns

| column | meaning |
|---|---|
| `temporal_data_available` | can this pair's timing be compared at all |
| `temporal_precision` | `month` \| `year` \| `mixed` \| `unknown` |
| `schedule_overlap` / `schedule_overlap_months` | only set at `month` precision |
| `same_active_year` / `year_difference` | only set at `year`/`mixed` precision |
| `temporal_score` | 0-100 heuristic, `null` when data is unavailable |
| `temporal_reason` | one sentence, matched to the precision actually used |

**Important:** Duke only ever has an estimated in-service year, never a month
or day. So in this dataset, `temporal_precision` is only ever `mixed` (144
pairs - Duke has a year, TECO has month dates) or `unknown` (16 pairs - Duke's
`P0017` has no year at all). The `month`/`year` tiers and the exact overlap
logic (`schedule_overlap_months`) are implemented and unit-tested against
synthetic dates in `tests/test_temporal.py`, but **do not fire on any real row
right now** - there's no pair where both sides have month-level dates. If Duke
data ever gains month precision, or a third utility with month-level dates is
added, the same code handles it without changes.

Mixed/year-precision scores are capped at 80, never 100 - reaching "same year"
compatibility is not treated as equal to a verified 6-month overlap. This is a
deliberate rule (`analysis/temporal.py`, `YEAR_PROXIMITY_SCORE_*`), not an
oversight: uncertain data should never outscore precise data.

## Rebuilding Task 3

```bash
python scripts/build_pair_features.py
python tests/test_geographic.py
python tests/test_temporal.py
python tests/test_pair_features_integrity.py
```
