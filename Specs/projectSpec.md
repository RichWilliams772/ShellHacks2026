GridSync — Project Specification

Source of truth for Cursor, Claude Code, and human contributors.

1. Project Overview

GridSync is an intelligent utility infrastructure coordination platform that analyzes publicly available future electric-utility construction plans and identifies potential coordination opportunities between neighboring utilities.

Tagline

Find where the grid can build together.

Core Problem

Utilities plan major infrastructure projects years in advance, but neighboring utilities may have limited visibility into similar projects occurring nearby or during overlapping construction periods.

GridSync identifies these overlaps and helps planners understand:

1. WHERE projects are geographically close.
2. WHEN construction schedules overlap.
3. WHAT projects involve similar infrastructure.
4. WHAT RESOURCES may be worth coordinating.

GridSync provides decision support.

It does not determine whether utilities should coordinate.

⸻

2. Hackathon Constraint

Development time: approximately 24 hours.

Prioritize:

1. Working end-to-end demo
2. Real public data
3. Correct calculations
4. Explainable results
5. Visual presentation
6. ML functionality
7. AI assistant
8. Stretch features

When choosing between:

complex + impressive

and

simple + working + explainable

always choose:

simple + working + explainable

⸻

3. MVP Utilities

The initial implementation compares:

* Duke Energy Florida
* Tampa Electric / TECO

The architecture should support additional utilities later, but nationwide coverage is NOT an MVP requirement.

⸻

4. Public Data Sources

Dataset A — Our Grid Future Planned Transmission Database

Purpose:

WHERE

Primary source for geographic information about planned transmission infrastructure.

Use for:

* Transmission project geometry
* Geographic location
* Project routes
* Voltage
* Project type
* Project status
* Geographic proximity calculations
* Map visualization

Available formats include:

* XLSX
* GIS shapefile

Source:

https://ourgridfuture.org/

This should be the primary geospatial backbone.

⸻

Dataset B — Duke Energy Florida / Florida PSC Filings

Purpose:

WHAT + WHEN

Use public Florida Public Service Commission filings to enrich Duke projects with available attributes such as:

* Project name
* Project identifier
* Project type
* Start date/year
* Completion date/year
* Voltage
* Capital cost
* Location
* Description
* Customers impacted

Not every field will exist for every project.

Source:

https://www.psc.state.fl.us/

⸻

Dataset C — Tampa Electric / Florida PSC Filings

Purpose:

WHAT + WHEN

Use Tampa Electric planning filings for:

* Project name/ID
* Construction category
* Start/end period
* Capital expenditure
* Infrastructure characteristics
* Transmission asset upgrades
* Substation projects
* Hardening projects

Primary planning source:

https://www.psc.state.fl.us/library/filings/2025/06533-2025/06533-2025.pdf

⸻

Dataset D — Utility Territory GIS

Purpose:

WHO NEIGHBORS WHOM

Use for:

* Utility service boundaries
* Geographic context
* Shared utility boundaries
* Future neighboring-utility discovery

Source:

https://ourgridfuture.org/

This dataset is optional for the MVP.

⸻

5. Data Availability Constraints

Do NOT assume all projects contain:

* Exact coordinates
* Exact dates
* Capital cost
* Detailed descriptions
* Voltage
* Customers impacted

The system MUST tolerate missing data.

Core features

Prioritize fields with stronger availability:

* Geographic location/geometry
* Schedule or project status
* Project type
* Voltage

Optional enrichment

Use when available:

* Cost
* Detailed description
* Customers impacted
* Additional infrastructure attributes

Do NOT make the analysis dependent on optional enrichment fields.

⸻

6. Data Provenance

Every project must retain its public source.

Minimum:

source_name
source_url

Prefer:

source_document
source_page
retrieved_date

Never present synthetic/demo records as verified public utility records.

Any fallback synthetic data must explicitly contain:

data_type = "demo"

⸻

7. Canonical Project Schema

Normalize utility data into:

