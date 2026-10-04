# Scout upstream Authorization mismatch — approval proposal

Status: evidence recorded; transport amendment **not implemented or deployed**.
This document requests no account, database or Cloudflare change by itself.

## Verified runtime evidence

Scout's existing ingress refresh succeeded and reached the Guardian account gate
with HTTP 401, Cloudflare Ray `a44fd999ca5b67cf-MIA`. The native receipt request
explicitly supplies the renewed ingress credential in Authorization and uses an
ephemeral session without cookies, credential storage or redirects.

Installed Scout source `07da312dcd8dbe10b6c86b7bd4f220f29044f646` made public
attempt `f559214a-652f-4557-ad99-d6d5f8f5bae7`. Stage 1 passed. Stage 2 failed
before browser launch with `nativeAuthorizationMissing`, HTTP 400. This fixed
classification comes from deployed route source
`770cd80ea5b963d89d782b0835f1bc1012d9c0c2` only after the existing hosted
composition and signed Access assertion checks pass. It means Guardian received
zero Authorization headers. No header value was collected or reported.

The observation identifies an upstream header mismatch. It does not establish
which individual upstream component consumed the header. No Guardian browser
credential submission, callback, exchange, native issuance or protected account
read occurred in this attempt.

The diagnostic deployment recreated only preview backend, using the unchanged
image `sha256:579c15b3b31b74ac3feef814ced96af8595c4a3f289f0b955ef8bbf6b0a61291`.
Only its two route source mounts changed. Direct Uvicorn and
`CODEXIFY_SKIP_STARTUP_SEEDING=1` remain active; exactly one safe suppression
marker appears. Serving route hashes match, backend is healthy, health returns
200, and anonymous account read remains 401. Nineteen other service identities,
start times, images and config hashes match. Schema `a7b9c4d2e6f1`, schema hash
and all ten preserved table count/fingerprint pairs match before/after.

Artifact: `/Volumes/Dev_SSD/Codexify-scout815-auth/770cd80ea-shape` on VaultNode.
Rollback uses its `compose.scout-rollback.yml` and the existing base/preview
Compose files, recreating only backend with no dependencies, build or pull.
It restores the previous diagnostic route mounts without a database downgrade.

## Exact approval boundary

ADR-092 currently requires a signed Access assertion **and** an opaque Access
Bearer at Guardian for the hosted Scout adapter. The same shape is required by
the native qualification and handoff exchange routes. The live upstream path
does not deliver the latter header. Keeping that predicate correctly fails
closed, but cannot complete the native flow.

## Smallest proposed correction

Amend only the qualified hosted Scout composition to recognize the observed
edge-consumed shape. Scout continues sending its existing Access OAuth Bearer
in Authorization; no new credential, header, registration or authorization path
is added to the client.

1. Keep private-preview mode, exact `preview.codexify.space` host/port, one Host
   and one Access assertion, fixed issuer/application audience, signature and
   expiry validation, and the existing explicit account-route allowlist.
2. At Guardian, permit zero Authorization headers only after those signed Access
   checks succeed. If Authorization is present, require the existing single
   opaque Access Bearer shape. Reject duplicates and other Bearer forms.
3. For qualification/exchange, continue rejecting account headers, API keys,
   Guardian keys and account/guest cookie selectors. Exchange still requires
   the single-use, origin-bound, 60-second S256 handoff, revalidates its canonical
   browser account, and issues a fresh independent canonical account_session.
4. For account APIs, continue requiring exactly one
   X-Guardian-Account-Session, rejecting all conflicting selectors, and sending
   its bytes through the existing exact-purpose/stored-session/canonical-user/
   account-approval validator. Access identity never becomes Guardian identity.
5. Personal Bearer sessions and explicit local API-key mode remain unchanged.
   No fallback, cookie export, browser-token reuse or extra route is permitted.

Affected implementation seams: `guardian/core/scout_account_transport.py`,
`guardian/routes/scout_auth.py`, their existing identity tests, and the qualified
hosted paragraph in ADR-092. No Cloudflare, BIC, OAuth registration, account,
password, role, ownership, database, migration or seed operation is proposed.

Before deployment, require positive proof for signed edge-consumed admission and
negative proof for absent/invalid/expired/wrong-issuer/wrong-audience assertions,
wrong host/mode/route, duplicate headers, conflicting selectors, invalid account
purpose/session, and invalid/replayed handoff. Re-run integrated auth tests and
retain the qualified no-seed startup/rollback/data-preservation checks. Then
resume the one Guardian sign-in and complete #815 continuity/logout proof.

This proposal does not grant approval and does not claim authenticated continuity.
#816–#818 remain deferred.
