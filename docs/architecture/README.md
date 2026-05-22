Purpose: Provide a KB-first entry point into Codexify's current architecture so humans and AI can orient quickly, find the right source files, and plan changes with an accurate map.
Last updated: 2026-05-22
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

Start here with [`00-current-state.md`](./00-current-state.md) when you need current-state interpretation, release readiness, or short-horizon priorities rather than structural architecture.
It is the live operational truth layer for release readiness, supported install path, active blockers, and short-horizon priorities.

If you need the live operational truth layer, read `00-current-state.md` first and treat the rest of the KB as supporting context.

## What Codexify Is

Codexify is a local-first chat and knowledge workspace built around a FastAPI backend, a React frontend, Postgres-backed state, Redis-backed background work, optional Neo4j graph features, and a growing command bus/tooling layer. The core loop today is thread-based chat: the frontend writes messages, the backend enqueues completion work, workers assemble context from messages plus retrieval layers, and results stream back through task events and durable domain events.

## Start Here

Start here first when you need current-state interpretation rather than structural architecture: [`00-current-state.md`](./00-current-state.md). It is the live operational truth layer for release readiness, supported install path, active blockers, and short-horizon priorities.

If you are working on delegation, start with [`delegation-operator-manual.md`](./delegation-operator-manual.md) first. That manual is the operator-facing front door for the delegation slice; use this KB page immediately after to anchor the manual back to the current runtime truth.

If you are working on Guardian-mediated coding-agent execution or future Pi SDK integration, start with [`ADR-020: Guardian Mediated Coding Agent Execution Contract`](./adr/020-guardian-mediated-coding-agent-execution-contract.md). That ADR defines the contract-only execution seam and keeps Guardian as the request, policy, transcript, and lineage owner.

If you are working on Execution Ledger gate artifacts, acceptance-criteria mapping, implementation-plan artifacts, or completion/proof evidence mapping over Campaign Runner and Guardian rails, start with [`Execution Ledger Gate Artifacts Contract`](./execution-ledger-gate-artifacts-contract.md) after ADR-028.

If you are working on proposed Execution Ledger token vocabularies (gate decisions, plan states, acceptance results, proof decisions, escalation reasons) before runtime tokenization, start with [`Execution Ledger Token Domain Proposal`](./execution-ledger-token-domain-proposal.md) after the gate/artifact contract.

If you are working on Pi SDK integration, Pi-like external coding-agent harnesses, or invocation governance boundaries, start with [`Pi Invocation Boundary Contract`](./pi-invocation-boundary-contract.md) first, then apply [`ADR-020: Guardian Mediated Coding Agent Execution Contract`](./adr/020-guardian-mediated-coding-agent-execution-contract.md) for Guardian ownership and result-return doctrine.

If you are working on a cross-surface Guardian intent spine for chat, voice, automation, CLI, or future plugin entrypoints, start with [`ADR-022: Guardian Intent Spine and Cross-Surface Control Plane`](./adr/022-guardian-intent-spine-and-cross-surface-control-plane.md). That ADR defines the canonical envelope and dispatch rules for "do this on my behalf" requests.

If you are working on slash-command connector invocation, active connector semantics, Obsidian context commands, GitHub/Discord/Drive-style connector context, or MCP connector/tool invocation boundaries, start with [`ADR-024: Context Command and Active Connector Semantics`](./adr/024-context-command-active-connector-semantics.md). That ADR defines the turn-scoped connector doctrine without claiming any specific connector runtime is already implemented.

If you are working on Flow Builder, delegation/specification workflows, tacit-knowledge extraction, or workflow authoring semantics, start with [`ADR-006: Flow Builder Elicitation Lane`](./adr/006-flow-builder-elicitation-lane.md) first. That ADR defines the upstream `interview -> extract -> normalize -> validate -> compile -> execute` lane and the boundary between elicitation and runnable execution.