{
  "id": "DUKE-001",
  "utility": "Duke Energy Florida",
  "project_name": "Transmission Upgrade",
  "project_type": "transmission_upgrade",
  "description": null,
  "voltage_kv": 230,
  "latitude": 28.5,
  "longitude": -81.3,
  "geometry": null,
  "start_date": "2027-01-01",
  "end_date": "2028-03-01",
  "status": "planned",
  "capital_cost": null,
  "customers_impacted": null,
  "source_name": "Florida Public Service Commission",
  "source_url": "...",
  "data_type": "public"
}

Optional values may be null.

Missing values must NOT be interpreted as zero.

⸻

8. Core System Architecture

PUBLIC UTILITY DATA
        ↓
DATA INGESTION
        ↓
NORMALIZATION
        ↓
CANONICAL PROJECT DATASET
        ↓
CROSS-UTILITY PAIR GENERATION
        ↓
┌───────────────────────────────┐
│ Geographic Engine             │
│ Temporal Engine               │
│ Similarity Engine             │
│ Infrastructure Comparison     │
└───────────────────────────────┘
        ↓
FEATURE VECTOR
        ↓
ML / SIMILARITY ANALYSIS
        ↓
COORDINATION SCORE
        ↓
RESOURCE RULES ENGINE
        ↓
COORDINATION PACKAGE
        ↓
REST API
        ↓
INTERACTIVE DASHBOARD
        ↓
OPTIONAL AI ASSISTANT

⸻

9. Recommended Stack

Frontend

* Next.js
* TypeScript
* Tailwind CSS

Map

Preferred:

* Mapbox

Fallback:

* Leaflet

Backend

* Python
* FastAPI
* Pydantic
* Pandas

Geographic Analysis

* GeoPandas
* Shapely
* Haversine/geodesic calculations

Machine Learning

* scikit-learn
* TF-IDF
* cosine similarity

Storage

Prefer simplicity:

* CSV
* JSON
* SQLite

Supabase/PostgreSQL may be used if already convenient.

Do NOT spend significant hackathon time building database infrastructure.

⸻

10. Pair Generation

GridSync compares:

Duke project
      ×
TECO project

Never compare:

Duke ↔ Duke
TECO ↔ TECO

Each pair becomes an analysis observation.

Example:

{
  "project_a": "DUKE-001",
  "project_b": "TECO-014"
}

Apply coarse filtering before expensive processing.

Extremely distant and temporally irrelevant pairs may be discarded.

Thresholds must be configurable constants.

⸻

11. Geographic Engine

Geographic calculations must be deterministic.

The LLM must NEVER calculate distances.

For point projects calculate:

distance_miles
distance_km

For transmission route geometry, use Shapely/GeoPandas when practical.

Prototype interpretation:

0–10 miles
Very strong geographic proximity
10–25 miles
Strong proximity
25–50 miles
Moderate proximity
50+ miles
Weak proximity

These are GridSync prototype heuristics.

They are NOT official utility-industry thresholds.

⸻

12. Temporal Engine

Calculate:

start_date_difference
end_date_difference
overlap_days
overlap_months
schedule_overlap_ratio

Where only years are available, support year-level temporal comparison.

Example:

Project A
2027 ───────────── 2028
Project B
      2027 ───────────── 2029
          ↓
Construction periods overlap.

The LLM must NEVER independently calculate schedule overlap.

⸻

13. Infrastructure Similarity

Compare available:

project_type
voltage_kv
status

Optional:

capital_cost
customers_impacted

Generate features such as:

project_type_similarity
voltage_similarity
status_similarity

Missing optional attributes should receive neutral treatment rather than automatically lowering a score.

⸻

14. NLP Similarity

NLP is an enrichment feature.

When sufficient project text exists, combine:

project_name
project_type
description

Use:

TF-IDF + cosine similarity

Return:

text_similarity = 0.0–1.0

Example:

Project A:

Reconductor existing 230 kV transmission corridor.

Project B:

Replace conductors along existing 230 kV transmission line.

Expected:

Relatively high similarity.

