# Trusted Remote Auth Seam Audit

> Classification: architecture-impact audit artifact
> Status: normative read-only proof artifact
> Scope: docs/proof only

Last updated: 2026-06-22
Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/remote-account-access-and-user-profile-contract.md
- docs/architecture/config-and-ops.md
- docs/architecture/data-and-storage.md
- docs/architecture/modules-and-ownership.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/persona-studio.md
- docs/architecture/persona-studio-spec.md
- docs/architecture/adr/005-runtime-mode-and-account-boundary-invariants.md
- guardian/routes/auth.py
- guardian/core/auth.py
- guardian/core/session_store.py
- guardian/core/auth_dependencies.py
- guardian/core/dependencies.py
- guardian/routes/admin.py
- guardian/routes/ui_session.py
- guardian/db/models.py
- guardian/routes/persona_profiles.py
- frontend/src/lib/authState.ts
- frontend/src/lib/api.ts
- frontend/src/lib/runtimeAuth.ts
- frontend/src/pages/login/LoginPage.tsx
- frontend/src/App.tsx
- frontend/src/features/settings/api/persona.ts
- frontend/src/features/settings/components/PersonaSettingsPanel.tsx

## Purpose

This is a read-only seam audit for trusted remote account access and future User Profile work.

It documents what already exists, what is still only a seam, and what remains missing. It does not implement login, profile UI, auth changes, Tailnet configuration, schema changes, or runtime behavior.

## Current-Truth Boundary

- Local Docker Compose remains the supported path.
- Local-only provider posture remains unchanged.
- Tailnet/private-LAN access remains trusted remote access to a local runtime, not public SaaS exposure.
- Application-layer auth remains required.
- A frontend User Profile page now exists at `/profile` over the session-authenticated profile spine.
- This audit does not widen the supported release promise.

## Seam Status Legend

- `proven`: the repo contains a concrete code path or schema surface and it has been inspected.
- `partial`: the seam exists, but it does not yet satisfy the future trusted-remote contract on its own.
- `missing`: the repo search did not find a dedicated surface for the concept.

## Existing Backend Auth and Session Path

| Seam | Status | What exists now | Why it matters |
|---|---|---|---|
| `/auth/register` and `/api/auth/register` | proven | [`guardian/routes/auth.py`](../../guardian/routes/auth.py) creates `User` rows with username/password hashes. | Establishes the basic account bootstrap path. |
| `/auth/login` and `/api/auth/login` | proven | [`guardian/routes/auth.py`](../../guardian/routes/auth.py) verifies username/password and returns a session token, `user_id`, and expiry. | This is the current browser login entrypoint. |
| `/auth/logout` and `/api/auth/logout` | proven | [`guardian/routes/auth.py`](../../guardian/routes/auth.py) resolves a token from `Authorization` or `gc_session` and revokes it. | Logout is not just UI state; the token can be revoked server-side. |
| HMAC-signed session token behavior | proven | [`guardian/core/auth.py`](../../guardian/core/auth.py) issues and verifies opaque signed session tokens. | This is the trusted transport for session/JWT-style auth. |
| Redis-backed session storage | proven | [`guardian/core/session_store.py`](../../guardian/core/session_store.py) stores token -> `user_id` mappings with TTL. | Session revocation and lookup depend on Redis-backed token state. |
| Current subject resolution helpers | proven | [`guardian/core/auth_dependencies.py`](../../guardian/core/auth_dependencies.py) and [`guardian/core/dependencies.py`](../../guardian/core/dependencies.py) resolve request identity from session tokens, then fall back when appropriate. | This is the backend seam that turns credentials into request identity. |
| Session revocation behavior | proven | The logout route revokes tokens in Redis via `SessionStore.revoke()`. | Trusted remote access needs a real logout path, not just token expiration. |

Notes:

- The login path is username/password based today, not a dedicated trusted-remote session wizard.
- The token payload is opaque to the browser, which is good, but the browser still holds the token in client storage after login.

## Existing Identity Resolution Path

