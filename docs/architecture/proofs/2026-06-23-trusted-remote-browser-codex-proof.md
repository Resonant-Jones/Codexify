# Trusted Remote Browser Codex Proof - 2026-06-23

> Classification: next-proof-needed
> Status: Codex in-app browser reached the Tailnet frontend and exercised register/login/profile metadata, but required browser network logs, browser storage inspection, CORS header capture, and logout/session-rejection capture are incomplete
> Scope: browser-operation proof packet only; no code, config, runtime, schema, migration, provider, queue, worker, routing, retrieval, or test behavior changed

## 1. Title and Scope

- Title: `Trusted Remote Browser Codex Proof - 2026-06-23`
- Codex's in-app browser was used.
- Browser context classification: browser running inside the Codex desktop/app environment on the operator host context. It is not independently proven to be a separate Tailnet/private-LAN client from the host machine.
- Evidence is classified according to what was actually captured.
- No runtime code/config behavior was changed.
- No raw password, token, cookie, API key, or HAR file is committed.

## 2. Classification

- `next-proof-needed`
- Reason:
  - Codex's browser reached `http://100.109.4.57:5173/register`, `/login`, `/profile`, and backend health endpoints.
  - Browser registration/login and metadata-only User Profile update were observed.
  - The browser tooling available in this session did not expose HAR export, DevTools Network request logs, CORS response headers for app requests, or normal browser storage inspection.
  - Logout/session-rejection proof was not fully captured from the browser session.
  - The Codex browser network path is not independently separable from the host.
- This is not `hold` because the captured browser UI flow did not show API-key exposure, profile fallback, unsafe CORS behavior, or local-provider drift.
- This is not `go` because the required browser network/storage/logout/CORS evidence is incomplete.

## 3. Environment

| Field | Value |
|---|---|
| Date/time | `2026-06-23T22:50:05Z` |
| Branch | `main` |
| HEAD commit | `6a6e6c1e802abc9b5fa15baceee7b71421d7b42c` |
| Operator | Codex session |
| Host machine | not independently identified in this session; historical proof chain identifies `VaultNode.local` for `100.109.4.57` |
| Codex browser/client | Codex in-app browser (`iab`) |
| Network path | Browser to Tailnet/private-LAN frontend at `http://100.109.4.57:5173`; browser to backend at `http://100.109.4.57:8888` |
| Frontend origin | `http://100.109.4.57:5173` |
| Backend origin | `http://100.109.4.57:8888` |
| Browser name/version | Not exposed by the browser-control surface |
| Screenshots captured | Yes, sanitized PNG artifacts |
| Browser network logs/HAR/protocol traces | No HAR or DevTools Network export available |
| Browser storage evidence | Attempted; storage APIs were unavailable in the inspection sandbox |
| Server logs | Not captured |

Artifacts:

- `docs/architecture/proofs/artifacts/2026-06-23-trusted-remote-browser-codex-proof/register-page-no-api-key-input.jpg`
- `docs/architecture/proofs/artifacts/2026-06-23-trusted-remote-browser-codex-proof/login-page-no-api-key-input.jpg`
- `docs/architecture/proofs/artifacts/2026-06-23-trusted-remote-browser-codex-proof/profile-metadata-redacted.jpg`

## 4. Overlay Config Evidence

Current tree note:

- `docker-compose.trusted-remote.example.yml`, `config/trusted-remote.env.example`, `docs/architecture/trusted-remote-access-runbook.md`, and prior `docs/architecture/proofs/2026-06-23-*trusted-remote*.md` packets were absent from the current `main` worktree before this task.
- Those files are present in Git history on the `personal-facts-guardrails` branch; the historical trusted-remote overlay expected:
  - `CODEXIFY_ENABLE_TRUSTED_REMOTE_ROUTE_SURFACE=true`
  - `GUARDIAN_AUTH_MODE=remote`
  - `GUARDIAN_EXPOSURE_MODE=local_safe`
  - `GUARDIAN_SESSION_SECRET=<present>`
  - `GUARDIAN_JWT_SECRET=<present>`
  - `GUARDIAN_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://100.109.4.57:5173`
  - `CODEXIFY_LOCAL_ONLY_MODE=true`
  - `ALLOW_CLOUD_PROVIDERS=false`
  - `LLM_PROVIDER=local`
  - `VITE_GUARDIAN_API_KEY=`
  - `VITE_GUARDIAN_DEV_API_KEY=`

Current command result:

```text
$ docker compose config
error while interpolating services.migrator.environment.GUARDIAN_API_KEY: required variable GUARDIAN_API_KEY is missing a value: GUARDIAN_API_KEY must be set in .env
```

Interpretation:

