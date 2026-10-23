# Guardian Coding Worker — Restart Reconciliation of Abandoned Executions

**Evaluated commit:** `325e225f92f97523c1737fa2deabc46eff1f185b`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-23
**Final classification:** **BLOCKED**

The restart-reconciliation contract is **not implemented**, because its
mandatory prerequisite — a **worker-liveness authority** — does not exist in this
runtime.

**What is proven.** The durable-acceptance prerequisite is real and working: a
Guardian coding run that a worker claims is durably `running` with a stamped
`started_at`, and it survives the worker's death as an *accepted* run. The
canonical operator-visible disposition for an unresolved outcome already exists
and needs **no migration**. And a worker restart performs **no** reconciliation
of an abandoned accepted run — proven by a controlled SIGKILL-and-restart
experiment against disposable PostgreSQL and Redis.

**What is missing.** Nothing in the runtime can tell an **abandoned** accepted
run from an **actively owned** one. Every candidate signal is either a
timestamp, Redis emptiness, or a table that no production code path ever
writes. The Guardian coding path has no worker identity, no per-run ownership
record, and no liveness signal. Fencing is explicitly absent.

**The consequence.** A reconciliation built on any of the available signals
would either guess or lie: it would escalate a run whose worker is alive and
mid-execution, or it would never escalate anything. Requirement 2 of the task
spec makes that gate explicit — *"If not, stop with BLOCKED and identify
durable worker-ownership/fencing as the next prerequisite. Do not invent a
process-liveness heuristic or widen the schema within this task."*

This proof identifies that prerequisite precisely. It does not approximate it.

---

## 1. Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Evaluated HEAD | `325e225f92f97523c1737fa2deabc46eff1f185b` |
| `git merge-base --is-ancestor 325e225f HEAD` | true (HEAD is the evaluated commit) |
| Working tree | clean at the evaluated commit; only this proof's files are new |
| Durable acceptance implementation | present (`claim_run_for_acceptance`, `guardian/agents/store.py:1113`) |
| Provider | **none** — no provider request, no live canary, no network egress |

## 2. The recovery contract that was to be reused

`guardian/core/guardian_dispatch.py` holds the accepted recovery vocabulary and
was **not modified**. It is a pure, in-memory value contract:

| Element | Location | Meaning |
|---|---|---|
| `GuardianDispatchState` | `guardian/core/guardian_dispatch.py:61` | `prepared`, `dispatched`, `executing`, `completed`, `failed`, `uncertain`, `quarantined`, `cancelled` |
| `GuardianDispatchRecord` | `:104` | frozen dataclass; the per-attempt dispatch state |
| `observe_liveness()` | `:230` | records an observed liveness signal |
| `classify_dispatch_health()` | `:255` | classifies liveness without assuming loss |
| `recover_dispatch()` | `:303` | decides the recovery disposition |
| `assert_dispatch_ready()` | `:353` | asserts a dispatch is authorized before enqueue |

The contract's own rules are already conservative, and they are the rules a
reconciliation must inherit:

- A terminal attempt is left alone.
- **An attempt with no liveness evidence at all is left alone.** *"absence of
  evidence is not evidence of loss."*
- An attempt whose lease is still within its expiry is healthy.
- An attempt whose lease expired **and** whose heartbeat is stale is
  **uncertain**, not lost.
- `recover_dispatch()` without fencing and without operator authorization
  **quarantines** — it never re-drives an attempt and never declares it lost.
- **Fencing is absent** (module docstring): *"There is no fencing token, epoch,
  or monotonic guard in this runtime, so a superseded attempt's writes cannot be
  rejected."*

Two of these facts matter for what follows. First, the quarantine-and-escalate
posture needs only *liveness evidence*, not fencing — fencing is what re-dispatch
would need, and re-dispatch is forbidden here. Second, the classifier's
"no evidence → leave alone" rule means that **if the runtime supplies no liveness
evidence, the existing contract classifies nothing at all** — which is exactly
the observed behaviour.

**The recovery contract was evaluated and preserved unchanged; it was not
applied.** Requirement 3 makes the reuse conditional on the liveness gate
passing, and §3 shows it does not. `guardian/core/guardian_dispatch.py` is
byte-for-byte unchanged, and no parallel worker-local classifier was written.

## 3. The worker-liveness authority gate

### 3.1 Complete inventory of durable records

