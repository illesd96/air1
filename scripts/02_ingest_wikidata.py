"""Bulk-ingest aircraft records from Wikidata.

Pulls every Wikidata entity that is a subclass of Q11436 (aircraft) and has an
English Wikipedia article. Upserts into the `aircraft` Mongo collection keyed by
slug. Safe to re-run — it merges on `sources.wikidata_id`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.db import aircraft, now_iso, log_ingest_run
from lib.slugify import slugify
from lib.wikidata import iter_aircraft, qid_from_uri


SCRIPT = "02_ingest_wikidata.py"


def _val(row: dict, key: str) -> str | None:
    return row.get(key, {}).get("value")


def main() -> None:
    coll = aircraft()
    inserted, updated = 0, 0

    for row in tqdm(iter_aircraft(), desc="Wikidata", unit="ac"):
        qid = qid_from_uri(_val(row, "item"))
        name = _val(row, "itemLabel") or qid
        if name == qid:
            continue  # no English label

        slug = slugify(name)
        if not slug:
            continue

        commons_filename = None
        if image := _val(row, "image"):
            commons_filename = image.rsplit("/", 1)[-1].replace("_", " ")

        doc = {
            "names": {"primary": name},
            "manufacturer":      _val(row, "manufacturerLabel"),
            "country_of_origin": _val(row, "countryLabel"),
            "first_flight":      _val(row, "firstFlight"),
            "introduction":      _val(row, "introduced"),
            "retired":           _val(row, "retired"),
            "production":        {"units_built": int(_val(row, "unitsBuilt")) if _val(row, "unitsBuilt") else None},
            "short_description": _val(row, "itemDescription") or "",
            "sources": {
                "wikidata_id":  qid,
                "wikipedia_url": _val(row, "wpUrl"),
            },
            "_commons_main_file": commons_filename,  # consumed by 04_download_images.py
            "last_updated": now_iso(),
        }

        result = coll.update_one(
            {"_id": slug},
            {
                "$set": doc,
                "$setOnInsert": {
                    "ingested_at": now_iso(),
                    "category":    "uncategorized",  # 05_categorize.py fixes this
                    "tags": [],
                    "story": {"draft": "", "hooks": [], "video_script": None, "status": "empty"},
                    "scores": {"fame": 0, "composite": 0},
                    "images": {"gallery": [], "external_refs": []},
                },
            },
            upsert=True,
        )
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1
        log_ingest_run(slug, SCRIPT)

    print(f"\nDone. Inserted: {inserted}, updated: {updated}")


if __name__ == "__main__":
    main()
