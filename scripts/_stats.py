"""Quick stats dump — number of docs per category, top scored, etc."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib.db import aircraft

c = aircraft()
print("Total:", c.estimated_document_count())
print()
print("By category:")
for r in c.aggregate([{"$group": {"_id": "$category", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}]):
    print(f"  {r['_id']!s:<20} {r['n']}")
print()
print("Top 10 by composite score:")
for d in c.find({}, {"names.primary": 1, "category": 1, "scores.composite": 1, "scores.fame": 1}).sort("scores.composite", -1).limit(10):
    score = (d.get("scores") or {}).get("composite", 0)
    fame = (d.get("scores") or {}).get("fame", 0)
    print(f"  composite={score:>6.1f} fame={fame:>4.0f}  [{d.get('category', '?'):<18}] {d['names']['primary']}")
