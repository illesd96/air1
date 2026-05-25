"""Apply bulk-categorize agent output back to Mongo.

Each agent writes data/exports/categorize_result_<n>.json with entries:
    { "slug": "...", "category": "...", "tags": ["..."] }
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft, log_ingest_run, now_iso

SCRIPT = "16_apply_categorize.py"
EXPORTS = Path(__file__).parent.parent / "data" / "exports"

ALLOWED = {"commercial", "military", "general-aviation", "historic"}


def main() -> None:
    coll = aircraft()
    total = 0
    for i in range(1, 5):
        path = EXPORTS / f"categorize_result_{i}.json"
        if not path.exists():
            print(f"  skip: {path.name} not found")
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        applied = 0
        for e in entries:
            slug = e.get("slug")
            cat = e.get("category")
            tags = e.get("tags") or []
            if cat not in ALLOWED:
                continue
            r = coll.update_one(
                {"_id": slug, "category": "uncategorized"},
                {
                    "$set": {"category": cat, "last_updated": now_iso()},
                    "$addToSet": {"tags": {"$each": tags}},
                },
            )
            if r.matched_count:
                applied += 1
                log_ingest_run(slug, SCRIPT)
        total += applied
        print(f"  batch {i}: applied {applied}/{len(entries)}")
    print(f"\nTotal categorized: {total}")


if __name__ == "__main__":
    main()
