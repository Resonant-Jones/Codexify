# Codexify Do Not Overclaim List

## Purpose

This document is an internal guardrail sheet for ResonantConstructs.ai client-facing conversations, demos, and proposal language reviews.

Its purpose is to preserve trust, scope discipline, and technical accuracy when using Codexify as proof-of-work.

## Core Rule

Codexify is not the offer. Codexify is the evidence.

The offer is scoped consulting: designing and implementing client-specific systems around real data boundaries, workflows, operating constraints, and risk posture. Codexify demonstrates capability patterns and implementation depth, but each deployment still requires scoped architecture, controls, and operating ownership.

## Maturity Boundary Model

| Tier | Meaning | Safe Client Language | Unsafe Claim |
|---|---|---|---|
| Implemented in code | A capability exists somewhere in the repository. | "This pattern is implemented in the codebase and can be reviewed as evidence." | "If it exists in code, it is ready for your deployment now." |
| Supported now | Explicitly part of current supported posture and release truth. | "This is in the current supported path and can be demoed as present capability." | "All installed or mounted surfaces are supported equally." |
| Internal/quarantined | Present for internal use, diagnostics, or guarded experimentation. | "This surface is internal/quarantined and not part of current client-ready scope." | "This internal route is available as a standard deliverable." |
| Pilot-track | Candidate for scoped pilot use with constraints and close supervision. | "This can be evaluated in a bounded pilot with explicit success/failure criteria." | "Pilot-track means production-ready by default." |
| Roadmap/future-facing | Directional or planned, but not currently committed delivery scope. | "This is roadmap direction and would require scoped planning before commitment." | "This will be included in your deployment timeline by default." |
| Unknown/unverified | Evidence is incomplete, stale, or absent for current runtime truth. | "We do not yet have current evidence for that claim in this environment." | "We assume it works because a related component exists." |

## Claims We Can Make Safely

- Codexify demonstrates multi-layer AI system architecture across frontend, API, queue, worker, and persistence seams.
- Codexify demonstrates local-first runtime design patterns with explicit operational boundaries.
- Codexify demonstrates queue-backed assistant execution and attempt-aware lifecycle handling.
- Codexify demonstrates document/media ingestion and retrieval architecture patterns.
- Codexify demonstrates provider/model governance patterns with policy-aware routing surfaces.
- Codexify demonstrates explicit trust-boundary thinking across client, backend, providers, and storage.
- Codexify demonstrates extensibility patterns through plugin and command surfaces with boundary controls.
- Codexify provides evidence-backed proof-of-capability for scoped consulting services.

## Claims We Must Not Make

- Codexify is production-ready for every client environment.
- Every feature in the repository is available for immediate client deployment.
- Internal/quarantined routes are supported client surfaces.
- Agent orchestration is fully autonomous and production-ready.
- Federation is turnkey.
- Voice and connectors are mature general offerings.
- Compliance is solved by architecture alone.
- Local-first automatically means compliant.
- Model routing alone eliminates vendor risk.
- Retrieval guarantees perfect answers.
- Persona configuration solves governance by itself.
- Demo success equals production reliability.

## High-Risk Overclaim Areas

### Internal/Quarantined Routes

**Risk:**
Internal surfaces are mistaken for supported customer-facing features.

**Safe Framing:**
Call out route posture explicitly before showing or discussing it.

**Do Not Say:**
"If it is mounted, it is customer-ready."

**Scope Requirement:**
Confirm supported-profile posture and route exposure rules before any client claim.

### Agent Orchestration

**Risk:**
Buyers hear "autonomy" where only bounded orchestration is proven.

**Safe Framing:**
Describe it as bounded automation requiring governance and approval design.

**Do Not Say:**
"This is fully autonomous operations."

**Scope Requirement:**
Define approval gates, rollback paths, and operator accountability per workflow.

### Federation

**Risk:**
Distributed sync is interpreted as turnkey multi-org production federation.

**Safe Framing:**
Present federation as a scope-intensive pattern requiring identity, trust, and policy design.

**Do Not Say:**
"Federation is plug-and-play."

**Scope Requirement:**
Scope trust model, key management, conflict policy, and failure handling first.

### Voice

**Risk:**
Voice demos are interpreted as mature enterprise voice operations.

**Safe Framing:**
Position voice as capability evidence requiring scoped quality, latency, and policy validation.

**Do Not Say:**
"Voice is fully ready across environments."

**Scope Requirement:**
Define model/provider policy, latency budget, and user experience acceptance criteria.

### Connectors

**Risk:**
Connector presence is interpreted as broad integration readiness.

**Safe Framing:**
State that each connector path is integration-specific and must be scoped and governed.

**Do Not Say:**
"Works with all your systems out of the box."

**Scope Requirement:**
Scope auth model, data boundaries, permissions, and operational monitoring per connector.

