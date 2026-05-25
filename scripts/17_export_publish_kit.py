"""Export per-aircraft publish kits as copy-paste-ready files.

For each aircraft with a `publish` subdocument, writes a folder at
`publish_kits/<category>/<slug>/` with separate files for each platform:

  README.md                — overview + thumbnail brief + engagement Q
  youtube-title.txt        — pick-one-of-five title list
  youtube-description.md   — full description block
  youtube-tags.txt         — comma-separated YouTube tags
  instagram-caption.txt    — hook + hashtags
  tiktok-caption.txt       — hook + hashtags
  thumbnail-brief.md       — focal subject + overlay + mood
  hooks.md                 — shortform + longform hooks
  seo-keywords.txt         — newline-separated keywords
  related.txt              — related aircraft slugs

Usage:
  python scripts/17_export_publish_kit.py            # all aircraft with publish
  python scripts/17_export_publish_kit.py f-16       # just one aircraft
  python scripts/17_export_publish_kit.py --category military
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import aircraft

ROOT = Path(__file__).parent.parent / "publish_kits"


def write_kit(doc: dict) -> int:
    slug = doc["_id"]
    cat = doc.get("category", "uncategorized")
    name = (doc.get("names") or {}).get("primary") or slug
    pub = doc.get("publish") or {}
    if not pub:
        return 0

    out_dir = ROOT / cat / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    hooks = pub.get("hooks") or {}
    titles = pub.get("titles") or []
    tags = pub.get("hashtags") or {}
    desc = pub.get("description_template") or ""
    thumb = pub.get("thumbnail_concept") or {}
    seo = pub.get("seo_keywords") or []
    eng_q = pub.get("engagement_question") or ""
    related = pub.get("related_aircraft") or []
    music = pub.get("music_mood") or ""
    runtimes = pub.get("runtimes") or {}

    # README — overview
    readme = [
        f"# {name}  ({slug})",
        f"_Category: **{cat}**_",
        "",
        f"**Composite score:** {(doc.get('scores') or {}).get('composite', 0):.1f}",
        f"**Music mood:** {music}",
        f"**Runtime targets:** shortform {runtimes.get('shortform_seconds', 0)}s / longform {runtimes.get('longform_seconds', 0)}s",
        "",
        "## Engagement question (pin in comments)",
        "",
        f"> {eng_q}",
        "",
        "## Files in this kit",
        "",
        "- `hooks.md` — short + long-form cold opens",
        "- `youtube-title.txt` — five title variants, pick one",
        "- `youtube-description.md` — full description block",
        "- `youtube-tags.txt` — SEO tags",
        "- `instagram-caption.txt` — hook + IG hashtags",
        "- `tiktok-caption.txt` — hook + TikTok hashtags",
        "- `thumbnail-brief.md` — what to shoot/render",
        "- `seo-keywords.txt`",
        "- `related.txt` — related-aircraft slugs",
    ]
    (out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")

    # Hooks
    (out_dir / "hooks.md").write_text(
        f"# Hooks for {name}\n\n"
        f"## Shortform (TikTok/Reels/Shorts — 3 sec)\n\n{hooks.get('shortform', '')}\n\n"
        f"## Longform (YouTube — 30 sec cold open)\n\n{hooks.get('longform', '')}\n",
        encoding="utf-8",
    )

    # YouTube title variants
    (out_dir / "youtube-title.txt").write_text(
        "\n".join(titles) + "\n", encoding="utf-8"
    )

    # YouTube description
    (out_dir / "youtube-description.md").write_text(desc + "\n", encoding="utf-8")

    # YouTube tags (comma-separated, max 500 chars per YT limit)
    (out_dir / "youtube-tags.txt").write_text(
        ", ".join(tags.get("youtube") or []) + "\n", encoding="utf-8"
    )

    # Instagram caption: short-form hook + IG hashtags block
    ig_lines = [
        hooks.get("shortform", ""),
        "",
        "",
        " ".join(tags.get("instagram") or []),
    ]
    (out_dir / "instagram-caption.txt").write_text("\n".join(ig_lines) + "\n", encoding="utf-8")

    # TikTok caption: short-form hook + TikTok hashtags
    tt_lines = [
        hooks.get("shortform", ""),
        "",
        " ".join(tags.get("tiktok") or []),
    ]
    (out_dir / "tiktok-caption.txt").write_text("\n".join(tt_lines) + "\n", encoding="utf-8")

    # Thumbnail brief
    (out_dir / "thumbnail-brief.md").write_text(
        f"# Thumbnail brief — {name}\n\n"
        f"**Focal subject:** {thumb.get('focal_subject', '')}\n\n"
        f"**Overlay text:** `{thumb.get('overlay_text', '')}`\n\n"
        f"**Mood / palette / lighting:** {thumb.get('mood', '')}\n",
        encoding="utf-8",
    )

    # SEO keywords
    (out_dir / "seo-keywords.txt").write_text("\n".join(seo) + "\n", encoding="utf-8")

    # Related aircraft
    (out_dir / "related.txt").write_text("\n".join(related) + "\n", encoding="utf-8")

    return 1


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("slug", nargs="?", help="just one aircraft by slug")
    p.add_argument("--category", choices=["commercial", "military", "general-aviation", "historic"])
    args = p.parse_args()

    coll = aircraft()
    query: dict = {"publish": {"$exists": True}}
    if args.slug:
        query["_id"] = args.slug
    elif args.category:
        query["category"] = args.category

    written = 0
    for doc in coll.find(query):
        written += write_kit(doc)
    print(f"Wrote publish kits for {written} aircraft under {ROOT}")


if __name__ == "__main__":
    main()
