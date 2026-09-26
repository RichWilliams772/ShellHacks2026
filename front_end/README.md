# GridSync — frontend

Next.js 16 + TypeScript + Tailwind + Leaflet dashboard for GridSync (see `Specs/projectSpec.md`).

## Run
```bash
npm install
npm run dev                  # http://localhost:3000, then click "Analyze projects"
```

## Data: saved snapshot vs. live backend
- **Default (`NEXT_PUBLIC_USE_MOCK` unset or `true`)**: uses `lib/mock/analyze.json`, a saved copy of
  `analyze_projects("Duke Energy Florida", "Tampa Electric")` from `analysis/pipeline.py`. It is real public data,
  not synthetic. Refresh it after the analysis pipeline changes (run from the repo root):
  ```bash
  python3 -c "import json; from analysis.pipeline import analyze_projects; json.dump(analyze_projects('Duke Energy Florida','Tampa Electric'), open('front_end/lib/mock/analyze.json','w'), indent=1)"
  ```
- **Live**: `cp .env.example .env.local`, set `NEXT_PUBLIC_USE_MOCK=false` and `NEXT_PUBLIC_API_URL`, restart `npm run dev`.
  The frontend calls `POST {API_URL}/analyze` with `{"utility_a", "utility_b"}` and expects the `analyze_projects()`
  output unchanged. The backend must allow CORS from `http://localhost:3000`.

## Where things live
| File | What it does |
|---|---|
| `lib/types.ts` | Mirrors `analyze_projects()` output field for field. Change here first if the pipeline output changes. |
| `lib/api.ts` | Snapshot/live switch. No field mapping; never computes scores, distances, or resources. |
| `lib/format.ts` | Display formatting. `null` shows "Not available", never 0. |
| `lib/config.ts` | API URL, the two MVP utilities, utility colors, map start view. |
| `app/globals.css` | Design tokens ("planning sheet" palette) and Leaflet overrides. |
| `components/Dashboard.tsx` | Page state: analyze, filters, selection. Side column shows the ranked list or one pair's details. |
| `components/ProjectMap.tsx` | Leaflet map: projects, approximate corridors, red distance line for the selected pair. |
| `components/OpportunityDetail.tsx` | Score, evidence, coordination package, score breakdown, project facts, sources. |

## Rules from the spec the UI follows
- Scores, distances, schedules, and shared resources come from the analysis only; filters just hide rows.
- Missing values display as "Not available".
- A line between two substations is labeled an approximate corridor, never the route.
- Every opportunity shows its evidence and public sources.
