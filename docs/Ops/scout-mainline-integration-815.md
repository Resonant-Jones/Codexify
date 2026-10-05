# Scout #815 mainline Guardian integration receipt

## Lineage and bounded integration

- Integration branch: `codex/scout-backend-integration-815`.
- Base: current `main`, `e992d8e2b836167e87e4f3c9343ec596cf15f566`.
- Historical source: `codex/scout-account-handoff-815`,
  `68d6c061f786f680f198f7328d40753b096625db`.
- Companion client: `codex/scout-client-integration-815`, sourced from
  `fa1329ce742bfdb9cc6d94880c4206f6d11109e0`.

Neither historical branch is merged. The transplant includes only the hosted
account transport, PKCE handoff, bounded non-secret qualification observations,
browser Continue to Scout flow, scoped logging redaction and startup seed opt-out
required by the preserved-preview restoration. The containing commit and PR bind
this receipt to the integration tree.

Current-main credential validators, purpose tokens, account/session store,
thread-read authority and durable task-event authorization are retained. No
execution-credential, coding-worker, provider implementation, schema, migration,
ownership, account provisioning, OAuth registration, Access/BIC policy, DNS,
Tunnel or deployment configuration is imported from historical branch history.

## Trust and runtime composition

Guardian/Vault is authoritative for accounts, ownership and durable state.
Cloudflare Access admits ingress but cannot create a Guardian identity. Scout's
native session is an independent instance of the existing exact-purpose
`account_session`, minted by the canonical issuer and stored/revoked by the
canonical session store.

- ADR-092's approved alternate transport is restricted to `preview.codexify.space`
  in `private_preview`, one Host and one RS256-validated Access assertion for the
  fixed issuer/application audience, and the explicitly scoped account APIs.
- The independently qualified edge may consume native Access Authorization.
  Its absence alone grants no trust. Access credentials are never reconstructed,
  copied or moved into an origin header. Forwarded native Authorization retains
  the strict opaque OAuth shape.
- `X-Guardian-Account-Session` is normalized only after admission validation, then
  evaluated by current-main canonical account validators. Mixed account, guest,
  key and operator selectors fail closed; invalid/expired/revoked/wrong-purpose
  credentials cannot fall back to another principal. Personal Bearer behavior
  remains unchanged.
- Same-origin explicit browser confirmation produces a fixed-callback S256 grant
  with a 60-second TTL and atomic single-use Redis consumption. Redemption
  revalidates the browser session, account purpose and current eligibility before
  creating the independent native session. No browser credential is returned.
- Qualification evidence contains only bounded UUID attempt IDs, fixed stage/status
  values and HTTP status. It lives in bounded process memory for ten minutes,
  never becomes authorization and never retains credentials or account content.
- `CODEXIFY_SKIP_STARTUP_SEEDING=1` skips exactly the existing seven provisioning
  hooks used by preserved-preview recovery. Absent/zero keeps main's default
  startup. Service/database initialization remains unchanged. No application
  lifespan was started against the preserved database during integration tests.

ADR-091/098 durable task-to-thread ownership remains authoritative before Redis
events are read. Mounted-application tests prove hosted normalization cannot bypass
owner checks, session revocation or signed Access admission.

## Fresh qualification

Run from the integration root with normal repository test bootstrap:

```sh
CODEXIFY_CONFIG_SOURCE=core CODEXIFY_DISABLE_DOTENV=1 \
CODEXIFY_EMBEDDINGS_BACKEND=mock GUARDIAN_API_KEY=synthetic-test-fixture \
/tmp/scout-handoff-test-venv/bin/python -m pytest -q \
  tests/identity/test_scout_qualification.py \
  tests/identity/test_scout_account_transport.py \
  tests/identity/test_scout_handoff.py \
  tests/identity/test_scout_handoff_routes.py \
  tests/identity/test_scout_app_mount.py \
  tests/identity/test_scout_no_seed_startup.py \
  tests/identity/test_account_purpose_strict_migration.py \
  tests/identity/test_operator_route_auth_migration.py \
  tests/identity/test_mixed_principal_boundary.py \
  tests/identity/test_task_event_stream_authorization.py \
  tests/identity/test_task_event_family_authorization.py \
  tests/identity/test_thread_read_access.py \
  --junitxml=/tmp/scout815-main-backend-root-results.xml
```

Result: **259 tests passed, zero failures/errors/skips**. XML and
`/tmp/scout815-main-backend-root-tests.log` record the result. Scout TestClients
explicitly remove only the test bootstrap's default operator-key injection;
conflicting selectors remain exercised. Initial runs exposed omitted fake Redis
bootstrap and injected-key fixture conflicts; the normal-bootstrap rerun resolves
both without changing production authentication. `backend/requirements-ci.txt`
declares `fakeredis[lua]==2.39.0` so CI executes the atomic Lua consumption tests.

The final combined run additionally includes `tests/core/test_auth_boundary.py`,
`test_multi_user_auth_mode.py`, `test_supported_profile_auth_coherence.py`, the
existing auth-flow/private-preview/trusted-remote/activation suites, auth-invite
attribution and remote chat-thread route tests, content/credential logging and
logging-isolation tests, and all `tests/architecture`. Result: **749 passed**, zero
failures/errors/skips (259 + 49 auth + 10 logging + 431 architecture).
Final XML/log: `/tmp/scout815-main-final-backend-results.xml` and
`/tmp/scout815-main-final-backend-tests.log`. Initial architecture checks found
unhydrated existing LFS JSON fixtures; checkout from the local object store fixes
the test inputs without changing tracked fixture content.

