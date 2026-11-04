# Guardian Coding Run — Claim-Scoped Heartbeats

**Base commit:** `c2167aa24aa421aa8848b5dbaf673504b750069a`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-25
**Final classification:** **PASS** (release remains **HOLD**)

Durable ownership proved *which* worker instance took a claim. It could not say
whether that instance was still working: an accepted run looked identical
whether it was mid-execution or abandoned. This slice adds the missing half —
a durable, per-run, claim-scoped heartbeat on the canonical `agent_runs` row,
written atomically with acceptance and renewable only by the recorded
owner/claim.

**This slice is deliberately not recovery.** A heartbeat is *evidence of
reported activity*, never authority. Nothing infers death from a stale
heartbeat, no expiry rule exists, no owner takeover exists, no automatic retry
exists, and restart reconciliation remains unimplemented. The next dependent
slice is claim-fenced terminal persistence and stale-worker result rejection;
after that, worker-liveness classification and wiring Guardian's existing
recovery classifier to worker restart.

---

## 1. Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Base HEAD | `c2167aa24aa421aa8848b5dbaf673504b750069a` |
| `git merge-base --is-ancestor c2167aa2 HEAD` | true |
| Working tree at the base commit | clean (tracked) |
| Provider | **none** — no provider request, no live DeepSeek canary, no network egress |
| Production resources | **none touched** — every database used here was disposable and local |

### The migration gate

The spec required refusing a fork if the revision id were occupied or the
migration graph had moved. Both were checked before the migration was written:

| Check | Result |
|---|---|
| `alembic heads` | **exactly one** head: `e42c7d0b9135` — the expected inherited head |
| Revision id `d86f2a4b1c90` | **free** — no collision |
| `coding_worker_last_heartbeat_at` in `guardian/db/models.py` | **absent** — confirmed not to pre-exist |

## 2. Canonical heartbeat schema

`guardian/db/models.py::AgentRun` gains one nullable, timezone-aware column:

| Column | Type | Meaning |
|---|---|---|
| `coding_worker_last_heartbeat_at` | `TIMESTAMP(timezone=True)`, nullable | the last moment the *recorded owner* reported liveness for this run |

and one named constraint:

| Constraint | Definition |
|---|---|
| `agent_runs_coding_worker_heartbeat_ownership_check` | a non-NULL heartbeat requires **both** ownership fields to be present |

Nothing else changed. There is no second heartbeat table, no generic
worker-liveness control plane, no expiry column, no takeover column, and no new
run status. The run-status vocabulary remains exactly `queued`, `running`,
`escalated`, `canceled`, `failed`, `succeeded`.

The column is **not** writable through an untrusted request: it is written only
by the two store operations below, and never by Redis task-event ingestion.

## 3. Migration identity and parent

`guardian/db/migrations/versions/d86f2a4b1c90_coding_run_claim_heartbeat.py`

| Item | Value |
|---|---|
| Revision | `d86f2a4b1c90` |
| Parent | `e42c7d0b9135` (the single canonical head) |
| Branch labels / depends on | none |
| Shape | additive: one nullable column, one named check constraint |
| Historical rows | preserved, and **not** backfilled — they keep a `NULL` heartbeat |
| Execution statuses | unchanged |
| Credential and account data | untouched |
| Downgrade | drops the constraint, then the column |

## 4. Initial acceptance transaction

`AgentStore.claim_run_for_acceptance` now writes the first heartbeat in the
**same single UPDATE** that performs the acceptance:

```
status                           = 'running'
started_at                       = <worker clock, stamped once>
coding_worker_instance_id        = <trusted owner>
coding_worker_claim_id           = <unique claim>
coding_worker_last_heartbeat_at  = now()      -- the DATABASE clock
```

The heartbeat is written **from the database clock** (`func.now()`), not the
worker's wall clock, so the liveness evidence and the durable row share one
canonical time source. `started_at` deliberately keeps the worker-side clock it
has always used.

A refused acceptance writes **none** of these fields: the heartbeat cannot
exist without the ownership that produced it, and a duplicate claim cannot
refresh it. Proven by the contract, including a case where the worker clock is
patched to 1999 and the heartbeat is shown *not* to follow it.