### Cron/Automation

**Risk:**
Scheduled runs are mistaken for business-process reliability guarantees.

**Safe Framing:**
Describe scheduling as one layer within a monitored and governed workflow.

**Do Not Say:**
"Cron means fully reliable automation."

**Scope Requirement:**
Define retries, idempotency, alerting, dead-letter behavior, and ownership.

### Command Bus

**Risk:**
Tool invocation capability is treated as unrestricted execution permission.

**Safe Framing:**
Explain command execution as policy-governed and explicitly bounded.

**Do Not Say:**
"The assistant can run anything safely."

**Scope Requirement:**
Define capability grants, least privilege, and auditable command boundaries.

### Command Center

**Risk:**
Operator UI presence is interpreted as complete production observability.

**Safe Framing:**
Describe current operator surfaces as useful visibility layers, not universal operational proof.

**Do Not Say:**
"This gives complete operational control for every scenario."

**Scope Requirement:**
Scope required observability signals, alerting, and runbook maturity for client ops needs.

### WebSocket/Realtime Surfaces

**Risk:**
Realtime event delivery is treated as guaranteed end-user visibility.

**Safe Framing:**
State clearly that event publication and UI receipt are separate reliability concerns.

**Do Not Say:**
"If events publish, users always see them instantly."

**Scope Requirement:**
Define reconnection behavior, backpressure handling, and fallback visibility paths.

### Compliance Posture

**Risk:**
Architecture language is mistaken for certification or legal readiness.

**Safe Framing:**
Frame architecture as support for compliance work, not compliance completion.

**Do Not Say:**
"This is compliance-ready by default."

**Scope Requirement:**
Perform scoped controls review against actual obligations and evidence requirements.

### Security/Privacy Posture

**Risk:**
Local-first and boundary language are interpreted as complete security coverage.

**Safe Framing:**
State that security/privacy outcomes require controls, operations, and governance beyond architecture.

**Do Not Say:**
"Local-first means secure forever."

**Scope Requirement:**
Scope identity, access, retention, incident response, and key-management practices.

### Local-First Deployment

**Risk:**
"Runs locally" is interpreted as low-ops or no-ops deployment.

**Safe Framing:**
Present local-first as an infrastructure choice with ongoing operations responsibility.

**Do Not Say:**
"Local deployment means no maintenance burden."

**Scope Requirement:**
Define backup, patching, monitoring, recovery, and support ownership model.

### Provider Routing

**Risk:**
Routing flexibility is interpreted as elimination of vendor and quality risk.

**Safe Framing:**
Describe routing as governance leverage, not risk elimination.

**Do Not Say:**
"Model routing removes vendor risk."

**Scope Requirement:**
Scope provider policy, budget controls, fallback behavior, and data exposure constraints.

### Retrieval Quality

**Risk:**
Retrieval architecture is interpreted as guaranteed answer correctness.

**Safe Framing:**
Explain retrieval as probabilistic and corpus-dependent, requiring evaluation.

**Do Not Say:**
"Retrieval is always accurate."

**Scope Requirement:**
Define corpus quality checks, relevance metrics, and false-positive/negative tolerance.

### Persona/Memory Systems

**Risk:**
Persona quality is mistaken for governance, policy, or access control.

**Safe Framing:**
Position persona/configuration as behavior-shaping, not authority or policy enforcement.

**Do Not Say:**
"Persona configuration handles governance automatically."

**Scope Requirement:**
Scope policy enforcement, auditability, and identity-bound access controls separately.

### Production Readiness

**Risk:**
Demo success is interpreted as deployability under real load and real operations.

**Safe Framing:**
State that production readiness requires explicit nonfunctional scope and acceptance tests.

**Do Not Say:**
"The demo proves production readiness."

**Scope Requirement:**
Define SLOs, failure budgets, load profile, reliability requirements, and operational runbooks.

### Client-Specific Deployment Scope

**Risk:**
A generic demo path is assumed to match a specific client environment.

**Safe Framing:**
Explain that deployment scope must map to client infrastructure, data boundaries, and workflows.

**Do Not Say:**
"What you saw is exactly what you will deploy."

**Scope Requirement:**
Run discovery to define data, identity, infra, risk, and phased delivery boundaries.

## Safe Language Replacements

