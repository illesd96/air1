"""Music generator — MusicGen by default."""
from __future__ import annotations

from pathlib import Path


def generate(prompt: str, dest: Path, *, duration_seconds: float,
             backend: str = "musicgen", model: str = "facebook/musicgen-medium",
             device: str = "cuda:0") -> Path:
    if backend == "musicgen":
        from audiocraft.models import MusicGen
        import torchaudio
        m = MusicGen.get_pretrained(model)
        m.set_generation_params(duration=duration_seconds)
        wav = m.generate([prompt])
        torchaudio.save(str(dest), wav[0].cpu(), m.sample_rate)
        return dest
    if backend == "stable-audio-open":
        # https://huggingface.co/stabilityai/stable-audio-open-1.0
        raise NotImplementedError("plug Stable Audio Open in here")
    raise ValueError(f"unknown music backend: {backend}")
