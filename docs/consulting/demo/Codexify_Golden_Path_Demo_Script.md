# Codexify Golden Path Demo Script

## Purpose

This document provides a repeatable, trust-first demo path for presenting Codexify as a reference implementation for ResonantConstructs.ai consulting work.

The goal is to build credibility through clear, evidence-backed walkthroughs, not feature spectacle. The demo should help buyers connect technical proof to operational pain and then move naturally into scoped consulting outcomes.

## Demo Positioning

Codexify is not the offer. Codexify is the evidence.

Use the demo to show how ResonantConstructs.ai designs AI systems around real workflow constraints, data boundaries, and operating reality. Position Codexify as an interactive capability menu that demonstrates architecture patterns, implementation quality, and governance posture that can be adapted for a client environment.

## Ideal Audience

Best fit audiences:

- Technical founders
- CTOs
- Operations leaders
- Privacy-conscious business owners
- Teams considering internal AI assistants
- Organizations with scattered documents or knowledge silos
- Buyers evaluating local-first or hybrid AI infrastructure

Avoid full technical depth too early for:

- Buyers who have not yet named a concrete business pain
- Buyers only asking for high-level strategy framing
- Non-technical stakeholders likely to be overwhelmed by route-level and queue-level detail

## Demo Preconditions

- Running Codexify environment on the supported local Docker Compose path
- Demo-safe dataset prepared and reviewed
- No private user data visible in threads, uploads, or logs
- Stable demo thread or prepared static walkthrough sequence
- Known route through UI screens and backup route if a view is unavailable
- Fallback screenshots and static explanation ready if runtime is unavailable
- Explicit maturity boundary language prepared before starting
- No experimental, internal-only, or quarantined surfaces shown without context

## Demo Principles

- Start with business pain, not feature inventory
- Show fewer things clearly
- Name maturity boundaries before the buyer discovers them
- Translate every technical behavior into operational value
- Do not demo roadmap as supported capability
- Never imply compliance readiness without scoped review
- Treat Codexify as proof-of-work, not a product pitch
- Keep “implemented”, “supported now”, and “internal/quarantined” separate

## Recommended Demo Lengths

| Demo Type | Duration | Best For | What to Emphasize |
|---|---:|---|---|
| 5-minute credibility demo | 5 minutes | Intro calls, executive screening | Trust boundary, local-first posture, one clean workflow proof, clear maturity boundaries |
| 15-minute discovery demo | 15 minutes | Discovery calls with mixed stakeholders | Golden path walkthrough from chat to retrieval with business pain mapping |
| 30-minute technical buyer demo | 30 minutes | CTO and architecture evaluators | Queue-backed execution model, governance, retrieval evidence, operator diagnostics |
| 60-minute architecture workshop | 60 minutes | Paid discovery or deep due diligence | End-to-end architecture decisions, failure modes, rollout constraints, scoped implementation plan |

## Golden Path Overview

Recommended order:

1. Trust boundary and runtime posture
2. Core assistant workflow
3. Document and media ingestion
4. Retrieval and local knowledge workflows
5. Provider and model governance
6. Persona and configuration layer
7. Extensibility, plugins, and command surfaces
8. Operator and diagnostic thinking

Why this order works:

- It starts with risk and control before capabilities.
- It demonstrates baseline value before advanced system depth.
- It keeps support posture explicit so trust is built early.
- It transitions naturally from proof-of-capability into consulting scope definition.

## Step 1: Trust Boundary and Runtime Posture

### What to Show

- Supported profile posture and route maturity model in `config/supported_profiles/v1-local-core-web-mcp.yaml`.
- Current release truth and “do not assume” constraints in `docs/architecture/00-current-state.md`.
- Local runtime topology and service boundaries from `docker-compose.yml` and `docs/architecture/system-overview.md`.
- Health surfaces: `/health`, `/health/chat`, and `/api/health/llm` as runtime truth points.

### What the Client Should Understand

- This is a deliberate local-first architecture, not accidental local development setup.
- Supported capabilities are explicitly bounded; not all code paths are release claims.
- The system is designed with explicit route posture and operational boundaries.

### Business Pain It Maps To

- “We cannot adopt AI if we cannot control where data and execution live.”
- “Our team does not trust black-box demos without runtime clarity.”

### Evidence Anchors

