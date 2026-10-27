# Guardian Delegation Campaign — Consolidated Integration Assessment

**Date:** 2026-10-27
**Evaluated branch:** `feature/guardian-delegation-acceptance-axis`
**Evaluated commit:** `fa5e0ee14f12c293a58f3b3b283f081eb8b1ea57`
**Release posture:** **HOLD** (unchanged)

This is a **consolidation**, not a new slice. It reads the campaign's
committed code and its proof receipts and asks one question: *given the
integrated runtime state, what recovery work actually remains — and is any of
it worth another implementation slice?*

**Evidence boundary.** This assessment is code-and-receipt level. It contains
no live or Private Preview verification, because the host's Docker engine was
unavailable for the whole of this assessment (§7). Where a claim would need
runtime proof, it is marked as such rather than asserted.

---

## 1. The campaign chain

Nine commits on the feature branch, eight of them implementation slices and
one documentation commit. Evidence class: **D** = proven against disposable
PostgreSQL/Redis, **L** = proven live, **U** = unproven or deliberately
deferred.

| Slice | Commit | Established | Evidence |
|---|---|---|---|
| Durable worker ownership | `c2167aa24` | Accepted runs carry a durable worker instance and claim identity | D |
| Claim-scoped heartbeat | `0db31d705` | The owner renews a heartbeat from the database clock, under its claim | D |
| Claim-fenced terminalization | `063d10ab7` | First-committer-wins: a late worker cannot overwrite a newer decision | D |
| Liveness classification | `ab26381ba` | A conservative, read-only verdict vocabulary over canonical evidence | D |
| Atomic uncertain-outcome quarantine | `158ea8930` | An authorized disposition and its escalation evidence commit together | D |
| Operator invocation route | `80d46f86c` | `POST /api/guardian/delegations/runs/{run_id}/quarantine`, operator-authenticated | D, gated |
| Read-only startup review | `9b7784529` | One bounded, read-only observation at worker startup | D |
| Completed-run integrity | `fa5e0ee14` | A completed run keeps its artifact and source-thread result | D |
| Restart reconciliation | `4748892b4` | Recorded as **BLOCKED**, deliberately | deferred |

No **capability** established in this chain has been proven against a live
*supported deployment*. The October 23 interruption experiment did run against
a live container, and its safety half held there — the restart re-executed
nothing, there was no second provider execution, no duplicate terminal result,
and no loss of the durable attempt record — but it established a **BLOCKED**
outcome for recovery, not a capability. Every row marked **D** above is
disposable-infrastructure evidence, and the operator route adds the further
constraint that its feature flag is **off by default** and quarantined by
**every** supported profile.

## 2. The integrated runtime state

The canonical run status vocabulary is `queued`, `running`, `escalated`,
`canceled`, `failed`, `succeeded`. Mapped onto the recovery problem, and onto
who can see each state:

| Canonical situation | Row status | Seen by the startup review? | Disposition authority |
|---|---|---|---|
| Never durably accepted | `queued` | **No** — outside the review population | none, and none needed |
| Accepted, recent heartbeat | `running` | Yes → `recently_observed` | none needed |
| Accepted, stale heartbeat | `running` | Yes → `stale_uncertain` | **operator**, via the quarantine route |
| Accepted, incomplete ownership/heartbeat | `running` | Yes → `missing_evidence` | **operator** |
| Accepted, self-contradicting record | `running` | Yes → `inconsistent` | **operator**; never auto-repaired |
| Terminal | `succeeded` / `failed` / `canceled` | No — outside the review population | already authoritative |
| Already escalated | `escalated` | No — outside the review population | already authoritative |

**The one hole in that table is the first row.** The coding queue is
destructive and at-most-once. `claim_run_for_acceptance()` writes the run row
**only** on acceptance; a refusal returns `RUN_ACCEPTANCE_REJECTED` and
leaves the row at `queued`. The startup review's population is `running`. So a
task consumed from the queue and never durably accepted leaves a `queued` row
that no reviewer will ever see. This is precisely the campaign's named
unestablished item, *"complete detection of work lost before durable
acceptance"*, and it is real.

