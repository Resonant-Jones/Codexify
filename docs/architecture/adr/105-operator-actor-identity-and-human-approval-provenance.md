# ADR-105: Operator Actor Identity and Human Approval Provenance

## Status

Proposed.

Acceptance is a human decision. This ADR records a contract only; it does not
change runtime behavior, and no runtime implementation is authorized by this
document alone.

## Date

2026-10-28

## Context

ADR-100 requires a durable Campaign Continuation Authority record to retain
approval provenance, binding an approving actor and an approval time, and
states that an *authorized human operator* approves the envelope. The durable
record already carries `approved_by_actor_id` and `approved_at`, and the store
rejects an empty actor.

The three Campaign Continuation Authority routes registered on
`campaign_runner_router` inherit that router's
`dependencies=[Depends(require_operator_auth)]`. Two of them — approval and
revocation — additionally resolve an actor through
`guardian/routes/coding_work_orders.py::_resolved_operator_actor_id`, which
dispatches on the kind of operator credential presented:

- `operator-api-key` → `get_single_user_id()`
- `operator-session` → `get_current_user_id(request)`

`get_current_user_id` resolves through
`guardian/core/auth_dependencies.py` → `SessionStore.verify(token)`, which is
the **account** session registry.

ADR-092 defines the `operator_session` credential as "a short-lived
representation of the authority of the API key that minted it… not an
administrator user, an impersonated user, an account session", and records that
`guardian/routes/admin.py::create_session` and `create_session_cookie` do not
write an account-session-store mapping. The two identity mechanisms are
therefore incompatible by design, and the consequence is observable on
`4791f219d`:

| Credential presented | List authorities | Approve | Revoke |
|---|---|---|---|
| `operator_session` (minted by `admin.create_session`) | 200 | 401 | 401 |
| raw `GUARDIAN_API_KEY` | 200 | 200 | 200 |
| none | 401 | 401 | 401 |

The failing path is **fail-closed**: the handler is not reached, no authority
record is mutated, and no store accessor is touched. This is not an
authorization bypass.

Where approval does succeed, the recorded actor is `get_single_user_id()` —
the deployment principal (`CODEXIFY_SINGLE_USER_ID`, default `local`). That is
a deployment label, not an individually identified human, so ADR-100's
approval-provenance requirement is not currently met by a named approver.

The distinction the current code collapses is: *being authorized to operate a
control plane* and *being identifiable as the human who approved something*.
These are not automatically the same fact. ADR-092 keeps the operator lane and
the account lane separate on purpose, and ADR-039 treats "operator" as "person
or entity responsible for the deployment" while recording that Codexify does
not yet ship a runtime operator/user role system.

A second, independent concern sits behind the same seam: even the working
lane records a deployment label rather than a person, so the durable record
cannot later distinguish "the operator of this deployment approved this" from
"an individually identified human approved this".

## Current-Truth Anchors

Proven by inspection and reproduction on `4791f219d`:

- `_resolved_operator_actor_id` resolves the operator-session lane through the
  account session store.
- The `operator_session` lane receives 401 `Invalid or expired session` on
  approval and revocation, while the same credential lists authorities
  successfully — the distinguishing prediction, reproduced with an in-memory
  recording store that never touches durable authority state.
- The raw API-key lane reaches both mutation handlers and records the
  deployment principal as the actor.
- `guardian/core/auth_dependencies.py::get_current_user_id` is the
  account-session resolver, not an operator resolver.
- ADR-092 states that an operator session is not an account session and is not
  stored in the account session store.
- The canonical account lane issues `purpose=account_session` with
  `subject=user.id` and writes the token-to-user mapping
  (`guardian/routes/auth.py::_login_user`).
- `guardian/routes/account_observability.py::_require_account_admin` already
  resolves a canonical account-admin principal: an exact-purpose account
  session, a persisted account mapping equal to the token subject, a persisted
  canonical `User` row, and `role == "admin"` — returning `account.id`. It is
  composed with the independent non-principal `require_service_capability`
  lock by `_account_admin_capability_dependencies`, whose stated purpose is to
  "require one human admin principal and an independent service lock".
- `users.role` is constrained to `('admin', 'guest')` by `users_role_check`.
- ADR-088 already records the canonical-user-id precedent: "Issuance requires a
  valid canonical Guardian operator identity with the required administrative
  role. The durable capability records the creating operator's canonical user
  ID."
- `CampaignContinuationAuthorityRecord` persists actor strings and timestamps,
  but no approval or revocation credential/provenance class. Its readback
  includes the actor strings without classification.
