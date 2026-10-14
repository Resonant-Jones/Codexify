# Current-main optional trace completion repair

Date: 2026-10-02. Baseline: `20bf69b88b6651b0d1d47916b04f3b684720f743`.
Branch: `main`. Authority: active ordinary-chat Goal and Development Operator
Level 0. Architecture-impact task: proof before repair, aligned with existing
ADR-001/003 and chat-runtime success/persistence boundaries. No new ADR.

## Causal proof

`_run_chat_completion_task_compat` used `trace_fallback` during final result
assembly without defining that name anywhere in the worker module. A dictionary
result trace bypassed the faulty expression. Absent/non-dictionary trace reached
it and raised NameError following otherwise successful generation.

Initial nonlocal assembly probe: four failed, two dict-trace controls passed.
Expanded local and nonlocal assembly probe: **eight failed, four passed**.
Every failure was `NameError: name 'trace_fallback' is not defined`. Both
persistence-enabled and persistence-disabled cases were affected.

## Repair and invariants

Use `trace`, the actual context trace already in scope, for the fallback copy
when it is a dictionary. Preserve an existing final dictionary trace. Absent or
non-dictionary trace remains absent; no trace, success, or message ID is invented.

The regression crosses local/nonlocal assembly, absent/string/dict trace, and
persistence disabled/enabled. Disabled persistence returns successful generation
with `executed=true`, `completed=false`, no message ID, and zero inserts. Enabled
persistence inserts exactly one assistant row through the controlled database
seam, returns its ID, and only then marks completion true. No provider, model,
queue, identity, token, fallback, retry, or persistence contract changed.

## Validation

From repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -q \
  tests/workers/test_chat_worker_missing_trace.py \
  guardian/tests/workers/test_chat_worker_completion_semantics.py \
  tests/core/test_completion_terminal_integrity.py \
  tests/workers/test_chat_worker_lifecycle_events.py \
  tests/workers/test_chat_worker_tool_loop.py
```

Result: **56 passed**, exit 0. Includes all 12 new regression/control cases and
neighboring successful terminal, provider failure, cancellation, assistant
persistence failure, lifecycle, and tool-loop tests. `git diff --check`: passed.

External artifacts:
`/private/tmp/codexify-main-missing-trace-20bf69b88-20261002`:
`before.xml`, `before.log`, `before-local.xml`, `before-local.log`, `after.xml`,
`after.log`. These are local proof artifacts, not published records.

## Closeout and remaining qualification

Files: worker, missing-trace regression suite, and this receipt.
Documentation follow-through: this receipt only. No release/current-state or ADR
change. Production diff is two references at final assembly.

Evidence class: proven-test with controlled context, generation, event, embedding,
and database seams. This does not prove live Whoosh'd, PostgreSQL persistence,
browser receipt, or complete supported-Compose operation. Earlier separate-branch
runtime proof remains tied to its evaluated source. Current-state remains HOLD.

Re-evaluation of the current user path still finds task-terminal handling in
GuardianChat that does not verify task/thread ownership before changing inference
state, and stream callbacks without a current-stream fence. Immutable accepted
queue-age/child deadline enforcement and safe restart/drain also remain to be
proved on this branch. The full Goal remains active and incomplete.

KB recommendation: optional diagnostic trace must not gate canonical successful
terminal validation and assistant persistence; test missing trace independently
of provider outcome and of whether persistence is enabled.
