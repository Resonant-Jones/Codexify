# Roadmap Signals (Derived)

Purpose: Surface decision-grade planning signals inferred from current code constraints and failure surfaces, without claiming product intent.
Last updated: 2026-02-17
Source anchors:
- guardian/guardian_api.py
- guardian/core/config.py
- guardian/config/core.py
- guardian/core/dependencies.py
- guardian/workers/chat_worker.py
- guardian/routes/chat.py
- guardian/queue/redis_queue.py
- guardian/routes/media.py
- guardian/workers/document_embed_worker.py
- guardian/routes/tools.py
- guardian/sync/api.py
- guardian/routes/rag_upload.py
- guardian/routes/codexify_router.py
- guardian/core/ai_router.py
- guardian/core/llm_catalog.py

## Top Constraints (From Code Reality)

1. Core chat completion is queue-coupled to Redis and worker availability.
   - Evidence: `guardian/routes/chat.py`, `guardian/workers/chat_worker.py`, `guardian/queue/redis_queue.py`.
2. Startup is fail-closed on auth key presence and config coherence checks.
   - Evidence: `guardian/guardian_api.py`, `guardian/core/config.py`.
3. Completion assembly is concentrated in one worker module with broad dependencies.
   - Evidence: `_build_messages_for_llm` and `_run_chat_task` in `guardian/workers/chat_worker.py`.
4. Config surface is split between core and legacy settings systems, reconciled at runtime.
   - Evidence: `guardian/core/config.py`, `guardian/config/core.py`.
5. Some execution surfaces are process-local/non-durable (tools jobs, sync bus).
   - Evidence: `guardian/routes/tools.py` (`JOBS` map), `guardian/sync/bus.py` (in-memory queues).

## Known Missing Pieces (Evidenced)

- RAG upload endpoint has optional dependency on `codexify.rag.enhanced_rag`; when missing it returns 503.
  - Evidence: `guardian/routes/rag_upload.py`.
- Provider catalog includes `anthropic`/`gemini`, but runtime `chat_with_ai` only supports `local`, `groq`, `openai`.
  - Evidence: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`.
- Tool job status is not durable across restart.
  - Evidence: in-memory `JOBS` dict in `guardian/routes/tools.py`.
- Sync subscribe bus is in-process only; no persistence/replay semantics.
  - Evidence: `guardian/sync/bus.py`, `guardian/sync/api.py`.
- Import-time side-effect risk exists via global `VectorStore()` construction in route modules.
  - Evidence: `guardian/routes/codexify_router.py`.

## High-Leverage Refactors (Recommendations)

1. **Remove import-time heavy initializers and shift to explicit startup factories.**
   - Why: reduce boot fragility and hidden transitive failures.
   - Anchors: `guardian/routes/codexify_router.py`, `guardian/core/dependencies.py`, `guardian/guardian_api.py`.
2. **Decompose chat worker into explicit stages with typed contracts (assemble -> generate -> persist -> emit).**
   - Why: isolate failures, simplify testing, make retry policy explicit.
   - Anchors: `guardian/workers/chat_worker.py`, `guardian/context/broker.py`, `guardian/core/ai_router.py`.
3. **Unify config system ownership (core vs legacy) behind one canonical read path.**
   - Why: remove startup mismatch class and lower operator confusion.
   - Anchors: `guardian/core/config.py`, `guardian/config/core.py`, tests under `tests/core/test_config_coherence.py`.
4. **Promote tool/sync execution state from memory to durable transport/store.**
   - Why: restart-safe operations and better observability.
   - Anchors: `guardian/routes/tools.py`, `guardian/sync/bus.py`, `guardian/queue/redis_queue.py`, `guardian/db/models.py`.
5. **Standardize provider capability contracts between catalog and runtime router.**
   - Why: avoid UX/runtime mismatch on selectable providers.
   - Anchors: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`, `frontend/src/components` provider selector tests.

## Stability Risks (Ranked 1-10)

- **10**: Import-time vector store initialization can fail module load/startup when local model path is unavailable.
  - Evidence: `guardian/routes/codexify_router.py`, `backend/rag/embedder.py`.
- **9**: Redis outage directly breaks completion enqueue and task event transport.
  - Evidence: `guardian/routes/chat.py`, `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`.
- **8**: Config coherence mismatch can block startup in strict mode.
  - Evidence: `guardian/core/config.py`.
- **8**: Chat worker is a high-coupling hotspot; regressions can simultaneously impact prompting, provider calls, and persistence.
  - Evidence: `guardian/workers/chat_worker.py`.
- **7**: Non-durable tool/sync state leads to silent loss after process restart.
  - Evidence: `guardian/routes/tools.py`, `guardian/sync/bus.py`.
- **7**: Provider catalog/runtime mismatch can produce selectable-but-unusable providers.
  - Evidence: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`.
- **6**: Ingestion parse/embed path can mark docs failed without retry orchestration.
  - Evidence: `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py`.
- **6**: Federation policy/env misconfiguration can hard-fail collaboration setup paths.
  - Evidence: `guardian/routes/federation.py`, `guardian/core/config.py`.
- **5**: Event outbox cleanup semantics could drop replay expectations if consumers lag or tenant config drifts.
  - Evidence: `/api/events` logic in `guardian/guardian_api.py`.
- **4**: Limited cron schedule grammar may constrain operations workflows.
  - Evidence: schedule validation in `guardian/routes/cron.py`.

## Sequencing Suggestions (Dependency-Aware)

1. **Stabilize startup boundaries first**: eliminate import-time heavy initialization and keep all service init in app/worker startup.
   - Anchors: `guardian/guardian_api.py`, `guardian/routes/codexify_router.py`, `guardian/core/dependencies.py`.
2. **Harden core loop observability and contracts**: formalize chat task stage boundaries and failure telemetry before feature expansion.
   - Anchors: `guardian/workers/chat_worker.py`, `guardian/queue/task_events.py`, `guardian/routes/chat.py`.
3. **Align provider/catalog behavior**: ensure UI-selectable providers are exactly those runtime can execute under current policy.
   - Anchors: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`, `frontend/src/lib/providerPref.ts`.
4. **Upgrade ingestion reliability**: add retry/backoff/idempotent recovery around document embedding failures.
   - Anchors: `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py`, `guardian/queue/document_embed_queue.py`.
5. **Make tool/sync paths durable**: migrate process-local registries/buses to Redis/Postgres-backed patterns already used in chat/cron.
   - Anchors: `guardian/routes/tools.py`, `guardian/sync/bus.py`, `guardian/queue/redis_queue.py`, `guardian/db/models.py`.
6. **Expand federation only after policy+telemetry hardening**: treat as high-blast-radius expansion after core-loop reliability targets are met.
   - Anchors: `guardian/routes/federation.py`, `guardian/core/auth.py`, `guardian/core/egress.py`.

