# Account import commit through canonical materialization proof — 2026-09-23

## Verdict and boundary

**F. Commit → queue → worker → canonical materialization passes** in the disposable isolated local runtime. The rendered Chromium Settings UI created, uploaded, and committed job `788e5d0b-0aab-4df9-8772-39a0907b6eec`. Its exact Redis item was observed before the worker started. The account-import worker consumed it, and the exact-job API and read-only PostgreSQL readback agree on a completed job with one imported thread, two imported messages, and zero failures. The canonical rows carry the expected OpenAI source provenance and belong to user `local` and a Project owned by `local`.

This is `proven-live-runtime` through canonical PostgreSQL materialization in the isolated local subset. It does not qualify the complete supported profile, private preview, end-user conversation visibility, embeddings, retrieval, or continuity. The historical Safari 422 observation and the affected user's current complaint remain distinct from this local result.

## Source and isolated runtime

- Source branch/HEAD: `main` / `38d60aa7cceb7afee024ccd4b9d7260b47c0d90e`. At start, `git status --short --branch --untracked-files=all` was clean (`main...origin/main [ahead 2]`). `git merge-base --is-ancestor d31858de06249da21494000aba7548614e5d2c25 HEAD` exited 0.
- Compose project: `codexify_account_import_ui_probe_20260923`. Retained PostgreSQL/Redis volumes were confirmed to belong to this isolated project; prior staged probe jobs were left untouched. The existing development/private-preview stack was not used.
- Compose sources: `docker-compose.yml`, `docker-compose.whooshd-smoke.yml`, and `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml`. The temporary override exposed loopback ports and mounted the same isolated staging directory into backend and `worker-account-import`. It is outside Git. Backend accepted `CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`, but this proof ran a subset of services, not full supported-profile qualification.
- Frontend: `http://127.0.0.1:5183`; backend: `http://127.0.0.1:8893`; PostgreSQL: `codexify_account_import_ui_probe_20260923-db-1` at `127.0.0.1:5548`; Redis: `codexify_account_import_ui_probe_20260923-redis-1`; worker: `codexify_account_import_ui_probe_20260923-worker-account-import-1`. Database revision: `a8d4c2f6b1e9`.
- Before the fresh job, backend, PostgreSQL, and Redis were healthy, frontend was reachable, and `worker-account-import` was absent/stopped. Baseline account-import queue depth was 0; existing account-import job count was 6; canonical thread/message counts for the new source ID were both 0. All Postgres inspection used read-only transactions.

## Synthetic browser-originated job

The test generated a temporary `openai-export` folder using the mapping conversation shape exercised by `tests/migration/test_openai_export_conversation_import.py`. It contained exactly one recoverable conversation with source ID `axis-import-materialization-20260923-01`, title `Axis Import Materialization Probe`, a user message with source ID `axis-import-user-message-20260923-01`, and an assistant message with source ID `axis-import-assistant-message-20260923-01`. The bodies were synthetic markers and are omitted here. The temporary fixture directory was removed after browser submission.

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `openai-export/conversations.json` | 985 | `1e622bfe53114c77792523bfca96cde557975b1f7d21f0fc1f2384f49dbbf862` |

The rendered UI path was Settings → Data → Import ChatGPT history → Import account data → OpenAI (ChatGPT) → Choose Folder. Playwright selected the generated folder through the actual file chooser. No account-import API was mocked or called directly as the primary action. At `2026-09-23T15:44:11.515Z`, browser network receipts showed `POST /api/imports/openai-account` HTTP 200, `POST /api/imports/openai-account/788e5d0b-0aab-4df9-8772-39a0907b6eec/files` HTTP 200, and only then `POST /api/imports/openai-account/788e5d0b-0aab-4df9-8772-39a0907b6eec/commit` HTTP 200. The exact-job status API returned HTTP 200 and `queued`, with 1/1 file and 985/985 bytes. Its staged manifest preserved the relative path, size, and SHA-256 above.

## Queue, worker, and terminal job

Before worker startup, Redis `LLEN codexify:queue:account-import` changed from baseline 0 to 1. A non-destructive `LRANGE codexify:queue:account-import 0 -1` returned one item with `type=openai_account_import`, `job_id=788e5d0b-0aab-4df9-8772-39a0907b6eec`, and `user_id=local`. The exact-job API and PostgreSQL row both showed `queued`, owner `local`, source `openai`, intact staged counts, populated `queued_at`, and null `started_at`/`completed_at`. No queue item was manually consumed.

