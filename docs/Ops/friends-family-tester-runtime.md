# Friends & Family Tester Runtime

> **Classification:** operator runbook
> **Profile:** `v1-friends-family-web`
> **ADR alignment:** ADR-005 (Runtime Mode and Account Boundary Invariants), ADR-039, ADR-040
> **Last updated:** 2026-07-11

## Purpose

This runbook documents how to run a stable, isolated Codexify instance for invited friends/family testers. The tester instance enables the auth router (register, login, logout) so testers can create real accounts, while keeping the default dev profile (`v1-local-core-web-mcp`) unchanged.

It also gives the tester UI a separate Tailscale identity, `codexify-test`. The Docker sidecar and the `frontend` share one network namespace, and Tailscale Serve proxies only the frontend to tailnet-only HTTPS on TCP 443. The sidecar is not VaultNode's host Tailscale identity, does not use host networking, and does not advertise subnets or an exit node.

## Non-Goals

- This is **not** a production deployment guide.
- This is **not** a public/hosted internet release.
- This is **not** a security hardening guide.
- This is **not** public internet hosting; Tailscale Funnel stays disabled.
- This is **not** a user invitation UX specification.

## How This Differs from Dev

| Aspect | Dev (`v1-local-core-web-mcp`) | Tester (`v1-friends-family-web`) |
|---|---|---|
| Compose project name | `codexify` (default) | `codexify_tester` |
| Env file | `.env` | `.env.tester` |
| Backend host port | `8888` | `127.0.0.1:8889` (operator only) |
| Frontend host port | `5173` | `127.0.0.1:5174` (operator fallback only) |
| Remote browser path | None | `https://codexify-test.<tailnet>.ts.net` on TCP 443 |
| Tailscale identity | VaultNode host identity | `codexify-test` Docker sidecar, tagged `tag:codexify-test` |
| Auth routes enabled | No (quarantined) | Yes |
| User accounts | N/A (single-user dev) | Register/login/logout |
| State isolation | Dev Postgres/Redis/Neo4j volumes | Separate volumes via project name |
| Supported profile | `v1-local-core-web-mcp` | `v1-friends-family-web` |
| Chat provider | Local runtime | DeepSeek `deepseek-v4-flash` only |

The friends/family profile sends chat completions to DeepSeek instead of
Whoosh'd. Its egress allowlist contains only `deepseek`; the API key remains
local-only in `.env.tester`.

## First-Time Setup

### 1. Copy the env template

```bash
cp .env.tester.example .env.tester
```

### 2. Generate real secrets

Use Python to generate cryptographically random secrets:

```bash
python -c "
import secrets
print('GUARDIAN_API_KEY=' + secrets.token_urlsafe(48))
print('GUARDIAN_SESSION_SECRET=' + secrets.token_urlsafe(48))
print('GUARDIAN_JWT_SECRET=' + secrets.token_urlsafe(48))
"
```

Or use OpenSSL:

```bash
echo "GUARDIAN_API_KEY=$(openssl rand -hex 48)"
echo "GUARDIAN_SESSION_SECRET=$(openssl rand -hex 48)"
echo "GUARDIAN_JWT_SECRET=$(openssl rand -hex 48)"
```

Copy the generated values into `.env.tester`, replacing the `<generate-a-real-secret>` placeholders.

### 3. Verify .env.tester is private

```bash
git check-ignore .env.tester && echo "OK: .env.tester is git-ignored" || echo "WARNING: .env.tester may be tracked"
```

### 4. Create the dedicated Tailscale auth key

In the Tailscale admin console, create an auth key with all of these properties:

- reusable, non-ephemeral, and pre-approved when device approval is enabled;
- tagged `tag:codexify-test` (the policy below defines its owner);
- scoped only to this server identity; do not enable Tailscale SSH;
- copied directly into `TAILSCALE_TEST_AUTHKEY` in the untracked `.env.tester`.

