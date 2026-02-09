TASK-2026-02-06-007 — Cron Data Model + CRUD Routes

**Goal:** DB-backed cron job definitions + run history.

**Deliverables:**

* `guardian/cron/models.py` (Pydantic)
* `guardian/routes/cron.py`

  * POST/GET/PATCH/DELETE jobs
  * trigger endpoint
  * runs listing endpoint
* DB migration:

  * `cron_jobs`
  * `cron_runs`

**Security:**

* enforce URL allowlist for webhook payload type (no localhost/internal by default)

**Tests:**

* CRUD works + auth enforced
* invalid schedule rejected
* allowlist blocks forbidden webhook target

---

# TASK-2026-02-06-007_cron_data_model_crud_routes — Cron Data Model + CRUD Routes

## Objective
Implement a **DB-backed cron/scheduler subsystem** with minimal CRUD + run history, wired behind authenticated API routes.

This task is part of **CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE** and must follow Runner_Protocol deterministic execution.

## Background / Rationale
We want first-class scheduled jobs ("cron jobs") in Codexify/Guardian so workflows can be persisted, audited, and executed by workers.

## Scope
### In-scope
- DB tables + ORM models for:
  - `cron_jobs`
  - `cron_runs`
- REST routes for cron jobs:
  - `POST /api/cron/jobs` (create)
  - `GET /api/cron/jobs` (list)
  - `GET /api/cron/jobs/{job_id}` (get)
  - `PATCH /api/cron/jobs/{job_id}` (update)
  - `DELETE /api/cron/jobs/{job_id}` (delete)
- Execution routes:
  - `POST /api/cron/jobs/{job_id}/trigger` (manual run trigger)
  - `GET /api/cron/jobs/{job_id}/runs` (list run history)
- Auth: enforce existing API-key auth dependency for all cron endpoints.
- Webhook job type guardrails: enforce **allowlist** for outbound targets (no localhost/internal by default).
- Focused tests for CRUD + schedule validation + allowlist enforcement.

### Out-of-scope
- A full scheduler loop / worker runner (that is Task 008).
- Complex cron expressions beyond what the project already uses (keep it minimal + validated).
- UI work.

---

## Deterministic Execution Constraints

### Allowed files (STRICT)
Only modify or create files in this list. If you discover the correct location differs, STOP and update this task artifact first.

1) API routes + schemas
- `guardian/routes/cron.py`
- `guardian/cron/models.py` *(may be created if missing)*
- `guardian/cron/__init__.py` *(optional if needed for exports)*
- `guardian/guardian_api.py`

2) DB models + access layer
- `guardian/db/models.py`

3) Migrations
- `guardian/db/migrations/versions/*.py` *(new migration(s) only)*

4) Tests
- `tests/routes/test_cron_routes.py`

5) Docs updates for this task only
- `docs/tasks/TASK_2026_02_06_007_cron_data_model_crud_routes.md`
- `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md`

### Commit mode
Two-phase commits:
- **Commit A**: implementation + tests
- **Commit B**: docs finalize (this task artifact + campaign mapping)

### Dependencies / prereqs
Run these first; capture outputs in the task summary.
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# confirm branch + clean tree
pwd
git rev-parse --abbrev-ref HEAD
git status --porcelain -uall

# quick discovery: confirm no existing cron routes already wired
rg -n "\\bcron\\b|cron_jobs|cron_runs|/api/cron" guardian tests docs | head -n 200

# confirm migration tooling is present (do not run destructive commands)
ls -la guardian/db/migrations 2>/dev/null || true
```

---

## Requirements

### Data model
Cron Job (`cron_jobs`) should minimally include:
- `id` (PK)
- `name` (string)
- `is_enabled` (bool)
- `schedule` (string; validated format)
- `job_type` (enum-ish string: e.g., `webhook`, `task_registry`, `noop` — keep minimal)
- `payload` (JSON) *(optional depending on job_type)*
- `created_at`, `updated_at`

Cron Run (`cron_runs`) should minimally include:
- `id` (PK)
- `job_id` (FK -> cron_jobs.id)
- `status` (`queued|running|succeeded|failed` or similar)
- `started_at`, `finished_at`
- `error` (string nullable)
- `result` (JSON nullable)

### Security
- All cron routes require auth.
- Webhook job type must reject forbidden targets by default:
  - deny: localhost, 127.0.0.1, 0.0.0.0, ::1, link-local, RFC1918 private ranges, and obvious metadata endpoints.
  - allowlist: explicit configured domains/hosts only (implementation detail may be env-based in later tasks; for now enforce a safe default that blocks internal).

### Validation
- Schedule string must be validated. Accept one of:
  - a simple interval format already used in the repo (prefer reuse), OR
  - a conservative subset (e.g., `@hourly`, `@daily`, `*/N * * * *` if cron parser exists).
- Invalid schedule returns 422/400 with clear message.

---

## Command checklist (copy/paste runnable)

### 1) Locate existing patterns (auth dependency + router registration)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# find how other routers enforce API key
rg -n "require_api_key|X-API-Key|GUARDIAN_API_KEY" guardian/routes | head -n 200

# locate router registration pattern
rg -n "include_router\(|APIRouter\(" guardian | head -n 200
```