If descriptions are unavailable, the analysis MUST still function.

Do NOT make NLP mandatory for a valid opportunity.

⸻

15. ML Strategy

There is no validated public label representing:

SHOULD_COORDINATE = TRUE/FALSE

Therefore:

DO NOT train a supervised coordination classifier.

DO NOT claim the system predicts successful coordination.

GridSync performs:

opportunity discovery

using engineered project-pair features.

Core feature vector:

{
  "distance_similarity": 0.91,
  "schedule_similarity": 0.82,
  "project_type_similarity": 1.0,
  "voltage_similarity": 0.90
}

Optional:

{
  "text_similarity": 0.76,
  "cost_similarity": 0.63
}

Possible unsupervised/similarity techniques:

* Feature normalization
* Nearest-neighbor similarity
* Clustering

Keep ML interpretable.

Do NOT add ML simply for complexity.

⸻

16. Coordination Opportunity Score

Return:

0–100

Initial prototype weighting:

Geographic proximity        40%
Schedule overlap            30%
Project similarity          20%
Infrastructure similarity   10%

Store weights in configuration.

Do NOT hard-code them into frontend components.

Optional features should adjust available evidence without penalizing missing data.

The score represents:

strength of potential coordination opportunity

It does NOT represent:

* Probability of coordination
* Probability of success
* Expected savings
* Financial ROI

⸻

17. Explainability

Every opportunity MUST explain its score.

Example:

COORDINATION SCORE
92 / 100
WHY THIS MATCHED
✓ Projects are 14.7 miles apart.
✓ Construction schedules overlap for approximately 8 months.
✓ Both involve transmission infrastructure.
✓ Both operate at similar voltage levels.

When NLP is available:

✓ Project descriptions show high construction similarity.

Reasons must come from structured analysis.

The LLM is not required to generate these explanations.

⸻

18. Standout Feature — Coordination Package

Finding overlap alone is insufficient.

GridSync should also answer:

What might these utilities actually coordinate?

For high-quality matches, generate a:

Coordination Package

Example:

POTENTIAL COORDINATION AREAS
👷 Specialized line crews
HIGH
🏗 Heavy equipment
HIGH
🚚 Material logistics
MEDIUM
⚡ Outage planning
MEDIUM

⸻

19. Resource Rules Engine

Potential resources must originate from deterministic mappings.

Example:

RESOURCE_RULES = {
    "transmission_upgrade": [
        "specialized_line_crews",
        "heavy_equipment",
        "material_logistics",
        "outage_planning"
    ],
    "substation_upgrade": [
        "electrical_crews",
        "cranes",
        "transformer_logistics",
        "outage_planning"
    ],
    "undergrounding": [
        "excavation_crews",
        "trenching_equipment",
        "traffic_control",
        "material_logistics"
    ]
}

Compare:

Project A potential resources
INTERSECTION
Project B potential resources
        ↓
Potential Shared Resources

The LLM must NOT invent required resources.

⸻

20. Resource Opportunity Strength

Resources may be classified:

HIGH
MEDIUM
LOW

Use deterministic evidence.

Example:

HIGH
if:
similar project type
AND
distance < configured threshold
AND
meaningful schedule overlap

All rules should remain configurable and explainable.

⸻

21. LLM Role

The LLM sits ABOVE the analysis system.

User
 ↓
LLM
 ↓
GridSync tools
 ↓
Structured analysis
 ↓
LLM explanation

The LLM MAY:

* Answer questions about existing results
* Summarize opportunities
* Explain structured evidence
* Translate technical analysis into plain language
* Filter/query opportunities
* Select GridSync analysis functions

The LLM MUST NOT independently determine:

* Geographic distance
* Schedule overlap
* Project cost
* Coordination score
* Shared resource eligibility
* Savings
* Required infrastructure

⸻

22. AI Assistant

AI Assistant is secondary to the core MVP.

Example questions:

Show me the strongest opportunities.
Show projects within 25 miles.
Which projects overlap in 2028?
Why did GridSync match these projects?
What resources could these projects potentially coordinate?
Show only transmission upgrades.

