# Fresh natural account import-to-recall proof R4 — 2026-09-23

## Classification

**`BLOCKED` after automatic embedding and exact vector parity, before recall completion.** R4 used a fresh isolated runtime and one bounded Chromium process. The rendered Settings import created, uploaded, committed, and completed one job under canonical owner `local`. The account-import worker materialized the source conversation; the continuously running chat-embedding worker processed both imported messages, which became `ready`. Backend and chat worker read the same two new Chroma records with stable IDs and matching canonical text hashes. After the task turn was interrupted, the Docker daemon became unreachable and the temporary R4 proof directory was absent. No recall thread or completion was submitted. The uninterrupted end-to-end chain therefore remains unproven.

This is a proof-environment continuity block, not an observed Codexify import, embedding, retrieval, or provider failure. The live result advances the post-materialization handoff from test evidence to bounded live-runtime evidence, but makes no retrieval or answer claim.

## Frozen source and fresh topology

- Evaluated clean local `main` at `25a0c9a48619ac72d99f16fae1bab425394c7814`, which contains embedding-handoff repair `dea9d49d874abd3c6ed47a1a8a0a3082c03abd02`; the ancestry check passed. Docker context: `desktop-linux`.
- Compose project: `codexify_natural_import_recall_r4_20260923`. The wrapper selected base `docker-compose.yml`, `docker-compose.whooshd-smoke.yml`, and the temporary R4 override only. The development and private-preview overrides were not loaded. Backend and workers used the R4 image tag `codexify-backend-runtime:proof-r4-25a0c9a4` built from the frozen checkout.
- Before creation, no R4 project containers or exact requested volume names existed. New volumes were `codexify_natural_import_recall_r4_20260923_pg`, `codexify_natural_import_recall_r4_20260923_chroma`, and `codexify_natural_import_recall_r4_20260923_imports`; Redis was fresh in the R4 project. The R2/R3, default, and private-preview volumes were not adopted or intentionally changed.
- `compose.sh config --quiet` passed. Rendered configuration and actual `docker inspect` mounts agreed: `db` used R4 PostgreSQL; backend, `worker-chat`, and `worker-chat-embed` shared R4 Chroma at `/app/.chroma`; backend and `worker-account-import` shared R4 import staging at `/app/data/imports`. Chroma mounts used `nocopy: true`. Runtime settings were Chroma, path `/app/.chroma`, collection `codexify_vault_supported`, and local embedding model `/models/bge-large-en-v1.5`.
- The normal migrator exited 0; the fresh database revision was `a8d4c2f6b1e9`, with user `local` and General Project `1|local`. Backend `/ping` and frontend returned successfully; the account-import, chat-embedding, and chat workers ran. Local Whoosh'd `/v1/models` exposed `local-chat`.
- Before import, read-only vector inspection from both backend and chat worker returned only `system-doc:builtin-help`, SHA-256 `49b815338b9bf67c7f5efda57d88a5a3a1db36ec97a6d587cd5e0feea81ce622`. The R4 source and markers were absent. No vector record was seeded.

## One rendered browser import

The synthetic OpenAI export contained one `conversations.json` file, 1,010 bytes, SHA-256 `52b3b78c27cf5b7aeaa8ab95a023c1386af5a33f4ecf6e0434171bebf84b7c01`. It used source conversation `axis-natural-import-recall-20260923-05`, title `Axis Natural Import Recall Probe R4`, source-message IDs `axis-natural-user-message-20260923-05` and `axis-natural-assistant-message-20260923-05`, and new markers `CODEXIFY_NATURAL_IMPORT_USER_MARKER_20260923_E` and `CODEXIFY_NATURAL_IMPORT_ASSISTANT_MARKER_20260923_E`. No real export was used.

The temporary `r4-browser-import.cjs` passed `node --check` before execution. A single Node/Playwright process (PID 6472) launched Chromium and kept it alive through the real rendered Settings → Imprint (`User Nickname: You`) → Data → Import ChatGPT history → OpenAI → Choose Folder flow. It located the actual `input[type="file"][webkitdirectory]`, used the browser file chooser's `setFiles(folder)`, and recorded sanitized request/response metadata without mocking the API. The browser intentionally closed after all lifecycle responses were captured; the receipt's final `chromiumDisconnected=true` reflects that normal close, not the R3 failure.

Job `9d774b1f-8c78-459b-9ca8-53eb324b12df` had HTTP 200 create, multipart upload, commit, and status responses. The upload response reported one uploaded file and 1,010 bytes; commit returned `queued`; status returned `running`. All four browser requests lacked `X-User-Id`. No request failed. PostgreSQL subsequently showed the same job `completed`, owner `local`, one declared and uploaded file, 1,010 declared and uploaded bytes, one imported thread, two imported messages, zero failures, and a checkpoint containing the exact R4 source conversation ID.

