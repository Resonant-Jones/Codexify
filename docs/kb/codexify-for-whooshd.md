# Codexify Knowledge Base for Whoosh'd

## Purpose

This document captures everything Whoosh'd needs to know about Codexify in order to serve it well as a high-throughput MLX inference backend. It is extracted from Codexify's own architecture docs, runtime contracts, worker code, and operational surfaces.

Every claim is tagged with a confidence level:
- `confirmed` — backed by live code, architecture docs, or runtime proofs
- `inferred` — reasonable deduction from available evidence but not explicitly stated
- `unknown` — genuinely unclear from available sources
- `needs-owner-decision` — Whoosh'd must decide how to handle this

## Executive Summary

Codexify is a local-first chat + knowledge workspace with a FastAPI backend, Redis-backed async task queue, and OpenAI-compatible local model interface. It currently uses Ollama as its primary local inference backend, communicating via OpenAI-compatible `/v1/chat/completions` and `/api/chat` endpoints.

For Whoosh'd to serve as a drop-in or superior replacement, it needs to:

1. **Speak OpenAI-compatible chat completions** (streaming + non-streaming) — `confirmed`
2. **Serve an `/api/tags` or equivalent model listing endpoint** — `confirmed`
3. **Support concurrent requests** (default 2 concurrent chat workers, configurable) — `confirmed`
4. **Handle model warm-up gracefully** (distinct from offline) — `confirmed`
5. **Support cancellation** — `confirmed`
6. **Provide health endpoints** that distinguish runtime availability from model readiness — `confirmed`
7. **Never silently collapse warm-up latency into "offline"** — `confirmed` (critical behavior contract)

## Confirmed Codexify Runtime Requirements

### Provider Runtime States (Canonical)

Codexify defines a rich set of provider states that Whoosh'd should report truthfully:

```
OFFLINE           — endpoint unreachable
CONNECTING        — initial probe in progress
RUNTIME_AVAILABLE — backend reachable, API responds, model may still be loading
MODEL_WARMING     — model loading weights, compiling, not ready to emit tokens
READY             — model ready to accept inference
GENERATING        — at least one active request streaming
DEGRADED          — slow warmup, queue backed up, memory pressure, repeated timeouts
ERROR             — provider responded with hard internal error
```

**Source:** `docs/architecture/chat-runtime-contract.md`, `docs/architecture/request-state-machine.md` — `confirmed`

### Request Lifecycle States (Canonical)

Each inference attempt tracks its own state separately from provider state:

```
QUEUED → DISPATCHING → AWAITING_ACK → AWAITING_MODEL → AWAITING_FIRST_TOKEN → STREAMING → COMPLETED
                                                                               → CANCELLED
                                                                               → TIMED_OUT
                                                                               → FAILED_RETRYABLE → REPLAYED
                                                                               → FAILED_FATAL
                                                                               → ORPHANED → REPLAYED
```

**Source:** `docs/architecture/chat-runtime-contract.md` — `confirmed`

### Critical Behavioral Rules

1. **Never map warmup to offline.** Only use `OFFLINE` for transport-unreachable or repeated hard reachability failure. `confirmed`
2. **Provider health is global; request health is per-turn.** One slow request does not mean the provider is down. `confirmed`
3. **Message identity ≠ request identity.** A message can have multiple request attempts (retries, replays). `confirmed`
4. **Never silently replay unresolved turns.** If replay happens, it must be explicit. `confirmed`
5. **Acceptance ≠ completion.** Route acceptance (lock + enqueue) does not guarantee dequeue or execution success. `confirmed`

## Codexify Workflows Whoosh'd Should Support

### 1. Chat Completions (Primary Workflow)

The core Codexify workflow:

1. User sends message → persisted to Postgres
2. Completion route acquires Redis turn lock → enqueues task → returns `task_id`
3. Chat worker dequeues → assembles context (messages + RAG + memory) → calls provider
4. If cloud provider fails, worker may rescue once to local inference
5. Worker may execute exactly one bounded tool turn (command bus invoke) then reinject result
6. Assistant output persisted to Postgres → task completed

**Implication for Whoosh'd:** The primary inference pattern is a **single-turn chat completion** with **optional single tool-call round-trip**. Whoosh'd does not need to support multi-turn agent loops natively — Codexify's worker handles orchestration. `confirmed`

### 2. Agent Task Execution (Coding Worker)

