# Guardian Coding Worker — Durable Acceptance Before Execution

**Base commit:** `d7f10c2621a368415f0813e480f4a7e0ccf8ac93`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-23
**Final classification:** **PASS** (for the durable acceptance prerequisite)

This proof establishes that a Guardian-bound coding execution cannot enter a
side-effecting execution path until its acceptance is durably recorded in
canonical PostgreSQL, and that an accepted run remains distinguishable from a
queued, never-started run after worker process death.

This is a **prerequisite**, not restart-time reconciliation. The acceptance
record is the substrate that reconciliation would read. Nothing reads it at
startup, no uncertain-outcome sweep exists, and no retry authority was added.

---

## 1. Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Base HEAD | `d7f10c2621a368415f0813e480f4a7e0ccf8ac93` |
| `git merge-base --is-ancestor d7f10c262 HEAD` | true |
| Evaluated change | the working-tree diff over `d7f10c262`, limited to the seven authorized files |
| Proof commit | this document is committed in the same commit as the change it describes; the tree under evaluation is exactly the diff over `d7f10c262` |

| File | Change | Lines |
|---|---|---|
| `guardian/agents/store.py` | `RUN_ACCEPTANCE_*` constants, `_CONTRADICTORY_IDENTITY`, `AgentStore.claim_run_for_acceptance` | +167 |
| `guardian/workers/coding_worker.py` | acceptance gate in `_process_task`, `_emit_acceptance_rejected` | +92 / -2 |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | new — 19 contract cases | 854 |
| `docs/architecture/guardian-delegation-loop-contract.md` | "Durable execution acceptance" section, one invariant, one recovery cross-reference | +26 / -1 |

No migration, no new table, no queue change, no credential-authority change,
no adapter change, no production runtime configuration change, and no ADR
change.

## 2. The durable representation

The acceptance record is the existing canonical `agent_runs` row. The schema
already permitted `status = 'running'` and already carried a nullable
`started_at`, so no migration was required.

| Field | Before acceptance | After acceptance |
|---|---|---|
| `agent_runs.status` | `queued` | `running` |
| `agent_runs.started_at` | `null` | stamped exactly once |

`AgentStore.claim_run_for_acceptance` (`guardian/agents/store.py:1113`) performs
the transition as a compare-and-set:

```sql
UPDATE agent_runs
   SET status = 'running', started_at = now()
 WHERE id = :id AND status = 'queued' AND deployment_id = :deployment_id
```

The update applies only while the row is still `queued`, so exactly one of two
racing workers can win, a terminal run is never reopened, and a duplicate claim
never refreshes `started_at`.

The claim returns one of three outcomes — `accepted`, `rejected`,
`unavailable` — and **anything other than `accepted` refuses execution**.
Unreachable persistence is `unavailable`, never permission to execute.

## 3. The boundary

Call sites in `guardian/workers/coding_worker.py::_process_task`:

| Line | Call | Phase |
|---|---|---|
| 2234 | `_validate_task_execution_binding(...)` | trusted binding validation |
| **2291** | **`self.store.claim_run_for_acceptance(...)`** | **durable acceptance** |
| 2324 | `_resolve_lease_context(...)` | side-effecting |
| 2369 | `_create_isolated_worktree(...)` | side-effecting |
| 2434 | `self._emit_running(...)` | side-effecting |
| 2965 | `request_coding_credential_lease(...)` | side-effecting |
| 3039 | `execute_authorized(...)` | side-effecting |

Acceptance therefore sits after the trusted binding validation and before every
side-effecting step. `task.running` now follows a successful durable acceptance
rather than preceding it.

**Refusal is non-destructive.** `_emit_acceptance_rejected`
(`guardian/workers/coding_worker.py:4293`) publishes the canonical generic,
**non-terminal** `task.event` (`TaskEventType.TASK_EVENT.value`) with the run's
lineage, `status="acceptance_rejected"`, a local `error_code`
(`EXECUTION_ACCEPTANCE_REJECTED` / `EXECUTION_ACCEPTANCE_UNAVAILABLE`), an
error message, and the execution provenance. It deliberately calls **neither**
`update_run_status` **nor** `store_coding_result`, so a duplicate delivery
cannot turn another worker's running attempt into a terminal failure, cannot
produce a second result artifact, and cannot post a second source-thread
message.

