# Guardian Delegation Loop Contract

Purpose: define v1 as a hybrid bridge: `Guardian-owned chat intake -> task normalization -> durable intent artifact -> existing coding-run backbone -> Guardian thread continuation -> Command Center transcript mirror`.

Last updated: 2026-10-26

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/adr/adr-index.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/self-extending-agent-plugin-system.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/delegation-runtime.md
- docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md
- docs/architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md
- docs/architecture/adr/ADR-048-guardian-three-channel-delegation-topology.md
- docs/iddb_policy_v1.md

## Classification

- Classification: Aligned with existing ADR(s)
- Governing ADRs/contracts:
  - ADR-010 Self-Extending Agent Plugin System
  - ADR-020 Guardian Mediated Coding Agent Execution Contract
  - ADR-022 Guardian Intent Spine and Cross-Surface Control Plane
  - Agent Tool Loop Contract
  - Pi Invocation Boundary Contract
  - Chat Runtime Contract
  - Runtime Protocol Token Contract
  - Account Export + Restore Contract
  - IDDB Policy v1
  - Delegation Runtime Contract
- Reason:
  - This task creates a contract document for the Guardian Delegation Loop v1 hybrid bridge. It binds existing runtime, delegation, approval, lineage, and coding-agent concepts without widening the supported release promise or changing runtime behavior.

## Scope

- v1 is scoped to Guardian-to-coding-agent delegation only.
- The execution backbone is the existing coding-run/AgentRun path.
- The source thread remains user truth.
- Command Center transcript is inspection truth, not a second conversational thread.
- Broad "answer as me" authority is out of scope.
- Intent-spine unification is deferred.

Boundary posture for this contract:

- Nodes in scope: Guardian-owned chat intake, durable intent artifact storage, existing coding-run/AgentRun backbone, source-thread continuation path, and Command Center transcript mirror.
- Trust boundary: Guardian remains the owner of intake, approval, lineage, and posting; the coding-run backbone is execution substrate only; the Command Center transcript is a mirror only.
- Threat posture: design first for honest-but-buggy execution, delayed visibility, superseded runs, and context leakage risk; block broader authority and personal-context spillover by default.

## Delegated Task read projection

A Delegated Task is a product/read-model projection over Guardian delegation lineage. Chat is the only implemented source surface in this slice; the projection itself must not redefine delegation as a chat-thread subtype. `GuardianDelegationIntent.intent_id` remains its identity and durable delegation authority. `GET /api/guardian/delegations?thread_id=<id>` lists the existing intents for one canonical source Chat Thread, using separate intent, run, approval, and visibility axes. The existing per-intent transcript endpoint remains read-only execution inspection truth.

Delegated Tasks are subordinate execution lineage, not conversational transcript authority. One Chat Thread may spawn many Delegated Tasks, and a Delegated Task may carry one or more execution attempts/runs under the existing execution records. Questions and clarifications return through Guardian to the originating Chat Thread; results are delivered back through Guardian. Direct human conversation inside a Delegated Task is not part of this slice.

Workspace inspection is the intended future presentation direction, but is not implemented here. Work Threads, sidebar task rows, and persistent reattachable stdout/stderr/PTY sessions remain deferred. This read projection does not change supported release posture.

## Current-Truth Anchors

What is true now:

- Codexify is local-first beta hardening on the supported Docker Compose path.
- Chat completion works on the supported path and persists into the source thread.
- Coding results return through Guardian into the source thread on the supported path.
- Existing runtime docs distinguish acceptance, execution, task-event visibility, and completion.
- Existing bounded tool/coding-agent contracts avoid claims of recursive autonomous execution.
- The Guardian delegation path can mint an execution binding from trusted account context, resolve an enforceable permission posture, persist both against the deployment, and enqueue exactly one coding-execution task. This is **code-path presence with contract tests, not live-runtime proof**: it has not been driven from a chat turn and has not been qualified on the supported Compose path.

What is not yet true:

- The Guardian Delegation Loop v1 is **not** implemented end to end. The delegation *authorization* and *dispatch* path now exists in code — a Guardian-owned execution binding, an enforceable permission posture, and a durable dispatch that enqueues one coding-execution task with a binding byte-identical to the persisted one — but it is **not yet driven from a chat turn**, and it is **not yet proven on the supported Compose path**.
- Guardian delegation is therefore still **non-executable from a user's conversation**. Nothing in this slice makes a chat turn produce a delegated task.
- The delegation route remains **flagged off by default** and quarantined by the supported profile, and no supported-profile or release-surface change has been made or authorized.
- The dispatch recovery contract is **quarantine-and-escalate**: automated re-dispatch is refused because no fencing token exists in this runtime.
- The operator quarantine **invocation path** exists and is proven in a disposable environment, but it is **not deployed**, **not enabled by default**, and **not part of the supported release surface**. The supported Compose path is unchanged.
- Broad "answer as me" authority does not exist.
- No new public release surface is implied by this contract.
- Intent-spine unification does not exist.
- No Command Center mirror implementation is claimed unless separately proven by current code and runtime docs.
- The current release gate is unchanged: the latest complete supported-Compose qualification remains `HOLD`, and autonomous coding-worker work is not promoted to default Beta support.

What this contract may assume:

- The contract may define the desired v1 semantics for future implementation.
- The contract may describe later phases as non-goals or deferred work.
- The contract may cross-link to existing architecture and ADR docs.

## Locked v1 Decisions

- Execution backbone: hybrid bridge
- Conversation model: non-blocking chat
- Approval model: scoped auto-approve
- Canonical contract artifact: this architecture contract document, not a new ADR
- Canonical future intake surface: Guardian-owned route
- Operator mirror: Command Center transcript surface, not second thread
- Phase 2 future scope: safe happy path only, with no human-approval or cancellation endpoints yet

## Entities

### `GuardianDelegationIntent`

Guardian-owned durable intent artifact for one delegated coding request. It binds `thread_id`, `source_message_id`, normalized work intent, work scope, `context_basis`, approval posture, lineage, and any later run linkage without claiming dispatch or completion by itself.

### `GuardianTaskPlan`

Task-normalized plan derived from `GuardianDelegationIntent`. It captures bounded work goals, repo/worktree scope, execution constraints, success criteria, and escalation points for the existing coding-run/AgentRun backbone.

### `GuardianApprovalDecision`

