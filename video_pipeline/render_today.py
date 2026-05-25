"""Daily picker — render 4 Shorts (one per category) of the highest-score
publish-ready aircraft that haven't been rendered yet."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.db import aircraft
from render_short import render, load_config


def pick_next_per_category() -> list[str]:
    picks: list[str] = []
    for cat in ["commercial", "military", "general-aviation", "historic"]:
        doc = aircraft().find_one(
            {
                "category": cat,
                "publish.shortform_script": {"$exists": True},
                "publish.shortform_render_path": {"$exists": False},
            },
            sort=[("scores.composite", -1)],
            projection={"_id": 1, "names.primary": 1, "scores.composite": 1},
        )
        if doc:
            picks.append(doc["_id"])
            print(f"  {cat:<18} pick: {doc.get('names', {}).get('primary')} (score {doc.get('scores', {}).get('composite', 0):.1f})")
    return picks


def main() -> None:
    cfg = load_config()
    picks = pick_next_per_category()
    if not picks:
        print("Nothing left to render.")
        return
    for slug in picks:
        try:
            render(slug, cfg)
        except Exception as e:
            print(f"!! {slug} failed: {e}")


if __name__ == "__main__":
    main()
