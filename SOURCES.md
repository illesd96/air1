# Sources

Every data source we use, what we use it for, and the licensing rules we follow.

## TL;DR licensing

| Source | Bulk data | Bulk images | Per-page reference link |
|---|---|---|---|
| Wikidata | ✅ free (CC0) | n/a | ✅ |
| Wikipedia | ✅ text under CC-BY-SA (must attribute) | ✅ when on Commons + CC/PD | ✅ |
| Wikimedia Commons | n/a | ✅ when CC-BY / CC-BY-SA / CC0 / PD | ✅ |
| NASA / USAF / USN / DoD archives | ✅ public domain | ✅ public domain | ✅ |
| Planespotters.net | ❌ ToS forbids scraping | ❌ photographer copyright | ✅ link only |
| JetPhotos | ❌ ToS forbids scraping | ❌ photographer copyright | ✅ link only |
| Airliners.net | ❌ ToS forbids scraping | ❌ photographer copyright | ✅ link only |
| AeroCorner | ⚠ ToS unclear — small manual lookups only | ❌ copyright assumed | ✅ link only |
| FlightRadar24 | ❌ no public API on free tier | n/a | ✅ link only |
| Aviation Fanatic | ⚠ small manual lookups only | ❌ copyright assumed | ✅ link only |
| AERO LENS | ❌ photo copyright | ❌ photo copyright | ✅ link only |

Rule of thumb: **machine-pull only from Wikidata, Wikipedia, Commons, and government archives.** Everywhere else, we generate links so a human can click through for research — no scraping, no image downloads.

---

## Bulk data sources (we machine-pull from these)

### 1. Wikidata
- **URL:** https://www.wikidata.org / SPARQL endpoint at https://query.wikidata.org/sparql
- **What we get:** Structured facts — first flight date, manufacturer, country, units built, engines, predecessors/successors, Wikipedia links, image filenames on Commons.
- **How:** SPARQL query for items that are subclasses of *aircraft model* (Q15056995) or *aircraft* (Q11436). See `scripts/lib/wikidata.py`.
- **License:** All Wikidata content is CC0 — no attribution required, but we record the Wikidata Q-ID per entry anyway for provenance.
- **Rate limit:** ~5 requests/sec, polite User-Agent required. We batch SPARQL queries with `LIMIT 500 OFFSET ...`.
- **User-Agent:** `aircraft-db/0.1 (pilles@eev-systems.com)` (per WMF policy).

### 2. Wikipedia (English, primary)
- **URL:** https://en.wikipedia.org / REST API at https://en.wikipedia.org/api/rest_v1/
- **What we get:**
  - Intro paragraph (`/page/summary/{title}`)
  - Pageview counts (`/metrics/pageviews/per-article/...`) — fuels the "hot" score
  - Full HTML (`/page/html/{title}`) if we need infobox parsing
- **License:** Article text is CC-BY-SA 4.0. We attribute by storing the Wikipedia URL + revision ID per entry.
- **Rate limit:** 200 req/sec for the REST API, but we keep it slow (~5/sec) to be polite.

### 3. Wikimedia Commons
- **URL:** https://commons.wikimedia.org / API at https://commons.wikimedia.org/w/api.php
- **What we get:** Images of aircraft + license metadata (we filter to CC-BY, CC-BY-SA, CC0, public-domain only).
- **How:** Two passes:
  1. Take the main image filename from the Wikipedia infobox (via REST API).
  2. Run a Commons category search for `Category:<Aircraft name>` to find gallery candidates.
- **License:** Per-file — we check `imageinfo|extmetadata` and skip anything that isn't CC/PD.
- **Attribution:** Every downloaded image gets a sibling `ATTRIBUTION.json` recording author, license, source URL, download date.

### 4. NASA Image and Video Library
- **URL:** https://images.nasa.gov / API at https://images-api.nasa.gov
- **What we get:** Public-domain photos of NASA/aviation history aircraft (X-15, SR-71, Space Shuttle ferry, lifting bodies, etc.).
- **License:** Public domain.
- **Use:** Supplementary for historic/experimental aircraft where Commons coverage is thin.

### 5. U.S. Department of Defense (USAF / USN) public affairs imagery
- **URLs:**
  - https://www.airforce.mil/News/Photos/
  - https://www.navy.mil/Resources/Photo-Gallery/
  - https://www.defense.gov/Multimedia/Photos/