The assistant should query structured GridSync results.

Do NOT build autonomous web browsing into the MVP assistant.

⸻

23. API Requirements

Required:

GET /health
GET /utilities
GET /projects
GET /projects/{id}
GET /opportunities
GET /opportunities/{id}
POST /analyze

Optional:

POST /assistant/query

⸻

24. Analyze Endpoint

Request:

{
  "utility_a": "Duke Energy Florida",
  "utility_b": "Tampa Electric"
}

Response:

{
  "projects_analyzed": 150,
  "pairs_evaluated": 3200,
  "opportunities": [
    {
      "project_a": {},
      "project_b": {},
      "features": {
        "distance_miles": 14.7,
        "schedule_overlap_months": 8,
        "project_type_similarity": 1.0,
        "voltage_similarity": 0.92,
        "text_similarity": 0.84
      },
      "coordination_score": 92,
      "reasons": [],
      "coordination_package": {}
    }
  ]
}

⸻

25. Dashboard Requirements

Primary screen must include:

Header

GridSync

Find where the grid can build together.

Utility Comparison

Duke Energy Florida
↕
Tampa Electric
[Analyze Opportunities]

KPI Cards

Display:

Projects Analyzed
Potential Matches
High-Opportunity Matches
Utilities Compared

Main Map

Display both utilities.

Ranked Opportunities

Example:

#1
Duke Transmission Upgrade
↕
TECO Transmission Upgrade
14.7 miles apart
8-month overlap
92 / 100
[View Opportunity]

⸻

26. Map Requirements

Projects from different utilities must be visually distinguishable.

When selecting an opportunity:

1. Highlight Project A.
2. Highlight Project B.
3. Draw a visual connection where practical.
4. Display distance.
5. Open opportunity details.

If GIS transmission routes are available, display routes when practical.

Do not sacrifice application stability for advanced map rendering.

⸻

27. Opportunity Detail Panel

Display:

Project A
Project B
Coordination Score
Geographic Distance
Schedule Overlap
Infrastructure Similarity
ML Similarity if available
Why This Matched
Coordination Package
Public Data Sources

⸻

28. Filters

MVP filters:

Year
Project type
Maximum distance
Minimum coordination score

⸻

29. Upload Feature

STATUS:

STRETCH

Potential future workflow:

PDF / CSV / XLSX
       ↓
Extraction
       ↓
Normalization
       ↓
Validation
       ↓
GridSync Schema
       ↓
Analysis

Do NOT implement this before the core MVP is stable.

⸻

30. Explicit Non-Goals

Do NOT build for the hackathon MVP:

* Production authentication
* Enterprise accounts
* Nationwide ingestion
* Automatic regulatory monitoring
* Complex PDF ingestion
* Kubernetes
* Microservices
* Vector database unless absolutely necessary
* Custom neural networks
* Deep learning
* Financial savings predictions
* Resource scheduling
* Contractor marketplace
* Production-grade utility recommendations

⸻

31. Major Constraints and Trade-Offs

Real Data vs Perfect Data

Choose:

real imperfect public data

over:

perfect synthetic data

⸻

Explainable ML vs Complex ML

Choose:

explainable similarity analysis

over:

black-box prediction

⸻

Preloaded Data vs Upload

Choose:

preloaded Duke + TECO

for MVP.

Upload is stretch.

⸻

Deterministic Algorithms vs LLM

Use deterministic code for:

distance
dates
overlap
scores
resource rules

Use ML for:

similarity
pattern discovery

Use LLM for:

interaction
summarization
explanation

⸻

32. Testing

At minimum test:

Geographic Engine

Known coordinates should produce expected approximate distances.

Temporal Engine

Test:

* Full overlap
* Partial overlap
* No overlap
* Identical dates
* Year-only dates

Similarity

Similar project descriptions should score higher than unrelated descriptions.

Resource Engine

Known project types should produce expected resource intersections.

Scoring