Guardian-owned decision record for whether a `GuardianDelegationIntent` or `GuardianTaskPlan` may dispatch. It keeps `approval_state`, `approval_source`, scope rationale, and blocking reason separate from acceptance, execution, and visibility.

### `GuardianThreadInterruption`

Source-thread continuation artifact used to request clarification, surface approval needs, post result delivery, or explain degraded visibility. It is a mirror into the user truth thread, not the canonical run transcript.

### `GuardianRunTranscriptEvent`

Durable, ordered event record sourced from agent-run or coding-run events. It exists for inspection, operator visibility, and Command Center mirroring, and must not replace source-thread conversational truth.

### `ContextBasisEntry`

Explicit provenance record for one included context source. A `context_basis` collection explains why each source was included, what fields were used, how confidently it was selected, and whether policy allowed its use.

## Status Axes

These axes are separate truths. This contract does not claim that every value below is already emitted end-to-end in the live runtime, and it does not authorize collapsing them into one field.

- `acceptance_status`: reuse existing protocol tokens `accepted`, `accepted_degraded`
- `approval_state`: `pending`, `approved`, `blocked`
- `approval_source`: `none`, `auto`, `human`
- `intent_status`: `draft`, `planning`, `awaiting_clarification`, `awaiting_approval`, `accepted`, `superseded`, `cancelled`, `failed`
- `run_status`: `not_enqueued`, `queued`, `running`, `completed`, `failed`, `cancelled`
- `visibility_status`: `not_posted`, `interrupt_posted`, `result_posted`, `stale_suppressed`, `delivery_degraded`

### Axis Ownership of Facts

Which axis owns which fact. Writing a fact onto the wrong axis is a category error, and the axes are not interchangeable.

- **`acceptance_status` is admission-scoped.** It records whether the request was admitted and whether the `task.created` start event was visible. `accepted` means admitted with a visible start event; `accepted_degraded` means admitted with degraded start-event visibility (publish failed, or the published event carried no event id). It is derived from the publish outcome in `guardian/core/chat_completion_service.py` and logged beside `task_created_visibility_scope` in `guardian/routes/chat.py`. **It never carries an execution fact.**
- **`intent_status` owns the execution outcome.** A dispatch failure sets `intent_status` to `failed`. It does not alter `acceptance_status`: the request was admitted, and admitting it did not fail.
- **`run_status` is a projection, not a stored field.** `GuardianDelegationIntent` has no `run_status` column. `_resolve_row_run_status` derives it from the linked `AgentRun`, returning `not_enqueued` when no run is linked. Adding a stored `run_status` would require a schema migration and is not authorized here.
- **`visibility_status` owns what the user actually saw.** A dispatch failure leaves it `not_posted`, because the user was never shown a start event.

Consequently, a Guardian dispatch failure must not be recorded as `accepted_degraded`: that token would assert an acceptance-and-visibility state that did not occur. No new protocol token is added for this; the existing axes already carry every fact.

### Dispatch authorization

Dispatching a delegated coding task requires two Guardian-owned authorizations, both resolved from trusted account, project, and workspace context — never from the request.

- **The execution binding** (`guardian/core/guardian_execution_binding.py`) names the provider, model, harness, credential reference, owner scope, and lineage for one attempt. It is secret-free, attempt-scoped, and immutable once established. The provider and credential come from the account's own registered credentials, or — where the account owns none — from a service-owned credential whose recorded service policy names that account, provider, model, funding route, and usage policy (ADR-094 sections 12 and 34). The model is pinned from the runtime's configuration for that provider. Discovery and authorization stay separate: discovery finds service-owned candidates only, and every candidate is decided by the existing credential authority before it can authorize anything. An account's own credential keeps precedence, a rejected account credential is never silently replaced by a service one, and where more than one service candidate authorizes and no existing rule resolves them, the selection fails closed rather than guessing. A caller proposal may narrow a grant, never widen one. The binding is persisted into the deployment spec **before** the task is queued, because the credential-lease authority re-reads it from the spec and the coding worker requires the task payload binding to equal the persisted one byte-for-byte.
- **The permission posture** (`guardian/core/guardian_permission_posture.py`) states which surfaces actually enforce the grant and which do not. Per ADR-077 rule 6, denied filesystem mutation is enforced below the model/tool layer; per rule 7, tool allowlists and prompt instructions are defense in depth, not filesystem, network, or process isolation. The git mutation guard **detects** an out-of-scope mutation and fails the attempt — it does not prevent the write. `allow_network` is a request, not an egress guarantee, because no sandbox provider is wired into the coding worker. The posture is therefore advisory for network egress and process isolation, and says so rather than claiming enforcement it cannot evidence.
- **The reasoning effort** is part of the execution binding, not a separate configuration surface. Guardian resolves the effective effort from the provider and model the binding pins, before anything is dispatched, and records it in the binding. The binding schema version is the discriminator: a version 2 binding *governs* the effort and therefore carries it, while a version 1 binding predates the contract and governs nothing, so the harness keeps its own default exactly as before. A version 1 binding is never reinterpreted as if it had governed one. The coding worker forwards the persisted value verbatim to the adapter and selects no level of its own — from the model identity, from ambient process configuration, or from a caller-supplied task field. Because the queued task's binding must equal the persisted one byte-for-byte, a tampered effort is a binding mismatch and is refused before any provider execution. An effort the harness does not accept, or one the lane has not validated, fails closed at resolution time; it is never clamped or downgraded to a level Guardian did not select. The lanes that have been validated are a bounded list in `guardian/agents/coding_agent_contracts.py`, not a model-capability registry: a lane that is not listed there has no validated compatibility rule and is left ungoverned.

### Durable execution acceptance

Dispatching a task is not the same as owning it. A queued coding task that has never been picked up, and a coding task whose worker has already begun and then died, are indistinguishable in the queue: the queue is lossy and at-most-once, and a dequeued task may still be executing. The **durable acceptance record** is what tells those two states apart in canonical PostgreSQL, and it is a precondition for any side-effecting execution.

The acceptance record is the existing canonical `agent_runs` row. No migration, no new table, and no separate execution ledger are required: the schema already permits `status = 'running'` and already carries a nullable `started_at`.

| Field | Before acceptance | After acceptance |
|---|---|---|
| `agent_runs.status` | `queued` | `running` |
| `agent_runs.started_at` | `null` | stamped exactly once |

