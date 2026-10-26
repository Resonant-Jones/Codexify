# Guardian Coding Run — Operator-Authorized Uncertain Quarantine

**Base commit:** `ab26381ba52dbe4c388dc0a4910e84e34b46b138`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-26
**Final classification:** **PASS** (release remains **HOLD**)

The campaign had proved durable ownership, a claim-scoped heartbeat, and
claim-fenced terminal persistence. What it had **not** proved was that an
operator can dispose of an *unresolved* execution safely: a run whose owning
worker stopped reporting, whose outcome is unknown, and whose external side
effects are unknown.

This slice implements exactly that: **an explicitly operator-authorized
uncertain-outcome quarantine with atomic PostgreSQL persistence**. It is a
persistence-and-authorization slice. It does not activate startup
reconciliation, does not make a stale heartbeat a death oracle, and does not
introduce a public operator route.

---

## 1. Evaluated source commit

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Base HEAD | `ab26381ba52dbe4c388dc0a4910e84e34b46b138` |
| Working tree at the base commit | clean (tracked) |
| `alembic heads` | **exactly one** head: `d86f2a4b1c90` — unchanged |
| New migration | **none** |
| New persisted status | **none** |
| Provider | **none** — no provider request, no live DeepSeek canary |
| Production resources | **none touched** — every database used was disposable and local |

## 2. Existing operator authority used

Guardian already had a trusted operator authority, and this slice uses it
**as-is**. It did not invent a replacement identity mechanism.

`guardian/core/dependencies.py::require_operator_auth` accepts either:

- a configured Guardian API key (`GUARDIAN_API_KEY` / `GUARDIAN_API_KEYS`),
  compared with `hmac.compare_digest`, or
- a current-format signed token carrying `OPERATOR_SESSION_PURPOSE`.

It returns a **derived actor identity** — `"operator-api-key"` or
`"operator-session"` — and it rejects account and guest credentials
*before* the API-key fallback, so a principal credential is never
reinterpreted as operator material.

`GuardianDelegationService.quarantine_uncertain_coding_run()` is the trusted
invocation boundary. It takes the operator's **credential material** (never a
boolean), verifies it through `require_operator_auth`, and derives the actor
from the verification. An unauthorized caller gets a 401 and nothing else.

The operator actor stays distinct from the account owner, the worker
instance, the execution claim, and the credential owner — asserted by the
contract.

## 3. Effective quarantine call graph

```
GuardianDelegationService.quarantine_uncertain_coding_run()   # guardian/core/guardian_delegation_service.py
    -> _authenticate_operator()                                # require_operator_auth
    -> AgentStore.get_coding_run_liveness_snapshot()            # canonical evidence, database clock
    -> classify_coding_run_liveness()                          # guardian/core/guardian_dispatch.py (read-only)
    -> AgentStore.quarantine_coding_run_as_uncertain()         # ONE transaction
           -> conditional UPDATE agent_runs (running + worker + claim + stale heartbeat)
           -> AgentStore._insert_escalation()                   # same session
           -> COMMIT
```

`observe_liveness()`, `classify_dispatch_health()` and `recover_dispatch()`
were inspected and **not modified**: the new path reuses the existing
classification and recovery vocabulary rather than introducing a second
taxonomy. The recovery reason code is the one the dispatch contract already
uses, `guardian_dispatch_liveness_unproven`.

## 4. Liveness evidence preconditions

| Precondition | Where it is checked |
|---|---|
| `status = running` | the store's conditional update |
| a durable deployment, and the run points at it | the store, inside the transaction |
| a recorded worker-instance id and claim id | the store, inside the transaction |
| the expected worker and claim match | the store, inside the transaction |
| the expected account matches | the store, inside the transaction |
| the recorded heartbeat is **older** than the horizon, by the **database clock** | the store's conditional update, inside the transaction |
| the canonical liveness evidence says `stale_uncertain` | the service, before the disposition |

A fresh heartbeat, a terminal run, an already-escalated run, and a
historical ownership-unknown row are all refused. The staleness condition is
evaluated **inside** the transaction, so a heartbeat that became fresh after
the operator's review refuses the transition — the contract proves it by
renewing the heartbeat between the review and the commit.

