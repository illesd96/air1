# Aircraft Short-Form Video Pipeline

Fully open-source automated YouTube Shorts / TikTok / Reels generation from the aircraft database.

## Goal

Render 4 vertical (1080×1920, 9:16) Shorts per day — one per category (commercial / military / general-aviation / historic) — from the `publish.shortform_script` field on each Mongo doc. Zero per-video cost, runs on a single beefy GPU PC.

## End-to-end flow

```
Mongo aircraft doc
    │
    ├── publish.shortform_script.voiceover  ──► TTS  (F5-TTS)         ──► narration.wav
    │                                                                       │
    │                                                                       └──► WhisperX ──► subtitles.json (word-level timing)
    │
    ├── publish.shortform_script.shot_list[].visual_prompt
    │        └──► Text-to-video (LTX-Video / HunyuanVideo / CogVideoX) ──► shot_N.mp4
    │
    ├── publish.music_mood ──► MusicGen ──► music.wav
    │
    ├── publish.shortform_script.title_card ──► Pillow render ──► title_card.png
    └── publish.shortform_script.end_card_cta ──► Pillow render ──► end_card.png

           └──► ffmpeg ──► assembles ──► short.mp4 (1080×1920, H.264, AAC)
```

## Project layout for the video pipeline

```
c:/Projects/fun/aircraft/
├── video_pipeline/
│   ├── README.md                      # this file's quick-start
│   ├── render_short.py                # orchestrator: slug → short.mp4
│   ├── steps/
│   │   ├── tts.py                     # F5-TTS / XTTS abstraction
│   │   ├── video_gen.py               # text-to-video model abstraction
│   │   ├── music.py                   # MusicGen wrapper
│   │   ├── subtitles.py               # WhisperX alignment + ffmpeg burn-in
│   │   ├── title_cards.py             # Pillow text overlays
│   │   └── assemble.py                # ffmpeg final composition
│   ├── config.toml                    # picks models, GPU device, paths
│   ├── voices/                        # 15-30s clean samples for cloning
│   └── workdir/<slug>/                # ephemeral per-render output
└── renders/<category>/<slug>.mp4      # published Shorts
```

## OSS toolchain (Q1-Q2 2026)

| Stage | Pick | Alternatives |
|---|---|---|
| TTS | **F5-TTS** | Coqui XTTS-v2, MeloTTS, Piper (CPU fallback) |
| Text-to-video (workhorse) | **LTX-Video** (real-time on RTX 4090) | Wan 2.1 (1.3B for 8GB), Stable Video Diffusion |
| Text-to-video (hero shots) | **HunyuanVideo** (highest quality at 24GB quantized) | Mochi 1 (Apache 2.0, 24GB quantized), CogVideoX-5B |
| Image-to-video | **CogVideoX-5B** | SVD, LTX-Video img2vid mode |
| Music | **MusicGen** (Audiocraft) | Stable Audio Open |
| Sound effects | **MMAudio** | hand-curated library |
| Subtitles + alignment | **WhisperX** | whisper-timestamped |
| Composition | **ffmpeg** | MoviePy if Python preferred |

## Hardware minimum (single PC)

- **GPU:** RTX 4090 (24 GB VRAM) — handles LTX-Video at real-time, quantized HunyuanVideo, F5-TTS, MusicGen, WhisperX
- **RAM:** 64 GB
- **Disk:** 500 GB+ NVMe (models alone are 80-150 GB cached)
- **OS:** Linux preferred (CUDA + ROCm compatibility), Windows 11 works

If you have a 3090 (24 GB), drop HunyuanVideo and use LTX-Video for everything plus CogVideoX-5B for image-to-video.

## Networking — DB on one PC, GPU on another

The clean split:
- **DB PC (this one):** Mongo, the 02-19 ingest scripts, the agent-spawned script generation, the orchestrator that picks the next aircraft to render.
- **GPU PC:** runs a small HTTP service (FastAPI) exposing endpoints for TTS / text-to-video / music / subtitles. The orchestrator on the DB PC POSTs jobs to the GPU PC and pulls back artifacts.

A simpler v0: SSH/rsync. The DB PC writes a job folder, rsyncs to the GPU PC, kicks off render via SSH, rsyncs result back. No HTTP service needed.

