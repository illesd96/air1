"""Text-to-video adapter — LTX-Video by default for speed, HunyuanVideo for hero shots.

These are stubs that expect the model's CLI / Python API to be installed.
Replace bodies as needed for your specific install (Diffusers vs custom repo).
"""
from __future__ import annotations

from pathlib import Path


def generate_clip(prompt: str, dest: Path, *, duration_seconds: float, backend: str,
                  resolution: str = "1080x1920", fps: int = 24,
                  device: str = "cuda:0", is_hero: bool = False, hero_backend: str | None = None) -> Path:
    """Generate a text-to-video clip and write to `dest` (mp4)."""
    chosen = hero_backend if (is_hero and hero_backend) else backend
    if chosen == "ltx-video":
        return _ltx_video(prompt, dest, duration_seconds, resolution, fps, device)
    if chosen == "hunyuan-video":
        return _hunyuan_video(prompt, dest, duration_seconds, resolution, fps, device)
    if chosen == "cogvideox-5b":
        return _cogvideox(prompt, dest, duration_seconds, resolution, fps, device)
    if chosen == "wan-2.1":
        return _wan21(prompt, dest, duration_seconds, resolution, fps, device)
    raise ValueError(f"unknown video_gen backend: {chosen}")


def _ltx_video(prompt: str, dest: Path, dur: float, res: str, fps: int, device: str) -> Path:
    # Example via Diffusers — adjust to your install.
    # from diffusers import LTXPipeline
    # pipe = LTXPipeline.from_pretrained("Lightricks/LTX-Video").to(device)
    # frames = pipe(prompt, height=h, width=w, num_frames=int(dur*fps)).frames
    # export_to_video(frames, dest, fps=fps)
    raise NotImplementedError("plug your LTX-Video install in here")


def _hunyuan_video(prompt: str, dest: Path, dur: float, res: str, fps: int, device: str) -> Path:
    # Hunyuan has its own repo + sample_video.py. Easiest to subprocess into it.
    raise NotImplementedError("plug your HunyuanVideo install in here")


def _cogvideox(prompt: str, dest: Path, dur: float, res: str, fps: int, device: str) -> Path:
    # Diffusers supports CogVideoX directly.
    raise NotImplementedError("plug your CogVideoX install in here")


def _wan21(prompt: str, dest: Path, dur: float, res: str, fps: int, device: str) -> Path:
    raise NotImplementedError("plug your Wan 2.1 install in here")


def image_to_video(image: Path, dest: Path, *, duration_seconds: float, motion_prompt: str | None = None,
                   fps: int = 24, device: str = "cuda:0") -> Path:
    """For Ken-Burns-style motion on stills — useful when we have a cover image
    but no need for full text-to-video. CogVideoX-5B and SVD do this well."""
    raise NotImplementedError("plug your image-to-video model in here")