`AgentStore.claim_run_for_acceptance` (`guardian/agents/store.py`) performs the transition as a **compare-and-set**: `UPDATE agent_runs SET status = 'running', started_at = now() WHERE id = :id AND status = 'queued' AND deployment_id = :deployment_id`. The update applies only while the row is still `queued`, so exactly one of two racing workers can win; a terminal run is never reopened; and a duplicate claim never refreshes `started_at`.

The claim's authority is the durable deployment record the run already points at — the same immutable spec the execution binding was validated against. The run must belong to that deployment, and every identity the deployment *asserts* — account, thread, source message, attempt, and coding task — must agree with the claiming task. Asserted identities are read from the deployment spec and from its persisted execution binding, because that binding is the record the credential-lease authority re-validates. A deployment that asserts nothing about an identity does not contradict the task; a deployment that asserts a different one does, and so does a deployment that contradicts itself.

**The boundary.** In `guardian/workers/coding_worker.py`, acceptance sits after the trusted execution-binding validation and before every side-effecting step: before the worktree lease, before the isolated worktree, before `task.running`, and before adapter entry. `task.running` therefore follows a successful durable acceptance rather than preceding it.

**Refusal is fail-closed and non-destructive.** The claim returns one of three outcomes — `accepted`, `rejected`, or `unavailable` — and anything other than `accepted` refuses execution. Unreachable persistence is `unavailable`, never permission to execute: missing persistence is not a weaker form of authorization. A refusal is published as the canonical generic, **non-terminal** `task.event` with a local `error_code` (`EXECUTION_ACCEPTANCE_REJECTED` or `EXECUTION_ACCEPTANCE_UNAVAILABLE`), following the worker's existing precedent for local error codes; no protocol token is added. A refusal never calls `update_run_status` and never calls `store_coding_result`, so a duplicate delivery cannot turn another worker's running attempt into a terminal failure, cannot produce a second result artifact, and cannot post a second source-thread message.

**What this does not yet provide.** The acceptance record makes an accepted run distinguishable from a queued, never-started run after worker process death. It does **not** implement restart-time reconciliation: nothing reads the acceptance record at startup, no uncertain-outcome sweep exists, and `observe_liveness()`, `classify_dispatch_health()`, and `recover_dispatch()` are not wired into any startup path. Reconciliation remains a separate, dependent task, and no retry authority is implied by the record.

### Durable coding-worker ownership

The acceptance record says *that* an execution was claimed. It does not say *who* claimed it, and without that, an accepted run cannot be told apart from one whose owner is still working. **Durable ownership** records the worker instance that took the claim and the unique claim it made, inside the existing `agent_runs` authority.

| Field | Meaning | Before | After acceptance |
|---|---|---|---|
| `agent_runs.coding_worker_instance_id` | the coding-worker instance that accepted the run | `null` | the internal instance identity |
| `agent_runs.coding_worker_claim_id` | the unique ownership claim made at that moment | `null` | a fresh claim identity |

Both fields are nullable and bounded, and the schema enforces that they are **both present or both absent** (`agent_runs_coding_worker_ownership_check`) and that a non-null claim identity is **unique** (`uq_agent_runs_coding_worker_claim_id`). The migration `e42c7d0b9135` is additive: it adds the two columns and the two named constraints, it preserves every existing row and the run-status vocabulary, and it does not backfill historical ownership. Rows accepted before the migration remain **ownership-unknown** — that is their truthful meaning, and the migration does not fabricate an owner for them.

**Ownership is executor metadata.** The instance identity identifies the worker *instance*, never an account, principal, or credential owner; the two identities are never conflated. The identity is generated inside the worker from a fresh uuid, using the repository's established `<prefix>_<uuid4 hex>` convention. It is **not** derived solely from a hostname or a PID, because two instances on one host must never collide and a restarted process must never inherit its predecessor's identity. It cannot be supplied by a queue payload, a deployment field, or model output; a trusted constructor seam exists only so a test can inject a deterministic value.

**The claim boundary.** The ownership claim and the `queued → running` transition are one statement in one transaction. A successful acceptance commits `status`, `started_at`, the instance identity, and the claim identity together; a failed acceptance commits none of them. The claim remains a compare-and-set on `status = 'queued'`, so a second worker cannot take an accepted run, cannot replace its owner or claim, cannot refresh `started_at`, and never reaches the adapter, a worktree, or a credential lease. A duplicate claim also publishes no terminal failure, so an accepted attempt is never reported as failed by a second delivery.

**What ownership does not provide.** A persisted owner is **not** proof that the worker is still alive: it records that an instance took the claim, not that it still holds it. There is deliberately no heartbeat column, no expiry, no takeover, and no automatic claim reassignment, and the restart-reconciliation posture described below remains unimplemented. A claim identity is durable correlation material for a future fencing mechanism; it is **not** retry authority, and it grants no permission to re-execute. Ownership stays subordinate to `agent_runs` — there is no separate ownership table and no independent control plane.

### Claim-scoped coding-run heartbeats

Durable ownership records *who* took a claim. A heartbeat records that the
recorded owner was **still reporting** while the execution was in flight. Both
are canonical `agent_runs` facts and both stay subordinate to it: a heartbeat is
**evidence of activity, never authority to act**.

| Field | Meaning | Before | After acceptance |
|---|---|---|---|
| `agent_runs.coding_worker_last_heartbeat_at` | the last moment the recorded owner reported liveness for this run | `null` | the acceptance timestamp, then each renewal |

The column is nullable and timezone-aware (`TIMESTAMP(timezone=True)`), and the
migration `d86f2a4b1c90` is additive: it adds the column and the named
constraint `agent_runs_coding_worker_heartbeat_ownership_check`, preserves every
existing row, leaves the run-status vocabulary untouched, and **does not
backfill** a heartbeat for a historical row. A run accepted before heartbeats
existed keeps a `NULL` heartbeat, which is the truthful meaning of "never
reported".

**The first heartbeat is part of acceptance.** `AgentStore.claim_run_for_acceptance`
writes `status`, `started_at`, the instance identity, the claim identity, and
the first heartbeat in **one statement in one transaction**, so a heartbeat can
never exist without the ownership that produced it, and a refused acceptance
writes none of them. The heartbeat timestamp comes from the **database clock**
(`now()`) rather than the worker's wall clock, so the liveness evidence and the
durable row share one canonical time source; `started_at` keeps the worker-side
clock it has always used.

**Renewal is claim-fenced and atomic.** `AgentStore.renew_coding_run_heartbeat`
performs a single conditional update:

```
UPDATE agent_runs
   SET coding_worker_last_heartbeat_at = now()
 WHERE run_id = :run_id
   AND status = 'running'
   AND coding_worker_instance_id = :worker_instance_id
   AND coding_worker_claim_id = :claim_id
```

There is no read-then-write sequence and no application-level ownership guess:
the database's own verdict is the authority. The operation returns `renewed`,
`not_eligible` (the row did not match — a different worker, a different claim, a
terminal or escalated run, or a run that no longer exists), or `unavailable`
(persistence could not be reached). A failed condition updates **zero rows**: it
never creates or repairs ownership metadata, never refreshes `started_at`, never
changes a terminal status, and never reopens a run. Knowing a `run_id` is not
authorization.

**The worker reports on its own thread.** The adapter invocation is
synchronous, so a heartbeat on the worker's own thread would be silent for the
whole duration of a provider call. The worker therefore runs a small
per-execution reporter (`_CodingRunHeartbeat`) that renews on an explicit,
documented cadence (`CODING_RUN_HEARTBEAT_INTERVAL_SECONDS`, default 15 seconds,
overridable by environment so it is testable) and **stops and joins** when the
execution ends. Each renewal opens its **own** bounded database session, so no
SQLAlchemy session is ever shared across threads. The reporter is scoped to
exactly one run and one claim, is held on the worker instance rather than in
process-global state, and is removed on every terminal path (success, failure,
cancellation) plus a `finally` safety net on the poll loop, so it cannot leak
into a later task or outlive a graceful shutdown. Graceful shutdown is a real
path rather than an assumption: `CodingWorker.shutdown()` stops and joins every
reporter the worker owns, and the worker loop calls it in a `finally`. The
reporter is a daemon thread, so an abrupt process death cannot leave it
holding the process open either. Stopping a reporter resolves nothing: the
canonical row keeps its status, owner, claim, and last heartbeat, and the
evidence simply stops moving.

**Loss of ownership stops the run.** When a renewal comes back `not_eligible`,
the reporter stops immediately and preserves the rejection reason
(`coding_run_claim_no_longer_eligible`); the worker then refuses to enter the
adapter, because the claim it holds is no longer the canonical owner of the
run. The worker never replaces the claim, never mints a new owner or binding,
never issues another credential lease, and never converts the rejection into a
successful execution. The refusal is published as the canonical generic,
**non-terminal** `task.event` with `error_code = 'EXECUTION_OWNERSHIP_LOST'`.

**What the heartbeat does not provide.** A heartbeat is a *report*, not a
guarantee:

- It does not prove the worker is alive. A stale heartbeat is **not** proof of
  worker death: the worker may be between phases, blocked on a provider call, or
  paused by the host.
- It does not stop an in-flight provider call or subprocess. The rejection check
  happens at the worker's cooperative boundaries, so an operation already
  running inside the adapter is **not** preempted. No side-effect fencing is
  claimed from this mechanism.
- It does not authorize execution, retry, requeue, escalation, or takeover. No
  expiry rule, no quarantine decision, and no classifier reads it.
- It does not implement restart reconciliation. Nothing reads the heartbeat at
  startup.

**Historical rows.** A `NULL` heartbeat means the run never reported one:
either it predates the migration, or it is ownership-unknown. Such a row stays
readable, acquires no synthetic heartbeat, and is **never** escalated because a
heartbeat is missing. The gate below is unchanged in substance: reconciliation
still requires a *demonstrated*-dead worker, and a stale heartbeat still cannot
authorize replay.

### Claim-fenced terminalization

Durable ownership says *who* holds a run. The heartbeat says that the holder was
still reporting. Neither says that only the holder may **finish** it. That is
the terminal authority boundary, and it is now enforced in the database.

**The terminal claim.** `AgentStore.claim_coding_run_terminal()` performs one
conditional update:

```
UPDATE agent_runs
   SET status = :terminal_status,
       ended_at = now(),
       error = :error
 WHERE run_id = :run_id
   AND status = 'running'
   AND coding_worker_instance_id = :worker_instance_id
   AND coding_worker_claim_id = :worker_claim_id
```

The worker instance and claim come from the durable acceptance, never from
model output, a queue payload, a tool result, or an HTTP request. The database
-- not an application-level check performed earlier -- decides who may write
the terminal status. The deployment lineage is checked in the same transaction:
a deployment that has been rewritten to contradict the run it accepted is not
an authority for finalizing it.

The operation distinguishes four outcomes:

| Outcome | Meaning |
|---|---|
| `terminal_accepted` | the claim still owned the run; the terminal transition was written |
| `terminal_rejected` | the claim did not match the run, or the run was disposed of by another authority (`escalated`) |
| `terminal_already_terminal` | the run already carried a terminal status; nothing was rewritten |
| `terminal_unavailable` | persistence could not be reached; the caller fails closed |

**One transaction.** The terminal decision and the canonical result writes that
belong to it -- the AgentRun terminal state, the coding-result artifact, the
Guardian delegation delivery state, and the source-thread result message --
commit together or not at all. `AgentStore.finalize_claimed_coding_result()`
opens one transaction, stages the delivery and the artifact on it, performs the
terminal claim, and commits only when the claim was accepted. A failure in any
of those writes rolls the whole terminal decision back: the run stays
`running`, no artifact exists, and no message was delivered.

This is the ordering repair. The earlier path delivered the source-thread
result first, committed it on its own, and only then wrote the terminal status
through an unguarded update -- so a result-side effect could outlive the
terminal decision that should have authorised it, and a stale worker could
deliver a message and publish `task.completed` for a run it no longer owned.

**Rejection produces nothing.** A rejected terminal claim writes no terminal
status, no coding-result artifact, no source-thread result, no terminal task
event, no execution attempt, and no credential lease. The worker reports the
refusal through the existing **non-terminal** ownership-lost event
(`EXECUTION_OWNERSHIP_LOST`) and stops. It does not replace the claim, mint a
new owner, issue another credential lease, grant a retry, or turn the refusal
into a successful execution.

**Terminal events follow the durable decision.** `task.completed`,
`task.failed`, and `task.cancelled` are published only after an accepted
terminal decision. A terminal event is never published merely because an
adapter returned successfully, and a rejected terminalization never publishes
one. Database persistence remains authoritative: the Redis event publication is
a separate transport operation, and no cross-system atomicity is claimed. If the
durable result is committed but the event is lost, the durable result stands.

**Idempotent readback.** An identical duplicate finalization after a committed
result observes the existing receipt. It does not reapply the terminal status,
create another artifact or message, publish another terminal event, refresh
`ended_at`, or grant another execution.