Codexify has a separate coding worker (`guardian/workers/coding_worker.py`)
that runs agent adapters. For the Campaign Runner module, the direct adapter
seam is the Pi broker path (`pi` / legacy-compatible `pi_codex_runner`).
Direct Codex CLI and Claude Code execution are unsupported there. Downstream
provider/model identities may still be resolved through Pi and surfaced in
backend receipts.

**Implication for Whoosh'd:** These agents will generate multiple sequential and potentially parallel inference calls to the provider. Whoosh'd should expect:
- Bursts of requests from a single coding session
- Potentially long-running generation jobs
- High token count requests (code generation contexts)

`confirmed`

### 3. Multi-User / Household Usage

Codexify supports both `single_user` and `multi_user` modes:
- `single_user`: implicit identity, no auth required, all data belongs to one user
- `multi_user`: explicit identity required, all data scoped by `user_id`, retrieval must enforce user isolation

**Implication for Whoosh'd:** Whoosh'd does not need to understand user identity. Codexify's backend handles that. But Whoosh'd should not leak responses or state across requests. `confirmed`

### 4. Context Assembly and RAG

Before calling the model, Codexify's `ContextBroker` assembles:
- Recent thread messages
- Semantic vector search results
- Thread/project documents
- Memory retrieval (for deep/diagnostic modes)
- Obsidian-backed workspace notes (when enabled)
- Optional graph context
- Verified personal facts

The final prompt sent to the model can be substantially longer than the user's raw message.

**Implication for Whoosh'd:** Expect large prompts. Codexify packs substantial context. Whoosh'd should support generous context windows. `confirmed`

### 5. Image/Vision Turns

Codexify can include images in chat turns. The completion service checks model vision capability before execution. Images are passed as base64 data URIs or URLs in the OpenAI-compatible message format.

**Implication for Whoosh'd:** If Whoosh'd serves multimodal MLX models, it should accept images in the standard OpenAI vision format. `confirmed`

### 6. Embedding Workflows

Codexify generates embeddings for messages and documents using a separate embedding model (currently BGE-large-en-v1.5 via sentence-transformers). Embeddings are used for semantic retrieval, not passed through the chat provider.

**Implication for Whoosh'd:** Embedding inference is a separate concern from chat completions. Whoosh'd should support `/v1/embeddings` endpoint if it wants to replace the embedding provider as well, but this is secondary to chat. `inferred`

### 7. TTS / Audio

Codexify has optional TTS (text-to-speech) capabilities via a separate microservice. The chat worker can auto-generate audio for assistant responses.

**Implication for Whoosh'd:** Not a core inference requirement. Low priority. `confirmed`

## Inference Patterns

### How Codexify Calls Models Today

Codexify communicates with local models via two endpoint patterns:

1. **OpenAI-compatible:** `POST {LOCAL_BASE_URL}/v1/chat/completions` with `{"stream": true}`
2. **Ollama-native:** `POST {LOCAL_BASE_URL}/api/chat` with `{"stream": true}`

The backend tries OpenAI-compat first, falls back to Ollama-native. Both use standard HTTP with `Authorization: Bearer {api_key}` headers.

**Source:** `guardian/core/ai_router.py::stream_local()` — `confirmed`

### Request Format (OpenAI-compatible)

```json
{
  "model": "model-name",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.7,
  "stream": true
}
```

With images:
```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "..."},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
  ]
}
```

**Source:** `guardian/core/ai_router.py` — `confirmed`

### Response Format (Streaming)

Codexify expects SSE-style streaming with `data:` prefixed JSON lines and `data: [DONE]` termination:

```
data: {"choices":[{"delta":{"content":"Hello"}}]}

data: {"choices":[{"delta":{"content":" world"}}]}

data: [DONE]
```

The chat worker extracts visible text from the stream using `_extract_visible_stream_text()` which specifically enforces "content only, never reasoning."

**Source:** `guardian/workers/chat_worker.py::_extract_visible_stream_text()` — `confirmed`

### Non-Streaming

Codexify's primary path uses streaming. Non-streaming is also supported via the same endpoints.

**Source:** `guardian/core/ai_router.py` — `confirmed`

### Timeout Behavior

Codexify uses a structured timeout policy through `LocalRuntimePolicy`:

| Timeout | Default | Purpose |
|---------|---------|---------|
| Connect timeout | configurable | Transport-level: connection refused, DNS failure |
| Read timeout | configurable | Waiting for response data |
| Warmup timeout | 90s (default) | Model loading/compilation |
| First-token timeout | inferable from read timeout | Time between model acceptance and first token |

