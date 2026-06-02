# Architecture Map

This page is the reading map for the exported Developer Guide corpus.
It does not introduce new architecture truth. It explains how to read the guide set so current release truth stays ahead of background doctrine.

## How To Read This Corpus

Use the pages in this order when you need to understand the system:

1. `runtime-truth.md` for the current supported path.
2. `operator-truth.md` for the operator-facing proof surfaces and risks.
3. `runtime-topology.md` for the implemented component map.
4. `chat-runtime.md` for queue-backed completion semantics.
5. `data-and-storage.md` for durable state and lineage.
6. `config-and-ops.md` for health, provider governance, and operational posture.
7. `retrieval-and-context.md` for orchestration-level retrieval policy.
8. `workspace-surface.md`, `identity-and-personas.md`, and `canonical-tokens.md` for the UI and semantic doctrine that shape how the runtime is interpreted.
9. `extension-boundaries.md` and `pi-invocation-boundary.md` for governed extension seams.
10. `proof-and-validation.md` for what counts as evidence.
11. `decentralized-infrastructure.md` last, so future direction is always read through current truth.

## Source Layers

The exported guide is intentionally split across four kinds of pages:

- current-truth pages, which describe the supported runtime and release posture
- runtime pages, which summarize implemented components and flows
- UI and doctrine pages, which explain how workspace, identity, tokens, and retrieval are supposed to be interpreted
- boundary pages, which describe the contracts that keep extension and invocation paths bounded

That separation matters. A design document can explain intent without proving release support. A runtime page can describe a component without widening the supported promise.

## Truth Hierarchy

`docs/architecture/00-current-state.md` is the short-horizon truth anchor for release reality.
If it conflicts with older architecture notes, diagrams, or broader product language, `00-current-state.md` wins.

This guide inherits that rule. The exported pages are references, not license to widen support.

## Reading Boundaries

- Runtime docs answer what exists and how the supported path works.
- UI docs answer how surfaces should be interpreted and presented.
- Doctrine docs answer why repeated concepts must be treated consistently.
- Boundary docs answer where authority stops.

If a claim cannot be located in the current truth layer or in a directly supported source anchor, treat it as working theory rather than release truth.
