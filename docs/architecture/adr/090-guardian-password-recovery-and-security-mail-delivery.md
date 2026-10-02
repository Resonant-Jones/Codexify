# ADR-090: Guardian Password Recovery and Security-Mail Delivery

**Status:** Proposed for human architecture review — 2026-09-25

## Context

ADR-088 governs first-password activation for a recipient who does not yet have
a canonical `User`. It explicitly defers password reset, recovery mail, and
account-wide session invalidation. A completed private-preview activation and
login for one admin account proves that one live path, not general recovery or
private-preview release support.

An existing account cannot receive another activation. Today an operator must
handle a forgotten password through a legacy credential-reset CLI. The current
`User.email` field has no verified-recovery-address state. Guardian's Redis
session store can revoke a specific token but has no account-wide revocation
primitive. The proposed user-owned Email product under ADR-047 is not a
transactional security-mail sender.

The first intended outbound sender is `support@resonantconstructs.ai`, which
the operator identifies as a Google Workspace send-as alias. Provider choice
must remain replaceable without changing Guardian recovery semantics.

## Proposed decision

Guardian owns a separate, purpose-bound password-recovery capability for an
**existing** account. It does not reuse an activation, invitation, Cloudflare
Access assertion, provider mailbox, or ordinary login session as recovery
authority. The first rollout is limited to the gated private-preview lane and
eligible guest accounts with a verified recovery address. Admin recovery needs
a separately accepted additional factor or operator procedure before enabling
unattended reset.

### Recovery address and authority

- A canonical Guardian account is the source of truth for the credential and
  recovery-address binding. `User.email` alone is not evidence that its owner
  controls the mailbox. Existing users must verify a recovery address while
  authenticated before self-service recovery becomes eligible.
- Changing a recovery address requires an authenticated account action and
  verification of the new address. An unverified change does not redirect
  reset mail. Shared aliases require explicit ownership policy before they
  can serve as recovery addresses.
- Cloudflare Access remains an outer admission gate. It neither issues reset
  capabilities nor grants Guardian account ownership. A recipient must still
  pass that gate to open the reset page in private preview.

### Request and redemption

1. `POST /api/auth/password-reset/requests` accepts an email and returns the
   same public response for eligible, unknown, ineligible, and rate-limited
   accounts. It makes no credential or session change.
2. For an eligible existing account, Guardian creates one active reset
   capability and one encrypted mail-delivery job in a single PostgreSQL
   transaction. A replacement request revokes the prior active capability.
   Request rate limits prevent repeated requests from making mail or links
   unusable as an abuse tactic.
3. The recipient receives a fixed-origin HTTPS link to `/reset-password`.
   The browser captures the bearer from the URL fragment and removes the
   fragment from browser-visible history before submitting it to Guardian.
   The page sets `Referrer-Policy: no-referrer` and loads no third-party assets
   that could receive a bearer.
4. `POST /api/auth/password-reset/complete` accepts the bearer and a new
   password. Guardian locks the capability and account row, verifies purpose,
   account binding, expiry, revocation, and single-use state, then hashes the
   password, consumes the capability, increments the account credential
   generation, and writes bounded audit provenance in one transaction.
5. Redemption does not create a user or a login session. The user signs in
   normally with the new password. A separate notification reports the
   credential change without including a bearer or password.

The reset bearer has at least 256 bits of random entropy, expires after 30
minutes, and is stored in its capability record only as a digest. The public
error for invalid, expired, revoked, and consumed links is generic. The
configured link origin is never derived from a request `Host` header.

### Encrypted delivery outbox

Guardian defines a narrow `SecurityMailSender` interface that accepts a
named security template, a Guardian-selected recipient, a stable delivery ID,
and bounded template data. A frontend or general-purpose agent cannot choose
an arbitrary recipient, message body, or bearer. The first adapter uses the
Gmail API with a sending principal authorized for the accepted
`support@resonantconstructs.ai` send-as alias. Its permission is limited to
sending; it must not require inbox-reading or domain-wide delegation. A
provider-neutral configuration selects the adapter.

The outbox stores the recipient and rendered reset link only in a short-lived
AEAD-encrypted payload. Its visible columns contain a capability reference,
purpose, delivery state, bounded attempt schedule, key version, and
non-secret provider receipt metadata. The encryption key is separate from
Guardian's session-signing secret, held by the backend secret boundary, and
versioned for rotation. Associated data binds the ciphertext to the
capability ID, purpose, and expiry. Raw bearers, full URLs, passwords,
plaintext mail payloads, and encryption keys are excluded from ordinary logs,
audit rows, errors, traces, and proof artifacts.
An old key version remains available only until its outstanding ciphertext is
purged; a new key version is used for new jobs.

