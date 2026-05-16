# Codexify Campaign Packet

## Campaign Pulse

What changed, what matters, and why now.

- Window covered: 2026-05-14 (latest generated packet run) to 2026-05-16 (first campaign-intelligence packet).
- What changed: an internal campaign-intelligence layer now exists with explicit source precedence, claim gates, mood lanes, and a reusable engine prompt; `master-campaign-brief.md` is present and supplies a clear strategic spine.
- Why it matters: prior generated outputs carry real risk flags and implementation-heavy evidence, so the current opportunity is to tighten public narrative around durable continuity claims that are already supportable.
- Why now: AI usage volume is rising faster than memory durability, and Codexify has a strong truth-bounded angle ready for repeatable campaign production.

## Source Inputs

Repos, docs, audits, website files, Drive notes, proof artifacts, and generated reports read.

- Repos: current repository checkout and `docs/` truth/marketing surfaces.
- Docs:
  - `docs/Marketing/master-campaign-brief.md`
  - `docs/Marketing/campaign-intelligence/README.md`
  - `docs/Marketing/campaign-intelligence/source-map.md`
  - `docs/Marketing/campaign-intelligence/campaign-packet-template.md`
  - `docs/Marketing/campaign-intelligence/claim-gate-checklist.md`
  - `docs/Marketing/campaign-intelligence/content-pillars.md`
  - `docs/Marketing/campaign-intelligence/mood-board-lanes.md`
  - `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`
  - `docs/Marketing/chatgpt-project-bundle/02-positioning-core.md`
  - `docs/Marketing/chatgpt-project-bundle/10-language-bank.md`
  - `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
  - `docs/architecture/00-current-state.md`
  - `docs/architecture/execution-ledger-gate-artifacts-contract.md`
  - `docs/architecture/execution-ledger-token-domain-proposal.md`
- Code/test signals:
  - `guardian/agents/execution_ledger_contracts.py`
  - `guardian/agents/execution_ledger_tokens.py`
  - `guardian/command_bus/permission_profiles.py`
  - `tests/command_bus/test_invoke_permission_profile_enforcement.py`
  - `tests/routes/test_connector_external_transport_policy.py`
- Audits: current marketing risk posture inferred from latest generated review notes and ledger.
- Website files: none read in this run.
- Drive notes: none read in this run.
- Proof artifacts:
  - `docs/architecture/2026-05-05-supported-profile-live-proof.md` (referenced by claim boundary)
  - `docs/architecture/2026-05-08-supported-profile-live-proof.md` (referenced by claim boundary)
  - `docs/architecture/2026-05-05-coding-result-return-path-live-proof.md` (referenced by claim boundary and latest review notes)
- Generated reports:
  - `docs/Marketing/generated/CAMPAIGN_2026_05_14_MARKETING_V1/run-metadata.json`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_14_MARKETING_V1/core-brief.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_14_MARKETING_V1/evidence-ledger.json`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_14_MARKETING_V1/review-notes.md`
  - `docs/Marketing/generated/history/run-history.jsonl`

## Claim Posture

### Safe

- Claim: Codexify is local-first by default on the supported path.
  - Evidence paths: `docs/architecture/00-current-state.md`, `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
  - Proof tier: live-proven/verified posture in current truth docs
- Claim: Codexify supports project/thread continuity as a central workflow surface.
  - Evidence paths: `docs/architecture/00-current-state.md`, `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`
  - Proof tier: implemented to live-proven posture (as documented)
- Claim: Upload -> embed -> readback is part of supported-path evidence.
  - Evidence paths: `docs/architecture/00-current-state.md`, `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
  - Proof tier: live-proven/verified posture in current truth docs
- Claim: Runtime truth surfaces are inspectable and claims are evidence-linked.
  - Evidence paths: `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`, `docs/Marketing/contracts/claim-truth-model.md`
  - Proof tier: implemented/verified governance posture

### Caution

- Claim: Command Center can be referenced as an operator-facing control seam.
  - Risk reason: must not imply autonomous dispatch or unsupervised execution.
  - Evidence paths: `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`, `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
  - Safe phrasing: "operator-facing, non-dispatch control seam"
