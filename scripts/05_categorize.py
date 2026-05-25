"""Assign a primary `category` and a tag set to each aircraft.

Strategy:
1. Seed file `data/seed/famous.csv` wins outright — those are hand-curated.
2. Heuristic rules on description / manufacturer / dates fill in the rest.
3. Anything left unclassified stays `category: uncategorized` for manual review.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.db import aircraft, log_ingest_run, now_iso

SCRIPT = "05_categorize.py"
SEED = Path(__file__).parent.parent / "data" / "seed" / "famous.csv"

MILITARY_KEYWORDS = {
    "fighter", "bomber", "attack", "interceptor", "reconnaissance",
    "military transport", "trainer aircraft of the", "anti-submarine",
    "gunship", "warplane", "air force", "navy", "marine",
}
GA_KEYWORDS = {
    "light aircraft", "general aviation", "business jet", "private jet",
    "single-engine piston", "light sport", "ultralight", "experimental",
    "homebuilt", "kit plane",
}
COMMERCIAL_KEYWORDS = {
    "airliner", "commercial", "regional jet", "freighter", "cargo aircraft",
    "wide-body", "narrow-body", "passenger",
}

HISTORIC_BEFORE_YEAR = 1955  # rough cutoff for "historic" by first-flight date


def apply_seed(coll) -> set[str]:
    seeded: set[str] = set()
    if not SEED.exists():
        return seeded

    with SEED.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            slug = row["slug"]
            tags = [t.strip() for t in row["key_tags"].split(";") if t.strip()]
            nicknames = [n.strip() for n in row.get("nicknames", "").split(";") if n.strip()]
            hooks = [h.strip() for h in row.get("hook_seed", "").split(";") if h.strip()]

            existing = coll.find_one({"_id": slug}, {"story": 1})
            story = (existing or {}).get("story") or {
                "draft": "", "hooks": [], "video_script": None, "status": "empty",
            }
            story["hooks"] = hooks  # seed hooks win

            update = {
                "category": row["category"],
                "tags":     tags,
                "scores.fame":  float(row["fame_seed"]),
                "names.primary": row["name"],
                "names.nicknames": nicknames,
                "story":    story,
                "last_updated": now_iso(),
            }
            coll.update_one(
                {"_id": slug},
                {
                    "$set": update,
                    "$setOnInsert": {
                        "ingested_at": now_iso(),
                        "sources":  {"wikidata_id": row.get("wikidata_id") or None},
                        "images":   {"gallery": [], "external_refs": []},
                    },
                },
                upsert=True,
            )
            log_ingest_run(slug, SCRIPT)
            seeded.add(slug)
    return seeded


def guess_category(text: str, first_flight: str | None) -> tuple[str, list[str]]:
    low = (text or "").lower()
    tags: list[str] = []

    year = None
    if first_flight and len(first_flight) >= 4 and first_flight[:4].isdigit():
        year = int(first_flight[:4])
        tags.append(f"era:{year // 10 * 10}s")

    if any(k in low for k in MILITARY_KEYWORDS):
        cat = "military"
    elif any(k in low for k in COMMERCIAL_KEYWORDS):
        cat = "commercial"
    elif any(k in low for k in GA_KEYWORDS):
        cat = "general-aviation"
    elif year and year < HISTORIC_BEFORE_YEAR:
        cat = "historic"
    else:
        cat = "uncategorized"

    return cat, tags


def main() -> None:
    coll = aircraft()

    seeded = apply_seed(coll)
    print(f"Applied seed entries: {len(seeded)}")

    cursor = coll.find(
        {"_id": {"$nin": list(seeded)}, "category": {"$in": [None, "uncategorized"]}},
        {"_id": 1, "long_description": 1, "short_description": 1, "first_flight": 1},
    )
    todo = list(cursor)
    print(f"Heuristic-categorizing: {len(todo)}")

    for doc in tqdm(todo, unit="ac"):
        text = (doc.get("long_description") or "") + " " + (doc.get("short_description") or "")
        cat, tags = guess_category(text, doc.get("first_flight"))
        coll.update_one(
            {"_id": doc["_id"]},
            {
                "$set":      {"category": cat, "last_updated": now_iso()},
                "$addToSet": {"tags": {"$each": tags}},
            },
        )
        log_ingest_run(doc["_id"], SCRIPT)


if __name__ == "__main__":
    main()
