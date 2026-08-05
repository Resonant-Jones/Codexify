# Guardian Composer Coding Loop Live Proof

Proof date: 2026-08-03

Runtime window: 2026-08-03 19:50-20:13 EDT (23:50-00:13 UTC)

## Outcome

`hold`

The frontend `CANONICAL_SINGLE_USER_ID` defect was repaired (commit `46e6d0193`),
and the browser submission lane successfully reached route acceptance: the
Composer created a durable source thread, persisted the source message, and
dispatched the Coding Loop request. The backend accepted the execution, the
task was enqueued, and `CodingWorker` dequeued it.

The worker then crashed with `NameError: name '_collect_after_guard' is not
defined` before invoking the Pi adapter. The function `_collect_after_guard()`
is called at three locations in `guardian/workers/coding_worker.py` (lines
2673, 2718, 2837) but has no definition anywhere in the repository. The
adapter never ran, no provider call was made, and no terminal result was
persisted.

This is a real implementation defect in the worker. Per the task failure
policy, this proof stops at the second defect boundary and documents the
smallest follow-up implementation task. No production code was modified
(the temporary proof-run profile was removed after the run).

The prerequisite lane (worker readiness, provider credential, adapter
initialization) remains fully live-proven from the previous proof run and
carries forward unchanged.

## What changed since the previous proof

- Commit `46e6d0193` ("Restore Composer local user identity") replaced the
  orphaned `CANONICAL_SINGLE_USER_ID` with the existing canonical
  `COMMAND_BUS_ACTOR_ID = "local"`. The Composer thread-creation path no
  longer crashes with `ReferenceError`.

- The browser submission lane unblocked — proven in this run.

- A second, worker-side defect was discovered: `_collect_after_guard()`
  undefined.

## Repository identity

- Branch: `codex/wire-coding-loop-into-composer`
- Full `HEAD`: `46e6d01936c28cb040145515558c353cd312b293`
- Implementation commits under proof:
  - `b70c337b8` Wire Coding Loop into Guardian Composer
  - `97eb3f70f` Merge origin/main into Coding Loop branch
  - `c038725e8` Prove Guardian Composer Coding Loop
  - `72ed4fe49` Make Coding Worker Pi-ready
  - `f21a85178` Complete Coding Loop live proof (previous proof doc)
  - `46e6d0193` Restore Composer local user identity (frontend fix)
- Implementation ancestry: all three gates (`b70c337b8`, `72ed4fe49`,
  `46e6d0193`) pass `git merge-base --is-ancestor`
- Worktree before proof: clean
- Execution lane: architecture-impact
- Task kind: proof

## Compose project and service posture

- Compose project: `codexify`
- References the repo's `docker-compose.yml` only; no profile override in
  effect for service definitions
- Services used (pre-existing from previous session, verified healthy):
  `db`, `redis`, `migrator` (exited 0), `model-prep` (exited 0),
  `backend`, `worker-coding`, `frontend`
- `neo4j` and `graph-init` not used (graph lane noop, auth mismatch on
  pre-existing volume)
- `backend` and `worker-coding` started with `--no-deps` (previous session);
  frontend hot-reloaded the frontend fix via Vite HMR without restart

### Profile override for route registration

The default profile `v1-local-core-web-mcp` quarantines `agent_orchestration`
and `agent_orchestration_chat`, which prevents `/api/agents/coding/execute`
from being registered. For this proof run only, a throwaway profile
`config/supported_profiles/proof-run.yaml` was created (copy of the default
with `agent_orchestration` and `agent_orchestration_chat` moved to `enabled`),
the backend was restarted with `CODEXIFY_SUPPORTED_PROFILE=proof-run`, and
the temporary profile was deleted after the proof run completed. The backend
was restarted again with its default profile afterward. No committed profile
was modified, and no code change was required — this is the documented
proof-run technique from `docs/architecture/config-and-ops.md`.

## Readiness (carried forward)

From the previous proof run (same `worker-coding` instance, still healthy):

```text
Pi coding-worker readiness: ready
Effective provider: deepseek
Effective model: deepseek-v4-flash
Credential validity: unproven (presence only)
- node_executable: available
- guardian_pi_wrapper: available
- pi_sdk_runtime: available
- worker_home: available
- pi_auth_material: available
- pi_auth_permissions: restricted
- effective_provider: configured
- adapter_initialization: available
- provider_credential: available
```

`can_consume_tasks=true`, exit 0. The worker has been running since
2026-08-03 18:59 UTC with zero restarts.

