# Guardian Coding Run — Claim-Fenced Terminal Results

**Base commit:** `0db31d7057d2bc5a1274b442d5c99f7793b0373f`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-25
**Final classification:** **PASS** (release remains **HOLD**)

Durable ownership proved *who* holds a run. The claim-scoped heartbeat proved
that the holder was **still reporting**. Neither proved that only the holder
may **finish** the run. This slice closes that gap: the terminal decision is
now an atomic, claim-fenced database update, and the canonical result writes
that belong to it commit with it.

**This slice is not recovery.** It introduces no worker-death classifier, no
expiry authorization, no owner takeover, no automatic retry, and no restart
reconciliation. A rejected terminalization produces *evidence of refusal*, not a
disposition: only an operator may decide what happens to an unresolved run.

---

## 1. Evaluated commit

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Base HEAD | `0db31d7057d2bc5a1274b442d5c99f7793b0373f` |
| Working tree at the base commit | clean (tracked) |
| `alembic heads` | **exactly one** head: `d86f2a4b1c90` — unchanged |
| New migration | **none**. No schema change in this slice |
| Provider | **none** — no provider request, no live DeepSeek canary |
| Production resources | **none touched** — every database used was disposable and local |

## 2. Effective terminal-persistence call graph

`AgentStore` carried **two** `store_coding_result` definitions. The second
shadowed the first, and the second is the effective implementation:

| Definition | Signature | Effective? |
|---|---|---|
| first | `store_coding_result(*, run_id, coding_task_id, attempt_id, result_json)` — a legacy in-memory/artifact-only overload | **no** — shadowed |
| second | `store_coding_result(*, run_id, coding_task_id, attempt_id, campaign_id, …, require_human_review_before_merge)` — the full implementation | **yes** |

No caller used the shadowed overload's `result_json` signature, so the shadowed
copy was unreachable. It was **removed** in this slice: it was a trap for the
next editor of this file, and a change to it would have silently done nothing.

The effective terminal-write inventory, before this slice:

| Operation | Role |
|---|---|
| `AgentStore.store_coding_result()` (second definition) | the result path: delivery, terminal status, artifact, campaign evidence |
| `AgentStore.update_run_status()` | the **unguarded** terminal status write |
| `AgentStore._deliver_guardian_delegation_result_to_thread()` | Guardian source-thread delivery + intent delivery state |
| `AgentStore._inject_coding_result_into_thread()` | non-Guardian source-thread delivery |
| `AgentStore.add_artifact()` | the coding-result artifact |
| `AgentStore.list_artifacts()` | the artifact-existence check |
| `AgentStore._record_campaign_execution_attempt()` | campaign evidence (best effort, separate store) |
| `CodingWorker._persist_and_emit_terminal()` | the success/failure terminal path |
| `CodingWorker._emit_terminal()` | publishes `task.completed` / `task.failed` |
| `CodingWorker._emit_failure()` | writes `failed` **unguarded**, publishes `task.failed` |
| `CodingWorker._emit_cancelled()` | writes `canceled` **unguarded**, publishes `task.cancelled` |
| `CodingWorker._emit_worktree_failure()` | worktree-isolation failure (post-acceptance) |
| `CodingWorker._emit_worktree_lease_failure()` | worktree-lease failure (post-acceptance) |

## 3. The previously unsafe ordering

Before this slice, `store_coding_result()` wrote in this order:

1. **the source-thread result message** — committed on its own session,
2. **the run's terminal status** — through `update_run_status()`, an unguarded
   write with no worker/claim condition,
3. **the coding-result artifact** — committed on its own session,
4. the terminal task event, published by the worker afterwards.

Two defects follow directly from that ordering.

**A result-side effect could outlive the terminal decision.** The message was
committed before the terminal status was even attempted, and the artifact was
committed on a third session. If the artifact write failed, the delivered
source-thread result stayed behind for a run that never reached a terminal
outcome.

**A stale worker could finish a run it no longer owned.** `update_run_status()`
had no worker/claim condition, so any worker that still held the run id could
move a `running` row to `failed` — and `_emit_failure()` published
`task.failed` regardless of whether the write had any effect. A worker whose
claim had been superseded could deliver a message, create an artifact, and
publish a terminal event.

Both are demonstrated as *behavioural* reds in §15.

## 4. The canonical terminal claim contract

`AgentStore.claim_coding_run_terminal()` performs one conditional update:

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

