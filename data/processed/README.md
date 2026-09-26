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

## A warning for Task 5 (scoring)

Do not `fillna(0)` on `geographic_score` or `temporal_score` when combining them.
110 pairs have a null geographic score and 16 have a null temporal score - those
are "unmeasured," and zero-filling them would make an unmeasured pair look like
a known bad match, reviving exactly the ranking bug this pipeline was built to
avoid.

There is a second, sharper trap here: **do not let a stale project's clean
geography accidentally win.** `DUKE-P0313` (Osprey-Haines City) has an
in-service year of 2023 and is only 6 miles from a 2026 TECO project - that
pair scores `geographic_score=100` but `temporal_score=20` (3 years apart). If
Task 5's weighted blend (`0.4 * geo + 0.3 * temporal + ...`) runs on that pair
versus a genuinely-2026 Duke project sitting 42-82 miles away
(`geographic_score` 20-50, `temporal_score=80` for being in the same year), the
2023 pair can out-score the honest 2026 one. A single blended number hides
that one pair is "close but stale" and the other is "farther but current" -
two very different stories that deserve to stay visible, not collapse into one
score that a judge then has to be talked out of. Surface both components next
to the blend, not just the blend.

## Two intentional design choices, in case they look like bugs

**`geographic_score` never factors in `pair_geography_confidence`.** A MEDIUM
project (one endpoint located) that happens to sit 6 miles away still scores
100 - the distance is real, only the confidence about the *other* endpoint is
lower. Folding confidence into the score would violate PROJECT_SPEC's own rule
("do not use confidence as a score"). Show both fields side by side instead of
blending them.

**Distance is `<= 10/25/50/100` with a hard cutoff at each boundary**, not a
smooth curve - 50.0 miles scores 50, 50.01 scores 20. This is the exact
worked example given for this rule; it is not something to soften without
being asked. The same is true of the year-proximity buckets: the task
deliberately specifies three tiers (same year / 1 year / 2+), so a project 3
years off and one 6 years off score identically. That coarseness is the
requested prototype, not an oversight.

---

# Task 4 outputs

## duke_teco_pair_similarity.csv

Task 3's file with text and infrastructure similarity appended. Same 160 rows,
every Task 3 column unchanged - only new columns added. Built by
`scripts/build_similarity_features.py` from `analysis/similarity.py` (TF-IDF
text) and `analysis/infrastructure.py` (structured attributes).

### Text similarity

TF-IDF is fit **once** across all 26 unique projects (10 Duke + 16 TECO), then
cosine similarity is looked up per pair - never refit per pair, which would
put every pair in its own incomparable vocabulary.

