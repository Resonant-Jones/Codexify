---
tags:
* architecture
* adr
* flow-builder
* elicitation
* workflow-authoring
  aliases:
* ADR-006
* Flow Builder Elicitation Lane
---

# ADR-006: Flow Builder Elicitation Lane

## Status

Accepted

## Date

2026-04-15

## Context

Codexify already has execution-centric workflow surfaces and control-plane doctrine, but many real users do not arrive with a complete delegatable spec. The useful work is often blocked upstream by tacit knowledge compression: the user knows the domain, the constraints, and the desired outcome, but not the exact runnable structure.

If Flow Builder only accepts a finished spec, it forces users to do the hardest part outside the system and leaves the actual bottleneck unnamed.

## Problem

The architecture must account for three truths:

- most users cannot supply a complete executable spec up front
- valuable work is blocked by the need to compress tacit expertise into explicit structure
- execution-only builders assume the spec already exists and therefore miss the real bottleneck

This is not a UI problem. It is a workflow-authoring and control-plane problem.

## Decision

Flow Builder must support an upstream elicitation lane.

The lane exists to convert vague goals and tacit expertise into explicit, inspectable, delegatable structure before runnable execution begins.

Flow Builder must support two authoring modes:

- Build from process: the user already knows the steps, and Flow Builder captures, normalizes, and compiles them.
- Build from expertise: the user knows the domain outcome, and Flow Builder helps discover, extract, and validate the steps before compilation.

A flow may begin in specification-building mode. A flow is not complete merely because it has executable nodes.

## Required conceptual stages

The canonical lane is `interview -> extract -> normalize -> validate -> compile -> execute`.

| Stage | Purpose |
|---|---|
| `interview` | Gather intent, constraints, vocabulary, and missing assumptions from the user. |
| `extract` | Pull candidate steps, rules, boundaries, and domain facts out of the conversation. |
| `normalize` | Convert raw notes into a canonical workflow shape with stable terms and structure. |
| `validate` | Check completeness, ambiguity, and internal consistency before execution is permitted. |
| `compile` | Produce an inspectable, revisable spec artifact from the validated structure. |
| `execute` | Run the compiled and validated workflow. |

The stage order matters architecturally even if the UX presents the stages as a conversational loop.

## Canonical doctrine

- A flow is not complete merely because it has executable nodes.
- A flow may begin in a specification-building mode.
- Flow Builder should support both:
  - Build from process
  - Build from expertise
- Elicitation is upstream of execution, not a thin prompt wrapper around it.
- Spec-building output must be treated as architecture, not as transient chat residue.

## Control-plane implications

- Elicitation outputs should be treated as structured workflow inputs, not loose chat residue.
- Validation must happen before execution.
- Compiled spec artifacts must be inspectable and revisable.
- The architecture should keep elicitation, compilation, execution, and observability distinct so the system does not blur authoring with runtime behavior.
- Any future runtime support must surface actual artifacts or states instead of hiding behind prompt magic.

## Proposed primitive family (not yet implemented)

The following primitives are bounded examples of the sort of seams this lane may require later. They are not current runtime claims.

- `elicitation.interview` - capture goals, constraints, and missing assumptions.
- `elicitation.refine` - tighten a draft through iterative clarification.
- `elicitation.extract_rules` - surface candidate rules and decision boundaries from the conversation.
- `elicitation.generate_checklist` - derive validation checkpoints from the draft spec.
- `elicitation.compile_profile` - compile the validated structure into an inspectable profile or artifact.
- `elicitation.validate_spec` - evaluate completeness, ambiguity, and rule consistency before execution.

## Non-goals

- This ADR does not promise implementation.
- This ADR does not claim that chat, persona, or workspace are replaced by Flow Builder.
- This ADR does not redesign the broader workflow engine.
- This ADR does not claim current `main` already exposes the lane as a supported runtime behavior.

## Risks

- Over-rigidity could force complete upfront structure and make the system harder to use for exploratory work.
- Architecture drift could occur if elicitation is implemented as hidden prompt magic instead of a bounded control-plane seam.
- False claims of support could appear if the concept is described as live before runtime proof exists.

## Consequences

### Positive

- Better delegation fidelity because the system can help turn tacit expertise into explicit structure.
- More truthful workflow authoring because the system acknowledges the spec-building phase instead of skipping it.
- Stronger reuse of expertise because validated structure can be compiled and revisited.

### Negative

- More up-front complexity in the authoring experience.
- New primitives and proof seams will be needed later if the architecture is implemented faithfully.
- The system must keep elicitation artifacts inspectable, which increases documentation and validation burden.

## Documentation follow-through deferred

- `docs/architecture/flows.md` should only be updated once an implemented or at least code-adjacent flow path exists.
- `docs/architecture/00-current-state.md` should only mention this when it becomes present supported reality.
- Runtime/state contracts should only expand after implementation introduces observable states or artifacts.
- No runtime proof is claimed in this ADR.

## Links

* [[ADR Index]]
* [[002-Dual-State-Machine-Model|ADR-002 Dual State Machine Model]]
* [[004-Retrieval-Policy-as-Control-Plane|ADR-004 Retrieval Policy as Control Plane]]
* [[chat-runtime-contract|Chat Runtime Contract]]
* [[router-decision-table|Retrieval Router Decision Table]]
* [[system-overview|System Overview]]
* [[flows|Critical Flows]]
* [[delegation-runtime|Delegation Runtime Contract]]
* [[00-current-state]]

## Notes

This ADR establishes the doctrine that Flow Builder must be able to move from tacit expertise to explicit, inspectable structure before execution. It does not claim that the runtime already does so.