Identical feature vectors must always produce identical scores.

Missing Data

Missing optional values must not crash analysis.

⸻

33. Development Order

Phase 1 — Data

Produce:

duke_projects.csv
teco_projects.csv

using real public data.

Validate fields and provenance.

⸻

Phase 2 — Analysis Engine

Implement independently:

geographic.py
temporal.py
similarity.py
scoring.py
resources.py

Write tests.

⸻

Phase 3 — API

Expose the engine through FastAPI.

POST /analyze must work before advanced frontend development.

⸻

Phase 4 — Dashboard

Implement:

* Utility comparison
* Analyze button
* KPIs
* Opportunity ranking

⸻

Phase 5 — Map

Add project visualization and selected-pair highlighting.

⸻

Phase 6 — Coordination Package

Display potential shared resources.

⸻

Phase 7 — Polish

Focus on:

* Loading states
* Error states
* Visual hierarchy
* Demo reliability
* Explainability
* Source attribution

⸻

Phase 8 — AI Assistant

Only after the primary application works.

⸻

Phase 9 — Stretch

Only after the demo is stable.

⸻

34. MVP Definition of Done

The MVP is complete when:

* Real Duke data loads.
* Real TECO data loads.
* Data follows one canonical schema.
* Public data provenance is retained.
* Projects appear on a map.
* Cross-utility project pairs are generated.
* Geographic proximity works.
* Temporal overlap works.
* Infrastructure similarity works.
* NLP similarity works when text is available.
* Missing NLP text does not break analysis.
* Coordination scores are generated.
* Opportunities are ranked.
* Every score is explainable.
* Coordination Package works.
* Public sources are visible.
* Missing optional data does not crash the application.
* Complete demo flow works reliably.

AI Assistant is desirable but NOT required for MVP completion.

⸻

35. Rules for Cursor and Claude Code

Before making changes:

1. Read PROJECT_SPEC.md.
2. Identify the requirement being implemented.
3. Inspect existing code.
4. Preserve working functionality.
5. Make the smallest reasonable implementation.

DO NOT:

* Change architecture without justification.
* Rewrite unrelated working code.
* Invent public utility data.
* Add unnecessary dependencies.
* Implement stretch features before MVP.
* Replace deterministic calculations with LLM calls.
* Claim unsupported financial savings.
* Train a supervised model without labels.
* Hide scoring logic.
* Treat missing values as zero.

After implementation:

1. Run relevant tests.
2. Run linting/type checking.
3. Verify existing functionality.
4. Report files changed.
5. Report tests performed.
6. Report any unresolved limitations.

⸻

36. Agent Workflow

When assigned a feature, follow:

READ SPEC
   ↓
UNDERSTAND REQUIREMENT
   ↓
INSPECT CURRENT IMPLEMENTATION
   ↓
IMPLEMENT MINIMUM SOLUTION
   ↓
TEST
   ↓
VERIFY INTEGRATION
   ↓
REPORT RESULT

Do not independently move to unrelated tasks.

⸻

37. Final Demo Story

The demo should communicate:

Utilities publish future construction plans, but discovering where neighboring projects overlap is difficult because planning information is fragmented.

Select:

Duke Energy Florida ↔ Tampa Electric

Click:

Analyze Opportunities

GridSync analyzes real public project information.

The map reveals nearby projects.

Open a high-scoring pair.

Show:

92 / 100
14.7 miles apart
8-month construction overlap
Similar transmission infrastructure

Then show:

Coordination Package

Potential coordination areas:
Specialized crews
Heavy equipment
Material logistics
Outage planning

Explain:

GridSync doesn’t decide whether utilities should coordinate. It surfaces opportunities that planners may otherwise have difficulty discovering across fragmented planning data.

If AI Assistant is implemented, finish by asking:

“Show me the strongest transmission coordination opportunities before 2030.”

⸻

38. Final Product Principle

GridSync should not attempt to replace utility planners.

GridSync should make it dramatically easier for planners to discover:

where, when, and why cross-utility coordination may be worth investigating.