- `CampaignRunnerStore.approve_continuation_authority` returns an existing
  unrevoked authority as an idempotent success when envelope, actor string, and
  expiry match, both before insert and after a uniqueness conflict. It does
  not compare actor provenance. In the collision fixture
  `CODEXIFY_SINGLE_USER_ID=local` and canonical admin `User.id=local`, a legacy
  raw-key approval and a future account-admin approval have identical stored
  actor bytes and satisfy the existing idempotency predicate. This is a
  source-level collision reproduction, not a live deployment test.
- The origin class of every pre-existing authority record is determinable
  rather than merely assumed. The table and its only writer were introduced
  together in `6beebd43b` (2026-10-05), so no earlier writer could have
  produced a different actor value; that writer resolved the approver through
  `get_single_user_id()` for the operator API-key lane and through an
  account-session-store lookup for the operator-session lane; and no
  `operator_session` credential is ever written to the account session store —
  `guardian/routes/admin.py` mints them without storing, while every
  `get_session_store().store(...)` call site stores an `account_session`
  credential. The operator-session lane therefore always failed closed before
  the handler ran and could never contribute an approver id. Every
  pre-existing approval and revocation is consequently a deployment-operator
  action.

Not yet proven:

- That a named-human approval path is reachable in the supported local Docker
  Compose posture.
- That the account-admin role may legitimately be designated the authorized
  human operator for authority approval without amending ADR-092.
- That the full backend suite passes after any runtime correction.
- That current-main supported-Compose qualification is green.
- That any external immutable deployment audit artifact exists for every
  historical record. Such an artifact cannot be assumed from the current
  authority schema or store readback.

## Decision

### 1. Human approval requires a canonical account-admin principal

Approval and revocation of a Campaign Continuation Authority are performed
only by a principal that satisfies all of the following:

- an exact-purpose `account_session` credential;
- a persisted canonical account mapping whose identity equals the token
  subject;
- a persisted canonical `User` row whose `role` is `admin` — and, in private
  preview, whose preview email role is also `admin`;
- an independent, non-principal service-capability gate.

The canonical `User.id` is the approving actor. The existing account-observability
admin seam is the reference implementation of this pattern; a shared dependency
must be derived from it rather than reimplemented.

No new credential class, token purpose, or identity primitive is introduced to
express this. The account lane and its `admin` role already exist and are
already the canonical human-actor mechanism.

### 2. The operator-control lane does not manufacture human identity

Raw API-key material and `operator_session` credentials retain their existing
operator-control lane. They may continue to authorize operator surfaces that do
not require a human approver.

They must never produce, imply, or be recorded as a human approver identity.
Concretely: an operator credential must not be accepted as sufficient to
approve or revoke a Campaign Continuation Authority, and an operator-derived
deployment principal must not be written into `approved_by_actor_id` or
`revoked_by_actor_id`.

This preserves ADR-092's rule that operator purpose or raw key must not
produce user identity, and it preserves the account / operator / guest
principal separation.

### 3. The two human-approval mutations leave the inherited operator-only router dependency

FastAPI applies a router's `dependencies` to every route registered on it and
combines, rather than replaces, route-level dependencies. The two
human-approval mutations therefore cannot keep the inherited
`require_operator_auth` dependency while additionally requiring an
account-admin principal: a single request would have to satisfy two
conflicting principal classes, and the operator gate would fail an
account-admin request before the account gate could be evaluated.

They move to a dedicated router on the same path prefix
(`/api/coding/campaign-runner`), mounted under the same `coding_work_orders`
label so that the supported-profile posture, the enabling flag, and the
internal-only topology are unchanged.

The read-only listing route remains in the operator-control lane on
`campaign_runner_router`. Reading the set of existing authorities is not an
approval and does not require a human actor.

### 4. Actor identity and credential provenance are distinct durable facts

For new human actions, `approved_by_actor_id` and `revoked_by_actor_id` carry
the canonical `User.id`. The existing `String(255)` actor fields are sufficient
for actor *identity*, but not for approval or revocation *provenance*.

The authority record must also durably classify **each action independently**:

- `legacy_deployment_operator`: historical operator-control or otherwise
  unverified action, without an individually verified human approver;
- `canonical_account_admin`: action authenticated through the exact-purpose
  account-admin lane plus the independent service-capability gate.

This is authority-record metadata, not a new principal, credential class,
capability family, token purpose, or human role. A narrow persisted provenance
discriminator for approval and one for revocation, on the existing canonical
authority record, is **required** — the distinguishability this contract
requires cannot be delivered by the actor string alone, and a preferred or
optional discriminator would leave the ambiguity in place. A later
implementation task must select the concrete schema representation, enforce
non-null classification for applicable actions, and prove migration,
backup/restore, and export/readback behavior. No DDL or data migration is
performed by this proposed ADR.

