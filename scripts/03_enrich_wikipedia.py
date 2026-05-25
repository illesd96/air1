"""Enrich each aircraft doc with Wikipedia summary text + 30-day pageviews."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.db import aircraft, log_ingest_run, now_iso
from lib.wikipedia import summary, pageviews_30d, polite_sleep

SCRIPT = "03_enrich_wikipedia.py"


def title_from_url(url: str) -> str | None:
    if not url or "/wiki/" not in url:
        return None
    return url.rsplit("/wiki/", 1)[-1].replace("_", " ")


def main() -> None:
    coll = aircraft()
    # Skip docs that already have a long_description — pass --all to force re-enrich.
    force_all = "--all" in sys.argv
    query: dict = {} if force_all else {"$or": [
        {"long_description": {"$in": [None, ""]}},
        {"long_description": {"$exists": False}},
    ]}
    cursor = coll.find(query, {"_id": 1, "sources.wikipedia_url": 1, "names.primary": 1})
    docs = list(cursor)
    print(f"Enriching {len(docs)} aircraft from Wikipedia (force_all={force_all})...")

    for doc in tqdm(docs, unit="ac"):
        url = (doc.get("sources") or {}).get("wikipedia_url")
        title = title_from_url(url) if url else (doc.get("names") or {}).get("primary")
        if not title:
            continue

        summ = summary(title)
        views = pageviews_30d(title)

        update = {"last_updated": now_iso()}
        if summ:
            update["long_description"] = summ.get("extract", "")
            if not (existing := coll.find_one({"_id": doc["_id"]}, {"short_description": 1})
                                   .get("short_description")):
                update["short_description"] = summ.get("description", "")
            if rev := summ.get("revision"):
                update["sources.wikipedia_revision"] = int(rev)
        if views is not None:
            update["scores.wiki_pageviews_30d"] = views

        coll.update_one({"_id": doc["_id"]}, {"$set": update})
        log_ingest_run(doc["_id"], SCRIPT)
        polite_sleep(0.2)


if __name__ == "__main__":
    main()
