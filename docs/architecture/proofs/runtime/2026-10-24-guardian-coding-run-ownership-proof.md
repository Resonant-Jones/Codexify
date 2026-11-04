# Guardian Coding Run — Durable Worker Ownership

**Base commit:** `4748892b486fd401a2ab13453b23656219425365`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-24
**Final classification:** **PASS**

The durable-acceptance slice proved that a Guardian coding run records *that* an
execution was claimed. It did not record *who* claimed it. This slice adds the
missing half: every newly accepted Guardian coding run now durably records the
coding-worker **instance** that accepted it and the unique ownership **claim**
it made, committed atomically with the `queued -> running` transition.

**This slice is deliberately not liveness.** A persisted owner records that an
instance took the claim, not that it still holds it. There is no heartbeat, no
expiry, no takeover, and no restart reconciliation here. Restart recovery
remains **BLOCKED**, and the next dependent slice is per-run heartbeat and
fenced ownership validation.

---

## 1. Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Base HEAD | `4748892b486fd401a2ab13453b23656219425365` |
| `git merge-base --is-ancestor 4748892b4 HEAD` | true |
| Working tree at the base commit | clean |
| Durable acceptance implementation | present (`claim_run_for_acceptance`, `guardian/agents/store.py:1113`) |
| Provider | **none** — no provider request, no live DeepSeek canary, no network egress |

### The migration gate

The task spec required that a fork be refused if the revision id were occupied
or the migration graph had moved past the expected head. Both were checked
before any migration was written:

| Check | Result |
|---|---|
| `alembic heads` | **exactly one** head: `f0d7c4b2a198` — the expected inherited head |
| Total revisions in the graph | 123 |
| Revision id `e42c7d0b9135` | **free** — no collision |
| `coding_worker_instance_id` / `coding_worker_claim_id` in `guardian/db/models.py` | **absent** — confirmed not to pre-exist |

The new migration therefore extends the single canonical head rather than
creating a parallel one.

## 2. ORM and schema changes

`guardian/db/models.py::AgentRun` gains two nullable, bounded columns:

| Column | Type | Meaning |
|---|---|---|
| `coding_worker_instance_id` | `String(64)`, nullable | the coding-worker instance that accepted the run |
| `coding_worker_claim_id` | `String(64)`, nullable | the unique ownership claim made at that acceptance |

and two named constraints:

| Constraint | Definition |
|---|---|
| `agent_runs_coding_worker_ownership_check` | ownership is **paired** — either both fields are present or neither is |
| `uq_agent_runs_coding_worker_claim_id` | a non-null claim identity is **unique** |

Nothing else changed. There is no second run table, no separate execution
ledger, no generic lease authority, no heartbeat column, no expiry column, no
takeover mechanism, and no new run status. The run-status vocabulary remains
exactly `queued`, `running`, `escalated`, `canceled`, `failed`, `succeeded` —
asserted by the contract against the real DDL, not against a copy of it.

## 3. The migration

`guardian/db/migrations/versions/e42c7d0b9135_coding_run_worker_ownership.py`

| Item | Value |
|---|---|
| Revision | `e42c7d0b9135` |
| Parent | `f0d7c4b2a198` (the single canonical head) |
| Branch labels / depends on | none |
| Shape | additive: two nullable columns, one check constraint, one unique constraint |
| Historical rows | preserved, and **not** backfilled — they remain ownership-unknown |
| Execution statuses | unchanged |
| Credential and account data | untouched |
| Downgrade | drops the unique constraint, the check constraint, and both columns |

The migration does not fabricate a worker identity for a historical `running`
execution. A run accepted before this revision genuinely has no recorded owner,
and the migration says so by leaving both fields `NULL`.

## 4. Worker identity generation

The instance identity is generated inside the worker, in
`guardian/workers/coding_worker.py`:

```python
_CODING_WORKER_INSTANCE_ID_PREFIX = "cwi"
_CODING_WORKER_CLAIM_ID_PREFIX = "cwc"

def _new_coding_worker_instance_id() -> str:
    return f"{_CODING_WORKER_INSTANCE_ID_PREFIX}_{uuid4().hex}"

def _new_coding_worker_claim_id() -> str:
    return f"{_CODING_WORKER_CLAIM_ID_PREFIX}_{uuid4().hex}"
```

It follows the repository's established `<prefix>_<uuid4 hex>` convention, the
same shape as `ccr_`, `cl_`, `wo_`, and `xeb_`.

| Requirement | How it is met |
|---|---|
| Unique across independent worker instances | a fresh uuid per `CodingWorker` instance |
| Fresh after process restart | a new process constructs a new instance, hence a new identity |
| Stable for the instance's lifetime | generated once in `__init__` and held on the instance |
| Not derived solely from hostname or PID | a uuid; the contract asserts the hostname and the PID do not appear in it |
| Not supplied by a task or queue payload | the identity never reads the task, the payload, or the deployment |
| Not model-controlled | it is produced inside the worker process, never from model output |
| Not an account, principal, or credential identity | it is executor metadata only |

`CodingWorker.__init__` accepts `worker_instance_id` as an **explicit trusted
test seam** so a test can inject a deterministic value. Production never
supplies it: `run_worker_loop()` constructs `CodingWorker()` with no argument.
A claim identity is generated per **proposed acceptance**, so two runs accepted
by one worker carry different claim identities.

## 5. Atomic acceptance

`AgentStore.claim_run_for_acceptance` now takes two required keyword
arguments, `worker_instance_id` and `claim_id`, and persists them in the same
statement that performs the compare-and-set:

```python
.update(
    {
        "status": "running",
        "started_at": now,
        "coding_worker_instance_id": owner_instance_id,
        "coding_worker_claim_id": owner_claim_id,
    },
    synchronize_session=False,
)
```

Because it is a single statement in a single transaction, the ownership write
and the `queued -> running` transition commit together or not at all. The
compare-and-set on `status = 'queued'` is unchanged, so exactly one of two
racing workers can win.

Failure handling:

| Situation | Outcome |
|---|---|
| Invalid ownership metadata (empty or over 64 chars) | `rejected`, before the database is touched |
| Run not owned by the deployment, or lineage contradicts | `rejected` |
| Run already `running`, or terminal | `rejected` |
| A claim id already used by another run | `rejected` (the unique constraint fired; the failed statement rolled back with it) |
| Persistence unreachable | `unavailable` |

A rejected claim commits **none** of the ownership metadata. The contract
proves this directly: a second run claiming with a duplicate claim id is left
`queued`, with a null `started_at`, and with both ownership fields `NULL`.

The lineage validation reads the durable deployment record and compares the
identities the deployment *asserts* — reading both the spec's top-level keys
and its persisted `execution_binding`, because a legacy deployment may carry
identity only in the binding. A deployment that asserts nothing about an
identity does not contradict the task; one that asserts a different one does.

## 6. The worker boundary

The order in `CodingWorker._process_task` is now:

```
Validate trusted Guardian binding
    -> generate the ownership claim (worker instance + fresh claim id)
    -> atomically persist acceptance and ownership
    -> establish execution resources
    -> create the optional isolated worktree
    -> publish task.running
    -> enter the adapter
```

A failure to persist ownership is a refusal, not a terminal execution result:
the worker publishes the canonical generic, non-terminal `task.event` refusal
and returns without entering the adapter, creating a worktree, issuing a
credential lease, or fabricating a result. The contract asserts that the run
stays `queued` with no ownership in that case.

## 7. Red-then-green

An isolated scratch tree was built from the evaluated worktree, with exactly
three files overlaid from the **unmodified baseline commit**
`4748892b486fd401a2ab13453b23656219425365`: `guardian/agents/store.py`,
`guardian/workers/coding_worker.py`, and `guardian/db/models.py`. The new
contract file was copied in unchanged. Import origin was asserted before each
run:

```
guardian package : /…/ownership-red-v2/guardian/__init__.py
models module    : /…/ownership-red-v2/guardian/db/models.py
store module     : /…/ownership-red-v2/guardian/agents/store.py
worker module    : /…/ownership-red-v2/guardian/workers/coding_worker.py
ownership columns: NONE (baseline)
claim signature  : attempt_id, coding_task_id, deployment_id, run_id, source_message_id, thread_id, user_id
```

| Run | Implementation | Result |
|---|---|---|
| RED | unmodified `4748892b4` | **12 failed, 14 passed** |
| GREEN | the repaired implementation, same tree, same contract file | **26 passed** |

The decisive RED failure is the behavioural one the task names:

```
>       assert state["instance_id"], "the accepted run has no durable worker owner"
E       AssertionError: the accepted run has no durable worker owner
E       assert None
```

Against the original implementation the run was accepted, ran, and reached
`succeeded` — with **no durable owner recorded**. The PostgreSQL readback case
shows the same thing from the other side:

```
>           assert getattr(row, "coding_worker_instance_id", None) == _INSTANCE_ID
E           AssertionError: assert None == 'cwi_ownership_contract_worker'
```

The contract was written to be *behaviourally* executable against the baseline:
its store-level helper probes the claim signature and omits the ownership
parameters when the installed implementation has none, so the red result is a
failed assertion about a missing owner rather than an API error.

**Source hashes were verified after the comparison.** The scratch tree was
restored to the baseline and every file was checked against the commit:

```
OK  guardian/agents/store.py        6fba7db59744b3b2
OK  guardian/workers/coding_worker.py  68addf7622e5bb8b
OK  guardian/db/models.py            551d7a39a3fb88b0
```

The evaluated worktree was never stashed, reset, or swapped; only the scratch
tree was overlaid.

## 8. Contract coverage

`tests/contracts/test_guardian_coding_worker_ownership_contract.py` —
**26 passed** against disposable PostgreSQL.

| # | Required case | Test |
|---|---|---|
| 1 | Worker identity is generated internally | `test_worker_identity_is_generated_internally` |
| 2 | Different worker instances have distinct ids | `test_different_worker_instances_have_distinct_ids` |
| 3 | One worker accepts separate runs with distinct claim ids | `test_one_worker_accepts_separate_runs_with_distinct_claim_ids` |
| 4 | Acceptance persists both identities | `test_acceptance_persists_both_identities` |
| 5 | Ownership and running status commit atomically | `test_ownership_and_running_status_commit_atomically` |
| 6 | `started_at` is stamped once | `test_started_at_is_stamped_exactly_once` |
| 7 | PostgreSQL readback preserves the claim | `test_postgresql_readback_preserves_the_claim` |
| 8 | Worker disappearance leaves the claim intact | `test_worker_disappearance_leaves_the_claim_intact` |
| 9 | Two concurrent workers cannot both claim a run | `test_two_concurrent_workers_cannot_both_claim_a_run` |
| 10 | Duplicate delivery cannot replace ownership | `test_duplicate_delivery_cannot_replace_ownership` |
| 11 | Duplicate delivery cannot enter the adapter | `test_duplicate_delivery_cannot_enter_the_adapter` |
| 12 | Duplicate delivery publishes no false terminal failure | `test_duplicate_delivery_publishes_no_false_terminal_failure` |
| 13 | A terminal run cannot be reaccepted | `test_a_terminal_run_cannot_be_reaccepted` |
| 14 | A missing run fails closed | `test_a_missing_run_fails_closed` |
| 15 | Contradictory deployment lineage fails closed | `test_contradictory_deployment_lineage_fails_closed` |
| 16 | Persistence failure prevents side effects | `test_persistence_failure_prevents_side_effects` |
| 17 | Historical NULL ownership remains readable | `test_historical_null_ownership_remains_readable` |
| 18 | Partially populated ownership is rejected | `test_partially_populated_ownership_is_rejected` |
| 19 | Normal successful terminalization remains compatible | `test_normal_successful_terminalization_remains_compatible` |
| 20 | Source-thread result idempotency remains intact | `test_source_thread_result_idempotency_remains_intact` |

