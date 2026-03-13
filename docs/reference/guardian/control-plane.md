# Guardian Control Plane: End-to-End Verification

This guide verifies the integrated Guardian control-plane flow with deterministic, read-only checks where possible.

## Prerequisites

- Backend running and reachable at `GUARDIAN_API_URL` (default: `http://localhost:8000`)
- WebSocket route running at `GUARDIAN_WS_URL` (default: `ws://localhost:8000/api/ws`)
- Valid API key in `GUARDIAN_API_KEY`
- Optional user identity in `GUARDIAN_USER_ID` (default: `default`)

## Environment Variables

- `GUARDIAN_API_URL` default `http://localhost:8000`
- `GUARDIAN_WS_URL` default `ws://localhost:8000/api/ws`
- `GUARDIAN_API_KEY` required for protected routes
- `GUARDIAN_USER_ID` default `default`
- `GUARDIAN_VERIFY_TIMEOUT_SECONDS` default `10`
- `REDIS_URL` default `redis://redis:6379/0`
- `UI_SESSION_TTL_SECONDS` default `1209600` (14 days)
- `UI_SESSION_MAX_TTL_SECONDS` default `2592000` (30 days)
- `UI_SESSION_MIN_TTL_SECONDS` default `60`

## UI Session Cache (Session Spine)

SessionSpine persists multi-tab UI state through `/api/ui/session`:

- `GET /api/ui/session?user_id=<user>&device_id=<device>`
- `PUT /api/ui/session`
- `PATCH /api/ui/session`
- `DELETE /api/ui/session?user_id=<user>&device_id=<device>`

Redis key format:

`ui:v1:{urlencoded_user_id}:{urlencoded_device_id}:session`

The value is JSON `SessionState` (tabs, activeTabId, drafts, model per tab, version).

Detailed behavior and invariants are documented in `docs/session-spine.md`.

Write-path guarantees:

- Invalid payloads with no valid tabs are rejected (`400`).
- `activeTabId` is normalized to an existing tab when possible.
- Corrupt cached JSON is discarded on read and treated as cache miss.
- Draft sync policy is local-first in the composer; `/api/ui/session` writes occur on debounced or boundary commits, not per keystroke.

### Auth Readiness Gate (Frontend)

Frontend startup now uses a single auth-readiness state:

- `status`: `unknown | authenticated | unauthenticated`
- `ready`: `true` only after auth has been resolved from token/dev-key inputs
- `token`: optional cached bearer token (when present)

Protected startup behavior:

- `/api/ui/session` hydration and persistence are gated behind authenticated+ready state.
- Thread/document startup fetches are gated behind authenticated+ready state.
- Gated skips are normal and logged once at debug level (no warning/error spam).

401 behavior:

- First HTTP `401` transitions auth state to `unauthenticated`.
- Protected polling/retries are expected to stop at the caller gate until re-authentication.
- No automatic retry loop is performed for `401`.

### SSE Auth + Backoff Policy

SSE connection to `/api/events` follows auth-readiness:

- Connect only when auth is `ready` and `authenticated`.
- Do not connect while auth is `unknown` or `unauthenticated`.
- On transition to `unauthenticated`, close EventSource and stop reconnect attempts.

Reconnect policy for non-auth failures:

- Exponential steps with jitter: `250ms -> 500ms -> 1s -> 2s -> 5s (max)`
- Backoff step logging is emitted at most once per step.
- Event-level failure spam is intentionally suppressed.

### Session API Examples

Get session state:

```bash
curl -sS \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/ui/session?user_id=${GUARDIAN_USER_ID:-default}&device_id=test-device" | jq
```

Set session state:

```bash
curl -sS -X PUT \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/ui/session" \
  -d '{
    "user_id":"'"${GUARDIAN_USER_ID:-default}"'",
    "device_id":"test-device",
    "ttl_seconds":1209600,
    "state":{
      "userId":"'"${GUARDIAN_USER_ID:-default}"'",
      "deviceId":"test-device",
      "tabs":[{"tabId":"tab-1","modelId":"default","createdAt":"2026-02-14T00:00:00.000Z","updatedAt":"2026-02-14T00:00:00.000Z"}],
      "activeTabId":"tab-1",
      "version":1,
      "updatedAt":"2026-02-14T00:00:00.000Z"
    }
  }'
```

Delete session state:

```bash
curl -sS -X DELETE \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/ui/session?user_id=${GUARDIAN_USER_ID:-default}&device_id=test-device"
```