If you are working on Guardian-thread binding, FlowDraft identity, Builder view semantics, or run receipts, start with [`ADR-014: Flow Builder Thread, Draft, and Receipts Contract`](./adr/014-flow-builder-thread-draft-and-receipts-contract.md) after ADR-006. That ADR defines the canonical relationship between conversation state, authored flow state, alternate Builder views, and run evidence.

If you are working on continuity governance, working-set decay, or import-aware continuity framing, start with [`ADR-015: Continuity Engine Working Set and Decay Contract`](./adr/015-continuity-engine-working-set-and-decay-contract.md) after the identity and retrieval contracts. That ADR defines the user-governed continuity layer above the current thread-first chat runtime.

If you are working on the continuity control plane itself, including scope, intensity, decay, import treatment, exclusions, inspection, and reset semantics, continue with [`ADR-016: Continuity Governance Surface Contract`](./adr/016-continuity-governance-surface-contract.md) after ADR-015. That ADR defines the user-governed surface that configures continuity behavior without collapsing it into persona ownership or deep identity consent.

If you are working on Pi SDK integration, external coding-agent harnesses, or Pi-like execution, start with [`Pi Invocation Boundary Contract`](./pi-invocation-boundary-contract.md) and then apply Guardian-mediated coding-agent execution doctrine (ADR-020 when present in this repo lineage). Treat provider/model integration (including Minimax) as a separate provider-lane concern.
If you are working on graph-write replay safety or receipt semantics for the inspection-only graph lane, continue with [`ADR-017: Graph Write Idempotency and Receipt Semantics`](./adr/017-graph-write-idempotency-and-receipt-semantics.md) after ADR-011. That ADR defines deterministic graph-write identity and ephemeral receipt claims without introducing graph truth.

If you are working on the latest graph-write inspection snapshot surface or its debug route, continue with [`ADR-018: Graph Write Inspection Surface`](./adr/018-graph-write-inspection-surface.md) after ADR-017. That ADR defines the latest-per-thread operator snapshot without promoting graph truth.

If you are working on the backend graph adapter seam or the no-op default implementation, continue with [`ADR-019: Graph Backend Adapter Contract`](./adr/019-graph-backend-adapter-contract.md) after ADR-018. That ADR defines the typed persistence seam without changing the current inspection-only runtime.

If you are working on the graph-write runtime flag boundary, default-off enforcement on the supported Compose path, or the factory selection contract, continue with [`ADR-026: Graph Write Runtime Flag Boundary on Supported Compose Path`](./adr/026-graph-write-runtime-flag-boundary-on-supported-compose-path.md) after ADR-019. That ADR repairs the runtime/config boundary so the documented default-off contract is actually enforced.

## KB Validity and Diagram Source Sets

Before generating architecture diagrams, read the [`KB Validity Matrix`](./kb-validity-matrix.md).

- Use the validity matrix before using docs as diagram inputs.
- For first-pass runtime architecture diagrams, use only `Runtime Diagram Source Set v1`.
- Treat [`00-current-state.md`](./00-current-state.md) as the short-horizon override when older or broader docs conflict with present release reality.
- Do not use quarantined legacy docs as source inputs, especially Threadspace / `guardian-backend_v2` / obsolete installer-era material.

## Doc Map