**Compatibility.** A run that was never accepted by this worker has no claim
and keeps the legacy behaviour. The established source-thread delivery key, the
identity checks, the sanitization, the deferred-delivery behaviour, the
degraded-delivery classification, and the visibility vocabulary are unchanged.

**What the fence does not provide.** A database terminal fence protects
canonical Codexify state. It does not terminate an already-running Pi
invocation, a provider request, a subprocess, an ongoing filesystem mutation,
or an external network operation. The worktree and mutation guard remain
independent boundaries, and a future recovery mechanism must still treat
uncertain external side effects conservatively.

### Canonical per-run liveness observation

Durable ownership says *who* holds a run; the claim-scoped heartbeat says that
the holder was still reporting; terminal fencing says who may *finish* it. None
of those is an interpretation. Guardian can now read the canonical evidence and
classify it — conservatively, and without acting on it.

**The snapshot.** `AgentStore.get_coding_run_liveness_snapshot()` reads one
coding run's liveness evidence from **one** PostgreSQL statement: the run id,
the deployment, the status, the start and end timestamps, the worker instance,
the claim, the claim-scoped heartbeat, and an `observed_at` taken from the
**database clock**. One statement means one consistent snapshot: mixing
timestamps from separate reads could produce a misleading ordering. The
application host clock is never the authoritative comparison clock.

The snapshot is read-only. It does not update the run, renew a heartbeat, touch
a lease, create a recovery attempt, emit an event, create an escalation, or
deliver a result. It carries no credential material, no secret, no raw prompt,
and no transcript content — only identity and timing facts. It is not a public
endpoint; where it becomes callable, the existing account and operator
read-authorization boundaries apply.

**The staleness horizon.** One explicit observational horizon, derived from the
cadence the worker actually implements:

```
stale_after_seconds = max(60, 3 * production_heartbeat_interval_seconds)
```

The production cadence is 15 seconds, so the horizon is **60 seconds**. It is an
**observation threshold**, not an execution-lease expiry and not a death
oracle. Crossing it means "recent liveness evidence is missing" — a statement
about evidence, not about the worker process. No retry, escalation,
cancellation, or takeover follows from it, and no persisted expiry, takeover
timestamp, or death marker was added.

**The distinctions.** The classification reuses the existing dispatch verdict
vocabulary (`GuardianDispatchState`) and adds an explicit evidence label:

| Evidence | Canonical record | Dispatch verdict | Meaning |
|---|---|---|---|
| `never_accepted` | `queued`, no claim | `dispatched` | execution was never durably accepted; **not** an abandoned execution |
| `recently_observed` | `running`, owner + claim, heartbeat inside the horizon | `executing` | the claim recently renewed liveness; **not** proof that a process exists |
| `stale_uncertain` | `running`, owner + claim, heartbeat older than the horizon | `uncertain` | recent liveness evidence is missing; the outcome is uncertain; **not** a determination that the worker died |
| `missing_evidence` | `running` without a usable owner, claim, or heartbeat | `uncertain` | insufficient evidence; nothing is inferred about whether work started or side effects occurred |
| `already_resolved` | `succeeded` / `failed` / `canceled` | `completed` / `failed` / `cancelled` | a canonical terminal disposition already exists |
| `already_escalated` | `escalated` | `quarantined` | an authoritative escalation disposition already exists |
| `inconsistent` | a record that contradicts itself | `uncertain` | the record requires inspection; it is never repaired automatically |
| `unobservable` | no record, or unreachable persistence | *(none)* | no observation could be made |

A record is inconsistent when it carries a partial ownership pair, when a
queued run carries accepted ownership, when its timestamps are impossibly
ordered, or when its heartbeat sits in the future. The run's timeline spans two
clocks — `started_at` is stamped by the application, the heartbeat and
`ended_at` by the database — so a comparison that spans them tolerates their
difference, while a comparison inside one clock is exact.

**Evidence, not decisions.** The classifier reports the observed state, the
worker identity, the claim identity, the heartbeat, the observation instant, the
computed heartbeat age, the threshold, whether evidence was available, the
conservative verdict, and the reason for uncertainty. It does **not** decide
whether to retry, requeue, terminate a process, revoke a credential, replace a
binding, transfer ownership, or escalate. It produces evidence for a
Guardian-owned decision that has not been made.

**Cross-worker isolation.** Classification is scoped to one `run_id` and the one
`(coding_worker_instance_id, coding_worker_claim_id)` pair recorded on it. One
worker's silence never makes another worker's run look healthy, and a stale
heartbeat never makes a peer run uncertain. A global coding-worker heartbeat
would not be a substitute, and none was introduced.

**It weakens nothing.** A liveness observation never changes a terminal run,
never changes an escalated run, never overrides an accepted claim, never
generates a terminal event, never publishes a source-thread result, and never
reopens a completed execution. A stale classification does not invalidate a
claim: only the governing persistence authority can accept or reject a terminal
write.

**What it cannot see.** A stale heartbeat says nothing about whether the
external harness finished a provider request, mutated an isolated worktree,
produced files, started a subprocess, made a network request, or committed an
external change. The absence of a canonical result is not the absence of
external side effects, and no provider-enforced sandbox conformance is claimed.

**Restart reconciliation is still deferred.** Nothing reads this classification
at startup. No worker-init, no poll loop, no recovery path consumes it, and
`recover_dispatch()` is not activated for production runs.

### Operator-authorized uncertain-outcome quarantine

Liveness classification produces *evidence*. The disposition that acts on that
evidence is a separate, explicitly authorized decision, and it is persisted
atomically.

**The authority.** Guardian already has an operator authority:
`require_operator_auth` accepts a configured Guardian API key or a
current-format signed token carrying the operator purpose, and it rejects
account and guest credentials *before* the API-key fallback, so a principal
credential is never reinterpreted as operator material. The disposition uses
that authority as-is. It does not accept a caller-supplied
`operator_authorized=True`, a client-supplied role string, or anything derived
from model output, a queue payload, or a tool result. The operator actor is
*derived* by the verification, and it is distinct from the account owner, the
worker instance, the execution claim, and the credential owner.

**The sequence.**

```
canonical liveness evidence
    -> operator reviews the uncertainty
    -> Guardian verifies the operator authority
    -> Guardian re-evaluates the existing quarantine contract
    -> guarded PostgreSQL disposition
```