| Durable source | Worker identity | Per-run liveness | Populated in production? | Usable for A/B/C? |
|---|---|---|---|---|
| `agent_runs` (`guardian/db/models.py:5531`) | **no column** | `started_at` only | yes | **No** — a timestamp, not a signal |
| `agent_deployments` (`:5484`) | **no column** | none | yes | **No** |
| `agent_run_attempts` (`:5632`) | **no column** | none | **no** — never created for Guardian runs | **No** |
| `coding_worktree_leases` (`:6511`) | ✔ `worker_id` | ✔ `last_heartbeat_at`, `expires_at` | **NO** — see §3.2 | **No** |
| `agent_escalations` (`:5745`) | no column | none | output of recovery, not an input | **No** |
| Redis task-event stream (`guardian/queue/task_events.py:147`) | none | one-shot events, not a heartbeat | yes, but **observational** | **No** |
| `GuardianDispatchRecord` | **no field** | carries `last_heartbeat_at` / `lease_expires_at` as *inputs* | **never persisted** | **No** |
| Chat-worker heartbeat (`guardian/workers/chat_worker.py:177`) | chat worker | ✔ fresh / stale / dead | yes | **No** — a *different* worker, and global, not per-run |
| Voice-worker heartbeat (`guardian/voice/runtime.py:8`) | voice worker | ✔ | yes | **No** — same |
| Fencing token / epoch | — | — | — | **absent by design** |

### 3.2 The lease table has the right shape and is never written

`coding_worktree_leases` is the only durable record in the schema that carries
exactly what the classifier wants: `worker_id`, `last_heartbeat_at`,
`expires_at`, and a status vocabulary that includes `abandoned`. The
`WorktreeLeaseStore` even offers `heartbeat()` (`guardian/agents/worktree_lease_store.py:136`)
and `mark_abandoned()` (`:159`), and the coding worker already calls
`lease_store.heartbeat()` when a lease exists
(`guardian/workers/coding_worker.py:1983`).

It does not help, for two independent reasons:

1. **No production code path creates a lease.** `WorktreeLeaseStore.create_lease`
   (`:62`) is called only from test code. A scan of every non-test module under
   `guardian/` finds no caller. This is corroborated by the live control-plane
   proofs of 2026-05-10, which recorded the row count as **0** before and after
   every dispatch: *"Lease rows: `0` (`coding_worktree_leases` count remained
   zero)"*.
2. **A lease is a worktree claim, so it cannot own a Guardian run.**
   `validate_lease_contract` (`guardian/agents/worktree_leases.py:183`) requires
   non-empty `work_order_id`, `base_ref`, `branch_name`, and `worktree_path`. A
   Guardian delegation has no work order, and on the non-isolated path it has
   neither a branch nor a worktree path. Fabricating those values to obtain a
   lease row would misstate what the lease means and would imply a cleanup
   obligation that does not exist.

### 3.3 The coding worker has no liveness signal

The runtime has an established heartbeat pattern, and the coding worker is the
one worker that does not use it:

| Worker | Heartbeat key | Writer | Freshness classifier |
|---|---|---|---|
| chat | `codexify:worker:chat:heartbeat` (TTL 45 s, 5 s interval) | `guardian/workers/chat_worker.py:685` | `guardian/routes/health.py:369` |
| voice | `codexify:worker:voice:heartbeat` | `guardian/voice/runtime.py:8` | — |
| **coding** | **none** | — | — |

The coding worker's startup is bare:

```python
def _initialize_worker() -> None:      # guardian/workers/coding_worker.py:4438
    db = _resolve_guardian_db()
    configure_db(db)

def run_worker_loop() -> None:         # :4443
    worker = CodingWorker()
    while True:
        worker.poll_once()
```

There is no registration, no identity, no heartbeat, and no startup
reconciliation. `poll_once()` (`:1930`) dequeues and processes; it never
classifies anything it finds in durable state.

Even the chat worker's heartbeat would not be transferable: it is **global per
worker type**, not per run, so it can say "a coding worker is alive" but never
"the worker that owns *this* run is alive". In the chat path the heartbeat is
not the recovery authority either — the chat recovery decision comes from the
durable terminal envelope, and the heartbeat only feeds the health surface
(`guardian/core/chat_completion_service.py:597`).

### 3.4 Gate verdict

