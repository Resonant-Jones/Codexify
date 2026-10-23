# Guardian Coding Worker — In-Flight Interruption and Restart Recovery

**Evaluated commit:** `c43ad1c676c6f4c863086f0a0ffd357dda41c6fe`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-23
**Final classification:** **BLOCKED**

One coding-worker attempt was interrupted **uncleanly while demonstrably
in flight**, and the worker was then restarted against the same durable state.

**The safety half of the contract held and was proven live:** the restart
re-executed nothing. There was no second provider execution, no second
fixture mutation, no new authorized attempt, no replacement credential lease,
no duplicate terminal result, and no loss of the durable attempt record.

**The recovery half of the contract is not implemented and could not be
exercised.** The committed implementation has no durable representation of an
uncertain in-flight attempt and no restart-time reconciliation. The recovery
contract exists as a library in `guardian/core/guardian_dispatch.py` whose
recovery functions have **no production caller**. A crashed attempt is
indistinguishable, in durable state, from one that was never started.

This is a recovery proof, not a recovery implementation. No runtime behaviour
was changed.

---

## 1. Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Evaluated HEAD | `c43ad1c676c6f4c863086f0a0ffd357dda41c6fe` |
| `git merge-base --is-ancestor c43ad1c67 HEAD` | true (HEAD is the evaluated commit) |
| Working tree | clean |
| Functional canary receipt | `docs/architecture/proofs/runtime/2026-10-22-guardian-service-credential-live-proof.md`, present at `c43ad1c67` |
| Build context | `git archive c43ad1c67`, restricted to the paths the Dockerfile consumes, `.dockerignore` exclusions applied by hand, no credential material |

The application source in the build context was verified byte-identical to the
evaluated worktree for `guardian/db/models.py`,
`guardian/core/guardian_delegation_service.py`,
`guardian/agents/execution_credentials.py`, `guardian/workers/coding_worker.py`,
`guardian/core/guardian_dispatch.py`, and `backend/Dockerfile`.

## 2. Proof images

| Image | Identity | Size |
|---|---|---|
| `codexify-backend-runtime:recov-20261023` | `sha256:644d131b8a1a5cf4ad7ee891e54168bd4b309f43fb94fbc91e7105b3da4f9c9f` | 4.79 GB |
| `codexify-worker-coding-runtime:recov-20261023` | `sha256:6b7e2170b03d799ff8a1d8f0083fcdbac3271ee8a055e739195040de466363e7` | 5.30 GB |

Built through the Docker daemon's BuildKit endpoint, because the buildx CLI
unconditionally renames a builder activity file and `rename`-over is denied by
this sandbox, while the classic builder silently skips this Dockerfile's
`RUN python - <<'PY'` heredocs. Normal image tags were not touched:
`:latest` = `7a08e1defa43` / `a3177274d0b5`; `git-proof-a70ca1465` =
`891cb0f57f77` / `40e8b035e9b7`.

## 3. Disposable topology

| Resource | Canary | Binding |
|---|---|---|
| Compose project | `codexify_recov_canary_20261023` | dedicated |
| PostgreSQL 15 | `…-db-1` | `127.0.0.1:15453` only |
| Redis 7 | `…-redis-1` | `127.0.0.1:16400` only |
| Backend | `…-backend-1` | `127.0.0.1:18900` only |
| Coding worker | `…-worker-coding-1` | no ingress |
| Volumes | pgdata, redisdata, data, worktrees | dedicated |

No production database, Private Preview volume, user workspace, operator
credential store, or Pi authentication directory was mounted or shared. The
Private Preview served 200 on `/` and `/health` throughout.