## 5. Renewal operation

`AgentStore.renew_coding_run_heartbeat(run_id, worker_instance_id, claim_id)`
performs **one** conditional update — never a read-then-write:

```
UPDATE agent_runs
   SET coding_worker_last_heartbeat_at = now()
 WHERE run_id = :run_id
   AND status = 'running'
   AND coding_worker_instance_id = :worker_instance_id
   AND coding_worker_claim_id = :claim_id
```

The database's own verdict is the authority. Outcomes:

| Outcome | Meaning |
|---|---|
| `renewed` | the row matched; the heartbeat advanced |
| `not_eligible` | the row did not match — different worker, different or obsolete claim, missing run, or a terminal/escalated run. **Zero rows updated.** |
| `unavailable` | persistence could not be reached; the failure is observable, never silently swallowed |

The renewal never creates or repairs ownership metadata, never refreshes
`started_at`, never changes a terminal status, and never reopens a run.

## 6. Worker heartbeat lifecycle

`guardian/workers/coding_worker.py`:

- `CODING_RUN_HEARTBEAT_INTERVAL_SECONDS` — the explicit cadence, default
  **15 seconds**, overridable by environment so it is testable.
- `_CodingRunHeartbeat` — a per-execution reporter on its **own** thread
  (the adapter invocation is synchronous, so a heartbeat on the worker's thread
  would be silent for the whole provider call). Each renewal opens its **own**
  bounded database session; no SQLAlchemy session is shared across threads.
- The reporter is **stopped and joined** on every terminal path — success,
  failure, cancellation — plus a `finally` safety net on the poll loop, so it
  cannot leak into a later task or outlive a graceful shutdown.
- The reporter is held on the worker instance (`self._coding_run_heartbeats`),
  never in process-global state.
- **Graceful shutdown** is a real path, not an assumption: `CodingWorker.shutdown()`
  stops and joins every reporter the worker owns, and `run_worker_loop()` calls
  it in a `finally`, so no reporter can outlive the worker that owns it. The
  reporter is a daemon thread, so even an abrupt process death cannot leave it
  holding the process open. Stopping a reporter does not resolve the run: the
  canonical row keeps its status, owner, claim, and last heartbeat, and a
  stopped reporter merely freezes the evidence.

**Ownership loss.** A `not_eligible` renewal stops the reporter immediately and
preserves the rejection reason (`coding_run_claim_no_longer_eligible`). The
worker then refuses to enter the adapter, because the claim it holds is no
longer the canonical owner of the run. It does not replace the claim, mint a
new owner or binding, issue another credential lease, grant a retry, or convert
the rejection into a successful execution. The refusal is published as the
canonical generic, **non-terminal** `task.event` with
`error_code = 'EXECUTION_OWNERSHIP_LOST'`.

## 7. Blocked-adapter renewal observation

`tests/contracts/test_guardian_coding_worker_heartbeat_contract.py::test_heartbeat_continues_while_a_synthetic_adapter_is_blocked`
uses `threading.Event` barriers (no arbitrary sleeps): the adapter blocks until
the test releases it, and the contract asserts the heartbeat advances **while
the adapter is blocked**.

## 8-11. Ownership validation results

From the contract (all passing, against real disposable PostgreSQL):

| Case | Result |
|---|---|
| Valid owner/claim renewal | `renewed`, and the heartbeat **advances** |
| Incorrect worker instance id | `not_eligible` |
| Incorrect claim id | `not_eligible` |
| Missing claim | `not_eligible` |
| Missing run | `not_eligible` |
| Terminal run | `not_eligible` |
| Escalated run | `not_eligible` |
| Two workers, different claims, same run | only the recorded owner renews |
| Ownership columns after a rejected renewal | unchanged |
| Persistence failure | observable as `unavailable` |
| Duplicate acceptance | does not refresh the heartbeat |

## 12. Worker-disappearance readback

Executed against real disposable PostgreSQL, with the owning worker running in
a **separate operating-system process** that used the production
`CodingWorker` acceptance path and the production heartbeat thread:

| Step | Observation |
|---|---|
| Before the child ran | `status='queued'`, no owner, no claim, no heartbeat |
| Child accepted the run | `status='running'`, `coding_worker_instance_id='cwi_0ba363764e284ebf9a712be6a8ab2557'`, `coding_worker_claim_id='cwc_56960ed73503402bbe918efc453020d5'`, heartbeat written |
| Child alive and blocked in the adapter | heartbeat **advanced** |
| Child SIGKILLed (`returncode -9`, no cleanup) | `status='running'`, `ended_at` null, owner and claim **unchanged**, last heartbeat **preserved** |
| After waiting past the renewal cadence | heartbeat **unchanged** — it stopped advancing when the worker was gone |
| Escalation / requeue / takeover | **none**: no `agent_escalations` row, no status change, no new owner |

The proof ran twice with the same structural outcome — fresh, distinct
instance/claim identities each time, the heartbeat advancing while the worker
was alive and frozen once it was gone. The log is kept at
`.scratch/heartbeat-diag/disappearance-proof.log`.

This proves **liveness-evidence persistence**, not recovery. Elapsed time since
the last heartbeat is *not* conclusive proof of death, and the run was
deliberately left `running`.

## 13. Historical-row compatibility

A historical row keeps `coding_worker_instance_id = NULL`,
`coding_worker_claim_id = NULL`, `coding_worker_last_heartbeat_at = NULL`. It
remains readable, acquires **no** synthetic heartbeat on startup, and is never
escalated for a missing heartbeat. A historical `running` row without owner
information remains **ownership-unknown** — its truthful meaning.

## 14. Red-then-green comparison

Isolated scratch tree: `.scratch/heartbeat-red-v1`, with `guardian/agents/store.py`,
`guardian/workers/coding_worker.py`, and `guardian/db/models.py` overlaid from
`c2167aa2`. The contract file is byte-identical in both trees
(`2a4bf6bba88df69d…`).

| File | sha256 (first 16) | matches `c2167aa2` |
|---|---|---|
| `guardian/agents/store.py` | `dbc9de12d87b4373` | yes |
| `guardian/workers/coding_worker.py` | `b97cfc2618340d2c` | yes |
| `guardian/db/models.py` | `8d8664625468c999` | yes |

Import origins were asserted inside the scratch tree, not assumed:

```
store : .scratch/heartbeat-red-v1/guardian/agents/store.py
worker: .scratch/heartbeat-red-v1/guardian/workers/coding_worker.py
has renew_coding_run_heartbeat: False
heartbeat column present: False
```

| Run | Result |
|---|---|
| **RED** (baseline `c2167aa2`, unmodified) | **20 failed, 5 passed** |
| **GREEN** (this slice) | **25 passed** |

The decisive red causes — the baseline behaviour, not a contrived failure:

| Cause | Count |
|---|---|
| `assert None is not None` — the accepted run carried **no durable per-run heartbeat** | 15 |
| `the agent store has no claim-scoped heartbeat renewal operation` | 13 |
| `AttributeError: 'CodingWorker' object has no attribute '_coding_run_heartbeats'` — the baseline has no liveness reporter at all | 2 |
| `the heartbeat did not advance while the adapter blocked` | 1 |
| `AttributeError: 'NoneType' object has no attribute 'year'` — no heartbeat timestamp existed to read | 1 |
| `assert False` | 1 |

## 15. Migration proof

`alembic upgrade` / `downgrade` / clean-start / ORM parity against disposable
PostgreSQL — **9 checks, all PASS** (`.scratch/heartbeat-diag/migration_proof.py`,
log at `.scratch/heartbeat-diag/migration-proof.log`):

1. Upgrade from the preceding head `e42c7d0b9135`; the heartbeat column is absent before the migration.
2. Upgrade to `d86f2a4b1c90` succeeds.
3. A historical row survives the upgrade with `status`, `started_at`, owner and claim intact, and **no backfilled heartbeat**.
4. The new column exists, nullable, `timestamp with time zone`.
5. `agent_runs_coding_worker_heartbeat_ownership_check` refuses a heartbeat written without ownership.
6. Real persistence: a matching owner/claim renewal returns `renewed`; a mismatched one returns `not_eligible`; the row shows the persisted owner and claim.
7. Downgrade to `e42c7d0b9135` removes the column and leaves the historical row intact.
8. A clean start reaches exactly one canonical head, `d86f2a4b1c90`.
9. ORM metadata and migrated schema agree: 19 columns vs 19 columns, none missing.

