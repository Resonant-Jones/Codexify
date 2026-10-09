# Live Synthetic Account Import and Embedding Proof

**Result:** the isolated synthetic import-to-embedding path passed on the source revision below. Natural retrieval through an ordinary chat request and provider-context inclusion remain unproven. This proof does not change the release HOLD or expand Beta support.

## Source and environment

- Source: `6678850ee633b0c886394bf85618cca906c11324` (`codex/synthetic-account-import-recall-qualification`), the required Goal04 commit. The worktree was clean before this proof artifact was created.
- Runtime: a task-owned Compose project, `codexify_live_import_embedding_g05_20261009`, using a fresh Postgres database migrated to `17b23052da6a`, a non-persistent isolated Redis, and task-owned appdata and Chroma volumes. No existing Compose project or volume was reset.
- Profile: `v1-local-core-web-mcp`; local auth; `CODEXIFY_MULTI_USER_ENABLED=false`; `DEBUG=false`; `DEV_MODE=false`; explicit identity directory `/app/data/identity`.
- Embedding: backend `chroma`, collection `goal05_synthetic_import_20261009`, shared path `/app/.chroma`; local model `/models/bge-large-en-v1.5` mounted read-only. The embedding worker startup log identified this model and `sentence_transformer` backend. The model mount was read-only and no provider fallback was used for embedding.
- API image: built from this worktree and tagged `codexify-live-import-g05:bfd3da6b3`.
- Python: existing `/Volumes/Dev_SSD/Codexify-main/.venv`; no packages were installed or changed.

## Synthetic fixture and procedure

The fixture existed only in the isolated execution. It contained two modern sharded `.dat` JSON conversations with the same external conversation identifier, one per authenticated synthetic account. Each conversation carried a distinct `workspace_id`, untrusted export `user_id`, and separate user/assistant message identifiers. Their relative paths were:

- `Workspace-A/conversations__goal05.part-0001/file_0000000000000001.dat`
- `Workspace-B/conversations__goal05.part-0002/file_0000000000000001.dat`

The assistant messages contained unique sentinels `NOVA-6A96C077` (A) and `QUASAR-D59D804B` (B). No user archive was accessed. This run did not include attachment bytes or opaque `.dat` payloads.

For each account, the driver created an isolated canonical `users` row and account-purpose session, then used the ordinary HTTP endpoints `POST /api/imports/openai-account`, `POST /{job_id}/files`, `POST /{job_id}/commit`, and `GET /{job_id}`. Real `worker-account-import` and `worker-chat-embed` containers consumed the isolated Redis queues. The verifier read canonical Postgres rows and queried the shared Chroma collection through `VectorStore.search(..., user_id=...)`; it did not write conversation rows, embedding status, or vector records directly.

## Validation

Commands, run from this worktree using the existing virtual environment:

```text
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/rag/test_openai_export_account_import.py
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/services/test_account_import_embedding_handoff.py
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/workers/test_account_import_worker.py
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python /private/tmp/codexify-live-import-embedding-20261009/run_db_suite.py
```

The final command supplied the temporary isolated `TEST_DATABASE_URL` to the existing integration owner, `tests/migration/test_openai_export_conversation_import.py`.

The isolated Compose services were started from the frozen worktree with:

```text
docker compose --project-name codexify_live_import_embedding_g05_20261009 --env-file /private/tmp/codexify-live-import-embedding-20261009/runtime.env -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f /private/tmp/codexify-live-import-embedding-20261009/override.yml up -d --no-deps --no-build backend
docker compose --project-name codexify_live_import_embedding_g05_20261009 --env-file /private/tmp/codexify-live-import-embedding-20261009/runtime.env -f docker-compose.yml -f docker-compose.whooshd-smoke.yml -f /private/tmp/codexify-live-import-embedding-20261009/override.yml up -d --no-deps --no-build worker-account-import worker-chat-embed
```

The synthetic HTTP driver ran as `docker exec -i codexify_live_import_embedding_g05_20261009-backend-1 python - < /private/tmp/codexify-live-import-embedding-20261009/live_driver.py`. The credential-bearing runtime file, fixture driver, fixture bytes, and receipt were temporary and were removed after closeout; no private archive or secret was retained.

| Surface | Result | Evidence |
|---|---|---|
| `tests/rag/test_openai_export_account_import.py` | PASS | 37 passed |
| `tests/services/test_account_import_embedding_handoff.py` | PASS | 3 passed |
| `tests/workers/test_account_import_worker.py` | PASS | 13 passed |
| `tests/migration/test_openai_export_conversation_import.py` | PASS | 30 passed against isolated Postgres; 0 skipped (2 warnings) |
| Isolated backend health | PASS | `GET /ping` returned HTTP 200; backend reported healthy |
| Real account-import queue worker | PASS | Started on isolated account-import queue; both jobs completed |
| Real embedding queue worker | PASS | Started on isolated chat-embed queue; log recorded message IDs 20–23 as embedded using the local model |

