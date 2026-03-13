# Guardian Agent Runtime & Delegation Loop: Onboarding

## Who This Is For

This guide serves two audiences:

- Product and operations users running delegated work from Guardian chat.
- Developers extending adapters, retry policy, confidence policy, persistence, and orchestration routes.

Use this document to onboard new people quickly without reading the full design plan first.

## User Perspective (Start Here)

Guardian is the main interface. A user asks for work in chat, and Guardian can run delegated loops through configured agents under supervision.

In practical terms, a delegated run is:

- A supervised execution loop with retries, confidence scoring, and escalation.
- Deterministic on commit boundaries for mutating work.
- Test-gated for mutation steps.

Core behavior to understand:

- Mutating work must pass tests before commit actions are allowed.
- Successful mutating step semantics are strict:
  - Commit A: mutation commit (code changes).
  - Commit B: validation boundary commit (allow-empty by default).
- Escalation preserves the worktree for human review instead of auto-cleaning it.

If something looks stuck or risky, Guardian escalates and keeps durable records (attempts, events, and escalation context).

## First Session Quickstart (Docker-First)

### Prerequisites

- Docker Desktop or equivalent Docker engine
- Valid API key (`GUARDIAN_API_KEY`) configured server-side
- Backend reachable from your shell (default: `http://localhost:8888`)

Set local shell variables (example placeholders only):

```bash
export BASE_URL="http://localhost:8888"
export API_KEY="<your-guardian-api-key>"
```

### 1) Bring up required services

```bash
docker compose up -d db redis backend worker-chat
```

Expected result:

- Containers are running for DB, Redis, backend, and worker-chat.

### 2) Apply migrations

```bash
docker compose exec backend alembic -c /app/backend/alembic.ini upgrade head
```

Expected result:

- Alembic reports database at latest revision (including orchestration tables).

### 3) Create a plan

```bash
curl -sS -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a small delegated onboarding run",
    "thread_id": 77,
    "proposed_steps": []
  }' \
  "${BASE_URL}/api/agents/plans"
```

Expected result:

- JSON payload with `ok: true`, a `plan_id`, and a `spec_hash`.

### 4) Create a deployment

```bash
curl -sS -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_id": "flow-onboarding",
    "thread_id": 77,
    "spec": {"steps": []},
    "trust_state": "supervised"
  }' \
  "${BASE_URL}/api/agents/deployments"
```

Expected result:

- JSON payload with `deployment.deployment_id`.

### 5) Start a run

```bash
DEPLOYMENT_ID="<paste-deployment-id>"

curl -sS -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "runtime_target": "container",
    "supervised": true
  }' \
  "${BASE_URL}/api/agents/deployments/${DEPLOYMENT_ID}/runs"
```

Expected result:

- JSON payload with `run.run_id` and initial run status.
- Lifecycle events begin with `created` and `started`.

### 6) Stream run events (SSE)

```bash
RUN_ID="<paste-run-id>"

curl -N \
  -H "X-API-Key: ${API_KEY}" \
  "${BASE_URL}/api/agents/runs/${RUN_ID}/events"
```

Expected result:

- SSE frames with `event:` and `data:` lines.
- You should see lifecycle event names over time.

### 7) Cancel a run

```bash
curl -sS -X POST \
  -H "X-API-Key: ${API_KEY}" \
  "${BASE_URL}/api/agents/runs/${RUN_ID}/cancel"
```

Expected result:

- JSON payload confirming canceled state.
- `canceled` event appears in event stream.

### 8) List runs for a chat thread

```bash
curl -sS \
  -H "X-API-Key: ${API_KEY}" \
  "${BASE_URL}/api/chat/77/agent-runs"
```

Expected result:

- JSON payload listing runs associated with `thread_id=77`.

### Canonical API Interfaces (Current Runtime)

Treat the following interfaces as canonical for runtime operations:

- `POST /api/agents/plans`
- `POST /api/agents/deployments`
- `POST /api/agents/deployments/{deployment_id}/runs`
- `POST /api/agents/runs/{run_id}/cancel`
- `GET /api/agents/runs/{run_id}`
- `GET /api/agents/runs/{run_id}/events`
- `GET /api/chat/{thread_id}/agent-runs`

