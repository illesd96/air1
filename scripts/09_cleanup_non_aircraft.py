"""Remove non-aircraft junk that slipped through the broad Wikidata SPARQL.

The query `wdt:P31/wdt:P279* wd:Q11436` matches items classified as aircraft
or any subclass thereof, but Wikidata's modeling is messy — accident pages,
competitions, registration numbers, and one-off named airframes all leak in.

We delete entries that look like noise. Conservative — when in doubt, keep.

Pass --yes to skip the interactive confirmation prompt.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft

NOISE_TITLE_PATTERNS = [
    r"\bcrash\b",
    r"\baccident\b",
    r"\bdisaster\b",
    r"\bcompetition\b",
    r"\bcauldron\b",
    r"\bmission\b",
    r"\braid\b",
    r"\bairline\b",
    r"\bairport\b",
    r"\boperation\b",
    r"\bsquadron\b",
    r"\bairshow\b",
    r"\bmuseum\b",
    r"\baward\b",
    r"\bschool\b",
]
NOISE_RE = re.compile("|".join(NOISE_TITLE_PATTERNS), re.IGNORECASE)
# Pure-number IDs (registrations like "44-83690", "57-1419", "356")
PURE_REG_RE = re.compile(r"^[0-9]{2,}[-]?[0-9]*$")


def main() -> None:
    coll = aircraft()
    to_delete: list[str] = []

    for doc in coll.find({}, {"_id": 1, "names.primary": 1, "category": 1, "scores.fame": 1}):
        if (doc.get("scores") or {}).get("fame", 0) >= 50:
            continue  # seeded famous → never delete
        name = (doc.get("names") or {}).get("primary") or doc["_id"]

        if NOISE_RE.search(name):
            to_delete.append(doc["_id"])
            continue
        if PURE_REG_RE.match(name.strip()):
            to_delete.append(doc["_id"])
            continue

    print(f"Will delete {len(to_delete)} non-aircraft entries.")
    for slug in to_delete[:25]:
        print(f"  - {slug}")
    if len(to_delete) > 25:
        print(f"  ... and {len(to_delete) - 25} more")

    auto_yes = "--yes" in sys.argv
    if to_delete and (auto_yes or input("\nConfirm delete? [y/N] ").strip().lower() == "y"):
        result = coll.delete_many({"_id": {"$in": to_delete}})
        print(f"Deleted: {result.deleted_count}")
    else:
        print("Aborted (no deletes).")


if __name__ == "__main__":
    main()
