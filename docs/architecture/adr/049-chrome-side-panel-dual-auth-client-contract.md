---
tags:
* architecture
* adr
* chrome-extension
* trusted-remote-access
* authentication
  aliases:
* ADR-049
* Chrome Side Panel Dual Auth Client Contract
---

# ADR-049: Chrome Side-Panel Dual-Auth Client Contract

## Status

Accepted for this bounded private-client implementation. Resonant Jones explicitly
authorized local API-key and Tailscale remote-session support on 2026-07-21.

## Date

2026-07-21

## Context

The private Chrome side-panel MVP originally implemented only the local Guardian
`X-API-Key` contract. Live unpacked-Chrome proof then established two separate
facts:

- the extension, action, side panel, exact-origin permission, and Tailscale HTTPS
  path were reachable; and
- the friends/family tester runtime correctly rejected the static API key because
  `GUARDIAN_AUTH_MODE=remote` permits only session/JWT authentication.

The backend already has the required remote identity path. `POST /api/auth/login`
exchanges a username and password for an opaque, expiring session token;
protected chat and task-event routes accept that token through
`Authorization: Bearer`; and `POST /api/auth/logout` revokes the server-side
session. Remote mode deliberately rejects `X-API-Key`.

Making the extension send both credentials on every request would weaken the
existing boundary. It would also make an authentication failure ambiguous: the
backend could not cleanly distinguish an operator-only local credential from an
end-user remote session.

## Decision

The private Chrome side-panel client supports two explicit, mutually exclusive
authentication modes per connection profile:

| Client mode | Intended topology | Credential acquisition | Request header |
|---|---|---|---|
| `local` | Same-device or otherwise explicitly local API-key runtime | Operator enters the matching Guardian API key | `X-API-Key` |
| `remote` | Tailscale/private-LAN runtime using Codexify remote auth | User enters Codexify username/password once; `/api/auth/login` returns a session | `Authorization: Bearer <session>` |

The extension must never attach `X-API-Key` and `Authorization` together. The
selected profile mode determines the only credential header used for thread,
message, completion, and task-event requests.

This decision reuses backend routes and identity behavior as-is. It adds no auth
route, token format, cookie contract, database schema, exposure mode, or account
mapping.

## State and credential ownership

The backend remains authoritative for user identity, session validity,
revocation, account scope, threads, messages, completion attempts, and task
events.

The extension owns only derived client state:

- `chrome.storage.local` holds the connection URL, explicit auth mode, selected
  thread, timestamps, and the local API key only when `authMode=local`.
- `chrome.storage.session` holds the remote session token, resolved user ID, and
  expiry only when `authMode=remote`.
- The remote username is used to establish the session and may be represented by
  the returned user ID in non-secret profile metadata.
- The remote password is request-local form state. It is never written to Chrome
  storage, logs, error messages, tests, analytics, source, or build output.
- `chrome.storage.sync` remains prohibited for all authentication material.

Chrome session storage is deliberately chosen because it is extension-scoped,
in-memory, not exposed to content scripts by default, and cleared when Chrome
restarts or the extension is disabled, reloaded, or updated. The user signs in
again after that boundary. Side-panel close/reopen and ordinary side-panel page
reload within the same extension session retain the remote session.

The version-1 API-key profile migrates to the version-2 `local` profile. No
stored API key is reclassified as a remote session token.

## Network and permission boundary

Tailscale supplies private transport reachability; it does not authenticate the
Codexify user. The extension still requests optional host access for exactly the
configured HTTP(S) origin and sends application credentials directly from the
side-panel page.

No new Chrome permission is required. The manifest remains limited to:

- required `sidePanel` and `storage`;
- optional `http://*/*` and `https://*/*` declarations used only for an
  exact-origin runtime request;
- no required host permissions, content scripts, page access, tab control, or
  browser automation.

The MV3 service worker remains stateless and does not receive, store, refresh,
or proxy either credential class.

## Session lifecycle and failure behavior

- Remote login stores the session only after exact-origin permission, successful
  login, and authenticated chat verification.
- A missing or expired remote session returns the side panel to the remote login
  form while retaining non-secret connection metadata.
- A protected-route `401` is authentication loss, not runtime unreachability and
  not authority to fall back to an API key.
- Remote disconnect attempts `/api/auth/logout` before clearing client state.
- Local clearing and origin-permission removal still proceed when the remote node
  is unreachable, so a failed revocation request cannot trap credentials in the
  browser.
- Server-side session expiry remains authoritative when logout cannot be
  delivered.
- No automatic credential-mode switching, replay, password retention, token
  refresh, or API-key fallback occurs.

## Identity and account invariants

- The authenticated session subject remains the backend-resolved user/account
  identity.
- The extension does not derive ownership from a username, display label,
  selected thread, Chrome profile, Tailscale identity, or API-key label.
