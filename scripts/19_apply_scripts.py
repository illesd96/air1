"""Apply pre-generated Short scripts back to Mongo.

Each agent writes data/exports/scripts_<n>.json — array of:
  {
    "slug": "...",
    "shortform_script": {
      "duration_target_seconds": 50,
      "voiceover": "Full ~110-word narration text.",
      "shot_list": [
        {"start_seconds": 0,  "end_seconds": 2,  "visual": "Title card: SR-71 silhouette", "visual_prompt": "Optional text-to-video prompt"},
        {"start_seconds": 2,  "end_seconds": 8,  "visual": "Banked SR-71 with shock cones", "visual_prompt": "..."}
      ],
      "title_card": "WE CAN'T BUILD IT AGAIN",
      "end_card_cta": "Subscribe for one aircraft a day."
    }
  }
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft, log_ingest_run, now_iso

SCRIPT = "19_apply_scripts.py"
EXPORTS = Path(__file__).parent.parent / "data" / "exports"


def main() -> None:
    coll = aircraft()
    total = 0
    candidates = [f"scripts_{i}.json" for i in range(1, 5)] + \
                 [f"scripts_{i}{s}.json" for i in range(1, 5) for s in ("a", "b")]
    for fname in candidates:
        path = EXPORTS / fname
        if not path.exists():
            print(f"  skip: {path.name} not found")
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        applied = 0
        for e in entries:
            slug = e.get("slug")
            script = e.get("shortform_script")
            if not slug or not script:
                continue
            r = coll.update_one(
                {"_id": slug},
                {"$set": {
                    "publish.shortform_script": script,
                    "last_updated": now_iso(),
                }},
            )
            if r.matched_count:
                applied += 1
                log_ingest_run(slug, SCRIPT)
        total += applied
        print(f"  {fname}: applied {applied}/{len(entries)}")
    print(f"\nTotal scripts applied: {total}")


if __name__ == "__main__":
    main()
