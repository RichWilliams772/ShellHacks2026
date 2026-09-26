# TASK 1 — Build TECO Project Geography Dataset

## Goal
Create the **minimum reliable TECO geography dataset** needed by GridSync to compare Tampa Electric (TECO) future transmission projects against Duke Energy projects.

This is a **data preparation task**, not a GIS platform project.

**Definition of success:** take TECO future projects from the Storm Protection Plan, match their circuit IDs to named transmission endpoints using TECO's FERC Form 1 / public records, attach defensible coordinates where available, and output a clean file that GridSync's analysis engine can consume.

Do not overengineer this task.

---

## Project Context

GridSync compares public future construction plans from neighboring electric utilities and identifies potential coordination opportunities based on:

1. Geographic proximity
2. Schedule overlap
3. Project similarity
4. Infrastructure similarity

For the MVP, the utilities are:

- Duke Energy Florida
- Tampa Electric Company (TECO)

The Duke/Our Grid Future dataset already provides strong project and substation geography.

The missing problem is TECO geography.

### Available data

**Dataset 1 — Our Grid Future**
- Duke and other planned transmission projects
- Project/substation information
- Substation latitude/longitude
- File: `OurGridFuture_PlannedTransmissionProjects_Jun2026.xlsx`

**Dataset 2 — TECO Storm Protection Plan (SPP)**
- Future TECO transmission upgrade projects
- Circuit IDs
- Voltage
- Pole count
- Project/construction/end dates
- Cost
- File: `TECO.pdf`

**Dataset 3 — TECO FERC Form 1 / public transmission inventory**
- Existing transmission circuits
- From/to substations
- Voltage
- Line length where available
- Primary purpose: translate TECO circuit IDs into named geographic endpoints.

**Secondary geographic reference — TECO 2025 Ten-Year Site Plan**
- File: `Tampa Electric Company 2025.pdf`
- Useful for service-area and facility context.
- Do NOT treat it as the primary circuit-geography source because its Schedule 10 is focused on transmission directly associated with proposed generating facilities, not the full set of SPP hardening circuits.

---

# Primary Objective

Build this join:

```text
TECO SPP future project
        |
        | circuit_id
        v
TECO FERC Form 1 transmission inventory
        |
        | from/to substation names
        v
Known/public substation coordinates
        |
        v
Normalized TECO project geography
```

Example:

```text
Transmission Upgrades-69 kV-66833
              |
              v
Circuit 66833
              |
              v
South Eloise <-> Lake Silver
              |
              v
endpoint coordinates
              |
              v
GridSync geographic analysis
```

---

# Scope

Focus first on these **2026 TECO Transmission Asset Upgrade circuits** from the SPP:

```text
66833
230037
66653
66004
66655
66831
66651
66058
66012
138005
66835
```

Known project metadata from the TECO SPP includes examples such as:

| Circuit | Voltage | Pole Count |
|---|---:|---:|
| 66833 | 69 kV | 145 |
| 230037 | 138/230 kV | 1 |
| 66653 | 69 kV | 93 |
| 66004 | 69 kV | 66 |
| 66655 | 69 kV | 73 |
| 66831 | 69 kV | 1 |
| 66651 | 69 kV | 30 |
| 66058 | 69 kV | 7 |
| 66012 | 69 kV | 15 |
| 138005 | 138/230 kV | 2 |
| 66835 | 69 kV | 1 |

Do not manually duplicate SPP metadata if it can be extracted from the source file.

---

# Known Geography Leads

These are leads to verify against source data before using them as canonical records:

```text
66833   -> South Eloise <-> Lake Silver
230037  -> Gannon <-> Juneau
66653   -> South Eloise <-> Sandhill
66004   -> 11th Avenue <-> 14th Street
138005  -> Ohio <-> Clearview
```

**IMPORTANT:** These are starting leads, not permission to hard-code unverified facts. Preserve provenance for every match.

---

# Required Output

Create:

```text
data/processed/teco_projects_geocoded.csv
```

Minimum schema:

```text
project_id
utility
circuit_id
project_type
voltage_kv
pole_count
project_start
construction_start
project_end
project_cost
from_substation
to_substation
from_lat
from_lon
to_lat
to_lon
line_length_miles
location_method
location_confidence
project_source
geography_source
```

Use `Tampa Electric` or one consistent canonical utility value throughout the project.

### `location_method`

Allowed values should stay simple:

```text
exact_substation_endpoints
single_substation
approximate_service_area
unknown
```

Do not create an elaborate taxonomy.

### `location_confidence`

Use only:

```text
HIGH
MEDIUM
LOW
UNKNOWN
```

Recommended interpretation:

**HIGH**
- Circuit ID directly matches a public transmission record AND
- named endpoint(s) can be located using defensible public/structured data.

**MEDIUM**
- Project has a reliable named substation or corridor but incomplete endpoint/route information.

**LOW**
- Only approximate geography such as service area is known.

