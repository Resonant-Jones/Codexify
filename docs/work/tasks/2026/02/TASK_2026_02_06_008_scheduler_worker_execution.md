TASK-2026-02-06-008 — Scheduler + Worker Execution

**Goal:** Actual execution path: schedule → enqueue → worker → executor → events.

**Deliverables:**

* `guardian/cron/scheduler.py` (APScheduler-backed)
* `guardian/cron/executor.py` (payload types)
* `guardian/workers/cron_worker.py` (queue consumer)
* events emitted on start/success/failure → visible to WS

**Tests:**

* manual trigger creates cron_run row
* execution updates status + emits event

---

# TASK-2026-02-06-008_scheduler_worker_execution: Scheduler + Worker Execution

- **Task-ID:** TASK-2026-02-06-008_scheduler_worker_execution
- **Title:** Scheduler + Worker Execution
- **Campaign:** CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- **Branch:** campaign/2026-02-06/guardian-parity-control-plane

## Objective
Implement the **actual execution path** end-to-end:

**schedule → enqueue → worker → executor → status + events**

This task wires the first real “Cron actually runs something” loop so later tasks can plug in task-registry integration and WS visibility.

## Background / Context
Task 007 defines the cron data model + CRUD. This task adds:
- a scheduler process that turns due `cron_jobs` into `cron_runs` and enqueues them
- a worker consumer that executes the payload deterministically
- consistent events emitted on start/success/failure (for WS broadcast later)

## Scope
### In-scope deliverables
- `guardian/cron/scheduler.py` — APScheduler-backed tick/scan loop (or existing scheduler lib if already present)
- `guardian/cron/executor.py` — payload types + execution function
- `guardian/workers/cron_worker.py` — queue consumer → executor → status update
- run status transitions recorded (at minimum: queued → running → success|failed)
- event emission hooks on start/success/failure (implementation can be a lightweight internal event dispatcher if WS isn’t ready yet)

### Explicitly out of scope
- Building the full WS broadcasting pipeline (only emit/record events so Task 012 can publish)
- Rich UI work
- Implementing the “cron ↔ task registry” mapping (Task 009)

## Allowed files (STRICT)
Only edit the files below. If you discover more are required, STOP and update this task artifact first.

- `guardian/cron/scheduler.py`
- `guardian/cron/executor.py`
- `guardian/workers/cron_worker.py`
- `guardian/db/models/cron.py`
- `guardian/db/migrations/versions/*_cron_run_execution_*.py` (only if a migration is strictly required)
- `guardian/tests/**/test_cron_*execution*.py`
- `docs/work/tasks/2026/02/TASK_2026_02_06_008_scheduler_worker_execution.md` (this artifact; Commit B only)
- `docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md` (mapping line; Commit B only)

## Dependencies / prereqs (commands)
Run these exactly and capture any relevant output in this artifact.

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# confirm scheduler/workers paths exist (or discover existing equivalents)
ls -la guardian/cron guardian/workers || true

# locate any existing cron queue / worker conventions
rg -n "cron_job|cron_run|scheduler|APScheduler|cron_worker" guardian | head -n 200

