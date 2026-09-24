# Imported-history semantic retrieval eligibility proof — 2026-09-23

## Verdict and proof boundary

**E. Personal Knowledge + normal selects imported evidence cross-project, and Project mode excludes it.** In the retained local account-import runtime, canonical imported messages 1 and 2 were pending before the normal embedding consumer ran. A Guardian backend startup sweep had placed exactly those two messages on the import-embedding queue. The persistent `worker-chat-embed` consumed both jobs, marked both messages ready, and wrote vectors that the configured `VectorStore.search()` found. A new, empty thread in General selected both imported messages through `ContextBroker.assemble()` with `personal_knowledge` and `normal`; the same thread and query selected neither in `project` mode.

This is `proven-live-runtime` only through broker selection in this isolated local database/Redis runtime. It is not provider-ready injection, an assistant answer, private-preview behavior, complete supported-Compose qualification, or a release claim. The focused tests below are `proven-test`, and the handoff explanation is `proven-code-path` corroborated by startup/worker logs.

## Evaluated source and retained runtime

- Repository: `/Volumes/Dev_SSD/Codexify-main`, branch `main`, evaluated HEAD `d0b31ae9914687567c2ce8d9f84e06c255f13ccf`. The initial `git status --short --branch --untracked-files=all` was clean (`main...origin/main [ahead 2]`). `git merge-base --is-ancestor d0b31ae9914687567c2ce8d9f84e06c255f13ccf HEAD` exited 0.
- Compose project: `codexify_account_import_ui_probe_20260923`; inputs: `docker-compose.yml`, `docker-compose.whooshd-smoke.yml`, `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml`. The retained PostgreSQL volume is `codexify_account_import_ui_probe_20260923_pg_data`; the retained Redis container is `codexify_account_import_ui_probe_20260923-redis-1`, with Redis 7.4.11, run ID `1769599ee62b00835b150735e04d315af9a0ca5c`, and its existing anonymous `/data` volume. Database Alembic revision: `a8d4c2f6b1e9`.
- The resolved vector backend is Chroma, path `/app/.chroma`, collection `codexify_vault_supported`. Both backend and chat-embedding worker bind the host path `/Volumes/Dev_SSD/Codexify-main/.chroma` to `/app/.chroma`. This vector directory is a repository-host bind, rather than a Compose-project-specific volume; unrelated local vectors were present. Exact imported message IDs, source conversation IDs, queue payloads, and worker receipts establish attribution of the two imported hits, but this run does not prove vector-store isolation between local Compose projects.
- The resolved persistent consumer is `worker-chat-embed`. `embedding-backfill` appears only when the `backfill` Compose profile is included and is a separate one-shot service. Only `db`, `redis`, and `backend` were reopened initially. `worker-chat-embed` was started after queue capture. The isolated `worker-account-import`, `worker-chat`, model/provider workers, and `embedding-backfill` were not started.

## Canonical source and completed-job diagnostics

Read-only PostgreSQL transactions reconfirmed thread 1 with `chat_threads.user_id=local`, Project 2 (`Imports`) with `projects.user_id=local`, `origin_system=openai`, and `source_thread_id=axis-import-materialization-20260923-01`. The source has exactly the two previously imported messages; no message body was printed.

| Message | Role | Source message ID | Before consumer: `embedding_status` | `embedding_error` | `embedding_queued_at` | `embedding_started_at` / `embedding_completed_at` / `embedded_at` |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | user | `axis-import-user-message-20260923-01` | `pending` | null | `2026-09-23T15:45:15.114707+00:00` | all null |
| 2 | assistant | `axis-import-assistant-message-20260923-01` | `pending` | null | `2026-09-23T15:45:15.114707+00:00` | all null |

Job `788e5d0b-0aab-4df9-8772-39a0907b6eec` remained `completed`, owner `local`, with 1 imported thread, 2 imported messages, and 0 failures; its completion time remained `2026-09-23T15:45:15.183967+00:00`. Its `checkpoint.source_summary` reports 1 discovered/accepted conversation, 0 skipped/failed, and `conversation_transactions_committed=true`. The durable job/checkpoint has **no embedding-mode, candidate, enqueued, deferred, or embedding-failure fields**; its checkpoint keys are `canonical_duplicate_count`, `conversation_ids`, `media_paths`, and `source_summary`. The import completion receipt therefore does not establish embedding completion or even embedding handoff. The importer defines embedding diagnostic counters, but those are not persisted in this job's checkpoint.

