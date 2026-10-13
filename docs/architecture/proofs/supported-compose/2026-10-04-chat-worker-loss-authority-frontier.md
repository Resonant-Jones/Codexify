# Worker-loss recovery authority frontier — 2026-10-04

## Classification and completed work

Development Operator Level 0, **HUMAN_DECISION_REQUIRED**, REPORT. The preceding
Goal continuation produced verified progress; this audit does not substitute
an authority decision for a repair. Frozen clean isolated branch
`codex/chat-postgres-terminal-deadline-20261003` at `a7ad1556c`.

Completed since the parent-owned snapshot authorization:

- `1d7d7128f`: accepted native vector construction/search physical deadline
  boundary, coherent parent-owned FAISS capture, immutable model binding and
  tensor attestation. Host and retained-worker focused suites each pass 37
  tests; private actual-worker native FAISS/Chroma reference parity and expiry
  pass. The overlapping fixture run OOM-killed the backend; the failure and
  subsequent recovery are explicitly preserved, not promoted to conformance.
- `94db56ca1`: fresh ordinary browser turn on repaired source, thread 37,
  authored message 70, assistant 71, duration 51,057 ms. SQL/API/receipt/event
  identity agrees, no model fallback, exact reply visible before/after reload,
  33 heartbeat samples and independent cleanup/custody validation pass.
- `a7ad1556c`: loaded native-parent snapshot mechanism passes on host CPU with
  the same cached model/native library versions. Parent additions remain
  authoritative; snapshot parity and deadline cleanup pass. Platform and fork
  warnings are explicitly bounded; it is not Linux concurrency qualification.

Full current-main/supported-Compose failure/recovery/retry/restart/shutdown
qualification remains **HOLD**. The Goal remains active. No merge, push,
deployment or release promotion was authorized or performed.

## Refreshed governing evidence

[Chat Runtime Contract](../../chat-runtime-contract.md) explicitly states:

> its orphan timing, ownership proof, and explicit-retry policy remain unresolved.

It also requires unknown/nonterminal receipts to remain unconfirmed, durable
assistant completion to take precedence, no inferred failure from an observer
threshold, and explicit new request identity for replay. Accepted failure or
cancellation fences later success for that exact attempt.

[ADR-087](../../adr/087-accepted-chat-task-execution-deadline.md) requires the
original immutable server-owned 720/60 envelope, non-sliding child bounds and
controlled deadline failure. It explicitly says:

> A crash must not be presented as a controlled deadline failure.

[ADR-091](../../adr/091-durable-chat-completion-attempt-authority.md) supplies
request/task/thread/turn resource authority and explicitly excludes the complete
replay/orphan/request-state model. Redis queue/lock/event/debug fields cannot
establish ownership. [Development Operator Goal](../../../Ops/codex-development-operator-goal.md)
requires an Authority Frontier Report when timing, ownership or state semantics
remain materially undecided. Main's October 4 current-state still marks full
qualification HOLD; branch receipts do not promote that release gate.

Current code retains destructive Redis `BRPOP` in `guardian/queue/redis_queue.py`.
`guardian/workers/chat_worker.py` records worker-controlled terminals and performs
owner-guarded lock cleanup in its live `finally` path; a vanished process cannot
execute that path. Current `ChatCompletionAttempt` stores identity, acceptance,
assistant link and terminal event kind, but no task-scoped worker generation,
lease or orphan diagnostic. The current retained database schema confirms these
fields at the accepted migration. Receipts in `guardian/routes/chat.py` prefer
the durable assistant link, then durable failed/cancelled kind, then Redis
terminal observation; they do not manufacture worker-loss truth.

A further persistence constraint matters for deadline-bound recovery:
`mark_chat_completion_attempt_accepted` sets its database timestamp after queue
acceptance using a new server clock read. It does not persist the queue payload's
original immutable work/terminal deadline snapshot. That timestamp alone is not
proof of the lost task's original envelope. A selected deadline-bound policy
must preserve and use the exact original server envelope for future tasks;
it must not invent or silently backfill historical deadlines from Redis or a
later timestamp. This audit makes no schema or acceptance-semantic change.

## Historical failure rechecked, without repeating a crash

Private Task Spec, read-only queries, current schema/runtime observations and
validation are retained at:
`/private/tmp/codexify-chat-worker-loss-frontier-a7ad1556c-20261004/`.

The [controlled crash proof](./2026-10-03-chat-active-worker-crash-loss.md)
recorded request `req_crash_759e31849235`, task
`4ab0d289-ba46-46cc-9900-7c46b2f9b50e`, thread 32 and turn
`61377848-45a5-4098-8f17-9082a88ec02b` after destructive dequeue.
A fresh read of that historical project's database still finds acceptance,
no completed-message link, and one user transcript row without an assistant.
Its schema is older and lacks the current durable terminal-event column.
This confirms that old unresolved record; it does **not** claim a new crash test
or current repaired-stack execution proof. No retry, crash, lock mutation,
queue clear, application edit or historical backfill was performed.

## Smallest human decision

Which worker-loss recovery policy is authorized?

1. **Deadline-bound reconciliation**: retain the original non-sliding envelope,
   wait until its terminal deadline, reconcile exact durable completion or
   terminal truth, then persist an honest lost-worker outcome if unresolved,
   fence late writes and permit only explicit new-identity retry. This avoids
   a new worker-generation authority but leaves crash ambiguity visible for up
   to the original envelope. It must not label a crash controlled deadline
   execution or reconstruct an original envelope from a later receipt timestamp.
2. **Confirmed task-scoped worker-loss recovery**: retain durable ownership of
   each active task by a specific worker generation, establish confirmed loss,
   reconcile any committed assistant, persist the authorized orphan outcome,
   fence late writes, release the matching lock and allow explicit retry sooner.
   This expands durable ownership/recovery semantics and needs that explicit
   authorization before implementation.

Both preserve authored message identity, use a new request/task for explicit
retry, retain prior completion evidence, reject automatic silent replay, and
require atomic late-write/lock fencing. The affected boundaries are acceptance,
durable attempt storage, worker ownership/lifecycle, terminal publication,
receipt/UI projection and retry admission. A pending user question presents
these two choices; silence or elapsed time is not approval.

## Boundary, validation and custody

Only this documentation receipt was changed after the last authorized
implementation/proof boundary. No new ADR, recovery implementation, durable
lifecycle field, worker lease, queue or terminal token was introduced.

Current repaired retained stack stays healthy and idle, queue zero, no locks,
positive heartbeat TTL, evaluation/system queues **34/17** unchanged. Backend
and worker lifecycle match the ordinary-turn proof; current source still matches
its 1,138-file matrix. Main remains `016352131`, with its unrelated staged
dev-log deletion preserved. Earlier native/serializer groups, sampler, Vite,
owned browser tab and copied test root were already independently confirmed
terminal/absent; this audit starts no such process or application turn.

Read-only source/schema/historical-record checks and independent current-runtime
custody validation passed. `python3 scripts/validate_docs.py`, local Markdown
link checks and `git diff --check` passed before the scoped docs commit. No
additional automated runtime suite applies to this docs-only frontier report.
Scoped commit is reported in closeout. The human decision is required by the
explicitly deferred governing contract, not by a hypothetical approval rule.