- Effective local Compose config could not be rendered from this checkout because `.env` is absent and `GUARDIAN_API_KEY` is required.
- The browser proof therefore cannot independently prove effective Compose overlay config from the current worktree.
- Browser console output did include: `Dev API key override disabled. Provide VITE_GUARDIAN_DEV_API_KEY only when needed for local-safe auth.`

## 5. Live Runtime Evidence

Shell-side probes:

```text
$ curl -sS -i http://100.109.4.57:8888/health
curl: (7) Failed to connect to 100.109.4.57 port 8888 after 1 ms: Couldn't connect to server
```

Browser-side backend probes succeeded:

| Endpoint | Browser result |
|---|---|
| `GET /health` | `status=ok`, supported profile `v1-local-core-web-mcp`, selected provider `local`, `cloud_capable_configuration_present=false`, `release_hold=false` |
| `GET /health/chat` | `ok=true`, `status=healthy`, Redis `ok`, worker heartbeat `fresh`, provider `local`, model `gemma-4-e4b-it-4bit` |
| `GET /api/health/llm` | `status=ok`, provider `local`, local base URL `http://host.docker.internal:8000/v1`, supported profile valid |
| `GET /api/llm/catalog` | Provider `local` displayed as `Whoosh'd`; browser snapshot showed local model inventory |
| `GET /openapi.json` | Route strings for `/auth/register`, `/auth/login`, `/auth/logout`, and `/api/user/profile` were present |

Interpretation:

- The Codex browser could reach the backend even though the shell network namespace could not.
- Local-only provider posture remained intact in browser-observed health/catalog evidence.

## 6. Browser Reachability Evidence

Captured with Codex's browser:

| Page | Result |
|---|---|
| `http://100.109.4.57:5173/register` | Loaded successfully; rendered username/password account creation fields |
| `http://100.109.4.57:5173/login` | Loaded successfully; rendered username/password sign-in fields |
| `http://100.109.4.57:5173/profile` | Loaded after login; rendered User Profile metadata page |

The `/register` and `/login` browser screenshots show no API-key input field.

## 7. Browser Registration and Login Evidence

- Throwaway username: `trusted-remote-codex-proof-2026-06-23-1782253942139`
- Password: `redacted`
- Registration through `/register` routed the browser to `/login`.
- Login through `/login` succeeded and routed the browser to `/`.
- The root app shell loaded after login.
- Browser console showed Vite/React dev logs and `Dev API key override disabled`.

Network limitation:

- No HAR export or DevTools Network request log was available from the Codex browser API.
- Therefore the proof cannot directly show the `/auth/register` or `/auth/login` request headers from the browser.
- Based on visible UI and console evidence, no browser API-key input or dev-key override was observed, but this is not enough for `go`.

## 8. Browser User Profile Evidence

Authenticated profile evidence:

- `/profile` loaded after login.
- The page text states: editable presentation metadata only, no canonical ownership fields or persona settings.
- Updated metadata-only fields:
  - `display_name`: `Codex Browser Proof User`
  - `avatar_url`: `https://example.invalid/codex-proof-avatar.png`
  - `timezone`: `America/New_York`
- The page showed `Profile saved.`
- The fields remained populated after save.

Boundary evidence:

- The page did not render editable canonical ownership fields.
- The page explicitly separated User Profile metadata from persona behavior.
- No Persona Profile UI was involved in the proof flow.
- No browser network logs were available to prove absence of Persona Profile API calls.

## 9. Logout and Session Rejection Evidence

- A logout control was not visible in the captured app shell or profile page.
- The Codex browser inspection sandbox did not expose the active session token, `fetch`, `localStorage`, or `sessionStorage` in a way that allowed a safe browser-session `/auth/logout` call and post-logout `/api/user/profile` capture.
- Post-logout `GET /api/user/profile` returning `401 Authentication required` was not captured in this Codex browser run.

Classification impact:

- This missing evidence requires `next-proof-needed`.

## 10. Browser Network Evidence

Available:

- Browser navigation and page DOM evidence for `/register`, `/login`, `/profile`, `/health`, `/health/chat`, `/api/health/llm`, `/api/llm/catalog`, and `/openapi.json`.
- Browser console logs:
  - Vite connected.
  - React DevTools informational message.
  - `[gc] env snapshot Object`.
  - `[gc] Dev API key override disabled. Provide VITE_GUARDIAN_DEV_API_KEY only when needed for local-safe auth.`

Missing:

- HAR export.
- DevTools Network screenshots.
- Protocol-level request/response table for `/auth/register`, `/auth/login`, authenticated `GET /api/user/profile`, authenticated `PATCH /api/user/profile`, `/auth/logout`, post-logout `GET /api/user/profile`, and CORS preflights.
- Header-level proof that browser requests lacked `X-API-Key`.
- Header-level proof that Authorization/session values were present and redacted.