## Derived-work handoff and normal consumer

Before starting `worker-chat-embed`, non-destructive Redis `LLEN` returned 2 for `codexify:queue:chat-import-embed` and 0 for `codexify:queue:chat-embed`. Bounded `LRANGE 0 9`, projected to structural fields without content, found two `chat_import_embed` tasks: `(message_id, thread_id)=(2,1)` and `(1,1)`. Each carried `user_id=local` in `meta`, the expected source conversation/message IDs, and `source=origin=chatgpt_import`. Both task `created_at` values were `2026-09-23T17:24:31Z`, about 99 minutes after import completion. No ordinary chat-embed task existed.

The current code and logs explain the delay and origin:

1. `guardian/workers/account_import_worker.py` passes `embedding_mode="defer"` to `import_openai_export_conversations()`. `backend/rag/openai_export_conversation_import.py` passes that mode to `ingest_chatgpt_conversation_records()`.
2. `_ingest_canonical_messages()` writes canonical messages and initial `pending`/`embedding_queued_at` metadata. Its `should_queue_embedding` condition is false for `defer`, so it adds no `pending_embed_items`. The resulting importer branch does not call `_process_chatgpt_embedding_batches()`. In this path, `embedding_queued_at` is import metadata and does **not** by itself prove a Redis task existed at import time.
3. The accepted later handoff is Guardian's backend startup sweep: `guardian/guardian_api.py` schedules `_run_chatgpt_import_startup_sweep()`, which calls `retry_chatgpt_import_embeddings(user_id=local, limit=128)`. That function scans same-user imported messages in `pending`/`failed` state and calls the `chat_import_embed` enqueue path. A bounded backend log at `17:24:31Z` reports 2 candidates, 2 queued, 0 failed. The exact queue task timestamps agree. This was a normal startup action from the preceding retained-runtime reopening, not a manual retry in this task.
4. `guardian/workers/chat_embedding_worker.py` polls the import queue before the ordinary chat-embed queue, loads the canonical message, writes through `VectorStore.add_texts()`, and updates the message embedding lifecycle. It does not scan PostgreSQL to manufacture work while idle. `guardian/workers/embedding_backfill_worker.py` has a separate database/vector scan, but its opt-in one-shot service was not run.

Thus the account-import worker itself does not enqueue import embeddings. A completed canonical import can remain `pending` until a later backend startup sweep schedules work and a persistent consumer processes it. In the observed retained runtime, that natural sweep did schedule both messages; permanent pending state was **not** observed. A completed import job alone has no guarantee of immediate semantic readiness.

The normal consumer container started at `2026-09-23T17:25:45.498078887Z`. Its bounded logs report successful embedding of message 1 at `17:25:49.403Z` and message 2 at `17:25:49.654Z`, with no corresponding failure. Both queue depths became 0. Repeating the exact read-only message query showed both `embedding_status=ready`, null `embedding_error`, and completed timestamps `17:25:49.397349Z` and `17:25:49.648221Z`, respectively. `embedded_at` remained null; lifecycle completion was recorded in `extra_meta.embedding_completed_at`.

## Vector search and cross-project broker selection

The live `guardian.vector.store.VectorStore` was opened with the resolved Chroma runtime and queried as `user_id=local`, `k=10`, using: “What was the assistant sentinel from the CODEXIFY imported materialization probe?” No text was added by this query. It returned 10 hits. Imported message 2 ranked first (score `0.5521582663`) and message 1 ranked second (score `0.4404861331`); both had `thread_id=1`, `user_id=local`, `namespace=thread:1`, and the exact imported `source_thread_id`. An in-memory SHA-256 comparison of hit 1's text to the known synthetic assistant marker returned true; no retrieved text or digest was printed. Other hits came from the shared local vector corpus and are not used as proof of imported-message identity.

Canonical Project lookup found the existing `General` Project 1 owned by `local`; its `system_role` was null in this retained database, so the observed identity is the existing named compatibility fallback rather than a proven durable `general` role. The normal `POST /api/chat/threads` route created exactly one native, empty probe thread: ID 2, title `Axis Imported Recall Probe`, owner `local`, `project_id=1`, `origin_system=codexify`, message count 0. Imported thread 1 remains in Project 2 (`Imports`), also owned by `local`.

