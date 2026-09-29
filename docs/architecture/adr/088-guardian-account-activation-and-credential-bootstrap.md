# ADR-088: Guardian Account Activation and Credential Bootstrap

**Status:** Accepted; implementation present, qualification incomplete

**Date:** 2026-09-17

**Approver:** Resonant Jones

## Approval and evidence boundary

Resonant Jones explicitly authorized the first one-time tester account-
activation slice and subsequently dispatched this ADR canonicalization task.
This ADR accepts the architecture boundary already selected for that slice. It
does not by itself prove frontend behavior, existing-auth regression safety,
security-sentinel closure, a disposable runtime flow, a live tester profile or
origin, or issuance to a real recipient.

The implementation and migration are present in the current worktree. Their
presence and focused backend/migration proof do not widen Codexify's release
promise. [`00-current-state.md`](../00-current-state.md) remains the authority
for current release and support claims.

## Context

Guardian is the canonical user, credential, role, and session authority.
Before this slice, the stabilized tester provisioner could create or reset a
canonical `User`, but the operator had to choose the user's durable password.
That made the operator part of password custody and provided no recipient-owned
credential-bootstrap lifecycle.

Existing invitation domains cannot safely fill that gap:

- account-observability invite links are acquisition-attribution capabilities,
  not authentication authority;
- collaboration and hosted-room invitations grant different, narrower
  relationship or room authority;
- Cloudflare Access and private-network controls are outer access perimeters,
  not Guardian identity;
- no transactional security-email runtime currently exists.

`User.password_hash` remains non-nullable. Creating a pending `User` with a
missing password, a known placeholder password, or an operator-selected
password would weaken the canonical credential boundary. The smallest safe
design is therefore a purpose-specific capability whose successful redemption
creates the canonical `User` and consumes the capability in one transaction.

## Decision

Guardian may allow an authorized operator to issue a one-time account-
activation capability that permits the intended recipient to establish their
own canonical Guardian account credential without the operator knowing the
durable password.

### Guardian owns activation state

Guardian owns issuance, persistence, revocation, redemption, account creation,
password hashing, and audit provenance. No frontend, network perimeter,
provider, mail system, observability subsystem, or collaboration subsystem may
become a second account or credential authority.

Activation is represented by a dedicated purpose-specific durable record. It
is not an account-observability invite, collaboration invite, room invite,
session, or identity record.

### Issuance is operator-authorized and recipient-bound

Issuance requires a valid canonical Guardian operator identity with the
required administrative role. The durable capability records the creating
operator's canonical user ID.

Each activation is bound at issuance to:

- one normalized recipient email;
- one canonical intended role from the existing `admin` / `guest` vocabulary;
- the account-activation purpose only;
- one explicit expiry timestamp.

Issuance fails closed when the recipient already has a canonical account. A
recipient may not have multiple concurrently usable activations; replacement
requires explicit revocation of the prior usable capability rather than silent
rotation.

### The bearer is transient and one-way persisted

The raw activation bearer is generated from at least 256 bits of cryptographic
randomness and is URL-safe. The raw bearer is transient secret material. It may
be returned only to the immediate issuance caller and must never be persisted.

Guardian persists only a cryptographic one-way digest suitable for lookup,
along with bounded lifecycle and provenance metadata. The durable record uses
timestamps for expiry, revocation, and consumption rather than treating the raw
bearer as identity or durable state.

The raw bearer, token digest, password, password hash, and complete activation
URL must not appear in logs, audit rows, documentation, proof artifacts, or
other durable output.

### Activation is expiring, revocable, and single-use

Every activation expires. An authorized operator may explicitly revoke an
unconsumed activation while preserving its lifecycle history. Revocation does
not delete or repurpose the record.

Redemption row-locks the matching capability and fails closed when the bearer
is missing, malformed, unknown, expired, revoked, consumed, or otherwise
unavailable. Successful redemption records a consumption timestamp and the
resulting canonical user ID. Replay must fail.

Public callers receive one generic unavailable response for all unusable
capability states. The public surface must not disclose whether a bearer was
unknown, expired, revoked, consumed, malformed, or associated with an account
collision.

### Recipient identity and role are not redemption inputs

Redemption accepts only the raw activation bearer and the recipient-selected
password. It must not accept caller-supplied email, username, user ID, role, or
operator identity as account authority.

The normalized recipient identity and intended role come exclusively from the
persisted activation record. Existing-account collision fails closed.

### User creation and capability consumption are atomic

Successful redemption uses the canonical Guardian password-hashing facility to
hash the recipient-selected password. The canonical `User` is created only at
redemption, with the activation-bound recipient identity and role.

Canonical `User` creation, activation consumption, resulting-user linkage, and
bounded redemption audit provenance participate in one database transaction.
If user creation fails, the capability remains unconsumed. If capability
consumption fails, no partially created `User` may remain.

`User.password_hash` remains non-nullable. This decision creates no pending
`User` lifecycle and authorizes no nullable-password migration.

### Activation does not establish a session

The activation capability authorizes only credential bootstrap and canonical
account creation. Successful redemption does not mint a session, log the user
in automatically, or extend the bearer's authority.

