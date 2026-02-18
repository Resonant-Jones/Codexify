# TASK-CAP-002 — Wire capability issuance for single-user local flows (minimal)

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Backend-only changes: run backend tests.
3. Stage and commit.
4. Output: summary, tests, commit hash.

## Task Description
This change belongs in `guardian/guardian_api.py` plus an existing authenticated route surface in `guardian/routes/admin.py` because you need a minimal issuance mechanism to unblock the UI: server generates short-lived grants on behalf of the authenticated user.

Files in scope:
- `guardian/guardian_api.py`
- `guardian/routes/admin.py`
- `guardian/tests/test_capability_issuance.py` (new)

Implement:
- Add endpoint: `POST /api/capabilities/issue`
- Requires auth
- Accepts requested actions + namespace/resource
- Returns signed/opaque grant token (or grant_id stored server-side)
- Keep minimal:
  - in-memory grant store (`dict`) with TTL
  - explicit TODO for persistent store later

Tests:
- Unauthenticated -> `401`
- Authenticated -> returns grant
- Grant can be used to call `/embed` or `/search` in tests

## Explicit Test Commands
```bash
pytest -v
```

## Explicit Git Add + Commit Steps
```bash
git add guardian/guardian_api.py guardian/routes/admin.py guardian/tests/test_capability_issuance.py
git commit -m "Security: add minimal capability issuance endpoint for local flows"
```

## Expected Output
- Issuance endpoint + tests passing.
- Git commit hash.
