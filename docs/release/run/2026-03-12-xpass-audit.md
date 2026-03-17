# XPASS Audit - 2026-03-12

Date: 2026-03-12
Branch tested: `codex/apply-campaign-task-execution-rules`
Commit tested: `2baba6776` (docs: audit xpassed tests after stabilization merge)
Operator: Claude Code

## Summary

Fresh baseline evidence from `pytest -v` shows `11 xpassed` tests in the current tree:

- `878 passed, 15 skipped, 33 xfailed, 11 xpassed, 25 warnings in 81.00s (0:01:21)`
- All 11 `XPASS` cases came from two files:
  - `tests/routes/test_chat_routes.py`: 3
  - `tests/scripts/test_cli_migrate.py`: 8

Audit conclusion:

- `3` tests are `stale xfail marker, likely safe to normalize`
- `8` tests are `passing but needs confirmation before marker removal`
- `0` tests are currently in `unclear, requires deeper investigation`

## Evidence

Primary baseline command:

```bash
pytest -v
```

Focused follow-up commands used only to expand the exact `XPASS` node ids from the baseline:

```bash
pytest -v -rX tests/routes/test_chat_routes.py
pytest -v -rX tests/scripts/test_cli_migrate.py
```

## Classification

### Stale xfail marker, likely safe to normalize

| Node id | Marker location | Likely reason now passing | Audit note |
|---|---|---|---|
| `tests/routes/test_chat_routes.py::TestChatThreadsPost::test_create_thread_reuses_recent_empty` | `tests/routes/test_chat_routes.py:137` | `guardian/routes/chat.py:1061-1072` now has an explicit idempotency guard that reuses the recent empty thread and returns `recent_id` directly when `count_messages(recent_id) == 0`. The mocked `id == 42` path now matches the assertion instead of drifting on a DB-generated id. | The original marker text says the real DB counter could diverge from the mock id, but that mismatch is not reproducing in the current handler. This looks like a stale route-era compatibility marker. |
| `tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_empty_context` | `tests/routes/test_chat_routes.py:982` | `guardian/routes/chat.py:1365-1380` now filters unusable messages and raises `HTTPException(status_code=400, detail="Thread has no usable context")` when the context collapses to empty. That matches the test exactly. | The marker reason says a status-code difference was acceptable, but the live route now returns the asserted `400`. Safe candidate for normalization. |
| `tests/routes/test_chat_routes.py::TestChatThreadBranchPost::test_branch_thread_success` | `tests/routes/test_chat_routes.py:1115` | `guardian/routes/chat.py:1654-1684` now builds the child thread from the parent and returns the `create_chat_thread(...)` record directly. With the mocked return payload, the response preserves `id == 2` and `parent_id == 1` as asserted. | Same pattern as the thread-reuse case: the harmless mock-vs-real id discrepancy described by the marker no longer appears in the current code path. |

### Passing but needs confirmation before marker removal

These eight tests live under the file-level marker at `tests/scripts/test_cli_migrate.py:21`:

`pytestmark = pytest.mark.xfail(reason="Legacy CLI migration API; superseded by backend.rag.chatgpt_migration.ingest_chatgpt_export", strict=False)`

They pass because narrow helper paths in the legacy script still work, not because the deprecated CLI has been re-endorsed as a supported surface.

| Node id | Likely reason now passing | Audit note |
|---|---|---|
| `tests/scripts/test_cli_migrate.py::TestCLIMigrateCommand::test_migrate_missing_file` | `scripts/chatgpt_import/cli_migrate.py:147-155` defines the `file` argument with `exists=True`, so Typer rejects `/nonexistent/file.json` before the deprecated migration path runs. | This is real passing behavior, but it only proves CLI argument validation still works. Removing the xfail cleanly would require deciding whether to keep this legacy command under support rather than just splitting out one passing test. |
| `tests/scripts/test_cli_migrate.py::TestCLIHistoryCommand::test_history_no_migrations` | `scripts/chatgpt_import/cli_migrate.py:351-356` returns early with a friendly "No migration history found" message when the log file is absent. | The behavior is stable and likely intentional, but the enclosing xfail documents product-level deprecation, not an isolated bug. Confirm desired support status before normalizing. |
| `tests/scripts/test_cli_migrate.py::TestCLIIntegration::test_cli_help_command` | Typer CLI framework generates help correctly for the main app. | CLI framework behavior is stable, but the module-level xfail documents product-level deprecation. Confirm desired support status before normalizing. |
| `tests/scripts/test_cli_migrate.py::TestCLIIntegration::test_cli_migrate_help` | Typer CLI framework generates subcommand help correctly. | CLI framework behavior is stable, but the module-level xfail documents product-level deprecation. Confirm desired support status before normalizing. |
| `tests/scripts/test_cli_migrate.py::TestCLIIntegration::test_cli_validate_help` | Typer CLI framework generates subcommand help correctly. | CLI framework behavior is stable, but the module-level xfail documents product-level deprecation. Confirm desired support status before normalizing. |
| `tests/scripts/test_cli_migrate.py::TestCLIIntegration::test_cli_history_help` | Typer CLI framework generates subcommand help correctly. | CLI framework behavior is stable, but the module-level xfail documents product-level deprecation. Confirm desired support status before normalizing. |
| `tests/scripts/test_cli_migrate.py::TestSummaryLogging::test_save_migration_summary` | `scripts/chatgpt_import/cli_migrate.py:118-144` still creates `logs/migration_summary.json`, stamps `completed_at`, and writes a list payload. | This helper remains functional, but it is still housed inside the deprecated CLI script. Marker removal should follow an ownership decision for the legacy script or extraction of the helper into a supported module. |
| `tests/scripts/test_cli_migrate.py::TestSummaryLogging::test_save_migration_summary_appends` | The same `save_migration_summary()` helper still appends successive summary dicts to the JSON list at `scripts/chatgpt_import/cli_migrate.py:126-142`. | Same conclusion as the prior row: the helper works, but the xfail is broader than this one behavior. Confirm support intent before removing the marker. |

### Unclear, requires deeper investigation

No current `XPASS` cases landed in this bucket. The route-side passes map cleanly to current implementation, and the CLI-side passes are explainable as helper-path successes inside a still-deprecated script.

## Recommended follow-up

Smallest safe next step:

1. Remove or narrow the three route-level `xfail` markers in `tests/routes/test_chat_routes.py`.
2. Decide whether `tests/scripts/test_cli_migrate.py` should stay under a file-level legacy `xfail`, or whether passing helper tests should be split out before any marker removal.
