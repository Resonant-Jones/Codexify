# Codexify Solo Operator Coding Worker Runbook

Purpose: give a solo operator the current truth surface for Guardian-mediated
coding-worker work without implying autonomous convergence, commit behavior,
or unbounded retry loops.

Last updated: 2026-10-26

Source anchors:
- `docs/architecture/00-current-state.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/delegation-operator-manual.md`
- `guardian/agents/coding_agent_contracts.py`
- `guardian/agents/test_results.py`
- `guardian/agents/store.py`
- `guardian/workers/`
- `guardian/tests/agents/test_test_results.py`

## Runtime Truths

1. A normalized test-result contract now exists in `guardian/agents/test_results.py`.
2. The contract is a preparatory seam for future autonomous convergence logic.
3. It does not by itself cause the coding worker to execute tests automatically.
4. It does not enable retry-until-tests-pass behavior.
5. Future loop work must consume the normalized test-result contract rather than
   raw stdout/stderr blobs.

## Operator-Visible Recovery Posture (and its limits)

**Read this before interpreting a stuck coding run.**

A Guardian coding execution that a worker has claimed is **durably accepted**.
The canonical `agent_runs` row moves `queued` -> `running` and `started_at` is
stamped exactly once, in PostgreSQL, before any worktree, credential lease, or
provider execution happens. A worker that dies mid-execution therefore leaves
behind an `agent_runs` row that reads `running` with a non-null `started_at`
and a null `ended_at`.

**What that looks like to an operator:** a run stuck in `running` with no
result artifact and no source-thread message. That is the *expected* durable
shape of an interrupted execution. It is not, by itself, evidence that the
worker is still running, and it is not evidence that it died.

**What the system does today about it: nothing.** A restarted coding worker
performs **no** restart reconciliation. It does not classify the abandoned run,
does not escalate it, does not quarantine it, and does not retry it. There is no
recovery status to look for, because no recovery record is written.

**Why not, precisely:** the runtime cannot yet tell an **abandoned** accepted
run from an **actively owned** one. The coding worker now records which worker
instance owns a run (`coding_worker_instance_id`, `coding_worker_claim_id`) and
reports a per-run liveness heartbeat
(`coding_worker_last_heartbeat_at`), but a heartbeat is *evidence of reported
activity*, not a verdict: nothing in the runtime compares it against a deadline,
and no startup path reads it. Every remaining substitute is a timestamp or an
empty queue, and both are unsafe: an elapsed time is not a death, and an empty
queue is equally consistent with a crash and with a success.

**Therefore, at the time of writing:**

| Signal | What it means |
|---|---|
| `agent_runs.status = 'running'`, `started_at` set, `ended_at` null | The execution was **accepted** and never reached a durable terminal state. It may still be executing. |
| No `agent_escalations` row | Nothing has classified it. This is the current, expected state — it is **not** a sign that a check ran and passed. |
| Empty `codexify:queue:coding-execution` | Nothing is waiting. The queue is lossy and at-most-once, so this says nothing about whether the accepted run completed. |
| No `coding_worktree_leases` row | The Guardian path never creates one. The lease table has the right shape but no production code path writes it. |
| An isolated Git worktree left behind | The worker created it and died before cleanup. Nothing reclaims it automatically. |

**What an operator can safely do.** Treat a `running` Guardian coding run with
a null `ended_at` as *unresolved*. It is safe to inspect the repository, the
worktree, and the run's `started_at` to decide for yourself. It is **not** safe
to re-dispatch the same task, and there is no supported automatic or manual
re-drive in this runtime — a re-dispatch would mint a new attempt without
fencing, and duplicate execution effects are not idempotent.

### Reading the claim-scoped heartbeat

An accepted coding run now carries three canonical facts in PostgreSQL:
`coding_worker_instance_id`, `coding_worker_claim_id`, and
`coding_worker_last_heartbeat_at`. The worker renews the heartbeat while it
executes, on an explicit cadence (`CODING_RUN_HEARTBEAT_INTERVAL_SECONDS`,
default 15 seconds), and stops the moment the execution ends.

The heartbeat is **evidence of reported activity, never authority**. Read it as
a hint about the run, not as a verdict about the worker:

| What you see | What it means | What it does **not** mean |
|---|---|---|
| `status = 'running'`, heartbeat **fresh** (moving with the cadence) | The recorded owner is still reporting. The execution is most likely in flight. | That the run will succeed, or that it is safe to touch the worktree. |
| `status = 'running'`, heartbeat **stale** (older than a few cadences) | The owner has stopped reporting. The worker may have died — or may be blocked in a long provider call, paused, or between phases. | **Not** proof of worker death. There is no expiry rule, and nothing in the runtime acts on a stale heartbeat. |
| `status = 'running'`, **no** ownership metadata and no heartbeat | A historical row from before ownership existed, or a run that was never accepted. It is **ownership-unknown**. | Not an abandoned run. Missing ownership is not evidence of loss, and such a row is never escalated for it. |
| A heartbeat renewal was **rejected** (`not_eligible`) | The database no longer sees this worker/claim as the owner of that run — a different worker, a different claim, or a terminal/escalated run. The worker stops reporting and refuses to enter the adapter. | Not a recoverable error and not a licence to retry. The worker does **not** take over the run, mint a new claim, or issue another credential lease. |
| `status` is terminal (`succeeded` / `failed` / `canceled` / `escalated`) with the heartbeat preserved | The run finished. The heartbeat history is retained for inspection; nothing renews it any more. | Not evidence that the run's side effects were fenced. A stale worker can still attempt a terminal write; that fencing is not implemented yet. |

**None of these observations authorizes a re-dispatch.** The runtime performs no
automatic re-drive, quarantine, escalation, or takeover on any of them, and
neither should an operator: a re-dispatch mints a new attempt without fencing,
and duplicate execution effects are not idempotent. The heartbeat narrows what
an operator can *know*; it does not grant permission to act.

**What is coming.** The operator-visible disposition for an unresolved run is
already defined and needs no migration: the canonical run moves to
`escalated` and one `agent_escalations` row is written with
`status = 'open'`, a `reason_code`, and the recovery evidence. What is missing
is the durable worker-ownership and liveness authority that would let the worker
decide that a run is genuinely abandoned. The evidence for that investigation is
in
`docs/architecture/proofs/runtime/2026-10-23-guardian-coding-restart-reconciliation-proof.md`.

