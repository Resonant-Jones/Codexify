# Existing Instance Upgrade Proof

Artifact date/time: 2026-04-04, run window 15:40-15:45 UTC
Branch / HEAD: `main` @ `780e9b7efc92c0c8d6ddb8258d23b4f2ef5fbc73`

## Scope

Status: PASS

This document covers the existing-instance upgrade class only.

It does not repeat the clean-start migration proof. That proof is in
[`2026-04-04-migration-upgrade-proof.md`](./2026-04-04-migration-upgrade-proof.md).

Upgrade class tested:

- Synthetic pre-upgrade fixture on the recent migration floor `d4b7f1a9c3e2`
- Not a real archived snapshot
- Not a broad historical upgrade sweep

## Environment

Status: PASS

Supported runtime path used:

- local Docker Compose
- Postgres
- Redis
- Neo4j
- backend and workers

Relevant runtime observations:

- backend started under the supported beta profile
- `persona_profiles` router remained quarantined under the supported profile
- schema consistency checks ran during backend startup without error

## Pre-upgrade Snapshot Definition

Status: PASS

The pre-upgrade database was created by:

1. Resetting the stack with `docker compose down -v`
2. Bringing up `db`, `redis`, and `neo4j`
3. Initializing the database to the older floor with:

```sh
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini upgrade d4b7f1a9c3e2
```

That floor is the recent mergepoint before the current HEAD upgrade.

The database stamp at that point was:

```text
d4b7f1a9c3e2 (head) (mergepoint)
```

Fixture seed state on that floor was created through the supported API path:

- `GET /health` returned `200`
- `GET /health/chat` returned `200`
- `GET /api/health/llm` returned `200`
- `POST /api/chat/threads` returned `200`
- created `thread_id=1`
- persisted `thread_config` with `providerId=local`, `modelId=qwen3.5:9b`, `inferenceMode=fast`, `retrievalSource=project`, `personaId=null`
- `POST /api/chat/1/messages` returned `200`
- persisted user message `message_id=1`
- `POST /api/chat/1/complete` returned `200`
- task acceptance was `accepted`
- assistant message persisted as `message_id=2`
- assistant content was `hello`
- `POST /api/media/upload/document` returned `200`
- uploaded document `id=93503eff-2869-4f19-8c5c-dedd61c484b2`
- document embedding reached `ready`
- `GET /api/chat/threads?limit=20&user_id=existing-instance-upgrade-fixture-20260404-oldfloor` found the thread and returned the same `thread_config`
- `GET /api/chat/1/profile` returned the default profile payload with `profiles_count=6`

Observed pre-upgrade output highlights:

- `completion_accept` was `accepted`
- `messages_final` reported `assistant_count=1`
- `documents_final` reported `embedding_status=ready`

## Exact Commands

Status: PASS

```sh
docker compose down -v
docker compose up -d db redis neo4j
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini upgrade d4b7f1a9c3e2
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
docker compose up -d model-prep graph-init backend worker-chat worker-document-embed worker-chat-embed worker-warmup
# seed fixture via docker compose exec -T backend python3 <<'PY' ... inline API probe ...
docker compose stop backend worker-chat worker-document-embed worker-chat-embed worker-warmup
docker compose run --rm migrator
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup
# verify upgraded runtime via docker compose exec -T backend python3 <<'PY' ... inline API probe ...
```

## Upgrade Execution

Status: PASS

The upgrade run was a supported migrator invocation on the populated older-floor database:

```sh
docker compose run --rm migrator
```

Observed output:

- migrator completed successfully
- seed defaults ran successfully after migration
- no manual revision stamping was required
- no bootstrap workaround was required
- no missing revision error occurred

Post-upgrade revision verification:

```sh
docker compose run --rm --entrypoint python migrator -m alembic -c /app/backend/alembic.ini current
```

Observed current revisions:

```text
d4b7f1a9c3e2 (head) (mergepoint)
b7c8d9e0f1a2 (head)
```

That is the current HEAD state after the upgrade run.

## Post-upgrade Runtime Checks

Status: PASS

Runtime restart:

- `docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup`

Startup health:

- `docker compose ps` showed backend healthy
- `docker compose ps` showed db healthy
- `docker compose ps` showed neo4j healthy
- `docker compose ps` showed redis healthy
- workers came up cleanly
- backend logs included `Verifying schema consistency...`
- backend logs included `Guardian API ready`

Runtime health probes after restart:

- `GET /health` returned `200`
- `GET /health/chat` returned `200`
- `GET /api/health/llm` returned `200`

Unsupported/support-boundary check:

- `GET /api/persona-profiles` returned `404`
- this is consistent with the supported-profile quarantine boundary and is not treated as a runtime failure

## Thread / Config Compatibility

Status: PASS

Pre-existing thread row loaded after upgrade:

- `GET /api/chat/threads?limit=20&user_id=existing-instance-upgrade-fixture-20260404-oldfloor` matched `thread_id=1`
- returned the same `thread_config` snapshot
- `GET /api/chat/1/profile` returned the default profile payload and `profiles_count=6`

Observed thread config readback:

- `providerId=local`
- `modelId=qwen3.5:9b`
- `inferenceMode=fast`
- `retrievalSource=project`
- `personaId=null`

## Completion Persistence After Upgrade

Status: PASS

Post-upgrade write path on the same upgraded thread:

- `POST /api/chat/1/messages` returned `200`
- persisted user message `message_id=3`
- `POST /api/chat/1/complete` returned `200`
- acceptance was `accepted`
- task id was `dc2cf968-d775-4549-8d9f-3036e4d4ba8a`
- `GET /api/chat/1/messages?limit=20` eventually reported `assistant_count=2`
- newest assistant message was `message_id=4`

Observed persisted assistant content:

- visible content stored for `message_id=4` included `upgraded`
- the stored content also included a stray `</think>` token in the visible text
- persistence itself succeeded; the assistant row was present after completion

## Retrieval After Upgrade

Status: PASS

The pre-upgrade document row survived the upgrade and remained ready:

- `GET /api/media/documents?thread_id=1&limit=5`
- matched the seeded document `id=93503eff-2869-4f19-8c5c-dedd61c484b2`
- `embedding_status=ready`

Supported retrieval proof after upgrade:

- `GET /api/health/retrieval?q=existing-instance-upgrade-proof-20260404-oldfloor-0f8df0e0e6c34c26a2deebc4d4b2f3dc`
- returned `ok=true`
- returned `proof_capable=true`
- returned `same_runtime_as_worker=true`
- returned `backend_store_source=shared`
- the seeded document was the top retrieval match

Observed retrieval body highlights:

- `backend_search_runtime.backend=chroma`
- `backend_search_runtime.collection=codexify_vault_supported`
- top match was the seeded document text containing the sentinel string

## Limitations

Status: PASS

This proof is intentionally narrow:

- it is a synthetic fixture, not an archived production snapshot
- it proves upgrade from the recent floor `d4b7f1a9c3e2` to current HEAD
- it does not prove older historical upgrade classes from every archived schema state
- `GET /api/persona-profiles` remains quarantined in the supported profile and returned `404`

## Verdict

Status: PASS

Current HEAD can upgrade an existing populated database from the recent migration floor `d4b7f1a9c3e2` on the supported local Docker Compose path without missing-revision drift, startup fallout, or loss of core-loop behavior.