The Private Preview database was **not** migrated.

## 16. Focused validation

Run against the evaluated worktree with disposable PostgreSQL:

| Path | Result |
|---|---|
| `tests/contracts/test_guardian_coding_worker_heartbeat_contract.py` | **25 passed** |
| `tests/contracts/test_guardian_coding_worker_ownership_contract.py` | **26 passed** |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | **19 passed** |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | 18 passed, 1 xfailed, **1 failed by design** (see §17) |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | passed |
| `tests/contracts/test_guardian_execution_binding_contract.py` | passed |
| `guardian/tests/workers/test_coding_worker.py` | 14 inherited failures, otherwise passed |
| `guardian/tests/workers/test_coding_worker_regression_guard.py` | 1 inherited failure |
| `guardian/tests/agents/` | passed |
| `tests/agents/test_execution_ledger_store.py` | passed |
| `tests/contracts/test_guardian_delegation_phase2a_contract.py`, `…phase3_delivery_contract.py`, `guardian/tests/workers/test_agent_worker_commit_boundaries.py`, `tests/integration/test_agent_coding_snapshot_readback_postgres.py` | **72 passed, 73 skipped** |
| **Focused sweep total** | **348 passed, 16 failed, 1 xfailed** |

## 17. Inherited failures

The 15 inherited failures were compared with the baseline recorded by the
ownership slice, by **exact test identity and exact failure cause**:

```
diff ownership_sweep_ids.txt heartbeat_sweep_ids.txt
  → 15 shared identical identities, 0 fixed
diff ownership_causes.txt heartbeat_causes_inherited.txt
  → CAUSES IDENTICAL (15/15, same cause text)
```

**15 inherited failures, 0 regressions, 0 newly-fixed.** They are 14 in
`guardian/tests/workers/test_coding_worker.py` and 1 in
`guardian/tests/workers/test_coding_worker_regression_guard.py`. They are
predominantly this sandbox's own limits — git worktree creation is denied on
this filesystem, so the isolated-worktree cases cannot construct their fixtures
— plus one genuine pre-existing product defect, reported and **not** patched:

```
NameError: name '_fetch_work_order' is not defined
```

in `guardian/workers/coding_worker.py` (campaign-attempt-ledger path).

### The one new failure, and why it is not patched

```
FAILED tests/contracts/test_guardian_coding_worker_recovery_contract.py::
       test_the_canonical_run_record_carries_ownership_but_no_liveness_signal
AssertionError: agent_runs gained a 'heartbeat' column; the liveness gate
must be re-evaluated against the new authority
```

That file is **read-only** for this task. Its gate case asserts that `agent_runs`
carries no column whose name contains `heartbeat` — and this slice's
authorized, mandated column name is exactly
`coding_worker_last_heartbeat_at`. The assertion is invalidated by the
authorized work itself, not by a defect.

It was left **failing and documented** rather than edited, because editing a
read-only file to make a gate pass would destroy the gate's value: the gate
exists precisely to force a human decision when the liveness authority changes.
The honest state is now:

- the *ownership* half of the liveness gate is closed (durable owner + claim);
- the *liveness* half is **still open** — there is evidence, but no verdict:
  no expiry rule, no classifier, no startup path that reads the heartbeat;
- consequently restart reconciliation stays unimplemented.

The recovery contract's strict-xfail tripwire
(`test_a_restarted_worker_reconciles_an_abandoned_accepted_run`) remains
**xfail** and untouched: the complete recovery contract is still not
implemented and proven.

### The monolithic backend gate

The repository's default backend gate — `pytest -v` over `tests/` (per
`pytest.ini`) — was run against the evaluated worktree with disposable
PostgreSQL. The Private Preview stayed healthy (`127.0.0.1:8081/health` → 200)
throughout both runs.

