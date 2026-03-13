# TASK-2026-02-16-001 Single User Identity Contract

## Task ID
- TASK-2026-02-16-001_single_user_identity_contract

## Goal
- Enforce server-derived single-user identity and prevent `X-User-Id` spoofing in non-debug runtime paths.

## Files Touched
- `guardian/core/dependencies.py`
- `guardian/routes/memory.py`
- `guardian/routes/channels.py`
- `guardian/routes/personal_facts.py`
- `guardian/routes/migration.py`
- `guardian/routes/rag_upload.py`
- `tests/routes/test_memory.py`
- `tests/routes/test_personal_facts_routes.py`
- `tests/routes/test_migration_routes.py`
- `guardian/tests/test_channels_routes.py`

## Tests Run
- `pytest -v tests/routes/test_memory.py tests/routes/test_personal_facts_routes.py tests/routes/test_migration_routes.py guardian/tests/test_channels_routes.py`
  - Result: `39 passed`
- `pytest -v`
  - Result: `1 failed, 671 passed, 15 skipped, 33 xfailed, 11 xpassed`
  - Unrelated pre-existing failure outside touched scope:
    - `tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`
    - Failure context: environment/system prompt dependency issue (`db` hostname unresolved) causing missing RAG memory context.

## Notes/Risks
- Added canonical single-user identity resolution in `guardian/core/dependencies.py`:
  - `get_single_user_id()` derives from `CODEXIFY_SINGLE_USER_ID` with stable default (`local`).
  - `get_request_user_id()` only honors `X-User-Id` when explicit `DEBUG=true` or `LOCAL_DEV=true`.
- Removed direct route-level trust of `X-User-Id` in all discovered in-scope call sites.
- Updated route tests to validate non-debug anti-spoof behavior.

## Commit A (Code/Tests)
- `10322d4a091d340353de6b61f984954da2a10318`

## Commit B (Docs/Mapping)
- `<this-commit>`
