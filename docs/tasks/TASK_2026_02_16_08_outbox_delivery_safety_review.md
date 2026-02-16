# TASK_2026_02_16_08_outbox_delivery_safety_review

## Task ID
TASK-2026-02-16-008_outbox_delivery_safety_review

## Goal
Review and harden outbox delivery and retry/poll safety for single-user-first operation.

## Files Touched
- guardian/core/outbox.py
- guardian/core/event_bus.py
- guardian/core/chat_db.py
- guardian/core/pgdb.py
- guardian/guardian_api.py
- tests/core/test_outbox_safety.py

## Tests Run
- `pytest -v`
- `pytest -v tests/core/test_outbox_safety.py`
  - Result: pass (`7 passed`)
- `pytest -v`
  - Result: run completes with unrelated environment-level failures when local `.env` has `AI_BACKEND=local` (legacy config expects `ollama|openai|gemini|groq|anthropic`)
- `AI_BACKEND=ollama pytest -v`
  - Result: baseline-equivalent outcome (`1 failed, 696 passed, 15 skipped, 33 xfailed, 11 xpassed`)
  - Remaining failure: `tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`

## Notes / Risks
- Added central outbox safety helpers in `guardian/core/outbox.py`:
  - tenant normalization (`normalize_outbox_tenant_id`)
  - bounded poll interval and batch-size parsing
  - robust `Last-Event-ID` parsing
- Hardened event bus behavior in `guardian/core/event_bus.py`:
  - normalizes blank tenant ids to safe default
  - tenant-aware fetch path with backward-compatible fallback filtering for legacy store signatures
- Added tenant-filter support in outbox store contract and implementation:
  - `guardian/core/chat_db.py:list_events_after(...)`
  - `guardian/core/pgdb.py:list_events_after(...)`
- Hardened `/api/events` stream loop in `guardian/guardian_api.py`:
  - uses safe parsing/clamping helpers for outbox polling config and `last_id`
  - fetches and deletes outbox events scoped to a normalized tenant id
  - skips malformed event IDs safely instead of crashing the stream loop
- Added focused regression tests in `tests/core/test_outbox_safety.py` covering parsing bounds, tenant normalization, tenant-aware fetch behavior, and blank tenant normalization on emit.

## Commit A
- `be713fc039edc254cb01f5d6b179eed8da4e01f1`

## Commit B
- `<this-commit>`
