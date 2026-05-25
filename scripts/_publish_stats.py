import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib.db import aircraft

c = aircraft()
total = c.count_documents({"publish": {"$exists": True}})
print("Aircraft with publish metadata:", total)
print()
print("By category:")
for r in c.aggregate([
    {"$match": {"publish": {"$exists": True}}},
    {"$group": {"_id": "$category", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]):
    print(f"  {r['_id']:<20} {r['n']}")
