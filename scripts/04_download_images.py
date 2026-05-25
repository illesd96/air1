"""Download Commons-hosted cover images (and a few gallery shots) for each aircraft.

Only downloads files whose license is on the allow-list in lib/commons.py.
Writes ATTRIBUTION.json in the destination folder.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm

from lib.commons import image_info, license_ok, download, write_attribution, polite_sleep
from lib.db import aircraft, log_ingest_run, now_iso

SCRIPT = "04_download_images.py"
IMG_ROOT = Path(os.getenv("IMAGE_ROOT", "./data/images"))


def main() -> None:
    coll = aircraft()
    cursor = coll.find(
        {"_commons_main_file": {"$exists": True, "$ne": None}, "category": {"$ne": "uncategorized"}},
        {"_id": 1, "category": 1, "_commons_main_file": 1, "images.cover": 1},
    )
    docs = list(cursor)
    print(f"Attempting cover image for {len(docs)} aircraft...")

    downloaded, skipped_license, errors = 0, 0, 0

    for doc in tqdm(docs, unit="ac"):
        if (doc.get("images") or {}).get("cover"):
            continue  # already have one

        filename = doc["_commons_main_file"]
        try:
            info = image_info(filename)
        except Exception as e:
            errors += 1
            print(f"  ! {doc['_id']}: {e}")
            continue
        if not info or not license_ok(info):
            skipped_license += 1
            continue

        dest_dir = IMG_ROOT / doc["category"] / doc["_id"]
        suffix = Path(filename).suffix or ".jpg"
        dest = dest_dir / f"cover{suffix}"
        try:
            download(info, dest)
            write_attribution(info, dest_dir, filename)
            md = info.get("extmetadata", {})
            coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "images.cover": {
                        "local_path":  str(dest.as_posix()),
                        "source_url":  f"https://commons.wikimedia.org/wiki/File:{filename.replace(' ', '_')}",
                        "license":     md.get("LicenseShortName", {}).get("value"),
                        "author":      md.get("Artist", {}).get("value"),
                        "downloaded_at": now_iso(),
                    },
                    "last_updated": now_iso(),
                }},
            )
            log_ingest_run(doc["_id"], SCRIPT)
            downloaded += 1
        except Exception as e:
            errors += 1
            print(f"  ! {doc['_id']}: {e}")

        polite_sleep(0.5)

    print(f"\nDone. Downloaded: {downloaded}, license-skipped: {skipped_license}, errors: {errors}")


if __name__ == "__main__":
    main()
