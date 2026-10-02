# Scout account handoff qualification — 2026-10-02

Base: f83fe5da326871d1948ba79d90831be1402375ec, the serving VaultNode revision.
This patch is separately reviewable from the older Scout client branch. It adds
no migration, seed, account ownership, Cloudflare, OAuth registration or BIC change.

The approved X-Guardian-Account-Session header transports unchanged canonical
account-session bytes only at preview.codexify.space in private-preview mode.
It requires an opaque Access Bearer plus a signed upstream Access assertion with
the fixed team issuer/application audience. Conflicting credentials fail closed.
The adapter supplies those account bytes to existing strict validators; Access
claims never create or select a Guardian principal. Personal Bearer behavior is
unchanged. Operator and guest routes cannot use this alternate transport.

After existing web account login, explicit Continue to Scout creates a Redis
handoff grant with 60-second TTL, random single-use code and S256 challenge.
Native redemption atomically consumes only a matching verifier, revalidates
account purpose, live session mapping and preview eligibility, then returns the
same session and expiry. The callback is the already registered Scout callback.
Malformed requests cannot echo codes/verifiers through validation errors. Tokens
and Access assertions are redacted from diagnostics.

Validation before deployment:

- 57 tests passed: Scout transport/store/routes, actual app mount without lifespan
  startup, existing strict-purpose and frozen operator route regressions.
- Command: CODEXIFY_CONFIG_SOURCE=core CODEXIFY_DISABLE_DOTENV=1
  CODEXIFY_EMBEDDINGS_BACKEND=mock GUARDIAN_API_KEY=<synthetic test fixture>
  python -m pytest -q tests/identity/test_scout_account_transport.py
  tests/identity/test_scout_handoff.py tests/identity/test_scout_handoff_routes.py
  tests/identity/test_scout_app_mount.py
  tests/identity/test_account_purpose_strict_migration.py
  tests/identity/test_operator_route_auth_migration.py --confcutdir=tests/identity.
- Python test environment uses the serving image's FastAPI 0.119.1, Starlette
  0.48.0, Pydantic 2.12.3, PyJWT 2.15.1 and cryptography 46.0.3. An earlier newer
  FastAPI run failed route enumeration also under unchanged baseline source;
  aligning runtime dependencies resolved that failure without application changes.
- LoginPage trustedRemote Vitest suite: 13 passed; Vite build passed.
- Black/isort checks of new Python modules and git diff --check passed.

No deployment or live authenticated handoff/read/continuity claim is established
by these tests. The existing preserved database and preview ingress remain
unchanged. Deployment must retain qualified base-image bytes and scoped source
mounts, and touch only preview backend/frontend, leaving concurrent proof stacks
and all worker/database volumes alone. Rollback uses the prior image and original
source mounts without database downgrade.

Commit-hook qualification: Black/isort required formatting of the touched app/log
modules; changes are nonsemantic. Security, secret detection, Bandit and the other
hooks passed. The repository-wide mypy import graph reports five pre-existing
errors in untouched coding_agent_contracts.py, watchdog/contracts.py and
routes/imprint.py. No Scout handoff module errors were reported. That unrelated
hook is excluded from the scoped commit retry and remains a recorded limitation;
this patch does not claim a clean repository-wide type check.

## Bounded preview deployment receipt

Auth source commit: 465497b0cca24dff5551433d9bb5139423a6d004.
The built image adds only the reviewed Guardian files to the qualified base
sha256:0f842ac1f9f8fec04af74b253f831aeb872644cbfbb58b839fd25eea37756649.
Serving image: sha256:c85760cf456e9a09a12983642a1fd6f4f1817903acb86ea3b3791134a84673d5.

Image syntax/hashes were checked in a read-only, network-disabled disposable
container without production mounts or application startup. The existing Compose
configuration plus scoped auth override passed config --quiet. Only preview
backend/frontend were recreated with --no-deps --no-build --pull never. Specific
read-only source mounts account for the existing Guardian/frontend bind mounts;
no main-checkout files, workers, database volumes or concurrent proof stacks were
replaced. The initial duplicate-shell frontend command exited without serving;
using the existing shell entrypoint corrected it. Both preview services now run.

The serving Guardian auth files match the committed patch hashes; serving
LoginPage SHA256 is 4852a8de441eef4672c864e28c51baa43b95ea5897cadab0810b2fce3f6a8597.
Preview origin 127.0.0.1:8081 returns health/login HTTP 200. An unadmitted Scout
exchange returns 401. Public Access verification keys are reachable from Guardian
(HTTP 200). DB revision remains a7b9c4d2e6f1; no migration/reset/replacement ran.
No Cloudflare, OAuth registration, BIC, account ownership or authorization policy
change occurred. The artifact and override live under
/Volumes/Dev_SSD/Codexify-scout815-auth/465497b0c on VaultNode. The original Compose
files and base image provide rollback without a database downgrade.

This establishes bounded deployment only. Canonical account handoff, native
protected read, task/message continuity and logout denial still require the
operator's secure sign-in in the actual Scout app. #815 remains open.


## Independent native session amendment — source qualification

The operator amended the approval: native exchange must issue a fresh exact-purpose
account_session for the same canonical User.id, rather than returning browser
session bytes. The revised source uses the canonical issuer and 24-hour session
store TTL, with a fresh nonce/store key/expiry. Browser approval is revalidated
before issuance; browser and native revocation are independent. Grant origin is
explicitly stored and checked by the atomic Redis consumption script. The selected
alternate header also invokes the existing strict validator before downstream
routing, including logout; failed selection never retries another credential.
Conflicting browser/native exchange account credentials are rejected.

Qualification: 68 backend tests pass, including independent nonce/expiry, browser
revocation preserving native authority, native logout preserving browser authority,
subsequent protected-read denial, replay refusing a second session, origin mismatch,
selected-account failure and the existing purpose/operator suites. Login page tests
pass 13 cases and the frontend build passes. No Swift contract change is required:
the native response still contains token, user_id and expires_at. These source
checks do not prove a live account login, and the amendment is not yet deployed.

Deployment boundary: the current backend entrypoint unconditionally invokes
backend/scripts/seed_defaults.py. Guardian's lifespan also invokes global system
doc seeding, local-user bootstrap, built-in help upsert, default project ensure,
sync-job support ensure and provider-row synchronization. No existing no-seed
startup switch was found. The amended approval expressly forbids seed operations;
therefore the old normal restart command must not be used for this revision.
A bounded opt-in guard proposal will suppress these startup provisioning hooks,
keep database/service initialization and auth validation, and use direct Uvicorn
to bypass the seed script. It requires explicit resolution before deployment;
no startup provisioning change has been applied or deployed at this checkpoint.

Amendment commit hooks: format, secret detection, Bandit and other applicable hooks
passed. Mypy again reports only existing errors in untouched modules (three errors
in coding_agent_contracts.py and watchdog/contracts.py for this six-file import
graph); the scoped retry excludes only that known failing hook. The proposed
no-seed guard was separately tested from /tmp without changing repository startup
source: two tests pass, proving the opt-in mode suppresses all seven provisioning
hooks and the default retains them. It remains a review proposal, not applied code.
