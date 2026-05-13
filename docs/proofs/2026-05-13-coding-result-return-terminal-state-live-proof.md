# Coding Result Return and Terminal-State Live Proof

**Artifact date:** 2026-05-13  
**Branch:** `main`  
**HEAD commit:** `46f0caaa699915ec04dc955ba7066e0639180a7a`
**Runtime path:** Supported local Docker Compose stack with `backend`, `frontend`, `db`, `redis`, `neo4j`, and the repaired `worker-coding` service. The worker now binds Guardian DB state directly and uses the local `qwen3-coder:30b` Ollama tag through the Codex adapter command.
**Proof window:** 2026-05-13T17:30:51-04:00 to 2026-05-13T17:35:46-04:00

## Scope

This proof reran the supported Compose coding-worker path after the worker/runtime repair and verified:

- coding results return through Guardian into the source thread without duplicate delivery
- the durable run record converges to a terminal state
- bounded delivery and terminal-state evidence appear in stored result/event payloads
- supported-profile posture remains local-first and honest
- Command Center remains non-dispatch / recommendation-only

## Repair Commit Ancestry

- `git merge-base --is-ancestor 85258b6a547077044ee99c0d6754881bc212e418 HEAD` returned success.

## Commands Run

```bash
git branch --show-current
git rev-parse HEAD
git merge-base --is-ancestor 85258b6a547077044ee99c0d6754881bc212e418 HEAD && echo terminal_repair_commit_present

docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend frontend worker-chat worker-coding worker-document-embed worker-chat-embed worker-warmup
docker compose ps

docker compose exec worker-coding sh -lc 'python - <<PY
# verify GuardianDB bootstrap can read agent_deployments and agent_runs
PY'

./.venv/bin/python -u - <<'PY'
# create a fresh source thread, post a source message, invoke
# POST /api/agents/coding/execute with adapter_kind=codex, and poll
# the live run until it reaches a terminal state
PY

docker compose exec backend sh -lc 'python - <<PY
# read Redis task-event stream, replay AgentStore.store_coding_result(),
# and confirm thread message count stays one for the run_id
PY'

./.venv/bin/python -m pytest -v guardian/tests/workers/test_coding_worker.py
./.venv/bin/python -m pytest -v guardian/tests/routes/test_agent_orchestration_events.py
./.venv/bin/python -m pytest -v guardian/tests/routes/test_coding_work_orders.py
./.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py
./.venv/bin/python scripts/validate_docs.py
git -c filter.lfs.clean=cat -c filter.lfs.smudge=cat diff --check -- guardian/workers/coding_worker.py guardian/tests/workers/test_coding_worker.py docker-compose.yml docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md
git -c filter.lfs.clean=cat -c filter.lfs.smudge=cat diff --check -- docs/proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md
```

## Supported-Profile Health

- `GET /health` returned `status: ok` and `release_hold: false`.
- `GET /health/chat` reported a healthy local chat posture with queue depth `0` and a fresh worker heartbeat.
- `GET /api/health/llm` remained honest about local-model behavior and did not widen support claims to cloud provider beta posture.
- `GET /api/llm/catalog` and `GET /api/llm/catalog?include=all` stayed available.

## Live Proof Result

### Run identity

- `thread_id: 41`
- `source_message_id: 61`
- `deployment_id: dep_83fc66c9e1404352`
- `run_id: run_1ab6883a1fa94dab`
- `coding_task_id: coding-live-1778707865`
- `result_message_id: 62`

### Route and worker path

- The public coding route accepted the canonical `codex` adapter request shape.
- The worker bootstrap now binds Guardian DB state directly, so the worker can see `agent_deployments` and `agent_runs`.
- The worker published `task.running` with `adapter_kind: codex`.
- The Codex adapter executed through the repaired supported path.

### Source-thread delivery evidence

- The source thread contains exactly one `coding_result` message for `run_1ab6883a1fa94dab`.
- That message is bounded and includes lineage metadata back to the source thread and source message.
- The result message was injected through `AgentStore.store_coding_result()` on the live worker path.

### Duplicate-delivery / idempotency evidence

- A safe replay of the same `AgentStore.store_coding_result()` call returned the existing message id `62`.
- After replay, the source thread still contained exactly one `coding_result` message for the run.
- This confirms replay did not duplicate source-thread delivery.

### Durable terminal-state evidence

- The run record converged to terminal state `failed`.
- The terminal state updated durably in the live DB row.
- The terminal event payload included:
  - `delivery_status: delivered`
  - `delivery_reason_code: null`
  - `result_message_id: 62`
  - `terminal_run_status: failed`
  - `terminal_run_status_updated: true`

### Terminal event / envelope evidence

- Live task-event stream entries for the run were:
  - `created`
  - `task.running`
  - `task.failed`
- The final terminal payload included bounded evidence fields:
  - `adapter_kind: codex`
  - `status: failed`
  - `coding_result_status: error`
  - `delivery_status: delivered`
  - `result_message_id: 62`
  - `terminal_run_status: failed`
  - `terminal_run_status_updated: true`
- The adapter summary was bounded and honest:
  - `Codex adapter execution timed out`

### Command Center boundary evidence

- No Command Center dispatch endpoint was called by the proof harness.
- No lease allocation from UI, terminal execution from UI, plugin runtime, or merge automation was exercised.
- The proof stayed on backend/store/worker seams only.

## Validation Results

- `./.venv/bin/python -m pytest -v guardian/tests/workers/test_coding_worker.py` -> `66 passed`
- `./.venv/bin/python -m pytest -v guardian/tests/routes/test_agent_orchestration_events.py` -> `17 passed`
- `./.venv/bin/python -m pytest -v guardian/tests/routes/test_coding_work_orders.py` -> `19 passed`
- `./.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py` -> `22 passed`
- `./.venv/bin/python scripts/validate_docs.py` -> passed
- `git diff --check` -> scoped check passed after excluding the unrelated LFS-managed marketing artifact

## Result

**PASS**

The supported Compose coding-worker path now executes through Guardian route -> queue -> worker -> store, returns a bounded result message into the source thread exactly once, and converges the durable run record to terminal state. The terminal status for this live smoke was `failed` because the Codex adapter timed out, but the required delivery and terminal-state evidence were produced and persisted correctly.

## Explicit Non-Claims

- This does not claim UI dispatch exists.
- This does not claim lease allocation from UI exists.
- This does not claim terminal execution from UI exists.
- This does not claim plugin runtime exists.
- This does not claim merge automation exists.
- This does not claim release readiness.
- This does not update `docs/architecture/00-current-state.md` in this implementation task.