No protocol token was added. `guardian/protocol_tokens.py` is unchanged, and the
worker already used local `error_code` strings
(`EXECUTION_BINDING_REJECTED`, `EXECUTION_CREDENTIAL_AUTHORIZATION_FAILED`).

## 4. Claim authority

The claim's authority is the durable deployment record the run already points
at — the same immutable spec the execution binding was validated against. The
run must belong to that deployment, and every identity the deployment
*asserts* — account, thread, source message, attempt, coding task — must agree
with the claiming task.

Asserted identities are read from the deployment spec **and** from its
persisted `execution_binding`, because that binding is the record the
credential-lease authority re-validates. A deployment that asserts nothing
about an identity does not contradict the task; a deployment that asserts a
different one does, and so does a deployment that contradicts itself.

> This rule was **revised during the proof**. The first implementation compared
> the task's attempt and coding-task identities against the deployment spec's
> top-level keys only. That is stricter than the durable record warrants, and it
> broke 62 existing worker tests whose deployments carry identity in the
> binding rather than at the top level. The revision reads the binding as well.
> The revision is itself proven by the red-then-green in §6 and by the
> regression comparison in §7.

## 5. Environment

| Resource | Value |
|---|---|
| Disposable PostgreSQL 15 | container `codexify-acceptance-pg`, `127.0.0.1:55450` only |
| Contract database | one uniquely-named throwaway database per case, created and dropped by the fixture |
| Redis | in-memory (`redis_queue._InMemoryRedis`), per case |
| Python | `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python` (SQLAlchemy 2.0.44, alembic 1.17.0, psycopg 3.2.10, pytest 8.4.2) |
| Provider | **none** — no provider request, no live canary, no network egress |

The credential authority was exercised **for real, in process**: the worker's
credential-lease client (`guardian/agents/credential_lease_client.py`) had only
its socket replaced, so the request body, the service-key check, the
deployment and lineage re-validation, the credential authority
(`issue_api_key_lease` + `seal_lease_payload`), the sealed lease payload, and
the worker-side lease validation were all production code paths. The lease
issued to the worker carried a real `authorization_evidence_ref`, the real
`provider_id` / `model_id` / `harness_id` from the seeded credential, and the
real attempt and coding-task identities.

The credential-lease route accepts a run whose status is `queued` **or**
`running` (`guardian/routes/agent_orchestration.py:651`), so the durably
accepted run remains leaseable — the acceptance gate does not conflict with the
credential authority.

The provider adapter was stubbed. The Pi harness version marker was supplied
from a temporary package root; no Pi SDK, provider request, or network access
was involved.

## 6. Red-then-green

Red-then-green was run as an **isolated scratch source comparison**, never a
worktree stash. A scratch tree was assembled from the evaluated worktree
(`guardian/`, `backend/`, `config/`, `codex_runner/`, `conftest.py`,
`pytest.ini`, and the contract file), and only the two implementation files were
swapped between the two runs. Import origin was asserted before each run:

```
guardian package : /…/acceptance-original-src/guardian/__init__.py
store module     : /…/acceptance-original-src/guardian/agents/store.py
worker module    : /…/acceptance-original-src/guardian/workers/coding_worker.py
```

The overlay is taken from the **explicit base commit** `d7f10c262`, not from
`HEAD`. After this change is committed, `HEAD` *is* the changed implementation,
so an overlay taken from `HEAD` silently compares the change against itself.
That substitution was made once during the proof and was caught immediately by
the RED run reporting 19 passed; every RED run below pins `d7f10c262`.

| Run | Implementation | Result |
|---|---|---|
| RED | original at `d7f10c262` | **17 failed, 2 passed** |
| GREEN | changed implementation, same tree, same file | **19 passed** |

The two cases that pass in RED are assertions about behaviour that must not
regress: the normal path still persists a terminal result and artifact, and one
attempt still delivers exactly one source-thread result message.

The 17 RED failures split into:

- **13** × `AttributeError: 'AgentStore' object has no attribute 'claim_run_for_acceptance'`
- **1** × `AttributeError: module 'guardian.agents.store' has no attribute 'RUN_ACCEPTANCE_ACCEPTED'`
- **3** × *decisive behavioural* failures — the defect this task targets:

```
AssertionError: assert 'queued' == 'running'        # at worktree creation
AssertionError: assert ['queued'] == ['running']    # at adapter entry
AssertionError: ['task.failed']                     # a duplicate publishes a false terminal outcome
```

Read plainly: against the original implementation the worker **entered the
provider adapter and created the isolated worktree while the canonical run row
was still `queued` with a null `started_at`**. There was no durable acceptance
record at the moment execution became side-effecting.

The third behavioural failure is worth stating separately, because it is a
distinct harm. A duplicate delivery of an already-completed attempt published a
**spurious terminal `task.failed`** for an attempt that had succeeded. The
canonical run *row* survived that, because `AgentStore.update_run_status` already
refuses to move a terminal run to a different terminal state — but the event
stream, which is what the UI and the transcript read, carried a false terminal
failure. The durable acceptance gate removes it at the source: the duplicate is
refused before the generic failure handler is reached, and the refusal is
published as the generic **non-terminal** `task.event` with
`status="acceptance_rejected"`.

## 7. Regression comparison

Focused validation sweep, worker files alone, same scratch tree, same complete
fixture set (`codex_runner/`, `backend/`, `config/` all present in both):

| Run | Result |
|---|---|
| baseline (original implementation) | **15 failed, 91 passed** |
| changed implementation | **15 failed, 91 passed** |

Comparison was by **exact test identity and exact failure cause**, including
the observed values in the assertion messages:

```
$ diff baseline_ids.txt green_ids.txt     →  IDENTITIES IDENTICAL (15/15)
$ diff baseline_causes.txt green_causes.txt → CAUSES IDENTICAL (including observed values)
```

**15 inherited failures, 0 regressions, 0 newly-fixed.** All fifteen are
present, unchanged, in both runs:

- 14 in `guardian/tests/workers/test_coding_worker.py`
- 1 in `guardian/tests/workers/test_coding_worker_regression_guard.py::test_no_name_error_in_guard_path`

The inherited failures are predominantly the sandbox's own limits: git
worktree creation is denied on this filesystem (`git init` fails with
`unable to unlink .git/config.lock`), so the isolated-worktree cases cannot
construct their fixtures. One is a genuine pre-existing product defect,
reported and **not** patched, per the task's non-goals:

```
NameError: name '_fetch_work_order' is not defined
```

in `guardian/workers/coding_worker.py` (campaign-attempt-ledger path).

Full focused sweep against the changed implementation:

| Result | Count |
|---|---|
| Passed | **249** |
| Failed | **15** (all inherited, identical to baseline) |

Covered paths: `tests/contracts/test_guardian_coding_worker_acceptance_contract.py`,
`tests/contracts/test_guardian_dispatch_integration_contract.py`,
`tests/contracts/test_guardian_execution_binding_contract.py`,
`tests/contracts/test_guardian_delegation_phase2a_contract.py`,
`tests/contracts/test_guardian_dispatch_contract.py`,
`tests/contracts/test_guardian_permission_posture_contract.py`,
`guardian/tests/workers/test_coding_worker.py`,
`guardian/tests/workers/test_coding_worker_regression_guard.py`,
`guardian/tests/agents/test_pi_readiness.py`.

The new contract file contributes **19 passed, 0 failed**.

### The monolithic backend gate

The repository's default backend gate — `pytest -v` over the whole suite — was
run twice: once against the changed implementation, and once against the
original implementation at `d7f10c262` in an isolated scratch tree that was a
complete copy of the evaluated worktree with only the two implementation files
reverted. The Private Preview stayed healthy (`127.0.0.1:8081/health` → 200)
throughout both runs.

| Run | Implementation | Result |
|---|---|---|
| baseline | original at `d7f10c262` | **155 failed, 8711 passed, 108 skipped, 35 xfailed, 11 xpassed, 40 errors** (40:53) |
| changed | the change under proof | **137 failed, 8729 passed, 108 skipped, 35 xfailed, 11 xpassed, 40 errors** (27:59) |