- `docs/architecture/00-current-state.md`
- `config/supported_profiles/v1-local-core-web-mcp.yaml`
- `docker-compose.yml`
- `docs/architecture/system-overview.md`
- `docs/architecture/config-and-ops.md`

### What Not to Overclaim

- Do not claim every mounted route is customer-ready.
- Do not claim cloud posture is part of current supported beta when local-only flags are active.
- Do not imply packaged desktop supersedes supported Compose posture.

### Transition Line

“Now that the trust boundary is explicit, let’s show the core workflow this architecture is actually built to support.”

## Step 2: Core Assistant Workflow

### What to Show

- Thread creation, message post, completion request flow (`/api/chat/threads`, `/api/chat/{thread_id}/messages`, `/api/chat/{thread_id}/complete`).
- Queue-backed handoff and worker execution seam in:
  - `guardian/routes/chat.py`
  - `guardian/workers/chat_worker.py`
  - `guardian/core/chat_completion_service.py`
  - `guardian/queue/redis_queue.py`
  - `guardian/queue/task_events.py`
- UI execution experience from `frontend/src/features/chat/GuardianChat.tsx`.

### What the Client Should Understand

- Acceptance and completion are different events in a queue-backed architecture.
- Runtime resilience comes from explicit request lifecycle handling, not optimistic UI assumptions.
- This reflects real operational design for asynchronous AI work, not a synchronous toy chat loop.

### Business Pain It Maps To

- “Our AI pilot looks fine in demos but fails under real load and retries.”
- “We cannot debug where failures happen across API, queue, worker, and provider.”

### Evidence Anchors

- `guardian/routes/chat.py`
- `guardian/workers/chat_worker.py`
- `guardian/core/chat_completion_service.py`
- `guardian/queue/redis_queue.py`
- `guardian/queue/task_events.py`
- `docs/architecture/flows.md`

### What Not to Overclaim

- Do not claim route acceptance means model completion succeeded.
- Do not claim task event publication guarantees UI receipt.
- Do not imply every failure mode is fully automated; operator diagnostics still matter.

### Transition Line

“Once the core run path is clear, we can show how your knowledge actually enters and becomes usable in this system.”

## Step 3: Document and Media Ingestion

### What to Show

- Upload flow and media/document handling via `guardian/routes/media.py`.
- Embedding queue workflow in `guardian/workers/document_embed_worker.py`.
- Retrieval storage seam in `guardian/vector/store.py`.
- User-facing implications from chat and settings surfaces.

### What the Client Should Understand

- Ingestion is an operational pipeline: validate, persist, extract, enqueue, embed, and retrieve.
- Durable AI knowledge requires workflow discipline, not one-click “AI upload” promises.
- The system is designed to keep ingestion observable and recoverable.

### Business Pain It Maps To

- “Our docs are scattered and AI answers are inconsistent.”
- “We do not know when uploaded content is actually ready for retrieval.”

### Evidence Anchors

- `guardian/routes/media.py`
- `guardian/workers/document_embed_worker.py`
- `guardian/vector/store.py`
- `docs/architecture/flows.md`
- `docs/architecture/system-overview.md`

### What Not to Overclaim

- Do not claim every content type has identical parsing quality.
- Do not imply ingestion readiness equals business-grade retrieval relevance.
- Do not present this as enterprise document governance by default.

### Transition Line

“Now that content is ingested, the critical question is whether the assistant can use the right knowledge in the right boundary.”

## Step 4: Retrieval and Local Knowledge Workflows

### What to Show

- Retrieval context assembly and source-mode behavior in `guardian/core/chat_completion_service.py`.
- Workspace and Obsidian pathway surfaces in:
  - `guardian/routes/obsidian.py`
  - `guardian/obsidian/indexer.py`
- Current supported proof posture statements in `docs/architecture/00-current-state.md` and `docs/architecture/flows.md`.

### What the Client Should Understand

- Retrieval is policy-shaped and boundary-aware, not blanket vector recall.
- Local knowledge workflows can be integrated while preserving user and thread boundaries.
- Searchability alone is weaker evidence than executed completion-path inclusion.

### Business Pain It Maps To

- “AI can search, but it does not reliably use the right internal context.”
- “We need private retrieval without flattening all team knowledge into one global pool.”

### Evidence Anchors

- `guardian/core/chat_completion_service.py`
- `guardian/routes/obsidian.py`
- `guardian/obsidian/indexer.py`
- `docs/architecture/00-current-state.md`
- `docs/architecture/flows.md`

