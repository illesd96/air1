"""Wikimedia Commons API helpers — image metadata, license filtering, download."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

USER_AGENT = os.getenv("USER_AGENT", "aircraft-db/0.1 (pilles@eev-systems.com)")
SESSION = requests.Session()
SESSION.headers["User-Agent"] = USER_AGENT

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# Whitelist of licenses we accept for download. Anything else: skip.
ALLOWED_LICENSES = {
    "cc-by-2.0", "cc-by-2.5", "cc-by-3.0", "cc-by-4.0",
    "cc-by-sa-2.0", "cc-by-sa-2.5", "cc-by-sa-3.0", "cc-by-sa-4.0",
    "cc0", "publicdomain", "pd-usgov", "pd-us", "pd-self",
}


def image_info(filename: str) -> dict | None:
    """Fetch image metadata from Commons, including license + author."""
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
        "format": "json",
    }
    r = SESSION.get(COMMONS_API, params=params, timeout=20)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [None])[0]
        if info:
            return info
    return None


def license_ok(info: dict) -> bool:
    md = info.get("extmetadata", {})
    short = (md.get("LicenseShortName", {}).get("value") or "").lower().strip()
    short_norm = short.replace(" ", "-")
    if any(short_norm.startswith(allowed) for allowed in ALLOWED_LICENSES):
        return True
    # Also accept anything tagged as public-domain in the metadata
    if "public domain" in short:
        return True
    return False


def download(info: dict, dest: Path) -> None:
    url = info["url"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    with SESSION.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)


def write_attribution(info: dict, dest_dir: Path, filename_on_commons: str) -> None:
    md = info.get("extmetadata", {})
    attr = {
        "file": filename_on_commons,
        "source_url": f"https://commons.wikimedia.org/wiki/File:{filename_on_commons.replace(' ', '_')}",
        "direct_url": info.get("url"),
        "license":    md.get("LicenseShortName", {}).get("value"),
        "license_url": md.get("LicenseUrl", {}).get("value"),
        "author":     md.get("Artist", {}).get("value"),
        "credit":     md.get("Credit", {}).get("value"),
        "description": md.get("ImageDescription", {}).get("value"),
    }
    (dest_dir / "ATTRIBUTION.json").open("a", encoding="utf-8").write(
        json.dumps(attr, indent=2, ensure_ascii=False) + "\n---\n"
    )


def polite_sleep(seconds: float = 0.5) -> None:
    time.sleep(seconds)