| Distinction | Can production establish it? |
|---|---|
| **A** — accepted and actively owned by a live worker | **No** |
| **B** — accepted and demonstrably abandoned | **No** |
| **C** — ambiguous liveness | **Yes — and it is the only outcome available** |

The signals the task spec names as insufficient map one-to-one onto everything
the runtime actually offers:

- *"A running AgentRun alone does not establish liveness"* → `agent_runs.status='running'` is the only thing an abandoned run leaves behind.
- *"An expired worktree lease alone does not prove the worker process is dead"* → no lease exists.
- *"An empty Redis queue does not establish that the accepted execution completed"* → the queue is empty after a crash **and** after a success.
- *"A missing CodingWorktreeLease row does not establish that no execution occurred"* → the row is always missing.
- *"A stale heartbeat cannot automatically authorize task replay"* → there is no heartbeat, and replay is forbidden regardless.

**The gate fails.** No implementation that satisfies the spec's safety
requirements can be written from the available evidence.

## 4. The controlled crash-and-restart proof

Disposable PostgreSQL (`codexify-recovery-pg`, `127.0.0.1:55460`) and disposable
Redis (`codexify-recovery-redis`, `127.0.0.1:56380`). A real Guardian
delegation was dispatched through the real `GuardianDelegationService`; the
credential authority was the real Guardian route, exercised in process; the
provider was a stub that performed the side effect and then **SIGKILLed the
worker** from inside the adapter. No provider request, no network egress, no
credential value printed or stored.

**Child 1 — the worker claims, performs a side effect, and dies uncleanly:**

```
returncode: -9   (-9 == SIGKILL)
stderr: ADAPTER_ENTERED: side effect performed
```

Original run and attempt identities, read back through a fresh session:

| Identity | Value |
|---|---|
| Canonical run id | `run_d8b8a1f62cfa492e` (the dispatched run) |
| Deployment | the run's `agent_deployments` row, unchanged |
| Attempt identity | the deployment spec's `attempt_id` and `coding_task_id`, unchanged by the crash |
| Source lineage | the originating thread and source message, unchanged |
| Queue task id | the dispatched coding-execution task, consumed by the child |
| Worktree lease | **none** — the Guardian path never creates one |

Canonical state after the crash, read back through a fresh session:

```json
{ "status": "running",
  "started_at": "2026-10-23 15:22:39.886798+00:00",
  "ended_at": null, "error": null,
  "escalation_rows": 0, "artifact_rows": 0,
  "step_rows": 0, "attempt_rows": 0,
  "worktree_lease_rows": 0,
  "coding_result_messages": 0 }
```

**Child 2 — a fresh worker starts against that same durable state:**

```
STARTUP_COMPLETE: _initialize_worker() returned
POLL_COMPLETE: processed=False        # the queue is empty; nothing was classified
```

Canonical state after the restart:

```json
{ "status": "running",
  "started_at": "2026-10-23 15:22:39.886798+00:00",
  "ended_at": null, "error": null,
  "escalation_rows": 0, "artifact_rows": 0,
  "step_rows": 0, "attempt_rows": 0,
  "worktree_lease_rows": 0,
  "coding_result_messages": 0 }
```

```
RECONCILIATION_OBSERVED: False
VERDICT: NO durable recovery classification
```

| Observation | Result |
|---|---|
| Accepted run survives the crash as `running` with a stable `started_at` | **yes** — the acceptance prerequisite works |
| Restart produces a durable recovery classification | **no** |
| Restart changes the canonical run status | **no** — still `running` |
| Restart creates an escalation record | **no** — 0 rows |
| Restart re-inserts the task into the queue | **no** — queue depth 0 |
| Restart issues a credential lease | **no** — 0 leases |
| Restart invokes the provider | **no** — 0 invocations after the crash |
| Restart fabricates a source-thread result | **no** — 0 messages |
| Restart creates a result artifact | **no** — 0 rows |

Counts for the whole experiment: **provider adapter invocations = 1** (the
interrupted execution, before the SIGKILL), **repository fixture mutations = 0**
(the synthetic adapter performed no filesystem write — it is a boundary probe,
not a provider), **credential leases issued = 1** (for the interrupted
execution; none after the restart), **source-thread result messages = 0**,
**result artifacts = 0**, **escalations = 0**.

