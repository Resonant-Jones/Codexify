# Core Code Reading Path

## 1. Title and purpose

This document is a guided code-reading path for understanding Codexify's current core runtime.

It is a development orientation aid, not a release promise, ADR, implementation plan, or exhaustive code walkthrough.

## 2. Source set and interpretation rules

### Required pre-read source set

1. `/docs/architecture/00-current-state.md`
2. `/docs/architecture/adr/adr-index.md`
3. `/docs/architecture/README.md`
4. `/docs/architecture/codexify-development-map-v1.md`
5. `/docs/architecture/generated/codexify-development-map-v1/README.md`
6. `/docs/architecture/system-overview.md`
7. `/docs/architecture/flows.md`
8. `/docs/architecture/modules-and-ownership.md`
9. `/docs/architecture/data-and-storage.md`
10. `/docs/architecture/config-and-ops.md`
11. `/docs/architecture/tech-debt-and-risks.md`

### Interpretation rules

- `00-current-state.md` wins for short-horizon release truth.
- `codexify-development-map-v1.md` is the visual companion to this reading guide.
- Generated Mermaid and SVG artifacts are convenience outputs; they do not replace the source map.
- Code-reading order does not imply ownership priority, release maturity, or shipped support by itself.
- Runtime topology and UI canon are adjacent but not interchangeable truth layers.

## 3. How to use this guide

Read the passes in order from 1 to 10.

Each pass gives:

- files to open
- why they matter
- what to inspect
- what not to infer from that pass alone
- companion docs for interpretation and proof boundaries

Use this as a map for orientation and dependency awareness, then verify claims against live current-state and supported-path proof artifacts before treating behavior as release truth.

## 4. Pass 1: Runtime entry and app shell

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/guardian_api.py` | FastAPI composition root and route wiring | startup wiring, middleware, mounted routers, `/api/events` surfaces | Router inclusion alone is not release support; route presence is not proof of shipped posture | `00-current-state.md`, `system-overview.md`, `config-and-ops.md` |
| `guardian/server/run.py` | Runtime launch path used by backend entry flow | how server bootstraps `guardian_api` | Server startup success does not prove queue, worker, or provider execution health | `config-and-ops.md`, `flows.md` |
| `frontend/src/App.tsx` | Frontend top-level route/view shell entry | route-to-view structure, session wiring, surface boundaries | Frontend route presence is not backend runtime topology truth | `ui-diagrams-v1.md`, `modules-and-ownership.md` |
| `frontend/src/components/persona/layout/AppShell.tsx` | UI shell and tokenized layout frame | shell composition, visible surfaces, diagnostics placement | UI shell structure is not queue/worker/provider execution proof | `ui-diagrams-v1.md`, `codexify-development-map-v1.md` |

## 5. Pass 2: Chat/thread acceptance path

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/routes/chat.py` | Main chat message and completion acceptance seam | message persistence, completion route contract, turn-lock and enqueue handoff | Route acceptance is not completion and not UI delivery | `flows.md`, `00-current-state.md`, `chat-runtime-contract.md` |
| `guardian/routes/threads.py` | Thread lifecycle and thread identity boundary | thread create/list/update semantics and thread ownership shape | Thread CRUD success does not prove worker execution lane behavior | `system-overview.md`, `data-and-storage.md` |

## 6. Pass 3: Redis queue, task events, locks, and heartbeat

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/queue/redis_queue.py` | Queue transport and Redis integration seam | queue names, enqueue/dequeue helpers, cancellation and heartbeat utilities | Redis transport health does not prove transcript durability | `data-and-storage.md`, `config-and-ops.md` |
| `guardian/queue/task_events.py` | Task event publication stream | `task.created/running/terminal` publish behavior and stream semantics | Task-event publication is not UI receipt | `flows.md`, `tech-debt-and-risks.md` |
| `guardian/queue/turn_lock.py` | Canonical per-thread lock ownership | lock envelope, stale-lock checks, release conditions | Lock acquisition does not prove downstream worker success | `flows.md`, `data-and-storage.md` |
| `guardian/routes/health.py` | Queue/provider/worker health reporting surfaces | `/health`, `/health/chat`, `/api/health/llm` distinctions | Health snapshots are operational truth, not durable chat-output truth | `00-current-state.md`, `config-and-ops.md` |

Redis reading posture for this pass:

- Redis is queue, lock, event, and heartbeat transport.
- Redis state is operational/ephemeral, not the durable system of record.

## 7. Pass 4: Worker execution lane

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/workers/chat_worker.py` | Executes accepted chat tasks | dequeue, completion invocation, assistant persistence, terminal events, lock release | Queue dequeue and run start do not guarantee final UI visibility | `flows.md`, `00-current-state.md` |
| `guardian/workers/document_embed_worker.py` | Executes document embedding jobs | embedding lifecycle transitions and retrieval corpus updates | Document parse success is not embedding-readiness proof | `data-and-storage.md`, `flows.md` |
| `guardian/workers/chat_embedding_worker.py` | Executes chat embedding lane | chat embedding queue consumption and vector write behavior | Embedding availability does not prove retrieval selection in a specific turn | `data-and-storage.md`, `tech-debt-and-risks.md` |
| `guardian/workers/cron_worker.py` | Executes cron queue tasks in control-plane lane | run-state transitions and task execution loop | Cron worker presence is not a broad user-facing cron release promise | `00-current-state.md`, `config-and-ops.md` |

