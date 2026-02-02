# Completion Request Pipeline (Current Runtime)

## Goal and Non-Goals

- Goal: explain the runtime flow for one user message -> one assistant completion as it exists today.
- Non-goals: product marketing, speculative/future architecture, or re-design proposals.

## Actors and Responsibilities

- API entrypoints (thread message + completion enqueue): `guardian/routes/chat.py` (`chat_post_message`, `chat_complete`)
- Task queue + task events: `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`
- Completion worker + message assembly: `guardian/workers/chat_worker.py` (`_build_messages_for_llm`, `_run_chat_task`)
- Context assembly: `guardian/context/broker.py` (`ContextBroker.assemble`)
- System prompt builder: `guardian/cognition/system_prompt_builder.py` + `guardian/cognition/prompts.py`
- Provider routing (local/cloud): `guardian/core/ai_router.py` (local/groq/openai)
- Legacy Groq helper (non-worker path): `guardian/core/dependencies.py::_groq_complete`
- Persistence sinks:
  - Chat DB + audit log: `guardian/core/chat_db.py` (via `chatlog_db` in routes/worker)
  - Embeddings: `guardian/vector/store.py` (auto-embed on message write)
  - Event outbox (optional): `guardian/core/event_bus.py` (enabled via `ENABLE_OUTBOX`)
  - Graph logging (optional, user messages): `guardian/routes/chat.py` + `guardian/workers/graph_backfill_worker.py`

## High-Level Flow (Diagram)

```
UI
  -> POST /api/chat/{thread_id}/messages
     -> chatlog_db + event_bus + vector_store (+ optional Neo4j)
  -> POST /api/chat/{thread_id}/complete
     -> Redis queue (ChatCompletionTask)
     -> chat_worker
        -> ContextBroker.assemble()
        -> build_guardian_system_prompt()
        -> assemble messages[]
        -> ai_router call (local/groq/openai)
        -> persist assistant message + embed + task.completed
```

## Step-by-Step Request Flow (Atomic)

1) UI posts the user message  
   - `POST /api/chat/{thread_id}/messages` -> `guardian/routes/chat.py::chat_post_message`  
   - Persists to chat DB (`chatlog_db.create_message`) and audit log.  
   - Emits `event_bus.emit_event("message.created", ...)`.  
   - Auto-embeds into vector store with metadata (`thread_id`, `role`, `message_id`, `timestamp`, `source="chat"`).  
   - Optional Neo4j graph logging if `GUARDIAN_ENABLE_GRAPH_LOGGING=true` and graph deps are available.

2) UI requests a completion  
   - `POST /api/chat/{thread_id}/complete` -> `guardian/routes/chat.py::chat_complete`  
   - Validates thread + context; enqueues `ChatCompletionTask` to Redis via `guardian/queue/redis_queue.py::enqueue`.  
   - Emits `task.created` to task events stream (`guardian/queue/task_events.py`).  
   - Failure points: thread not found (404), queue unavailable (503).

3) Worker dequeues task  
   - `guardian/workers/chat_worker.py::run_forever` -> `_run_chat_task`  
   - If task cancelled, emits `task.cancelled` and exits.

4) Worker loads recent messages  
   - `_build_messages_for_llm` calls `chatlog_db.list_messages(...)` (default `max_context=50`).  
   - Uses latest user message as the RAG query.  
   - Failure points: missing thread, empty context.

5) Context assembly  
   - `ContextBroker.assemble(thread_id, query, depth_mode, user_id)` in `guardian/context/broker.py`.  
   - Errors are soft: failures are logged and the bundle defaults to empty lists.

6) System prompt construction  
   - `build_guardian_system_prompt(...)` in `guardian/cognition/system_prompt_builder.py`.  
   - Assembles base + depth + imprint + persona + system docs + RAG hint blocks.  
   - Truncates only system docs first when over budget; hard-truncates the tail if still over.

7) Provider payload assembly  
   - `_build_messages_for_llm` builds the final message array:  
     - system prompt (required)  
     - optional context system message (from `build_context_system_message`)  
     - recent verbatim turns from the thread  

8) Provider call + timeouts  
   - `guardian/core/ai_router.py::chat_with_ai` routes to:
     - `call_local` -> 30s timeout (OpenAI-compatible local server)
     - `call_groq` -> 30s timeout
     - `call_openai` -> 30s timeout
     - `stream_local` uses `LLM_REQUEST_TIMEOUT_SECONDS` (default 60s)
   - Failure points: provider config errors, request timeouts, upstream errors.  
   - Retry behavior: no retry in the worker path. The legacy `_groq_complete` path (used by `/chat`) retries once with a fallback model if configured.