**Source:** `guardian/core/ai_router.py::LocalRuntimePolicy`, `guardian/workers/warmup_worker.py` — `confirmed`

**Critical:** The system explicitly warns against collapsing these timeouts into a single "provider offline" judgment. `confirmed`

## Model Routing Requirements

### Provider Abstraction

Codexify has a provider registry with governance categories:

| Category | Providers | Meaning |
|----------|-----------|---------|
| `local_only` | `local` | Local execution, no cloud dependency |
| `static_authorized` | `openai`, `groq` | Cloud providers with static model descriptors |
| `discovery_backed` | `alibaba`, `minimax` | Cloud providers with live inventory discovery |
| `disabled` | `anthropic`, `gemini` | Known but unavailable |

**Source:** `docs/architecture/system-overview.md`, `docs/infra/system_architecture.md` — `confirmed`

### Local Model Resolution

The local provider is currently Ollama. Codexify resolves the local model through a priority chain:

1. `LOCAL_CHAT_MODEL` (authoritative in strict/local-only mode)
2. `LOCAL_LLM_MODEL`
3. `DEFAULT_LOCAL_MODEL`
4. `LLM_MODEL`

Model availability is validated against the Ollama `/api/tags` endpoint.

**Source:** `guardian/core/ai_router.py::resolve_local_execution_model()` — `confirmed`

### Model Listing / Discovery

Codexify calls the local model listing endpoint to discover available models. For Ollama, this is `GET /api/tags`. The `discover_local_model_inventory()` function probes this.

**Implication for Whoosh'd:** Whoosh'd should implement a model listing endpoint equivalent to Ollama's `/api/tags` or a separate discovery mechanism. `confirmed`

### Fallback Behavior

When a non-local (cloud) provider fails, the chat worker may rescue once to local inference if:
- The selection was not explicit, or
- Explicit local fallback is enabled and the provider was not pinned

The terminal payload records this as `fallback_reason="cloud_failure_local_rescue"`. This is execution degradation, not silent success.

**Source:** `docs/architecture/completion_pipeline.md`, `guardian/workers/chat_worker.py` — `confirmed`

### MLX Model Assumptions

Codexify currently uses Ollama as its local backend. It has no explicit MLX awareness. The local model interface is purely OpenAI-compatible HTTP.

**Implication for Whoosh'd:** Whoosh'd should present the same OpenAI-compatible HTTP interface that Ollama presents. MLX-specific optimizations (shared memory, batched inference) are an implementation detail behind this interface. `needs-owner-decision`

## Concurrency and Queueing Requirements

### Worker Concurrency

The chat worker defaults to **2 concurrent task executors** (`CHAT_WORKER_CONCURRENCY=2`). Tasks are submitted to a `ThreadPoolExecutor`.

**Source:** `guardian/workers/chat_worker.py::CONCURRENCY` — `confirmed`

### Additional Workers

Codexify runs multiple worker processes, each with its own concurrency:

| Worker | Queue | Purpose |
|--------|-------|---------|
| `worker-chat` | `codexify:queue:chat` | Chat completion (2 concurrent) |
| `worker-coding` | coding execution queue | Agent/coding task execution |
| `worker-chat-embed` | `codexify:queue:chat-embed` | Message embedding |
| `worker-document-embed` | `codexify:queue:document-embed` | Document embedding |
| `worker-warmup` | `codexify:queue:system` | Model warm-up |
| `worker-voice` | voice queue | TTS audio generation |
| `worker-cron` | cron queue | Scheduled job execution |

**Source:** `docker-compose.yml`, `guardian/workers/` — `confirmed`

### Queueing Model

Codexify uses Redis-backed task queues:
- `codexify:queue:chat` — chat completion tasks
- `codexify:queue:chat-embed` — message embedding jobs
- `codexify:queue:document-embed` — document embedding jobs
- `codexify:queue:system` — warmup tasks

Tasks are enqueued as JSON payloads. Workers `dequeue()` with blocking timeout.

**Source:** `guardian/queue/redis_queue.py` — `confirmed`

### Request Priority

Codexify does not currently implement request priority. All chat tasks go into a single Redis queue and are processed in FIFO order.