### Reading a claim-fenced terminal result

A terminal coding result is now written by one atomic database decision: the
recorded worker instance and claim must still own the run. The terminal status,
the coding-result artifact, the Guardian delivery state, and the source-thread
result message commit together, or none of them do.

| What you see | What it means | What it does **not** mean |
|---|---|---|
| The run is terminal, the artifact exists, and a source-thread result was posted | The claim owned the run when it finished. The result is authoritative. | That the Redis event was published. Database persistence is authoritative; the event is transport. |
| The run is terminal but **no** source-thread result was posted | The delivery was deferred, degraded, or suppressed by the existing contract. The terminal outcome still stands. | That the result was lost. Read the artifact and the run's error field. |
| The run is terminal with **no matching Redis event** | The durable result committed and the event publication failed, or the event has not been observed yet. | That the execution did not finish. The durable row is the truth; the event is not. |
| The run is still `running`, with **no terminal result**, and the worker reported ownership lost | A stale worker's terminalization was refused: the claim no longer owned the run. Nothing was written -- no status, no artifact, no message, no terminal event. | That the execution failed. The refusal is deliberately **not** a terminal outcome; only an operator may decide what happens next. |
| The run is `escalated` and a worker later reported success | Another authority disposed of the run; the late worker completion was refused. No artifact, no source-thread result, and no `task.completed` event came from that worker. | That the worker's work was worthless. The external side effects it may have produced are unknown and are **not** fenced. |
| A worktree or patch artifact exists for a run with no terminal result | The worker mutated something before it lost or never reached its terminal outcome. | That the mutation was rolled back. The database fence protects canonical state only; the filesystem is not fenced. |
| The run is `running` with no terminal result and no worker activity | The execution is unresolved. | That it may be re-dispatched. |

**None of these observations authorizes a re-dispatch.** The runtime performs no
automatic re-drive, takeover, or retry on any of them, and neither should an
operator: a re-dispatch mints a new attempt without fencing, and duplicate
execution effects are not idempotent. In particular, an orphaned worktree
mutation or patch artifact is an *external* side effect the runtime cannot
contain -- it has to be inspected and cleaned up by a human before anything is
re-dispatched.

### Reading a coding run's liveness classification

Guardian can now read a run's canonical ownership and heartbeat evidence and
classify it. The classification is **observational**: it reports evidence and a
conservative verdict, and it authorises nothing.

| The classification says | What it establishes | What it does **not** establish |
|---|---|---|
| **recently observed** — the claim renewed liveness inside the horizon (60 seconds) | The recorded owner was still reporting, very recently. | That the worker process currently exists, that it will finish, or that its worktree is safe to touch. |
| **stale and uncertain** — the last renewal is older than the horizon | Recent liveness evidence is **missing**. The worker may be between phases, blocked on a provider call, paused, or gone. | **Not** that the worker died. There is no expiry rule, no takeover, and nothing that acts on a stale heartbeat. |
| **missing evidence** — a running run with no usable owner, claim, or heartbeat | There is not enough evidence to classify liveness. Typical of a historical row. | Not that the work never started, and **not** that no side effects occurred. |
| **never accepted** — the run is `queued` with no claim | The execution was never durably accepted. | Not that it was abandoned. It is simply not running yet. |
| **already resolved** — the run is `succeeded`, `failed` or `canceled` | A canonical terminal disposition already exists. | Not that its external effects are bounded. The terminal write was claim-fenced; the filesystem was not. |
| **already escalated** — the run is `escalated` | An authoritative escalation disposition already exists. A classification never creates another one. | Not that the worker is dead, and not that the escalation says so. |
| **inconsistent** — the record contradicts itself (a partial ownership pair, a queued run with accepted ownership, impossible timestamps, a heartbeat in the future) | The canonical record needs **human inspection** before anything is decided about the run. | Not that the run is fine, and not that it is lost. Anomalous records are never repaired automatically. |
| **unobservable** — there is no record, or persistence is unreachable | Nothing could be read. | Nothing about the execution. |

**A stale classification cannot authorize re-dispatch.** It is evidence of
uncertainty, not a decision. No automatic retry, takeover, escalation, or
cancellation follows from it, and neither should an operator: a re-dispatch
mints a new attempt without fencing, and duplicate execution effects are not
idempotent.

**External side effects remain uncertain.** A stale heartbeat says nothing
about whether the harness finished a provider request, mutated an isolated
worktree, produced files, started a subprocess, made a network request, or
committed an external change. The absence of a canonical result is **not** the
absence of external side effects. Inspect the worktree and the repository
before you re-drive anything.

### Disposing of an uncertain coding run

When a run is unresolved, Guardian can record an **operator-authorized
quarantine**: the canonical run moves to `escalated` and one open escalation
record explains why, committed together. This is a disposition, not a
recovery.

**How to read the evidence first.** A stale heartbeat means the owning claim
has not renewed liveness recently. It does **not** mean the worker stopped: a
worker between phases, blocked on a provider call, or paused by the host looks
exactly the same. A fresh heartbeat means the worker is still reporting — and
an active worker is not a recovery candidate, so the disposition is refused
while the heartbeat is fresh. A run with no ownership record is
ownership-unknown and belongs to a separate investigation, not to this
disposition.

**What an authorized quarantine changes.** The run's canonical status becomes
`escalated`; one open escalation record is written with the run, the original
worker instance and claim, the last heartbeat, the database observation
instant, the liveness verdict, the verified operator actor, and the recorded
reason; the run's end timestamp is stamped. That is all.

**What it does not change.** It does not stop the worker, the provider call, a
subprocess, or a filesystem mutation that may already be in flight. It deletes
no worktree and no artifact. It delivers **no** source-thread result and
publishes **no** `task.failed` / `task.completed` / `task.cancelled` event. The
run's outcome stays `unknown`; `escalated` is not `failed`, and it is not proof
that the worker died. It grants no retry and no ownership transfer.

**Why the worktree still needs inspection.** A quarantine protects canonical
state only. The worker may already have modified an isolated worktree, left an
untracked file, started a subprocess, or begun a commit. The disposition
records whether a worktree was *known* to exist; when that cannot be
established, the record says so rather than claiming preservation. Inspect the
worktree and the repository yourself.

