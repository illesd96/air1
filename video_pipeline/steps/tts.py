"""Text-to-speech adapter — F5-TTS by default.

Replaceable: swap the backend in config.toml. Each backend returns a wav file
on disk and a list of word-timings, ideally; if a backend can't provide
timings, the subtitles step uses WhisperX to align after the fact.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TTSResult:
    audio_path: Path
    word_timings: list[dict] | None  # [{"word": "It", "start": 0.0, "end": 0.12}, ...]


def synthesize(text: str, dest: Path, *, backend: str, voice_sample: Path | None,
               ref_text: str | None = None, device: str = "cuda:0") -> TTSResult:
    if backend == "f5-tts":
        return _f5_tts(text, dest, voice_sample, ref_text, device)
    if backend == "xtts-v2":
        return _xtts(text, dest, voice_sample, device)
    if backend == "piper":
        return _piper(text, dest)
    raise ValueError(f"unknown tts backend: {backend}")


def _f5_tts(text: str, dest: Path, voice_sample: Path, ref_text: str | None, device: str) -> TTSResult:
    # The CLI form is the simplest:
    #   f5-tts_infer-cli --ref_audio voice.wav --ref_text "..." --gen_text "..." --output_path narration.wav
    # The Python API is also fine; pin to whatever F5-TTS revision you installed.
    import subprocess
    args = [
        "f5-tts_infer-cli",
        "--ref_audio", str(voice_sample),
        "--gen_text", text,
        "--output_path", str(dest),
    ]
    if ref_text:
        args += ["--ref_text", ref_text]
    subprocess.run(args, check=True)
    return TTSResult(audio_path=dest, word_timings=None)


def _xtts(text: str, dest: Path, voice_sample: Path, device: str) -> TTSResult:
    from TTS.api import TTS
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    tts.tts_to_file(text=text, speaker_wav=str(voice_sample), language="en", file_path=str(dest))
    return TTSResult(audio_path=dest, word_timings=None)


def _piper(text: str, dest: Path) -> TTSResult:
    # CPU fallback — for batches if GPU is saturated.
    import subprocess
    subprocess.run(["piper", "--model", "en_US-lessac-medium", "--output_file", str(dest)],
                   input=text, text=True, check=True)
    return TTSResult(audio_path=dest, word_timings=None)
