import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib.db import aircraft

c = aircraft()
total = c.count_documents({"publish.shortform_script": {"$exists": True}})
print("Aircraft with shortform_script:", total)
print()
print("By category:")
for r in c.aggregate([
    {"$match": {"publish.shortform_script": {"$exists": True}}},
    {"$group": {"_id": "$category", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]):
    print(f"  {r['_id']:<20} {r['n']}")

# Sample
print("\n=== Sample: SR-71 ===")
doc = c.find_one({"_id": "sr-71"}, {"publish.shortform_script": 1})
import json
print(json.dumps(doc.get("publish", {}).get("shortform_script", {}), indent=2, ensure_ascii=False))