| Instead of Saying | Say This |
|---|---|
| "This is ready to deploy for you." | "This is a reference implementation; your deployment would be scoped to your environment, data boundaries, and operating constraints." |
| "The system is fully autonomous." | "The architecture supports bounded automation, and autonomy level is a governance and scope decision." |
| "This solves compliance." | "This provides architecture patterns that can support compliance work; obligations still require scoped controls review." |
| "Everything here is supported." | "Support posture is bounded; we separate implemented, supported, internal/quarantined, pilot-track, and roadmap." |
| "If it is in the repo, it is available now." | "Code presence is evidence of capability, not automatic deployment scope." |
| "Local-first means secure by default." | "Local-first can reduce exposure, but security outcomes still depend on controls and operations." |
| "Routing eliminates vendor risk." | "Routing improves control options, but vendor, cost, latency, and quality risks still need policy management." |
| "Retrieval guarantees correct answers." | "Retrieval improves relevance when corpus and governance are scoped, but it remains probabilistic." |
| "We can connect to all your systems quickly." | "Integrations are scoped per system with explicit auth, permissions, and data-boundary controls." |
| "This is production-ready for everyone." | "Production readiness is client-specific and requires explicit reliability, security, and operations acceptance criteria." |
| "The event stream proves the user saw it." | "Event publication and UI receipt are separate concerns, and both need verification." |
| "The demo path is your rollout plan." | "The demo is evidence of approach; rollout planning comes from scoped discovery and phased implementation." |

## Feature-Specific Guardrails

| Capability Area | Safe Claim | Unsafe Claim | Likely Consulting Path |
|---|---|---|---|
| Chat/runtime execution | Queue-backed execution patterns are demonstrated. | Every accepted request is guaranteed completed and visible instantly. | Lifecycle observability, failure-mode mapping, SLO and retry policy design. |
| Document/media ingestion | Ingestion and embed architecture is implemented and demonstrable. | Any uploaded document will produce high-quality answers automatically. | Corpus curation, parsing QA, retention, and relevance governance. |
| Retrieval/RAG | Retrieval policy patterns are demonstrated. | Retrieval is always accurate and complete. | Corpus evaluation, retrieval tuning, and boundary-safe context policy. |
| Obsidian/local workspace ingestion | Local workspace ingestion pathways are demonstrated. | Workspace ingestion is universal multi-tenant knowledge governance. | User/project boundary policy, indexing strategy, and evidence validation. |
| Provider/model routing | Provider governance and routing seams are demonstrated. | Routing alone solves reliability, cost, and data-risk concerns. | Provider policy, budget controls, fallback lanes, and governance reporting. |
| Local-first infrastructure | Local-first runtime posture is demonstrable. | Local runtime removes ongoing operational responsibility. | Infrastructure sizing, backup/recovery, patching, and support ownership. |
| Persona/configuration | Persona/config layers can improve role fit and consistency. | Persona configuration replaces policy and access controls. | Prompt-policy alignment, role boundaries, and audit-friendly controls. |
| Plugin architecture | Extensible plugin patterns are present. | Plugins are universally safe and turnkey for client production. | Capability grants, permissioning, and integration hardening per plugin. |
| Command bus/tool execution | Bounded command execution architecture is present. | Assistants can run arbitrary actions safely by default. | Least-privilege command design, approvals, and audit trails. |
| Command Center/operator diagnostics | Operator-facing diagnostics are available. | Current UI surfaces provide complete production observability by default. | Ops dashboard scope, alerting, and incident workflow design. |
| Agent orchestration | Orchestration concepts and bounded patterns are represented. | Fully autonomous enterprise workflows are production-ready now. | Approval ladders, kill switches, and human-in-the-loop control design. |
| Federation | Federation-related architecture surfaces exist. | Cross-org federation is turnkey and ready without trust design. | Identity/trust contracts, sync policy, and conflict-resolution governance. |
| Voice | Voice-capable surfaces exist in the codebase. | Voice is a mature general offering in all client settings. | Quality targets, UX acceptance criteria, and provider policy constraints. |
| Connectors | Connector patterns and interfaces are represented. | Connectors are ready for all enterprise systems out of the box. | Integration-by-integration scoping, security review, and support mapping. |
| Cron/automation | Scheduling and recurring job patterns are present. | Scheduled jobs equal end-to-end process reliability. | Idempotency, run-state observability, exception handling, and owner model. |

## Demo Guardrails

- Do not start with the most experimental feature.
- Do not show private data.
- Do not show unsupported surfaces without naming the boundary first.
- Do not let technical curiosity replace the client pain narrative.
- Do not turn the demo into a feature inventory.
- Do not imply that the demo path is a deployment promise.
- Always transition back to the client's operating problem and success criteria.

## Technical Buyer Guardrails

- Be precise about runtime posture and current supported path.
- Name local/cloud boundaries explicitly.
- Separate supported routes from mounted/internal routes.
- Explain queue lifecycle honestly: acceptance, enqueue, execution, persistence, visibility.
- Explain retrieval limitations honestly, including false positives/negatives.
- Explain provider routing honestly, including policy and residual risk.
- Acknowledge missing hardening where relevant.
- Never hide maturity caveats to "keep momentum."

## Compliance and Privacy Guardrails

