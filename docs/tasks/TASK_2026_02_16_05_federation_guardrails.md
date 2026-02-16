# TASK-2026-02-16-005 Federation Guardrails

## Task ID
- TASK-2026-02-16-005_federation_guardrails

## Goal
- Ensure federation is disabled by default and, when enabled, enforce authenticated access plus signed trust-policy guardrails.

## Files Touched
- `guardian/core/config.py`
- `guardian/core/auth.py`
- `guardian/routes/federation.py`
- `tests/core/test_federation_trust_policy_auth.py`
- `tests/federation/test_federated_session_exchange.py`

## Tests Run
- `pytest -v tests/core/test_federation_trust_policy_auth.py tests/federation/test_federated_session_exchange.py`
  - Result: `37 passed`
- `pytest -v`
  - Result: `1 failed, 685 passed, 15 skipped, 33 xfailed, 11 xpassed`
  - Unrelated pre-existing failure outside touched scope:
    - `tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`
    - Failure context: environment/system prompt dependency issue (`db` hostname unresolved) causing missing RAG memory context in test harness.

## Notes/Risks
- Added explicit federation defaults and guardrail settings to `guardian/core/config.py`:
  - `GUARDIAN_FEDERATION_ENABLED=false` by default
  - signed policy requirement enabled by default
- Added signed trust-policy signing/verification helpers in `guardian/core/auth.py` using base64url HMAC-SHA256.
- Enforced guardrails in `guardian/routes/federation.py`:
  - federation endpoints now require API key auth at router level
  - all federation endpoints fail closed when federation is disabled
  - when enabled, endpoints require a valid signed trust policy
  - session request/accept now enforce trust-policy node/origin allowlists
  - websocket relay now rejects connections with policy violations
- Added tests covering trust-policy signing/verification and route-level federation gating behavior.

## Commit A (Code/Tests)
- `46ac90155dd28c2669400a92d4dddc083396223e`

## Commit B (Docs/Mapping)
- `<pending>`
