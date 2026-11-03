# Main reconciliation and private-preview restart — 2026-10-21

## Scope and authority

The operator authorized local-main reconciliation and private-preview restart, then separately approved integrating the existing UMS ORM fix and repairing the three missing collaboration tables. No push was authorized or performed. ADR-084 behavior and the release HOLD are unchanged; these repairs restore existing mappings and canonical schema, without introducing a new contract or ADR.

## Git and files

- Origin snapshot: `f7e6a7f48dd1928e25f7588208484c68e9db93e4`.
- Original local main: `5c8a8ecd9d4bf1970e6296d5bf5a1fad3b981196`, preserved on `codex/backup-main-before-reconcile-20261021`; the dirty temporary checkout's staged work was preserved.
- Reconciliation merge: `e41a15abe66c7de645013246374c7bfa49acd67d`. Both histories retained; documentation conflicts resolved without widening release claims.
- ORM restoration: `ba291b025df16c4fa44515f3a3621daed0d52e1d`, cherry-picked with provenance from `1ee3a0f65408b8cc7e54e6afc2f17fd31429c035`. Changes are four ORM classes plus PrimaryKeyConstraint in `guardian/db/models.py`, and the original Oct 16 proof document. Existing ORM classes were unchanged by AST comparison.
- Serving source: `/Volumes/Dev_SSD/offload/codex/worktrees/main-reconcile-20261021`. The untracked operator-only Compose overlay remains required. Its frontend mount was adapted from the old frontend-directory layout to the new repository-root workspace layout.
- Unrelated primary-checkout continuity edits and untracked files were preserved. This receipt and the current-state/hash follow-through change documentation only.

## Schema repair

Applied the separately approved SQL in one transaction, restoring only `collaboration_audit_log`, `collaboration_permissions`, and `shared_links` plus six indexes from canonical migration `13a4a6dc5ba1`. Approved SQL SHA256: `4b7ab7031ddd9d99d32a033b561198c7cee8910e7fd1f48526c99d61f4c87869`. No migration stamp change or data deletion occurred. The recorded head remains `f0d7c4b2a198`; users 7, chat_threads 5131, chat_messages 113443 before and after. Fresh EXPECTED_TABLES comparison reported no missing tables.

## Validation

Direct four-model imports, memory service imports, and SQLAlchemy configure_mappers passed. Disposable PostgreSQL 15 validation ran from the isolated source using the primary checkout's Python environment:

```text
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -q tests/migration/test_memory_revision_persistence_migration.py tests/migration/test_memory_review_revision_persistence_migration.py tests/migration/test_memory_lifecycle_revision_persistence_migration.py tests/migration/test_memory_purge_tombstone_migration.py tests/services/test_memory_purge.py tests/services/test_memory_vault_mutation.py -o addopts= -o cache_dir=/private/tmp/codexify-main-reconcile-20261021/orm-validation/pytest-cache --tb=short --junitxml=/private/tmp/codexify-main-reconcile-20261021/orm-validation/results.xml
```

Result: **124 passed, 1 failed, 0 errors, 0 skipped**, 136 warnings. The inherited failure is `test_fresh_migration_creates_purge_tombstones_with_orm_parity`: its terminal-head assertion expects `c7f4a9b2e6d1`, but main's actual head is `f0d7c4b2a198`. The original fix proof records the same failure. It was not bypassed or repaired. All 76 service tests passed. The task-owned disposable database was removed after validation.

## Runtime evidence

Sequential builds avoided duplicate backend-image exporters. Running backend image: `sha256:7a08e1defa4351c52e004b13af3d97d39a9d6fc1e5a0fb49914227fdfd853812`; coding-worker image: `sha256:a3177274d0b5e90e4db762f6723b312ed57b6c1bf2f2aaa69995ce9ab735229b`. Image IDs and live ORM-file hashes matched the repaired serving revision. Application/config mounts use that source; persistent data/media/import/model paths retain the primary checkout. Named persistent volumes were retained. Only the existing loopback origin port `127.0.0.1:8081` is published.

Docker returned a transient API 500 during startup; retry completed. Frontend dependencies installed from the locked workspace and Vite started. At 21:41 UTC, `/`, `/health`, and `/health/chat` returned HTTP 200; core status was ok, chat ok=true/status=healthy with a fresh worker heartbeat. The supported profile reports `v1-whooshd-deepseek-web`, valid=true and release_hold=true. The actual `/main.tsx` entry and `/components/library/LibraryView.tsx` module both returned JavaScript with HTTP 200. Setup jobs exited zero. The e2e helper exit is setup evidence, not an executed browser test suite.

Documentation checks: `make docs PYTHON=python3` passed, with an inherited diagram review-marker warning; scoped `git diff --check` passed. The current-state knowledge-graph content hash was refreshed while its freshness remains stale.

## Limits and evidence custody

This is bounded local restart/source/schema/health evidence. No new provider inference, ordinary-chat durable readback, browser interaction, external ingress, or complete supported-core qualification was performed. No release claim was widened. Startup restarts and transient health timeouts were observed before stabilization.

Nonsecret command receipts, SQL, before/after runtime snapshots, HTTP bodies, database counts, image IDs, and test XML remain under `/private/tmp/codexify-main-reconcile-20261021`; temporary artifacts are not a durable release bundle. Credentials and env files were not committed.
