"""Orchestrator: takes one slug, renders a vertical Short.

Run on the GPU PC. Reads `publish.shortform_script` from Mongo, runs every
stage, writes `renders/<category>/<slug>.mp4`, and stamps
`publish.shortform_render_path` back into Mongo so the daily picker won't
re-render.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "video_pipeline"))

try:
    import tomllib  # py311+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

from lib.db import aircraft, log_ingest_run, now_iso
from steps import tts, video_gen, music, subtitles, title_cards, assemble

CONFIG_PATH = ROOT / "video_pipeline" / "config.toml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Missing {CONFIG_PATH}. Copy from config.example.toml.")
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def render(slug: str, cfg: dict) -> Path:
    doc = aircraft().find_one({"_id": slug})
    if not doc:
        raise SystemExit(f"no doc for {slug}")
    pub = doc.get("publish") or {}
    script = pub.get("shortform_script")
    if not script:
        raise SystemExit(f"{slug}: publish.shortform_script not set yet")

    category = doc.get("category", "uncategorized")
    workdir = ROOT / cfg["output"]["workdir"] / slug
    workdir.mkdir(parents=True, exist_ok=True)
    out_dir = ROOT / cfg["output"]["renders_dir"] / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.mp4"

    # Stage 1 — narration
    narration = workdir / "narration.wav"
    tts.synthesize(
        text=script["voiceover"],
        dest=narration,
        backend=cfg["tts"]["backend"],
        voice_sample=Path(cfg["tts"]["voice_sample"]),
        ref_text=cfg["tts"].get("ref_text"),
        device=cfg["gpu"]["device"],
    )

    # Stage 2 — subtitles
    align_json = workdir / "align.json"
    subtitles.align(
        narration_wav=narration, transcript=script["voiceover"], dest_json=align_json,
        model=cfg["subtitles"]["model"], language=cfg["subtitles"]["language"],
        device=cfg["gpu"]["device"],
    )
    srt = subtitles.export_srt(align_json, workdir / "subs.srt", style=cfg["subtitles"]["style"])

    # Stage 3 — visuals (one clip per shot)
    clips: list[Path] = []
    for i, shot in enumerate(script["shot_list"]):
        dur = float(shot["end_seconds"]) - float(shot["start_seconds"])
        is_hero = (i == 0)
        clip = workdir / f"shot_{i:02d}.mp4"
        video_gen.generate_clip(
            prompt=shot["visual_prompt"],
            dest=clip,
            duration_seconds=dur,
            backend=cfg["video_gen"]["backend"],
            hero_backend=cfg["video_gen"].get("hero_backend"),
            is_hero=is_hero,
            resolution=cfg["video_gen"]["resolution"],
            fps=cfg["video_gen"]["fps"],
            device=cfg["gpu"]["device"],
        )
        clips.append(clip)

    # Stage 4 — music
    music_wav = workdir / "music.wav"
    music.generate(
        prompt=pub.get("music_mood") or "ambient cinematic background",
        dest=music_wav,
        duration_seconds=script["duration_target_seconds"]
            + cfg["assemble"]["title_card_seconds"]
            + cfg["assemble"]["end_card_seconds"],
        backend=cfg["music"]["backend"],
        model=cfg["music"].get("model", "facebook/musicgen-medium"),
        device=cfg["gpu"]["device"],
    )

    # Stage 5 — title & end cards
    title_png = title_cards.render_title_card(script["title_card"], workdir / "title.png")
    end_png   = title_cards.render_end_card(script["end_card_cta"], workdir / "end.png")

    # Stage 6 — assemble
    assemble.assemble(
        clips=clips,
        narration=narration,
        music=music_wav,
        subtitles_srt=srt,
        title_card=title_png,
        end_card=end_png,
        out=out_path,
        fps=cfg["video_gen"]["fps"],
        title_card_seconds=cfg["assemble"]["title_card_seconds"],
        end_card_seconds=cfg["assemble"]["end_card_seconds"],
        burn_in_subs=cfg["subtitles"]["burn_in"],
    )

    # Stamp back into Mongo
    aircraft().update_one(
        {"_id": slug},
        {"$set": {
            "publish.shortform_render_path": str(out_path.relative_to(ROOT).as_posix()),
            "publish.shortform_rendered_at": now_iso(),
            "last_updated": now_iso(),
        }},
    )
    log_ingest_run(slug, "render_short.py")
    print(f"Rendered: {out_path}")
    return out_path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("slug")
    args = p.parse_args()
    render(args.slug, load_config())


if __name__ == "__main__":
    main()