Set `TAILSCALE_TEST_FQDN` to `codexify-test.<your-tailnet>.ts.net`. The exact tailnet domain is visible in the admin console. Do not set `TS_ROUTES`, `--advertise-exit-node`, `--accept-routes`, or `network_mode: host` for this service.

## Tailnet policy and sharing

Add this focused snippet to the existing tailnet policy. It is intentionally additive: retain existing operator rules, but do not add a broad `*:*` rule for testers.

```hujson
{
  "tagOwners": {
    "tag:codexify-test": ["autogroup:admin"],
  },
  "grants": [
    // A recipient of a machine-sharing invite may reach only the Tailscale
    // sidecar's private HTTPS listener. It has no grant to VaultNode itself.
    {
      "src": ["autogroup:shared"],
      "dst": ["tag:codexify-test"],
      "ip": ["tcp:443"],
    },
  ],
  "tests": [
    {
      "src": "<tester@example.com>",
      "accept": ["tag:codexify-test:443"],
      "deny": [
        "tag:codexify-test:22",
        "tag:codexify-test:5432",
        "<vaultnode-host-alias>:22",
        "<vaultnode-host-alias>:8888",
      ],
    },
  ],
}
```

Replace both angle-bracket placeholders before saving the policy; `<vaultnode-host-alias>` must be a host alias already defined in the tailnet policy. After the sidecar appears as `codexify-test`, use the **Share** action for that machine in the Tailscale admin console and send the tester the invite. Sharing exposes only that machine to the recipient's existing Tailscale account; it does not make the tester a member of the personal tailnet and does not expose VaultNode's other machines, subnet routes, or host ports.

## Starting the Tester Stack

### Start dependencies first (db, redis, neo4j)

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  up -d db redis neo4j
```

Wait for all three to become healthy:

```bash
docker compose --env-file .env.tester -p codexify_tester ps
```

### Run graph-init

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  up graph-init
```

### Run migrations

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  run --rm migrator
```

### Prepare the embedding model

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  run --rm model-prep
```

### Start application services

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  up -d backend frontend worker-chat worker-chat-embed worker-document-embed worker-warmup
```

`frontend` starts its `tailscale-codexify-test` dependency automatically. The persistent `codexify_tailscale_test_state` named volume preserves the sidecar identity and Serve configuration across `down`/`up` and image rebuilds. Do not use `down -v` unless deliberately wiping the tester instance and its Tailscale node state.

## Verifying Health

### Backend health

```bash
curl -i http://localhost:8889/health
```

Expected: `200 OK`, `"status": "ok"`, `"supported_profile": {"name": "v1-friends-family-web"}`.

### Tailscale identity and Serve configuration

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  exec -T tailscale-codexify-test tailscale status --json

COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  exec -T tailscale-codexify-test tailscale serve status --json
```

Expected: the first output identifies `codexify-test`; the second configures only private HTTPS on TCP 443 and proxies to `127.0.0.1:5173`. The Tailscale admin console should show a distinct, tagged `codexify-test` machine.

### Tester access boundary

Ask the tester to open the FQDN from their Tailscale client:

```text
https://codexify-test.<your-tailnet>.ts.net
```

The browser should load Codexify and its same-origin `/api` requests should succeed. These must fail from the tester device: `https://vaultnode.<your-tailnet>.ts.net`, `ssh vaultnode.<your-tailnet>.ts.net`, and direct database/dashboard attempts. Confirm the policy editor's `tests` block passes before sending the share invite.

### Restart persistence

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  restart tailscale-codexify-test frontend

COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  exec -T tailscale-codexify-test tailscale status --json
```

Expected: the node retains the same `codexify-test` identity and the tester can reload the same FQDN.

### Chat health (queue + worker)

```bash
curl -i http://localhost:8889/health/chat
```

### LLM health (provider runtime)

```bash
curl -i http://localhost:8889/api/health/llm
```

### Auth route mount verification

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  exec -T backend python - <<'PY'
from guardian.guardian_api import app
for r in app.routes:
    path = getattr(r, "path", "")
    if "auth" in path:
        print(sorted(getattr(r, "methods", [])), path)
PY
```

