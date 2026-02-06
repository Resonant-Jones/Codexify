# TASK_2026_02_06_010_realtime_permissions_tests_use_sqlite_or_skip_without_db

## Objective

Prevent database-host-dependent test failures in local/dev environments.

## Background

Realtime permission tests error when PostgreSQL is unreachable, producing noisy failures unrelated to logic correctness.

## Requirements (choose and codify one)

Option A:

- Use SQLite or in-memory DB for permission tests

Option B:

- Skip tests cleanly unless required DB env vars are present

## Acceptance Criteria

- No `OperationalError` due to missing DB host
- Test suite behavior is deterministic
- Skips are explicit and documented if used

## Files Likely Touched

- Test fixtures
- Test decorators / setup

## Commit Plan

- Commit A: test harness fix
- Commit B: docs/task mapping update
