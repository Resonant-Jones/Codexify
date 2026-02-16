# TASK-2026-02-16-004 Config Unification or Startup Assertions

## Task ID
- TASK-2026-02-16-004_config_unification_or_startup_assertions

## Goal
- Prevent silent security posture drift by enforcing strict startup-time config coherence checks.

## Files Touched
- `guardian/core/config.py`
- `guardian/guardian_api.py`
- `guardian/server/app.py`
- `tests/core/test_config_coherence.py`

## Tests Run
- `pytest -v tests/core/test_config_coherence.py tests/test_startup.py`
  - Result: `16 passed`
- `pytest -v`
  - Result: `1 failed, 678 passed, 15 skipped, 33 xfailed, 11 xpassed`
  - Unrelated pre-existing failure outside touched scope:
    - `tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`
    - Failure context: environment/system prompt dependency issue (`db` hostname unresolved) causing missing RAG memory context in test harness.

## Notes/Risks
- Added explicit startup coherence assertion flow instead of attempting a risky broad config migration:
  - `assert_config_coherence(...)` in `guardian/core/config.py`
  - dedicated `ConfigCoherenceError` with detailed mismatch diagnostics
  - coherence checks include overlapping security-relevant fields plus explicit provider/cloud-mode guardrails when env overrides are set
- Added security-critical fields (`GUARDIAN_API_KEY`, `GUARDIAN_API_KEYS`, `GUARDIAN_DATABASE_URL`) to `guardian/core/config.Settings` so coherence checks can validate shared values across config systems.
- Enforced startup fail-closed behavior in both app entrypoints:
  - `guardian/guardian_api.py` lifespan startup
  - `guardian/server/app.py` startup hook
- Added tests for pass/fail coherence scenarios and legacy-unavailable fallback behavior.

## Commit A (Code/Tests)
- `a66b2bbd0ad4c7e161f64d45a256384365f27208`

## Commit B (Docs/Mapping)
- `<pending>`