The classifier's `stale_uncertain` result is what the operator reviews. It is
never the authorization, and it never triggers anything by itself.

**Canonical preconditions.** The target must be a `running` run with a durable
deployment, existing Guardian execution lineage, a recorded worker instance and
claim, and a heartbeat **older than the observation horizon**. The expected
worker, claim, and account must match. A fresh heartbeat is refused: an
actively reporting worker is not an abandoned-run candidate. A historical
ownership-unknown row is refused: it needs a separate operator investigation
procedure, and its ownership is never backfilled or inferred.

**One transaction.** The guarded transition and the escalation evidence commit
together:

```
UPDATE agent_runs
   SET status = 'escalated', ended_at = now()
 WHERE run_id = :run
   AND status = 'running'
   AND coding_worker_instance_id = :worker
   AND coding_worker_claim_id = :claim
   AND coding_worker_last_heartbeat_at <= now() - :horizon
```

The staleness condition is evaluated by the **database clock, inside the
transaction**, so a heartbeat that became fresh after the operator's review
refuses the transition. The `AgentEscalation` row is inserted on the same
session: `status = open`, the existing recovery reason
`guardian_dispatch_liveness_unproven`, an appropriate severity, an
evidence-backed `preserved_worktree`, and a bounded evidence payload. There is
never an escalated run without its committed escalation evidence, and never
escalation evidence attached to a run whose transition did not commit. The
public `AgentStore.add_escalation()` keeps its existing behaviour; a
narrow session-aware helper serves the guarded path.

**Evidence, not verdicts.** The escalation records the run, the deployment, the
original worker instance and claim, the last heartbeat, the database
observation instant, the conservative liveness verdict, the recovery reason, the
verified operator actor, the operator decision provenance, the original
execution status, the final disposition, and the worktree preservation
evidence. It carries no credential material, no raw prompt, and no transcript
content. When the existence of a worktree cannot be established, the evidence
records that uncertainty rather than claiming a worktree was preserved.

**Three meanings stay distinct.**

```
classification = stale_uncertain
disposition    = escalated
result         = unknown
```

`escalated` is not `failed`, and `quarantined` is not proof that the previous
worker stopped executing. A quarantine is an operator-visible decision to
withhold canonical completion until the unresolved execution is investigated.
No `task.failed`, `task.completed`, or `task.cancelled` is fabricated, and the
disposition grants no retry, requeue, credential, binding, or ownership
authority.

**Races and duplicates.** A terminal decision that committed first is never
overwritten: the quarantine refuses, the terminal status, its artifact, and
its source-thread result are preserved, and no quarantine escalation is
created. A quarantine that committed first blocks the late worker: the
escalated status stands, exactly one escalation record exists, and the stale
worker's terminalization is rejected by the claim fence — no artifact, no
source-thread result, no terminal event. A repeated authorized request for the
same run, claim, operator, and reason observes the existing disposition
read-only: no second escalation, no reset timestamp, no replaced provenance, no
reopened run. A run escalated for a different reason or by a different
authority is a conflict, and its existing disposition is never rewritten.

**Active peers.** A disposition is scoped to one run and its recorded owner. It
never reads, classifies, modifies, or delivers anything for a peer worker's
run, and a peer's activity never makes a stale run look healthy.

**What a quarantine does not do.** It does not stop an already-running Pi
invocation, provider request, subprocess, filesystem mutation, or network
operation. It deletes no worktree and no artifact. A quarantined run's external
side effects remain uncertain and remain subject to operator inspection. No
startup reconciliation is activated, and no worker-death determination is
made.

### The operator invocation path

The quarantine above is now reachable by an explicitly authenticated
operator, through the **existing** Guardian delegation route family. That adds
an *invocation path*, not an authority.

**The route.** One bounded, operator-only POST action:

```
POST /api/guardian/delegations/runs/{run_id}/quarantine
```

It lives on the existing `guardian/routes/guardian_delegations.py` router
(`APIRouter(prefix="/api/guardian/delegations")`). No second router is
introduced, and application-level router registration is unchanged. The `runs`
path segment keeps the action out of the `{intent_id}` space, so it cannot
collide with `/{intent_id}`, `/{intent_id}/approve`, or
`/{intent_id}/cancel`.

**The feature gate.** The whole router — this route included — is included
through the existing gate `CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES`,
whose `default_enabled` is `False` and is **not** changed by this work. Under
the default posture the route is absent and the supported release profile
still quarantines the family. A feature-gated route proven in a disposable
environment is not a deployment: it says nothing about the supported Compose
path.

**The authentication boundary.** The router already carries
`dependencies=[Depends(require_operator_auth)]`, so the route requires
operator authority before the handler runs. The route reads the credential
material from the verified request — `X-API-Key`, `Authorization: Bearer`, or
the `gc_session` cookie — and hands it to the service server-side. The
service then performs its **own** authoritative verification; the dependency's
returned display identity (`"operator-api-key"` or `"operator-session"`) is
never used as authority. No credential material is read from the body, the
query string, or the path, and none reaches the response, the exception
detail, the application logs, the escalation evidence, or the Redis task
events.

**The request contract.** A strict model with `extra = "forbid"`:

| Field | Bound | Meaning |
|---|---|---|
| `expected_worker_instance_id` | 1–64 | the worker the operator believes owns the run |
| `expected_worker_claim_id` | 1–64 | the claim the operator believes owns the run |
| `reason` | 1–2000 | the operator's explicit reason |

The two identity values are **optimistic concurrency conditions**, not
authority: the service still revalidates the canonical run, the ownership, the
lineage, and the heartbeat condition inside the transaction. The model refuses
an authorization boolean, a target run status, an escalation status, a new
execution binding, a credential selection, a retry instruction, a worktree
deletion instruction, a provider command, and a client-supplied escalation
payload.

**The receipt.** A successful invocation returns a bounded receipt grounded in
committed database state: `run_id`, `disposition`, `escalation_id`,
`reason_code`, `original_worker_instance_id`, `original_worker_claim_id`,
`operator_actor`, `already_quarantined`, and `recorded_at`. A newly committed
quarantine answers **201**; a repeated identical request observes the existing
disposition read-only and answers **200**. Nothing else is returned: no raw
prompts, no transcript content, no provider responses, no secret values, and
no arbitrary escalation payload.

