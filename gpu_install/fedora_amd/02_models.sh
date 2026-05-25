#!/usr/bin/env bash
# Install + pre-download all models that run on ROCm (Radeon 8060S / gfx1151).
# Notable changes from the NVIDIA path:
#   - HunyuanVideo is SKIPPED. It's impractical on Strix Halo for now.
#   - LTX-Video carries both workhorse and hero shots.
#   - CogVideoX-5B is added as an image-to-video fallback.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

# Honor the ROCm env from ~/.bashrc
export PATH=/opt/rocm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export HSA_OVERRIDE_GFX_VERSION=${HSA_OVERRIDE_GFX_VERSION:-11.0.0}
export PYTORCH_ROCM_ARCH=${PYTORCH_ROCM_ARCH:-gfx1100}

c_green() { printf '\033[1;32m%s\033[0m\n' "$1"; }
c_blue()  { printf '\033[1;34m%s\033[0m\n' "$1"; }

# ---------- F5-TTS ----------
c_green "[1/5] F5-TTS"
pip install --upgrade f5-tts
# F5-TTS 1.1.x changed load_model() signature; pre-cache the weights via the
# stable huggingface_hub API instead. First render will use the cache.
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("SWivid/F5-TTS", allow_patterns=["F5TTS_v1_Base/*", "F5TTS_Base/*"])
snapshot_download("charactr/vocos-mel-24khz")  # vocoder
print("F5-TTS weights cached")
PY

# ---------- Diffusers stack ----------
c_green "[2/5] Diffusers + dependencies"
pip install --upgrade diffusers transformers accelerate sentencepiece protobuf \
    imageio imageio-ffmpeg ftfy einops omegaconf safetensors

# ---------- LTX-Video (workhorse — handles every shot on Strix Halo) ----------
c_green "[3/5] LTX-Video (~14 GB download)"
python - <<'PY'
import torch
from diffusers import LTXPipeline
LTXPipeline.from_pretrained("Lightricks/LTX-Video", torch_dtype=torch.bfloat16)
print("LTX-Video weights cached")
PY

# ---------- CogVideoX-5B (image-to-video, alternative for stills you already have) ----------
c_green "[4/5] CogVideoX-5B (image-to-video)"
python - <<'PY'
import torch
from diffusers import CogVideoXImageToVideoPipeline
CogVideoXImageToVideoPipeline.from_pretrained("THUDM/CogVideoX-5b-I2V", torch_dtype=torch.bfloat16)
print("CogVideoX-5B weights cached")
PY

# ---------- MusicGen + WhisperX ----------
c_green "[5/5] MusicGen + WhisperX"
pip install --upgrade audiocraft whisperx
python - <<'PY'
from audiocraft.models import MusicGen
MusicGen.get_pretrained("facebook/musicgen-medium")
print("MusicGen ready")

# WhisperX uses CTranslate2 under the hood — on ROCm we run the large model on
# CPU which is plenty fast for 60-second clips on a 16-core Ryzen.
import whisperx
whisperx.load_model("large-v3", "cpu", compute_type="int8")
print("WhisperX ready (CPU int8 — Strix Halo CPU is fast enough for short clips)")
PY

du -sh ~/.cache/huggingface 2>/dev/null || true
c_blue "Note: HunyuanVideo is intentionally skipped on this hardware. Set hero_backend = \"ltx-video\" in config.toml."
