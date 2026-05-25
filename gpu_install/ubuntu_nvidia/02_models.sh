#!/usr/bin/env bash
# Install + pre-download all model weights.
# Total disk usage: ~50-65 GB after this step.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

c_green() { printf '\033[1;32m%s\033[0m\n' "$1"; }

# Hugging Face cache lives in ~/.cache/huggingface/ by default — set HF_HOME to
# put it on a bigger disk if you want.
# export HF_HOME=/mnt/big-disk/hf-cache

# ---------- F5-TTS ----------
c_green "[1/5] F5-TTS"
pip install --upgrade f5-tts
# F5-TTS 1.1.x changed load_model() signature; pre-cache via huggingface_hub.
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("SWivid/F5-TTS", allow_patterns=["F5TTS_v1_Base/*", "F5TTS_Base/*"])
snapshot_download("charactr/vocos-mel-24khz")
print("F5-TTS weights cached")
PY

# ---------- Diffusers stack (LTX-Video + HunyuanVideo + CogVideoX live here) ----------
c_green "[2/5] Diffusers + dependencies"
pip install --upgrade diffusers transformers accelerate sentencepiece protobuf \
    imageio imageio-ffmpeg ftfy einops omegaconf safetensors

# ---------- LTX-Video ----------
c_green "[3/5] LTX-Video (~14 GB download)"
python - <<'PY'
from diffusers import LTXPipeline
import torch
LTXPipeline.from_pretrained("Lightricks/LTX-Video", torch_dtype=torch.bfloat16)
print("LTX-Video weights cached")
PY

# ---------- HunyuanVideo ----------
c_green "[4/5] HunyuanVideo (~28 GB; FP8 is smaller, see notes)"
python - <<'PY'
import os, torch
from diffusers import HunyuanVideoPipeline
# Community repackaged for Diffusers
HunyuanVideoPipeline.from_pretrained("hunyuanvideo-community/HunyuanVideo", torch_dtype=torch.bfloat16)
print("HunyuanVideo weights cached")
PY

# ---------- MusicGen ----------
c_green "[5/5] MusicGen (transformers) + WhisperX"
# Use transformers' native MusicGen instead of audiocraft (which pulls
# spacy + thinc + a broken PyAV build chain).
pip install --upgrade whisperx
python - <<'PY'
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration
print("Downloading MusicGen-medium via transformers (~3 GB)...")
AutoProcessor.from_pretrained("facebook/musicgen-medium")
MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-medium")
print("MusicGen ready (transformers backend)")

import whisperx
whisperx.load_model("large-v3", "cuda", compute_type="float16")
print("WhisperX ready")
PY

du -sh ~/.cache/huggingface 2>/dev/null || true
c_green "All models cached."
