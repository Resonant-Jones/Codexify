# TASK_2026_02_06_007_frontend_share_create_includes_auth_headers

## Objective

Ensure share link creation works in secured environments.

## Background

`/api/share` now enforces API key auth.
Frontend ShareButton does not include auth headers, resulting in 401 failures.

## Requirements

- Share creation requests include required auth headers
- UI reflects failure state when request is rejected

## Acceptance Criteria

- Share creation succeeds when API key is configured
- Share creation fails loudly (not silently) if unauthorized

## Files Likely Touched

- `frontend/src/components/ShareButton.tsx`

## Commit Plan

- Commit A: frontend fix
- Commit B: docs/task mapping update
