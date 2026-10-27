# Guardian Coding Worker — Read-Only Startup Review

**Date:** 2026-10-26
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Base commit:** `80d46f86caec66a239cb4e04daac5874bba4b74e`
**Classification:** **PASS** — with release status unchanged at **HOLD**

This receipt records the **read-only startup review** the coding worker now
performs on startup: one bounded observation of the unresolved Guardian coding
runs, classified with the liveness classifier this campaign already proved,
and **nothing else**.

It does not modify, weaken, or supersede the previous slices. The liveness
classification (`ab26381ba`), the atomic operator-authorized quarantine
(`158ea893`) and the operator HTTP route (`80d46f86c`) are unchanged. This
slice adds the missing observation point — and deliberately stops there.

---

## 1. Evaluated branch and commit

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Base HEAD | `80d46f86caec66a239cb4e04daac5874bba4b74e` |
| Tracked working tree at start | clean |
| `git merge-base --is-ancestor 80d46f86c HEAD` | true |
| `alembic heads` | `d86f2a4b1c90 (head)` — single head, unchanged |
| Import origin (swept) | `/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/guardian/__init__.py` |

Source hashes (SHA-256), evaluated tree:

| File | Hash |
|---|---|
| `guardian/agents/store.py` | `a6a6bcfa5d58e293ac6de558556a37fec4a5e941a5c8fae43f2c6c71a3fd2338` |
| `guardian/workers/coding_worker.py` | `e4118ead01b5742220b1bf4b67d8ff649fd9a4d4006a8e252891d9a45c83599c` |
| `tests/contracts/test_guardian_coding_worker_restart_review_contract.py` | `01eb0ee1902521a2448df705b99887d2dae8cbf4f14d677a18c23ff04a9c4f25` |
| `guardian/tests/workers/test_coding_worker.py` | `ee8c52fde6652d0ad8570725115e7555f31d7755957d9b18b9303443a2cab888` |
| `docs/architecture/guardian-delegation-loop-contract.md` | `10c2ba2df77d2cddc5c7f3a092417d8c257f585be31987d33cae5ce78f006190` |
| `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md` | `0158a1625c1b65b9f6f500c86ced1fb1ee19f789e0e7f9d33e560f75757431db` |

Baseline (`80d46f86c`) hashes, for the red/green comparison:

| File | Baseline hash |
|---|---|
| `guardian/agents/store.py` | `e8b6c14e71e91b2eabe151c7e3c8a6c97a62d8d69bcd50b4d4a56aa45189c44b` |
| `guardian/workers/coding_worker.py` | `a48ea25c4dd4273559638260a6b0fc67ab6465e12aac3aca5fcd006dd19faabc` |
| `guardian/tests/workers/test_coding_worker.py` | `c170108c6c3cfb99d2eb6034c8f8c901027b7b58f822eeae0a451b2841712bdf` |

## 2. Startup integration point

The coding worker's process entrypoint is `python -m guardian.workers.coding_worker`
(`docker-compose.runtime.yml:361`), which calls `run_worker_loop()`:

```python
def run_worker_loop() -> None:
    logger.info("[coding-worker] starting coding worker loop")
    _initialize_worker()          # canonical PostgreSQL access is established here
    worker = CodingWorker()
    review = worker.review_unresolved_coding_runs()   # <-- the read-only review
    _log_coding_run_startup_review(review)
    if review.review_error_code == CODING_RUN_REVIEW_UNAVAILABLE:
        raise RuntimeError(...)
    try:
        while True:
            worker.poll_once()    # <-- destructive queue consumption starts here
```

The review therefore sits **exactly** between the two points the slice
specifies: after canonical database access is established, and before the
first destructive dequeue. It runs **once**. There is no background loop, no
watcher, and no scheduler.

The review requires no Redis dequeue, no credential selection, no worktree, no
adapter registration, no Pi invocation, and no provider access. The contract
case `test_the_startup_review_runs_before_destructive_dequeue` asserts the
ordering directly, by recording `review` then `dequeue` on the real loop.

## 3. Canonical run-selection predicate

