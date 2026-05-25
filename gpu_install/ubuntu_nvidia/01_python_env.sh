#!/usr/bin/env bash
# Python 3.11 venv + PyTorch matching CUDA 12.4.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
    python3.11 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# CRITICAL ORDER: install PyTorch CUDA before anything that depends on torch,
# so transitive deps don't pull a different build from PyPI.
pip install --no-cache-dir --upgrade --force-reinstall \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124

# Now safe to install the rest.
pip install -r video_pipeline/requirements.txt

# Sanity-check
python - <<'PY'
import torch, sys
ok = torch.cuda.is_available()
print(f"torch.__version__   = {torch.__version__}")
print(f"cuda available      = {ok}")
print(f"cuda device         = {torch.cuda.get_device_name(0) if ok else 'NONE'}")
print(f"cuda compute cap.   = {torch.cuda.get_device_capability(0) if ok else None}")
sys.exit(0 if ok else 1)
PY
