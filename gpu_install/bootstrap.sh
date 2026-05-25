#!/usr/bin/env bash
# Top-level bootstrap. Detects the OS + GPU vendor and routes to the right
# subfolder of stage scripts.
#
#   gpu_install/
#     bootstrap.sh           ← this file
#     ubuntu_nvidia/         ← apt + CUDA + NVIDIA driver path
#     fedora_amd/            ← dnf + ROCm + AMD GPU path
#     03_configure.sh        ← shared (no OS/GPU specifics)
#     04_verify.sh           ← shared
#
# Stages:
#   00 — System packages + GPU driver/runtime  (may reboot or require re-login)
#   01 — Python venv + PyTorch matching the GPU
#   02 — Model installs + weight pre-download
#   03 — Configure (Mongo URI, voice sample)
#   04 — Verify end-to-end
#
# State lives in gpu_install/.state/ — delete a marker file to redo a stage.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGES="$ROOT/gpu_install"
STATE="$STAGES/.state"
mkdir -p "$STATE"

c_green() { printf '\033[1;32m%s\033[0m\n' "$1"; }
c_blue()  { printf '\033[1;34m%s\033[0m\n' "$1"; }
c_red()   { printf '\033[1;31m%s\033[0m\n' "$1"; }

# ---------- detect platform ----------
distro="unknown"
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    distro="${ID:-unknown}"
fi

gpu_vendor="unknown"
if lspci 2>/dev/null | grep -qi 'vga.*nvidia\|3d.*nvidia'; then
    gpu_vendor="nvidia"
elif lspci 2>/dev/null | grep -qi 'vga.*amd\|3d.*amd\|vga.*ati\|display.*amd'; then
    gpu_vendor="amd"
fi

platform=""
if [[ "$distro" =~ ^(ubuntu|debian|pop)$ ]] && [[ "$gpu_vendor" == "nvidia" ]]; then
    platform="ubuntu_nvidia"
elif [[ "$distro" =~ ^(fedora|rhel|centos|rocky|alma)$ ]] && [[ "$gpu_vendor" == "amd" ]]; then
    platform="fedora_amd"
elif [[ "$distro" == "fedora" ]] && [[ "$gpu_vendor" == "nvidia" ]]; then
    c_red "Detected Fedora + NVIDIA — not covered yet. You can adapt fedora_amd/00_system.sh swapping ROCm for the rpmfusion 'akmod-nvidia' + 'xorg-x11-drv-nvidia-cuda' packages."
    exit 1
elif [[ "$distro" =~ ^(ubuntu|debian|pop)$ ]] && [[ "$gpu_vendor" == "amd" ]]; then
    c_red "Detected Ubuntu + AMD — not covered yet. You can adapt ubuntu_nvidia scripts: replace the NVIDIA section with AMD's ROCm install (https://rocm.docs.amd.com/projects/install-on-linux)."
    exit 1
else
    c_red "Couldn't detect a supported (distro, GPU) combo. distro=$distro gpu=$gpu_vendor"
    c_red "Set the PLATFORM env var to one of: ubuntu_nvidia, fedora_amd"
    [[ -n "${PLATFORM:-}" ]] && platform="$PLATFORM"
    [[ -z "$platform" ]] && exit 1
fi

c_green "Detected platform: $platform  (distro=$distro, gpu=$gpu_vendor)"
echo

run_stage() {
    local stage="$1"
    local dir="$2"
    local marker="$STATE/${stage}.done"
    if [[ -f "$marker" ]]; then
        c_green "[skip] $stage already complete (rm $marker to redo)"
        return 0
    fi
    c_blue "[run]  $dir/$stage.sh"
    bash "$STAGES/$dir/$stage.sh"
    touch "$marker"
    c_green "[done] $stage"
}

run_shared() {
    local stage="$1"
    local marker="$STATE/${stage}.done"
    if [[ -f "$marker" ]]; then
        c_green "[skip] $stage already complete"
        return 0
    fi
    c_blue "[run]  $stage.sh (shared)"
    bash "$STAGES/$stage.sh"
    touch "$marker"
    c_green "[done] $stage"
}

c_blue "===== aircraft GPU pipeline bootstrap ($platform) ====="
echo "Project root: $ROOT"
echo

run_stage 00_system    "$platform"
# After 00, if the script needs you to reboot (NVIDIA driver) or re-login (AMD render
# group), the marker won't be set; just re-run bootstrap.sh and it picks up here.
run_stage 01_python_env "$platform"
run_stage 02_models     "$platform"
run_shared 03_configure
run_shared 04_verify

c_green "===== DONE — run a test:  source .venv/bin/activate && python video_pipeline/render_short.py f-16 ====="