**UNKNOWN**
- No defensible geography was found.

Do not convert missing information into `0`.

---

# Implementation Steps

## 1. Extract TECO SPP projects

Extract the 2026 Transmission Asset Upgrade records from `TECO.pdf`.

Normalize the circuit number as a **string**, not an integer.

Example:

```python
circuit_id = "66833"
```

Retain the source metadata that is useful to GridSync:

```text
project_id
circuit_id
voltage_kv
pole_count
project_start
construction_start
project_end
project_cost
```

Do not build a general-purpose PDF ingestion framework.

A one-purpose extraction/cleaning script is sufficient.

---

## 2. Extract transmission circuit inventory

From the TECO FERC Form 1/public transmission inventory, create a small normalized lookup:

```text
circuit_id
from_substation
to_substation
voltage_kv
line_length_miles
source
```

Save it as:

```text
data/interim/teco_circuit_lookup.csv
```

If a circuit appears in multiple physical segments, preserve those rows during extraction.

Then create a project-level representation appropriate for GridSync.

Do NOT create a full electrical-network graph unless it becomes absolutely necessary to resolve a specific circuit.

---

## 3. Join SPP projects to circuit inventory

Primary join key:

```text
circuit_id
```

Normalize strings before matching:

```python
str(value).strip()
```

Do not use fuzzy matching on circuit IDs.

A circuit ID must match exactly.

Report unmatched circuits rather than guessing.

---

## 4. Resolve substation coordinates

Use this priority order:

### Priority 1 — Our Grid Future substation table

Search `Substations in Planned Projects` in:

```text
OurGridFuture_PlannedTransmissionProjects_Jun2026.xlsx
```

Use normalized substation names for matching.

Safe normalization can include:

- lowercase
- trim whitespace
- remove trailing `substation`
- normalize punctuation

Do not use aggressive fuzzy matching automatically.

If a fuzzy match is needed, surface it for manual verification rather than silently accepting it.

### Priority 2 — authoritative/public geographic source

If a TECO substation is absent from Our Grid Future, use an identifiable public source with coordinates or enough location information to geocode it.

Record that source in:

```text
geography_source
```

### Priority 3 — approximate geography

Only use service-area or approximate geography when exact endpoints cannot be found.

Mark these:

```text
location_confidence = LOW
```

The UI and scoring engine must be able to distinguish these from exact locations.

---

# Geographic Representation

For an exact endpoint match, store both endpoints.

Example:

```json
{
  "from_substation": "South Eloise",
  "from_lat": 27.98,
  "from_lon": -81.74,
  "to_substation": "Lake Silver",
  "to_lat": 28.03,
  "to_lon": -81.73
}
```

GridSync may derive a midpoint for visualization/fast comparison:

```python
mid_lat = (from_lat + to_lat) / 2
mid_lon = (from_lon + to_lon) / 2
```

Do not introduce PostGIS or a spatial database just to calculate this.

---

# Critical Geographic Constraint

## DO NOT claim endpoint-to-endpoint lines are the physical transmission route.

If the frontend draws:

```text
from_substation -------- to_substation
```

that is an **approximate project corridor**, not verified transmission-line geometry.

Name it accordingly in code and UI.

Good:

```text
approximate_corridor
endpoint_connection
```

Bad:

```text
actual_route
transmission_geometry
verified_line_path
```

unless actual GIS geometry is obtained.

For the MVP, endpoint coordinates and/or project midpoint are enough for proximity calculations.

---

# GridSync Geographic Distance

Do not train ML to calculate geography.

Geographic distance is deterministic.

For MVP use Haversine/geodesic distance between representative project locations.

If both endpoints are available, a simple first implementation may compare endpoint combinations and use the minimum distance:

```text
A.from <-> B.from
A.from <-> B.to
A.to   <-> B.from
A.to   <-> B.to
```

Then:

```text
project_distance = minimum(endpoint distances)
```

This is acceptable for the hackathon and is more defensible than pretending a straight line is the actual project route.

Do not implement computational geometry unless real line geometry is already available.

---

# Missing Data Rules

Missing data must remain missing.

Examples:

```text
unknown coordinate -> null
unknown line length -> null
unknown endpoint -> null
```

NEVER do:

```text
unknown line length -> 0
unknown distance -> 0
unknown cost -> 0
```

because zero has a real semantic meaning and would corrupt scoring.

The scoring system must ignore or reweight unavailable optional features rather than treating missing values as zeros.

---

# Provenance Requirements

Every geocoded project must retain enough information to explain where its location came from.

At minimum:

```text
project_source
geography_source
location_method
location_confidence
```

Example:

```text
project_source = "TECO 2026-2035 Storm Protection Plan"
geography_source = "TECO 2024 FERC Form 1 + Our Grid Future substations"
location_method = "exact_substation_endpoints"
location_confidence = "HIGH"
```

Do not invent citations, URLs, coordinates, endpoints, costs, dates, or circuit mappings.