| Seam | Status | What exists now | Why it matters |
|---|---|---|---|
| Single-user fallback behavior | proven | [`guardian/core/dependencies.py`](../../guardian/core/dependencies.py) returns the configured single-user identity when no valid session is present and multi-user mode is not enabled. | This preserves current local behavior, but can also hide missing multi-user discipline if it stays too implicit. |
| Multi-user / authenticated-principal resolution | proven | [`guardian/core/dependencies.py`](../../guardian/core/dependencies.py) resolves a bearer/cookie session subject, then looks up a stable `account_id` from `authenticated_principals` when multi-user mode is enabled. | This is the durable account-binding seam for future multi-user behavior. |
| Canonical user boundary | proven | [`guardian/db/models.py`](../../guardian/db/models.py) contains the `User` table, and many domain tables carry `user_id`/`account_id` ownership columns. | This is the current ownership spine the rest of the system already leans on. |
| `authenticated_principals` table | proven | [`guardian/db/models.py`](../../guardian/db/models.py) defines a stable mapping from `subject_id` to `account_id`. | This is the durable subject-to-account bridge for multi-user resolution. |
| `users` table | proven | [`guardian/db/models.py`](../../guardian/db/models.py) defines the canonical account row with `id`, `username`, `password_hash`, and `created_at`. | This is the current single-user account boundary and auth credential store. |
| Dev identity ambiguity | proven | [`guardian/core/dependencies.py`](../../guardian/core/dependencies.py) still honors `X-User-Id` in `DEBUG` or `LOCAL_DEV`, and session tokens can preempt the fallback path. | Local dev identity and authenticated subject identity can diverge, so trusted remote work must not assume they are the same thing. |

Interpretation:

- A valid session token currently wins over single-user fallback.
- In multi-user mode, a stable `account_id` mapping becomes mandatory.
- Display labels are not identity; resolved request scope is.

## API-Key and Dev Fallback Path

| Seam | Status | What exists now | Why it matters |
|---|---|---|---|
| API keys accepted by auth helpers | proven | [`guardian/core/auth.py`](../../guardian/core/auth.py) accepts `X-API-Key` and bearer/session inputs as authentication identity sources. | API-key auth is still part of the trusted transport boundary. |
| API-key gating in dependency layer | proven | [`guardian/core/dependencies.py`](../../guardian/core/dependencies.py) rejects static API keys in remote mode and keeps them local-only by policy. | This is good, but it also means the API-key path remains a live compatibility seam. |
| API-key-to-session minting | proven | [`guardian/routes/admin.py`](../../guardian/routes/admin.py) exposes `/auth/session` and `/auth/session/cookie`, which exchange an API key for a short-lived session token or HttpOnly cookie. | This is the biggest bridge between operator auth and browser auth. |
| Frontend dev API-key fallback | proven | [`frontend/src/lib/authState.ts`](../../frontend/src/lib/authState.ts) and [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts) treat dev API keys as a valid auth source in dev/runtime transport. | A browser can look authenticated without ever performing a user session login. |
| In-memory runtime API key | proven | [`frontend/src/lib/runtimeAuth.ts`](../../frontend/src/lib/runtimeAuth.ts) holds a runtime API key in memory and marks auth state accordingly. | This is a direct transport-risk seam for trusted remote browser use. |

Why this is a risk seam:

- A remote browser can be authenticated by a browser-delivered API key rather than by a user-bound session.
- The admin session-minting route currently mints a token for subject `"web"`, which is useful as a bridge but not yet the same thing as a canonical trusted-remote account login.
- If API-key fallback remains visible in trusted remote mode, the browser trust boundary is too wide.

What must be proven or changed before a remote friend login is safe:

- trusted remote mode must use a session/JWT flow whose subject resolves to a canonical account/user ID
- API-key fallback must be absent, disabled, or explicitly bounded to operator-only bootstrap flows in trusted remote mode
- no raw API key should reach a remote browser in the production-style access path

