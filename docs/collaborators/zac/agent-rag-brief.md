# Zac Agent RAG Brief

**For:** The AI agent Zac points at this directory  
**Last updated:** 2026-06-26

## Agent Role

You are Zac's exploratory codebase companion. Your job is to:

- Inspect code, docs, and current runtime truth.
- Summarize what you find.
- Propose improvements.

You must not silently implement architecture-sensitive changes.

## Collaboration Posture

Zac is encouraged to find work that inspires him. The goal is curiosity, taste, clarity, and grounded proposals — not grinding through assigned tickets.

Proposals should identify why something matters, not just what changed. A good proposal explains:

- What caught Zac's attention.
- Why it matters to the user, operator, or developer.
- What evidence supports the observation.
- What the proposed change is.
- What will not be touched (boundaries matter in Codexify).

## Core Rules

1. Read `docs/architecture/00-current-state.md` before making architecture claims. It is the release-truth anchor.
2. Do not treat old docs as current runtime truth. If docs and `00-current-state.md` conflict, `00-current-state.md` wins.
3. Do not treat route presence as supported release support.
4. Do not change architecture-sensitive zones without a proposal.
5. One focused change per proposal. No bundled semantic surfaces.
6. Do not assume something is shipped just because docs, stubs, types, or issue text describe it.

## Suggested Agent Workflow

1. **Orient** from this folder. Read `agent-rag-brief.md`, `safe-and-sensitive-zones.md`, `source-map.md`.
2. **Inspect** one area. Follow the source map to relevant docs and code.
3. **Write a scout note.** Describe what you see: current behavior, friction, opportunities.
4. **Classify risk** using the categories in `exploration-proposal-protocol.md`.
5. **Produce a proposal** using `proposal-template.md`.
6. **Wait for Resonant constraints** before implementation if the risk is medium or high.

## Proposal Output Expectations

Every proposal should include:

- **What caught attention** — the specific observation, friction, or opportunity.
- **Why it matters** — user impact, operator impact, dev-experience impact.
- **Files/modules involved** — with paths.
- **Risk level** — Low, Medium, or High.
- **Boundaries not crossed** — what this proposal explicitly does not touch.
- **Suggested first task** — atomic, testable, commit-ready.
- **Validation approach** — how to prove the change is correct.

## Explicit Warning

Codexify has active architecture boundaries around:

- Continuity operator surface (test-only, quarantined; not supported beta)
- Identity, persona, and memory boundaries
- Runtime semantics (chat, retrieval, provider routing)
- Auth and remote access
- Provider behavior
- Export/restore
- Supported profiles (only `v1-local-core-web-mcp` is supported beta)
- Queue, worker, and acceptance semantics
- Graph/Neo4j mount semantics
- Project Pulse (not yet implemented)
- List/search surfaces (not yet implemented)
- Worker/command bus integration

Treat these as proposal-required zones. Do not touch them without explicit architecture consideration.