## 5. Atomic transition implementation

```
UPDATE agent_runs
   SET status = 'escalated',
       ended_at = now()
 WHERE run_id = :run
   AND status = 'running'
   AND coding_worker_instance_id = :worker
   AND coding_worker_claim_id = :claim
   AND coding_worker_last_heartbeat_at IS NOT NULL
   AND coding_worker_last_heartbeat_at <= now() - :horizon
```

`now()` is PostgreSQL's clock, evaluated inside the transaction. The run's
`error` column is left untouched, and its owner and claim are never rewritten.

## 6. Escalation-record transaction boundary

`AgentStore.add_escalation()` committed on its own, so a disposition could
leave a run escalated with no evidence — or evidence attached to a run that
never escalated. This slice extracts a narrow **session-aware** helper,
`AgentStore._insert_escalation()`, and the public `add_escalation()` keeps
its existing behaviour (its own session, its own commit). The guarded
disposition inserts its escalation row on the *same* session as the
transition, so the two commit together or not at all.

The record uses the existing canonical representation: `status = open`,
`reason_code = guardian_dispatch_liveness_unproven`, a severity from the
existing vocabulary (`soft` / `hard`), an evidence-backed `preserved_worktree`,
and a bounded `payload_json`.

## 7. Original worker and claim preservation

The escalation payload carries `original_worker_instance_id`,
`original_worker_claim_id`, `original_execution_status = running`, and
`final_disposition = escalated`. The canonical row's own owner and claim
columns are untouched. The contract asserts both.

## 8. Explicit authorization evidence

The escalation payload records:

| Field | Source |
|---|---|
| `operator_actor` | derived by `require_operator_auth` — never supplied by the caller |
| `operator_decision_provenance` | the decision path, the verified actor, and the authority source |
| `liveness_evidence` / `liveness_verdict` / `liveness_reason_code` | the canonical classification |
| `last_heartbeat_at` / `observed_at` / `heartbeat_age_seconds` | the canonical evidence |
| `stale_after_seconds` | the observation horizon |
| `run_id` / `deployment_id` / `account_origin_user_id` | the canonical row |
| `execution_result` | `unknown` — the outcome is not decided |
| `preserved_worktree` / `worktree_presence` | evidence-backed, or `unknown` when a worktree cannot be established |

No credential material, secret, raw prompt, or transcript content enters the
evidence: the contract asserts the service key value is absent and that no
credential-shaped marker appears.

## 9. Duplicate-request behavior

| Situation | Result |
|---|---|
| the same run, claim, operator, and reason, requested again | `already_disposed` — the existing disposition is observed read-only; no second escalation, no reset timestamp, no replaced provenance, no reopened run |
| the run was escalated for a **different** reason or by a **different** authority | `conflict` — the existing disposition is never rewritten |
| two concurrent authorized requests | one `quarantined`, one `already_disposed`; exactly one escalation record (the loser re-reads the canonical row after losing the race) |

The concurrency case was run three times consecutively: 34 passed, 34 passed,
34 passed.

## 10. Concurrent terminal/quarantine race

| Who commits first | Outcome |
|---|---|
| the worker's terminal decision | the quarantine refuses; the terminal status, its artifact and its source-thread result are preserved; no quarantine escalation; no false uncertainty receipt |
| the quarantine | the late worker terminalization is rejected by the claim fence: `terminal_accepted = false`, the escalated status stands, exactly one escalation record, no stale-worker artifact, no stale-worker source-thread result, no terminal event |

## 11. Active-peer protection

A disposition is scoped to one run and its recorded owner. The contract runs
two independently accepted runs (Worker A → Run A, Worker B → Run B) and
asserts that disposing Run A leaves Run B's status, owner, claim, heartbeat and
delivery untouched, with no escalation record on the peer. A peer's activity
never makes a stale run look healthy, and a stale run never makes a peer
uncertain.

## 12. Late terminal-result rejection

After a quarantine, the original claim attempts to finalize the run. The
claim-fenced terminal write refuses it: `terminal_claim = terminal_rejected`,
the run stays `escalated`, and there is no coding-result artifact, no
source-thread result, and no terminal event.

## 13-15. Source-thread, artifact, queue and lease non-mutation