The worker instance and claim come from the durable acceptance. They are never
taken from model output, a queue payload, a tool result, or an HTTP request.
The database — not an application-level check performed earlier — decides who
may write the terminal status.

The deployment lineage is checked in the same transaction: a deployment whose
persisted spec contradicts the run's own lineage (`thread_id`,
`account_origin_user_id`) is not an authority for finalizing that run.

| Outcome | Meaning |
|---|---|
| `terminal_accepted` | the claim still owned the run; the terminal transition was written |
| `terminal_rejected` | the claim did not match the run, or the run was disposed of by another authority (`escalated`) |
| `terminal_already_terminal` | the run already carried a terminal status; nothing was rewritten |
| `terminal_unavailable` | persistence could not be reached; the caller fails closed |

An escalated run is classified as *rejected*, not *already terminal*: an
escalation is another authority's disposition, and the late worker's completion
is refused rather than treated as a redundant duplicate.

## 5. The database transaction boundary

`AgentStore.finalize_claimed_coding_result()` is the fenced terminalization:

```
BEGIN
  stage the source-thread result message      (shared session)
  stage the Guardian delivery state           (shared session)
  stage the coding-result artifact            (shared session)
  claim_coding_run_terminal(...)              (the conditional update)
  if accepted:  COMMIT                        (one durable outcome)
  if rejected:  ROLLBACK                      (nothing was written)
COMMIT/ROLLBACK
```

The established delivery helpers keep their own commit points, so a shared
session is handed to them wrapped in a small view whose `commit()` **flushes**
into the caller's transaction instead of committing it. The writes become
visible to the owning transaction and their generated keys become available,
but they are not committed until the terminal decision is accepted. The
established delivery contract — which patches one of those commit points
directly — keeps working unchanged.

The campaign and work-order evidence are **not** part of the transaction: they
are best-effort side stores with their own transactions, and they are recorded
*after* the accepted commit. A rejected terminalization therefore leaves no
execution attempt behind.

## 6. Worker and claim identity validation

The worker records the claim it received at durable acceptance
(`self._coding_run_claims[run_id]`) and drops it when the run reaches a
terminal state. Every post-acceptance terminal path goes through it:

| Path | Fenced? |
|---|---|
| normal adapter success (`_persist_and_emit_terminal`) | yes |
| adapter failure (`_emit_failure`) | yes |
| validation failure | yes (same terminal funnel) |
| mutation-scope failure | yes (same terminal funnel) |
| worktree failure after acceptance (`_emit_worktree_failure`) | yes |
| credential-lease failure after acceptance (`_emit_worktree_lease_failure`) | yes |
| cancellation after acceptance (`_emit_cancelled`) | yes |
| result-delivery failure | yes (same terminal funnel) |
| unexpected processing exceptions | yes (via `_emit_failure`) |
| pre-acceptance validation failures | **no** — they keep their existing authorized behaviour |

## 7. Artifact-persistence behaviour

The coding-result artifact is staged on the same session as the terminal
decision. The artifact-existence check reads on that same session, so it sees
the transaction it belongs to. A duplicate finalization finds the existing
artifact and creates no second one.

## 8. Source-thread delivery behaviour

The delivery key, the identity checks, the sanitization, the deferred-delivery
behaviour, the degraded-delivery classification and the visibility vocabulary
are unchanged. What changed is *when* the delivery may become durable: it
commits with the terminal decision that authorised it, and it does not commit
at all when the claim was refused.

A claim rejection is different from an authorized execution whose delivery
failed. The first produces **nothing** — no status, no artifact, no message,
no event. The second produces a terminal run with a degraded delivery, exactly
as before.

## 9. Terminal-event publication ordering

`task.completed`, `task.failed` and `task.cancelled` are published only after
an **accepted** terminal decision. A terminal event is never published merely
because an adapter returned successfully. A rejected terminalization publishes
the canonical **non-terminal** `task.event` with
`error_code = 'EXECUTION_OWNERSHIP_LOST'` instead — the existing local refusal
reason, unchanged.

Database persistence remains authoritative. The Redis event publication is a
separate transport operation; no cross-system atomicity is claimed, and a
missing event never invalidates a committed result. No already-persisted
terminal event is rewritten to hide disagreement.

## 10. Stale-claim rejection

Every rejected terminalization leaves the canonical row untouched and writes
nothing else:

