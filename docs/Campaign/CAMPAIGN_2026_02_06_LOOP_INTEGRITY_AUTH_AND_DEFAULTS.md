# CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

## Campaign-ID

CAMPAIGN-2026-02-06-LOOP_INTEGRITY_AUTH_AND_DEFAULTS

## Status

PLANNED

## Objective

Close regressions introduced by recent environment hardening and auth enforcement by restoring safe defaults, enforcing frontend/backend auth parity, and aligning test behavior with intended security semantics.

This campaign focuses on:

- Default configuration safety (no breakage on fresh clone)
- Frontend parity with Guardian API key enforcement
- Security-consistent error semantics (404 vs 403)
- Test determinism in local/dev environments

## Scope

- Guardian backend (embeddings, auth, share, memory routes)
- Frontend editor + share flows
- Test suite correctness and stability
- Repo templates and environment defaults

## Tasks

- TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix
- TASK-2026-02-06-006_frontend_autosave_includes_auth_headers
- TASK-2026-02-06-007_frontend_share_create_includes_auth_headers
- TASK-2026-02-06-008_memory_routes_return_404_on_cross_user_access
- TASK-2026-02-06-009_share_create_requires_api_key_returns_401
- TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db

## Mapping (placeholders)

TASK-2026-02-06-005_embedder_stub_alias_to_dummy_and_template_fix -> [62b4ba58, 2738a365]
TASK-2026-02-06-006_frontend_autosave_includes_auth_headers -> [<commitA>, <commitB>]
TASK-2026-02-06-007_frontend_share_create_includes_auth_headers -> [<commitA>, <commitB>]
TASK-2026-02-06-008_memory_routes_return_404_on_cross_user_access -> [<commitA>, <commitB>]
TASK-2026-02-06-009_share_create_requires_api_key_returns_401 -> [<commitA>, <commitB>]
TASK-2026-02-06-010_realtime_permissions_tests_use_sqlite_or_skip_without_db -> [<commitA>, <commitB>]

## Completion Criteria

- All tasks merged with A/B commit structure
- Fresh clone + default `.env` does not break embeddings, autosave, or sharing
- Test suite passes or fails *only* for meaningful reasons
- Campaign mapping filled with commit hashes
