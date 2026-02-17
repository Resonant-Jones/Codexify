# TASK-CAP-000 — Add capability grant model (TTL + scope + max_calls)

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Backend-only changes: run backend tests.
3. Stage and commit.
4. Output: summary, tests, commit hash.

## Task Description
This change belongs in `guardian/core/capabilities.py` because capability grants are the enforcement primitive: short-lived, scoped, deny-by-default.

Files in scope:
- `guardian/core/capabilities.py` (new)
- `guardian/tests/test_capabilities.py` (new)

Implement:
- `CapabilityGrant` fields:
  - `grant_id` (uuid)
  - `action` (string enum-like)
  - `resource` (string, supports prefix matching)
  - `expires_at` (UTC timestamp)
  - `max_calls` (int)
  - `calls_used` (int)
- Methods:
  - `is_expired(now)`
  - `allows(action, resource, now)`
  - `consume_call()` raises if exceeded
- Tests:
  - deny-by-default
  - expiry behavior
  - `max_calls` enforcement
  - resource prefix matching (if included)

## Explicit Test Commands
```bash
pytest -v
```

## Explicit Git Add + Commit Steps
```bash
git add guardian/core/capabilities.py guardian/tests/test_capabilities.py
git commit -m "Core: add capability grants with TTL and max_calls enforcement"
```

## Expected Output
- Capability model added + tests passing.
- Git commit hash.
