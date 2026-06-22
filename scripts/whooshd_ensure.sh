#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# whooshd_ensure.sh
#
# Idempotent Whoosh'd launcher for Codexify development.
#
# Usage:
#   bash scripts/whooshd_ensure.sh
#
# What it does:
#   1. Probes localhost:8000/health
#   2. If healthy → done
#   3. If not → starts Whoosh'd via the installed `whooshd` CLI
#      with --codexify (binds 0.0.0.0:8000) and --adapter mlx
#   4. Waits up to 30s for health check
#
# Requires the `whooshd` CLI to be available on PATH (installed at
# ~/.local/bin/whooshd or similar).  If not found, prints setup
# instructions.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

HEALTH_URL="${WHOOSHD_HEALTH_URL:-http://127.0.0.1:8000/health}"
MAX_WAIT_SEC="${WHOOSHD_ENSURE_TIMEOUT:-30}"

echo "── Whoosh'd ensure ──"

# ── Step 1: Probe existing ──
if curl -sf --max-time 3 "$HEALTH_URL" >/dev/null 2>&1; then
    echo -e "  ${GREEN}[OK]${NC} Whoosh'd already running"
    echo ""
    curl -sf "$HEALTH_URL" | python3 -m json.tool 2>/dev/null || true
    exit 0
fi

echo "  Whoosh'd not running. Starting..."

# ── Step 2: Locate whooshd CLI ──
WHOOSHD_BIN=""
if command -v whooshd &>/dev/null; then
    WHOOSHD_BIN="$(command -v whooshd)"
elif [[ -x "$HOME/.local/bin/whooshd" ]]; then
    WHOOSHD_BIN="$HOME/.local/bin/whooshd"
fi

if [[ -z "$WHOOSHD_BIN" ]]; then
    echo -e "  ${RED}[FAIL]${NC} whooshd CLI not found on PATH or at ~/.local/bin/whooshd"
    echo ""
    echo "  Clone Whoosh'd and symlink the CLI:"
    echo "    git clone <whooshd-repo> /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd"
    echo "    ln -s /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/bin/whooshd ~/.local/bin/whooshd"
    exit 1
fi

echo "  Using whooshd at: $WHOOSHD_BIN"

# ── Step 3: Start Whoosh'd in Codexify mode ──
# --codexify binds 0.0.0.0:8000 so Docker containers can reach it
# --adapter mlx uses MLX backend
WHOOSHD_LOG="${WHOOSHD_LOG:-/tmp/whooshd-codexify.log}"
echo "  Starting: whooshd --codexify --adapter mlx"
echo "  Log: $WHOOSHD_LOG"

nohup "$WHOOSHD_BIN" --codexify --adapter mlx > "$WHOOSHD_LOG" 2>&1 &
WHOOSHD_PID=$!
echo "  PID: $WHOOSHD_PID"

# ── Step 4: Wait for health ──
echo "  Waiting for health check (max ${MAX_WAIT_SEC}s)..."
ELAPSED=0
while [[ $ELAPSED -lt $MAX_WAIT_SEC ]]; do
    if curl -sf --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
        echo ""
        echo -e "  ${GREEN}[OK]${NC} Whoosh'd healthy after ${ELAPSED}s"
        curl -sf "$HEALTH_URL" | python3 -m json.tool 2>/dev/null || true
        exit 0
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [[ $((ELAPSED % 5)) -eq 0 ]]; then
        echo "    ... ${ELAPSED}s"
    fi
done

echo ""
echo -e "  ${RED}[FAIL]${NC} Whoosh'd did not become healthy within ${MAX_WAIT_SEC}s"
echo "  Check log: tail -50 $WHOOSHD_LOG"
exit 1