```python
AgentRun.status == "running"
AND AgentDeployment.spec_json["guardian_delegation"]["ownership"]
    == "guardian_delegation_intent"
```

The deployment ownership marker is the **persisted Guardian delegation
ownership authority** — the same marker the store reads through
`_guardian_delegation_metadata()` and that the delegation service writes when
it creates the deployment. It is the *deployment authority* that identifies the
population, not a name convention and not a column on `AgentRun`.

An `AgentRun` that merely shares the table with a Guardian coding run is
**not** in the population. The contract proves it with a running run whose
deployment carries no Guardian ownership: it is not inspected
(`test_only_guardian_bound_coding_runs_are_inspected`). The same holds on the
worker's own SQLite-backed test double
(`test_the_startup_review_ignores_a_run_that_is_not_guardian_bound`).

The JSON predicate is a JSON *path* expression, which renders `->` / `->>` on
PostgreSQL and `JSON_EXTRACT` on SQLite. It is deliberately not a `.contains()`
call: on SQLite that degrades to a `LIKE` over the serialized JSON text and
silently fails to match a nested object.

## 4. Read-only database projection

One statement, one row per candidate, carrying exactly the identity and
timing facts the classifier needs:

```
run_id, deployment_id, status, started_at, ended_at,
coding_worker_instance_id, coding_worker_claim_id,
coding_worker_last_heartbeat_at, observed_at
```

This is the same field set the existing canonical liveness snapshot uses, so
the classifier consumes it unchanged. The projection carries **no** credential
material, no secret value, no raw prompt, and no transcript content.

The read is a single statement, so a run's status, ownership identities,
heartbeat, and observation instant come from **one consistent snapshot**.
Mixing timestamps from separately sampled reads could produce a misleading
ordering — for example a heartbeat read before a terminalization that the
status read missed.

## 5. Database observation clock

`observed_at` is `func.now()` — the **database** clock, constant for the
statement. The application host clock is never the authoritative comparison
clock.

`observation_instant` exists as an explicit seam, exactly as it does on the
existing canonical liveness snapshot, so a contract test can pin the
observation instant and exercise the staleness boundary exactly rather than
sleeping across it. Production callers omit it.

## 6. Bounded inventory policy

| Property | Value |
|---|---|
| Row bound | `CODING_RUN_REVIEW_MAX_ROWS = 200` |
| Ordering | `AgentRun.id ASC` — deterministic, and the primary key is the stable keyset |
| Continuation | `after_id` continues the keyset from the last row read |
| Truncation detection | one extra row is read (`limit + 1`), so "the population ended here" is distinguishable from "the population continues past the bound" |
| Memory | bounded: at most `limit + 1` rows are ever materialised |

The cursor is a pagination key, not a persisted ledger. Nothing is written.

## 7. Review completeness handling

The three states are distinguished by `review_complete` together with
`review_error_code`:

| State | `review_complete` | `review_error_code` |
|---|---|---|
| **complete** | `True` | `None` |
| **partial** | `False` | `guardian_coding_run_review_partial` |
| **unavailable** | `False` | `guardian_coding_run_review_unavailable` |

- A **partial** review means the bounded read stopped at its limit and more
  unresolved runs may exist. It is never presented as a complete inventory.
- An **unavailable** review means the canonical store could not be read. It is
  **never** an empty inventory: an unreachable database is not evidence that
  no unresolved run exists. A worker that cannot reach canonical persistence
  cannot durably accept anything, so it **refuses to consume coding tasks**
  rather than dequeue work it could never accept
  (`test_an_unreachable_store_stops_the_worker_before_it_consumes`).

The store's `error_code` is non-`None` only when the read itself failed; a
truncated but successful read reports `complete=False` with no error code.
That keeps the two discriminators independent.

## 8. Fresh-heartbeat observation

A run whose recorded owner renewed its heartbeat within the established
observation horizon (`max(60s, 3 × actual heartbeat cadence)`) is
**recently_observed**.

Meaning: recent owner activity was observed.
**Not**: that a worker process currently exists.

`test_a_fresh_heartbeat_is_classified_conservatively`.

## 9. Stale-heartbeat observation

