TASK-2026-02-06-009 — Cron ↔ Task Registry Integration

**Goal:** Cron execution becomes a first-class task type.

**Deliverables:**

* register `CronExecutionTask` in `guardian/tasks/types.py` (or your actual registry file)
* ensure existing queue conventions are used (no parallel queue abstraction)

**Tests:**

* task registry resolves cron task correctly

---

# TASK-2026-02-06-009_cron_to_task_registry_integration — Cron ↔ Task Registry Integration

- **Task-ID:** TASK-2026-02-06-009_cron_to_task_registry_integration
- **Title:** Cron ↔ Task Registry Integration
- **Branch:** campaign/2026-02-06/guardian-parity-control-plane
- **Commit mode:** two-phase (Commit A = implementation, Commit B = docs finalize + mapping)

## Objective
Make cron execution a first-class **task type** in the backend task registry so scheduler/worker execution can reuse the same task resolution + dispatch path as other tasks.

This is a *wiring* task: **do not invent a parallel queue abstraction**.

## Background
The control plane campaign introduces cron jobs + scheduler + worker execution. If cron jobs are a bespoke pathway, you’ll get drift (permissions, audit logging, retries, metrics). The registry should be the single source of truth for “what tasks exist” and “how to run them”.

## Deterministic execution constraints
### Allowed files (STRICT)
Only modify the files in this list:

- `guardian/tasks/types.py` *(or the repo’s actual task registry file if different — only one file should own the registry)*
- `guardian/tasks/__init__.py` *(only if needed to export/compose registry)*
- `guardian/tasks/cron.py` *(only if it already exists and is the canonical cron task implementation location)*
- `guardian/tests/**/test_*task*registry*.py` *(or the existing nearest test file that asserts registry behavior)*
- `docs/tasks/TASK_2026_02_06_009_cron_to_task_registry_integration.md`
- `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md`

If you discover the true registry file path is different, STOP and update this task’s Allowed Files first (do not proceed with out-of-scope edits).

### Out of scope
- Creating a new queue/worker abstraction.
- Implementing the full scheduler/worker runtime (that is Task 008).
- Adding new cron CRUD routes (that is Task 007).
- Broad refactors of existing task system.

## Dependencies / prereqs
Run these commands first and record outputs or key findings in the Summary section.

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# locate the task registry / task types module
rg -n "class .*Task|TaskRegistry|TASK_TYPES|register_task|task_registry" guardian/tasks || true

# locate any existing cron task implementation hooks
rg -n "Cron|cron" guardian/tasks guardian/workers guardian/scheduler guardian/core || true
```

## Command checklist (copy/paste runnable)
### 1) Locate current task registry contract
```bash
# confirm registry API surface
rg -n "TASK_TYPES|TaskRegistry|register_task|resolve_task" guardian/tasks || true

# open the most likely registry file
ls -la guardian/tasks || true
```

### 2) Implement CronExecutionTask registration
Implementation rules:
- Create (or reuse) a task type named `CronExecutionTask` (or match existing naming conventions).
- The registry key should be a stable string (e.g. `"cron.execute"`), not a Python class name.
- The resolved task callable/class must accept whatever payload is already produced by the scheduler/worker design (Task 008). Keep it minimal.

```bash
# after edits, show scoped diff
git diff --stat
```

### 3) Add/adjust tests
Add a focused test that:
- Imports/loads the registry
- Resolves the cron task key
- Asserts the resolved handler/type is the expected cron task entrypoint

```bash
# run the narrowest possible test(s)
pytest -q -k "task_registry or cron_to_task_registry or CronExecutionTask" || true
```

### 4) Pre-commit validation
```bash
git status --porcelain -uall

# optional: fast type/lint if present
# (only run if these exist / are already in the repo; otherwise skip and note in Summary)
# make test
```

## Expected outputs (success signals)
- Task registry can resolve the cron execution task by key.
- At least one automated test asserts the registry resolution behavior.
- No new queue abstraction is introduced.
- `git status --porcelain -uall` is clean after Commit B.

## Rollback / cleanup
If anything goes sideways:

```bash
# discard working changes

git restore --source=HEAD --staged --worktree -- guardian/tasks guardian/tests || true

git status --porcelain -uall
```

## Commit plan
### Commit A (implementation)
**Message (exact):**
- `TASK-2026-02-06-009_cron_to_task_registry_integration: register cron execution task type`

**Commands:**
```bash
# stage ONLY implementation + tests

git add \
  guardian/tasks \
  guardian/tests

git commit --no-verify -m "TASK-2026-02-06-009_cron_to_task_registry_integration: register cron execution task type"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)
**Message (exact):**
- `TASK-2026-02-06-009_cron_to_task_registry_integration: docs finalize + mapping`

**Commands:**
```bash
# stage ONLY docs artifacts

git add \
  docs/tasks/TASK_2026_02_06_009_cron_to_task_registry_integration.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-009_cron_to_task_registry_integration: docs finalize + mapping"

git log -1 --oneline

git status --porcelain -uall
```

## Notes for the task artifact Summary
Fill these in after execution:

- **Commands run + outcomes:**
  - `git status --porcelain -uall` (clean)
  - `rg -n "class .*Task|TaskRegistry|TASK_TYPES|register_task|task_registry" guardian/tasks || true`
  - `rg -n "Cron|cron" guardian/tasks guardian/workers guardian/scheduler guardian/core || true`
  - `rg -n "TASK_TYPES|TaskRegistry|register_task|resolve_task" guardian/tasks || true`
  - `ls -la guardian/tasks || true`
  - `git diff --stat`
  - `pytest -q -k "task_registry or cron_to_task_registry or CronExecutionTask" || true`
  - `pytest -q guardian/tests/test_task_registry_cron_execution.py`
- **Files changed (Commit A):**
  - `guardian/tasks/types.py`
  - `guardian/tests/test_task_registry_cron_execution.py`
- **Tests run:**
  - `pytest -q guardian/tests/test_task_registry_cron_execution.py` -> `2 passed`
  - broad `-k` run produced no selected tests in this layout
- **Result:**
  - `CronExecutionTask` registered under key `cron.execute`
  - `task_from_dict` resolves `cron.execute` payloads to `CronExecutionTask`

## Campaign mapping line
Update the campaign file mapping when you have hashes:

- `TASK-2026-02-06-009_cron_to_task_registry_integration -> [dea42fdc, d3418591]`
