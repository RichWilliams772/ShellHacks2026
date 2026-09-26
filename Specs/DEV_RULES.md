# GridSync Development Rules

## Purpose

This file defines the development and collaboration rules for the GridSync hackathon project.

**Goal:** let three developers and their AI coding agents work in parallel without destabilizing the project or overengineering the solution.

This is a **24-hour hackathon project**. Favor working software, clear interfaces, small changes, and fast integration over production-grade architecture.

---

## 1. Source of Truth

All contributors and AI agents must read these files before making significant changes:

1. `PROJECT_SPEC.md` — authoritative product scope and architecture.
2. The relevant `TASK_X.md` — authoritative scope for the current task.
3. `DEV_RULES.md` — authoritative collaboration and development rules.

If a task conflicts with the project specification, stop and surface the conflict instead of silently changing the architecture.

Do not add features simply because they seem useful. MVP requirements take priority over stretch features.

---

## 2. Repository Structure

Keep the repository simple:

```text
GridSync/
├── PROJECT_SPEC.md
├── DEV_RULES.md
├── AGENTS.md
├── README.md
├── TASK_1_TECO_GEOGRAPHY.md
├── data/
│   ├── raw/
│   └── processed/
├── analysis/
├── backend/
├── frontend/
└── tests/
```

Do not reorganize the repository without a clear reason agreed on by the team.

Do not create unnecessary services, packages, abstraction layers, or nested folder structures.

---

## 3. Branch Strategy

`main` is the shared stable integration branch.

Nobody should perform normal development directly on `main`.

Use three primary workstream branches:

```text
main
├── feature/data-analysis
├── feature/backend-api
└── feature/frontend-dashboard
```

### Ownership

#### `feature/data-analysis`
Owns:
- dataset ingestion and normalization
- TECO geography enrichment
- Duke/TECO project records
- geographic calculations
- temporal overlap
- project similarity
- coordination scoring
- shared-resource rules
- analysis tests

#### `feature/backend-api`
Owns:
- FastAPI application
- Pydantic models
- API endpoints
- loading processed data
- integration with analysis functions
- response/error handling
- LLM integration only after the core API works

#### `feature/frontend-dashboard`
Owns:
- Next.js application
- dashboard
- map
- project visualization
- opportunity cards
- filters
- Coordination Package UI
- loading/error states

Avoid editing files owned by another workstream unless necessary and communicated to that teammate.

---

## 4. Branch Workflow

Before starting work:

```bash
git checkout main
git pull origin main
git checkout feature/<your-workstream>
git merge main
```

Commit small, understandable changes:

```bash
git add .
git commit -m "Add TECO circuit geography enrichment"
git push origin feature/data-analysis
```

Do not wait until the end of the hackathon to push.

Push regularly so work is backed up and visible to teammates.

---

## 5. Pull Requests and Merging

Completed, usable increments should be merged into `main` through a pull request.

For this hackathon, PR review should be fast:

1. Does it run?
2. Does it follow `PROJECT_SPEC.md`?
3. Does it follow the frozen interfaces?
4. Does it break another workstream?
5. Does it introduce unnecessary complexity?

If those checks pass, merge it.

Prefer **Squash and Merge** to keep `main` readable.

Do not introduce heavyweight approval processes, merge queues, release branches, or GitFlow.

After another workstream merges into `main`, sync it into your branch:

```bash
git checkout main
git pull origin main

git checkout feature/<your-workstream>
git merge main
```

For this hackathon, prefer straightforward merges over complicated rebase workflows unless the developer is comfortable resolving them.

---

## 6. Protect `main`

Recommended GitHub settings:

- prevent force pushes to `main`
- prevent deletion of `main`
- prefer pull requests before merging

Do **not** require unnecessary hackathon bureaucracy such as:

- multiple mandatory reviewers
- signed commits
- merge queues
- complex deployment gates
- large CI matrices

Protection should prevent accidents, not slow the team down.

---

## 7. Freeze Interfaces Early

The team should agree on data and API contracts before each component is complete.

The frontend must **not** wait for the backend.

The backend must **not** wait for the final analysis engine.

Build against agreed mock data.

Example opportunity contract:

