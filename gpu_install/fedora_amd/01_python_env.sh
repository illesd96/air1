#!/usr/bin/env bash
# Python 3.11 venv + PyTorch (ROCm 6.2 wheels).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# PyTorch's ROCm 6.2 index ships cp310/cp311/cp312 wheels (not 3.13 yet), so we
# pin to 3.12. Only accept SYSTEM Pythons — uv-managed and pyenv Pythons under
# ~/.local/share/{uv,pyenv}/ build relocatable interpreters that break venvs.
find_system_python() {
    for cand in /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3.10; do
        if [[ -x "$cand" ]] && "$cand" -c "import ensurepip, venv" >/dev/null 2>&1; then
            echo "$cand"
            return
        fi
    done
}

PY="$(find_system_python || true)"

if [[ -z "$PY" ]]; then
    echo "No system /usr/bin/python3.{10,11,12} found. Installing python3.12 via dnf..."
    sudo dnf install -y python3.12 python3.12-devel
    PY="$(find_system_python || true)"
fi

if [[ -z "$PY" ]]; then
    echo "FAILED: could not find or install a suitable system Python." >&2
    echo "Try manually:  sudo dnf install -y python3.12 python3.12-devel" >&2
    exit 1
fi
echo "Using interpreter: $($PY --version) at $PY"

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

# CRITICAL ORDER: PyTorch ROCm MUST be installed before anything that depends
# on torch (whisperx, diffusers, audiocraft) — otherwise pip will pull the
# CUDA build from PyPI as a transitive dependency, and `--upgrade` won't
# switch a CUDA wheel to a ROCm one because the version number looks "newer".
#
# If a previous run left a CUDA torch in this venv, blow it away first.
pip uninstall -y torch torchvision torchaudio \
    pytorch-triton pytorch-triton-rocm triton \
    nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 \
    nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 \
    nvidia-cufile-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 \
    nvidia-cusparse-cu12 nvidia-cusparselt-cu12 nvidia-nccl-cu12 \
    nvidia-nvjitlink-cu12 nvidia-nvtx-cu12 \
    2>/dev/null || true

# PyTorch ROCm 6.3 has cp310/cp311/cp312 wheels for torch 2.5-2.8. ROCm 6.2
# index only goes up to ~2.5.x, which whisperx (which needs ~2.8) won't accept.
pip install --no-cache-dir --upgrade --force-reinstall \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/rocm6.3

# Now safe to install the rest — torch is locked in.
pip install -r video_pipeline/requirements.txt

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
