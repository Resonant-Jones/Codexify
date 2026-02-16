# TASK-2026-02-16-002 Lock Down Egress by Default

## Task ID
- TASK-2026-02-16-002_lock_down_egress_by_default

## Goal
- Enforce explicit opt-in for outbound egress (OpenAI, Groq, ElevenLabs, federation, webhooks) with fail-closed local-only defaults.

## Files Touched
- `guardian/core/config.py`
- `guardian/core/egress.py`
- `guardian/core/ai_router.py`
- `guardian/core/dependencies.py`
- `guardian/routes/federation.py`
- `guardian/routes/cron.py`
- `guardian/cron/executor.py`
- `guardian/providers/openai_adapter.py`
- `guardian/providers/groq_adapter.py`
- `guardian/providers/groq_client.py`
- `guardian/tts/providers/elevenlabs_provider.py`
- `guardian/image_gen/providers/openai.py`
- `guardian/tests/core/test_ai_router.py`
- `guardian/tests/core/test_egress.py`
- `tests/routes/test_cron_routes.py`
- `tests/federation/test_federated_session_exchange.py`

## Tests Run
- `pytest -v guardian/tests/core/test_ai_router.py guardian/tests/core/test_egress.py tests/routes/test_cron_routes.py tests/federation/test_federated_session_exchange.py`
  - Result: `45 passed`
- `pytest -v`
  - Result: `1 failed, 673 passed, 15 skipped, 33 xfailed, 11 xpassed`
  - Unrelated pre-existing failure outside touched scope:
    - `tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`
    - Failure context: environment/system prompt dependency issue (`db` hostname unresolved) causing missing RAG memory context.

## Notes/Risks
- Added centralized fail-closed egress policy in `guardian/core/egress.py`:
  - default deny via `CODEXIFY_LOCAL_ONLY_MODE=true`
  - explicit opt-in via `CODEXIFY_EGRESS_ALLOWLIST`
  - cloud-specific hard gate via `ALLOW_CLOUD_PROVIDERS`
- Enforced egress checks in OpenAI/Groq provider paths, ElevenLabs TTS, federation session request route, and webhook creation/execution paths.
- Added tests to verify blocked-by-default behavior and explicit opt-in behavior.

## Commit A (Code/Tests)
- `6841529bad60dc9d54bbf4736f07f7896995224b`

## Commit B (Docs/Mapping)
- `<this-commit>`