**Implication for Whoosh'd:** Codexify currently does not differentiate between urgent and background inference. If Whoosh'd supports priority lanes, Codexify would need to be adapted to use them — but this is a Codexify concern, not a Whoosh'd concern. `inferred`

### Cancellation

Codexify supports cancellation via a Redis-based cancellation set. The chat worker checks `is_cancelled(task.task_id)` before and during execution. Cancelled tasks publish `task.cancelled` events and are cleared from the cancellation set.

**Implication for Whoosh'd:** Whoosh'd should support request cancellation — ideally by dropping the in-flight generation when the client disconnects or sends an explicit cancel signal. `confirmed`

## Streaming Requirements

### SSE-Style Streaming

Codexify expects the provider to stream responses as `data:` prefixed JSON lines over HTTP chunked transfer encoding, terminated by `data: [DONE]`.

**Source:** `guardian/core/ai_router.py::stream_local()` — `confirmed`

### Content-Only Stream Extraction

The chat worker explicitly extracts only visible text content from streams: `_extract_visible_stream_text()` enforces "content only, never reasoning." Codexify does not pass through chain-of-thought or reasoning tokens to the UI.

**Implication for Whoosh'd:** If Whoosh'd serves reasoning-capable models, the reasoning content should be separable from the visible response. Codexify currently discards reasoning. `confirmed`

### Token-Level Progress

The worker publishes `task.progress` events with individual tokens (truncated to 4096 chars) and `task.chunk` events with deltas. These flow through Redis task event streams to the frontend via SSE.

**Source:** `guardian/workers/chat_worker.py::_run_chat_task()` — `confirmed`

### First-Token Latency

Codexify tracks `awaiting_first_token_at` → `first_token_at` as a lifecycle timing field. Fast first-token times are important for perceived responsiveness.

**Implication for Whoosh'd:** Low time-to-first-token (TTFT) is critical for Codexify's UX. Whoosh'd should optimize for this. `confirmed`

## Context, RAG, and Prompt Assembly

### Prompt Structure

Before reaching the provider, Codexify assembles a complete prompt package:

```
[System message] — built by build_guardian_system_prompt()
  ├── Persona/profile instructions
  ├── Verified personal facts (when present)
  ├── Retrieval context prefix (source mode, identity scope)
  └── Tool-use instructions (when applicable)

[Context message] — built by ContextBroker
  ├── Semantic retrieval results
  ├── Thread/project document context
  ├── Memory retrieval (deep/diagnostic modes)
  └── Optional graph/federated context

[Conversation messages] — recent thread history
  ├── User messages
  └── Assistant messages
```

**Source:** `guardian/core/chat_completion_service.py`, `guardian/context/broker.py`, `guardian/cognition/system_prompt_builder.py` — `confirmed`

### Context Assembly Policy

The retrieval router defines source modes:

| Source Mode | Included Evidence | Required |
|---|---|---|
| `conversation` | Thread messages only | None |
| `project` | Thread + semantic + docs | None |
| `personal_knowledge` | Thread + semantic + memory + obsidian | `obsidian` |
| `obsidian_only` | Thread + obsidian | `obsidian` (fails closed if none) |
| `workspace` | Thread + semantic + obsidian + memory | User-bounded |

**Source:** `docs/architecture/router-decision-table.md`, `guardian/context/retrieval_router_policy.py` — `confirmed`

### Prompt Size

Codexify can generate very large prompts, especially in `deep` or `workspace` modes. The system prompt, context bundle, and thread history can collectively reach thousands of tokens.

**Implication for Whoosh'd:** Support large context windows. MLX models with generous context limits (32K-128K+) will be valuable. `confirmed`

### Prompt Caching

For the MiniMax/Anthropic-compatible path, Codexify uses prompt caching with `cache_control: {type: "ephemeral"}` on stable system/tool prefixes. This is provider-specific and not currently used for the local path.

**Implication for Whoosh'd:** Prompt caching could significantly reduce latency for Codexify's large, stable system prompts. If Whoosh'd can implement KV-cache reuse across requests with similar system prefixes, this would be a competitive advantage. `needs-owner-decision`

## Persona and Identity Boundaries

### Persona System

Codexify has a Persona system that defines:
- System prompt tone and behavior
- Voice/style preferences
- Retrieval source mode preferences
- Active memory tag filters

Personas are selected per-thread and are injected into the system prompt before inference.

**Source:** `docs/architecture/persona-studio.md`, `docs/infra/persona_system_architecture.md` — `confirmed`