### What Not to Overclaim

- Do not claim any retrieval trace alone is full proof of completion influence.
- Do not imply connector/federation breadth when showing local Obsidian scope.
- Do not promise zero false positives/negatives in semantic retrieval.

### Transition Line

“Once knowledge flow is visible, model governance becomes the next trust decision.”

## Step 5: Provider and Model Governance

### What to Show

- Provider governance registry in `guardian/core/provider_registry.py`.
- Runtime routing behavior and output normalization seams in `guardian/core/ai_router.py`.
- Supported provider contract in `config/supported_profiles/v1-local-core-web-mcp.yaml`.
- Operational interpretation guidance in `docs/architecture/config-and-ops.md`.

### What the Client Should Understand

- Provider inventory, configured provider, and supported provider posture are not the same concept.
- Governance is explicit and inspectable, enabling controlled local/cloud posture decisions.
- Model routing can be policy-driven instead of ad hoc per engineer.

### Business Pain It Maps To

- “Model selection and cloud usage are unmanaged in our organization.”
- “We need to avoid lock-in and still keep reliable defaults.”

### Evidence Anchors

- `guardian/core/provider_registry.py`
- `guardian/core/ai_router.py`
- `config/supported_profiles/v1-local-core-web-mcp.yaml`
- `docs/architecture/config-and-ops.md`
- `frontend/src/features/settings/SettingsView.tsx`

### What Not to Overclaim

- Do not claim all listed providers are currently supported in release posture.
- Do not imply cloud providers are approved just because code paths exist.
- Do not claim compliance coverage from provider toggles alone.

### Transition Line

“With provider governance in place, we can show how persona and configuration shape behavior without losing control.”

## Step 6: Persona and Configuration Layer

### What to Show

- Settings and runtime config entry points in `frontend/src/features/settings/SettingsView.tsx`.
- Persona Studio configuration and local draft harness in `frontend/src/features/personaStudio/PersonaStudioPage.tsx`.
- Auth/exposure boundary behavior in:
  - `guardian/core/dependencies.py`
  - `guardian/core/public_exposure.py`

### What the Client Should Understand

- Persona and prompt structure can be managed as a system layer, not hidden one-off prompts.
- Runtime config, auth mode, and exposure policy are explicit operating controls.
- The right pattern is governed behavior design, not prompt mythology.

### Business Pain It Maps To

- “Assistant behavior is inconsistent across teams and users.”
- “We need controlled assistant personalization without uncontrolled prompt drift.”

### Evidence Anchors

- `frontend/src/features/settings/SettingsView.tsx`
- `frontend/src/features/personaStudio/PersonaStudioPage.tsx`
- `guardian/core/dependencies.py`
- `guardian/core/public_exposure.py`
- `docs/architecture/config-and-ops.md`

### What Not to Overclaim

- Do not present persona tuning as a substitute for policy enforcement.
- Do not imply all persona surfaces are production governance workflows.
- Do not suggest this alone solves organizational AI governance.

### Transition Line

“The next layer is how extensibility works without turning the system into an unbounded execution surface.”

## Step 7: Extensibility, Plugins, and Command Surfaces

### What to Show

- Plugin manifest contract and validation in `guardian/plugins/plugin_manifest.py`.
- Plugin discovery rules in `guardian/plugins/plugin_loader.py`.
- Command surface entry point in `guardian/routes/command_bus.py`.
- Capability policy and grant resolution seams in:
  - `guardian/core/capability_policy.py`
  - `guardian/core/capability_grants.py`
- Internal-only posture of command bus in `config/supported_profiles/v1-local-core-web-mcp.yaml`.

### What the Client Should Understand

- Extensibility can be structured with typed manifests, policies, and explicit route posture.
- Capability grants and policy checks are code-level governance primitives.
- This is architecture evidence for safe extension design, not blanket “agents can do anything.”

### Business Pain It Maps To

- “We need integrations and automation, but we cannot accept uncontrolled tool execution.”
- “We need permission boundaries and auditability before we expand AI actions.”

### Evidence Anchors

- `guardian/plugins/plugin_manifest.py`
- `guardian/plugins/plugin_loader.py`
- `guardian/routes/command_bus.py`
- `guardian/core/capability_policy.py`
- `guardian/core/capability_grants.py`
- `config/supported_profiles/v1-local-core-web-mcp.yaml`

