# 2026-03-31 Source Selector Hardening Proof

## Scope

This artifact records the strongest truthful supported-path proof for the new chat `Source` selector after the post-implementation hardening pass.

- Validation source of truth: repo-supported backend proof seams exercised from this checkout
- User-facing scope under proof:
  - `Project` keeps widening project-local only
  - `Personal Knowledge` can widen across same-user projects
  - active-thread-first behavior still holds in both modes
  - `/chat/{thread_id}/complete` response exposes `source_mode`
  - broker diagnostics expose `widen_reason`
- Out of scope:
  - browser-driven composer interaction
  - a full worker-queue round trip against a running multi-project embedding corpus

## Exact Commands Run

```bash
pytest -v \
  tests/routes/test_chat_source_mode.py \
  tests/core/test_chat_completion_service_source_mode_fallback.py \
  tests/core/test_context_broker_source_mode.py
```

## What Was Proven In A Supported Runtime Seam

### 1. Route seam proof

`tests/routes/test_chat_source_mode.py`

Proved through the FastAPI route seam:

- `POST /chat/{thread_id}/complete` includes normalized `source_mode` in the response body
- omitted, blank, and invalid request values safely normalize to `project`
- the temporary transport bridge still encodes normalized `source_mode` into `ChatCompletionTask.origin`

### 2. Completion-service seam proof

`tests/core/test_chat_completion_service_source_mode_fallback.py`

Proved through the live completion-service assembly path:

- missing `origin` falls back cleanly to `project`
- malformed `origin` falls back cleanly to `project`
- invalid `source_mode` values inside `origin` fall back cleanly to `project`
- a valid `personal_knowledge` origin value survives parsing and reaches broker assembly
- malformed or absent `origin` does not throw or break `build_messages_for_llm`

This is the supported local proof that the temporary `origin` bridge remains safe while it exists.

### 3. Broker seam proof

`tests/core/test_context_broker_source_mode.py`

Proved through `ContextBroker.assemble(...)`:

- active thread is always searched first
- `Project` widening stays within same-user, same-project sibling threads
- `Personal Knowledge` can widen across same-user projects
- `Personal Knowledge` marks `widen_reason=explicit_personal_knowledge` whenever widening beyond the active thread executes, even if the first widened hit comes from a same-project sibling
- archived, `exclude_from_identity`, and other-user threads are excluded
- trace output keeps both `source_mode` and `widen_reason` operator-visible

## What Remains Code-Path-Only Or Unproven Live

- I did not run a browser proof of the composer control in this hardening task.
- I did not run a full queue-backed worker completion against a live local corpus containing multiple real projects and persisted embeddings.
- Because of that, this artifact proves the supported backend seams truthfully, but not a full end-to-end operator session from browser click through queued completion worker output.

## Limitation

The exact limitation in this environment is runtime scope, not uncertainty in the seam behavior:

- proven here: route, completion-service, and broker seams
- not proven here: full browser-to-worker live runtime with real stored embeddings spanning multiple projects

## Result

The post-hardening pass leaves the `Source` selector behavior operator-legible and safely bounded:

- safe default remains `project`
- `source_mode` stays visible at the route seam
- `widen_reason` stays visible at the broker seam
- the temporary `origin` bridge is still in use, but its fallback behavior is now explicitly covered
