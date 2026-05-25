# Aircraft Database — Build Plan

A MongoDB-backed encyclopedia of aircraft, designed for use as source material for
a series of YouTube videos — one video per day, rotating across four categories.

## Goals

1. **Coverage:** 500+ aircraft across four categories (commercial, military, general aviation, historic/vintage), with room to grow.
2. **Rich metadata:** Specs, history, manufacturer, dates, tags, plus a free-form "story" field for video script drafts.
3. **Tags everywhere:** Multiple tag dimensions (era, role, propulsion, country, fame, story-hooks) so we can slice the data many ways.
4. **Hot / relevance score:** A computed score so we can rank aircraft by fame, production volume, current interest, and cultural impact.
5. **Images:** Download Creative Commons / public-domain images locally; keep reference links to copyrighted archives (Planespotters, JetPhotos) for research without violating their ToS.
6. **Transparency of sources:** Every fact and every image traces back to a logged source. See [SOURCES.md](SOURCES.md).

## The four video categories

Per the user's plan — one video per day, one in each category:

| Category | Slug | Examples |
|---|---|---|
| Commercial aviation | `commercial` | Boeing 747, Airbus A380, Concorde, Embraer E-Jets, DC-3 |
| Military aviation | `military` | F-16, SR-71, B-2, A-10, MiG-21, Spitfire, F-35 |
| General aviation | `general-aviation` | Cessna 172, Cirrus SR22, Gulfstream G650, Pilatus PC-12 |
| Historic / vintage | `historic` | Wright Flyer, Fokker Dr.I, P-51 Mustang, Hindenburg, Tu-144 |

(Many aircraft fit multiple — e.g. the Spitfire is both `military` and `historic`. We use **`category`** as the primary slot for the rotation, and **`tags`** for everything else, so the rotation stays clean while cross-cuts remain searchable.)

## Architecture

```
c:/Projects/fun/aircraft/
├── PLAN.md                  this file
├── SOURCES.md               sources catalogue + licensing notes
├── README.md                quick-start: docker up, scripts, queries
├── docker-compose.yml       MongoDB + Mongo Express (web UI)
├── requirements.txt         Python deps (pymongo, requests, etc.)
├── .gitignore
├── .env.example             Mongo URI, user-agent string
│
├── data/
│   ├── images/              downloaded CC/PD images
│   │   ├── commercial/<slug>/cover.jpg, gallery-1.jpg, ATTRIBUTION.json
│   │   ├── military/
│   │   ├── general-aviation/
│   │   └── historic/
│   ├── exports/             periodic JSON dumps of the collection (for git diffs / backup)
│   └── seed/                hand-curated CSV/JSON for the initial famous-list
│
├── scripts/
│   ├── 00_docker_up.ps1         start MongoDB
│   ├── 01_setup_db.py           create collections, indexes, JSON-schema validators
│   ├── 02_ingest_wikidata.py    SPARQL bulk import of aircraft entities → Mongo
│   ├── 03_enrich_wikipedia.py   pull intros, infobox specs, pageview counts
│   ├── 04_download_images.py    fetch CC/PD images from Commons + record attribution
│   ├── 05_categorize.py         assign category + tags (rules + manual overrides)
│   ├── 06_calculate_scores.py   compute hot/relevance composite score
│   ├── 07_external_refs.py      build URLs for Planespotters, JetPhotos, AeroCorner, FR24
│   ├── 08_export.py             dump Mongo → data/exports/*.json (for review/backup)
│   ├── query.py                 CLI: search, filter by tag, top-N by score
│   └── lib/
│       ├── db.py                Mongo client + helpers
│       ├── wikidata.py          SPARQL helpers
│       ├── wikipedia.py         REST + pageviews API
│       ├── commons.py           Wikimedia Commons API + license checks
│       └── slugify.py
│
├── stories/                 video script drafts (markdown, free-form)
│   ├── commercial/<slug>.md
│   ├── military/<slug>.md
│   ├── general-aviation/<slug>.md
│   └── historic/<slug>.md
│
└── schema/
    └── aircraft.schema.json     JSON schema mirroring the Mongo validator
```

## MongoDB schema (collection `aircraft`)

Each document looks like this. Fields marked **★** are required.

