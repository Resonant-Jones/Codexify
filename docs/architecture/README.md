Purpose: Provide a KB-first entry point into Codexify's current architecture so humans and AI can orient quickly, find the right source files, and plan changes with an accurate map.
Last updated: 2026-03-11
Source anchors:
- docs/architecture/
- guardian/guardian_api.py
- guardian/routes/
- guardian/workers/
- guardian/db/models.py
- guardian/core/config.py
- guardian/core/dependencies.py
- frontend/src/App.tsx
- frontend/src/components/persona/layout/AppShell.tsx
- docker-compose.yml

# Codexify Architecture KB

## What Codexify Is

Codexify is a local-first chat and knowledge workspace built around a FastAPI backend, a React frontend, Postgres-backed state, Redis-backed background work, optional Neo4j graph features, and a growing command bus/tooling layer. The core loop today is thread-based chat: the frontend writes messages, the backend enqueues completion work, workers assemble context from messages plus retrieval layers, and results stream back through task events and durable domain events.

## Start Here

When you need current-state interpretation instead of structural architecture, begin with [`00-current-state.md`](./00-current-state.md). It is the live operational truth layer for release readiness, supported install path, active blockers, and short-horizon priorities.

## Doc Map

- [`00-current-state.md`](./00-current-state.md): live operational truth, current release/readiness interpretation, and short-horizon priorities.
- [System Overview](./system-overview.md): runtime components, topology, and critical paths.
- [Critical Flows](./flows.md): step-by-step operational flows with Mermaid diagrams and failure modes.
- [Data and Storage](./data-and-storage.md): storage systems, key tables, invariants, and data risk hotspots.
- [Config and Ops](./config-and-ops.md): env vars, config resolution, run commands, health checks, logging, and debugging cues.
- [Modules and Ownership](./modules-and-ownership.md): subsystem map, dependency edges, and blast radius guidance.
- [Roadmap Signals](./roadmap-signals.md): derived planning constraints, refactor leverage points, and sequencing suggestions.
- [Tech Debt and Risks](./tech-debt-and-risks.md): evidence-backed risk register.
- [Completion Pipeline](./completion_pipeline.md): older deep dive on completion internals; treat as supplementary and verify against current routes/workers.
- [Inference Providers](./providers.md): provider notes; verify against current catalog/router behavior before relying on it.
- [Guardian Agent Delegation Recon](./guardian-agent-delegation-recon.md): focused notes on delegation and agent runtime work.
- [Solo Operator Runtime Bootcamp](./solo-operator-runtime-bootcamp.md): operational bootstrapping guide for solo runtime work.

## Where Do I Change X?

- Chat thread/message API contract: `guardian/routes/chat.py`
- Completion assembly and provider execution: `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`
- RAG depth behavior and retrieval composition: `guardian/context/broker.py`, `guardian/memoryos/retriever.py`
- Provider catalog, model selection, and runtime support: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`
- Startup order, router wiring, middleware, SSE: `guardian/guardian_api.py`
- Auth mode, API key/session behavior, and exposure policy: `guardian/core/dependencies.py`, `guardian/core/public_exposure.py`
- Document/image upload, parsing, dedupe, and embedding enqueue: `guardian/routes/media.py`, `guardian/services/document_parsers/`, `guardian/queue/document_embed_queue.py`
- Generated docs and thread document links: `guardian/routes/documents.py`
- DB schema and invariants: `guardian/db/models.py`, `guardian/db/migrations/`
- Redis queues, cancellation, task streams, and turn locks: `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`
- Durable event outbox and `/api/events`: `guardian/core/event_bus.py`, `guardian/core/outbox.py`, `guardian/guardian_api.py`
- Command bus and tool execution policy: `guardian/routes/command_bus.py`, `guardian/command_bus/`, `guardian/routes/tools.py`
- Cron jobs and background automation: `guardian/routes/cron.py`, `guardian/cron/`, `guardian/workers/cron_worker.py`
- Federation and peer context/search: `guardian/routes/federation.py`, `guardian/routes/federation_context.py`, `guardian/sync/`
- Frontend routing, shell state, and live event consumption: `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/hooks/useLiveEvents.ts`, `frontend/src/state/session/SessionSpine.ts`
- Frontend auth and API request behavior: `frontend/src/lib/api.ts`, `frontend/src/lib/authState.ts`, `frontend/src/lib/runtimeConfig.ts`
- Testing reality for backend, realtime, federation, and frontend harnesses: `tests/`, `frontend/src/vitest.config.ts`, `frontend/src/playwright.config.ts`, `frontend/src/cypress.config.ts`

## Keep This KB Current

- Update the matching doc whenever a critical path changes:
  - chat/RAG/ingestion/tool flow changes belong in `flows.md`
  - schema/storage changes belong in `data-and-storage.md`
  - config/startup/health changes belong in `config-and-ops.md`
- Refresh `Last updated` and `Source anchors` when a new file becomes part of the path.
- Mark anything uncertain as `Unverified` and point to the verification file or endpoint.
- Keep present-state descriptions out of `roadmap-signals.md`; keep recommendations there instead.
- When a change increases coupling or risk, add it to `tech-debt-and-risks.md` in the same PR.
- Re-run the repo's docs check after edits and record the result, even if the docs command is currently broken.
