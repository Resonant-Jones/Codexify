# Configuration Inspector v1 Backend Proof

**Date:** 2026-09-29

**Evidence class:** accepted ADR + source inspection + focused TestClient proof

**Release posture:** internal operator capability; no Beta or release-support expansion

## Source and result

- Source commit before implementation: `493abd8ec50c9710eda2ea60795f383a204de44b`
- Resulting implementation commit: `dc77599ec50c9710eda2ea60795f383a204de44b`
- Files changed by this task:
  - `guardian/routes/configuration_inspector.py`
  - `guardian/guardian_api.py`
  - `tests/routes/test_configuration_inspector.py`
  - `tests/identity/test_operator_route_auth_migration.py`
  - `docs/architecture/proofs/runtime/2026-09-29-configuration-inspector-v1-backend-proof.md`
  - `docs/architecture/configuration-inspector-control-plane.md`

The implementation is aligned with accepted ADR-095. ADR-095, ADR-094,
supported-profile manifests, `guardian/protocol_tokens.py`, and
`docs/architecture/00-current-state.md` were not changed.

## Endpoint and authority

The route is exactly `GET /api/operator/configuration`. The router declares
`Depends(require_operator_auth)` and exposes no mutation method or declared
query parameter; arbitrary query keys do not select configuration values. It
is included beside the existing admin router inside the single existing
`_include_router(label="admin",
flag_name="CODEXIFY_ENABLE_ADMIN_ROUTES", core_surface=True)` invocation.
The existing route-family and supported-profile gate logic was not changed,
and no Inspector-specific flag was added. The auth regression ledger records
this route under `guardian.routes.configuration_inspector`.

The allowlisted response has these sections:

- `process`: Guardian service, current PID, and responding-process scope.
- `supported_profile`: profile name, version, surface class, and validity.
- `mounted_routes`: mounted route-family labels with an explicit observation
  interpretation.
- `provider_egress`: configured provider class, local-only mode, cloud policy,
  and allowlist-presence boolean.
- `local_inference`: configured local target only.

All response models use `extra="forbid"`. Evidence vocabulary is local to this
response schema; no global protocol tokens were added.

## Configuration evidence owners

| Family | Source used | Claim and limit |
|---|---|---|
| O02 | `request.app.state.supported_profile`, published by Guardian startup | `resolved` when the bounded profile fields validate; otherwise `unavailable` with `supported_profile_state_unavailable`. The raw manifest, mismatches, and provider contract are omitted. |
| O15 | `request.app.state.supported_profile["routes"]["mounted"]` | `observed` for the startup-published route labels; otherwise `unavailable` with `mounted_route_inventory_unavailable`. The response states that mounting does not establish authorization, health, or release support. |
| O07 | `Settings` fields for `LLM_PROVIDER`, local-only mode, cloud allowance, and egress allowlist | `resolved` only for a recognized provider and typed policy fields; otherwise `unavailable`. The allowlist is reduced to a boolean; keys, URLs, raw allowlist values, and provider availability are omitted. |
| O08 | `default_model_for_provider("local", settings)` | `resolved` for a safe configured target; otherwise `unavailable` with `local_inference_target_unavailable`. This is not advertised inventory, runtime identity, or a served-model claim. |

Each section fails independently with a fixed sanitized reason. Exceptions are
not returned, and one unavailable section does not replace another section's
owner or evidence.

## Focused proof

The tests use the configured project virtual environment at
`/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest`; the current worktree has no
local `.venv`.

| Command | Result |
|---|---|
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/routes/test_configuration_inspector.py` | 11 passed. |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/identity/test_operator_session_boundary.py tests/identity/test_operator_route_auth_migration.py` | 23 passed, 10 warnings. |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/core/test_supported_profile_startup.py guardian/tests/routes/test_health_supported_profile.py` | 5 passed; 3 health tests failed during setup. |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/routes/test_configuration_inspector.py tests/identity/test_operator_session_boundary.py tests/identity/test_operator_route_auth_migration.py tests/core/test_supported_profile_startup.py guardian/tests/routes/test_health_supported_profile.py` | 39 passed, 3 failed, 10 warnings. |

The three health-test failures occur while their setup calls
`_refresh_supported_profile_state`, before the health request assertions. The
fixture configures `LOCAL_BASE_URL` as
`http://host.docker.internal:11434/v1`, while the `v1-local-core-web-mcp`
profile requires `http://host.docker.internal:8000/v1`; the observed exception
is `supported profile drift`. Neither the health test file nor the profile was
changed for this task. The mismatch remains unresolved and is not attributed
to Configuration Inspector behavior.

The focused Inspector tests establish:

- raw configured operator key and exact-purpose operator session succeed;
- anonymous, account-purpose, and Hosted Room guest credentials receive 401;
- sentinel Guardian/local/provider/database/Redis/egress values do not occur in
  serialized responses;
- no account or user selector exists in the response models, and the isolated
  route works without account-data fixtures or lookup;
- the O08 unavailable case leaves O02/O15/O07 evidence unchanged;
- outbound `requests` calls, provider discovery, and the active LLM-health
  handler are patched to fail if called; the Inspector still returns 200;
- the isolated FastAPI route harness depends only on app state, safe settings,
  and operator auth. It requires no Postgres or Redis fixture, and the route
  contains no persistence or configuration-write call.

These tests are focused route evidence. They do not establish deployment-wide
runtime health or release qualification.

## Scope limits

The frontend/UI is not implemented. Cross-process aggregation, history,
persistence, mutation, active probes, account/user data, provider availability,
and served-model provenance are not implemented. Release support did not
change; `docs/architecture/00-current-state.md` remains the release-truth
source.

## Documentation validation

`make docs PYTHON=python3` passed: required architecture docs, README links,
source headings, and diagram freshness checks passed. Make also printed a
duplicate-target override warning for `canonical-audit-live-proof-receipt`
from Makefile lines 264 and 288; it did not fail validation.
