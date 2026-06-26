# Safe and Sensitive Zones

**For:** Zac's agent — know where to explore and where to propose first  
**Last updated:** 2026-06-26

## Purpose

This file gives Zac's agent a compact map of exploration zones. Some areas are safe to explore and propose changes in directly. Other areas are architecture-sensitive — proposals must come before implementation, and Resonant's constraints are required.

This is not a permission system. It is a risk-awareness map. Curiosity is welcome in all zones. Implementation without proposal is only welcome in safe zones.

## Safe Exploration Zones

These areas are lower risk. Zac's agent can explore freely and propose changes directly. Low-risk proposals may become standard Codexify tasks.

- **UI feel and visual polish** — spacing, typography, color consistency, layout refinements.
- **Component readability** — clearer prop names, simpler markup, better component structure.
- **Docs readability** — clarifying ambiguous prose, fixing broken links, adding missing sections.
- **Onboarding docs** — making first-run docs clearer, adding troubleshooting guidance.
- **Empty states and labels** — improving UX copy, adding helpful hints, fixing inconsistent labels.
- **Frontend affordances that do not alter runtime meaning** — tooltips, aria-labels, keyboard navigation, minor animation refinements.
- **Dev-experience friction notes** — documenting things that are confusing or slow during development.
- **Small bug reports with evidence** — observing and documenting reproducible misbehavior without proposing architecture changes.

## Proposal-Required Zones

These areas are architecture-sensitive. Changes here require a proposal, risk classification, and Resonant's constraints before any implementation.

Do not implement changes in these zones without a proposal:

- **Continuity operator** — six-route surface is test-only, quarantined, and complete for its defined scope. Expansion requires a new architecture-impact contract.
- **Reality State / Reality Commit / Project Reality concepts** — these are part of the Continuity Protocol Suite. They are contract-defined, not runtime-implemented (beyond the test-only operator surface).
- **Export/restore** — the export artifact contract governs portability. Changes affect what users can carry between instances.
- **Account identity and provenance** — identity precedence, persona borrowing, and deep identity consent are governed by contracts.
- **Chat runtime** — completion, retrieval, context assembly, and turn-lock semantics are core to the supported beta path.
- **Memory/persona boundaries** — personal facts, memory entries, and persona configuration have lifecycle and boundary rules.
- **Provider routing** — catalog, health, and router behavior govern which models are available and executable.
- **Retrieval** — RAG depth, context broker behavior, and embedding pipelines are runtime-critical.
- **Auth and remote access** — API key handling, session behavior, and exposure mode are security-sensitive.
- **Queue/worker/acceptance semantics** — Redis queue structure, task events, and completion lifecycle are high-blast-radius.
- **Supported profile activation** — the `v1-local-core-web-mcp` profile is the supported beta contract. Adding or activating profiles is a release decision.
- **Project Pulse** — not yet implemented. Requires its own contract and architecture-impact task.
- **Graph/Neo4j mount semantics** — graph writes are default-off. Graph support requires explicit enablement.

## Current Protected Milestone

The Continuity operator six-route surface is complete as test-only and quarantined.

- All six routes (write, packet readback, diagnostics, state readback, commit readback, link readback) exist and are live-proven.
- They are gated behind `test-continuity` profile, `CODEXIFY_ENABLE_CONTINUITY_OPERATOR_ROUTES=true`, and API key auth.
- The supported beta profile `v1-local-core-web-mcp` quarantines all six routes (returns 404).
- No expansion without a new architecture-impact contract.

## How to Ask for Constraints

If Zac's agent explores a sensitive zone and finds something worth changing:

1. Write a proposal using the template in `proposal-template.md`.
2. Classify the risk.
3. Include explicit questions for Resonant in the proposal.
4. Bring the proposal to Resonant before writing any implementation code.

Resonant will provide constraints: what's in scope, what's deferred, what contracts govern the change, and what ADR alignment is needed.

## Forbidden Assumptions

Zac's agent must not assume:

- Route exists means supported.
- Test profile means beta profile.
- Diagnostics means Project Pulse.
- Exact readback means list/search.
- Local DB IDs mean export identity.
- Graph-off flags mean graph support.
- Docs-only contracts mean shipped runtime behavior.
- Route presence means release support.
- Stubs or types mean implemented features.
- Code comments about future plans mean current reality.
