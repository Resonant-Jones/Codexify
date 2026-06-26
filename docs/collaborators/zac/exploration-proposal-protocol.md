# Exploration and Proposal Protocol

**For:** Zac and Zac's agent  
**Last updated:** 2026-06-26

## Philosophy

Zac is not expected to work like Resonant Jones. Zac should explore what feels alive, awkward, undercooked, or worth improving. Inspiration is welcome. Curiosity is the engine.

But architecture drift is not welcome. Codexify has boundaries that matter. Changes inside those boundaries require proposals and review before implementation.

This protocol exists so Zac can explore freely while keeping architecture governance intact.

## Exploration Loop

1. **Pick an area.** Let curiosity guide you. What feels interesting? What feels awkward? What looks undercooked?
2. **Inspect current truth.** Read the relevant docs, source files, and tests. Ground observations in evidence.
3. **Notice friction or opportunity.** Something feels slow. Something is missing. Something is unclear. Something could be simpler.
4. **Classify risk.** Use the risk classes below.
5. **Write a proposal.** Use the template in `proposal-template.md`.
6. **Get constraints if needed.** For medium or high-risk proposals, bring the proposal to Resonant for constraints.
7. **Produce a Codexify task prompt.** Only after constraints are clear.

## Proposal Format

A good proposal is short, evidence-backed, and bounded. It should include:

- **Title** — descriptive and specific.
- **What caught my attention** — the observation, not a solution.
- **Why it matters** — user impact, operator impact, dev-experience impact.
- **Affected files/modules** — with paths.
- **Current evidence** — what docs, code, tests, or live proof support the observation.
- **Proposed change** — what would change, at a high level.
- **What I will not touch** — explicit boundaries. This is as important as what you will touch.
- **Risk classification** — Low, Medium, or High.
- **Validation** — how to prove the change is correct.
- **Open questions for Resonant** — things you need constraints on.

## Risk Classes

### Low Risk

Changes that do not alter runtime meaning or architecture contracts.

Examples:
- Copy and docs readability improvements.
- Small UI polish (spacing, labels, empty states).
- Local component styling.
- Dev-experience friction notes.
- Small bug reports with evidence.

Low-risk proposals may become standard Codexify tasks without heavy architecture review.

### Medium Risk

Changes that touch behavior, settings, or API surfaces but do not alter core runtime semantics.

Examples:
- Behavior changes in non-sensitive modules.
- Settings additions or renames.
- API touchpoints outside sensitive zones.
- Local state management changes.
- Test harness improvements.

Medium-risk proposals need Resonant's constraints before implementation.

### High Risk

Changes that touch runtime semantics, identity, memory, routing, auth, or architecture contracts.

Examples:
- Continuity operator changes.
- Reality State, Reality Commit, or Project Reality surfaces.
- Export/restore behavior.
- Account identity and provenance.
- Chat runtime semantics.
- Memory and persona boundaries.
- Provider routing.
- Retrieval behavior.
- Auth and remote access.
- Queue, worker, or acceptance semantics.
- Supported profile activation.
- Project Pulse.
- Graph/Neo4j mount semantics.

High-risk proposals require an architecture-impact Codexify task lane and governing docs.

## Proposal-Before-Change Rule

- Low-risk proposals may become standard Codexify tasks.
- Medium-risk proposals need Resonant's constraints.
- High-risk proposals need architecture-impact task lane and governing docs/ADRs.

Never skip from observation to implementation for medium or high-risk changes.

## Examples of Good Proposals

**Good example (low risk):**
- Title: "Clarify empty-state message on the chat thread list"
- What caught my attention: "When no threads exist, the empty state says 'No threads' but doesn't suggest what to do next."
- Why it matters: "New users may not know how to start their first thread."
- Proposed change: "Add a short hint: 'Start a new thread to begin chatting.'"
- Risk: Low
- What I will not touch: "No API changes, no runtime behavior changes."
- Suggested first task: "Edit the frontend empty-state component text."

**Good example (medium risk):**
- Title: "Add tooltip to model selector explaining runtime-family badges"
- What caught my attention: "The model selector shows [MLX] and [GGUF] badges but doesn't explain what they mean."
- Why it matters: "Users may select an incompatible model and get errors without understanding why."
- Evidence observed: "Frontend model selector component in Persona Studio settings."
- Proposed change: "Add a small info tooltip next to the runtime-family badge column."
- Risk: Medium (touches settings UI, may need catalog backend alignment)
- What I will not touch: "No provider routing changes, no catalog changes."
- Questions for Resonant: "Where should the explanation text live? Is there a tooltip component pattern already?"

## Examples of Forbidden Bundles

**Do not combine these in one proposal:**

- "Add list/search AND build a UI for it" — these are separate semantic surfaces.
- "Add diagnostics improvements AND Project Pulse summary" — diagnostics is counts; Pulse is interpretation.
- "Activate Continuity operator in supported beta AND add new routes" — activation and new semantics are separate.
- "Improve export/restore AND include continuity state" — each needs its own contract.
- "Add chat hooks AND worker integration for continuity" — chat hooks and worker integrations are separate architecture-impact surfaces.

## When to Ask Resonant

Ask Resonant when:

- The proposal touches any sensitive zone listed in `safe-and-sensitive-zones.md`.
- You are unsure whether a risk is Medium or High.
- The proposed change crosses module boundaries you haven't explored fully.
- You want clarity on whether something is already planned or deferred.
- The change might affect the supported beta profile `v1-local-core-web-mcp`.