- The architecture can support privacy and compliance objectives.
- Architecture alone does not certify compliance.
- Every client requires scoped controls review against actual obligations.
- Data classification, retention, access control, logging, backup, incident response, and vendor exposure must be explicitly scoped.
- Do not imply HIPAA, SOC 2, GDPR, FERPA, or other regime readiness without scoped review and evidence.
- Keep legal claims out of demo language; use operational scope language instead.

## Local-First Infrastructure Guardrails

- Local-first posture can reduce certain exposure and dependency risks.
- Local-first does not remove operational responsibility.
- Clients still need backup, patching, access control, monitoring, incident response, recovery planning, and maintenance ownership.
- Hardware choices must be scoped to workload, budget, risk tolerance, and support capacity.
- Do not imply "runs locally" means "safe forever."

## Agent and Automation Guardrails

- Bounded automation can be designed safely with explicit controls.
- Autonomous execution must be scoped and justified per workflow.
- Human approval gates may be required for high-impact actions.
- Command surfaces must follow capability policies and least privilege.
- Scheduling/cron capability does not equal process reliability by itself.
- Do not sell "hands-free AI operations" as a default posture.

## Provider and Model Routing Guardrails

- Provider governance patterns are demonstrated in the implementation.
- Model routing can reduce lock-in pressure and improve control options.
- Routing does not eliminate vendor risk, cost volatility, data exposure, latency risk, or quality variability.
- Cloud-provider use must be governed by explicit policy and client approval.

## Retrieval and Document Intelligence Guardrails

- Retrieval architecture is demonstrated.
- Retrieval quality must be evaluated per client corpus.
- Ingestion does not guarantee useful or accurate answers.
- Semantic search can produce false positives and false negatives.
- Document governance, retention, permissions, and relevance scoring require explicit scope.

## Persona and Configuration Guardrails

- Persona/configuration can improve role fit and behavior consistency.
- Persona layers do not replace policy enforcement, access control, or auditability.
- Do not lead business buyers with persona mythology unless directly relevant.
- Keep identity boundaries and governance language explicit.

## Extensibility, Plugins, and Command Surface Guardrails

- Extensibility patterns are demonstrated in Codexify.
- Plugin and command surfaces require explicit permission boundaries.
- Internal command surfaces are not blanket client-ready features.
- Client integrations must be scoped, tested, monitored, and governed before production claims.

## Red Flag Phrases to Avoid

- "Fully autonomous"
- "Production-ready for everyone"
- "Compliance solved"
- "Secure by default"
- "No vendor risk"
- "Perfect retrieval"
- "Works with all your systems"
- "Just plug it in"
- "Everything in the repo is available"
- "This will replace your team"
- "No maintenance required"
- "Future-proof"

## Client-Safe Phrases to Use

- "Reference implementation"
- "Scoped deployment"
- "Supported posture"
- "Pilot-track capability"
- "Internal/quarantined surface"
- "Client-specific controls review"
- "Architecture pattern"
- "Operational boundary"
- "Governed workflow"
- "Evidence-backed demo"
- "Implementation path"
- "Maturity boundary"

## Pre-Demo Honesty Checklist

- [ ] Do I know which client pain this demo is addressing?
- [ ] Have I reviewed supported vs internal/quarantined boundaries?
- [ ] Am I using demo-safe data only?
- [ ] Have I prepared safe language for experimental features?
- [ ] Do I know which features I will not show?
- [ ] Do I know the primary consulting offer this demo should lead to?
- [ ] Am I avoiding compliance claims?
- [ ] Am I avoiding production-readiness assumptions?
- [ ] Can I explain route acceptance vs completion?
- [ ] Can I explain event publication vs UI receipt?
- [ ] Can I close by asking about the client's environment instead of pitching a product?

## Proposal Review Checklist

- [ ] Does the proposal distinguish Codexify as evidence rather than product?
- [ ] Does it define the client-specific scope?
- [ ] Does it avoid unsupported feature claims?
- [ ] Does it name assumptions and dependencies?
- [ ] Does it define what is out of scope?
- [ ] Does it include operational responsibilities?
- [ ] Does it avoid compliance certification language?
- [ ] Does it separate pilot-track from production deliverables?
- [ ] Does it define success criteria?
- [ ] Does it include maintenance/support expectations?

## Appendix: Evidence Anchors

Primary source status in this worktree:

- Missing: `docs/consulting/Codexify_Codebase_Capability_Audit.md`
- Missing: `docs/consulting/case-study/Codexify_As_Reference_Implementation.md`
- Available: `docs/consulting/demo/Codexify_Golden_Path_Demo_Script.md`

Current claim-gate and runtime references:

- `docs/architecture/00-current-state.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/config-and-ops.md`
- `config/supported_profiles/v1-local-core-web-mcp.yaml`
- `docker-compose.yml`
- `docker-compose.runtime.yml`
- `README.md`

Implementation seam anchors referenced for maturity-safe framing:

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