**Why re-dispatch remains forbidden.** A re-dispatch mints a new attempt
without fencing, and duplicate execution effects are not idempotent. A
quarantine withholds canonical completion until the unresolved execution is
investigated; it never re-drives anything, and it does not enable a re-drive
either. Any re-dispatch needs separate authority and separate proof.

**If the disposition is refused.** A refusal is a fact, not a failure: the
worker is still reporting, the run already carries a different disposition, the
claim no longer matches, or the evidence was re-read and found stale. Re-read
the canonical state before assuming the run is abandoned.

### Invoking the quarantine over HTTP

The disposition above is reachable by an operator over HTTP, through the
**existing** Guardian delegation route family:

```
POST /api/guardian/delegations/runs/{run_id}/quarantine
```

**This route is not enabled by default.** It lives on the `guardian_delegations`
router, which is included only when the existing feature gate
`CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES` is explicitly enabled. That
gate's default is off, the supported release profile quarantines the family,
and nothing in this runbook changes either. A route proven with the gate
enabled is **not** a deployment: it does not mean the supported Compose path
exposes it.

**The bounded workflow.**

1. **Obtain the canonical liveness evidence.** Read the run's classification
   first ("Reading a coding run's liveness classification"). You are looking
   for **stale and uncertain**. Anything else — recently observed, missing
   evidence, never accepted, already resolved, already escalated,
   inconsistent, unobservable — is not a candidate, and the disposition will
   refuse it.
2. **Verify the intended run and worker claim.** Read
   `coding_worker_instance_id` and `coding_worker_claim_id` from the canonical
   run row. These are the values you will send. They are checked again inside
   the transaction against the database clock, so if the worker renewed its
   heartbeat after you read it, the disposition is refused.
3. **Review possible external side effects.** Before disposing of anything,
   look at the worktree, the repository, and any provider session the run may
   have touched. A quarantine protects canonical state only.
4. **Invoke the operator-only action.** One deliberate POST against one
   identified run, with an explicit reason:

   ```bash
   curl -sS -X POST \
     "http://<guardian-host>:<port>/api/guardian/delegations/runs/<run-id>/quarantine" \
     -H "X-API-Key: ${GUARDIAN_API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{
           "expected_worker_instance_id": "<worker-instance-id>",
           "expected_worker_claim_id": "<worker-claim-id>",
           "reason": "<why you are disposing of this run>"
         }'
   ```

   Replace every placeholder. **Never** place a credential in the body, the
   query string, or the path: the operator credential travels in the header
   only, and the body carries only the two ownership values and your reason.
   An operator-purpose session token in `Authorization: Bearer <token>` or in
   the `gc_session` cookie works as well. Account and guest credentials never
   authorize this, even when the run id and claim id are known.
5. **Read back the committed escalation evidence.** The response is a bounded
   receipt: `run_id`, `disposition`, `escalation_id`, `reason_code`,
   `original_worker_instance_id`, `original_worker_claim_id`,
   `operator_actor`, `already_quarantined`, and `recorded_at`. Then re-read the
   canonical run row and the `agent_escalations` row in PostgreSQL to confirm
   the committed state independently of the response.
6. **Inspect the preserved worktree and external effects separately.** The
   receipt does not tell you what the worker did. Do that yourself.

**Reading the outcome.**

| Response | What it means |
|---|---|
| `201` | Guardian committed the quarantine and its open escalation, together. |
| `200` | An identical escalation already existed and was observed read-only. Nothing was duplicated, re-stamped, or rewritten. |
| `401` | The operator credential was missing, expired, malformed, or was an account or guest credential. |
| `404` | No such run. |
| `409` | The run is not eligible: the ownership values do not match, the heartbeat is fresh, the run is already terminal, or it carries a conflicting disposition. Re-read the canonical state. |
| `503` | The database was unreachable. Nothing was committed. |

**What the receipt does not say.** It does not say the worker was stopped, that
external effects were prevented, that the worktree was restored, that a
provider session was cancelled, that a Git commit was undone, or that the
execution outcome is known. Those remain yours to inspect.

**There is no automatic path to this.** Nothing in the runtime calls this route
on a timer, at startup, or in the background, and no heartbeat-age watcher
watches for it. A run that goes unresolved while Guardian is down is still
reconciled by you, deliberately.

## Pi Runtime Readiness Gate

The source-Compose coding worker uses a dedicated
`codexify-worker-coding-runtime:latest` image. The image installs the exact
`@earendil-works/pi-coding-agent` version declared in
`codex_runner/pi-runtime/package-lock.json`; it does not depend on a host-local
SDK build. The worker does not mount a shared Pi auth volume or receive a
deployment-wide provider, model, or provider API key.

Wrapper presence is not execution readiness. Before starting the Redis
consumer, the worker checks Node, the Guardian wrapper, the pinned Pi SDK
artifacts, a usable Git CLI, and non-executing adapter initialization. Startup
does not resolve provider/model identity or inspect credential state. Guardian
authorizes those for each invocation. Before each attempt, the worker requests
a sealed, attempt-bound credential lease; the initial account-scoped
implementation accepts encrypted account credentials or service-owned
credentials covered by explicit Guardian policy. Operator-owned credentials are
not an account fallback. The Pi process receives any required plaintext only
for that invocation through its trusted runtime path. Queue and durable
execution records contain references and identity metadata, never key material.
A `blocked` readiness result exits with status 78 before the worker can dequeue
a task.

From the repository root, validate Compose without rendering secret-bearing
values, build the exact image, and inspect readiness:

```bash
docker compose config --quiet
docker compose build worker-coding
docker compose run --rm --no-deps --entrypoint python worker-coding /app/backend/scripts/docker/check_worker_coding_readiness.py --format human
docker compose run --rm --no-deps --entrypoint python worker-coding /app/backend/scripts/docker/check_worker_coding_readiness.py --format json
```

The command is Compose-owned. Do not shell-source the project env file; Docker Compose parses
the project environment without applying shell quoting rules. In particular,
an apostrophe in `LOCAL_PROVIDER_DISPLAY_NAME` remains valid and unchanged.
Use `docker compose config --quiet`, rather than printing the full resolved
configuration, when the goal is validation only.

### Credential and provider setup

