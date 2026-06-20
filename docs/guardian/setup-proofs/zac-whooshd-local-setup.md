# Zac Whoosh'd Local Setup Proof

## Run metadata

| Field | Value |
|---|---|
| Date/time | 2026-06-20T04:02 UTC |
| Machine class | Apple Silicon macOS |
| Repo branch | `main` |
| HEAD | `a971ac175a0bd33dc225791cfef907598d95aa7e` |
| Worktree dirty before setup | No (clean) |
| Local env file modified | `.env` (local-only, not committed) |

## Env keys configured

The following keys were set or changed in `.env`:

- `GUARDIAN_API_KEY` (secret, not shown)
- `CODEXIFY_LOCAL_ONLY_MODE=true`
- `ALLOW_CLOUD_PROVIDERS=false`
- `LLM_PROVIDER=local`
- `CODEXIFY_CONFIG_SOURCE=core`
- `AI_BACKEND=local` (legacy compat only; `LLM_PROVIDER` is canonical)
- `LOCAL_RUNTIME_PRESET=whooshd-mlx`
- `LOCAL_BASE_URL=http://host.docker.internal:8000/v1`
- `LOCAL_DOCKER_FALLBACK_BASE_URL=http://host.docker.internal:8000/v1`
- `LOCAL_PROVIDER_DISPLAY_NAME=Whoosh'd`
- `LOCAL_PROVIDER_VENDOR=whooshd`
- `LOCAL_CHAT_MODEL=mlx-community/gemma-4-12B-it-qat-4bit`
- `LOCAL_LLM_MODEL=mlx-community/gemma-4-12B-it-qat-4bit`
- `LLM_MODEL=mlx-community/gemma-4-12B-it-qat-4bit`
- `LOCAL_API_KEY=local`
- `LOCAL_COMPAT_FIRST=1`
- `LOCAL_ENABLE_OLLAMA_GENERATE_FALLBACK=0`
- `VAULTNODE_BASE_URL=http://host.docker.internal:8000`
- `VAULTNODE_HEALTH_ENDPOINTS=/health,/health/runtime,/ready,/v1/models,/api/tags`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (defaults)
- `NEO4J_USER`, `NEO4J_PASS` (secret, not shown)
- `EMBED_PROVIDER=local`
- `CODEXIFY_EMBEDDINGS_BACKEND=local`
- `LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5`
- `OPENAI_API_KEY=local` (SDK init placeholder)

## Whoosh'd inventory proof

### Host-side endpoint

```
GET http://127.0.0.1:8000/v1/models
```

Response:

```json
{
  "object": "list",
  "data": [
    {
      "id": "mlx-community/gemma-4-12B-it-qat-4bit",
      "object": "model",
      "created": 1700000000,
      "owned_by": "whooshd"
    }
  ]
}
```

### Whoosh'd health

```json
{
  "ok": true,
  "runner": "whooshd",
  "version": "0.1.0rc1",
  "status": "ready",
  "model_lifecycle": "ready",
  "memory": { "pressure": "normal", "total_gb": 32.0 }
}
```

### Docker-visible base URL

`http://host.docker.internal:8000/v1`

### Selected model id from live inventory

`mlx-community/gemma-4-12B-it-qat-4bit`

## Docker Compose validation

```
docker compose config >/tmp/codexify-compose-config.txt
```

Result: exit 0, config valid.

## Docker Compose services started

| Service | Status |
|---|---|
| db (postgres:15) | healthy |
| redis (redis:7-alpine) | healthy |
| neo4j (neo4j:5) | healthy |
| migrator | completed successfully |
| model-prep | completed successfully |
| graph-init | completed successfully |
| backend | healthy |
| worker-chat | running |
| worker-chat-embed | running |
| worker-document-embed | running |
| worker-warmup | running |

Note: The `neo4j_data` volume was recreated during setup because the prior volume's password did not match the new `.env`. Neo4j graph writes remain default-off (`CODEXIFY_ENABLE_GRAPH_WRITES=false`).

## Health endpoint results

### GET /health

