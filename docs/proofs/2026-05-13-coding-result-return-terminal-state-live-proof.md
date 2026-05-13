# Coding Result Return and Terminal-State Live Proof Attempt

**Artifact date:** 2026-05-13  
**Branch:** `main`  
**HEAD commit:** `b53ffd10277e4f41a079a70a7dadb04fe07f9c16`  
**Runtime path:** Local Docker Compose stack (`db`, `redis`, `neo4j`, `backend`, `frontend`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`, `worker-warmup`; `worker-coding` was temporarily stopped for deterministic worker probing)  
**Proof window:** 2026-05-13T14:03:12-04:00 to 2026-05-13T14:12:02-04:00

## Scope

This attempt was meant to prove the supported local path for coding-result return after commit `85258b6a547077044ee99c0d6754881bc212e418` repaired the backend store and terminal run-state repair behavior.

Required proof goals:
- coding results return through Guardian into the source thread without duplicate delivery
- the durable run record converges to a terminal state
- bounded delivery and terminal-state evidence appear in stored result/event payloads
- supported-profile posture remains local-first and honest
- Command Center remains non-dispatch / recommendation-only

## What Was Verified

- The repository HEAD included the repair commit ancestry:
  - `git merge-base --is-ancestor 85258b6a547077044ee99c0d6754881bc212e418 HEAD` returned success.
- The repo working tree was clean before the proof run.
- The supported Compose stack came up healthy:
  - `docker compose ps` showed `backend` healthy and `db`/`redis`/`neo4j` healthy.
- Supported-profile health stayed local-first and honest:
  - `GET /health` returned `status: ok` and `release_hold: false`.
  - `GET /health/chat` returned `status: healthy`, `provider: local`, queue depth `0`, and a fresh worker heartbeat.
  - `GET /api/health/llm` reported `status: down` because the local model endpoint timed out, which is honest degradation rather than cloud-provider promotion.
  - `GET /api/llm/catalog` and `GET /api/llm/catalog?include=all` stayed available and did not widen the supported beta claim.

## Commands Run

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git merge-base --is-ancestor 85258b6a547077044ee99c0d6754881bc212e418 HEAD && echo terminal_repair_commit_present

docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend frontend worker-chat worker-coding worker-document-embed worker-chat-embed worker-warmup
docker compose ps

docker compose exec -T backend python - <<'PY'
# Supported-profile probes
# - GET /health
# - GET /health/chat
# - GET /api/health/llm
# - GET /api/llm/catalog
# - GET /api/llm/catalog?include=all
PY

docker compose exec -T backend python - <<'PY'
# Live coding-result proof attempt:
# create source thread, create deployment/run, enqueue coding task
PY

docker compose run --rm --entrypoint python worker-coding - <<'PY'
# Worker probe:
# patch adapter registry and call CodingWorker.poll_once()
PY

docker compose exec -T backend python - <<'PY'
# Post-run evidence collection:
# read run record, source-thread messages, task events, and replay AgentStore.store_coding_result()
PY
```

## Live Proof Attempts and Outcomes

### Attempt 1: public coding-execute route

- `POST /api/agents/coding/execute` with `adapter_kind=codex` was rejected by request validation because the public envelope currently accepts `pi_sdk`, `external_cli`, or `mock`.
- This was a route-shape mismatch, not a successful live proof.

### Attempt 2: public route with `pi_sdk`

- The route accepted the task and created a live run.
- The worker resolved the Pi runner path, but the Compose runtime does not mount the `codex_runner/src/agent-wrapper.js` asset tree.
- Observed failure:
  - `Cannot find module '/app/codex_runner/src/agent-wrapper.js'`
- Result:
  - no source-thread `coding_result` message was delivered
  - terminal task event was `task.failed`
  - live run remained unproven for the result-return requirement

### Attempt 3: direct live queue/store probe

- A fresh source thread was created on the supported backend API.
- A fresh run/deployment was written through the live Guardian store and enqueued on the live Redis coding queue.
- A one-shot worker probe consumed the queue item from the live stack.
- The worker still terminated with a failure terminal event and did not persist a source-thread `coding_result` message on the live path.
- Observed task-event payloads showed:
  - `task.running`
  - `task.failed`
  - `delivery_reason_code: delivery_database_unavailable`
  - `terminal_run_status: failed`
  - `result_message_id: null`

## Evidence Details

### Supported-profile health

- `/health`
  - `status: ok`
  - `release_hold: false`
- `/health/chat`
  - `status: healthy`
  - `provider: local`
  - `queue.depth: 0`
  - fresh worker heartbeat
- `/api/health/llm`
  - `status: down`
  - local provider stayed selected
  - the reported failure was a local endpoint timeout
- `/api/llm/catalog`
  - local catalog visible
- `/api/llm/catalog?include=all`
  - operator catalog visible without widening support

### Source-thread delivery evidence

- Live worker attempts did not produce a persisted `coding_result` message in the source thread.
- For the final fresh run, message count for `kind=coding_result` and `run_id=run_015b9cb7b09b423b` remained `0`.
- The final live worker attempt therefore did not satisfy the source-thread delivery requirement.

### Duplicate-delivery / idempotency evidence

- `AgentStore.store_coding_result()` replay was invoked on an earlier run as a safety check.
- That replay returned:
  - `delivery_status: delivered`
  - `result_message_id: 52`
  - `terminal_run_status: succeeded`
- This proves the store replay/idempotency path can return bounded delivery evidence when invoked directly.
- It does **not** convert the live worker attempt into a PASS, because the live worker did not produce the source-thread message itself.

### Durable terminal-state evidence

- The live worker attempts produced terminal failure events, not terminal success evidence.
- For the final fresh run, task-event payloads reported:
  - `terminal_run_status: failed`
  - `terminal_run_status_updated: false`
  - `delivery_reason_code: delivery_database_unavailable`
- The replay path could update a prior run record to succeeded, but that was a replay of the store seam, not the live worker completion seam.

### Terminal event / envelope evidence

- Final live task-event payloads were bounded and included:
  - `run_id`
  - `source_thread_id`
  - `source_message_id`
  - `coding_task_id`
  - `adapter_kind`
  - `delivery_status`
  - `delivery_reason_code`
  - `terminal_run_status`
- The payloads did **not** include a delivered `result_message_id` from the live worker attempt.

### Command Center boundary evidence

- This proof did not call any dispatch endpoint from Command Center.
- No lease allocation, branch allocation, worktree allocation, or merge automation was triggered by the proof harness.
- The live proof attempt remained on backend/store/worker seams only.

## Validation Results

Not all requested validation commands were run to completion in this attempt because the live proof itself remained blocked at the worker/result-delivery seam.

Observed successful checks:
- `git merge-base --is-ancestor 85258b6a547077044ee99c0d6754881bc212e418 HEAD`
- `docker compose ps`
- `docker compose run --rm migrator`
- `docker compose up -d ...` for the supported stack

Still outstanding for a PASS:
- live source-thread `coding_result` delivery from the worker path
- live terminal success evidence from the worker path
- duplicate-delivery proof from a live worker-delivered result

## Result

**INCOMPLETE**

The idempotent store replay works, but the live worker path in this Compose runtime still did not produce the required source-thread coding result or terminal success evidence.

## Explicit Non-Claims

- This does not prove Command Center dispatch.
- This does not prove lease allocation from UI.
- This does not prove terminal execution from UI.
- This does not prove plugin runtime.
- This does not prove merge automation.
- This does not prove release readiness.
- This does not justify updating `docs/architecture/00-current-state.md` as resolved.

## Follow-up Blocker

The live proof is still blocked by the coding-worker runtime seam in this Compose environment. The worker attempts observed here did not complete the source-thread delivery path on the live stack, so the repaired result-return and terminal-convergence claims remain unproven on the supported path.
