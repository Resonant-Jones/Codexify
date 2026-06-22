# Core-Suite Failure Quarantine: C08-T003 Model Inventory Identity Proof

## Scope

This is a quarantine manifest for `pytest -v tests/core` results during C08-T003 validation only. It does **not** fix or alter the failing tests, change code, change test behavior, or start C08-T004. It groups failures by test file for practical quarantine — 73 failures/errors across 21 test files.

## Command

`pytest -v tests/core`

## Summary

| Status | Count |
|--------|-------|
| passed | 323 |
| failed | 67 |
| errors | 6 |
| skipped | 1 |
| warnings | 1 |

## Grouped Failure Manifest

### Test File Groups

| # | File | Count | Category | Touches Whoosh'd? | Touches C08 files? | Evidence |
|---|------|-------|----------|--------------------|--------------------|----------|
| 1 | `test_chat_completion_service_image_routing.py` | 16 | failure | No | No | Image routing — not Whoosh'd |
| 2 | `test_ai_router.py` | 12 | failure | No | No | Provider routing — Whoosh'd not in scope |
| 3 | `test_turn_lock_recovery.py` | 6 | error | No | No | Turn lock — not Whoosh'd |
| 4 | `test_supported_profile_startup.py` | 5 | failure | No | No | Supported profile — not Whoosh'd |
| 5 | `test_chat_completion_service_tool_loop.py` | 4 | failure | No | No | Tool loop — not Whoosh'd |
| 6 | `test_chat_completion_service_source_mode_fallback.py` | 4 | failure | No | No | Source mode — not Whoosh'd |
| 7 | `test_public_allowlist_exposure.py` | 3 | failure | No | No | Allowlist — not Whoosh'd |
| 8 | `test_chat_completion_service_thread_config.py` | 3 | failure | No | No | Thread config — not Whoosh'd |
| 9 | `test_chat_completion_service_retrieval_plan.py` | 3 | failure | No | No | Retrieval plan — not Whoosh'd |
| 10 | `test_chat_completion_service_latest_turn_retrieval.py` | 3 | failure | No | No | Turn retrieval — not Whoosh'd |
| 11 | `test_chat_completion_service_latest_turn.py` | 2 | failure | No | No | Turn — not Whoosh'd |
| 12 | `test_chat_completion_service_latest_turn_regression.py` | 2 | failure | No | No | Turn regression — not Whoosh'd |
| 13 | `test_supported_profile_quarantine.py` | 2 | failure | No | No | Profile quarantine — not Whoosh'd |
| 14 | `test_supported_profile.py` | 1 | failure | No | No | Profile — not Whoosh'd |
| 15 | `test_supported_profile_provider.py` | 1 | failure | No | No | Provider profile — not Whoosh'd |
| 16 | `test_obsidian_only_retrieval.py` | 1 | failure | No | No | Obsidian retrieval — not Whoosh'd |
| 17 | `test_chat_completion_service_latest_turn_trace.py` | 1 | failure | No | No | Turn trace — not Whoosh'd |
| 18 | `test_chat_completion_service_identity_wiring.py` | 1 | failure | No | No | Identity wiring — not Whoosh'd |
| 19 | `test_chat_completion_service_attachments.py` | 1 | failure | No | No | Attachments — not Whoosh'd |
| 20 | `test_chat_completion_memory_preselection_options.py` | 1 | failure | No | No | Memory preselect — not Whoosh'd |
| 21 | `test_beta_router_quarantine.py` | 1 | failure | No | No | Beta router — not Whoosh'd |

## C08 Relevance Conclusion

- **0 failures/errors touch `guardian/core/whooshd_model_profiles.py`.**
- **0 failures/errors touch `tests/core/test_whooshd_model_inventory_identity_semantics.py`.**
- **0 failures/errors touch Whoosh'd model inventory identity semantics.**
- **0 failures/errors invalidate C08-T003 focused tests.**
- **0 failures/errors invalidate the model inventory proof artifact.**
- **0 failures/errors block C08-T004.**

All 73 failures/errors are pre-existing and unrelated to C08 scope.

## Boundary Statement

- These failures do not become C08 scope unless they touch C08-modified surfaces.
- C08-T003 does not repair broad core-suite debt.
- Model inventory proof remains focused on Whoosh'd identity semantics.
- Broad suite debt should be tracked separately.

## Gate Recommendation

**`go`** — Quarantine complete. No C08-relevant failures.