**The mapping.** Ownership mismatch, fresh heartbeat, changed claim, terminal
run, and conflicting existing escalation are **409**; an unknown run is
**404**; an operator authentication or authorization failure is **401**; an
unavailable database is **503**. The route never converts a persistence
failure into a success. It performs **no** database write of its own: the
service and `AgentStore.quarantine_coding_run_as_uncertain()` remain the sole
implementation, the run's transition and its escalation evidence commit
together or not at all, and no terminal task event and no source-thread result
is published from the route.

**No automatic recovery.** The route records an operator decision. It does not
start, poll, schedule, or watch. `observe_liveness()`,
`classify_dispatch_health()`, and `recover_dispatch()` are not wired into
coding-worker startup, no heartbeat-age watcher is added, no automatic
quarantine is scheduled, no task replay is implemented, and no ownership
takeover is granted. A worker that dies while Guardian is down is still
reconciled only by an operator, and the strict-xfail restart-reconciliation
tripwire remains unresolved.

**What the response means.** A 201 means Guardian durably recorded an
authorized uncertain-outcome quarantine. It does not mean the previous worker
was killed, that external effects were prevented, that the worktree was
restored, that a provider session was cancelled, that a Git commit was undone,
or that the execution outcome is known.

### Restart reconciliation of abandoned executions

The durable acceptance record makes an accepted run **distinguishable from a
queued, never-started run** after worker process death. It does not, by itself,
make an abandoned run distinguishable from an **actively owned** one — and
restart reconciliation requires exactly that second distinction.

**The gate.** A reconciliation may only touch an accepted execution whose
owning worker is *demonstrably* gone. The runtime must therefore supply durable
evidence of **which worker instance owns which run**, and whether that owner is
still alive. A running `AgentRun` does not establish liveness. An expired
worktree lease does not prove the worker process is dead. An empty queue does not
establish that the accepted execution completed. A missing lease row does not
establish that no execution occurred. A stale heartbeat cannot authorize task
replay.

**The gate still fails, on the liveness authority half.** Durable ownership now
exists — `agent_runs.coding_worker_instance_id` records which instance took the
claim — and per-run liveness *evidence* now exists as well
(`agent_runs.coding_worker_last_heartbeat_at`). A conservative, read-only
classification of that evidence now exists too. What is still missing is
*authority*: the evidence cannot be turned into a verdict that authorises
anything.

- `agent_runs` carries a heartbeat column, but it records only that the
  recorded owner last reported. Nothing converts a stale timestamp into a
  liveness decision: there is no expiry rule, no takeover, no death marker,
  and no startup path that reads it. The other liveness-adjacent fields
  (`started_at`, the ownership identities) remain what they were.
- `coding_worktree_leases` has exactly the right shape — `worker_id`,
  `last_heartbeat_at`, `expires_at` — but **no production code path creates a
  lease**, and the lease contract is worktree-scoped, so it cannot own a
  Guardian run that has no branch, no worktree path, and no work order.
- The coding worker publishes a **per-run, claim-scoped** heartbeat for the run
  it owns. It is scoped to one run and one claim, and it stops when the
  execution ends — so it is not a global worker heartbeat, and a heartbeat that
  stops advancing does not, by itself, say why.
- The dispatch record (`guardian/core/guardian_dispatch.py`) is a frozen,
  unpersisted value object with no worker-identity field. Its
  `last_heartbeat_at` and `lease_expires_at` are *inputs* to the classifier,
  not observations the runtime records.
- The liveness classification reads the canonical evidence and reports a
  conservative verdict — `stale_uncertain` is exactly "recent liveness
  evidence is missing", and it authorises nothing. It is not wired into any
  startup or dispatch path.
- Fencing is absent by design, and stays absent.

Consequently, **no restart reconciliation is implemented today**. A restarted
coding worker performs no classification, writes no escalation, re-inserts no
task, issues no credential lease, invokes no provider, and fabricates no
source-thread result. That is the correct behaviour under the gate: an
implementation built on the available signals would either escalate a run whose
worker is alive and mid-execution, or escalate nothing at all.

**The disposition already exists.** The operator-visible outcome for an
unresolved execution needs no migration and no new status. The canonical run
moves to `escalated` — already permitted by the `agent_runs` status check — and
one `agent_escalations` row is written with `status = 'open'`, a `reason_code`,
a human-readable reason, `preserved_worktree`, and a `payload_json` carrying the
recovery evidence. The three states the contract keeps distinct are:

| Meaning | Representation |
|---|---|
| Recovery classification | `uncertain` / `quarantined` in the dispatch vocabulary |
| Canonical run disposition | `agent_runs.status = 'escalated'` |
| Actual execution result | `unknown`, carried in the escalation evidence |

**What is deferred.** The durable worker-ownership and liveness authority that
would let the worker decide that a run is genuinely abandoned, and the fencing
that would let a reconciler be safe against a late terminal success. The next
task supplies that authority; the recovery contract, the disposition, and the
startup integration point are already in place for it. The evidence is in
`docs/architecture/proofs/runtime/2026-10-23-guardian-coding-restart-reconciliation-proof.md`.

### Dispatch recovery

The queue is `LPUSH` + destructive `BRPOP`/`RPOP` with no ack, no pending list, and no requeue. Four layers must therefore be kept distinct, because a guarantee on one says nothing about another:

| Layer | Guarantee | Mechanism |
|---|---|---|
| Task delivery | **At-most-once, and lossy** | `guardian/queue/redis_queue.py` |
| Attempt execution | **Unguaranteed** | a dequeued task may still be executing |
| Execution effects | **Not idempotent** | the adapter runs a subprocess with write access and may commit |
| Result delivery | **Idempotent** per (intent, run) | `build_guardian_delegation_result_delivery_key` |

**No exactly-once execution claim is made.** A missing heartbeat is *uncertain*, not lost: the worker may be between phases, blocked on a subprocess, or in a long validation loop. Recovery is therefore **quarantine-and-escalate**. Automated re-dispatch is refused while no fencing token exists, because without fencing a superseded attempt's writes cannot be rejected, and isolation alone bounds cross-contamination but not duplicate logical effects. A recovery attempt must mint a new attempt id, a new binding, and a freshly issued credential lease. This mirrors the existing chat recovery idiom, which also refuses to execute during recovery.

Dispatch state lives in `guardian/core/guardian_dispatch.py` and is durable and queryable: `prepared`, `dispatched`, `executing`, `completed`, `failed`, `uncertain`, `quarantined`, `cancelled`. Recovery reads that state; it never infers from absence.