- Remote mode never sends a raw Guardian API key to the remote browser path.
- Local mode does not claim a multi-user session identity.
- Runtime mode and account-boundary semantics remain governed by ADR-005 and are
  not changed by this client.

## Consequences

### Positive

- The private extension can use the existing Tailscale tester origin without
  weakening remote auth.
- Local API-key compatibility remains available for same-device operator use.
- Header behavior is deterministic and testable.
- Remote passwords are not retained, and session tokens naturally leave storage
  at the browser/extension lifecycle boundary.
- The backend, queue, workers, provider path, persistence, and event semantics are
  unchanged.

### Costs and limitations

- Remote users must sign in again after Chrome restarts or the unpacked extension
  is reloaded following a rebuild.
- There is no refresh-token or silent-renewal contract.
- The extension does not share the normal web application's session storage or
  cookies; it establishes its own backend session through the same login route.
- A compromised Chrome profile or host can inspect an active extension session.
- Tailscale/private-LAN live proof is required before claiming this topology
  works for a specific deployment.

## Rejected alternatives

### Send both API key and Bearer session

Rejected. Remote mode intentionally rejects static API keys, and mixed authority
would obscure identity and fallback behavior.

### Enable API-key acceptance in remote mode

Rejected. That would weaken backend exposure semantics and contradict the
trusted-remote contract.

### Store the remote password

Rejected. The password is only for session establishment and must not become an
extension credential store.

### Persist the remote token in `chrome.storage.local`

Rejected for this client. The existing session is expiring and revocable; Chrome
session storage better matches its lifecycle and reduces persistence after
browser restart or extension reload.

### Proxy chat or login through the service worker

Rejected. The disposable worker must not become an auth broker, chat-state owner,
or liveness dependency.

## Proof surface

Automated proof must show:

- version-1 local profiles migrate without exposing or reclassifying the key;
- remote profile serialization contains no session token or password;
- the remote session token is stored only in `chrome.storage.session`;
- local requests attach only `X-API-Key`;
- remote requests attach only `Authorization: Bearer`;
- remote login parses the existing session response;
- remote logout uses the same Bearer session;
- first-run, restored local, restored remote, task acceptance, terminal refresh,
  and disconnect behaviors remain covered;
- the production manifest and artifact permission posture is unchanged.

Live proof for one Tailscale deployment must show:

1. Chrome grants only the configured Tailscale origin.
2. A provisioned Codexify username/password creates a remote session without an
   API key in the browser flow.
3. Existing threads load under the authenticated account.
4. A message/completion reaches terminal evidence and the persisted assistant
   reply is re-read.
5. Side-panel close/reopen restores the session and selected thread within the
   same Chrome session.
6. Disconnect clears extension state and subsequent protected access requires a
   new login.

This proof is topology-specific and does not widen the supported beta release.

## Release-truth boundary

`docs/architecture/00-current-state.md` remains unchanged. Local Docker Compose
remains the supported install path. This private, unpacked extension and its
Tailscale access path remain internal, manually installed, and outside the
supported beta and Chrome Web Store claims.

## Non-goals

- Backend authentication, exposure, session, JWT, or account-schema changes.
- Public internet or hosted-SaaS support.
- Tailscale configuration, identity federation, or automatic topology discovery.
- Multiple connection profiles or shared Network Profile persistence.
- Cookie sharing with the normal Codexify web application.
- Refresh tokens, OAuth, passkeys, hardware-backed credentials, or automatic
  session renewal.
- Page content, content scripts, tabs, browser automation, or Web Store packaging.

## Governing and related documents

- [ADR-005: Runtime Mode and Account Boundary Invariants](./005-runtime-mode-and-account-boundary-invariants.md)
- [ADR-039: Operator / User Access Boundary](./039-operator-user-access-boundary.md)
- [ADR-040: Network Profile Topology Resolution Contract](./040-network-profile-topology-resolution-contract.md)
- [Remote Account Access and User Profile Contract](../remote-account-access-and-user-profile-contract.md)
- [Trusted Remote Auth Seam Audit](../trusted-remote-auth-seam-audit.md)
- [Chrome Side-Panel Client](../chrome-side-panel-client.md)
- [ADR-001: Queue-Based Completion Acceptance Model](./001-queue-based-completion-acceptance-model.md)
- [ADR-003: Message Identity vs Request Identity](./003-message-identity-vs-request-identity.md)
- [ADR-038: Chat Transport Visibility and Adaptive Stream Recovery Contract](./038-chat-transport-visibility-and-adaptive-stream-recovery-contract.md)

## Documentation follow-through

- Add ADR-049 to the ADR index and architecture KB.
- Update the Chrome side-panel architecture boundary and operator README.
- Explicitly leave `00-current-state.md` unchanged.
