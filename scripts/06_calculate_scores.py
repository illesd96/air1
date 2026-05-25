"""Compute the composite hot/relevance score for every aircraft.

composite = w_fame * fame
          + w_views * normalize(wiki_pageviews_30d)
          + w_units * normalize(log(units_built))
          + w_active * (100 if still in service else 60)

Tweak the WEIGHTS dict to taste.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.db import aircraft, log_ingest_run, now_iso

SCRIPT = "06_calculate_scores.py"

WEIGHTS = {
    "fame":   0.30,
    "views":  0.35,
    "units":  0.15,
    "active": 0.10,
    "media":  0.10,   # cultural_impact, manual or default 50
}


def normalize(values: list[float]) -> dict[int, float]:
    """Map a list of values to 0-100 based on rank percentile."""
    if not values:
        return {}
    lo, hi = min(values), max(values)
    if hi == lo:
        return {i: 50.0 for i in range(len(values))}
    return {i: 100 * (v - lo) / (hi - lo) for i, v in enumerate(values)}


def main() -> None:
    coll = aircraft()
    docs = list(coll.find({}, {
        "_id": 1, "scores": 1, "production": 1, "retired": 1, "status": 1,
    }))
    print(f"Scoring {len(docs)} aircraft...")

    views_raw  = [d.get("scores", {}).get("wiki_pageviews_30d") or 0 for d in docs]
    units_raw  = [math.log10((d.get("production", {}) or {}).get("units_built") or 1) for d in docs]

    views_norm = normalize(views_raw)
    units_norm = normalize(units_raw)

    for i, doc in enumerate(tqdm(docs, unit="ac")):
        scores = doc.get("scores", {}) or {}
        fame = float(scores.get("fame") or 0)
        media = float(scores.get("cultural_impact") or 50)
        active_score = 100 if not doc.get("retired") else 60

        composite = (
            WEIGHTS["fame"]   * fame
          + WEIGHTS["views"]  * views_norm[i]
          + WEIGHTS["units"]  * units_norm[i]
          + WEIGHTS["active"] * active_score
          + WEIGHTS["media"]  * media
        )

        coll.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "scores.production_volume_norm": units_norm[i],
                "scores.composite": round(composite, 2),
                "last_updated": now_iso(),
            }},
        )
        log_ingest_run(doc["_id"], SCRIPT)

    # Show the top 20 so we can sanity-check
    print("\nTop 20 by composite score:")
    for d in coll.find({}, {"names.primary": 1, "category": 1, "scores.composite": 1})\
                 .sort("scores.composite", -1).limit(20):
        print(f"  {d['scores']['composite']:6.2f}  [{d.get('category', '?'):<18}]  {d['names']['primary']}")


if __name__ == "__main__":
    main()
