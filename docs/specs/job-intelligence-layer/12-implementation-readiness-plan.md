# Implementation Readiness Plan

This is a planning document.
It is not implemented.
It does not create runtime prompt execution, API behavior, worker behavior, persistence behavior, UI behavior, model behavior, or canonical schema behavior.
It does not widen the current Codexify release promise.

## Purpose

This document defines the smallest proof sequence that would justify moving the Job Intelligence Layer from docs-only incubation toward implementation planning.

The aim is to preserve a strict boundary between:

- synthetic experimentation
- planning contracts
- future proof work
- any later runtime integration

## Current Readiness

What is true now:

- the Job Intelligence Layer remains a docs-first incubation lane
- the planning contracts for extraction, review, lineage, and pipeline decomposition exist
- the first docs-local extraction prompt template now exists at `prompts/extraction-v0.md`
- that prompt remains manual-only, synthetic-only, and non-runtime

What remains not true:

- no runtime prompt registry exists for this lane
- no model call exists
- no automated prompt execution exists
- no canonical Job Intelligence schema exists
- no persistence model exists
- no review UI exists
- no real customer data is in scope

## First Proof Thesis

The first implementation-oriented proof should remain narrow:

```text
synthetic source text
-> structured extraction output
-> Job Profile draft object
-> review packet
```

That proof should demonstrate semantics, traceability, and human-review posture before any runtime wiring is proposed.

## Prompt and Provider Boundary

The first docs-local extraction prompt template now exists at `prompts/extraction-v0.md`.

Boundary rules for the current lane:

- it remains manual-only and non-runtime
- automated prompt execution remains deferred
- provider and model selection remain deferred
- real customer data remains out of scope
- output remains illustrative until a separate proof task defines validation expectations

The current prompt file is a planning aid, not a runtime contract.

## Recommended Proof Sequence

### Phase 0: Docs-local prompt and contract alignment

- keep the prompt template docs-local
- keep the fixture lane synthetic-only
- confirm the prompt preserves raw source text versus interpreted fields
- confirm human review remains required

### Phase 1: Deterministic proof harness

- prefer a CLI proof or pure backend helper before any dev-only route
- use synthetic inputs only
- fail closed on missing or contradictory input
- keep prompt output, normalization, draft assembly, and review packet boundaries inspectable

### Phase 2: Evaluation and reviewability proof

- compare synthetic outputs against explicit expectations
- prove ambiguity, missing information, and policy questions remain visible
- prove no pricing, scheduling, or dispatch commitments are invented
- prove subjective customer labels and sensitive-trait inference remain excluded

### Phase 3: Runtime consideration gate

- only after prior proof exists should runtime integration even be considered
- any runtime step must separately justify prompt registration, schema work, persistence, UI, and operator truth surfaces

## Readiness Gates

Implementation planning is not ready until all of the following are true:

- the synthetic fixture set is sufficient to stress extraction ambiguity
- a dedicated proof path exists for structured output validation
- draft assembly semantics are stable enough to compare across runs
- human-review requirements are explicit
- provider and model boundaries are justified against Codexify's local-first posture
- real-customer-data handling remains deferred until a separate policy task exists

## Non-Goals

- no runtime prompt registry
- no provider integration
- no automated prompt execution
- no API route
- no worker
- no persistence model
- no database migration
- no UI
- no transcription pipeline
- no consent or retention policy
- no pricing automation
- no dispatch automation
- no canonical JSON Schema
- no canonical runtime tokens

## Open Questions

- Should the first executable proof normalize prompt output before draft assembly?
- Should a future validator check prompt output directly or only check normalized artifacts?
- What synthetic fixture breadth is enough before considering anonymized real-world examples?
- Which provider or model boundary, if any, is acceptable for local-first experimentation?
- What proof threshold justifies automated prompt execution?
