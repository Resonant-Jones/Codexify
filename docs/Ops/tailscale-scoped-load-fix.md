# Codexify Scoped Tailscale Load Fix

## Root Cause

The scoped Tailscale frontend was healthy, but the browser shell used
`/api/health/llm` as its startup gate. That endpoint performs provider and model
inventory work and was observed exceeding the browser's 4-second gate timeout.
The resulting full-screen gate prevented use of an otherwise rendered shell.

Two independent WebSocket defects were also present:

- Vite rewrote `/api/ws/*` to `/ws/*`, although the backend's canonical RPC
  route is `/api/ws/rpc`.
- The collaboration client constructed its URL from an intentionally blank
  `VITE_GUARDIAN_API_BASE`, which could produce an invalid `ws:///...` URL
  instead of the same-origin `/api/collab/ws/{documentId}` path.

## Changes Made

- Proxy `/health`, `/api/ws/*`, and `/api/collab/ws/*` from the existing Vite
  frontend to the backend without browser-visible backend hostnames.
- Keep WebSocket proxy entries before the general `/api` proxy so Vite upgrades
  them correctly.
- Use `/health` with a bounded abort timeout for browser readiness. The shell
  remains usable while the probe retries.
- Keep the degraded-state notice small and non-blocking rather than covering the
  application.
- Derive collaboration WebSocket URLs through the runtime same-origin resolver.
- Enable sanitized request timing for the tester backend. It logs only method,
  path, status, duration, request ID, and `local` or `tailscale` class.

## Security Impact

The external browser still sees one origin:

`https://codexify-test.tail6b75da.ts.net`

The backend remains reachable only through the existing frontend proxy. No
backend, Ollama, database, subnet, exit-node, or Funnel exposure was added.

## Before

| Probe | Result |
| --- | --- |
| `/register` | HTML in about 10 ms TTFB |
| `/api/health/llm` | backend JSON in about 0.5 s when warm; may perform slower provider discovery |
| Root shell | rendered but covered by the full-screen startup gate after the LLM probe timed out |
| `/api/ws/rpc` | proxy configuration rewrote the canonical path and returned `404` on a normal HTTP probe |

## After

| Probe | Result |
| --- | --- |
| `/register` | HTML from the scoped origin |
| `/health` | same-origin backend JSON, about 11 ms TTFB in the verification run |
| `/api/health/llm` | backend JSON, about 0.55 s TTFB in the verification run |
| Root shell | visible and interactive without a startup overlay after reload |
| WebSocket routes | canonical `/api/ws/*` and `/api/collab/ws/*` are explicit Vite WebSocket proxies. The current `v1-friends-family-web` profile intentionally quarantines the optional WebSocket control-plane route, so an upgrade probe returns `403`; enabling it would be a profile change, not a scoped-load repair. |

## External Test Results

Validated from the scoped service:

```bash
curl -k https://codexify-test.tail6b75da.ts.net/register
curl -k https://codexify-test.tail6b75da.ts.net/health
curl -k https://codexify-test.tail6b75da.ts.net/api/health/llm
```

The Tailscale sidecar still serves only private HTTPS on TCP 443 to the Vite
frontend, with Funnel disabled. Browser inspection confirmed the registration
shell and, after the fix, the root chat shell render without a blocking startup
gate.

## Registration Schema Recovery (2026-07-25)

The scoped registration `500` was not a Tailscale, proxy, or password-policy
failure. The live Guardian source included the account-observability ORM models,
but the database remained at Alembic revision `a1c2d3e4f5b6`. Guardian verifies
that its model tables exist while initializing the authentication database, so
every registration attempt failed before it could query or write a user.

The expected repair is to build the `codexify-backend-runtime` image from the
deployment checkout, run the existing `migrator` service through
`alembic upgrade heads`, and then restart only the backend. The target revision
is `b2c3d4e5f6a7`, which creates these four tables:

- `account_observability_account_metadata`
- `account_observability_guest_identities`
- `account_observability_invite_links`
- `account_observability_presence_sessions`

Do not repair this condition with manual DDL, `alembic stamp`, a downgrade, or
a database reset. Those can make the revision marker disagree with the schema
or destroy tester state.

During the 2026-07-25 recovery, Docker Desktop could not resolve the BuildKit
frontend, so rebuilding the image was unavailable. The tracked `b2c3d4e5f6a7`
migration was placed in the stopped migrator container and the normal
`upgrade heads` command was run; this advanced the existing tester database
without changing source files or resetting data. That is an incident recovery
step, not a durable image build. A fresh environment will still need an image
rebuilt from the checkout after Docker image-resolution is restored.

## Recovery Validation

After the migration and backend restart, a new scoped account registered with
HTTP `200`, a duplicate request returned the intentional HTTP `409`, and login
returned a session token with HTTP `200`. A browser created a separate scoped
account, entered the authenticated shell, submitted a chat message, and saw the
assistant response complete. Reloading retained both the session and the chat
thread; the browser console had no error entries.

The authenticated continuation uses the same-origin `/api/events` SSE path for
task events. The optional WebSocket control-plane router remains quarantined by
the supported tester profile, so it must not be enabled merely to validate the
chat stream.