### What Not to Overclaim

- Do not claim command surfaces are all public-facing in current support posture.
- Do not imply autonomous multi-step orchestration is a default supported behavior.
- Do not claim connector or plugin breadth without scoped implementation proof.

### Transition Line

“Finally, we show how operators diagnose reality so this becomes an operating system pattern, not a fragile demo.”

## Step 8: Operator and Diagnostic Thinking

### What to Show

- Health and operations interpretation workflow from `docs/architecture/config-and-ops.md`.
- Queue/event semantics and terminal visibility behavior in `guardian/queue/task_events.py` and `docs/architecture/flows.md`.
- Command Center surface as operator aid in `frontend/src/features/commandCenter/CommandCenterPage.tsx`.
- Desktop runtime contract signals in `src-tauri/src/commands.rs`.

### What the Client Should Understand

- Operational confidence comes from layered evidence: health, queue state, worker behavior, and persisted outcomes.
- Diagnostic visibility is necessary for production-worthy AI systems.
- This is a design style ResonantConstructs.ai can apply to client-specific environments.

### Business Pain It Maps To

- “We cannot support AI operations because failures are opaque.”
- “Our pilots fail because there is no diagnostic model for runtime behavior.”

### Evidence Anchors

- `docs/architecture/config-and-ops.md`
- `docs/architecture/flows.md`
- `guardian/queue/task_events.py`
- `frontend/src/features/commandCenter/CommandCenterPage.tsx`
- `src-tauri/src/commands.rs`

### What Not to Overclaim

- Do not claim one UI panel is complete observability.
- Do not present internal operator surfaces as generally released customer tooling.
- Do not claim that diagnostics eliminate the need for scoped reliability engineering.

### Transition Line

“The value here is not a demo artifact; it is the operating pattern we can adapt to your environment with explicit constraints.”

## Optional Advanced Modules to Mention Carefully

Use these modules only after core pain and core path are clear.

| Module | How to Mention Safely | What Not to Promise | When Relevant in Engagement |
|---|---|---|---|
| Agent orchestration | Mention as internal or constrained exploration surfaces | Full autonomous operations as default supported behavior | When a client needs bounded automation lanes and formal approval controls |
| Federation | Mention as architecture direction for selective sync patterns | Turnkey multi-node deployment readiness | When client has explicit cross-node trust and sync requirements |
| Voice | Mention as optional capability lane with current constraints | Universal production voice quality and complete workflow coverage | When operations require voice-specific UX and model/provider evaluation |
| Connectors | Mention as scoped integration pattern requiring boundary design | Plug-and-play enterprise integration breadth | When client has named systems and governance expectations |
| Cron and automation | Mention as scheduler/job primitives present in architecture | Fully managed business process automation out of the box | When client needs defined periodic AI workflows |
| Command Center | Mention as operator-facing aid, not sole release truth source | Complete observability replacement for logs/health/events | When client has operational maturity goals and incident workflows |
| WebSocket/realtime surfaces | Mention as part of runtime event options and evolution | Guaranteed end-user realtime delivery across all failure modes | When latency-sensitive workflow and transport constraints are explicit |

## What Not to Show First

Do not lead with these in early demos:

- Persona mythology
- Experimental agent orchestration
- Federation surfaces
- Voice features
- Plugin internals
- Deep architecture diagrams
- Feature inventory tours
- Roadmap-heavy claims

Reason: these paths create cognitive load, invite unsupported assumptions, and pull the conversation away from the client’s immediate pain.

## What Not to Overclaim

- Internal-only or quarantined routes are not customer-ready promises
- Experimental agent/orchestration seams are not default production behavior
- Federation is not equivalent to live supported multi-node deployment
- Voice and connector surfaces should not be sold as fully mature without scope proof
- Compliance readiness cannot be implied from architecture alone
- Production deployment assumptions must be scoped and validated per environment
- Unsupported surfaces must remain explicitly unsupported
- “Code exists” is not the same as “supported now”
- Route acceptance is not completion
- Event publication is not guaranteed UI receipt

## Client Pain Mapping

