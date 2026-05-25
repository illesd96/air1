"""Export the uncategorized aircraft in 4 batches for bulk-categorize agents.

Each batch is a JSON array of {slug, name, manufacturer, country, description_excerpt}
so an agent can assign category + a few baseline tags per entry.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft


def main() -> None:
    coll = aircraft()
    docs = list(coll.find(
        {"category": "uncategorized"},
        {
            "_id": 1, "names.primary": 1, "manufacturer": 1,
            "country_of_origin": 1, "short_description": 1, "long_description": 1,
        },
    ).sort("_id", 1))
    print(f"Found {len(docs)} uncategorized aircraft")

    # Skip docs with no description at all — nothing to categorize against
    have_text = [d for d in docs if d.get("short_description") or d.get("long_description")]
    print(f"  with description: {len(have_text)}")

    # Slim each entry
    for d in have_text:
        d["name"] = d.get("names", {}).get("primary")
        d.pop("names", None)
        d["excerpt"] = (d.get("long_description") or d.get("short_description") or "")[:300]
        d.pop("short_description", None)
        d.pop("long_description", None)

    # 4 batches
    out_dir = Path(__file__).parent.parent / "data" / "exports"
    batches = 4
    per_batch = (len(have_text) + batches - 1) // batches
    for i in range(batches):
        chunk = have_text[i * per_batch : (i + 1) * per_batch]
        out_path = out_dir / f"categorize_batch_{i + 1}.json"
        out_path.write_text(json.dumps(chunk, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  batch {i + 1}: {len(chunk)} aircraft -> {out_path.name}")


if __name__ == "__main__":
    main()