**Active-worker protection.** It cannot be demonstrated, because there is no
classification to protect. A two-worker runtime is in scope for this task, and
the property it would need to prove — *"worker B starting must not escalate a
run actively owned by worker A"* — has no mechanism behind it: with no
per-run ownership record, worker B cannot tell whether a `running` run belongs
to a live peer or to a dead one, and the only sound answer it can give is to
leave every accepted run alone. That is exactly what the experiment observes.
Building the two-worker proof on top of a timestamp or a queue-depth check
would produce a false sense of safety, which is what the gate forbids.

This is the required red: *persisted running execution + worker disappearance +
worker restart → no durable recovery classification*. The green half — the
same scenario producing an evidence-backed, durable recovery disposition — is
blocked on §8 and is specified by the strict-xfail tripwire in §7.

## 5. The disposition already exists and needs no migration

The operator-visible disposition for an unresolved outcome fits the existing
schema exactly, with **no new table, no new status, and no new column**:

| Element | Where | Value |
|---|---|---|
| Canonical run disposition | `agent_runs.status` | `escalated` — already permitted by `agent_runs_status_check` (`guardian/db/models.py:5570`) |
| Recovery record | `agent_escalations` (`:5745`) | `status='open'`, `severity`, `reason_code`, `reason`, `preserved_worktree`, `payload_json` |
| Write path | `AgentStore.add_escalation` (`guardian/agents/store.py:1582`) | the existing canonical writer |
| Read path | `AgentStore.list_escalations` (`:1797`) | the existing canonical reader |

`update_run_status(status="escalated")` also stamps `ended_at`, so the run's
terminal time is durable. The three states the spec requires to remain distinct
map cleanly:

- **Recovery classification** — `uncertain` (the dispatch vocabulary) / `quarantined`.
- **Canonical run disposition** — `escalated`.
- **Actual execution result** — `unknown`, carried in the escalation `payload_json`.

**So the representation is not the missing piece. The liveness authority is.**
`test_the_canonical_escalated_disposition_requires_no_migration` writes exactly
this disposition through the existing store API and reads it back through a
fresh session, asserting that the run becomes `escalated`, that the escalation
is `open`, that the lineage (`run_id`, `deployment_id`, `thread_id`,
`started_at`) is unchanged, and that the evidence payload carries no credential
material.

## 6. The startup integration point

`guardian/workers/coding_worker.py`:

| Line | Call | Role |
|---|---|---|
| 4438 | `_initialize_worker()` | the startup hook — database initialization only |
| 4443 | `run_worker_loop()` | the poll loop |
| 1930 | `poll_once()` | dequeue and process |

The intended integration point is `_initialize_worker()`, between database
initialization and the first `poll_once()`. The spec's required order maps onto
it directly: *initialize database → verify recovery authority → reconcile
qualifying prior accepted executions → establish readiness → begin consuming new
coding tasks*. Everything the gate would need is already in place at that
point: the database is bound, and the recovery contract is importable. What is
missing is the evidence that would let step three distinguish abandoned from
active.

## 7. The contract coverage

`tests/contracts/test_guardian_coding_worker_recovery_contract.py` — **19
passed, 1 xfailed** against disposable PostgreSQL.

**The gate (9 cases).** The canonical run record carries no worker ownership;
the deployment record carries no worker ownership; the dispatch recovery record
is an unpersisted value object with no worker identity; no production code path
creates a worktree lease; the coding worker publishes no heartbeat (with the
chat and voice workers as contrast); the lease contract cannot carry a Guardian
run; the existing classifier leaves an evidence-free attempt alone; the
existing contract quarantines rather than re-dispatching; the existing
classifier marks stale evidence uncertain when evidence *is* supplied.

**The gap (7 cases).** A restarted worker performs no reconciliation of an
abandoned run; the accepted run survives the disappearance with a stable
`started_at`; a restart re-inserts no queue task; a restart fabricates no
source-thread result; a restart produces no result artifact; a terminal run is
untouched by a restart; repeated restarts leave the canonical state unchanged.

**The disposition (2 cases).** The escalated disposition requires no migration;
escalating preserves the original lineage; the evidence row carries no
credential material.

**The tripwire (1 case, xfail).**
`test_a_restarted_worker_reconciles_an_abandoned_accepted_run` asserts the
desired end-to-end behaviour and is marked `xfail(strict=True)`. It is the
specification for the next task, and it will fail the suite if the behaviour
ever starts happening without the prerequisite landing.

### The eighteen required cases

