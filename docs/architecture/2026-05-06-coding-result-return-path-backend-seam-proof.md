# Coding Result Return Path Backend-Seam Proof - 2026-05-06

## Scope

Backend-seam verification of the Guardian-mediated coding-agent result return path.

In scope:

- Guardian intake of coding-agent execution metadata
- durable result persistence back into the originating source thread
- source message and attempt lineage in persisted metadata
- failure handling that avoids creating misleading success messages

Out of scope:

- live Compose proof
- repair of the worker runtime artifact that provides `/app/codex_runner/src/agent-wrapper.js`
- provider routing changes
- new autonomous coding-agent behavior

## What Was Proven

- Successful coding-agent results persist a `coding_result` assistant message in the same thread that originated the request.
- Partial-success coding-agent results also persist a `coding_result` assistant message.
- Persisted result metadata includes:
  - `source_message_id`
  - `coding_task_id`
  - `attempt_id`
  - `adapter_kind`
  - `coding_result_status`
  - `files_changed`
  - `artifacts`
  - `adapter_session_ref`
  - `result_captured_by_guardian`
- The original user-authored source message is not mutated.
- Failed coding-agent results do not create a misleading success assistant message.
- Failure evidence still binds the run back to the source thread and attempt id in the task-event stream and durable artifact payload.

## Validation Commands

```bash
./.venv/bin/python -m pytest -v guardian/tests/workers/test_coding_worker.py
./.venv/bin/python -m pytest -v guardian/tests/routes/test_agent_orchestration_events.py -k preserves_source_thread_lineage
./.venv/bin/python scripts/validate_docs.py
git diff --check
```

## Result Interpretation

Backend-seam proof: yes.

Live supported-path proof: no.

## Known Gaps

- The live Compose worker-image path still needs the runtime artifact that provides `/app/codex_runner/src/agent-wrapper.js`.
- The supported live-path proof remains pending until the corrected worker image is exercised end to end.