| Rejected because | Terminal status | Artifact | Source-thread message | Terminal event | Execution attempt |
|---|---|---|---|---|---|
| wrong worker instance | none | none | none | none | none |
| wrong claim | none | none | none | none | none |
| absent claim | none | none | none | none | none |
| absent worker instance | none | none | none | none | none |
| missing run | none | none | none | none | none |
| already succeeded / failed / canceled | unchanged | none | none | none | none |
| escalated | unchanged (`escalated`) | none | none | none | none |
| contradictory deployment lineage | none | none | none | none | none |
| persistence unavailable | none | none | none | none | none |

No replacement credential lease and no new execution attempt are produced, and
a rejected worker selects no other credential and redispatches nothing.

## 11. Escalation versus terminal race

`test_an_escalated_run_is_not_overwritten_by_a_late_worker`: Worker A accepts
the run, the run is disposed of authoritatively (`escalated`), and Worker A
then returns success and attempts terminal persistence.

| Expectation | Result |
|---|---|
| the run remains `escalated` | yes |
| the escalation evidence remains intact | yes |
| no coding-result artifact by the stale worker | yes |
| no source-thread result by the stale worker | yes |
| no `task.completed` by the stale worker | yes |
| Worker A receives no retry authority | yes |

## 12. Concurrent terminalization

Two independent sessions, real PostgreSQL, `threading.Barrier` — no timing
guesses.

| Scenario | Result |
|---|---|
| two terminal calls with the same valid claim | one `terminal_accepted`, one `terminal_already_terminal`; one artifact, one message, one terminal status |
| a stale claim racing the owner | the owner wins; the stale claim is rejected or observes the terminal run; no second artifact |
| a valid terminal call racing a terminal-state transition | the conditional update resolves it; the run is never reopened |
| a valid terminal call racing an escalation | the escalated run is not overwritten |
| duplicate result delivery after a successful terminalization | the existing receipt is observed; no second artifact, no second message, no refreshed `ended_at` |

## 13. Heartbeat shutdown interaction

- A valid claim can terminalize while its heartbeat reporter is active: the
  reporter renews on its own cadence, and the terminal decision is independent
  of it.
- The reporter cannot reopen a terminal status: renewal requires the run to
  still be `running`.
- Normal terminalization stops renewal cleanly (`_stop_coding_run_liveness`).
- An expected terminal transition is not misreported as hostile ownership loss:
  the accepted terminalization publishes its terminal event, not the
  ownership-lost one.
- A rejected terminal claim stops further terminal publication.
- No reporter survives execution shutdown: `CodingWorker.shutdown()` stops and
  joins every reporter, and the worker's poll loop keeps its `finally` safety
  net.
- The original worker and claim identities remain immutable.

## 14. Transaction rollback evidence

| Injected failure | Result |
|---|---|
| before the terminal claim | nothing committed |
| during the conditional terminal update | the update fails; nothing committed |
| during artifact insertion | the whole transaction rolls back: the run stays `running`, no artifact, **no source-thread message** |
| during result-message insertion | the whole transaction rolls back |
| during delivery-state persistence | the whole transaction rolls back |
| immediately before commit | nothing committed |
| after a successful commit but before event publication | the durable terminal result remains authoritative even if the event is missing |

`test_a_failed_result_write_leaves_no_source_thread_result` is the decisive
case: on the baseline a delivered message survived a failed terminal write
(`assert 1 == 0`); with the fence, nothing survives.

## 15. Red-then-green comparison

Isolated scratch tree: `.scratch/terminal-fence-red-v1`, built from
`git archive 0db31d705` (only `.claude/commands` is excluded — the desktop
permission gate blocks those three paths). The contract file was copied in
byte-identically.

| File | sha256 (first 16) | matches `0db31d705` |
|---|---|---|
| `guardian/agents/store.py` | `580fcc2182911e00` | yes |
| `guardian/workers/coding_worker.py` | `641b41925069dae6` | yes |

Import origins were asserted inside the scratch tree:

```
store : .scratch/terminal-fence-red-v1/guardian/agents/store.py
worker: .scratch/terminal-fence-red-v1/guardian/workers/coding_worker.py
has finalize_claimed_coding_result: False
```

| Run | Result |
|---|---|
| **RED** (baseline `0db31d705`, unmodified) | **22 failed, 1 passed** |
| **GREEN** (this slice) | **23 passed** |

Red causes:

| Cause | Count | Kind |
|---|---|---|
| `AttributeError: 'AgentStore' object has no attribute 'finalize_claimed_coding_result'` | 18 | the capability does not exist |
| `AttributeError: 'CodingWorker' object has no attribute '_coding_run_claims'` | 2 | the capability does not exist |
| **`AssertionError: assert 'succeeded' == 'running'`** | 1 | **behavioural** |
| **`AssertionError: assert 1 == 0`** | 1 | **behavioural** |

