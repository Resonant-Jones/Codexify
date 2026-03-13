# TASK-IR-003 — Add startup fail-closed guard for missing secret broker backing

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Backend-only changes: run backend tests.
3. Stage and commit.
4. Output: summary, tests, commit hash.

## Task Description
This change belongs in the active settings module `guardian/config/core.py` because the system must not silently run insecure defaults when secret storage is misconfigured.

Files in scope:
- `guardian/config/core.py`
- `guardian/tests/test_config_security.py` (new)

Implement:
- Add env flags:
  - `CODEXIFY_SECRET_STORE=env|keychain` (default `env`)
  - `CODEXIFY_REQUIRE_SECRET_STORE=true|false` (default `false`)
- If `CODEXIFY_REQUIRE_SECRET_STORE=true` and configured store is unavailable, hard fail on startup with an actionable error.

## Explicit Test Commands
```bash
pytest -v
```

## Explicit Git Add + Commit Steps
```bash
git add guardian/config/core.py guardian/tests/test_config_security.py
git commit -m "Security: add fail-closed secret store requirement flag"
```

## Expected Output
- New config flags + tests passing.
- Git commit hash.
