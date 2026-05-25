#!/usr/bin/env bash
# Restore the MongoDB dump on this Fedora PC.
#
# Run AFTER you've copied aircraft.archive over from the Windows DB PC and
# placed it under ~/Downloads (or pass a different path as the first arg).
#
# Usage:
#   bash gpu_install/restore_db.sh                       # uses ~/Downloads/aircraft.archive
#   bash gpu_install/restore_db.sh /path/to/dump.archive

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

c_blue()  { printf '\033[1;34m%s\033[0m\n' "$1"; }
c_green() { printf '\033[1;32m%s\033[0m\n' "$1"; }
c_red()   { printf '\033[1;31m%s\033[0m\n' "$1"; }

# ---------- locate archive ----------
ARCHIVE="${1:-$HOME/Downloads/aircraft.archive}"
if [[ ! -f "$ARCHIVE" ]]; then
    c_red "No archive at: $ARCHIVE"
    c_red "Pass the path as the first arg, e.g.:"
    c_red "    bash gpu_install/restore_db.sh ~/somewhere/aircraft.archive"
    exit 1
fi
c_green "Using archive: $ARCHIVE  ($(du -h "$ARCHIVE" | cut -f1))"

# ---------- install podman + podman-compose if not present ----------
if ! command -v podman >/dev/null 2>&1 || ! command -v podman-compose >/dev/null 2>&1; then
    c_blue "Installing podman + podman-compose..."
    sudo dnf install -y --skip-unavailable podman podman-compose
fi

# Prefer `podman compose` (subcommand) over `podman-compose` (Python wrapper).
COMPOSE=""
if podman compose version >/dev/null 2>&1; then
    COMPOSE="podman compose"
elif command -v podman-compose >/dev/null 2>&1; then
    COMPOSE="podman-compose"
else
    c_red "Neither 'podman compose' nor 'podman-compose' is available."
    exit 1
fi
c_green "Compose backend: $COMPOSE"

# ---------- bring up the containers ----------
c_blue "Starting Mongo + Mongo Express..."
$COMPOSE up -d

# Wait for mongo to be reachable
c_blue "Waiting for Mongo to accept connections..."
for i in $(seq 1 30); do
    if podman exec aircraft-mongo mongosh --quiet \
        -u aircraft -p aircraft --authenticationDatabase admin \
        --eval 'db.runCommand({ ping: 1 }).ok' 2>/dev/null | grep -q '^1$'; then
        c_green "Mongo is up."
        break
    fi
    if [[ "$i" -eq 30 ]]; then
        c_red "Mongo didn't come up within 60s. Check 'podman logs aircraft-mongo'."
        exit 1
    fi
    sleep 2
done

# ---------- copy archive in + restore ----------
c_blue "Copying archive into the container..."
podman cp "$ARCHIVE" aircraft-mongo:/tmp/aircraft.archive

c_blue "Restoring (this is fast — gzipped, 1.9 MB)..."
podman exec aircraft-mongo mongorestore \
    --uri="mongodb://aircraft:aircraft@localhost:27017/?authSource=admin" \
    --gzip --archive=/tmp/aircraft.archive --drop

# ---------- verify ----------
count=$(podman exec aircraft-mongo mongosh --quiet \
    -u aircraft -p aircraft --authenticationDatabase admin \
    --eval 'db.getSiblingDB("aircraft").aircraft.countDocuments({})')

if [[ "$count" =~ ^[0-9]+$ ]] && [[ "$count" -ge 1000 ]]; then
    c_green "============================================================"
    c_green "  Restored. Aircraft count: $count"
    c_green "  Mongo Express UI: http://localhost:8081"
    c_green "  Mongo URI: mongodb://aircraft:aircraft@localhost:27017/?authSource=admin"
    c_green "============================================================"
else
    c_red "Restore reported but count is unexpected: '$count'"
    c_red "Run manually:  podman exec -it aircraft-mongo mongosh -u aircraft -p aircraft --authenticationDatabase admin"
    exit 1
fi

# ---------- pre-populate .env so stage 03 doesn't have to ask ----------
ENV_FILE="$ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" << 'EOF'
MONGO_URI=mongodb://aircraft:aircraft@localhost:27017/?authSource=admin
MONGO_DB=aircraft
USER_AGENT=aircraft-db/0.1 (pilles@eev-systems.com)
IMAGE_ROOT=./data/images
EOF
    c_green "Wrote .env pointing at localhost."
else
    c_blue ".env already exists — leaving it alone."
fi

c_green "Next: bash gpu_install/bootstrap.sh   (skips straight to stage 02/03/04)"
