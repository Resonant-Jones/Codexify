# Supported Compose Beta Path Proof — 2026-04-13

**Artifact date:** 2026-04-13
**Proof window:** 2026-04-14T02:00–03:30 UTC
**Branch:** `codex/add-retrieval-explainer` (checked out; 6 commits ahead of `main`)
**HEAD commit:** `92ca70419cd2df7e65fc00ca042e36b3f4b4e5ad`
**Worktree:** clean

---

## Runtime Path

Local Docker Compose stack (`docker-compose.yml` at repo root), same runtime path used in all prior supported-path proofs.

Containers running at time of proof:

| Container | Status | Ports |
|---|---|---|
| `codexify-backend-1` | healthy | 8888 |
| `codexify-frontend-1` | up | 5173 |
| `codexify-db-1` | healthy | 5433→5432 |
| `codexify-redis-1` | healthy | 6379 |
| `codexify-neo4j-1` | healthy | 7474, 7687 |
| `codexify-worker-chat-1` | up | 8888/tcp |
| `codexify-worker-chat-embed-1` | up | 8888/tcp |
| `codexify-worker-document-embed-1` | up | 8888/tcp |
| `codexify-worker-voice-1` | up | 8888/tcp |
| `codexify-worker-warmup-1` | up | 8888/tcp |

**Stack verdict: PASS** — All containers healthy/up.

---

## Supported-Profile Posture

| Check | Result |
|---|---|
| Active completion provider | `local` (Ollama at `host.docker.internal:11434`) |
| Active model | `Gemma 4 E 4 B Hauhau` (configured) |
| Cloud providers (OpenAI, Anthropic, Gemini) | Disabled — missing credentials |
| Retrieval backend | Chroma (`/app/.chroma`), shared runtime with worker write path |
| `CODEXIFY_LOCAL_ONLY_MODE` | `false` (not restrictive; posture driven by credential absence) |

**Verdict: PASS** — Active completion path is exclusively local via Ollama. No cloud provider is in the execution path.

---

## Health Surface Reconciliation

### `/health`
```
{"status":"ok","service":"core","timestamp":"2026-04-14T02:03:01.933076+00:00","details":{}}
```
**Result: PASS**

### `/health/chat`
```
{"ok":false,"status":"unhealthy",
 "error":"local_model_resolution_error",
 "provider":"local","model":"Gemma 4 E 4 B Hauhau",
 "provider_runtime":{"id":"local","authorized":true,"available":true,
   "enabled":false,
   "disabled_reason":"No runnable local model was found among the requested or configured local candidates"},
 "model_resolution":{
   "failure_kind":"local_model_unavailable",
   "error":"local_model_resolution_error",
   "message":"No runnable local model was found...",
   "endpoint_resolution":{"state":"available",
     "attempted_sequence":["http://host.docker.internal:11434"],
     "attempts":[{"base_url":"http://host.docker.internal:11434","label":"host.docker.internal:11434","source":"primary","attempted":true,"selected":true}]}},
 "completion_service":{"ok":true,"worker_heartbeat_detected":true,
   "worker_heartbeat_age_seconds":0.243}}
```
**Result: FAIL** — Local Ollama model name mismatch. Codexify is configured for `Gemma 4 E 4 B Hauhau` but the Ollama instance has `gemma4-e4b-hauhau:latest`. Completion requests return HTTP 400: `invalid model name`. Worker heartbeats are fresh, Redis/queue are healthy.

### `/api/health/llm`
```
{"status":"down","service":"llm","ok":false,"status":"misconfigured",
 "error":"local_model_resolution_error",
 "failure_kind":"local_model_unavailable",
 "provider":"local","model":"Gemma 4 E 4 B Hauhau",
 "provider_runtime":{"id":"local","authorized":true,"available":true,
   "enabled":false,
   "disabled_reason":"No runnable local model was found..."}}
```
**Result: FAIL** — Same model name mismatch as `/health/chat`.

### `/api/health/retrieval`
```
{"status":"ready","ok":true,"reason":"backend search runtime matches canonical worker write runtime",
 "worker_write_runtime":{"backend":"chroma","chroma_path":"/app/.chroma",
   "collection":"codexify_vault_supported"},
 "backend_search_runtime":{"backend":"chroma","chroma_path":"/app/.chroma",
   "collection":"codexify_vault_supported"},
 "backend_store_source":"shared","same_runtime_as_worker":true,
 "proof_capable":true}
```
**Result: PASS** — Chroma is the active retrieval backend, shared with worker write path. `proof_capable: true`.

