#!/usr/bin/env bash
# Narrow operator bring-up for Zac's Mac Studio local beta deployment.
#
# This script is a front door over the existing supported Docker + Whoosh'd
# smoke/proof seams. It does not enable Pattern/Instance sync, federation,
# graph writes, cloud providers, or any non-Compose release path.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MODE="minimal"
RUN_PROOF=0
CHECK_ONLY=0

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/zac_mac_studio_bringup.sh [--full] [--prove] [--check-only]

Options:
  --full        Start the full Compose stack instead of the minimal smoke stack.
  --prove       After detached bring-up, run the supported-path proof harness.
  --check-only  Check host prerequisites and exit before starting services.

Scope:
  Supported local beta Docker path only. This does not ship or validate
  Pattern/Instance sync, federation, graph writes, or cloud-provider beta use.
EOF
}

log() {
  printf '[zac-bringup] %s\n' "$*"
}

fail() {
  printf '[zac-bringup] FAIL: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

env_value() {
  local key="$1"
  grep -h -E "^${key}=" .env 2>/dev/null | tail -n1 | sed -E "s/^${key}=//"
}

for arg in "$@"; do
  case "$arg" in
    --full)
      MODE="full"
      ;;
    --prove)
      RUN_PROOF=1
      ;;
    --check-only)
      CHECK_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      fail "Unknown argument: $arg"
      ;;
  esac
done

log "Checking Zac Mac Studio local beta prerequisites"

[[ "$(uname -s)" == "Darwin" ]] || fail "This operator path is scoped to macOS"
if [[ "$(uname -m)" != "arm64" ]]; then
  fail "This operator path expects Apple Silicon arm64 hardware"
fi

require_cmd docker
require_cmd curl
require_cmd jq
require_cmd python3

docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is not available"
docker info >/dev/null 2>&1 || fail "Docker daemon is not reachable. Start Docker Desktop and retry."

[[ -f .env ]] || fail "Missing .env. Copy .env.template to .env and set local beta values."

GUARDIAN_KEY="$(scripts/dev/dev-key.sh 2>/dev/null || true)"
[[ -n "$GUARDIAN_KEY" ]] || fail "GUARDIAN_API_KEY is missing from .env"
export GUARDIAN_API_KEY="$GUARDIAN_KEY"

VITE_KEY="$(env_value VITE_GUARDIAN_API_KEY)"
[[ -n "$VITE_KEY" ]] || fail "VITE_GUARDIAN_API_KEY is missing from .env"

NEO4J_PASS="$(env_value NEO4J_PASS)"
[[ -n "$NEO4J_PASS" ]] || fail "NEO4J_PASS is missing from .env"

if ! curl -sf --max-time 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then
  if ! command -v whooshd >/dev/null 2>&1 && [[ ! -x "$HOME/.local/bin/whooshd" ]]; then
    fail "Whoosh'd is not running and the whooshd CLI was not found. See docs/Ops/WHOOSHD_LOCAL_RUNTIME_RUNBOOK.md."
  fi
fi

log "Prerequisites are present"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  log "Check-only complete; no services started"
  exit 0
fi

log "Starting supported Whoosh'd Docker smoke path in detached mode: $MODE"
bash scripts/whooshd_docker_smoke_up.sh "$MODE" --detach

log "Backend health:"
curl -fsS http://127.0.0.1:8888/health | jq '{status, supported_profile, provider_runtime: .provider_runtime?}' || true

log "Chat health:"
curl -fsS http://127.0.0.1:8888/health/chat | jq '.' || true

log "LLM health:"
curl -fsS -H "X-API-Key: $GUARDIAN_API_KEY" http://127.0.0.1:8888/health/llm | jq '.' || true

if [[ "$RUN_PROOF" -eq 1 ]]; then
  log "Running supported-path proof through the same Whoosh'd Compose override"
  CODEXIFY_COMPOSE_ARGS="-f docker-compose.yml -f docker-compose.whooshd-smoke.yml" \
    GUARDIAN_API_KEY="$GUARDIAN_API_KEY" \
    bash scripts/verification/run_supported_path_proof.sh
fi

log "Bring-up complete"
log "UI: http://127.0.0.1:5173"
log "API docs: http://127.0.0.1:8888/docs"