## Live results

| Account | Canonical owner | Job | Outcome | Canonical lineage |
|---|---|---|---|---|
| A | `goal05-account-a-2e8b217e6b` | `d32a56e9-bbc1-4624-9b07-29e274e7421e` | `completed`, 1 thread / 2 messages | thread 11; messages 20 and 21; both source IDs retained |
| B | `goal05-account-b-2e8b217e6b` | `867975a9-e1b8-4ad9-84fc-f56270724df9` | `completed`, 1 thread / 2 messages | thread 12; messages 22 and 23; both source IDs retained |
| A replay | `goal05-account-a-2e8b217e6b` | `f3f161cc-155f-4f1a-b2f2-bc61a3b6521e` | `completed_with_warnings`; duplicate count 3 | Same A thread and message IDs remained; no extra source thread or message was created |

Both canonical threads used the same external source conversation ID, `goal05-shared-conversation-2e8b217e6b`, while resolving to separate authenticated owners and separate owner-matched projects. Each thread contained the expected user-then-assistant order. Message metadata retained `source_thread_id`, distinct `source_message_id`, `openai_export_source_path`, and turn index. Export `user_id` was not used as the canonical owner. A’s job read under B’s account credential returned HTTP 404.

After the worker handoff, Postgres reported `embedding_status=ready` for all four source messages. The shared Chroma collection contained `chat-import-message:20` and `:21` for A, and `:22` and `:23` for B. Separate account-scoped vector searches returned the matching account’s sentinel; each opposite-account query had zero results containing the foreign sentinel. Search results included `user_id`, `source_thread_id`, `source_message_id`, canonical `thread_id`, and `message_id` metadata. The worker and backend used the same named Chroma volume, path, and collection.

The replay job reported duplicate count 3 while preserving the original canonical IDs and message count. That count is recorded as emitted by the job; the proof does not infer that it means three newly created canonical objects.

## Gate classification

| Gate | Classification | Boundary |
|---|---|---|
| Synthetic sharded workspace import through HTTP staging and queue materialization | PASS | Two modern `.dat` workspace paths completed through the real import worker. Legacy `conversations.json`, `Unassigned`, attachment linkage, and opaque-payload diagnostics were not exercised in this live run. |
| Canonical persistence, order, ownership, and source-message lineage | PASS | Postgres readback showed two ordered messages per account, owner-aligned threads/projects/messages, and retained source metadata. |
| Cross-account import-job isolation | PASS | Account B could not read account A’s job (404). Shared external conversation ID resolved into separately owned canonical threads. |
| Replay deduplication | PASS | Replaying A preserved the same canonical thread/message IDs and row counts. Job-level duplicate count was 3 and status `completed_with_warnings`. |
| Real embedding handoff and readiness | PASS | Both real workers ran; all four Postgres message rows reached `ready`; all four deterministic message IDs were visible in the shared Chroma collection. |
| Account-scoped semantic vector search | PASS | Each account’s sentinel was retrievable for its owner; opposite-account scoped searches returned no foreign sentinel. This proves vector query behavior only. |
| Ordinary chat retrieval, provider-context inclusion, and persisted answer | BLOCKED / not exercised | No ordinary chat request was made. There is no evidence here that selected vector evidence enters provider input or that an assistant answer is persisted. Natural recall remains unqualified. |
| Interrupted live-batch recovery | BLOCKED / not exercised | Focused recovery tests passed, but this live run did not interrupt a worker mid-batch and observe resume behavior. |
| Unsupported-payload diagnostic behavior | BLOCKED / not exercised | The live fixture contained only readable JSON `.dat` files; no unreadable or unsupported payload was submitted. |

## Architecture and limits

This acceptance-only proof aligns with ADR-005 (account boundary), ADR-004 (retrieval policy), ADR-013 (imported conversations do not become personal facts), ADR-069 (Beta runtime boundary), ADR-081 (canonical Project account authority), and ADR-092 (purpose-scoped credentials), plus the Account Export + Restore Contract and current account-import/retrieval contracts. Postgres remained canonical; source metadata remained provenance; vector presence was not treated as provider-context evidence. No implementation semantics, current-state declaration, supported-profile declaration, or release posture changed.

The run establishes import persistence, deduplication, embedding readiness, and account-scoped vector search on this isolated synthetic runtime. It does not establish attachment linkage, legacy/unassigned/opaque format behavior in the live runtime, interrupted live recovery, ordinary-chat retrieval, successful answer generation, or release readiness. A separate isolated natural-recall qualification must capture retrieval selection, provider input, persisted assistant answer, and the cross-account negative control before that gate can pass.