- [`00-current-state.md`](./00-current-state.md): live operational truth, current release/readiness interpretation, and short-horizon priorities.
- [Codex Knowledge Compiler Contract](./codex-knowledge-compiler-contract.md): docs-only architecture contract for the reusable scoped knowledge-compilation pattern behind Codex Wiki / LLM Wiki / compiled project memory. It does not claim runtime implementation or release support and does not override `00-current-state.md`.
- [Codexify Development Map v1](./codexify-development-map-v1.md): visual current-state orientation map for subsystem boundaries, dependency edges, data spine, UI/runtime separation, and development maturity posture. It is not a release promise and does not override `00-current-state.md`.
- [Architecture Atlas](./architecture-atlas.md): peer-facing reading guide for the validated architecture corpus, runtime diagrams, and UI diagrams.
- [Agent Protocol Operations Index](./agent-protocol-operations.md): agent-facing map for task rituals, campaign/task interpretation, architecture-impact workflow, validation expectations, and contingency behavior.
- [Execution Ledger Gate Artifacts Contract](./execution-ledger-gate-artifacts-contract.md): docs-only follow-through contract for ADR-028 defining gate artifacts, acceptance-criteria mapping, implementation plans, and completion/proof evidence mapping onto Campaign Runner and Guardian execution surfaces.
- [Execution Ledger Token Domain Proposal](./execution-ledger-token-domain-proposal.md): docs-only proposal for candidate Execution Ledger token domains, semantics, and registry placement guidance before runtime tokenization.
- [Workspace Surface Spec v1](./codexify_workspace_surface_spec_v_1.md): UI/design-canon contract for Workspace as Shelf + Scratchpad + Inspector across Dashboard, Guardian, and Documents; not first-pass runtime topology truth.
- [Persona Studio Architecture](./persona-studio.md): shell-integrated persona/profile configuration surface, local draft state, diagnostics preview, and boundary rules; complements the broader product spec.
- [Guardian Intent Spine and Cross-Surface Control Plane](./adr/022-guardian-intent-spine-and-cross-surface-control-plane.md): canonical cross-surface intent envelope and dispatch contract for chat, voice, automations, CLI, and future plugin surfaces.
- [Context Command and Active Connector Semantics](./adr/024-context-command-active-connector-semantics.md): governing contract for slash-command connector invocation, active connector semantics, and turn-scoped connector/tool boundaries.
- [System Overview](./system-overview.md): current runtime components, topology, and critical paths.
- [Critical Flows](./flows.md): current trigger-to-output runtime flows with failure modes.
- [Flow Builder Elicitation Lane ADR](./adr/006-flow-builder-elicitation-lane.md): upstream spec-building lane for tacit-knowledge extraction, workflow authoring semantics, and validation-before-execution doctrine.
- [Flow Builder Thread, Draft, and Receipts Contract ADR](./adr/014-flow-builder-thread-draft-and-receipts-contract.md): canonical Guardian-thread, FlowDraft, Builder-view, and run-receipt contract for flow authoring semantics.
- [Flow Builder Typed Surface and Run Receipt Contract ADR](./adr/027-flow-builder-typed-surface-and-run-receipt-contract.md): typed vocabulary, validation issue taxonomy, semantic step contract, test/activation distinction, and complete RunReceipt field contract for future implementation planning.
- [Flow Builder Token Domain Inventory](./flow-builder-token-domains.md): candidate token domains for future Flow Builder implementation only; planning inventory, not runtime truth.
- [FlowDraft Schema Proposal](./flowdraft-schema-proposal.md): future durable draft shape for Flow Builder artifacts only; schema planning, not runtime truth.
- [VariableChip and TypedStepOutput Contract](./variable-chip-typed-output-contract.md): future variable wiring and typed output contract only; planning surface, not runtime truth.
- [Flow Builder ValidationIssue Taxonomy](./flow-builder-validation-issue-taxonomy.md): future validation taxonomy only; planning surface, not runtime truth.
- [Flow Builder SemanticStep Contract](./flow-builder-semantic-step-contract.md): future semantic AI-step contract only; planning surface, not runtime truth.
- [Flow Builder ConditionalContainer Contract](./flow-builder-conditional-container-contract.md): future conditional control-flow contract only; planning surface, not runtime truth.
- [Flow Builder RunReceipt Persistence Model](./flow-builder-runreceipt-persistence-model.md): future receipt persistence model only; planning surface, not runtime truth.
- [Flow Builder Surface Research Application](./flow-builder-surface-research-application.md): research-derived concept mapping from Workspace Studio to Codexify Flow Builder vocabulary and future task candidates (research input, not runtime truth).
- [Flow Builder Activity and Proof Surface Design](./flow-builder-activity-proof-surface.md): future activity/proof surface design only; planning surface, not runtime truth.
- [Flow Builder TestRun and Activation Contract](./flow-builder-testrun-activation-contract.md): future backend contract for execution attempts and durable enablement only; planning surface, not runtime truth.
- [Flow Builder Typed Surface Campaign](../Campaign/CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md): implementation sequencing guidance for ADR-027 follow-through; this is not runtime truth and does not widen the supported beta surface.
- [Memory Graph Derived Write Hook ADR](./adr/007-memory-graph-derived-write-hook.md): derived graph candidate emission after assistant persistence, kept non-blocking and idempotent.
- [Candidate Trace Surface](./candidate-trace-surface.md): backend-only pre-answer candidate diagnostic surface, TTL-bound and excluded from export.
- [Candidate Trace Ingestion Pipeline](./candidate-ingest-pipeline.md): backend-only ingest seam for normalized candidate-trace payloads; log-only scaffold for future graph/entity extraction.
- [Candidate Trace Ingest Worker ADR](./adr/009-candidate-trace-ingest-worker.md): asynchronous candidate-trace ingestion scaffold, log-only and non-blocking.
- [Graph Write Task Seam ADR](./adr/011-graph-write-task-seam-and-worker-scaffold.md): queue-backed graph-write task handoff and inspection-only worker scaffold for derived graph candidates.
- [Graph Write Inspection Surface ADR](./adr/018-graph-write-inspection-surface.md): latest-per-thread graph-write inspection snapshots for operator/debug visibility, ephemeral and non-canonical.
- [Graph Backend Adapter Contract ADR](./adr/019-graph-backend-adapter-contract.md): typed graph backend seam with a default no-op implementation, mounted after inspection.
- [Post-Completion Eval Spine ADR](./adr/012-post-completion-eval-spine.md): durable post-completion trace snapshot and attempt-scoped verdict layer; inspection-only and non-gating.
- [Verified Personal Facts Context Injection ADR](./adr/013-verified-personal-facts-context-injection.md): bounded backend injection of verified active personal facts into provider-ready chat context.
- [Data and Storage](./data-and-storage.md): storage systems, key tables, invariants, and data risk hotspots.
- [Config and Ops](./config-and-ops.md): env vars, config resolution, supported run paths, health checks, logging, and debugging cues.
- [Modules and Ownership](./modules-and-ownership.md): subsystem map, dependency edges, and blast radius guidance.
- [Bounded Tool-Augmented Completion Live Proof](./2026-04-20-bounded-tool-augmented-completion-live-proof.md): fresh supported-path live proof for the one-turn command-bus tool slice on the current `main` tip.
- [Tool Jobs Cleanup Live Proof](./2026-04-28-tool-jobs-cleanup-live-proof.md): supported Compose schema proof that the dedicated `tool_jobs` cleanup migration restores downgrade shape, removes the table again on upgrade, and leaves `command_runs` / `command_run_events` intact.
- [Supported Profile Live Proof](./2026-05-05-supported-profile-live-proof.md): fresh live proof for the supported local-first beta path after the posture, return-path, trace, and runtime-target fixes; not a release promise.
- [Runtime Diagrams v1](./runtime-diagrams-v1.md): first-pass current runtime diagram pack with source-scoped evidence notes and confidence labels.
- [Diagram Governance](./diagram-governance.md): policy for runtime-source-only diagram generation, module eligibility gates, required metadata, and freshness marker workflow.
- [Module Diagram Coverage Matrix](./module-diagram-coverage-matrix.md): high-coupling module coverage decisions, required diagram types, and review-marker tracking.
- [Roadmap Signals](./roadmap-signals.md): planning guidance derived from the current codebase; not a first-pass runtime diagram source.
- [Tech Debt and Risks](./tech-debt-and-risks.md): evidence-backed current risk register; use for risk overlays, not baseline topology.
- [Core Export Workflow](../release/core-export-workflow.md): local-only `Publishing_Portal/Core/` source-mirror workflow for public-facing packaging and review. This is generated output, not the source of truth, and does not replace supported-path live proof.
- [Unity Audit Doctrine](./unity-audit-doctrine.md): doctrine-first coherence and synthesis layer across runtime truth, contracts, operator reality, governance, extension boundaries, and community-facing narrative. It does not replace live proof, release truth, or ADR authority.
- [Chat Runtime Contract](./chat-runtime-contract.md): normative frontend/shared-runtime vocabulary for provider runtime, request lifecycle, replay, and transcript-integrity semantics.
- [Agent Tool Loop Contract](./agent-tool-loop-contract.md): implemented one-turn tool-augmented completion contract on the canonical command-bus lane.
- [Identity Precedence Contract](./identity-precedence-contract.md): canonical identity-layer precedence, actor-plus-role posture, and persisted/resolved/request-scoped semantics.
- [IDDB Policy v1](./iddb_policy_v1.md): identity-data governance covering diary/identity layer separation, Imprint_Zero/light identity, opt-in deep identity, persona borrowing semantics, and sensitive-trait non-inference rules; not a runtime topology source.
- [Organizational Cognition Specs](../specs/organizational-cognition/README.md): conceptual product/architecture doctrine mapping AI-enabled team roles onto Codexify's identity, retrieval, continuity, orchestration, and synchronization layers. It is not runtime truth and not a release promise.
- [Runtime Protocol Token Contract](./runtime-protocol-token-contract.md): canonical runtime tokens for statuses, events, machine-readable failure codes, and bounded tool-loop meanings.
- [Guardian Retrieval Navigation Model](./guardian-retrieval-navigation-model.md): planning-only doctrine for future retrieval navigation and route priors before expensive retrieval or full-vault ingestion; not current runtime behavior and not a release promise.
- [Web Agent Spec v1](./web-agent-spec.md): architecture/specification note for governed web retrieval, extraction, and browser/service connector boundaries; not current runtime proof.
- [Search-as-RAG Provider Adapter Contract](./web-search-provider-adapter-contract.md): architecture/specification contract for future Search-as-RAG provider adapters; not current runtime support.
- [Web Evidence Intake Gate Contract](./web-evidence-intake-gate-contract.md): future pre-synthesis safety and provenance gate for web-derived evidence; not current runtime support.
- [Self-Extending Agent Plugin System](./self-extending-agent-plugin-system.md): canonical architecture note for bounded generated extensions, plugin forge flow, and sovereignty boundaries.
- [Pi Invocation Boundary Contract](./pi-invocation-boundary-contract.md): canonical boundary for future Guardian-mediated invocation of Pi-like external coding-agent harnesses, including command authority, result return, lineage, and provider-lane separation.
- [ADR-020 Guardian Mediated Coding Agent Execution Contract](./adr/020-guardian-mediated-coding-agent-execution-contract.md): contract-only seam for Guardian-mediated coding-agent requests and results, including future Pi SDK adapters.
- [Pi Invocation Boundary Contract](./pi-invocation-boundary-contract.md): Codexify-native boundary contract for future Pi-like harness invocation, Guardian ownership, provider-lane separation, and bounded result return.
- [Identity and Runtime Mode](./identity-and-runtime-mode.md): canonical runtime-mode and account-boundary invariants for pre-auth guardrails and export-safe isolation.
- [Account Export + Restore Contract](./account-export-restore-contract.md): provenance, lineage, and restore semantics for durable artifacts and imported state.
- [Continuity Engine Working Set and Decay Contract](./adr/015-continuity-engine-working-set-and-decay-contract.md): user-governed continuity layer above thread-first chat, with working-set decay, provenance, and imported-history scaffolding.
- [Continuity Governance Surface Contract](./adr/016-continuity-governance-surface-contract.md): user-governed continuity control plane for scope, intensity, decay, import treatment, exclusions, inspectability, and reset semantics.
- [Graph Write Idempotency and Receipt Semantics](./adr/017-graph-write-idempotency-and-receipt-semantics.md): deterministic graph-write identity and ephemeral receipt claims for the inspection-only graph lane.
- [Neo4j Graph Backend Adapter Flagged Off By Default ADR](./adr/025-neo4j-graph-backend-adapter-flagged-off-by-default.md): first real graph persistence adapter behind explicit default-off runtime selection.
- [Graph Write Inspection Surface](./adr/018-graph-write-inspection-surface.md): latest-per-thread graph-write inspection snapshots for operator/debug visibility, ephemeral and non-canonical.
- [Graph Backend Adapter Contract](./adr/019-graph-backend-adapter-contract.md): typed graph backend seam with a default no-op implementation, mounted after inspection.
- [Graph Write Runtime Flag Boundary](./adr/026-graph-write-runtime-flag-boundary-on-supported-compose-path.md): default-off graph-write runtime boundary enforcement on the supported Docker Compose path.
- [Delegation Runtime Contract](./delegation-runtime.md): current delegation seam, runtime contract, and source-thread provenance rules.
- [Delegation Operator Manual](./delegation-operator-manual.md): operator procedure for supervised delegation, recovery, and summary persistence.
- [Chat Runtime Gap Analysis](./chat-runtime-gap-analysis.md): companion note explaining why the runtime contract exists and which ambiguity classes it is intended to shrink.
- [Completion Pipeline](./completion_pipeline.md): older completion deep dive; supplementary only and verify against current routes/workers.
- [Inference Providers](./providers.md): provider notes; supplementary only and verify against current catalog/router/health behavior.
- [Guardian Agent Delegation Recon](./guardian-agent-delegation-recon.md): focused planning/recon notes on delegation and agent runtime work; use only as supplementary planning context.
- [Solo Operator Runtime Bootcamp](./solo-operator-runtime-bootcamp.md): operational bootstrapping guide for solo runtime work.
- [Auth and Runtime Mode Audit 2026-04-20](./2026-04-20-auth-runtime-mode-audit.md): read-only audit of auth, runtime-mode, and Alembic state after DB reset; identifies multi-head migration fork and `X-User-Id` header conflation risk.

