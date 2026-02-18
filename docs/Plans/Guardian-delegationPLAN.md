# Patch Plan Update: Deterministic CI-Gated Multi-Agent Loop v1

## Summary
This extends Guardian orchestration with deterministic retries, confidence scoring, durable escalation telemetry, strict commit boundaries, and SSE event streaming.
Locked semantic: `Task = each mutating step` and each successful task produces exactly two commits:
- Commit A: mutation commit (after tests pass)
- Commit B: validation boundary commit (allow-empty preferred)

## Phase 0: Preconditions and Repo Safety
1. Treat this as a dedicated patch sequence because unrelated workspace changes may exist.
2. Enforce worker invariant: no commits unless tests pass for the current mutating step.
3. Persist every attempt and outcome, including failures and escalations.

## Phase 1: Durable Postgres Domain (Expanded)
1. Durable entities:
- `agent_deployments`
- `agent_runs`
- `agent_run_steps`
- `agent_run_attempts`
- `agent_run_artifacts`
- `agent_confidence_reports`
- `agent_escalations`
- `agent_events`
- `agent_reflections`
2. Migration chains from Alembic head `a7c9d1e2f3b4`.

## Phase 2: Config and Runtime Flags
1. Add deterministic retry and commit policy flags:
- `AGENT_MAX_ATTEMPTS=5`
- `AGENT_MIN_ATTEMPTS_BEFORE_ABORT=2`
- `AGENT_NO_PROGRESS_WINDOW=2`
- `AGENT_MAX_SAME_SIGNATURE_REPEATS=2`
- `AGENT_REGRESSION_LIMIT=2`
- `AGENT_AUTO_ROLLBACK_ON_FAIL=true`
- `AGENT_VALIDATOR_MODEL_ENABLED=false`
- `AGENT_REQUIRE_TWO_COMMITS=true`
- `AGENT_VALIDATION_COMMIT_ALLOW_EMPTY=true`

## Phase 3: Confidence Engine (Step + Task)
1. Guardian confidence is canonical. Model self-confidence is telemetry only.
2. Step confidence formula:
`C_step = 0.35*C_tests + 0.20*C_schema + 0.20*C_spec_alignment + 0.15*C_diff_risk + 0.10*C_model_stability`
3. Task confidence formula:
`C_task = 0.40*mean(C_step) + 0.25*min(C_step) + 0.15*C_convergence + 0.10*C_risk + 0.10*(1-escalation_penalty)`
4. Thresholds:
- Step: `>=0.85 continue`, `0.70-0.85 warn`, `0.55-0.70 soft escalate`, `<0.55 hard escalate`
- Task: `>=0.85 autonomous approve`, `0.70-0.85 optional audit`, `0.55-0.70 audit required`, `<0.55 block merge/human required`

## Phase 4: Adaptive Retry Engine
1. Attempt metrics:
- `fail_count`
- `fail_signature`
- `diff_added`, `diff_deleted`
- `error_category`
2. Progress definition: `fail_count` reduced OR error category improved.
3. Early escalation triggers after min attempts:
- no-progress window reached
- repeated signature exceeds threshold
- regression exceeds best-so-far + regression limit
- spec alignment violation (immediate)

## Phase 5: Worker Determinism + Commit Doctrine
1. No intermediate retry attempts create commits.
2. Failed runs produce zero commits.
3. Successful mutating step produces exactly two commits; both hashes are persisted in artifacts.
4. Commit B defaults to allow-empty boundary commit.

## Phase 6: Worktree Naming, Rollback, Preservation
1. Deterministic worktree id derived from `deployment_id:run_id:step_index`.
2. Auto rollback default ON for failed runs.
3. Escalated runs preserve worktree/branch for review.
4. Worktree creation applies only to mutating steps.

## Phase 7: Agent Events + SSE Integration
1. Emit durable typed events:
- `created`, `started`, `attempt_failed`, `attempt_progress`, `step_succeeded`
- `escalated`, `canceled`, `failed`, `succeeded`
2. Publish to Redis task stream with `task_id = run_id`.
3. Keep `/api/tasks/{task_id}/events` compatibility unchanged.

## Phase 8: Adapter Contract + Validator Scaffold
1. Strict JSON `AgentRunEnvelope` is required for delegated adapters.
2. v1 adapters:
- Codex
- ClaudeCode
3. Optional validator pre-step (feature-flagged) can generate/improve tests before done, but passing tests remains required.

## Acceptance Mapping
1. Failing test run never produces commits.
2. Successful mutating task produces exactly two commits and both hashes are stored.
3. Attempts are persisted and queryable.
4. Escalations persist and stream.
5. Confidence is computed per-step and per-task and drives escalation behavior.