A run whose recorded owner has not renewed within the horizon is
**stale_uncertain**.

Meaning: the current execution outcome is uncertain.
**Not**: that the worker died, was killed, or lost its work.

`test_a_stale_heartbeat_remains_uncertain` also asserts the classification
used the established horizon.

## 10. Missing-evidence observation

A running run whose ownership or heartbeat evidence is unusable is
**missing_evidence**.

Meaning: there is insufficient evidence for a reliable liveness classification.
**Not**: that the execution never started, and **not** that no side effects
occurred.

`test_historical_missing_ownership_remains_unknown` and
`test_a_missing_heartbeat_remains_unknown` also assert the review **backfills
no identity and manufactures no initial heartbeat**.

A self-contradicting record is reported as **inconsistent** and is never
repaired (`test_an_inconsistent_record_is_reported_and_not_repaired`).

## 11. Active-peer protection

A system may legitimately run several coding workers, and a restarting worker
may meet work still executing on another machine. The review classifies each
run on **its own** evidence and never touches it:

- `test_an_active_peer_worker_remains_untouched` — Worker A's run (stale) and
  Worker B's run (fresh) are classified independently; the peer's run stays
  `running`, keeps its own instance and claim, and gains no escalation.
- `test_a_second_worker_cannot_claim_a_reviewed_run` — reviewing a run does
  not transfer its ownership; the original instance and claim are unchanged.
- `test_multiple_runs_of_one_worker_remain_independent` — two runs of one
  worker are reviewed independently.

## 12. Terminal-run handling

A terminal or escalated run is authoritative and is never a recovery
candidate:

| Case | Contract |
|---|---|
| terminal success | `test_a_terminal_success_is_preserved` |
| terminal failure | `test_a_terminal_failure_is_preserved` |
| canceled execution | `test_a_canceled_execution_is_preserved` |
| escalated execution | `test_an_escalated_execution_is_preserved` |

Each asserts the row is **unchanged**, and the escalated case additionally
asserts the existing escalation is neither duplicated nor replaced.

## 13. Historical-row handling

Historical running rows that predate the ownership and heartbeat columns stay
`missing_evidence`. The review does not backfill an owner, does not
manufacture an initial heartbeat, does not declare historical work lost, and
does not discard those rows from the review: they are counted and reported
like any other candidate.

## 14. Controlled worker interruption

A real, two-process experiment against one disposable PostgreSQL database and
one disposable Redis. No real provider key, no Pi, no live model request.

| Step | What happened |
|---|---|
| 1 | One synthetic Guardian coding delegation was created through the real delegation service; a queued run was persisted. |
| 2 | The task was placed on the real coding queue (`queue_length_after_dispatch: 1`). |
| 3 | **Worker A** started the real `run_worker_loop()`, dequeued the task, validated the execution binding, and **durably accepted** the run. |
| 4 | The claim-scoped heartbeat was persisted: `heartbeat_at: 2026-10-27 02:13:21.115464+00:00`, with `worker_instance_id` and `claim_id` recorded. |
| 5 | Worker A entered a **controlled synthetic adapter boundary** (`worker A reached the adapter boundary: adapter-boundary-reached`). The adapter is the repo's own seam: the credential-lease authority is stubbed exactly as the repo's worker test suite stubs it, and the adapter is a synthetic one that blocks. Everything before it — the dequeue, the binding validation, the durable acceptance, the heartbeat — is the real code path. |
| 6 | The parent terminated Worker A with **SIGKILL**: `worker A terminated: returncode=-9 (-9 is SIGKILL)`. No graceful shutdown ran. |
| 7 | **PostgreSQL and Redis kept running.** |

Canonical state immediately after the SIGKILL:

```json
{
  "status": "running",
  "worker_instance_id": "cwi_24b4803a41ad449487b79f3cab471ae9",
  "claim_id": "cwc_6aebe6d9873041a48957ac4a241a6bce",
  "started_at": "2026-10-27 02:13:21.108669+00:00",
  "ended_at": "None",
  "error": null,
  "heartbeat_at": "2026-10-27 02:13:21.115464+00:00",
  "escalation_count": 0,
  "artifact_count": 0
}
```