- Claim: Provider breadth and connector ecosystem can be mentioned.
  - Risk reason: current posture is local-first; maturity is constrained.
  - Evidence paths: `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`, `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
  - Safe phrasing: "evolving and bounded, not broad default support"
- Claim: Event visibility and runtime traces are useful in messaging.
  - Risk reason: visibility does not equal guaranteed delivery or completion.
  - Evidence paths: `docs/Marketing/chatgpt-project-bundle/10-language-bank.md`, `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
  - Safe phrasing: "inspectable lifecycle visibility"
- Claim: Execution Ledger gate artifacts and token-domain scaffolding strengthen proof-before-promise discipline.
  - Risk reason: current posture is proof-adjacent architecture scaffolding; runtime wiring is intentionally deferred for parts of this seam.
  - Evidence paths: `docs/architecture/execution-ledger-gate-artifacts-contract.md`, `docs/architecture/execution-ledger-token-domain-proposal.md`, `guardian/agents/execution_ledger_contracts.py`, `guardian/agents/execution_ledger_tokens.py`
  - Safe phrasing: "bounded contract models for intent, plan, and proof review"
- Claim: Permission-profile and external-transport policy checks strengthen bounded execution posture.
  - Risk reason: this is scoped enforcement evidence in specific command-bus and connector seams, not a blanket product-wide security guarantee.
  - Evidence paths: `guardian/command_bus/permission_profiles.py`, `tests/command_bus/test_invoke_permission_profile_enforcement.py`, `tests/routes/test_connector_external_transport_policy.py`
  - Safe phrasing: "pre-dispatch and pre-persistence policy checks on scoped execution paths"

### Future-Facing

- Claim: Hosted deployment is a standard supported product lane today.
  - Why future-only: not current default supported posture.
  - Evidence needed to promote: explicit current-state support claim and fresh live proof artifacts.
- Claim: Federation and broad connector maturity are core release promises now.
  - Why future-only: currently marked constrained/evolving.
  - Evidence needed to promote: explicit support matrix plus live proof and release-posture updates.
- Claim: Broad enterprise readiness is current-tense product posture.
  - Why future-only: exceeds current proof boundary.
  - Evidence needed to promote: updated current-state truth plus specific operational/compliance evidence.

### Rejected / Do Not Say

- Unsafe line: "Codexify provides fully autonomous agents that run unsupervised end to end."
  - Why rejected: directly outside current truth boundary.
  - Blocking source: `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`, `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
- Unsafe line: "Codexify is a mature hosted SaaS platform."
  - Why rejected: conflicts with local-first supported-path posture.
  - Blocking source: `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`
- Unsafe line: "Codexify is broadly enterprise-ready out of the box."
  - Why rejected: unsupported readiness overclaim.
  - Blocking source: `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
- Unsafe line: "Codexify guarantees privacy/security and zero context loss."
  - Why rejected: absolute guarantees are prohibited.
  - Blocking source: `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`, `docs/Marketing/brand/constitution.md`

## Architecture Signal Addendum

These architecture signals reinforce the campaign's inspectability and bounded-execution narrative without widening public claims:

- Execution Ledger gate artifacts formalize three distinct checkpoints: intent/scope, implementation-plan, and completion/proof review.
- The gate-artifact contract explicitly preserves "acceptance is not completion" and "event publication is not UI receipt," which aligns with proof-before-promise messaging.
- The token-domain proposal plus bounded backend token registry introduces canonical vocabulary for gate decisions, validation modes, criterion results, and proof outcomes, reducing lifecycle ambiguity in future implementation seams.
- Permission-profile evaluation adds explicit allow/deny checks at dispatch time (actor/subject/task scope, command class/id, write-path scope, shell, network, connector usage) before side effects.
- Connector external-transport policy tests show deny-before-persistence behavior (including `blocked_before_persistence` responses) for missing allow rules, explicit deny rules, malformed URLs, and unsupported transports.

Campaign interpretation rule:
- Treat these as proof-adjacent infrastructure maturity signals that support conservative claims around inspectability and bounded execution.
- Do not promote them to autonomous-agent claims, hosted-SaaS maturity claims, enterprise-readiness claims, or absolute privacy/security guarantees.

## Audience Target

Primary segment: Solo AI builders
Pain: tool sprawl, chat debris, and context loss across projects.
Desired transformation: from disposable AI sessions to owned, durable project continuity.
Best channel: Website hero + supporting social carousel.
Likely objection: "This sounds like another note app or chatbot wrapper."

## Core Message