```jsonc
{
  "_id": "boeing-747",                       // ★ slug, stable across runs
  "names": {
    "primary": "Boeing 747",                  // ★
    "official": "Boeing 747",
    "nicknames": ["Jumbo Jet", "Queen of the Skies"],
    "translations": { "ja": "ボーイング747" }
  },
  "category": "commercial",                   // ★ one of: commercial | military | general-aviation | historic
  "subcategory": "wide-body airliner",        // free-form

  // ─── tags: the main classification engine ───
  // Tags are flat strings; the categories below are conventions, not separate fields.
  "tags": [
    // era
    "era:jet-age", "era:1960s",
    // role
    "role:airliner", "role:freighter", "role:vip-transport",
    // propulsion
    "engine:turbofan", "engines:4",
    // configuration
    "config:wide-body", "config:double-deck",
    // origin
    "country:usa", "manufacturer:boeing",
    // fame & story hooks
    "fame:iconic", "story:first-of-kind", "story:pop-culture",
    "story:retirement-arc", "story:747-supertanker"
  ],

  // ─── factual metadata ───
  "manufacturer": "Boeing Commercial Airplanes",
  "country_of_origin": "United States",
  "first_flight": "1969-02-09",               // ISO date or year-only string
  "introduction": "1970-01-22",
  "retired": null,                            // null if still flying somewhere
  "status": "in production (747-8F)",         // human-readable status

  "specs": {
    "role": "Wide-body airliner",
    "crew": 2,
    "capacity": 660,
    "length_m": 70.6,
    "wingspan_m": 64.4,
    "height_m": 19.4,
    "max_speed_kmh": 988,
    "cruise_speed_kmh": 933,
    "range_km": 14815,
    "service_ceiling_m": 13100,
    "engines": "4 × GE/PW/RR turbofans",
    "mtow_kg": 447700
  },

  "production": {
    "units_built": 1574,
    "in_service": null,
    "production_years": "1968–present"
  },

  // ─── descriptive content ───
  "short_description": "The original wide-body that opened mass intercontinental travel...",
  "long_description": "...",                  // pulled from Wikipedia intro (CC-BY-SA, attributed)
  "story": {
    "draft": "",                              // free-form: where you'll write the video script
    "hooks": [],                              // bullet-point story angles to consider
    "video_script": null,                     // final cut
    "status": "empty"                          // empty | drafted | scripted | recorded | published
  },

  // ─── ranking ───
  "scores": {
    "fame": 98,                               // 0-100, manually-seeded for top entries
    "wiki_pageviews_30d": 184320,             // raw, from Wikipedia API
    "production_volume_norm": 60,             // log-scaled, 0-100
    "cultural_impact": 95,                    // manual or appears-in-media count
    "trending": 50,                           // recent news mentions (optional)
    "composite": 85                           // weighted sum, used for sort
  },

  // ─── images ───
  "images": {
    "cover": {
      "local_path": "data/images/commercial/boeing-747/cover.jpg",
      "source_url": "https://commons.wikimedia.org/wiki/File:...",
      "license": "CC-BY-SA-4.0",
      "author": "Photographer Name",
      "downloaded_at": "2026-05-21T12:00:00Z"
    },
    "gallery": [ /* same shape */ ],
    "external_refs": [
      { "site": "Planespotters", "url": "https://www.planespotters.net/airframe/boeing-747", "kind": "fleet+history" },
      { "site": "JetPhotos",     "url": "https://www.jetphotos.com/search?keywords=747", "kind": "photos" },
      { "site": "Airliners.net", "url": "https://www.airliners.net/aircraft-data/boeing-747-400/49", "kind": "photos+specs" },
      { "site": "AeroCorner",    "url": "https://aerocorner.com/aircraft/boeing-747/", "kind": "specs" },
      { "site": "FlightRadar24", "url": "https://www.flightradar24.com/data/aircraft/747", "kind": "live-tracking" }
    ]
  },

  // ─── provenance ───
  "sources": {
    "wikidata_id": "Q34284",
    "wikipedia_url": "https://en.wikipedia.org/wiki/Boeing_747",
    "wikipedia_revision": 1234567890,
    "ingest_runs": [
      { "script": "02_ingest_wikidata.py", "at": "2026-05-21T10:00:00Z" },
      { "script": "03_enrich_wikipedia.py", "at": "2026-05-21T10:15:00Z" }
    ]
  },

  "ingested_at": "2026-05-21T10:00:00Z",
  "last_updated": "2026-05-21T10:15:00Z"
}
```

### Indexes

- `_id` (slug) — primary key
- `category` — for the four-category rotation
- `tags` (multikey) — fast tag filtering
- `scores.composite` (desc) — top-N "hot" queries
- `names.primary` (text) — search

## Hot / Relevance score

The `composite` is a weighted blend of normalized signals. Default weights:

