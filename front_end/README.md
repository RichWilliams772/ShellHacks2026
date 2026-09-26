# GridSync — frontend

Next.js 16 + TypeScript + Tailwind + Leaflet dashboard for GridSync (see `shellhacks-2026-ideas/projectSpec.md`).

## Run
```bash
npm install
cp .env.example .env.local   # first time only
npm run dev                  # http://localhost:3000
```

## Mock vs. live backend
- `NEXT_PUBLIC_USE_MOCK=true` (default): uses `lib/mock/*.json`. These are **synthetic demo records**
  (`data_type: "demo"`) and the header shows a "DEMO DATA" badge. Never present them as real utility data.
- `NEXT_PUBLIC_USE_MOCK=false`: calls `POST {NEXT_PUBLIC_API_URL}/analyze`, `GET /utilities`, `GET /projects`.
  Restart `npm run dev` after changing `.env.local`. The backend must allow CORS from `http://localhost:3000`.

## Where things live
| File | What it does |
|---|---|
| `lib/types.ts` | Response shapes (spec §7, §24). Change here first if the API changes. |
| `lib/api.ts` | All backend calls + mock switch. Converts the backend response into `lib/types.ts`. Accepts both the spec §24 shape (`features`, `coordination_package.resources`) and the brief's shape (`opportunity_id`, `analysis`, `shared_resources`, `name`, `construction_start`). Never computes scores. |
| `lib/config.ts` | API URL, high-opportunity threshold, utility colors, map center. |
| `lib/format.ts` | Display formatting. `null` shows "Not available", never 0. |
| `components/Dashboard.tsx` | Page state: analyze, filters, selection. |
| `components/ProjectMap.tsx` | Leaflet map (client-only), pair highlight + distance line. |
| `components/OpportunityDetail.tsx` | Score, metrics, reasons, coordination package, sources. |

## What the backend should send per project
- `latitude` / `longitude` (needed for markers and the distance line)
- `location_confidence`: `HIGH | MEDIUM | LOW | UNKNOWN`
- `geometry` (GeoJSON line, optional) + `geometry_precision`: `route | approximate_corridor | endpoint_connection`.
  Anything that isn't `route` is drawn dotted and labeled "not an exact route".
- Optional score components (0–1): `distance_similarity`, `schedule_similarity`, `project_similarity`, `infrastructure_similarity`.
  The "Score breakdown" bars only appear for components the backend sends.

## Rules from the spec the UI follows
- Distance, overlap, scores and shared resources come from the backend only; filters just hide rows.
- Missing values display as "Not available".
- Every opportunity shows its reasons and public sources.
