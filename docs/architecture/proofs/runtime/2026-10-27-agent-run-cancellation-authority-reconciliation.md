# Agent Run Cancellation — Authority and Lifecycle Reconciliation

## Result

`CANCELLATION_AUTHORITY_UNRECONCILED`

Authenticated Agent Run cancellation is not currently reachable, and correcting the
identity comparison alone would not make it truthful. Five independent defects were
reproduced or source-proven at the evaluated revision. The route is uniformly
unauthorized today; with the identity defect hypothetically removed it reports a
terminal cancellation that no worker observed, never signals the queue, and — for a
run that already succeeded — reports `canceled` while the durable status remains
`succeeded`.

This document authorizes no implementation. It establishes the authority model, the
identity relationship that is currently missing, the acknowledgement boundaries, and
the single first implementation slice that can be taken safely. Two of the four
prerequisites for that slice are architecture decisions, not code changes.

## Evaluated revision and method

| Field | Value |
| --- | --- |
| Proof branch | `proof/agent-run-cancellation-authority` |
| Evaluated HEAD | `9bb23732bff11e2d49a325cabde11f4019374f0d` (`origin/main` at evaluation) |
| Related PR | [#914](https://github.com/Resonant-Jones/Codexify/pull/914), head `0149dc3b50d79aad9ff0864a91487b39a720b32c`, **open, not merged** |
| Repository state | Clean tree; no application file modified by this investigation |
| Environment | macOS arm64, project virtualenv, Python 3.12, pytest 8.4.2 |
| Durable resources used | **None.** No database, no Redis, no worker, no live credential |

The cancellation implementation is identical between the PR #914 base (`6e0fb06d2`) and
`origin/main` (`9bb23732b`): `git diff 6e0fb06d2 origin/main -- guardian/routes/agent_orchestration.py
guardian/agents/store.py guardian/queue/redis_queue.py guardian/workers/coding_worker.py
guardian/workers/agent_worker.py` is empty. PR #914's readback repair changes four
readback handlers and adds one helper; it does not touch `cancel_run`. The readback
defect and the cancellation defect are separate and independently fixable.

### Evidence labels

- **Proven by test** — executed in this investigation and observed.
- **Proven by source inspection** — established by reading the evaluated revision.
- **Inferred** — follows from proven facts but was not executed.
- **Unresolved** — requires a decision or an environment this investigation did not have.

### Reproduction method

A bounded `TestClient` probe was run outside the repository tree against the mounted
route module, using a synthetic account identity, an isolated in-memory `AgentStore`
subclass that records reads and status transitions, and a recording `AgentEventPublisher`
subclass. `guardian.queue.redis_queue.cancel` was replaced in the probe process only, to
record whether the route ever signals the queue. No production code was modified.

## Governing architecture

| Decision | Status | Bearing on cancellation |
| --- | --- | --- |
| [ADR-020](../../adr/020-guardian-mediated-coding-agent-execution-contract.md) — Guardian-mediated coding-agent execution | **Accepted** | Guardian owns intake, request identity, thread identity, policy, result ingestion, and the terminal decision about a coding result. A cancellation request that terminates an execution is a Guardian-side decision about a Guardian-owned execution. |
| [ADR-039](../../adr/039-operator-user-access-boundary.md) — Operator / User access boundary | **Proposed** | Establishes the operator-vs-user role separation in principle, but is **not an accepted decision**. It cannot be cited as governing authority for an operator cancellation right. |
| [ADR-069](../../adr/069-codexify-beta-runtime-support-boundary.md) — Beta runtime support boundary | Accepted | Route availability is not Beta support. Cancellation being reachable does not widen the supported promise. |
| [ADR-081](../../adr/081-project-ownership-authority.md) — Project ownership authority | Accepted | `projects.user_id` is the sole canonical Project ownership authority; description data never grants, denies, transfers, or overrides account authority. Thread ownership remains independently authoritative. |
| [ADR-092](../../adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md) — Credential purpose and mixed-principal boundary | Accepted (partial runtime implementation) | Account sessions, operator sessions, and Hosted Room guest sessions are separate credential classes. An operator credential never becomes an account credential. Mixed-principal credentials fail closed. |
| [ADR-094](../../adr/094-account-scoped-execution-credential-authority.md) — Account-scoped execution credential authority | Accepted | Guardian verifies the invoking account before dispatch and records a secret-free, owner-scoped binding. The durable binding is the execution's authority record, not deployment metadata. |
| [2026-10-02 Agent/Coding Snapshot Readback proof](../2026-10-02-agent-coding-snapshot-readback-proof.md) | Evidence for its evaluated revision | Requires exact account-origin provenance plus surviving canonical thread ownership for account reads, and existence-hiding `404` for absent or foreign resources. Its red operator-metadata exploit establishes that deployment metadata must never confer account read entitlement. |
| [00 Current State](../../00-current-state.md) | Authoritative for release | Release gate remains `HOLD`. Nothing in this document changes that. |

**Accepted authority vs. current implementation.** ADR-020, ADR-081, ADR-092, and ADR-094
are accepted decisions. The current cancellation route does not implement them: it
rejects every principal, authorizes through the reader that ADR-081 and the 2026-10-02
proof explicitly reject for account scope, and reports a terminal outcome the worker
never observed.

## 1. Reproduced HTTP failure

**Proven by test.** Case 1 — current implementation, authenticated owning account,
in-memory store, run in `running` state:

```
status_code: 403
body: {"detail":"account_identity_mismatch"}
store calls: []
durable status after: running
events emitted: []
queue cancel calls: []
```

All five properties the task asked to confirm hold:

- A legitimate authenticated account receives **403**. *Proven by test.*
- The rejection happens **before resource lookup** — the recording store recorded zero
  calls. *Proven by test.*
- The run remains unchanged (`running`). *Proven by test.*
- The implementation never reaches queue cancellation. *Proven by test* and
  *proven by source inspection*: `guardian/routes/agent_orchestration.py` imports only
  `guardian.queue.task_events` (line 49) and `enqueue_coding_execution` (line 558);
  `redis_queue.cancel` is never imported by the route module at the evaluated revision.
- No `canceled` event is emitted. *Proven by test.*

## 2. The exact identity-resolution contradiction

**Proven by source inspection.** `guardian/routes/agent_orchestration.py:88-94`:

```python
def _resolved_request_user(current_user: Any, requested_user: str) -> str:
    resolved = str(current_user or "").strip()
    if not resolved or resolved.startswith("Depends("):
        raise HTTPException(status_code=401, detail="account_identity_missing")
    if str(requested_user or "").strip() != resolved:
        raise HTTPException(status_code=403, detail="account_identity_mismatch")
    return resolved
```

The function implements one contract — *a caller-requested identity must match the
authenticated account* — and `cancel_run` at line 753 calls it with an empty requested
identity:

```python
request_user = _resolved_request_user(current_user, "") or None
```

An empty string never equals a resolved account, so the comparison fails for every
principal. The trailing `or None` is unreachable: the function either returns a
non-empty string or raises.

This is the same shape of defect the readback repair on PR #914 addressed for four
readback handlers, and it has the same origin. At the reader commit the 2026-10-02
proof qualifies (`a352c088a`), the resolver had fallback semantics and returned the
**authenticated** identity for an empty request. Commit `f83fe5da3` ("Bind coding
execution identity per invocation") repurposed the function for strict execution
matching and migrated the execution call site. The readback and cancellation call
sites were left behind.

Cancellation is not, however, merely a second readback. It is a **mutation**, so it
needs a resource-authority decision, not only an identity-resolution decision.

## 3. Principal and resource authorization matrix

### 3.1 Principal authority (evaluated revision)

| Principal | Reached at | Current outcome | Evidence |
| --- | --- | --- | --- |
| Authenticated owning account | `get_current_user` | 403 `account_identity_mismatch` | Proven by test |
| Different authenticated account | `get_current_user` | 403 `account_identity_mismatch` | Proven by test (same code path) |
| Local self-operator (local mode API key) | `get_current_user` | 403 `account_identity_mismatch` | Proven by test |
| Remote operator credential | `verify_account_session` | 401 — an operator-purpose token is not an account session | Proven by source inspection (`guardian/core/dependencies.py:1012-1066`) |
| Hosted Room guest | `verify_account_session` | 401 — a verified guest token is not an account session | Proven by source inspection (same function) |
| Missing authentication | `verify_account_session` | 401 | Proven by source inspection |
| Mixed credentials | `reject_mixed_principal_credentials` | 400 canonical mixed-principal rejection at the remote boundary | Proven by source inspection; ADR-092 governs |
| Forged `X-User-Id` | `get_request_user_id` | Never becomes an account principal in the remote lane. In the local lane it is honored only under `DEBUG`/`LOCAL_DEV`, where it *becomes* the principal rather than overriding an account | Proven by source inspection; see §9 for the environment finding |

### 3.2 Resource authority

| Resource | Durable evidence required | Current reader behaviour | Evidence |
| --- | --- | --- | --- |
| R1 Durable account-origin coding run | `AgentRun.account_origin_user_id` equals the account **and** the surviving canonical `ChatThread.user_id` equals the account **and** run/deployment/thread lineage is consistent | `get_account_run` implements this | Proven by source inspection (`guardian/agents/store.py:850-911`) |
| R2 Foreign account run | Absence of the above | `get_account_run` returns `None` → 404 | Proven by source inspection |
| R3 Operator-created run | No account-origin provenance; deployment metadata is actor-controlled and confers nothing | `get_account_run` returns `None` → 404 | Proven by source inspection; the 2026-10-02 red exploit proves metadata confers no entitlement |
| R4 Threadless local operator run | No account origin; the local operator lane | `get_run` returns it when the deployment spec carries no conflicting `user_id` | Proven by source inspection (`store.py:838-848`) |
| R5 Memory-only run | No durable authority at all | `get_run` memory path returns it; `get_account_run` returns `None` | Proven by source inspection; the existing guardian test `test_chat_thread_agent_runs_rejects_memory_only_authority` asserts the account lane returns 404 |
| R6 Historical NULL-origin run | `account_origin_user_id IS NULL` | `get_account_run` returns `None` → 404 | Proven by source inspection |
| R7 Deleted or reassigned canonical thread | `ChatThread.user_id` no longer equals the account | `get_account_run` join fails → 404 | Proven by source inspection; 2026-10-02 proof exercised real FK deletion |
| R8 Unknown run | No row | All readers return `None` → 404 | Proven by source inspection |

### 3.3 Combination matrix

Current observed outcome is uniform for every authenticated principal: **403**, because
the identity comparison precedes resource lookup. Unauthenticated and mixed-principal
requests fail earlier at the authentication dependency.

Legend — `403` identity rejected before lookup · `401` authentication required or
invalid · `400` mixed-principal credentials rejected · `404` existence-hidden ·
`A` cancellation request accepted, subject to the execution-state rules in §6 ·
`ADR` authority undecided, requires an architecture decision.

| Principal \ Resource | R1 account-origin | R2 foreign | R3 operator-created | R4 threadless local operator | R5 memory-only | R6 NULL-origin | R7 reassigned thread | R8 unknown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Authenticated owning account | 403 → **A** | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 |
| Different authenticated account | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 | 403 → 404 |
| Local self-operator | 403 → **A** only where the local identity matches the durable owner | 403 → 404 | 403 → **A** | 403 → **A** (bounded local compatibility) | 403 → **ADR** | 403 → **ADR** | 403 → 404 | 403 → 404 |
| Remote operator credential | 401 | 401 | 401 | 401 | 401 | 401 | 401 | 401 |
| Hosted Room guest | 401 | 401 | 401 | 401 | 401 | 401 | 401 | 401 |
| Missing authentication | 401 | 401 | 401 | 401 | 401 | 401 | 401 | 401 |
| Mixed credentials | 400 | 400 | 400 | 400 | 400 | 400 | 400 | 400 |
| Forged `X-User-Id` | 403 (header is never an account authority) | 403 | 403 | 403 | 403 | 403 | 403 | 403 |

Two cells are deliberately left **ADR** rather than guessed. The local operator lane has
no durable account authority — a memory-only or NULL-origin run is visible to
`get_run` in local mode — so "may a local operator cancel a run that has no durable
account provenance?" is an authority question that ADR-039, still *Proposed*, does not
answer. It must not be settled by a test expectation.

Cancellation authority is never inferred from deployment metadata, in any cell.

## 4. Run-to-queue identity trace

**Proven by source inspection.**

| Identifier | Generated where | Persisted where | Transported where | Disposition |
| --- | --- | --- | --- | --- |
| `AgentRun.run_id` | `AgentStore.create_run` (`_new_external_id("run")`) | `agent_runs.run_id` | Execute route → queue payload `run_id` | Durable, unique, account-scoped |
| `AgentRun.deployment_id` | `AgentStore.create_deployment` | `agent_deployments.deployment_id` | Queue payload `deployment_id` | Durable |
| `AgentRun.account_origin_user_id` | Execute route, from the resolved account | `agent_runs.account_origin_user_id` | Not in the queue payload | Durable provenance; `NULL` for operator-created runs |
| `CodingExecutionTask.task_id` | `redis_queue.enqueue_coding_execution` — `str(uuid.uuid4())` | **Nowhere durable** | Redis queue record `task_id`; `BaseTask.task_id` on the worker | **Ephemeral** |
| `CodingExecutionTask.coding_task_id` | Caller (the envelope) | Deployment `spec_json.coding_task_id` | Queue payload `coding_task_id` | Durable, but caller-supplied and not unique |
| `CodingExecutionTask.attempt_id` | Caller (the envelope) | Deployment `spec_json` / binding | Queue payload `attempt_id` | Durable, caller-supplied |
| `execution_binding.binding_id` | `_build_execution_binding` | Deployment `spec_json.execution_binding` | Queue payload `execution_binding_id` | Durable, secret-free |
| Enqueue return value | `enqueue_coding_execution` returns the generated `task_id` | — | **Discarded** at `guardian/routes/agent_orchestration.py:599` (`enqueue_coding_execution(task_payload)`) | **Lost** |

**Verdict: no durable authoritative run-to-queue-task mapping exists.** The only link
between a durable run and its queued execution is the `run_id` field inside a Redis
queue record. Redis is not the durable authority for this relationship, and
`agent_runs` has no column for the queue task id — the model at
`guardian/db/models.py:5531-5584` has no `task_id`/`queue_task_id` field.

A second, latent identity alias exists in the same area.
`CodingExecutionTask.from_dict` (`guardian/tasks/types.py:680-695`) resolves
`coding_task_id` from `payload.get("coding_task_id") or payload.get("codingTaskId") or
payload.get("task_id") or base["task_id"]` — so a queue record without an explicit
`coding_task_id` would read the **queue task id** as the coding task id. The execute
route always sets `coding_task_id` explicitly, so the evaluated path is unambiguous;
the alias remains a latent trap for any other producer of coding-execution records.

`enqueue_coding_execution` also places `**payload` after `"task_id": task_id` in the
record literal, so a payload containing `task_id` would override the generated value in
the record while the function still returned the generated one. The evaluated execute
payload carries no `task_id` key, so the two agree today.

The following identities are explicitly **not** available as a cancellation correlation
and must not be overloaded: Project identity, Thread identity, credential reference,
worktree lease identity, provider identity. Possession of a queue id must never be
inferred to be ownership of a run.

## 5. Queue cancellation trace

**Proven by source inspection** (`guardian/queue/redis_queue.py:727-745`):

```python
def cancel(task_id: str) -> None:      # SADD codexify:queue:cancelled <task_id>
def is_cancelled(task_id: str) -> bool:  # SISMEMBER
def clear_cancelled(task_id: str) -> None:  # SREM
```

- The cancellation signal is a membership flag in the Redis set
  `codexify:queue:cancelled` (`redis_queue.py:39`), keyed by **queue task id**.
- It carries no timestamp, no requester identity, no reason, and no expiry. The set is
  unbounded and has no TTL; entries are removed only by an explicit `clear_cancelled`.
- It is therefore a **request flag**, not a durable record, and it is not scoped to an
  account.
- The route never calls it (§1). The only producers of `cancel` are the chat-worker
  paths; `cancel_run` has no queue path at all.

## 6. Worker observation checkpoints

**Proven by source inspection** (`guardian/workers/coding_worker.py`):

| Line | Checkpoint | Scope |
| --- | --- | --- |
| 2046-2048 | `if is_cancelled(task.task_id): self._emit_cancelled(task); return` | Start of `_process_task`, **before** deployment lookup, binding validation, credential lease, and adapter invocation — the pre-execution boundary |
| 2679-2681 | `if is_cancelled(task.task_id): self._emit_cancelled(task); return` | First statement of each validation-attempt iteration, **before** the adapter call of that attempt |
| 2825-2830 | `result = execute_authorized(request, identity, credential_material=..., read_only=...)` | The adapter execution itself — **synchronous and blocking** |

`execute_authorized` (`guardian/agents/adapters/pi_codex_runner.py:74-84`) takes no
cancellation callback; `AgentExecutionRequest`
(`guardian/agents/adapters/base.py:123`, fields `prompt`, `cwd`, `timeout_seconds`,
`metadata`) carries no cancel-check surface.

**Consequences.**

- Cancellation is observable only **before** adapter execution and at **validation-attempt
  boundaries**. It is not observable while an adapter is executing.
- No claim of in-flight process interruption is made or supportable at the evaluated
  revision. The only duration bound on the adapter is `timeout_seconds`, which is the
  execution timeout budget, not a cancellation mechanism.
- `guardian/workers/agent_worker.py` contains **no** cancellation handling at all — no
  `is_cancelled` reference and no cancel import. Only the coding worker participates in
  the queue-cancellation protocol.

**The worker already owns terminalization correctly.**
`coding_worker.py:4146-4173`:

```python
def _emit_cancelled(self, task: CodingExecutionTask) -> None:
    """Emit task.cancelled event."""
    self.store.update_run_status(run_id=task.run_id, status="canceled")
    task_events.publish_with_visibility(
        task.run_id, "task.cancelled",
        {**build_coding_result_lineage_payload(
            run_id=task.run_id, queue_task_id=task.task_id,
            coding_task_id=task.coding_task_id, attempt_id=task.attempt_id, ...),
         "status": "cancelled", "reason": "cancelled_before_execution"},
    )
```

The worker sets the terminal status **only when it has actually observed the
cancellation**, and it publishes the canonical `task.cancelled` token
(`guardian/protocol_tokens.py:125`) with full lineage including the queue task id. The
route's own cancellation handling duplicates and pre-empts this, and does so with
strictly weaker semantics. This is the single most important structural finding in
this document: **terminal cancellation is already correctly owned by the worker; the
route should not write the terminal status at all.**

## 7. Durable mutation analysis

**Proven by source inspection** (`guardian/agents/store.py:1043-1090`):

```python
def update_run_status(self, *, run_id, status, error=None,
                       rollback_applied=None, rollback_reason=None) -> bool:
    ...
    row = session.query(AgentRun).filter_by(run_id=run_id).first()
    if row is None:
        return False
    current_status = _normalize_agent_run_status(row.status)
    if _is_terminal_agent_run_status(current_status):
        if not _is_terminal_agent_run_status(normalized_status):
            return True                     # refused, but reported as success
        if normalized_status != current_status:
            return True                     # refused, but reported as success
    row.status = normalized_status
    ...
    session.commit()
    return True
```

Findings:

1. **The return value does not distinguish a transition from a refusal.** A run that
   already reached a terminal state returns `True` for a refused replacement. The
   route ignores the return value entirely, so it cannot tell the difference.
2. **No ownership check in the mutation.** `update_run_status` has no `user_id`
   parameter. Authorization is performed by a separate prior read, so ownership and
   status are **not** checked in the same transaction — a time-of-check/time-of-use
   window between the authorizing read and the write.
3. **Terminal states resist unauthorized replacement in the row but not in the API
   answer.** The row is protected; the response is not. See §8.
4. **A cancellation event can be emitted without a committed transition.** The route
   calls `_event_publisher.emit(...)` unconditionally after `update_run_status`,
   including when the mutation was refused.
5. **Database errors do not fail closed inside the route.** `update_run_status` does
   not catch database exceptions, but the route has no error handling either, so a
   database failure surfaces as an unhandled server error rather than a controlled
   "cancellation not recorded" outcome.
6. **Redis failures can create contradictory durable status.** The route commits the
   durable status change and then publishes the event; the publisher swallows publish
   failures with a warning (`guardian/agents/events.py:73-76`). A durable
   `status='canceled'` can therefore exist with no corresponding `canceled` event
   having reached the stream.
7. **The status vocabulary is closed at the database level.** The
   `agent_runs_status_check` constraint (`guardian/db/models.py:5570-5573`) permits
   only `('queued', 'running', 'escalated', 'canceled', 'failed', 'succeeded')`. There
   is no "cancellation requested" or "cancelling" state, and `escalated` is terminal
   per `_is_terminal_agent_run_status` (`store.py:116-122`) while `_normalize_agent_run_status`
   maps an unknown or empty value to `failed` (`store.py:107-113`).

**Narrowest authoritative mutation seam.** A cancellation mutation must check
ownership and the current status **in the same transaction** and must return a
distinguishable outcome — `transitioned` / `already_terminal` / `not_found` / `not_authorized`
— instead of a bare boolean. A parallel run-state store must not be introduced; the
existing `agent_runs` row and its existing status vocabulary are the only durable
state.

## 8. Terminal event truth matrix

**Proven by source inspection and by test.** Five distinct "cancel" surfaces exist at
the evaluated revision.

| Surface | Producer | Token | Durable status written | Means |
| --- | --- | --- | --- | --- |
| Route `cancel_run` | `guardian/routes/agent_orchestration.py:757-762` | `canceled` (not a `TaskEventType`) | Yes — `status="canceled"` | A request was received. Does **not** mean the worker observed it, and does not mean execution stopped. |
| Route `cancel_run` event | `guardian/agents/events.py:54-76` | `canceled`, payload `{"run_id": ...}` only | — | A request was received. Published to the same Redis stream key the worker uses, but under a **non-canonical** event type, so a consumer filtering on `task.cancelled` will not observe it. |
| Worker `_emit_cancelled` | `guardian/workers/coding_worker.py:4146-4173` | `task.cancelled` (canonical) with full lineage | Yes — `status="canceled"` | The worker **observed** the cancellation flag and abandoned the attempt before execution. |
| Worker `_emit_terminal` | `coding_worker.py` terminal paths | `task.completed` / `task.failed` | Yes | The attempt reached a terminal result. |
| `AgentRun.status` | `agent_runs.status` | `canceled` / `succeeded` / `failed` / `escalated` | — | Durable state of the run. |

**A `canceled` event must never be treated as proof of stopped execution merely
because the HTTP route returned success.** The route's event and status are written
before — and independently of — any worker observation. Only the worker's
`task.cancelled` carries the `reason: "cancelled_before_execution"` lineage that
distinguishes observation from request.

Note also a vocabulary inconsistency: the worker's event payload reports
`status: "cancelled"` (two l's) while the durable status normalizes to `canceled`
(one l, `store.py:111-112`) and the route's event type is the bare string `canceled`.
Three spellings of the same concept exist across the durable status, the route event,
and the worker event payload.

### False-success scenario (proven by test)

**Case 3** — identity defect hypothetically removed, run already `succeeded`:

```
status_code: 200
body: {"ok":true,"run_id":"run_ae70367e05084f50","status":"canceled"}
store calls: [('get_run', {...'user_id': 'account-owner'}),
              ('update_run_status', {...'requested': 'canceled', 'returned': True,
                                     'status_before': 'succeeded', 'status_after': 'succeeded'})]
durable status after: succeeded
events emitted: [('run_ae70367e05084f50', 'canceled', {'run_id': 'run_ae70367e05084f50'})]
```

The route answered `200 {"status": "canceled"}` and published a `canceled` event for a
run that had already **succeeded**. The durable status was not changed — the store
refused the transition and returned `True` — and the route could not tell. An operator
or account would be told their completed coding run was cancelled, while durable
readback and the transcript still show success.

**Case 4** — duplicate cancel request, same run:

```
first:  200 {"ok":true,...,"status":"canceled"}
second: 200 {"ok":true,...,"status":"canceled"}
events emitted: [('run_...', 'canceled', {...}), ('run_...', 'canceled', {...})]
```

The duplicate is not idempotent at the event level: a second `canceled` event is
published for the same run. The second mutation is a no-op (status stays `canceled`),
and the store again reported `True`.

## 9. Cancellation semantics by execution state

**Proven by source inspection**, with the worker checkpoints from §6.

| Execution state | Observable today | Can execution actually stop? | Can a request be recorded? | Can a terminal `canceled` be truthfully emitted? | Duplicate request |
| --- | --- | --- | --- | --- | --- |
| Queued, before worker admission | Yes — checkpoint at 2046 | Yes, the worker will not start it | Yes, if the route could signal the queue task (it cannot today) | Yes — the worker emits `task.cancelled` with `reason: cancelled_before_execution` | Should be idempotent; today it emits a second route-level `canceled` event |
| Worker admitted, adapter not yet invoked | Yes — checkpoint at 2679 for the first attempt | Yes, the attempt is abandoned | Same as above | Yes, by the worker | Same |
| Adapter actively executing | **No** — no checkpoint inside `execute_authorized` | **Not demonstrated.** No cancel-check surface exists on the request | Only as a request flag nobody reads | **No** — no worker observation exists | Same |
| Retry / validation attempt boundary | Yes — checkpoint at 2679 for subsequent attempts | Yes, the next attempt is abandoned | Same | Yes, by the worker | Same |
| Already succeeded | No — the run is terminal | Not applicable | Yes today, and **reported as canceled** (false success, §8) | **No** — the durable status is `succeeded` | Same |
| Already failed | No | Not applicable | Yes today, reported as canceled (same false success) | **No** | Same |
| Already canceled | No | Not applicable | Yes today, and a second `canceled` event is published | No new truth | Not idempotent today |
| Unknown or unauthorized run | Route answers 404 only *after* the identity defect is fixed; today 403 | Not applicable | No | No | Not applicable |

**Do not assume that setting `AgentRun.status` to `canceled` terminates a worker.**
It does not: the worker's checkpoints read the Redis set, not the database status. The
durable status is downstream of worker observation, never upstream of it.

**A conflict response is necessary.** Cancelling a run that already reached a terminal
state is not a no-op success and not a failure of authorization — it is a conflict with
the run's actual outcome. The current status vocabulary offers no way to express it
(`agent_runs_status_check` permits no such state), so the vocabulary decision is part of
the required architecture decision.

## 10. Failure and recovery matrix

| Scenario | Observed / expected behaviour | Evidence |
| --- | --- | --- |
| Duplicate cancel request | Both requests answer 200; two `canceled` events are published; the second mutation is a no-op reported as `True` | **Proven by test** (Case 4) |
| Worker already completed | Route answers 200 `canceled`; durable status remains `succeeded`; a `canceled` event is published | **Proven by test** (Case 3) and source inspection |
| Worker started between authorization and signalling | The route's authorization read and its status write are separate transactions; the worker may begin execution in between. The status write would then be refused by the terminal-status guard, but the route reports success | **Proven by source inspection**; the interleaving itself is **inferred** — no concurrent execution was observed |
| Redis unavailable | `redis_queue.cancel` would raise inside `_with_reconnect` after its internal retry; the route never calls it, so today the flag is simply never set. Any future signalling must define the failure mode: an unavailable queue must not be reported as a recorded cancellation | **Proven by source inspection** for the mechanics; the *concurrent* failure mode is **inferred** |
| Redis restart after a cancellation request | The cancel set is a Redis set with no TTL and no durable owner record. Whether a member survives depends entirely on Redis persistence configuration, which is not a Guardian-owned durability boundary | **Unresolved** — no Redis persistence configuration was evaluated in this investigation |
| Database unavailable | `update_run_status` propagates the database exception; the route has no handling, so the request fails with an unhandled server error rather than a controlled "not recorded" answer | **Proven by source inspection**; no live failure was induced |
| Worker crash before observing cancellation | The run stays in a non-terminal durable status forever; the queue flag is never consumed and never cleared, so a redelivered attempt observes it — but only if the flag survived | **Inferred** from the checkpoint and set semantics |
| Concurrent run ownership changes | Ownership is checked in a prior read, not in the mutation transaction, so a concurrent change is not observed by the write | **Proven by source inspection** (TOCTOU) |
| Stale or repeated queue delivery | The worker checks the flag at admission, so a redelivered attempt for a cancelled task is abandoned — provided the flag survived | **Inferred** |
| Unknown queue task id | `is_cancelled` on an unknown id is `False`; a cancellation signal for an id no worker holds is silently inert | **Proven by source inspection** |
| Memory-only run in the account lane | `get_account_run` returns `None` → 404 | **Proven by source inspection**; asserted by the existing guardian test |
| Operator metadata spoof | Deployment metadata confers no account entitlement | **Proven by source inspection**; the 2026-10-02 proof's red exploit established this |

**No mock was substituted for real crash or restart proof.** The crash, restart, and
concurrency rows above are marked *inferred* or *unresolved* precisely because this
investigation did not induce them.

### Environment finding relevant to this surface

`tests/routes/test_account_restore.py:19` performs a **module-level**
`os.environ.setdefault("LOCAL_DEV", "1")`. Because pytest imports every collected test
module during collection, the local-debug `X-User-Id` override is enabled for the whole
session of a full-suite run. In that lane `X-User-Id` becomes the request *principal*
rather than overriding an account — so a cancellation test that assumes the header is
ignored would be environment-dependent. This file is outside the authorized scope of
this investigation and was not modified; it is recorded here because it directly
affects how any cancellation authorization test must be written.

## 11. Explicit uncertainties

1. Whether the queue cancellation set survives a Redis restart — **unresolved**; Redis
   persistence configuration was not evaluated.
2. Whether a worker actively executing an adapter can be interrupted — **unresolved**;
   no interruption surface exists at the evaluated revision, so there is nothing to
   prove.
3. The correct local-operator cancellation authority for runs without durable account
   provenance — **unresolved**; ADR-039 is *Proposed*, so no accepted decision governs
   it.
4. Whether cancellation should be permitted at all for a run whose durable status is
   already terminal, and what the honest response vocabulary is — **unresolved**; the
   `agent_runs_status_check` constraint admits no "cancellation requested" state.
5. The concurrency interleavings in §10 are **inferred** from source structure; no
   concurrent execution was observed.
6. Current-tip PostgreSQL snapshot qualification — **not established**; see §14.

## 12. Recommended first implementation slice

Exactly one slice is recommended. It is deliberately narrower than "make cancellation
work", because two of its prerequisites are architecture decisions.

> **Slice 1 — Authorized, truthful cancellation *request* for account-owned runs, with
> no execution-termination claim.**

**Why this slice.** The worker already owns terminalization correctly (§6). The route's
terminal write is the defect, not the worker's. The safe first move is therefore to
remove the route's ability to assert a terminal outcome it cannot observe, to put the
authorization on the durable account reader, and to report only what has actually
happened. Execution signalling is a second slice because it depends on a missing
durable correlation (§4).

**Slice 1 scope.**

1. Resolve the authenticated account identity for the route — the account-resolution
   shape already proposed on PR #914 — and reject an unavailable identity before any
   resource lookup. The strict body-to-account comparison used by coding execution is
   **not** applicable here, because a cancellation body carries no requested identity.
2. Authorize against the **lane-correct durable reader**: `get_account_run` for the
   remote and Private Preview lanes, and the bounded local operator reader only in the
   local operator lane, mirroring the read route's lane split. The route must not use
   the local-compatible reader unconditionally, which is the current defect.
3. **Do not write `AgentRun.status = "canceled"` and do not emit a terminal
   `canceled` event from the route.** The worker sets the terminal status and emits the
   canonical `task.cancelled` when it observes the cancellation. This removes the false
   success in §8 by construction.
4. Record the cancellation *request* durably and answer with a request-level outcome
   that cannot be mistaken for termination.
5. Introduce a cancellation mutation seam in `AgentStore` that checks ownership and
   the current status in one transaction and returns a distinguishable outcome
   (`transitioned` / `already_terminal` / `not_found` / `not_authorized`) instead of a
   bare boolean.

**Explicitly out of slice 1:** signalling the queue, and any claim that execution
stopped. Slice 1 makes cancellation *honest*; it does not yet make it *effective*.

**Files the implementation would need.**

| File | Change |
| --- | --- |
| `guardian/routes/agent_orchestration.py` | `cancel_run` identity resolution, lane-correct authorization, truthful response, no terminal write, no terminal event |
| `guardian/agents/store.py` | A cancellation-intent mutation seam that performs ownership + status checks in one transaction and distinguishes outcomes. No change to `AgentStore`'s owner-filtering behaviour elsewhere |
| `guardian/db/models.py` + a new Alembic migration | **Required** if the cancellation request is recorded as durable state: `agent_runs_status_check` admits no "cancellation requested" value, and `agent_runs` has no request column. A new column **or** a separate durable request record must be chosen by the architecture decision |
| `guardian/agents/events.py` | Possibly a request-level event emission, if the request is to be visible on the run stream. The canonical token to use is itself an architecture decision (§13) |

**Focused tests the implementation would need.**

- `tests/core/test_supported_profile_quarantine.py` — a cancellation route test
  asserting: an authenticated owning account is authorized; a foreign account receives
  404; a missing identity fails closed before lookup; a forged `X-User-Id` cannot select
  another account; an already-terminal run does **not** produce a terminal cancellation
  answer; a duplicate request does not produce a second terminal event.
- `guardian/tests/routes/test_agent_orchestration_events.py` — the explicit route
  suite, which currently asserts that the memory-only thread read remains 404 and that
  the local threadless operator run remains readable; cancellation coverage belongs
  alongside it, invoked explicitly because `pytest.ini` excludes `guardian/tests`.
- `tests/identity/test_account_purpose_strict_migration.py` — the adjacent
  account-purpose boundary, to confirm the operator and guest lanes stay separated.

**Durable proof the implementation requires before it may be called complete.**

1. A PostgreSQL-backed proof with a real account session showing: the owning account
   can request cancellation; a foreign account receives existence-hiding 404; a
   NULL-origin and an operator-created run receive 404 in the account lane; a
   deleted or reassigned canonical thread receives 404.
2. A durable proof that the cancellation request is committed in the same transaction
   as its ownership check, with the outcome distinguishable from a refused transition.
3. A Redis-backed proof that a cancellation request recorded for a queued task causes
   the worker to abandon the attempt and emit the canonical `task.cancelled` with
   lineage — which requires slice 2 and the durable run-to-queue correlation.
4. A proof that a duplicate request is idempotent and does not emit a second terminal
   event.

## 13. ADR impact

**Classification: Architecture-Impact investigation. This task does not authorize a
changed runtime contract.**

Slice 1 aligns with the accepted decisions — ADR-020 (Guardian owns the execution
lifecycle and result ingestion), ADR-081 (durable ownership, never deployment
metadata), ADR-092 (credential purpose separation, mixed principals fail closed), and
ADR-094 (account-scoped authority). It does not require a new execution authority.

**Two prerequisites are not covered by any accepted decision and need an explicit
architecture decision before implementation:**

1. **Cancellation intent representation.** Recording a cancellation *request* durably
   requires either a new `agent_runs` state — the
   `agent_runs_status_check` constraint permits only
   `('queued', 'running', 'escalated', 'canceled', 'failed', 'succeeded')` — or a
   separate durable request record. Neither the vocabulary of "cancellation
   requested" nor the conflict answer for an already-terminal run exists in an accepted
   decision.
2. **Durable run-to-queue-task correlation.** Without a persisted queue task id, a
   cancellation request cannot reach the correct queued execution. A new persisted
   mapping is a schema decision; deriving it from Project, Thread, credential, lease,
   or provider identity is forbidden; and deployment metadata is actor-controlled and
   must not carry it, because the 2026-10-02 proof established that metadata confers no
   entitlement.

**Required decision vehicle:** an **ADR amendment** to ADR-020 (execution lifecycle
ownership) is the most likely fit if cancellation intent is treated as part of the
Guardian-mediated execution contract, together with the acknowledgement vocabulary
(requested / accepted / observed / terminated). A **new ADR** is the better fit if
cancellation intent is treated as a durable, account-scoped resource with its own
lifecycle. An ADR amendment is also needed to settle the local-operator cancellation
boundary, because ADR-039 remains **Proposed** and cannot carry that decision.

**No new canonical token may be introduced without that decision.** The existing
canonical `task.cancelled` token (`guardian/protocol_tokens.py:125`) is the worker's
terminal-observation token and must keep that meaning. The route's non-canonical
`canceled` event type is a defect to remove, not a vocabulary to extend.

## 14. Release-proof limitations

- This document is an **investigation**. It changes no runtime behaviour, no schema,
  no workflow, and no test.
- **No durable runtime proof.** Every runtime observation in this document comes from
  a bounded in-memory probe with synthetic identities. There is no PostgreSQL, no
  Redis, no worker, and no live credential. Memory-only fixtures do not establish
  durable ownership or durability.
- **No current-tip PostgreSQL snapshot qualification.** A disposable loopback
  PostgreSQL was not available during this investigation — the local Docker daemon was
  unresponsive, and an embedded server could not complete `initdb` because the
  environment denies the file removal that PostgreSQL's bootstrap performs. The
  2026-10-02 readback proof remains evidence for its evaluated revision only.
- **The 2026-10-02 proof is not re-asserted.** Its 121-case result belongs to its
  evaluated revision and must not be presented as current-tip qualification.
- **Release posture is unchanged.** `docs/architecture/00-current-state.md` keeps the
  release gate at `HOLD`. Cancellation reachability is not release qualification
  (ADR-069), and nothing here widens the supported promise.
- **Backend CI remains red** on an unrelated Whoosh'd assertion, and the frozen
  operator manifest drift in `tests/identity/test_operator_route_auth_migration.py`
  remains open. Neither was investigated or repaired.

## 15. Validation record

| Check | Result |
| --- | --- |
| `tests/core/test_supported_profile_quarantine.py` | **3 failed, 10 passed** at the evaluated revision. The three failures are the readback `403` and the two coding-route `422` bodies — the defects PR #914 corrects. None of the three is a cancellation case. |
| `guardian/tests/routes/test_agent_orchestration_events.py` (explicit invocation) | **20 collected, 18 passed, 2 failed** at the evaluated revision. The two failures are `test_chat_thread_agent_runs_rejects_memory_only_authority` and `test_local_operator_can_read_threadless_agent_run` — both the readback identity defect, not cancellation. |
| `tests/identity/test_account_purpose_strict_migration.py` | **23 passed** |
| Bounded cancellation probe (4 cases) | 403 reproduced; false success reproduced; duplicate-event behaviour reproduced; queue-signal absence reproduced |
| `python scripts/validate_docs.py` | Passed |
| `git diff --check` | Clean |
| Application, schema, workflow, and test files modified | **None** |

The three and two failures above are the pre-existing readback and coding-route
defects that PR #914 already carries corrections for; they are recorded here because
this proof evaluates `origin/main`, not the PR branch. At PR #914's head
`0149dc3b5` the same suites report 25 passed for the supported-profile file and
20 passed for the Guardian route suite. Neither set of failures involves
cancellation.
