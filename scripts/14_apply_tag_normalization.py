"""Apply tag-normalization output back to Mongo.

Input file `data/exports/tag_normalization.json` shape:
{
  "rename": { "old_tag": "new_tag", ... },           // rename across all docs
  "delete": ["tag_to_drop", ...],                    // remove entirely
  "merge":  { "canonical": ["alias1", "alias2"] }    // alias→canonical
}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.db import aircraft, now_iso, log_ingest_run

SCRIPT = "14_apply_tag_normalization.py"
INPUT = Path(__file__).parent.parent / "data" / "exports" / "tag_normalization.json"


def main() -> None:
    if not INPUT.exists():
        print(f"Missing input: {INPUT}")
        sys.exit(1)
    spec = json.loads(INPUT.read_text(encoding="utf-8"))
    rename = spec.get("rename", {})
    delete = set(spec.get("delete", []))
    merges = spec.get("merge", {})

    # Flatten merges into rename: each alias → canonical
    for canonical, aliases in merges.items():
        for a in aliases:
            rename[a] = canonical

    print(f"Rename rules: {len(rename)}, delete tags: {len(delete)}")

    coll = aircraft()
    cursor = coll.find({"tags": {"$exists": True, "$ne": []}}, {"_id": 1, "tags": 1})
    docs = list(cursor)
    touched = 0
    for doc in tqdm(docs, unit="ac"):
        new_tags: list[str] = []
        for t in doc.get("tags") or []:
            t = rename.get(t, t)
            if t in delete:
                continue
            if t not in new_tags:
                new_tags.append(t)
        if new_tags != doc.get("tags"):
            coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {"tags": new_tags, "last_updated": now_iso()}},
            )
            log_ingest_run(doc["_id"], SCRIPT)
            touched += 1
    print(f"\nTouched {touched} aircraft.")


if __name__ == "__main__":
    main()
