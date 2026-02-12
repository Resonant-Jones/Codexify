# TASK-2026-02-12-005_flow_runner_execute_trace: Flow Runner (deterministic execution + tracing)

## Metadata
- Task-ID: TASK-2026-02-12-005_flow_runner_execute_trace
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/tasks/TASK_2026_02_12_005_flow_runner_execute_trace.md
- Owner: resonant_jones
- Risk: HIGH
- Commit mode: two-phase

## Objective
Implement run_flow() to execute compiled flows deterministically with budgets, tracing, and idempotency checks.

## Scope
### In-scope
- run_flow(compiled_flow, context) -> FlowRun
- Budget enforcement: max_steps, max_tokens (where measurable), timeout_seconds
- Step trace: start/end, params (redacted), outputs, errors
- Idempotency: lookup by idempotency key and return cached run if configured

### Out-of-scope
- Production connector side effects beyond declared primitives
- NL parsing

## Allowed files (STRICT)
- guardian/flows/runner.py
- guardian/flows/spec.py (only if run models required)
- guardian/flows/primitives.py (only if handler invocation requires tweaks)
- guardian/flows/compiler.py (only if runner requires compiled shape adjustment)
- guardian/flows/__init__.py
- docs/tasks/TASK_2026_02_12_005_flow_runner_execute_trace.md
- docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md

## Preconditions (NO GUESSING)
```bash
cd <REPO_ROOT>
git status --porcelain -uall
# EXPECTED: (no output)
```

## Execution plan (copy/paste)
```bash
cd <REPO_ROOT>
git status --porcelain -uall

# implement runner in guardian/flows/runner.py

python -c "from guardian.flows.runner import run_flow; print('ok')"

git status --porcelain -uall
```

## Expected results (explicit)
- Import check prints `ok`.
- Runner returns a `FlowRun` object containing `step_results` and `status`.
- Budget violations result in deterministic failure status (no partial side-effects beyond already executed steps).

## Rollback / cleanup
```bash
cd <REPO_ROOT>
git checkout -- guardian/flows/runner.py guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/compiler.py guardian/flows/__init__.py
```

## Commit plan (MANUAL; index.lock workaround)

### Commit A (implementation) — two-phase only

**Commit message (EXACT):** `TASK-2026-02-12-005_flow_runner_execute_trace: flow runner deterministic execution + trace`

**Manual commands (explicit paths only):**
```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add guardian/flows/runner.py guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/compiler.py guardian/flows/__init__.py
git commit --no-verify -m "TASK-2026-02-12-005_flow_runner_execute_trace: flow runner deterministic execution + trace"
git log -1 --oneline
git status --porcelain -uall
```

Commit A hash: e55f6d7d

### Commit B (docs finalize + mapping) — two-phase only

**Commit message (EXACT):** `TASK-2026-02-12-005_flow_runner_execute_trace: docs finalize + mapping`

**Manual commands:**
```bash
cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_005_flow_runner_execute_trace.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-005_flow_runner_execute_trace: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

## Campaign mapping (SOURCE OF TRUTH)
- TASK-2026-02-12-005_flow_runner_execute_trace -> [e55f6d7d, <commitB>]

## Completion Summary (fill after completion)
- Status: DONE
- What changed:
  - Implemented `run_flow()` in `guardian/flows/runner.py` with deterministic execution over compiled steps.
  - Added budget enforcement (`max_steps`, `max_tokens`, `timeout_seconds`), per-step trace records, and redaction-aware parameter tracing.
  - Added in-memory idempotency cache support keyed by rendered idempotency template/context and exported runner APIs from `guardian/flows/__init__.py`.
- Commands run:
  ```bash
  git status --porcelain -uall
  .venv/bin/python -c "from guardian.flows.runner import run_flow; print('ok')"
  git add guardian/flows/runner.py guardian/flows/spec.py guardian/flows/primitives.py guardian/flows/compiler.py guardian/flows/__init__.py
  git commit --no-verify -m "TASK-2026-02-12-005_flow_runner_execute_trace: flow runner deterministic execution + trace"
  ```
- Tests:
  - `.venv/bin/python -c "from guardian.flows.runner import run_flow; print('ok')"` (pass)
- Scope check:
  - git status clean before starting: yes
  - Only allowed files modified: yes
- Commit info:
  - Commit mode: two-phase
  - Commit A hash (impl): e55f6d7d
  - Commit B hash (docs finalize): recorded in campaign mapping as `<commitB>`
- Campaign mapping updated: yes
- Notes / gotchas:
  - Original repository artifact filename used `2026_02-12` while campaign referenced `2026_02_12`; the canonical file path was created for commit-path consistency.
  - Runtime command checks used `.venv/bin/python` because system `python` in this shell is missing required dependencies.
