# Guardian Coding Run — Liveness Classification from Canonical Evidence

**Base commit:** `063d10ab7e105a4d6b807a832cb4a372b5b30d5d`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-26
**Final classification:** **PASS** (release remains **HOLD**)

Durable ownership says *who* holds a run. The claim-scoped heartbeat says that
the holder was **still reporting**. Terminal fencing says who may *finish* it.
None of those is an interpretation. This slice adds the missing piece: a
**read-only, deterministic classification** of one coding run's canonical
liveness evidence, and nothing else.

**This slice is observational.** It introduces no worker-death classifier, no
expiry, no takeover, no automatic escalation, no automatic retry, and no
restart reconciliation. A stale heartbeat remains evidence of *uncertainty*, not
proof that the worker died. Nothing here is wired into startup.

---

## 1. Evaluated commit

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Base HEAD | `063d10ab7e105a4d6b807a832cb4a372b5b30d5d` |
| Working tree at the base commit | clean (tracked) |
| `alembic heads` | **exactly one** head: `d86f2a4b1c90` — unchanged |
| New migration | **none** |
| New persisted status | **none** |
| Provider | **none** — no provider request, no live DeepSeek canary |
| Production resources | **none touched** — every database used was disposable and local |

## 2. Effective classifier call graph

The classification **extends the existing dispatch observation path**; it does
not create a competing service.

| Operation | File | Role |
|---|---|---|
| `observe_liveness()` | `guardian/core/guardian_dispatch.py` | existing: records an observed liveness signal on a dispatch record |
| `classify_dispatch_health()` | `guardian/core/guardian_dispatch.py` | existing: classifies an attempt's liveness without assuming it is lost |
| `recover_dispatch()` | `guardian/core/guardian_dispatch.py` | existing: decides what recovery does — **unchanged**, and not activated |
| `assert_dispatch_ready()` | `guardian/core/guardian_dispatch.py` | existing: the pre-queue authority check — unchanged |
| `AgentStore.get_coding_run_liveness_snapshot()` | `guardian/agents/store.py` | **new**: the canonical read-only projection |
| `classify_coding_run_liveness()` | `guardian/core/guardian_dispatch.py` | **new**: the classification |

The new classification reuses the accepted dispatch vocabulary. It reaches
`executing`, `dispatched`, `uncertain`, `quarantined`, `completed`, `failed`
and `cancelled` — all existing `GuardianDispatchState` members — and adds an
explicit *evidence* label for the finer distinction. No canonical verdict is
redefined, and the dispatch integration contract proves that every verdict the
classification can reach is an existing one.

## 3. Canonical snapshot fields

`AgentStore.get_coding_run_liveness_snapshot(run_id, *, user_id=None, observation_instant=None)` returns:

```
run_id
deployment_id
status
started_at
ended_at
coding_worker_instance_id
coding_worker_claim_id
coding_worker_last_heartbeat_at
observed_at
```

Every field comes from **one** PostgreSQL statement, so the run's status,
ownership identities, heartbeat, and the observation instant share a single
consistent snapshot. Mixing timestamps from separate reads could produce a
misleading ordering.

The projection carries no credential material, no secret, no raw prompt, and no
transcript content. It is **not** the WebUI coding-run projection
(`get_coding_run_snapshot()`): that one is a read model assembled from several
separate reads, carries the latest result, and carries no ownership or
heartbeat facts. This one is a single consistent read of the liveness evidence
and nothing else.

The optional `user_id` applies the same read-authorization boundary the other
account reads apply: the deployment's asserted user and the thread's user must
both match, and a run that does not belong to the reader is reported as absent
rather than classified. No new public endpoint was exposed.

## 4. Database observation-clock behavior

`observed_at` is the **database** clock (`now()`), read in the same statement
as the run row. The application host clock is never the authoritative
comparison clock. `observation_instant` exists only so a contract test can pin
the observation instant and exercise the staleness boundary exactly; production
callers omit it.

Measured on this environment, the application clock runs about **5.6 ms**
ahead of the database clock. That difference is why a comparison that spans
the two clocks is tolerant and a comparison inside one clock is exact — see
§6.

## 5. Heartbeat cadence source

The production cadence is the coding worker's claim-scoped heartbeat:

```python
# guardian/workers/coding_worker.py
CODING_RUN_HEARTBEAT_INTERVAL_SECONDS = float(
    os.getenv("CODING_RUN_HEARTBEAT_INTERVAL_SECONDS", "15")
)
```

