# ADR-092: Credential Purpose and Mixed-Principal Authentication Boundary

**Status:** Accepted architecture contract — 2026-09-26; runtime enforcement pending

## Context and evidence boundary

Guardian account sessions and Hosted Room guest sessions are separate credential
classes. Current account login issues a signed token whose `subject` is the
canonical user ID, then stores that token with its user ID in the session store.
That signed payload has no explicit account-purpose claim. The current guest
token uses `subject=hosted_room_guest_session` as its purpose marker and binds
one room, participant, and invitation. Both token families use the configured
Guardian session-signing secret. Generic remote signed-token validation checks
signature and a nonempty subject without consistently checking credential
class. This is a **static token-purpose separation concern**, not proof of a
live account-authentication bypass; private-preview account authentication
also requires a stored session for an approved account.

ADR-091 supplies durable `backend_task_id -> ChatCompletionAttempt -> thread_id`
authority, and the shared thread-read policy accepts an already-authenticated
account `RequestUserScope` or `HostedRoomGuestPrincipal`. The current task-event
SSE handler still uses only account-oriented authentication and does not apply
that durable lookup or thread policy. This ADR defines the missing
authentication contract. It does not repair the handler or claim the
public-ingress boundary is closed.

## Decision

### Distinct principal and credential lanes

- The **account lane** uses the supported account session/Bearer mechanisms,
  currently `Authorization` and `gc_session`, and resolves a canonical
  `RequestUserScope`. A local API key remains governed by the separate local
  runtime contract; it does not become a remote account session.
- The **Hosted Room guest lane** uses the purpose-scoped
  `codexify_hosted_room_session` credential and resolves a
  `HostedRoomGuestPrincipal` for exactly one room, participant, and invitation.
  Current session expiry and durable room, invitation, and participant
  eligibility checks remain authoritative.

The lanes are not interchangeable. A guest credential never resolves an
account principal; an account credential never resolves a guest principal.
Neither a cookie name nor the first decoder attempted is authority to change
class. A failed validation in one lane cannot fall back to the other.

### Signed-token class and purpose

A token signed by a trusted Codexify signing key is valid only for the
credential class and purpose explicitly encoded and validated for that token.
Shared signing infrastructure does not create shared authority. Signature,
expiry, a nonempty `subject` or JWT `sub`, and a persisted account mapping are
not substitutes for the required purpose check.

For **remote signed account credentials**, the explicit account-authentication
purpose is `purpose=account_session`. The existing account `subject` (or JWT
`sub`) continues to identify the account subject; it must not be overloaded as
the class marker. Account validation must require this exact purpose and reject
guest-purpose tokens, even when their signature is valid or they arrive through
`Authorization` or `gc_session`. Guest validation must continue to require the
existing exact `subject=hosted_room_guest_session` domain and its bound claims;
it must reject account-purpose credentials. Conflicting class claims fail
closed. The future runtime task must register any new contract-bearing values
in the appropriate canonical token domain before using them in code.

Current login issues a signed account token containing `subject`, `exp`, and
`nonce`, but no `purpose`; it stores the token-to-user mapping with a TTL and
returns the token to the client. The same token can be presented through a
Bearer header or `gc_session`. Private preview additionally requires the
stored session and approved account. No current account issuer or validator
enforces `purpose=account_session` yet. Account activation capabilities under
ADR-088 remain separate, purpose-bound bootstrap credentials; redemption still
leads to ordinary login rather than an automatic session.

### Legacy remote account-session transition

A remote signed account credential without the exact
`purpose=account_session` claim is a **legacy purpose-less credential**,
regardless of whether it is presented through Bearer or `gc_session`. When
strict purpose enforcement activates, it fails account authentication under
the existing invalid-account-credential response semantics. Neither a valid
signature, an account-shaped `subject`, nor a still-live token-to-user record
repairs the missing claim. It is not rewritten, re-signed, or converted in
place. No grace mode may interpret missing purpose as account purpose, even
when a persisted account session exists. A wrong-purpose credential likewise
fails account authentication. A rejected legacy token is never retried in the
Hosted Room guest lane, and a guest token is never retried as an account token.
ADR-092's presence-based mixed-lane HTTP 400 rule remains unchanged when both
credential classes are presented.

The transition is **reauthentication through the canonical account login**.
The user supplies their existing account login credential and receives a newly
issued token with `purpose=account_session` for the same canonical `User`.
Reauthentication does not delete or recreate the account or migrate ownership.
The account ID, projects, threads, messages, account admission and approval
state, activation history, and unrelated durable session or audit history
remain under their existing authority. Existing Redis session records need
not be deleted as a prerequisite; after enforcement they cannot authenticate
without the required signed purpose and may expire by their ordinary TTL.
Only the validity of the old credential changes. Local/single-user API-key
operation is outside this remote-session transition.

**Activation is one coordinated issuer-and-validator deployment unit.** The
implementation sequence is:

1. Make every remote account-session issuer emit the exact
   `purpose=account_session` claim while retaining its canonical account
   subject binding.
2. Prove a newly issued account token authenticates through the supported
   Bearer and `gc_session` transports, including private-preview stored-session
   and approval checks.
3. Prove a valid Hosted Room guest token cannot authenticate through the
   account lane.
