# Supported Profile Proof

## Scope

This artifact records fresh live-runtime evidence from the local Compose path on `2026-03-19` for the Beta local supported profile.

Required proof points:

- effective supported-profile flags are active in the live stack
- quarantined non-core routes are unavailable on that profile
- live thread creation and assistant completion succeed on the supported path
- live upload -> embed -> retrieve succeeds on the supported path
- provider/catalog behavior observed in the live stack does not contradict the provider-governance hardening intent

Only this file was changed for this task.

## Environment

- Evidence captured: `2026-03-19T20:02:19Z`
- Repo branch: `codex/document-supported-profile-proof`
- Commit under test: `7cf7d11d3e0e1ddb44958deff0fc3aa60be920e7`
- API base: `http://127.0.0.1:8888`
- Temp env file: `/tmp/codexify-beta.env`

Temp env creation command used first:

```bash
cat > /tmp/codexify-beta.env <<'EOF'
GUARDIAN_API_KEY=test-dev-key
CODEXIFY_RUNTIME_ENV_FILE=/tmp/codexify-beta.env
CODEXIFY_BETA_CORE_ONLY=true
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
EOF
```

Exact initial startup command:

```bash
docker compose --env-file /tmp/codexify-beta.env up -d
```

Observed initial result:

```text
time="2026-03-19T15:48:15-04:00" level=warning msg="The \"LOCAL_CHAT_MODEL\" variable is not set. Defaulting to a blank string."
time="2026-03-19T15:48:15-04:00" level=warning msg="The \"NEO4J_PASS\" variable is not set. Defaulting to a blank string."
dependency failed to start: container codexify-neo4j-1 exited (1)
```

Live logs showed the concrete failure:

```text
neo4j-1       | neo4j/ is invalid
neo4j-1       | Invalid value for NEO4J_AUTH: 'neo4j/'
```

To continue runtime evidence capture on the same Compose path, I appended the baseline non-profile values the current repo still expects from `.env`:

```bash
printf '\nNEO4J_PASS=codexify\nLOCAL_CHAT_MODEL=qwen3.5:27b\n' >> /tmp/codexify-beta.env
printf 'AI_BACKEND=ollama\n' >> /tmp/codexify-beta.env
```

Recovery startup commands:

```bash
docker compose --env-file /tmp/codexify-beta.env up -d
docker compose --env-file /tmp/codexify-beta.env up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup frontend
```

Observed recovery result:

```text
codexify-backend-1                 Up (healthy)
codexify-worker-chat-1             Up
codexify-worker-document-embed-1   Up
codexify-worker-chat-embed-1       Up
codexify-worker-warmup-1           Up
codexify-frontend-1                Up
```

Repo-defined smoke command executed against the live supported env:

```bash
GUARDIAN_API_KEY=test-dev-key \
BETA_ENV_SOURCE_FILE=/tmp/codexify-beta.env \
bash scripts/verification/smoke_beta1.sh
```

Observed smoke result:

```text
[2026-03-19T19:57:52Z] Checking Beta-1 quarantined routes
[2026-03-19T19:57:52Z] Checking Beta-1 core routes remain mounted
[2026-03-19T19:57:52Z] PASS: Beta-1 smoke completed in 30s
```

## Effective Profile Flags

Compose config command:

```bash
docker compose --env-file /tmp/codexify-beta.env config
```

Observed config excerpt after env-file selection fix:

```text
ALLOW_CLOUD_PROVIDERS: "false"
CODEXIFY_BETA_CORE_ONLY: "true"
CODEXIFY_LOCAL_ONLY_MODE: "true"
CODEXIFY_RUNTIME_ENV_FILE: /tmp/codexify-beta.env
```

Live backend container check:

```bash
docker compose --env-file /tmp/codexify-beta.env exec -T backend sh -lc \
  'printf "backend beta=%s local_only=%s cloud=%s runtime_env=%s local_chat_model=%s ai_backend=%s\n" \
  "$CODEXIFY_BETA_CORE_ONLY" "$CODEXIFY_LOCAL_ONLY_MODE" "$ALLOW_CLOUD_PROVIDERS" \
  "$CODEXIFY_RUNTIME_ENV_FILE" "$LOCAL_CHAT_MODEL" "$AI_BACKEND"'
```

Observed result:

```text
backend beta=true local_only=true cloud=false runtime_env=/tmp/codexify-beta.env local_chat_model=qwen3.5:27b ai_backend=ollama
```

Live worker check:

```text
worker-chat beta=true local_only=true cloud=false local_chat_model=qwen3.5:27b ai_backend=ollama
```

Result:

- `CODEXIFY_BETA_CORE_ONLY=true` was active in the live runtime
- `CODEXIFY_LOCAL_ONLY_MODE=true` was active in the live runtime
- `ALLOW_CLOUD_PROVIDERS=false` was active in the live runtime
- the Compose env-file selection fix is effective
- the current stack still needs additional baseline runtime values beyond the five-line proof env before full startup succeeds

## Provider Surface Checks

Live health check command:

```bash
curl -sS -H 'X-API-Key: test-dev-key' http://127.0.0.1:8888/api/health/llm
```

Observed result:

```json
{
  "provider": "local",
  "model": "library2/ministral-3:8b",
  "provider_runtime": {
    "id": "local",
    "authorized": true,
    "available": true,
    "enabled": true
  },
  "ok": true,
  "status": "online",
  "checked_endpoint": "/api/tags"
}
```

Live catalog command:

```bash
curl -sS -H 'X-API-Key: test-dev-key' \
  'http://127.0.0.1:8888/api/llm/catalog?include=all'
```

Observed result summary:

- `local` was the only `enabled:true` provider
- `openai`, `anthropic`, `gemini`, `groq`, `alibaba`, and `minimax` all returned `enabled:false`
- disabled cloud providers were surfaced as unavailable rather than active runtime options

Observed drift risk:

- live container env pinned `LOCAL_CHAT_MODEL=qwen3.5:27b`
- `/api/health/llm` reported active local model `library2/ministral-3:8b`
- `/api/llm/catalog?include=all` also surfaced a large local catalog and treated `library2/ministral-3:8b` as the default runtime model

Assessment:

- the live stack did not expose any cloud provider as enabled, which is consistent with the provider-governance hardening intent
- the catalog/runtime drift risk still exists on the local model surface: the health/catalog default did not match the env-pinned `LOCAL_CHAT_MODEL`
- I did not see live evidence of cloud egress governance being bypassed, but I did see evidence that model-selection surfaces can drift if the catalog and runtime pin are not kept aligned

## Quarantined Route Checks

Probe commands:

```bash
curl -sS -o /tmp/connectors.out -w 'connectors_status=%{http_code}\n' \
  -H 'X-API-Key: test-dev-key' \
  http://127.0.0.1:8888/api/connectors

curl -sS -o /tmp/tools.out -w 'tools_status=%{http_code}\n' \
  -H 'X-API-Key: test-dev-key' \
  http://127.0.0.1:8888/api/tools/manifest
```

Observed results:

```text
connectors_status=404
connectors_body={"detail":"Not Found"}

tools_status=404
tools_body={"detail":"Not Found"}
```

Result:

- `GET /api/connectors` was unavailable as expected
- `GET /api/tools/manifest` was unavailable as expected
- both routes were explicitly quarantined in the live supported profile

## Happy-Path Thread and Completion Proof

Fresh live commands:

```bash
POST /api/chat/threads
POST /api/chat/6/messages
POST /api/chat/6/complete
GET  /api/chat/6/messages?limit=50
GET  /api/chat/debug/rag-trace/6/latest
```

Observed thread creation result:

```json
{
  "ok": true,
  "id": 6,
  "thread": {
    "id": 6,
    "user_id": "beta-proof-user-20260319-happy",
    "title": "beta-proof-happy-1773950446",
    "project_id": 1
  }
}
```

Observed message post result:

```json
{
  "ok": true,
  "message": {
    "id": 36,
    "thread_id": 6,
    "role": "user",
    "content": "Reply with exactly: supported-profile-happy-path-20260319"
  }
}
```

Observed completion enqueue result:

```json
{
  "ok": true,
  "task_id": "c1b0c24a-ecc5-4722-b168-cdcdc1dd5e0c",
  "turn_id": "511b8e10-9c7e-4a3d-9790-6227b7758241",
  "thread_id": 6,
  "messages_url": "/api/chat/6/messages",
  "trace_url": "/api/chat/debug/rag-trace/6/latest"
}
```

