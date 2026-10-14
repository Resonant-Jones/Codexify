# Scout #815 canonical account handoff decision

Status: approved hosted composition; integration source transplants the proven
architecture into current main without importing the historical backend branch.

Guardian/Vault remains canonical account, ownership and durable-state authority.
Cloudflare Access admission never creates a Guardian user or account session.
`connection = endpoint/transport + explicit authentication mode`.

## Approved transport and issuance

- Hosted Scout uses the registered public native OAuth client and S256 PKCE in
  ASWebAuthenticationSession. It sends Access in Authorization; the independently
  qualified edge consumes that Authorization before reaching Guardian.
- Guardian accepts `X-Guardian-Account-Session` only on the exact preview host,
  in private-preview mode, with one cryptographically validated upstream Access
  assertion for the fixed issuer/application audience. Missing Authorization alone
  grants no trust. Access bytes are never reconstructed or moved to another header.
- The existing canonical browser account login requires explicit Continue to
  Scout. A fixed-callback, origin-bound S256 grant expires within 60 seconds and
  is consumed atomically. Redemption revalidates browser credential purpose,
  live session mapping and canonical account eligibility.
- Guardian's existing issuer/store creates a fresh independent exact-purpose
  `account_session` for the same canonical user. Browser token bytes are never
  returned. Native nonce, expiry, storage and logout/revocation are independent.
- The alternate header is transport for this existing credential class, never
  a new authority. Current-main account validators and durable task/thread access
  retain authority. Conflicting selectors, revoked/invalid/wrong-purpose material
  and unqualified ingress fail closed with no key/cookie/guest/operator fallback.
- Personal HTTPS nodes retain explicit supported auth selection, account Bearer
  where supported or explicitly chosen local API key. Tailscale is transport,
  not identity. No hosted paid-service account is required for one's own node.

## Client lifecycle and evidence

Credentials remain in separate profile/origin Keychain records. Secret-free
configuration cannot authorize a request; missing or expired sessions fail before
protected dispatch. Wrong-origin requests and redirects cannot receive credentials.
A marked account failure clears only that account credential; unrelated operator
401 responses do not indiscriminately revoke a valid session. Logout removes the
local credential and requests canonical server revocation.

[ADR-092](../../docs/architecture/adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md)
governs purpose/mixed-principal enforcement and the approved hosted transport.
The separate backend integration carries its amendment; no new credential class,
database schema, migration, ownership, account provisioning or Access policy is
introduced by these integrations.

[October 4 live evidence](SCOUT_LIVE_CONTINUITY_2026-10-04.md) records the nine-stage
sign-in, two persisted turns, task events, documents, resume and logout denial on
the source branches and preserved runtime. It is historical evidence, not a claim
that a newly integrated build was live-authenticated.
[The integration receipt](SCOUT_MAINLINE_INTEGRATION_815.md) records fresh tests and
builds. Personal-node live continuity, the final physical iPhone loop and deliberate
failed/cancelled live tasks remain unproven. Release support remains separately gated.
