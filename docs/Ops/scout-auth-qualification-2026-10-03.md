# Scout authentication qualification — 2026-10-03

Architecture-impact lane, aligned with ADR-092. Guardian remains canonical
account authority; this adds diagnostic evidence only, with no new credential,
principal, account provisioning, ownership, approval, schema or Access policy.
The VaultNode account audit is complete and is not repeated by this surface.

Scout Settings shows nine independent stages: ingress credential availability,
system browser launch, canonical browser account confirmation, native callback
receipt, state validation, handoff exchange acceptance, fresh native issuance,
profile/origin Keychain save plus readback, and account-header thread read.
Passed evidence is monotonic for this attempt. An observed failure is displayed
separately from earlier unobserved stages. Profile changes cancel/supersede the
operation and discard its receipt. A check of an older stored session cannot
qualify the new attempt's issuance or storage.

A random public UUIDv4 is independent of OAuth state, challenge, code, verifier
and session. It travels as `scout_attempt` on the fixed browser URL and as
`X-Scout-Auth-Attempt` on login, handoff, exchange and the native protected read.
Callback parameters remain exactly code/state; the public ID is not authority.

The existing Scout auth router owns these hosted-only diagnostic routes:

- PUT/GET `/api/auth/scout/qualification/{identity}` require the existing scoped
  signed Access admission and the qualified edge-consumed composition (or one
  opaque Access Bearer when forwarded); account/key/cookie
  selectors cannot substitute for it. PUT registers evidence, not a session.
- POST `/api/auth/scout/qualification/{identity}/browser` requires same-origin
  hosted admission. Browser loaded is observation only. Account confirmation
  invokes the existing strict canonical account validator; UI readiness alone
  cannot confirm a user. This route issues no session or grant.

Receipts are process-local, capped at 128, and expire after ten minutes from
registration. Retries cannot extend retention. Restart, timeout, expiry or a
missing receipt means evidence unavailable, not invalid authentication. They
contain only a public ID, fixed stage/status enums and numeric HTTP status.
They contain no user identifier, credential or callback query value. Headers
are no-store/no-referrer. Arbitrary validation inputs are never reflected.
Backend logs use only the existing safe request_id/event_type/status/http_status
fields. A successful login is recorded only after canonical issuance succeeds;
fresh native issuance only after its independent session-store write succeeds;
protected read only after selected account validation and the actual response.
These fixed diagnostic labels remain local to this qualification contract;
they are not queue/task events, credential purposes or release status tokens.

Scout polls the receipt while its system browser is open, validates the callback
locally, requires the server's fixed fresh-issuance boolean header, validates and
saves the native session, checks exact Keychain readback, then immediately reads
`/api/chat/threads` through the shared account selector with
`X-Guardian-Account-Session`. No cookie, API key or alternate-origin fallback is
introduced. Diagnostic messages never interpolate an error, URL or response body.

Validation: complete SwiftPM suite, canonical signed proof-simulator build,
LoginPage regression suite/Vite build, integrated Scout handoff/transport/mount,
strict-purpose/operator and no-seed suites, plus safe receipt/correlation tests.
Deployment retains direct Uvicorn and `CODEXIFY_SKIP_STARTUP_SEEDING=1`, and
recreates only preview backend/frontend and the origin proxy with its bounded
logging override. The origin keeps its existing conf.d routing and access policy;
the main log records only method, query-free URI, protocol and HTTP status. Raw
nginx error logging is disabled during this window because it can include the
request/referrer. Safe HTTP status and Guardian stage logs remain available.
Removing the isolated main-config mount restores the prior origin logging. Existing workers, database volumes,
Cloudflare, BIC and public OAuth registration are preserved. Source/build/install
proof does not establish an authenticated native handoff or full #815 continuity.

Live proof remains pending one operator sign-in, then thread/message/completion,
task events, persisted output, resume, documents and native logout/denial. Do not
start #816–#818 before the full #815 loop is proven.

Source qualification: 57 SwiftPM tests, signed proof-simulator BUILD SUCCEEDED,
78 integrated backend tests, 16 browser tests and Vite build passed. Canonical
login body AST is identical to its previous implementation. The managed-shell
simulator build could not reach CoreSimulator; the host lane succeeded. No
automated test claims operator sign-in or live continuity.