## Where Do I Change X?

- Chat thread/message API contract: `guardian/routes/chat.py`
- Completion assembly and provider execution: `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`
- Candidate trace surface and transient runtime diagnostics: `guardian/core/chat_completion_service.py`, `guardian/core/candidate_trace_store.py`, `guardian/routes/chat.py`, `guardian/services/account_export.py`
- Candidate trace ingestion scaffold: `guardian/core/chat_completion_service.py`, `guardian/queue/redis_queue.py`, `guardian/workers/candidate_ingest_worker.py`, `guardian/workers/graph_write_worker.py`, `docs/architecture/candidate-ingest-pipeline.md`
- Identity precedence, persona/imprint assembly, and status-surface wording: `docs/architecture/identity-precedence-contract.md`, `guardian/cognition/identity_contract.py`, `guardian/cognition/identity_resolution.py`, `guardian/cognition/system_prompt_builder.py`, `guardian/core/chat_completion_service.py`, `guardian/routes/imprint.py`, `guardian/routes/chat.py`, `frontend/src/features/settings/`
- RAG depth behavior and retrieval composition: `guardian/context/broker.py`, `guardian/memoryos/retriever.py`
- Continuity working-set builder, decay governance, and import-aware continuity framing: `docs/architecture/adr/015-continuity-engine-working-set-and-decay-contract.md`
- Flow Builder elicitation lane, delegation/specification workflows, tacit-knowledge extraction, and workflow authoring semantics: `docs/architecture/adr/006-flow-builder-elicitation-lane.md`
- Flow Builder / Guardian integration semantics, FlowDraft identity, Builder support lanes, and run receipts: `docs/architecture/adr/014-flow-builder-thread-draft-and-receipts-contract.md`
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

- Keep [`00-current-state.md`](./00-current-state.md) first in the doc map when refreshing this KB.
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
