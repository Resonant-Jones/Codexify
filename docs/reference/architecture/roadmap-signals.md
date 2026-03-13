Purpose: Surface decision-grade planning signals derived from the current implementation so roadmap work follows actual dependency constraints, not product wish-casting.
Last updated: 2026-03-11
Source anchors:
- guardian/guardian_api.py
- guardian/core/
- guardian/config/
- guardian/routes/
- guardian/context/
- guardian/workers/
- guardian/command_bus/
- guardian/sync/
- frontend/src/
- tests/core/test_config_coherence.py

# Roadmap Signals

## Top Constraints

1. The primary chat loop is queue-coupled.
   - Recommendation impact: backend API improvements alone do not improve completion reliability if Redis or workers remain unstable.
   - Anchors: `guardian/routes/chat.py`, `guardian/workers/chat_worker.py`, `guardian/queue/redis_queue.py`

2. Config is still split between canonical and legacy settings paths.
   - Recommendation impact: large operational changes carry higher startup-risk until config ownership is unified.
   - Anchors: `guardian/core/config.py`, `guardian/config/core.py`, `tests/core/test_config_coherence.py`

3. Completion logic is concentrated in a narrow set of high-coupling files.
   - Recommendation impact: feature work in chat, prompting, provider routing, and persistence competes for the same code surface.
   - Anchors: `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`

4. The command bus is newer than the legacy tools surface, and both currently coexist.
   - Recommendation impact: tooling changes need migration discipline to avoid double-maintaining contracts.
   - Anchors: `guardian/routes/command_bus.py`, `guardian/command_bus/invoke.py`, `guardian/routes/tools.py`

5. Frontend routing and shell orchestration are mostly hand-rolled.
   - Recommendation impact: UI changes often involve coupled pathname logic, local storage, and cross-component events rather than one routing/state abstraction.
   - Anchors: `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/state/session/SessionSpine.ts`

## Known Missing Pieces

- Provider capability mismatch:
  - the catalog advertises providers that the runtime completion router does not fully execute today.
  - Anchors: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`
- Durable sync path:
  - `/api/sync/subscribe` is backed by an in-process bus, not Redis/Postgres durability.
  - Anchors: `guardian/sync/api.py`, `guardian/sync/bus.py`
- Tool execution unification:
  - legacy `/tools` still exposes process-local job state even though the command bus has durable run/event tables.
  - Anchors: `guardian/routes/tools.py`, `guardian/command_bus/store.py`, `guardian/db/models.py`
- Config precedence clarity:
  - dotenv layering plus dual settings systems still requires code reading to predict final values.
  - Anchors: `guardian/core/dependencies.py`, `guardian/core/config.py`, `guardian/config/core.py`
- Ingestion retry orchestration:
  - document embedding failures are visible in status fields, but an obvious built-in retry workflow was not confirmed in the scanned runtime path.
  - Anchors: `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py`

## High-Leverage Refactors

1. Unify config reads behind one canonical settings surface.
   - Why it matters: reduces startup ambiguity, operator confusion, and mismatch bugs.
   - Anchors: `guardian/core/config.py`, `guardian/config/core.py`, `guardian/core/dependencies.py`

2. Split completion execution into explicit stage boundaries.
   - Why it matters: better testability, clearer retries, and smaller blast radius when changing RAG or provider logic.
   - Anchors: `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`, `guardian/context/broker.py`

3. Finish the migration from legacy tools shim to command bus.
   - Why it matters: removes contract duplication and makes tool/job behavior more durable and observable.
   - Anchors: `guardian/routes/tools.py`, `guardian/routes/command_bus.py`, `guardian/command_bus/invoke.py`

4. Normalize provider capability reporting.
   - Why it matters: UI planning and runtime execution should agree on what is actually usable.
   - Anchors: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`, `guardian/core/provider_state.py`

5. Reduce frontend orchestration sprawl in the shell.
   - Why it matters: UI feature work will stay expensive while route logic, session persistence, and DOM event choreography live in one surface.
   - Anchors: `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/state/session/SessionSpine.ts`

## Stability Risks (1-10)

- `10`: Redis availability is a hard dependency for chat execution and task event visibility.
  - Anchors: `guardian/routes/chat.py`, `guardian/queue/redis_queue.py`
- `9`: Config coherence failures can prevent the backend from booting at all.
  - Anchors: `guardian/core/config.py`, `guardian/config/core.py`
- `8`: Completion-service changes can break prompting, retrieval, persistence, and provider selection together.
  - Anchors: `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`
- `8`: Legacy tools and command bus duality can create drift in callable-tool behavior.
  - Anchors: `guardian/routes/tools.py`, `guardian/routes/command_bus.py`
- `7`: Document ingestion is partly synchronous in the API process and partly asynchronous in workers, which complicates recovery and latency tuning.
  - Anchors: `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py`
- `7`: Provider catalog/runtime mismatches can create false-positive readiness signals for product work.
  - Anchors: `guardian/core/llm_catalog.py`, `guardian/core/ai_router.py`
- `6`: Frontend shell state is distributed across pathname checks, local/session storage, and custom events.
  - Anchors: `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`
- `6`: Sync subscriptions are not durable across restarts.
  - Anchors: `guardian/sync/bus.py`, `guardian/sync/api.py`
- `5`: Federation remains a high-blast-radius area due to feature flags, trust policy, egress, and peer behavior all intersecting.
  - Anchors: `guardian/routes/federation.py`, `guardian/core/egress.py`

## Sequencing Suggestions

1. Stabilize configuration first.
   - Recommendation: reduce the dual-settings surface before adding more environment-dependent features.

2. Harden the core completion loop second.
   - Recommendation: make stage boundaries, telemetry, and retry behavior explicit before expanding chat-side features.

3. Align provider reporting with actual runtime support.
   - Recommendation: remove selectable-but-unusable provider states before investing in provider UX or auto-routing work.

4. Consolidate tool execution on the command bus.
   - Recommendation: treat `/tools` as a migration surface, not a long-term parallel architecture.

5. Improve ingestion recovery and retries.
   - Recommendation: once core completion is stable, make failed document ingestion easier to replay without manual DB intervention.

6. Only then expand federation/sync expectations.
   - Recommendation: peer features should come after local-core durability and observability improve.

## PM Notes

- Features that depend on stronger retrieval quality will inherit current ingestion and provider-state constraints.
- Features that depend on autonomous tool use will inherit current command bus versus legacy tools migration costs.
- Features that depend on multi-user or multi-node workflows will inherit auth, collaboration, and federation complexity quickly.