| Demo Moment | Client Pain | What Codexify Proves | Consulting Offer Path |
|---|---|---|---|
| Trust boundary posture | “We need private AI guardrails.” | Local-first supported contract, explicit route posture, clear boundaries | AI readiness and boundary audit |
| Core chat execution flow | “Our pilots break under real operations.” | Queue-backed execution and lifecycle-aware design | Internal AI assistant architecture and runtime hardening |
| Document/media ingestion | “Our knowledge is fragmented.” | Repeatable ingest to retrieval pipeline with worker-backed processing | Secure document intelligence and knowledge pipeline design |
| Retrieval workflow | “AI answers are generic or wrong.” | Local knowledge retrieval with source-mode boundary logic | Private RAG implementation with scoped relevance tuning |
| Provider governance | “Model usage is unmanaged and risky.” | Policy-shaped provider/model posture and health/catalog separation | Provider governance and routing strategy |
| Persona/config layer | “Assistant behavior is inconsistent by team.” | Configurable behavior layer with explicit runtime controls | AI workflow application design and operating model standardization |
| Extensibility/capability surfaces | “We need integrations without new risk.” | Typed plugin contracts and capability-grant patterns | Extensible system architecture with permission boundaries |
| Operator diagnostics | “We cannot support AI in production.” | Multi-surface diagnostic posture and failure-mode visibility | Operationalization, incident playbooks, and reliability roadmap |

## Technical Buyer Questions and Suggested Answers

| Buyer Question | Suggested Answer | Evidence Anchor |
|---|---|---|
| Is this production-ready? | Codexify is a local-first beta reference implementation with a defined supported path; readiness for your environment requires scoped validation and hardening. | `docs/architecture/00-current-state.md`, `config/supported_profiles/v1-local-core-web-mcp.yaml` |
| What runs locally? | The supported path is local Docker Compose with backend, workers, DB, Redis, and frontend on local infrastructure. | `docker-compose.yml`, `docs/architecture/system-overview.md` |
| What depends on cloud APIs? | Current supported posture is local-only by default; cloud-capable lanes exist but are policy-gated and not equivalent to supported release posture. | `config/supported_profiles/v1-local-core-web-mcp.yaml`, `docs/architecture/config-and-ops.md` |
| How do you prevent vendor lock-in? | Provider governance is explicit and routable through registry policy rather than hardcoded single-provider coupling. | `guardian/core/provider_registry.py`, `guardian/core/ai_router.py` |
| How is retrieval handled? | Retrieval is assembled through context broker/completion workflow with source-mode boundary logic and worker-executed completion evidence. | `guardian/core/chat_completion_service.py`, `docs/architecture/flows.md` |
| How do you handle sensitive data? | Exposure/auth behavior is explicit, local-first posture is default, and public allowlist mode is policy-gated. | `guardian/core/dependencies.py`, `guardian/core/public_exposure.py` |
| What happens when a model fails? | The architecture separates request lifecycle from provider state, so failures are diagnosable at queue/worker/provider layers rather than collapsed into one error. | `docs/architecture/flows.md`, `guardian/queue/task_events.py` |
| Is this autonomous agent behavior? | Not as a baseline supported claim; command and extension surfaces are bounded and posture-aware, with internal-only lanes called out. | `config/supported_profiles/v1-local-core-web-mcp.yaml`, `guardian/routes/command_bus.py` |
| Can this integrate with our documents? | The reference implementation proves ingestion, embedding, and retrieval pathways; client-specific adapters and governance are scoped per engagement. | `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py`, `guardian/vector/store.py` |
| How do you scope compliance? | We treat compliance as a scoped engagement deliverable tied to your controls, data classes, and deployment posture, not a generic demo claim. | `docs/architecture/config-and-ops.md`, `docs/architecture/00-current-state.md` |
| What would a client implementation include? | A bounded architecture slice: trust boundary design, retrieval/governance lanes, operations diagnostics, and rollout plan tied to your workflows. | `docs/architecture/system-overview.md`, `docs/architecture/flows.md` |
| What are the biggest risks? | Overclaiming unsupported surfaces, skipping operator visibility, and ignoring identity/permission boundaries during integration. | `docs/architecture/00-current-state.md`, `config/supported_profiles/v1-local-core-web-mcp.yaml` |

## Non-Technical Buyer Translation

- “This helps your team find and use internal knowledge without sending everything blindly into public tools.”
- “This shows how AI workflows can be governed instead of improvised.”
- “This demonstrates how local and cloud AI can be chosen deliberately instead of by accident.”
- “This is evidence of how we design operationally reliable AI systems, not a one-size-fits-all product pitch.”

