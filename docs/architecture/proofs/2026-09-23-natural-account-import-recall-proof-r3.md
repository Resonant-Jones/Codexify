# Fresh natural account import-to-recall proof R3 — 2026-09-23

## Classification

**`BLOCKED` at rendered folder upload.** A new isolated runtime at the committed embedding-handoff repair reached the Settings account-import UI, and folder selection created one job under canonical owner `local`. The browser automation session closed while applying the folder selection. The job remained `receiving` with one declared file and zero uploaded files; no commit or canonical conversation occurred. This is an incomplete browser/harness transport attempt, not evidence that the repaired embedding handoff failed. No second browser import, direct API upload, recovery action, or recall completion was attempted.

## Frozen source and isolation

- Evaluated clean local `main` at `dea9d49d874abd3c6ed47a1a8a0a3082c03abd02`. `git merge-base --is-ancestor 7eafe427391bd172b6dec00939ea0ea7d9c520cf HEAD` and the same check for `dea9d49d874abd3c6ed47a1a8a0a3082c03abd02` both passed. Docker context: `desktop-linux`.
- Compose project: `codexify_natural_import_recall_r3_20260923`. The temporary wrapper `/private/tmp/codexify-natural-import-recall-r3-20260923/compose.sh` selected the repository base Compose file, the checked-in Whoosh'd smoke override, and the R3 temporary override. The development and private-preview overrides were not loaded. The backend/worker image was built from this checkout as `codexify-backend-runtime:proof-r3-dea9d49d`, image ID `sha256:7a874700456ea11804d38946c9da8e85b30e4c3fa6ade489c199afcb307877aa`.
- Before creation, no R3 project container or exact R3 volume name existed. New proof-owned volumes were `codexify_natural_import_recall_r3_20260923_pg`, `codexify_natural_import_recall_r3_20260923_chroma`, and `codexify_natural_import_recall_r3_20260923_imports`. Redis was a fresh container in the same project. The R2, earlier failed, default, and private-preview volumes were not reused or changed.
- `compose.sh config --quiet` passed. The rendered configuration and actual container mounts agreed: `db` used R3 PostgreSQL; backend, `worker-chat`, and `worker-chat-embed` shared R3 Chroma at `/app/.chroma`; backend and `worker-account-import` shared R3 import staging at `/app/data/imports`. Chroma mounts used `nocopy: true`. The vector configuration was `chroma`, `/app/.chroma`, collection `codexify_vault_supported`, with local embedding model `/models/bge-large-en-v1.5`.
- The normal migrator exited 0; the fresh database reached Alembic revision `a8d4c2f6b1e9`, contained user `local`, and had General Project `1|local`. Backend `/ping` returned healthy, frontend Vite became ready, and the account-import, chat-embedding, and chat workers were running. Local Whoosh'd `/v1/models` exposed logical `local-chat`.
- Before import, read-only VectorStore inspection from both backend and `worker-chat` returned the same one built-in record, `system-doc:builtin-help`, hash `49b815338b9bf67c7f5efda57d88a5a3a1db36ec97a6d587cd5e0feea81ce622`. No R3 source ID or marker was present. No vector record was seeded.

## Synthetic fixture and first failed boundary

The only selected fixture was `/private/tmp/codexify-natural-import-recall-r3-20260923/fixture/openai-export/conversations.json`: one file, 1,010 bytes, SHA-256 `2fe6b9a694aafc82f74c74356e29c09df7a2b0c4697ddd77c61c9b46e843146e`. Its new source conversation ID was `axis-natural-import-recall-20260923-04`, title `Axis Natural Import Recall Probe R3`, with source-message IDs `axis-natural-user-message-20260923-04` and `axis-natural-assistant-message-20260923-04`. The bodies carried new markers `CODEXIFY_NATURAL_IMPORT_USER_MARKER_20260923_D` and `CODEXIFY_NATURAL_IMPORT_ASSISTANT_MARKER_20260923_D`. No real export was used.

A fresh Chromium session rendered Settings → Imprint with `User Nickname: You`, then Settings → Data → Import ChatGPT history → Import account data. OpenAI (ChatGPT) was selected. The rendered `Choose Folder` control opened the browser file chooser. The Playwright CLI `upload` command supplied the R3 fixture folder, then failed with `Error: Session closed`; a later session snapshot reported the browser was not open. The CLI's first sandboxed launch had exited with `SIGABRT`; an escalated fresh Chromium launch succeeded. The subsequent session closure occurred during folder upload, after UI navigation and before a completed upload receipt could be captured.

PostgreSQL recorded exactly one account-import job, `31358caa-70b8-447e-b856-fa31ce3e3046`, with `user_id=local`, `source_system=openai`, `status=receiving`, `total_file_count=1`, `uploaded_file_count=0`, `imported_thread_count=0`, `imported_message_count=0`, and `failure_count=0`. Its checkpoint had empty conversation and media lists. A second read after the browser closure showed the same state, zero `chat_threads`, zero `chat_messages`, and zero queued account-import or `chat-import-embed` tasks. The browser session closed before its planned sanitized request-header capture could be read; this receipt does not claim a live `X-User-Id` header observation. The canonical job owner is observed directly in PostgreSQL.

| Boundary | R3 result |
| --- | --- |
| Frozen repair, fresh isolated topology, migration, canonical `local`, clean shared Chroma baseline | Passed live runtime checks |
| Rendered Settings and OpenAI folder picker | Passed browser observation |
| Folder upload and commit | **Blocked:** browser session closed; 0/1 files uploaded and no commit |
| Canonical materialization, automatic enqueue, pending → ready, vector parity, retrieval, provider input, answer, persistence | Not attempted after the first failed boundary |

## Validation and closeout

- `pnpm --dir frontend/src exec vitest run features/imports/__tests__/accountImportCoordinator.ChatGPTImportModal.test.ts components/modals/__tests__/ChatGPTImportModal.test.tsx`: 2 files, 22 tests passed. This is regression-test evidence, not the R3 upload outcome.
- `.venv/bin/python -m pytest -v tests/routes/test_migration_routes.py tests/workers/test_account_import_worker.py tests/migration/test_openai_export_conversation_import.py`: 59 passed. This is route/import/worker test evidence.
- `.venv/bin/python -m pytest -v tests/core/test_context_broker_source_mode.py tests/core/test_context_broker_depth.py tests/core/test_retrieval_user_isolation_and_widening.py tests/context/test_retrieval_scope_boundaries.py`: 53 passed. This is retrieval-policy test evidence; R3 submitted no recall completion.

Only R3 proof services were stopped after the blocked boundary. Its named PostgreSQL, Chroma, and import-staging volumes, temporary fixture, browser snapshots, and diagnostics were retained. No `docker compose down -v`, manual enqueue, backfill, vector write, status reset, service restart to provoke indexing, second import job, or recall completion occurred. R2 remains frozen at `4beacf64dfae93834b154f68b361aa46b094eeb6` and its volumes were untouched.

**Next prerequisite:** run a new clean isolated natural import-to-recall attempt with a reliable rendered-browser folder upload. Use new project/volumes and synthetic IDs; do not resume or repair this incomplete R3 job. The post-materialization handoff and downstream chain remain `proven-test` or prior bounded replay evidence, not R3 live proof.

**ADR impact:** aligned with ADR-005, ADR-067, and ADR-081; no ADR change. **Documentation follow-through:** this receipt only. **Current-state and release claims:** unchanged.
