# Codexify Codebase Capability Audit

## Executive Summary

Codexify is a large local-first AI application stack centered on a FastAPI backend (`guardian/`) and a React/Tauri frontend (`frontend/src`, `src-tauri/`). The repository demonstrates substantial implementation depth in chat orchestration, retrieval, document/media ingestion, provider governance, worker-based execution, and runtime health instrumentation.

The strongest consulting evidence is in:
- Local-first AI runtime architecture with explicit queue/worker boundaries
- AI workflow app UX design across chat, workspace, settings, and diagnostics
- Provider/model routing governance and health visibility
- Private knowledge ingestion/retrieval seams (documents + workspace/Obsidian)
- Extension/plugin and command-bus style tool-execution architecture

The biggest caution for client packaging is release posture vs implementation breadth. The codebase includes many advanced surfaces (federation, command bus, cron, voice, connectors, agent orchestration), but the supported profile explicitly quarantines many of them in current beta posture (`config/supported_profiles/v1-local-core-web-mcp.yaml`). This is evidence of engineering discipline, but also means demos should distinguish “implemented in code” from “currently supported in release posture.”

## Repository Overview

### Primary languages and frameworks

- Python backend and worker system
  - `guardian/`, `backend/`, `tests/`
  - FastAPI app wiring in [`guardian/guardian_api.py`](/Volumes/Dev_SSD/Codexify-main/guardian/guardian_api.py)
  - Python packaging and deps in [`pyproject.toml`](/Volumes/Dev_SSD/Codexify-main/pyproject.toml), [`requirements.txt`](/Volumes/Dev_SSD/Codexify-main/requirements.txt)
- TypeScript/React frontend
  - App shell and feature modules in `frontend/src/`
  - Frontend package and scripts in [`frontend/package.json`](/Volumes/Dev_SSD/Codexify-main/frontend/package.json)
- Rust/Tauri desktop shell
  - Desktop runtime commands in [`src-tauri/src/commands.rs`](/Volumes/Dev_SSD/Codexify-main/src-tauri/src/commands.rs)

### Frontend stack

- React + TypeScript + Vite + Vitest + Cypress + Playwright
  - [`frontend/package.json`](/Volumes/Dev_SSD/Codexify-main/frontend/package.json)
  - [`frontend/src/App.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/App.tsx)
  - [`frontend/src/components/persona/layout/AppShell.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/components/persona/layout/AppShell.tsx)

### Backend stack

- FastAPI routing + dependency injection + worker queue pattern
  - [`guardian/guardian_api.py`](/Volumes/Dev_SSD/Codexify-main/guardian/guardian_api.py)
  - [`guardian/routes/chat.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/chat.py)
  - [`guardian/core/chat_completion_service.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/chat_completion_service.py)
  - [`guardian/workers/chat_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/chat_worker.py)

### Database/storage layers

- Postgres as primary system of record (chat, projects, documents, runs)
  - Compose env and DSNs in [`docker-compose.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.yml)
- Redis for queueing, turn locks, event streams
  - [`guardian/queue/redis_queue.py`](/Volumes/Dev_SSD/Codexify-main/guardian/queue/redis_queue.py)
  - [`guardian/queue/turn_lock.py`](/Volumes/Dev_SSD/Codexify-main/guardian/queue/turn_lock.py)
  - [`guardian/queue/task_events.py`](/Volumes/Dev_SSD/Codexify-main/guardian/queue/task_events.py)
- Vector storage (Chroma/FAISS abstractions)
  - [`guardian/vector/store.py`](/Volumes/Dev_SSD/Codexify-main/guardian/vector/store.py)
  - [`backend/rag/embedder.py`](/Volumes/Dev_SSD/Codexify-main/backend/rag/embedder.py)