| # | Required case | Status now |
|---|---|---|
| 1 | Startup detects a qualifying abandoned accepted run | **blocked** — no liveness authority; tripwire xfails |
| 2 | The recovered run retains its original identity | **blocked**, but the disposition is proven to preserve lineage (case 2 of §5) |
| 3 | Recovery classification uses existing Guardian authority | **proven available**; the classifier is exercised in the gate cases |
| 4 | The unresolved run becomes durably operator-visible | **blocked** on the trigger; the representation is proven |
| 5 | No automatic retry occurs | **proven today** — a restart re-inserts no task |
| 6 | No credential lease is renewed | **proven today** — no lease is issued by a restart |
| 7 | No replacement dispatch is created | **proven today** — nothing is enqueued |
| 8 | No duplicate provider invocation occurs | **proven today** — no adapter is entered |
| 9 | No new source-thread result is fabricated | **proven today** — 0 messages |
| 10 | An active worker is not falsely classified as abandoned | **blocked** — there is no classification at all, so it cannot be false; but it cannot be *true* either |
| 11 | An ambiguous owner is not treated as proven dead | **proven** — the classifier's own rule leaves an evidence-free attempt alone |
| 12 | An already-terminal run remains unchanged | **proven today** |
| 13 | Two concurrent reconcilers cannot produce conflicting dispositions | **blocked** — needs the disposition path to exist first |
| 14 | Repeated restarts are idempotent | **proven today** (trivially: nothing changes) |
| 15 | PostgreSQL failure prevents unsafe recovery | **blocked** — the recovery path does not exist to fail |
| 16 | Existing normal acceptance and completion still work | **proven** — the acceptance contract still passes 19/19 |
| 17 | Cross-account recovery inspection cannot expose unrelated run details | **blocked** — there is no recovery inspection surface yet |
| 18 | Existing worker acceptance tests remain valid | **proven** — the acceptance contract and the focused worker sweep are unchanged |

## 8. The smallest durable prerequisite

**A durable, per-run coding-worker ownership claim with liveness and fencing.**

Concretely, the next task needs exactly this and nothing more:

1. **A durable ownership record that binds a coding run to the worker instance
   that owns it.** The natural home is the existing `coding_worktree_leases`
   table — it already carries `worker_id`, `last_heartbeat_at`, and
   `expires_at` — but its contract is worktree-scoped, and a Guardian run
   without worktree isolation has no branch, no worktree path, and no work
   order. Either the lease contract is generalised to a run-scoped ownership
   claim, or a **new** durable run-ownership table is added. The latter is a
   migration and therefore its own authorized task.
2. **A per-run liveness signal that stops when the owner stops.** The runtime's
   established pattern is a Redis heartbeat with a TTL, written by the worker
   and read by a freshness classifier
   (`guardian/workers/chat_worker.py:685`, `guardian/routes/health.py:369`). A
   coding-worker equivalent, scoped per owned run rather than globally, is the
   shape to follow. A *global* coding heartbeat is not sufficient: it cannot
   attribute ownership of a specific run, and it would let a starting worker
   escalate a run owned by a live peer.
3. **Fencing, so a superseded owner's writes can be rejected.** The dispatch
   contract states plainly that fencing is absent, and that without it
   re-dispatch is unsafe against duplicate logical effects. Quarantine-and-
   escalate does not strictly require fencing, but a *concurrent* reconciler
   needs it to be safe against a late terminal success from the previous owner.

With (1) and (2), the existing `observe_liveness()` → `classify_dispatch_health()`
→ `recover_dispatch()` chain can be wired at the startup hook exactly as
specified, with no new recovery taxonomy and no new persisted status. With (3),
the escalation can be made safe against a late terminal success. The xfail
tripwire in §7 is written to pass as soon as that lands.

## 9. What was not done, by design

- **No restart reconciliation was implemented.** The gate forbade it.
- `observe_liveness()`, `classify_dispatch_health()`, and `recover_dispatch()`
  are **unchanged**. No parallel worker-local classifier was written.
- No worker heartbeat, no worker identity, no ownership record, no fencing.
- No migration, no new table, no new persisted status, no new protocol token.
- No Redis queue redesign, no acknowledgement semantics, no retry authority.
- No credential-authority change, no adapter change, no provider change.
- The inherited `NameError: name '_fetch_work_order' is not defined` in
  `guardian/workers/coding_worker.py` was reported, not patched.