The two behavioural reds are the two defects of §3, observed through the
worker path so that they hold on both trees:

- **A — an invalidated claim produced a terminal outcome.** The worker
  accepted the run, the canonical owner changed while it was executing, and it
  returned success. The baseline finalized the run (`succeeded`); the repaired
  runtime writes no terminal status, no artifact, no source-thread result and
  no terminal event.
- **B — a result-side effect outlived a failed terminal write.** The baseline
  delivered the source-thread result first and left it behind when the
  canonical result write failed (`assert 1 == 0`); the repaired runtime rolls
  the whole terminal decision back.

## 16. Focused validation

| Path | Result |
|---|---|
| `tests/contracts/test_guardian_coding_worker_terminal_fencing_contract.py` | **23 passed** |
| `tests/contracts/test_guardian_coding_worker_heartbeat_contract.py` | **25 passed** |
| `tests/contracts/test_guardian_coding_worker_ownership_contract.py` | **26 passed** |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | **19 passed** |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | 18 passed, 1 xfailed, **1 failed by design** (see §17) |
| `tests/contracts/test_guardian_delegation_phase2a_contract.py` | passed |
| `tests/contracts/test_guardian_delegation_phase3_delivery_contract.py` | passed |
| `tests/contracts/test_guardian_delegation_approval_cancel_contract.py` | passed |
| `guardian/tests/workers/test_coding_worker.py` | 14 inherited failures, otherwise passed |
| `guardian/tests/workers/test_coding_worker_regression_guard.py` | 1 inherited failure |
| `guardian/tests/agents/` | passed |
| `tests/agents/test_execution_ledger_store.py` | passed |
| **Focused sweep total** | **402 passed, 16 failed, 1 xfailed** |

### The monolithic backend gate

The repository's default backend gate — `pytest -v` over `tests/` (per
`pytest.ini`) — was run against the evaluated tree with disposable PostgreSQL.
The Private Preview stayed healthy (`127.0.0.1:8081/health` → 200) throughout.

| Run | Result |
|---|---|
| baseline (`0db31d705`, recorded by the heartbeat slice) | **145 failed, 8791 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** |
| this evaluation, on the final tree | **136 failed, 8823 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** (22:48) |

Compared by **exact failure identity**:

| Category | Count |
|---|---|
| Shared identical failure identities | **136** |
| Failures not in the baseline | **0** |
| Failed only in the baseline | 9 — the load-sensitive `tests/workers/test_document_worker_shutdown.py` signal cases and `tests/vector/test_vector_physical_deadline.py::test_chroma_bound_search_preserves_results_and_deferred_parent_handle`, which the heartbeat slice already proved non-attributable by running the unmodified baseline in the same environment with the same causes |

The +32 passed and −9 failed are the baseline's own environment flakes not
reproducing in this run. The 5 collection errors (`fakeredis`, `mcp`, and two
duplicate-basename modules) are identical in every run and are local-environment
gaps, not regressions.

## 17. Inherited failures and the stale-test discrepancy

The 15 inherited failures are identical to the baseline recorded by the
heartbeat slice — by exact test identity:

```
diff heartbeat_sweep_ids.txt final_sweep_ids.txt
  → identical failure identities, 0 fixed, 0 introduced
```

The final focused sweep on the evaluated tree is **402 passed, 16 failed,
1 xfailed**, and the 16 failure identities are byte-identical to the baseline's
15 inherited failures plus the one documented recovery gate case below.

They are 14 in `guardian/tests/workers/test_coding_worker.py` and 1 in
`guardian/tests/workers/test_coding_worker_regression_guard.py`. They are
predominantly this sandbox's own limits — git worktree creation is denied on
this filesystem, so the isolated-worktree cases cannot construct their
fixtures — plus one genuine pre-existing product defect, reported and **not**
patched:

```
NameError: name '_fetch_work_order' is not defined
```

in `guardian/workers/coding_worker.py` (campaign-attempt-ledger path).

### The known obsolete recovery assertion

`tests/contracts/test_guardian_coding_worker_recovery_contract.py` is
**read-only** in this task. Its gate case

```
test_the_canonical_run_record_carries_ownership_but_no_liveness_signal
```

