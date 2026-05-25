"""Dump the aircraft collection to JSON for review/backup/version control."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft


def main() -> None:
    dest_dir = Path(__file__).parent.parent / "data" / "exports"
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"aircraft-{stamp}.json"

    docs = list(aircraft().find({}))
    dest.write_text(json.dumps(docs, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {len(docs)} docs to {dest}")


if __name__ == "__main__":
    main()