`guardian/core/guardian_dispatch.py` restates the value as
`CODING_RUN_HEARTBEAT_INTERVAL_SECONDS = 15` rather than importing the worker
module, so that `guardian.core` never depends on a worker module. The contract
asserts that the two agree, so the restatement cannot drift silently.

## 6. Staleness horizon calculation

```
stale_after_seconds = max(60, 3 * production_heartbeat_interval_seconds)
                    = max(60, 3 * 15)
                    = 60 seconds
```

No governing accepted contract defines a different observation horizon, so the
formula in the task specification governs.

It is an **observation threshold**, not an execution-lease expiry and not a
death oracle. The contract asserts that no `worker_dead_at`,
`ownership_expires_at`, or `automatic_takeover_at` exists on the verdict, and
that no new persisted status was minted.

**The two-clock tolerance.** The run's timeline spans two clocks: `started_at`
is stamped by the application, the heartbeat and `ended_at` by the database. A
heartbeat written in the same transaction as `started_at` therefore legitimately
sits a few milliseconds *before* it. A comparison that tolerated only that
would be a false positive on every freshly accepted run. So:

- comparisons that span the two clocks (`started_at` vs the heartbeat,
  `started_at` vs `ended_at`) tolerate
  `CODING_RUN_LIVENESS_CLOCK_SKEW_TOLERANCE_SECONDS = 5`;
- comparisons inside one clock (the heartbeat vs the observation instant, the
  heartbeat vs `ended_at`) are exact.

## 7-13. The classifications

| Evidence | Canonical record | Dispatch verdict | Meaning |
|---|---|---|---|
| `never_accepted` | `queued`, no claim | `dispatched` | never durably accepted — **not** an abandoned execution |
| `recently_observed` | `running`, owner + claim, heartbeat inside the horizon | `executing` | the claim recently renewed liveness — **not** proof a process exists |
| `stale_uncertain` | `running`, owner + claim, heartbeat older than the horizon | `uncertain` | recent liveness evidence is missing — **not** a determination that the worker died |
| `missing_evidence` | `running` without a usable owner, claim, or heartbeat | `uncertain` | insufficient evidence — nothing is inferred about whether work started |
| `already_resolved` | `succeeded` / `failed` / `canceled` | `completed` / `failed` / `cancelled` | a canonical terminal disposition already exists |
| `already_escalated` | `escalated` | `quarantined` | an authoritative escalation disposition already exists |
| `inconsistent` | a record that contradicts itself | `uncertain` | the record requires inspection; it is never repaired automatically |
| `unobservable` | no record, or unreachable persistence | *(none)* | no observation could be made |

A record is **inconsistent** when it carries a partial ownership pair, when a
`queued` run carries accepted ownership, when its timestamps are impossibly
ordered, or when its heartbeat sits in the future beyond the tolerance. The
canonical schema refuses a half-written ownership pair, so that state is
reachable only in a record written outside the acceptance contract — the
classifier still reads it conservatively.

An **escalated** run is classified as *rejected-by-another-authority*, not as
"already terminal": an escalation is a disposition, and a classification never
duplicates it.

## 14. Concurrent-worker isolation

| Scenario | Result |
|---|---|
| Worker A's run is stale, Worker B's run is fresh | A → `stale_uncertain`, B → `recently_observed` |
| One worker instance owns two runs, each with its own claim | classified **per run**, from each run's own heartbeat |

The classification is scoped to the exact `run_id` and the exact
`(coding_worker_instance_id, coding_worker_claim_id)` pair recorded on it. A
global coding-worker heartbeat would not be a substitute, and none was
introduced: the coding worker still publishes no Redis worker heartbeat.

## 15. Controlled worker-disappearance observation

A controlled synthetic execution against a real disposable PostgreSQL: a run is
accepted, the worker instance and claim are persisted, the heartbeat is
persisted, and the worker disappears without renewing. The canonical state is
then read and classified at controlled observation instants.

```
--- observed immediately after the worker disappeared ---
  status                : running
  worker instance       : cwi_disappearance_worker
  claim                 : cwc_disappearance_claim
  heartbeat             : 2026-10-26 11:18:17.228765+00:00
  observed_at           : 2026-10-26 11:18:17.232625+00:00
  heartbeat age (s)     : 0.004
  evidence              : recently_observed
  dispatch verdict      : executing

--- observed past the staleness horizon ---
  heartbeat age (s)     : 61.003
  evidence              : stale_uncertain
  dispatch verdict      : uncertain
  reason                : guardian_coding_run_liveness_stale

--- the canonical state after the observation ---
  status                : running
  ended_at              : None
  error                 : None
  escalations           : 0
  coding_result artifacts: 0
  source-thread messages : 0
```

