# ADR-092: Credential Purpose and Mixed-Principal Authentication Boundary

**Status:** Accepted architecture contract — 2026-09-26; partial runtime implementation

## Context and evidence boundary

Guardian account sessions, API-key-exchanged operator sessions, and Hosted Room
guest sessions are separate credential classes. Canonical account login now
issues a signed token whose `subject` is the canonical user ID and whose
purpose is `account_session`, then stores that token with its user ID in the
session store. The current guest
token uses `subject=hosted_room_guest_session` as its purpose marker and binds
one room, participant, and invitation. These token families use the configured
Guardian session-signing secret. The admin session endpoints use the same
signer to exchange `GUARDIAN_API_KEY` for a token with `subject="web"`, without
a canonical user ID or account-session-store entry. Generic remote
signed-token validation checks signature and a nonempty subject without
consistently checking credential class. A purpose-specific operator validator
is now used by the Continuity operator route; generic remote account
validation remains unstrict. This is a **static token-purpose
separation concern**, not proof of a live account-authentication bypass;
private-preview account authentication also requires a stored session for an
approved account.

ADR-091 supplies durable `backend_task_id -> ChatCompletionAttempt -> thread_id`
authority, and the shared thread-read policy accepts an already-authenticated
account `RequestUserScope` or `HostedRoomGuestPrincipal`. The task-event SSE
route now composes those authorities: it resolves the task through the durable
attempt, applies the thread-read policy, and only then consumes Redis events.
The route accepts only account/local request-user or purpose-scoped guest
principals; remote operator credentials do not resolve thread authority. This
bounded code/test result does not claim the public-ingress boundary is closed.

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
- The **operator lane** uses configured Guardian API-key authority or its
  signed `operator_session` derivative only on explicitly operator-authorized
  surfaces. It does not resolve a canonical user or a `RequestUserScope`.
  `X-Admin-Token` and private-preview account-admin checks remain separate
  additional gates wherever the route currently requires them.

The lanes are not interchangeable. A credential from one lane never resolves
a principal in either other lane.
Neither a cookie name nor the first decoder attempted is authority to change
class. A failed validation in one lane cannot fall back to another.

Human administrative account-observability actions use the **account lane** as
their sole principal. The exact-purpose `account_session` resolves the
canonical human and audit actor; Guardian-owned admin permission authorizes
that account. A route-required service key is a separate, non-principal
capability gate and cannot resolve a user, grant admin status, or become an
`operator_session`. The implemented dashboard viewer snapshot uses the same
one-principal/service-capability distinction, but remains available to its
current authorized admin and guest viewers; admin authorization is required
for admin-only operations, not for that viewer projection.

The same configured raw Guardian key can have different route-bounded roles:
`require_operator_auth` treats it as operator-principal material on an
explicit operator/control-plane route, while a dedicated service-capability
dependency treats it only as capability proof on an explicitly designated
human-account route. The selected dependency contract, not the key bytes,
determines its meaning. A route must never evaluate the same key as both a
service capability and an operator principal. The service-capability
dependency must validate only the required key, return no account or operator
principal, perform no account lookup or admin check, and provide no fallback
authentication. Generic `require_api_key` and `require_operator_auth` are not
that dependency on human account-observability routes.

| Route pattern | Sole principal | Additional gates | Example and boundary |
|---|---|---|---|
| Machine/operator control plane | Exact-purpose `operator_session` or raw key admitted by `require_operator_auth` | Route-specific operator controls, if any | Continuity operator routes; no canonical human audit actor is inferred. |
| Human administrative account observability | Exact-purpose `account_session` for the canonical human | Admin authorization on that account; non-principal service capability where required | Invite, retention, and future account-observability admin routes; no `operator_session` is accepted. |

The current dashboard viewer snapshot also has one account principal and a
service-capability gate, but admits its authorized guest as well as admin
viewer; it is not an admin-only route. Its generic router dependency still
needs migration. The five account-observability invite and retention operations
now use exact-purpose account sessions, persisted account admin authorization,
and a non-principal service-capability gate. These rows do not claim full
runtime enforcement across other account consumers.

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
guest- and operator-purpose tokens, even when their signature is valid or they
arrive through `Authorization` or `gc_session`. Guest validation must continue
to require the existing exact `subject=hosted_room_guest_session` domain and
its bound claims; it must reject account- and operator-purpose credentials. A signed
API-key-exchanged operator credential must carry exactly
`purpose=operator_session`; operator validation must reject account and guest
credentials. Raw Guardian API-key material is operator credential material,
not a signed account session. Conflicting class claims fail closed. The future
runtime task must register any new contract-bearing values in the appropriate
canonical token domain before using them in code.

