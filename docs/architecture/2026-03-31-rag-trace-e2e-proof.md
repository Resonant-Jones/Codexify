# 2026-03-31 RAG Trace End-to-End Proof

## Scope

This artifact records the strongest truthful supported-path proof for RAG trace truth on the local completion path, after source selector hardening and diagnostics surface binding.

- Validation source of truth: repo-supported backend proof seams exercised from this checkout
- User-facing scope under proof:
  - Active thread can complete successfully
  - Latest RAG trace becomes retrievable after completion
  - Chat-side diagnostics surface resolves active thread correctly
  - Settings diagnostics surface resolves active thread correctly
  - `source_mode` is visible and truthful in diagnostics
  - `widen_reason` is visible and truthful in diagnostics/trace
  - Empty state for untouched threads
  - No trace bleeding across threads
- Out of scope:
  - Full browser-to-worker live runtime with real embeddings
  - Real multi-project corpus with persisted embeddings

## Exact Commands Run

```bash
pytest -v \
  tests/routes/test_chat_source_mode.py \
  tests/routes/test_chat_profile_trace.py \
  tests/core/test_context_broker_source_mode.py \
  tests/core/test_chat_completion_service_source_mode_fallback.py
```

## What Was Proven In A Supported Runtime Seam

### 1. Route seam proof — thread completion

`tests/routes/test_chat_source_mode.py`

Proved through the FastAPI route seam:

- `POST /chat/{thread_id}/complete` enqueues a task and returns `source_mode` in response
- `source_mode` is normalized and encoded into task `origin`
- Task is enqueued to the correct queue (`codexify:queue:chat`)

### 2. Route seam proof — RAG trace retrieval

`tests/routes/test_chat_profile_trace.py`

Proved through `GET /chat/{thread_id}/debug/rag-trace/latest`:

- `test_rag_trace_uses_persisted_candidate_for_completed_task` — trace retrieved from candidate metadata path includes `documents`, `graph`, and `payload_summary`
- `test_rag_trace_remains_empty_without_completed_evidence` — empty state returned when no trace exists
- `test_rag_trace_does_not_bleed_across_threads` — thread isolation verified

### 3. Broker seam proof — source_mode and widen_reason

`tests/core/test_context_broker_source_mode.py`

Proved through `ContextBroker.assemble(...)`:

- `test_project_source_widens_only_within_same_project` — `source_mode=project`, `widen_reason=insufficient_thread_hits`
- `test_personal_knowledge_widens_same_user_across_projects` — `source_mode=personal_knowledge`, `widen_reason=explicit_personal_knowledge`
- `test_low_confidence_thread_hits_trigger_project_widening` — `source_mode=project`, `widen_reason=low_confidence_thread_hits`
- `test_strong_thread_hits_keep_trace_stable_without_widening` — `source_mode=project`, `widen_reason=none`

### 4. Completion-service seam proof — source_mode fallback

`tests/core/test_chat_completion_service_source_mode_fallback.py`

Proved through the live completion-service assembly path:

- Missing or malformed `origin` falls back to `project`
- `personal_knowledge` survives parsing and reaches broker assembly

### 5. New focused proof — source_mode and widen_reason through retrieval path

Added `test_rag_trace_candidate_preserves_source_mode_and_widen_reason` to `tests/routes/test_chat_profile_trace.py`:

- Verifies that when a trace with `source_mode` and `widen_reason` is stored via the candidate path, it is returned intact from `get_latest_rag_trace`
- This proves the retrieval path does not strip these fields

## What Remains Code-Path-Only Or Unproven Live

- I did not run a full browser-to-worker live proof with real embeddings spanning multiple projects.
- Frontend diagnostics surfaces (GuardianChat, MemoryBrowser) are code-verified but not exercised in a live browser session.
- The trace is persisted via thread metadata, which is proven through the candidate retrieval path test.

## Limitation

The exact limitation in this environment is runtime scope, not uncertainty in the seam behavior:

- proven here: route, completion-service, broker, and trace retrieval seams
- not proven here: full browser-to-worker live runtime with real stored embeddings

## Result

The RAG trace path is operator-legible and truthworthy:

- `source_mode` is visible at the broker seam and preserved through retrieval
- `widen_reason` is visible at the broker seam and preserved through retrieval
- Latest trace is retrievable per-thread after completion
- Empty state is truthful for untouched threads
- No trace bleeding across threads
- Both chat and settings diagnostics surfaces bind to `activeThreadId` for trace fetching