- Optional Neo4j graph surface
  - service and graph-init in [`docker-compose.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.yml)
  - backend adapters in `guardian/memory_graph/*`
- Filesystem/object storage abstraction for media
  - [`guardian/core/storage.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/storage.py)

### Local services/infrastructure dependencies

- Docker Compose topology with `backend`, `frontend`, `db`, `redis`, `neo4j`, multiple workers
  - [`docker-compose.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.yml)
  - runtime-image topology in [`docker-compose.runtime.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.runtime.yml)

### Package managers and major dependency files

- Python: `pip`/setuptools
  - [`requirements.txt`](/Volumes/Dev_SSD/Codexify-main/requirements.txt)
  - [`pyproject.toml`](/Volumes/Dev_SSD/Codexify-main/pyproject.toml)
- Node: `pnpm` (workspace + frontend), also lockfiles present
  - [`package.json`](/Volumes/Dev_SSD/Codexify-main/package.json)
  - [`pnpm-lock.yaml`](/Volumes/Dev_SSD/Codexify-main/pnpm-lock.yaml)
  - [`frontend/package.json`](/Volumes/Dev_SSD/Codexify-main/frontend/package.json)

### Test framework and test locations

- Backend tests (pytest): `tests/` with broad subsystem coverage
  - 271 Python test files in `tests/`
- Frontend tests (Vitest/Playwright/Cypress): `frontend/src` and `frontend/tests`
  - 145 test/spec files detected under `frontend/src`
- Representative config:
  - [`pytest.ini`](/Volumes/Dev_SSD/Codexify-main/pytest.ini)
  - [`frontend/src/vitest.config.ts`](/Volumes/Dev_SSD/Codexify-main/frontend/src/vitest.config.ts)

### Build/run scripts

- Root scripts: [`package.json`](/Volumes/Dev_SSD/Codexify-main/package.json)
- Dev/ops/proof scripts: `scripts/` (audit, proofs, release, verification)
- Compose-based startup: [`docker-compose.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.yml)

### Environment/configuration files (without secrets)

- [` .env.example`](/Volumes/Dev_SSD/Codexify-main/.env.example)
- [` .env.template`](/Volumes/Dev_SSD/Codexify-main/.env.template)
- Supported profile contract: [`config/supported_profiles/v1-local-core-web-mcp.yaml`](/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-local-core-web-mcp.yaml)
- Architecture current-truth and ops docs:
  - [`docs/architecture/00-current-state.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/00-current-state.md)
  - [`docs/architecture/config-and-ops.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/config-and-ops.md)

## Product Surface Area

| Capability | Status | Evidence | Notes |
|---|---|---|---|
| Threaded chat UX + completion lifecycle | Implemented | [`frontend/src/features/chat/GuardianChat.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/chat/GuardianChat.tsx), [`guardian/routes/chat.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/chat.py), [`guardian/workers/chat_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/chat_worker.py) | Queue/worker architecture with turn locking and task events is concrete. |
| Provider/model routing and governance | Implemented | [`guardian/core/provider_registry.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/provider_registry.py), [`guardian/core/ai_router.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/ai_router.py), [`guardian/core/llm_catalog.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/llm_catalog.py) | Strong policy separation between discovery-backed/static/local/disabled providers. |
| Runtime health and operator diagnostics | Implemented | [`guardian/routes/health.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/health.py), [`frontend/src/features/commandCenter/CommandCenterPage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/commandCenter/CommandCenterPage.tsx) | Command Center route exists with observability hooks; release posture should be checked before client claims. |
| Persona-aware assistant configuration | Partially implemented | [`guardian/routes/persona_profiles.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/persona_profiles.py), [`frontend/src/features/personaStudio/PersonaStudioPage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/personaStudio/PersonaStudioPage.tsx), [`guardian/cognition/system_profiles/store.py`](/Volumes/Dev_SSD/Codexify-main/guardian/cognition/system_profiles/store.py) | Profile CRUD is real; Persona Studio includes local ephemeral harness behaviors that are clearly non-runtime execution. |
| Personal facts / memory routes | Implemented (feature), Quarantined (supported profile) | [`guardian/routes/memory.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/memory.py), [`guardian/routes/personal_facts.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/personal_facts.py), [`config/supported_profiles/v1-local-core-web-mcp.yaml`](/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-local-core-web-mcp.yaml) | Code exists and tests exist, but supported profile marks these as quarantined for current beta surface. |
| Document autosave/generation and linking | Implemented | [`guardian/routes/documents.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/documents.py), [`guardian/db/models.py`](/Volumes/Dev_SSD/Codexify-main/guardian/db/models.py) | Includes thread/project link handling and generation metadata. |
| Media upload + parsing + embedding lifecycle | Implemented | [`guardian/routes/media.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/media.py), [`guardian/workers/document_embed_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/document_embed_worker.py), [`guardian/services/document_parsers`](/Volumes/Dev_SSD/Codexify-main/guardian/services/document_parsers) | Mature ingestion chain with parse status and async embedding jobs. |
| Vector retrieval / RAG | Implemented | [`guardian/vector/store.py`](/Volumes/Dev_SSD/Codexify-main/guardian/vector/store.py), [`backend/rag/embedder.py`](/Volumes/Dev_SSD/Codexify-main/backend/rag/embedder.py), [`guardian/context/broker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/context/broker.py) | Explicit namespace and user-scoped retrieval boundaries visible in code. |
| Workspace-local Obsidian ingestion and retrieval routing | Implemented (backend seam) | [`guardian/routes/obsidian.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/obsidian.py), [`guardian/obsidian/indexer.py`](/Volumes/Dev_SSD/Codexify-main/guardian/obsidian/indexer.py), [`tests/obsidian/test_live_runtime_proof.py`](/Volumes/Dev_SSD/Codexify-main/tests/obsidian/test_live_runtime_proof.py) | Strong backend control plane and tests; should be demoed as local workspace ingestion path. |
| Settings/configuration UI | Implemented | [`frontend/src/features/settings/SettingsView.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/settings/SettingsView.tsx) | Includes connectors, imprint/persona, data, and desktop connection controls. |
| Project/thread/workspace UX surfaces | Implemented | [`guardian/routes/projects.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/projects.py), [`guardian/routes/workspace.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/workspace.py), `frontend/src/components/dashboard/*` | Good evidence for multi-surface AI workspace design patterns. |
| Share links for threads/documents | Implemented | [`guardian/routes/share.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/share.py), [`frontend/src/pages/SharePage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/pages/SharePage.tsx) | Secure tokenized sharing exists in backend and UI route. |
| Auth / identity boundary | Implemented | [`guardian/routes/auth.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/auth.py), [`guardian/core/dependencies.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/dependencies.py), [`guardian/core/public_exposure.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/public_exposure.py) | Local vs remote auth posture is explicit and enforced server-side. |
| Capability/permission policy model | Implemented | [`guardian/core/capability_policy.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/capability_policy.py), [`guardian/core/capability_grants.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/capability_grants.py), identity tests under `tests/identity/` | Strong consulting evidence for explicit permission boundaries. |
| Plugin architecture and manifests | Implemented | [`guardian/plugins/plugin_manifest.py`](/Volumes/Dev_SSD/Codexify-main/guardian/plugins/plugin_manifest.py), [`guardian/plugins/plugin_loader.py`](/Volumes/Dev_SSD/Codexify-main/guardian/plugins/plugin_loader.py), [`plugins/chatterbox/manifest.json`](/Volumes/Dev_SSD/Codexify-main/plugins/chatterbox/manifest.json) | Real manifest schema and loaders; production plugin distribution model appears still evolving. |
| Command bus / tool execution | Implemented (internal posture) | [`guardian/routes/command_bus.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/command_bus.py), `guardian/command_bus/*`, supported profile `internal_only` route posture | Architecturally strong but currently framed as internal in supported profile. |
| Delegation and agent orchestration APIs | Prototype/demo | [`guardian/routes/delegations.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/delegations.py), [`guardian/routes/agent_orchestration.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/agent_orchestration.py) | Significant scaffolding and persistence/eventing exist; client claims should remain bounded to supervised orchestration prototypes. |
| Cron/automation routes | Implemented (internal/quarantined posture) | [`guardian/routes/cron.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/cron.py), `guardian/cron/*` | Includes webhook policy controls; profile currently quarantines cron from supported public surface. |
| Realtime websocket RPC | Implemented (internal/quarantined posture) | [`guardian/routes/websocket.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/websocket.py), `guardian/ws/*` | Includes auth, rate limiting, payload validation, and audit logging. |
| Voice capabilities (TTS/STT/turn-based) | Partially implemented | [`guardian/routes/voice.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/voice.py), [`guardian/workers/voice_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/voice_worker.py), frontend voice handling in [`frontend/src/features/chat/ChatView.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/chat/ChatView.tsx) | Broad surface exists; release docs indicate caution and optional behavior. |
| Federation surfaces | Experimental | [`guardian/routes/federation.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/federation.py), [`guardian/routes/federation_context.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/federation_context.py), tests in `tests/federation/` | Real code and tests, but not part of current supported local-beta claim. |
| Local-first desktop app runtime | Implemented | [`src-tauri/src/commands.rs`](/Volumes/Dev_SSD/Codexify-main/src-tauri/src/commands.rs), [`frontend/src/lib/runtimeConfig.ts`](/Volumes/Dev_SSD/Codexify-main/frontend/src/lib/runtimeConfig.ts), [`docker-compose.runtime.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.runtime.yml) | Strong evidence for packaged-runtime operational flows. |

## Architecture Map

### Major modules/directories

- `guardian/`: backend runtime core (routes, orchestration, context, workers, policy)
- `backend/`: embedding/vector and service support modules
- `frontend/src/`: UI shell, feature modules, API/runtime integration
- `src-tauri/`: desktop launcher/runtime bridge
- `tests/`: backend and contract/proof test suites
- `config/supported_profiles/`: release posture contracts
- `docs/architecture/`: operational and architectural truth docs

### Data flow (as implemented)

```text
Frontend (React/Tauri shell)
  -> FastAPI route layer (guardian/routes/*)
  -> enqueue + lock (Redis queues/turn locks)
  -> worker execution (guardian/workers/*)
  -> completion/context/provider routing (guardian/core/*, guardian/context/*)
  -> persistence (Postgres + media storage + vector store)
  -> event publication (task events/outbox/SSE/ws)
  -> frontend event consumers update UI state
```

### User input path (chat)

- UI send path in [`frontend/src/features/chat/GuardianChat.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/chat/GuardianChat.tsx)
- Route acceptance in [`guardian/routes/chat.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/chat.py)
- Tasked execution in [`guardian/workers/chat_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/chat_worker.py)
- Completion assembly and tool-loop bounds in [`guardian/core/chat_completion_service.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/chat_completion_service.py)

### Provider/model routing

- Routing and provider call logic in [`guardian/core/ai_router.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/ai_router.py)
- Governance and capability registry in [`guardian/core/provider_registry.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/provider_registry.py)
- Catalog/selection helpers in [`guardian/core/llm_catalog.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/llm_catalog.py)

### Memory/retrieval

- Context assembly and retrieval policy in [`guardian/context/broker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/context/broker.py)
- Vector search/index in [`guardian/vector/store.py`](/Volumes/Dev_SSD/Codexify-main/guardian/vector/store.py)
- Obsidian local indexing in [`guardian/obsidian/indexer.py`](/Volumes/Dev_SSD/Codexify-main/guardian/obsidian/indexer.py)
- Memory routes/silos in [`guardian/routes/memory.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/memory.py)

### Persistence

- ORM models/migrations in `guardian/db/`
- Primary DB loading via [`guardian/core/db.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/db.py)
- Media storage via [`guardian/core/storage.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/storage.py)

### Configuration and runtime posture

- Runtime env boundary in [`guardian/core/dependencies.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/dependencies.py)
- Supported release profile in [`config/supported_profiles/v1-local-core-web-mcp.yaml`](/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-local-core-web-mcp.yaml)
- Current status contract in [`docs/architecture/00-current-state.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/00-current-state.md)

### Local-first vs cloud/API dependent boundary

- Local-first defaults and env posture in [` .env.example`](/Volumes/Dev_SSD/Codexify-main/.env.example)
- Provider governance around cloud enablement in [`guardian/core/provider_registry.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/provider_registry.py)
- Egress policy hooks in [`guardian/core/egress.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/egress.py)

## Consulting-Relevant Capability Evidence

| Consulting Service | Credibility Level | Code Evidence | Demo Value | Gaps Before Selling |
|---|---|---|---|---|
| AI workflow application design | Strong | App shell and multi-surface UI in [`frontend/src/components/persona/layout/AppShell.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/components/persona/layout/AppShell.tsx), chat/workspace/settings flows across `frontend/src/features/*` | Demonstrates end-to-end AI app UX architecture beyond a single chat box | Consolidate a smaller “golden path” demo script to reduce feature sprawl risk |
| Internal AI assistant design | Strong | Threaded chat, queue workers, provider routing: [`guardian/routes/chat.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/chat.py), [`guardian/workers/chat_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/chat_worker.py) | Shows robust async assistant execution model and event-driven lifecycle | Package clear SLAs for timeout/retry behavior and request-state semantics |
| Private knowledge-base / RAG system design | Strong | Document ingestion + embeddings + retrieval + obsidian paths: [`guardian/routes/media.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/media.py), [`guardian/vector/store.py`](/Volumes/Dev_SSD/Codexify-main/guardian/vector/store.py), [`guardian/routes/obsidian.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/obsidian.py) | Strong proof for local knowledge retrieval patterns and ingestion lifecycle control | Harden retrieval quality benchmarking pack for client-facing KPIs |
| Persona-aware assistant systems | Moderate | Persona profile APIs and studio surface: [`guardian/routes/persona_profiles.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/persona_profiles.py), [`frontend/src/features/personaStudio/PersonaStudioPage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/personaStudio/PersonaStudioPage.tsx) | Demonstrates configurable persona/system behavior layers | Clarify runtime vs studio simulation paths; tighten persistence + deployment story |
| Local-first AI infrastructure planning | Strong | Compose topology + packaged runtime + profile contract: [`docker-compose.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.yml), [`docker-compose.runtime.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.runtime.yml), [`config/supported_profiles/v1-local-core-web-mcp.yaml`](/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-local-core-web-mcp.yaml) | Excellent proof of local-first architecture and operational boundary design | Publish explicit “reference architecture variants” (single-node, SMB server, hybrid cloud) |
| Secure document intelligence | Moderate | Signed media URLs and scoped docs/routes: [`guardian/core/media_signing.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/media_signing.py), [`guardian/routes/documents.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/documents.py) | Good evidence for secure media/document handling patterns | Add formal threat model + data retention controls + redaction compliance pack |
| Model/provider routing | Strong | Canonical governance and routing in [`guardian/core/provider_registry.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/provider_registry.py), [`guardian/core/ai_router.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/ai_router.py) | Demonstrates policy-controlled model selection under local/cloud constraints | Add client-ready observability dashboard for routing decisions and cost tradeoffs |
| AI onboarding or migration workflows | Moderate | ChatGPT migration paths and routes/scripts: `scripts/chatgpt_import/*`, compose profile `chatgpt-migrate` in [`docker-compose.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.yml) | Shows migration capability narrative and practical import seams | Improve migration UX and deterministic report artifacts for non-technical stakeholders |
| Business process automation | Moderate | Cron routes/workers + delegations: [`guardian/routes/cron.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/cron.py), [`guardian/routes/delegations.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/delegations.py) | Credible architecture for scheduled/queued automation flows | Current supported profile quarantines many automation surfaces; define GA subset first |
| Plugin/extensible AI system architecture | Strong | Plugin manifest schema/loader + command bus: [`guardian/plugins/plugin_manifest.py`](/Volumes/Dev_SSD/Codexify-main/guardian/plugins/plugin_manifest.py), [`guardian/plugins/plugin_loader.py`](/Volumes/Dev_SSD/Codexify-main/guardian/plugins/plugin_loader.py), [`guardian/routes/command_bus.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/command_bus.py) | Strong system-architecture demonstration for extensibility | Publish stable plugin SDK lifecycle/versioning and compatibility commitments |
| AI governance, identity, or permission boundary design | Strong | Auth/exposure boundaries + capability policy/grants + user scope checks: [`guardian/core/dependencies.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/dependencies.py), [`guardian/core/capability_policy.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/capability_policy.py), identity tests in `tests/identity/` | Strong due-diligence signal for enterprise consulting | Add formal policy docs + audit controls mapping (SOC2-style control matrix) |
| Custom dashboard or command-center UI design | Moderate | Command Center feature module: [`frontend/src/features/commandCenter/CommandCenterPage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/commandCenter/CommandCenterPage.tsx) | Demonstrates operator-oriented telemetry UI patterns | Route is feature-gated and posture-sensitive; avoid overclaiming production operational readiness |

## Demo Narrative: Codexify as Interactive Buffet Menu

A prospective client should leave the demo understanding that ResonantConstructs.ai can design and implement a full local-first AI product stack, not just an LLM wrapper.

Suggested narrative order:

1. Start with runtime posture and trust boundary
- Show health/profile truth surfaces and local-first defaults:
  - [`docs/architecture/00-current-state.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/00-current-state.md)
  - [`config/supported_profiles/v1-local-core-web-mcp.yaml`](/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-local-core-web-mcp.yaml)
- Business pain mapped: teams need private AI systems that remain useful without mandatory cloud dependence.

2. Show core assistant workflow (threaded chat + async execution)
- UI: chat and session flow in [`frontend/src/features/chat/GuardianChat.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/chat/GuardianChat.tsx)
- Backend: route/queue/worker decomposition in [`guardian/routes/chat.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/chat.py)
- Business pain mapped: brittle synchronous assistants, no reliability instrumentation.

3. Show document + retrieval lifecycle
- Upload, parse, embedding, retrieval seams:
  - [`guardian/routes/media.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/media.py)
  - [`guardian/workers/document_embed_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/document_embed_worker.py)
  - [`guardian/vector/store.py`](/Volumes/Dev_SSD/Codexify-main/guardian/vector/store.py)
- Business pain mapped: unstructured knowledge scattered across files with no retrieval governance.

4. Show local knowledge ingestion path (workspace/Obsidian)
- [`guardian/routes/obsidian.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/obsidian.py), [`guardian/obsidian/indexer.py`](/Volumes/Dev_SSD/Codexify-main/guardian/obsidian/indexer.py)
- Business pain mapped: client knowledge trapped in local notes with no operationalized AI layer.

5. Show configurability and extensibility
- Settings, persona profile controls, plugin/command bus architecture
  - [`frontend/src/features/settings/SettingsView.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/settings/SettingsView.tsx)
  - [`guardian/routes/persona_profiles.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/persona_profiles.py)
  - [`guardian/routes/command_bus.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/command_bus.py)

What not to overclaim:
- Do not present quarantined/internal routes as supported GA client product surfaces.
- Do not imply all advanced modules (federation, orchestration, cron, voice) are equally productionized for the current supported profile.
- Do not conflate “code exists” with “release-ready for default client deployment.”

Strongest proof-of-work areas:
- Queue-backed assistant runtime architecture
- Local-first retrieval + ingestion stack
- Provider governance and runtime health/ops structure
- Explicit trust/identity/policy boundaries

Better framed as roadmap or controlled pilot:
- Full federated production deployments
- Generalized multi-agent autonomous orchestration
- Broad connector ecosystem at stable GA posture

## Risk and Maturity Assessment

| Severity | Risk | Evidence | Why It Matters | Recommended Remediation |
|---|---|---|---|---|
| High | Supported surface vs implemented surface mismatch risk | Supported profile quarantines many implemented routes (`memory`, `connectors`, `cron`, `websocket`, `agent_orchestration`, etc.) in [`config/supported_profiles/v1-local-core-web-mcp.yaml`](/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-local-core-web-mcp.yaml) | In consulting demos, overclaiming can damage credibility in technical due diligence | Maintain a strict “supported-now vs implemented-experimental” matrix in demo and proposals |
| High | Secret hygiene exposure in local templates and environment handling | Sensitive env keys visible in templates and local files (`.env.example` includes full key-shaped placeholders) | Client reviewers scrutinize key management; sloppy handling weakens trust | Add secret-scanning + documented secret-management policy for client deployments; keep examples synthetic and clearly non-operational |
| High | Runtime complexity and multi-surface operational burden | 45 route modules, 16 worker modules, multiple runtime modes and compose files | High operational complexity increases failure modes and onboarding cost | Publish a narrow reference deployment profile plus architecture decision boundaries for client projects |
| Medium | Legacy/parallel surfaces may cause architectural ambiguity | Parallel route groups, compatibility bridges in frontend proxying, and internal-only pathways in [`frontend/src/vite.config.ts`](/Volumes/Dev_SSD/Codexify-main/frontend/src/vite.config.ts) and `guardian/routes/*` | Ambiguous boundaries can create regression and integration confusion | Formalize route lifecycle policy: stable, deprecated, internal-only, experimental |
| Medium | Partial/feature-gated UX may be interpreted as production-ready | Command Center is feature-gated (`VITE_ENABLE_COMMAND_CENTER`) in [`frontend/src/features/commandCenter/CommandCenterPage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/commandCenter/CommandCenterPage.tsx) | Technical buyers may assume all visible UX is GA | Add explicit UI badging for experimental/internal surfaces |
| Medium | In-memory or non-durable debug traces can be mistaken for durable observability | Architecture docs call out dev-only/non-durable trace behavior (`docs/architecture/flows.md`) | Weak observability claims are a common due-diligence failure point | Build a durable observability package (retained traces, correlation IDs, audit exports) |
| Medium | Voice and connector surfaces may be ahead of hardened delivery guarantees | Voice and connectors are broad but posture-sensitive (`guardian/routes/voice.py`, `guardian/routes/connectors.py`) | Could create mismatch between pitch and stable deployability | Define MVP contract for each surface with explicit SLOs and out-of-scope items |
| Low | Documentation drift risk in fast-moving architecture | Very large docs corpus (141 architecture files), multiple historical proof artifacts | Can confuse internal teams and clients if “current truth” is unclear | Enforce doc lifecycle labels and a single canonical readiness summary per release window |
| Low | Multi-language/runtime toolchain overhead | Python + Node + Rust + Docker + optional model infrastructure | Increases onboarding friction for client handoff teams | Provide role-specific setup runbooks (operator/dev/analyst) and “minimum viable local stack” path |

## Recommended AI Consulting KB Documents

| Filename | Purpose | Source Evidence |
|---|---|---|
| `docs/consulting/offers/Local_First_AI_Runtime_Architecture_Offer.md` | Productized offer for local-first AI system architecture and implementation | [`docker-compose.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.yml), [`docker-compose.runtime.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.runtime.yml), [`docs/architecture/system-overview.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/system-overview.md) |
| `docs/consulting/offers/Private_Knowledge_RAG_Implementation_Offer.md` | Client-facing offer for ingestion, retrieval, and workspace knowledge operations | [`guardian/routes/media.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/media.py), [`guardian/vector/store.py`](/Volumes/Dev_SSD/Codexify-main/guardian/vector/store.py), [`guardian/routes/obsidian.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/obsidian.py) |
| `docs/consulting/offers/Provider_Governance_and_Model_Routing_Offer.md` | Offer for model policy, routing controls, and runtime reliability | [`guardian/core/provider_registry.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/provider_registry.py), [`guardian/core/ai_router.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/ai_router.py), [`docs/architecture/config-and-ops.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/config-and-ops.md) |
| `docs/consulting/demo/Codexify_Golden_Path_Demo_Script.md` | 20–30 minute deterministic demo flow for technical buyers | [`frontend/src/features/chat/GuardianChat.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/chat/GuardianChat.tsx), [`frontend/src/features/settings/SettingsView.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/settings/SettingsView.tsx), [`docs/architecture/00-current-state.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/00-current-state.md) |
| `docs/consulting/demo/Codexify_Do_Not_Overclaim_List.md` | Guardrail sheet to keep demos aligned with supported runtime posture | [`config/supported_profiles/v1-local-core-web-mcp.yaml`](/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-local-core-web-mcp.yaml), [`docs/architecture/00-current-state.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/00-current-state.md) |
| `docs/consulting/architecture/Client_Facing_System_Architecture_OnePager.md` | Concise architecture map for proposals and discovery calls | [`docs/architecture/system-overview.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/system-overview.md), [`docs/architecture/flows.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/flows.md) |
| `docs/consulting/internal/Capability_Maturity_Matrix.md` | Internal scoring matrix: implemented vs supported vs pilot-ready | [`guardian/guardian_api.py`](/Volumes/Dev_SSD/Codexify-main/guardian/guardian_api.py), route modules in `guardian/routes/`, supported profile YAML |
| `docs/consulting/internal/Technical_Due_Diligence_QA_Playbook.md` | Standard answers/evidence map for CTO/architecture diligence | `tests/`, `docs/architecture/*`, `config/supported_profiles/*`, `docker-compose*.yml` |
| `docs/consulting/sow/AI_Workflow_App_SOW_Language.md` | Reusable SOW language for AI workflow app builds | [`frontend/src/components/persona/layout/AppShell.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/components/persona/layout/AppShell.tsx), [`guardian/routes/chat.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/chat.py) |
| `docs/consulting/sow/RAG_and_Document_Intelligence_SOW_Language.md` | Reusable SOW language for document intelligence deployments | [`guardian/routes/documents.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/documents.py), [`guardian/routes/media.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/media.py), [`guardian/workers/document_embed_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/document_embed_worker.py) |
| `docs/consulting/compliance/Risk_and_Data_Boundary_Notes.md` | Data privacy, identity, and permission-boundary notes for compliance discussions | [`guardian/core/dependencies.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/dependencies.py), [`guardian/core/capability_policy.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/capability_policy.py), [`guardian/core/public_exposure.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/public_exposure.py) |
| `docs/consulting/case-study/Codexify_As_Reference_Implementation.md` | Case-study framing that separates proven behavior from roadmap | [`docs/architecture/00-current-state.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/00-current-state.md), `docs/proofs/`, `tests/proofs/` |

## Open Questions for Resonant Jones

1. Which client archetype should anchor the first consulting packaging pass: SMB ops teams, enterprise internal-platform teams, or product startups?
2. Should the consulting narrative prioritize the currently supported beta profile only, or include internal/quarantined surfaces as “pilot-track capabilities” in the same deck?
3. Do you want Codexify’s persona/memory surfaces framed as first-class offerings now, or as optional layers behind workflow and retrieval foundations?
4. Is the preferred sales motion “architecture + build partnership” or “diagnostic audit + hardening roadmap” first?
5. Which proof artifacts should be considered mandatory in every consulting proposal appendix (tests, runtime proof docs, architecture status docs)?

## Appendix: Important Files and Directories

### Runtime and architecture anchors

- [`README.md`](/Volumes/Dev_SSD/Codexify-main/README.md)
- [`docs/architecture/00-current-state.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/00-current-state.md)
- [`docs/architecture/system-overview.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/system-overview.md)
- [`docs/architecture/flows.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/flows.md)
- [`docs/architecture/config-and-ops.md`](/Volumes/Dev_SSD/Codexify-main/docs/architecture/config-and-ops.md)

### Infra and config

- [`docker-compose.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.yml)
- [`docker-compose.runtime.yml`](/Volumes/Dev_SSD/Codexify-main/docker-compose.runtime.yml)
- [`config/supported_profiles/v1-local-core-web-mcp.yaml`](/Volumes/Dev_SSD/Codexify-main/config/supported_profiles/v1-local-core-web-mcp.yaml)
- [` .env.example`](/Volumes/Dev_SSD/Codexify-main/.env.example)

### Backend execution path

- [`guardian/guardian_api.py`](/Volumes/Dev_SSD/Codexify-main/guardian/guardian_api.py)
- [`guardian/routes/chat.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/chat.py)
- [`guardian/core/chat_completion_service.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/chat_completion_service.py)
- [`guardian/workers/chat_worker.py`](/Volumes/Dev_SSD/Codexify-main/guardian/workers/chat_worker.py)
- [`guardian/queue/redis_queue.py`](/Volumes/Dev_SSD/Codexify-main/guardian/queue/redis_queue.py)

### Retrieval and documents

- [`guardian/routes/media.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/media.py)
- [`guardian/routes/documents.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/documents.py)
- [`guardian/vector/store.py`](/Volumes/Dev_SSD/Codexify-main/guardian/vector/store.py)
- [`backend/rag/embedder.py`](/Volumes/Dev_SSD/Codexify-main/backend/rag/embedder.py)
- [`guardian/routes/obsidian.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/obsidian.py)
- [`guardian/obsidian/indexer.py`](/Volumes/Dev_SSD/Codexify-main/guardian/obsidian/indexer.py)

### Governance/extensibility

- [`guardian/core/provider_registry.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/provider_registry.py)
- [`guardian/core/capability_policy.py`](/Volumes/Dev_SSD/Codexify-main/guardian/core/capability_policy.py)
- [`guardian/routes/command_bus.py`](/Volumes/Dev_SSD/Codexify-main/guardian/routes/command_bus.py)
- [`guardian/plugins/plugin_manifest.py`](/Volumes/Dev_SSD/Codexify-main/guardian/plugins/plugin_manifest.py)

### Frontend product surfaces

- [`frontend/src/App.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/App.tsx)
- [`frontend/src/components/persona/layout/AppShell.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/components/persona/layout/AppShell.tsx)
- [`frontend/src/features/chat/GuardianChat.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/chat/GuardianChat.tsx)
- [`frontend/src/features/settings/SettingsView.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/settings/SettingsView.tsx)
- [`frontend/src/features/commandCenter/CommandCenterPage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/commandCenter/CommandCenterPage.tsx)
- [`frontend/src/features/personaStudio/PersonaStudioPage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/personaStudio/PersonaStudioPage.tsx)
- [`frontend/src/features/flowBuilder/FlowBuilderPage.tsx`](/Volumes/Dev_SSD/Codexify-main/frontend/src/features/flowBuilder/FlowBuilderPage.tsx)

### Test and proof surfaces

- `tests/` (271 Python test files)
- `frontend/src` test suites (145 test/spec files)
- `tests/proofs/`
- `docs/proofs/`