4. Enable strict account-purpose validation only when all serving account
   issuers are purpose-aware. Do not serve a strict validator beside an old
   purpose-less issuer or expose an intermediate half-upgraded backend.
5. Prove pre-transition purpose-less account tokens fail closed even when
   validly signed, unexpired, and still present in the session store.
6. Prove canonical login issues a purpose-tagged replacement for the same
   account and restores authorized access to its existing data.

The current private-preview Compose topology declares one backend service,
with no repository-defined rolling multi-version backend pool. Its cutover
gate is to make the issuer and strict validator available together in the
same backend replacement before that backend accepts requests. If a future
deployment serves multiple backend versions concurrently, it needs a
separately reviewed coordination plan before strict enforcement; this ADR
does not authorize a legacy-token acceptance window to bridge versions.
This amendment defines the cutover contract only: no issuer, validator,
session, deployment, or live credential is changed here.

### Hosted Room completion-event observation

A currently eligible Hosted Room guest may observe task lifecycle events for
a completion whose ADR-091 durable attempt binds the task to that same room's
canonical backing thread. This is a Hosted Room operation subordinate to room
read and authorized completion visibility. The guest must pass the existing
guest session, invitation, participation, room lifecycle, and shared
thread-read checks. The task ID and event stream never grant authority.

This decision grants no access to a task from another room, an ordinary
private-account task, generic `/api/events`, or any other account route. It
does not make the guest the owner of `chat_threads.user_id`. The rule applies
to the task-specific SSE admission decision and every new connection or
reconnect; it does not change task-event payloads or transport semantics.

### Mixed-lane requests

There is **no precedence** between account and Hosted Room guest credentials.
On a protected request that can receive these credential selectors, nonempty
account-side authentication material (`Authorization` or `gc_session`) together
with a nonempty
`codexify_hosted_room_session` credential is a mixed-lane request. Detect
presence before validating either credential or looking up any protected
resource. This includes malformed, stale, or otherwise invalid material; an
invalid account credential cannot silently become a valid guest request, or
vice versa. The client must intentionally present one principal lane.
An `X-API-Key` presented alongside the guest credential at a remote
multi-principal boundary is also conflicting material and must be rejected;
it does not become a remote account principal. Deliberately local/single-user
API-key behavior remains outside this decision.

The canonical mixed-lane response is **HTTP 400** with machine-readable error
`mixed_principal_credentials` and a generic message such as `Conflicting
authentication contexts`. It must reveal neither credential's validity nor
the existence of a task, thread, or room. The error value is a contract for a
future runtime implementation; it is not an emitted token today and must be
registered under the runtime protocol-token rules before use.

| Request state | Result before protected data access |
|---|---|
| No credential, or one lane with an invalid credential | Existing authentication failure semantics, normally HTTP 401 in remote mode. |
| Both credential lanes present | HTTP 400 `mixed_principal_credentials`, regardless of either credential's validity. |
| Valid principal without resource access | Existing thread or Hosted Room authorization response. |
| Unknown protected resource after authentication | Existing non-disclosing not-found response. |

Authentication and mixed-lane rejection precede task, thread, room, and Redis
lookups. This ADR does not change precedence between multiple mechanisms
*within* the account lane.

## Implementation order and proof obligation

1. Classify credential presence and reject mixed lanes before resource lookup.
2. Validate the selected credential's explicit class and purpose using its
   canonical decoder; resolve exactly one typed principal without cross-lane
   fallback.
3. For task-event SSE, resolve the task through ADR-091's durable attempt,
   authorize its canonical thread through the shared policy, and only then
   consume Redis events. A missing durable attempt fails closed.

Implementation must prove account and guest cross-class rejection, mixed
presence with valid and invalid material, anonymous denial before resource
lookup, same-room guest access, wrong-room and ineligible-guest denial, and
zero Redis consumption on denied task-event requests. The legacy account-token
transition and any resulting client cookie-coexistence effects require
explicit compatibility qualification before enforcement is activated. In
particular, executable tests must cover purpose-tagged login issuance through
Bearer and `gc_session`; validly signed, unexpired, purpose-less legacy token
rejection with a live session-store row; valid guest and wrong-purpose token
rejection in the account lane; normal-login replacement after legacy denial;
same-account owned-data readback after replacement; mixed-lane HTTP 400
`mixed_principal_credentials` before either decoder or resource lookup; and
ordinary authentication failure for a malformed, expired, or unknown token
presented in only one lane.

## Relationship to governing decisions and current truth

- **ADR-039:** Account users and infrastructure operators remain distinct;
  neither role grants guest or task authority by itself.
- **ADR-053:** Guest sessions remain room-, participant-, invitation-, and
  lifecycle-scoped. This ADR classifies same-room completion-event observation
  as a bounded Hosted Room operation without making the guest a general user.
- **ADR-088:** Account activation remains a one-time credential-bootstrap
  capability, not a session or a guest credential.
- **ADR-091:** Postgres attempt-to-thread binding is the task authority;
  Redis transports events and never decides ownership.

This decision extends those boundaries without superseding them. Intentional
local/single-user defaults remain separate and unchanged. No token issuance,
validation, SSE, Cloudflare, or release behavior is changed by this document.
The task-event SSE repair and full public-ingress requalification remain
pending; `PUBLIC_INGRESS_AUTH_BOUNDARY=HOLD` remains the accurate status.
