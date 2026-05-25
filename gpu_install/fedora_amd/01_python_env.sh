#!/usr/bin/env bash
# Python 3.11 venv + PyTorch (ROCm 6.2 wheels).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
    python3.11 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# Pipeline-side small deps
pip install -r video_pipeline/requirements.txt

# PyTorch ROCm wheels. As of 2025-Q4 / 2026-Q1 PyTorch ships ROCm 6.2 builds for cp311.
# When a newer ROCm is needed, bump the URL:  https://pytorch.org/get-started/locally/
pip install --upgrade \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/rocm6.2

# Sanity-check
python - <<'PY'
import torch, sys, os
print("torch.__version__   =", torch.__version__)
print("torch.version.hip   =", getattr(torch.version, "hip", None))
print("cuda available      =", torch.cuda.is_available())   # ROCm exposes itself as CUDA in PyTorch
if torch.cuda.is_available():
    print("device              =", torch.cuda.get_device_name(0))
    print("HSA_OVERRIDE_GFX    =", os.environ.get("HSA_OVERRIDE_GFX_VERSION"))
    print("PYTORCH_ROCM_ARCH   =", os.environ.get("PYTORCH_ROCM_ARCH"))
sys.exit(0 if torch.cuda.is_available() else 1)
PY
