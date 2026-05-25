"""Export the top-N per category as JSON for research agents to enrich.

Writes data/exports/research_<category>.json with the top 25 by composite score
per category. Each agent will read its file and return enriched story hooks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft

CATEGORIES = ["commercial", "military", "general-aviation", "historic"]


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--skip", type=int, default=0, help="rank to start from (0-indexed)")
    p.add_argument("--limit", type=int, default=25, help="how many per category")
    p.add_argument("--suffix", default="", help="suffix to add to output file (e.g. '_26_50')")
    args = p.parse_args()

    out_dir = Path(__file__).parent.parent / "data" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    for cat in CATEGORIES:
        cursor = aircraft().find(
            {"category": cat},
            {
                "_id": 1, "names": 1, "manufacturer": 1, "country_of_origin": 1,
                "first_flight": 1, "retired": 1,
                "short_description": 1, "long_description": 1,
                "scores.composite": 1, "scores.fame": 1, "scores.wiki_pageviews_30d": 1,
                "tags": 1, "story.hooks": 1,
                "sources.wikipedia_url": 1,
            },
        ).sort("scores.composite", -1).skip(args.skip).limit(args.limit)

        docs = list(cursor)
        for d in docs:
            d["scores"] = d.get("scores", {})
            d["_long_description_excerpt"] = (d.get("long_description") or "")[:400]
            d.pop("long_description", None)

        out_path = out_dir / f"research_{cat}{args.suffix}.json"
        out_path.write_text(json.dumps(docs, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  wrote {len(docs)} aircraft to {out_path}")


if __name__ == "__main__":
    main()