The controlled SIGKILL proves termination **in this experiment**. It does not
create a general production worker-death oracle, and nothing in the product
infers death from it.

## 15. Restart review result

**Worker B** started the real worker startup path against the same durable
state, with nothing edited by hand in between. Its own output:

```json
{
  "reviewed_count": 1,
  "recently_observed_count": 1,
  "stale_uncertain_count": 0,
  "missing_evidence_count": 0,
  "inconsistent_count": 0,
  "already_resolved_count": 0,
  "already_escalated_count": 0,
  "review_complete": true,
  "review_error_code": null,
  "run_ids": ["run_313275987ddd4f53"],
  "stale_uncertain_run_ids": []
}
```

The **controlled observation beyond the staleness horizon** — the observation
instant pinned 120 s past the kill, so the boundary is exercised exactly and
no elapsed sleep is relied upon:

```json
{
  "reviewed_count": 1,
  "recently_observed_count": 0,
  "stale_uncertain_count": 1,
  "missing_evidence_count": 0,
  "review_complete": true,
  "review_error_code": null,
  "run_ids": ["run_313275987ddd4f53"],
  "stale_uncertain_run_ids": ["run_313275987ddd4f53"]
}
```

Before the staleness horizon → `recently_observed`. Beyond it →
`stale_uncertain`. Neither changed anything.

## 16. No re-execution evidence

| Check | Result |
|---|---|
| Canonical state unchanged by the restart review | **True** — byte-identical to the post-SIGKILL state |
| Queue replenished by the restart | **False** (`queue_length_after_restart: 0`) |
| Worker B re-executed the task | **no** — the task was consumed once, by Worker A, before the crash |

The run's status, worker instance, claim, and heartbeat were **identical**
before and after Worker B's review.

## 17. No escalation or retry evidence

| Check | Result |
|---|---|
| Escalation created by the restart | **none** (`escalation_count: 0`) |
| Coding-result artifact created | **none** (`artifact_count: 0`) |
| Source-thread result delivered | **none** |
| Terminal task event published | **none** |
| Credential lease issued | **none** |
| New worker attempt authorized | **none** |
| Ownership replaced | **none** — the original instance and claim are intact |

The contract asserts each of these independently, on the read path.

## 18. Diagnostic output shape

The result is a bounded, structured summary:

```
reviewed_count, recently_observed_count, stale_uncertain_count,
missing_evidence_count, inconsistent_count, already_resolved_count,
already_escalated_count, review_complete, review_error_code,
run_ids, stale_uncertain_run_ids
```

It carries no credential value, no raw prompt, no transcript content, no
provider response, and no account content. It is an internal diagnostic: there
is no public diagnostics endpoint, and no feature gate exposes it. The
identifier lists are bounded by the review's read limit, and the log line that
lists stale run identifiers is bounded separately
(`_CODING_RUN_REVIEW_LOG_ID_LIMIT = 20`).

`inconsistent_count` is one field beyond the slice's list. It exists so a
self-contradicting record — exactly the malformed case §12 warns about — is
visible rather than silently dropped.

## 19. Red-then-green evidence

The **final** 32-case contract, run against the **unmodified** baseline
`80d46f86c` (the tracked changes were stashed; the new contract was kept in
place so it could run against the baseline):

| Run | Result |
|---|---|
| **RED** — the contract at baseline `80d46f86c` | **32 failed, 0 passed** |
| **GREEN** — the contract at the evaluated tree | **32 passed** |

The RED condition is the missing startup review capability, and it is clean:
every case fails at the baseline because neither
`AgentStore.list_unresolved_guardian_coding_runs()` nor
`CodingWorker.review_unresolved_coding_runs()` exists. No persistence
capability was invented, and no previous slice's PASS was altered.

The same source hashes, the same fixtures, and the same disposable
infrastructure were used for both runs.

## 20. Focused validation