Worker lane interpretation:

- Accepted tasks become executed work only when workers dequeue and run them.
- Worker downtime or stale heartbeat can stall core chat despite accepted route responses.

## 8. Pass 5: Completion assembly and context formation

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/core/chat_completion_service.py` | Core completion assembly seam | recent message loading, provider-ready payload assembly, persisted completion breadcrumbs | Debug assembly metadata alone is not executed-path proof | `flows.md`, `00-current-state.md` |
| `guardian/context/broker.py` | Context policy and retrieval composition | thread/doc/vector/memory/workspace context composition and provenance signals | Retrieval selection intent is not proof of injected context unless executed-path evidence confirms it | `flows.md`, `data-and-storage.md` |
| `guardian/memoryos/retriever.py` | Memory retrieval adapter in context lane | memory retrieval scope and fallback behavior | Memory retrieval availability does not imply broad continuity product support | `system-overview.md`, `tech-debt-and-risks.md` |
| `guardian/vector/store.py` | Vector retrieval backend seam | search/read APIs and store behavior used by broker and workers | Vector searchability alone is weaker than worker-visible injected-context proof | `data-and-storage.md`, `00-current-state.md` |

Workspace-local retrieval caveat:

- Current-state and proof docs must be used to confirm when workspace-local retrieval is release-valid for supported posture.
- Retrieval traces are diagnostic unless backed by executed-path proof surfaces.

## 9. Pass 6: Provider routing and model boundary

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/core/ai_router.py` | Provider execution boundary and fallback lane | selected-provider execution path, timeout handling, response normalization | Provider routing intent is not equivalent to successful completion persistence | `flows.md`, `config-and-ops.md` |
| `guardian/core/llm_catalog.py` | Provider/model inventory surface | what catalog exposes by default vs diagnostic/operator views | Catalog visibility is not release support | `00-current-state.md`, `config-and-ops.md` |
| `guardian/core/provider_state.py` | Provider runtime health/state helpers | runtime status shaping and propagation surfaces | Provider runtime availability is not equal to completion success | `chat-runtime-contract.md`, `system-overview.md` |
| `guardian/core/provider_registry.py` | Governance posture source for provider lanes | authorized/disabled/local-only categories and policy-facing decisions | Cloud inventory presence is not local-first beta support | `00-current-state.md`, `config-and-ops.md` |

Provider boundary interpretation:

- Supported beta posture is local-only unless `00-current-state.md` explicitly says otherwise.
- Health, catalog, and supported-profile contract must be read together.

## 10. Pass 7: Persistence and durable state

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/db/models.py` | Durable entity contract and FK edges | core tables (`projects`, `chat_threads`, `chat_messages`, docs/media, control-plane tables) | Table presence does not imply feature is release-promised | `data-and-storage.md`, `00-current-state.md` |
| `guardian/core/db.py` | DB adapter and persistence entry lane | session/transaction helpers and runtime DB access patterns | DB row writes alone do not prove event or UI delivery | `flows.md`, `modules-and-ownership.md` |
| `guardian/core/storage.py` | Media/object storage boundary | storage backend selection and bytes persistence | Stored bytes are not equivalent to retrieval-ready semantic context | `data-and-storage.md`, `config-and-ops.md` |
| `guardian/core/outbox.py` | Durable event outbox seam | event persistence and stream export behavior | Outbox publication is not guaranteed client consumption | `data-and-storage.md`, `flows.md` |

Durability interpretation:

- Postgres is the system of record.
- Durable metadata and operational queue state must be kept conceptually separate.

## 11. Pass 8: Media/document ingestion and retrieval corpus

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/routes/media.py` | Upload validation and ingestion entrypoint | content validation, dedupe, storage writes, embed enqueue trigger | Upload acceptance does not prove parse or embed completion | `flows.md`, `data-and-storage.md` |
| `guardian/routes/documents.py` | Document metadata and readback surface | document identity, detail readback, linkage surfaces | Document detail availability does not prove retrieval inclusion in a turn | `00-current-state.md`, `flows.md` |
| `guardian/services/document_parsers/` | Parsing implementation seam | parser capability boundaries and failure handling | Parser output alone is not semantic-retrieval readiness | `data-and-storage.md`, `tech-debt-and-risks.md` |
| `guardian/runtime/embed/embedder.py` | Embedding runtime adapter | embedding backend readiness and write path assumptions | Embedder readiness does not imply corpus freshness without worker success | `config-and-ops.md`, `data-and-storage.md` |

Ingestion interpretation:

- Document/thread/project linkage defines retrieval scope eligibility.
- Embedding lifecycle state is required for retrieval availability, not just upload success.

## 12. Pass 9: Internal/control-plane lanes