| Signal | Source | Weight |
|---|---|---|
| Wikipedia 30-day pageviews | Wikipedia REST API `/pageviews/per-article/...` | 0.35 |
| Production volume (log-scaled) | Wikidata `P1092` or Wikipedia infobox | 0.15 |
| Fame seed | Hand-curated for top ~100 aircraft | 0.20 |
| Cultural impact | "appears in media" count (manual + WD `P1441`) | 0.15 |
| Trending (news mentions) | Optional: Google News RSS | 0.10 |
| Recency (still active) | derived from `retired` / `status` | 0.05 |

The weights live in [scripts/06_calculate_scores.py](scripts/06_calculate_scores.py) and are easy to tweak. The composite is recomputed any time we run that script — pageview counts naturally make things "hot" when they're trending.

## Phases & build order

### Phase 1 — Foundation (this session)
- [x] Confirm scope, storage, scale with the user
- [ ] Write PLAN.md, SOURCES.md, README.md
- [ ] Create folder skeleton + docker-compose + requirements
- [ ] Write schema + DB setup script
- [ ] Hand-curate `data/seed/famous.csv` with ~80 canonical aircraft (~20 per category) as a quality anchor

### Phase 2 — Bulk ingest (next session)
- Run `02_ingest_wikidata.py`: SPARQL query for all instances of *aircraft model* (Q15056995) — yields 5,000+ entries. We'll filter down to those with Wikipedia articles.
- Run `03_enrich_wikipedia.py`: pull intro paragraph + infobox + 30-day pageviews for each.
- Result: every aircraft has names, dates, specs, and a description.

### Phase 3 — Categorize & tag
- `05_categorize.py` applies rules:
  - Wikidata "instance of"/"subclass of" → category guess (e.g. *fighter aircraft* → military)
  - Manufacturer + decade → era/origin tags
  - Engine count, configuration from infobox → propulsion/config tags
- Manual overrides in `data/seed/category_overrides.csv` for edge cases.

### Phase 4 — Images
- `04_download_images.py`: for each aircraft, query Commons for the main image referenced from the Wikipedia article, plus 2-4 gallery photos.
- License filter: only download `CC-BY`, `CC-BY-SA`, `CC0`, public-domain. Skip anything else.
- Save image + write `ATTRIBUTION.json` alongside it with author/license/source URL.
- Backfill external reference URLs to Planespotters / JetPhotos / etc. by registration or model name (no downloading — just URL construction).

### Phase 5 — Scoring
- `06_calculate_scores.py` builds the composite score. Sort top 100 — sanity check that famous aircraft float to the top.

### Phase 6 — Stories
- For each high-score aircraft, create a stub `stories/<category>/<slug>.md` with prompts:
  - "What's the hook?"
  - "Surprising fact."
  - "One scene to show."
  - Pre-filled with `story.hooks` from the doc.
- This is where you write video scripts.

### Phase 7 — Query tools
- `query.py` — CLI: `query.py --category military --top 10 --tag era:cold-war`
- Optional: a tiny web UI later (Mongo Express handles the basic case immediately).

## Use of multiple agents

The user asked us to "use more agents if needed". Where parallel agents help:
- **Research enrichment per category** — four agents in parallel, one each for commercial / military / GA / historic, each fact-checking the top 25 entries against Wikipedia and adding 3–5 story hooks per aircraft. This is the slow, judgment-heavy part.
- **Tag normalization** — one agent reviews all tags across the corpus, merges synonyms, fixes typos.
- **Story-hook generation** — one agent per category drafts "what would make a good 5-minute video about this?" angles.

We don't parallelize the bulk Wikidata/Wikipedia/Commons pulls — those are network-bound and serial scripts with rate limiting are simpler than coordinating multiple agents hitting the same APIs.

## Open questions

1. **Hosting:** MongoDB will run locally via Docker. If you want this accessible from another machine later, we can switch to MongoDB Atlas free tier — schema doesn't change.
2. **Story workflow:** Do you want the stories in Mongo too (queryable), in Markdown files (easy to edit in VS Code), or both? Current default: both — Mongo holds bullet-point hooks, Markdown files hold the full draft.
3. **Photo budget:** Wikimedia Commons API is rate-limited but free. ~500 aircraft × ~5 photos ≈ 2500 downloads, totaling maybe 500MB–1GB on disk. OK?
4. **Refresh cadence:** Pageviews change. Set up a `/loop` that re-runs `06_calculate_scores.py` weekly so the "hot" ranking stays fresh?
