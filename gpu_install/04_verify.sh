#!/usr/bin/env bash
# End-to-end sanity check + (optional) one test render.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

c_green() { printf '\033[1;32m%s\033[0m\n' "$1"; }
c_red()   { printf '\033[1;31m%s\033[0m\n' "$1"; }

# ---------- imports + GPU ----------
python - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA not available"
print(f"GPU: {torch.cuda.get_device_name(0)}  /  VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")

# Each module just imports; nothing heavy here.
import f5_tts
import diffusers
import audiocraft
import whisperx
import pymongo
print("All packages import OK")
PY

# ---------- Mongo reachable (via pymongo) ----------
. .env
count=$(python - <<'PY'
import os
from pymongo import MongoClient
c = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=5000)
print(c[os.environ.get("MONGO_DB", "aircraft")]["aircraft"].estimated_document_count())
PY
)
if [[ -z "$count" || "$count" -lt 100 ]]; then
    c_red "Mongo unreachable or empty (count=$count)"
    exit 1
fi
c_green "Mongo reachable. Aircraft count: $count"

# ---------- ffmpeg ----------
ffmpeg -version | head -1

# ---------- optional test render ----------
read -rp "Run a test render for f-16? (~5 min) [y/N]: " ans
if [[ "${ans:-N}" =~ ^[Yy]$ ]]; then
    python video_pipeline/render_short.py f-16
    ls -lh renders/military/f-16.mp4
    c_green "Test render complete."
else
    c_green "Skipped test render. When ready: python video_pipeline/render_short.py f-16"
fi
