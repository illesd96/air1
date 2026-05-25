"""Generate reference URLs for the no-scrape sites (Planespotters/JetPhotos/etc.).

We never download from these. We just build search URLs so a human can click
through during research. See SOURCES.md for the licensing rationale.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.db import aircraft, log_ingest_run, now_iso
from lib.slugify import slugify

SCRIPT = "07_external_refs.py"


def build_refs(name: str) -> list[dict]:
    q = quote_plus(name)
    slug = slugify(name)
    return [
        {"site": "Planespotters", "url": f"https://www.planespotters.net/search?q={q}", "kind": "fleet+history"},
        {"site": "JetPhotos",     "url": f"https://www.jetphotos.com/search?keywords={q}", "kind": "photos"},
        {"site": "Airliners.net", "url": f"https://www.airliners.net/search?keywords={q}", "kind": "photos+forums"},
        {"site": "AeroCorner",    "url": f"https://aerocorner.com/?s={q}", "kind": "specs"},
        {"site": "FlightRadar24", "url": f"https://www.flightradar24.com/data/aircraft/{slug}", "kind": "live-tracking"},
        {"site": "Wikipedia",     "url": f"https://en.wikipedia.org/wiki/Special:Search/{q}", "kind": "encyclopedia"},
    ]


def main() -> None:
    coll = aircraft()
    docs = list(coll.find({}, {"_id": 1, "names.primary": 1}))
    print(f"Building external refs for {len(docs)} aircraft...")

    for doc in tqdm(docs, unit="ac"):
        name = doc.get("names", {}).get("primary")
        if not name:
            continue
        refs = build_refs(name)
        coll.update_one(
            {"_id": doc["_id"]},
            {"$set": {"images.external_refs": refs, "last_updated": now_iso()}},
        )
        log_ingest_run(doc["_id"], SCRIPT)


if __name__ == "__main__":
    main()