## render_short.py — single-Short orchestrator (skeleton)

```python
def render_short(slug: str, out_path: Path) -> None:
    doc = aircraft().find_one({"_id": slug})
    script = doc["publish"]["shortform_script"]

    workdir = Path("video_pipeline/workdir") / slug
    workdir.mkdir(parents=True, exist_ok=True)

    narration = tts(script["voiceover"], workdir / "narration.wav")
    timing    = subtitles(narration, script["voiceover"], workdir / "subtitles.json")
    music     = music_gen(doc["publish"]["music_mood"], duration=script["duration_target_seconds"], dest=workdir / "music.wav")

    clips = []
    for i, shot in enumerate(script["shot_list"]):
        clip = video_gen(shot["visual_prompt"], duration=shot["end_seconds"] - shot["start_seconds"], dest=workdir / f"shot_{i:02d}.mp4")
        clips.append(clip)

    title_card = render_title_card(script["title_card"], workdir / "title.png")
    end_card   = render_end_card(script["end_card_cta"], workdir / "end.png")

    assemble(
        clips=clips,
        narration=narration,
        music=music,
        subtitles=timing,
        title_card=title_card,
        end_card=end_card,
        out=out_path,
    )
```

## Daily cron — pick + render 4 Shorts/day

```python
def pick_next_per_category() -> list[str]:
    """For each category, pick the highest-composite-score aircraft
    that has publish.shortform_script and no publish.shortform_render_path."""
    picks = []
    for cat in ["commercial", "military", "general-aviation", "historic"]:
        doc = aircraft().find_one(
            {
                "category": cat,
                "publish.shortform_script": {"$exists": True},
                "publish.shortform_render_path": {"$exists": False},
            },
            sort=[("scores.composite", -1)],
        )
        if doc:
            picks.append(doc["_id"])
    return picks
```

Schedule with `cron` (Linux) or Task Scheduler (Windows) to run daily at 03:00. After each render, set `publish.shortform_render_path` so it's not re-rendered.

## What's already pre-generated (zero GPU work)

After running this session's pipeline you have, per aircraft, for the top 100 of each category:

- `publish.hooks.shortform` — 3-sec cold-open hook
- `publish.shortform_script.voiceover` — full 100-130 word narration **(generating now via 4 agents)**
- `publish.shortform_script.shot_list` — 5-8 shots with `visual_prompt` ready for text-to-video
- `publish.shortform_script.title_card` — first 1.5 sec title overlay
- `publish.shortform_script.end_card_cta` — last 1.5 sec call-to-action
- `publish.thumbnail_concept` — for the Short's preview image
- `publish.hashtags.tiktok` — caption hashtags
- `publish.music_mood` — text prompt for MusicGen

All you need to do on the GPU PC is run the per-stage models and ffmpeg.

## Upload automation (optional v2)

- **YouTube:** [`google-api-python-client`](https://github.com/googleapis/google-api-python-client) — official YouTube Data API. Upload + set title/description/tags from the `publish` subdoc.
- **TikTok:** No official API for personal channels; use a browser-automation library or [`tikapi`](https://tikapi.io) (paid). Many creators upload TikTok manually.
- **Instagram Reels:** Graph API for business accounts.

Recommended: build YouTube auto-upload first, do TikTok/Reels manually until the channel proves out.

## Cost estimate

- **Capex:** GPU PC (~$2,000-3,500 depending on parts)
- **Opex:** $0/month for the pipeline (all OSS, electricity excluded)
- **Compute time per Short on RTX 4090:**
  - F5-TTS: ~10 sec
  - LTX-Video × 6 shots: ~3 min total
  - WhisperX: ~5 sec
  - MusicGen: ~20 sec
  - ffmpeg: ~5 sec
  - **Total: ~4 min per Short. 4 Shorts/day = ~16 min/day of GPU time.**

## Status

- [x] Mongo `publish` subdoc shape extended with `shortform_script` field
- [x] Agents pre-generating `publish.shortform_script` for 400 aircraft (in flight)
- [ ] `video_pipeline/` scaffold + per-stage abstraction modules (next: I'll lay these down so the GPU PC just plugs in)
- [ ] First end-to-end test render of one Short
- [ ] Daily cron + auto-upload