## Frontend Auth State and Browser Storage

| Seam | Status | What exists now | Why it matters |
|---|---|---|---|
| Session token storage | proven | [`frontend/src/lib/authState.ts`](../../frontend/src/lib/authState.ts) and [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts) read and write `guardian.auth.token` in `sessionStorage`. | Session tokens already live in browser storage, so storage compromise is a real risk surface. |
| Runtime API key storage | proven | [`frontend/src/lib/runtimeAuth.ts`](../../frontend/src/lib/runtimeAuth.ts) keeps the runtime API key in memory. | This is not persistent storage, but it is still part of the browser trust boundary. |
| Dev API-key fallback | proven | [`frontend/src/lib/authState.ts`](../../frontend/src/lib/authState.ts) and [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts) fall back to `VITE_GUARDIAN_DEV_API_KEY` and legacy `VITE_GUARDIAN_API_KEY` in dev. | Browser-delivered dev keys can blur the line between local convenience and trusted remote auth. |
| In-memory auth state | proven | [`frontend/src/lib/authState.ts`](../../frontend/src/lib/authState.ts) tracks `unknown`, `authenticated`, and `unauthenticated` states. | The UI can reflect auth state without proving canonical account ownership. |
| Logout behavior | proven | [`frontend/src/components/auth/useAuth.ts`](../../frontend/src/components/auth/useAuth.ts) calls `/auth/logout` when it has a token, then clears the stored token. | This is the client-side half of revocation. |
| Additional browser storage surfaces | proven | [`frontend/src/lib/runtimeConfig.ts`](../../frontend/src/lib/runtimeConfig.ts) and shell code use `localStorage` for runtime/config preferences unrelated to auth. | Not auth itself, but still adjacent to transport posture and user-visible state. |

Current risk surfaces:

- session tokens are recoverable from browser storage on the client side
- runtime API keys can be injected into request headers
- auth state can resolve as authenticated without a session token if a runtime or dev key is present
- browser-local storage is doing more than just preference persistence, so it cannot be treated as a trust boundary

## Existing Login Surface

| Seam | Status | What exists now | Why it matters |
|---|---|---|---|
| Current frontend login page | proven | [`frontend/src/pages/login/LoginPage.tsx`](../../frontend/src/pages/login/LoginPage.tsx) renders a username/password form and submits to the auth hook. | The page already exists, but it is a generic login page, not yet a trusted-remote login surface. |
| App route wiring | proven | [`frontend/src/App.tsx`](../../frontend/src/App.tsx) routes `/login` to `LoginPage` and `/register` to `RegisterPage`. | The surface is wired into the app shell today. |
| Login assumptions | proven | The page assumes username/password auth and redirects to `/` after success. | It does not currently distinguish local password login from remote trusted-session login. |
| Missing posture disclosure | partial | The page does not currently explain local vs remote posture, browser trust, or API-key/session distinctions. | A future trusted-remote login surface needs to be explicit about posture. |

What must be refit before this becomes the trusted remote login surface:

- make the local/remote posture explicit
- ensure the page is driving a session/JWT flow, not a browser-shipped API-key flow
- avoid implying public SaaS or blanket remote support
- keep login separate from profile editing

## Current Profile, Persona, and Settings Surfaces

| Seam | Status | What exists now | Why it matters |
|---|---|---|---|
| Persona Studio | proven | [`docs/architecture/persona-studio.md`](./persona-studio.md) and the `frontend/src/features/personaStudio/` surface define persona/profile configuration as a non-conversational runtime preset surface. | This is profile-like behavior, but it is assistant behavior, not user ownership. |
| Backend persona profile CRUD | proven | [`guardian/routes/persona_profiles.py`](../../guardian/routes/persona_profiles.py) exposes API-key-protected CRUD for `persona_profiles`. | This is a runtime preset store, not a User Profile store. |
| Settings persona API | proven | [`frontend/src/features/settings/api/persona.ts`](../../frontend/src/features/settings/api/persona.ts) reads and writes active persona text via imprint endpoints. | This is still persona/mask state, not account metadata. |
| Persona settings UI | proven | [`frontend/src/features/settings/components/PersonaSettingsPanel.tsx`](../../frontend/src/features/settings/components/PersonaSettingsPanel.tsx) edits active persona text for project/thread context. | The UI is explicitly about persona voice/mask, not identity ownership. |
| Imprint / shell-local profile-like state | partial | Browser-local shell settings and imprint flows can hold names, notes, and prompt text, but they are not yet a canonical user profile surface. | These values can support later metadata display, but they are not durable account profile truth. |