# verify test runner is available
python -V
pytest --version
```

## Command checklist (exact)
### 0) Preflight / cleanliness
```bash
git status --porcelain -uall
```
- Must be clean before starting.

### 1) Locate existing patterns to follow (queue + DB session + logging)
```bash
rg -n "enqueue|queue|worker" guardian/workers guardian | head -n 200
rg -n "get_db|SessionLocal|async_session|GuardianDB" guardian | head -n 200
rg -n "logger =|logging\.getLogger" guardian/cron guardian/workers | head -n 200
```

### 2) Implement scheduler tick → enqueue
Implementation requirements:
- Determine “due” jobs (whatever the data model defines: `next_run_at`, `enabled`, etc.)
- Create a `cron_run` row and mark it `queued`
- Enqueue a payload that includes at minimum: `cron_run_id`, `cron_job_id`, and a resolved execution target

After edits:
```bash
git status --porcelain -uall
```

### 3) Implement worker consumer → executor
Implementation requirements:
- Worker pulls message
- Marks run `running`
- Executes deterministically via `executor.py`
- Writes `success` or `failed` + error message (bounded length)
- Emits start/success/failure event hook

After edits:
```bash
git status --porcelain -uall
```

### 4) Add tests (minimum viable)
Add a focused test that proves:
- given a due job, scheduler creates a `cron_run` and enqueues a message (queue can be a stub/in-memory mock)
- given a queued message, worker executes and updates run status to success

Run:
```bash
pytest -q
```

If full suite is too slow, at minimum:
```bash
pytest -q guardian/tests -k "cron and (scheduler or worker or execution)"
```

### 5) Optional manual verification (only if DB + worker runtime is available)
If your local env has DB + worker running, do a quick smoke:
```bash
# start services if you have compose; adjust service names to match repo
# docker compose up -d postgres redis

# run a scheduler tick once (or run module entrypoint)
python -c "from guardian.cron.scheduler import tick_once; tick_once()"
```
Expected: a new `cron_run` row is created and queued.

## Expected outputs / success signals
- Tests added and passing (`pytest -q` or the targeted subset above)
- Scheduler path creates `cron_run` and enqueues payload without raising
- Worker path marks `running` then `success|failed` and persists an error message on failure
- No unbounded logs of payload contents (avoid leaking secrets)

## Rollback / cleanup
If anything goes sideways:
```bash
git restore -- \
  guardian/cron/scheduler.py \
  guardian/cron/executor.py \
  guardian/workers/cron_worker.py \
  guardian/db/models/cron.py

git clean -fd

git status --porcelain -uall
```

## Commit mode
Two-phase:
- **Commit A:** implementation + tests
- **Commit B:** docs finalize (this artifact + campaign mapping)

## Commit commands
### Commit A (implementation)
```bash
git status --porcelain -uall

git add \
  guardian/cron/scheduler.py \
  guardian/cron/executor.py \
  guardian/workers/cron_worker.py \
  guardian/db/models/cron.py \
  guardian/db/migrations/versions \
  guardian/tests

git commit --no-verify -m "TASK-2026-02-06-008_scheduler_worker_execution: scheduler tick → enqueue + worker execute"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)
```bash
git add \
  docs/work/tasks/2026/02/TASK_2026_02_06_008_scheduler_worker_execution.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-008_scheduler_worker_execution: docs finalize + mapping"

git log -1 --oneline
```

## Campaign mapping line (to update in campaign doc)
- TASK-2026-02-06-008_scheduler_worker_execution -> [dacffa97, 663ba791]

## Notes / results
(As you execute: paste the commands run + key outputs + what changed + hashes here.)

- Commands run:
  - `git status --porcelain -uall`
  - `ls -la guardian/cron guardian/workers || true`
  - `rg -n "cron_job|cron_run|scheduler|APScheduler|cron_worker" guardian | head -n 200`
  - `python -V`
  - `pytest --version`
  - `pytest -q guardian/tests/test_cron_scheduler_worker_execution.py`
  - `pytest -q guardian/tests -k "cron and (scheduler or worker or execution)"`
- Key outputs:
  - `pytest -q guardian/tests/test_cron_scheduler_worker_execution.py` -> `2 passed`
  - broader `-k` run hit unrelated collection error in `guardian/tests/db/test_seed.py`:
    `neomodel.exceptions.NodeClassAlreadyDefined`
- Summary of changes:
  - Added `guardian/cron/scheduler.py` with due-job scan + run creation + queue enqueue + `cron.run.queued` event.
  - Added `guardian/cron/executor.py` with deterministic `noop` and `webhook` execution behavior.
  - Added `guardian/workers/cron_worker.py` with queued -> running -> succeeded/failed status transitions and start/success/failure events.
  - Added `guardian/tests/test_cron_scheduler_worker_execution.py` covering scheduler enqueue path and worker execution status updates.
- Commit A: `dacffa97`
- Commit B: `663ba791`
