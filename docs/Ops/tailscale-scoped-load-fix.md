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
| WebSocket routes | canonical `/api/ws/*` and `/api/collab/ws/*` are explicit Vite WebSocket proxies; unauthenticated upgrade probes are correctly rejected by backend auth (`403`) rather than rewritten to a nonexistent route |

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

## Remaining Risks

- The browser still reports expected unauthenticated `401` responses before
  login and optional voice-capability `404` responses. Neither blocks shell
  rendering.
- A real scoped-user register, login, chat submission, and authenticated
  WebSocket exchange were not performed by this diagnostic run.
- Provider discovery can still delay LLM status and chat readiness; it no
  longer controls initial UI availability.

## Rollback

Revert the scoped change set, then restart only the frontend for proxy/UI
changes and the backend for timing-log configuration:

```bash
docker restart codexify_tester-frontend-1
docker restart codexify_tester-backend-1
```

Use the task commit when available for a precise rollback; do not remove the
Tailscale sidecar volume or change the Serve/Funnel policy as part of rollback.