| Files to open | Why they matter | What to inspect | What not to infer | Companion docs |
|---|---|---|---|---|
| `guardian/routes/command_bus.py` | Command bus route contract | invoke contract, policy gates, run lifecycle surfaces | Route existence is not broad end-user feature support | `00-current-state.md`, `config-and-ops.md` |
| `guardian/command_bus/` | Control-plane implementation seam | policy, idempotency, loopback execution boundaries | Internal command tooling should not be read as open agent autonomy | `modules-and-ownership.md`, `tech-debt-and-risks.md` |
| `guardian/routes/cron.py` | Cron control-plane route | job CRUD and queue handoff semantics | Cron route presence is not broad cron UX release promise | `00-current-state.md`, `flows.md` |
| `guardian/cron/` | Scheduler/control-plane implementation | due-run scanning and run enqueueing behavior | Scheduler internals do not imply mature operator UX | `config-and-ops.md`, `tech-debt-and-risks.md` |
| `guardian/routes/agent_orchestration.py` | Agent control-plane/orchestration lane | work-order control surfaces and status inspection semantics | Control-plane visibility does not imply fully shipped delegation runtime promises | `00-current-state.md`, `system-overview.md` |

Control-plane interpretation:

- Treat these lanes as internal/control-plane unless current-state explicitly promotes a surface.
- Keep command/tool behavior bounded and policy-governed.

## 13. Pass 10: Optional, experimental, and not-release-promise lanes

| Anchor set | Current posture to apply while reading | What not to infer | Companion docs |
|---|---|---|---|
| Graph and Neo4j lane: `guardian/memory_graph/graph_backend_factory.py`, `guardian/memory_graph/neo4j_graph_backend.py`, `guardian/routes/graph.py` | Optional and feature-flagged, default-off on supported Compose posture | Do not treat graph writes as baseline shipped user-facing behavior | `00-current-state.md`, `config-and-ops.md`, `codexify-development-map-v1.md` |
| Federation and sync lane: `guardian/routes/federation.py`, `guardian/routes/federation_context.py`, `guardian/sync/api.py` | Experimental/expansion lane | Do not read route presence as current release promise | `00-current-state.md`, `system-overview.md`, `tech-debt-and-risks.md` |
| Flow Builder contracts/docs: `docs/architecture/adr/006-flow-builder-elicitation-lane.md`, `docs/architecture/adr/014-flow-builder-thread-draft-and-receipts-contract.md`, `docs/architecture/adr/027-flow-builder-typed-surface-and-run-receipt-contract.md` | Experimental/planning/contracts only | Do not infer shipped runtime Flow Builder surface from contract docs | `00-current-state.md`, `README.md` |
| Campaign Runner and Execution Ledger seams: `guardian/agents/campaign_runner_store.py`, `guardian/agents/execution_ledger_store.py`, `docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`, `docs/architecture/execution-ledger-gate-artifacts-contract.md` | Internal/control-plane and contract lane | Do not treat these as broad user-facing shipped product promises | `00-current-state.md`, `codexify-development-map-v1.md` |
| Job Intelligence and Persona Studio docs: `docs/specs/job-intelligence-layer/README.md`, `docs/architecture/persona-studio.md`, `docs/architecture/persona-studio-spec.md` | Experimental/planning or optional surface | Do not treat spec/document presence as current release support | `00-current-state.md`, `README.md` |
| Desktop shell lane: `src-tauri/`, frontend runtime bridge files | Optional shell around current stack | Do not treat desktop packaging as a replacement for supported local Docker Compose install path | `00-current-state.md`, `config-and-ops.md`, `codexify-development-map-v1.md` |

How to identify maturity in this pass:

- Check `00-current-state.md` first for explicit support claims.
- Treat planning contracts/specs as doctrine and design input, not shipped runtime behavior.
- Keep optional, feature-flagged, and internal labels conservative.

## 14. Suggested first reading route

1. `docs/architecture/00-current-state.md`
2. `docs/architecture/codexify-development-map-v1.md`
3. `docs/architecture/generated/codexify-development-map-v1/01-current-codexify-system-map.svg`
4. `docs/architecture/flows.md`
5. `guardian/routes/chat.py`
6. `guardian/queue/redis_queue.py`
7. `guardian/workers/chat_worker.py`
8. `guardian/core/chat_completion_service.py`
9. `guardian/context/broker.py`
10. `guardian/core/ai_router.py`
11. `guardian/db/models.py`

## 15. Common misreads to avoid

- Route acceptance is not completion.
- Task-event publication is not UI receipt.
- Catalog presence is not provider support.
- Doc presence is not shipped release surface.
- Generated diagrams are convenience artifacts, not governing truth.
- UI canon is not backend runtime topology.
- Redis state is operational/ephemeral, not the durable system of record.

## 16. Follow-up candidates

- Link this guide from `docs/architecture/README.md` in a separate task.
- Create a companion "Core Chat Flow Walkthrough" if deeper line-level explanation is needed.
- Add rendered callout diagrams later if a visual pass-by-pass onboarding aid is useful.
