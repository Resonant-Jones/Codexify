# Scout #815: account handoff decision

Status: proposal awaiting operator decision; no new auth route or transport is deployed.
Date: 2026-10-02.

## Proven checkpoint

Operator-supplied Device Hub evidence at 16:51:45 UTC shows the installed Scout
simulator reporting that its native request reached Guardian's account gate:
HTTP 401, Cloudflare Ray `a4453689ff3df8ae-MIA`. The installed classifier requires
`X-Guardian-Auth-Failure: ACCOUNT_SESSION_INVALID`; HTTP 401 alone cannot produce
this result. This is operator-observed native admission evidence, not an
authenticated Guardian read. No credential, callback, or response body is recorded.

The current serving source on VaultNode was re-read via its configured SSH alias:
`/Volumes/Dev_SSD/Codexify-main`, revision
`f83fe5da326871d1948ba79d90831be1402375ec`. Its canonical login issues
`purpose=account_session` for the existing `User.id`, stores the session mapping,
and returns its expiry. Its account extractor selects Authorization Bearer before
`gc_session`. No browser-to-native handoff route exists in the inspected auth seams.
Scout's branch predates ADR-092 and must not deploy its older purpose-less issuer.

## Decision required

The original goal requires an account Bearer header. Native Cloudflare admission
is currently qualified using an Access Bearer in that same header. Two tokens
cannot occupy that field. Cloudflare's documented opaque Managed OAuth token is
not a downstream Access JWT; its linked-app header mechanism does not establish
that the opaque token can be moved to `CF-Access-Token`.

Recommended amendment: for the hosted profile only, retain the qualified Access
Bearer and carry the separately issued account session in a dedicated
`X-Guardian-Account-Session` header. Personal nodes without this ingress keep the
canonical account Bearer path. Both transports feed the same strict account
validator, canonical user resolution, approval checks, expiry and revocation.
No Access identity becomes a Guardian account; no API key is introduced.

This adds a supported account transport and needs an ADR-092 amendment, not an
inline parser exception. Approval must explicitly amend the original Bearer-only
acceptance criterion for the hosted composition. No new OAuth client or policy
is proposed. Do not deploy or assume this amendment is approved from this document.

## Bounded implementation after approval

1. Add one browser-to-native handoff to the existing Guardian/web login. Scout
   opens a same-origin page with a PKCE S256 challenge and random state. The page
   uses the existing canonical account login and clearly confirms transfer of
   that account session to Scout; Google/OTP remains the separate Access gate.
2. An authenticated account creates a short-lived (at most 60 seconds), single-use
   opaque handoff code bound to its exact account session, PKCE challenge, fixed
   Scout callback and initiating state. Store the grant in existing Redis, with
   no database migration. Use atomic consume after verifier checks; replay,
   expiry, revocation, missing/wrong verifier and wrong origin fail closed.
3. Redirect only to the fixed Scout callback with code and state, never a session
   token. Do not accept arbitrary callback destinations. Redact callback queries
   and handoff bodies in every proxy/application diagnostic; send no-store and
   no-referrer responses. Do not save codes/verifiers in documents or logs.
4. Scout validates callback and state, exchanges the code with the verifier over
   its fixed origin using the qualified ingress credential, then stores only the
   returned canonical account session in a separate profile/origin Keychain
   record. The exchange must revalidate the bound session, account and expiry.
   It must not issue account ownership from a Cloudflare assertion.
5. Define explicit credential selection before validation. The dedicated header
   always selects the account lane; invalid header credentials never fall back
   to Bearer/cookie/key. Reject conflicting account transports and guest/operator
   credentials under ADR-092. Preserve every account consumer (thread/message,
   task events, documents, logout and user-scope resolution), not just one read.
   Keep operator and guest handlers unchanged and reject inappropriate material.
6. Complete Scout's shared remote-session selector, per-profile credentials and
   volatile state, account restoration/expiry, marked invalid-session handling,
   logout/revocation and reauthentication. No X-API-Key or anonymous fallback.
7. Validate purpose, mixed-lane rejection, PKCE replay/origin protection,
   route coverage, expiration/logout, profile isolation and no-secret diagnostics.
   Run complete SwiftPM tests, canonical simulator build, then protected account
   reads and the entire #815 continuity loop through Scout.

Expected seams: Guardian auth routes, account credential extraction/dependencies,
session store and neighboring tests; frontend login/router/API seams; Scout
shared authentication selector, Keychain store, lifecycle/views/tests; ADR-092
and Scout docs. Backend work must be separately reviewable against the qualified
serving revision, not a broad merge of main into the older Scout branch.

## Deployment approval boundary

The restoration approval authorized the pinned existing application revision,
not this new authentication deployment. Approval for this proposal must include
building and deploying only its reviewed Guardian/frontend changes to the
existing preview after tests pass, with the current schema and preserved data.
Require no migrations, seeds, access policy changes, new registration, DNS,
Tunnel, BIC changes or account/ownership mutations. Stop for any such requirement.
Rollback is the pinned application image; revoke unused transient handoff grants.
Do not downgrade or replace the preserved database.

Ingress admission has passed. Guardian handoff, protected authenticated reads,
remoteSession and full continuity remain incomplete; #815 cannot close and
#816–#818 remain deferred.

Sources: serving ADR-092, `guardian/routes/auth.py`,
`guardian/core/auth_dependencies.py`, `guardian/core/dependencies.py`;
[Cloudflare Managed OAuth](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/) and
[linked-app limitations](https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/linked-apps/).
