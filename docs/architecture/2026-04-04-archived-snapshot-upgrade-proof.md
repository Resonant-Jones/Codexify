# Archived Snapshot Upgrade Proof: Synthetic Archived Floor on Current HEAD

Artifact date/time: 2026-04-04T17:58:40Z  
Run window: 2026-04-04T17:43:31Z -> 2026-04-04T17:58:40Z  
Branch: `main`  
HEAD commit: `c4b3e1a6fea986e84a8c8ac2a66bb7b753d978a5`  
Runtime path: supported local Docker Compose stack with `db`, `redis`, `neo4j`, `backend`, `worker-chat`, `worker-document-embed`, `worker-chat-embed`, and `worker-warmup`  
Proof class: archived-snapshot upgrade proof  
Historical upgrade class tested: exported-and-restored synthetic snapshot from archived floor `b5e6c55f0f0c`  
Not tested here: clean-start migration proof, recent-floor synthetic upgrade proof, real archived production copy, or a broad historical sweep

## Scope

Status: PASS

This artifact proves that a preserved older database state, exported from the live archived floor observed in this session, can be restored and upgraded to current `HEAD` on the supported local Docker Compose path without losing core chat/retrieval correctness.

It covers:

- upgrade from an older archived floor to current `HEAD`
- pre-existing thread/message continuity after upgrade
- `chat_threads.thread_config` compatibility and readback after upgrade
- completion persistence on the upgraded thread
- supported retrieval on the upgraded state

It does **not** prove:

- a real archived production copy
- every historical upgrade era
- DB-side document readiness transition from `pending` to `ready` on this archived snapshot
- clean-start migration/bootstrap, which is covered by a separate proof artifact

## Archived Snapshot Source

Status: PASS

The snapshot source was a synthetic fixture created on the archived floor `b5e6c55f0f0c`.

The seed was inserted with SQL-only writes against the live archived-floor schema already confirmed in this session:

```sql
WITH seed_project AS (
  INSERT INTO projects (name, description, icon)
  VALUES ('Archived Snapshot Upgrade Project', 'Synthetic archived snapshot seed project', NULL)
  RETURNING id
), seed_thread AS (
  INSERT INTO chat_threads (user_id, title, summary, project_id, parent_id)
  SELECT 'archived-snapshot-upgrade-fixture-20260404-archivedfloor',
         'Archived Snapshot Upgrade Fixture',
         '',
         id,
         NULL
  FROM seed_project
  RETURNING id, project_id
), seed_message AS (
  INSERT INTO chat_messages (thread_id, role, content)
  SELECT id, 'user', 'Reply with exactly one word: hello'
  FROM seed_thread
  RETURNING id, thread_id
), seed_document AS (
  INSERT INTO uploaded_documents (
    id,
    project_id,
    thread_id,
    user_id,
    filename,
    filesize,
    mime_type,
    src_url,
    parsed_text
  )
  SELECT
    '649fdb90-4628-4dfd-b4ed-f329b8e2b3f2',
    t.project_id,
    t.id,
    'archived-snapshot-upgrade-fixture-20260404-archivedfloor',
    'archived-snapshot-upgrade-proof-20260404-doc-be1ab659545d4b5399dae44eec772fa9.txt',
    115,
    'text/plain',
    '/media/documents/archived-snapshot-upgrade-proof-20260404-doc-be1ab659545d4b5399dae44eec772fa9.txt',
    'archived-snapshot-upgrade-proof-20260404-doc-be1ab659545d4b5399dae44eec772fa9\narchived snapshot retrieval sentinel\n'
  FROM seed_thread AS t
  RETURNING id
)
SELECT
  (SELECT id FROM seed_project) AS project_id,
  (SELECT id FROM seed_thread) AS thread_id,
  (SELECT id FROM seed_message) AS message_id,
  (SELECT id FROM seed_document) AS document_id;
```

Seeded rows and captured IDs:

- `projects.id = 1`
- `chat_threads.id = 1`
- `chat_messages.id = 1`
- `uploaded_documents.id = 649fdb90-4628-4dfd-b4ed-f329b8e2b3f2`

The seeded data contained:

- one project row with required `name`
- one pre-existing thread row referencing that project
- one persisted user message
- one uploaded document row referencing the same project and thread
- no embedding lifecycle columns, because they were not present in this archived-floor schema

Observed verification queries:

- `SELECT * FROM projects ORDER BY id DESC LIMIT 1;`
- `SELECT id, user_id, title, summary, project_id, parent_id, archived_at, created_at, updated_at FROM chat_threads ORDER BY id DESC LIMIT 1;`
- `SELECT id, project_id, thread_id, user_id, filename, filesize, mime_type, src_url, parsed_text, created_at, updated_at, deleted_at FROM uploaded_documents ORDER BY created_at DESC LIMIT 1;`

The snapshot was exported with:

```bash
docker compose exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' > /tmp/codexify-archived-snapshot-b5e6-seeded-20260404.sql
```

That dump was then restored into a fresh database after `docker compose down -v`.

