# Codexify Solo Operator Coding Worker Runbook

Purpose: give a solo operator the current truth surface for Guardian-mediated
coding-worker work without implying autonomous convergence, commit behavior,
or unbounded retry loops.

Last updated: 2026-05-26

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

- Every attempted coding-worker run captures Git porcelain state before the
  adapter executes when the cwd resolves to a Git repository.
- If the worktree is already dirty before execution, the worker fails closed
  with `DIRTY_WORKTREE_PRECHECK_FAILED` before the adapter runs.
- After each adapter attempt, the worker captures Git porcelain state again and
  compares it to the preflight snapshot.
- When `allow_write=false`, any new repository mutation fails closed with
  `MUTATION_SCOPE_VIOLATION`.
- When `allow_write=true`, changed paths must match `permission_policy.allowed_paths`.
- Allowed paths support exact repo-relative paths, directory prefixes ending in
  `/`, and simple glob patterns via `fnmatch`.
- Absolute paths and `..` segments in `allowed_paths` are ignored safely.
- If the cwd is not a Git repository, the worker emits explicit unverified
  evidence and continues without claiming scope proof.
- Scope violations stop the retry loop immediately.
- Validation failures may retry only when mutation scope is clean or within the
  allowed path set.

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
- If `allow_write=true`, every changed path must match a sanitized
  `allowed_paths` entry. Supported matches are:
  - exact repo-relative paths
  - directory prefixes ending in `/`
  - simple `fnmatch` glob patterns
- Absolute policy paths and paths containing `..` are ignored safely and do
  not widen the allowed scope.
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
- Downstream provider/model identities may still resolve through the Pi broker
  adapter, but Guardian still owns the loop boundary and stops at the bounded
  validation attempts.
  boundary and stops after the bounded attempts are exhausted.

## Follow-Through Rule

When the worker-side loop is implemented later, it must:

1. normalize subprocess output through this contract,
2. persist or forward the normalized result,
3. keep retry policy separate from normalization, and
4. keep operator-visible truth deterministic across repeated attempts.
# Codexify Coding Worker Runbook

Purpose: Operating runbook for the Guardian coding-worker adapter pipeline (ADR-020).
Last updated: 2026-05-10
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
- `pi_codex_runner` -> `pi_codex_runner`

Public coding-execution requests should use one of the explicit supported
adapter kinds above. Direct Codex/Claude adapter kinds are unsupported for
Campaign Runner and fail closed rather than remapping silently. `mock` and
`external_cli` are not part of the supported public route contract.

The supported local Compose worker also needs the `codex_runner` tree available
at `/app/codex_runner` so the Pi runner path stays runnable when selected.

Unknown adapter names fail closed with `ADAPTER_NOT_FOUND`; route acceptance is
not execution success.

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
- When `allow_write=true`, changed paths must match `permission_policy.allowed_paths`.
- Allowed paths are repo-relative only. Exact paths, directory prefixes ending
  in `/`, and simple `fnmatch` globs are accepted.
- Absolute paths and `..` segments in `allowed_paths` are ignored safely.
- If the cwd is not a Git repository, the worker emits explicit unverified
  evidence and continues without claiming scope proof.
- Scope violations stop the retry loop immediately.
- Validation failures may retry only when the mutation scope is clean or
  within the allowed path set.
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
This is still not autonomous commit/merge behavior. Downstream provider/model
identity can be resolved by the Pi broker adapter and recorded in backend
receipts, but Guardian owns the retry boundary and future convergence work
must consume the normalized validation results instead of raw logs.

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
    "adapter_kind": "pi",
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
set -a; source .env; set +a

# Check containers
docker compose ps

# Verify Redis connectivity
docker exec codexify-redis-1 redis-cli ping

# Check queue is empty
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:coding-execution
```

### 2. Submit a Test Task

```bash
set -a; source .env; set +a

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
      "adapter_kind": "pi",
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
set -a; source .env; set +a

# In a separate terminal
python -m guardian.workers.coding_worker
```

## Docker Compose

Add `worker-coding` to `docker-compose.runtime.yml`:

```yaml
worker-coding:
  image: ${CODEXIFY_IMAGE_REGISTRY:-ghcr.io/resonant-jones}/codexify-runtime:${CODEXIFY_IMAGE_TAG:-local-beta}
  working_dir: /app
  depends_on:
    redis:
      condition: service_healthy
    backend:
      condition: service_healthy
  env_file: ${CODEXIFY_RUNTIME_ENV_FILE:-.env}
  environment:
    <<: *postgres_env
    LANG: C.UTF-8
    LC_ALL: C.UTF-8
    PYTHONUTF8: "1"
    PYTHONIOENCODING: utf-8
    PYTHONPATH: /app
    REDIS_URL: redis://redis:6379/0
    GUARDIAN_DB_URL: postgresql://${POSTGRES_USER:-codexify}:${POSTGRES_PASSWORD:-codexify}@db:5432/${POSTGRES_DB:-Codexify}
    NEO4J_BOLT_URL: bolt://neo4j:7687
  restart: unless-stopped
  command: ["python", "-m", "guardian.workers.coding_worker"]
```

## Failure Signatures

| Symptom | Likely Cause | Remediation |
|---------|--------------|-------------|
| `ADAPTER_NOT_FOUND` in worker logs or run events | `adapter_kind` resolved to an unregistered adapter | Check the deployment spec and `guardian/agents/adapters/__init__.py` |
| Redis connection errors | Wrong `REDIS_URL` | Verify `redis://redis:6379/0` in container |
| Thread injection fails silently | No Postgres / `_has_db()` false | Check `DATABASE_URL` env var |
| Tasks stuck in queue | Worker not running | Start worker or check logs |
| Idempotency not working | Old run_id in retry | Each attempt should have unique `attempt_id` |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis connection |
| `DATABASE_URL` | For thread injection | None | Postgres for result injection |
| `GUARDIAN_DB_URL` | For thread injection | None | Alternative DB URL |
| `CODING_WORKER_POLL_INTERVAL_SECONDS` | No | `0.5` | Poll frequency |
| `CODEXIFY_SINGLE_USER_ID` | For local dev | `local` | User context |
| `CAMPAIGN_RUNNER_PROVIDER_ADAPTER` | No | `pi` | Declares the preferred Campaign Runner broker adapter posture |
| `CAMPAIGN_RUNNER_PI_ROUTE` | No | `default` | Selects the Pi broker route when the worker launches Campaign Runner |
| `CAMPAIGN_RUNNER_REQUIRE_BACKEND_RECEIPT` | No | `true` | Requires backend receipts before brokered execution is treated as successful |

## Pi Broker Operational Note

Campaign Runner coding execution should be configured through the Pi broker
adapter for this module. Guardian should receive coding requests with
`adapter_kind="pi"` so the worker routes execution through the registered Pi
broker seam. Direct Codex/Claude CLI execution is unsupported here. If Pi
resolves work onto a downstream provider/model, that identity must be surfaced
through the stored backend receipt rather than inferred from worker config.

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
