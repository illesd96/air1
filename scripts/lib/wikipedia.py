"""Wikipedia REST API helpers — summary, pageviews, HTML."""
from __future__ import annotations

import os
import time
from datetime import date, timedelta

import requests

USER_AGENT = os.getenv("USER_AGENT", "aircraft-db/0.1 (pilles@eev-systems.com)")
SESSION = requests.Session()
SESSION.headers["User-Agent"] = USER_AGENT


def _get(url: str) -> dict | None:
    r = SESSION.get(url, timeout=20)
    if r.status_code in (400, 404):
        return None
    r.raise_for_status()
    return r.json()


def summary(title: str) -> dict | None:
    """Intro paragraph + infobox-y bits via /page/summary."""
    safe = title.replace(" ", "_")
    return _get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe}")


def pageviews_30d(title: str) -> int | None:
    """Total Wikipedia pageviews for the last 30 complete days."""
    today = date.today()
    end = today - timedelta(days=1)
    start = end - timedelta(days=29)
    safe = title.replace(" ", "_")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/all-agents/{safe}/daily/"
        f"{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}"
    )
    data = _get(url)
    if not data or "items" not in data:
        return None
    return sum(item["views"] for item in data["items"])


def polite_sleep(seconds: float = 0.2) -> None:
    time.sleep(seconds)
