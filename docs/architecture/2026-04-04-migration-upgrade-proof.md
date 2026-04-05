# Migration / Upgrade Proof: Clean-Start on Current HEAD

**Artifact window:** 2026-04-04T05:31:47Z to 2026-04-04T05:42:02Z  
**Branch:** `main`  
**HEAD commit:** `65520918483e194da808115d94ebde9078a42886`  
**Runtime path:** supported local Docker Compose stack with `db`, `redis`, `neo4j`, `backend`, `worker-chat`, `worker-document-embed`, `worker-chat-embed`, and `worker-warmup`  
**Proof class:** clean-start migration proof only  
**Existing-instance upgrade:** not run

## 1. Scope

This artifact proves the current `HEAD` can bootstrap from a clean database state on the supported local Docker Compose path, then serve the migrated runtime correctly.

It covers:

- clean-start Alembic migration on an empty Postgres volume
- backend and worker startup after migration
- `chat_threads.thread_config` persistence and readback
- thread profile surface behavior while `persona_profiles` remains quarantined in supported profile
- chat completion acceptance and assistant persistence
- document upload, embedding readiness, and supported retrieval via `GET /api/health/retrieval?q=...`

It does **not** prove:

- upgrade from an older live database snapshot
- any fallback or workaround for a broken migration chain, because none was required here
- that the dedicated persona-profile API route is part of the supported beta surface, because it is still quarantined

## 2. Environment

| Item | Value |
|---|---|
| Artifact date | 2026-04-04 |
| Capture window | 2026-04-04T05:31:47Z -> 2026-04-04T05:42:02Z |
| Branch | `main` |
| HEAD | `65520918483e194da808115d94ebde9078a42886` |
| Compose runtime | local Docker Compose |
| Fresh-state target | Postgres volume `pg_data` removed via `docker compose down -v` |
| Supported retrieval surface | `GET /api/health/retrieval?q=...` |

Observed steady-state service status after startup:

```text
codexify-backend-1                 Up (healthy)
codexify-db-1                      Up (healthy)
codexify-neo4j-1                   Up (healthy)
codexify-redis-1                   Up (healthy)
codexify-worker-chat-1             Up
codexify-worker-chat-embed-1       Up
codexify-worker-document-embed-1   Up
codexify-worker-warmup-1           Up
```

`graph-init`, `migrator`, and `model-prep` exited `0` during startup.

The running backend advertised the supported local model as `qwen3.5:9b` in health surfaces. The completion request below explicitly passed `qwen3.5:0.8b`, and the persisted assistant metadata records that explicit selection.

## 3. Exact Commands

### Clean-start teardown

```bash
docker compose down -v
```

Observed result:

- database and graph volumes were removed
- Docker reported `hf_cache` as still in use, but that cache is not part of the schema proof

### Fresh dependency bring-up

```bash
docker compose up -d db redis neo4j
```

### Migration command

```bash
docker compose run --rm migrator
```

### Runtime startup command

```bash
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup
```

### Live probe command 1

```bash
docker compose exec -T backend python3 <<'PY'
# health: /health, /health/chat, /api/health/llm
# quarantine check: /api/persona-profiles
# thread proof: POST /api/chat/threads, GET /api/chat/threads, GET /api/chat/{thread_id}/profile
# chat proof: POST /api/chat/{thread_id}/messages, POST /api/chat/{thread_id}/complete
# assistant persistence check: GET /api/chat/{thread_id}/messages?limit=20
PY
```

### Live probe command 2

```bash
docker compose exec -T backend python3 <<'PY'
# upload proof: POST /api/media/upload/document
# embed proof: GET /api/media/documents?thread_id=1&limit=5 until embedding_status=ready
# retrieval proof: GET /api/health/retrieval?q=migration-upgrade-proof-20260404-...
PY
```

## 4. Observed Migration Output

`docker compose run --rm migrator` completed without error and applied the migration chain on the fresh database.

Key observed output:

```text
[Migrator] Using Alembic config: /app/backend/alembic.ini
[docker] run: /opt/python/bin/python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads
INFO  [alembic.runtime.migration] Running upgrade ... -> b7c8d9e0f1a2, add persona profiles table for Persona Studio first-wave runtime fields
[Migrator] Running seed defaults
[Seed] Seeding complete.
[Migrator] Done
```

Backend startup then verified schema consistency and reported the applied revision:

```text
[Backend] Verifying required tables + alembic_version
[Backend] OK: alembic_version=d4b7f1a9c3e2
[startup] Guardian API ready
```

No missing-revision, stale-head, or bootstrapping workaround was needed.

## 5. Observed Runtime Results After Migration

### Health

The health surfaces were healthy on the migrated runtime:

- `GET /health` returned `200` with `status: ok`
- `GET /health/chat` returned `200` with `status: healthy`, `redis: ok`, `worker_heartbeat_status: fresh`, and `queue.depth: 0`
- `GET /api/health/llm` returned `200` with `status: online`, `provider: local`, and the supported local model advertised as `qwen3.5:9b`

### Persona-profile surface

`GET /api/persona-profiles` returned `404 Not Found`:

```json
{"detail":"Not Found"}
```

That is expected in the supported profile because the dedicated persona-profile router is still quarantined.

`GET /api/chat/1/profile` still returned a fallback thread profile response and did not error:

```json
{"profile":{"mode":"cloud","name":"Default","profile_id":"default","source":"default","system_prompt_blocks":{}},"profiles_count":6,"status_code":200}
```

### `chat_threads.thread_config`