Compared by **exact test identity**, extracted from both the mid-run `-v`
markers and the short-test-summary block:

| Category | Count |
|---|---|
| Shared identical failure identities | **135** |
| Failed only in baseline — the new acceptance contract | **17** |
| Failed only in baseline — scratch-copy artifact (see below) | **1** |
| Failing in the changed run but not the baseline | **2** |
| Collection errors, identical in both runs | **40** |

**Zero regressions.** The seventeen acceptance-contract cases fail against the
original implementation and pass against the change — the same seventeen the
isolated red-then-green in §6 exercises.

The one remaining baseline-only failure is
`tests/architecture/test_guardian_evidence_packet_make_target.py::test_make_target_passes_current_fixture_set_without_writing_files`,
and it is an **artifact of the scratch-copy method, not of the change**. That
test snapshots `scripts/guardian/`, `docs/architecture/fixtures/` and the
`Makefile`, runs `make guardian-evidence-packets-validate`, and asserts the
snapshot is unchanged. The scratch copy excluded `__pycache__`, so the system
Python 3.14 that the Makefile invokes had to compile
`validate_evidence_packet`; this sandbox denies the atomic rename that
bytecode caching depends on, so a stray hashed `cpython-314.pyc.<hash>` file
was left behind and the snapshot assertion caught it. Copying the already
compiled `validate_evidence_packet.cpython-314.pyc` into the baseline tree makes
the test **pass there as well** — proved directly, not inferred.

The two identities that failed in the changed run but not the baseline are
load-sensitive flakes, and both **pass in isolation in both trees**:

| Identity | Changed tree, isolated | Baseline tree, isolated |
|---|---|---|
| `tests/vector/test_vector_physical_deadline.py::test_chroma_bound_search_preserves_results_and_deferred_parent_handle` | passed (twice) | passed |
| `tests/workers/test_document_worker_shutdown.py::test_faiss_success_preserves_worker_index_between_jobs` | passed (twice) | passed |

Both are chroma/faiss vector-store and worker-shutdown tests that build and
tear down native indexes; neither touches the coding worker, the agent store's
acceptance operation, or anything the change alters. Two further
baseline-only identities (`test_accepted_constructor_retains_parent_add_authority`
and `test_active_failure_commits_before_shutdown`) likewise pass in isolation
in both trees. The suite's own run-to-run variance confirms the flakiness: two
full runs of the *same* changed code reported 144 and 137 failures.

## 8. PostgreSQL readback

Read back through canonical sessions with raw SQL against the disposable
PostgreSQL.

**Before acceptance** — a dispatched Guardian run:

```json
{ "id": 1, "run_id": "run_53dc16a7957446fd", "status": "queued",
  "started_at": null, "ended_at": null, "error": null,
  "thread_id": 1, "deployment_id": 1 }
```

**After the compare-and-set** — `claim outcome: accepted`:

```json
{ "id": 1, "run_id": "run_53dc16a7957446fd", "status": "running",
  "started_at": "2026-10-23 12:23:34.645205+00:00",
  "ended_at": null, "error": null,
  "thread_id": 1, "deployment_id": 1 }
```

**After the worker process disappears** — no terminalization, the worker object
simply ceases to exist:

```json
{ "id": 1, "run_id": "run_53dc16a7957446fd", "status": "running",
  "started_at": "2026-10-23 12:23:34.645205+00:00",
  "ended_at": null, "error": null,
  "thread_id": 1, "deployment_id": 1 }
```

**Contrast** — a queued, never-started run: `status = "queued"`,
`started_at = null`.

```
accepted run distinguishable from queued never-started run: True
```

**No extra table.** The `agent_*` tables present after the run are exactly the
pre-existing set:

```
agent_confidence_reports, agent_deployments, agent_escalations, agent_events,
agent_extension_install_bindings, agent_extension_install_gate_decisions,
agent_extension_proposals, agent_extension_registry_entries,
agent_reflections, agent_run_artifacts, agent_run_attempts, agent_run_steps,
agent_runs
```