```json
{
  "project_a": {
    "id": "DUKE-0288",
    "utility": "Duke Energy",
    "name": "North Central Florida Upgrade Project"
  },
  "project_b": {
    "id": "TECO-66833",
    "utility": "Tampa Electric",
    "name": "Transmission Upgrade 66833"
  },
  "analysis": {
    "distance_miles": 18.4,
    "schedule_overlap_months": 7,
    "similarity_score": 0.84,
    "coordination_score": 87
  },
  "shared_resources": [
    "specialized_line_crews",
    "heavy_equipment",
    "outage_planning"
  ],
  "location_confidence": "HIGH"
}
```

If this contract changes, communicate it to all three workstreams immediately.

Do not independently invent incompatible schemas.

---

## 8. Component Boundary

Target integration flow:

```text
Data / Analysis
    |
    | analyze_projects(...)
    v
structured Python result
    |
    v
FastAPI
    |
    | JSON
    v
Frontend Dashboard
```

Person 1 should expose analysis through a simple callable interface.

Person 2 should convert that result into the agreed API response.

Person 3 should consume that response without needing to understand the internals of the analysis engine.

Keep these boundaries simple.

---

## 9. AI Coding Agent Rules

Cursor, Claude Code, Codex, or another coding agent must follow the same ownership boundaries as human developers.

Before coding, the agent must:

1. Read `PROJECT_SPEC.md`.
2. Read `DEV_RULES.md`.
3. Read the relevant `TASK_X.md`.
4. Inspect the existing repository before proposing structural changes.
5. Implement the minimum change required for the current task.

Agents must not independently redesign the architecture.

Do not let multiple agents edit the same files simultaneously.

If two agents are needed for the same workstream, use separate branches or Git worktrees.

Example:

```bash
git worktree add ../gridsync-claude -b task/claude-analysis
```

Recommended agent workflow:

```text
Claude/Cursor implements
        ↓
run tests
        ↓
human inspects
        ↓
optional second agent reviews
        ↓
fix confirmed issues
        ↓
PR to main
```

Do not create agent-to-agent complexity unless it saves meaningful time.

---

## 10. Anti-Overengineering Rules

This is one of the highest-priority sections of this document.

Use the simplest technology that satisfies the MVP.

### Preferred

- Python
- Pandas
- scikit-learn
- FastAPI
- Pydantic
- CSV / JSON
- simple SQLite only if persistence becomes useful
- Next.js
- TypeScript
- Tailwind
- Mapbox or Leaflet

### Do not introduce unless absolutely required

- Kubernetes
- Kafka
- Spark
- Airflow
- microservices
- PostGIS
- graph databases
- vector databases
- RAG pipelines
- distributed queues
- event-driven architecture
- complicated cloud infrastructure
- generalized ETL frameworks
- generalized GIS platforms
- custom authentication
- premature caching
- premature optimization
- unnecessary design patterns

Do not build infrastructure for hypothetical future requirements.

Do not create abstractions until there is an actual repeated problem worth abstracting.

A 50-line clear implementation is preferable to a 300-line extensible framework for this hackathon.

---

## 11. Data Integrity Rules

Never invent project data.

Never invent coordinates.

Never convert missing values to `0` unless zero is actually known.

Keep provenance for enriched data where practical.

For geographic enrichment, retain fields such as:

```text
location_source
location_confidence
```

If only project endpoints are known, a straight line between them may be used for visualization **only if it is explicitly labeled as an approximate project corridor**.

Do not claim an approximate corridor is the physical transmission-line route.

Do not silently replace uncertain data with guesses.

---

## 12. Analysis Rules

Deterministic calculations should remain deterministic.

Use code for:

- geographic distance
- schedule overlap
- date differences
- voltage differences
- filtering
- resource-rule matching

Use ML for similarity/opportunity discovery where appropriate.

For the MVP, TF-IDF + cosine similarity is acceptable.

Do not train a supervised `SHOULD_COORDINATE` model because the project does not have defensible historical coordination labels.

The LLM must not calculate project distance, invent resources, or determine factual eligibility.

Pipeline:

```text
projects
   ↓
deterministic calculations
   ↓
ML similarity
   ↓
resource rules
   ↓
structured opportunity
   ↓
optional LLM explanation
```

Algorithms produce facts.

ML produces similarity signals.

Rules produce potential resource-sharing categories.

The LLM explains already-computed evidence.

---

## 13. Scoring Must Be Explainable

Every Coordination Score displayed to the user should be explainable using its component signals.

Prototype weighting may use:

```text
Geographic proximity:     40%
Schedule overlap:         30%
Project similarity:       20%
Infrastructure similarity:10%
```

These are hackathon prototype weights, not industry standards.

Keep them configurable and clearly described as heuristic.

The UI should expose evidence such as:

```text
18 miles apart
7-month construction overlap
similar transmission work
same/similar voltage class
84% text similarity
```

Do not present the Coordination Score as an authoritative utility-planning decision.

---

## 14. Do Not Estimate Unsupported Savings

GridSync identifies **potential coordination/resource-sharing opportunities**.

Do not invent dollar savings, labor savings, outage reductions, or efficiency percentages without a defensible source and calculation.

Prefer language such as:

> Potential opportunity to coordinate specialized crews, equipment mobilization, material logistics, or outage planning.

The planner makes the final decision.

---

## 15. Testing Expectations

Tests should focus on things likely to break the demo.

Prioritize tests for:

- project normalization
- circuit joins
- coordinate validity
- geographic distance
- temporal overlap
- scoring boundaries
- API response shape
- critical frontend rendering

Do not spend hackathon time chasing exhaustive test coverage percentages.

Before merging, verify the changed feature actually runs.

---

## 16. Integration Milestone

By roughly the halfway point, stop adding unrelated features and establish one complete vertical slice:

```text
real Duke project
      +
real TECO project
      ↓
analysis
      ↓
FastAPI
      ↓
JSON
      ↓
frontend map
      ↓
Coordination Score
      ↓
Coordination Package
```

A working end-to-end slice is more valuable than three sophisticated disconnected components.

Once this works, improve the model, UI, LLM explanation, and presentation.

---

## 17. Communication Rules

Communicate immediately when:

- changing a shared schema
- renaming shared fields
- changing an API endpoint
- moving shared files
- changing dependencies used by another workstream
- discovering bad source data
- changing scoring logic
- merging something another teammate depends on

Do not silently make cross-team breaking changes.

Short messages are enough:

```text
Merged TECO geography enrichment to main.
Adds from_lat/from_lon/to_lat/to_lon/location_confidence.
Backend can pull now.
```

---

## 18. Commit Guidelines

Use understandable commit messages:

```text
Add TECO circuit geography enrichment
Add Haversine project distance calculation
Expose analyze endpoint
Add opportunity map markers
Fix missing schedule handling
```

Avoid meaningless commits such as:

```text
stuff
changes
update
fix
asdf
```

Small commits are easier to inspect and recover during a hackathon.

---

## 19. Dependency Rules

Before adding a dependency, ask:

1. Can the existing stack already do this?
2. Does this dependency save meaningful hackathon time?
3. Will teammates need additional setup because of it?

Do not add a large framework for one small function.

If adding a dependency, update the appropriate dependency file immediately.

---

## 20. Definition of Done for a Task

A task is done when:

- the requested functionality works
- it follows the agreed interface
- relevant tests pass
- no known critical regression was introduced
- source/provenance requirements are respected
- code is pushed
- the teammate can explain what changed in 1–3 sentences

A task is **not** waiting for production-level perfection.

---

## 21. Stop Conditions

Stop expanding a task when its acceptance criteria are satisfied.

Do not continue adding:

- abstractions
- additional models
- extra endpoints
- new data sources
- extra UI modes
- infrastructure
- refactors

unless they directly unblock the MVP or demo.

When uncertain, choose the smaller implementation.

---

## 22. Hackathon Priority Order

When tradeoffs appear, use this priority order:

```text
1. Correct real data
2. Working end-to-end demo
3. Explainable analysis
4. Reliable integration
5. Clear UI
6. Demo/pitch polish
7. Stretch features
8. Architectural elegance
```

**A simple system that works from real data to a polished demo beats a sophisticated system that is only partially connected.**