But note *what it is*: the row is not lost, and the run is not unresolved —
it never started. Nothing about it is ambiguous, and no disposition is owed
to it. What is missing is the **knowledge that it was ever enqueued**,
because destructive dequeue erases that.

The October 23 interruption receipt reached the same conclusion from the
opposite direction, and records it in the durable-state vocabulary:

> Recovery classification | **none recorded** — the run remains `queued`; no
> `uncertain`, no `quarantined`, no escalation

That receipt's finding — *"a crashed attempt is indistinguishable, in durable
state, from one that was never started"* — is the same hole, observed before
the review existed. The review does not close it, and it is not supposed to:
the review's population is `running`, by design, because a `queued` row is
not an unresolved execution.

## 3. The five candidate next gates, evaluated

The campaign's own "Next Gate" section listed five candidates and warned
against admitting all of them by default. Against the integrated state:

### (a) Independently established worker-termination evidence — **not a product capability**

The system's correct answer is already the one it gives: *recent liveness
evidence is missing*. It cannot do better, because termination is a fact about
a process, a machine, or a provider session — none of which this runtime can
observe for another host. Inferring it from elapsed time would be a guess
that produces false positives on blocked workers, and from an empty queue
would be a guess that cannot distinguish a crash from a success.

So termination evidence is an **operator-side observation** of the outside
world, not a product feature. Adding an inference mechanism would replace a
named uncertainty with a plausible-sounding wrong answer.

### (b) A separate explicit operator recovery decision — **already implemented**

The operator decision exists: `POST /api/guardian/delegations/runs/{run_id}/quarantine`
(`80d46f86c`), operator-authenticated, atomically dispositioning, idempotent,
and bounded to the operator's own ownership expectation. Nothing further is
required to give an operator the authority to dispose of an uncertain run.

### (c) Additional external side-effect inspection — **operator procedure, already documented**

The product cannot inspect a provider's side effects, a worktree's contents,
or a Git history. The runbook's bounded workflow already has the operator
review possible external effects before disposing, and inspect the preserved
worktree and external effects afterwards. This is correctly a procedure, and
it is written down.

### (d) Integration of the existing quarantine disposition — **already implemented, and correctly not wired into the review**

The disposition is integrated end to end: service → atomic persistence →
operator route. The startup review deliberately does **not** invoke it. That
separation is the point: observation never becomes disposition without an
operator's hand on it.

### (e) A queue-delivery guarantee stronger than destructive dequeue — **the only genuine system gap, and it belongs to a different subsystem**

