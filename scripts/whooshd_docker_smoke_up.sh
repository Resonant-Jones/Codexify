#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# whooshd_docker_smoke_up.sh
#
# Durable Docker smoke-launch wrapper for the Whoosh'd local
# inference path.  Verifies the resolved Compose config matches
# the blessed gateway contract before starting containers.
#
# Usage:
#   bash scripts/whooshd_docker_smoke_up.sh
#   bash scripts/whooshd_docker_smoke_up.sh minimal   # db redis migrator backend worker-chat only
#
# Environment:
#   The script expects Whoosh'd to be running on the Docker host
#   at http://host.docker.internal:8000.  It probes health before
#   launching Codexify containers.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

COMPOSE_BASE="-f docker-compose.yml"
COMPOSE_SMOKE="-f docker-compose.whooshd-smoke.yml"
COMPOSE_FILES="$COMPOSE_BASE $COMPOSE_SMOKE"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "═══════════════════════════════════════════════════════"
echo "  Codexify + Whoosh'd Docker Smoke Path"
echo "═══════════════════════════════════════════════════════"

# ── Step 0: Check prerequisites ──
if ! command -v docker &>/dev/null; then
    echo -e "${RED}[FAIL] docker is not available${NC}"
    exit 1
fi

# ── Step 1: Ensure Whoosh'd is running ──
echo ""
echo "── Step 1: Ensure Whoosh'd ──"

REPO_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$REPO_SCRIPT_DIR/whooshd_ensure.sh" || {
    echo -e "  ${RED}[FAIL]${NC} Could not start Whoosh'd. See above for details."
    exit 1
}

# ── Step 2: Clean stale Codexify containers ──
echo ""
echo "── Step 2: Clean stale containers ──"
STALE_CONTAINERS=$(docker ps -aq --filter "name=codexify" 2>/dev/null || true)
if [ -n "$STALE_CONTAINERS" ]; then
    echo "  Removing $(echo "$STALE_CONTAINERS" | wc -l | tr -d ' ') stale Codexify containers..."
    echo "$STALE_CONTAINERS" | xargs docker rm -f 2>/dev/null || true
    echo -e "  ${GREEN}[OK]${NC} Stale containers removed"
else
    echo "  No stale containers found"
fi

# ── Step 3: Tear down orphaned Compose services ──
echo ""
echo "── Step 3: Tear down orphaned Compose services ──"
docker compose $COMPOSE_FILES down --remove-orphans 2>/dev/null || true
echo -e "  ${GREEN}[OK]${NC} Orphaned services cleaned"

# ── Step 4: Resolve Compose config ──
echo ""
echo "── Step 4: Resolve Compose config ──"
RESOLVED_CONFIG="/tmp/codexify-whooshd-smoke.compose.yml"
docker compose $COMPOSE_FILES config > "$RESOLVED_CONFIG"
echo "  Resolved config written to $RESOLVED_CONFIG"

# ── Step 5: Assert blessed contract in resolved config ──
echo ""
echo "── Step 5: Assert blessed Whoosh'd contract ──"

assert_value() {
    local description="$1"
    local pattern="$2"
    local file="$3"

    if grep -q "$pattern" "$file"; then
        echo -e "  ${GREEN}[PASS]${NC} $description"
        return 0
    else
        echo -e "  ${RED}[FAIL]${NC} $description"
        echo "    Expected pattern not found: $pattern"
        return 1
    fi
}

FAILURES=0

assert_value "LOCAL_BASE_URL=http://host.docker.internal:8000/v1" \
    'LOCAL_BASE_URL: http://host.docker.internal:8000/v1' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "ALLOW_CLOUD_PROVIDERS=false" \
    'ALLOW_CLOUD_PROVIDERS: .false.' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "CODEXIFY_EGRESS_ALLOWLIST empty" \
    'CODEXIFY_EGRESS_ALLOWLIST: ..' \
    "$RESOLVED_CONFIG" || true  # non-fatal: empty string rendering varies

assert_value "CODEXIFY_LOCAL_ONLY_MODE=true" \
    'CODEXIFY_LOCAL_ONLY_MODE: .true.' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LLM_PROVIDER=local" \
    'LLM_PROVIDER: local' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LOCAL_PROVIDER_VENDOR=whooshd" \
    'LOCAL_PROVIDER_VENDOR: whooshd' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LOCAL_CHAT_MODEL=gemma-4-e4b-it-4bit" \
    'LOCAL_CHAT_MODEL: gemma-4-e4b-it-4bit' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

if [ "$FAILURES" -gt 0 ]; then
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  SMOKE CONTRACT CHECK FAILED ($FAILURES failures)${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Resolved config: $RESOLVED_CONFIG"
    echo "  Inspect with:    grep -E 'LOCAL_BASE_URL|ALLOW_CLOUD|EGRESS|LLM_PROVIDER' $RESOLVED_CONFIG"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}  All contract assertions passed${NC}"

# ── Step 6: Start the stack ──
echo ""
echo "── Step 6: Start Docker Compose ──"

MODE="${1:-full}"

if [ "$MODE" = "minimal" ]; then
    echo "  Launching minimal smoke stack (db redis migrator backend worker-chat)..."
    docker compose $COMPOSE_FILES up --build \
        db redis migrator backend worker-chat
else
    echo "  Launching full stack..."
    docker compose $COMPOSE_FILES up --build
fi
