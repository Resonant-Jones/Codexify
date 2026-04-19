# Codexify Architecture Atlas

This document is the peer-facing entrypoint into the validated Codexify architecture corpus. It helps readers start in the right places, separate current truth from supporting material, and review the runtime and UI diagram packs without treating this atlas as a source of architecture truth.

## Audience

This document is for:

- engineers reviewing Codexify for the first time
- collaborators trying to understand current structure before making changes
- peers evaluating runtime shape versus UI architecture

## Reading order

1. [`/docs/architecture/00-current-state.md`](./00-current-state.md): Read first for the short-horizon operational truth that overrides broader docs when release reality is the question.
2. [`/docs/architecture/kb-validity-matrix.md`](./kb-validity-matrix.md): Use next to determine which docs are safe to trust as diagram inputs and which are supplementary or quarantined.
3. [`/docs/architecture/adr/adr-index.md`](adr/adr-index.md): Read next to understand why major architectural choices were made — including queue-backed completion acceptance, provider vs request state separation, message vs request identity, and retrieval policy as a control plane.
4. [`/docs/architecture/runtime-diagrams-v1.md`](./runtime-diagrams-v1.md): Review the runtime diagram pack after the truth, validity rules, and decision rationale are established.
5. [`/docs/architecture/ui-diagrams-v1.md`](./ui-diagrams-v1.md): Read the UI diagram pack after runtime so presentation architecture stays distinct from system topology.
6. [`/docs/architecture/system-overview.md`](./system-overview.md): Use this as the baseline narrative for current runtime components, boundaries, and critical paths.
7. [`/docs/architecture/flows.md`](./flows.md): Read next for trigger-to-output runtime behavior and operational sequencing.
8. [`/docs/architecture/data-and-storage.md`](./data-and-storage.md): Use this to understand durable state, storage roles, and persistence invariants.
9. [`/docs/architecture/config-and-ops.md`](./config-and-ops.md): Read this for supported run paths, config precedence, and operator-facing runtime constraints.
10. [`/docs/architecture/modules-and-ownership.md`](./modules-and-ownership.md): Use this to inspect subsystem seams, dependency edges, and ownership boundaries.
11. [`/docs/architecture/tech-debt-and-risks.md`](./tech-debt-and-risks.md): Finish with the current risk register so caveats are interpreted after the baseline architecture is clear.

## Current-truth model

- `00-current-state.md` is the short-horizon operational truth layer.
- The KB validity matrix decides what is safe to use as diagram source material.
- `runtime-diagrams-v1.md` and `ui-diagrams-v1.md` are scoped views over validated source sets, not replacements for the source docs.
- Roadmap documents, supplementary deep dives, and quarantined legacy docs must not be confused with current runtime truth.

## ADR lane

The ADR lane (`docs/architecture/adr/`) is the architectural decision layer of the Codexify corpus.

ADRs explain **why** major choices exist, specifically around:

- **Queue-backed completion acceptance** — why `acceptance_status=accepted` does not mean `completed=true` and how worker execution relates to request lifecycle
- **Provider/runtime vs request state separation** — why Codexify treats provider availability, model warmth, and request-level state as separate state machines
- **Message identity vs request identity** — why `message_id` and `request_id` refer to different entities and why that distinction matters for transcript integrity
- **Retrieval policy as a control plane** — why retrieval routing, source mode, and boundary labels are treated as a policy layer rather than a direct implementation detail
- **Imprint UI deprecation and identity ownership** — why durable user modeling belongs under Settings, Persona Studio owns authored profile composition, and heavy inspectors remain in Diagnostics

ADRs are part of the validated architecture corpus. They are not speculative planning docs, not code walkthroughs, and not excluded by the "what this atlas intentionally excludes" section.

Route readers to the ADR lane after establishing current truth and validity — before the diagram packs — so the rationale is clear before structural details are examined.

See [`adr-index.md`](adr/adr-index.md) for the full ADR graph and per-document reading order.

## Two-view model

**Runtime view** covers current system topology, storage, flows, and subsystem seams.

**UI view** covers token law, layout law, rendering law, and diagnostics-facing conceptual surfaces.

The runtime view explains how the system is structured and operates. The UI view explains how presentation-side architecture is constrained and interpreted. They are adjacent, but they are not interchangeable.

## What this atlas intentionally excludes

- legacy Threadspace / `guardian-backend_v2` material
- future-feature architecture
- speculative implementation details
- direct code walkthroughs
- backend observability deep dives that are not part of the baseline peer-facing pass

## Peer review checklist

- Am I reading a current-truth document or a conceptual one?
- Am I using the validity matrix before trusting a diagram?
- Am I mixing runtime and UI concerns?
- Am I relying on a quarantined legacy document?
- If a claim seems surprising, which source doc should I verify first?

## Next documents after the atlas

- **Current truth** (start here): [`00-current-state.md`](./00-current-state.md)
- **Validity and trust rules**: [`kb-validity-matrix.md`](./kb-validity-matrix.md)
- **Architectural decision rationale**: [`adr/adr-index.md`](adr/adr-index.md) — queue-backed acceptance, dual state machine model, message vs request identity, retrieval policy as control plane, imprint UI deprecation and identity ownership
- **Runtime structure**: [`system-overview.md`](./system-overview.md), [`flows.md`](./flows.md), [`config-and-ops.md`](./config-and-ops.md)
- **Storage and data**: [`data-and-storage.md`](./data-and-storage.md)
- **Ownership and seams**: [`modules-and-ownership.md`](./modules-and-ownership.md)
- **Risk and caveats**: [`tech-debt-and-risks.md`](./tech-debt-and-risks.md)
