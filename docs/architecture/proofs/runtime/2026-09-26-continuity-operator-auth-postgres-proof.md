# Continuity Operator Authentication PostgreSQL Qualification

**Date:** 2026-09-27
**Outcome:** PASS
**Branch / HEAD:** `codex/restore-conversation-import-pipeline` / `1598b9dbd30a1c156d70c6d44ffe02c57afa0d72`

## Scope

This proof qualifies the first explicit `operator_session` consumer, the six-route Continuity operator surface, against PostgreSQL at the exact committed baseline above. It is a test/runtime qualification only. No production or test implementation was changed.

The pre-existing host-side run failed before reaching the integration assertions because `db:5432` is a Compose-network hostname and did not resolve from host pytest. That was a topology mismatch, not an operator-auth result.

## PostgreSQL target and safety

The repository Compose PostgreSQL service was run under the unique project
`codexify-operator-auth-pgproof-20260927`, with its own project-scoped network
and fresh volume `codexify-operator-auth-pgproof-20260927_pg_data`. It used a
synthetic test database/user and an ephemeral mode-0600 environment file under
`/private/tmp`; no credential or full DSN is recorded here. Host pytest used
the explicit loopback endpoint `127.0.0.1:5433`.

Before tests, the container reported `db:5432 - accepting connections`, a
read-only query returned the expected test database name, and a host TCP probe
to `127.0.0.1:5433` succeeded. The repository `migrator` service applied the
Alembic heads and completed its defaults seeding. This target was created with
a new named project and fresh volume; it was not the existing application DB
or the running private-preview DB. The existing application and preview
projects were not restarted or modified.

The tests use explicit UUID-derived IDs except the link-readback fixture's
fixed uniqueness tuple. Therefore the targeted integration run and full suite
were run against separate fresh database states. The first full-suite attempt
reused the targeted run's state and hit a duplicate
`(state_id, packet_id, relationship)=(state-x, pkt-x, contributed)` key in
that fixture. Only the uniquely named disposable test volume was removed and
recreated; after rerunning migrations, the full suite passed on the clean
state. No test or application behavior was changed.

## Eight PostgreSQL integration cases

Collection confirmed these eight cases:

1. `tests/continuity/test_continuity_operator_commit_readback_route.py::test_live_commit_readback_roundtrip`
2. `tests/continuity/test_continuity_operator_diagnostics_route.py::test_live_diagnostics_with_data`
3. `tests/continuity/test_continuity_operator_diagnostics_route.py::test_live_diagnostics_no_write_side_effects`
4. `tests/continuity/test_continuity_operator_link_readback_route.py::test_live_link_readback_roundtrip`
5. `tests/continuity/test_continuity_operator_profile_activation.py::test_live_stamp_persistence_under_test_profile`
6. `tests/continuity/test_continuity_operator_readback_route.py::test_live_readback_roundtrip`
7. `tests/continuity/test_continuity_operator_route.py::test_live_stamp_route`
8. `tests/continuity/test_continuity_operator_state_readback_route.py::test_live_state_readback_roundtrip`

Command:

```text
.venv/bin/pytest -v -m integration tests/continuity/test_continuity_operator_*.py
```

Result: **8 passed, 59 deselected** (the expected non-integration cases were
excluded by `-m integration`). No integration assertion failed.

## Full Continuity operator suite

Command:

```text
.venv/bin/pytest -v tests/continuity/test_continuity_operator_*.py
```

The command ran with the same explicit loopback test DSN, against the clean
fresh database after migrations. Result: **67 passed**, with no skips or
deselections. One non-blocking warning was reported by pytest.

## Focused operator/authentication regression

Command:

```text
.venv/bin/pytest -v \
  tests/identity/test_operator_session_boundary.py \
  tests/auth/test_auth_flow.py \
  tests/auth/test_private_preview_access.py \
  tests/routes/test_admin.py \
  tests/identity/test_identity_boundary_contract.py
```

Result: **35 passed**. Two non-blocking warnings were reported by pytest.

## Boundary and implementation status

- The exact committed baseline `1598b9dbd30a1c156d70c6d44ffe02c57afa0d72` was qualified.
- No production or test source changed; ADR-092 and this proof receipt are the only task-owned documentation changes.
- Generic `require_api_key`, `guardian/core/auth_dependencies.py`, task-event SSE, Cloudflare configuration, and the dirty public-ingress HOLD receipt were not changed.
- Public-ingress status remains **HOLD**. This proof does not qualify the public-ingress matrix or complete ADR-092 enforcement.
- Remaining operator-route migration, strict generic account-purpose validation, `auth_dependencies.py` bypass closure, legacy account-token rejection, mixed-principal enforcement, task-event SSE authorization, and public-ingress qualification remain deferred.

The initial host failure was a Compose DNS/topology mismatch. The targeted,
clean full-suite, and focused authentication results establish that the
committed operator-session Continuity integration passes against the isolated
PostgreSQL target.
