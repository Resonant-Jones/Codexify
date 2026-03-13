# TASK_2026_02_02_001 — InMemoryRedis: support turn locks (set/delete + TTL/NX)

## Goal

Fix pytest failures caused by the in-test Redis stub lacking `set()` and `delete()` (used by per-thread turn-lock logic). Implement minimal Redis semantics for NX + TTL so the lock system works during tests.

## Allowed files (only)

- guardian/queue/redis_queue.py
- docs/work/tasks/2026/02/TASK_2026_02_02_001_inmemoryredis_support_turn_locks.md

## What to change

In `guardian/queue/redis_queue.py`, locate the in-test Redis stub class (commonly `_InMemoryRedis`), and implement:

### 1) Storage + expiry tracking

Ensure the stub maintains:

- a backing dict for values (use the existing one)
- an expiry dict mapping key -> epoch seconds (create if missing)

### 2) Expiry helpers

Add helpers to enforce TTL:

- `_now()` returns `time.time()`
- `_purge_if_expired(key)` removes expired keys from both dicts

### 3) Implement `set()`

Add:

- `set(key, value, ex=None, nx=False)`
- NX semantics: if `nx=True` and key exists (non-expired), do not overwrite; return falsy (None/False)
- TTL semantics: if `ex` provided, expire after `ex` seconds
- Return truthy on success (True/1)

### 4) Implement `delete()`

Add:

- `delete(key)` removes key (respect expiry)
- Return integer deleted count (0 or 1)

### 5) Make TTL effective

Update existing stub methods that read/write a key (`get`, `exists`, `incr`, etc.) to call `_purge_if_expired(key)` first (only when the method takes a single key argument; keep changes minimal).

## Do NOT change

- Any production Redis client behavior (only the in-memory stub)

## Checks to run

```bash
pytest -q guardian/tests/test_chat_memory.py::test_chat_turn_lock_rejects -vv -s
pytest -q guardian/tests/test_chat_memory.py::test_chat_crud -vv -s

-----

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