Text = `project_name` + normalized `project_type` (e.g. "transmission
upgrade"), lowercased, utility branding stripped, **bare voltage figures
stripped** (`"230 kV"`, `"69kV"`, `"138/230 kV"` all removed as tokens -
voltage is already its own component below; leaving these in was originally
tried and rejected once real data showed it double-counting - see below).
Excludes anything geographic/temporal/cost/ID - those are Task 3's territory,
not "what is this project."

`ngram_range=(1,1)` - tested against `(1,2)` on the real corpus first;
bigrams made same-type vs different-type separation *worse* on 26 documents
(median 0.097 vs 0.165), so unigrams were kept, not defaulted to.

| column | meaning |
|---|---|
| `text_similarity_available` | was there enough text on both sides |
| `text_similarity_raw` | cosine similarity, 0.0-1.0 |
| `text_similarity_score` | `raw * 100` |
| `shared_text_terms` | the actual overlapping words that drove the score |

Coverage: 160/160 (every project has at least a name). Range: 0.00-31.60.

**Fixed after a code review caught it:** the first version left voltage digits
in project names, reasoning the effect was minor. It wasn't. `DUKE-P0313`
("...230 kV Line") vs `TECO-230037` ("...138/230 kV...") shared only 3 text
terms, and 2 of them - `"230"` and `"kv"` - were the voltage figure, not word
choice; `voltage_similarity` was separately scoring that same 230kV match as
100. `normalize_text` now strips any number directly adjacent to "kv" before
vectorizing (`analysis.similarity.VOLTAGE_TOKEN`), confirmed against the real
data: zero pairs now have a bare voltage number in `shared_text_terms`.

**The remaining limitation, by design:** TECO's 11 transmission-upgrade names
are near-identical templates ("Transmission Upgrades-69 kV-66833"), so raw
text similarity alone underrates genuinely similar projects when Duke's name
is long and place-heavy. Concrete example in this data: `DUKE-P0062`
(Brooksville West, Mondon Hill, Bushnell East) vs `TECO-230037` scores only
11.23 on text, despite being the *same project type with overlapping
voltage* - `infrastructure_similarity` for that same pair is 100. That gap is
not a bug - it's exactly why infrastructure similarity is a **separate,
independent column** and not folded into the text score. Read both, always.

**Missing text is never a Python falsy check.** `build_project_text` and
`build_corpus` use `is_missing()`, not `if value:` - `float('nan')` is truthy
in Python, so a naive check would have written the literal text `"nan nan"`
into the corpus for any project missing both a name and a type, silently
reporting `text_similarity_available=True` on garbage. Doesn't occur on this
dataset (every one of the 26 projects has both fields), but a second utility
or a partially-filled record could have hit it without this guard.

**An all-missing or stop-word-only corpus degrades instead of crashing.**
`fit_tfidf` catches scikit-learn's "empty vocabulary" `ValueError` and returns
an empty lookup, so every pair correctly reports `text_similarity_available =
False` instead of the whole Task 4 script stopping mid-run.

### Infrastructure similarity

| column | meaning |
|---|---|
| `project_type_similarity` | 100 = same normalized type, 0 = different, `null` = either missing/unknown |
| `voltage_similarity` | 100 = overlapping range/class, lower = further apart, `null` = voltage unknown on either side |
| `infrastructure_similarity` | weighted average of the two above, reweighted when one is missing |
| `infrastructure_similarity_available` | was any structured comparison possible at all |

Weights: project type 50%, voltage 35% (TASK_4's own recommended prototype
starting point; PROJECT_SPEC defines no numeric weights for this component).
**`line_type` and `AC/DC` are not in this file at all** - checked directly
against the raw Our Grid Future workbook: both columns are blank for every one
of the 10 Duke projects used, and TECO's schema never had them. Rather than
ship an always-null column pretending to compare something never measured,
they're left out entirely. If a source ever populates them, add a function to
`analysis/infrastructure.py` the same way `project_type`/`voltage` are done.

Voltage rule (gap in kV between the two projects' nominal ranges; overlapping
ranges always score 100 regardless of gap size):

```
overlap -> 100      gap <= 75 kV -> 70      gap <= 150 kV -> 40      gap > 150 kV -> 15
```

Coverage: 160/160 have `project_type_similarity` (always populated).
110/160 have `voltage_similarity` - the other 50 are Duke x TECO-substation
-hardening pairs, where TECO's substation projects carry no voltage figure at
all (real gap, not a bug: substation hardening work isn't filed with a
voltage class the way circuit upgrades are).

### similarity_confidence

Describes **evidence available**, not similarity strength. A pair can be
`HIGH` confidence and near-zero similarity - that means "confidently
dissimilar," not "we don't know."

```
text + type + voltage all available -> HIGH   (110 pairs)
text + type only (voltage missing)   -> MEDIUM (50 pairs)
```

LOW/UNKNOWN never occur in this dataset (every project has a name and a
type), but the function handles them generally - see `tests/test_infrastructure.py`.

## Rebuilding Task 4

```bash
python scripts/build_similarity_features.py
python tests/test_similarity.py
python tests/test_infrastructure.py
python tests/test_pair_similarity_integrity.py
```
