"""Word-level forced alignment via WhisperX, then SRT export."""
from __future__ import annotations

import json
from pathlib import Path


def align(narration_wav: Path, transcript: str, dest_json: Path, *,
          model: str = "large-v3", language: str = "en", device: str = "cuda:0") -> Path:
    """Align the known transcript to the audio, producing word-level timestamps."""
    import whisperx
    audio = whisperx.load_audio(str(narration_wav))
    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    result = whisperx.align(
        [{"text": transcript, "start": 0.0, "end": 0.0}],   # placeholder; aligner fills in
        align_model, metadata, audio, device, return_char_alignments=False,
    )
    dest_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return dest_json


def export_srt(align_json: Path, dest_srt: Path, *, style: str = "kinetic") -> Path:
    """Convert alignment to SRT. `kinetic` makes one cue per word; `static` one per sentence."""
    data = json.loads(align_json.read_text(encoding="utf-8"))
    words = []
    for seg in data.get("segments", []):
        words.extend(seg.get("words", []))

    lines: list[str] = []
    if style == "kinetic":
        for idx, w in enumerate(words, start=1):
            lines.append(str(idx))
            lines.append(f"{_fmt(w['start'])} --> {_fmt(w['end'])}")
            lines.append(w["word"].strip())
            lines.append("")
    else:
        for idx, seg in enumerate(data.get("segments", []), start=1):
            lines.append(str(idx))
            lines.append(f"{_fmt(seg['start'])} --> {_fmt(seg['end'])}")
            lines.append(seg.get("text", "").strip())
            lines.append("")
    dest_srt.write_text("\n".join(lines), encoding="utf-8")
    return dest_srt


def _fmt(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
