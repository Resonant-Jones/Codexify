# Command Bus, Auth, Tool Calls, and Automations

This guide covers the current backend contract for:

- identity/auth in API calls
- creating a `run_id`
- streaming run events
- legacy tool shim behavior
- automation execution paths

## 1) Identity model (what must be present)

There are two identity layers:

1. Transport auth (`X-API-Key`, optional bearer/cookie depending on auth mode)
2. Invocation actor (required by command bus invoke contract)

For command execution, the server validates both:

- request is authenticated by API key/session
- `actor.id` claim matches the authenticated subject (or delegated rules)

### Actor payload shape

Use:

```json
{
  "actor": {
    "kind": "human",
    "id": "local"
  }
}
```

Do not use `type`; use `kind`.

## 2) Canonical run lifecycle (how `run_id` is created)

`run_id` is created by `POST /api/guardian/commands/invoke`.

Recommended sequence:

1. Fetch command catalog from `GET /api/guardian/commands/manifest`
2. Pick a `command_id`
3. Invoke with `invoke_version`, `actor`, and `arguments`
4. Read `run_id` from response
5. Stream events at `GET /api/guardian/commands/runs/{run_id}/events`

### Minimal working example

```bash
export BASE_URL="http://localhost:8888"
export API_KEY="${GUARDIAN_API_KEY:?GUARDIAN_API_KEY not set}"
export USER_ID="${CODEXIFY_SINGLE_USER_ID:-local}"

CMD_ID="$(
  curl -sS -H "X-API-Key: $API_KEY" \
    "$BASE_URL/api/guardian/commands/manifest" \
  | jq -r '
      .commands[]
      | select(.operation_id=="ping_ping_get" or (.method=="GET" and .path_template=="/ping"))
      | .command_id
    ' | head -n1
)"

RESP="$(
  curl -sS \
    -H "X-API-Key: $API_KEY" \
    -H "X-User-Id: $USER_ID" \
    -H "Content-Type: application/json" \
    -X POST "$BASE_URL/api/guardian/commands/invoke" \
    -d "{
      \"invoke_version\":\"1.0\",
      \"command_id\":\"$CMD_ID\",
      \"actor\":{\"kind\":\"human\",\"id\":\"$USER_ID\"},
      \"arguments\":{\"path_params\":{},\"query\":{},\"headers\":{}}
    }"
)"

echo "$RESP" | jq
RUN_ID="$(echo "$RESP" | jq -r '.run_id')"
echo "RUN_ID=$RUN_ID"

curl -N -sS \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-Id: $USER_ID" \
  "$BASE_URL/api/guardian/commands/runs/$RUN_ID/events?after_seq=0"
```

## 3) Legacy tools shim behavior

Legacy endpoints:

- `POST /tools/execute`
- `POST /api/tools/execute`
- `GET /tools/manifest`
- `GET /api/tools/manifest`

These now shim-forward to command bus and include deprecation headers:

- `X-Codexify-Deprecated: true`
- `X-Codexify-Deprecation-Replaced-By: /api/guardian/commands/<manifest|invoke>`
- `X-Codexify-Deprecation-Phase: 1.5`

### Actor synthesis in shim

If legacy request omits `actor`, shim derives actor from identity context:

- `X-User-Id` if present
- otherwise single-user identity fallback (`CODEXIFY_SINGLE_USER_ID`, default `local`)

If no identity context is available, shim rejects with `401 missing_identity_context`.

## 4) Common failure modes

### `missing_identity_context`

Cause:

- no usable `X-User-Id` and no single-user fallback resolved

Fix:

- pass `X-User-Id` explicitly for CLI calls
- verify `CODEXIFY_SINGLE_USER_ID` config

### `invalid_actor`

Cause:

- actor schema mismatch (for example, `type` instead of `kind`)

Fix:

- use `actor.kind` with one of `human | agent | system`

### `actor_claim_not_permitted`

Cause:

- `actor.id` does not match authenticated subject

Fix:

- align `actor.id` with the same user identity used by request auth

## 5) Tool calls vs automations (current state)

### Immediate tool calls

- Legacy: `POST /api/tools/execute` (shim)
- Canonical: `POST /api/guardian/commands/invoke`
- Returns `run_id`/status and supports SSE events

### Scheduled automations

- API surface: `/api/cron/*`
- Create jobs at `POST /api/cron/jobs`
- Trigger ad hoc run at `POST /api/cron/jobs/{job_id}/trigger`
- Inspect history at `GET /api/cron/jobs/{job_id}/runs`

This is the durable automation lane today. Command bus approvals/policy lanes are planned for later phases.

## 6) CLI checklist

Before invoking commands from shell scripts:

1. Ensure `GUARDIAN_API_KEY` is set
2. Set `BASE_URL` explicitly
3. Pass `X-User-Id` explicitly for deterministic identity
4. Use canonical command bus endpoints for new integrations
5. Treat `/tools/*` as compatibility-only

## 7) Host shell key bootstrap (common local issue)

If your current shell does not have `GUARDIAN_API_KEY` exported, requests can fail
or be misleading during debugging. Bootstrap from `.env` in the current shell:

```bash
set -a
source .env
set +a
```

Quick verification:

```bash
curl -sS -H "X-API-Key: ${GUARDIAN_API_KEY:-}" \
  "http://localhost:8888/authz/debug" | jq
```

Expected: `received_api_key` should be masked and non-empty when a key is loaded.

Optional helper script:

```bash
source scripts/dev/export-guardian-key.sh
```

By default it does not print the key. Set `PRINT_GUARDIAN_API_KEY=1` only when
you explicitly need to inspect the value.