Account provider API keys are registered through the account-authenticated
`POST /api/agents/coding/credentials` endpoint. The response contains an opaque
credential reference, not the key. Coding requests choose a provider, model,
and credential reference independently; Guardian verifies that the account
owns the credential and that its provider matches the requested binding.
Service-owned credentials require explicit Guardian policy for the account,
provider/model, funding route, and usage policy. Operator credentials are not
an account fallback. The current API-key path does not implement a credential
management UI or non-exportable subscription/brokered entitlements.

Do not put provider keys in `.env`, `PI_PROVIDER`, `PI_MODEL`, a shared Pi auth
volume, task payloads, command-line arguments, logs, or documentation. Do not
use Pi `/login` to authorize account-scoped coding work. The default harness is
configurable with `CODEXIFY_DEFAULT_HARNESS` in the Guardian runtime
environment; its initial value is `pi`. Provider and model are resolved from
each invocation binding and cannot be selected by worker environment.

### Readiness states

| State | Meaning | Queue behavior |
|---|---|---|
| `ready` | Node, wrapper, pinned SDK artifacts, a usable Git CLI, and the non-executing adapter probe passed. | Worker may start consuming tasks. |
| `blocked` | One or more required prerequisites failed. | Startup exits before queue consumption. |

Stable reasons and recovery:

| Reason | Recovery |
|---|---|
| `node_missing` | Rebuild `worker-coding`; do not substitute an arbitrary host Node binary. |
| `wrapper_missing` | Restore the tracked `codex_runner/src/agent-wrapper.js` mount and rerun readiness. |
| `pi_sdk_build_missing` | Run `docker compose build --no-cache worker-coding`, then rerun readiness. |
| `adapter_initialization_failed` | Rebuild the image and inspect the secret-free readiness JSON plus worker logs for packaging drift. |
| `git_missing` | Rebuild `worker-coding` and `backend` from the canonical `backend/Dockerfile`; Git is installed in the shared `runtime` stage. Do not mount a host Git binary. |
| `git_probe_failed` | Rebuild the image; the image's Git binary did not run `git --version` successfully. |
| `git_probe_timeout` | Rebuild the image; the image's Git binary did not answer `git --version` within the bounded probe timeout. |

### Canonical Git installation

Git is a **mandatory runtime prerequisite**, not an optional tool. Guardian's
repository-binding authority resolves a working-tree root with Git, and the
coding worker's mutation enforcement inspects porcelain state with Git. A runtime
without a usable Git CLI cannot perform those already-authorized operations.

Git is installed once, by `apt-get`, in the canonical `runtime` stage of
`backend/Dockerfile`. The `worker-coding-runtime` stage derives from `runtime`,
so the backend image and the coding-worker image ship the same Git. There is no
second installation, no host-mounted Git binary, and no package installation
during worker startup.

To verify an image carries it:

```bash
docker run --rm --entrypoint git codexify-worker-coding-runtime:latest --version
docker run --rm --entrypoint git codexify-backend-runtime:latest --version
```

**This is a packaging prerequisite, not a sandbox.** Shipping Git does not
isolate the worker: it is the same *detective* boundary the mutation guard has
always been. The guard observes a mutation after the fact and fails the
attempt; it does not prevent the write, and it provides no filesystem, network,
or process isolation. See the mutation scope guard sections below and ADR-077
rules 6-8.

After readiness reports `ready`, start and inspect the service:

```bash
docker compose up -d worker-coding
docker compose ps worker-coding
docker compose logs worker-coding --tail=100
```

Do not submit a coding task while readiness is `blocked`. A process restart or
wrapper file on disk does not override the gate.

## Bounded Validation Retry

- The worker can run a supervised validation command after the adapter returns.
- Validation only runs when shell execution is allowed and the task has a
  working directory.
- Validation evidence is normalized through `guardian/agents/test_results.py`
  before it is stored or emitted.
- `passed` and `not_run` keep the current attempt terminally successful when
  the mutation scope guard is clean or within allowed scope.
- `failed` and `error` can trigger bounded retries only when the mutation scope
  is clean or within allowed paths.
- If shell execution is blocked, the worker records a normalized `not_run`
  result with reason `validation_shell_not_allowed`.
- Retry behavior is bounded; it does not imply convergence, commit behavior, or
  infinite retry.

## Mutation Scope Guard

The worker has two mutation checks: the git mutation guard and the isolated
worktree scope check. Both read the same Guardian-authorized write scope, and
both now interpret it with **one** normalized rule set.

**One scope interpretation.** `permission_policy.allowed_paths` entries are
repository-relative. Each entry is one of:

- `.` — explicit repository-root authorization.
- A path prefix — an exact file, or a directory and everything beneath it.
  Prefixes are matched on a path boundary, so a scope of `src` never
  authorizes the sibling `src-other`. A trailing `/` is accepted and
  equivalent.
- An explicitly authorized glob pattern (`*`, `?`, `[`).

**Rejected entries.** An empty string is *not* whole-repository access. An
absolute path outside the bound repository, and any entry containing a `..`
segment, are rejected. A scope that resolves to no valid entry authorizes
nothing at all: with `allow_write=true` the attempt fails closed with
`MUTATION_SCOPE_VIOLATION` rather than treating the repository as
unrestricted.

**Known Guardian-emitter incompatibility.** The delegated-task posture still
emits `allowed_paths=("",)`, and `GUARDIAN_DEFAULT_ALLOWED_PATH_SCOPE` in
`guardian/core/guardian_permission_posture.py` still declares `("",)` as the
whole-repository default. Under the normalized scope those are rejected, so a
delegated task will now fail closed until the emitter migrates to the
explicit root token `(".",)`. That migration is upstream work in
`guardian/core/guardian_delegation_service.py` and
`guardian/core/guardian_permission_posture.py`; it was deliberately not made
here.

**Changed paths.** A changed path that is absolute, contains a `..` segment, or
resolves outside the bound repository is rejected before the scope is
consulted.

- Every attempted coding-worker run captures Git porcelain state before the
  adapter executes when the cwd resolves to a Git repository.
- If the worktree is already dirty before execution, the worker fails closed
  with `DIRTY_WORKTREE_PRECHECK_FAILED` before the adapter runs.
- After each adapter attempt, the worker captures Git porcelain state again and
  compares it to the preflight snapshot.
- When `allow_write=false`, any new repository mutation fails closed with
  `MUTATION_SCOPE_VIOLATION`.