Compatibility stream note:

- Existing consumers of `/api/tasks/{task_id}/events` remain valid where `task_id == run_id`.

Adapter contract reference:

- Delegated adapters must return strict `AgentRunEnvelope` payloads.

## Daily Operator Workflow

Use this loop for normal operations:

1. Define intent in chat.
2. Launch run from deployment.
3. Observe SSE lifecycle during execution.
4. Inspect run status and artifacts.
5. Continue on success, or triage escalation/failure.

Event names you should expect:

- `created`
- `started`
- `attempt_failed`
- `attempt_progress`
- `step_succeeded`
- `escalated`
- `canceled`
- `failed`
- `succeeded`

Primary inspection points:

- `GET /api/agents/runs/{run_id}` for run status.
- `GET /api/agents/runs/{run_id}/events` for live stream.
- Compatibility consumers may continue reading `/api/tasks/{task_id}/events` where `task_id == run_id`.

## Safety and Trust Gates (Practical)

Operational safety model:

- Supervised is default.
- Unsupervised start requires explicit unlock at deployment trust state.
- No commit actions before tests pass for mutating steps.
- Retry behavior is adaptive and escalates early when a run is stuck.

Confidence outcomes are practical control signals.

Step confidence bands:

- `>= 0.85`: continue
- `0.70 - 0.85`: warn
- `0.55 - 0.70`: soft escalate
- `< 0.55`: hard escalate

Task confidence bands:

- `>= 0.85`: autonomous approve
- `0.70 - 0.85`: optional audit
- `0.55 - 0.70`: audit required
- `< 0.55`: block merge, human required

Security reminders:

- Keep provider and Guardian secrets server-side only.
- Do not expose backend API keys to frontend in production.
- Do not commit secret values to `.env` files tracked in git.

## Failure Modes and What To Do

### 1) Tests never pass

- Symptom: repeated `attempt_failed`, terminal `failed`.
- Likely cause: mutation did not satisfy test suite or introduced regressions.
- Immediate recovery action: inspect the last failing attempt details and rerun with narrowed scope.
- Where to inspect:
  - `GET /api/agents/runs/{run_id}`
  - SSE stream for attempt lifecycle
  - run artifacts and attempt telemetry in orchestration records

### 2) Repeated same failure signature

- Symptom: attempts repeat with effectively same failure signature, then escalation.
- Likely cause: loop is not making progress and is cycling the same fix.
- Immediate recovery action: human intervention to change strategy, constraints, or input spec.
- Where to inspect:
  - `/api/agents/runs/{run_id}`
  - event stream for escalation reason
  - attempt telemetry (`fail_signature`, `error_category`)

### 3) Regression in fail count

- Symptom: failing test count increases versus best-so-far attempt.
- Likely cause: an attempted fix widened breakage.
- Immediate recovery action: stop autonomous continuation, review diff risk and step intent.
- Where to inspect:
  - run status endpoint
  - attempt metrics and event timeline
  - step-level confidence reports

### 4) Spec alignment violation

- Symptom: immediate escalation without normal retry continuation.
- Likely cause: output violated step contract or intent requirements.
- Immediate recovery action: revise task specification and rerun under supervision.
- Where to inspect:
  - run endpoint (escalated status)
  - event stream for `reason_code`
  - stored escalation payload

### 5) SSE shows escalation but run appears idle

- Symptom: escalated event is emitted, no further progress events.
- Likely cause: expected behavior after escalation pause.
- Immediate recovery action: inspect preserved worktree and decide manual continue/cancel.
- Where to inspect:
  - `GET /api/agents/runs/{run_id}`
  - `GET /api/agents/runs/{run_id}/events`
  - durable artifacts and escalation records

## Dev Notes (Contributor Appendix)

### Architecture map

Key implementation areas:

- Adapters:
  - `guardian/agents/adapters/base.py`
  - `guardian/agents/adapters/codex.py`
  - `guardian/agents/adapters/claudecode.py`