The contract asserts, after a disposition: no source-thread result message, no
coding-result artifact, no queue task enqueued or dequeued, no
credential-lease row, and no new execution attempt. The disposition is a
canonical state change, not an execution.

## 16. Transaction rollback evidence

An injected failure during the escalation-row insertion leaves the run
`running` with **zero** escalation records: the transaction rolls back, so
there is no escalated run without its committed evidence, and no escalation
evidence attached to a run whose transition failed. Unreachable persistence
returns `unavailable` and is surfaced as a 503 — persistence unavailability is
never transformed into permission to quarantine.

## 17. PostgreSQL readback

The contract reads every assertion back through an **independent database
session**: the run's status, the run's owner and claim, the escalation rows,
the artifact count, and the source-thread message count.

| After the disposition | Read back |
|---|---|
| `status` | `escalated` |
| `coding_worker_instance_id` | Worker A — unchanged |
| `coding_worker_claim_id` | Claim A — unchanged |
| open escalation records | exactly 1 |
| coding-result artifacts | 0 |
| source-thread result messages | 0 |
| late terminalization with Claim A | rejected |

## 18. Red-then-green comparison

Isolated scratch tree: `.scratch/quarantine-red-v1`, built from
`git archive ab26381ba` (only `.claude/commands` is excluded — the desktop
permission gate blocks those three paths).

| File | sha256 (first 16) | matches `ab26381ba` |
|---|---|---|
| `guardian/agents/store.py` | `5eaac374a1e84f40` | yes |
| `guardian/core/guardian_delegation_service.py` | `c2d85a9800bcb7bd` | yes |

Import origins were asserted inside the scratch tree:

```
store  : .scratch/quarantine-red-v1/guardian/agents/store.py
service: .scratch/quarantine-red-v1/guardian/core/guardian_delegation_service.py
has guarded store op:   False
has guarded service op: False
```

**The two substantive failures** (`.scratch/quarantine/probe_defects.py` — the
same probe runs against both trees and reports the durable state afterwards):

| Probe | Baseline `ab26381ba` | Repaired |
|---|---|---|
| **A** — the escalation evidence write fails mid-disposition | durable state: `status = escalated`, `escalations = 0` → **an escalated run without committed evidence** | durable state: `status = running`, `escalations = 0` → no partial escalation |
| **B** — a competing terminal decision committed first | durable state: `status = succeeded`, `open_escalations = 1` → **an open escalation attached to a completed run** | durable state: `status = succeeded`, `escalations = 0` → no contradictory state |

That is the defect the spec named: the ordinary implementation commits
independently, so a status transition and its escalation evidence can diverge
in either direction.

**The contract against the baseline**: 33 failed, 1 passed. The causes are
absent capabilities, not behavioural claims:

| Cause | Count |
|---|---|
| `AttributeError: 'GuardianDelegationService' object has no attribute 'quarantine_uncertain_coding_run'` | 30 |
| `AttributeError: 'AgentStore' object has no attribute 'quarantine_coding_run_as_uncertain'` | 1 |
| `AttributeError: AgentStore ... has no attribute '_insert_escalation'` | 1 |
| `AssertionError: assert 0 == 1` (the boolean cannot be passed) | 1 |

| Run | Result |
|---|---|
| **baseline** (`ab26381ba`, unmodified) | **33 failed, 1 passed** (+ the two substantive probe defects) |
| **repaired** | **34 passed** |

## 19. Focused validation

| Path | Result |
|---|---|
| `tests/contracts/test_guardian_coding_run_uncertain_quarantine_contract.py` | **34 passed** |
| `tests/contracts/test_guardian_coding_worker_terminal_fencing_contract.py` | 23 passed |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | 19 passed, 1 xfailed |
| `tests/contracts/test_guardian_coding_run_liveness_contract.py` | 31 passed |
| `tests/contracts/test_guardian_coding_worker_heartbeat_contract.py` | 25 passed |
| `tests/contracts/test_guardian_coding_worker_ownership_contract.py` | 26 passed |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | 19 passed |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | 21 passed |
| `guardian/tests/workers/test_coding_worker.py` | 14 inherited failures, otherwise passed |
| `guardian/tests/workers/test_guardian_coding_worker_regression_guard.py` | 1 inherited failure |
| the delegation contracts, `guardian/tests/agents/`, `tests/agents/test_execution_ledger_store.py` | passed |
| **Focused sweep total** | **489 passed, 15 failed, 1 xfailed** |