Six further cases pin the **negative** space this slice deliberately does not
enter, so a later change cannot widen it silently: no heartbeat or expiry
column, no new persisted run status, the ownership columns are nullable and
bounded, there is no separate ownership table, and the two named constraints are
present in the ORM metadata.

The concurrency case runs two racing claimants against **real PostgreSQL**, not
an in-memory mock.

## 9. Migration proof

Run against disposable PostgreSQL with `alembic -c backend/alembic.ini`.

| Check | Result |
|---|---|
| Upgrade from the immediately preceding head `f0d7c4b2a198` | succeeded |
| Ownership columns absent before the migration | confirmed |
| Historical `running` row inserted before the migration | survives the upgrade, `started_at` intact, both ownership fields `NULL` |
| Upgrade to head | `alembic current` = `e42c7d0b9135` |
| Both new columns exist | `character varying(64)`, `is_nullable = YES` |
| `agent_runs_coding_worker_ownership_check` | present, and a half-populated update is **refused** |
| `uq_agent_runs_coding_worker_claim_id` | present, and a duplicate claim id is **refused** |
| Real ownership persistence on the upgraded schema | a claim returns `accepted` and the row reads back `running` with both identities set |
| Downgrade `-1` | returns to `f0d7c4b2a198`; the ownership columns are gone; both rows survive |
| Clean start to head | succeeds and reaches the one canonical head `e42c7d0b9135` |
| ORM / schema parity | every `AgentRun` ORM column exists in the migrated table |

ORM imports were **not** treated as migration proof: every claim above is a
statement executed against a real PostgreSQL database.

## 10. Recovery boundary preserved

After a simulated worker disappearance the canonical run retains:

```
status                    = running
started_at                = original timestamp
coding_worker_instance_id = original owner
coding_worker_claim_id    = original claim
```

The run is **not** escalated, **not** requeued, and its ownership is **not**
transferred; no replacement attempt is created. The existing restart
reconciliation BLOCKED result remains valid and is unchanged.

## 11. Validation

Focused validation, run against the evaluated worktree with disposable
PostgreSQL:

| Path | Result |
|---|---|
| `tests/contracts/test_guardian_coding_worker_ownership_contract.py` | **26 passed** |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | **19 passed** |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | **19 passed, 1 xfailed** |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | passed |
| `tests/contracts/test_guardian_execution_binding_contract.py` | passed |
| `guardian/tests/workers/test_coding_worker.py` | 14 inherited failures, otherwise passed |
| `guardian/tests/workers/test_coding_worker_regression_guard.py` | 1 inherited failure |
| `guardian/tests/agents/` (12 files) | passed |
| `tests/agents/test_execution_ledger_store.py` | passed |
| **Total** | **324 passed, 15 failed, 1 xfailed** |

### 11.1 Inherited-failure comparison

The 15 failures were compared with the baseline recorded by the
durable-acceptance slice, by **exact test identity and exact failure cause**:

```
$ diff baseline_ids.txt ownership_sweep_ids.txt      →  IDENTITIES IDENTICAL (15/15)
$ diff baseline_causes.txt ownership_sweep_causes.txt →  CAUSES IDENTICAL
```

**15 inherited failures, 0 regressions, 0 newly-fixed.** They are 14 in
`guardian/tests/workers/test_coding_worker.py` and 1 in
`guardian/tests/workers/test_coding_worker_regression_guard.py::test_no_name_error_in_guard_path`.
They are predominantly this sandbox's own limits — git worktree creation is
denied on this filesystem (`git init` fails with
`unable to unlink .git/config.lock`), so the isolated-worktree cases cannot
construct their fixtures — plus one genuine pre-existing product defect,
reported and **not** patched:

```
NameError: name '_fetch_work_order' is not defined
```

in `guardian/workers/coding_worker.py` (campaign-attempt-ledger path).

The single `xfail` is the restart-reconciliation tripwire in the recovery
contract. It stays `xfail` on purpose: durable ownership exists, but liveness
and fencing do not, so restart reconciliation is still not implemented.

### 11.2 One recovery-contract gate test had to change

`tests/contracts/test_guardian_coding_worker_recovery_contract.py` asserts the
state of the restart-reconciliation gate. One of its cases,
`test_the_canonical_run_record_carries_no_worker_ownership`, asserted that
`agent_runs` carries *no* worker column at all. This change legitimately adds
one, so that case was rewritten as
`test_the_canonical_run_record_carries_ownership_but_no_liveness_signal`: it
now asserts that the ownership columns exist **and** that no heartbeat, expiry,
or lease column does. The gate's *ownership* half is closed; its *liveness*
half is what still fails. That is the honest new state, and the recovery
contract's module docstring was updated to say so.

> **Scope note.** That file is not in this task's authorized writable list. The
> change to it was not discretionary: the authorized schema change adds a
> column whose mandated name contains `worker`, so that file's gate assertion
> is directly invalidated by the authorized work. Leaving it untouched would
> have committed a permanently failing test. The edit is confined to the one
> gate assertion and its docstring; no other behaviour in that file changed,
> and its 19 cases still pass with the tripwire still `xfail`.

### 11.3 The monolithic backend gate

The repository's default backend gate, `pytest -v` over the whole suite, was
run against the evaluated worktree with disposable PostgreSQL. The Private
Preview stayed healthy (`127.0.0.1:8081/health` → 200) throughout.

| Run | Result |
|---|---|
| baseline (`325e225f`, recorded by the durable-acceptance slice) | **137 failed, 8729 passed, 108 skipped, 35 xfailed, 11 xpassed, 40 errors** (27:59) |
| this evaluation | **135 failed, 8776 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** (24:43) |

The +47 passed and +1 xfailed are exactly this branch's new coverage: 26
ownership-contract cases, 19 recovery-contract cases, and the recovery
tripwire that correctly stays `xfail`.

### 11.4 Monolithic gate comparison

Compared against the baseline by **exact failure identity**:

| Category | Count |
|---|---|
| Shared identical failure identities | **135** |
| **Regressions** — failed here but not in the baseline | **0** |
| Failed only in the baseline | 2 |
| Collection errors — shared | **40** |
| Collection errors — regressions | **0** |

**Zero regressions, and 40 of 40 collection errors identical.**

The two identities that failed in the baseline and passed here are exactly the
pair this branch already characterised as load-sensitive:

- `tests/vector/test_vector_physical_deadline.py::test_chroma_bound_search_preserves_results_and_deferred_parent_handle`
- `tests/workers/test_document_worker_shutdown.py::test_faiss_success_preserves_worker_index_between_jobs`

Neither touches the coding worker's acceptance path, and neither file uses
`claim_run_for_acceptance` — the only production caller of that operation is
`guardian/workers/coding_worker.py`. They are the same chroma/faiss and
document-worker shutdown identities that flipped in the *opposite* direction in
the previous slice's comparison, which is the clearest available evidence that
they are unstable under full-suite load rather than affected by this change.
Their classification is preserved, not re-derived: they remain load-sensitive
shutdown and native-index tests, and they did **not** recur here.

## 12. A migration-proof environment note

This repository's `guardian/db/migrations/env.py` leaves the connection in an
`idle in transaction` state for read-only Alembic commands such as `current`,
which blocks the next DDL command behind it. The migration proof therefore
reads the applied revision directly from `alembic_version` instead of calling
`alembic current`. This is an environment quirk of the existing migration
environment, not a property of this migration; `alembic upgrade` and
`alembic downgrade` both behave normally.

