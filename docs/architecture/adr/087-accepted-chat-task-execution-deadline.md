# ADR-087: Accepted Chat Task Execution Deadline

**Status:** Accepted

**Date:** 2026-09-12

**Approver:** Resonant Jones

## Approval and execution boundary

Resonant Jones explicitly dispatched the task "Define a finite accepted
chat-task execution deadline" for execution. This ADR accepts the bounded
runtime contract below. It authorizes no source, configuration, database,
provider, queue, worker, Compose, or live-runtime change.

```text
ACCEPTED_TASK_EXECUTION_ENVELOPE_REQUIRED=true
ACCEPTED_TASK_EXECUTION_ENVELOPE_IMPLEMENTED=false
FINITE_ACCEPTED_TASK_DRAIN_BUDGET_PROVEN=false
SAFE_OPERATOR_STOP_PROVEN=false
APPLICATION_RUNTIME_RECOVERY_PROVEN=false
PRIVATE_PREVIEW_RELEASE_READY=false
```

This decision extends the queue-acceptance boundary in
[ADR-001](./001-Queue-Based-Completion-Acceptance-Model.md), the dual request
and provider state model in
[ADR-002](./002-Dual-State-Machine-Model.md), the message/request identity
boundary in [ADR-003](./003-Message-Identity-vs-Request-Identity.md), and the
transport-observation distinction in
[ADR-038](./038-Chat-Transport-Visibility-and-Adaptive-Stream-Recovery-Contract.md).
It remains inside the Beta support and evidence discipline of
[ADR-069](./069-codexify-beta-runtime-support-boundary.md). The
[chat runtime contract](../chat-runtime-contract.md) remains the canonical
request-state vocabulary; this ADR narrows only hard-deadline semantics.

## Context

Private Preview shutdown classification proved that operator stop can leave
`worker-chat` alive until Docker exhausts its grace period and sends `SIGKILL`.
That forced exit was not an out-of-memory kill. It can interrupt an accepted
task and bypass worker cleanup. Adding signal handlers or extending a static
Compose grace period cannot produce a safe drain while accepted work can
continue for an unbounded wall-clock duration.

The current evidence boundary is:

```text
PRIVATE_PREVIEW_CHROMA_RUNTIME_QUALIFIED=true

FORCED_SIGKILL_AFTER_GRACE_TIMEOUT=true
WORKER_OOM_KILLED=false

FORCED_KILL_CAN_INTERRUPT_ACCEPTED_TASK_LIFECYCLE=true
FORCED_KILL_CAN_BYPASS_WORKER_CLEANUP=true

ACCEPTED_CHAT_TASK_TOTAL_DEADLINE_IMPLEMENTED=false
FINITE_ACCEPTED_TASK_DRAIN_BUDGET_PROVEN=false
SAFE_OPERATOR_STOP_PROVEN=false
```

The supported Private Preview chat path currently selects the local Whoosh'd
provider with `qwen3.8-27b-4bit` and admits one worker-owned chat task at a time.
Its generic provider request setting is 60 seconds, while the Qwen
extended-thinking local stream uses a 10-second connection timeout and a
300-second read-inactivity allowance. Those settings constrain some periods of
inactivity, individual Redis operations, or a loopback command request. They do
not compose into one absolute deadline covering queue age, retrieval,
generation, tools, persistence, events, and cleanup.

### Current runtime constraint census

This census records source-path evidence at the decision revision. It is not
implementation proof for the contract accepted below.

| Accepted-task surface | Current classification | Evidence and constraint |
| --- | --- | --- |
| Provider streaming | Partially bounded | The local provider uses finite connect and read-inactivity timeouts, but continuing frames can keep `iter_lines()` alive indefinitely. There is no total stream wall-clock deadline. |
| Provider/tool-loop recursion or iteration | Partially bounded | The current completion path permits only a bounded two-provider-call/one-command shape, and loopback HTTP has a finite request timeout. Child duration does not inherit one parent deadline, and provider streaming can still escape the finite iteration count. |
| Context/retrieval work | Unbounded | Synchronous chat-log and vector-store work has no accepted-task parent deadline or proven finite operation ceiling. |
| PostgreSQL connection establishment | Unbounded | The current `psycopg.connect()` path has no proven effective connect deadline. |
| PostgreSQL statement execution | Unbounded | Accepted-task statements have no proven effective statement deadline. |
| PostgreSQL lock waiting | Unbounded | Accepted-task database work has no proven effective lock-wait deadline. |
| Assistant-message persistence | Unbounded | Persistence crosses the unbounded PostgreSQL connection, statement, and lock surfaces. |
| Terminal event publication | Partially bounded | Direct Redis operations have finite socket limits and bounded reconnect attempts, but the full terminal sequence and its durable/outbox participation do not inherit one finite parent deadline. |
| Turn-lock cleanup | Partially bounded | Canonical release uses bounded Redis operations, but cleanup occurs only after upstream work returns and has no accepted-task parent deadline. |