## Remaining Risks

- The browser still reports expected unauthenticated `401` responses before
  login and optional voice-capability `404` responses. Neither blocks shell
  rendering.
- Provider discovery can still delay LLM status and chat readiness; it no
  longer controls initial UI availability.
- The account-observability migration is now present in the running tester
  database, but the current runtime image predates it. Rebuild the image before
  provisioning a fresh scoped database.
- The optional WebSocket control-plane route is intentionally unavailable under
  `v1-friends-family-web`; this does not block the authenticated `/api/events`
  chat stream.

## Rollback

Revert the scoped change set, then restart only the frontend for proxy/UI
changes and the backend for timing-log configuration:

```bash
docker restart codexify_tester-frontend-1
docker restart codexify_tester-backend-1
```

Use the task commit when available for a precise rollback; do not remove the
Tailscale sidecar volume or change the Serve/Funnel policy as part of rollback.

For an account-observability rollout failure, restore a backend source/image
that is compatible with the current database and investigate the migration
chain. Do not downgrade the live tester database without explicit recovery
approval.

## Fresh-Instance Migration Readiness Proof (2026-07-25)

### BuildKit DNS Root Cause

Docker Desktop on macOS (`v29.6.2`) runs BuildKit inside a Linux VM.
BuildKit's internal DNS resolver (`192.168.65.7:53`) intermittently fails to
resolve external registries (`registry-1.docker.io`, `pypi.org`, Debian
repos) during `docker build`. This manifests as:

- `dial tcp: lookup … on 192.168.65.7:53: i/o timeout`
- `failed to resolve source metadata for docker.io/docker/dockerfile:1`
- Hangs during `apt-get update` or `pip install` stages

### Repair Applied

- **Removed `#syntax=docker/dockerfile:1`** from `backend/Dockerfile`.
  The built-in Dockerfile syntax is sufficient; removing the directive
  eliminates a remote fetch that was the first failure point.
- **Added `network: host` to the backend build anchor** in
  `docker-compose.yml` (`x-backend-runtime-build`). This routes BuildKit
  through the host network stack during image builds, using the host's DNS
  resolver instead of BuildKit's internal resolver.

Exact rebuild command:

```bash
DOCKER_BUILDKIT=1 docker build --network=host \
  --target runtime -f backend/Dockerfile \
  -t codexify-backend-runtime:latest .
```

Or via Compose (after the `network: host` addition):

```bash
docker compose build backend
```

### Constraint Name Length Fix

PostgreSQL limits identifiers to 63 characters. Three `CheckConstraint` names
in revision `b2c3d4e5f6a7` exceeded this limit and were shortened using the
`ao_` prefix pattern. The affected names in `guardian/db/models.py` and the
migration file were updated to match. These fixes must be in both the ORM
models and the migration for `verify_schema_consistency()` to pass.

### Fresh-Database Isolation Method

A dedicated Compose project (`codexify_fresh_proof`) with its own named
volume (`pg_data_fresh_proof`) and distinct host ports (`5435`, `8890`, `6380`)
was used. The `.env.proof` file (deleted after proof) matched the
`v1-friends-family-web` profile contract (`LLM_PROVIDER=deepseek`,
`ALLOW_CLOUD_PROVIDERS=true`).

### Migration Proof

- Empty database confirmed: `0` user tables before migration.
- `alembic upgrade heads` completed successfully, reaching `b2c3d4e5f6a7`.
- All four account-observability tables created:
  `account_observability_account_metadata`,
  `account_observability_guest_identities`,
  `account_observability_invite_links`,
  `account_observability_presence_sessions`.
- `verify_schema_consistency()` passed (backend reached healthy state).

### Scoped Registration Proof

All tested from `localhost:8890` against the fresh backend:

| Test | Result |
| --- | --- |
| Fresh registration | HTTP `200` |
| Duplicate registration | HTTP `409` |
| Login | HTTP `200` with JWT |
| Authenticated GET `/api/chat/threads` | HTTP `200` |
| `/health` | HTTP `200`, `v1-friends-family-web` active |
| `/ping` | HTTP `200` |
| `/api/health/llm` | `down` (expected: proof key cannot reach DeepSeek) |
| `/api/events` SSE | Endpoint present (canonical same-origin path) |
| `/api/ws/rpc` | HTTP `404` (route not mounted under `v1-friends-family-web`; expected profile policy) |
| Funnel | Not enabled (proof environment is loopback-only, no Tailscale) |

### Cleanup

```bash
COMPOSE_PROJECT_NAME=codexify_fresh_proof \
  docker compose --env-file .env.proof \
  -f docker-compose.yml -f docker-compose.fresh-proof.yml down -v
rm -f .env.proof docker-compose.fresh-proof.yml
```

The original `codexify_tester` deployment was verified healthy after cleanup.
No tester data was modified or removed.

### Verdict

**GREEN — fresh-instance readiness proven.** A newly built backend image
from the current repository state can initialize a completely fresh database
through Alembic revision `b2c3d4e5f6a7` and serve scoped registration.