Commit hooks: isort made one nonsemantic import-format change, which was retained
and revalidated. Mypy reports three previously recorded errors in untouched
`guardian/agents/coding_agent_contracts.py` and `guardian/watchdog/contracts.py`.
It reports no error in the five checked files for this slice. The scoped commit
retry skips only that existing failing hook; no clean repository-wide type-check
claim is made. Other applicable hooks, including secrets and Bandit, passed.

## Runtime and installation checkpoint

Backend/browser source commit: `f231ef3cfd13b577bfe033209735c4468ee13313`.
Scout source commit: `3f6d1cdcd2a5bbd23160748cd0f002d6dae41b2c`.
Serving image: `sha256:579c15b3b31b74ac3feef814ced96af8595c4a3f289f0b955ef8bbf6b0a61291`.
Qualified base: `sha256:f9e7f5ff1e69d03a4f626bdbf99ff6ba032687f7f374517ed1f05a565a99a158`.
Artifact: `/Volumes/Dev_SSD/Codexify-scout815-auth/f231ef3cf-r2` on VaultNode.

Build uses the existing local base tag after checking that exact image hash;
passing a bare sha256 value to FROM was interpreted as a registry name and the
first build stopped before application startup. The corrected build runs with
pull disabled and networking disabled. Syntax/hash inspection runs read-only
without application startup. Forward and rollback Compose configurations preserve
all unrelated services, environment, durable volumes and networks. nginx syntax
passes against its existing routing config and network.

Only preview backend, frontend and origin were recreated, without dependencies,
build or pull. Serving backend bytes match the source at both package mounts;
both frontend files and nginx config match. Guardian is healthy with the approved
direct Python/Uvicorn command, skip-seeding flag and exactly one safe suppression
marker. Origin health/login return 200; anonymous account and qualification reads
return 401. A synthetic query canary is absent from new origin logs; its safe
query-free GET /login status is present. No account login was submitted by the
agent during qualification.

Immediately before/after restart, schema revision `a7b9c4d2e6f1`, schema hash and
all ten table count/fingerprint pairs are identical. Eighteen other service
identities, start times, image IDs and configuration hashes are identical,
including preserved workers and the independent chat proof stack. No migration,
seed, account provisioning/reset, password, role, approval or Cloudflare mutation
was performed.

The signed Scout build was installed in the existing proof Simulator without
uninstall/reset or Keychain/data removal and launched successfully. Device Hub's
actual Settings accessibility tree shows all nine qualification rows, initially
Waiting/pending. Installation proves the UI surface, not account authentication.
The operator was asked for one secure Guardian sign-in; native issuance, protected
read, full continuity and logout/revocation remain pending its result.

Rollback: use the artifact's compose.scout-rollback.yml with the existing base and
private-preview Compose files and the same bounded three-service command. It
restores the previously qualified application auth bytes while retaining safe
origin logging during the proof window. No database downgrade is involved.

## Native admission rejection classification

After native ingress renewal, the qualifier returned HTTP 400 before browser
launch. Its fixed response identified native admission rejection. The qualifier
now exposes only a fixed `X-Scout-Qualification-Rejection` enum on that existing
rejection: missing/ambiguous/unsupported Authorization or conflicting selectors.
No header value, cookie, credential, identity or callback data is reflected.
The accepted request predicate and signed Access validation are unchanged.
Five new rejection tests join the integrated **83 passing backend tests**.
This is diagnostic evidence; it does not admit a previously rejected composition.

The updated route diagnostic is deployed as two read-only route mounts on the
same image, recreating only backend with the existing no-seed direct command.
Serving hashes/health/anonymous denial pass, and nineteen other services plus
schema and all ten preserved table fingerprints are unchanged. Public native
attempt `f559214a-652f-4557-ad99-d6d5f8f5bae7` reports stage 1 passed and stage 2
`nativeAuthorizationMissing` HTTP 400, before browser launch. The existing signed
Access checks passed, but Guardian received no Authorization header. The current
admission predicate remains unchanged and fails closed. The separate
[bounded transport proposal](scout-edge-consumed-access-proposal-2026-10-03.md)
is prepared for operator approval; its authentication amendment is not applied.

## October 4 — approved edge-consumed composition

