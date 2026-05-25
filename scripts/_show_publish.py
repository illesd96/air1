"""Show a sample publish doc for a given slug."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.db import aircraft

slug = sys.argv[1] if len(sys.argv) > 1 else "sr-71"
doc = aircraft().find_one({"_id": slug}, {"names.primary": 1, "publish": 1})
if not doc:
    print(f"no doc for {slug}")
    sys.exit(1)
print(f"=== {doc['names']['primary']} ({slug}) ===\n")
print(json.dumps(doc.get("publish", {}), indent=2, ensure_ascii=False))
