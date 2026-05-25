"""Backfill `_commons_main_file` for aircraft missing it.

For each doc without `_commons_main_file`, pull the Wikipedia REST summary —
its `originalimage.source` field points at a Commons file. Extract the filename.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.db import aircraft, now_iso, log_ingest_run
from lib.wikipedia import summary, polite_sleep

SCRIPT = "03b_backfill_images.py"


def extract_commons_filename(url: str | None) -> str | None:
    if not url:
        return None
    # Typical: https://upload.wikimedia.org/wikipedia/commons/thumb/.../filename.jpg/500px-filename.jpg
    # Or:      https://upload.wikimedia.org/wikipedia/commons/.../filename.jpg
    if "wikipedia/commons" not in url:
        return None
    tail = url.rsplit("/", 1)[-1]
    if tail.startswith(("250px-", "300px-", "500px-", "1024px-")) or "px-" in tail.split("-")[0]:
        # Thumbnail path: prefer the path segment one level up
        parts = url.split("/")
        if len(parts) >= 2:
            tail = parts[-2]
    return unquote(tail).replace("_", " ")


def main() -> None:
    coll = aircraft()
    cursor = coll.find(
        {
            "_commons_main_file": {"$in": [None, ""]},
            "$or": [
                {"sources.wikipedia_url": {"$exists": True}},
                {"names.primary": {"$exists": True}},
            ],
        },
        {"_id": 1, "sources.wikipedia_url": 1, "names.primary": 1},
    )
    docs = list(cursor)
    cursor2 = coll.find({"_commons_main_file": {"$exists": False}}, {"_id": 1, "sources.wikipedia_url": 1, "names.primary": 1})
    docs += list(cursor2)
    seen = set()
    docs = [d for d in docs if d["_id"] not in seen and not seen.add(d["_id"])]

    print(f"Backfilling image filenames for {len(docs)} aircraft...")
    found, missing = 0, 0
    for doc in tqdm(docs, unit="ac"):
        url = (doc.get("sources") or {}).get("wikipedia_url")
        if url:
            title = url.rsplit("/wiki/", 1)[-1].replace("_", " ")
        else:
            title = (doc.get("names") or {}).get("primary")
        if not title:
            continue
        summ = summary(title)
        if not summ:
            missing += 1
            polite_sleep(0.2)
            continue
        orig = (summ.get("originalimage") or {}).get("source")
        filename = extract_commons_filename(orig)
        if filename:
            coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {"_commons_main_file": filename, "last_updated": now_iso()}},
            )
            log_ingest_run(doc["_id"], SCRIPT)
            found += 1
        else:
            missing += 1
        polite_sleep(0.2)

    print(f"\nDone. Found: {found}, missing: {missing}")


if __name__ == "__main__":
    main()
