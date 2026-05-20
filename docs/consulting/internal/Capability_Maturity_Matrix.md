# Capability Maturity Matrix

## Purpose

This document is an internal maturity and claim-control matrix for ResonantConstructs.ai consulting work. It is meant to help decide what Codexify capabilities are safe to sell, safe to show, suitable for pilots, useful only as architectural proof, or not ready to claim.

The goal is sales discipline, demo discipline, proposal discipline, and scope discipline. This matrix is not product marketing. It is an internal operating document for matching repository evidence to consulting offers without flattening supported, pilot, internal, and future-facing surfaces into a single story.

## Core Rule

Codexify is not the offer. Codexify is the evidence.

Consulting offers still need to be scoped around client pain, data boundaries, workflow shape, infrastructure posture, operating model, support expectations, and risk. A capability can be real in code and still be the wrong thing to package, promise, or show first.

## How to Read This Matrix

Each capability is scored across implementation status, support posture, evidence strength, demo safety, offer readiness, risk, and recommended claim level.

- A high implementation score does not automatically mean offer-ready.
- A pilot-track capability may still be useful in technical discovery or architecture workshops.
- Internal or quarantined surfaces may strengthen credibility in technical conversations while remaining out of scope for default client delivery.
- The supported local Docker Compose path, `docs/architecture/00-current-state.md`, and `config/supported_profiles/v1-local-core-web-mcp.yaml` are the primary claim gates when code breadth and supported breadth diverge.
- This matrix should be updated whenever support posture, live proof, validation coverage, or delivery readiness changes.

## Scoring Dimensions

| Dimension | Values | Meaning |
|---|---|---|
| Implementation Status | Implemented; Partially implemented; Prototype/demo; Experimental; Planned/placeholder; Unknown | What the repository actually shows today. |
| Support Posture | Supported now; Internal/quarantined; Pilot-track; Roadmap/future-facing; Unknown/unverified | Whether the capability is part of the present supported posture, intentionally constrained, usable only in bounded pilots, or still future-facing. |
| Evidence Strength | Strong; Moderate; Weak; Not evidenced; Unknown | How well the capability is anchored by current docs, code seams, tests, or live-proof statements. |
| Demo Safety | Safe to show; Safe with caveat; Mention only; Avoid showing; Unknown | Whether this should appear in a standard consulting demo and how much framing it requires. |
| Offer Readiness | Offer-ready; Pilot-ready; Evidence only; Not offer-ready; Unknown | Whether this can support a near-term consulting offer, only a pilot, only credibility evidence, or should stay out of offer language. |
| Risk Level | Low; Medium; High; Unknown | Overclaim, operational, delivery, and support risk if used in client-facing language. |
| Recommended Claim Level | Strong client-facing claim; Cautious client-facing claim; Internal proof only; Pilot-only claim; Do not claim; Unknown | The strongest safe external language level supported by current evidence. |

## Capability Maturity Summary

| Capability | Implementation Status | Support Posture | Evidence Strength | Demo Safety | Offer Readiness | Risk Level | Recommended Claim Level |
|---|---|---|---|---|---|---|---|
| Local-first runtime architecture | Implemented | Supported now | Strong | Safe to show | Offer-ready | Low | Strong client-facing claim |
| Core assistant/chat workflow | Implemented | Supported now | Strong | Safe to show | Offer-ready | Low | Strong client-facing claim |
| Queue-backed execution lifecycle | Implemented | Supported now | Strong | Safe with caveat | Offer-ready | Medium | Cautious client-facing claim |
| Private knowledge-base / RAG workflows | Implemented | Supported now | Strong | Safe with caveat | Offer-ready | Medium | Cautious client-facing claim |
| Document/media ingestion | Implemented | Supported now | Strong | Safe with caveat | Offer-ready | Medium | Cautious client-facing claim |
| Obsidian/local workspace ingestion | Implemented | Supported now | Strong | Safe with caveat | Pilot-ready | Medium | Cautious client-facing claim |
| Provider/model routing governance | Implemented | Supported now | Strong | Safe to show | Offer-ready | Medium | Strong client-facing claim |
| Settings/configuration UI | Implemented | Pilot-track | Moderate | Safe with caveat | Evidence only | Medium | Cautious client-facing claim |
| Persona-aware assistant configuration | Partially implemented | Pilot-track | Moderate | Safe with caveat | Pilot-ready | Medium | Pilot-only claim |
| Identity/auth/exposure boundaries | Implemented | Supported now | Strong | Safe to show | Offer-ready | Low | Strong client-facing claim |
| Capability policy and permission grants | Implemented | Supported now | Strong | Safe with caveat | Offer-ready | Medium | Cautious client-facing claim |
| Plugin architecture | Implemented | Pilot-track | Strong | Safe with caveat | Pilot-ready | Medium | Pilot-only claim |
| Command bus/tool execution | Implemented | Internal/quarantined | Strong | Mention only | Evidence only | High | Internal proof only |
| Command Center/operator diagnostics | Implemented | Pilot-track | Moderate | Safe with caveat | Pilot-ready | Medium | Pilot-only claim |
| Share links | Implemented | Internal/quarantined | Moderate | Mention only | Evidence only | High | Internal proof only |
| Project/thread/workspace UX | Implemented | Pilot-track | Moderate | Safe with caveat | Pilot-ready | Medium | Cautious client-facing claim |
| ChatGPT migration/import workflows | Implemented | Pilot-track | Moderate | Mention only | Pilot-ready | Medium | Pilot-only claim |
| Cron/automation | Implemented | Internal/quarantined | Moderate | Avoid showing | Evidence only | High | Internal proof only |
| Connectors | Partially implemented | Internal/quarantined | Weak | Mention only | Not offer-ready | High | Do not claim |
| WebSocket/realtime surfaces | Implemented | Internal/quarantined | Moderate | Mention only | Evidence only | High | Internal proof only |
| Voice | Partially implemented | Internal/quarantined | Moderate | Avoid showing | Not offer-ready | High | Do not claim |
| Federation | Experimental | Roadmap/future-facing | Weak | Avoid showing | Not offer-ready | High | Do not claim |
| Agent orchestration/delegation | Prototype/demo | Internal/quarantined | Moderate | Mention only | Not offer-ready | High | Internal proof only |
| Local desktop/Tauri runtime | Implemented | Pilot-track | Strong | Safe with caveat | Pilot-ready | Medium | Pilot-only claim |
| Secure document intelligence | Implemented | Supported now | Moderate | Safe with caveat | Offer-ready | Medium | Cautious client-facing claim |
| Compliance/privacy posture | Partially implemented | Unknown/unverified | Weak | Mention only | Not offer-ready | High | Do not claim |
| Observability/health surfaces | Implemented | Supported now | Strong | Safe to show | Offer-ready | Low | Strong client-facing claim |