The operator approved the bounded amendment and withdrew the requirement that
the opaque Access Bearer reach Guardian on this qualified hosted composition.
ADR-092 is amended. The qualifier, exchange and account adapter retain mandatory
exact-host/private-preview/signed-assertion admission, fixed issuer/audience,
signature/expiry and duplicate/conflict checks before recognizing absent
Authorization. A forwarded Authorization remains single opaque Access Bearer.
Absence alone is never trusted, and no Access credential moves to another header.
Canonical account purpose/session/user/approval, PKCE parent revalidation and fresh
independent native issuance remain decisive. Personal Bearer behavior is unchanged.

Fixed response observation `X-Scout-Access-Admission` permits Settings to report
“Access admitted / Authorization edge-consumed” as admitted rather than failed.
It carries no credential, principal or authority. The client accepts that fixed
label only from HTTP 200 at its exact qualification origin/path/attempt.
**100 backend tests, 62 SwiftPM tests, 16 browser tests, Vite build and signed
Simulator build pass**. Deployment and live native sign-in/continuity remain
unproven at this source checkpoint; no infrastructure/account/database change ran.

### October 4 deployment checkpoint

Backend transport/ADR commit: `5836ed986e4cc6175b5184fe6b5d2fb23a989ed1`.
Scout diagnostics commit: `ae6855b721dbbe0f0fff6148285a9a7bcd1d7341`.
VaultNode artifact: `/Volumes/Dev_SSD/Codexify-scout815-auth/5836ed986-edge`.
The serving image remains
`sha256:579c15b3b31b74ac3feef814ced96af8595c4a3f289f0b955ef8bbf6b0a61291`.
Only four read-only mount sources changed: the route and transport files at
their Guardian and compatibility package locations. Both route hashes are
`424bd8f3eff1aed8f06bae5d24cbd00df30bce38570e987eeb2b87e1eff864ec`;
both transport hashes are
`206d3df4cd8aca3a5043fc09818a9d648a51f0dd00a1a723c67d4a84127c832a`.
Running bytes match. Full resolved Compose comparison in memory confirms those
four source changes are the only configuration delta. Syntax/hash validation
ran in the same image with no network, read-only files and no application startup.

Only backend was recreated, with no dependencies, build or image pull. Its
existing direct Python/Uvicorn command and skip-seeding flag remain active;
exactly one safe suppression marker appears. Backend is healthy. Origin
`/health` returns 200; an anonymous `/api/chat/threads` read returns 401.
Schema revision `a7b9c4d2e6f1`, schema fingerprint and all ten preserved table
count/fingerprint pairs are identical before and after. All 29 other running
service identities, start times, images and configuration hashes are unchanged.
No migration, seeding, account or external-access operation ran.

The artifact's `compose.scout-rollback.yml` retains the immediately preceding
qualified runtime configuration. Applying it with the existing base/private-preview
Compose files and the same backend-only/no-dependencies/no-build/no-pull command
restores prior source mounts without any database operation.

The signed Scout build was installed and launched in the existing proof Simulator
without uninstall/reset or profile/Keychain removal. Its actual Server screen
requests Guardian sign-in; this is installation proof, not authentication proof.
Device Hub AX inspection works, but coordinate input returns `noWindowsAvailable`.
The operator was asked to use Settings, check stored ingress, complete one Guardian
sign-in and return to Scout. Native admitted state, issuance, protected read and
full continuity/logout remain pending the live attempt.

Commit hooks retained one isort import-order change; the affected mounted-route
tests were rerun and both pass. The current mypy hook reports five errors in three
untouched files: two in coding_agent_contracts.py, one in watchdog/contracts.py,
and two in routes/imprint.py. Those files match starting HEAD. The scoped commit
skips only mypy; all other applicable hooks pass. No repository-wide clean
type-check claim is made.

### October 4 native preflight recovery

Attempt `b3467715-a301-468b-8ee4-101a5c086aa6` stopped locally at ingress
availability with `credentialMissing`; every later stage was unobserved.
No corresponding browser/account/handoff event reached the backend. The existing
Check stored ingress action subsequently reached Guardian's account gate with
HTTP 401, Cloudflare Ray `a456c0e6dcb7d941-MIA`. This is Access admission only.

New attempt `d0d1f7bd-7ba3-4710-9b0a-49ccad8a4938` passed ingress availability
and the amended native qualification preflight, then launched its system browser.
The standard sign-in Continue prompt was accepted. The backend's bounded event
records `browser_loaded / passed / HTTP 200` for that public ID. This proves
browser arrival; it does not prove canonical account login, callback, exchange,
native issuance, Keychain storage, protected account read or continuity. The
operator was handed the open browser for the one Guardian account sign-in.