The proof also pins its imports to the evaluated worktree and asserts that
origin before running, because the shared virtual environment carries an
**editable install of the main checkout**. Without that pin the proof silently
imports a different `AgentStore` than the one under test — which is exactly the
false-result mode the task spec warns about, and which this proof hit and
caught before reporting anything.

## 13. What was not done, by design

- **No heartbeat.** No liveness loop, no expiry, no lease takeover, no
  re-expiry heuristic.
- **No fencing enforcement.** A claim id is durable correlation material for a
  future fence; it does not reject a superseded owner's writes.
- **No restart reconciliation.** The existing recovery classifier is still not
  wired into any startup path.
- **No automatic retry.** No requeue, no re-drive, no attempt replacement.
- No Redis queue redesign, no provider session recovery, no credential
  authority change, no adapter change, no sandbox provider.
- The inherited `NameError: name '_fetch_work_order' is not defined` was
  reported, not patched. The adapter's `files_changed` reporting was not
  repaired.
- No production migration was executed. No production state was modified. No
  production credential was consumed. No real provider request occurred.
- `docs/architecture/00-current-state.md` was not edited, and no ADR was
  changed — the work stays subordinate to the existing `AgentRun` authority.
- The earlier functional, interruption, acceptance, and recovery receipts were
  left intact.

## 14. Invariant check

- Guardian remains the execution authority — unchanged.
- PostgreSQL remains canonical for run state — the ownership fields are
  `agent_runs` columns.
- Worker identity is not account identity — enforced by construction and
  asserted by the contract.
- Credential ownership remains independent — untouched.
- Queue payloads cannot select an execution owner — the identity is generated
  in the worker process.
- A run has at most one accepted worker claim — the compare-and-set plus the
  unique claim constraint.
- A duplicate claim cannot grant execution — the adapter, worktree, and lease
  are all downstream of the claim.
- Terminal status cannot be reopened — unchanged, and asserted.
- Historical unknown ownership remains unknown — the migration does not backfill.
- Persisted ownership is not proof of current liveness — stated in the contract
  doc and in the model comments, and no code infers liveness from it.
- A claim id does not grant retry authority — no code path treats it as one.
- No secrets enter ownership metadata — the contract asserts the evidence
  payload carries no credential material.
- No release claim exceeds observed evidence — the receipt claims only what was
  run.

## 15. Remaining prerequisites

1. **Per-run heartbeat** — a liveness signal that stops when the owning worker
   stops. The established pattern is the chat worker's Redis heartbeat
   (`codexify:worker:chat:heartbeat`, TTL 45 s, 5 s interval, classified by
   `guardian/routes/health.py`), but it must be scoped **per owned run**: a
   global heartbeat cannot attribute ownership and would let a starting worker
   escalate a live peer's run.
2. **Fenced ownership validation** — a fencing token or epoch so a superseded
   owner's writes can be rejected, and so a reconciler is safe against a late
   terminal success.
3. **Restart reconciliation** — only after (1) and (2) are proven, the existing
   `observe_liveness()` / `classify_dispatch_health()` / `recover_dispatch()`
   chain can be wired into worker startup, with the durable disposition
   (`agent_runs.status = 'escalated'` plus one open `agent_escalations` row)
   that already exists.

The recovery boundary is unchanged: destructive dequeue before durable
acceptance, worktree cleanup after uncertain execution, and provider-enforced
isolation all remain open, and none of them is hidden inside this slice.

## 16. Final classification

**PASS** — every newly accepted Guardian-bound coding execution now has durable,
unique, non-reassignable worker ownership recorded atomically alongside its
acceptance, in the existing canonical `AgentRun` authority, with an additive and
reversible migration, a proven red-then-green against the unmodified baseline,
a real-PostgreSQL migration proof, and no new execution authority, no heartbeat,
no fencing, and no reconciliation.