| Observation instant | Classification | Dispatch verdict |
|---|---|---|
| inside the horizon | `recently_observed` | `executing` |
| beyond the horizon | `stale_uncertain` | `uncertain` |

What does **not** happen: the run is not declared dead, not escalated, not
retried, not canceled. Its status stays `running`, no escalation row is
created, no recovery attempt appears, no result is fabricated. A stale
classification is evidence, and evidence does not dispose of a run. The log is
kept at `.scratch/liveness/disappearance-observation.log`.

## 16. Obsolete-test repair

`tests/contracts/test_guardian_coding_worker_recovery_contract.py` carried
`test_the_canonical_run_record_carries_ownership_but_no_liveness_signal`,
which asserted that `agent_runs` contains no column whose name contains
`heartbeat`. The heartbeat column landed in the previous slice, so that
assertion had become obsolete.

It was **repaired, not deleted**, and renamed to
`test_the_canonical_run_record_carries_ownership_and_liveness_evidence`. It
now verifies the present architecture:

- `agent_runs` has durable worker identity
  (`coding_worker_instance_id`);
- `agent_runs` has durable claim identity (`coding_worker_claim_id`);
- `agent_runs` has a claim-scoped heartbeat
  (`coding_worker_last_heartbeat_at`);
- heartbeat evidence alone is **not** proof of worker death: there is no
  `expires`, `lease`, `takeover`, or `dead` column, and the existing classifier
  still marks stale evidence *uncertain* rather than lost;
- ownership cannot be automatically transferred: no takeover or expiry
  column exists, and the recovery path still quarantines rather than
  re-dispatching;
- restart reconciliation remains unimplemented: the strict-xfail tripwire is
  untouched.

A second stale assertion, `test_the_coding_worker_publishes_no_heartbeat`, was
renamed `test_the_coding_worker_publishes_no_redis_worker_heartbeat` and
corrected: the coding worker has **no Redis** worker heartbeat, and its liveness
signal is the durable, claim-scoped heartbeat in PostgreSQL.

The recovery contract's module docstring was corrected for the same reason.

## 17. Strict-xfail recovery tripwire result

```
tests/contracts/test_guardian_coding_worker_recovery_contract.py::
    test_a_restarted_worker_reconciles_an_abandoned_accepted_run  XFAIL
```

**The tripwire remains strict-xfail and unresolved.** It was not marked
passing, not removed, and not weakened: restart reconciliation is still not
implemented, so the behaviour it specifies still does not happen.

## 18. Before-and-after evidence

Isolated scratch tree: `.scratch/liveness-red-v1`, built from
`git archive 063d10ab7` (only `.claude/commands` is excluded — the desktop
permission gate blocks those three paths).

| File | sha256 (first 16) | matches `063d10ab7` |
|---|---|---|
| `guardian/core/guardian_dispatch.py` | `9600051b93763272` | yes |
| `guardian/agents/store.py` | `ebbe9e37c374a095` | yes |

Import origins were asserted inside the scratch tree:

```
dispatch: .scratch/liveness-red-v1/guardian/core/guardian_dispatch.py
store   : .scratch/liveness-red-v1/guardian/agents/store.py
has classify_coding_run_liveness: False
has get_coding_run_liveness_snapshot: False
```

| Run | Result |
|---|---|
| **baseline** (`063d10ab7`, unmodified) | **29 failed, 2 passed** |
| **this evaluation** | **31 passed** |

**The two cases that pass on the baseline are the two that assert the existing
contract is unchanged** — `test_the_existing_dispatch_classifier_is_unchanged`
and `test_the_restart_reconciliation_tripwire_remains_unresolved`. That is the
honest shape for this slice: it adds a capability and changes nothing.

The red causes are **absent capabilities, not behavioural regressions**:

| Cause | Count |
|---|---|
| `AttributeError: 'AgentStore' object has no attribute 'get_coding_run_liveness_snapshot'` | 25 |
| `AssertionError: the baseline has no claim-scoped liveness classification: the canonical ownership and heartbeat evidence is not reachable` | 3 |
| `AttributeError: module 'guardian.core.guardian_dispatch' has no attribute 'CodingRunLivenessVerdict'` | 1 |