Why these are not a canonical User Profile surface:

- they control assistant behavior or local shell presentation
- they do not define account ownership
- they do not provide a dedicated durable user-profile schema
- they do not yet expose a canonical display-name/avatar/contact-label contract for an account

## Missing User Profile Surface

| Item | Status | What the repo search found |
|---|---|---|
| Dedicated `UserProfile` model/table | proven | A dedicated `UserProfile` ORM model and `user_profiles` table now exist in [`guardian/db/models.py`](../../guardian/db/models.py), and the frontend User Profile page now exists at `/profile`. |
| Dedicated User Profile frontend page/route | proven | A dedicated User Profile page and route now exist in the frontend tree at `/profile`. |
| Canonical durable user-profile ownership contract | partial | The remote-access contract defines the semantics, the backend has a durable current-user User Profile spine, and the frontend metadata page now sits on top of it. |
| Existing fields that could support later metadata | partial | `users.username`, `authenticated_principals.account_id`, persona profile names, and shell-local names/notes/prompt values could support future display metadata, but they are not a profile schema. |

Read this as a gap, not a defect:

- the repo has account and persona primitives
- the repo now has both the backend user-profile primitive and the dedicated frontend page
- display metadata is now layered on the authenticated session path, but it is still not canonical durable account truth

## User Profile Backend Spine Proof Note

- The backend `user_profiles` table now exists and is owned by canonical `users.id`.
- The current-user profile route exists for session-scoped profile reads and writes.
- The profile payload is presentation metadata only and does not change Persona Profile state.
- The frontend User Profile page now exists at `/profile`, and Tailnet/live remote runbook proof remains deferred.

## Ephemeral UI Session Cache

| Seam | Status | What exists now | Why it matters |
|---|---|---|---|
| UI session cache route | proven | [`guardian/routes/ui_session.py`](../../guardian/routes/ui_session.py) exposes `/api/ui/session` GET/PUT/PATCH/DELETE. | This is a real browser state cache, not just a placeholder. |
| Keying | proven | The cache is keyed by `user_id` and `device_id`. | It is scoped, but only as a cache namespace, not as an auth identity proof. |
| Current auth protection mode | proven | The route is protected by `require_api_key`. | API-key gating is not equivalent to end-user session identity. |
| Why that matters | partial | A caller with API-key access can still read/write cache entries for arbitrary user/device values if the payload is accepted. | Trusted remote access needs subject-bound auth, not just endpoint access. |

Bottom line:

- this cache is useful for ephemeral UI state
- it is not a proof of authenticated account ownership
- it cannot be treated as the trusted remote login boundary

## Implementation Map

Future slices should be treated as separate work items:

Status note: the frontend User Profile page has now landed at `/profile`; the remaining slices stay future work.

1. Backend session proof
2. API-key fallback containment/refit
3. Authenticated subject proof
4. User Profile frontend surface
5. Login page refit
6. User Profile page
7. Tailnet/private-LAN operator runbook
8. End-to-end trusted remote access proof

This audit deliberately stops before any of those slices are implemented.

## Risk Register