After activation, the recipient authenticates through Guardian's existing
ordinary login path using the password they selected.

### Audit provenance is bounded and secret-free

Guardian records bounded audit events for issuance, revocation, and redemption
through the existing audit authority. Audit provenance may include the durable
activation ID, applicable operator/actor ID, resulting user ID, event type, and
bounded outcome metadata.

Audit provenance must exclude:

- raw activation bearers;
- token digests;
- passwords;
- password hashes; and
- complete activation URLs.

No parallel audit database is introduced.

### Initial delivery is manual and out of band

Until a separately governed transactional security-mail transport exists, the
authorized operator receives the activation URL exactly once for manual,
out-of-band delivery. The bearer is carried in the URL fragment so it is not
sent to the HTTP server as part of the initial page request.

The URL is not persisted and cannot be reconstructed from the one-way digest.
If the URL is lost or delivery is uncertain, the operator revokes the pending
capability and issues a replacement; Guardian does not re-display the original
bearer.

Future transactional security email may transport an activation capability,
but transport success and activation success remain distinct states. Email
transport requires separate governance and runtime proof before it becomes
current truth.

## Failure and trust boundaries

The principal trust boundaries are:

- **Operator boundary:** only an authorized canonical Guardian administrator
  may issue or revoke.
- **Recipient boundary:** possession of the bearer grants only one bounded
  activation attempt; recipient identity and role remain server-bound.
- **Browser/network boundary:** the bearer is removed from the visible URL and
  retained only transiently by the activation client; outer access controls do
  not become account authority.
- **Database boundary:** only the digest and lifecycle metadata are durable;
  row locking and transactionality enforce single-use account creation.
- **Transport boundary:** manual or future email delivery carries a capability
  but does not prove redemption, account creation, login, or session creation.

## Alignment

This decision aligns with and does not supersede:

- [ADR-005: Runtime Mode and Account Boundary Invariants](./005-runtime-mode-and-account-boundary-invariants.md);
- [ADR-039: Operator / User Access Boundary](./039-operator-user-access-boundary.md);
- [ADR-049: Admin Account Observability and Invite Attribution](./ADR-049-admin-account-observability-and-invite-attribution.md); and
- the [Remote Account Access and User Profile Contract](../remote-account-access-and-user-profile-contract.md).

ADR-049's account-observability invite remains acquisition attribution only.
This ADR reuses no observability invite record or authority.

## Implementation alignment and current proof boundary

The existing worktree slice implements the accepted boundary through:

- a dedicated `AccountActivationCapability` model and Alembic revision
  `a8d4c2f6b1e9`, based on `7e5a5fccf253`;
- Guardian activation token and lifecycle services;
- public redemption through the canonical auth router;
- a tester-runtime issuance/revocation CLI;
- a bounded `/activate` recipient surface.

Focused backend activation and PostgreSQL migration proof have been reported
for the slice. The following remain unproven by this ADR and deferred to a
separate proof task:

- frontend activation tests and browser behavior;
- existing authentication and tester-provisioning regressions;
- security sentinel inspection;
- disposable end-to-end runtime activation and replay;
- live tester runtime/profile/origin qualification; and
- real-recipient activation issuance.

No release or supported-path claim is widened.

## Consequences

### Positive

- The recipient, not the operator, chooses the durable password.
- Guardian remains the sole credential and account authority.
- Account creation cannot occur before successful recipient redemption.
- Digest-only persistence limits bearer disclosure after database compromise.
- Expiry, explicit revocation, row locking, and atomic consumption bound replay
  and partial-write failure.
- Existing login and session semantics remain unchanged.

### Negative

- Initial delivery is operationally manual and the URL cannot be recovered if
  lost.
- Operators must revoke and replace uncertain or lost activations explicitly.
- This slice does not solve account recovery, password mutation, or session
  invalidation.
- Live qualification remains a separate operational proof burden.

## Explicitly deferred

This decision does not authorize or implement:

- authenticated password change;
- forgot-password or password reset;
- account recovery;
- credential epochs or account-wide credential generations;
- revoke-all-session behavior;
- automatic login after activation;
- Gmail, SMTP, or transactional security mail;
- MFA or passkeys;
- Cloudflare identity integration;
- collaboration, social, Contacts, Circles, Spaces, or room-invitation
  semantics; or
- release-support expansion.

Any future change that broadens the activation capability's purpose, permits a
provider or perimeter to become account authority, introduces automated
security-mail transport, or adds credential/session invalidation semantics
requires separate architecture review and proof.

## Related documents

- [`00-current-state.md`](../00-current-state.md)
- [Account activation and invitation terrain](../inspections/2026-09-17-account-activation-invitation-terrain.md)
- [Remote Account Access and User Profile Contract](../remote-account-access-and-user-profile-contract.md)
- [ADR-005: Runtime Mode and Account Boundary Invariants](./005-runtime-mode-and-account-boundary-invariants.md)
- [ADR-039: Operator / User Access Boundary](./039-operator-user-access-boundary.md)
- [ADR-049: Admin Account Observability and Invite Attribution](./ADR-049-admin-account-observability-and-invite-attribution.md)
