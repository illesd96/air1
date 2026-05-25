#!/usr/bin/env bash
# Interactive — sets up Mongo URI + voice sample paths in config.toml and .env.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

c_blue()  { printf '\033[1;34m%s\033[0m\n' "$1"; }
c_red()   { printf '\033[1;31m%s\033[0m\n' "$1"; }

# ---------- .env ----------
if [[ ! -f .env ]]; then
    c_blue "Setting up .env"
    read -rp "Enter the LAN IP of the Windows DB PC (e.g. 192.168.1.42): " db_ip
    cat > .env << EOF
MONGO_URI=mongodb://aircraft:aircraft@${db_ip}:27017/?authSource=admin
MONGO_DB=aircraft
USER_AGENT=aircraft-db/0.1 (pilles@eev-systems.com)
EOF
fi
. .env
echo "MONGO_URI = $MONGO_URI"

# ---------- Mongo reachability ----------
c_blue "Testing Mongo reachability..."
if ! mongosh "$MONGO_URI" --eval "db.aircraft.countDocuments({})" --quiet 2>/dev/null | grep -qE '^[0-9]+$'; then
    c_red "Cannot reach Mongo at $MONGO_URI"
    c_red "  - Check the DB PC's docker-compose.yml binds Mongo to 0.0.0.0 (not 127.0.0.1)"
    c_red "  - Check Windows firewall allows inbound 27017"
    c_red "  - You can edit ~/aircraft/.env then re-run: bash gpu_install/03_configure.sh"
    exit 1
fi
echo "Mongo reachable. Aircraft count: $(mongosh "$MONGO_URI" --eval 'db.aircraft.countDocuments({})' --quiet)"

# ---------- voice sample ----------
mkdir -p video_pipeline/voices
if [[ ! -f video_pipeline/voices/narrator.wav ]]; then
    c_blue "No voice sample found at video_pipeline/voices/narrator.wav"
    echo "Provide a path to a 15-30 second WAV/MP3 recording (mono, 24kHz ideal)."
    read -rp "Voice sample path (leave blank to skip — pipeline will use F5-TTS default): " vsrc
    if [[ -n "$vsrc" && -f "$vsrc" ]]; then
        ffmpeg -y -i "$vsrc" -ac 1 -ar 24000 video_pipeline/voices/narrator.wav
        echo "Saved: video_pipeline/voices/narrator.wav"
    else
        echo "Skipped — using default voice. Drop a WAV in video_pipeline/voices/ later and edit config.toml."
    fi
fi

# ---------- ref_text ----------
ref_text="This is a short reference clip of my normal speaking voice for cloning."
if [[ -f video_pipeline/voices/narrator.wav ]]; then
    read -rp "Type the spoken text of your reference clip (or press Enter for default): " typed
    if [[ -n "$typed" ]]; then
        ref_text="$typed"
    fi
fi

# ---------- config.toml ----------
if [[ ! -f video_pipeline/config.toml ]]; then
    cp video_pipeline/config.example.toml video_pipeline/config.toml
fi

# If we're on the AMD path, force hero_backend = ltx-video (HunyuanVideo is impractical on Strix Halo)
HERO=""
if lspci 2>/dev/null | grep -qi 'vga.*amd\|3d.*amd\|vga.*ati'; then
    HERO="ltx-video"
fi

python - <<PY
import re
p = "video_pipeline/config.toml"
src = open(p, encoding="utf-8").read()
src = re.sub(r'^uri\s*=.*$', f'uri = "${MONGO_URI}"', src, count=1, flags=re.MULTILINE)
src = re.sub(r'^ref_text\s*=.*$', f'ref_text = "${ref_text}"', src, count=1, flags=re.MULTILINE)
hero = "${HERO}"
if hero:
    src = re.sub(r'^hero_backend\s*=.*$', f'hero_backend = "{hero}"', src, count=1, flags=re.MULTILINE)
open(p, "w", encoding="utf-8").write(src)
print("Wrote", p)
PY