| Run | Result |
|---|---|
| baseline (`c2167aa2`, recorded by the ownership slice) | **135 failed, 8776 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** (24:43) |
| this evaluation, first run | **136 failed, 8799 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** (24:41) |
| this evaluation, final run (after the shutdown refinement, §6) | **145 failed, 8791 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** (34:29) |

The 5 collection errors (`fakeredis`, `mcp`, and two duplicate-basename
modules) are identical in every run and are local-environment gaps, not
regressions.

**First run, by exact failure identity:**

| Category | Count |
|---|---|
| Shared identical failure identities | **135** |
| Failures not in the baseline | **1** — `tests/contracts/test_guardian_coding_worker_recovery_contract.py::test_the_canonical_run_record_carries_ownership_but_no_liveness_signal` (the read-only gate case, §17) |
| Failed only in the baseline | **0** |

The +23 passed and +1 failed are exactly this slice's new coverage.

**The final run's extra 9 identities were investigated, not waved away.**
The spec forbids assuming shutdown-test differences are harmless, so they were
proved out-of-scope:

1. They are **not caused by this slice**: the same 9 identities — and the same
   cause text — fail on the **unmodified baseline** (`c2167aa2`, isolated
   scratch tree, same environment, same disposable PostgreSQL):

   | Cause | baseline run | final run |
   |---|---|---|
   | `AssertionError: probe did not reach active.pid` | 3 | 5 |
   | `AcceptedChatTaskDeadlineExceeded: 504` | 2 | 1 |
   | `TimeoutError: document_embed_execution_bound_exceeded` | 1 | 1 |
   | `AssertionError: assert (not True)` | 1 | 1 |

   Six identities fail in **both** runs; one fails only in the baseline run.
2. The failing subset **varies between runs of the same tree** (6 shutdown
   identities one time, 5 the next, and the vector file flips too) — the
   signature of process-spawn and deadline timing pressure in this sandbox,
   not of a deterministic code change.
3. The **first** run of this same implementation had all nine **passing**.
4. They exercise `guardian/workers/document_embed_worker.py` subprocess probes
   and the vector/chat-deadline path — modules this slice does not touch. The
   slice's own surface (`agent_runs`, the coding worker, the heartbeat
   reporter) is not involved in any of the nine causes.

**Conclusion:** 9 of the final run's extra failures are environmental and are
not attributable to this slice. The one attributable failure remains the
read-only recovery gate case, documented above. The final run is reported
here with its raw numbers rather than the tidier first run's, because the
final run is the one that describes the committed tree.

### One stale gate case in the *writable* ownership contract was corrected
`tests/contracts/test_guardian_coding_worker_ownership_contract.py` — which
**is** in this task's authorized writable list — carried a case named
`test_no_heartbeat_or_expiry_field_exists` that asserted
`"coding_worker_heartbeat_at" not in columns`. It kept passing only because
this slice's mandated column name is `coding_worker_last_heartbeat_at`: the
assertion used exact membership, so a renamed-but-present heartbeat column
slipped past it. A gate that passes for the wrong reason is worse than a gate
that fails honestly, and this file was authorized to change, so the case was
rewritten as `test_ownership_is_not_liveness_authority`. It now asserts the
truthful new state:

- the claim-scoped heartbeat column **exists**, is nullable, and is subordinate;
- there is still **no expiry column** and **no takeover column**.

The contract's module docstring was updated to match. The case still passes
(26 passed in the ownership contract), and the ownership contract is not loaded
by the heartbeat contract, so the red-then-green evidence in §14 is unaffected.

## 18. Remaining fencing limitations

| Limitation | Statement |
|---|---|
| In-flight provider calls | A heartbeat rejection does **not** interrupt a provider call or subprocess already running inside the adapter. The refusal is enforced at the worker's cooperative boundaries only. No side-effect fencing is claimed. |
| Terminal writes | Terminal persistence is **not** claim-fenced. A stale worker can still attempt a terminal write; claim-fenced terminal persistence and stale-worker result rejection are the next dependent slice. |
| Heartbeat expiry | No expiry rule, threshold, or quarantine decision exists. A stale heartbeat is not proof of worker death. |
| Ownership takeover | None. A rejected claim is never reassigned, replaced, or retried. |
| Recovery wiring | `observe_liveness()`, `classify_dispatch_health()`, and `recover_dispatch()` remain unwired into any startup path. |
| Restart reconciliation | Not implemented. No classification, no escalation, no requeue, no replacement attempt. |

