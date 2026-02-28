# Tech Debt and Risks

Purpose: Maintain an actionable, evidence-linked risk register for architecture and runtime debt that can regress reliability, security, or delivery speed.
Last updated: 2026-02-17
Source anchors:
- guardian/guardian_api.py
- guardian/routes/chat.py
- guardian/workers/chat_worker.py
- guardian/context/broker.py
- guardian/core/config.py
- guardian/config/core.py
- guardian/routes/media.py
- guardian/workers/document_embed_worker.py
- guardian/routes/tools.py
- guardian/sync/bus.py
- guardian/routes/rag_upload.py
- guardian/routes/codexify_router.py
- guardian/core/ai_router.py
- guardian/core/llm_catalog.py
- guardian/routes/federation.py
- guardian/core/egress.py
- docker-compose.yml

- Risk: Import-time `VectorStore()` construction can fail route module loading and break startup under missing embed model conditions. | Subsystem: `embedding/bootstrap` | Severity: high | Evidence: `guardian/routes/codexify_router.py`, `backend/rag/embedder.py` | Mitigation: Move heavy initialization behind startup factory and lazy dependency injection.
- Risk: Chat completion availability depends on Redis queue health with limited graceful degradation. | Subsystem: `chat/queue` | Severity: high | Evidence: `guardian/routes/chat.py`, `guardian/queue/redis_queue.py` | Mitigation: Add queue health gating plus fallback mode or clearer degraded-state signaling.
- Risk: Chat worker combines retrieval, prompting, provider execution, persistence, and events in one module, increasing regression blast radius. | Subsystem: `chat-worker` | Severity: high | Evidence: `guardian/workers/chat_worker.py` | Mitigation: Split into explicit stage functions with contract tests per stage.
- Risk: Provider catalog can advertise providers the runtime router cannot execute (`anthropic`, `gemini`). | Subsystem: `provider-routing` | Severity: medium | Evidence: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py` | Mitigation: Enforce shared provider capability source and deny unsupported options at catalog build time.
- Risk: Dual config systems increase startup complexity and mismatch risk. | Subsystem: `config` | Severity: high | Evidence: `guardian/core/config.py`, `guardian/config/core.py` | Mitigation: Deprecate one settings path and keep one canonical schema + migration plan.
- Risk: Dotenv load ordering intent and effective precedence can diverge because all layers load with `override=False`. | Subsystem: `config` | Severity: medium | Evidence: `guardian/core/dependencies.py` | Mitigation: Document/implement deterministic precedence explicitly and add regression tests for layer overrides.
- Risk: Tool execution jobs are stored in an in-memory dict and are lost on restart. | Subsystem: `tools` | Severity: medium | Evidence: `guardian/routes/tools.py` | Mitigation: Persist tool jobs in Postgres/Redis using existing task model patterns.
- Risk: Sync event bus is process-local; no replay/durability guarantees for subscribers. | Subsystem: `sync` | Severity: medium | Evidence: `guardian/sync/bus.py`, `guardian/sync/api.py` | Mitigation: Back sync publish/subscribe with Redis streams or outbox table.
- Risk: `upload-chat` RAG endpoint hard-depends on optional module and returns 503 when unavailable. | Subsystem: `rag-ingestion` | Severity: medium | Evidence: `guardian/routes/rag_upload.py` | Mitigation: Either remove endpoint from public contract or ship a guaranteed default implementation.
- Risk: Document embedding failures can leave uploads in failed state without built-in retry workflow. | Subsystem: `ingestion` | Severity: medium | Evidence: `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py` | Mitigation: Add retry queue + admin rerun endpoint based on `embedding_status`.
- Risk: Event outbox cleanup in stream loop could conflict with lagging consumers if tenant/id semantics drift. | Subsystem: `events` | Severity: medium | Evidence: `/api/events` logic in `guardian/guardian_api.py`, `guardian/core/event_bus.py` | Mitigation: Track consumer cursors separately from global delete-through logic.
- Risk: Redis in Compose is configured without persistence (`appendonly no`), so queued work/events can be lost on restart. | Subsystem: `ops/queue` | Severity: medium | Evidence: `docker-compose.yml` Redis command | Mitigation: Enable persistence in non-dev environments and document durability expectations.
- Risk: Federation path has strict policy/signature/env coupling and can fail closed with limited operator diagnostics. | Subsystem: `federation` | Severity: medium | Evidence: `guardian/routes/federation.py`, `guardian/core/config.py` | Mitigation: Add explicit startup validation endpoint and policy lint command.
- Risk: Webhook cron jobs rely on runtime egress policy and allowlist correctness; misconfigurations surface as runtime failures. | Subsystem: `cron/egress` | Severity: medium | Evidence: `guardian/routes/cron.py`, `guardian/cron/executor.py`, `guardian/core/egress.py` | Mitigation: Add dry-run validation endpoint for webhook target + policy preview.
- Risk: Sensitive user text is persisted broadly (chat content, parsed docs, generated docs) with encryption-at-rest assumptions not encoded in app logic. | Subsystem: `data-security` | Severity: high | Evidence: `guardian/db/models.py` content columns and media/doc tables | Mitigation: Define and enforce storage encryption/key-management controls at infra layer and document compliance boundaries.
- Risk: Local provider hostname resolution failures (especially `.local` in containers) are common and operationally expensive. | Subsystem: `provider-connectivity` | Severity: low | Evidence: error handling in `guardian/core/ai_router.py`, containerized topology in `docker-compose.yml` | Mitigation: Add startup connectivity preflight and explicit env validation for local base URL.
- Risk: Mixed-dimension embedding stores (after provider/model swaps) can reduce recall due to dimension-based skip behavior in retrieval paths. | Subsystem: `memoryos/embeddings` | Severity: medium | Evidence: dimension-safe guards in `guardian/memoryos/mid_term.py`, `guardian/memoryos/long_term.py` | Mitigation: Monitor skip-ratio telemetry and run an opt-in full re-embedding maintenance task when skip ratios stay elevated.