Frontend account-session invalidation uses the registered
`X-Guardian-Auth-Failure: ACCOUNT_SESSION_INVALID` response signal. Guardian
emits it only for a missing or rejected account-lane credential; a signed
credential with another purpose and an operator-route rejection do not carry
the signal. The frontend therefore does not infer account invalidity from HTTP
401 alone. This signal classifies failure only and grants no route authority.

| Signed credential class | Account validator | Operator validator | Hosted Room guest validator |
|---|---|---|---|
| `account_session` | Account checks required | Reject | Reject |
| `operator_session` | Reject | Operator checks required | Reject |
| Hosted Room guest session | Reject | Reject | Room, invitation, participant, and lifecycle checks required |

The shared `issue_session_token` signer may remain shared only with an explicit,
mandatory purpose input (or an equivalent typed API) and **no default
purpose**. Canonical account login must request `account_session`; the
API-key-exchange endpoints must request `operator_session`. `subject="web"` is
legacy subject data, not the operator-class authority. A future unclassified
caller blocks implementation rather than inheriting a purpose from the signer.

Current login issues a signed account token containing `subject`, `exp`,
`nonce`, and `purpose=account_session`; it stores the token-to-user mapping
with a TTL and returns the token to the client. The same token can be
presented through a Bearer header or `gc_session`. Private preview additionally
requires the stored session and approved account. Generic account validation
does not yet enforce `purpose=account_session`. Account activation capabilities under
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

### API-key-exchanged operator credential

The `/auth/session` and `/auth/session/cookie` endpoints in
`guardian/routes/admin.py` exchange the
configured `GUARDIAN_API_KEY` for a signed `subject="web"` token; the cookie
endpoint places that token in `gc_session`. Neither endpoint authenticates a
canonical `User` or writes an account-session-store mapping. This credential
is an **operator_session**: a short-lived representation of the authority of
the API key that minted it. It is not an administrator *user*, an impersonated
user, an account session, or a Hosted Room guest. It creates no account ID,
membership, project, thread, document ownership, or guest participation.
The separate `require_admin` gate still requires its existing admin token,
private-preview account-admin principal, or bounded local debug condition;
an operator session does not satisfy that extra gate by itself.

Current consumer inventory, based on the production call graph, is:

| Current surface | Classification and observed behavior | Target authority |
|---|---|---|
| `guardian/routes/admin.py` `/auth/session` and `/auth/session/cookie` | API-key exchange; the only production `subject="web"` issuers. They issue explicit `operator_session` tokens and do not store them as account sessions. | Operator issuance only, with explicit `operator_session` purpose. |
| `guardian/routes/continuity_operator.py` | Uses `require_operator_auth`, which admits configured API-key authority or a valid exact-purpose `operator_session` and rejects other signed credential classes. It does not resolve account identity. | Explicit operator authority on this developer/operator-only route. |
| `guardian/core/dependencies.py::verify_api_key` / `require_api_key` in generic remote mode | Accepts any valid native session or compatible JWT signature before class validation. Consumers include operator/control routes **and** account-owned chat, projects, documents, Persona, task/event, and other application routes. | An operator token may pass only a route explicitly admitting operator authority. Its current generic acceptance on user-owned routes is implementation debt, not permission. |
| `guardian/core/dependencies.py::get_request_user_id`, `get_request_user_scope`, and `verify_api_key` in private preview | Private preview requires a stored approved account session, so the unstored admin-issued web token does not satisfy that path as issued. Generic multi-user subject parsing can otherwise treat a signed `web` subject as user context. | Operator purpose must fail account resolution before session-store or subject mapping. |
| `guardian/core/auth.py::require_auth` / `require_user` | Accepts a signed `web` token as a generic session and accepts raw `GUARDIAN_API_KEY`/`X-Guardian-Key` material; `require_user` can then construct user context. Account-export and federation-context routes consume that helper. | Operator purpose or raw key must not produce user identity. Current acceptance is implementation debt. |
| `guardian/core/auth_dependencies.py` store resolver and its callers | Account login stores user-bound tokens; admin issuance does not. Store-only resolution is used by private-preview, WebSocket, dashboard, account-observability, logout, and other consumers. | Validate account purpose before resolving account identity; a store hit cannot convert operator purpose into account authority. |
| `guardian/core/hosted_room_session.py` guest decoder | Requires exact `subject=hosted_room_guest_session`; rejects a `subject="web"` token. | Guest-only, with current room, invitation, participant, and lifecycle checks. |
| Public entry points and local API-key mode | Public endpoints grant no principal from a web token. Deliberately local/single-user API-key handling is governed by its existing runtime-mode contract. | No implicit account or guest authority; local behavior remains separate. |

