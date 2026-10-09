# Bounded tool-loop deadline admission and failure truth

Date: 2026-10-03. Baseline: `a97be7fe7`. Classification:
`AUTHORIZED_IMPLEMENTATION` under the ordinary chat reliability Goal and
ADR-087's immutable accepted deadline. Complete qualification remains `HOLD`.

## Atomic Task Spec and causal seam

Prevent the bounded tool loop from beginning command work after its parent's
work deadline. Preserve the canonical accepted-task deadline error across
synchronous/asynchronous command invocation instead of reclassifying it as a
tool failure. Preserve advertised-subset authority, one-command limit,
read-only invocation policy, identity, legacy tasks, and successful in-budget
continuation. Bound this task to the shared service, a focused fixture, and this
receipt. It does not authorize a new command cancellation mechanism.

The real shared service checked the parent deadline before provider attempts,
but did not check it between a normalized tool decision and `execute_invoke`.
Argument/authority preparation could consume the remaining time. The generic
command exception handler also wrapped typed or reconstructed canonical
deadline exceptions as `ToolLoopExecutionError`. An ordinary command error
observed after expiry similarly displaced the parent's authoritative outcome.

## Repair

`guardian/core/chat_completion_service.py` captures the immutable accepted
snapshot once for the bounded loop. It checks remaining work time after the
tool decision and immediately before invocation. It checks again after command
return or a non-deadline command exception. Typed/serialized canonical deadline
HTTP exceptions pass through unchanged. New parent deadline failures record
`attempted=true`, since the first provider attempt already ran; they cannot
present the task as completed or begin follow-up generation.

No provider, model, command, actor, advertised subset, write permission,
confirmation, idempotency, persistence, or automatic replay policy changed.
No new protocol token or ADR was introduced. Successful plain answers retain
the existing terminal path, including its reserve for already-completed work.

## Proof and validation

`tests/core/test_chat_tool_admission_deadline.py` runs the real shared
completion/tool loop with the existing qualification-shaped synthetic Whoosh'd
structured response and synthetic advertised command `op::lookup_widget`.
Provider generation and command execution are fixture seams; no actual model,
Whoosh'd process, tool runtime, Redis, or production database is qualified.

The immutable task has one second of synthetic remaining work time. Cases
cover expiry during normalization, expiry during argument preparation,
typed/serialized command deadline exceptions in synchronous/asynchronous
paths, ordinary command errors at expiry, successful command return at expiry,
in-budget and legacy continuation, and ordinary command failure before expiry.
Assertions retain timestamps, block late invocation/follow-up generation, keep
canonical error identity, and preserve the read-only/confirmation flags.

- Baseline first 11 cases: **8 failed, 3 passed**.
- Additional late-success baseline probe: **2 failed**.
- Repaired focused fixture: **13 passed**.
- Service/worker tool loops, provider transport convergence, terminal integrity,
  local streaming/non-streaming deadlines, worker rescue and queue deadlines:
  **120 passed**, zero skips/failures in the retained JUnit report.
- New test Ruff, Python compilation, and `git diff --check`: **passed**.
- Whole-service Ruff: **failed on 15 pre-existing findings**. Immutable baseline
  source checked via stdin has the same normalized finding multiset. No unrelated
  lint repair or whole-service lint success is claimed.

Commands from repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -o addopts='' -q \
  tests/core/test_chat_tool_admission_deadline.py \
  tests/core/test_chat_completion_service_tool_loop.py \
  tests/workers/test_chat_worker_tool_loop.py \
  tests/providers/test_tool_turn_transport_convergence.py \
  tests/core/test_completion_terminal_integrity.py \
  tests/core/test_chat_nonstream_accepted_deadline.py \
  tests/core/test_chat_stream_accepted_deadline.py \
  tests/workers/test_chat_worker_rescue_deadline.py \
  tests/workers/test_chat_worker_queue_deadline.py
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m ruff check \
  tests/core/test_chat_tool_admission_deadline.py
python3 -m py_compile guardian/core/chat_completion_service.py \
  tests/core/test_chat_tool_admission_deadline.py
git diff --check
```

Evidence: `/private/tmp/codexify-chat-tool-deadline-a97be7fe7-20261003/`.
Baseline/final logs and XML, immutable service source, and lint comparison are
retained. The neighboring loopback HTTP deadline fixture logged a connection
reset in its server thread during forced transport closure; pytest exited zero
and the scoped JUnit report contains no errors. This receipt does not claim
thread-warning-free test infrastructure.

## Whole-path re-evaluation and limits

The tested shared service now prevents late command admission and preserves
deadline truth for worker failure projection. The worker's existing canonical
deadline handling and focused regression group remain compatible. This does
not prove live terminal event delivery, durable deadline receipts, browser
deadline presentation, or actual tool execution against the supported runtime.

An already-running command remains unbounded by this repair: no cooperative
cancellation/quiescence or finite command-child transport was implemented.
Context/retrieval, cloud children, PostgreSQL, persistence, events, rollback,
cleanup, and finite drain still need envelope proof/repair. ADR-087 Slice B/C/D
are not declared complete. The retained runtime still runs the earlier
integration source; its canary does not qualify this new service change.

The intermittent cancellation failure remains unlocalized after the bounded
trace probe. Partial-output execution-field meaning and active-worker-loss
reconciliation remain unresolved. Documentation follow-through is this receipt;
no current-state promotion, runtime mutation, push, merge to main, deployment,
or memory update occurred.