- The adapter's empty `files_changed` reporting was not repaired.
- No production state was modified, no production credentials were consumed, no
  real provider request occurred, no sandbox claim was made.
- The earlier PASS and BLOCKED receipts were left intact, and
  `docs/architecture/00-current-state.md` was not edited.
- **Commit-message deviation.** The task spec prescribes
  `fix(delegation): reconcile abandoned coding executions on restart`. That
  message asserts an implementation this proof did not make — the gate forbade
  it — and would contradict the BLOCKED classification recorded in the same
  commit. The commit therefore uses
  `docs(proofs): record Guardian coding restart reconciliation as blocked`,
  which follows the repository's existing convention for a proof-only change.
  The authorized file set is unchanged.

## 10. Validation

Focused sweep, run against the evaluated commit with disposable PostgreSQL:

| Path | Result |
|---|---|
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | **19 passed, 1 xfailed** |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | **19 passed** |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | passed |
| `guardian/tests/workers/test_coding_worker.py` | 15 inherited failures, otherwise passed |
| `guardian/tests/workers/test_coding_worker_regression_guard.py` | 1 inherited failure |
| `guardian/tests/agents/test_pi_readiness.py` | passed |
| **Total** | **163 passed, 15 failed, 1 xfailed** |

Focused **AgentStore terminal-state, credential, lease, and result-delivery**
tests, run separately against the same commit:

| Path | Result |
|---|---|
| `guardian/tests/agents/` (12 files, including `test_execution_credentials.py`, `test_worktree_lease_store.py`, `test_worktree_leases.py`) | passed |
| `tests/agents/test_execution_ledger_store.py` | passed |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | passed |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | 1 xfailed (the tripwire) |
| **Total** | **156 passed, 1 xfailed** |

### 10.1 Inherited-failure comparison

The 15 failures are compared by **exact test identity and exact failure cause**
against the unmodified baseline recorded by the durable-acceptance slice at the
same commit `325e225f`:

```
$ diff baseline_ids.txt recovery_ids.txt       →  IDENTITIES IDENTICAL (15/15)
$ diff baseline_causes.txt recovery_causes.txt  →  CAUSES IDENTICAL
```

**15 inherited failures, 0 regressions.** All fifteen are present and
unchanged in both runs — 14 in `guardian/tests/workers/test_coding_worker.py`
and 1 in
`guardian/tests/workers/test_coding_worker_regression_guard.py::test_no_name_error_in_guard_path`.
They are predominantly this sandbox's own limits: git worktree creation is
denied on this filesystem (`git init` fails with
`unable to unlink .git/config.lock`), so the isolated-worktree cases cannot
construct their fixtures. One is a genuine pre-existing product defect,
reported and **not** patched:

```
NameError: name '_fetch_work_order' is not defined
```

in `guardian/workers/coding_worker.py` (campaign-attempt-ledger path).

### 10.2 The monolithic backend gate

The repository's default backend gate — `pytest -v` over the whole suite — was
run against the evaluated commit, and compared by **exact test identity** with
the gate the durable-acceptance slice recorded at the same commit `325e225f`.
The Private Preview stayed healthy (`127.0.0.1:8081/health` → 200) throughout.