The durable acceptance record described above is the substrate this recovery reads: it is what makes an accepted run distinguishable from a queued, never-started run after the worker process disappears. Restart-time reconciliation of that record — reading it at startup and classifying the uncertain outcomes it implies — is **not implemented** and remains a separate, dependent task.

## Coding Delegation Context Policy

Guardian-to-coding-agent delegation is work-scoped by default.

Authoritative default context hierarchy, highest precedence first:

1. `source_message_id` and the selected user turn
2. Codexify Project Knowledge Base
3. Project-scoped architecture docs, ADRs, task files, protocols, and linked artifacts
4. GitHub repository context when configured and task-relevant, including relevant files, issues, PRs, commits, and discussions
5. Current thread context only when needed to resolve immediate task framing
6. Explicitly work-scoped engineering preferences and protocols

Excluded by default:

- broad chat history
- general personal facts
- identity-derived facts
- emotional venting
- client, boss, or relationship commentary
- unrelated prior conversations

Required rules:

- Guardian coding delegation may use only explicit task input, project-scoped knowledge, linked artifacts, configured repository context, and explicitly work-scoped preferences/protocols.
- Personal facts and broad chat history are excluded by default.
- Stored preferences or protocols may be included only if explicitly marked work-scoped, relevant to the task, policy-allowed, and recorded in `context_basis`.
- Raw personal facts may never be injected directly into coding prompts, agent commentary, code comments, commit messages, PR text, or result summaries.
- No coding task prompt, code comment, commit message, PR text, agent commentary, or result summary may include excluded personal or conversational context.

## `ContextBasisEntry`

`ContextBasisEntry` is the minimum provenance unit for any context included in a Guardian-to-coding-agent delegation payload.

Required fields:

| Field | Meaning |
| --- | --- |
| `source_type` | The canonical source category for the included context. |
| `source_id` | Stable reference for the included source object, document, thread turn, repo object, or policy artifact. |
| `included_fields` | The specific fields, excerpts, or structured attributes that were included from the source. |
| `reason` | Why the source was included for this delegated task. |
| `confidence` | The confidence Guardian has that the source is relevant and correctly scoped for the delegated task. |
| `policy_allowed` | Boolean or equivalent explicit indicator that policy allowed inclusion of this source. |

Recommended `source_type` values for coding v1:

- `selected_turn`
- `project_kb`
- `architecture_doc`
- `adr`
- `task_file`
- `protocol_doc`
- `linked_document`
- `linked_image`
- `github_file`
- `github_issue`
- `github_pr`
- `github_commit`
- `github_discussion`
- `thread_frame`
- `work_scoped_preference`

## Invariants

- Guardian may not infer durable user identity traits or durable intent from the delegated task.
- Guardian coding delegation may use only explicit task input, project-scoped knowledge, linked artifacts, configured repository context, and explicitly work-scoped preferences/protocols.
- Personal facts and broad chat history are excluded by default.
- A delegated result may not post back to the thread without `thread_id`, `source_message_id`, and lineage.
- A superseded run may complete, but its result must be suppressed from the source thread.
- Durable run transcript is sourced from agent-run events.
- Thread interruptions and global notifications are mirrors.
- Acceptance, approval, execution, and visibility must not be collapsed into one state.
- The reasoning effort is Guardian's to select and the binding's to carry. A worker task may not choose or widen its own invocation options, and an effort the Guardian did not authorize must not reach the harness.
- The credential that authorizes a delegated execution keeps its real owner. A service-owned credential serves an account only where the service's own recorded policy names that account, provider, model, funding route, and usage policy, and it remains service-owned in the binding. Credential discovery is not authorization, and an account principal does not become the credential's owner by using a service-owned key.
- A side-effecting coding execution may not begin until its acceptance is durably recorded in canonical PostgreSQL. Missing or unreachable persistence is never permission to execute, and a refused or duplicated acceptance never overwrites another worker's run, artifact, or source-thread result.
- A coding run records the worker instance that accepted it and the unique claim it made, atomically with acceptance. Worker identity is executor metadata: it is not an account, a principal, or a credential owner, and a queue payload cannot choose it. A persisted owner is not proof of liveness, and a claim identity grants no retry authority.
- Only the recorded owner and claim may renew a coding run's heartbeat, and renewal is a single conditional database update. A heartbeat is evidence of reported activity, never authority to execute, retry, escalate, or take over. A stale heartbeat is not proof of worker death, and a missing heartbeat on a historical run is not evidence of abandonment.
- Only the recorded owner and claim may finalize an accepted coding run, and the terminal decision is a single conditional database update committed together with the result writes that belong to it. A rejected claim writes no terminal status, no coding-result artifact, no source-thread result, and no terminal event. A terminal or escalated run cannot be reopened, and a heartbeat never authorizes a terminal write by itself.
- A coding run's liveness may be classified from canonical evidence, and the classification is read-only. A stale heartbeat is evidence that recent liveness evidence is missing, never proof that the worker died; a recent heartbeat is evidence of recent activity, never proof that a process exists; a missing heartbeat on a historical run is evidence of nothing. The classification reports evidence and a conservative verdict; it never retries, requeues, terminates a process, revokes a credential, replaces a binding, transfers ownership, or escalates a run, and it never mutates canonical state.
- An uncertain coding run may be dispositioned only by a **verified** operator authority, and only while its recorded worker instance and claim still own it and its heartbeat is still older than the observation horizon. The disposition and its escalation evidence commit together; it preserves the original owner and claim; it creates no retry, requeue, credential, binding, or ownership authority; and a terminal or escalated decision that committed first is never overwritten.
- A restart may not classify a coding execution as abandoned without durable evidence of worker ownership and liveness. An elapsed timestamp, an empty queue, or a missing lease row are not such evidence. Until that authority exists, an accepted run that never reached a terminal state stays unresolved rather than being escalated, retried, or declared lost.

## Deferred Phases / Non-Goals

- No runtime implementation in this slice.
- No route implementation in this slice.
- No database migration in this slice.
- No second thread.
- No broad auto-approve.
- No intent-spine unification.
- No current-state/release-truth widening.

## Proof Surface for Future Phases

- Safe happy path proves selected turn -> work-scoped `context_basis` -> `GuardianDelegationIntent` -> scoped auto-approval -> AgentRun dispatch -> linked `run_id`.
- Thread closure proves exactly one terminal result delivery.
- Supersession proves stale completion suppression.
- Command Center proves transcript mirror from durable run events.
- Approval lifecycle proves approve/cancel behavior only after happy path is proven.