The created thread persisted a normalized `thread_config` and remained readable through the thread list surface.

Observed create response:

```json
{"project_id":1,"status_code":200,"thread_config":{"inferenceMode":"fast","modelId":"qwen3.5:9b","personaId":null,"providerId":"local","retrievalSource":"project"},"thread_id":1}
```

Observed list response for the same thread:

```json
{"active_profile_id":null,"match_found":true,"project_id":1,"status_code":200,"thread_config":{"inferenceMode":"fast","modelId":"qwen3.5:9b","personaId":null,"providerId":"local","retrievalSource":"project"}}
```

Important nuance:

- the create payload requested `qwen3.5:0.8b`
- the persisted row normalized to the supported runtime model `qwen3.5:9b`
- the completion request below used explicit provider/model overrides, so this proof establishes persistence and compatibility of a `thread_config`-bearing row, not precedence against explicit overrides

### Chat completion

The completion request was accepted:

```json
{"acceptance_status":"accepted","acceptance_warnings":[],"depth_mode":"normal","effective_depth_mode":"light","ok":true,"requested_depth_mode":"light","source_mode":"project","status_code":200,"task_id":"325a07e4-a843-44b8-b405-a945eab5f936","thread_id":1,"messages_url":"/api/chat/1/messages","trace_url":"/api/chat/debug/rag-trace/1/latest","turn_id":"3758a271-964e-4201-904d-3dd02352e1fc"}
```

The worker later persisted the assistant turn:

```text
[chat-worker] assistant_message_persisted thread_id=1 turn_id=3758a271-964e-4201-904d-3dd02352e1fc task_id=325a07e4-a843-44b8-b405-a945eab5f936 assistant_message_id=2
[task] completed type=chat_completion id=325a07e4-a843-44b8-b405-a945eab5f936 run_id=b4c2f92bfb7e4abfa51be7541d15628a thread=1 turn_id=3758a271-964e-4201-904d-3dd02352e1fc message_id=2
```

Direct message fetch after completion:

```json
{"assistant_count":1,"messages":[{"content":"Reply with exactly one word: hello","id":1,"metadata":null,"role":"user"},{"content":"hello","id":2,"metadata":{"selection_source":"explicit","final_model":"qwen3.5:0.8b","resolved_provider":"local","turn_id":"3758a271-964e-4201-904d-3dd02352e1fc"},"role":"assistant"}],"status_code":200,"total":2}
```

### Document upload and embed readiness

Upload succeeded:

```json
{"embedding_status":"pending","filename":"migration-upgrade-proof-20260404-6d9af3c5b7c24c9c9c1a4cf7fb4a1b21.txt","id":"c758795d-9997-4ee3-abce-2ddcd0775447","status_code":200,"thread_id":1}
```

Embedding transitioned to ready on the second poll:

```json
{"attempt":2,"count":1,"document":{"embedding_completed_at":"2026-04-04T05:41:50.204825+00:00","embedding_started_at":"2026-04-04T05:41:49.646241+00:00","embedding_status":"ready","filename":"migration-upgrade-proof-20260404-6d9af3c5b7c24c9c9c1a4cf7fb4a1b21.txt","id":"c758795d-9997-4ee3-abce-2ddcd0775447"},"status_code":200}
```

Supported retrieval proof passed:

```json
{"first_match":{"filename":"migration-upgrade-proof-20260404-6d9af3c5b7c24c9c9c1a4cf7fb4a1b21.txt","namespace":"thread:1","text":"migration upgrade proof sentinel\nmigration-upgrade-proof-20260404-6d9af3c5b7c24c9c9c1a4cf7fb4a1b21\n"},"match_count":5,"ok":true,"proof_capable":true,"same_runtime_as_worker":true,"status":"ready","status_code":200}
```

## 6. Drift / Limitations Observed

### Probe-path limitation

The first all-in-one live probe command aborted with:

```text
requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

That did **not** correspond to a backend crash:

```text
docker inspect codexify-backend-1 -> 0 running 0
```

I resumed with a focused upload/retrieval command and completed the remaining proof from the same healthy runtime.

### Clean-start scope boundary

This artifact proves a clean-start migration from a fresh database volume.

It does **not** prove upgrade-from-existing-instance behavior on a previously populated database snapshot.

### Persona-profile scope boundary

The dedicated persona-profile API route is still quarantined under the supported profile, so the proof does not claim a live `/api/persona-profiles` release surface.

### Thread-config scope boundary

This proof shows that a thread carrying `thread_config` survives create/list/profile/completion flows on the migrated runtime.

It does **not** isolate precedence between `thread_config` values and explicit completion overrides, because the completion request in this run supplied explicit provider/model values.

## 7. Verdict

| Case | Status | Notes |
|---|---|---|
| Clean-start migration from empty DB | PASS | `docker compose run --rm migrator` completed cleanly |
| Backend and workers start after migration | PASS | backend healthy; workers up; init jobs exited `0` |
| `chat_threads.thread_config` persistence | PASS | normalized thread row readable via create/list |
| Persona-profile dedicated API route | LIMITATION | still quarantined in supported profile |
| Chat completion persistence | PASS | assistant `hello` persisted as message `id=2` |
| Upload -> embed-ready -> supported retrieval | PASS | document became `ready`; `/api/health/retrieval?q=...` matched sentinel |
| Existing-instance upgrade | NOT PROVEN | not run |

Bottom line:

- current `HEAD` can bootstrap honestly from a clean database and run the supported local Docker Compose path after migration
- current `HEAD` still lacks a proof for upgrading an existing live instance from an older snapshot