The canonical turn-lock implementation currently defaults to a 180-second
lease. It exposes renewal machinery, but the accepted chat-completion path does
not currently prove deadline-aware renewal. That lease is shorter than the
envelope selected here and cannot remain the implementation default without a
deadline-aware change.

## Decision

### One immutable server-owned envelope at acceptance

The route that successfully admits an attempt into the canonical queue owns
the deadline snapshot. The accepted task envelope freezes these exact fields:

```text
accepted_at
work_deadline_at
terminal_deadline_at
```

All three are absolute server-authored timestamps. They are established as one
atomic consequence of successful canonical queue acceptance and are immutable
for that request/attempt identity. Clients cannot supply, override, reset,
refresh, or extend them.

The budget is fixed as:

```text
ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS=720
ACCEPTED_CHAT_TASK_TERMINAL_BUDGET_SECONDS=60
ACCEPTED_CHAT_TASK_TOTAL_BUDGET_SECONDS=780

work_deadline_at = accepted_at + 720 seconds
terminal_deadline_at = accepted_at + 780 seconds
TOTAL = WORK + TERMINAL
```

The 720-second work budget is a deliberate absolute ceiling. The current
maximum-shaped tool path can require two local-provider attempts plus one
loopback command. Existing local-provider settings allow up to 10 seconds for
connection and 300 seconds of read inactivity per attempt, while the loopback
command path permits 30 seconds. Those current limits do not form a total
deadline, but their nominal 650-second sum grounds a 720-second work window and
leaves 70 seconds for bounded dispatch, context, retrieval, and coordination.
The limit also tolerates supported local-model warmup without allowing frames,
retries, or tools to extend execution indefinitely.

The separate 60-second terminal budget is reserved for bounded persistence,
failure evidence, terminal event publication, rollback, task cleanup, and
turn-lock/Redis cleanup. It cannot be spent on new generation or child work.
The resulting 780-second total gives future worker shutdown a finite maximum
remaining task envelope while retaining a distinct terminalization reserve.
These values are architecture policy, not a claim about current enforcement.

```text
ACCEPTED_TASK_DEADLINE_SERVER_OWNED=true
ACCEPTED_TASK_DEADLINE_IMMUTABLE=true
QUEUE_WAIT_CONSUMES_TASK_BUDGET=true
DEADLINE_IS_NON_SLIDING=true
CHILD_DEADLINE_MUST_NOT_EXCEED_PARENT=true
```

### Queue wait consumes the attempt budget

The envelope starts at successful canonical queue acceptance, not worker
dequeue, provider acceptance, first token, or first visible stream frame. Queue
delay consumes the work budget.

If `work_deadline_at` is already exhausted when the worker dequeues the task,
the worker performs zero provider invocations and zero tool invocations and
enters authoritative deadline terminalization immediately. Dequeue never
mints a replacement budget. A user-authorized replay creates a new
request/attempt identity and a new independently authorized acceptance-time
snapshot; it does not extend the original attempt.

### The work deadline is absolute and non-sliding

Token arrival, provider frames, tool output, retries, fallback, retrieval
progress, or any other activity never changes `work_deadline_at`. A provider
that continues returning frames must still be interrupted when the absolute
work deadline is reached.

Every blocking child operation reachable from accepted chat work inherits the
parent deadline:

```text
CHILD_DEADLINE <= PARENT_DEADLINE
child_effective_limit = min(child_policy_limit, remaining_parent_budget)
```

This applies to provider connection and streaming, retries, fallback, tool and
command invocation, connector work, context assembly, retrieval, graph lookup,
database work, persistence, events, and cleanup. A child cannot discard,
replace, reset, refresh, or extend the inherited deadline. A subsystem unable
to accept or enforce that bound fails closed; ADR-087 is not implemented while
such a path remains reachable.

At `work_deadline_at`, no new provider, retrieval, fallback, tool, command,
connector, or other external execution step may begin. Work already completed
successfully may proceed only through the bounded terminal path.

### Terminalization reserve

The interval from `work_deadline_at` through `terminal_deadline_at` exists only
to establish an authoritative bounded outcome. As applicable, it covers:

- final assistant persistence for work already successfully completed;
- deadline-failure persistence and evidence;
- terminal task-event publication;
- task-state cleanup and bounded rollback;
- turn-lock release; and
- bounded Redis cleanup.

Every operation in this window is clipped to its remaining terminal budget.
The terminal reserve never continues generation and never starts replacement
work.

### PostgreSQL is inside the envelope

Every PostgreSQL operation reachable from accepted chat work must enforce an
effective bound no longer than its remaining work or terminal budget. The
implementation must provide equivalents of:

- connection timeout for connection establishment;
- statement timeout for statement execution; and
- lock timeout for lock acquisition or waiting.

The exact mechanism may vary across the database abstraction, but an ordinary
unbounded `psycopg.connect()`, statement, or lock wait does not conform.

```text
FINITE_POSTGRES_BOUNDS_REQUIRED=true
```

Assistant-message persistence, deadline-failure evidence, transaction rollback,
and database-backed terminal/outbox activity remain part of the same accepted
task envelope. PostgreSQL cannot become an escape hatch beyond
`terminal_deadline_at`.

### Authoritative hard-deadline disposition

At `work_deadline_at`, work that has already completed may use the terminal
reserve only to satisfy the existing durable success path. Otherwise the
worker begins authoritative deadline-failure terminalization. It must emit the
following outcome before `terminal_deadline_at`:

```text
SERVER_DEADLINE_TERMINAL_EVENT=task.failed
SERVER_DEADLINE_ERROR_CODE=CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED
SERVER_DEADLINE_REQUEST_STATE=failed_retryable
```

The user-authored message remains `submitted_unanswered`. No automatic replay
occurs. A user-authorized retry/replay requires a new request/attempt identity.

This is not the existing `timed_out` state. `timed_out` means an observer or
presentation policy crossed a waiting threshold while authoritative backend
terminal truth remains unknown. It may reconcile later under the canonical
request-state contract. By contrast,
`CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED` is known server execution truth for the
same attempt.

It is also neither user cancellation nor orphan classification:

```text
SERVER_DEADLINE_IS_TIMED_OUT_STATE=false
SERVER_DEADLINE_IS_USER_CANCELLATION=false
SERVER_DEADLINE_IS_ORPHAN_STATE=false
```

If a worker or process disappears without authoritative terminal evidence,
existing orphan/ambiguity semantics apply. A crash must not be presented as a
controlled deadline failure.

### Request-state reconciliation

The canonical request-state vocabulary does not gain a new state. Directly
observed authoritative deadline failure is allowed through these narrowly
added transitions:

```text
queued -> failed_retryable
dispatching -> failed_retryable
awaiting_ack -> failed_retryable
awaiting_model -> failed_retryable
awaiting_first_token -> failed_retryable
streaming -> failed_retryable
```

`dispatching`, `awaiting_ack`, and `streaming` already permitted that outcome;
ADR-087 preserves those paths and adds only the missing nonterminal paths.
When an observer classified the attempt before authoritative evidence arrived,
the same attempt may reconcile through:

```text
timed_out -> failed_retryable
orphaned -> failed_retryable
```

The existing `timed_out -> completed`, `timed_out -> orphaned`,
`orphaned -> completed`, and explicit replay paths remain valid because
observation ambiguity is not execution truth. No unrelated transition is
broadened.

### Completion and failure precedence

Precedence is deterministic:

1. If durable successful completion was already established within the
   envelope, completion wins, even if an observer previously classified the
   attempt `timed_out`.
2. If there is no durable completion and the hard deadline expires under
   authoritative worker control, deadline failure wins.
3. If the worker/process disappears without authoritative terminal evidence,
   existing orphan/ambiguity semantics apply.

Successful completion continues to require the existing canonical assistant
persistence and terminal-evidence path. ADR-087 creates no second success
path. Once an attempt is authoritatively terminated with
`CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED`, that same attempt cannot later become
`completed`.

Partial visible output is not durable completion. If the work deadline expires
after partial streaming but before successful assistant persistence, the
attempt becomes `failed_retryable` with the deadline error unless prior durable
completion evidence proves otherwise. The server must not fabricate an
assistant message from partial output merely to meet the deadline.

```text
PARTIAL_STREAM_COUNTS_AS_COMPLETION=false
AUTOMATIC_REPLAY_ON_DEADLINE=false
```

### Turn-lock lifetime

Turn ownership must remain valid through the complete execution and
terminalization envelope plus a fixed safety margin:

```text
TURN_LOCK_SAFETY_MARGIN_SECONDS=60
turn_lock_lease_expires_at >= terminal_deadline_at + 60 seconds
```

Equivalently, when the lock is acquired at acceptance and is not renewed, the
effective lock TTL must be at least:

```text
780 + 60 = 840 seconds
```

```text
TURN_LOCK_MUST_OUTLIVE_TASK_ENVELOPE=true
```

The current canonical 180-second default does not satisfy this relationship.
Slice A must either raise the initial lease to at least 840 seconds or implement
deadline-aware renewal that continuously guarantees the same
`terminal_deadline_at + 60 seconds` lower bound. Renewal may preserve lock
ownership; it may never extend the task envelope.

### Operator shutdown

Graceful worker shutdown depends on complete enforcement of this envelope. A
future SIGTERM/SIGINT implementation must stop new intake, preserve work
already dequeued, wait only for that accepted work inside its existing finite
envelope, and allow its bounded terminal/cleanup path to finish.

Because every active attempt then has a finite `terminal_deadline_at`, Compose
stop grace can be derived from the maximum remaining envelope plus a separately
bounded dequeue/process margin. Operator shutdown remains distinct from user
cancellation and must not reuse cancellation semantics.

```text
FINITE_PROVIDER_STREAM_BOUND_REQUIRED=true
FINITE_TOOL_CHILD_BOUND_REQUIRED=true
GRACEFUL_SHUTDOWN_DEPENDS_ON_DEADLINE_IMPLEMENTATION=true
```

## Required implementation sequence

Acceptance of this ADR does not authorize implementation. Subsequent work must
proceed in dependency order:

1. **Slice A — deadline authority and task envelope.** Add the server-owned
   acceptance snapshot, task serialization, deadline helper/context, canonical
   protocol error token, request-state transitions, and turn-lock alignment.
2. **Slice B — provider/stream/tool deadline propagation.** Enforce a total
   stream deadline, cap child requests to remaining time, propagate through
   fallback and the tool loop, and prevent sliding renewal.
3. **Slice C — PostgreSQL/persistence deadline propagation.** Bound connection,
   statement, and lock waits plus assistant persistence, failure evidence,
   terminal events, rollback, and cleanup.
4. **Slice D — graceful worker shutdown.** Add SIGTERM/SIGINT handling, stop
   intake, drain only accepted finite-envelope tasks, and derive Compose grace
   from runtime evidence.

Slice D cannot be claimed safe after Slice A alone. Provider/tool and database
escape hatches must be closed first.

The decision changes execution semantics, not the logical runtime component
graph:

```text
RUNTIME_TOPOLOGY_CHANGED=false
```

## Consequences

### Positive

- Every accepted chat attempt has one finite, inspectable wall-clock envelope.
- Queue backlog, continuing stream frames, retries, and tools cannot mint more
  execution time.
- Observation ambiguity remains distinct from authoritative server failure.
- Turn ownership and worker-drain planning gain exact finite relationships.
- PostgreSQL and terminal cleanup become explicit parts of the runtime proof.

### Negative

- The current provider, tool, database, lock, and worker paths are
  non-conformant until all required slices land.
- Some long-running local completions will become retryable failures rather
  than run indefinitely.
- Turn-lock policy must change from its current 180-second default or gain
  deadline-aware renewal.
- The 780-second total is a product/runtime constraint that future changes must
  revise through architecture review rather than ad hoc timeout tuning.

## Invariants

- Route acceptance and durable completion remain separate truths.
- Message identity and request-attempt identity remain separate.
- `timed_out` remains observer/policy ambiguity.
- Hard server deadline failure is authoritative execution truth.
- Deadline exhaustion is not user cancellation or process-death ambiguity.
- Queue age consumes the attempt budget.
- Activity never refreshes an absolute deadline.
- No child operation outlives its parent deadline.
- Partial streaming is not durable completion.
- No automatic replay occurs.
- PostgreSQL, assistant persistence, events, and cleanup remain within the
  envelope.
- Turn-lock ownership outlives legitimate execution by at least the required
  60-second margin.
- Graceful operator shutdown remains unproven until all four implementation
  slices are complete and runtime-qualified.
- This architecture decision makes no release-support claim.

## Follow-on task

The next separately authorized architecture-impact task is **Implement
accepted chat-task deadline authority and task envelope**. It is Slice A only:
acceptance-time fields, immutable serialization, shared deadline context,
canonical failure token and transitions, and turn-lock alignment. It must not
jump directly to provider propagation, PostgreSQL changes, or graceful worker
shutdown.
