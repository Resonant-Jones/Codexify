# Codexify Solo Operator Coding Worker Runbook

Purpose: give a solo operator the current truth surface for Guardian-mediated
coding-worker work without implying autonomous convergence, commit behavior,
or unbounded retry loops.

Last updated: 2026-05-09

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
- MiniMax may run behind the `codex` adapter, but Guardian still owns the loop
  boundary and stops at the bounded validation attempts.

## Follow-Through Rule

When the worker-side loop is implemented later, it must:

1. normalize subprocess output through this contract,
2. persist or forward the normalized result,
3. keep retry policy separate from normalization, and
4. keep operator-visible truth deterministic across repeated attempts.
# Codexify Coding Worker Runbook

Purpose: Operating runbook for the Guardian coding-worker adapter pipeline (ADR-020).
Last updated: 2026-05-09
Source anchors:
- `guardian/routes/agent_orchestration.py` - `POST /api/agents/coding/execute`
- `guardian/agents/adapters/__init__.py` - adapter registry
- `guardian/agents/adapters/pi_codex_runner.py` - PiCodexRunnerAdapter
- `guardian/agents/adapters/codex.py` - CodexAdapter
- `guardian/agents/adapters/claudecode.py` - ClaudeCodeAdapter
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

- `pi_sdk`, `pi`, or `pi_codex_runner` -> `pi_codex_runner`
- `codex` -> `codex`
- `claudecode` -> `claudecode`

Unknown adapter names fail closed with `ADAPTER_NOT_FOUND`; route acceptance is
not execution success.

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

### Single-Attempt Validation Command

The worker may perform a supervised validation pass after a success-like
adapter result when `validation_command` is configured and shell execution is
allowed. The command runs in the task `cwd`, the subprocess result is
normalized through `guardian/agents/test_results.py`, and the normalized
evidence is stored on the coding result and emitted on the terminal event.

Validation outcomes are bounded and explicit:

- `passed` keeps the attempt successful.
- `not_run` records a supervised skip, usually because shell execution is
  blocked or the working directory is missing.
- `failed` and `error` fail closed for the current attempt and emit
  `task.failed` with `VALIDATION_FAILED`.

`max_validation_attempts` is the bounded retry ceiling. Values clamp to the
worker policy range, and retries only happen when the mutation scope guard
remains clean or within the allowed path set.

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
3. `task.completed` or `task.failed` - Execution finished

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
| Idempotency not working | Stale or duplicated task payload | Each attempt should have unique `attempt_id` |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis connection |
| `DATABASE_URL` | For thread injection | None | Postgres for result injection |
| `GUARDIAN_DB_URL` | For thread injection | None | Alternative DB URL |
| `CODING_WORKER_POLL_INTERVAL_SECONDS` | No | `0.5` | Poll frequency |
| `CODEXIFY_SINGLE_USER_ID` | For local dev | `local` | User context |
| `CODEX_ADAPTER_COMMAND` | For `codex` adapter customization | `codex exec` | Command prefix used by the Codex adapter |

## MiniMax / Codex Operational Note

MiniMax-backed coding execution should be configured through the Codex CLI
profile/config outside Guardian. Guardian should receive coding requests with
`adapter_kind="codex"` so the worker routes execution through the registered
Codex adapter. If needed, set `CODEX_ADAPTER_COMMAND` to point the Codex adapter
at the desired Codex CLI profile.

This runbook does not describe an autonomous retry-until-tests-pass loop. The
current coding worker executes a single adapter attempt with at most one
optional validation pass, returns the result through
`AgentStore.store_coding_result()`, and records failure events when execution
or result delivery fails.

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