The 15 failures are exactly the inherited ones (14 in
`guardian/tests/workers/test_coding_worker.py` and 1 in
`guardian/tests/workers/test_coding_worker_regression_guard.py`), by exact
test identity. No new failure was introduced by this slice.

### The monolithic backend gate: aborted, not completed

The default backend gate — `pytest -v` over `tests/` — was started against
the evaluated tree with disposable PostgreSQL. It reached **87 %** (7 955
passed, 115 failures) and was then **aborted by the runtime's one-hour
background-task cap**, not by a failure of the suite or of the code.

The cause is environmental, and it is recorded rather than glossed: the
disposable PostgreSQL container had served every slice of this campaign for
about eighteen hours, and a wedged pytest process from an earlier attempt —
which could not be signalled, because `kill` and `ps` are blocked in this
environment — left the machine at a load average of 8–13. The database-heavy
phases then ran roughly two to four times slower than in the previous slices'
gates (which completed 9 100 tests in 22–25 minutes). An earlier attempt to
run a second pytest process against the same container produced a genuine
cross-process DDL stall; it was cleared by terminating the wedged backend and
dropping the abandoned disposable databases, and the gate was then re-run
alone.

What the partial run still proves, compared by **exact failure identity**
against the terminal-fencing slice's baseline (135 failures):

