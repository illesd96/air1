"""Export all publish-ready aircraft as input for script-generation agents.

Splits into 4 batches (one per agent) and writes:
  data/exports/script_input_<n>.json
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
        {"publish": {"$exists": True}},
        {
            "_id": 1, "names": 1, "category": 1, "manufacturer": 1, "country_of_origin": 1,
            "first_flight": 1, "retired": 1, "tags": 1,
            "short_description": 1, "long_description": 1,
            "story.hooks": 1, "publish": 1,
        },
    ).sort([("category", 1), ("scores.composite", -1)]))

    # Slim each entry — agents don't need everything
    for d in docs:
        d["name"] = (d.get("names") or {}).get("primary")
        d.pop("names", None)
        d["excerpt"] = (d.get("long_description") or d.get("short_description") or "")[:600]
        d.pop("long_description", None)
        d.pop("short_description", None)
        # Trim publish to just what's useful for scripting
        pub = d.get("publish") or {}
        d["publish_seed"] = {
            "hooks":  pub.get("hooks"),
            "music_mood": pub.get("music_mood"),
            "runtimes": pub.get("runtimes"),
            "engagement_question": pub.get("engagement_question"),
        }
        d.pop("publish", None)

    print(f"Exporting {len(docs)} aircraft for script generation")

    out_dir = Path(__file__).parent.parent / "data" / "exports"
    batches = 4
    per_batch = (len(docs) + batches - 1) // batches
    for i in range(batches):
        chunk = docs[i * per_batch : (i + 1) * per_batch]
        out_path = out_dir / f"script_input_{i + 1}.json"
        out_path.write_text(json.dumps(chunk, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  batch {i + 1}: {len(chunk)} aircraft -> {out_path.name}")


if __name__ == "__main__":
    main()