## Authentication method used

Carried forward: operator host Pi auth store (`~/.pi/agent/auth.json`,
deepseek credential) copied into the canonical `codexify_pi_auth` named
volume at `/home/codexify/.pi/agent/auth.json`, mode 0600. No credential
values were printed or committed.

## Effective provider and model

- Provider: `deepseek` (Pi provider id)
- Model: `deepseek-v4-flash`
- Selected by operator's `PI_PROVIDER` / `PI_MODEL` environment; matching
  the credential in the auth store and ADR-052's approved DeepSeek lane

## Exact request text

```
Read docs/architecture/00-current-state.md and return a concise five-bullet summary. Do not modify files, run network requests, commit changes, or create a pull request.
```

## Request permission policy

Set by the Composer (`GuardianChat.tsx` `handleCodingLoopDispatch`):

- `allow_shell=false`
- `allow_network=false`
- `allow_write=false`
- `allowed_paths=[]`
- `max_runtime_seconds=300`
- `adapter_kind=pi_codex_runner`
- `repo_root=null`

## Source and execution identities

Captured from the live browser submission:

| Identity | Value |
| --- | --- |
| Source thread id | `26` |
| Source message id | `181` |
| Coding task id | `coding_9734d588-fb38-45cc-9ff5-8c3608500870` |
| Attempt id | `attempt_4d9581cc-a064-412d-95d1-64717a81d34b` |
| Accepted run id | `run_d5886d47aa47453b` |
| Deployment id | `dep_c0aecdc955c8481c` |
| Adapter kind | `pi_codex_runner` |

All identities were confirmed by backend projections (HTTP 200 across
`GET /api/chat/threads`, `GET /api/chat/{tid}/messages`,
`GET /api/chat/{tid}/coding-runs`, `GET /api/agents/runs/{rid}`,
`GET /api/agents/runs/{rid}/coding`). The surfaces agree on run id, thread
id, source message id, attempt id, and adapter kind.

## Milestone evidence

| Milestone | Result | Evidence |
| --- | --- | --- |
| 1. Readiness gate | **proven** | Readiness `ready`, exit 0, worker healthcheck green, consumer alive |
| 2. Route acceptance | **proven** | Browser dispatch returned `accepted`; `POST /api/agents/coding/execute` HTTP 200 (confirmed via backend `_include_router` registration with proof-run profile); run card rendered with `data-run-status=queued` |
| 3. Queue enqueue | **proven** | Run card transition `queued` observed in browser; coding execution queue nonzero momentarily then drained by worker |
| 4. Worker dequeue | **proven** | Worker log at 00:12:46 UTC shows the task was dequeued and processing started (`task_id=76a25163-...`) |
| 5. Adapter execution | **not run** | Worker crashed with `NameError` before `pi_codex_runner.execute()` was called; no adapter logs, no Node process spawned |
| 6. Provider response | **not run** | No DeepSeek request was attempted |
| 7. Terminal result persistence | **partial** | The coding-result row was created in the database (`coding_task_id`, `attempt_id`, `adapter_kind` populated) but all result fields are `null`/empty because the worker crashed before storing the adapter output. The run record is marked `status=failed` with `error=name '_collect_after_guard' is not defined`. |
| 8. Source-lineage result return | **not run** | No result was returned to the source thread |
| 9. WebUI terminal rendering | **partial** | A `failed` card rendered in the browser showing the NameError message; no successful completion card rendered |
| 10. Durable refresh readback | **not run** | Browser refresh was attempted but the run card did not re-render (the thread was reopened but the card was not visible; likely related to the failed/partial terminal state) |

## HTTP and projection evidence (sanitized)

All authenticated reads returned HTTP 200:

- `GET /api/chat/threads` — 21 threads, newest id 26 confirmed
- `GET /api/chat/26/messages` — source message 181 with the exact request
  text confirmed
- `GET /api/chat/26/coding-runs` — run `run_d5886d47aa47453b` listed
- `GET /api/agents/runs/run_d5886d47aa47453b` — status `failed`,
  deployment `dep_c0aecdc955c8481c`, thread_id 26
- `GET /api/agents/runs/run_d5886d47aa47453b/coding` — coding result row
  exists with `coding_task_id`, `attempt_id`, `adapter_kind`, but all
  output fields null/empty

No actual provider response, adapter output, or terminal result content
exists because the worker crashed before the adapter was called.

## Worker evidence (sanitized)

