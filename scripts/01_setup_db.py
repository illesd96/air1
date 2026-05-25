"""Create the `aircraft` collection, apply a JSON-schema validator, and build indexes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `python scripts/01_setup_db.py` from project root
sys.path.insert(0, str(Path(__file__).parent))

from lib.db import db, INDEXES, aircraft

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "aircraft.schema.json"


def main() -> None:
    database = db()
    print(f"Connected to Mongo: {database.name}")

    # Soft validator: warn on invalid documents, don't reject (we want to ingest
    # imperfect data and clean it up over time).
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema.pop("$schema", None)  # Mongo doesn't accept the $schema keyword

    # Mongo's $jsonSchema accepts "number" but not "integer" — coerce.
    def _coerce(node):
        if isinstance(node, dict):
            if "type" in node:
                if node["type"] == "integer":
                    node["type"] = "number"
                elif isinstance(node["type"], list):
                    node["type"] = ["number" if t == "integer" else t for t in node["type"]]
            for v in node.values():
                _coerce(v)
        elif isinstance(node, list):
            for v in node:
                _coerce(v)
    _coerce(schema)

    collections = database.list_collection_names()
    if "aircraft" not in collections:
        database.create_collection(
            "aircraft",
            validator={"$jsonSchema": schema},
            validationLevel="moderate",
            validationAction="warn",
        )
        print("Created collection: aircraft")
    else:
        database.command({
            "collMod": "aircraft",
            "validator": {"$jsonSchema": schema},
            "validationLevel": "moderate",
            "validationAction": "warn",
        })
        print("Updated collection validator: aircraft")

    coll = aircraft()
    for keys, opts in INDEXES:
        name = coll.create_index(keys, **opts)
        print(f"Index: {name}")

    print(f"Documents currently in collection: {coll.estimated_document_count()}")


if __name__ == "__main__":
    main()
