#!/usr/bin/env bash
# System packages, NVIDIA driver, CUDA 12.4 toolkit.
# Reboot required after NVIDIA driver install.

set -euo pipefail

c_red()   { printf '\033[1;31m%s\033[0m\n' "$1"; }
c_green() { printf '\033[1;32m%s\033[0m\n' "$1"; }

if [[ "$(id -u)" -eq 0 ]]; then
    c_red "Don't run this as root. Run as your normal user; sudo prompts will appear as needed."
    exit 1
fi

# ---------- apt packages ----------
sudo apt update
sudo apt install -y \
    build-essential git git-lfs curl wget unzip \
    ffmpeg libsndfile1 libass-dev \
    libgl1 libglib2.0-0 \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    pkg-config \
    openssh-server \
    mongodb-clients

git lfs install

# ---------- NVIDIA driver ----------
if ! command -v nvidia-smi >/dev/null 2>&1; then
    sudo ubuntu-drivers autoinstall
    c_red "============================================================"
    c_red "  NVIDIA driver installed. You MUST reboot now."
    c_red "  After reboot, run again:  bash gpu_install/bootstrap.sh"
    c_red "============================================================"
    exit 0   # marker won't be written; on next run we resume here
fi

c_green "NVIDIA driver already active:"
nvidia-smi | head -20

# ---------- CUDA toolkit 12.4 ----------
if ! command -v nvcc >/dev/null 2>&1 || ! nvcc --version | grep -q "release 12"; then
    if [[ ! -f cuda-keyring_1.1-1_all.deb ]]; then
        wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
    fi
    sudo dpkg -i cuda-keyring_1.1-1_all.deb || true
    sudo apt update
    sudo apt install -y cuda-toolkit-12-4

    # Bash login
    if ! grep -q 'cuda-12.4/bin' "$HOME/.bashrc"; then
        cat >> "$HOME/.bashrc" << 'EOF'

# CUDA 12.4 (added by aircraft bootstrap)
export PATH=/usr/local/cuda-12.4/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH
EOF
    fi
fi

# Make CUDA available to the rest of this script
export PATH=/usr/local/cuda-12.4/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:${LD_LIBRARY_PATH:-}

c_green "CUDA toolkit version:"
nvcc --version | tail -2

# ---------- ffmpeg sanity ----------
if ! ffmpeg -encoders 2>&1 | grep -q libx264; then
    c_red "ffmpeg has no libx264 encoder — install a newer ffmpeg build (sudo add-apt-repository ppa:savoury1/ffmpeg6 && sudo apt install -y ffmpeg)"
    exit 1
fi
c_green "ffmpeg + libx264 + AAC OK"