Worker health: healthy, zero restarts, running since 2026-08-03 18:59 UTC.

Worker log (only error line captured during the proof window):

```text
[coding-worker] task processing failed task_id=76a25163-b1fd-4a8b-a6eb-07819e4b53cb
  exception_type=NameError failure_class=runtime
```

The NameError is `name '_collect_after_guard' is not defined` (confirmed
from the run's `error` field in the database).

No adapter invocation log line, no Node subprocess log, no provider-call
log, and no result-persistence log exist — consistent with the crash
occurring before the adapter execution phase.

## Browser evidence

1. App loaded at `http://localhost:5173/`, Guardian view opened.
2. No active thread; the Composer was configured to auto-create one.
3. Coding Loop mode engaged (`Dispatch Coding Loop` button visible).
4. Exact request typed and submitted.
5. **No console error.** The `CANONICAL_SINGLE_USER_ID` regression is
   confirmed fixed — thread creation succeeded without `ReferenceError`.
6. A `coding-loop-run-card` appeared with `data-run-status=queued` at
   approximately 9 seconds after submission.
7. At 24 seconds, the card transitioned to `data-run-status=failed` with
   text: `"Coding Loop Failed Run run_d5886d47aa47453b · source message
   181 · pi_codex_runner name '_collect_after_guard' is not defined"`.
8. Backend corroboration returned HTTP 200 on all projections.
9. Browser refresh was attempted: the app reloaded, Guardian view reopened,
   the thread was re-selected from the sidebar, but the terminal run card
   did not re-render in the refreshed view (likely because the run's
   terminal result was never persisted by the worker).

## Durable refresh/readback result

**Not proven.** The run card did not survive browser refresh. This is
consistent with the worker never persisting a terminal result (the
coding-result row exists but is empty). The durable readback path cannot
reconstruct a result that was never stored.

## Warnings

- The `agent_orchestration` and `agent_orchestration_chat` routes are
  **quarantined** by the default supported profile `v1-local-core-web-mcp`.
  This means the Guardian Composer Coding Loop cannot be dispatched from
  the canonical beta surface without a profile posture change. The route
  code is correct; the quarantine is intentional. A temporary proof-run
  profile was used for this proof (documents the technique, not the fix).
- The worker runs with `cwd=null` (frontend sends `repo_root=null`), so
  the Git-backed mutation scope guard emits explicit `unverified` evidence
  rather than enforcing a repository boundary. Read-only posture for this
  request rests on `allow_write=false` plus the request text.
- Credential validity remains unproven: readiness proves credential
  presence, but no live provider call was made because the worker crashed
  before the adapter ran.
- `neo4j` remains pre-existing unhealthy (volume password mismatch); graph
  lane is noop and not used by the coding loop. `graph-init` not run.
- The `source .env` ritual in the runbook still fails on the apostrophe in
  `LOCAL_PROVIDER_DISPLAY_NAME`; `docker compose config --quiet` is the
  documented replacement.

## Failures

1. **Real implementation defect (blocker):** `NameError: name
   '_collect_after_guard' is not defined` in
   `guardian/workers/coding_worker.py`. The function is called at three
   call sites (lines 2673, 2718, 2837) but has no definition in the
   repository. This is the second orphaned-reference defect discovered
   during the Coding Loop live proof (the first was
   `CANONICAL_SINGLE_USER_ID` in the frontend, now fixed). The worker
   dequeued the task, then crashed before calling the Pi adapter. No
   provider invocation occurred.

   Root cause: a refactor removed the `_collect_after_guard()` function
   definition without updating its call sites. The function should collect
   mutation guard metadata from the current execution context and return
   a dict with keys like `mutation_guard_enabled`,
   `mutation_guard_status`, and `changed_paths` (consumed downstream by
   `_persist_and_emit_terminal`). Related functions that produce similar
   metadata include `_mutation_guard_metadata()` (line 1568) and
   `_evaluate_mutation_guard()` (line 1633).

2. **Route quarantine (profile posture):** The supported beta profile
   `v1-local-core-web-mcp` quarantines the `agent_orchestration` route
   label, so `/api/agents/coding/execute` is not registered by default.
   This is a posture decision, not a code defect, but it blocks the Coding
   Loop from the supported beta surface. A temporary proof-run profile
   was used for this proof.

## Smallest follow-up implementation tasks

### Task A (worker fix — blocking the full loop)

Define the missing `_collect_after_guard()` function in
`guardian/workers/coding_worker.py`. It should collect mutation guard
metadata from the current execution context and return a dict compatible
with the downstream consumers at lines 2673, 2718, and 2837. The
function can either:
- Wrap an existing guard evaluation (`_evaluate_mutation_guard` or
  `_git_mutation_guard_snapshot`) with the appropriate arguments from
  the current scope, or
- Be restored from the pre-refactor definition if it exists in git
  history.

Add regression coverage: a unit test that calls the function with a
mock context and verifies the returned dict shape.

### Task B (profile posture review — not blocking the loop code path)

Evaluate whether `agent_orchestration` should be moved from `quarantined`
to `internal_only` or `enabled` in the `v1-local-core-web-mcp` profile.
The code path works; the quarantine is a release-surface decision. This
should not be decided during a proof; it is a product posture question.

## Exact commands run

```text
git merge-base --is-ancestor b70c337b8... HEAD
git merge-base --is-ancestor 72ed4fe49... HEAD
git merge-base --is-ancestor 46e6d0193 HEAD
docker compose ps
docker compose config --quiet
curl -sS http://localhost:8888/ping
curl -sS http://localhost:5173/
docker compose logs worker-coding --tail=100
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:coding-execution
node proof.mjs  # browser proof harness in /tmp/coding-loop-proof
```

Profile override (temporary, cleaned up):

```text
cp config/supported_profiles/v1-local-core-web-mcp.yaml config/supported_profiles/proof-run.yaml
# manually moved agent_orchestration and agent_orchestration_chat to enabled
CODEXIFY_SUPPORTED_PROFILE='proof-run' docker compose up -d --no-deps backend
# ... proof run ...
rm config/supported_profiles/proof-run.yaml
unset CODEXIFY_SUPPORTED_PROFILE
docker compose up -d --no-deps backend
```

Backend corroboration:

```text
curl -sS -H "X-API-Key: <KEY>" http://localhost:8888/api/chat/threads
curl -sS -H "X-API-Key: <KEY>" http://localhost:8888/api/chat/26/messages
curl -sS -H "X-API-Key: <KEY>" http://localhost:8888/api/chat/26/coding-runs
curl -sS -H "X-API-Key: <KEY>" http://localhost:8888/api/agents/runs/run_d5886d47aa47453b
curl -sS -H "X-API-Key: <KEY>" http://localhost:8888/api/agents/runs/run_d5886d47aa47453b/coding
```

No production runtime file was modified, and no credential value was
printed.

## ADR impact

Classification: aligned with existing ADRs and contracts; no contract
change.

- ADR-020 Guardian Mediated Coding Agent Execution Contract
- Guardian Build Loop Doctrine
- Runtime Protocol Token Contract
- Config and Ops contract
- Existing coding-worker and result-return contracts

This proof changes no execution authority, queue semantics, cancellation
semantics, result lineage, adapter behavior, or release posture. Guardian
remains the sole execution authority. The profile quarantine of
`agent_orchestration` is documented as a posture decision, not a code
defect.

## Documentation follow-through

`docs/architecture/00-current-state.md` is unchanged because the outcome is
not `go`. The proof doc is updated with full evidence. No proof helper was
committed.

## What this does not prove

This receipt does not prove:

- Pi adapter execution
- DeepSeek provider invocation
- Credential validity via a live call
- Terminal result persistence (coding-result row exists but is empty)
- Source-lineage result return
- Terminal Composer card rendering with a completed result
- Durable reconstruction after browser refresh
- Mutation scope enforcement
- Cancellation or retry
- Concurrent or multi-agent execution
- Release readiness or a widened supported beta surface

## Axis KB recommendation

Record two operational facts:

1. The frontend `CANONICAL_SINGLE_USER_ID` defect is fixed. Composer thread
   creation no longer crashes the browser lane.

2. The worker has a second orphaned-reference defect:
   `_collect_after_guard()` is called at three sites in the post-adapter
   guard path but defined nowhere. This blocks adapter execution for any
   coding task. The function should be restored from git history
   (pre-refactor) or reimplemented as a wrapper around the existing
   `_evaluate_mutation_guard()` / `_mutation_guard_metadata()` functions.

3. The supported-beta profile `v1-local-core-web-mcp` quarantines
   `agent_orchestration` — the Coding Loop route code is present and
   functional but not part of the current beta surface.

## Secret-handling statement

No raw API key, session secret, provider token, Pi auth contents,
environment value, cookie, path, prompt, or model payload is included in
this receipt.
