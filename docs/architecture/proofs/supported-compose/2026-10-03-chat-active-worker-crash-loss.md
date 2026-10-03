# Active chat worker crash loss proof

Date: 2026-10-03. Classification: `PROOF_REQUIRED`. Evaluated path:
`v1-local-core-web-mcp` retained Compose project
`codexify_chat_proof_f091_20261002`. The test used a disposable local chat
thread and a real ordinary API completion. No task was replayed automatically;
the worker was manually restarted after the crash. This is a verified failure,
not a qualification pass.

## Atomic Task Spec

Workflow lane: `proof`.

Context: prior retained-Compose proof covered a turn queued while an idle worker
was stopped. It did not establish recovery after the worker had destructively
dequeued an active task. The ordinary chat queue uses Redis `BRPOP`, and the
durable `chat_completion_attempts` row records identity and acceptance but no
execution state.

Goal: determine whether a task accepted and dequeued by `worker-chat` receives
durable terminal evidence, safe lock cleanup, and explicit-retry availability
when the worker process is killed before completion.

Files:
- `guardian/queue/redis_queue.py`
- `guardian/workers/chat_worker.py`
- `guardian/db/models.py`
- `guardian/db/migrations/versions/c9f3e2a7b601_add_chat_completion_attempts.py`
- `guardian/core/chat_completion_service.py`
- `docs/architecture/adr/001-queue-based-completion-acceptance-model.md`
- `docs/architecture/adr/002-dual-state-machine-model.md`
- `docs/architecture/adr/003-message-identity-vs-request-identity.md`
- `docs/architecture/adr/087-accepted-chat-task-execution-deadline.md`
- `docs/architecture/adr/091-durable-chat-completion-attempt-authority.md`
- `docs/architecture/chat-runtime-contract.md`
- `docs/architecture/00-current-state.md`
- `docs/architecture/proofs/supported-compose/2026-10-03-chat-active-worker-crash-loss.md`

This change belongs in the chat acceptance, worker, and durable attempt
recovery boundary; this proof makes no implementation change.

Acceptance criteria:
- Record the accepted request/task/thread/turn identity and the exact failure
  point independently from Redis queue, event, lock, transcript, and Postgres
  state.
- Restore `worker-chat` and leave the retained stack healthy after the proof.
- Stop before choosing automatic replay, orphan timing, or a new durable
  lifecycle authority.

Source evidence:
- ADR-001, ADR-002, ADR-003, ADR-087, ADR-091, and the Chat Runtime Contract.
- Retained Compose API at `127.0.0.1:18888`; Redis and Postgres in the named
  project.
- Current worktree and Compose overlay have identical whole-file hashes for
  `guardian/queue/redis_queue.py` and identical `_run_chat_task` and
  `run_forever` function hashes for `guardian/workers/chat_worker.py`.

## Runtime conditions and action

Before the test, the supported-profile `/health` endpoint returned HTTP 200
with status `ok`; `worker-chat` was running with restart policy
`unless-stopped`; the chat queue length was zero; and no canonical
`turn_lock:*` keys existed.

The API created thread `32`, persisted authored user message `72`, and accepted
request `req_crash_759e31849235` as task
`4ab0d289-ba46-46cc-9900-7c46b2f9b50e` for turn
`61377848-45a5-4098-8f17-9082a88ec02b`. Redis `XRANGE` showed the task had been
dequeued and entered worker execution. `worker-chat` was killed immediately
after observing `task.running` and before any terminal event or assistant
message.

## Observed state after the worker restart

| Surface | Observed value |
| --- | --- |
| Redis task events | `task.state`, `task.running`, `task.created`; no terminal event |
| Redis chat queue | Empty after worker restart |
| Postgres attempt | Request/task/thread/turn matched; `accepted_at` set; no execution-state or terminal-status column |
| Durable transcript | One user row (`72`); no assistant row |
| Canonical turn lock | `turn_lock:32` remained; `PTTL` was `758613` ms after restart and readback |
| Worker process | `docker kill` left the container exited with restart count `0` despite `unless-stopped`; manual `docker start` restored it to `running` |
| Explicit retry | Same thread and turn with a new request ID returned HTTP `429`, detail `turn_in_flight`; no second attempt was accepted |
| Stack restoration | Backend health returned HTTP 200; worker running; queue still empty |

The original attempt remains accepted without terminal status. Worker startup
did not requeue or terminalize it. The completion UI was not browser-observed
during this proof; the last persisted event remains nonterminal. The retry
failure is a fresh API observation, not an inference from unit tests.

## Authority frontier

The governing sources establish that queue acceptance is not completion
(ADR-001), provider and request states remain distinct (ADR-002), authored
message identity survives retries while each attempt has a new request identity
(ADR-003), deadline failure is final for the same attempt (ADR-087), and
`ORPHANED` plus explicit new-identity replay exist in the Chat Runtime Contract.
ADR-091 intentionally implements durable request/task/thread/turn binding and
does not implement the complete request-state or replay lifecycle.

Those sources do not decide how this runtime proves an individual worker's
death while preserving safety across multiple workers, whether to terminalize
as `ORPHANED` immediately or wait for the immutable accepted-task deadline,
where the terminal attempt state is durably authoritative, or how a delayed
assistant persistence/terminal event is reconciled. Automatic silent replay is
not an available default because ADR-003 forbids it and the task payload is
currently not durably stored.

Materially distinct policy choices remain:

1. **Deadline-bound reconciliation:** preserve the existing worker lease until
   the accepted deadline expires; then reconcile any assistant message and
   terminal event, or mark the attempt failed/retryable and allow an explicit
   new attempt. This is the smaller change but can leave a crashed turn pending
   for about 13 minutes.
2. **Confirmed-worker-loss orphaning:** add task-scoped worker ownership/lease
   evidence and durable attempt state. Once the owning worker generation is
   confirmed dead, persist `ORPHANED`, publish terminal evidence, release the
   lock with fencing, reconcile any already-persisted assistant, and allow an
   explicit retry with the same authored message and a new request identity.
   This closes the user-visible wait sooner but expands the durable recovery
   mechanism.

The smallest human decision is which crash policy to authorize: wait for the
accepted deadline before exposing a retryable failure, or add task-scoped
worker-loss evidence and orphan immediately after confirmed process loss. In
either option, automatic replay remains disabled. No files outside this proof
and its current-state entry were changed by this proof task.
