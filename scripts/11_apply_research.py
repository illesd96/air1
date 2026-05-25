"""Apply research-agent output (JSON of {slug, hooks, extra_tags, story_seed}) back to Mongo.

Each agent writes data/exports/enriched_<category>.json with entries like:

    {
      "slug": "boeing-747",
      "hooks": ["...", "..."],
      "extra_tags": ["story:...", "..."],
      "story_seed": "First-draft paragraph for the video script."
    }

Also drops a stub `stories/<category>/<slug>.md` for human script writing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft, log_ingest_run, now_iso

SCRIPT = "11_apply_research.py"
EXPORTS = Path(__file__).parent.parent / "data" / "exports"
STORIES = Path(__file__).parent.parent / "stories"


def main() -> None:
    coll = aircraft()
    total = 0
    for cat in ["commercial", "military", "general-aviation", "historic"]:
        path = EXPORTS / f"enriched_{cat}.json"
        if not path.exists():
            print(f"  skip: {path.name} not found")
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n{cat}: applying {len(entries)} enrichments")
        for e in entries:
            slug = e["slug"]
            hooks = e.get("hooks", [])
            extra_tags = e.get("extra_tags", [])
            seed = (e.get("story_seed") or "").strip()

            update_set = {"story.hooks": hooks, "last_updated": now_iso()}
            update = {"$set": update_set}
            if extra_tags:
                update["$addToSet"] = {"tags": {"$each": extra_tags}}
            r = coll.update_one({"_id": slug}, update)
            if r.matched_count == 0:
                print(f"   ! no doc for {slug}")
                continue

            log_ingest_run(slug, SCRIPT)
            total += 1

            md_dir = STORIES / cat
            md_dir.mkdir(parents=True, exist_ok=True)
            md_path = md_dir / f"{slug}.md"
            if not md_path.exists():
                lines = [
                    f"# {slug}\n",
                    "## Hooks\n",
                    *[f"- {h}\n" for h in hooks],
                    "\n## Seed paragraph\n\n",
                    seed + "\n" if seed else "_(empty)_\n",
                    "\n## Draft\n\n_(your video script goes here)_\n",
                ]
                md_path.write_text("".join(lines), encoding="utf-8")

    print(f"\nApplied {total} enrichments. Stub markdowns under stories/.")


if __name__ == "__main__":
    main()
