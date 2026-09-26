# GridSync backend

FastAPI service for cross-utility coordination opportunities. Project retrieval
can load Aaron's processed Duke and TECO CSVs. Opportunity scores stay on the
labeled demo catalog until analysis is wired to those records. This backend
does not scrape filings.

## Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

`GET /health` reports the project catalog separately from `analysis_dataset_status`.
When `data/processed/duke_projects_normalized.csv` and
`data/processed/teco_projects_geocoded.csv` are present, the server selects the
processed catalog unless `GRIDSYNC_PROJECT_CATALOG=demo`. Set
`GRIDSYNC_PROJECT_CATALOG=processed` to force that catalog, or
`GRIDSYNC_PROJECT_CATALOG=demo` to keep the labeled demo engine.

`GET /utilities`, `GET /projects`, and `GET /projects/{id}` read the selected
catalog. In processed mode, `POST /analyze` and `GET /opportunities` copy Aaron's
precomputed public opportunities. Explicit demo mode still scores the demo fixtures.

## Demo data

`app/fixtures.py` is the default source. Every fixture has:

- `data_type` = `demo`
- `source_name` = `GridSync demo fixture (not a public utility record)`
- `source_url` = `https://example.invalid/gridsync/demo-fixtures`

Unknown optional fields are `null`. They are not stored as zero.

## Replace fixtures with a verified file

Set `GRIDSYNC_DATA_FILE` to a `.csv` or `.json` file, then restart the API.
Do not relabel the demo fixtures as `public`.

JSON is either a list of projects or `{"projects": [...]}`.

### Columns

Required on every row:

| Column | Notes |
| --- | --- |
| `id` | Stable project id. Letters, numbers, `.`, `_`, `-`. |
| `utility` | Utility name, for example `Duke Energy Florida`. |
| `project_name` | Project title from the source. |
| `source_name` | Publisher or filing source. |
| `source_url` | Public URL for that source. |
| `data_type` | `public` for a verified record, or `demo` for a fixture. Required. Never defaulted. |

Optional project fields. Leave blank or JSON `null` when the source does not provide them. Do not use `0` for unknown voltage, cost, customers, or coordinates.

| Column | Notes |
| --- | --- |
| `project_type` | For example `transmission_upgrade`. |
| `description` | Free text. Text similarity runs only when both projects have a description. |
| `voltage_kv` | Positive number, or blank. |
| `latitude` | Decimal degrees. Both latitude and longitude, or neither. |
| `longitude` | Decimal degrees. |
| `geometry` | GeoJSON object, or a JSON string in CSV. LineString distance is a vertex haversine, not a geodesic route buffer. |
| `start_date` | `YYYY-MM-DD`, or `YYYY` when only a year is known. |
| `end_date` | `YYYY-MM-DD`, or `YYYY` when only a year is known. |
| `status` | For example `planned`. |
| `capital_cost` | Reported cost, or blank. Not used in the score. |
| `customers_impacted` | Integer, or blank. Not used in the score. |

Provenance fields:

| Column | Required | Notes |
| --- | --- | --- |
| `source_name` | yes | Name of the public source. |
| `source_url` | yes | URL of the public source. |
| `source_document` | no | Document title. |
| `source_page` | no | Page or section. |
| `retrieved_date` | no | `YYYY-MM-DD`. |
| `data_type` | yes | `demo` or `public`. |

The loader does not check that a `public` row is actually a Duke or TECO filing. It only requires the provenance fields to be present.

## Opportunity explanation

`POST /assistant/query` still filters structured results when `opportunity_id` is omitted, and `llm_used` stays false. Supply `opportunity_id` to explain one opportunity that `/analyze` already returned. The server sends that opportunity's evidence to one chat-completions call. The model is instructed not to invent distances, dates, scores, resources, savings, or a recommendation. `llm_used` is true only when that call returns text.

Set these in the environment. Do not commit the key.

| Variable | Required | Purpose |
| --- | --- | --- |
| `GRIDSYNC_LLM_API_KEY` | yes, for a model call | Bearer token. Absent key returns the structured record and `llm_used: false`. |
| `GRIDSYNC_LLM_MODEL` | no | Chat model. Defaults to `gpt-4o-mini`. |
| `GRIDSYNC_LLM_BASE_URL` | no | OpenAI-compatible API origin. Defaults to `https://api.openai.com/v1`. |

```bash
export GRIDSYNC_LLM_API_KEY="your-key"
export GRIDSYNC_LLM_MODEL="gpt-4o-mini"
export GRIDSYNC_LLM_BASE_URL="https://api.openai.com/v1"

curl -s -X POST http://127.0.0.1:8000/assistant/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Explain this opportunity.","utility_a":"Duke Energy Florida","utility_b":"Tampa Electric","opportunity_id":"DUKE-P0132__TECO-138005"}'
```

A provider failure also keeps `llm_used` false and returns the structured record. `15.05` miles on the top public pair is the minimum distance between known endpoints.

## Not implemented

- PDF or XLSX scraping
- A verified Duke Energy Florida dataset
- A verified Tampa Electric dataset
- Supervised coordination prediction
- Savings, ROI, or resource scheduling

## Score

Weights live in `app/config.py`: geographic proximity 40%, schedule overlap 30%, project similarity 20%, infrastructure similarity 10%. Missing components are omitted and the remaining weights are renormalized. The score is opportunity strength, not a probability or a recommendation.
