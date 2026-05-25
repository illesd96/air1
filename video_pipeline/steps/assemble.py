"""Final composition via ffmpeg.

Stitches: title card (silent 1.5s) → ordered shot clips with narration over the
whole, music ducked under it, subtitles burned in → end card (silent 1.5s) →
output 1080×1920 H.264 + AAC.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path


def assemble(
    clips: list[Path],
    narration: Path,
    music: Path,
    subtitles_srt: Path,
    title_card: Path,
    end_card: Path,
    out: Path,
    *,
    fps: int = 24,
    title_card_seconds: float = 1.5,
    end_card_seconds: float = 1.5,
    burn_in_subs: bool = True,
    music_volume: float = 0.18,
) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)

    # 1) Build a list of all visual segments: title_card → clips → end_card
    #    Each becomes an input. The title and end cards are PNGs we extend to N seconds.
    inputs: list[str] = []
    filter_parts: list[str] = []
    next_idx = 0

    def add_image_as_clip(img: Path, dur: float) -> int:
        nonlocal next_idx
        inputs.extend(["-loop", "1", "-t", f"{dur:.3f}", "-i", str(img)])
        idx = next_idx
        next_idx += 1
        # scale to 1080x1920 just in case
        filter_parts.append(f"[{idx}:v]scale=1080:1920,setsar=1,fps={fps}[v{idx}]")
        return idx

    def add_video_clip(p: Path) -> int:
        nonlocal next_idx
        inputs.extend(["-i", str(p)])
        idx = next_idx
        next_idx += 1
        filter_parts.append(f"[{idx}:v]scale=1080:1920,setsar=1,fps={fps}[v{idx}]")
        return idx

    title_idx = add_image_as_clip(title_card, title_card_seconds)
    clip_idxs = [add_video_clip(c) for c in clips]
    end_idx = add_image_as_clip(end_card, end_card_seconds)

    all_v = [f"[v{i}]" for i in [title_idx, *clip_idxs, end_idx]]
    concat = "".join(all_v) + f"concat=n={len(all_v)}:v=1:a=0[vbase]"
    filter_parts.append(concat)

    # Subtitles burn-in
    if burn_in_subs:
        srt_path = str(subtitles_srt).replace("\\", "/")
        filter_parts.append(f"[vbase]subtitles='{srt_path}':force_style='Fontsize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=180'[vout]")
    else:
        filter_parts.append("[vbase]null[vout]")

    # Audio: narration (full duration, no offset — title card is silent intro) + music (ducked)
    narration_idx = next_idx; next_idx += 1
    inputs.extend(["-i", str(narration)])
    music_idx = next_idx; next_idx += 1
    inputs.extend(["-i", str(music)])

    # Delay narration by title_card_seconds so it lines up with the first real clip
    filter_parts.append(f"[{narration_idx}:a]adelay={int(title_card_seconds*1000)}|{int(title_card_seconds*1000)},apad[narr]")
    filter_parts.append(f"[{music_idx}:a]volume={music_volume}[mus]")
    filter_parts.append("[narr][mus]amix=inputs=2:duration=first:dropout_transition=0[aout]")

    filtergraph = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filtergraph,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out),
    ]
    print(">", " ".join(shlex.quote(x) for x in cmd))
    subprocess.run(cmd, check=True)
    return out
