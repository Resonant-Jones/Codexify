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

## Independent-session image checkpoint (not deployed)

Source Git revision: 7c7def912. The bounded image
codexify-scout-native-session:7c7def912 was built on the pinned qualified base.
Image SHA256: eeb253ded052cb05fb6a28ec0d4f0131cdadac53c7fae5a64ca18792ad7a5083.
Reviewed source hashes and Python syntax passed in a network-disabled, read-only
container with only public source artifacts mounted and /tmp writable; application
startup was not invoked. Core dependency versions match the serving preview.
Artifact location: /Volumes/Dev_SSD/Codexify-scout815-auth/7c7def912 on VaultNode.

No preview service was restarted for this amendment, and no startup guard was
applied. The separately tested review proposal is
/tmp/scout815-no-seed-startup-proposal.md with the concrete diff at
/tmp/scout815-no-seed-startup-proposal.patch on the operator host. The operator was
asked to approve that additional opt-in startup behavior before deployment.
Native sign-in must wait for the amended revision; the earlier served patch still
returns the browser token. Full #815 continuity and #816–#818 remain unqualified.

## Approved no-seed startup source qualification

The operator subsequently approved the opt-in startup guard solely for the
existing preview qualification. `CODEXIFY_SKIP_STARTUP_SEEDING=1` suppresses the
seven identified hooks: global system docs, default user, built-in help, default
project, sync-job support, provider-row seed/synchronization, and import replay.
The flag is checked when lifespan starts. Its absence preserves existing startup
behavior; database/schema verification, service initialization, route bindings,
and authentication are retained. No new permanent startup policy is established.

The bounded preview command is `python -m uvicorn guardian.guardian_api:app
--host 0.0.0.0 --port 8888`. It bypasses the wrapper's unconditional seed script.
The wrapper's other responsibilities are the existing uppercase app symlink,
database readiness/schema probes, and embedding directory validation. These must
be qualified read-only before restart; missing non-seeding initialization is a
stop condition, not permission to compensate with another mutation.

The integrated account transport, handoff, purpose/operator and startup suite
passes 70 tests. Both startup modes execute the actual lifespan with isolated
spies: all seven hooks run once by default, and none runs with the flag. Database,
service, configuration and route bindings still run once in both modes. Two
additional tests pass against the pinned original API source with the identical
guard; its lifespan AST matches the amended source. This prepares rollback with
the original image/source plus the same approved no-seed guard and direct command.
Rollback must not use the original seed-producing wrapper during this window.

These tests prove source behavior only. Image, serving-source, anonymous denial,
database-preservation and secure native continuity evidence will be recorded
after the bounded deployment. Workers and the independent chat-proof stack stay
on their existing configuration and image.

Startup commit hooks pass formatting, secret detection, Bandit and the other
applicable checks. Mypy reports five existing errors in untouched
coding_agent_contracts.py, watchdog/contracts.py and routes/imprint.py. The
scoped commit retry excludes only that failing hook; the passing runtime tests
and docs checks do not erase the unrelated type-check limitation.

First guarded deployment: commit 6c6adaa74, image
27959164b29bb95683c5162ff2ba3e7b6c51eb404681485db5d3609c7bfa071e.
Only preview backend/frontend were recreated. Serving auth/LoginPage hashes and
the no-seed flag match the reviewed artifact; origin health/login return 200,
anonymous account reads return 401, and exchange without signed Access admission
returns 401. Schema hash, ten recorded table counts/row fingerprints and all
preserved service identities/configurations remain unchanged across startup.

The uppercase `/app/Codexify` alias exists only in the old container's writable
layer. Inspection found no Guardian/auth/runtime reference to it outside the
wrapper, which treats alias failure as a warning. Direct Uvicorn uses `/app` and
the existing `guardian`/`codexify` mounts, and serving health/auth denial confirms
that no required initialization is missing. No alias repair was performed.

The logging boundary sanitizes the first free-form suppression message, so its
absence is not evidence of a hook invocation. A safe static
`scout_startup_provisioning_disabled` marker replaces it; both guard-mode tests
also assert its presence/absence. The final image receipt must verify that marker
alongside serving bytes, flag, health and unchanged database posture.

## Final no-seed deployment receipt

Source revision: dcd8c2b7347632dc196f2181094bc4a1425c4785. Serving image:
sha256:f9e7f5ff1e69d03a4f626bdbf99ff6ba032687f7f374517ed1f05a565a99a158.
The artifact contains only five reviewed Guardian files, the reviewed LoginPage,
and qualification/Compose/rollback metadata. Build and syntax/hash qualification
use the already-pinned base with network disabled and no application startup.
Both forward and rollback Compose configurations retain all other services,
environment, volumes and networks. Only preview backend/frontend were recreated
with `up -d --no-deps --no-build --pull never backend frontend`.

Serving hashes match all reviewed files at both Guardian package mounts and the
frontend mount. The backend uses the approved direct command and flag; its safe
startup suppression marker appears exactly once. Guardian is healthy. Origin
`127.0.0.1:8081` health/login return 200, anonymous account thread reads return 401,
and Scout exchange without signed hosted admission returns 401. No seed script,
migration, import replay or bootstrap ran. Schema and all ten table counts/row
fingerprints are identical before/after; the existing workers, database and
independent chat-proof stack retain their container identities and configuration.
The [non-secret receipt](scout-no-seed-preview-receipt-2026-10-02.json) records the
image/base/source, schema fingerprint, table aggregates and remaining proof gates.

Rollback remains the pinned prior image/source. Use only
`/Volumes/Dev_SSD/Codexify-scout815-auth/dcd8c2b73/compose.scout-rollback.yml` with
the existing base/private-preview Compose files and the same bounded two-service
command. This removes Scout auth overrides but retains the tested no-seed guard
on the original API source; it does not downgrade or replace the database.

Final source tests pass 70 cases, guarded rollback passes both modes, docs checks
pass, and applicable commit hooks pass with the previously recorded mypy
limitation. Client Swift bytes did not change; prior 50-test/signed simulator
qualification remains separate from live proof. Device Hub currently shows no
Guardian account session and its coordinate input reports `noWindowsAvailable`.
The operator is asked to complete secure native Guardian sign-in and report only
non-secret status. Protected authenticated reads, session restoration/expiry,
logout/revocation and the complete #815 continuity loop remain unproven.