**No historical runtime regression is claimed.** This is an observational
capability: the baseline could not answer "is this run still alive?" from
canonical evidence at all. How the existing dispatch classifier handled the
now-persisted ownership and heartbeat fields on the baseline is therefore
precisely *not at all*: `GuardianDispatchRecord` has no worker-identity field,
`classify_dispatch_health()` reads only caller-supplied `last_heartbeat_at` and
`lease_expires_at` inputs rather than the canonical row, and the store exposed
no canonical liveness projection. The classification is new reach, not a
repair of a wrong answer.

## 19. Focused validation

| Path | Result |
|---|---|
| `tests/contracts/test_guardian_coding_run_liveness_contract.py` | **31 passed** |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | **19 passed, 1 xfailed** |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | **21 passed** |
| `tests/contracts/test_guardian_coding_worker_terminal_fencing_contract.py` | 23 passed |
| `tests/contracts/test_guardian_coding_worker_heartbeat_contract.py` | 25 passed |
| `tests/contracts/test_guardian_coding_worker_ownership_contract.py` | 26 passed |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | 19 passed |
| `tests/contracts/test_guardian_delegation_phase2a_contract.py` | passed |
| `tests/contracts/test_guardian_delegation_phase3_delivery_contract.py` | passed |
| `tests/contracts/test_guardian_delegation_approval_cancel_contract.py` | passed |
| `guardian/tests/workers/test_coding_worker.py` | 14 inherited failures, otherwise passed |
| `guardian/tests/workers/test_coding_worker_regression_guard.py` | 1 inherited failure |
| `guardian/tests/agents/` | passed |
| `tests/agents/test_execution_ledger_store.py` | passed |
| **Focused sweep total** | **455 passed, 15 failed, 1 xfailed** |

The focused sweep's 15 failures are exactly the inherited ones — 14 in
`guardian/tests/workers/test_coding_worker.py` and 1 in
`guardian/tests/workers/test_coding_worker_regression_guard.py` — and the
previous slice's 16th failure (the obsolete recovery gate case) is **gone**:
this task was authorized to repair that file, and did.

### The monolithic backend gate

The repository's default backend gate — `pytest -v` over `tests/` (per
`pytest.ini`) — was run against the evaluated tree with disposable PostgreSQL.
The Private Preview stayed healthy (`127.0.0.1:8081/health` → 200) throughout.

| Run | Result |
|---|---|
| baseline (`063d10ab7`, recorded by the terminal-fencing slice) | **136 failed, 8823 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** |
| this evaluation | **135 failed, 8856 passed, 108 skipped, 36 xfailed, 11 xpassed, 40 errors** (24:46) |

Compared by **exact failure identity**:

| Category | Count |
|---|---|
| Shared identical failure identities | **135** |
| Failures not in the baseline | **0** |
| Failed only in the baseline | **1** — `test_the_canonical_run_record_carries_ownership_but_no_liveness_signal`, the obsolete assertion this task was authorized to repair |

**Zero regressions, and one inherited failure closed.** The +33 passed are this
slice's new coverage (31 liveness cases, the dispatch vocabulary-reuse case) and
the repaired recovery contract. The 5 collection errors (`fakeredis`, `mcp`, and
two duplicate-basename modules) are identical in every run and are
local-environment gaps, not regressions.

## 20. Inherited failures

The inherited failures are the same ones the terminal-fencing slice recorded:
14 in `guardian/tests/workers/test_coding_worker.py` and 1 in
`guardian/tests/workers/test_coding_worker_regression_guard.py`, identical by
exact test identity. They are predominantly this sandbox's own limits — git
worktree creation is denied on this filesystem — plus one genuine pre-existing
product defect, reported and **not** patched:

```
NameError: name '_fetch_work_order' is not defined
```

in `guardian/workers/coding_worker.py` (campaign-attempt-ledger path).

The previously reported recovery-contract discrepancy is **closed**: that file
is authorized in this task, its obsolete assertion was repaired, and it is now
green.

## 21. Remaining worker-death authority gap

The classification stops where the authority begins. What is still missing:

1. **An independently justified reconciliation trigger.** Nothing may treat a
   stale heartbeat as a death oracle. The next task must justify a trigger on
   its own terms and establish an atomic, operator-visible uncertain-outcome
   disposition.