- When `allow_write=true`, changed paths must match the normalized scope.
- There is no implicit wildcard: a narrow scope never widens.
- If the cwd is not a Git repository, the worker emits explicit unverified
  evidence and continues without claiming scope proof.
- Scope violations stop the retry loop immediately.
- Validation failures may retry only when mutation scope is clean or within the
  allowed path set.

**Remaining enforcement limitations.**

- Both checks are **detective, not preventive**. The write has already landed
  when the guard fires (ADR-077 rules 7-8). No sandbox provider is wired into
  the coding worker, so no filesystem, process, or network isolation is
  claimed here.
- The two checks observe different trees. The isolated scope check reads the
  isolated worktree; the git mutation guard reads the task's repository. A
  mutation that lands only in the isolated worktree is visible to the guard
  only when the guard observes that tree.
- A scope entry is a path prefix. A path authorized as a file also authorizes
  a subtree of that name, so replacing an authorized file with a directory of
  the same name stays inside the prefix.
- With `allow_write=false` the guard denies every mutation, while the isolated
  scope check evaluates the declared scope only. This difference is unchanged
  by the scope unification.
- An absolute scope entry is resolved against the bound root of the check that
  consumes it.

## Mutation Scope Guard

- The worker now inspects Git porcelain state before the first adapter attempt
  and again after each attempt, including any validation step that runs before
  the final decision.
- If `cwd` is inside a Git repository, the worker treats the repository root as
  the mutation boundary and compares post-attempt porcelain paths against the
  clean preflight baseline.
- If `cwd` is not inside a Git repository, the guard degrades explicitly:
  validation can still run, the attempt can still complete, and the emitted
  metadata marks the mutation scope as `unverified`.
- If the repository is already dirty before execution starts, the worker fails
  closed with `DIRTY_WORKTREE_PRECHECK_FAILED` before calling the adapter.
- If `allow_write=false`, any new porcelain changes fail closed with
  `MUTATION_SCOPE_VIOLATION`.
- If `allow_write=true`, every changed path must match a normalized
  `allowed_paths` entry. The supported entries are:
  - `.` for explicit repository-root authorization
  - repository-relative path prefixes, matched on a path boundary
  - explicit `fnmatch` glob patterns
- An empty `allowed_paths` entry, an absolute path outside the bound
  repository, and any `..` segment are rejected. They never widen the allowed
  scope, and they never imply whole-repository access.
- A scope that resolves to no valid entry authorizes nothing: with
  `allow_write=true` the attempt fails closed with `MUTATION_SCOPE_VIOLATION`.
- The git mutation guard and the isolated worktree scope check share this one
  interpretation, so they reach the same decision for the same scope and the
  same changed path.
- Mutation guard metadata is emitted on task events and stored result artifacts
  using bounded lists and totals:
  - `mutation_guard_enabled`
  - `mutation_guard_status`
  - `mutation_guard_error_code`
  - `changed_paths`
  - `disallowed_paths`
  - `allowed_paths`
  - `changed_paths_truncated` and `changed_paths_total`
- Path lists are truncated to 50 entries when necessary.
- Scope violations stop the retry loop immediately.
- Validation failures can retry only when the guard status is verified.
- This still does not add commits, worktree isolation, auto-merge, or infinite
  retry.
6. Lease-bound execution now exists in the worker seam when `worktree_lease_id`
   is supplied.
7. Guardian can optionally create a disposable detached Git worktree when
   `CODING_WORKER_WORKTREE_ISOLATION` is enabled.
8. Commit-after-green is now an opt-in worker seam and remains bounded to
   existing leased worktree paths.

## Bounded Validation Retry

- The worker now supports bounded supervised validation retries.
- Default maximum validation attempts: `3`.
- Environment override: `CODING_WORKER_MAX_VALIDATION_ATTEMPTS`.
- Valid values clamp to the range `1..10`.
- `1` preserves the old single-attempt behavior.
- Retries happen only after a success-like adapter result and a failing
  validation command.
- Retries do not happen when the adapter fails, when no validation command is
  present, or when shell execution is blocked by policy.
- The retry prompt includes bounded validation feedback: command, status, exit
  code, fail signature, and truncated stdout/stderr previews.
- Final validation failure is still a terminal failure.
- The worker stops when attempts are exhausted; this is still not autonomous
  commit/merge behavior.

## Operator Interpretation

- `passed` means the test subprocess exited cleanly and may carry summary counts.
- `failed` means the subprocess returned a nonzero exit code and produced a
  deterministic fail signature.
- `error` means the command could not be treated as a valid test result.
- `not_run` means the run was intentionally skipped by policy and must not be
  mistaken for success.

## What This Does Not Mean

- It does not mean Guardian has an autonomous remediation loop.
- It does not mean coding-worker execution now re-runs until green without
  bounds.
- It does not mean adapter success is equivalent to repository test success.
- It does not mean retry policy should read raw terminal output directly once
  this seam is wired into the worker path.
- MiniMax or other downstream providers may run behind the Pi broker adapter,
  but Guardian still owns the loop boundary and stops after the bounded
  attempts are exhausted.

## Follow-Through Rule

When the worker-side loop is implemented later, it must:

1. normalize subprocess output through this contract,
2. persist or forward the normalized result,
3. keep retry policy separate from normalization, and
4. keep operator-visible truth deterministic across repeated attempts.
# Codexify Coding Worker Runbook

Purpose: Operating runbook for the Guardian coding-worker adapter pipeline (ADR-020).
Last updated: 2026-08-03
Source anchors:
- `guardian/routes/agent_orchestration.py` - `POST /api/agents/coding/execute`
- `guardian/agents/adapters/__init__.py` - adapter registry
- `guardian/agents/adapters/pi_codex_runner.py` - PiCodexRunnerAdapter
- `guardian/workers/coding_worker.py` - CodingWorker
- `guardian/queue/redis_queue.py` - `enqueue_coding_execution`, `dequeue_coding_execution`
- `guardian/tasks/types.py` - `CodingExecutionTask`
- `guardian/agents/store.py` - `AgentStore.store_coding_result()`

## Architecture Overview