### Redis Inspection and Safe Clear

List all UI session cache keys:

```bash
redis-cli --scan --pattern 'ui:v1:*:*:session'
```

Inspect one exact key:

```bash
USER_ID="${GUARDIAN_USER_ID:-default}"
DEVICE_ID="test-device"
ENC_USER="$(python -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1].strip(), safe=\"\"))' "$USER_ID")"
ENC_DEVICE="$(python -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1].strip(), safe=\"\"))' "$DEVICE_ID")"
redis-cli GET "ui:v1:${ENC_USER}:${ENC_DEVICE}:session"
```

Clear one device-scoped key safely:

```bash
redis-cli DEL "ui:v1:${ENC_USER}:${ENC_DEVICE}:session"
```

Clear only UI session cache keys (bulk):

```bash
redis-cli --scan --pattern 'ui:v1:*:*:session' | xargs -r redis-cli DEL
```

### Redis Restart Simulation

```bash
docker compose restart redis
```

Expected behavior after reload:

- SessionSpine rehydrates from Redis if key exists.
- If Redis is empty/cold, SessionSpine creates a default single tab.
- Threads/messages still load from durable backend storage.

## WS Connect/Auth Example

Run a minimal WebSocket auth/connect check:

```bash
GUARDIAN_API_KEY="your-key" GUARDIAN_WS_URL="ws://localhost:8000/api/ws" \
python - <<'PY'
import asyncio
import json
import os
import websockets

ws_url = os.getenv("GUARDIAN_WS_URL", "ws://localhost:8000/api/ws")
api_key = os.getenv("GUARDIAN_API_KEY", "")

async def main() -> None:
    async with websockets.connect(
        ws_url,
        additional_headers={"X-API-Key": api_key},
        open_timeout=10,
    ) as ws:
        await ws.send(json.dumps({"id": "verify-1", "method": "ping", "params": {}}))
        message = await asyncio.wait_for(ws.recv(), timeout=10)
        print(message)

asyncio.run(main())
PY
```

Expected outcome: socket opens and returns a structured response frame (or deterministic auth/validation error frame).

## Cron Examples

List cron jobs:

```bash
curl -sS \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/cron/jobs"
```

Create cron job:

```bash
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/cron/jobs" \
  -d '{"name":"verify-job","schedule":"@hourly","job_type":"noop","payload":{},"is_enabled":true}'
```

Trigger a run:

```bash
curl -sS -X POST \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/cron/jobs/<job_id>/trigger"
```

Observe run records:

```bash
curl -sS \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/cron/jobs/<job_id>/runs"
```

## Browser Approvals Lifecycle

List approvals:

```bash
curl -sS \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/browser/approvals"
```

Request approval:

```bash
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/browser/approvals/request" \
  -d '{"operation":"evaluate","target":"https://example.com","reason":"verification"}'
```

Approve request:

```bash
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/browser/approvals/<approval_id>/approve" \
  -d '{"reason":"approved for verification"}'
```

Session lifecycle:

```bash
curl -sS -X POST -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/browser/sessions"

curl -sS -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/browser/sessions/<session_id>"

curl -sS -X DELETE -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/browser/sessions/<session_id>"
```

## Channels Pairing Flow

Create channel config:

```bash
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  -H "X-User-Id: ${GUARDIAN_USER_ID:-default}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/channels/configs" \
  -d '{"channel":"slack","config_json":{"token_ref":"vault://slack/token"}}'
```

Create pairing request:

```bash
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  -H "X-User-Id: ${GUARDIAN_USER_ID:-default}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/channels/pairings/slack" \
  -d '{"external_id":"user-123","status":"pending"}'
```

Approve pairing:

```bash
curl -sS -X PATCH \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  -H "X-User-Id: ${GUARDIAN_USER_ID:-default}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/channels/pairings/slack/user-123" \
  -d '{"status":"approved"}'
```

List message audit:

```bash
curl -sS \
  -H "X-API-Key: ${GUARDIAN_API_KEY}" \
  -H "X-User-Id: ${GUARDIAN_USER_ID:-default}" \
  "${GUARDIAN_API_URL:-http://localhost:8000}/api/channels/messages/slack?limit=50"
```

## Deterministic Checklist

Use the script:

```bash
chmod +x scripts/verification/e2e_control_plane_checklist.sh
./scripts/verification/e2e_control_plane_checklist.sh
```

The script exits `0` on pass and non-zero with one clear remediation message on failure.