## Suggested Talk Track

Opening:

“What we want to show today is not a product we are asking you to buy. Codexify is our reference implementation. It demonstrates how we design AI systems around real workflow constraints, trust boundaries, and operational reliability.”

Trust boundary transition:

“Before we show features, we start with posture. We separate what is implemented from what is supported now, and we call out internal and quarantined surfaces up front.”

Core workflow transition:

“Now let’s run the primary assistant flow and show where acceptance, execution, and completion are different stages. This is where many AI pilots break in production.”

Knowledge transition:

“Next, we show how documents and local knowledge become usable context in the assistant path, with explicit boundaries rather than hidden global memory assumptions.”

Governance transition:

“Then we show model governance and runtime controls, so provider choice is a policy decision, not a hidden default.”

Extensibility transition:

“Finally, we touch extensibility and operator diagnostics to show that this architecture can evolve safely without sacrificing control.”

Closing setup:

“The useful outcome from this demo is not to clone Codexify directly. The useful outcome is to identify which of these architecture patterns addresses your highest-cost AI workflow pain.”

## Demo Close

“The next useful step is not to copy Codexify into your environment. The next useful step is to identify which of these patterns solves a real operational problem for your team.”

“From there, we scope a bounded implementation slice around your data boundaries, workflow constraints, and operating model so results are measurable and trustworthy.”

## Follow-Up Offers

- AI readiness and workflow audit
  - Supported by: trust boundary posture, runtime preconditions, operator diagnostics
- Private knowledge-base and RAG implementation
  - Supported by: ingestion and retrieval steps with boundary-aware context assembly
- Internal AI assistant design
  - Supported by: queue-backed assistant flow, request lifecycle model, and UI interaction pattern
- Local-first AI infrastructure planning
  - Supported by: supported profile posture, Compose topology, and local/cloud governance framing
- Provider governance and model routing
  - Supported by: provider registry, routing controls, and health/catalog interpretation
- Secure document intelligence
  - Supported by: media/document pipeline and embedding worker architecture
- AI workflow application design
  - Supported by: persona/configuration layer and operational flow sequencing
- Plugin and extensible system architecture
  - Supported by: plugin manifest/loader contracts and capability policy seams
- AI governance and permission-boundary design
  - Supported by: capability grants/policy, auth and exposure boundaries, route posture model

## Internal Rehearsal Checklist

- [ ] Demo environment is healthy on supported local Compose path
- [ ] Demo-safe data is prepared and verified
- [ ] Supported vs internal vs quarantined boundaries are reviewed
- [ ] Client pain hypothesis is written before the call
- [ ] One primary follow-up offer is selected in advance
- [ ] No private data is visible in UI, logs, or uploads
- [ ] Fallback explanation or screenshots are ready
- [ ] No unsupported claims are in the talk track
- [ ] Close language is prepared and pain-driven

## Appendix: Evidence Anchors

- `config/supported_profiles/v1-local-core-web-mcp.yaml`
- `docker-compose.yml`
- `docker-compose.runtime.yml`
- `docs/architecture/00-current-state.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/config-and-ops.md`
- `guardian/routes/chat.py`
- `guardian/workers/chat_worker.py`
- `guardian/core/chat_completion_service.py`
- `guardian/queue/redis_queue.py`
- `guardian/queue/turn_lock.py`
- `guardian/queue/task_events.py`
- `guardian/core/provider_registry.py`
- `guardian/core/ai_router.py`
- `guardian/routes/media.py`
- `guardian/workers/document_embed_worker.py`
- `guardian/vector/store.py`
- `guardian/routes/obsidian.py`
- `guardian/obsidian/indexer.py`
- `guardian/core/capability_policy.py`
- `guardian/core/capability_grants.py`
- `guardian/core/dependencies.py`
- `guardian/core/public_exposure.py`
- `guardian/plugins/plugin_manifest.py`
- `guardian/plugins/plugin_loader.py`
- `guardian/routes/command_bus.py`
- `frontend/src/features/chat/GuardianChat.tsx`
- `frontend/src/features/settings/SettingsView.tsx`
- `frontend/src/features/commandCenter/CommandCenterPage.tsx`
- `frontend/src/features/personaStudio/PersonaStudioPage.tsx`
- `src-tauri/src/commands.rs`