| Run | Result |
|---|---|
| baseline (`325e225f`, recorded by the acceptance slice) | **137 failed, 8729 passed, 108 skipped, 35 xfailed, 11 xpassed, 40 errors** (27:59) |
| this evaluation (`325e225f` + this proof's files) | **140 failed, 8745 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** (41:47) |

| Category | Count |
|---|---|
| Shared identical failure identities | **136** |
| Failed only in this run | 4 — all in `tests/workers/test_document_worker_shutdown.py` |
| Failed only in the baseline | 1 — `tests/vector/test_vector_physical_deadline.py::test_chroma_bound_search_preserves_results_and_deferred_parent_handle` |
| Collection errors, identical in both runs | **40** |

The outcome counters reconcile exactly: the +16 passed and +1 xfailed are this
proof's 19 passing contract cases and its one strict-xfail tripwire. **No
recovery-contract case failed in the monolithic run.**

**The four differences are load-sensitive flakes, and this was verified in an
unmodified tree rather than argued.** All four funnel through
`_run_active_probe` in `tests/workers/test_document_worker_shutdown.py`, which
spawns a document worker as a **subprocess** and waits on wall-clock timeouts
(`_wait_for(path, timeout=30)`, `process.join(10)`, `process.join(20)`). They
are the same identities the acceptance slice already recorded as unstable.

Run in isolation in the **unmodified baseline tree** — the `325e225f`
implementation, with none of this proof's files present:

| Identity | Unmodified baseline tree, isolated | This tree, isolated |
|---|---|---|
| `test_active_success_commits_before_shutdown` | **failed** | failed |
| `test_hung_writer_is_reaped_before_failed_commit_with_no_late_writes` | **failed** | failed |
| `test_repeated_signals_do_not_duplicate_finalization` | passed | failed |
| `test_signal_during_dequeue_drains_the_already_owned_job` | passed | failed |

Two of the four fail in a tree that contains **none** of this change, one
passes there and failed here, and one run of the same unmodified tree hung past
a 300-second limit. This change adds **no runtime code** — it adds one test
file and two documentation edits — so it cannot be the cause. These are the
known unstable identities, and the count difference between the two gate runs
(137 vs 140) is that instability, not a regression.

**Conclusion: 0 regressions.**

### 10.3 Repository hygiene

```
$ git diff --check        →  clean
$ git status --short --branch
## feature/guardian-delegation-acceptance-axis
```

Only the authorized files are touched. `guardian/core/guardian_dispatch.py`,
`guardian/agents/store.py`, and `guardian/workers/coding_worker.py` are
**unchanged** — this task changed no runtime code, because the gate forbade it.

## 11. Invariant check

- Guardian owns execution and recovery authority — unchanged; nothing here
  grants recovery authority.
- PostgreSQL remains canonical execution truth — unchanged; the acceptance
  record is still the canonical fact.
- **Worker liveness must be established, not guessed** — honoured. This proof
  is a refusal to guess, and the refusal is the deliverable.
- An active worker must not be falsely quarantined — honoured by not
  implementing anything that could quarantine.
- An uncertain attempt must not be silently retried — honoured; no retry
  exists, and the controlled proof observed no requeue.
- A terminal result cannot be overwritten by recovery — honoured; a terminal
  run is untouched by a restart.
- Queue state cannot authorize provider execution — unchanged.
- Worker restart cannot create credential authority — unchanged; the restart
  issued no lease.
- Execution binding and lineage remain immutable — the disposition, when it
  lands, preserves them; proven by the lineage test.
- No cross-account recovery visibility — no recovery surface exists to leak.
- No secret material in recovery evidence — proven by the evidence test.
- No new release claim from a synthetic recovery proof — none made.

## 12. Remaining recovery gaps

These remain open and are **not** hidden inside the recovery classification:

1. **Destructive dequeue before durable acceptance** — a task removed from the
   queue and lost before acceptance is unrecoverable, and no acceptance record
   exists to reconcile.
2. **Abandoned accepted attempt after worker death** — this task's subject;
   blocked on the prerequisite in §8.
3. **Restart-time uncertain classification** — blocked on the same.
4. **Quarantine/escalation persistence** — the representation exists (§5); the
   trigger is blocked.
5. **Worktree lease recovery and cleanup** — the lease path is not populated in
   production; uncertain worktrees are not cleaned.
6. **Git worktree cleanup after uncertain execution** — a crashed worker can
   leave an isolated worktree behind, and nothing reclaims it.
7. **Operator-driven resolution of an uncertain attempt** — the operator
   resolution workflow remains outside the recovery contract, as specified.
8. **Provider-enforced process/network/filesystem isolation** — unproven and
   unchanged.

## 13. Final classification

**BLOCKED** — *Authoritative worker-liveness/fencing or another prerequisite is
missing.*

The restart-reconciliation contract is **not** implemented. The durable
acceptance prerequisite that preceded it is proven and working, the canonical
escalated disposition is proven to need no migration, and the absence of
reconciliation is proven by a controlled SIGKILL-and-restart experiment against
disposable PostgreSQL and Redis. The gate that gates the implementation fails:
the runtime has no per-run worker ownership and no coding-worker liveness
signal, so an abandoned accepted run cannot be distinguished from an actively
owned one without guessing. The smallest durable prerequisite is specified in
§8, and the contract file carries a strict-xfail tripwire that turns green the
moment it lands.

Release status remains **HOLD**. The previous functional delegation PASS remains
historical, branch-scoped evidence. Interruption recovery remains **BLOCKED**,
and this proof does not change that: it locates the missing prerequisite rather
than satisfying it.
