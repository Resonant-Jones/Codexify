# Codexify Architecture KB

Purpose: Provide a fast, implementation-accurate map of Codexify so contributors can onboard quickly, reason correctly about current behavior, and plan safe changes.
Last updated: 2026-02-17
Source anchors:
- README.md
- docker-compose.yml
- guardian/guardian_api.py
- guardian/routes/
- guardian/workers/
- guardian/db/models.py
- guardian/core/config.py
- frontend/src/App.tsx
- frontend/src/components/persona/layout/AppShell.tsx

## What Codexify Is

Codexify is a local-first chat and knowledge workspace with a FastAPI backend (`guardian/guardian_api.py`), a React frontend (`frontend/src`), Postgres-backed state, Redis-backed task queues/event streams, and optional graph/federation subsystems. The primary runtime path is thread-based chat where completion work is queued to workers, context is assembled from messages + retrieval layers, and results are persisted and streamed back via SSE/websocket surfaces.

## Architecture Doc Map

- [System Overview](./system-overview.md)
- [Critical Flows](./flows.md)
- [Data and Storage](./data-and-storage.md)
- [Config and Ops](./config-and-ops.md)
- [Modules and Ownership](./modules-and-ownership.md)
- [Roadmap Signals (Derived)](./roadmap-signals.md)
- [Tech Debt and Risks](./tech-debt-and-risks.md)
- [Solo Operator Runtime Bootcamp](./solo-operator-runtime-bootcamp.md)
- [Solo Operator System Map](../Ops/SOLO_OPERATOR_SYSTEM_MAP.md)
- [Solo Operator Automation Runbook](../Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md)
- [Solo Operator Failure Signatures](../Ops/SOLO_OPERATOR_FAILURE_SIGNATURES.md)
- [Inference Providers (Legacy Notes)](./providers.md)
- [Completion Pipeline (Legacy Deep Dive)](./completion_pipeline.md)

## Where To Change X

- Chat completion enqueue API: `guardian/routes/chat.py`
- Completion worker behavior and streaming: `guardian/workers/chat_worker.py`
- RAG/context assembly depth behavior: `guardian/context/broker.py`
- Provider/model routing and timeouts: `guardian/core/ai_router.py`
- Provider catalog and model selection UX payload: `guardian/core/llm_catalog.py`
- System prompt layering/profile selection: `guardian/cognition/system_prompt_builder.py`, `guardian/cognition/system_profiles/resolver.py`
- Document/image ingestion and media identity: `guardian/routes/media.py`, `guardian/services/document_parsers/`, `guardian/services/document_chunking.py`
- Document embedding queue worker: `guardian/workers/document_embed_worker.py`, `guardian/queue/document_embed_queue.py`
- Thread/document autosave + generation: `guardian/routes/documents.py`
- API bootstrap, middleware, SSE, router wiring: `guardian/guardian_api.py`
- Auth boundary (local vs remote/session JWT): `guardian/core/dependencies.py`, `guardian/core/public_exposure.py`
- DB schema entities and invariants: `guardian/db/models.py`, `guardian/db/migrations/versions/`
- Frontend shell routing/state: `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`
- Frontend API auth header behavior: `frontend/src/lib/api.ts`, `frontend/src/lib/authState.ts`
- Cron/task execution system: `guardian/routes/cron.py`, `guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py`
- Federation and peer trust policy: `guardian/routes/federation.py`, `guardian/core/auth.py`, `guardian/core/config.py`

## Keep This KB Current

- After touching runtime flows, update at least one of: `system-overview.md`, `flows.md`, `modules-and-ownership.md`.
- Add/refresh source anchors whenever a new critical file becomes part of a path.
- If behavior is uncertain, mark it `Unverified` and point to the exact verification file/endpoint.
- Keep “current state” docs descriptive; put recommendations only in `roadmap-signals.md`.
- When schema or queue contracts change, update both `data-and-storage.md` and `tech-debt-and-risks.md` in the same PR.
- Re-run docs validation (`make docs`) and fix broken links/formatting before merge.