- Worker:
  - `guardian/workers/agent_worker.py`
- Store/persistence service:
  - `guardian/agents/store.py`
- Events publisher:
  - `guardian/agents/events.py`
- Routes:
  - `guardian/routes/agent_orchestration.py`
  - mounted in `guardian/guardian_api.py`
- Configuration flags:
  - `guardian/core/config.py`
- DB models and migration:
  - `guardian/db/models.py`
  - `guardian/db/migrations/versions/9f3d2b1a7c4e_add_agent_orchestration_tables.py`

### Durable orchestration tables

- `agent_deployments`
- `agent_runs`
- `agent_run_steps`
- `agent_run_attempts`
- `agent_run_artifacts`
- `agent_confidence_reports`
- `agent_escalations`
- `agent_events`
- `agent_reflections`

### Deterministic invariants

- No intermediate retry attempt can create commits.
- Successful mutating step creates exactly two commits:
  - mutation commit
  - validation boundary commit
- Failed run produces zero commits for the failed step path.
- Escalations persist durably and are emitted on stream.
- Failed runs can auto-clean worktrees; escalated runs preserve worktree for review.

### Confidence formulas and policy constants

Step confidence:

```text
C_step =
  0.35*C_tests +
  0.20*C_schema +
  0.20*C_spec_alignment +
  0.15*C_diff_risk +
  0.10*C_model_stability
```

Task confidence:

```text
C_task =
  0.40*mean(C_step) +
  0.25*min(C_step) +
  0.15*C_convergence +
  0.10*C_risk +
  0.10*(1-escalation_penalty)
```

Retry policy defaults (configurable):

- `AGENT_MAX_ATTEMPTS=5`
- `AGENT_MIN_ATTEMPTS_BEFORE_ABORT=2`
- `AGENT_NO_PROGRESS_WINDOW=2`
- `AGENT_MAX_SAME_SIGNATURE_REPEATS=2`
- `AGENT_REGRESSION_LIMIT=2`
- `AGENT_AUTO_ROLLBACK_ON_FAIL=true`
- `AGENT_VALIDATOR_MODEL_ENABLED=false`
- `AGENT_REQUIRE_TWO_COMMITS=true`
- `AGENT_VALIDATION_COMMIT_ALLOW_EMPTY=true`

### Extension guidance

Add a new delegated adapter:

1. Implement adapter contract in terms of strict `AgentRunEnvelope` output.
2. Register adapter in `guardian/agents/adapters/__init__.py`.
3. Add tests for envelope shape and failure mapping.

Tune policy behavior:

- Add or adjust policy flags in `guardian/core/config.py`.
- Keep deterministic behavior and update tests accordingly.

Add event types:

1. Add event emission site in worker or route layer.
2. Persist via `AgentEventPublisher.emit`.
3. Ensure stream compatibility for `/api/agents/runs/{run_id}/events` and `/api/tasks/{task_id}/events`.
4. Add route and worker tests.

### Test strategy references

- Confidence engine tests:
  - `guardian/tests/agents/test_confidence_engine.py`
- Adaptive retry tests:
  - `guardian/tests/agents/test_adaptive_retry.py`
- Commit boundary tests:
  - `guardian/tests/workers/test_agent_worker_commit_boundaries.py`
- Event persistence and SSE tests:
  - `guardian/tests/routes/test_agent_orchestration_events.py`

For deeper rationale and phased design context, see:

- `docs/work/plans/Guardian-delegationPLAN.md`

## Glossary

- **deployment**: Durable record of a delegated specification and trust state.
- **run**: One execution instance created from a deployment.
- **step**: A unit of work within a run.
- **attempt**: A single retry iteration for a step.
- **escalation**: Durable pause/alert state when policy blocks continuation.
- **confidence report**: Guardian-derived step or task confidence record used for decisions.
- **validation boundary commit**: Commit B after mutation success, used as deterministic validation boundary.
- **worktree preservation**: Retaining escalated run workspace for human review instead of deleting it.
