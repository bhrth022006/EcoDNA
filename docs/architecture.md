# BioScope AI — System Architecture Reference

This is an implementation blueprint for the full platform described in the original brief. The working prototype in `frontend/` + `backend/` demonstrates the UI/UX, real diversity-index math, real geographic mapping, and a real trained species classifier — this document covers the fuller production system a dev team would build toward.

## 1. Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + TypeScript, Tailwind CSS, D3.js/Chart.js, Leaflet |
| Backend API | Python, FastAPI, Pydantic v2 |
| Auth | JWT (access + refresh), email verification via signed token links, bcrypt password hashing |
| Primary DB | PostgreSQL (+ PostGIS extension for geo queries) |
| Object storage | S3-compatible bucket for raw FASTA/FASTQ uploads and generated reports |
| Task queue | Celery or Arq workers backed by Redis, for async pipeline runs |
| Bioinformatics | Biopython, BLAST+, Kraken2, QIIME2/DADA2 (denoising), VSEARCH, scikit-bio (diversity indices) |
| ML | scikit-learn / XGBoost for tabular habitat & risk models, PyTorch/TensorFlow for sequence classifiers (CNN/transformer over k-mers) |
| Deployment | Docker Compose for dev, Kubernetes or ECS for prod, Nginx reverse proxy, GitHub Actions CI/CD |

## 2. Core data model (PostgreSQL)

```
users            (id, email, password_hash, role[admin|researcher|student], verified_at, created_at)
datasets         (id, owner_id, name, format, upload_path, status[uploaded|validating|processing|complete|failed], created_at)
sequences        (id, dataset_id, sample_id, raw_seq, quality_scores, length, gc_content)
taxonomy_ranks   (id, kingdom, phylum, class, order, family, genus, species, external_ref[ncbi|gbif|itis|bold])
species          (id, taxonomy_rank_id, common_name, iucn_status, is_invasive, habitat_tags[])
predictions      (id, sequence_id, species_id, confidence, model_version, feature_attribution jsonb)
sampling_sites   (id, dataset_id, name, lat, lng, collected_at)   -- implemented in this prototype
locations        (id, dataset_id, sample_id, lat, lng, site_name, collected_at)
environmental_data (id, location_id, temperature, ph, salinity, altitude, pollution_index, collected_at)
biodiversity_metrics (id, dataset_id, richness, shannon, simpson, evenness, health_score, computed_at)
reports          (id, dataset_id, type[pdf|xlsx|csv], storage_path, generated_at)
ai_models        (id, name, task, version, status, accuracy_metrics jsonb)
audit_logs       (id, user_id, action, target_type, target_id, created_at)
```

Indices are computed server-side (not hardcoded) using the same formulas as the prototype:
- **Shannon (H')** = −Σ pᵢ ln(pᵢ)
- **Simpson (1−D)** = 1 − Σ pᵢ²
- **Evenness (J')** = H' / ln(S), where S = richness

## 3. Pipeline (async, Celery/Arq)

1. **Ingest & validate** — format check, missing-value scan, duplicate detection, invalid-base detection, metadata completeness.
2. **Preprocess** — quality trimming, DADA2/VSEARCH denoising, contaminant removal (host DNA filtering), deduplication, normalization.
3. **Classify** — Kraken2 or BLAST+ against a local mirror of NCBI GenBank/BOLD reference sequences; fallback to the trained k-mer classifier (see `backend/ml_model/`) for novel/unmatched sequences; write confidence scores and full taxonomic lineage.
4. **Enrich** — join to GBIF/ITIS/Catalogue of Life/WoRMS for accepted names and synonyms; join to IUCN Red List for conservation status; flag invasive species against a curated regional invasive-species list.
5. **Compute** — biodiversity indices, rarity/dominance flags, habitat prediction model, environmental correlation.
6. **Report** — render PDF/XLSX/CSV, store in object storage, notify the user.

Each stage writes progress to `datasets.status` so the frontend can poll or subscribe (websocket) for a pipeline-steps panel.

## 4. External database integration

Rather than re-hosting taxonomy data, mirror or query on demand:
- **NCBI GenBank / BOLD Systems** — reference sequences for BLAST/Kraken2 databases (bulk download + periodic refresh, not live per-request calls).
- **GBIF / ITIS / Catalogue of Life / WoRMS** — canonical taxonomic names, synonyms, distribution data via their REST APIs, cached locally.
- **IUCN Red List API** — conservation status, refreshed on a schedule (rate-limited, requires an API key).
- **EOL** — supplementary species descriptions/images for the species detail view.

## 5. API surface

The prototype backend (`backend/app/`) already implements a working subset:

```
POST   /api/auth/register /api/auth/login   GET /api/auth/me
GET/POST/DELETE /api/datasets   POST /api/datasets/{id}/upload   GET /api/datasets/{id}/species
GET    /api/datasets/{id}/sites            # real GPS sampling sites + per-site diversity
GET    /api/biodiversity/{dataset_id}
GET    /api/taxonomy
POST   /api/reports/{id}/generate   GET /api/reports/{id}
POST   /api/chat
POST   /api/predict                        # trained k-mer classifier
GET    /api/admin/users /api/admin/stats
```

The fuller production surface would add:

```
POST   /auth/verify-email /auth/reset-password
GET    /taxonomy/tree?dataset_id=
GET    /compare?a=&b=
GET    /admin/models /admin/audit-logs
POST   /model/train                        # retrain classifier from uploaded labeled data
```

## 6. Security

JWT access/refresh tokens, role-based route guards (admin/researcher/student), rate limiting on `/predict` and `/auth`, virus/format scanning on upload, signed URLs for report downloads, audit logging on every mutating admin action.

## 7. Suggested build order

1. Auth + dataset upload/validation (no ML yet) — get the data model and RBAC solid first. ✅ done in prototype
2. Preprocessing pipeline + Kraken2/BLAST integration against a small reference subset.
3. Biodiversity index computation + dashboard API. ✅ done in prototype
4. External taxonomy/conservation enrichment (GBIF/IUCN).
5. ML habitat + novel-species classifiers, explainability layer. ✅ partially done — k-mer RandomForest classifier with feature-importance explainability, trained on synthetic data
6. Reporting, notifications, admin tooling, comparison/trend analysis last — they depend on everything above being stable.

## What's real vs. simulated in this prototype

| Area | Status |
|---|---|
| Auth, JWT, dataset CRUD | Real |
| Shannon/Simpson/Pielou math | Real, computed server-side from stored data |
| Species classifier | Real trained RandomForest, but on **synthetic** reference sequences |
| Geographic mapping | Real GPS coordinates, real Leaflet map, real per-site diversity |
| Taxonomy tree, search, invasive-species flags in the UI | Still sample data in the frontend — not yet backed by the database |
| Kraken2/BLAST/DADA2 pipeline | Not implemented — see section 3 for how it would plug in |
| GenBank/GBIF/IUCN live integration | Not implemented — see section 4 |