This is an exported-and-restored synthetic snapshot, not a real archived production copy.

## Environment

Status: PASS

Supported runtime path used:

- local Docker Compose
- Postgres
- Redis
- Neo4j
- backend and workers

Observed steady-state service status after startup:

```text
codexify-backend-1                Up (healthy)
codexify-db-1                     Up (healthy)
codexify-neo4j-1                  Up (healthy)
codexify-redis-1                  Up (healthy)
codexify-worker-chat-1            Up
codexify-worker-chat-embed-1      Up
codexify-worker-document-embed-1  Up
codexify-worker-warmup-1          Up
```

Backend startup logs after upgrade reported:

```text
[Backend] OK: alembic_version=d4b7f1a9c3e2
[startup] Guardian API ready
```

The supported-profile quarantine boundary remained in force during startup, including the dedicated persona-profile router.

## Exact Commands

Status: PASS

### Seed archived-floor fixture

```bash
docker compose up -d db redis neo4j
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
WITH seed_project AS (
  INSERT INTO projects (name, description, icon)
  VALUES ('Archived Snapshot Upgrade Project', 'Synthetic archived snapshot seed project', NULL)
  RETURNING id
), seed_thread AS (
  INSERT INTO chat_threads (user_id, title, summary, project_id, parent_id)
  SELECT 'archived-snapshot-upgrade-fixture-20260404-archivedfloor',
         'Archived Snapshot Upgrade Fixture',
         '',
         id,
         NULL
  FROM seed_project
  RETURNING id, project_id
), seed_message AS (
  INSERT INTO chat_messages (thread_id, role, content)
  SELECT id, 'user', 'Reply with exactly one word: hello'
  FROM seed_thread
  RETURNING id, thread_id
), seed_document AS (
  INSERT INTO uploaded_documents (
    id,
    project_id,
    thread_id,
    user_id,
    filename,
    filesize,
    mime_type,
    src_url,
    parsed_text
  )
  SELECT
    '649fdb90-4628-4dfd-b4ed-f329b8e2b3f2',
    t.project_id,
    t.id,
    'archived-snapshot-upgrade-fixture-20260404-archivedfloor',
    'archived-snapshot-upgrade-proof-20260404-doc-be1ab659545d4b5399dae44eec772fa9.txt',
    115,
    'text/plain',
    '/media/documents/archived-snapshot-upgrade-proof-20260404-doc-be1ab659545d4b5399dae44eec772fa9.txt',
    'archived-snapshot-upgrade-proof-20260404-doc-be1ab659545d4b5399dae44eec772fa9\narchived snapshot retrieval sentinel\n'
  FROM seed_thread AS t
  RETURNING id
)
SELECT
  (SELECT id FROM seed_project) AS project_id,
  (SELECT id FROM seed_thread) AS thread_id,
  (SELECT id FROM seed_message) AS message_id,
  (SELECT id FROM seed_document) AS document_id;
SQL
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
SELECT * FROM projects ORDER BY id DESC LIMIT 1;
SELECT id, user_id, title, summary, project_id, parent_id, archived_at, created_at, updated_at FROM chat_threads ORDER BY id DESC LIMIT 1;
SELECT id, project_id, thread_id, user_id, filename, filesize, mime_type, src_url, parsed_text, created_at, updated_at, deleted_at FROM uploaded_documents ORDER BY created_at DESC LIMIT 1;
SQL
docker compose exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' > /tmp/codexify-archived-snapshot-b5e6-seeded-20260404.sql
```

### Restore snapshot and migrate

```bash
docker compose down -v
docker compose up -d db redis neo4j
docker compose exec -T db sh -lc 'until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do sleep 1; done; psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < /tmp/codexify-archived-snapshot-b5e6-seeded-20260404.sql
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
docker compose run --rm migrator
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
docker compose up -d --no-deps backend worker-chat worker-document-embed worker-chat-embed worker-warmup
```

### Post-upgrade probes

```bash
docker compose exec -T backend python3 <<'PY'
# health: /health, /health/chat, /api/health/llm
# thread/config readback: /api/chat/threads?limit=20&user_id=...
# config patch: PATCH /api/chat/threads/1/config
# completion: POST /api/chat/1/complete
# message persistence check: GET /api/chat/1/messages?limit=20
PY
docker compose exec -T backend python3 <<'PY'
# thread/profile readback: /api/chat/1/profile
# document readback: /api/media/documents?thread_id=1&limit=5
# supported retrieval: GET /api/health/retrieval?q=archived-snapshot-upgrade-proof-...
PY
```

## Upgrade Execution

Status: PASS

The restored snapshot reported the older floor before migration:

```text
b5e6c55f0f0c
```

The supported migrator then executed successfully on that populated database:

```text
Running upgrade b5e6c55f0f0c -> d3b3e9f5d5ab, add imprint/persona/system_docs tables
Running upgrade ... -> b0c1d2e3f4a5, add thread_config to chat_threads
Running upgrade ... -> 4f6c8d1a2b3c, add imprint observations and folded state tables
Running upgrade 4f6c8d1a2b3c, b0c1d2e3f4a5 -> d4b7f1a9c3e2, merge heads after imprint observations and thread_config
Running upgrade e9a4c1b8d2f7 -> b7c8d9e0f1a2, add persona profiles table for Persona Studio first-wave runtime fields
Done
```

Observed post-upgrade revision state:

```text
d4b7f1a9c3e2 (head) (mergepoint)
b7c8d9e0f1a2 (head)
```

No missing revision, stale head, or manual revision stamping was required.

## Post-upgrade Runtime Checks

Status: PASS

Runtime restart after migration succeeded with the supported Compose stack:

- backend started cleanly
- `worker-chat` started cleanly
- `worker-document-embed` started cleanly
- `worker-chat-embed` started cleanly
- `worker-warmup` started cleanly

Health probes after restart returned `200`:

- `GET /health`
- `GET /health/chat`
- `GET /api/health/llm`

The supported profile remained quarantined where expected, including the dedicated persona-profile API route.

## Thread / Config Compatibility

Status: PASS

The pre-existing upgraded thread row loaded after migration:

- `GET /api/chat/threads?limit=20&user_id=archived-snapshot-upgrade-fixture-20260404-archivedfloor`
- matched `thread_id=1`
- returned the upgraded `thread_config`

Observed thread config readback:

```json
{"inferenceMode":"fast","modelId":"qwen3.5:9b","personaId":null,"providerId":"local","retrievalSource":"project"}
```

The same thread accepted a config patch after upgrade:

```json
{"ok":true,"thread_config":{"inferenceMode":"fast","modelId":"qwen3.5:9b","personaId":null,"providerId":"local","retrievalSource":"project"},"thread_id":1}
```

`GET /api/chat/1/profile` returned the default profile payload and did not error.

## Completion Persistence After Upgrade

Status: PASS

The upgraded archived thread accepted a new completion request:

```json
{"acceptance_status":"accepted","acceptance_warnings":[],"depth_mode":"normal","effective_depth_mode":"light","ok":true,"requested_depth_mode":"light","source_mode":"project","task_id":"799456c3-c37a-46ee-9ed7-8303f2c50631","thread_id":1,"messages_url":"/api/chat/1/messages","trace_url":"/api/chat/debug/rag-trace/1/latest","turn_id":"fba8b202-96dd-409b-91ec-1ff7c13e9adf"}
```

The first full probe script aborted on its own assertion because it expected an `assistant_count` field that this response shape does not expose. That was a probe bug, not a runtime failure.

The returned message list body still contained the persisted assistant row:

```json
{"id":2,"role":"assistant","content":"hello","thread_id":1}
```

Backend logs also recorded assistant persistence:

```text
[chat-worker] assistant_message_persisted thread_id=1 turn_id=fba8b202-96dd-409b-91ec-1ff7c13e9adf task_id=799456c3-c37a-46ee-9ed7-8303f2c50631 assistant_message_id=2
```

## Retrieval After Upgrade

Status: PASS with a narrow limitation

The upgraded snapshot still exposed the seeded document through the supported document surface:

```json
{"id":"649fdb90-4628-4dfd-b4ed-f329b8e2b3f2","project_id":1,"thread_id":1,"embedding_status":"pending","filename":"archived-snapshot-upgrade-proof-20260404-doc-be1ab659545d4b5399dae44eec772fa9.txt"}
```

Important limitation:

- the DB-side document row still read back as `pending`
- I did **not** prove a fresh post-upgrade transition of that archived snapshot row to `ready`

Supported retrieval on the upgraded state still passed:

```json
{"ok":true,"proof_capable":true,"same_runtime_as_worker":true,"status":"ready","search":{"match_count":5}}
```

The top retrieval match included the seeded sentinel text:

```text
archived-snapshot-upgrade-proof-20260404-doc-be1ab659545d4b5399dae44eec772fa9
archived snapshot retrieval sentinel
```

This proves the supported retrieval lane still works on the upgraded archived snapshot, even though DB-side document readiness on that row remained unproven.

## Limitations

Status: PASS

This proof is intentionally narrow:

- it is a synthetic exported-and-restored snapshot, not a real archived production copy
- it proves one archived-floor schema era only: `b5e6c55f0f0c`
- it does not cover every historical schema era
- document readiness remained `pending` in DB readback after upgrade
- the dedicated persona-profile API route is still quarantined under the supported profile

## Verdict

Status: PASS with limitations

Current `HEAD` can restore and upgrade this synthetic archived-floor snapshot on the supported local Docker Compose path without missing-revision drift or startup fallout.

Core-loop behavior on the upgraded snapshot remained correct:

- the pre-existing thread loaded
- `thread_config` was readable and patchable after upgrade
- a new completion persisted an assistant row
- supported retrieval succeeded on `/api/health/retrieval?q=...`

The remaining open gap is broader historical coverage beyond this synthetic archived-floor fixture, plus DB-side document readiness transition on that row.
