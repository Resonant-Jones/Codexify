# Supported RAG Path Proof on Current HEAD

Branch: `main`

HEAD: `f0817a331`

Evidence capture timestamp: `2026-04-03T23:54:31Z` UTC

Runtime note: all live observations below were taken against the same Docker Compose deployment after the startup command shown here. Host-port `curl` was not reachable from this shell, so the final HTTP probes were executed with `docker compose exec -T backend python3` against the running backend container. That still exercised the same compose runtime.

Supported proof surface for this artifact: `GET /api/health/retrieval?q=...`

`/api/retrieve` was intentionally not exercised and is not part of the proof scope here.

## Startup

Commands used to bring up the supported stack:

```bash
docker compose stop backend worker-document-embed worker-chat worker-chat-embed
CODEXIFY_SINGLE_USER_ID=proof-rag-20260403 docker compose up -d --force-recreate backend worker-document-embed worker-chat worker-chat-embed
```

Live compose state after startup:

```text
NAME                               IMAGE                            COMMAND                  SERVICE                 CREATED          STATUS                    PORTS
codexify-backend-1                 codexify-backend                 "python -c 'import o…"   backend                 29 minutes ago   Up 29 minutes (healthy)   0.0.0.0:8888->8888/tcp, [::]:8888->8888/tcp
codexify-worker-chat-1             codexify-worker-chat             "python -m guardian.…"   worker-chat             29 minutes ago   Up 29 minutes             8888/tcp
codexify-worker-chat-embed-1       codexify-worker-chat-embed       "python -m guardian.…"   worker-chat-embed       29 minutes ago   Up 29 minutes             8888/tcp
codexify-worker-document-embed-1   codexify-worker-document-embed   "python -m guardian.…"   worker-document-embed   29 minutes ago   Up 29 minutes             8888/tcp
```

Verdict: pass.

## Supported-Profile Flags

Command used:

```bash
docker compose exec -T backend env | grep -E '^(CODEXIFY_BETA_CORE_ONLY|CODEXIFY_LOCAL_ONLY_MODE|ALLOW_CLOUD_PROVIDERS|CODEXIFY_VECTOR_STORE|CODEXIFY_CHROMA_PATH|CODEXIFY_COLLECTION)='
docker compose exec -T worker-document-embed env | grep -E '^(CODEXIFY_BETA_CORE_ONLY|CODEXIFY_LOCAL_ONLY_MODE|ALLOW_CLOUD_PROVIDERS|CODEXIFY_VECTOR_STORE|CODEXIFY_CHROMA_PATH|CODEXIFY_COLLECTION)='
```

Observed backend env:

```text
CODEXIFY_CHROMA_PATH=./.chroma
CODEXIFY_VECTOR_STORE=chroma
CODEXIFY_COLLECTION=codexify_vault_supported
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_BETA_CORE_ONLY=true
```

Observed worker-document-embed env:

```text
CODEXIFY_BETA_CORE_ONLY=true
CODEXIFY_VECTOR_STORE=chroma
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_COLLECTION=codexify_vault_supported
CODEXIFY_LOCAL_ONLY_MODE=true
CODEXIFY_CHROMA_PATH=./.chroma
```

Verdict: pass.

## Beta-Core Quarantine

Command used:

```bash
docker compose exec -T -e API_KEY="$API_KEY" backend python3
```

The Python probe requested `GET /api/connectors` with the live API key.

Observed output:

```text
[quarantine] status=404
{"detail":"Not Found"}
```

Verdict: pass.

## Health Checks

Commands used:

```bash
docker compose exec -T -e API_KEY="$API_KEY" backend python3
```

Observed outputs:

```text
[health] {"status":"ok","service":"core","timestamp":"2026-04-03T23:54:27.894813+00:00","details":{}}
[vector] {"status":"ok","service":"vector","timestamp":"2026-04-03T23:54:28.507599+00:00","details":{"ok":true,"status":"ok","backend":"chroma","source":"probe","added":1,"matches":1},"ok":true,"backend":"chroma","source":"probe","added":1,"matches":1}
[embedder] {"status":"ok","embedder":{"backend":"local","model":"/models/bge-large-en-v1.5","ready":true,"present":true,"reason":"local embedder preflight passed"}}
```

Verdict: pass.

## Chat Proof

Thread create, user message persistence, completion acceptance, and assistant persistence were all exercised against the live supported compose deployment.

Observed outputs from the chat proof:

```text
[thread.create] {"ok":true,"id":269,"thread":{"id":269,"user_id":"default","title":"supported-rag-proof-20260403","summary":"","project_id":null,"parent_id":null,"archived_at":null,"is_diary":false,"diary_mode":false,"exclude_from_identity":false,"modeling_excluded":false,"metadata":{},"active_profile_id":null,"thread_config":{"providerId":"local","modelId":"qwen3.5:9b","inferenceMode":"fast","retrievalSource":"project","personaId":null},"created_at":"2026-04-03T23:30:53.941137+00:00","updated_at":"2026-04-03T23:30:53.941137+00:00"}}
[message.create] {"ok":true,"message":{"id":13367,"thread_id":269,"role":"user","content":"Reply with exactly one word: hello"}}
[chat.complete] {"ok":true,"acceptance_status":"accepted","acceptance_warnings":[],"task_id":"48dfc068-8b55-4f6c-a37e-0d38cf0473cc","turn_id":"ff1016c2-1f23-4189-9bba-535e1aab8a4b","thread_id":269,"source_mode":"project","depth_mode":"normal","requested_depth_mode":"deep","effective_depth_mode":"light","depth_downgrade_reason":"no_project","messages_url":"/api/chat/269/messages","trace_url":"/api/chat/debug/rag-trace/269/latest"}
[messages.final] {"ok":true,"total":2,"messages":[{"id":13367,"thread_id":269,"role":"user","content":"Reply with exactly one word: hello","created_at":"2026-04-03T23:30:53.996006+00:00","kind":"chat"},{"id":13368,"thread_id":269,"role":"assistant","content":"hello","created_at":"2026-04-03T23:32:42.883923+00:00","kind":"chat","metadata":{"turn_id":"ff1016c2-1f23-4189-9bba-535e1aab8a4b","execution":{"final_model":"qwen3.5:9b","final_provider":"local","attempted_model":"qwen3.5:9b","attempted_provider":"local","fallback_triggered":false},"final_model":"qwen3.5:9b","final_provider":"local","resolved_model":"qwen3.5:9b","attempted_model":"qwen3.5:9b","fallback_reason":null,"payload_summary":{"version":1,"final_model":"qwen3.5:9b","graph_count":1,"memory_count":0,"message_count":2,"final_provider":"local","graph_injected":true,"obsidian_count":0,"resolved_model":"qwen3.5:9b","semantic_count":0,"attempted_model":"qwen3.5:9b","fallback_reason":null,"memory_injected":false,"completion_truth":{"accepted":true,"executed":true,"attempted":true,"completed":true,"fallback_attempted":false},"has_system_prompt":true,"obsidian_injected":false,"resolved_provider":"local","semantic_injected":false,"attempted_provider":"local","federated_injected":false,"payload_char_count":2804,"retrieval_injected":true,"final_provider_truth":{"executed":true,"attempted":true,"completed":true,"authorized":true,"configured":true,"selectable":true,"discoverable":true},"linked_document_count":0,"attempted_provider_truth":{"executed":true,"attempted":true,"completed":true,"authorized":true,"configured":true,"selectable":true,"discoverable":true},"has_user_system_override":false,"linked_document_injected":false,"payload_estimated_tokens":701,"persona_or_imprint_present":false},"completion_truth":{"accepted":true,"executed":true,"attempted":true,"completed":true,"fallback_attempted":false},"selection_source":"explicit","resolved_provider":"local","attempted_provider":"local","final_provider_truth":{"executed":true,"attempted":true,"completed":true,"authorized":true,"configured":true,"selectable":true,"discoverable":true},"attempted_provider_truth":{"executed":true,"attempted":true,"completed":true,"authorized":true,"configured":true,"selectable":true,"discoverable":true}},"execution":{"attempted_provider":"local","attempted_model":"qwen3.5:9b","final_provider":"local","final_model":"qwen3.5:9b","fallback_triggered":false},"turn_id":"ff1016c2-1f23-4189-9bba-535e1aab8a4b","audio_status":"unavailable","audio_url":null,"audio_mime_type":null,"audio_duration_ms":null}]}
```

Verdict: pass.

## Document Upload

Command used:

```bash
curl -sS -X POST http://localhost:8888/api/media/upload/document -H "X-API-Key: ${API_KEY}" -F 'project_id=1' -F 'thread_id=269' -F 'user_id=proof-rag-20260403' -F 'file=@/tmp/supported-rag-proof-20260403.txt;type=text/plain'
```

Observed output:

```text
{"id":"a27df344-354d-4921-8ef0-0e91658e7dfd","project_id":1,"thread_id":269,"src_url":"/media/documents/20260403-40fd6ec3--supported-rag-proof-20260403.txt?sig=2MnaU6l0hpk0OQt2Z1AClVBrTRNvhG3WmUOvFJyzqV0","filename":"supported-rag-proof-20260403.txt","filesize":90,"mime_type":"text/plain","source_tag":"uploaded","parsed_text":"supported-rag-proof-20260403 violet puma 7xq\nsupported-rag-proof-20260403 violet puma 7xq\n","embedding_status":"pending","embedding_error":null,"embedding_started_at":null,"embedding_completed_at":null,"created_at":"2026-04-03T23:33:01.006563+00:00"}
```

Verdict: pass.

## Document Lifecycle Truth

Command used:

```bash
docker compose exec -T -e API_KEY="$API_KEY" backend python3
```

The probe queried `GET /api/media/documents?thread_id=269&limit=5`.

Observed output:

```text
{"documents":[{"id":"a27df344-354d-4921-8ef0-0e91658e7dfd","project_id":1,"thread_id":269,"src_url":"/media/documents/20260403-40fd6ec3--supported-rag-proof-20260403.txt?sig=2MnaU6l0hpk0OQt2Z1AClVBrTRNvhG3WmUOvFJyzqV0","filename":"supported-rag-proof-20260403.txt","mime_type":"text/plain","filesize":90,"source_tag":"uploaded","embedding_status":"ready","embedding_error":null,"embedding_started_at":"2026-04-03T23:33:01.127363+00:00","embedding_completed_at":"2026-04-03T23:33:01.987251+00:00","created_at":"2026-04-03T23:33:00.965687+00:00"}],"count":1}
```

Lifecycle verdict: pass. The uploaded document moved from `pending` to `ready` with populated start and completion timestamps.

## Retrieval Proof

Command used:

```bash
docker compose exec -T -e API_KEY="$API_KEY" backend python3
```

The probe requested `GET /api/health/retrieval?q=supported-rag-proof-20260403%20violet%20puma%207xq`.

Observed output (key excerpt):

```text
[retrieval] status=200
{"status":"ready","ok":true,"reason":"backend search runtime matches canonical worker write runtime","worker_write_runtime":{"backend":"chroma","chroma_path":"/app/.chroma","collection":"codexify_vault_supported"},"backend_search_runtime":{"backend":"chroma","chroma_path":"/app/.chroma","collection":"codexify_vault_supported"},"backend_store_source":"shared","same_runtime_as_worker":true,"proof_capable":true,"search":{"executed":true,"query":"supported-rag-proof-20260403 violet puma 7xq","k":5,"namespace":null,"match_count":5,"matches":[{"text":"supported-rag-proof-20260403 violet puma 7xq\nsupported-rag-proof-20260403 violet puma 7xq\n","meta":{"source":"document","filename":"supported-rag-proof-20260403.txt","doc_id":"a27df344-354d-4921-8ef0-0e91658e7dfd","project_id":1,"thread_id":269,"user_id":"proof-rag-20260403","timestamp":"2026-04-03T23:33:01.134997+00:00","namespace":"thread:269","chunk_count":1,"chunk_index":0},"metadata":{"source":"document","filename":"supported-rag-proof-20260403.txt","doc_id":"a27df344-354d-4921-8ef0-0e91658e7dfd","project_id":1,"thread_id":269,"user_id":"proof-rag-20260403","timestamp":"2026-04-03T23:33:01.134997+00:00","namespace":"thread:269","chunk_count":1,"chunk_index":0},"score":0.9474131986498833,"id":"doc_bd0cf5917d1f4e608cf1686ade07d5cc"}],"error":null}}
[quarantine] status=404
{"detail":"Not Found"}
```

Verdict: pass.

## Backend / Worker Runtime Contract

The runtime contract was proven in two ways:

1. Backend and worker envs matched on the canonical vector-store settings.
2. The retrieval surface returned `same_runtime_as_worker: true` and reported the same `backend`, `chroma_path`, and `collection` values for search and worker write runtime.

Observed contract verdict: pass.

## What Was Proven

- Supported-profile flags are active in the running backend.
- Beta-core quarantine still blocks the quarantined routes.
- Thread creation works.
- Chat completion works and the assistant output is persisted.
- Document upload works.
- Uploaded documents move through lifecycle truthfully from `pending` to `ready`.
- Retrieval succeeds on the supported release surface: `GET /api/health/retrieval?q=...`.
- Backend and worker are running with the same vector-store runtime contract.

## What Was Not Proven

- `POST /api/retrieve` was intentionally not exercised.
- Legacy standalone server behavior was not part of scope.
- Unrelated routes/workers were not broadened beyond the quarantine sentinel checks and the required runtime proof.
