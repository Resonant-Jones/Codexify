---
tags:
* architecture
* adr
* agent-run
* cancellation
* execution-lifecycle
  aliases:
* ADR-104
* Agent Run Cancellation Intent
* Cancellation Intent and Worker Observation
---

# ADR-104: Agent Run Cancellation Intent and Worker Observation

## Status

**Proposed** — 2026-10-27. Not accepted. This document proposes a contract for human
review; it does not authorize an implementation, and it does not change any accepted
decision.

## Date and evaluated source revision

| Field | Value |
| --- | --- |
| Date | 2026-10-27 |
| Evaluated source revision | `07069740e63107413b8e324d4b4fb99e8beb25a8` (`origin/main`) |
| Proposal branch | `architecture/agent-run-cancellation-intent-proposal` |
| Source reconciliation | PR [#917](https://github.com/Resonant-Jones/Codexify/pull/917), evidence commit `568d4445d337b0570149d33532e56b3618e510a2` |
| Related implementation | PR [#914](https://github.com/Resonant-Jones/Codexify/pull/914) |

The source reconciliation is a **proposed** evidence document, not accepted
architecture. It is cited here as the factual basis for the problem statement, and its
conclusions are re-verified against the evaluated revision below.

## Problem statement

Agent Run cancellation is currently not reachable, and the parts of it that are
reachable are not truthful. The source reconciliation recorded five defects. Re-verified
at the evaluated revision, two of them are already fixed and three remain.

The remaining problem is narrower than "cancellation is broken". It is:

> **There is no durable, account-scoped record that a cancellation was requested, and
> therefore no way for a worker to learn that it should stop, and no way for an
> operator-visible surface to distinguish "cancellation requested" from "execution
> terminated".**

Closing the identity and authorization defects (already done) makes the route
*reachable*. It does not make it *correct*: the route still writes a terminal status it
cannot observe, never signals the queue, and has no run-to-queue-task correlation to
signal even if it wanted to.

The reconciliation recommended a durable run-to-queue-task mapping. This ADR proposes a
narrower model, and the narrowing is the substance of the proposal.

## Governing accepted decisions

| Decision | Status | Bearing |
| --- | --- | --- |
| [ADR-020](020-guardian-mediated-coding-agent-execution-contract.md) — Guardian-mediated coding-agent execution | Accepted | Guardian owns intake, request identity, thread identity, policy, and result ingestion. A cancellation request is a Guardian-side decision about a Guardian-owned execution, and the terminal decision about a coding result stays with the party that observes it. |
| [ADR-081](081-project-ownership-authority.md) — Project and thread ownership authority | Accepted | `projects.user_id` and `chat_threads.user_id` are the durable ownership authorities. Human-visible description data and deployment metadata never grant, deny, transfer, select, or override account authority. |
| [ADR-092](092-credential-purpose-and-mixed-principal-authentication-boundary.md) — Credential purpose and principal separation | Accepted (partial runtime implementation) | Account sessions, operator sessions, and Hosted Room guest sessions are distinct credential classes. An operator credential never becomes an account credential. Mixed principals fail closed. |
| [ADR-094](094-account-scoped-execution-credential-authority.md) — Account-scoped execution credential authority | Accepted | Guardian authenticates the invoking principal and verifies its account before dispatch, and records a secret-free owner-scoped binding. The durable binding — not deployment metadata — is the execution's authority record. |

### Related but not accepted

[ADR-039](039-operator-user-access-boundary.md) — Operator / User Access Boundary is
**Proposed**, not Accepted. It cannot independently authorize local operator
cancellation, and this ADR does not rely on it.

### Unrelated decisions whose allocation is preserved

- **ADR-102** — Saved Widget Identity, Classification, and Revision Boundary. Accepted 2026-10-25.
- **ADR-103** — Recipient-Local Direct Message Read State. Accepted 2026-10-26.

Neither decision is present in this base revision: ADR-102 is allocated and accepted on
its own integration line, and ADR-103 is allocated and accepted on local development
branches. Their numbers are reserved and are recorded here so that they are not reused.
They are named in plain text rather than as links, because at this revision their source
files are not present in the tree and a link to them would be a broken link. This ADR
neither amends nor supersedes either one.

## Existing implementation findings

All findings below were re-verified at the evaluated revision
`07069740e63107413b8e324d4b4fb99e8beb25a8`.

### F1 — The evaluated mainline does not parse, and CI reported green anyway

**Proven by source inspection.** Two tracked Python files fail `ast.parse` at the
evaluated revision:

| File | Parse failure |
| --- | --- |
| `guardian/routes/agent_orchestration.py` | line 497 — `leading zeros in decimal integer literals are not permitted` |
| `tests/core/test_supported_profile_quarantine.py` | line 62 — `':' expected after dictionary key` |

A sweep of all 2,080 tracked Python files found exactly these two failures.

The cause in the route module is a merge resolution defect. Commit `f2ecc40da`
("Merge branch 'main' into integrate/coding-readback-contracts-20261027", landed on
main through PR #916 as `47d5c5989`) introduced a new
`_authenticated_account_user` function and **dropped the closing `"""` of its
docstring**. The unterminated string therefore swallows the remainder of the module
until line 676, and `ADR-020` inside a later docstring is parsed as a numeric literal.
The last revision at which this file parsed was `324780eda`.

The consequence is that `guardian.routes.agent_orchestration` **cannot be imported at
the evaluated revision**, so the entire Coding Agent route surface — including the
Coding Loop execute route and `cancel_run` — is non-loadable on main.

**This is invisible to the current CI posture.** The Guardian CI run for the evaluated
revision (`40527720430`) reports `Backend Tests (Python 3.11): success`, but the job
took the **no-op path**: `backend_changed=false`, and the `Run backend tests` step
conclusion is `skipped`. The run that would have exercised the breakage — the CI run
for the PR #916 merge, `40527634752` — was **cancelled after 33 seconds** by the
workflow's `concurrency: guardian-ci-${{ github.ref }} / cancel-in-progress: true`
group when the next push arrived. The breakage therefore reached main without a single
pytest execution against it.

This finding is recorded because it constrains the implementation prerequisite order:
no cancellation work can be validated on this mainline until the parse break is
repaired, and the CI posture that let it through needs independent attention.

### F2 — Identity and authorization defects are already fixed

**Proven by source inspection.** Commit `8d4965dca` ("fix(agents): require durable
ownership for run cancellation", merged through PR #915 as `04489d7b2`) repaired two of
the five defects recorded by PR #917. The current `cancel_run` body:

```python
request_user = _resolved_request_user(current_user)
if dependencies.is_private_preview() or dependencies._auth_mode() == "remote":
    run = _store.get_account_run(run_id, user_id=request_user)
else:
    run = _store.get_run(run_id, user_id=request_user)
```

So the current implementation resolves the authenticated identity without a
caller-requested identity, and uses the durable account reader in remote and Private
Preview modes while keeping the bounded local operator reader in local mode. Defects 1
and 2 of the reconciliation are closed. The three remaining defects are not.

### F3 — The route still claims a terminal outcome it cannot observe

**Proven by source inspection.** The remainder of the handler is unchanged:

```python
_store.update_run_status(run_id=run_id, status="canceled")
_event_publisher.emit(run_id=run_id, event_type="canceled", payload={"run_id": run_id})
return {"ok": True, "run_id": run_id, "status": "canceled"}
```

`AgentStore.update_run_status` (`guardian/agents/store.py:1043-1090`) returns `True` for
a *refused* transition — a run whose status is already terminal and different returns
`True` without changing the row — and the route ignores the return value. The route
therefore publishes a `canceled` event and answers `{"status": "canceled"}` for a run
that may have already succeeded. PR #917 reproduced this as a false-success scenario.

### F4 — The route never signals the queue

**Proven by source inspection.** The route module imports only
`guardian.queue.task_events` and `enqueue_coding_execution`; `redis_queue.cancel` is
never imported. The route has no queue-cancellation path at all.

### F5 — No durable run-to-queue-task mapping exists

**Proven by source inspection.** `redis_queue.enqueue_coding_execution` generates
`task_id = str(uuid.uuid4())` internally and returns it; the execute route
(`guardian/routes/agent_orchestration.py`, `enqueue_coding_execution(task_payload)`)
discards the return value. The `agent_runs` table has no queue-task column. The only
link between a durable run and its queued execution is a `run_id` field inside a Redis
queue record, and Redis is not the durable authority for that relationship.

### F6 — The worker already owns terminalization correctly, and already has a persisted execution claim

**Proven by source inspection.** `guardian/workers/coding_worker.py:4146-4173`:

```python
def _emit_cancelled(self, task: CodingExecutionTask) -> None:
    """Emit task.cancelled event."""
    self.store.update_run_status(run_id=task.run_id, status="canceled")
    task_events.publish_with_visibility(
        task.run_id, "task.cancelled",
        {**build_coding_result_lineage_payload(
            run_id=task.run_id, queue_task_id=task.task_id, ...),
         "status": "cancelled", "reason": "cancelled_before_execution"},
    )
```

The worker sets the terminal status and publishes the canonical `task.cancelled` token
**only when it has observed the cancellation**, and it carries full lineage. The route
duplicates and pre-empts this with a strictly weaker write. Terminal cancellation is
already correctly owned by the party that can observe it.

### F7 — Run identity transport is sufficient for durable observation

**Proven by source inspection.** The supported account-owned coding path carries one
canonical run identity end to end:

| Stage | Evidence at the evaluated revision |
| --- | --- |
| Run id is server-generated | `AgentStore.create_run` — `run_id = _new_external_id("run")` (`guardian/agents/store.py:741`) |
| Run id is durable | `agent_runs.run_id`, `String(64)`, `unique=True`, `nullable=False` (`guardian/db/models.py:5537`) |
| Queue payload carries the same run id | execute route — `"run_id": run["run_id"]` in the coding execution task payload |
| Worker receives that identity | `CodingExecutionTask.run_id` (`guardian/tasks/types.py:655`); `task = task_from_dict(payload)` (`coding_worker.py:1758`) |
| Worker can reach the canonical store | `self.store = agent_store or _store` (`coding_worker.py:1750`); `self.store.get_deployment(...)` is already used at admission |
| The run id locates the intended run | `AgentRun.deployment_id` → `AgentDeployment.spec_json.execution_binding` → the persisted execution claim |

**A run id is a locator, not a bearer capability.** Possession of a run id confers no
authority: authorization is the separate durable account-origin check, and the worker's
use of the run id is a lookup of a record it already holds an execution claim against.

### F8 — The worker already has a persisted execution claim, and it binds the attempt

**Proven by source inspection.** `_validate_task_execution_binding`
(`guardian/workers/coding_worker.py:1714-1743`) requires the queue payload's
`execution_binding` to be **exactly equal** to the deployment's persisted
`execution_binding` (`execution_binding_queue_mismatch` otherwise), and then requires
the binding's `coding_task_id`, `attempt_id`, `thread_id`, `source_message_id`,
`user_id`, and `project_id` to match the task and the deployment. The binding is
persisted in `agent_deployments.spec_json.execution_binding`.

The durable chain is therefore:

```
AgentRun.run_id → AgentRun.deployment_id → agent_deployments.spec_json.execution_binding
                                                          ↳ attempt_id, coding_task_id, user_id, thread_id, source_message_id
```

`CodingExecutionBinding` does **not** carry `run_id`; the run→claim link is the
deployment foreign key. `agent_runs` has no attempt column.

### F9 — Cancellation checkpoints are bounded, and the adapter is not interruptible

**Proven by source inspection.** The coding worker consults `is_cancelled(task.task_id)`
at exactly two points: `coding_worker.py:2046` (start of `_process_task`, before
deployment lookup, binding validation, credential lease, and adapter invocation) and
`coding_worker.py:2679` (first statement of each validation-attempt iteration, before
that attempt's adapter call). The adapter executes through a blocking
`execute_authorized(request, identity, credential_material=..., read_only=...)`
(`coding_worker.py:2825`); `AgentExecutionRequest` carries no cancellation callback, and
`AgentAdapter.execute` is synchronous.

`guardian/workers/agent_worker.py` contains no cancellation handling at all.

### F10 — The reconciliation's evidence remains sound, but two of its five defects are now closed

The PR #917 evidence document was merged as
`docs/architecture/proofs/runtime/2026-10-27-agent-run-cancellation-authority-reconciliation.md`.
Its defect list was accurate **for the revision it evaluated**
(`9bb23732bff11e2d49a325cabde11f4019374f0d`). Defects 1 and 2 were fixed afterwards by
`8d4965dca`. Defects 3, 4, and 5 remain, and F1 above is newer than the reconciliation
and was not visible to it.

## Alternatives considered

### A. A new `AgentRun` status such as `cancellation_requested`

| Dimension | Assessment |
| --- | --- |
| Canonical authority | Strong: `AgentRun` is already the durable run authority. |
| Schema complexity | Low: one enum value. |
| Migration cost | Low: one constraint change, no new column, no backfill of existing rows. |
| Idempotence | Poor. A status is a single mutable value; "requested" and "requested again" are indistinguishable, and re-requesting after a terminal outcome would have to be encoded in the status vocabulary rather than derived. |
| Concurrent state transitions | Poor. The status is the same field a worker writes on completion. A cancellation request and a worker completion contend for one column, so the ordering of two writers must be arbitrated by the value alone, and a request that loses the race has no durable trace. |
| Export and restore | Would require the new status to be recognized by every restore path as an in-flight intent rather than a terminal outcome. |
| Operator legibility | High, but at the cost of putting a *request* into a field that otherwise means "what the run is doing". |
| Compatibility with terminal states | Poor. The existing `agent_runs_status_check` constraint permits only `('queued','running','escalated','canceled','failed','succeeded')`, and `_is_terminal_agent_run_status` treats `escalated` as terminal. Adding a non-terminal status changes the meaning of "terminal" for every reader of the column, and the reconciliation already showed that a terminal-status guard can silently refuse a transition while the caller believes it succeeded. |
| Recovery after worker or Redis restart | Good: a status survives both. |
| Requesting-account attribution | Poor: the status column cannot also carry who requested it. |
| Additional control-plane complexity | Low. |

**Not recommended.** It overloads the one field that records the run's *outcome* with a
*request*, and it makes a request compete with a completion for a single value.

### B. A separate durable cancellation-request entity

| Dimension | Assessment |
| --- | --- |
| Canonical authority | Mixed: a second durable table creates a second source of truth about a run's lifecycle, and the relationship between a run and its cancellation request becomes a new consistency problem. |
| Schema complexity | High: a new table, its foreign keys, its own lifecycle, its own export/restore handling. |
| Migration cost | High: new table, new indexes, new ORM mappings, new migration. |
| Idempotence | Good: a unique constraint on `(run_id)` makes a duplicate request a no-op. |
| Concurrent state transitions | Good: the request row is independent of the run's status column, so a request and a completion do not contend. |
| Export and restore | Requires a new join in every export path, including the account export/restore contract governed by ADR-081. |
| Operator legibility | Good, but requires a second read to answer "was this cancelled?". |
| Compatibility with terminal states | Good: a request can be recorded against an already-terminal run without changing the run's outcome. |
| Recovery after worker or Redis restart | Good. |
| Requesting-account attribution | Good: a dedicated column. |
| Additional control-plane complexity | **High.** A parallel run-state store is explicitly out of scope for this proposal. |

**Not recommended.** It is the most expressive option and the most expensive one. It
introduces a second durable lifecycle for a single run, and the reconciliation's own
guidance was to avoid a parallel run-state store.

### C. Monotonic cancellation-intent metadata on the existing `AgentRun` — **recommended**

| Dimension | Assessment |
| --- | --- |
| Canonical authority | Strong: `AgentRun` remains the single durable run authority, exactly as the invariants require. |
| Schema complexity | Low: additive nullable metadata on an existing row. No new table, no new relationship, no new lifecycle. |
| Migration cost | Moderate: one migration adding nullable columns and their index. No backfill is meaningful — existing rows have no request. |
| Idempotence | Good: intent is monotonic. A second request either finds the same request or records a later one; neither erases the first. |
| Concurrent state transitions | Good: intent metadata is disjoint from the `status` column, so a cancellation request and a worker completion never contend for the same value. A committed terminal outcome can never be overwritten by a later request. |
| Export and restore | Moderate: the intent fields join the existing `agent_runs` projection. They are attributes of a run, not a separate resource, so account export/restore needs no new join. |
| Operator legibility | Good: "cancellation requested" is readable from the run record without a second lookup, and it is visibly distinct from the run's actual status. |
| Compatibility with terminal states | Good: the intent fields are orthogonal to `status`. A run can be `succeeded` and still carry a recorded request, and the request never changes the recorded outcome. |
| Recovery after worker or Redis restart | Good: intent is durable, so a restarted worker reads it. This is strictly better than the Redis flag, which is a non-durable request marker. |
| Requesting-account attribution | Good: a dedicated field records the requesting account. |
| Additional control-plane complexity | Low: no new control plane, no new resolver, no new authority concept. |

**Recommended.** It is the only option that keeps `AgentRun` as the single durable run
authority, keeps request and outcome orthogonal, and avoids a second control plane.

### D. Persist a run-to-queue-task correlation and call `redis_queue.cancel(task_id)`

**Not recommended for this contract, and not required.** See the observation model
below. The Redis cancel set is a request marker without timestamp, requester, reason, or
expiry, and it is not an account-scoped authority. Making it the mechanism for
account-owned cancellation would create exactly the parallel cancellation truth this
proposal is designed to avoid. The correlation remains a legitimate future optimization
for task families that have no durable run record, and the existing Redis mechanism
stays available for them.

## Recommended durable intent representation

**Cancellation intent is durable, monotonic metadata on the existing `AgentRun` row,
orthogonal to the run's `status` column.**

Conceptually, an intent carries:

| Concept | Purpose |
| --- | --- |
| *when the request was recorded* | Ordering against terminal outcomes, and operator legibility. |
| *which account recorded the request* | Attribution, and the proof that the request came from an authorized account rather than from the possession of a run id. |

These are **conceptual** fields. Exact names, types, nullability, index shape, and
migration behavior are implementation decisions for the implementation task, not
decisions of this ADR. This ADR does not add them.

Three properties are decided here, because they are the contract rather than the
encoding:

1. **Intent is additive.** Recording a request never changes `AgentRun.status`.
2. **Intent is monotonic.** A recorded request is never erased by a later request, a
   worker completion, or a failure.
3. **Intent is not a terminal outcome.** A run that carries a recorded request may still
   be `running`, and may still end `succeeded` or `failed`. The recorded outcome and the
   recorded request are two separate facts about the same run.

## Run ID authority and observation model

**The run id is the observation key; it is never the authority.**

The proposed model:

```
HTTP cancellation request
  → authenticated account (account-session authority)
  → durable account-origin + canonical thread ownership + lineage check
  → one transaction: recheck ownership, recheck terminal status, record intent
  → commit
  → acknowledge the REQUEST (not the termination)
  → worker observes the intent at a supported checkpoint, through the canonical run id,
    while holding the execution claim for that run
  → worker abandons the attempt and commits the terminal canceled transition
  → worker publishes the canonical task.cancelled token
  → durable readback shows both the recorded outcome and the recorded request
```

The worker resolves the canonical `AgentRun` by the run id it already holds, reads the
durable intent, and acts on it. **This makes a persisted run-to-queue-task correlation
unnecessary for this contract.** The correlation exists only to call
`redis_queue.cancel(task_id)`; if the worker observes intent directly through the run
record, the queue task id is not needed to deliver the intent.

What the run id does *not* do:

- It does not authorize anything. A request is authorized by the account check, not by
  the run id.
- It does not identify the attempt. The attempt is identified by the execution claim.
- It does not carry queue ownership. Queue identity is not ownership.

### Producer scope

`CodingExecutionTask` is produced by more than one path, and the proposal does **not**
apply uniformly.

| Producer | Reliable run identity? | In scope? |
| --- | --- | --- |
| The Coding Loop execute route (`POST /api/agents/coding/execute`) | Yes — the run is created by the same handler, and the queue payload carries `run["run_id"]` | **Yes.** This is the supported account-owned coding path. |
| Any other producer of `coding_execution` queue records | Not established | **No.** A producer without a durable account-owned run must not be brought under this contract by assumption. A producer that does not carry a reliable run id, or that carries one without a matching execution claim, must be recorded as a limitation and excluded. |

This ADR does not assume the proposal applies to every execution family, and it does not
assert coverage of producers it has not traced.

## Execution-claim and attempt consistency

Worker observation must be consistent with the legitimate execution claim, so that a
stale or unrelated attempt cannot act on — or be confused by — a cancellation intent.

The mechanism already exists at the evaluated revision. `_validate_task_execution_binding`
already requires the queue payload's `execution_binding` to equal the deployment's
persisted `execution_binding` exactly, and already binds `coding_task_id`, `attempt_id`,
`user_id`, `thread_id`, and `source_message_id`. The proposed observation is therefore
fenced by three checks the worker can already perform:

1. **Run identity** — the task's `run_id` resolves to a canonical `AgentRun`.
2. **Claim identity** — that run's deployment carries the same persisted
   `execution_binding` the task carries, including its `attempt_id`.
3. **Claim freshness** — the attempt that observes the intent is the attempt the
   accepted execution claim describes. A superseded attempt, or a redelivered record
   whose attempt no longer matches, does not act on the intent.

A run that carries a recorded intent but whose binding does not match the observing
task's binding is **not** observed by that task. A stale attempt must not be able to
consume or clear an intent that belongs to a different attempt.

**Fail-closed admission.** If the database cannot establish the required authority at a
checkpoint — the run cannot be read, the deployment cannot be read, the binding does not
match — the worker **fails closed**. It does not execute, and it does not treat the
uncertainty as permission to proceed. A failed read is not proof that a cancellation was
observed, and it is equally not proof that one was not requested. These are different
states and must be reported differently: *observation of a cancellation* is a positive
finding; *failure to establish authority* is a separate condition.

## Account authorization rules

The initial proposed scope is **account-owned coding runs with durable account-origin
provenance**.

A valid cancellation request requires all of:

1. Valid account-session authority (ADR-092 credential class, not an operator or guest
   credential).
2. A canonical account identity resolved from the authenticated request context.
3. Matching durable account-origin provenance on the run
   (`agent_runs.account_origin_user_id`).
4. A surviving canonical thread owned by that account.
5. Consistent deployment/run/thread lineage.
6. A run in a state eligible for cancellation — not already terminal.
7. Ownership and status checked **in the same database transaction** that records the
   intent.

Unknown and foreign resources remain **existence-hidden** (404), consistent with the
2026-10-02 readback proof and ADR-081.

Cancellation authority is **never** derived from:

- deployment metadata,
- a queue task id,
- a coding task id,
- an attempt id alone,
- Project metadata,
- a thread id alone,
- provider identity,
- worktree lease identity.

The first implementation must not grant cancellation rights to remote operator
credentials, Hosted Room guests, mixed principals, historical NULL-origin runs,
operator-created runs, memory-only runs, or foreign-account resources. Local
account-authenticated execution may qualify **when the same durable account ownership
requirements are satisfied** — the local lane does not relax the ownership proof, it
only changes which credential class authenticates the account.

## Cancellation request outcomes

A request-level outcome is a distinct thing from a terminal outcome. The proposed
outcomes and HTTP semantics are:

| Outcome | Meaning | Proposed HTTP |
| --- | --- | --- |
| `request_recorded` | The account was authorized, the run was eligible, and the intent was committed. | `202 Accepted` |
| `already_requested` | The account was authorized and the run is eligible, and an intent is already recorded. The request is idempotent. | `202 Accepted` (idempotent) |
| `already_terminal` | The run has already reached a terminal outcome. A cancellation cannot be truthfully applied, and the committed outcome is not replaced. | `409 Conflict` |
| `not_found_or_not_authorized` | The run does not exist, or is not visible to this account. The two are indistinguishable. | `404 Not Found` |
| `storage_unavailable` | The durable store could not establish or record the request. | `503 Service Unavailable` |

The response must **not** claim terminal cancellation, and must not set
`status = "canceled"`. It reports that a request was recorded, and the request-level
distinction is carried by the outcome name rather than by a new canonical protocol
token. **No new canonical token is introduced by this ADR.** The existing
`task.cancelled` token keeps its meaning — a worker-observed, durably committed
terminal cancellation — and the route's bare `canceled` event type is a defect to
remove, not a vocabulary to extend.

## Worker observation and terminal acknowledgement

A worker may report a terminal cancellation **only** after all of:

1. It observes the durable cancellation request on the canonical run.
2. It confirms the expected execution identity for that run and attempt.
3. It abandons execution at a supported checkpoint.
4. The terminal canceled transition is durably acknowledged.
5. The transition still belongs to the expected run and execution attempt.

**`AgentStore.update_run_status` is not sufficient terminal-transition proof.** As
recorded in F3, it returns `True` for some refused state changes, and it performs no
ownership check. The implementation must introduce an explicit transition outcome —
something that distinguishes *transitioned* from *already terminal* from *not found* —
**before** the canonical `task.cancelled` event is published. No terminal cancellation
event may be published before authoritative persistence acknowledges the terminal
outcome.

Proposed observation points, to be re-verified against the code as it exists at
implementation time:

| Point | Current location | What it can establish |
| --- | --- | --- |
| Before execution admission | `coding_worker.py:2046` | The run was never started; the attempt can be abandoned with no adapter invocation. |
| Before each validation attempt | `coding_worker.py:2679` | The attempt is abandoned at an attempt boundary. |

The current `is_cancelled(task.task_id)` checks are **not** the proposed checks. They
read a Redis flag keyed by the queue task id. The proposal replaces them, for
account-owned coding runs, with a durable intent read through the canonical run id and
the execution claim. Redis cancellation is **not** modified by this proposal and
remains available for other task families; it must not become a parallel authority for
account-owned Agent Run cancellation.

## In-flight limitations

The coding adapter executes through a blocking call with no cancellation callback and
no interruption surface. This ADR therefore states, and does not exceed:

- A **queued** run can be abandoned when the worker observes the intent before
  execution.
- An **admitted** run can be abandoned at a supported checkpoint.
- An **actively executing adapter is not proven interruptible.** No in-flight process
  interruption mechanism is authorized by this ADR.
- A cancellation request received during execution **may remain pending**; it is
  observed at the next supported checkpoint, if the attempt is still alive.
- Execution may **finish before** a cancellation can be observed. A completed run
  retains its actual terminal outcome.
- A durable cancellation request is **not proof that execution stopped**.

The only duration bound on the adapter is the execution timeout budget, which is a
timeout and not a cancellation mechanism.

## Idempotence and concurrency

| Scenario | Proposed behavior |
| --- | --- |
| Duplicate cancellation request | Idempotent. The first eligible request records the intent; a second finds it recorded and returns the idempotent `202`. No second terminal event is produced, because a terminal event is only produced by the worker's terminal transition. |
| Cancellation versus successful completion | Whichever transaction commits first is authoritative for that field. A cancellation intent committed after a terminal outcome returns `already_terminal` and does not alter the recorded outcome. A terminal outcome committed after a recorded intent does not erase the intent, and the run keeps both facts. |
| Cancellation versus failure | As above. The recorded outcome is never overwritten by a request. |
| Cancellation versus worker admission | The worker observes the intent at admission and abandons the attempt, producing the canonical terminal outcome. |
| Cancellation versus another validation attempt | The intent is observed at the next attempt boundary. |
| Worker restart | The intent is durable on the run. A restarted worker reads it at the next supported checkpoint. This is strictly stronger than a Redis marker, whose survival depends on Redis persistence configuration. |
| Duplicate queue delivery | The first delivery observes the intent and abandons the attempt. A redelivery observes the same intent and abandons again. Because the attempt binding is checked, a redelivery whose attempt no longer matches the persisted claim does not act. |
| Database read failure at a checkpoint | Fail closed. The worker does not execute under unresolved admission authority, and does not report an observed cancellation it did not establish. |
| Redis restart | Not material to this contract, because the contract does not depend on Redis for account-owned cancellation intent. |
| Stale execution claims | An attempt whose binding does not match the run's persisted claim does not observe or consume the intent. |
| Concurrent ownership change | The ownership check and the intent write occur in the same transaction, so a concurrent reassignment is either seen before the write (the request is refused) or after it (the reassignment is a separate governed operation). |

**An earlier cancellation request must not automatically rewrite a later legitimate
completed result.** The two are separate durable facts. The implementation must prove
that terminal acknowledgement and event publication remain coherent under these races.

## Restart and recovery

- The intent is durable on the run, so it survives worker restart, Redis restart, and
  process crash.
- A worker that crashes before observing a recorded intent leaves the run in a
  non-terminal state carrying the intent. The next attempt for that run observes it.
- A worker that crashes *after* committing the terminal transition but before publishing
  the event leaves a durable terminal state with a missing event. The implementation
  must define whether that is repaired, and if so by what mechanism. This ADR does not
  decide it; it records it as an open implementation question.
- Redis loss does not lose the intent, because the intent is not in Redis.

## Local operator deferral

**Deferred, explicitly.**

Out of the initial scope:

- threadless local operator runs,
- operator-created runs,
- operator-authorized cancellation,
- hosted or cross-node cancellation,
- in-flight adapter interruption.

**Local operator readback compatibility does not automatically grant cancellation
authority.** The local lane's bounded read compatibility exists because legacy local
run inspection had no durable account provenance to check; a *mutation* is a different
decision, and it needs separate accepted authority.

ADR-039 is **Proposed**. It cannot be used as accepted authority for a local operator
mutation right. A future decision must either accept an operator-cancellation rule or
record that local operator cancellation is not authorized at all. The local lane's
existing `get_run` reader is retained for readback; this ADR does not propose to
change it, and it does not propose that the local lane use it for cancellation
authority beyond what an accepted decision permits.

## Schema implications

This ADR proposes **no schema change as an act of this document**. The implementation
that follows an accepted ADR-104 would require:

- One Alembic migration adding monotonic intent metadata to `agent_runs`, with the
  exact column names, types, nullability, and indexes decided at implementation time.
- No backfill that invents request history. Existing rows have no recorded request,
  and that absence must remain distinguishable from "requested and cleared".
- No change to the `agent_runs_status_check` constraint, because the intent fields are
  orthogonal to `status`.
- No change to the `account_origin_user_id` column, to thread ownership, to the
  `agent_deployments` projection, or to the execution binding schema.

The migration must be compatible with the account export and restore contract governed
by ADR-081: the intent fields are attributes of a run, so they join the existing run
projection rather than requiring a new resource relationship.

## Compatibility and migration concerns

- **Existing runs** are unaffected. A row without intent fields has no recorded
  request, and its behavior is unchanged.
- **Existing queue cancellation** is unchanged. Other task families continue to use the
  Redis mechanism.
- **Existing readback** is unchanged. The intent fields are additive to the run
  projection; they do not alter ownership checks or the account readers.
- **Existing terminal vocabulary** is unchanged. `status` keeps its current values and
  its current meaning.
- **The canonical `task.cancelled` token** keeps its current meaning — a
  worker-observed, durably committed terminal cancellation.
- **The route's bare `canceled` event type** is a defect to remove. It is not adopted
  as a canonical token and is not preserved for compatibility.
- **The evaluated mainline does not parse** (F1). The implementation prerequisite order
  below accounts for that.

## Non-goals

This ADR does not:

- Implement cancellation.
- Modify `cancel_run`, `AgentStore`, the coding worker, the Redis cancellation
  mechanism, or any request schema.
- Add database columns or migrations.
- Introduce a run-to-queue-task correlation.
- Introduce a new canonical status or event token.
- Expand operator authority, or authorize local operator cancellation.
- Amend ADR-020, ADR-039, ADR-081, ADR-092, ADR-094, ADR-102, or ADR-103.
- Change the current-state document, the supported-profile manifest, release
  metadata, or any frontend surface.
- Reopen PR #914, or repair the Whoosh'd CI failure, the frozen operator-manifest
  drift, or the `LOCAL_DEV` collection leak.
- Claim runtime, deployment, or release qualification.

## Implementation prerequisite order

If a human reviewer accepts this ADR, the following order applies. Each step is a
separate, independently reviewable slice; none is authorized by this ADR.

1. **Repair the evaluated mainline's parse break** (F1) and the CI posture that let it
   through unrepresented. Until the route module imports, no cancellation work can be
   executed or proven. This is a prerequisite for *validating* everything below, and it
   is outside the cancellation contract.
2. **Land the explicit terminal-transition outcome** in `AgentStore` — a mutation seam
   that checks ownership and status in one transaction and distinguishes
   *transitioned* / *already terminal* / *not found* / *not authorized* from the
   current bare boolean. Required before any terminal cancellation event is published.
3. **Land the durable intent representation** — migration, ORM mapping, and the
   monotonic, transactional record path.
4. **Land the request-level route contract** — account authorization per the rules
   above, the request-level outcomes, and the removal of the route's terminal write and
   its bare `canceled` event.
5. **Land the worker observation** — durable intent read through the canonical run id
   and the execution claim, at the two supported checkpoints, with fail-closed
   admission.
6. **Land the operator-visible truth** — a surface that shows the recorded request
   separately from the recorded outcome, and does not display "canceled" until the
   authoritative terminal transition has committed.

## Proof required before acceptance or release claims

**This ADR is Proposed. Acceptance requires human review. Any runtime implementation
requires the proof below before it may be described as working.**

1. Authorized durable request creation, with the account-session authority and the
   durable ownership proof, against real PostgreSQL.
2. Foreign-account rejection with existence-hiding 404.
3. Atomic ownership and terminal-status checks — a request committed in the same
   transaction as its ownership check.
4. Duplicate request idempotence — no second terminal event.
5. Worker observation by canonical run identity, and execution-claim and attempt
   binding.
6. Accurate terminal acknowledgement — the canonical `task.cancelled` event is
   published only after the terminal transition is durably acknowledged.
7. Worker restart with a persisted intent.
8. No false terminal event, and no `status = "canceled"` at request time.
9. No unauthorized local operator compatibility.
10. Documentation validation and the Document Lifecycle Graph source-hash check.

**No live runtime qualification is inferred from this document.** The evaluated
mainline's parse break means the current coding-agent route surface is not executable
at all, and that is itself a qualification blocker for any cancellation claim.

## Evidence labels used in this document

- **Proven by source inspection** — established by reading the evaluated revision.
- **Proven by test** — executed and observed.
- **Inferred** — follows from proven facts but was not executed.
- **Unresolved** — requires a decision or an environment this task did not have.

The ADR-number uniqueness audit, the evaluated mainline revision, the run and task
identity trace, the three persistence alternatives, the recommended durable intent
authority, the account authorization boundaries, the proposed mutation outcomes, the
worker observation model, the execution-claim consistency argument, the terminal event
truth analysis, the concurrency and recovery limitations, the DLG source-hash
verification, and the documentation validation are recorded in the accompanying change
and are reproducible from the evaluated revision.