### `/api/llm/catalog?include=all`
Returns provider catalog with `local`, `openai`, `anthropic`, `gemini`. Local provider has one model confirmed available (`gemma4-e4b-hauhau:latest` per Ollama `/api/tags`). Cloud providers all disabled due to missing credentials. Ollama endpoint is reachable at `host.docker.internal:11434`.
**Result: PASS**

**Health reconciliation verdict: PARTIAL PASS** — Core health, retrieval health, and LLM catalog are healthy. LLM health surfaces correctly report the model name mismatch as `local_model_unavailable`.

---

## Retrieval-Posture Diagnostics Surface

### New Route: `GET /api/chat/debug/retrieval-posture/{thread_id}/latest`

**Route presence: CONFIRMED** — The route is registered in `guardian/routes/chat.py` at the current HEAD (`get_latest_retrieval_posture`, `get_latest_retrieval_posture_endpoint`, and `api_get_latest_retrieval_posture`).

### Route Behavior (Actual Live Test)

```sh
# Empty state — new thread with no completions
curl "http://localhost:8888/api/chat/debug/retrieval-posture/1215/latest" \
  -H "X-API-Key: <key>"
# Response:
{"thread_id":1215,"status":"empty","retrieval_posture":null}
```

**Route is live and returning correct empty-state shape.**

**Known limitation**: The route's populated-state path (`payload_summary["retrieval_posture"]`) requires the completion-service seam to emit the canonical snapshot into the task's `payload_summary`. This emission has NOT yet been implemented in `guardian/core/chat_completion_service.py` at this commit. The fast path (`if posture is None: return canonical from completion-service`) is a dead letter until that seam is updated. The fallback synthesis path (`_synthesize_retrieval_posture`) reads legacy trace fields (`source_mode`, `widen_reason`) which are also not yet persisted into the task.completed event payload — so the fallback also returns empty for all threads.

**Practical consequence**: The diagnostics surface is correctly wired and responds correctly, but cannot demonstrate a populated posture on the live stack until (a) the completion-service emits `payload_summary["retrieval_posture"]`, and (b) historical task.completed events are back-filled or new completions run to completion.

### Exact Commands Run

```sh
# Create thread
curl -s -X POST http://localhost:8888/api/chat/threads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"title": "proof-2026-04-13"}'

# Post message
curl -s -X POST http://localhost:8888/api/chat/1215/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"content": "Hello world", "role": "user"}'

# Accept completion
curl -s -X POST http://localhost:8888/api/chat/1215/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{}'

# Check retrieval-posture (empty state confirmed)
curl "http://localhost:8888/api/chat/debug/retrieval-posture/1215/latest" \
  -H "X-API-Key: <key>"
```

**Posture route verdict: CONFIRMED PRESENT, CORRECT EMPTY-STATE RESPONSE, NO POPULATED STATE DEMONSTRATED DUE TO MODEL UNAVAILABILITY**

---

## Chat Completion Proof

### Attempted Commands

```sh
curl -s -X POST http://localhost:8888/api/chat/1215/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{}'
```

**Acceptance response:**
```json
{"ok":true,"acceptance_status":"accepted","task_id":"ee3ed122-ddcd-40e1-b73f-b80771838258",
 "turn_id":"0d7f3a46-a0e1-4962-b4d9-f9b2ea56201c","thread_id":1215,
 "source_mode":"project","depth_mode":"normal"}
```

**Worker log (chat-worker-1):**
```
ERROR - [task] failed type=chat_completion id=ee3ed122...
  err=502: Local inference request failed for model 'Gemma 4 E 4 B Hauhau'.
  Attempted endpoints:
    http://host.docker.internal:11434/api/chat (HTTP 400: invalid model name);
    http://host.docker.internal:11434/v1/chat/completions (HTTP 400: invalid model name)
```

**Root cause**: Ollama is running at `host.docker.internal:11434` with model `gemma4-e4b-hauhau:latest`. Codexify is configured with `LOCAL_CHAT_MODEL=Gemma 4 E 4 B Hauhau` which does not match any available model name in the Ollama registry.

