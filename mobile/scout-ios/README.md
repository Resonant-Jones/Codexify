# Scout iOS Native Client

> Build proof: [SCOUT_V1_BUILD_PROOF.md](./SCOUT_V1_BUILD_PROOF.md)

Scout is a native SwiftUI client for operating against an existing Codexify/Guardian (Vault) backend. It is a mobile operator console, not a full clone of the Codexify web UI.

This implementation follows the concepts defined in [`../../docs/architecture/ios-scout-vault-remote-contract.md`](../../docs/architecture/ios-scout-vault-remote-contract.md).

**Guardian is the operator. Vault remains the long-term memory authority.** Scout observes and operates through Guardian/Vault surfaces; Vault remains the interpretation and persistence authority.

## Current V1 Capability Surface

Scout V1 implements five tabs:

| Tab | Purpose |
|---|---|
| Guardian Chat | Thread-scoped operations (Conversation + Inspector) |
| Server Status | Vault health and runtime evidence |
| Activity | Cross-thread task receipt timeline |
| Artifacts | Global document listing |
| Settings | Endpoint profile and API key configuration |

## Guardian Chat Lifecycle

Scout supports the full thread operation loop:

1. **Empty list** — When no threads exist, the list shows "No threads yet" with a direct "New Thread" button.
2. **New Thread** — Creates a thread container via `POST /api/chat/threads`. Thread creation does not send a message automatically.
3. **Auto-enter** — After creation, Scout navigates into the new thread immediately.
4. **Empty thread ready state** — A new empty thread shows "Thread ready" with an invitation to send the first message. No completion has been requested yet.
5. **Send message** — Posts a user message via `POST /api/chat/{thread_id}/messages`. Sending a message does not request completion automatically.
6. **Request completion** — Enqueues a Guardian response via `POST /api/chat/{thread_id}/complete`. Route acceptance does not prove completion.
7. **SSE task observation** — Connects to `GET /api/tasks/{task_id}/events` to stream live task events.
8. **Terminal refresh** — On `task.completed`, automatically refreshes persisted thread messages. On `task.failed` or `task.cancelled`, shows a neutral status without synthesizing assistant output.
9. **Rename thread** — Patches the thread title via `PATCH /api/chat/threads/{thread_id}`. The navigation title updates immediately and the thread list refreshes on return.

### Conversation / Inspector Split

Each thread detail is organized into two tabs:

- **Conversation** — Messages, composer, send, completion request, refresh messages
- **Inspector** — Thread Documents, Retrieval Evidence, Task Receipts, with dedicated refresh buttons

## Server Status

The Server Status tab provides Vault-level observability with Status and Evidence tabs:

- **Status** — Endpoint info, reachability (validation state + probe message), authentication state
- **Evidence** — Health snapshot (latency, service, health status, timestamp), LLM health (provider, model), Catalog (model count, providers, model names)

All evidence is display-only. Scout does not interpret health, readiness, or provider state.

## Activity

The Activity tab aggregates cross-thread task receipts using existing per-thread probes (`ScoutGuardianThreadsProbe` + `ScoutThreadTasksProbe`). It shows a unified timeline of task events across all threads with thread context. No global task-history backend route exists yet — Activity uses N+1 per-thread loading.

Future planned surfaces (not yet implemented): Active Tasks, SSE Observations, Completion Requests, Notifications.

## Artifacts

The Artifacts tab lists global documents via `GET /api/media/documents`. It is distinct from the thread-scoped Inspector: Inspector shows evidence attached to a specific thread; Artifacts shows user-owned outputs across all threads.

## Settings

Settings configures the Vault endpoint profile and API key:

- **Endpoint Profile** — Name, base URL, transport type with local draft validation
- **API Key** — Stored in iOS Keychain, never written to UserDefaults
- **Connectivity** — Validate draft, test connection with health probe
- **Persistence** — Non-secret profile fields saved to `@AppStorage`; API key in Keychain only

## Boundaries and Non-Claims

- Scout is not the full Codexify web UI.
- Scout is not the durable memory authority.
- Scout does not add backend routes.
- Scout does not replace the supported local Docker Compose path.
- Scout does not prove model availability by itself.
- Scout does not widen release support for delegation, federation, graph writes, or cloud providers.
- Scout observes and operates through Guardian/Vault surfaces; Vault remains the interpretation and persistence authority.
- Route acceptance is not completion. Task-event publication is not UI receipt. Scout does not infer completion success from HTTP 2xx.
- Scout does not synthesize assistant messages locally.

## Validation / Smoke Checklist

**Package build:**
```bash
cd mobile/scout-ios && swift build
```