Expected output should include `POST /auth/register` and `POST /auth/login`.

### Verify register/login work

```bash
# Register a test user
curl -i -X POST http://localhost:8889/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"tester1","password":"test-password-123"}'

# Login with the same credentials
curl -i -X POST http://localhost:8889/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tester1","password":"test-password-123"}'
```

Both should return `200 OK`. Register returns `{"ok":true,"user_id":"tester1","username":"tester1"}`. Login returns a `token`, `user_id`, and `expires_at`.

## Stopping Without Deleting Volumes

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  down
```

This stops containers but preserves volumes (`pg_data`, `neo4j_data`, `codexify_tailscale_test_state`, etc.). State and the dedicated Tailscale identity are retained for the next `up`.

## Intentionally Wiping Only Tester State

> **WARNING**: `docker compose down -v` wipes volumes for the selected Compose project. Make sure `COMPOSE_PROJECT_NAME=codexify_tester` is set correctly before running this.

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  down -v
```

This permanently deletes the tester Postgres, Redis, Neo4j, and Chroma volumes. The dev stack (`COMPOSE_PROJECT_NAME=codexify`) is not affected.

## Backing Up Tester Postgres

### Before risky migrations

```bash
COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  exec -T db pg_dump \
    -U "${POSTGRES_USER:-codexify}" \
    -d "${POSTGRES_DB:-Codexify}" \
    -F c -f /tmp/codexify_tester_pre_migration.dump

# Copy the dump to the host
docker compose --env-file .env.tester -p codexify_tester \
  cp db:/tmp/codexify_tester_pre_migration.dump ./codexify_tester_pre_migration.dump
```

### Restore from backup

```bash
docker compose --env-file .env.tester -p codexify_tester \
  cp ./codexify_tester_pre_migration.dump db:/tmp/codexify_tester_pre_migration.dump

COMPOSE_PROJECT_NAME=codexify_tester \
  docker compose --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  exec -T db pg_restore \
    -U "${POSTGRES_USER:-codexify}" \
    -d "${POSTGRES_DB:-Codexify}" \
    --clean --if-exists \
    /tmp/codexify_tester_pre_migration.dump
```

## Migration Safety Ritual Before Updating Tester

1. **Back up** Postgres (see above).
2. **Stop** the tester stack (`down`, not `down -v`).
3. **Pull or rebuild** the latest images.
4. **Run the migrator** in isolation:
   ```bash
   COMPOSE_PROJECT_NAME=codexify_tester \
     docker compose --env-file .env.tester \
     -f docker-compose.yml -f docker-compose.tester.yml \
     run --rm migrator
   ```
5. **Verify health** endpoints return `200`.
6. **Verify auth route mount** is still present.
7. **Verify register/login** still work.
8. If anything fails, **restore from backup** before debugging.

## Important Warnings

- **Tester validation is not a complete production security review.** Secrets are stored in a plain `.env.tester` file; protect that file with host permissions and rotate/revoke the auth key if it is exposed.
- **Do not expose tester ports to the public internet.** Tailscale Serve is tailnet-private and terminates HTTPS for the dedicated node; Tailscale Funnel must remain disabled.
- **Do not reuse secrets** between `.env.tester` and `.env`.
- **The dev stack and tester stack share Docker images but have fully isolated volumes** thanks to distinct `COMPOSE_PROJECT_NAME` values.
- **`docker compose down -v` is destructive** — it removes all volumes for the given project. Double-check `COMPOSE_PROJECT_NAME` before running it.
- **Tester host ports bind only to loopback.** Remote testers must use the shared `codexify-test` FQDN, never a VaultNode IP, hostname, or host port.

## Related Documents

- [00 Current State](../architecture/00-current-state.md) — canonical release truth
- [Config and Ops](../architecture/config-and-ops.md) — env vars, config resolution, health checks
- [System Overview](../architecture/system-overview.md) — runtime components and topology
- [Account Export + Restore Contract](../architecture/account-export-restore-contract.md) — export/restore guarantees (deferred for tester profile)
