# BioScope AI — Backend

A real, runnable FastAPI backend for the BioScope AI frontend. SQLite by
default (zero setup), swappable to Postgres by changing one env var.

What's real here: authentication (JWT), a proper relational schema,
CSV ingestion of pipeline results, and genuine Shannon/Simpson/Pielou
diversity math computed from stored abundance data. What's *not* here:
an actual Kraken2/BLAST/DADA2 sequencing pipeline — that's a separate,
heavier service (see "Wiring in a real bioinformatics pipeline" below).

## 1. Setup

```bash
cd bioscope-backend
python3 -m venv venv

# macOS/Linux
source venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and, at minimum, replace `JWT_SECRET_KEY` with a real secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 2. Seed sample data (optional but recommended)

Creates a demo login and one populated dataset so every screen has real
numbers to show immediately.

```bash
python seed.py
```

Login: `demo@bioscope.ai` / `demo1234`

## 3. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

- API base: `http://localhost:8000`
- Interactive docs (try every endpoint from the browser): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

## 4. Connect the frontend

In `bioscope.html`, add a small API client near the top of your `<script>`
block and swap the mock-data functions for fetch calls:

```javascript
const API_BASE = "http://localhost:8000/api";
let authToken = localStorage.getItem("bioscope_token");

async function apiRequest(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

async function login(email, password) {
  const data = await apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  authToken = data.access_token;
  localStorage.setItem("bioscope_token", authToken);
  return data.user;
}

async function getDatasets() {
  return apiRequest("/datasets");
}

async function getBiodiversityMetrics(datasetId) {
  return apiRequest(`/biodiversity/${datasetId}`);
}

async function askChat(message, datasetId) {
  const data = await apiRequest("/chat", {
    method: "POST",
    body: JSON.stringify({ message, dataset_id: datasetId }),
  });
  return data.reply;
}
```

Then replace wherever the frontend currently reads from a hardcoded
`sampleData` object with a call to the matching function above, e.g.:

```javascript
// before
const metrics = calculateMetricsFromSampleData();

// after
const metrics = await getBiodiversityMetrics(currentDatasetId);
```

Because the frontend is opened as a static file (`file://` or Live Server
on port 5500) and the API runs on port 8000, this is a cross-origin
request — CORS is already enabled for `localhost:5500` and `localhost:3000`
in `.env`. Add any other origin you use to `CORS_ORIGINS`.

## Geographic mapping

Sampling sites live in their own `sampling_sites` table (dataset_id, name,
latitude, longitude), and each `SpeciesObservation` carries an optional
`site_id`. This is what lets the map plot *where each species was found*
rather than dropping one pin per dataset.

To populate it, include three extra columns in your upload CSV:

```
species_name,read_count,confidence,site_name,latitude,longitude
Salmo trutta,1840,0.96,Elkhorn Slough Mouth,36.8108,-121.7870
```

Each distinct `site_name` becomes one site; coordinates are validated
(lat -90..90, lng -180..180) and the dataset's own lat/lng is set to the
centroid of its sites. The columns are optional — a CSV without them still
uploads fine, it just won't appear on the map.

The frontend renders this with Leaflet over CARTO dark basemap tiles, which
requires an internet connection. Everything else in the app works offline.

## 5. Uploading real pipeline output

`POST /api/datasets/{id}/upload` accepts a CSV with columns
`species_name,read_count,confidence`. This is the ingestion point for
whatever your sequencing pipeline produces — point your pipeline's final
output at this endpoint (or write a small adapter script that converts a
Kraken2/QIIME2 report into this CSV shape).

## API summary

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/register`, `/login`, `GET /me` | Auth |
| `GET/POST/DELETE /api/datasets` | Dataset CRUD |
| `POST /api/datasets/{id}/upload` | Ingest pipeline results (CSV) |
| `GET /api/datasets/{id}/species` | List identified taxa for a dataset |
| `GET /api/biodiversity/{id}` | Shannon, Simpson, Pielou, richness |
| `GET /api/taxonomy` | Reference taxonomy tree (filter by rank/parent/search) |
| `POST /api/reports/{id}/generate`, `GET /api/reports/{id}` | Biodiversity reports |
| `POST /api/chat` | Dataset-grounded Q&A (rule-based; swap for Claude API) |
| `GET /api/datasets/{id}/sites` | Sampling sites with real GPS coordinates + per-site diversity |
| `POST /api/predict` | Trained k-mer RandomForest classifier — species prediction from a raw sequence |
| `GET /api/predict/health` | Classifier status + species count |
| `GET /api/admin/users`, `/stats` | Admin-only |

## The species classifier (`ml_model/`)

This backend also serves the trained k-mer classifier from `ml_model/model.joblib`
directly on `/api/predict` — no separate service or port needed anymore.
It's a real trained RandomForest (not a lookup table), but trained on
**synthetic** reference sequences (`ml_model/generate_data.py`), not real
GenBank/BOLD data. To retrain on new data:

```bash
cd ml_model
python generate_data.py     # regenerates data/reference_sequences.csv
python train_model.py       # retrains, overwrites model.joblib
```

Restart the server afterward — the model loads once at first request and is
cached in memory.

## Wiring in a real bioinformatics pipeline

This backend deliberately stops at "ingest a CSV of results" rather than
running Kraken2/BLAST/DADA2 itself — those tools need their own container
with reference databases (GBs of data), aren't callable from a normal web
request (they run for minutes-to-hours), and belong in a background worker,
not the API process. The pattern:

1. User uploads raw FASTQ via a new `/api/datasets/{id}/upload-raw` endpoint.
2. That endpoint saves the file and pushes a job onto a queue (Celery + Redis,
   or AWS SQS/Batch).
3. A separate worker process runs the actual pipeline (DADA2 for ASVs →
   Kraken2/BLAST against a reference DB → taxonomy assignment) and writes
   results back via the existing `SpeciesObservation` model.
4. The frontend polls `GET /api/datasets/{id}` and shows `status: processing`
   until the worker flips it to `completed`.

See `bioscope-architecture.md` (from the earlier turn) for the fuller
Postgres schema and endpoint list this scaffold is a working subset of.

## Moving to Postgres

```bash
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/bioscope
```

```bash
pip install psycopg2-binary
```

Everything else (models, routers) is unchanged — SQLAlchemy abstracts the
database engine.