| Path | Result |
|---|---|
| `tests/contracts/test_guardian_coding_worker_restart_review_contract.py` | **32 passed** |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | 19 passed, 1 xfailed |
| `tests/contracts/test_guardian_coding_run_liveness_contract.py` | 31 passed |
| `tests/contracts/test_guardian_coding_run_uncertain_quarantine_contract.py` | 34 passed |
| `tests/contracts/test_guardian_coding_run_quarantine_operator_route_contract.py` | 39 passed |
| `tests/contracts/test_guardian_coding_worker_terminal_fencing_contract.py` | 23 passed |
| `tests/contracts/test_guardian_coding_worker_heartbeat_contract.py` | 25 passed |
| `tests/contracts/test_guardian_coding_worker_ownership_contract.py` | 26 passed |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | 19 passed |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | 21 passed |
| `guardian/tests/workers/test_coding_worker.py` | 91 passed, 14 inherited failures |
| `guardian/tests/workers/test_coding_worker_regression_guard.py` | 2 passed, 1 inherited failure |
| `guardian/tests/agents/` | 107 passed |
| `tests/agents/test_execution_ledger_store.py` | 11 passed |
| **Focused sweep total** | **481 passed, 15 failed, 1 xfailed** (497 collected) |

The sweep ran against disposable PostgreSQL with the worktree pinned on
`PYTHONPATH`:

```
PYTHONPATH=<worktree> \
TEST_DATABASE_URL=postgresql+psycopg://hb:hbpw@127.0.0.1:55500/hbdb \
python -m pytest -o addopts="" -q -p no:randomly \
  tests/contracts/test_guardian_coding_worker_restart_review_contract.py \
  ... (the 14 paths above) ...
```

`alembic heads` → `d86f2a4b1c90 (head)`, single head, unchanged.

The monolithic backend gate is reported as **NOT RUN** to completion, for the
same reason recorded by the previous slice: it was never run to a clean
baseline, and a partial monolithic result is not a substitute for one.

### The contract's 32 cases

| # | Spec case | Test |
|---|---|---|
| 1 | Startup review runs before destructive dequeue | `test_the_startup_review_runs_before_destructive_dequeue` |
| 2 | Canonical PostgreSQL observation is used | `test_the_review_uses_the_database_observation_clock` |
| 3 | Only Guardian-bound coding runs are inspected | `test_only_guardian_bound_coding_runs_are_inspected` |
| 4 | Running accepted run is discovered | `test_a_running_accepted_run_is_discovered` |
| 5 | Queued never-accepted run is not treated as abandoned | `test_a_queued_never_accepted_run_is_not_treated_as_abandoned` |
| 6 | Fresh heartbeat is classified conservatively | `test_a_fresh_heartbeat_is_classified_conservatively` |
| 7 | Stale heartbeat remains uncertain | `test_a_stale_heartbeat_remains_uncertain` |
| 8 | Historical missing ownership remains unknown | `test_historical_missing_ownership_remains_unknown` |
| 9 | Missing heartbeat remains unknown | `test_a_missing_heartbeat_remains_unknown` |
| 10 | Terminal success is preserved | `test_a_terminal_success_is_preserved` |
| 11 | Terminal failure is preserved | `test_a_terminal_failure_is_preserved` |
| 12 | Canceled execution is preserved | `test_a_canceled_execution_is_preserved` |
| 13 | Escalated execution is preserved | `test_an_escalated_execution_is_preserved` |
| 14 | Active peer worker remains untouched | `test_an_active_peer_worker_remains_untouched` |
| 15 | A second worker cannot claim a reviewed run | `test_a_second_worker_cannot_claim_a_reviewed_run` |
| 16 | Multiple runs owned by one worker remain independent | `test_multiple_runs_of_one_worker_remain_independent` |
| 17 | Cross-account execution data is not publicly exposed | `test_cross_account_execution_data_is_not_publicly_exposed` |
| 18 | Review pagination is bounded | `test_the_review_pagination_is_bounded` |
| 19 | Partial review is reported as partial | `test_a_partial_review_is_reported_as_partial` |
| 20 | Database unavailability is not treated as an empty inventory | `test_database_unavailability_is_not_an_empty_inventory` |
| 21 | No AgentRun mutation occurs | `test_no_agent_run_mutation_occurs` |
| 22 | No AgentEscalation is created | `test_no_agent_escalation_is_created` |
| 23 | No retry or requeue occurs | `test_no_retry_or_requeue_occurs` |
| 24 | No credential lease is issued | `test_no_credential_lease_is_issued` |
| 25 | No new adapter invocation occurs | `test_no_new_adapter_invocation_occurs` |
| 26 | No source-thread result is fabricated | `test_no_source_thread_result_is_fabricated` |
| 27 | No coding-result artifact is fabricated | `test_no_coding_result_artifact_is_fabricated` |
| 28 | No terminal task event is fabricated | `test_no_terminal_task_event_is_fabricated` |
| 29 | Existing normal worker execution remains functional | `test_existing_normal_worker_execution_remains_functional` |
| 30 | The strict-xfail restart-reconciliation tripwire remains unresolved | `test_the_restart_reconciliation_tripwire_remains_unresolved` |
| — | A self-contradicting record is reported, never repaired | `test_an_inconsistent_record_is_reported_and_not_repaired` |
| — | A worker without canonical persistence consumes nothing | `test_an_unreachable_store_stops_the_worker_before_it_consumes` |