---

# What NOT To Build

This section is mandatory.

Do **not** build any of the following for Task 1:

- PostGIS
- Neo4j
- graph database
- vector database
- embeddings
- LLM extraction pipeline
- RAG system
- autonomous research agent
- general-purpose PDF ingestion platform
- web scraper framework
- GIS tile server
- utility network simulator
- power-flow model
- custom geocoder
- supervised ML model
- route reconstruction algorithm
- complex fuzzy entity-resolution system
- production ETL orchestration
- Airflow
- Kafka
- Spark
- Kubernetes
- unnecessary database

For 11 projects, **Pandas + Python + CSV is enough**.

Prefer a 100-line clear script over a 1,000-line abstraction.

---

# Recommended File Structure

Keep it small:

```text
data/
  raw/
  interim/
    teco_circuit_lookup.csv
  processed/
    teco_projects_geocoded.csv

scripts/
  extract_teco_projects.py
  build_teco_geography.py

tests/
  test_teco_geography.py
```

Do not reorganize the repository if equivalent folders already exist.

Use the existing project structure whenever possible.

---

# Minimum Tests

Only test things that could materially break the demo.

### Test 1 — exact circuit join

```text
SPP circuit 66833
must never accidentally match another circuit.
```

### Test 2 — coordinate validity

For non-null coordinates:

```text
-90 <= latitude <= 90
-180 <= longitude <= 180
```

### Test 3 — missing values

Missing coordinates remain null rather than becoming zero.

### Test 4 — provenance

Every HIGH-confidence record must contain a non-empty `geography_source`.

### Test 5 — expected project count

The extraction should find the expected 2026 SPP transmission-upgrade records or explicitly report why the count differs.

Do not create a massive test suite for this task.

---

# Completion Criteria

Task 1 is DONE when:

1. 2026 TECO Transmission Asset Upgrade projects are extracted from the SPP.
2. Circuit IDs are normalized.
3. A Form 1/public circuit-to-substation lookup exists.
4. SPP projects are joined to that lookup.
5. Available endpoint coordinates are attached.
6. Every location has provenance and confidence.
7. Unresolved circuits remain explicitly unresolved.
8. `teco_projects_geocoded.csv` is produced.
9. Basic validation tests pass.
10. The resulting file can be loaded directly by the GridSync analysis engine.

**Do not block completion because all 11 projects are not geocoded.**

For the hackathon, a smaller number of HIGH-confidence real projects is preferable to fabricated or weak geography.

Target:

```text
5+ HIGH-confidence TECO projects = sufficient MVP
8+ HIGH-confidence TECO projects = excellent
11/11 = nice to have, NOT required
```

---

# Stop Condition

This task has a strict anti-overengineering stop condition.

Once we have enough HIGH-confidence TECO projects to produce meaningful Duke × TECO comparisons, stop data hunting and hand the dataset to the analysis/backend pipeline.

Do not spend hours resolving the final obscure circuit.

The hackathon product matters more than perfect data coverage.

---

# Instructions for Claude / Cursor Agent

Before changing code:

1. Read `PROJECT_SPEC.md`.
2. Read this file completely.
3. Inspect the repository structure.
4. Reuse existing code and dependencies where possible.
5. Identify the smallest implementation needed to satisfy the completion criteria.

While implementing:

- Work only on Task 1.
- Do not implement frontend features.
- Do not implement the LLM assistant.
- Do not redesign GridSync architecture.
- Do not add infrastructure unless required by this task.
- Do not replace deterministic geographic calculations with AI.
- Do not fabricate missing data.
- Preserve source provenance.
- Prefer simple Python/Pandas transformations.
- Keep functions small and readable.
- Add comments only where reasoning is not obvious.

If a source cannot support a field, leave the field null and continue.

If a circuit cannot be confidently mapped, output it as unresolved and continue.

Do not stop the entire pipeline because one project is incomplete.

---

# Agent Execution Order

```text
READ SPEC
   ↓
INSPECT EXISTING FILES/CODE
   ↓
EXTRACT SPP PROJECTS
   ↓
BUILD CIRCUIT LOOKUP
   ↓
EXACT JOIN ON CIRCUIT ID
   ↓
RESOLVE SUBSTATION COORDINATES
   ↓
ASSIGN CONFIDENCE + PROVENANCE
   ↓
VALIDATE
   ↓
WRITE teco_projects_geocoded.csv
   ↓
RUN TESTS
   ↓
REPORT MATCHED + UNMATCHED CIRCUITS
   ↓
STOP
```

Do not begin Task 2 or stretch features.

---

# Final Agent Report

When finished, report only:

- files created/modified
- number of TECO SPP projects extracted
- number matched to circuit records
- number with HIGH/MEDIUM/LOW/UNKNOWN geography confidence
- unresolved circuit IDs
- tests run and results
- any assumptions that materially affect GridSync

Do not claim unresolved data is solved.
