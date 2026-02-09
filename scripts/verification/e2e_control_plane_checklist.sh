#!/usr/bin/env bash
set -euo pipefail

say() {
  printf '\n[%s] %s\n' "$1" "$2"
}

fail() {
  printf '\n[FAIL] %s\n' "$1" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

API_URL="${GUARDIAN_API_URL:-http://localhost:8000}"
WS_URL="${GUARDIAN_WS_URL:-ws://localhost:8000/api/ws}"
API_KEY="${GUARDIAN_API_KEY:-}"
USER_ID="${GUARDIAN_USER_ID:-default}"
TIMEOUT="${GUARDIAN_VERIFY_TIMEOUT_SECONDS:-10}"

say STEP "Preflight tool checks"
require_cmd curl
require_cmd python
require_cmd git

say STEP "Repo cleanliness"
if [[ -n "$(git status --porcelain -uall)" ]]; then
  fail "Working tree is not clean. Run: git status --porcelain -uall"
fi

say STEP "HTTP health endpoint"
if ! curl -fsS --max-time "$TIMEOUT" "$API_URL/health" >/dev/null; then
  fail "Cannot reach $API_URL/health. Start backend first."
fi

if [[ -z "$API_KEY" ]]; then
  fail "GUARDIAN_API_KEY is required for protected checks. Export GUARDIAN_API_KEY and retry."
fi

say STEP "Cron route auth + availability"
if ! curl -fsS --max-time "$TIMEOUT" -H "X-API-Key: $API_KEY" "$API_URL/api/cron/jobs" >/dev/null; then
  fail "Cron route check failed at $API_URL/api/cron/jobs with provided API key."
fi

say STEP "Browser route auth + availability"
if ! curl -fsS --max-time "$TIMEOUT" -H "X-API-Key: $API_KEY" "$API_URL/api/browser/approvals" >/dev/null; then
  fail "Browser approvals route check failed at $API_URL/api/browser/approvals with provided API key."
fi

say STEP "Channels route auth + availability"
if ! curl -fsS --max-time "$TIMEOUT" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-Id: $USER_ID" \
  "$API_URL/api/channels/configs" >/dev/null; then
  fail "Channels route check failed at $API_URL/api/channels/configs with provided API key/user."
fi

say STEP "WebSocket auth/connect check"
python - <<'PY' "$WS_URL" "$API_KEY" "$TIMEOUT"
import asyncio
import json
import sys

ws_url = sys.argv[1]
api_key = sys.argv[2]
timeout_s = float(sys.argv[3])

try:
    import websockets  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"websockets dependency is unavailable: {exc}")

async def main() -> None:
    async with websockets.connect(
        ws_url,
        additional_headers={"X-API-Key": api_key},
        open_timeout=timeout_s,
    ) as ws:
        await ws.send(json.dumps({"id": "e2e-check", "method": "ping", "params": {}}))
        await asyncio.wait_for(ws.recv(), timeout=timeout_s)

asyncio.run(main())
PY

say PASS "Control-plane verification checks passed"
