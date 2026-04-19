Purpose: Provide a KB-first entry point into Codexify's current architecture so humans and AI can orient quickly, find the right source files, and plan changes with an accurate map.
Last updated: 2026-04-15
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
- frontend/src/features/personaStudio/
- docker-compose.yml
- guardian/routes/agent_orchestration.py
- guardian/routes/codex.py
- guardian/codex/lineage.py
- guardian/agents/store.py
- guardian/agents/events.py
- guardian/workers/agent_worker.py
- guardian/command_bus/contracts.py

# Codexify Architecture KB

## What Codexify Is

Codexify is a local-first chat and knowledge workspace built around a FastAPI backend, a React frontend, Postgres-backed state, Redis-backed background work, optional Neo4j graph features, and a growing command bus/tooling layer. The core loop today is thread-based chat: the frontend writes messages, the backend enqueues completion work, workers assemble context from messages plus retrieval layers, and results stream back through task events and durable domain events.

## Start Here

Start here first when you need current-state interpretation rather than structural architecture: [`00-current-state.md`](./00-current-state.md). It is the live operational truth layer for release readiness, supported install path, active blockers, and short-horizon priorities.

If you are working on delegation, start with [`delegation-operator-manual.md`](./delegation-operator-manual.md) first. That manual is the operator-facing front door for the delegation slice; use this KB page immediately after to anchor the manual back to the current runtime truth.

If you are working on Flow Builder, delegation/specification workflows, tacit-knowledge extraction, or workflow authoring semantics, start with [`ADR-006: Flow Builder Elicitation Lane`](./adr/005-flow-builder-elicitation-lane.md) first. That ADR defines the upstream `interview -> extract -> normalize -> validate -> compile -> execute` lane and the boundary between elicitation and runnable execution.

## KB Validity and Diagram Source Sets

Before generating architecture diagrams, read the [`KB Validity Matrix`](./kb-validity-matrix.md).

- Use the validity matrix before using docs as diagram inputs.
- For first-pass runtime architecture diagrams, use only `Runtime Diagram Source Set v1`.
- Treat [`00-current-state.md`](./00-current-state.md) as the short-horizon override when older or broader docs conflict with present release reality.
- Do not use quarantined legacy docs as source inputs, especially Threadspace / `guardian-backend_v2` / obsolete installer-era material.

## Doc Map

- [`00-current-state.md`](./00-current-state.md): live operational truth, current release/readiness interpretation, and short-horizon priorities.
- [Architecture Atlas](./architecture-atlas.md): peer-facing reading guide for the validated architecture corpus, runtime diagrams, and UI diagrams.
- [Workspace Surface Spec v1](./codexify_workspace_surface_spec_v_1.md): UI/design-canon contract for Workspace as Shelf + Scratchpad + Inspector across Dashboard, Guardian, and Documents; not first-pass runtime topology truth.
- [Persona Studio Architecture](./persona-studio.md): shell-integrated persona/profile configuration surface, local draft state, diagnostics preview, and boundary rules; complements the broader product spec.
- [System Overview](./system-overview.md): current runtime components, topology, and critical paths.
- [Critical Flows](./flows.md): current trigger-to-output runtime flows with failure modes.
- [Flow Builder Elicitation Lane ADR](./adr/005-flow-builder-elicitation-lane.md): upstream spec-building lane for tacit-knowledge extraction, workflow authoring semantics, and validation-before-execution doctrine.
- [Data and Storage](./data-and-storage.md): storage systems, key tables, invariants, and data risk hotspots.
- [Config and Ops](./config-and-ops.md): env vars, config resolution, supported run paths, health checks, logging, and debugging cues.
- [Modules and Ownership](./modules-and-ownership.md): subsystem map, dependency edges, and blast radius guidance.
- [Runtime Diagrams v1](./runtime-diagrams-v1.md): first-pass current runtime diagram pack with source-scoped evidence notes and confidence labels.
- [Roadmap Signals](./roadmap-signals.md): planning guidance derived from the current codebase; not a first-pass runtime diagram source.
- [Tech Debt and Risks](./tech-debt-and-risks.md): evidence-backed current risk register; use for risk overlays, not baseline topology.
- [Chat Runtime Contract](./chat-runtime-contract.md): normative frontend/shared-runtime vocabulary for provider runtime, request lifecycle, replay, and transcript-integrity semantics.
- [Agent Tool Loop Contract](./agent-tool-loop-contract.md): canonical bounded tool-augmented completion loop contract for future ReAct/function-calling orchestration; runtime semantics and transcript integrity only.
- [Identity Precedence Contract](./identity-precedence-contract.md): canonical identity-layer precedence, actor-plus-role posture, and persisted/resolved/request-scoped semantics.
- [Runtime Protocol Token Contract](./runtime-protocol-token-contract.md): canonical runtime tokens for statuses, events, and machine-readable failure codes.
- [Account Export + Restore Contract](./account-export-restore-contract.md): provenance, lineage, and restore semantics for durable artifacts and imported state.
- [Delegation Runtime Contract](./delegation-runtime.md): current delegation seam, runtime contract, and source-thread provenance rules.
- [Delegation Operator Manual](./delegation-operator-manual.md): operator procedure for supervised delegation, recovery, and summary persistence.
- [Chat Runtime Gap Analysis](./chat-runtime-gap-analysis.md): companion note explaining why the runtime contract exists and which ambiguity classes it is intended to shrink.
- [Completion Pipeline](./completion_pipeline.md): older completion deep dive; supplementary only and verify against current routes/workers.
- [Inference Providers](./providers.md): provider notes; supplementary only and verify against current catalog/router/health behavior.
- [Guardian Agent Delegation Recon](./guardian-agent-delegation-recon.md): focused planning/recon notes on delegation and agent runtime work; use only as supplementary planning context.
- [Solo Operator Runtime Bootcamp](./solo-operator-runtime-bootcamp.md): operational bootstrapping guide for solo runtime work.