Three further cases live in `guardian/tests/workers/test_coding_worker.py`,
against the worker's own SQLite-backed test double, so the review is exercised
on the same surface the worker's normal execution uses:

- `test_the_startup_review_finds_a_guardian_bound_running_run`
- `test_the_startup_review_ignores_a_run_that_is_not_guardian_bound`
- `test_the_startup_review_leaves_the_canonical_run_unchanged`

## 21. Inherited failure comparison

The 15 failures are compared by **exact test identity and cause**, and were
re-run at the **unmodified baseline `80d46f86c`** to prove inheritance:

| | Baseline `80d46f86c` | Evaluated tree |
|---|---|---|
| `guardian/tests/workers/test_coding_worker.py` + `test_coding_worker_regression_guard.py` | **15 failed, 91 passed** | **15 failed, 94 passed** (+3 = this slice's new cases) |
| Failure identities | identical | identical |
| Causes | identical | identical |

The 14 failures in `guardian/tests/workers/test_coding_worker.py` are the same
environmental ones this campaign has recorded across slices — this sandbox
denies `git worktree` creation, so the isolated-worktree cases cannot build
their sandbox:
`test_one_worker_runs_two_pi_bindings_against_local_provider_mocks`,
`test_worker_records_campaign_attempt_ledger_and_work_order_markers`,
`test_worktree_isolation_enabled_runs_adapter_and_validation_in_isolated_cwd`,
`test_worktree_isolation_preserves_relative_subdirectory_cwd`,
`test_isolated_success_captures_patch_manifest_and_terminal_metadata`,
`test_isolated_success_patch_capture_includes_untracked_file`,
`test_patch_artifact_root_can_stay_clean_with_gitignore_rule`,
`test_dirty_original_checkout_does_not_block_isolated_execution`,
`test_isolated_success_cleans_up_by_default_without_promoting_changes`,
`test_isolated_failure_keeps_worktree_by_default`,
`test_oversized_patch_writes_manifest_without_partial_patch`,
`test_keep_on_success_flag_preserves_isolated_worktree`,
`test_cleanup_failure_is_reported_without_overwriting_success`,
`test_dirty_preflight_fails_before_adapter_execution`.

The 15th, in
`guardian/tests/workers/test_coding_worker_regression_guard.py::test_no_name_error_in_guard_path`,
is a genuine pre-existing product defect: `NameError: name
'_fetch_work_order' is not defined` in the campaign-attempt-ledger path of
`guardian/workers/coding_worker.py`. It is reported and **not** patched here
— fixing it is a separate change with its own blast radius, and it is not
what this slice is about.

**No new failure was introduced by this slice.** The recovery contract's
strict-xfail restart-reconciliation tripwire is **unchanged and still
xfail**.

### Lint

`ruff` on every changed Python file reports **the same three findings as the
baseline** — `store.py`'s `F541` (an f-string without placeholders, in the
result-message builder) and the worker test file's `F821` (`_fetch_work_order`,
the pre-existing defect above) and `F841`. This slice adds **zero** new lint
findings; the three unused imports its new contract initially carried were
removed rather than left behind.