### 2) Implement models + migrations + routes (within allowed files)
- Add SQLAlchemy models + Alembic migration for `cron_jobs` and `cron_runs`.
- Add Pydantic request/response models.
- Add routes listed in Scope with auth enforced.
- Implement safe allowlist/denylist check for webhook targets.

### 3) Tests
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# run the smallest relevant test set
pytest -q guardian/tests/test_cron_routes.py -q || pytest -q tests/routes/test_cron_routes.py -q
```

### 4) Pre-commit sanity
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall
```

---

## Expected outputs (success signals)
- New migration exists and defines both tables with correct FK.
- `POST/GET/PATCH/DELETE` cron jobs works under tests.
- Invalid schedule is rejected.
- Webhook target allowlist/denylist blocks forbidden internal/localhost targets.
- All modified endpoints enforce auth.
- `git status --porcelain -uall` is clean after Commit A and after Commit B.

---

## Rollback / cleanup
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# discard uncommitted changes (CAUTION)
git restore --staged --worktree -- \
  guardian/guardian_api.py \
  guardian/routes/cron.py \
  guardian/cron/models.py \
  guardian/db/models.py \
  guardian/cron/__init__.py \
  guardian/db/migrations/versions \
  tests/routes/test_cron_routes.py \
  docs/tasks/TASK_2026_02_06_007_cron_data_model_crud_routes.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git clean -fd -- guardian/cron tests/routes guardian/db/migrations/versions

git status --porcelain -uall
```

---

## Commit plan

### Commit A (implementation + tests)
**Commit message (exact):**
- `TASK-2026-02-06-007_cron_data_model_crud_routes: cron models + routes + migration`

**Commands (exact):**
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  guardian/guardian_api.py \
  guardian/routes/cron.py \
  guardian/cron/models.py \
  guardian/cron/__init__.py \
  guardian/db/models.py \
  guardian/db/migrations/versions \
  tests/routes/test_cron_routes.py

git commit --no-verify -m "TASK-2026-02-06-007_cron_data_model_crud_routes: cron models + routes + migration"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)
**Commit message (exact):**
- `TASK-2026-02-06-007_cron_data_model_crud_routes: docs finalize + mapping`

**Commands (exact):**
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git add \
  docs/tasks/TASK_2026_02_06_007_cron_data_model_crud_routes.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-007_cron_data_model_crud_routes: docs finalize + mapping"

git log -1 --oneline
```

---

## Task summary (fill during execution)
- Branch: `campaign/2026-02-06/guardian-parity-control-plane`
- Commit A: `46aed0cf` (`TASK-2026-02-06-007_cron_data_model_crud_routes: cron models + routes + migration`)
- Commit B: `0b163be1`
- Files changed:
  - `guardian/routes/cron.py`
  - `guardian/cron/models.py`
  - `guardian/cron/__init__.py`
  - `guardian/db/models.py`
  - `guardian/db/migrations/versions/e5d6f4a2190c_add_cron_jobs_and_runs.py`
  - `guardian/guardian_api.py`
  - `tests/routes/test_cron_routes.py`
- Commands run + results:
  - `pytest -q tests/routes/test_cron_routes.py` -> initially failed on SQLite in-memory table visibility; fixed by `StaticPool` in tests.
  - `pytest -q tests/routes/test_cron_routes.py` -> initially failed on missing auth coverage + SQLite autoincrement for `cron_runs.id`; fixed by router-level dependency and `Integer` PK.
  - `pytest -q tests/routes/test_cron_routes.py` -> pass (`6 passed`).
- Notes / follow-ups:
  - Task implements conservative schedule validation (`@hourly`, `@daily`, `@weekly`, `@monthly`, and `*/N * * * *`).
  - Webhook targets deny localhost/private/internal addresses by default and support optional `CRON_WEBHOOK_ALLOWLIST`.
