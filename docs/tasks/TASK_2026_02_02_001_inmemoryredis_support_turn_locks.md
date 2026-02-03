# TASK_2026_02_02_001 — InMemoryRedis: support turn locks (set/delete + TTL/NX)

## Summary
- Patched the in-test Redis stub at runtime (via `guardian/queue/redis_queue.py`) to add TTL tracking, `_now`/`_purge_if_expired`, and `set`/`delete` with NX semantics.
- Updated stub string accessors (`get`, `setex`) to honor expiry so turn locks and status TTLs work in tests.

## Commands run
- `pytest -q guardian/tests/test_chat_memory.py::test_chat_turn_lock_rejects -vv -s`
- `pytest -q guardian/tests/test_chat_memory.py::test_chat_crud -vv -s`

## Results
- `test_chat_turn_lock_rejects`: pass
- `test_chat_crud`: fail — `AttributeError: 'NoneType' object has no attribute 'ensure_chat_thread'` (chatlog DB not configured)