**Test runner (232 assertions):**
```bash
cd mobile/scout-ios && swiftc -o /tmp/scout_test_runner \
  Scout/Models/*.swift Scout/Services/*.swift Tests/Runner.swift \
  -framework Security && /tmp/scout_test_runner
```

**Manual operator checklist** for verifying a Scout V1 build:

- [ ] Configure endpoint URL and API key in Settings
- [ ] Validate draft — check local validation feedback
- [ ] Test Connection — verify reachability and authentication state
- [ ] Load Server Status — confirm health, LLM, and catalog evidence
- [ ] Create a new thread — verify auto-navigation into thread
- [ ] Confirm empty thread ready state is shown
- [ ] Send a message — verify it appears in the conversation
- [ ] Request Guardian Response — verify task acceptance evidence
- [ ] Observe SSE task events — verify live task status stream
- [ ] Wait for terminal event — verify messages auto-refresh
- [ ] Rename thread — verify title updates in nav bar
- [ ] Return to thread list — verify renamed title appears
- [ ] View Activity tab — verify cross-thread task receipts
- [ ] View Artifacts tab — verify global document listing

## Hosted ingress and account qualification (October 4, 2026)

The registered public native client uses ASWebAuthenticationSession and PKCE S256.
For initial setup in Settings, select remote-session mode, then **Use hosted Codexify** and
**Authorize hosted ingress**. Keep the existing profile on subsequent sign-ins;
Use hosted Codexify creates a new profile identity. Complete Google/OTP only in the system browser.
**Check stored ingress** reads only this connection's Keychain credential, renews
an expired credential through its existing refresh grant when available, and
qualifies the protected API response without another browser login. A Guardian
account-session failure marker establishes that the request reached Guardian;
an Access challenge or an HTTP status alone does not. Returning to Settings
restores credential-presence status, not an authenticated-account claim.
The exact callback is `ai.resonantconstructs.codexify.scout://access-callback`.
No client secret exists. Ingress credentials remain in a separate profile/origin-scoped
Keychain record; neither credentials nor callback results belong in proof files.

Cloudflare admission and Guardian account identity remain distinct. After ingress
admission, **Sign in to Guardian** opens the existing canonical web account login.
An explicit **Continue to Scout** confirmation authorizes a separate native
session through a 60-second, single-use, origin-bound PKCE code and the already
registered callback. The server revalidates browser purpose, live session mapping
and account eligibility, then issues a fresh canonical `account_session` for the
same `User.id`. Browser session bytes are never returned to Scout. Native nonce,
expiry, revocation and logout are independent of the browser session.
No Access identity is converted into a Guardian user.

**Check account session** performs a protected thread read. Restoring a Keychain
record alone does not prove authentication. **Log out Guardian** removes this
connection's local account session and requests canonical server revocation;
the result distinguishes remote confirmation from a failed revocation request.
After accepted hosted logout, a bounded in-memory replay can additionally prove
Guardian HTTP 401 while Access remains admitted. No credential is restored or exported.
A marked account-session failure clears only the affected account credential.
Unrelated 401 responses preserve it. Expiry requires explicit sign-in again.

Connection = endpoint/transport + explicit authentication mode. Hosted requests
use Access in Authorization and the approved X-Guardian-Account-Session alternate
transport for the canonical account credential. Guardian accepts the alternate
header only at the fixed preview host/application with signed upstream admission;
its existing strict account validator remains authoritative. The approved
edge-consumed composition permits missing origin Authorization only after signed
fixed-host/private-preview Access validation; missing Authorization alone grants no trust.
Personal HTTPS
nodes retain account Bearer where supported, or explicitly selected local API
keys. Tailscale is transport, not identity. There is no local-key fallback.
All credentials are scoped by profile and origin, held only in Keychain. Legacy
global API keys are preserved but never silently adopted; explicitly save a key
for the selected personal connection. Credential-bearing requests cannot follow
redirects. Profile/account changes reset volatile client projections; Guardian
remains durable authority.

Source and tests implement this handoff. The independent-session amendment and
approved no-seed guard are deployed and verified on preview; the proof Simulator
completed all nine authentication stages, two full persisted-output continuity
turns, resume, document reads and logout denial. See [the live proof](SCOUT_LIVE_CONTINUITY_2026-10-04.md)
for exact build revisions and limits. LLM/operator evidence routes are
not promoted to account-authorized routes by this change. App Intents remain
downstream of operational continuity.

Live PKCE/token/admission qualification requires human sign-in in the dedicated
Scout proof simulator. Do not capture credentials, OTPs, callback codes, or tokens
in screenshots or logs. See [the progress record](SCOUT_REMOTE_SESSION_PROGRESS.md)
for historical evidence. Physical-device continuity, release support and
#816–#818 remain separate work; none is started automatically.