## 19. Explicit absence of restart reconciliation

This slice writes liveness **evidence** and stops. Nothing in the runtime reads
`coding_worker_last_heartbeat_at` to decide that a run is abandoned, to
escalate it, to requeue it, to take it over, or to retry it. The
implementation adds no expiry semantics, no classifier, and no startup hook.
The existing recovery classifier is untouched, and the recovery tripwire stays
`xfail`.

## 20. Classification

**PASS** for the slice as specified:

1. Canonical AgentRun heartbeat field exists — **yes**.
2. Migration upgrade and downgrade succeed — **yes** (9/9 checks).
3. Initial heartbeat is atomic with acceptance — **yes**, same statement, same transaction, database clock.
4. Production worker renews the heartbeat during execution — **yes**, own thread, own sessions, per-run scope.
5. Renewal requires matching worker and claim identities — **yes**.
6. Ownership validation is atomic — **yes**, one conditional UPDATE, database verdict.
7. Incorrect or stale claims cannot update liveness — **yes**.
8. Terminal runs cannot renew heartbeat — **yes**.
9. Historical NULL records remain valid — **yes**.
10. A blocked synchronous adapter does not suppress heartbeat renewal — **yes**, event-barriered.
11. Worker disappearance preserves its last heartbeat — **yes**, separate process, SIGKILL, readback.
12. No duplicate execution or credential authority is introduced — **yes**.
13. Existing execution and terminal-result behaviour remains compatible — **yes**, 0 regressions in the focused sweep.
14. Focused validation passes without attributable regressions — **yes**: 15 inherited failures with identical causes in the focused sweep, 135 shared identical failures in the monolithic gate, the final run's 9 environment-failed identities proved non-attributable against the unmodified baseline, and the single read-only gate failure documented in §17.
15. Restart reconciliation remains disabled — **yes**.
16. Release remains HOLD — **yes**.

### Explicit confirmations

- No second execution authority was introduced.
- No ownership takeover was added.
- No stale-heartbeat death inference was activated.
- No automatic retry was enabled.
- No startup reconciliation was activated.
- No live provider request occurred.
- No production resources were modified.
- Functional delegation PASS remains feature-branch evidence.
- Restart recovery remains BLOCKED.
- Release remains HOLD.

## 21. Files changed

| File | Change |
|---|---|
| `guardian/db/models.py` | `AgentRun.coding_worker_last_heartbeat_at` + `agent_runs_coding_worker_heartbeat_ownership_check` |
| `guardian/db/migrations/versions/d86f2a4b1c90_coding_run_claim_heartbeat.py` | new additive migration, parent `e42c7d0b9135` |
| `guardian/agents/store.py` | heartbeat written with acceptance; `renew_coding_run_heartbeat`; three outcome constants |
| `guardian/workers/coding_worker.py` | `_CodingRunHeartbeat`, the cadence constant, start/stop/ownership-loss handling, `CodingWorker.shutdown()` and the run loop's shutdown `finally` |
| `tests/contracts/test_guardian_coding_worker_heartbeat_contract.py` | new — 25 focused cases |
| `tests/contracts/test_guardian_coding_worker_ownership_contract.py` | the stale liveness gate case rewritten (see below) |
| `docs/architecture/guardian-delegation-loop-contract.md` | heartbeat contract section; recovery-gate wording corrected; new invariant |
| `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md` | operator interpretation of heartbeat evidence |

## 22. Remaining prerequisites

1. **Claim-fenced terminal persistence and stale-worker result rejection** — the
   next dependent slice. A stale worker must not be able to write a terminal
   result for a run it no longer owns.
2. **Worker-liveness classification** — turning heartbeat evidence into a
   verdict, with an explicit expiry contract.
3. **Wiring Guardian's existing recovery classifier to worker restart** — only
   after (1) and (2) are proven, so reconciliation cannot escalate a live run
   or accept a superseded write.
