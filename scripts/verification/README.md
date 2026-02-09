# Verification Scripts

## e2e_control_plane_checklist.sh

Deterministic end-to-end verification for Guardian control-plane wiring.

What it verifies:
- clean repo state
- backend health endpoint
- authenticated cron route access
- authenticated browser approvals route access
- authenticated channels route access
- websocket connect + auth + basic RPC frame exchange

The script is read-only and safe to run repeatedly.

## Usage

```bash
chmod +x scripts/verification/e2e_control_plane_checklist.sh
GUARDIAN_API_KEY="your-key" \
GUARDIAN_API_URL="http://localhost:8000" \
GUARDIAN_WS_URL="ws://localhost:8000/api/ws" \
GUARDIAN_USER_ID="default" \
./scripts/verification/e2e_control_plane_checklist.sh
```

## Environment variables

- `GUARDIAN_API_KEY` required
- `GUARDIAN_API_URL` default `http://localhost:8000`
- `GUARDIAN_WS_URL` default `ws://localhost:8000/api/ws`
- `GUARDIAN_USER_ID` default `default`
- `GUARDIAN_VERIFY_TIMEOUT_SECONDS` default `10`

## Failure model

- exits non-zero on first failed step
- prints one explicit remediation message per failure