```
┌─────────────┐     POST /api/agents/coding/execute     ┌──────────────┐
│   Client    │ ─────────────────────────────────────────▶│   Backend    │
└─────────────┘                                          └──────┬───────┘
       │                                                         │
       │ SSE: task.running, task.completed                      │ enqueue
       ▼                                                         ▼
┌─────────────┐                                          ┌──────────────┐
│   Events    │◀─────────────────────────────────────────│    Redis     │
└─────────────┘   task.running / task.completed          │   Queue      │
                                                                 │
                                                                 │ dequeue
                                                                 ▼
                                                         ┌──────────────┐
                                                         │ CodingWorker │
                                                         └──────┬───────┘
                                                                │
                                                                │ execute
                                                                ▼
                                                         ┌──────────────┐
                                                         │  Registered  │
                                                         │Coding Adapter│
                                                         └──────────────┘
```

## Canonical Interface

### Execute Coding Task

`adapter_kind` controls which registered coding-worker adapter executes the task.
The route persists the requested value in the deployment spec, and the worker
resolves it at execution time. Missing or blank values preserve the legacy
default of `pi_codex_runner`.

Supported values:

- `pi` -> `pi_codex_runner`
- `pi_sdk` or `pi_codex_runner` -> `pi_codex_runner`

Public coding-execution requests should use one of the explicit supported
adapter kinds above. Direct `codex` and `claudecode` values are rejected; they
are retained only as legacy unsupported values so persisted jobs fail closed
instead of silently switching providers. `mock` and `external_cli` are not part
of the supported public route contract.

The supported local Compose worker also needs the `codex_runner` tree available
at `/app/codex_runner` so the Pi runner path stays runnable when selected.

Unknown adapter names fail closed with `ADAPTER_NOT_FOUND`; route acceptance is
not execution success. Direct Codex/Claude execution is unsupported for this
module and must be replaced with the Pi broker adapter.

### Lease-Bound Execution

- Optional request/spec/task fields:
  - `worktree_lease_id`
  - `require_worktree_lease`
- If a lease is provided, the worker resolves durable lease state and requires
  an active, valid lease contract.
- When lease-bound, the worker uses lease `worktree_path` as the effective cwd
  for both adapter execution and validation commands.
- Lease heartbeats are attempted during execution.
- Missing, inactive, invalid, or unavailable lease context fails closed.
- This remains a backend seam only in this phase. There is no UI command center
  for lease inspection yet.

### Optional Worktree Isolation

- Optional flag: `CODING_WORKER_WORKTREE_ISOLATION`.
- Default: disabled (`false`).
- Accepted truthy values: `1`, `true`, `yes`, `on`.
- When enabled and `cwd` resolves inside a Git repository:
  - Guardian creates a detached disposable worktree from current `HEAD`.
  - Adapter execution and optional validation run inside that isolated path.
  - Mutation-scope preflight and scope checks run against the isolated worktree,
    not the operator's active checkout.
  - Success cleanup default: remove isolated worktree
    (`CODING_WORKER_KEEP_WORKTREE_ON_SUCCESS=false`).
  - Failure retention default: keep isolated worktree for inspection
    (`CODING_WORKER_KEEP_WORKTREE_ON_FAILURE=true`).
- Optional root override: `CODING_WORKER_WORKTREE_ROOT`.
  - Default root when enabled: `<repo_root>/.codexify/coding-worktrees`.
- When enabled and `cwd` is not inside a Git repository:
  - Worker fails closed with `WORKTREE_ISOLATION_UNAVAILABLE`.
  - Worker does not silently fall back to direct execution.
- This seam does not promote changes back to the operator checkout.
- Dirty source checkouts can still be processed in isolation mode because the
  disposable worktree is created from `HEAD`.

### Patch Artifact Capture for Isolated Runs

Purpose:
- Preserve reviewable evidence of isolated coding-worker output before
  worktree cleanup/retention finalizes.
- Keep operator truth visible without auto-apply, auto-commit, merge, or
  promotion into the active checkout.

Environment flags:
- `CODING_WORKER_CAPTURE_PATCH_ARTIFACTS`
  - Default: enabled when `CODING_WORKER_WORKTREE_ISOLATION=true`
  - False values: `0`, `false`, `no`, `off`
- `CODING_WORKER_PATCH_ARTIFACT_ROOT`
  - Default: `<repo_root>/.codexify/coding-artifacts`
- `CODING_WORKER_PATCH_MAX_BYTES`
  - Default: `2000000`
  - Clamp range: `1024..20000000`

Artifact layout:
- `<artifact_root>/<run_id>/<coding_task_id>/<attempt_id>/changes.patch`
- `<artifact_root>/<run_id>/<coding_task_id>/<attempt_id>/manifest.json`

Manifest fields (summary):
- `schema_version`, `created_at`
- lineage: `run_id`, `deployment_id`, `coding_task_id`, `attempt_id`,
  `attempt_number`, `request_id`, `thread_id`, `source_message_id`,
  `adapter_kind`
- execution context: `repo_root`, `worktree_path`, `base_head`
- validation/mutation context: `validation_status`,
  `validation_fail_signature`, `mutation_guard_status`
- changed path summary: `changed_paths` (bounded to 50),
  `changed_paths_total`, `changed_paths_truncated`
- patch metadata: `patch_status`, `patch_path`, `patch_sha256`,
  `patch_size_bytes`, `patch_total_bytes`

Behavior by terminal outcome:
- Isolated success with changes:
  - Captures bounded `git diff --binary HEAD --` evidence
  - Emits `task.patch_artifact_created`
  - Includes compact `coding_patch` metadata in terminal payload and stored
    coding result artifacts
- Final validation failure with changes:
  - Captures the same bounded patch/manifest evidence before failure terminal
    emission
  - Preserves existing failure semantics
- Mutation scope violation:
  - Does not produce an apply-ready patch file
  - Writes manifest evidence with `patch_status=blocked_scope_violation`
    and bounded changed-path summary
- Oversized patch:
  - Writes manifest evidence with `patch_status=too_large`
  - Does not write partial patch content as if complete

Cleanup/retention interaction:
- Patch artifacts are written before isolated worktree cleanup/retention
  decisions finalize.
- Worktree cleanup can succeed or fail independently of patch artifact
  availability.
- Retained worktrees remain optional and policy-driven; artifacts are separate
  operator evidence.

Explicit non-goals:
- no auto-apply
- no auto-commit
- no auto-merge
- no promotion back to active checkout
- no branch push
- no release-proof claim by artifact presence alone