**Current Status:** Persona Studio is a frontend-local configuration surface. Runtime application is partially wired. `confirmed`

### Identity Isolation

In `multi_user` mode:
- Every entity belongs to exactly one `user_id`
- Retrieval MUST NOT cross user boundaries
- Context assembly must be user-scoped
- No entity may depend on another user's private data

**Source:** `docs/architecture/identity-and-runtime-mode.md` — `confirmed`

**Implication for Whoosh'd:** Whoosh'd does not need to enforce user isolation — Codexify's backend handles that. But Whoosh'd must not leak cached responses, KV-cache state, or model state across requests from different users. `confirmed`

### Session Ownership

Codexify manages session/thread ownership at the application layer. Whoosh'd does not need session awareness. However, if Whoosh'd implements any form of request affinity or sticky sessions, it must respect Codexify's ownership boundaries.

`inferred`

## API Surface Codexify Likely Needs

### Required Endpoints

Based on Codexify's current local provider interface:

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/v1/chat/completions` | POST | Chat completion (streaming + non-streaming) | **Critical** |
| `/api/chat` | POST | Ollama-native chat (fallback) | High |
| `/api/tags` | GET | Model listing/discovery | **Critical** |
| `/v1/models` | GET | OpenAI-compatible model list | High |
| `/api/generate` | POST | Ollama-native generate (fallback for non-chat) | Medium |
| Health endpoint | GET | Runtime availability check | High |

`confirmed` for `/v1/chat/completions` and `/api/tags`; `inferred` for the rest based on Codexify's current Ollama interface.

### Health Check Surface

Codexify's health endpoints:

| Endpoint | What it checks |
|----------|---------------|
| `/health` | Overall system health, supported profile alignment |
| `/health/chat` | Redis reachability, queue depth, worker heartbeat |
| `/api/health/llm` | Active provider runtime status, completion service health |
| `/ping` | Simple liveness check (no auth) |

**Implication for Whoosh'd:** Codexify probes the local model endpoint to determine provider health. Whoosh'd should provide a health endpoint that clearly distinguishes:
- Transport reachability (process alive, port open)
- Model loading/warming status
- Ready to serve

`confirmed`

### Metrics

Codexify exposes `/metrics` for Prometheus scraping. The backend initializes Prometheus metrics during startup.

`confirmed`

### Model Warm-Up

Codexify's `worker-warmup` sends a probe request to the local model to trigger weight loading. It retries up to 5 times with exponential backoff (default 1s base, 8s max, 90s total warmup timeout).

**Implication for Whoosh'd:** Whoosh'd should handle a warm-up probe gracefully — return a meaningful response that distinguishes "model loading" from "error" without consuming inference resources. A lightweight `/health` ping that triggers model loading would be ideal. `confirmed`

## Observability and Debugging Needs

### What Codexify Logs/Metrics

Codexify tracks per-request:
- `client_send_ts`, `server_ack_ts`, `model_load_start_ts`, `model_ready_ts`
- `first_token_ts`, `stream_end_ts`, `timeout_ts`
- `transport_latency`, `ack_latency`, `model_warmup_latency`, `first_token_latency`, `total_completion_latency`
- `provider`, `model`, `attempt_number`, `wasReplay`

**Source:** `docs/architecture/request-state-machine.md` — `confirmed`

### Request/Response Logging

The AI router logs structured inference requests with:
```
chat.inference.request.built {
  provider, model, endpoint_kind, has_images,
  message_count, content_part_counts, stream
}
```

**Source:** `guardian/core/ai_router.py::stream_local()` — `confirmed`

### Debug Surfaces

- `GET /debug/rag-trace/{thread_id}/latest` — dev-only, in-memory, non-durable
- `GET /api/tasks/{task_id}/events` — task event stream
- Worker logs with prefix like `[chat-worker]`, `[task]`, `[turn-lock]`

`confirmed`

### What Whoosh'd Should Expose

For effective debugging:
1. Per-request latency breakdown (queue time, load time, generation time)
2. Model loading/warming status
3. Active request count
4. Queue depth (if Whoosh'd has internal queuing)
5. Token throughput metrics
6. Error classification (timeout vs model error vs client error)

`needs-owner-decision`

## Security, Privacy, and Sovereignty Requirements

### Local-First Operation

Codexify's supported beta posture is `local_only`:
- `CODEXIFY_LOCAL_ONLY_MODE=true`
- `ALLOW_CLOUD_PROVIDERS=false`
- `LLM_PROVIDER=local`

All inference data stays on the local machine. Cloud providers are explicitly gated behind configuration flags.

**Source:** `docs/architecture/00-current-state.md`, `README.md` — `confirmed`

### API Key Handling

Codexify sends `Authorization: Bearer {api_key}` to the local provider. For local-only mode, this is typically `local` or a configured key. The key is stored server-side in environment variables and never exposed to the frontend in production.

**Source:** `guardian/core/ai_router.py`, `README.md` — `confirmed`

### Data Retention

Codexify does not retain prompts or responses in the inference layer. Everything is persisted in Postgres at the application layer. The inference provider is stateless from Codexify's perspective.

**Implication for Whoosh'd:** Whoosh'd should be stateless or explicitly document any caching/retention behavior. Minimal retention of prompts/responses is preferred unless explicitly configured. `inferred`

### Network Exposure

Codexify runs entirely within Docker Compose by default. The local model endpoint is accessed via `host.docker.internal` or `localhost`. No public network exposure is assumed for local inference.

**Implication for Whoosh'd:** Bind to localhost by default. Support configurable bind addresses. `confirmed`

### Privacy-First Defaults

Codexify is explicitly local-first and privacy-respecting. All data remains on the user's machine. This is a core product value.

**Implication for Whoosh'd:** Whoosh'd must not phone home, send telemetry without explicit opt-in, or log prompts/responses externally by default. `confirmed`

### Auth Boundaries

Codexify uses `X-API-Key` header for backend auth (dev/trusted environments) and session/JWT for remote deployments. The inference provider itself is accessed with a bearer token.

**Implication for Whoosh'd:** Support a simple API key/bearer token auth mechanism. Default to permissive local auth. `confirmed`

## Deployment Assumptions

### Hardware

Codexify's current supported path targets:
- macOS (macOS-first, Tauri desktop shell)
- Docker Compose on a single machine
- Apple Silicon (inferred from MLX/Ollama usage)

**Source:** `README.md`, `docker-compose.yml` — `confirmed`

### Mac mini / Mac Studio

Codexify is designed to run on a single machine — typically a Mac with sufficient RAM for local models. The Tauri desktop shell is macOS-first.

**Implication for Whoosh'd:** Whoosh'd should run well on Apple Silicon Macs (M1/M2/M3/M4) with configurable RAM usage. This is the primary deployment target. `confirmed`

### Single-Node Architecture

Codexify operates on a single machine. There is no distributed inference, no model sharding across nodes, no load balancing across multiple inference servers.

**Source:** `docs/architecture/system-overview.md` — `confirmed`

### Scaling with RAM

Codexify's performance scales with available RAM for larger models. The embedding model (BGE-large-en) and chat model both need to fit in memory.

**Implication for Whoosh'd:** RAM-efficient model loading (MLX shared weights, lazy loading) is valuable. Support for multiple concurrent models in RAM would be ideal (e.g., a small fast model + a large capable model). `inferred`

### Restart Behavior

Codexify expects the model provider to be available when the backend starts. The warmup worker handles model preloading. If the provider goes down, Codexify marks it as `OFFLINE` after repeated probe failures.

**Implication for Whoosh'd:** Whoosh'd should survive restarts cleanly and reload models on startup. Provide clear signals about loading status during startup. `confirmed`

### ThreadWake Cache / Warm-Cache Concepts

Codexify has a `worker-warmup` that preloads models. The term "ThreadWake Cache" is not used in Codexify's codebase, but the concept maps to Codexify's model warm-up behavior.

**Implication for Whoosh'd:** If Whoosh'd implements KV-cache warming or prompt prefix caching, this would benefit Codexify's large system prompts. `needs-owner-decision`

## Design Implications for Whoosh'd

### 1. Interface Compatibility

**Highest Priority:**
- Implement OpenAI-compatible `/v1/chat/completions` with streaming (`stream: true`)
- Implement model listing endpoint (Ollama-compatible `/api/tags` or OpenAI-compatible `/v1/models`)
- Support standard `Authorization: Bearer` header
- Return SSE-style streaming responses with `data: [DONE]` termination

### 2. State Reporting

**Critical:**
- Expose provider state distinctions (offline vs warming vs ready vs generating vs degraded)
- Health endpoint must differentiate "process alive" from "model loaded"
- Never report "offline" during model warm-up

### 3. Concurrency

**Important:**
- Support at least 2 concurrent chat completions (Codexify's default)
- Handle concurrent embedding requests separately from chat
- Reasonable target: 4-8 concurrent chat requests for headroom

### 4. Latency Profile

**Important:**
- Minimize time-to-first-token (Codexify tracks and exposes this)
- Handle large context windows efficiently (Codexify packs substantial context)
- Support prompt sizes up to 32K tokens minimum, 128K+ ideally

### 5. Cancellation

**Important:**
- Support request cancellation (drop in-flight generation)
- Respond to client disconnect by stopping generation

### 6. Model Management

**Important:**
- Support loading/unloading models without restart
- Report model loading status accurately
- Support warm-up probes that trigger loading without full inference

### 7. MLX-Specific Optimizations

**Competitive Advantage:**
- Shared model weights across concurrent requests (MLX can share loaded weights)
- Prompt prefix caching / KV-cache reuse (Codexify's system prompts are large and stable)
- Batched inference when multiple requests queue up
- Model quantization options (Codexify users may have limited RAM)

### 8. Security

**Required:**
- Bind to localhost by default
- No telemetry without explicit opt-in
- No external logging of prompts/responses
- Simple API key auth (accept any bearer token in dev, configurable in prod)

## Unknowns and Questions

### Unknown: MLX Model Compatibility

| Question | Status |
|----------|--------|
| Does Codexify have any MLX-specific model requirements? | `unknown` — Codexify currently uses Ollama, which may use llama.cpp or MLX backends. |
| Will Codexify adopt MLX-native model formats? | `unknown` — No evidence in current codebase. |
| Does Codexify need specific MLX model quantization formats? | `unknown` |

### Unknown: Performance Requirements

| Question | Status |
|----------|--------|
| What tokens-per-second is considered acceptable? | `unknown` — Not specified in architecture docs |
| What is the maximum acceptable TTFT? | `unknown` — Not specified, but the code tracks it |
| What is the minimum context window size? | `inferred` — At least 8K based on prompt assembly patterns, likely 32K+ |

### Unknown: Multi-Model Support

| Question | Status |
|----------|--------|
| Does Codexify need to switch between models mid-session? | `inferred` — The current code supports provider/model selection per-request |
| Does Codexify need multiple models loaded simultaneously? | `unknown` — Chat model + embedding model are separate, but the embedding model runs in-process |

### Needs Owner Decision

| Question | Recommendation |
|----------|---------------|
| Should Whoosh'd implement Ollama-compatible `/api/tags` or OpenAI-compatible `/v1/models`? | Implement both — `/v1/models` for standards compliance, `/api/tags` for Codexify compatibility |
| Should Whoosh'd implement `/api/chat` (Ollama-native) or only `/v1/chat/completions`? | Implement both if possible — Codexify tries OpenAI-compat first, falls back to Ollama-native |
| Should Whoosh'd support prompt prefix caching? | Yes — this would significantly benefit Codexify's large, stable system prompts |
| Should Whoosh'd support batched inference? | Yes — Codexify runs concurrent workers, and batching would improve throughput |
| Should Whoosh'd expose MLX-specific endpoints? | Consider it — MLX shared memory could reduce load times for model switching |

## Recommended First Implementation Targets

Based on what Codexify actually needs to function, in priority order:

### Tier 1: Basic Replacement (MVP)
1. **OpenAI-compatible `/v1/chat/completions`** with streaming
2. **Model listing endpoint** (`/api/tags` and/or `/v1/models`)
3. **Health check** that distinguishes process-alive from model-ready
4. **Basic auth** (accept any bearer token)
5. **Cancellation** support

### Tier 2: Production Readiness
6. **Multiple concurrent requests** (2-4 minimum)
7. **Model warm-up** with accurate status reporting
8. **Large context windows** (32K+ tokens)
9. **Request logging/metrics** (latency breakdown)
10. **Graceful error handling** (distinguish timeout from model error)

### Tier 3: Optimization
11. **Prompt prefix caching** / KV-cache reuse
12. **Batched inference** for concurrent requests
13. **Multi-model support** (fast + capable models)
14. **MLX shared memory** for fast model switching
15. **Embedding endpoint** (`/v1/embeddings`)

---

*Last updated: 2026-05-15*
*Source: Codexify repository at `main` tip, architecture docs, worker code, runtime contracts*