| Category | Count |
|---|---|
| failures in the partial run that are also in the baseline | **114** |
| failures in the partial run that are **not** in the baseline | **1** |
| failures in the baseline that the partial run did not reach | 20 (the suite's tail) |

The single new identity is
`tests/command_bus/test_chat_loopback_accepted_deadline.py::test_parent_total_deadline_closes_real_http[/headers]`
— one parametrisation of a wall-clock **deadline** test whose three sibling
parametrisations (`[/silent]`, `[/trickle]`, `[/redirect]`) passed in the
same run. Re-run in isolation on the committed tree, that file is **15/15
green**. It is a load artefact of the saturated machine, not a regression.

**The authoritative regression evidence for this slice is the focused sweep**
above: 489 passed, 15 failed, failure identities byte-identical to the
baseline. The monolithic gate is reported as **NOT RUN to completion** for
the reason above, rather than being presented as a clean full-suite pass.

## 20. Inherited failures

The inherited failures are the same pre-existing ones every slice in this
campaign has recorded: 14 in `guardian/tests/workers/test_coding_worker.py` and
1 in `guardian/tests/workers/test_coding_worker_regression_guard.py`. They are
predominantly this sandbox's own limits — git worktree creation is denied on
this filesystem — plus one genuine pre-existing product defect, reported and
**not** patched:

```
NameError: name '_fetch_work_order' is not defined
```

in `guardian/workers/coding_worker.py` (campaign-attempt-ledger path).

The recovery contract's strict-xfail restart-reconciliation tripwire is
**unchanged and still xfail**. The successful implementation of a manual
quarantine does not imply that worker restart reconciles anything.

## 21. Remaining operator-invocation and restart-reconciliation gaps

1. **No production invocation path.** The disposition is an internal service
   method with a verified operator boundary. There is no operator route, no
   CLI, and no UI. This slice does not claim an end-to-end operator workflow.
2. **No startup reconciliation.** Nothing reads the disposition at worker
   start, and `recover_dispatch()` is not activated.
3. **No worker-death determination.** `stale_uncertain` remains evidence of
   uncertainty. A stale heartbeat is still not a death oracle.
4. **No external side-effect accounting.** The disposition records what the
   canonical store knows; it does not inventory or contain external effects.
5. **No retry authority.** Nothing here may be reused to justify a re-drive
   without separate authorization and separate proof.

## 22. External side-effect limitations

A database quarantine cannot guarantee that the original worker stopped
performing external actions. The worker may already have modified an isolated
worktree, created an untracked file, started a subprocess, issued a provider
request, initiated a network operation, produced an uncommitted patch, or begun
a git commit. The disposition does not imply that any of those were prevented,
undone, or inventoried. It deletes no worktree and no artifact. Potentially
affected external resources remain subject to operator inspection, and no
provider-enforced sandbox conformance is claimed.

## 23. PASS/HOLD/BLOCKED classification

**PASS** — the guarded, explicitly authorized quarantine persistence contract
is proven.

| Acceptance criterion | Evidence |
|---|---|
| 1. Existing trusted operator authority is used | `require_operator_auth`, unchanged; the actor is derived by the verification |
| 2. No caller-supplied boolean can substitute for authorization | the disposition takes no boolean; the contract proves a `TypeError` and an unchanged run |
| 3. Canonical liveness evidence is revalidated | the staleness condition is evaluated by the database clock inside the transaction; the contract renews the heartbeat mid-flight and sees the refusal |
| 4. Heartbeat staleness alone cannot trigger quarantine | staleness is refused without an operator decision, and a fresh heartbeat is refused with one |
| 5. The original worker and claim identities are verified | the conditional update; contract cases for a wrong worker, a wrong claim, and an absent claim |
| 6. Run escalation and escalation evidence commit atomically | one session, one commit; probe A shows the baseline's partial escalation and the repair's rollback |
| 7. Duplicate quarantine is idempotent | `already_disposed`, one escalation, no reset timestamp, no replaced provenance |
| 8. Concurrent terminalization cannot produce contradictory durable state | probe B shows the baseline's contradiction; the repair refuses both ways |
| 9. An active peer worker remains unaffected | the two-run contract case |
| 10. Late terminal results remain rejected after escalation | `terminal_accepted = false`, escalated status preserved |
| 11. No source-thread result is fabricated | the contract asserts zero messages |
| 12. No replacement attempt or lease is created | the contract asserts zero attempts and zero leases |
| 13. No automatic retry or startup reconciliation is introduced | no production caller; `recover_dispatch()` untouched and uncalled |
| 14. PostgreSQL readback proves the final disposition | every assertion read back through an independent session |
| 15. Focused tests pass without attributable regressions | the focused sweep: no attributable regression |
| 16. Release remains HOLD | yes |

### Explicit confirmations

- No new operator authority was invented.
- No new public control plane was activated.
- No stale-heartbeat death inference was introduced.
- No automatic escalation or retry was enabled.
- No ownership takeover occurred.
- No startup reconciliation was activated.
- No provider request was made.
- No production resources were modified.
- No external sandbox guarantees were claimed.
- Restart recovery remains unqualified.
- Release remains HOLD.

## 24. Files changed

| File | Change |
|---|---|
| `guardian/agents/store.py` | `_insert_escalation()` (session-aware), `quarantine_coding_run_as_uncertain()`, `_existing_quarantine_disposition()`; `add_escalation()` refactored onto the helper with its behaviour preserved |
| `guardian/core/guardian_delegation_service.py` | `quarantine_uncertain_coding_run()` and `_authenticate_operator()` — the verified operator boundary |
| `tests/contracts/test_guardian_coding_run_uncertain_quarantine_contract.py` | new — 34 focused cases |
| `docs/architecture/guardian-delegation-loop-contract.md` | the authorized-quarantine section and its invariant |
| `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md` | operator reading of the disposition |
| `docs/architecture/proofs/runtime/2026-10-26-guardian-coding-uncertain-quarantine-proof.md` | this receipt |

`tests/contracts/test_guardian_coding_worker_terminal_fencing_contract.py` and
`tests/contracts/test_guardian_coding_worker_recovery_contract.py` were
authorized but **needed no change**: no assertion in either was invalidated by
this slice, and the strict-xfail tripwire was left exactly as it was.

## 25. Remaining recovery prerequisites

1. An **authorized production invocation path** for the disposition — the
   primitive is proven; exposing it is a separate, separately-authorized step.
2. A **bounded worker-startup reconciliation** that establishes, on its own
   terms, whether the triggering evidence is sufficient to justify a recovery
   action. Heartbeat staleness alone remains insufficient.
3. A **conservative account of external side effects** a fenced-out worker may
   already have produced, and the operator procedure that inspects them.