Classification impact:

- Browser network evidence is incomplete, so this packet cannot classify `go`.

## 11. Browser Storage Evidence

Attempted from the Codex browser page inspection surface:

```text
localStorage: unavailable in inspection sandbox
sessionStorage: unavailable in inspection sandbox
cookieNames: []
containsGuardianApiKeyName: false
containsXApiKeyName: false
```

Interpretation:

- The inspection sandbox did not expose normal storage APIs, so this is not a complete browser storage inspection.
- No API-key strings were observed in the limited inspection bundle.
- The frontend source seam uses `guardian.auth.token` in `sessionStorage`, but source inspection is not browser storage proof.

Classification impact:

- Browser storage evidence is missing/incomplete, so this packet cannot classify `go`.

## 12. CORS and Origin Evidence

- Exact browser origin observed: `http://100.109.4.57:5173`.
- Browser-side session/profile flow worked from that origin.
- Historical origin reproof in Git history recorded the exact origin in `GUARDIAN_ALLOWED_ORIGINS`.

Missing:

- DevTools Network evidence for preflight requests.
- Response-header proof for `Access-Control-Allow-Origin`.
- Evidence of any rejected origin.

Classification impact:

- CORS/origin proof is incomplete in this Codex browser run.

## 13. Console Evidence and Known Console Noise

Captured console output was limited to:

- Vite connecting/connected.
- React DevTools recommendation.
- `[gc] env snapshot Object`.
- `[gc] Dev API key override disabled. Provide VITE_GUARDIAN_DEV_API_KEY only when needed for local-safe auth.`

Known optional-surface 404 noise listed in the task was not captured in this run.

No console error was observed that blocked register/login/profile metadata save.

## 14. Account-Scoped Data Evidence

Deferred.

- No thread/document/retrieval proof was attempted because this task is scoped to browser-side trusted remote login/profile evidence.
- No unauthenticated account-scoped thread/document/retrieval rejection was captured.

## 15. Comparison Against Prior Proof Chain

| Prior proof item | Prior state | Current result |
|---|---|---|
| First live proof | Local auth mode and browser API-key env present | Current browser console reports dev API-key override disabled; effective config not independently rendered in current checkout |
| Overlay smoke | Route surface absent | Browser-observed OpenAPI text includes auth/profile routes |
| Session/profile smoke | Unauthenticated profile fallback | Not retested in this browser run |
| Session-gate reproof | Local-only, no remote browser | Codex browser now reached Tailnet frontend/backend, but it is not a separately proven remote client |
| Remote-client proof | Curl over Tailnet only, no browser | Browser UI proof captured for register/login/profile |
| Browser proof | Origin allowlist gap and no real browser | Browser reached exact Tailnet frontend origin |
| Browser origin reproof | Origin gap closed, still no real browser | CORS headers not recaptured in browser tooling |
| Browser final proof | Checklist existed, still no browser capture | Browser capture partially completed |
| Browser network logs previously missing | Missing | Still missing |
| Browser storage inspection previously missing | Missing | Still missing/incomplete |
| Remote frontend screenshots previously missing | Missing | Captured sanitized register/login/profile screenshots |

## 16. Known Limitations

- Codex's browser does not prove the intended separate remote-browser context.
- Browser network logs/HAR are missing.
- Browser storage inspection is incomplete.
- CORS header evidence is missing.
- Logout/session-rejection evidence is incomplete.
- Account-scoped thread/document/retrieval proof remains deferred.
- Shell-side `curl` could not reach the backend IP, although browser-side backend navigation worked.
- Current `main` lacked the trusted-remote overlay/runbook/proof files before this task; prior packets were read from Git history.
- This proof does not claim public internet support, SaaS support, true multi-user release support, Tailnet automation, or packaged desktop replacement of local Compose.

## 17. Final Decision

- Final classification: `next-proof-needed`
- Reason: Codex's browser captured real frontend reachability plus register/login/profile metadata evidence, but the required browser network, browser storage, CORS header, logout/session-rejection, and separable remote-client evidence are incomplete.
- Exact next step: capture the same flow from a browser context that can provide DevTools Network/HAR evidence, Application/Storage evidence, CORS response headers, and logout/post-logout `401` evidence. Redact all session credentials before committing artifacts.

If the missing evidence is captured successfully, the narrow claim allowed would be:

- trusted remote browser access over private Tailnet/private-LAN path is proven for session login and metadata-only User Profile read/write under the opt-in overlay.

Still outside that claim:

- public internet support
- SaaS support
- general multi-user release support
- account-scoped thread/document/retrieval proof
- packaged desktop replacement of local Compose
