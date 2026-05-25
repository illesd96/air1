"""MongoDB client + helpers shared across all ingest scripts."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.collection import Collection
from pymongo.database import Database

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://aircraft:aircraft@localhost:27017/?authSource=admin")
MONGO_DB = os.getenv("MONGO_DB", "aircraft")


@lru_cache(maxsize=1)
def client() -> MongoClient:
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)


def db() -> Database:
    return client()[MONGO_DB]


def aircraft() -> Collection:
    return db()["aircraft"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_ingest_run(_id: str, script: str) -> None:
    """Append an ingest-run entry to a document's provenance log."""
    aircraft().update_one(
        {"_id": _id},
        {
            "$push": {"sources.ingest_runs": {"script": script, "at": now_iso()}},
            "$set":  {"last_updated": now_iso()},
        },
    )


INDEXES = [
    ([("category", ASCENDING)], {}),
    ([("tags", ASCENDING)], {}),
    ([("scores.composite", DESCENDING)], {}),
    ([("sources.wikidata_id", ASCENDING)], {"sparse": True}),
    ([("names.primary", TEXT)], {"default_language": "english"}),
]
