# TASK-BROKER-000 — Introduce Secret Broker interface + env-backed implementation

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Backend-only changes: run backend tests.
3. Stage and commit.
4. Output: summary, tests, commit hash.

## Task Description
This change belongs in `guardian/core/secret_broker.py` because the broker is the single choke point for secrets access (agents never see long-lived raw tokens).

Files in scope:
- `guardian/core/secret_broker.py` (new)
- `guardian/tests/test_secret_broker.py` (new)

Implement:
- Define interface:
  - `get_secret(secret_id: str) -> str`
  - `set_secret(secret_id: str, value: str) -> None` (optional for now)
  - `is_available() -> bool`
- Implement `EnvSecretBroker`:
  - Maps `secret_id` -> env var convention (e.g. `CODEXIFY_SECRET_<ID>`)
  - Never logs secret values; redact in errors
- Add minimal tests:
  - Missing secret raises controlled error
  - Returned secret matches env
  - Redaction behavior

## Explicit Test Commands
```bash
pytest -v
```

## Explicit Git Add + Commit Steps
```bash
git add guardian/core/secret_broker.py guardian/tests/test_secret_broker.py
git commit -m "Core: add SecretBroker interface with env-backed implementation"
```

## Expected Output
- Broker abstraction merged + tests passing.
- Git commit hash.