The capability and encrypted outbox row commit together. A bounded delivery
worker sends only committed jobs. Retry uses the **same** capability and
encrypted payload; it never mints a new bearer. Delivery status distinguishes
`pending`, `accepted_by_provider`, `retryable`, `outcome_unknown`, and
`permanent_failure`. Provider acceptance does not prove inbox delivery.
An ambiguous provider outcome may cause duplicate messages carrying the same
link; the design makes no exactly-once mail claim. A consumed, revoked, or
expired capability is never delivered again. Ciphertext is deleted after
provider acceptance or terminal expiry/failure; only bounded, secret-free
delivery receipts remain. A user can request a replacement within rate limits
if a message is lost.

### Session invalidation

Add an account credential generation with a migration default for existing
users. A newly issued session records the generation, and every private-
preview session resolution compares it with the canonical account value.
Reset increments the value in the password-change transaction, making earlier
sessions unusable even while their Redis entries await TTL expiry. A failed
generation lookup fails closed. The implementation must audit every preview
session resolver so no signed-token or cookie fallback bypasses this check.
The existing session behavior of other runtime modes is not changed by this
proposal without separate qualification.

### Abuse and failure boundaries

- Apply bounded limits by source and normalized account identifier without
  exposing account existence through response content or timing.
- Never change an account merely because reset mail was requested or accepted
  by Google. Mail delivery can be delayed, duplicated, rejected, or unknown.
- If encryption is unavailable, create neither capability nor outbox job and
  return the generic public response. If the provider is unavailable after
  encrypted commit, retain bounded retryable state. Never fall back to an
  unencrypted mail queue or return the link in an HTTP response.
- Verification and reset links are distinct purposes and cannot redeem each
  other. Account deletion, loss of allowlist eligibility, or loss of verified
  recovery-address binding makes outstanding reset links unusable.
- Keep the legacy operator reset path as a documented exception until a
  separately proven recovery alternative exists for ineligible accounts.

## Proof required before rollout

- PostgreSQL clean-start, existing-instance upgrade, rollback posture, row
  locking, atomic redemption, and concurrent/replayed-token evidence.
- Secret-safety checks across schema, logs, errors, worker retries, provider
  responses, audit rows, and browser URL handling; key rotation and missing-key
  failure checks.
- Generic request responses and rate-limit checks for known, unknown,
  ineligible, and removed accounts.
- Verified recovery-address enrollment and denial for unverified/shared
  addresses; guest and admin negative controls.
- Session rejection across every preview bearer/cookie resolver after reset,
  including sessions issued before the migration.
- Gmail send-as readiness, provider acceptance, ambiguous outcome, retry,
  duplicate delivery, and ciphertext-purge evidence in an isolated runtime.
- A real private-preview recipient proof through request, mail receipt,
  redemption, old-session rejection, and normal login. This does not by
  itself widen public Beta support.

## Alignment and current-truth boundary

This proposal extends [ADR-088](./088-guardian-account-activation-and-credential-bootstrap.md)
without changing activation semantics. It preserves Guardian credential
authority under [ADR-005](./005-runtime-mode-and-account-boundary-invariants.md)
and the [Remote Account Access and User Profile Contract](../remote-account-access-and-user-profile-contract.md).
It does not implement or depend on the user-owned correspondence system of
[ADR-047](./047-codexify-email-routing-identity-mailbox-governance-provider-adapter-contract.md).
The [current-state document](../00-current-state.md) remains the release gate.

This document is **proposed architecture only**. It authorizes no schema,
mailbox, Google Workspace, secret, runtime, or release change until human
review and separately scoped implementation work.

## Human decisions before acceptance

1. Confirm the guest-first scope and the additional factor or operator path
   required for admin recovery.
2. Confirm recovery-address verification and treatment of shared aliases.
3. Confirm the service-owned Google sending principal and that the
   `support@resonantconstructs.ai` send-as alias is accepted for that principal.
4. Confirm encryption-key custody and operational rotation for the local
   private-preview host.

## Reference guidance

- [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
  informs generic responses, token handling, rate limits, and fixed-origin
  links; this proposal does not assert compliance by citation alone.
- [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html)
  informs recovery-address verification and recovery notification; the
  private-preview authentication assurance level is not classified here.
- [Google Gmail API send-as aliases](https://developers.google.com/workspace/gmail/api/guides/alias_and_signature_settings)
  distinguishes an accepted alias from one pending verification.
- [Google Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)
  identifies the send-only scope for the first adapter.
