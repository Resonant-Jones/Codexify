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