```json
{
  "status": "ok",
  "service": "core",
  "details": {
    "supported_profile": {
      "name": "v1-local-core-web-mcp",
      "valid": true,
      "mismatches": [],
      "selected_provider": "local",
      "selected_provider_supported": true,
      "release_hold": true
    }
  }
}
```

Result: **ok**. Supported profile valid, provider `local`, no mismatches.

### GET /health/chat

```json
{
  "ok": true,
  "status": "healthy",
  "redis": "ok",
  "worker": { "status": "fresh", "heartbeat_age_seconds": 1.884 },
  "queue": { "depth": 0, "status": "progressing" },
  "completion_service": { "ok": true, "redis_reachable": true, "enqueue_test_ok": true, "worker_heartbeat_detected": true },
  "provider": "local",
  "model": "mlx-community/gemma-4-12B-it-qat-4bit",
  "provider_runtime": { "id": "local", "authorized": true, "available": true, "enabled": true },
  "configured_model_available": true
}
```

Result: **healthy**. Redis ok, worker heartbeat fresh, enqueue ok, provider available, model available.

### GET /api/health/llm

```json
{
  "status": "ok",
  "service": "llm",
  "details": {
    "provider": "local",
    "model": "mlx-community/gemma-4-12B-it-qat-4bit",
    "local_base_url": "http://host.docker.internal:8000/v1",
    "provider_runtime": { "id": "local", "authorized": true, "available": true, "enabled": true },
    "completion_service": { "ok": true },
    "ok": true,
    "status": "online",
    "configured_model_available": true
  }
}
```

Result: **ok/online**. Provider local, model available, endpoint resolved.

### GET /api/llm/catalog?include=all

Result: **ok**. Local provider entry:

- `id: local`, `displayName: Whoosh'd`, `enabled: true`, `authorized: true`, `available: true`
- Model: `mlx-community/gemma-4-12B-it-qat-4bit` (vision_chat, confirmed)
- `truth.executable: true`, `truth.selectable: true`, `truth.supported_profile_approved: true`
- All cloud providers: disabled (egress disallowed or missing credentials)

## Chat completion proof

| Step | Result |
|---|---|
| Thread created | Thread 23 (`Whooshd setup proof`) |
| User message posted | Message 140 |
| Completion accepted | Task `b083d493-4042-470f-97ea-ca3bf6770346` |
| Worker dequeued | `[task] running type=chat_completion` |
| Context assembled | 1 message, depth=normal |
| Provider call | `ai_router: chat.inference.request.built` |
| Assistant persisted | Message 141 |
| Task completed | `[task] completed` |

### Assistant response

> Hello! I'm here and ready whenever you are. How can I help you get started today?

### Execution metadata from persisted message

```
final_provider: local
final_model: mlx-community/gemma-4-12B-it-qat-4bit
selection_source: whooshd_model_profile
fallback_triggered: false
completion_truth.completed: true
```

## Upload -> embed -> readback proof

**Not run.** Reason: this proof focuses on the Whoosh'd chat completion path. The existing workspace proof harness (`scripts/proofs/prove_workspace_obsidian_e2e.py`) was not exercised here; it can be run as a separate proof artifact.

## Limitations and drift

- `release_hold: true` is reported by `/health`. This is expected for the current beta posture and not a setup issue.
- The task events endpoint (`/api/tasks/{task_id}/events`) returned empty arrays during polling, but the worker logs and persisted messages prove completion succeeded. The task-event visibility path may have a timing or transport nuance worth investigating separately.
- The `supported_profile_mismatches` in the worker-side `final_provider_truth` metadata contains `"supported profile manifest is not configured"` — this is a worker-scoped context difference (the worker does not load the supported profile manifest at runtime), not a setup failure.
- `cloud_capable_configuration_present: true` appears in health output. This is because `OPENAI_API_KEY=local` is set as an SDK init placeholder. Cloud providers remain disabled by egress policy.

## Verdict

**go** — Whoosh'd local runtime is configured, reachable from Docker containers, model inventory is live, all health surfaces are green, and an end-to-end chat completion was executed and persisted using the local provider with `mlx-community/gemma-4-12B-it-qat-4bit`.