| | Baseline | Evaluated tree |
|---|---|---|
| `guardian/agents/store.py` | 1 finding | 1 finding |
| `guardian/workers/coding_worker.py` | 0 findings | 0 findings |
| `guardian/tests/workers/test_coding_worker.py` | 2 findings | 2 findings |
| `tests/contracts/test_guardian_coding_worker_restart_review_contract.py` | — (new file) | 0 findings |

## 22. Remaining recovery limitations

1. **No worker-death determination.** A stale heartbeat remains missing
   evidence, not proof that a process stopped. The review names the
   uncertainty; it does not resolve it.
2. **No restart reconciliation.** The strict-xfail
   restart-reconciliation tripwire in the recovery contract is **unchanged and
   still xfail**: the tripwire asserts an *escalation*, and a read-only review
   creates none.
3. **No automatic quarantine.** The review never calls the quarantine
   service, the quarantine persistence, or the operator HTTP route.
4. **No automatic retry, requeue, or ownership takeover.**
5. **No external process termination, worktree cleanup, provider-session
   cancellation, or rollback.** A committed observation protects canonical
   state only.
6. **No operator UI and no public endpoint.**
7. **External side effects remain uncertain.** A stale accepted run may have
   touched the worktree, the repository, and a provider session; the review
   says nothing about any of that.
8. **Restart recovery remains unqualified.**

## 23. Explicit feature-gate posture

This slice changes **no** feature gate and **no** router.

- `CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES` remains `default_enabled=False`.
- `guardian/guardian_api.py` is **not** modified. The supported-profile
  quarantine of the Guardian delegation family is unchanged, so the operator
  quarantine route remains **unavailable** in Supported Beta and in Private
  Preview even with the flag enabled.
- The startup review is an **internal observation**. It is not a public
  endpoint, it is not gated, and it does not imply that the operator HTTP
  route is reachable in a supported deployment.
- No default feature gate was activated.

## 24. Classification

**PASS**, with release status unchanged at **HOLD**.

The stopping condition is met: coding-worker startup produces a bounded,
accurate, read-only review of the unresolved accepted Guardian coding runs,
without modifying execution state or granting recovery authority, and a
controlled cross-process restart proves the review observes without acting.

### Invariant checks

- Guardian remains the execution and recovery authority.
- PostgreSQL remains canonical for the review's evidence.
- Startup is an observation trigger, **not** evidence of worker death.
- Recent heartbeat activity is **not** proof that a process still exists.
- Stale heartbeat activity is **not** proof that a process stopped.
- The starting worker **cannot** assume ownership of another worker's run.
- Review cannot invalidate a worker claim.
- Review cannot authorize terminalization, escalation, or retry.
- A terminal result is not reopened.
- Historical missing evidence remains unknown.
- Redis queue state is not treated as proof of execution completion.
- No secret or raw transcript enters the review diagnostic.
- No second recovery authority was introduced.
- No feature-branch proof widens default Beta support.

### Explicit confirmations

- **No new execution authority.** The review only reads and classifies.
- **No automatic quarantine.** The quarantine service, persistence, and
  operator route are never invoked by the review.
- **No worker-death inference.** A stale heartbeat is reported as
  `stale_uncertain`, which is the established "evidence missing" verdict.
- **No ownership takeover.** The reviewed run keeps its owner and its claim.
- **No automatic retry.** No task is requeued or re-executed.
- **No startup reconciliation mutation.** The review changed no run, created
  no escalation, and published no terminal event.
- **No real provider request.** No provider key was used, Pi was not launched,
  and the adapter was a controlled synthetic one.
- **No production state modification.** Every database and queue touched was a
  disposable container database and a disposable Redis.
- **No default feature-gate activation.**
- **No unsupported sandbox claim.** The controlled SIGKILL proves termination
  in the experiment; it is not a production worker-death oracle.
- **Restart recovery remains unqualified.**
- **Release remains HOLD.**