## Natural canonical and derived state

- PostgreSQL held Imports Project `2|local`, imported thread `1|local|project=2|origin_system=openai`, and two messages owned by `local`. Message 1 was the user source ID, SHA-256 `b372235b0d995e357131dfb7b028c7b3f09beff5ef420c5f5530da76c15761d9`; message 2 was the assistant source ID, SHA-256 `14e2d12841ec728b487141c86e610237a727f20c20ca369a5ed304e3ff562175`. Both carried the exact source conversation ID and were observed with `embedding_status=ready`.
- The account-import worker started before import with `recovered=0`, processed one conversation batch, and recorded `thread_count=1 message_count=2`. The continuously running `worker-chat-embed` logged `embedded message_id=1 thread_id=1` and `embedded message_id=2 thread_id=1` after materialization. No service restart, backfill, manual enqueue, or manual vector insertion occurred.
- After consumption, the dedicated import-embedding queue and ordinary chat-embedding queue both had depth zero. A positive queue-depth sample was not captured because two messages were consumed promptly. The worker logs, `ready` rows, and stable `chat-import-message:1` / `chat-import-message:2` vector IDs support the natural import-embedding path; they do not constitute a direct time-series receipt of the transient queue depth.
- Read-only inspection from both backend and `worker-chat` returned identical new records: `chat-import-message:1` and `chat-import-message:2`, each owned by `local`, in `thread:1`, with `source=chatgpt_import`, exact R4 source thread and source-message IDs, and text hashes matching the canonical messages above. The assistant vector contained the expected answer marker. Both saw the same built-in record as before. Counts alone were not used as parity evidence.

## Interruption boundary and validation

After vector parity, the task turn was interrupted. On continuation at approximately 23:06 UTC, both sandboxed and escalated `docker ps` returned `Cannot connect to the Docker daemon`, and `/private/tmp/codexify-natural-import-recall-r4-20260923/` was absent. The cause of the Docker and temporary-directory loss was not established. The R4 services could not be inspected or stopped, and retention of their Docker volumes could not be verified after the interruption. The temporary harness, fixture, and sanitized JSON receipt had been written and inspected during the live run but were no longer present on continuation. The observations above are drawn from the retained command outputs in this task, not from a surviving private receipt file.

No General recall thread, model completion, provider capture, persisted assistant answer, or Project-mode negative control was attempted. The one-completion limit was preserved at zero. Restarting services or rebuilding the proof from the interrupted R4 state would invalidate the required uninterrupted chain, so this receipt stops here.

| Boundary | R4 result |
| --- | --- |
| Fresh topology, migration, canonical `local`, clean shared Chroma baseline | Passed live runtime checks |
| Rendered browser folder upload and real create/upload/commit/status | Passed; four HTTP 200 responses, no `X-User-Id` |
| Canonical materialization | Passed; one conversation, two messages, zero job failures |
| Automatic import embedding and backend/chat-worker vector parity | Passed bounded live checks; no positive queue-depth sample |
| General recall, retrieval, actual Whoosh'd input, answer, persistence, negative scope control | Not attempted after proof-environment interruption |

Regression guards run on the frozen checkout after the interruption:

- `pnpm --dir frontend/src exec vitest run features/imports/__tests__/accountImportCoordinator.ChatGPTImportModal.test.ts components/modals/__tests__/ChatGPTImportModal.test.tsx`: 2 files, 22 tests passed.
- `.venv/bin/python -m pytest -v tests/routes/test_migration_routes.py tests/workers/test_account_import_worker.py tests/migration/test_openai_export_conversation_import.py tests/services/test_account_import_embedding_handoff.py tests/workers/test_chat_embedding_worker_import_replay.py`: 64 passed.
- `.venv/bin/python -m pytest -v tests/core/test_context_broker_source_mode.py tests/core/test_context_broker_depth.py tests/core/test_retrieval_user_isolation_and_widening.py tests/context/test_retrieval_scope_boundaries.py`: 53 passed.

**Next prerequisite:** use a new isolated runtime and synthetic IDs for an uninterrupted import-to-recall qualification through one completion. Do not resume R4, provoke a recovery sweep, or treat this partial proof as a provider/retrieval result. The automatic import-to-embedding handoff itself now has bounded fresh live-runtime evidence; the complete continuity chain remains open.

**ADR impact:** aligned with ADR-005, ADR-067, and ADR-081; no ADR amendment. **Documentation follow-through:** this receipt only. **Current-state and release claims:** unchanged.
