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
