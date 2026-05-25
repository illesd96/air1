"""Resume the Wikidata bulk pull from where we stopped.

Use this once https://query.wikidata.org/sparql is no longer rate-limiting.
It will keep going from the alphabetical position after the last item already
in Mongo and merge new aircraft into the collection.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.db import aircraft, now_iso, log_ingest_run
from lib.slugify import slugify
from lib.wikidata import iter_aircraft, qid_from_uri


SCRIPT = "02b_resume_wikidata.py"


def _val(row: dict, key: str) -> str | None:
    return row.get(key, {}).get("value")


def main(start_offset: int = 0) -> None:
    coll = aircraft()
    inserted, updated = 0, 0

    print(f"Resuming Wikidata ingest from offset {start_offset}...")
    for row in tqdm(iter_aircraft(start_offset=start_offset), desc="Wikidata", unit="ac"):
        qid = qid_from_uri(_val(row, "item"))
        name = _val(row, "itemLabel") or qid
        if name == qid:
            continue
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
            "sources": {"wikidata_id": qid, "wikipedia_url": _val(row, "wpUrl")},
            "_commons_main_file": commons_filename,
            "last_updated": now_iso(),
        }

        result = coll.update_one(
            {"_id": slug},
            {
                "$set": doc,
                "$setOnInsert": {
                    "ingested_at": now_iso(),
                    "category":    "uncategorized",
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
    offset = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(offset)