**Synthetic context.** Account `canary-recov-20261023`; Project id `1`
(`General`, created by the product's own `seed_account_default_projects`);
Chat Thread id `1`; source message id `1`; repository binding
`eecf3c7b-2466-4276-b9d5-b60753971fad` → `/worktrees/canary-fixture`;
fixture repository head `7492b82c18e1a3e5da6c7aff1bc3994fc82d2ea7`. The
Alembic graph reached its actual head `f0d7c4b2a198`.

**Credential posture.** The same dedicated DeepSeek test key used by the
functional canary — byte-distinct from every operator credential, compared by
equality only, with no value, prefix, suffix, length, or fingerprint ever
emitted. Registered through Guardian's canonical custody path as
`owner_scope=service`, `owner_id=codexify-service`,
`funding_route=codexify_metered`, `source_class=service_api_key`,
`provider_id=deepseek`, `usage_policy_ref=usage-policy-codexify-metered`,
`allowed_account_ids=[canary-recov-20261023]`,
`allowed_model_ids=[deepseek-v4-flash]`, reference
`ccr_a5494474471a4f3289e8dbd740e7759c`. The account-scope HTTP route was
deliberately not used.

## 4. The recovery contract as implemented

Read from the source, not assumed:

* **Durable dispatch states** — `GuardianDispatchState` in
  `guardian/core/guardian_dispatch.py`: `PENDING`, `DISPATCHED`, `RUNNING`,
  `SUCCEEDED`, `FAILED`, `UNCERTAIN`, `QUARANTINED`, plus `CANCELLED`.
* **Attempt states** — the `agent_run_attempts` / `agent_run_steps` tables.
  On this path the worker writes **no** attempt or step rows; the attempt is
  represented by the task's `attempt_id` and the credential-lease row.
* **Worker acceptance** — the queue item is consumed destructively; acceptance
  is observable only through the task event stream
  (`task.created` → `task.worktree_created` → `task.running`).
* **Queue acknowledgement** — the final `task.completed` event. Absent on an
  interrupted attempt.
* **Execution lease lifecycle** — `coding_execution_credential_leases`, two
  minute lifetime, `owner_scope`/`owner_id` carried from the credential row.
* **Heartbeat / timeout** — the worker heartbeats the **worktree** lease, not a
  Guardian dispatch record. `coding_worktree_leases` had **0 rows**: the
  production code never calls `create_lease`; only the store's own tests do.
* **Worker startup reconciliation** — **none**. `run_worker_loop()` starts a
  fresh `CodingWorker` and calls `poll_once()`; there is no scan for prior
  accepted attempts.
* **Uncertain-outcome representation** — `UNCERTAIN` and `QUARANTINED` exist
  in `GuardianDispatchState`, but `guardian/db/models.py` has **no column or
  table** for them, and `observe_liveness`, `classify_dispatch_health`, and
  `recover_dispatch` have **no production caller**. Only
  `build_dispatch_record` and `mark_dispatched` are called, at dispatch time,
  in memory.
* **Retry authorization** — `recover_dispatch` refuses to re-dispatch without
  a fencing token (`guardian_dispatch_recovery_requires_fencing`) or an
  explicit operator authorization
  (`guardian_dispatch_recovery_requires_operator_authorization`); a recovery
  attempt must be a *new* attempt with a new attempt id, a new binding, and a
  freshly issued lease. Recovery never executes the original task.
* **Operator-visible recovery evidence** — the `guardian_dispatch.py`
  contract and its unit tests.

**The four situations the contract distinguishes:**

1. *Work never accepted* — no queue consumption, no lease, no worktree.
2. *Work accepted, execution not started* — `task.created` only.
3. *Work started, outcome uncertain* — **the case this proof targets.**
4. *Work completed, terminal acknowledgement not persisted* — `task.completed`
   present but the durable run record not updated.

**Intended transition after unexpected worker termination** (module
docstring): *quarantine-and-escalate* — an attempt whose liveness is unproven is
marked **uncertain** and escalated, never silently re-dispatched. A missing
heartbeat is **uncertain, not lost**; the attempt may still be executing.

## 5. Git worktree isolation — enabled and verified real

`CODING_WORKER_WORKTREE_ISOLATION=true` was set on the worker. The isolation
identity is **observable, not inferred from the flag**:

* the worktree was created at
  `/worktrees/canary-fixture/.codexify/coding-worktrees/run_a3cc96a0cfe641b4-gct_79fbda2f62244879-gat_6de2ea75c4e9486b`
  — the run, coding-task, and attempt identities are in the path;
* `task.worktree_created` was emitted with `worktree_path` and `base_head`
  `7492b82c…`;
* the worktree existed on disk with its own base commit, and the source
  fixture repository stayed **clean** with **0** `canary-ok:` lines, while the
  worktree carried the single mutation.

This closes the `worktree_id=null` observation from the functional canary. The
`worktree_id` / `worktree_path` **columns on `agent_runs` remained NULL** even
after the worktree was created: the worker populates them only on the
terminal write, so during an in-flight attempt the worktree identity is
carried by the event stream and the filesystem, not by the run row.

## 6. The exact interruption boundary

Deterministic, and crossed in this order:

```
durable dispatch            agent_deployments.spec_json persisted
  → worker acceptance       task dequeued (destructive), task.created emitted
  → worktree created        task.worktree_created emitted, lease row written
  → execution started       task.running emitted, adapter entered
  → side effect performed   canary_marker.txt mutated inside the worktree
  → [INTERRUPTION POINT]    adapter blocked; no terminal outcome written
```

The interruption point is established by an out-of-band marker written by the
adapter itself, so the harness *knows* the boundary was crossed rather than
inferring it from timing. The marker recorded:

```
reached                   true
cwd                       …/.codexify/coding-worktrees/run_…-gct_…-gat_…
mutation_written          true
read_only                 false
reasoning_effort_requested  off
identity.provider_id      deepseek
identity.model_id         deepseek-v4-flash
identity.harness_id       pi
identity.attempt_id       gat_6de2ea75c4e9486b
identity.credential_owner_scope  service
identity.funding_route    codexify_metered
```

**Instrumentation disclosure.** The provider adapter was substituted at
runtime by a controlled seam outside the tracked repository — the same shape
the repository's own worker test uses
(`monkeypatch.setattr(coding_worker, "ADAPTERS", …)`). No file in the image
was modified and no runtime implementation was overlaid. Everything else was
the real machinery: the real worker loop, the real Redis queue and its
destructive consumption, the real database, agent store, run/deployment
persistence, the real Git worktree isolation, the real credential-lease
resolution, and the real binding verification.

**Because the provider exchange was synthetic, this proves recovery behaviour
under the contract it actually exercises. It is not, and is not described as,
a live DeepSeek recovery proof.** Real provider executions in this run: **0**.

## 7. Identities

| Entity | Identity |
|---|---|
| Intent | `gdi_…` (accepted, `approval_state=approved`, `approval_mode=scoped_auto`) |
| Run | `run_a3cc96a0cfe641b4` |
| Deployment | `dep_89632cc141a4463f` |
| Coding task | `gct_79fbda2f62244879` |
| Queue task | `ffb4f47a-e1c1-41af-92b4-ef5c30778c4f` |
| Attempt | `gat_6de2ea75c4e9486b` |
| Execution binding | `xeb_6d35ed2512d043b5a208bdbc936b13a5` |
| Credential lease | `cl_b80cb1f2e8d74135a56950faa86cd74b` (owner `service` / `codexify-service`, issued 10:06:04, expires 10:08:04) |
| Worktree | `…/coding-worktrees/run_a3cc96a0cfe641b4-gct_79fbda2f62244879-gat_6de2ea75c4e9486b` |
| Fixture repository | `7492b82c18e1a3e5da6c7aff1bc3994fc82d2ea7` |

Binding content: provider `deepseek`, model `deepseek-v4-flash`, harness `pi`,
`reasoning_effort=off`, `schema_version=2`, `credential_owner_scope=service`,
`credential_owner_id=codexify-service`, `credential_source_class=service_api_key`,
`funding_route=codexify_metered`, `allowed_paths=(".",)`, `max_attempts=1`.

## 8. Before the crash

| Evidence | Value |
|---|---|
| `agent_runs.status` | `queued` |
| `agent_runs.worktree_id` / `worktree_path` | `NULL` / `NULL` |
| `agent_runs.started_at` / `ended_at` / `error` | `NULL` / `NULL` / `NULL` |
| `agent_run_attempts` rows | 0 |
| `agent_run_steps` rows | 0 |
| `agent_run_artifacts` rows | 0 |
| Credential leases for the attempt | 1 (service / `codexify-service`) |
| `coding_worktree_leases` rows | 0 |
| Source thread messages | 1 (the authored request) |
| Run event stream | `task.created`, `task.worktree_created`, `task.running` — **no `task.completed`** |
| Source fixture repository | clean; 0 `canary-ok:` lines; head `7492b82c` |
| Isolated worktree | present; `M canary_marker.txt`; **1** `canary-ok:` line; no new commit |
| Worker container | `running exit=0` |

## 9. Crash method and after-crash state

**Method.** `docker kill --signal=KILL codexify_recov_canary_20261023-worker-coding-1`
— a deliberate unclean process termination, not the normal stop handler
(`run_worker_coding.py` installs a SIGTERM/SIGINT handler that terminates the
child gracefully; SIGKILL bypasses it entirely). The harness was PID 1 inside
the container.

**Observable state after the kill.** Container `exited exit=137 oom=false`
(137 = 128+9 = SIGKILL; `oom=false` confirms this was a deliberate kill, not
an OOM). PostgreSQL, Redis, and the backend container all remained running.
No task, attempt, lease, or run record was edited manually, and no replacement
task was submitted.

**Pre-crash vs post-crash diff: 67 leaf values compared, exactly 1 differs** —
`worker_container_state` (`running exit=0` → `exited exit=137`). Every durable
and runtime fact was byte-identical: the run row, the attempt/step/artifact
counts, the credential lease, the thread message list, the Redis keys and
queue lengths, the event stream, the source repository, and the isolated
worktree with its single mutation.

## 10. Worker restart

The same coding-worker service was restarted against the **same** disposable
PostgreSQL and Redis, with the **same** instrumentation (the same synthetic
adapter armed and ready). The restarted worker initialised, armed the
provider seam, polled the queue, and idled.

| Observation | Result |
|---|---|
| Worker readiness | initialised; provider seam armed; poll loop running |
| Adapter re-entry | **none** — the live marker file was never rewritten |
| Second provider execution | **0** (real: 0; synthetic: 0 after the crash) |
| Second fixture mutation | **0** — the worktree still has exactly **1** `canary-ok:` line, byte-identical diff to the pre-crash diff |
| Source fixture repository | still clean; still 0 `canary-ok:` lines |
| New commit | none; the worktree is still at base `7492b82c` |
| New authorized attempt | none — `agent_run_attempts` still 0 |
| Replacement credential lease | none — 1 lease in the whole database, the original, with `owner_scope=service` |
| Duplicate terminal result | none — `agent_run_artifacts` still 0 |
| Source-thread results | none — the thread still holds exactly 1 message, the authored request |
| Run event stream | unchanged — still `task.worktree_created`, `task.running`, no terminal event |
| Durable run record | unchanged — `status=queued`, `ended_at=NULL`, `error=NULL` |
| Worktree identity | preserved on disk with its mutation intact |
| Credential isolation | no credential was selected, re-issued, or substituted by the restarted worker |

**Post-crash vs post-restart diff: 68 leaf values compared.** The only
differences are the container's exit state and the fields my own capture
instrument could not re-read because I had deliberately emptied the live
marker file. Every database, queue, thread, and worktree fact was identical.

## 11. What the restart did *not* do — and why that matters

The restart did not re-execute. But it did not **reconcile** either: it found
an empty queue and had nothing to do. Nothing in the restarted worker
recognised the previously accepted work, because there is no code path that
does so.

**The durable state cannot distinguish an interrupted attempt from one that
never started.** After the crash the run row reads `status=queued` with
`started_at=NULL`, `ended_at=NULL`, `error=NULL`, zero attempt rows, zero
step rows, zero artifact rows, and one thread message. A task that was
dispatched and never picked up leaves the same durable shape. The only
durable evidence that work *had* started is:

* the run's Redis event stream, ending at `task.running` with no terminal
  event (a Redis stream, not PostgreSQL);
* the expired credential lease row (whose `expires_at` has passed);
* the worktree directory and its mutation, on the worker's local volume.

None of these is a durable, queryable *recovery state*. There is no
`uncertain` or `quarantined` column, table, or row, and no startup path that
would produce one.

This is exactly the condition the task spec names: *"If the current
implementation cannot represent an uncertain in-flight attempt durably, stop
with BLOCKED and identify the missing contract."* The contract exists
(`guardian/core/guardian_dispatch.py`, quarantine-and-escalate, with unit
tests), but it is a library with no production caller, and the states it
defines have no durable representation.

The consequence is a real, live risk that this proof makes concrete: the
absence of re-execution came from the queue item having been destructively
consumed, **not** from a check that recognised the attempt as uncertain. A
redelivery — the queue's own retry behaviour, a producer republishing, or an
operator-driven replay — would reach the worker with nothing to distinguish it
from fresh work, and the side effect would happen twice.

## 12. Canonical persistence readback

Read from PostgreSQL, the same tables the product reads:

| Fact | Value |
|---|---|
| Original run ID | `run_a3cc96a0cfe641b4` (survived) |
| Original attempt ID | `gat_6de2ea75c4e9486b` (survived) |
| Dispatch ID | `dep_89632cc141a4463f` (survived) |
| Execution-binding identity | `xeb_6d35ed2512d043b5a208bdbc936b13a5` (survived, owner `service`, funding `codexify_metered`) |
| Worker identity | container `codexify_recov_canary_20261023-worker-coding-1`; harness pid 1 |
| Worktree identity | `…/coding-worktrees/run_a3cc96a0cfe641b4-gct_79fbda2f62244879-gat_6de2ea75c4e9486b` (survived) |
| Lease identity | `cl_b80cb1f2e8d74135a56950faa86cd74b` (survived, expired) |
| Pre-crash durable state | run `queued`; 0 attempts/steps/artifacts; 1 lease; 1 thread message; 3 task events |
| Post-crash durable state | identical except the container exit state |
| Post-restart durable state | identical to post-crash |
| Recovery classification | **none recorded** — the run remains `queued`; no `uncertain`, no `quarantined`, no escalation |
| Queue disposition | the coding queue was consumed; no coding queue key remains; the only list is `codexify:queue:system` (1 unrelated entry) |
| Final attempt posture | **unresolved** — accepted, side-effected, never terminalised |
| Source-thread message count | 1 (the authored request); 0 results |
| Fixture status and diff | source repository clean; isolated worktree `M canary_marker.txt`, one added line, no commit |

## 13. Validation results

Focused checks against the evaluated worktree, on disposable PostgreSQL:

| Selection | Result |
|---|---|
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | pass |
| `tests/contracts/test_guardian_execution_binding_contract.py` | pass |
| `guardian/tests/agents/test_execution_credentials.py` | pass |
| `guardian/tests/agents/test_worktree_lease_store.py` | pass |
| `guardian/tests/workers/test_coding_worker.py` | 14 pre-existing failures |
| `guardian/tests/workers/test_coding_worker_regression_guard.py` | 1 pre-existing failure |
| **Total** | **162 passed, 15 failed** |

**Inherited failures identified by testcase and root cause.** The same two
worker files were re-run with the two producer files restored to their
pre-repair state (commit `e28dbcff9`, which already contains the restored UMS
ORM mappings, so the module graph still imports) and with the evaluated HEAD.
Compared on **identity and cause**, not counts:

* before: 93 tests, 15 failing
* after: 93 tests, 15 failing
* failing in both phases: **15** — identical identities
* failing only after: **0**
* failing only before: **0**
* causes that changed for a shared failure: **0**
* **REGRESSIONS: 0**

The causes are unchanged and are not caused by the credential-selection repair:
eleven `assert 'failed' == 'completed'` (the isolated-execution path never
reaches a terminal state), `assert 'task.failed' == 'task.completed'`,
`assert ['task.completed'] == [..., 'task.completed']`,
`assert [AgentExecuti…'attempts': 1}] == []`, `assert '?? .codexify/' == ''`,
two `assert False`, and
`store_coding_result was not called — worker did not reach the adapter
execution phase`.

**One of these is a genuine pre-existing defect in the worker, and it is
reported here rather than patched:**
`guardian/tests/workers/test_coding_worker.py::test_worker_records_campaign_attempt_ledger_and_work_order_markers`
fails with `NameError: name '_fetch_work_order' is not defined` — a missing
helper in `guardian/workers/coding_worker.py`, on the campaign-attempt-ledger
path. It is the same family of defect the adjacent regression-guard file
exists to catch. It is **not** in this task's authorized write surface.

**Full-suite status: NOT RUN.** The shared 7.7 GB Docker VM hosts the
operator's live Private Preview, and a prior monolithic run in that
environment exhausted the VM and restarted unrelated services. The focused
selection above, with the identity-and-cause comparison, is the retained
evidence.

## 14. Known limitations

* This is a **functional recovery proof**. It is **not** ADR-077 sandbox
  conformance, and it is not evidence of exactly-once provider execution or
  exactly-once side effects. The restart did not re-execute; that is not the
  same as the system proving it cannot.
* The provider exchange was **synthetic**. Real provider executions: **0**.
  This proves the recovery and re-execution behaviour of the queue, worker,
  persistence, and isolation machinery, not DeepSeek-facing behaviour.
* The Git mutation guard remains **detective, not preventive**.
  Provider-enforced filesystem, process, and network isolation remain
  unproven.
* The `agent_runs.worktree_id` / `worktree_path` columns are populated only
  on the terminal write, so during an in-flight attempt the worktree identity
  lives in the event stream and the filesystem, not in the durable run row.
* The adapter's previously empty `files_changed` report remains separately
  deferred, as instructed.
* The restart reconciled nothing, because no reconciliation path exists. The
  proof establishes the *absence* of a contract, not the behaviour of one.
* **Restart recovery of an accepted attempt remains unproven** in the positive
  sense: no attempt was recovered, because none was eligible to be.

## 15. ADR impact and invariants

* **ADR-020, ADR-065, ADR-069, ADR-077, ADR-093, ADR-094** — unchanged. No
  ADR was modified.
* The evidence bears directly on ADR-077 and the `guardian_dispatch.py`
  contract: the *specified* quarantine-and-escalate behaviour is not
  implemented in the runtime, and the task spec's requirement that an uncertain
  attempt be durably represented is not met.
* Invariants observed: Guardian owned the authorization; the credential's
  owner and funding route were truthful end to end; no ambient secret became
  task authority; reasoning effort stayed Guardian-owned (`off`); write scope
  could not widen (the mutation was confined to the isolated worktree, and
  the source repository stayed clean); one attempt remained one attempt; no
  unauthorized provider execution, mutation, lease, attempt, or result was
  produced; PostgreSQL remained canonical for the durable records; no success
  or release claim is made beyond the observed behaviour.

## 16. Cleanup

* Disposable worker and backend stopped; PostgreSQL and Redis containers
  removed; the dedicated Docker network removed; temporary worktrees and
  fixtures removed with the volumes.
* The disposable Guardian credential registration was revoked and its at-rest
  secret destroyed. The extracted key file was truncated to zero bytes.
* Normal image tags verified unchanged; the Private Preview verified healthy.
* Only secret-free evidence is retained. The **provider-side** key was *not*
  revoked, because that action was not separately authorized; no provider-side
  revocation is claimed.

## 17. Classification

**BLOCKED.** The interruption was deterministic and demonstrably in flight,
the termination was unclean, the durable identities survived, and the
restart produced **no** duplicate execution, mutation, attempt, lease, or
result. But the accepted recovery contract could not be exercised, because the
committed implementation **cannot represent an uncertain in-flight attempt
durably** and has **no restart-time reconciliation**: the recovery functions
in `guardian/core/guardian_dispatch.py` have no production caller, and the
`UNCERTAIN` / `QUARANTINED` states have no durable column, table, or row. A
crashed attempt is indistinguishable in durable state from one that never
started.

**The smallest remaining repair, in one sentence:** persist a durable
dispatch state for an accepted attempt that reaches an uncertain outcome, and
wire the existing `observe_liveness` / `classify_dispatch_health` /
`recover_dispatch` contract into a restart-time reconciliation path that
marks the attempt **uncertain** and escalates it, exactly as the module
docstring already specifies — without granting the restarted worker any
retry authority.

That repair is application-source work and is outside this task's authorized
write surface, so it is recorded as a prerequisite rather than performed.

### Distinguishing the results

* **Functional delegation** — PASS, proven separately in
  `2026-10-22-guardian-service-credential-live-proof.md` (`c43ad1c67`).
* **Interruption / recovery proof** — **BLOCKED** (this receipt). The safety
  half holds; the recovery-representation half is absent.
* **Git worktree isolation** — **evidence obtained**: real isolated
  worktree, identity observable, mutation confined, source repository clean.
  This is functional evidence, not a sandbox-conformance claim.
* **Provider-enforced sandbox conformance** — **not claimed**; unproven.
* **Beta release qualification** — **HOLD**.

### Confirmations

* No account-ownership misrepresentation — the credential stayed
  `service` / `codexify-service` / `codexify_metered` throughout.
* No unauthorized operator credential use — the key was the dedicated test
  key, byte-distinct from every operator credential.
* No application-source overlay or retry workaround — the only substitution
  was the provider adapter at runtime, disclosed above; no file in the image
  was modified.
* No production modification — the Private Preview served 200 throughout and
  its image digests and volumes are unchanged.
* No automatic second attempt — the restarted worker executed nothing.
* Conversational intake remains unavailable.
* Restart recovery remains unproven.
* Provider-enforced sandbox isolation remains unproven.
* Release qualification remains **HOLD**.

### Artifacts

* Proof receipt:
  `docs/architecture/proofs/runtime/2026-10-23-guardian-coding-worker-interruption-recovery-proof.md`
* Evaluated commit: `c43ad1c676c6f4c863086f0a0ffd357dda41c6fe`
* Proof images: `sha256:644d131b8a1a5cf4ad7ee891e54168bd4b309f43fb94fbc91e7105b3da4f9c9f`
  (backend), `sha256:6b7e2170b03d799ff8a1d8f0083fcdbac3271ee8a055e739195040de466363e7`
  (worker)
* Run / deployment / task / attempt / binding / lease:
  `run_a3cc96a0cfe641b4` / `dep_89632cc141a4463f` / `gct_79fbda2f62244879` /
  `gat_6de2ea75c4e9486b` / `xeb_6d35ed2512d043b5a208bdbc936b13a5` /
  `cl_b80cb1f2e8d74135a56950faa86cd74b`
* Credential reference: `ccr_a5494474471a4f3289e8dbd740e7759c` (revoked at
  teardown, at-rest secret destroyed)
* The functional canary receipt and both historical BLOCKED receipts are
  unchanged.