### Commit-After-Green Gate (Phase 4)

- Commit behavior is opt-in via `commit_after_validation=true`.
- Commit behavior requires a valid resolved worktree lease.
- Commit behavior runs only after validation passes.
- Commit behavior does not run when validation fails, errors, is skipped, or is
  not configured.
- Commit operations run inside the lease `worktree_path` only.
- Commit hash and bounded commit metadata are captured in result/event envelopes.
- Guardian still does not auto-create long-lived branches for commit-gated flow.
- Guardian still does not merge branches or push branches.
- This is a backend seam only in this phase. There is no UI command center for
  commit-gate inspection yet.

### Normalized Test Results

A normalized test-result contract now exists in `guardian/agents/test_results.py`.
It is a preparatory seam for future autonomous convergence work, but this task
does not make the coding worker run tests automatically. Any later loop that
reasons about pass/fail convergence must consume the normalized contract rather
than raw stdout/stderr.

### Bounded Validation Retry

The coding worker can run a supervised validation command after the adapter
returns, as long as the task permits shell execution and a working directory
is available. Validation evidence is normalized before it is stored or
emitted.

Validation failure can trigger bounded retries, but only when the mutation
scope guard is clean or within the allowed path set. The worker stops retrying
as soon as the guard reports a scope violation.

This is still supervised, bounded behavior. It does not add retry-until-tests-
pass convergence, worktree isolation, commit behavior, auto-merge, or infinite
retry. Future convergence work should consume the normalized validation result
instead of parsing raw stdout or stderr directly.

### Mutation Scope Guard

The worker now snapshots Git porcelain state before each adapter attempt when
the task cwd resolves to a Git repository.

- Dirty preflight worktrees fail closed with `DIRTY_WORKTREE_PRECHECK_FAILED`
  before the adapter runs.
- After each attempt, the worker compares the new porcelain state against the
  preflight snapshot.
- When `allow_write=false`, any new repository mutation fails closed with
  `MUTATION_SCOPE_VIOLATION`.
- When `allow_write=true`, changed paths must match the normalized
  `permission_policy.allowed_paths` scope.
- The scope entries are repo-relative. `.` is the explicit repository-root
  token; a path prefix covers an exact file or a directory and everything
  beneath it, matched on a path boundary; an explicit `fnmatch` glob is
  accepted as written.
- An empty entry, an absolute path outside the bound repository, and any `..`
  segment are rejected. None of them widens the allowed scope, and none of
  them implies whole-repository access.
- A scope that resolves to no valid entry authorizes nothing: with
  `allow_write=true` the attempt fails closed with `MUTATION_SCOPE_VIOLATION`.
- The git mutation guard and the isolated worktree scope check share this one
  interpretation and reach the same decision for the same scope and the same
  changed path.
- If the cwd is not a Git repository, the worker emits explicit unverified
  evidence and continues without claiming scope proof.
- Scope violations stop the retry loop immediately.
- Validation failures may retry only when the mutation scope is clean or
  within the allowed path set.
- These checks remain detective rather than preventive: the write has already
  landed when the guard fires, and no sandbox provider backs them.

The coding worker can run one optional validation command after the adapter
returns, as long as the task permits shell execution and a working directory
is available. Validation evidence is normalized before it is stored or
emitted.

This remains supervised and bounded. A missing validation command means no
validation run happened. Validation failure may feed the bounded retry loop
described below, but this section does not imply commit behavior or autonomous
convergence.

### Bounded Validation Retry

The worker can retry a coding attempt when the adapter succeeds but validation
fails. Retry boundaries are controlled by `max_validation_attempts` on the
task, with a default of `1` and a hard cap of `3`. Values below `1` normalize
to `1`; values above the cap are rejected at the route boundary and bounded in
the worker path as a defense-in-depth check.

The worker may perform a supervised validation pass after a success-like
adapter result when `validation_command` is configured and shell execution is
allowed. The command runs in the task `cwd`, the subprocess result is
normalized through `guardian/agents/test_results.py`, and the normalized
evidence is stored on the coding result and emitted on the terminal event.
Retries happen only when all of the following are true:

- the adapter returned a success-like result,
- a validation command is configured,
- shell execution is allowed by policy,
- the task has a working directory, and
- the validation result is `failed`.

Retries do not happen when validation is `not_run`, when shell execution is
blocked, when no validation command is configured, when the adapter itself
fails before validation can run, when validation returns `error`, when the same
fail signature repeats, or when the configured attempt budget is exhausted.
Validation evidence stays normalized and bounded, and retry prompts only reuse
the previous attempt’s bounded failure evidence.

`max_validation_attempts` is the bounded retry ceiling. Values clamp to the
worker policy range, and retries only happen when the mutation scope guard
remains clean or within the allowed path set.
This is still not autonomous commit/merge behavior. MiniMax can run behind the
`codex` adapter, but Guardian owns the retry boundary and future convergence
work must consume the normalized validation results instead of raw logs.

### Explicit Non-Goals Still In Effect

- No auto-commit loop from generic coding-worker runs.
- No auto-merge.
- No branch push.
- No promotion of isolated worktree output into the operator checkout.
- No infinite retry behavior.
- No release-readiness claim from this seam by itself.

```bash
BASE_URL="${BASE_URL:-http://localhost:8888}"
API_KEY="${GUARDIAN_API_KEY:-}"

curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/agents/coding/execute" \
  -d '{
    "coding_task_id": "task-001",
    "thread_id": "123",
    "source_message_id": "msg-456",
    "attempt_id": "attempt-1",
    "user_id": "local",
    "project_id": null,
    "adapter_kind": "pi_sdk",
    "instructions": "Create a test file at hello.txt",
    "repo_root": "/workspace/repo",
    "context_summary": null,
    "permission_policy": {
      "allow_shell": true,
      "allow_network": false,
      "allow_write": true,
      "allowed_paths": ["hello.txt"],
      "max_runtime_seconds": 300
    }
  }'
```

**Response:**
```json
{
  "ok": true,
  "run_id": "run_abc123def456",
  "deployment_id": "dep_xyz789",
  "coding_task_id": "task-001"
}
```

### Poll Run Events

```bash
RUN_ID="run_abc123def456"

curl -N -sS \
  -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/agents/runs/$RUN_ID/events"
```