Codexify exists because AI made thought faster, but not more durable, so serious builders can own the thread and build intelligence they can keep.

## Positioning Method

Choose one primary method:
- status flip
- myth
- hidden door
- ritual
- superpower

Selected primary method: status flip.

Why this method fits the moment:
It cleanly reframes current behavior ("AI chat is disposable") into a higher-status operating identity ("AI work should become durable intelligence"), while staying fully inside supportable continuity and retrieval claims.

## Visual Direction

Mood lane: Memory Spine
Image concepts:
- a single luminous thread moving through search -> chat -> document -> artifact
- stacked project timeline cards showing continuity instead of scroll-loss
- split panel: disposable session debris versus linked project memory spine
Ad layout ideas:
- Concept A: "Own the Thread" vertical timeline ad with one core claim and one proof callout
- Concept B: "Chat History Is Not Memory" split-screen ad (left fogged chat stack, right structured continuity spine)
- Concept C: "Build Intelligence You Can Keep" quiet dark interface card with restrained teal/cyan trace lines
Infographic ideas:
- "The Lineage of an Idea": Search -> Chat -> Upload -> Synthesis -> Artifact -> Retrieval loop
- "Disposable Chat vs Durable Memory": side-by-side comparison grid
- "What Codexify Preserves": conversations, docs, workflow traces, project artifacts, proof surfaces
Motion/transition notes:
- slow connective line reveals between nodes
- subtle card stacking, no high-energy neon transitions
- emphasize continuity accumulation over flashy UI movement

## Draft Assets

Homepage block:
"AI thought is accelerating, but continuity is still fragile. Codexify is a local-first cognitive workspace that helps you keep the thread from first question to reusable artifact."

Social post:
"Most AI workflows still end in scrollback. Codexify helps turn fragments into durable project intelligence you can retrieve, inspect, and build on. Own the thread. Build intelligence you can keep."

Educational post:
"AI chat history is not memory. Memory means structured continuity: linked threads, retrievable documents, explicit proof surfaces, and context you can audit."

Ad copy:
Headline: "Own the thread of your work."
Body: "Codexify helps serious builders turn chats, docs, and workflow traces into durable intelligence in a local-first workspace."
CTA: "Explore Codexify"

Founder note:
"I built Codexify around one frustration: AI made thought faster, but not more durable. Continuity should be infrastructure, not luck."

Infographic caption:
"The value is not only the final artifact. It is the traceable line that made the artifact possible."

## Proof Assets Needed

Screenshots:
- thread/project continuity view with linked artifact evidence
- upload -> retrieval example on supported path
- runtime truth surface (health/catalog/events/proof panel)

Runtime traces:
- bounded request lifecycle trace showing acceptance vs completion distinction
- evidence of persisted completion artifact in source thread context
- command-bus blocked trace showing `permission_profile_denied:*` with `run.blocked` before dispatch
- connector policy denial trace showing `blocked_before_persistence: true` and zero persistence writes

Docs:
- refreshed references to `docs/architecture/00-current-state.md`
- latest supported-profile proof artifact links
- claim ledger snapshot used for packet classification
- architecture references for gate artifacts and token-domain proposal
- code/test seam references for permission-profile enforcement and connector transport policy enforcement

Demos:
- short "idea -> upload -> retrieval -> artifact" walkthrough gif/video
- side-by-side "chat history vs memory spine" educational demo

Repo evidence:
- `docs/Marketing/generated/CAMPAIGN_2026_05_14_MARKETING_V1/review-notes.md`
- `docs/Marketing/generated/CAMPAIGN_2026_05_14_MARKETING_V1/evidence-ledger.json`
- `docs/Marketing/generated/history/run-history.jsonl`

## Do-Not-Say List

Unsafe lines, hype claims, unsupported promises.

- "Fully autonomous agents manage your work end to end."
- "Codexify is a mature hosted SaaS platform today."
- "Enterprise-ready out of the box for broad compliance guarantees."
- "Guaranteed privacy/security with zero risk."
- "Zero context loss forever."
- "Universal AI brain that replaces all other tools."
- "Set-and-forget automation with no human supervision."

## Next Best Artifact

The one artifact that should be produced next.

Produce a homepage hero mockup packet for the Memory Spine lane (desktop + mobile) using the "Own the thread. Build intelligence you can keep." spine with one safe claim and one proof-callout annotation per frame.
