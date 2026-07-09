# Friends & Family Tester Runtime

> **Classification:** operator runbook
> **Profile:** `v1-friends-family-web`
> **ADR alignment:** ADR-005 (Runtime Mode and Account Boundary Invariants)
> **Last updated:** 2026-07-09

## Purpose

This runbook documents how to run a stable, isolated Codexify instance for invited friends/family testers. The tester instance enables the auth router (register, login, logout) so testers can create real accounts, while keeping the default dev profile (`v1-local-core-web-mcp`) unchanged.

## Non-Goals

- This is **not** a production deployment guide.
- This is **not** a public/hosted internet release.
- This is **not** a security hardening guide.
- This is **not** a TLS/reverse proxy setup guide.
- This is **not** a user invitation UX specification.

## How This Differs from Dev

| Aspect | Dev (`v1-local-core-web-mcp`) | Tester (`v1-friends-family-web`) |
|---|---|---|
| Compose project name | `codexify` (default) | `codexify_tester` |
| Env file | `.env` | `.env.tester` |
| Backend host port | `8888` | `8889` |
| Frontend host port | `5173` | `5174` |
| Auth routes enabled | No (quarantined) | Yes |
| User accounts | N/A (single-user dev) | Register/login/logout |
| State isolation | Dev Postgres/Redis/Neo4j volumes | Separate volumes via project name |
| Supported profile | `v1-local-core-web-mcp` | `v1-friends-family-web` |

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

## Verifying Health

### Backend health

```bash
curl -i http://localhost:8889/health
```

Expected: `200 OK`, `"status": "ok"`, `"supported_profile": {"name": "v1-friends-family-web"}`.

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

This stops containers but preserves volumes (`pg_data`, `neo4j_data`, etc.). State is retained for the next `up`.

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

- **Tester validation is not production security review.** Secrets are stored in a plain `.env.tester` file. Session tokens are not TLS-protected over localhost.
- **Do not expose tester ports to the public internet** without a reverse proxy, TLS, and proper security hardening (out of scope for this runbook).
- **Do not reuse secrets** between `.env.tester` and `.env`.
- **The dev stack and tester stack share Docker images but have fully isolated volumes** thanks to distinct `COMPOSE_PROJECT_NAME` values.
- **`docker compose down -v` is destructive** — it removes all volumes for the given project. Double-check `COMPOSE_PROJECT_NAME` before running it.
- **The tester and dev stacks cannot run simultaneously** because Docker Compose appends host port mappings (they are not replaced by overrides). The backend, frontend, db, and neo4j host ports will conflict. Stop the dev stack before starting the tester, and vice versa.

## Related Documents

- [00 Current State](../architecture/00-current-state.md) — canonical release truth
- [Config and Ops](../architecture/config-and-ops.md) — env vars, config resolution, health checks
- [System Overview](../architecture/system-overview.md) — runtime components and topology
- [Account Export + Restore Contract](../architecture/account-export-restore-contract.md) — export/restore guarantees (deferred for tester profile)
