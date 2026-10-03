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

- PUT/GET `/api/auth/scout/qualification/{identity}` require the existing signed
  Access admission and native opaque Bearer composition; account/key/cookie
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