A cutoff inferred solely from actor ID strings, the deployment's current
`CODEXIFY_SINGLE_USER_ID`, the current admin registry, or mutable wall-clock
configuration is insufficient. A cutover could replace explicit columns only
if its immutable per-record provenance evidence remains persisted and
unambiguous across restores, exports, clock differences, and colliding IDs.
No such durable mechanism is established in the inspected implementation;
do not claim a schema-free solution on that basis.

### 5. Historical deployment-principal attributions are legacy, unverified provenance

All authority approvals created before the separately authorized human-approval
runtime cutover have **legacy/unverified human provenance**, regardless of
whether their actor string matches `local`, a configured deployment principal,
or a canonical `User.id`. Existing records must retain their original actor
string, timestamps, envelope, expiry, and revocation history; migration may
classify their known pre-cutover origin as legacy, but must never infer or
back-fill an individual's identity. A historical deployment principal is not
a named human even if its bytes match an admin ID.

The same principle applies independently to historical revocations. A future
human admin may revoke a legacy-approved authority; the revocation must carry
human provenance without upgrading or replacing the original legacy approval
provenance. A legacy revocation stays legacy when read back later.

Before any authority can be consumed for automatic continuation, unresolved or
legacy approval provenance must fail closed as **not human-approved**. An
unrevoked legacy record must not become eligible merely because its actor ID
matches a current admin. Revocation remains permitted through the correctly
authenticated human lane, but replacing a legacy approval requires an explicit
new human approval after revocation, not relabeling the old row.

Every readback, operator view, audit, export, restore, and downstream authority
consumer must preserve and distinguish these classes without deriving human
identity from actor strings. If a historical row's origin cannot be proven,
classify it as legacy/unverified, never as verified human approval.

In this codebase the origin of every pre-existing row is proven, as recorded
under Current-Truth Anchors: the table and its only writer share a single
origin commit, and the operator-session lane could never have contributed an
approver id because no `operator_session` credential is ever written to the
account session store. A bounded migration may therefore assert
`legacy_deployment_operator` for those rows directly, rather than recording a
weaker unclassified marker. The conservative fallback above remains the rule
for any row whose origin cannot be established, and it must never be relaxed
to accommodate an unproven row.

The approval store's idempotency comparison (including its integrity-error
retry path) must compare **approval provenance class** as well as actor ID,
envelope, and expiry. Identical actor bytes across distinct provenance classes
must not produce an idempotent success. The existing one-unrevoked-authority
constraint then requires explicit revocation before a new human approval.

### 6. No new authority primitives

This decision does not create an operator registry, extend
`capability_family`, introduce a new token purpose or credential class, or
create a parallel Campaign authority store. Human principal resolution
composes existing account-session, canonical `User`, `admin` role and
service-capability primitives. Persisted *provenance metadata* and a bounded
migration may be necessary to keep old and new actions distinguishable.

### 7. Consequence: human approval availability depends on an admin account

Because the operator-control lane can no longer approve, a deployment must
have an admin account for Campaign Continuation Authority approval and
revocation to be available at all. This is a deliberate consequence of
recording a human approver, and it must be stated plainly rather than
discovered at runtime.

The account-admin role must remain reachable in the supported local posture
for this to be an acceptable operational constraint. If it is not, that is a
separate finding requiring its own decision; it is not grounds to weaken this
contract or to fall back to the operator lane.

## Relationship to Existing Decisions

- **ADR-092 — Credential Purpose and Mixed-Principal Authentication Boundary.**
  This decision is subordinate to ADR-092 and does not amend it. Operator
  credentials keep their lane and do not produce user identity. The account
  lane is used for a purpose ADR-092 already recognizes: a canonical
  account-session principal with an explicit role.
- **ADR-100 — Campaign Continuation Authority Contract.** This decision
  supplies the approving-actor mechanism ADR-100 requires, and narrows
  ADR-100's "authorized human operator" to a defined, existing principal class.
  ADR-100 is not amended; this ADR states how its approval-provenance
  requirement is met.
- **ADR-039 — Operator / User Access Boundary.** Consistent with ADR-039's
  operator vocabulary and with its scope limit: ADR-039 remains docs-only
  role language, and this ADR does not implement a runtime operator role
  system. It does not create one; it selects an existing role.
- **ADR-088 — Guardian Account Activation and Credential Bootstrap.**
  Consistent with ADR-088's operator boundary and its canonical-user-id
  provenance precedent.
- **ADR-049 — Admin Account Observability and Invite Attribution.** The
  account-observability admin seam is the reference implementation for the
  account-admin principal and the independent service-capability lock.

## Non-Goals

This ADR does not:

- implement automatic continuation, dispatch, or any execution behavior;
- create an operator registry, operator role table, or new credential class;
- extend `capability_family` or the `users_role_check` vocabulary;
- introduce a new token purpose or canonical token domain value;
- change, weaken, or re-scope the `require_operator_auth` operator gate;
- change account login, account activation, invitation, or guest semantics;
- fabricate historical human identity, overwrite historical actor fields, or
  convert legacy approvals into human-approved authority;
- change supported-profile configuration or expand any enabled surface;
- update release claims, release metadata, or the release gate.

## Consequences

- The operator-session lane stops being a candidate for human approval. The
  401 it currently receives on the two mutation routes becomes the correct,
  intended outcome rather than a defect to be repaired by widening the
  operator gate.
- The operator-session credential remains a valid credential for the
  operator-control lane generally, and the read-only listing route continues
  to admit it.
- Human approval requires an admin account in the deployment. This is an
  operational constraint that must be documented for operators.
- Future approvals and revocations have verifiable canonical-human provenance,
  while historical and unresolved approvals remain independently classified as
  legacy/unverified and ineligible for automatic continuation.
- The existing authority record needs durable, collision-safe provenance
  classification. A narrow schema/migration slice is expected unless a simpler
  existing persisted mechanism is proven equivalent in the subsequent task.
- The account-admin dependency that today lives privately in
  `guardian/routes/account_observability.py` must be promoted to a shared
  seam, because the two surfaces need the same rule and a private copy would
  be able to drift.

## Proof Surface For Future Implementation

The runtime correction authorized by a later, separately approved task must
demonstrate, at minimum:

- the positive path: an exact-purpose account session belonging to a
  persisted canonical admin `User` reaches the approval handler, and the
  durable record stores that canonical `User.id` plus verified-human approval
  provenance;
- a collision fixture where a legacy deployment principal and a canonical
  admin `User.id` are identical; idempotency **both before insert and after a
  uniqueness conflict** must reject cross-class equivalence without mutating
  the legacy record;
- migration/readback/export/restore tests proving all pre-cutover approvals
  remain legacy/unverified even under actor-ID collisions, missing previous
  deployment configuration, and process restart; existing actor values and
  timestamps remain unchanged;
- independent approval and revocation classification, including a human
  revocation of a legacy-approved row without upgrading original approval,
  and legacy-revoked rows without retrospective human attribution;
- downstream authorization tests that treat legacy, missing, or unclassified
  approval provenance as **not** human-approved, regardless of status or
  actor-string equality;
- the negative credential paths: missing credentials, an operator
  `operator_session`, a raw operator API key, an account session for a
  non-admin account, an expired session, a malformed token, and a
  mixed-principal request are each rejected before any handler runs;
- zero unauthorized mutation: on every rejected request, no authority record
  is approved, revoked, or otherwise modified, and no protected store
  operation is reached;
- no regression to the operator-control lane for the listing route or for any
  other operator surface;
- no change to the `users_role_check` vocabulary, the `capability_family`
  vocabulary, or the set of canonical token purposes;
- the supported-profile mounting posture for `coding_work_orders` unchanged,
  with the two mutation routes still internal-only and still default-off;
- the frozen operator-route manifest reconciled with the router split,
  preserving the historical inventory and enumerating the ADR-100 routes
  separately.

## Stop Condition

Stop and report rather than proceed if any of the following holds:

- the existing account-admin role cannot legitimately be designated the
  authorized human operator for Campaign Continuation Authority approval or
  revocation under ADR-092 and ADR-100;
- reaching an admin account requires a credential class, token purpose, role
  vocabulary, or *account-identity* schema change not already present;
- durable provenance classification cannot be achieved on the canonical
  authority record, with a bounded migration or equivalently proven persisted
  mechanism, without changing unrelated authority domains;
- migration cannot preserve historical actor data while classifying old
  approvals and revocations as legacy/unverified;
- the later runtime task would allow legacy or unclassified approvals to
  authorize automatic continuation;
- the account-admin seam cannot be shared without changing existing account
  observability behavior.

## Related Documents

- [ADR-092: Credential Purpose and Mixed-Principal Authentication Boundary](./092-credential-purpose-and-mixed-principal-authentication-boundary.md)
- [ADR-100: Campaign Continuation Authority Contract](./100-campaign-continuation-authority-contract.md)
- [ADR-039: Operator / User Access Boundary](./039-operator-user-access-boundary.md)
- [ADR-088: Guardian Account Activation and Credential Bootstrap](./088-guardian-account-activation-and-credential-bootstrap.md)
- [ADR-049: Admin Account Observability and Invite Attribution](./ADR-049-admin-account-observability-and-invite-attribution.md)
- [Current State](../00-current-state.md)