Observed task lifecycle from the live task event stream:

```text
task.created
task.running
task.progress
task.completed
```

Observed terminal event:

```json
{
  "type": "task.completed",
  "task_id": "c1b0c24a-ecc5-4722-b168-cdcdc1dd5e0c",
  "data": {
    "duration_ms": 7126,
    "thread_id": 6,
    "turn_id": "511b8e10-9c7e-4a3d-9790-6227b7758241",
    "message_id": 37,
    "provider": "local",
    "model": "library2/ministral-3:8b",
    "resolved_provider": "local",
    "resolved_model": "library2/ministral-3:8b",
    "persistence_outcome": "persisted"
  }
}
```

Observed persisted assistant message:

```json
{
  "id": 37,
  "thread_id": 6,
  "role": "assistant",
  "metadata": {
    "turn_id": "511b8e10-9c7e-4a3d-9790-6227b7758241",
    "final_model": "library2/ministral-3:8b",
    "final_provider": "local"
  }
}
```

Observed assistant content:

```text
**supported-profile-happy-path-20260319**
```

Result:

- thread creation succeeded
- message post succeeded
- completion request succeeded
- task lifecycle was visible in the live event stream
- assistant output was persisted and retrievable afterward

## Upload -> Embed -> Retrieve Proof

Fresh live document command:

```bash
POST /api/media/upload/document
GET  /api/media/documents?thread_id=6&limit=20
POST /api/retrieve
```

Uploaded marker:

```text
beta-proof-rag-marker-20260319-obsidian-lattice
```

Observed upload result:

```json
{
  "id": "d2d5f1cf-2c31-4998-91e1-66632ee21449",
  "project_id": 1,
  "thread_id": 6,
  "filename": "beta-supported-proof-doc.txt",
  "embedding_status": "pending"
}
```

Observed document lifecycle:

```json
{
  "id": "d2d5f1cf-2c31-4998-91e1-66632ee21449",
  "embedding_status": "failed",
  "embedding_error": "Error in compaction: Failed to apply logs to the hnsw segment writer",
  "embedding_started_at": "2026-03-19T20:01:34.138236+00:00",
  "embedding_completed_at": "2026-03-19T20:01:35.789549+00:00"
}
```

Observed worker log:

```text
[document-embed] embedding failed doc_id=d2d5f1cf-2c31-4998-91e1-66632ee21449 err=Error in compaction: Failed to apply logs to the hnsw segment writer
```

Observed retrieval/debug route result:

```text
POST /api/retrieve -> 404 Not Found
```

Supported-profile OpenAPI surface at capture time only exposed:

```text
/api/media/documents
/api/media/documents/{document_id}
/api/media/upload/document
```

Result:

- upload succeeded
- embed did not reach `ready`; it failed in the live worker
- no mounted retrieval/debug route was available on this supported profile to prove runtime retrieval afterward
- the required upload -> embed -> retrieve proof was not achieved

## Failures Observed

- the exact five-line temp env file did not boot the full stack by itself; the current Compose path still required baseline runtime values for `NEO4J_PASS`, `LOCAL_CHAT_MODEL`, and `AI_BACKEND`
- the local provider surface still shows drift between the env pin (`qwen3.5:27b`) and the health/catalog default (`library2/ministral-3:8b`)
- the RAG trace after the successful completion was still odd:

```json
{"documents":[],"graph":[],"active_profile_id":"default","provider_override":null,"model_override":null,"injection_hash":null,"retrieval_mode":null,"model_mode":"cloud"}
```

- `model_mode:"cloud"` in that trace did not match the live completion event, which resolved `provider:"local"`
- the upload -> embed flow failed with `Error in compaction: Failed to apply logs to the hnsw segment writer`
- `POST /api/retrieve` was not mounted on the supported profile, so retrieval closure could not be shown through that debug surface

## Verdict

The supported profile is only partially proven on the live Compose path in the current repo state.

Proven live:

- the supported-profile flags are active
- quarantined non-core routes are unavailable
- the supported chat happy path works end to end for thread create -> message post -> completion -> persisted assistant output
- the repo-defined `smoke_beta1.sh` run passes against the supported env

Not proven live:

- upload -> embed -> retrieve

Because the required document ingestion and retrieval proof failed in the live runtime, this artifact does not support a full success verdict for the supported profile release evidence yet.