2. **Fencing.** A stale worker may still attempt a terminal write; the
   claim-fenced terminal persistence of the previous slice is what makes that
   write refuse. Without an equivalent fence for any *other* effect, a
   superseded worker can still mutate a worktree.
3. **External side-effect accounting.** Nothing in the canonical record says
   whether the harness finished a provider request, mutated an isolated
   worktree, produced files, started a subprocess, made a network request, or
   committed an external change.
4. **A liveness verdict, not just evidence.** `stale_uncertain` is the honest
   ceiling: "recent liveness evidence is missing". Turning that into a
   disposition is the next task's job, and it must remain safe against an
   active peer worker, a late worker terminal result, a concurrent escalation,
   and an already completed run.

## 22. Absence of recovery side effects

The classification is read-only and is not wired into anything:

- `CodingWorker.__init__()`, `CodingWorker._initialize_worker()`,
  `run_worker_loop()` and `poll_once()` do not call it.
- `recover_dispatch()` is not activated for production runs.
- No recovery action happens at startup.
- The contract asserts, against an independent database session, that
  classification changes no status, creates no escalation, touches no queue
  task, touches no credential lease, creates no coding-result artifact, and
  delivers no source-thread result.

Verified against the production sources:

```
$ grep -rn "classify_coding_run_liveness\|get_coding_run_liveness_snapshot" \
      --include=*.py guardian/ backend/ scripts/ services/
(no production caller)

$ grep -rn "recover_dispatch(" --include=*.py guardian/ backend/ scripts/
(no production caller)
```

Both the classifier and the snapshot exist only as a projection and a
classification, reachable only from a caller that chooses to ask.

## 23. PASS/HOLD/BLOCKED verdict

**PASS** for the slice as specified:

1. Read-only canonical liveness snapshots — **yes**.
2. An explicit, documented observation horizon — **yes**, 60 seconds, derived from the cadence.
3. Comparison against the database clock — **yes**, `observed_at` is `now()`.
4. Per-run, claim-scoped classification — **yes**.
5. Fresh activity distinguished from current process existence — **yes**.
6. Stale heartbeat classified conservatively — **yes**, `stale_uncertain`.
7. Historical missing evidence remains unknown — **yes**.
8. Terminal runs excluded from abandonment inference — **yes**.
9. Escalated runs retain their established disposition — **yes**.
10. Concurrent workers independently classified — **yes**.
11. Existing dispatch authority reused — **yes**, no new verdict vocabulary.
12. Obsolete recovery assertion corrected — **yes**.
13. Strict-xfail restart tripwire intact — **yes**, still xfail.
14. No new execution or recovery authority created — **yes**.
15. No database or queue mutation through classification — **yes**.
16. Focused validation has no attributable regressions — **yes**.
17. Release remains HOLD — **yes**.

### Explicit confirmations

- No new execution authority.
- No worker-death inference from heartbeat staleness alone.
- No ownership takeover.
- No automatic escalation.
- No automatic retry.
- No startup reconciliation.
- No real provider invocation.
- No production resources modified.
- No unsupported sandbox-conformance claim.
- Functional delegation remains feature-branch evidence.
- Restart recovery remains BLOCKED.
- Release remains HOLD.

## 24. Files changed

| File | Change |
|---|---|
| `guardian/agents/store.py` | `get_coding_run_liveness_snapshot()` — the canonical read-only projection |
| `guardian/core/guardian_dispatch.py` | the cadence constant, the staleness horizon, the evidence vocabulary, `CodingRunLivenessVerdict`, and `classify_coding_run_liveness()` |
| `tests/contracts/test_guardian_coding_run_liveness_contract.py` | new — 31 focused cases |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | the obsolete liveness assertion repaired and renamed; the Redis-heartbeat assertion corrected; the module docstring corrected |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | the vocabulary-reuse case |
| `docs/architecture/guardian-delegation-loop-contract.md` | the liveness observation section, the recovery-gate wording, the new invariant |
| `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md` | operator reading of a liveness classification |
| `docs/architecture/proofs/runtime/2026-10-26-guardian-coding-run-liveness-classification-proof.md` | this receipt |

## 25. Remaining recovery prerequisites

1. An independently justified reconciliation trigger that a stale heartbeat
   cannot satisfy on its own.
2. An atomic, operator-visible uncertain-outcome disposition, safe against an
   active peer worker, a late worker terminal result, a concurrent escalation,
   and an already completed run.
3. A conservative account of the external side effects a fenced-out worker may
   already have produced.