Repository pre-commit checks pass except transitive mypy: three `call-overload`
errors in unchanged `guardian/watchdog/contracts.py:466` and
`guardian/routes/imprint.py:508,531`. Their blob hashes match the mainline base.
No unrelated type repair is included. The repository mypy v1.3.0 executable with
`--ignore-missing-imports --explicit-package-bases --follow-imports=skip` passes
all 13 touched Python files; this narrower result does not claim their imported
mainline modules pass. Only the known transitive mypy hook is skipped at commit;
secret scanning, formatting, security and path checks run normally. Logs:
`/tmp/scout815-backend-precommit.log` and `/tmp/scout815-main-mypy-scoped.log`.

```sh
pnpm --dir frontend/src exec vitest run \
  pages/__tests__/LoginPage.trustedRemote.test.tsx \
  test/authState.test.ts test/auth-gate.test.ts \
  test/live-events-auth-gate.test.tsx test/App.authProfile.test.tsx \
  test/api.desktop-auth.test.ts test/api.preflight.test.ts \
  test/api.completion-turn-id.test.ts
pnpm --dir frontend/src exec vite build
```

Result: **60 tests passed in eight files** and **production build passed**.
Logs: `/tmp/scout815-main-browser-full-tests.log` and
`/tmp/scout815-main-browser-build.log`. Existing duplicate-style, Browserslist
and chunk-size warnings remain. Compatible installed dependencies from the
source worktree were reused; current-main manifests/lockfiles were verified
identical and remain unchanged. Tests/builds execute integration source files.

The client receipt records its complete **66-test SwiftPM suite** and successful
**signed Simulator build**. CI/review on both exact integration heads remains the
merge gate. Focused local proof does not substitute for that gate.

## PR review follow-up

The auth family now mounts Scout through the same `auth` route gate as ordinary
login/logout. `CODEXIFY_ENABLE_AUTH_ROUTES=false` and supported-profile quarantine
remove handoff, exchange and every qualification method. Access/account/PKCE
validation remains unchanged. The focused matrix above was rerun after this
repair: **752 passed, zero failures/errors/skips**; XML/log:
`/tmp/scout815-review-backend-results.xml` and
`/tmp/scout815-review-backend-tests.log`.

Guardian CI originally stopped at a mount-test assumption that every item in
`app.routes` has `.path`. Its FastAPI 0.142.2 uses lazy included routers. The test
now proves both handlers by real HTTP rejection instead of framework internals.
All **nine mount/gating cases** also pass with CI's FastAPI 0.142.2 and Starlette
1.7.0 installed in an isolated `/tmp` dependency overlay. Production dependency
requirements are unchanged. Log: `/tmp/scout815-review-ci-framework-tests.log`.
The eight-file frontend matrix again passes **60 tests**, and the production
frontend build succeeds. Logs: `/tmp/scout815-review-browser-tests.log` and
`/tmp/scout815-review-browser-build.log`. The temporary dependency symlink used
for this check is excluded from the commit.

The immutable initial backend integration was separately reviewed with Codex
Security (scan `cc205de8-49db-44e5-bbf7-838f424438c3`). Its only reportable finding
was the configured auth-gate bypass corrected above. That report remains evidence
for the initial commit; final-head CI and review remain required.

A later full CI run exposed module-global app wiring retained by an earlier
supported-profile test. The enabled-Scout mount case correctly received 404
from that quarantined app. This was reproduced locally by running that profile
test before the Scout mount test. Scout's mount tests now explicitly reload the
app under a scoped test posture and restore prior environment/app wiring after
each case, without entering lifespan or changing the production route gate.
All **23 combined supported-profile, beta-quarantine and Scout mount cases**
pass in CI's framework overlay, including the previously failing order. Logs/XML:
`/tmp/scout815-review-mount-order-tests.log` and
`/tmp/scout815-review-mount-order-results.xml`. Scoped mypy and applicable hooks
pass for this test-only repair; full CI on the published follow-up remains the
merge gate.

## Evidence boundaries and follow-through

[Historical backend qualification](https://github.com/Resonant-Jones/Codexify/blob/68d6c061f786f680f198f7328d40753b096625db/docs/Ops/scout-auth-qualification-2026-10-03.md)
and [the source live packet](https://github.com/Resonant-Jones/Codexify/blob/fa1329ce742bfdb9cc6d94880c4206f6d11109e0/mobile/scout-ios/SCOUT_LIVE_CONTINUITY_2026-10-04.md)
remain historical source/runtime evidence. Integration tests use isolated
fixtures; this receipt claims no new live sign-in, database mutation, deployment
or widened release support. `00-current-state.md` remains the release gate.

Personal-node live continuity, final physical iPhone continuity and deliberate
failed/cancelled live tasks remain non-blocking unproven gaps. #813 current truth
is updated only after both integrations reach main. #818 contract preparation and
#816 implementation remain downstream; neither is included in this PR.
