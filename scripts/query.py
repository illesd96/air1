"""Tiny query CLI.

Examples:
    python scripts/query.py --top 10
    python scripts/query.py --category military --top 10
    python scripts/query.py --tag era:cold-war --tag role:fighter --top 20
    python scripts/query.py --search "Spitfire"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--category", choices=["commercial", "military", "general-aviation", "historic", "uncategorized"])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--search")
    args = p.parse_args()

    query: dict = {}
    if args.category:
        query["category"] = args.category
    if args.tag:
        query["tags"] = {"$all": args.tag}
    if args.search:
        query["$text"] = {"$search": args.search}

    cursor = aircraft().find(
        query,
        {"_id": 1, "names.primary": 1, "category": 1, "scores.composite": 1, "tags": 1, "short_description": 1},
    ).sort("scores.composite", -1).limit(args.top)

    for d in cursor:
        score = (d.get("scores") or {}).get("composite", 0)
        print(f"  {score:6.2f}  [{d.get('category', '?'):<18}]  {d['names']['primary']}")
        if d.get("short_description"):
            print(f"          {d['short_description'][:140]}")
        if d.get("tags"):
            print(f"          tags: {', '.join(d['tags'][:8])}")
        print()


if __name__ == "__main__":
    main()