## Where Do I Change X?

- Chat thread/message API contract: `guardian/routes/chat.py`
- Completion assembly and provider execution: `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`
- Identity precedence, persona/imprint assembly, and status-surface wording: `docs/architecture/identity-precedence-contract.md`, `guardian/cognition/identity_contract.py`, `guardian/cognition/identity_resolution.py`, `guardian/cognition/system_prompt_builder.py`, `guardian/core/chat_completion_service.py`, `guardian/routes/imprint.py`, `guardian/routes/chat.py`, `frontend/src/features/settings/`
- RAG depth behavior and retrieval composition: `guardian/context/broker.py`, `guardian/memoryos/retriever.py`
- Flow Builder elicitation lane, delegation/specification workflows, tacit-knowledge extraction, and workflow authoring semantics: `docs/architecture/adr/005-flow-builder-elicitation-lane.md`
- Provider catalog, model selection, and runtime support: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`
- Startup order, router wiring, middleware, SSE: `guardian/guardian_api.py`
- Auth mode, API key/session behavior, and exposure policy: `guardian/core/dependencies.py`, `guardian/core/public_exposure.py`
- Delegation planning, run persistence, lineage, and result injection: `guardian/routes/agent_orchestration.py`, `guardian/routes/codex.py`, `guardian/routes/delegations.py`, `guardian/codex/lineage.py`, `guardian/core/delegation_service.py`, `guardian/agents/store.py`, `guardian/agents/events.py`, `guardian/workers/agent_worker.py`, `guardian/workers/delegation_worker.py`, `guardian/tasks/types.py`, `guardian/protocol_tokens.py`
- Document/image upload, parsing, dedupe, and embedding enqueue: `guardian/routes/media.py`, `guardian/services/document_parsers/`, `guardian/queue/document_embed_queue.py`
- Generated docs and thread document links: `guardian/routes/documents.py`
- DB schema and invariants: `guardian/db/models.py`, `guardian/db/migrations/`
- Redis queues, cancellation, task streams, and turn locks: `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`
- Durable event outbox and `/api/events`: `guardian/core/event_bus.py`, `guardian/core/outbox.py`, `guardian/guardian_api.py`
- Command bus and tool execution policy: `guardian/routes/command_bus.py`, `guardian/command_bus/`
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
  - delegation runtime or provenance changes belong in `delegation-runtime.md` and `delegation-operator-manual.md`
- Refresh `Last updated` and `Source anchors` when a new file becomes part of the path.
- Mark anything uncertain as `Unverified` and point to the verification file or endpoint.
- Keep present-state descriptions out of `roadmap-signals.md`; keep recommendations there instead.
- When a change increases coupling or risk, add it to `tech-debt-and-risks.md` in the same PR.
- Re-run the repo's docs check after edits and record the result, even if the docs command is currently broken.
