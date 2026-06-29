# Paul Exploration and Proposal Protocol

**For:** Paul and Paul's agent
**Last updated:** 2026-06-29

## Philosophy

Paul is not expected to work like Resonant Jones. Paul should study what feels interesting, underexplained, or structurally important. The first move is usually a report, not a change.

Architecture drift is still not welcome. Codexify has boundaries that matter. Changes inside those boundaries require proposals and review before implementation.

This protocol keeps the study lane calm while preserving architecture governance.

## Exploration Loop

1. Pick one area.
2. Inspect current truth.
3. Notice friction, opportunity, or a boundary worth understanding.
4. Classify risk.
5. Write a report first.
6. Turn the report into a proposal only if the change still seems worth pursuing.
7. Get constraints before implementation if the risk is medium or high.

## Report-to-Proposal Shape

A good report is short, evidence-backed, and bounded. It should answer:

- What did I inspect?
- What did I observe?
- Why does it matter?
- What is still unclear?
- What would I need to ask Resonant before changing anything?

A good proposal adds the missing implementation shape:

- Title
- What caught attention
- Why it matters
- Evidence observed
- Files/modules likely involved
- Risk classification
- Proposed first move
- What I will not touch
- Questions for Resonant
- Suggested validation

## Risk Classes

### Low Risk

Changes that do not alter runtime meaning or architecture contracts.

Examples:

- Copy and docs readability improvements.
- Small UI polish.
- Local component styling.
- Dev-experience friction notes.

### Medium Risk

Changes that touch behavior, settings, or API surfaces but do not alter core runtime semantics.

Examples:

- Behavior changes in non-sensitive modules.
- Settings additions or renames.
- API touchpoints outside sensitive zones.
- Local state management changes.

### High Risk

Changes that touch runtime semantics, identity, memory, routing, auth, or architecture contracts.

Examples:

- Continuity operator changes.
- Export/restore behavior.
- Account identity and provenance.
- Chat runtime semantics.
- Memory and persona boundaries.
- Provider routing.
- Retrieval behavior.
- Auth and remote access.
- Queue, worker, or acceptance semantics.
- Supported profile activation.
- Graph/Neo4j mount semantics.

## Proposal-Before-Change Rule

- Low-risk reports may become standard Codexify tasks.
- Medium-risk proposals need Resonant's constraints.
- High-risk proposals need the architecture-impact task lane and governing docs.

Never skip from observation to implementation for medium or high-risk changes.
