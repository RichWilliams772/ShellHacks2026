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
  The frontend calls `POST {API_URL}/analyze` with `{"utility_a", "utility_b"}`. **The real backend does not return
  `analyze_projects()` output as-is** — it reshapes the same underlying data into its own field names, closer to
  PROJECT_SPEC's canonical schema (`project_name` not `name`, `latitude`/`longitude` not `mid_lat`/`mid_lon`,
  `reasons` not `evidence`, no `summary` wrapper, etc.). `lib/api.ts`'s `mapAnalyzeResponse()` translates the real
  response into `lib/types.ts`'s shape before anything else sees it — verified field-by-field against a live
  response, not guessed. If the backend's field names change, that function is the only place to update; every
  component keeps working off `lib/types.ts` unchanged. The backend must allow CORS from `http://localhost:3000`.

## Where things live
| File | What it does |
|---|---|
| `lib/types.ts` | The frontend's own internal contract — not a mirror of any one backend response. Change here first if a component needs a new field. |
| `lib/api.ts` | Snapshot/live switch, plus `mapAnalyzeResponse()` translating the real backend's shape into `lib/types.ts`. Only renames/reshapes existing fields; never computes a score, distance, overlap, or resource. |
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
