# Cognitive Role Topology

> Classification: conceptual product/architecture doctrine<br>
> Runtime impact: none<br>
> Release promise: none<br>
> Interpretation rule: if this conflicts with `docs/architecture/00-current-state.md`, current-state wins.

## Purpose

Define the four-role cognitive topology that maps AI-enabled team design onto Codexify's architecture.

The goal is not to copy a business hiring framework. The goal is to extract the underlying operational roles that any scalable intelligence system requires.

## Core Thesis

Every scalable AI-native system needs four irreducible cognitive functions:

1. Direction and meaning
2. Signal acquisition
3. Continuity and trust
4. Adaptive execution

In business language, these resemble:

1. Key Person of Influence
2. Head of Growth
3. Head of Delight
4. High Agency Generalist

In Codexify language, they become:

1. Canonical meaning surface
2. Retrieval and signal router
3. Runtime continuity layer
4. Governed orchestration layer

## Role Map

| Cognitive Function | Business Role | Codexify Equivalent |
| --- | --- | --- |
| Meaning and direction | Key Person of Influence | Identity spine, provenance, canonical truth |
| Signal acquisition | Head of Growth | Retrieval router, context broker, signal digest |
| Continuity and trust | Head of Delight | Workspace, runtime state, observability, memory boundaries |
| Adaptive execution | High Agency Generalist | Guardian orchestration, command bus, bounded tool loop |

## Architectural Interpretation

As a conceptual framing layer, Codexify can be read as coordinating:

- user-authored intent
- thread/project context
- retrieval scope
- model execution
- queue-backed work
- worker results
- diagnostic traces
- durable memory
- human approval

Under this framing, that coordination can be treated as organizational cognition in software form.

## Invariants

- No role may own identity absolutely.
- No role may bypass provenance.
- No role may silently widen retrieval scope.
- No role may convert acceptance into completion.
- No role may treat generated output as confirmed truth without proof or review.
- No role may mutate durable identity without explicit user consent.

## Useful Design Question

For any new Codexify feature, ask:

> Which cognitive role does this serve?

If the answer is unclear, the feature may be mixing responsibilities.