Only `worker-account-import` was started, using `docker compose -p codexify_account_import_ui_probe_20260923 -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f /private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml up -d --no-deps worker-account-import`. Its container start timestamp was `2026-09-23T15:45:12.008707302Z`. Bounded logs reported `recovered=1`, canonical importer processing 1/1 conversation, `thread_count=1 message_count=2`, and `imported=1 failed=0 skipped=0`. Worker startup recovery re-enqueues incomplete queued jobs, so the logs do not distinguish the original Redis payload from the recovered payload. The exact job was processed once to completion and Redis queue depth became 0. Exact-job API and Postgres then agreed on `completed`; the observed status sequence was `queued` → `completed`, with `started_at` recording the intervening worker execution. A separate API snapshot of `running` was not captured.

| Exact-job terminal field | Value |
| --- | --- |
| `status` | `completed` |
| `uploaded_file_count` / `uploaded_byte_count` | 1 / 985 |
| `imported_thread_count` / `imported_message_count` / `imported_media_count` | 1 / 2 / 0 |
| `duplicate_count` / `skipped_count` / `warning_count` / `failure_count` | 0 / 0 / 0 / 0 |
| `queued_at` | `2026-09-23T15:44:11.450901+00:00` |
| `started_at` | `2026-09-23T15:45:12.908659+00:00` |
| `completed_at` | `2026-09-23T15:45:15.183967+00:00` |

The terminal source summary reported one conversation discovered and accepted, zero failed/skipped, and committed conversation transactions. No canonical completion is inferred from queue disappearance alone.

## Canonical PostgreSQL reconciliation

Read-only queries selected the imported thread by `chat_threads.metadata->>'source_thread_id'`, then messages by their existing `extra_meta` provenance, rather than by title alone. They returned exactly one thread and two messages:

| Row | Canonical ID | Owner / parent | Existing provenance and order |
| --- | --- | --- | --- |
| Project | `2` | `projects.user_id=local` | Existing Project linked by the imported thread |
| Thread | `1` | `chat_threads.user_id=local`, `project_id=2` | `origin_system=openai`; `source_thread_id=axis-import-materialization-20260923-01` |
| User message | `1` | `thread_id=1`, `user_id=local` | `role=user`; matching source conversation ID; `source_message_id=axis-import-user-message-20260923-01`; `turn_index=0` |
| Assistant message | `2` | `thread_id=1`, `user_id=local` | `role=assistant`; matching source conversation ID; `source_message_id=axis-import-assistant-message-20260923-01`; `turn_index=1` |

The durable 1-thread/2-message counts match both the two recoverable source messages and the exact job's `imported_thread_count=1` / `imported_message_count=2`; `failure_count=0`. `embedded_at` was null on both messages, consistent with the worker's deferred embedding path. No embedding or retrieval behavior was tested.

## Validation and scope

| Command | Result | Evidence posture |
| --- | --- | --- |
| `pnpm --dir frontend/src exec eslint tests/playwright/migration_e2e_import.spec.ts` | Passed | `proven-test` syntax/style |
| `pnpm --dir frontend/src exec playwright test tests/playwright/migration_e2e_import.spec.ts --config=/private/tmp/codexify-account-import-ui-staging-20260923/playwright.config.mjs --project=chromium --grep 'commits a valid OpenAI export for materialization'` | 1 passed | `proven-live-runtime` for the exercised browser → commit → queued boundary |
| `.venv/bin/python -m pytest -v tests/workers/test_account_import_worker.py` | 9 passed | `proven-test` |
| `.venv/bin/python -m pytest -v tests/migration/test_openai_export_conversation_import.py` | 21 passed | `proven-test` |
| `.venv/bin/python -m pytest -v tests/routes/test_migration_routes.py` | 28 passed | `proven-test` |
| `rg -n 'openai_account_import|account-import|source_thread_id|imported_thread_count|imported_message_count' guardian backend/rag tests` | Completed; located current fields and tests | Discovery only |

The temporary Playwright config is the one used by the preceding staging proof; the checked-in config/package layout does not run the requested `pnpm --dir frontend ... --project=chromium` command directly. After readback, only the isolated proof services were stopped; their volumes were retained for review. This task changed only the Playwright test and this proof artifact. Production frontend, route, queue, worker, importer, ownership, provenance, schema, UMS, and retrieval behavior were unchanged. Only synthetic data entered the isolated local runtime; no real user export or private-preview state was touched. No release claim or `00-current-state.md` update follows from this proof.

ADR impact: **No ADR impact**. Documentation follow-through: **proof artifact only**. Current-state change: **none**. Release-claim change: **none**.

Next prerequisite: **Trace the newly materialized imported conversation from canonical Postgres state into the user-visible conversation list and governed retrieval/continuity path.**
