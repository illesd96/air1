# Aircraft video pipeline

End-to-end auto-render for vertical Shorts. See `../docs/VIDEO_PIPELINE.md` for the full design.

## Quick start (GPU PC)

```bash
# 1. Install deps (one time)
pip install -r video_pipeline/requirements.txt
# install F5-TTS, LTX-Video, WhisperX, MusicGen per their docs

# 2. Configure
cp video_pipeline/config.example.toml video_pipeline/config.toml
# edit GPU device, model paths, voice sample path

# 3. Render one Short
python video_pipeline/render_short.py sr-71

# 4. Render today's batch (4 — one per category)
python video_pipeline/render_today.py
```

Output: `renders/<category>/<slug>.mp4` plus the workdir under `video_pipeline/workdir/<slug>/` with all the intermediate artifacts.

## Module layout

| File | What it does |
|---|---|
| `render_short.py` | Orchestrator — takes a slug, runs every stage, outputs the final MP4 |
| `render_today.py` | Picks the next-best aircraft per category, renders all four |
| `steps/tts.py` | F5-TTS / XTTS adapter — text → narration.wav |
| `steps/video_gen.py` | LTX-Video / HunyuanVideo / CogVideoX adapter — visual_prompt → clip.mp4 |
| `steps/music.py` | MusicGen adapter — mood prompt + duration → music.wav |
| `steps/subtitles.py` | WhisperX adapter — narration + transcript → word-timed JSON, then SRT |
| `steps/title_cards.py` | Pillow + ImageMagick fonts — rendered overlay PNGs |
| `steps/assemble.py` | ffmpeg composition: clips + narration + music + subtitles + cards → 1080×1920 MP4 |

Each `steps/*.py` is a thin wrapper. Replace the model behind a step without changing the orchestrator.
