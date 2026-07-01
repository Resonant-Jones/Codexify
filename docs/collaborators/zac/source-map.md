# Zac Source Map

**For:** Zac's agent — deeper pointers into Codexify docs and code  
**Last updated:** 2026-06-26

## Always Read First

Before exploring any area, orient from:

- `docs/architecture/00-current-state.md` — the release-truth anchor.
- `docs/collaborators/zac/README.md` — this directory's entrypoint.
- `docs/collaborators/zac/agent-rag-brief.md` — your agent operating brief.
- `docs/collaborators/zac/agent-startup-prompt.md` — copy-paste startup prompt for Zac's agent.

## Report-Only Mode

When Zac wants to learn rather than propose, use these report-only files:

- `docs/collaborators/zac/report-only-agent-lenses.md` — seven report-only lenses (Cartographer, Doc Gardener, UI Naturalist, Runtime Boundary Scout, Dev-Experience Mechanic, Test Cartographer, Continuity Museum Guide).
- `docs/collaborators/zac/report-request-prompts.md` — copy-paste prompts for each lens plus a general report prompt.
- `docs/collaborators/zac/report-output-templates.md` — standardized report shapes for each lens type.

Reports produce understanding. Proposals produce intent. Both are valid, but they are separate agent modes.

## Current Continuity Milestone

The Continuity operator six-route surface is complete as a test-only, quarantined substrate.

- `docs/architecture/continuity-operator-phase-explainer.md` — human-readable phase explainer.
- `docs/architecture/2026-06-25-continuity-operator-six-route-milestone-handoff.md` — handoff record (COMPLETE).
- `docs/architecture/continuity-operator-loop-proof-chain.md` — full evidence chain (23+ proof rows).
- `docs/architecture/2026-06-25-continuity-operator-documentation-alignment-audit.md` — alignment audit (PASS).
- `docs/architecture/2026-06-25-continuity-operator-six-route-hardening-regression-rerun.md` — hardening rerun (PASS).

## Architecture Governance

- `docs/architecture/adr/adr-index.md` — ADR index, if present.
- `docs/architecture/adr/030-continuity-protocol-suite-runtime-gate.md` — ADR-030: overall continuity runtime gate.
- `docs/architecture/adr/031-continuity-phase-a-storage-migration-gate.md` — ADR-031: Phase A storage migration gate.
- `docs/architecture/agent-protocol-operations.md` — agent-facing map for task rituals and architecture-impact workflow.
- `docs/architecture/config-and-ops.md` — env vars, config resolution, health checks, logging, debugging.
- `docs/architecture/data-and-storage.md` — storage systems, key tables, invariants, data risk hotspots.
- `docs/architecture/README.md` — architecture KB entrypoint and doc map.

## Sensitive Domains

- `docs/architecture/account-export-restore-contract.md` — export artifact contract: provenance, lineage, restore semantics.
- `docs/architecture/runtime-protocol-token-contract.md` — canonical runtime tokens for statuses, events, error codes.
- `docs/architecture/collab-chat-identity-contract.md` — proposed collab thread identity contract, if present.

## Code Entrypoints

Key implementation files for orientation:

### Continuity Operator
- `guardian/routes/continuity_operator.py` — implemented six-route operator surface.
- `guardian/continuity/write_actions.py` — explicit write-action service.
- `guardian/continuity/persistence.py` — continuity persistence adapter.
- `tests/continuity/test_continuity_operator_six_route_surface.py` — regression guardrail (16 tests).

### Backend Core
- `guardian/guardian_api.py` — FastAPI app entrypoint, startup, middleware, route mounting.
- `guardian/core/config.py` — canonical Pydantic settings.
- `guardian/core/dependencies.py` — auth, API key, exposure mode, DB session.
- `guardian/core/ai_router.py` — provider routing and selection.
- `guardian/core/chat_completion_service.py` — completion assembly and provider execution.
- `guardian/core/llm_catalog.py` — provider/model catalog.

### Chat and RAG
- `guardian/routes/chat.py` — chat thread and message API.
- `guardian/workers/chat_worker.py` — chat completion worker.
- `guardian/context/broker.py` — context assembly for completion.
- `guardian/memoryos/retriever.py` — retrieval composition.

### Queue and Events
- `guardian/queue/redis_queue.py` — Redis queues, task events, cancellation.
- `guardian/queue/task_events.py` — task event publishing.
- `guardian/queue/turn_lock.py` — canonical per-thread turn lock.
- `guardian/core/event_bus.py` — durable domain events.

### Identity and Memory
- `guardian/cognition/identity_contract.py` — identity precedence contract.
- `guardian/cognition/identity_resolution.py` — identity resolution at request scope.
- `guardian/routes/imprint.py` — imprint/identity API.

### DB and Models
- `guardian/db/models.py` — SQLAlchemy models for Postgres.
- `guardian/db/migrations/` — Alembic migration tree.

### Frontend
- `frontend/src/App.tsx` — React app entrypoint.
- `frontend/src/components/persona/layout/AppShell.tsx` — main shell layout.
- `frontend/src/features/personaStudio/` — Persona Studio feature.
- `frontend/src/features/settings/` — settings feature.
- `frontend/src/lib/api.ts` — frontend API client.
- `frontend/src/lib/runtimeConfig.ts` — runtime config resolution.

### Configuration
- `docker-compose.yml` — supported local Docker Compose stack.
- `config/supported_profiles/v1-local-core-web-mcp.yaml` — supported beta profile contract.
- `config/supported_profiles/test-continuity.yaml` — test-only continuity profile.

## Note

If a listed file is missing, do not invent its contents. Report it as missing and continue from available sources. The architecture docs and code are the truth — not this map.