asserts that `agent_runs` carries no column whose name contains `heartbeat`.
That assertion predates the heartbeat column implemented by the previous slice
and is invalidated by it. It was **not** edited to manufacture a green suite.
It is recorded here as an identified pre-existing test discrepancy, separate
from any terminal-fencing regression. The strict-xfail restart-reconciliation
tripwire (`test_a_restarted_worker_reconciles_an_abandoned_accepted_run`)
remains **xfail** and untouched: the complete recovery contract is still not
implemented and proven.

## 18. External side-effect limitations

A database terminal fence protects canonical Codexify state. It does **not**
terminate:

- an already-running Pi invocation,
- a provider request,
- a subprocess,
- an ongoing filesystem mutation,
- an external network operation.

No provider-enforced sandbox containment and no complete side-effect fencing is
claimed. The existing worktree and mutation guard remain independent
boundaries, and a future recovery mechanism must still treat uncertain
external side effects conservatively. A stale worker may still have mutated a
worktree before its terminalization was refused; the operator has to inspect
and clean that up by hand.

## 19. Explicit absence of restart reconciliation

This slice writes a terminal *authority*, not a recovery policy. Nothing in the
runtime reads a heartbeat, an expiry, or a stale worker to decide that a run is
abandoned, to escalate it, to requeue it, to take it over, or to retry it.
`observe_liveness()`, `classify_dispatch_health()` and `recover_dispatch()`
remain unwired into any startup path. The implementation adds no expiry
semantics, no classifier, and no startup hook.

## 20. Classification

**PASS** for the slice as specified:

1. Accepted Guardian terminalization requires the original worker and claim — **yes**.
2. Terminal authorization is enforced atomically in PostgreSQL — **yes**, one conditional update.
3. Rejected claims cannot persist terminal state — **yes**.
4. Rejected claims cannot persist coding-result artifacts — **yes**.
5. Rejected claims cannot deliver source-thread result messages — **yes**.
6. Rejected claims cannot publish authoritative terminal task events — **yes**.
7. Result persistence does not outrun the terminal authorization decision — **yes**, one transaction.
8. Competing terminal decisions resolve to one canonical outcome — **yes**.
9. Escalated runs cannot be overwritten by late worker success — **yes**.
10. Existing source-thread idempotency remains intact — **yes**.
11. Existing legacy execution behaviour remains compatible — **yes**, the unclaimed path is unchanged.
12. Heartbeat helpers terminate correctly around terminalization — **yes**.
13. PostgreSQL failures fail closed — **yes**.
14. Red-then-green evidence exists — **yes**, with two behavioural reds.
15. No new migration, retry, or credential authority is introduced — **yes**.
16. Release status remains HOLD — **yes**.

### Explicit confirmations

- No second execution authority was introduced.
- No heartbeat-expiry death inference was activated.
- No owner takeover was implemented.
- No automatic retry was enabled.
- No restart reconciliation was activated.
- No real provider call occurred.
- No production resources were modified.
- No provider-enforced sandbox guarantee was claimed.
- Functional delegation PASS remains feature-branch evidence.
- Restart recovery remains BLOCKED.
- Release remains HOLD.

## 21. Files changed

| File | Change |
|---|---|
| `guardian/agents/store.py` | `claim_coding_run_terminal`, `finalize_claimed_run_status`, `finalize_claimed_coding_result`, the shared-transaction session view, session-aware delivery/artifact helpers, removal of the shadowed `store_coding_result` overload |
| `guardian/workers/coding_worker.py` | the ownership-claim registry, claim-fenced terminal paths, terminal-event suppression, ownership-loss reporting on a refused terminalization |
| `tests/contracts/test_guardian_coding_worker_terminal_fencing_contract.py` | new — 23 focused cases |
| `docs/architecture/guardian-delegation-loop-contract.md` | the claim-fenced terminalization section, the new invariant |
| `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md` | operator reading of a claim-fenced terminal result |
| `docs/architecture/proofs/runtime/2026-10-25-guardian-coding-terminal-fencing-proof.md` | this receipt |

## 22. Remaining prerequisites

1. **Worker-liveness classification** — turning heartbeat evidence into a
   verdict, with an explicit expiry contract. Until then, a stale heartbeat
   remains evidence of uncertainty, not proof of death.
2. **Wiring Guardian's existing recovery classifier to worker restart** — only
   after the classification exists, so reconciliation cannot escalate a live
   run or accept a superseded write.
3. **External side-effect handling** — a conservative account of the
   filesystem and provider effects a fenced-out worker may already have
   produced.
