#!/usr/bin/env bash
# Python 3.11 venv + PyTorch (ROCm 6.2 wheels).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# PyTorch's ROCm 6.2 index ships cp310/cp311/cp312 wheels (not 3.13 yet), so we
# pin to 3.12 by preference. Specifically use /usr/bin/python3.12 to avoid the
# user-local Pythons (~/.local/bin) that may be missing ensurepip.
PY=""
for cand in /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3.10 python3.12 python3.11 python3.10 python3; do
    if [[ -x "$cand" ]] || command -v "$cand" >/dev/null 2>&1; then
        # Confirm ensurepip is available (some user-local builds lack it)
        if "$cand" -c "import ensurepip" >/dev/null 2>&1; then
            PY="$cand"
            break
        fi
    fi
done
if [[ -z "$PY" ]]; then
    echo "No suitable Python (with ensurepip) found. Install python3.12 first:" >&2
    echo "    sudo dnf install -y python3.12 python3.12-devel" >&2
    exit 1
fi
echo "Using interpreter: $($PY --version) at $(command -v $PY || echo $PY)"

# Re-create the venv if a previous run left one behind for a different Python.
if [[ -d .venv ]] && ! .venv/bin/python --version 2>/dev/null | grep -q "$($PY --version | awk '{print $2}' | cut -d. -f1,2)"; then
    echo "Existing .venv uses a different Python — removing."
    rm -rf .venv
fi
if [[ ! -d .venv ]]; then
    "$PY" -m venv .venv || {
        echo "ensurepip path failed; falling back to manual pip bootstrap"
        "$PY" -m venv --without-pip .venv
        curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        .venv/bin/python /tmp/get-pip.py
    }
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