9) Response guard + persistence  
   - Response is sanitized by `guardian/core/message_guard.py`.  
   - Assistant message is persisted (`chatlog_db.create_message`), audit log updated.  
   - Emits `event_bus.emit_event("message.created", ...)`.  
   - Auto-embeds assistant message in vector store.  
   - Publishes `task.completed` with `{provider, model, trace}` in task events stream.

## What Exactly Is in the Context Bundle

Source: `guardian/context/broker.py::ContextBroker.assemble`

Keys produced today:
- `messages`: recent thread messages (always present)
- `semantic`: vector-store search results (empty list for `shallow`)
- `graph`: graph-derived snippets (empty list unless enabled)
- `memory`: memory search results (deep/diagnostic only)
- `sensors`: sensor snapshot (diagnostic only)
- `federated`: federated search results (only when `federated=True`)

Depth modes (current behavior):
- `shallow`: `messages`, `semantic` (empty), `graph` (empty unless enabled)
- `normal`: `messages`, `semantic`, `graph` (optional)
- `deep`: `messages`, `semantic`, `graph`, `memory`
- `diagnostic`: `messages`, `semantic`, `graph`, `memory`, `sensors`

Notes:
- The broker returns raw chat messages and retrieved snippets as-is; it does not rewrite or summarize them.
- `graph` is gated by `GUARDIAN_ENABLE_GRAPH_CONTEXT` (see `guardian/core/config.py`).
- The chat worker additionally attaches `user_system_override` to the bundle if provided, but it is not currently used in prompt assembly.
- `rag_trace` is returned separately and includes only semantic + graph summaries (snippets truncated to ~100 chars).

## What Exactly Is in the System Prompt

Source: `guardian/cognition/system_prompt_builder.py`, `guardian/cognition/prompts.py`

Blocks (in order):
1) Immutable base rules (`_base_codexify_system_prompt`)
2) Depth mode block (`_depth_block`)
3) Imprint style block (`_imprint_zero_style_block`) via `guardian/cognition/imprints/store.py`
4) User persona block (`_user_persona_block`) via `guardian/cognition/personas/store.py`
5) System docs block (`_system_docs_block`) via `guardian/cognition/system_docs/store.py`
6) RAG hint block (`_rag_hint_block`) (light hints only, no snippets)

Truncation rules and token cap:
- Heuristic token estimate: `len(text) // 4`.
- Default cap: 2000 tokens (can be overridden by caller).
- If over cap: system docs are truncated first, preserving base/depth/imprint/persona.
- If still over cap: hard truncate the tail and append `[TRUNCATED DUE TO TOKEN BUDGET]`.

## Provider Payload Shape (Conceptual)

Source: `guardian/workers/chat_worker.py::_build_messages_for_llm`, `guardian/core/ai_router.py`

```pseudo
messages = [
  {"role": "system", "content": system_prompt},
  {"role": "system", "content": context_snippets},  # optional
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "..."},
  {"role": "user", "content": "..."},
]

payload = {
  "model": resolved_model,
  "messages": messages,
  "temperature": 0.7,
}
```

Not included:
- Full thread history beyond `max_context`
- Raw embedding vectors or store internals
- Untruncated system docs beyond the token cap
- Federated context (not enabled in the chat worker path)

## Persistence After Completion

- Assistant message persisted to chat DB: `guardian/workers/chat_worker.py` -> `chatlog_db.create_message`
- Audit log entry: `chatlog_db.write_audit_log`
- Embedding write (assistant message): `guardian/vector/store.py::VectorStore.add_texts`
  - Metadata: `thread_id`, `role`, `message_id`, `timestamp`, `source="chat"`
- Task events stream update: `task.completed` with provider/model/trace in `guardian/queue/task_events.py`
- Event outbox (optional): `guardian/core/event_bus.py` when `ENABLE_OUTBOX=true`
- Graph logging:
  - User messages are logged directly in `guardian/routes/chat.py` when enabled.
  - Assistant messages are not written in the worker; graph backfill (`guardian/workers/graph_backfill_worker.py`) can ingest from DB if configured.

## Debugging Checklist

- Logs
  - API: `guardian/routes/chat.py` ([chat] logger)
  - Worker: `guardian/workers/chat_worker.py` ([chat-worker], [task])
  - Context: `guardian/context/broker.py` ([ContextBroker])
- Confirm provider/model
  - Read `task.completed` from `codexify:task:{task_id}:events` (via `guardian/queue/task_events.py`)
  - Worker logs include provider/model in task completion data
- Verify assembled context
  - `GET /api/chat/debug/rag-trace/{thread_id}/latest` (`guardian/routes/chat.py`)
  - Note: rag_trace exposes semantic + graph only; memory hits are logged but not surfaced in the trace payload.
- Confirm prompt truncation
  - Look for `[chat-worker] large system prompt` warnings (token estimate > 2048)
