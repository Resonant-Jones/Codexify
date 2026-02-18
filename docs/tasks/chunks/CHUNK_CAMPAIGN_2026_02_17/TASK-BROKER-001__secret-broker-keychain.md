# TASK-BROKER-001 — Add macOS Keychain broker (best-effort, optional dependency)

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Backend-only changes: run backend tests.
3. Stage and commit.
4. Output: summary, tests, commit hash.

## Task Description
This change belongs in `guardian/core/secret_broker_keychain.py` because OS-backed secure storage is the desired long-term store. Implement best-effort macOS Keychain support with a soft dependency so local dev does not break.

Files in scope:
- `guardian/core/secret_broker_keychain.py` (new)
- `guardian/tests/test_secret_broker_keychain.py` (new, skip if keychain unavailable)
- `requirements/dev.in` (existing dependency convention for optional local developer tooling)

Implement:
- `KeychainSecretBroker` using `keyring` (if installed):
  - Service name: `codexify`
  - Account: `secret_id`
- If dependency missing:
  - `is_available()` returns false
  - `get_secret()` raises actionable error (`install keyring`)
- Tests:
  - Skip on CI if keychain backend not available (`pytest.skip` markers)

## Explicit Test Commands
```bash
pytest -v
```

## Explicit Git Add + Commit Steps
```bash
git add guardian/core/secret_broker_keychain.py guardian/tests/test_secret_broker_keychain.py requirements/dev.in
git commit -m "Core: add KeychainSecretBroker (optional) for OS-backed secrets"
```

## Expected Output
- Optional keychain broker with safe fallbacks + tests passing/skipping appropriately.
- Git commit hash.