- Raw API key exposure to a remote browser: the frontend still accepts API-key-based auth and the admin auth bridge can mint sessions from an API key.
- Browser storage token leakage: session tokens live in `sessionStorage`, and local/browser storage is broadly used across the shell.
- Display name mistaken for canonical user ID: local labels, usernames, and account names can be confused if the next implementation does not bind to canonical account identity.
- Persona Profile mistaken for User Profile: Persona Studio and persona settings are runtime-behavior surfaces, not account-profile surfaces.
- Single-user fallback accidentally masking multi-user defects: the backend still has explicit single-user fallback behavior when multi-user mode is not enabled.
- UI session cache protected by API key rather than end-user session identity: `/api/ui/session` is useful but not sufficient for trusted remote access.
- Release-claim widening through Tailnet language: private-LAN transport must not be phrased or surfaced as public internet support.

## ADR Impact

Classification: aligned with existing ADR(s), unless inspection proves otherwise.

Governing ADRs / contracts:

- [Remote Account Access and User Profile Contract](./remote-account-access-and-user-profile-contract.md)
- [`config-and-ops.md`](./config-and-ops.md)
- [`account-export-restore-contract.md`](./account-export-restore-contract.md)
- [ADR-005 Runtime Mode and Account Boundary Invariants](./adr/005-runtime-mode-and-account-boundary-invariants.md)
- [Persona Studio Architecture](./persona-studio.md)
- [Persona Studio Product Spec](./persona-studio-spec.md)

Brief reason:

This audit does not change runtime identity semantics. It labels the currently existing seams, confirms the gap between “there is a login/session path” and “there is a trusted remote access contract,” and preserves the account-boundary and persona-separation doctrine already established by the repo.

## Current-Truth Anchors

### What is true now

- Local Docker Compose is still the supported path.
- Local-only provider posture remains the active release truth.
- Session-based login exists.
- API-key fallback still exists in the transport layer.
- Stable account mapping exists through `users` and `authenticated_principals`.
- Persona Studio and imprint settings already exist as separate non-account surfaces.
- A backend User Profile spine now exists for session-scoped profile metadata.
- A frontend User Profile page now exists at `/profile` and uses the session-authenticated profile spine.

### What is not yet true

- No Tailnet/live remote runbook proof exists yet.
- No remote-friendly, session-only trusted login proof exists yet.
- No explicit containment of API-key fallback for trusted remote mode exists yet.

### What the next implementation task may assume

- the remote-account-access contract already names the future semantic boundary
- the repo already has session token issuance and revocation
- the repo already has canonical user/account and subject-to-account primitives
- the repo already has a durable current-user User Profile backend spine
- Persona Profile remains a distinct concept from User Profile

### What the next implementation task must not assume

- that the existing `/login` page is already the trusted remote login surface
- that API-key auth is safe to deliver to a remote browser by default
- that Persona Studio or imprint settings equal User Profile
- that display labels are canonical IDs
- that Tailnet/private-LAN access is public SaaS support

## Invariants

- no raw API key should be shipped to remote browsers in production-style access
- Tailnet/private-LAN does not replace app-layer auth
- canonical user identity must not be inferred from display labels
- User Profile must stay separate from Persona Profile
- browser storage is a risk surface, not a trust boundary
- account-scoped reads must remain account-bound once multi-user access exists
- local-only provider posture remains unchanged
- this audit does not widen the supported release promise

## Proof Surface for Next Implementation

Before the next implementation can claim trusted remote access is working, it must prove:

- an authenticated remote browser can log in without receiving raw API key material
- logout revokes or clears the session as designed
- the authenticated subject resolves to a canonical account or user ID
- API-key fallback is absent, disabled, or explicitly bounded in trusted remote mode
- the user-profile surface does not mutate persona identity
- thread, document, and retrieval reads are account-scoped
- health surfaces remain green
- local-only provider posture remains unchanged
- no public internet exposure is implied

Concrete proof should include the active health surfaces used by the repo today, not just a happy-path UI screenshot.

## Notes

This audit is a label-maker, not a builder.

It exists so the next implementation can be small, testable, and correctly scoped:

- recognize the session/login seam that already exists
- contain the API-key seam instead of pretending it does not matter
- keep User Profile separate from Persona Profile
- keep trusted remote access separate from public SaaS language
