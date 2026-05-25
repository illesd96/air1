#!/usr/bin/env bash
# Fedora 41/42/43 system packages + AMD GPU stack (Mesa + ROCm).
# Target hardware: AMD Ryzen AI Max+ 395 with Radeon 8060S (RDNA 3.5, gfx1151).

set -euo pipefail

c_red()   { printf '\033[1;31m%s\033[0m\n' "$1"; }
c_green() { printf '\033[1;32m%s\033[0m\n' "$1"; }
c_blue()  { printf '\033[1;34m%s\033[0m\n' "$1"; }

if [[ "$(id -u)" -eq 0 ]]; then
    c_red "Don't run this as root. Run as your normal user; sudo prompts will appear as needed."
    exit 1
fi

# ---------- base toolchain ----------
# `--skip-unavailable` so any single missing optional package doesn't abort the
# whole transaction; we re-validate the critical ones below.
sudo dnf install -y --skip-unavailable \
    @development-tools \
    git git-lfs curl wget unzip \
    ffmpeg-free libsndfile libass libass-devel \
    mesa-libGL mesa-libEGL mesa-vulkan-drivers vulkan-loader \
    python3 python3-devel python3-pip python3-virtualenv \
    pkgconf openssh-server

# RPM Fusion enables full ffmpeg (not just ffmpeg-free) — needed for libx264.
if ! rpm -q rpmfusion-free-release >/dev/null 2>&1; then
    sudo dnf install -y \
        https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
fi
# Replace ffmpeg-free with the full ffmpeg
sudo dnf swap -y ffmpeg-free ffmpeg --allowerasing || true

git lfs install

# ---------- AMD GPU stack (ROCm) ----------
# Strix Halo's iGPU (Radeon 8060S) is gfx1151. ROCm 6.2.x and later expose it,
# though some packages still need HSA_OVERRIDE_GFX_VERSION=11.0.0 as a hint.
if ! command -v rocminfo >/dev/null 2>&1; then
    c_blue "Installing ROCm + ROCm runtimes..."
    sudo dnf install -y \
        rocminfo rocm-smi rocm-clinfo \
        rocm-hip rocm-hip-devel \
        rocm-opencl rocm-opencl-devel \
        rocblas hipblas \
        miopen-hip rccl \
        hip-runtime-amd || {
        c_red "ROCm packages weren't found in the default Fedora repos. Falling back to AMD's official ROCm repo."

        sudo tee /etc/yum.repos.d/rocm.repo > /dev/null <<'EOF'
[ROCm-6.2]
name=ROCm 6.2 (Fedora)
baseurl=https://repo.radeon.com/rocm/rhel9/6.2/main
enabled=1
priority=50
gpgcheck=1
gpgkey=https://repo.radeon.com/rocm/rocm.gpg.key
EOF
        sudo dnf install -y rocminfo rocm-smi rocm-clinfo \
            rocm-hip rocm-hip-devel rocm-opencl rocm-opencl-devel \
            rocblas hipblas miopen-hip rccl
    }

    # User must be in the render+video groups to talk to /dev/kfd and /dev/dri/*
    sudo usermod -aG render,video "$USER"
fi

# Persist ROCm env to ~/.bashrc (idempotent)
if ! grep -q 'aircraft bootstrap (ROCm)' "$HOME/.bashrc"; then
    cat >> "$HOME/.bashrc" << 'EOF'

# aircraft bootstrap (ROCm)
export PATH=/opt/rocm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
# Strix Halo Radeon 8060S maps to gfx1151. PyTorch may not yet ship kernels for
# this exact target — overriding to gfx1100 (RDNA 3) keeps things working.
export HSA_OVERRIDE_GFX_VERSION=11.0.0
# AMD-specific knobs
export PYTORCH_ROCM_ARCH=gfx1100
EOF
fi
export PATH=/opt/rocm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export HSA_OVERRIDE_GFX_VERSION=11.0.0
export PYTORCH_ROCM_ARCH=gfx1100

# ---------- verify ----------
c_green "rocminfo (truncated):"
rocminfo 2>/dev/null | grep -E "Name:|Marketing Name|gfx" | head -10 || c_red "rocminfo failed — re-log in after group change, then re-run."

c_green "Mesa Vulkan driver:"
vulkaninfo --summary 2>/dev/null | grep -E "deviceName|driverName" || true

c_green "ffmpeg encoders:"
ffmpeg -hide_banner -encoders 2>&1 | grep -E 'libx264|aac' || c_red "ffmpeg missing libx264"

# Note about render group — needs re-login to take effect
if ! id -nG "$USER" | grep -qw render; then
    c_red "============================================================"
    c_red "  You were added to the 'render' and 'video' groups."
    c_red "  Log out and back in (or reboot) for it to take effect,"
    c_red "  then re-run:  bash gpu_install/bootstrap.sh"
    c_red "============================================================"
    exit 0   # bootstrap won't mark this stage done; will retry next time
fi