## Detailed Capability Matrix

| Capability | What Exists | Evidence Anchors | Consulting Value | Safe Claim | Unsafe Claim | Demo Guidance | Offer Path | Hardening Needed |
|---|---|---|---|---|---|---|---|---|
| Local-first runtime architecture | Supported Compose stack, local-only provider contract, profile-based posture. | `docs/architecture/00-current-state.md`, `config/supported_profiles/v1-local-core-web-mcp.yaml`, `docker-compose.yml`, `docker-compose.runtime.yml` | Strong proof for private and local-first architecture planning. | Codexify demonstrates local-first AI runtime architecture with explicit support boundaries. | Codexify is already a packaged production platform for every client environment. | Show this first to anchor trust and scope. | Offer-ready for local-first architecture planning. | Publish client-ready reference variants and deployment decision criteria. |
| Core assistant/chat workflow | Threaded chat UI, chat routes, worker execution, persisted completion flow. | `frontend/src/features/chat/GuardianChat.tsx`, `guardian/routes/chat.py`, `guardian/workers/chat_worker.py`, `guardian/core/chat_completion_service.py` | Strong proof for internal assistant design. | Codexify demonstrates a real assistant workflow beyond a synchronous demo chat loop. | The chat surface is universally production-ready without client-specific reliability design. | Safe core demo moment. | Offer-ready for internal assistant architecture. | Package clearer SLA language for queue, timeout, and failure semantics. |
| Queue-backed execution lifecycle | Route -> queue -> worker -> persistence -> task events pattern is explicit. | `guardian/queue/redis_queue.py`, `guardian/queue/turn_lock.py`, `guardian/queue/task_events.py`, `docs/architecture/flows.md` | Strong proof for failure-aware workflow design. | Codexify demonstrates queue-backed assistant execution patterns that can inform client-specific internal assistant architecture. | Request acceptance guarantees successful completion. | Show with the caveat that acceptance and completion are different states. | Offer-ready inside reliability-oriented assistant builds. | Add client-facing observability and retry/runbook materials. |
| Private knowledge-base / RAG workflows | Upload, embed, retrieve, context assembly, source-mode controls. | `guardian/routes/media.py`, `guardian/vector/store.py`, `guardian/core/chat_completion_service.py`, `docs/architecture/flows.md` | Directly relevant to knowledge retrieval engagements. | Codexify demonstrates private knowledge ingestion and retrieval patterns, but retrieval quality must be evaluated against each client corpus. | Retrieval guarantees perfect answers. | Safe after the core chat path. | Offer-ready for scoped RAG implementations. | Create a retrieval quality evaluation pack and corpus readiness checklist. |
| Document/media ingestion | Media route, parsers, embed worker, persistence lifecycle. | `guardian/routes/media.py`, `guardian/workers/document_embed_worker.py`, `docs/architecture/system-overview.md` | Strong proof for document-intelligence pipeline design. | Codexify demonstrates an operational ingestion pipeline for private AI knowledge workflows. | Every file type is equally mature and production-ready. | Show with clear content-type and quality caveats. | Offer-ready as part of document-intelligence delivery. | Add supported-format matrices, failure reporting, and validation assets. |
| Obsidian/local workspace ingestion | Local note indexing and workspace-scoped retrieval on supported path. | `guardian/routes/obsidian.py`, `guardian/obsidian/indexer.py`, `docs/architecture/00-current-state.md`, `docs/architecture/config-and-ops.md` | Good proof for local workspace intelligence and note-based workflows. | Codexify demonstrates workspace-local knowledge ingestion and retrieval on the supported path. | Codexify already supports broad connector sync or enterprise content federation. | Safe with a strict local-workspace framing. | Pilot-ready for bounded local knowledge pilots. | Publish boundary notes on scope, sync limits, and evaluation criteria. |
| Provider/model routing governance | Registry, router, catalog, supported local-only posture, health alignment. | `guardian/core/provider_registry.py`, `guardian/core/ai_router.py`, `docs/architecture/config-and-ops.md`, `config/supported_profiles/v1-local-core-web-mcp.yaml` | Strong proof for vendor-neutral governance design. | Codexify demonstrates provider governance architecture, but provider approval, egress policy, cost controls, and fallback logic must be scoped per client. | Any configured provider is part of the current supported offer. | Safe to show if the local-only posture is stated clearly. | Offer-ready for provider governance and routing consulting. | Create a provider governance runbook and decision matrix. |
| Settings/configuration UI | Settings surfaces exist across data, persona, desktop, and connectors. | `frontend/src/features/settings/SettingsView.tsx`, `docs/consulting/Codexify_Codebase_Capability_Audit.md` | Proof of configuration thinking, not a clean offer by itself. | Codexify shows structured AI system configuration surfaces and operator controls. | Every visible setting maps to a supported client-ready feature. | Show only in support of a stronger core workflow. | Evidence only unless paired with a larger offer. | Separate supported controls from posture-sensitive or internal controls. |
| Persona-aware assistant configuration | Persona profiles, Persona Studio, backing profile storage. | `frontend/src/features/personaStudio/PersonaStudioPage.tsx`, `guardian/routes/persona_profiles.py`, `docs/consulting/Codexify_Codebase_Capability_Audit.md` | Useful for role-tuned assistant discovery. | Codexify demonstrates persona-aware assistant configuration patterns for bounded use cases. | Persona orchestration is a mature productized capability across all client contexts. | Show only with explicit simulation-versus-runtime caveats. | Pilot-ready for narrow persona configuration pilots. | Clarify runtime behavior, persistence rules, and governance boundaries. |
| Identity/auth/exposure boundaries | Auth routes, dependency-enforced identity, public exposure controls. | `guardian/core/dependencies.py`, `guardian/core/public_exposure.py`, `guardian/routes/auth.py` | Strong proof for least-privilege and exposure-boundary consulting. | Codexify demonstrates explicit identity and exposure boundaries in code and runtime posture. | Local-first automatically means compliant or secure. | Safe to show early with scoped language. | Offer-ready for trust-boundary and permission design. | Add formal threat models and control-mapping artifacts. |
| Capability policy and permission grants | Capability policy and grants are implemented in backend seams. | `guardian/core/capability_policy.py`, `guardian/core/capability_grants.py`, `docs/consulting/Codexify_Codebase_Capability_Audit.md` | Strong proof for governed AI capability design. | Codexify demonstrates code-enforced capability policy and permission-grant patterns. | Governance lives only in prompts or UI language. | Mention in governance sections; do not oversell as a product surface. | Offer-ready inside governance and boundary-design work. | Create policy examples, audit questions, and delivery templates. |
| Plugin architecture | Manifest schema, loader, public MCP posture, evolving plugin SDK story. | `guardian/plugins/plugin_manifest.py`, `guardian/plugins/plugin_loader.py`, `config/supported_profiles/v1-local-core-web-mcp.yaml` | Strong proof for extensibility strategy consulting. | Codexify demonstrates extensible architecture patterns for controlled capability expansion. | The plugin system is a stable general-purpose marketplace product today. | Show only to technical buyers with lifecycle caveats. | Pilot-ready for extensibility architecture engagements. | Publish versioning, compatibility, and trust-model guidance. |
| Command bus/tool execution | Internal-only route posture with strong underlying command surfaces. | `guardian/routes/command_bus.py`, `docs/architecture/config-and-ops.md`, `config/supported_profiles/v1-local-core-web-mcp.yaml` | Strong proof of backend control-plane design. | Codexify demonstrates internal command and tool execution architecture. | Command bus routes are supported public client surfaces. | Mention only in architecture discussions. | Evidence only for credibility and design depth. | Keep internal posture explicit and define a smaller safe subset before widening. |
| Command Center/operator diagnostics | Health surfaces plus posture-sensitive operator UI and worker-control visibility. | `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `guardian/routes/health.py`, `docs/architecture/config-and-ops.md`, `docs/architecture/00-current-state.md` | Useful for operations UX and support workflow consulting. | Codexify demonstrates operator-oriented diagnostic thinking and health visibility patterns. | The Command Center is a released GA operations product surface. | Safe with caveat for technical and ops buyers. | Pilot-ready when scoped as operator workflow design. | Align UI posture, backend truth, and demo-safe subsets. |
| Share links | Share route exists but is quarantined in the supported profile. | `guardian/routes/share.py`, `config/supported_profiles/v1-local-core-web-mcp.yaml`, `docs/consulting/Codexify_Codebase_Capability_Audit.md` | Helpful as design evidence for selective exposure patterns. | Codexify includes share-link architecture that may inform scoped collaboration designs. | Secure sharing is part of the supported release promise today. | Mention only if asked. | Evidence only, not a default offer surface. | Fresh support proof, threat modeling, and support posture alignment. |
| Project/thread/workspace UX | Projects and threads are active; workspace surfaces exist alongside retrieval flows. | `guardian/routes/projects.py`, `guardian/routes/workspace.py`, `frontend/src/features/chat/GuardianChat.tsx`, `docs/consulting/Codexify_Codebase_Capability_Audit.md` | Good proof for workflow-aware AI product design. | Codexify demonstrates multi-surface AI workspace design patterns. | All workspace-adjacent UX is fully standardized and supported. | Show only enough to support the consulting narrative. | Pilot-ready inside AI workflow application design. | Tighten which workspace flows are supported versus exploratory. |
| ChatGPT migration/import workflows | Import scripts and migration surfaces exist. | `docker-compose.yml`, `docs/consulting/Codexify_Codebase_Capability_Audit.md` | Useful for migration discovery conversations. | Codexify shows migration-oriented seams that can inform scoped import projects. | Migration is turnkey and low-risk for every client corpus. | Mention only unless the buyer has a migration pain. | Pilot-ready for migration discovery and scoped imports. | Create deterministic reporting and client-facing migration checklists. |
| Cron/automation | Cron routes and workers exist but are quarantined from the supported profile. | `guardian/routes/cron.py`, `config/supported_profiles/v1-local-core-web-mcp.yaml`, `docs/architecture/config-and-ops.md` | Good proof of automation architecture depth. | Codexify includes automation architecture that may support future bounded workflow pilots. | Automation is a supported client-ready default feature. | Avoid showing in standard demos. | Evidence only. | Define a safe automation subset, failure boundaries, and operator controls. |
| Connectors | Connector routes exist but remain quarantined and under-evidenced in this posture. | `guardian/routes/connectors.py`, `config/supported_profiles/v1-local-core-web-mcp.yaml` | Limited present consulting value outside architecture direction. | Codexify contains connector-adjacent seams, but current support posture does not treat them as active client surfaces. | Codexify offers a mature connector ecosystem today. | Mention only if directly asked, and carefully. | Not offer-ready. | Support matrix, provider-by-provider proof, and boundary docs. |
| WebSocket/realtime surfaces | Auth, rate-limited realtime route exists but is quarantined. | `guardian/routes/websocket.py`, `docs/architecture/config-and-ops.md`, `config/supported_profiles/v1-local-core-web-mcp.yaml` | Useful as proof of realtime design capability. | Codexify demonstrates realtime surface architecture with explicit guardrails. | Realtime collaboration is part of the supported consulting offer by default. | Mention only in technical due diligence. | Evidence only. | Determine supported transport scope and operational guarantees. |
| Voice | Voice route and worker surfaces exist, but support posture remains cautious. | `guardian/routes/voice.py`, `config/supported_profiles/v1-local-core-web-mcp.yaml`, `docs/consulting/Codexify_Codebase_Capability_Audit.md` | Limited current value unless a client explicitly needs voice exploration. | Codexify has voice-related implementation work, but it is not a safe default consulting claim. | Production voice workflows are ready for immediate packaging. | Avoid showing in standard demos. | Not offer-ready. | Clear support posture, proof, and UX reliability criteria. |
| Federation | Federation routes and tests exist, but current release truth excludes them. | `guardian/routes/federation.py`, `docs/architecture/00-current-state.md`, `config/supported_profiles/v1-local-core-web-mcp.yaml` | Useful only as future-state architecture depth. | Codexify contains federation-oriented architectural work. | Federation is currently supported and ready to deploy broadly. | Avoid showing except in roadmap discussions. | Not offer-ready. | Protocol, trust, ops, and client-delivery hardening. |
| Agent orchestration/delegation | Delegation and orchestration routes exist as supervised prototype surfaces. | `guardian/routes/delegations.py`, `guardian/routes/agent_orchestration.py`, `docs/architecture/00-current-state.md` | Strong credibility for supervised orchestration architecture thinking. | Codexify includes supervised orchestration prototypes that can inform future pilot design. | Agent orchestration is fully autonomous and ready for unsupervised business operations. | Mention only, never as a lead demo. | Not offer-ready. | Stronger supervision, safety bounds, proof, and narrow pilot definition. |
| Local desktop/Tauri runtime | Tauri commands, runtime config bridge, packaged runtime contracts exist. | `src-tauri/src/commands.rs`, `docker-compose.runtime.yml`, `docs/architecture/config-and-ops.md`, `docs/architecture/00-current-state.md` | Useful for desktop-first local AI planning. | Codexify demonstrates packaged desktop runtime patterns, but the supported path remains local Compose. | The desktop shell replaces the supported runtime posture today. | Show only after stating that desktop is not the main support claim. | Pilot-ready for scoped desktop or launcher planning. | Fresh desktop proof, support contract, and deployment packaging notes. |
| Secure document intelligence | Document routes, signed media handling, scoped retrieval lifecycle. | `guardian/routes/media.py`, `guardian/vector/store.py`, `docs/consulting/case-study/Codexify_As_Reference_Implementation.md` | Good basis for document-intelligence consulting with strong caveats. | Codexify demonstrates secure document-intelligence patterns for scoped internal workflows. | Local document handling alone proves compliance readiness. | Safe with caveat when tied to client-specific controls. | Offer-ready for scoped document intelligence. | Data retention, redaction, and control-mapping artifacts. |
| Compliance/privacy posture | Local-first posture and trust boundaries exist, but no broad compliance pack is proven. | `docs/architecture/00-current-state.md`, `guardian/core/public_exposure.py`, `docs/consulting/case-study/Codexify_As_Reference_Implementation.md` | Useful for scoping risk conversations, not for packaged compliance claims. | Codexify shows privacy-aware architecture choices that can support later compliance work. | Codexify is compliant by default or ready for regulated deployment without review. | Mention only and keep scope narrow. | Not offer-ready. | Formal control mapping, retention policy, audit evidence, and legal review inputs. |
| Observability/health surfaces | Health endpoints, operator truth docs, runtime alignment guidance. | `guardian/routes/health.py`, `docs/architecture/config-and-ops.md`, `docs/architecture/00-current-state.md` | Strong proof for operational discipline and diagnostics. | Codexify demonstrates observable health and posture surfaces that support failure-aware operation. | A green health endpoint proves every adjacent subsystem is production-safe. | Safe to show as part of trust-boundary framing. | Offer-ready within operations and hardening engagements. | Expand client-facing runbooks and incident interpretation guides. |

## Offer-Ready Capabilities

- AI readiness and workflow audit: offer-ready because the repo shows real route, worker, retrieval, policy, and health boundaries that map cleanly to discovery and due diligence.
- Local-first runtime architecture: offer-ready because supported posture, current-state truth, and Compose topology provide strong evidence for private deployment planning.
- Private knowledge-base / RAG implementation: offer-ready because ingestion, retrieval, and local knowledge flows are concrete; still scope corpus quality, evaluation criteria, and support boundaries per client.
- Provider governance and model routing: offer-ready because the registry, router, posture docs, and health interpretation rules are strong; still scope egress, approvals, cost controls, and fallback policy.
- Internal AI assistant architecture: offer-ready because queue-backed execution and failure-aware lifecycle design are well evidenced; still scope reliability targets, escalation rules, and human oversight.
- Secure document intelligence: offer-ready for scoped internal use cases because the ingestion and retrieval rails are real; still scope sensitive-data handling, retention, and control mapping.
- AI governance and permission-boundary design: offer-ready because capability policy, grants, auth, and exposure controls show explicit boundaries in code.
- AI workflow application design: offer-ready because Codexify demonstrates multi-surface workflow UX, not just prompt wrappers; still scope role design and adoption plan per client.

## Pilot-Track Capabilities

- Persona-aware assistant configuration: useful for bounded pilots where role-shaping is important, but runtime behavior and governance boundaries need tighter operational definition.
- Command Center/operator diagnostics: useful in technical discovery and support-workflow pilots, but should not be sold as a released general operations console.
- Plugin/extensible system architecture: useful where clients need extension patterns, but versioning, compatibility, and trust-model commitments still need narrowing.
- ChatGPT migration/import workflows: useful for clients migrating knowledge or threads, but require deterministic reporting, corpus triage, and scoped import success criteria.
- Obsidian/local workspace ingestion: useful for local knowledge pilots, but should stay framed as local-workspace retrieval rather than broad connector readiness.
- Local desktop/Tauri runtime: useful for desktop-first local AI explorations, but the supported-now claim still belongs to the Compose path.
- Project/thread/workspace UX: useful when scoping workflow applications, but should stay anchored to the demonstrated subset rather than treated as a polished product shell.

## Internal / Quarantined Capabilities

- Command bus/tool execution: strong internal architecture evidence; safe to cite in technical diligence, not safe to package as a default surface.
- Cron/automation: real code, current quarantine; useful for architecture depth, not for standard offer language.
- WebSocket/realtime surfaces: valuable as implementation evidence, but not part of the present supported promise.
- Connectors: route presence exists, but maturity and support posture are too weak for active claims.
- Agent orchestration/delegation: useful only as supervised prototype evidence, never as autonomous default delivery language.
- Share links: implemented but quarantined, so treat as internal capability evidence rather than active client scope.

Safe conversational use for this category: these surfaces show that ResonantConstructs.ai can reason about and implement adjacent architecture when a client need justifies it, but they should not be sold as default deliverables or current supported release features.

## Roadmap / Future-Facing Capabilities

- Federation: best framed as architectural direction and distributed-systems depth, not a current consulting deliverable.
- Generalized autonomous orchestration: current proof is not strong enough for buyer-facing readiness language.
- Broad connector ecosystem: current posture does not support breadth claims.
- Production voice workflows: implementation exists, but support proof and delivery posture are not strong enough.
- Multi-node production deployments: local-first and packaged-runtime evidence exist, but broad production multi-node support is not presently proven here.
- Compliance-ready packaged controls: privacy-aware design exists, but formal compliance controls and evidence packs are still missing.

## Capabilities to Avoid Leading With

- Persona mythology: it distracts from operational value and overstates a partially implemented area.
- Autonomous agents: this raises expectations faster than the repo can safely support.
- Federation: architecturally interesting, but too future-facing for early buyer trust.
- Voice: broad surface, weak current support posture, high overclaim risk.
- Command bus internals: strong engineering evidence, poor early-stage buyer framing.
- Cron automation: currently quarantined and easy to misread as productized autonomy.
- Connector breadth: route presence does not equal a supported connector program.
- Roadmap-heavy claims: they invite evaluation on future posture rather than present truth.
- Compliance claims: current evidence supports scoped privacy conversations, not packaged compliance assurances.

## Capability-to-Offer Map

| Consulting Offer | Supporting Capabilities | Current Readiness | Caveats | Next Asset to Create |
|---|---|---|---|---|
| AI readiness and workflow audit | Local-first runtime architecture, queue-backed execution, observability, governance boundaries | Offer-ready | Must stay evidence-led and scoped to client workflows, not product sales. | `docs/consulting/internal/Technical_Due_Diligence_QA_Playbook.md` |
| Private knowledge-base / RAG implementation | Document/media ingestion, private RAG, Obsidian/local workspace ingestion, secure document intelligence | Offer-ready | Corpus quality, retrieval evaluation, and data boundaries must be scoped per client. | `docs/consulting/offers/Private_Knowledge_RAG_Implementation_Offer.md` |
| Internal AI assistant design | Core assistant workflow, queue-backed execution, persona-aware configuration, project/thread/workspace UX | Offer-ready | Reliability, escalation, and human review rules still need client-specific design. | `docs/consulting/sow/Internal_AI_Assistant_SOW_Language.md` |
| Local-first AI infrastructure planning | Local-first runtime architecture, identity boundaries, desktop runtime posture, observability | Offer-ready | Supported path is Compose-first; desktop and multi-node variants remain scoped options. | `docs/consulting/offers/Local_First_AI_Runtime_Architecture_Offer.md` |
| Provider governance and model routing | Provider/model routing governance, capability policy, observability | Offer-ready | Cloud posture, fallback policy, and cost governance must be tailored. | `docs/consulting/offers/Provider_Governance_and_Model_Routing_Offer.md` |
| Secure document intelligence | Document/media ingestion, private RAG, secure document intelligence, identity boundaries | Offer-ready | Do not imply compliance readiness without explicit controls work. | `docs/consulting/compliance/Risk_and_Data_Boundary_Notes.md` |
| AI workflow application design | Core assistant workflow, project/thread/workspace UX, settings UI, operator diagnostics | Offer-ready | UX breadth should be scoped around the client workflow, not the full repo surface. | `docs/consulting/architecture/Client_Facing_System_Architecture_OnePager.md` |
| Plugin/extensible system architecture | Plugin architecture, command bus, capability policy | Pilot-ready | Keep plugin SDK and command bus posture separate from supported-now claims. | `docs/consulting/offers/Plugin_Extensible_System_Architecture_Offer.md` |
| AI governance and permission-boundary design | Identity/auth/exposure boundaries, capability policy and permission grants, provider governance | Offer-ready | Needs stronger control-mapping artifacts for regulated buyers. | `docs/consulting/compliance/Risk_and_Data_Boundary_Notes.md` |
| Technical due diligence and AI systems audit | Observability, support posture docs, runtime architecture, governance seams | Offer-ready | Must stay anchored to what is evidenced now, not future intent. | `docs/consulting/internal/Technical_Due_Diligence_QA_Playbook.md` |
| Managed optimization / support retainer | Observability, operator diagnostics, provider governance, ingestion quality evaluation | Pilot-ready | Requires clearer runbooks, support boundaries, and metrics packs. | `docs/consulting/offers/Managed_Optimization_and_Support_Retainer.md` |

## Capability-to-Demo Map

| Demo Moment | Capabilities Shown | Demo Safety | Must-Say Caveat |
|---|---|---|---|
| Trust boundary and runtime posture | Local-first runtime architecture, observability/health surfaces, identity posture | Safe to show | Supported local Compose posture is the real claim gate; implemented breadth is larger than supported breadth. |
| Core assistant workflow | Core assistant/chat workflow, queue-backed execution lifecycle | Safe to show | Acceptance is not completion; queue and worker boundaries remain operationally meaningful. |
| Document/media ingestion | Document/media ingestion, secure document intelligence | Safe with caveat | Ingestion readiness does not prove retrieval quality or compliance coverage. |
| Retrieval/local knowledge workflows | Private knowledge-base / RAG workflows, Obsidian/local workspace ingestion | Safe with caveat | Retrieval quality and local-workspace scope still need corpus-specific evaluation. |
| Provider/model governance | Provider/model routing governance, capability policy and permission grants | Safe to show | Current supported posture is local-only; broader provider surfaces are not automatically in scope. |
| Persona/configuration layer | Settings/configuration UI, persona-aware assistant configuration | Safe with caveat | Persona and settings surfaces include pilot-track or posture-sensitive elements. |
| Extensibility/plugin/command surfaces | Plugin architecture, command bus/tool execution | Mention only | Extensibility proof is real, but command bus is internal-only and plugin commitments are still narrow. |
| Operator/diagnostic thinking | Command Center/operator diagnostics, observability/health surfaces | Safe with caveat | Operator UI is supplemental evidence, not the released beta source of truth. |

## Buyer-Visible Claim Levels

| Claim Level | Meaning | Example Language |
|---|---|---|
| Strong client-facing claim | Safe to use in proposals, demos, and discovery if still scoped to client context. | ResonantConstructs.ai can design and deliver local-first AI systems with explicit runtime, governance, and observability boundaries. |
| Cautious client-facing claim | Safe only with clear caveats about corpus quality, support posture, or deployment scope. | Codexify demonstrates private knowledge retrieval patterns, but evaluation and support must be scoped to each client corpus and workflow. |
| Pilot-only claim | Safe only in bounded pilot discussions with guardrails and explicit success criteria. | Persona-aware assistant configuration can be explored in a narrow pilot where governance and behavior boundaries are defined upfront. |
| Internal proof only | Useful in technical diligence as proof of engineering depth, but not as active offer language. | Codexify includes internal command and automation architecture that informs future capability design. |
| Do not claim | Not safe for buyer-facing use under current evidence and posture. | Codexify is compliance-ready, fully autonomous, and broadly federated for unsupervised production use. |

## Risk Notes

- Supported surface and implemented surface do not match. The supported profile must win over route breadth when client claims are written.
- Internal or quarantined routes create overclaim risk if route presence is mistaken for supported release posture.
- Local-first and privacy-aware design do not equal compliance readiness. Control mapping, retention, audit, and legal review remain separate work.
- Retrieval quality should never be assumed from ingestion success or index presence alone.
- Local-first infrastructure still carries maintenance burden around hardware, upgrades, backups, and operator support.
- Provider governance remains a live risk area because configured, discovered, supported, and executable providers are distinct states.
- Automation and autonomy claims carry the highest trust risk because implementation depth outpaces supported delivery posture.
- Observability exists, but proof freshness and operator runbooks still matter before support commitments are made.
- Client-specific deployment shape can widen risk quickly; every offer still needs scope controls and a statement of what is not included.

## Recommended Next Hardening Steps

- Maintain a supported-now versus implemented matrix alongside the supported profile.
- Add explicit demo-safe labels for experimental, internal, and pilot-track surfaces.
- Create a retrieval quality evaluation pack for document and workspace corpora.
- Create client-facing reference architecture variants for local-only, hybrid, and desktop-first deployments.
- Create a provider governance runbook that covers approvals, egress, fallback, and cost controls.
- Create risk and data-boundary notes for privacy, retention, and sensitive-document handling.
- Create a technical due diligence Q&A playbook grounded in current supported posture.
- Create SOW language for RAG, document intelligence, internal assistants, and governance engagements.
- Add evidence checklists that must be refreshed before each major consulting offer or demo.

## Recommended Next Consulting Documents

| Document | Purpose | Primary Source Documents |
|---|---|---|
| `docs/consulting/internal/Technical_Due_Diligence_QA_Playbook.md` | Standard answers for technical buyers, diligence calls, and proposal review. | `docs/consulting/Codexify_Codebase_Capability_Audit.md`, `docs/architecture/00-current-state.md`, `docs/architecture/config-and-ops.md` |
| `docs/consulting/offers/Private_Knowledge_RAG_Implementation_Offer.md` | Offer framing, scope, exclusions, and delivery model for private RAG work. | `docs/consulting/Codexify_Codebase_Capability_Audit.md`, `docs/consulting/case-study/Codexify_As_Reference_Implementation.md`, `docs/architecture/flows.md` |
| `docs/consulting/offers/Local_First_AI_Runtime_Architecture_Offer.md` | Offer framing for local-first and hybrid AI infrastructure planning. | `docs/architecture/00-current-state.md`, `docs/architecture/system-overview.md`, `docker-compose.yml`, `docker-compose.runtime.yml` |
| `docs/consulting/offers/Provider_Governance_and_Model_Routing_Offer.md` | Offer framing for provider governance, routing, and vendor-risk mitigation. | `docs/architecture/config-and-ops.md`, `config/supported_profiles/v1-local-core-web-mcp.yaml`, `guardian/core/provider_registry.py` |
| `docs/consulting/compliance/Risk_and_Data_Boundary_Notes.md` | Internal notes for privacy, exposure boundaries, retention, and compliance caveats. | `guardian/core/public_exposure.py`, `guardian/core/dependencies.py`, `docs/architecture/00-current-state.md` |
| `docs/consulting/architecture/Client_Facing_System_Architecture_OnePager.md` | A clean buyer-facing architecture overview without internal implementation sprawl. | `docs/consulting/case-study/Codexify_As_Reference_Implementation.md`, `docs/architecture/system-overview.md`, `docs/architecture/flows.md` |
| `docs/consulting/sow/RAG_and_Document_Intelligence_SOW_Language.md` | Reusable SOW language for document intelligence and private retrieval projects. | `docs/consulting/Codexify_Codebase_Capability_Audit.md`, `docs/architecture/flows.md`, `guardian/routes/media.py` |
| `docs/consulting/sow/Internal_AI_Assistant_SOW_Language.md` | Reusable SOW language for assistant architecture and workflow application delivery. | `guardian/routes/chat.py`, `guardian/workers/chat_worker.py`, `docs/architecture/flows.md` |

## Validation Notes

- Discovery commands run:
  - `pwd`
  - `git rev-parse --show-toplevel`
  - `git branch --show-current`
  - `git status --short`
  - `find docs/consulting -maxdepth 5 -type f | sort`
  - `git ls-files docs/consulting`
  - requested `test -f` checks for primary consulting sources
- Source documents found in this worktree:
  - `docs/consulting/Codexify_Codebase_Capability_Audit.md`
  - `docs/consulting/case-study/Codexify_As_Reference_Implementation.md`
  - `docs/consulting/demo/Codexify_Golden_Path_Demo_Script.md`
- Source documents missing in this worktree:
  - `docs/consulting/README.md`
  - `docs/consulting/demo/Codexify_Do_Not_Overclaim_List.md`
- Historical continuity notes:
  - `docs/consulting/README.md` appears in git history at commit `703a41f67727ee617f3b2f7709f8e9acd4428f13`.
  - `docs/consulting/demo/Codexify_Do_Not_Overclaim_List.md` appears in git history at commit `12aef340bf6a240f78d58acdd018713695d6e74d`.
  - These files were not used as active primary sources because they are absent from the current checkout.
- Important evidence paths were verified in the current worktree before inclusion in the appendix.
- `git status --short` required full repo access because Git LFS temp-path access under the shared repo storage was blocked in the sandboxed run.
- Final file existence check: `FOUND matrix`.
- Whitespace and diff validation: `git diff --check -- docs/consulting/internal/Capability_Maturity_Matrix.md` passed with no output.
- Docs validation: `python3 scripts/validate_docs.py` passed with `Docs validation passed: required architecture docs, README links, and source headings verified.`

## Appendix: Evidence Anchors

Primary consulting sources present in this worktree:

- `docs/consulting/Codexify_Codebase_Capability_Audit.md`
- `docs/consulting/case-study/Codexify_As_Reference_Implementation.md`
- `docs/consulting/demo/Codexify_Golden_Path_Demo_Script.md`

Architecture and runtime posture anchors:

- `docs/architecture/00-current-state.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/config-and-ops.md`
- `config/supported_profiles/v1-local-core-web-mcp.yaml`
- `docker-compose.yml`
- `docker-compose.runtime.yml`
- `README.md`

Execution and retrieval anchors:

- `guardian/routes/chat.py`
- `guardian/workers/chat_worker.py`
- `guardian/core/chat_completion_service.py`
- `guardian/queue/redis_queue.py`
- `guardian/queue/turn_lock.py`
- `guardian/queue/task_events.py`
- `guardian/routes/media.py`
- `guardian/workers/document_embed_worker.py`
- `guardian/vector/store.py`
- `guardian/routes/obsidian.py`
- `guardian/obsidian/indexer.py`

Governance and boundary anchors:

- `guardian/core/provider_registry.py`
- `guardian/core/ai_router.py`
- `guardian/core/capability_policy.py`
- `guardian/core/capability_grants.py`
- `guardian/core/dependencies.py`
- `guardian/core/public_exposure.py`

Extensibility and additional surface anchors:

- `guardian/plugins/plugin_manifest.py`
- `guardian/plugins/plugin_loader.py`
- `guardian/routes/command_bus.py`
- `guardian/routes/share.py`
- `guardian/routes/projects.py`
- `guardian/routes/workspace.py`
- `guardian/routes/cron.py`
- `guardian/routes/connectors.py`
- `guardian/routes/websocket.py`
- `guardian/routes/voice.py`
- `guardian/routes/federation.py`
- `guardian/routes/delegations.py`
- `guardian/routes/agent_orchestration.py`

Frontend and desktop anchors:

- `frontend/src/features/chat/GuardianChat.tsx`
- `frontend/src/features/settings/SettingsView.tsx`
- `frontend/src/features/commandCenter/CommandCenterPage.tsx`
- `frontend/src/features/personaStudio/PersonaStudioPage.tsx`
- `src-tauri/src/commands.rs`
