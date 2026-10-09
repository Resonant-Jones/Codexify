# Accepted deadline propagation through context — 2026-10-04

## Repair and authority

Development Operator Level 0, `AUTHORIZED_IMPLEMENTATION`, EXECUTE/PROOF.
ADR-087 makes accepted work expiry fatal and forbids replacement child work
beyond it. ADR-001/002/003/038/069 and the Chat Runtime Contract preserve queue
acceptance, identity, terminal truth and release boundaries. This repair is
aligned with those contracts; no new ADR or runtime token is introduced.

Context assembly previously caught `AcceptedChatTaskDeadlineExceeded` as an
optional semantic/history/memory/context error. It could continue assembly,
widen retrieval, start legacy memory fallback or construct a fallback prompt
instead of returning the parent failure to the completion caller.

Explicit rethrows now precede broad optional-error catches in the relevant
context/retrieval functions: **28** in `guardian/context/broker.py`, **2** in
`guardian/memoryos/retriever.py`, and **11** in
`guardian/core/chat_completion_service.py`. They preserve the same exception
instance, detail and deadline authority. Ordinary optional errors retain their
existing behavior. No envelope, attempt, provider, model, queue or persistence
semantics are changed.

The repair started at clean `0f03bab57120f3ccc5b47a6829c428c632cca15b`.
Main and its unrelated staged Dev Log deletion were untouched. No merge, push
or deployment occurred. Full supported qualification remains **HOLD**.

## Regression evidence

New `tests/core/test_context_deadline_propagation.py` covers primary semantic
search, history, documents, personal facts, memory assembly, legacy fallback,
MemoryOS, shared prompt building and return to the completion caller before
provider execution. It asserts exact exception identity, no subsequent fallback
or provider call, and unchanged ordinary optional-error behavior.

The initial host baseline had ten failures and two passing optional-error
controls. One memory fixture had not enabled its memory-store gate. The first
post-repair host run had 100 passing checks and that one fixture failure. The
fixture was corrected; no production behavior was changed for it. A corrected
baseline on the actual worker's old source independently reproduced **ten
failures, two passes, zero errors/skips** before the source refresh.

Final checks: **101 host passes**, **101 actual worker passes**, zero failures,
errors or skips. Host/worker durations were 8.517/10.222 seconds. The suite
includes broker depth/source modes, MemoryOS retrieval, shared source-mode
fallback and the new regressions.

Host command, from repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest tests/core/test_context_deadline_propagation.py tests/core/test_context_broker_depth.py tests/core/test_context_broker_source_mode.py tests/memoryos/test_retriever.py tests/core/test_chat_completion_service_source_mode_fallback.py -q
```

The same five files and exact necessary test helpers were copied into the
owned worker fixture and run with its Python/pytest. Initial/final outputs and
XML are retained.

## Supported-runtime native observation

Fresh evidence root:
`/private/tmp/codexify-chat-context-deadline-propagation-0f03bab57-20261004/`.
The Task Spec preceded edits. Artifacts include source-before copies, guard
counts, tests, lint baseline/current output, native source/result/process,
refresh/health/source matrix, cleanup and independent validation.

At chat queue zero, no turn locks and fresh idle heartbeat, only the three
changed runtime files were copied into the retained source snapshot. Backend
and worker were restarted once. All **1,136** tracked Guardian/backend Python
files then matched checkout, snapshot and both containers. Migration remained
`d4c69e03a712`.

A private broker fixture on the actual worker executes native PostgreSQL
`SELECT pg_sleep(1)` in its history-fetch seam with a valid immutable envelope
aged to 0.15 seconds remaining work. PostgreSQL expiry escaped the broker in
**0.151873 seconds** with `CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED`. The only
recorded child was history; later retrieval did not start. Completion truth
remained accepted true, attempted/fallback_attempted/executed/completed false.
No model was instantiated and no application request/message/attempt was
created. This is a controlled native propagation proof, not a new full turn.

Evaluation queue stayed **31**. System queue changed **11→12** from backend
startup warmup; it was retained. Chat queue stayed zero and turn locks empty.
General/chat health remained `ok`/`healthy`, with fresh idle heartbeat and
positive TTL. Thread 34 still held exact messages **64/65** and its prior
successful assistant marker.

The successful durable attempt still links assistant **65**, with nullable
`terminal_event_type` unchanged from the original browser SQL receipt. The
first independent validator wrongly expected that field to equal
`task.completed`; its original source/error are retained. The corrected
validator compared actual durable values to the original receipt and passed.
Cleanup had already completed and was not repeated for this correction.

Nine copied test/helper files were hash-verified before removal of the exact
owned folder `/tmp/codexify-context-deadline-6a243902`. An independent check
confirmed absence and only the application Python process remaining. Native
probe and corrected validator exited 0.

## Other validation and limitations

Ruff passed for the broker and new test file. MemoryOS/shared service still
have **4/15 inherited findings**; exact logical-path baseline comparison found
zero new findings. They were not repaired outside this Task.

- `python3 /private/tmp/codexify-chat-context-deadline-propagation-0f03bab57-20261004/validate.py` — passed after the documented receipt-assumption correction.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — passed.
- `git diff --check` — passed.

This closes fatal deadline propagation through the tested context seams. It
does not implement native vector child bounds, qualify every context operation,
prove a fresh browser/chat turn after this repair, establish active-worker-loss
recovery or close restart/shutdown qualification. Prior completed readback
remains consistent, but new supported-path/browser evidence is still required.
The next obligations are that fresh path proof and production native vector
bound integration. The Goal stays active and qualification remains HOLD.
