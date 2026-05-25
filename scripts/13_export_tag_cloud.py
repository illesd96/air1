"""Export all distinct tags + counts as JSON for the tag-cleanup agent."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft


def main() -> None:
    coll = aircraft()
    tag_counts: dict[str, int] = {}
    for doc in coll.find({"tags": {"$exists": True, "$ne": []}}, {"tags": 1}):
        for tag in doc.get("tags") or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    out = [{"tag": t, "count": n} for t, n in sorted_tags]

    dest = Path(__file__).parent.parent / "data" / "exports" / "tag_cloud.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(out)} distinct tags to {dest}")
    print("\nTop 20:")
    for t in out[:20]:
        print(f"  {t['count']:>4}  {t['tag']}")


if __name__ == "__main__":
    main()
