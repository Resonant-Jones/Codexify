# TASK_2026_02_06_008_memory_routes_return_404_on_cross_user_access

## Objective

Align memory route behavior with non-disclosure security semantics.

## Background

Tests expect a 404 when a resource exists but belongs to another user.
Current behavior returns 403, leaking existence.

## Requirements

- Ownership mismatch must return 404
- Auth missing behavior remains unchanged
- Test expectations must pass

## Acceptance Criteria

- Cross-user memory access returns 404
- Tests `test_memory_update_other_user_404` and delete equivalent pass

## Files Likely Touched

- Guardian memory routes
- Authorization logic

## Commit Plan

- Commit A: backend behavior change
- Commit B: docs/task mapping update