**Expected event progression:**
1. `created` - Run created, task enqueued
2. `task.running` - Worker picked up task
3. `task.validation_started` and, if configured, `task.validation_passed`, `task.validation_failed`, or `task.validation_retrying`
4. `task.completed` or `task.failed` - Execution finished

## Operational Drill

### 1. Core Health

```bash
docker compose config --quiet

# Check containers
docker compose ps

# Verify Redis connectivity
docker exec codexify-redis-1 redis-cli ping

# Check queue is empty
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:coding-execution
```

### 2. Submit a Test Task

```bash
GUARDIAN_API_KEY="$(scripts/dev/dev-key.sh)"

RESP="$(
  curl -sS -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $GUARDIAN_API_KEY" \
    http://localhost:8888/api/agents/coding/execute \
    -d '{
      "coding_task_id": "health-check-001",
      "thread_id": null,
      "source_message_id": null,
      "attempt_id": "attempt-1",
      "user_id": "local",
      "project_id": null,
      "adapter_kind": "pi_sdk",
      "instructions": "echo health-check-ok",
      "repo_root": "/tmp",
      "context_summary": null,
      "permission_policy": {
        "allow_shell": true,
        "allow_network": false,
        "allow_write": false,
        "allowed_paths": [],
        "max_runtime_seconds": 30
      }
    }'
)"

echo "$RESP" | jq
RUN_ID="$(echo "$RESP" | jq -r '.run_id')"
```

### 3. Observe Queue

```bash
# Check queue depth
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:coding-execution

# Peek at messages (don't pop)
docker exec codexify-redis-1 redis-cli LRANGE codexify:queue:coding-execution 0 -1
```

### 4. Stream Events

```bash
curl -N -sS \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  "http://localhost:8888/api/agents/runs/$RUN_ID/events"
```

### 5. Start Worker Manually

```bash
docker compose build worker-coding
docker compose run --rm --no-deps --entrypoint python worker-coding /app/backend/scripts/docker/check_worker_coding_readiness.py --format human
docker compose up -d worker-coding
```

## Docker Compose

The supported source lane is the `worker-coding` service in
`docker-compose.yml`. It builds Dockerfile target `worker-coding-runtime`,
mounts the tracked Guardian and runner sources, and mounts only the named Pi
configuration volume at `/home/codexify/.pi`. Its healthcheck runs the same
canonical readiness script used by operators; it is not a process-only health
claim.

The packaged `docker-compose.runtime.yml` lane is a separate artifact contract
and is not made Pi-ready by this source-Compose change.

## Failure Signatures

| Symptom | Likely Cause | Remediation |
|---------|--------------|-------------|
| Readiness exits 78 | One or more Pi prerequisites are `blocked` | Use the stable readiness reason and recovery table above; do not enqueue work |
| Readiness exits 78 with `git_missing` | The image has no usable Git CLI | Rebuild from the canonical `backend/Dockerfile`; the `runtime` stage installs Git and `worker-coding-runtime` inherits it |
| `ADAPTER_NOT_FOUND` in worker logs or run events | `adapter_kind` resolved to an unregistered adapter | Check the deployment spec and `guardian/agents/adapters/__init__.py` |
| Redis connection errors | Wrong `REDIS_URL` | Verify `redis://redis:6379/0` in container |
| Thread injection fails silently | No Postgres / `_has_db()` false | Check `DATABASE_URL` env var |
| Tasks stuck in queue | Worker not running | Start worker or check logs |
| Idempotency not working | Old run_id in retry | Each attempt should have unique `attempt_id` |
| `MUTATION_SCOPE_VIOLATION` with a `mutation_guard_warning` naming an unresolved scope | The task's `allowed_paths` resolved to no valid entry — an empty string, an absolute path outside the bound repository, a `..` segment, or a missing list | Name the scope explicitly: `.` for the whole bound repository, a repository-relative path prefix, or a glob. An empty scope is no longer whole-repository access |
| `MUTATION_SCOPE_VIOLATION` on a delegated task that used to succeed | The delegated-task posture still emits `allowed_paths=("",)` | The upstream Guardian emitter must migrate the delegated scope to `(".",)`. This worker no longer treats an empty scope as the whole repository |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis connection |
| `DATABASE_URL` | For thread injection | None | Postgres for result injection |
| `GUARDIAN_DB_URL` | For thread injection | None | Alternative DB URL |
| `GUARDIAN_API_KEY` | Yes | None | Worker-to-Guardian service authentication for invocation-bound credential lease requests; not a provider credential |
| `CODING_WORKER_POLL_INTERVAL_SECONDS` | No | `0.5` | Poll frequency |
| `CODEXIFY_SINGLE_USER_ID` | For local dev | `local` | User context |
| `CAMPAIGN_RUNNER_PROVIDER_ADAPTER` | No | `pi` | Declares the preferred Campaign Runner adapter seam |
| `CAMPAIGN_RUNNER_PI_ROUTE` | No | `default` | Declares the requested Pi route label |
| `CAMPAIGN_RUNNER_REQUIRE_BACKEND_RECEIPT` | No | `true` | Documents that brokered execution should preserve backend receipts |
| `CODEXIFY_DEFAULT_HARNESS` | No | `pi` | Set in the Guardian runtime environment; provider/model and credential authority remain invocation-scoped |

## Pi Broker Operational Note

Guardian accepts the initial Pi adapter kinds `pi`, `pi_sdk`, and
`pi_codex_runner`. The latter remains a legacy-compatible name for the Pi
broker lane; it does not select a provider or model. Each account invocation
must carry its own authorized provider/model binding and credential reference.
This branch-local implementation does not widen the repository's release
support claims or make every Pi provider/model combination a proven runtime
path.

This runbook does not describe an autonomous retry-until-tests-pass loop. The
current coding worker executes a single adapter attempt, returns the result
through `AgentStore.store_coding_result()`, and records failure events when
execution or result delivery fails.

## Monitoring

### Queue Metrics

```bash
# Queue depth
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:coding-execution

# Message age (first item)
docker exec codexify-redis-1 redis-cli LINDEX codexify:queue:coding-execution -1 | jq -r '.created_at'
```

### Worker Health

```bash
# Check if worker is running
docker compose ps worker-coding

# View worker logs
docker compose logs worker-coding --tail=100 -f
```