## 9. The 19 contract cases

`tests/contracts/test_guardian_coding_worker_acceptance_contract.py`, against a
disposable PostgreSQL, each case creating and dropping its own database.

| # | Case | Establishes |
|---|---|---|
| 1 | `test_the_store_exports_the_canonical_acceptance_outcomes` | the store publishes the outcome vocabulary |
| 2 | `test_a_valid_queued_guardian_run_is_accepted` | a queued run with a valid binding is accepted |
| 3 | `test_accepted_state_persists_as_running` | the canonical row moves to `running` |
| 4 | `test_started_at_is_populated_exactly_once` | a duplicate claim does not refresh `started_at` |
| 5 | `test_original_run_and_deployment_identities_are_unchanged` | run id and deployment id are unchanged by acceptance |
| 6 | `test_accepted_state_is_readable_through_a_new_session` | the acceptance is durable, not session-scoped |
| 7 | `test_acceptance_precedes_worktree_creation` | **acceptance precedes the first filesystem side effect** |
| 8 | `test_acceptance_precedes_adapter_entry` | **the adapter observes `running` with a stamped `started_at`** |
| 9 | `test_a_duplicate_claim_does_not_enter_execution` | a duplicate enters no adapter, opens no second artifact, posts no second message, rewrites no status, and publishes **no terminal event** — only the non-terminal acceptance refusal |
| 10 | `test_two_concurrent_claims_cannot_both_succeed` | exactly one of two racing claims wins |
| 11 | `test_a_terminal_run_cannot_be_reaccepted` | `succeeded` / `failed` / `canceled` / `escalated` are never reopened |
| 12 | `test_a_missing_run_fails_closed` | a missing run is refused |
| 13 | `test_a_mismatched_deployment_fails_closed` | a run belonging to another deployment is refused |
| 14 | `test_a_mismatched_attempt_or_binding_fails_closed` | identity contradiction is refused |
| 15 | `test_postgresql_failure_prevents_adapter_execution` | a database failure stops execution |
| 16 | `test_unavailable_persistence_is_refused` | missing persistence is never permission to execute |
| 17 | `test_accepted_state_survives_a_worker_disappearance` | the record survives the worker |
| 18 | `test_normal_success_still_persists_a_terminal_result` | the normal path still persists a terminal result and an artifact |
| 19 | `test_source_thread_result_is_not_duplicated` | one attempt delivers exactly one source-thread result message |

Cases 2–6 and 10–17 exercise the claim through the store against a run,
deployment, execution binding, and queued task produced by a real
`GuardianDelegationService` dispatch, so that lineage is authentic. Cases 7–9
and 18–19 drive the real `CodingWorker._process_task` with a stubbed provider
adapter.

### Mapping to the sixteen required cases

| Required case | Contract case |
|---|---|
| 1. A valid queued Guardian run is accepted | `test_a_valid_queued_guardian_run_is_accepted` |
| 2. The accepted state persists as running | `test_accepted_state_persists_as_running` |
| 3. `started_at` is non-NULL | `test_started_at_is_populated_exactly_once` |
| 4. The original run and deployment identities are unchanged | `test_original_run_and_deployment_identities_are_unchanged` |
| 5. The accepted state is readable through a new database session | `test_accepted_state_is_readable_through_a_new_session` |
| 6. Acceptance occurs before worktree creation | `test_acceptance_precedes_worktree_creation` |
| 7. Acceptance occurs before adapter entry | `test_acceptance_precedes_adapter_entry` |
| 8. A duplicate claim does not enter execution | `test_a_duplicate_claim_does_not_enter_execution` |
| 9. Two concurrent claims cannot both succeed | `test_two_concurrent_claims_cannot_both_succeed` |
| 10. A terminal run cannot be reaccepted | `test_a_terminal_run_cannot_be_reaccepted` |
| 11. A missing run fails closed | `test_a_missing_run_fails_closed` |
| 12. A mismatched deployment or binding fails closed | `test_a_mismatched_deployment_fails_closed`, `test_a_mismatched_attempt_or_binding_fails_closed` |
| 13. PostgreSQL failure prevents adapter execution | `test_postgresql_failure_prevents_adapter_execution` |
| 14. Accepted state survives a simulated worker disappearance | `test_accepted_state_survives_a_worker_disappearance` |
| 15. Existing successful terminal persistence remains correct | `test_normal_success_still_persists_a_terminal_result` |
| 16. Existing source-thread result idempotency remains intact | `test_source_thread_result_is_not_duplicated` |