This table classifies consumers of the signed web token, including the broad
`require_api_key` route family; it does not grant operator authority to every
route that currently uses that generic helper. In particular, ordinary
account-owned application routes and task/event routes must not admit an
operator token merely because its signature passes. The operator lane is
limited to surfaces explicitly authorized for Guardian/API-key control-plane
operations. `continuity_operator.py` was the first migrated consumer with
purpose-specific operator-session validation. The frozen operator-only route
set was subsequently migrated through that same explicit seam at
`0731a02a60811093a70128e461b4a55c8f56a13c`. The admin diagnostic gate
still uses its own `X-Admin-Token` or private-preview account-admin check.
Remaining generic remote acceptance and subject-only user construction must be
narrowed in later runtime work; this document is not live bypass proof.

### Bounded PostgreSQL qualification

At commit `1598b9dbd30a1c156d70c6d44ffe02c57afa0d72`, the first explicit
`operator_session` consumer—the six-route Continuity operator surface—passed
the eight PostgreSQL integration cases, the complete 67-case Continuity
operator suite, and the focused 35-test operator/authentication regression
against an isolated disposable PostgreSQL target. The evidence is recorded in
[`2026-09-26-continuity-operator-auth-postgres-proof.md`](../proofs/runtime/2026-09-26-continuity-operator-auth-postgres-proof.md).
This qualifies only that consumer and does not mean ADR-092 is fully
runtime-enforced. At `0731a02a60811093a70128e461b4a55c8f56a13c`, the
separate frozen operator-only migration passed its activation-aware test
qualification: 52/52 declared migrations structurally use
`require_operator_auth`; 23 enabled declarations passed applicable route proof;
28 default-off declarations retained their profile/flag posture; one graph
declaration remained unmounted; and four separately quarantined model-override
declarations remained qualified. The five-route account-observability
service-capability separation is now qualified by focused tests:
`require_service_capability` returns no principal, and the route-owned human
gate checks exact `account_session` purpose, the approved session, and the
persisted admin account before capability validation. Strict generic
account-purpose validation, `auth_dependencies.py` bypass closure, legacy
account-token rejection, and public-ingress qualification remain deferred.
Task-event SSE object authorization is implemented at its route-specific
principal boundary and remains subject to the focused proof receipt. Remote HTTP mixed-principal
rejection is now implemented at the generic and strict account dependencies,
the explicit operator-auth dependency, the account-observability human gate,
and authenticated Hosted Room guest session-inspection, message, and invoke
routes. It does not change local/single-user handling or establish task-event
ownership.

The shared WebSocket account handshake in `guardian/ws/auth.py` now checks an
exact signed `purpose=account_session` before consulting the approved session
store. It rejects a missing or different purpose, an expired or malformed
token, an absent session mapping, and a mapping that disagrees with the signed
subject. Both query and first-auth-frame credential transports use this seam;
private-preview approval still follows the mapping, while the local API-key
lane remains available in local posture. Focused WebSocket and auth regressions
qualified this bounded code path. This does not close the generic
`auth_dependencies.py` resolver, the remaining account-route migration, or
the public-ingress proof.

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

There is **no precedence** between account, Hosted Room guest, and operator
credentials. A protected request that presents nonempty material from more
than one **principal-establishing credential lane** is mixed, whether the
combination is account + guest, account + operator, guest + operator, or all
three. Detect presence before validating any credential or looking up a
protected resource.
This includes malformed, stale, or otherwise invalid material; failed
validation in one lane cannot fall back to another. The client must
intentionally present one principal lane.

