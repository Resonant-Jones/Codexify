# TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db

## TASK METADATA

- Campaign-ID: CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- Task-ID: TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db
- Risk: MED
- Task artifact: docs/tasks/TASK_2026_02_06_010_realtime_permissions_tests_use_sqlite_or_skip_without_db.md
- Owner: resonant_jones

## Objective

Make realtime collaboration permission tests deterministic in dev/CI:

- Either run using SQLite (or an in-memory DB) **without requiring Postgres**
- OR explicitly skip with a clear reason when DB is not configured.

## Scope

### In-scope

- Make `tests/realtime/test_collaboration_permissions.py` not error with psycopg OperationalError when DB host is missing.
- Prefer **skip-if-no-db** or **SQLite fallback**.
- Update any test fixtures/config only as needed to achieve deterministic behavior.

### Out-of-scope

- No production database migrations.
- No changes to runtime collaboration permissions logic beyond what’s required for tests.

## Allowed files (STRICT)

- tests/realtime/test_collaboration_permissions.py
- tests/conftest.py
- conftest.py
- guardian/**/test_*.py
- docs/tasks/TASK_2026_02_06_010_realtime_permissions_tests_use_sqlite_or_skip_without_db.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

> If a required file is outside this list, STOP and emit a Blocker Prompt requesting expansion.

## Dependencies / prereqs (NO GUESSING)

Run these first and record outputs in the task Summary:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
python --version
python -c "import sqlalchemy; print('sqlalchemy ok')"
python -c "import psycopg; print('psycopg ok')" || true
```
Command checklist (copy/paste)

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: clean tree
git status --porcelain -uall

# 1) identify failing tests
pytest -q tests/realtime/test_collaboration_permissions.py -q

# 2) implement within allowed files only
# Goal: no psycopg OperationalError when DB is not configured

# 3) re-run realtime tests
pytest -q tests/realtime/test_collaboration_permissions.py -q

# 4) confirm only allowed files changed
git status --porcelain -uall

Expected outputs (success signals)
 • pytest -q tests/realtime/test_collaboration_permissions.py completes without:
 • sqlalchemy.exc.OperationalError
 • psycopg.OperationalError
 • Acceptable outcomes:
 • Tests PASS, or
 • Tests SKIP with explicit message like “Postgres not configured” (must be intentional, not error).

Rollback / cleanup

git restore --staged --worktree -- \
  tests/realtime/test_collaboration_permissions.py \
  tests/conftest.py \
  conftest.py \
  docs/tasks/TASK_2026_02_06_010_realtime_permissions_tests_use_sqlite_or_skip_without_db.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git status --porcelain -uall

Commit mode
 • two-phase (MANUAL)

Commit plan (MANUAL)

Commit A (implementation)
 • Commit message (EXACT):
 • TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db: make realtime tests deterministic

Commands:

git status --porcelain -uall
git add tests/realtime/test_collaboration_permissions.py tests/conftest.py conftest.py
git commit --no-verify -m "TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db: make realtime tests deterministic"
git log -1 --oneline
git status --porcelain -uall

Commit B (docs finalize)
 • Commit message (EXACT):
 • TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db: docs finalize + mapping

Commands:

git status --porcelain -uall
git add docs/tasks/TASK_2026_02_06_010_realtime_permissions_tests_use_sqlite_or_skip_without_db.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md
git commit --no-verify -m "TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall

Mapping
 • TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db -> [, ]

Summary (fill after completion)
 • What changed
 • Added a module-level `pytest.skipif` guard in `tests/realtime/test_collaboration_permissions.py` to skip realtime permission tests when `TEST_DATABASE_URL` is not set, avoiding Postgres host `OperationalError`.
 • Commands run + results
 • `python --version` => Python 3.13.9
 • `python -c "import sqlalchemy; print('sqlalchemy ok')"` => ModuleNotFoundError (system python)
 • `python -c "import psycopg; print('psycopg ok')"` => ModuleNotFoundError (system python)
 • `venv/bin/python -m pytest -q tests/realtime/test_collaboration_permissions.py -q` => skipped (no OperationalError)
 • `pytest -q tests/realtime/test_collaboration_permissions.py -q` => skipped
 • `git status --porcelain -uall` => only `tests/realtime/test_collaboration_permissions.py` before Commit A
 • Commit A
 • 3f7b9d79
 • Commit B
 • 27d53128
 • Final mapping with real hashes
 • TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db -> [3f7b9d79, 27d53128]

---

## 2) Update the campaign mapping line for Task 010
In:

`docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md`

Make sure Task 010 line is in the required format:

```text
TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db -> [<commitA>, <commitB>]

(Leave placeholders until hashes exist.)

⸻

3) Commit the docs-only fix (Task artifact + campaign mapping placeholders)

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  docs/tasks/TASK_2026_02_06_010_realtime_permissions_tests_use_sqlite_or_skip_without_db.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db: docs finalize + constraints"

git log -1 --oneline
git status --porcelain -uall


⸻