This is the §2 hole. Detecting work lost before durable acceptance is a
**queue-delivery** property, not a recovery property: it is about whether the
queue can lose a task, not about what to do with a run whose outcome is
uncertain. It is also an explicit non-goal of this campaign (*"no Redis
acknowledgement redesign"*), and it is a larger change than anything this
campaign has done.

Its blast radius is worth stating precisely, because it is **not** confined to
the delegation path. The coding-execution queue
(`codexify:queue:coding-execution`) is dedicated, but it has **two**
producers — the Guardian delegation dispatch
(`guardian/core/guardian_delegation_service.py:1794`) and the ordinary
`coding_execute` route (`guardian/routes/agent_orchestration.py:599`) — and
one consumer, the coding worker
(`guardian/workers/coding_worker.py:2302`). A stronger delivery guarantee
would therefore change the semantics of the **non-delegation** coding entry
point too, which is why it belongs to the queue subsystem's own decision
rather than to a delegation-recovery slice.

### Summary

| Candidate | Verdict |
|---|---|
| (a) worker-termination evidence | Operator procedure; **not** product surface |
| (b) explicit operator recovery decision | **Done** (`80d46f86c`) |
| (c) external side-effect inspection | Operator procedure; already documented |
| (d) quarantine disposition integration | **Done** (`158ea8930`, `80d46f86c`) |
| (e) stronger queue-delivery guarantee | **The one real gap** — owned by the queue subsystem |

**One** of the five is a genuine capability gap, and it lives outside the
delegation campaign's boundary.

## 4. What this assessment concludes

The campaign's recovery path is, at its intended boundary, **complete for the
operator-decision model**:

```
observe (startup review, read-only)
    → an operator decides, with the run's own ownership in hand
        → disposition commits atomically with its evidence
```

Everything that remains is one of three things, and none of them is another
delegation-recovery slice:

1. **A release-posture decision.** Whether the operator route is admitted to
   a supported profile is a *supported-profile* question, and the current
   answer (quarantined in all five profiles, flag off by default) is a
   deliberate posture rather than a gap. Nothing in this campaign changed it.
2. **Operator procedure.** Termination evidence and external side-effect
   inspection happen on the machine and in the provider, and are written down
   in the operator runbook.
3. **A queue-subsystem property.** Pre-acceptance loss detection belongs to
   the queue's delivery guarantee.

**Recommendation: do not open another implementation slice on this branch.**
The remaining concern that is genuinely a *system* concern is the queue's
delivery guarantee, and it is not a recovery feature. Adding more recovery
surface on top of a complete observe → decide → dispose path would be the
"endlessly expanding recovery subsystem" the campaign explicitly warns
against.

Automatic execution recovery and restart reconciliation remain **deliberately
unimplemented**, and nothing in this assessment argues for either. The
strict-xfail restart-reconciliation tripwire remains unresolved and should
stay that way.

## 5. Release-truth qualification

**This feature branch is not the authority for current mainline release
readiness.** Its `docs/architecture/00-current-state.md` is dated
**2026-10-15**, while the current Project KB carries an October 26 version.
The branch's contracts and receipts describe a *feature-branch* truth.

Consequences:

- No release claim may be drawn from this branch's `00-current-state.md`.
- This slice did not modify `00-current-state.md`, and must not.
- Before any release discussion, the campaign needs to be **re-landed onto
  current mainline**, and its receipts re-verified against the tree that
  actually ships. A proof receipt is evidence about the tree it was produced
  on; it does not travel automatically onto a different one.

## 6. Focused validation carried forward

From the receipts, at their respective evaluated commits:

| Suite | Result |
|---|---|
| Restart-review contract | 33 passed |
| Uncertain-quarantine contract | 34 passed |
| Quarantine operator-route contract | 39 passed |
| Liveness-classification contract | 31 passed |
| Terminal-fencing contract | 23 passed |
| Heartbeat contract | 25 passed |
| Ownership contract | 26 passed |
| Acceptance contract | 19 passed |
| Recovery contract | 19 passed, 1 xfailed (the restart-reconciliation tripwire) |
| Focused sweep (498 collected) | 482 passed, 15 failed, 1 xfailed |

The 15 failures are inherited by exact identity and cause — 14 in
`guardian/tests/workers/test_coding_worker.py` (this sandbox denies
`git worktree` creation, so the isolated-worktree cases cannot build their
sandbox) and 1 pre-existing product defect
(`NameError: name '_fetch_work_order' is not defined` in
`guardian/workers/coding_worker.py`'s campaign-attempt-ledger path). That
defect remains unpatched and is worth its own small slice; it is unrelated to
recovery.

The monolithic backend gate is **NOT RUN** to completion, across this whole
campaign. No slice's result should be read as a clean full-suite pass.

## 7. Environment status

### Diagnosis

The host's Docker Desktop Linux VM is **wedged in a kernel RCU stall**. From
the VM's own log:

```
"rcu: INFO: rcu_sched detected expedited stalls on CPUs/tasks: { 1-...D } 453762 jiffies"
"rcu: blocking rcu_node structures"
"Sending NMI from CPU 2 to CPUs 1"
```

and from the backend log:

```
init failed to shutdown the VM: Post "http://ipc/shutdown": context deadline exceeded
guest-connect dial to 172.17.0.2:5432 failed: reading status: EOF
```

The engine cannot serve (`docker version` → empty server version), and
Docker Desktop's own `docker desktop restart` hangs in `stopping` because the
VM will not shut down. The host was heavily loaded at the time (load average
peaked around 4.8, and was far higher earlier), which is consistent with the
stall.

### Consequence

Lost from the engine's view: the disposable PostgreSQL and Redis containers,
the image cache, and the containers of the **Private Preview** stack.

### Volume integrity: **UNVERIFIED**

The named volumes live inside the VM disk image (`Docker.raw`), which the
reset did not delete. But because the engine cannot mount that disk, their
presence and their contents **could not be confirmed**. This assessment
therefore makes no claim about the Private Preview vector store.

### Recovery — operator action, outside this sandbox

Docker Desktop's own lifecycle commands were attempted first, and they fail
because the VM cannot shut down:

```
$ docker desktop restart
✗ Failed to stop Docker Desktop
stopping Docker Desktop: processes still running:
  /Applications/Docker.app/Contents/MacOS/Docker Desktop (18311)
  /Applications/Docker.app/Contents/MacOS/com.docker.backend (18273)
  /Applications/Docker.app/Contents/MacOS/com.docker.backend (18276)
  /Applications/Docker.app/Contents/MacOS/com.docker.backend (18277)
  /Applications/Docker.app/Contents/MacOS/Docker Desktop Helper (18343)
  /Applications/Docker.app/Contents/MacOS/Docker Desktop Helper (18347)
  /Applications/Docker.app/Contents/MacOS/Docker Desktop Helper (Renderer) (18375)
  /Applications/Docker.app/Contents/MacOS/com.docker.build (18308)
  : context deadline exceeded
```

`docker desktop diagnose` also fails (`✗ Failed to diagnose Docker Desktop`,
panic in the system gatherer). The engine stays down throughout
(`docker version` → empty server version).

**Do this from a normal shell, outside the agent sandbox:**

1. **Force-restart the VM, preserving the disk.**
   ```bash
   osascript -e 'quit app "Docker Desktop"'
   pkill -9 -f com.docker.backend      # 18273 18276 18277
   pkill -9 -f 'Docker Desktop Helper' # 18343 18347 18375
   pkill -9 -f com.docker.build       # 18308
   pkill -9 -f com.docker.vmm         # if a VM process is present
   open -a Docker
   ```
   This preserves `Docker.raw`, and therefore the named volumes. Wait for
   `docker version` to report a server version before proceeding.
2. **If the engine still will not start, reboot the host.** That also
   preserves `Docker.raw`.
3. **Do NOT use Docker Desktop's "Reset to factory defaults".** It recreates
   the VM disk and would discard the named volumes — including
   `private_preview_chroma`, which the private-preview compose mounts
   `nocopy: true` and which holds the operator's vector store. A factory
   reset converts a recoverable outage into permanent data loss.
4. **After the engine returns**, verify volume integrity before anything
   else:
   ```bash
   docker volume ls
   docker compose --env-file .env.private-preview \
     -p codexify_private_preview \
     -f docker-compose.yml -f docker-compose.private-preview.yml \
     up -d
   scripts/private_preview_validate.sh static
   scripts/private_preview_validate.sh reachability
   ```
   Never `down -v`.
5. **Restore the disposable proof environment** for any further
   database-backed proof (this campaign's disposable pair):
   ```bash
   docker run --rm -d --name codexify-hb-pg \
     -e POSTGRES_PASSWORD=hbpw -e POSTGRES_USER=hb -e POSTGRES_DB=hbdb \
     -p 127.0.0.1::5432 postgres:16-alpine
   docker run --rm -d --name codexify-hb-redis -p 127.0.0.1::6379 redis:7-alpine
   ```
   (The repository's own compose uses `postgres:15` and `redis:7-alpine`; the
   disposable pair above is what this campaign's proofs ran against.)

### Why the recovery was not performed from this session

This sandbox denies process enumeration and signalling outright:

```
$ pgrep -u "$(id -u)" | wc -l
0
$ killall -0 codexify_nonexistent_probe
killall: could not sysctl(KERN_PROC): Operation not permitted
$ kill -9 18273
/bin/bash: line 0: kill: (18273) - Operation not permitted
```

The wedged processes cannot be located or signalled from inside the session,
and the one supported route to a clean shutdown (`docker desktop stop` /
`restart`) blocks on the same wedged VM. The recovery therefore requires one
command set from outside the sandbox, and nothing more.

## 8. Classification

**PASS** as an assessment: the campaign's recovery path is complete for the
operator-decision model, one genuine capability gap remains and it belongs to
the queue subsystem, and no further delegation-recovery slice is warranted.

Release status: **HOLD**, unchanged. Restart recovery remains unqualified.
Automatic execution recovery remains deliberately unimplemented.