At a remote multi-principal boundary, `Authorization` and `gc_session` may
carry either a signed account or operator credential. Classify signed material
by its explicit purpose when needed to distinguish those two lanes. An
unverified purpose is presence evidence only, never authority. An absent,
malformed, or conflicting purpose establishes neither lane and cannot be
treated as an account credential by default. The separate
`codexify_hosted_room_session` selector is guest-lane material. Its presence
with any nonempty `Authorization` or `gc_session` material is mixed even if
that signed material is malformed or expired. Nonempty raw
`X-API-Key` or `X-Guardian-Key` material is operator-lane material wherever it
is validated by an operator-authentication seam. Its presence alongside an
account credential or guest selector at that seam is mixed even if either
credential is invalid; it does not become a remote account principal. On a
route explicitly requiring a non-principal service capability, that same raw
key is capability material only; its presence beside one account session is
not mixed-principal authentication. A missing or invalid service capability
denies that route and never falls back to operator or account authentication.
Signed `operator_session` remains principal material even on such a route:
`account_session` plus `operator_session` is always mixed and rejected.
On an operator-auth route, raw key plus signed operator token is two selectors
in the same lane, not automatically a cross-principal mix;
this ADR does not add precedence between those selectors or permit either to
establish account or guest authority. Distinguishing account and operator purposes
presented through separate signed selectors must not perform identity,
session-store, guest, or protected-resource lookup.
Deliberately local/single-user API-key identity resolution remains governed by
the local runtime-mode contract and is outside this remote multi-principal
rule; this is not a remote credential fallback.

The canonical mixed-lane response is **HTTP 400** with machine-readable error
`mixed_principal_credentials` and a generic message such as `Conflicting
authentication contexts`. It must reveal neither credential's validity nor
the existence of a task, thread, or room. The error is registered in
`guardian/protocol_tokens.py` and emitted by the shared remote HTTP presence
check. That check reads an unverified purpose claim only to classify account
versus operator presence; it does not treat the claim as authority. Raw
operator keys are classified only at the operator-auth seam, so a route's
non-principal service-capability factor remains separate. The implementation
does not change local/single-user behavior, WebSocket authentication, or
task-event object authorization.

| Request state | Result before protected data access |
|---|---|
| No credential, or one lane with an invalid credential | Existing authentication failure semantics, normally HTTP 401 in remote mode. |
| More than one principal lane present | HTTP 400 `mixed_principal_credentials`, regardless of credential validity. |
| One account principal plus a route-required non-principal service capability | Not mixed; each account, authorization, and capability gate must pass independently. |
| Valid principal without resource access | Existing thread or Hosted Room authorization response. |
| Unknown protected resource after authentication | Existing non-disclosing not-found response. |

Authentication and mixed-lane rejection precede task, thread, room, and Redis
lookups. This ADR does not change precedence between multiple mechanisms
*within* the account lane. Each route must declare whether a raw key is an
operator selector or a service-capability factor before classifying credential
presence; the same key cannot fill both roles on that route.

## Implementation order and proof obligation

1. Classify credential presence and reject mixed lanes before resource lookup.
2. Validate the selected credential's explicit class and purpose using its
   canonical decoder; resolve exactly one typed principal without cross-lane
   fallback.
3. For task-event SSE, resolve the task through ADR-091's durable attempt,
   authorize its canonical thread through the shared policy, and only then
   consume Redis events. A missing durable attempt fails closed.

Implementation must prove account, guest, and operator cross-class rejection;
operator-purpose rejection by account and guest validators; account- and
guest-purpose rejection by the operator validator; raw operator-key mixed
presence on operator-auth routes; account-session plus service-capability
admission only on routes expressly requiring that capability; denial of
service-key-only, non-admin, and invalid-session fallback cases;
mixed presence with valid and invalid material; anonymous denial before resource
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
  neither role grants guest or task authority by itself. An API-key-derived
  operator session is not a canonical user account.
- **ADR-053:** Guest sessions remain room-, participant-, invitation-, and
  lifecycle-scoped. This ADR classifies same-room completion-event observation
  as a bounded Hosted Room operation without making the guest a general user.
- **ADR-088:** Account activation remains a one-time credential-bootstrap
  capability, not a session or a guest credential.
- **ADR-091:** Postgres attempt-to-thread binding is the task authority;
  Redis transports events and never decides ownership.

This decision extends those boundaries without superseding them. Intentional
local/single-user defaults remain separate and unchanged. The task-event SSE
route uses the existing mixed-principal presence detector before task lookup,
then exact remote account-session validation or the existing local request-user
path; a guest cookie resolves only to its guest principal. The explicit
operator-session seam, qualified Continuity operator consumer, and frozen
operator-only route migration are implemented and test-qualified on their
bounded surfaces. Global account-purpose strictness and three-lane mixed
rejection remain accepted contracts that are **not yet globally runtime-enforced**.
The task-event route enforces its own mixed-credential boundary without changing
global credential defaults. Full public-ingress requalification remains
pending; `PUBLIC_INGRESS_AUTH_BOUNDARY=HOLD` remains the accurate status.
