# TASK-CAP-001 — Enforce capability checks in one high-risk surface (vector write/read)

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Backend-only changes: run backend tests.
3. Stage and commit.
4. Output: summary, tests, commit hash.

## Task Description
This change belongs in `guardian/routes/codexify_router.py` because `/embed` and `/search` are high-impact primitives; capability enforcement here prevents lateral movement even after auth.

Files in scope:
- `guardian/routes/codexify_router.py`
- `guardian/tests/test_capability_enforcement_vector.py` (new targeted tests)

Implement:
- Require a capability grant for:
  - action `vector:write` on `/embed`
  - action `vector:read` on `/search`
- Resource should be namespace-scoped (e.g. `resource="ns:<namespace_id>"`).
- Deny requests lacking grant or with mismatched scope (`403`).

Tests:
- Without capability -> `403`
- With valid capability -> success path
- Expired capability -> `403`

## Explicit Test Commands
```bash
pytest -v
```

## Explicit Git Add + Commit Steps
```bash
git add guardian/routes/codexify_router.py guardian/tests/test_capability_enforcement_vector.py
git commit -m "Security: enforce capability grants on vector read/write endpoints"
```

## Expected Output
- Capability enforcement in vector endpoints + tests passing.
- Git commit hash.
