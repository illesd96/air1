import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib.db import aircraft

c = aircraft()
print("Total:", c.estimated_document_count())
last = c.find({"sources.wikidata_id": {"$exists": True, "$ne": None}}, {"names.primary": 1}).sort("names.primary", -1).limit(3)
for d in last:
    print(" Z-end:", d.get("names", {}).get("primary"))
first_b_onward = c.find({"sources.wikidata_id": {"$exists": True, "$ne": None}, "names.primary": {"$gte": "B"}}, {"names.primary": 1}).sort("names.primary", 1).limit(1)
for d in first_b_onward:
    print(" first ≥ B:", d.get("names", {}).get("primary"))