Two further cases close the acceptance criteria that the numbered list states
separately: `test_unavailable_persistence_is_refused` (missing or unavailable
persistence fails closed) and
`test_the_store_exports_the_canonical_acceptance_outcomes` (the outcome
vocabulary is published under canonical names).

### Requirements-to-evidence map

| Requirement | Evidence |
|---|---|
| Atomic claim, no unguarded read-then-update | compare-and-set `UPDATE … WHERE status='queued'`; §2; cases 9, 10 |
| Commit before reporting success | `session.commit()` precedes the `accepted` return; `guardian/agents/store.py:1253` |
| Terminal run never overwritten, `started_at` never refreshed | the update's `status='queued'` predicate; case 3 |
| Boundary before worktree, adapter, tools, mutation, validation | call-site table; §3; cases 6, 7 |
| `task.running` follows durable acceptance | `_emit_running` at 2434 is after the claim at 2291 |
| Persistence failure observable, never a false success | `_emit_acceptance_rejected`; §3; cases 13, 16 |
| Duplicate does not overwrite, re-lease, re-artifact, re-message | case 8; §3 |
| Legacy paths preserved | §7 regression comparison; 0 regressions |
| No fallback treating missing PostgreSQL as permission | `unavailable` refuses; case 16 |
| `queued → running → succeeded` preserved | case 15 |
| No duplicate artifacts or thread messages | cases 15, 19 |


## 10. Classification

**PASS** for this prerequisite. All nineteen contract cases pass against a
disposable PostgreSQL; the same file and the same tree fail 17 of 19 against the
original implementation, with three decisive behavioural failures showing
execution beginning while the run was still `queued`, and a duplicate delivery
publishing a false terminal outcome; the durable before/after/survival readback
confirms the accepted run is distinguishable from a queued, never-started run;
the focused sweep shows 15 inherited failures that are identical in identity and
cause to the pre-change baseline, with zero regressions; and the repository's
monolithic backend gate, run against both implementations, shares **135
identical failure identities** and **40 identical collection errors**, with the
seventeen acceptance-contract cases failing only in the baseline and **zero
regressions**.

## 11. What was not proven, and what was not done

**Not proven / not implemented.**

- Restart-time reconciliation of the acceptance record does not exist. Nothing
  reads it at startup, and no uncertain-outcome sweep exists. This is the next
  dependent task, not this one.
- `observe_liveness()`, `classify_dispatch_health()`, and `recover_dispatch()`
  are **not** wired into any startup path.
- No retry authority was added. No queue semantics were changed.
- No provider was contacted; no live canary was run; no release was promoted.

**Explicitly not done, per the task's non-goals.**

- The inherited `NameError: name '_fetch_work_order' is not defined` was
  reported, not patched.
- The adapter's empty `files_changed` report was not repaired.
- No migration, no queue implementation, no credential-authority change, no
  adapter change, no production runtime configuration change.
- No conversational intake activation, no public route activation, no
  production deployment, no branch integration, no release promotion.
- `docs/architecture/00-current-state.md` was not edited, and no earlier receipt
  was rewritten.

**Invariant checks.**

- Guardian still owns execution authorization. The acceptance claim consumes an
  authorization that was already validated; it grants nothing.
- Credentials retain their true canonical owner. The lease was issued by the
  unchanged credential authority.
- No ambient secret became task authority.
- Provider and model identity remain explicit.
- Permission scope did not widen inside the worker.
- One attempt remains one attempt: a duplicate delivery reaches no adapter and
  produces no second artifact or message.
- Queue acceptance does not imply execution success; durable acceptance does
  not imply it either.
- PostgreSQL remains canonical for durable results.
- Release status remains **HOLD**.