- **License:** Public domain (U.S. Government work, 17 USC §105). We still record source URL + photographer credit.
- **Use:** Modern military aircraft photos.

---

## Reference-only sources (we store URLs, never scrape)

These are the seven sites in the original prompt. We use them to:
- Validate facts we got from Wikidata/Wikipedia
- Generate clickable reference URLs in each aircraft document under `images.external_refs`
- Send you (the human) to them when you need a deeper photo dive for a video

### 6. Planespotters.net
- **URL:** https://www.planespotters.net
- **Their position:** ToS prohibits automated access. Image rights belong to the original photographers.
- **What we do:** Build deep-links per aircraft (e.g. `https://www.planespotters.net/airframe/<reg>`) and store them. A human clicks through.
- **Strengths to remember when designing videos:** 267k+ registrations, 67k+ airframes, 1.7M+ photos, full ownership/operator history per airframe — the gold standard for tracing a specific tail number's career.

### 7. JetPhotos
- **URL:** https://www.jetphotos.com
- **Their position:** Photos are owned by the contributing photographer. No bulk scraping.
- **What we do:** Build search URLs (`https://www.jetphotos.com/search?keywords=<model>`) per entry.
- **Strengths:** Largest current aviation photo archive — best place to find every photo of a specific registration.

### 8. Airliners.net
- **URL:** https://www.airliners.net
- **Their position:** Photographer copyright. Forum content is community-licensed.
- **What we do:** Build URLs to the per-model data pages (`/aircraft-data/<manufacturer-model>/<id>`).
- **Strengths:** Historic photography archive, vintage liveries, active enthusiast forum.

### 9. AeroCorner Aircraft Database
- **URL:** https://aerocorner.com/aircraft/
- **Their position:** Standard copyright. ~900 aircraft profiles.
- **What we do:** Build URLs to the per-model encyclopedia entries (`/aircraft/<manufacturer-model>/`). Useful for cross-checking specs against a curated source.

### 10. FlightRadar24
- **URL:** https://www.flightradar24.com
- **Their position:** No free API for bulk data. The site itself is interactive.
- **What we do:** Build search URLs (`/data/aircraft/<model>`) so a human can pull up live data when researching.
- **Strengths:** Live aircraft tracking, "what's in the air right now" angles for current-fleet videos.

### 11. Aviation Fanatic
- **URL:** https://www.aviationfanatic.com
- **Their position:** Free encyclopedia; copyright on the site's own materials.
- **What we do:** Link only — useful for cross-referencing rarer types and airline/airport details.

### 12. AERO LENS Photo Database
- **URL:** https://www.aerolens.eu (formerly known as aerolens.aero — verify before linking)
- **Their position:** Photographer copyright on all images.
- **What we do:** Link to category pages when relevant — strong on military jets, airshows, museum aircraft, prototypes, boneyards.

---

## Other sources we may pull from later

- **EASA / FAA type certificates** — official spec sheets (public records, downloadable PDFs). Useful for definitive specs on certified aircraft.
- **Janes (paywalled)** — definitive military reference. Not free, not scraped. If you have a subscription we can use it manually.
- **Aviation Safety Network** (https://aviation-safety.net) — accidents/incidents, owned by Flight Safety Foundation. Reference-only.
- **Boeing / Airbus / Lockheed Martin official pages** — manufacturer specs and history. Free to read, photos generally copyrighted (some press kits are licensed for editorial use).
- **Wikiquote / IMDb** — for the "appears in pop culture" tag (Top Gun, Independence Day, etc.). Manual lookups.

---

## How attribution is recorded per document

Inside each MongoDB aircraft document:
- `sources.wikidata_id` — the Q-ID
- `sources.wikipedia_url` + `sources.wikipedia_revision` — frozen reference for the CC-BY-SA text we used
- `sources.ingest_runs` — log of every script that touched the doc
- `images.cover.source_url`, `.license`, `.author` — per-image attribution

Inside each downloaded image folder:
- `data/images/<category>/<slug>/ATTRIBUTION.json` — full metadata, structured for legal audit

---

## What we will not do

- We will not scrape Planespotters, JetPhotos, Airliners.net, AeroCorner, FR24, Aviation Fanatic, or AERO LENS.
- We will not download or store images whose license we cannot verify.
- We will not republish Wikipedia text without the CC-BY-SA attribution attached.
- We will not redistribute downloaded photos as if they were ours — the `ATTRIBUTION.json` travels with the file and any video we make uses it for credit.
