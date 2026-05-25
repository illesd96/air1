# Aircraft Database

A MongoDB-backed encyclopedia of aircraft for building a daily YouTube video pipeline — one video per day, rotating across commercial / military / general aviation / historic categories.

See [PLAN.md](PLAN.md) for the full design and [SOURCES.md](SOURCES.md) for the data-source catalogue and licensing notes.

## Quick start

```powershell
# 1. Start MongoDB (and the web UI on http://localhost:8081)
docker compose up -d

# 2. Python deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Configure
Copy-Item .env.example .env

# 4. Build the database (run in order)
python scripts/01_setup_db.py            # create collections + indexes
python scripts/02_ingest_wikidata.py     # ~5-10 min, bulk SPARQL pull
python scripts/03_enrich_wikipedia.py    # ~30 min, polite rate-limit
python scripts/05_categorize.py          # tag + category assignment
python scripts/06_calculate_scores.py    # hot/relevance ranking
python scripts/04_download_images.py     # ~1 hr, CC/PD images only
python scripts/07_external_refs.py       # build Planespotters/JetPhotos/etc links
```

## Query examples

```powershell
# Top 10 military aircraft by relevance score
python scripts/query.py --category military --top 10

# All Cold-War-era jet fighters
python scripts/query.py --tag era:cold-war --tag role:fighter --tag engine:jet

# Search by name
python scripts/query.py --search "Spitfire"
```

Or browse visually at http://localhost:8081 (Mongo Express).

## Layout

| Path | What's there |
|---|---|
| `PLAN.md` | The full build plan and schema design |
| `SOURCES.md` | Every data source, what we use it for, licensing rules |
| `docker-compose.yml` | MongoDB + Mongo Express |
| `scripts/` | Ingestion + query scripts (numbered to indicate run order) |
| `data/images/<category>/<slug>/` | Downloaded CC/PD images + `ATTRIBUTION.json` |
| `data/exports/` | Periodic JSON dumps of the whole collection |
| `data/seed/` | Hand-curated CSVs (famous list, category overrides) |
| `stories/<category>/<slug>.md` | Video script drafts |
| `schema/aircraft.schema.json` | JSON Schema mirroring the Mongo validator |

## Status

- [x] Plan + sources docs written
- [x] Project skeleton + Docker setup
- [ ] DB schema + setup script
- [ ] Wikidata bulk ingest
- [ ] Wikipedia enrichment
- [ ] Categorization + tags
- [ ] Image downloads
- [ ] Scoring
- [ ] Story-hook generation (multi-agent)
