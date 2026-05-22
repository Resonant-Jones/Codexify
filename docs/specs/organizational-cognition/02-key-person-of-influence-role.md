# Key Person of Influence Role

> Classification: conceptual product/architecture doctrine<br>
> Runtime impact: none<br>
> Release promise: none<br>
> Interpretation rule: if this conflicts with `docs/architecture/00-current-state.md`, current-state wins.

Grounding note: this spec maps to Codexify's identity and provenance posture. In current architecture and policy docs, IDDB separates "what happened" from "who you are," keeps deep identity opt-in, and treats personas as masks that borrow identity rather than own it. Export/restore doctrine likewise preserves provenance, project membership, thread/message structure, media linkage, and relationship structure rather than silently collapsing them.

## Purpose

Define the Codexify equivalent of the "Key Person of Influence" role.

In Codexify, this is not celebrity, branding, or audience growth. It is the system function that preserves coherent meaning, identity, direction, and trust.

## Codexify Translation

The Key Person of Influence maps to:

- Guardian identity spine
- provenance and lineage
- canonical truth layers
- thread continuity
- user-owned identity boundaries
- project-level meaning
- narrative and decision context

## System Responsibility

This role answers:

- Who is speaking?
- What is the source of this claim?
- Which thread, project, or artifact does this belong to?
- What is durable truth versus transient conversation?
- What should persist as memory?
- What must remain only diary/history?
- Which persona is speaking, and what authority does it have?

## Design Interpretation

The system's "influence" is not persuasion.

It is coherence.

This framing is most useful when a Codexify environment preserves:

- source messages remain traceable
- generated artifacts retain lineage
- personas do not own identity
- memory promotion is explicit
- user sovereignty is preserved
- runtime outputs can be tied back to originating context

## Related Existing Surfaces

- IDDB / Identity Mirror
- Persona Studio
- Thread-artifact lineage
- Account export/restore
- Chat runtime message identity
- Source-thread preservation
- Project ownership boundaries

## Invariants

- Chat history is content, not automatically identity.
- Deep identity is opt-in.
- Personas borrow identity; they do not own it.
- Artifacts must preserve source-thread or source-message lineage when possible.
- Generated outputs must not erase the difference between draft, reviewed, corrected, and confirmed.
- Identity labels must not be inferred durably without consent.

## Failure Modes

| Failure | Consequence |
| --- | --- |
| Persona owns identity | Identity contamination |
| Artifact loses source thread | Broken provenance |
| Memory promoted silently | Sovereignty violation |
| Assistant reply cannot bind to request | Transcript integrity failure |
| Export drops lineage | Account portability failure |

## Product Language

This role is the system's "meaning anchor."

It gives the runtime a stable self-reference point without turning the assistant into an identity owner.