**Historical evidence**: Worker logs show thread 1214 had two successful completions (`task_id=1c08aa48...`, `task_id=5066f206...`) earlier in this container's uptime, using `source_mode=personal_knowledge` and achieving `semantic=2` and `semantic=3` retrieval. These confirm the worker can complete successfully when the model name matches.

**Chat completion verdict: BLOCKED** — Task accepted and queued, but worker cannot call Ollama due to model name mismatch. The `qwen3.5:9b` model used in the 2026-04-10 proof is no longer available in the Ollama instance; it has been replaced with `gemma4-e4b-hauhau:latest`. The `LOCAL_CHAT_MODEL` environment variable needs to be updated to `gemma4-e4b-hauhau:latest` to restore completions.

---

## Retrieval (Chroma) Proof

**Result: PASS** — `/api/health/retrieval` confirms `proof_capable: true`, `same_runtime_as_worker: true`, Chroma backend active with correct collection (`codexify_vault_supported`). Worker logs for successful thread 1214 completions show `ContextBroker thread=1214 depth=normal messages=N semantic=2 obsidian=0 docs(project/thread)=0/0 memory=0 graph=3(contributed)` confirming live semantic retrieval against Chroma.

**Upload→parse→embed→retrieve chain**: NOT EXERCISED — file upload seam was not invoked in this proof run. Chroma vector store is confirmed healthy and proof-capable, but specific upload workflow was not tested.

---

## What Remains Out of Scope

| Out-of-scope surface | Reason |
|---|---|
| Browser/operator UI proof | No Selenium/playwright test; only runtime API seams exercised |
| Upload→parse→embed→retrieve chain | File upload seam not invoked in this run |
| Populated retrieval posture state | Requires completion to succeed and completion-service seam to emit `payload_summary["retrieval_posture"]` |
| Chat completion (current) | BLOCKED — model name mismatch between Codexify config and Ollama registry |
| Command bus external surface | Internal-only in supported profile |
| Quarantined surfaces (voice, vision, MCP connectors) | Not part of supported local-beta profile |
| Cloud deployment modes | Not exercised; local Docker Compose only |

---

## Final Verdict

| Section | Result |
|---|---|
| Supported-profile posture | **PASS** — Local-only active; no cloud providers in execution path |
| Health surface reconciliation | **PARTIAL PASS** — Core health and retrieval health PASS; LLM health surfaces correctly report model name mismatch |
| Retrieval (Chroma) proof | **PASS** — Chroma active, `proof_capable: true`, worker logs confirm live semantic retrieval |
| Chat completion proof | **BLOCKED** — Model name mismatch; `LOCAL_CHAT_MODEL` must be updated from `Gemma 4 E 4 B Hauhau` to `gemma4-e4b-hauhau:latest` |
| Retrieval-posture diagnostics surface | **CONFIRMED PRESENT** — Route is live and returns correct empty-state shape. Populated state not demonstrated (requires completion-service seam to emit `payload_summary["retrieval_posture"]`). |

**Final verdict: NOT YET PASS — Local Ollama model name mismatch must be resolved before fresh live completion proof can succeed.**

---

## Required Action Before Next Proof

Update `LOCAL_CHAT_MODEL` in `.env` or `docker-compose.yml` to match the available Ollama model:

```
# Current (broken):
LOCAL_CHAT_MODEL=Gemma 4 E 4 B Hauhau

# Required:
LOCAL_CHAT_MODEL=gemma4-e4b-hauhau:latest
```

Or update the Ollama instance to have a model aliased as `Gemma 4 E 4 B Hauhau`.

---

## Active Blockers

1. **Chat completion BLOCKED**: `LOCAL_CHAT_MODEL` name mismatch with Ollama registry — completions fail with HTTP 400
2. **Retrieval-posture populated state NOT YET DEMONSTRATED**: `payload_summary["retrieval_posture"]` emission not yet implemented in `guardian/core/chat_completion_service.py`; historical task.completed events lack the required fields

---

*Proof artifact generated by Claude Code runtime proof run. Commands and outputs captured live during execution window 2026-04-14T02:00–03:30 UTC.*
