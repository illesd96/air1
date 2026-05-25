"""Music generator — MusicGen via transformers (no audiocraft dependency)."""
from __future__ import annotations

from pathlib import Path


def generate(prompt: str, dest: Path, *, duration_seconds: float,
             backend: str = "musicgen", model: str = "facebook/musicgen-medium",
             device: str = "cuda:0") -> Path:
    if backend == "musicgen":
        return _musicgen_transformers(prompt, dest, duration_seconds, model, device)
    if backend == "stable-audio-open":
        # https://huggingface.co/stabilityai/stable-audio-open-1.0
        raise NotImplementedError("plug Stable Audio Open in here")
    raise ValueError(f"unknown music backend: {backend}")


def _musicgen_transformers(prompt: str, dest: Path, duration_seconds: float,
                            model_name: str, device: str) -> Path:
    """MusicGen via Hugging Face transformers — works on CUDA and ROCm."""
    import scipy.io.wavfile
    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    processor = AutoProcessor.from_pretrained(model_name)
    model = MusicgenForConditionalGeneration.from_pretrained(
        model_name, torch_dtype=torch.float16
    ).to(device)

    # MusicGen generates at 32 kHz; 50 tokens ≈ 1 second of audio.
    max_new_tokens = int(duration_seconds * 50)

    inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
    with torch.no_grad():
        audio = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True)

    sampling_rate = model.config.audio_encoder.sampling_rate
    wav = audio[0, 0].float().cpu().numpy()
    dest.parent.mkdir(parents=True, exist_ok=True)
    scipy.io.wavfile.write(dest, sampling_rate, wav)
    return dest
