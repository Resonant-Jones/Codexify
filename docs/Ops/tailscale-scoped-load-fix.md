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
