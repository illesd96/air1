"""Apply publish-enrichment agent output back to Mongo.

Each agent writes data/exports/publish_<category>.json — an array of entries
matching the `publish` subdocument shape from schema/aircraft.schema.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft, log_ingest_run, now_iso

SCRIPT = "12_apply_publish.py"
EXPORTS = Path(__file__).parent.parent / "data" / "exports"


def main() -> None:
    suffix = sys.argv[1] if len(sys.argv) > 1 else ""
    coll = aircraft()
    total = 0
    for cat in ["commercial", "military", "general-aviation", "historic"]:
        path = EXPORTS / f"publish_{cat}{suffix}.json"
        if not path.exists():
            print(f"  skip: {path.name} not found")
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n{cat}: applying {len(entries)} publish docs")
        for e in entries:
            slug = e.pop("slug")
            r = coll.update_one(
                {"_id": slug},
                {"$set": {"publish": e, "last_updated": now_iso()}},
            )
            if r.matched_count == 0:
                print(f"   ! no doc for {slug}")
                continue
            log_ingest_run(slug, SCRIPT)
            total += 1
    print(f"\nApplied publish metadata to {total} aircraft.")


if __name__ == "__main__":
    main()
