# GridSync

**Find where the grid can build together.**

GridSync compares Duke Energy Florida's and Tampa Electric's own public infrastructure
plans and surfaces pairs of nearby, similarly-timed projects that might be worth
coordinating — shared crews, shared equipment, shared outage windows. It's decision
support for utility planners, not an automated recommendation: GridSync scores how
strongly two projects' public data lines up and explains why; a human still decides
whether coordination makes sense.

Built in ~24 hours for ShellHacks 2026.

## What it does

- **Coordination scoring** — a deterministic pipeline scores every Duke × TECO project
  pair on geographic proximity, schedule overlap, project-description similarity, and
  infrastructure similarity, then ranks the results. Every score traces back to public
  filings (FPSC dockets, FERC Form 1 schedules, utility planning databases) — nothing
  is estimated or invented, and a missing value is shown as missing, never as zero.
- **Interactive dashboard** — a map of every project, a ranked opportunity list with
  filters (year, project type, distance, minimum score), and a detail view per pair
  showing the score breakdown, supporting evidence, potential shared-resource
  categories, and each project's public source.
- **Coordination Heatmap** — the same ranked opportunities plotted as a weighted heat
  layer, so a planner can see where coordination potential clusters geographically
  without opening every card.
- **Coordination Brief** — a one-click, fully deterministic summary of any pair
  (copy to clipboard or export as PDF) for pasting into an email or meeting notes.
- **GridSync Assistant** — a floating chat panel, grounded in the same structured
  analysis the dashboard shows. It reasons and answers naturally rather than filling
  out a fixed template, can work through "what if" planning questions (*"what if this
  schedule moved up six months?"*) using the real numbers as a starting point, and can
  pull and cite short excerpts from the underlying source PDFs (TECO's Storm Protection
  Plan, its FPSC Annual Report) when a question asks what a filing actually says. Its
  one hard rule: never state a fact, number, or claim that isn't in the data.

## Architecture

```
data/                  Public source files (utility filings, FERC schedules) and the
                        processed CSVs/JSON the pipeline and backend read.
analysis/               The scoring pipeline: geographic, temporal, text and
                        infrastructure similarity, scoring, confidence, resource
                        matching. analyze_projects() is the canonical entry point.
scripts/                One-time build scripts: normalize raw filings into the
                        processed data/ files, extract PDF text for the assistant's
                        document retrieval.
backend/                FastAPI service. Serves the processed analysis over HTTP,
                        answers assistant questions (structured retrieval + an LLM
                        call + lightweight TF-IDF document retrieval).
front_end/              Next.js + Leaflet dashboard. Map, ranked list, opportunity
                        detail, heatmap, coordination brief, assistant widget.
tests/, backend/tests/  pytest suites for the pipeline and the API.
```

The frontend never recomputes a score, distance, or resource match — it only displays
what the backend returns. The backend's assistant never recalculates a score either —
it explains and reasons over the pipeline's own output.

## Quickstart

**Backend** (FastAPI, port 8123 to match the frontend's default):
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8123
```

**Frontend** (Next.js):
```bash
cd front_end
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_USE_MOCK=false to call the live backend
npm run dev                  # http://localhost:3000, then click "Analyze projects"
```

By default the frontend uses a saved snapshot of real analysis output
(`front_end/lib/mock/analyze.json`) and needs no backend running at all. Set
`NEXT_PUBLIC_USE_MOCK=false` in `.env.local` to hit the live FastAPI service instead.

**Optional — enable the AI assistant's model calls** (without a key it still answers
from the structured record, just without natural-language reasoning):
```bash
export GRIDSYNC_LLM_API_KEY="your-key"
export GRIDSYNC_LLM_MODEL="gemini-3.5-flash-lite"          # or any OpenAI-compatible model
export GRIDSYNC_LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
```

**Optional — build the assistant's document index** (needed once for it to cite the
source PDFs; the repo ships a prebuilt copy at `data/processed/assistant_document_chunks.json`):
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python3 scripts/build_assistant_index.py
```

## Testing

```bash
cd backend && source .venv/bin/activate && pytest      # API + assistant + retrieval
python3 -m pytest tests/                                # analysis pipeline
cd front_end && npx tsc --noEmit && npm run lint         # frontend
```

## Data sources

Duke Energy Florida and Tampa Electric's own public planning filings: Duke's planned
transmission projects database, Tampa Electric's FPSC-filed 2026-2035 Storm Protection
Plan (Docket No. 20250016-EI), and Tampa Electric's FPSC Annual Report (FERC Form 1
schedules). No filing is scraped live at request time — each was processed once into
the `data/` files the pipeline and assistant read, with the original source recorded on
every row.

## Design principles

- **Missing is never zero.** An unavailable distance, date, or score is shown as
  unavailable, never coerced into a number that could be mistaken for a real one.
- **A drawn line is an approximate corridor, never the physical route** — it's the
  straight line between two known endpoints, and every distance is described as the
  minimum distance between those endpoints, not a route length.
- **The score measures data alignment, not a recommendation.** GridSync says how
  strongly two projects' public data lines up. It doesn't say utilities should
  coordinate, estimate savings, or predict success — that judgment stays with the
  planner.
- **The assistant explains; it doesn't calculate.** Every number the assistant states
  comes from the pipeline's own output or a cited filing excerpt — never a model guess.

## Scope

MVP covers one utility pair — Duke Energy Florida and Tampa Electric — by design; the
pipeline is written to extend to more utilities later, but nationwide coverage was
explicitly out of scope for the hackathon build. There's no live PDF/filing scraping,
and GridSync does not estimate financial savings or ROI — the public data underlying
these projects doesn't support a defensible estimate.