`ContextBroker.assemble()` was called directly with the real Postgres chat store, configured vector store, and runtime retrieval policy. The query above, probe thread 2, `user_id=local`, `project_id=1`, and `depth_mode=normal` were held constant:

| Source mode | Effective trace source/depth | Semantic selection | Widen reason | Imported selection |
| --- | --- | --- | --- | --- |
| `personal_knowledge` | `personal_knowledge` / `normal`; active thread 2, Project 1; retrieval executed | 2 hits, both `candidate_thread_semantic`: message 1 rank 1 (`0.4404861331`), message 2 rank 2 (`0.5521582663`); both thread 1, source conversation `axis-import-materialization-20260923-01`, owner `local` | `explicit_personal_knowledge` | Yes, including assistant message 2 |
| `project` | `project` / `normal`; active thread 2, Project 1; retrieval executed | 0 semantic hits; absence reason `retrieval_no_candidates` | `none` | No |

The broker's trust/policy ordering put message 1 before message 2 despite the latter's higher raw vector score; both were selected. Probe history and memory hit counts were 0 in both calls. Since Project 1 differs from imported Project 2 and both canonical owners are `local`, the selected imported evidence entered through governed same-user Personal Knowledge widening, not same-thread history or ordinary same-Project retrieval. Project mode's exclusion is the negative scope control.

## Validation, invariants, and limits

| Command or check | Result | Evidence posture |
| --- | --- | --- |
| `.venv/bin/python -m pytest -v tests/migration/test_openai_export_conversation_import.py` | 21/21 passed | `proven-test` |
| `.venv/bin/python -m pytest -v tests/core/test_context_broker_source_mode.py tests/core/test_context_broker_depth.py tests/core/test_retrieval_user_isolation_and_widening.py tests/context/test_retrieval_scope_boundaries.py` | 53/53 passed | `proven-test` |
| `.venv/bin/python -m pytest -v tests/routes/test_chat_source_mode.py` | 8 passed, 10 failed: the failing cases expected HTTP 200 and received 503, reproducing the previously reported environment-specific route-test failure | `proven-test` only for the passing cases; failed route guard is separate from this live broker proof |
| `docker compose -p codexify_account_import_ui_probe_20260923 -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f /private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml --profile backfill config --services \| rg 'chat.*embed\|embedding.*backfill'` | Located `worker-chat-embed` and `embedding-backfill` | Configuration discovery, not runtime proof |
| `redis-cli LLEN codexify:queue:chat-import-embed` / `redis-cli LLEN codexify:queue:chat-embed`, executed in the retained Redis container | 2/0 before consumer, 0/0 after; bounded `LRANGE` identified messages 1 and 2 | `proven-live-runtime` queue observation |
| Read-only PostgreSQL queries, worker logs, `VectorStore.search()`, and both `ContextBroker.assemble()` calls described above | Canonical identity, worker transition, vector hits, positive selection, and negative control passed | `proven-live-runtime` for this bounded runtime |

Only this proof artifact is a repository write. Imported message bodies, source IDs, thread/Project ownership, and the completed import job remained unchanged; the authorized normal worker changed only embedding lifecycle metadata and derived vector state. No manual embedding enqueue, retry invocation, manual backfill, policy edit, UMS operation, completion request, model/provider call, private-preview mutation, or release-claim change occurred. The route-test 503 failures were not repaired within this diagnostic task. After observation, `worker-chat-embed`, backend, Redis, and PostgreSQL were stopped within the isolated Compose project; their retained containers and volumes were not removed. The shared host Chroma bind and a startup sweep separated from import completion limit claims about timing and isolation.

**ADR impact:** No ADR impact. ADR-004's backend-owned retrieval control plane, ADR-005/ADR-081 account and Project authority, ADR-060's local same-user retrieval distinction, ADR-067's derived-vector authority boundary, and ADR-076's built-in Project role boundary remain unchanged. `docs/architecture/00-current-state.md` and release claims remain unchanged. **Documentation follow-through:** this proof artifact only.

**Next prerequisite:** Prove the selected imported semantic evidence is injected into the provider-ready completion context and that a new Guardian thread can answer using it under Personal Knowledge + normal depth.
