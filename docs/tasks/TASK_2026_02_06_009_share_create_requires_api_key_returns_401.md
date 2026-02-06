# TASK_2026_02_06_009_share_create_requires_api_key_returns_401

## Objective

Fix share creation auth test mismatch.

## Background

Test expects `/api/share` to return 401 without API key, but current behavior returns 200.

## Requirements

- API key enforcement must be consistent in runtime and tests
- Test behavior must match production semantics

## Acceptance Criteria

- Missing API key → 401
- Test `test_create_share_requires_api_key` passes reliably

## Files Likely Touched

- Share router
- Dependency injection / app setup
- Tests

## Commit Plan

- Commit A: backend/test fix
- Commit B: docs/task mapping update
