# Implementation Readiness Plan

This is a planning document.
It is not an implementation plan for production.
It is not executable.
It does not create prompt files, schema files, tests, fixtures, routes, UI, persistence, workers, or runtime behavior.
It defines the readiness boundary for a future first executable proof.

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
- the deterministic docs-local fixture validator now exists at `scripts/job_intelligence/validate_fixture.py`
- the deterministic extraction-output validator now exists at `scripts/job_intelligence/validate_extraction_output.py`
- the deterministic proof-report runner now exists at `scripts/job_intelligence/run_fixture_proof.py`
- the deterministic assembly helper now exists at `scripts/job_intelligence/assemble_fixture_draft.py`

What remains not true:

- no runtime prompt registry exists for this lane
- no model call exists
- no automated prompt execution exists
- no canonical Job Intelligence schema exists
- no persistence model exists
- no review UI exists
- no real customer data is in scope

## Reconciliation Note

- the current checkout has the docs-local extraction prompt template
- the deterministic fixture validator validates synthetic fixture shape and safety invariants only
- the deterministic extraction-output validator is standard-library only and docs-local
- it validates shape and safety boundaries for extraction-shaped JSON artifacts
- it keeps automated prompt execution deferred
- the deterministic proof-report runner calls the fixture validator first
- it validates cross-artifact fixture consistency and emits a machine-readable proof report
- the deterministic assembly helper validates the docs-local fixture first
- it deterministically assembles Job Profile draft and review packet artifacts from the synthetic extraction fixture
- it compares generated artifacts against the docs-local expected artifacts
- it does not call a model
- it does not create runtime behavior
- it does not validate extraction quality
- it does not prove production readiness
- runtime, prompt registry, schema, persistence, review UI, transcription, consent, retention, pricing, and dispatch remain deferred

## First Proof Thesis

The first implementation-oriented proof should remain narrow:

```text
synthetic source text
-> structured extraction output
-> Job Profile draft object
-> review packet
```

That proof should demonstrate semantics, traceability, and human-review posture before any runtime wiring is proposed.

Constraints for that first proof:

- no real customer data
- no voice or transcription
- no production API
- no durable persistence
- no dispatcher UI
- no pricing or dispatch automation
- no customer-facing messaging

## Candidate Proof Interfaces

### CLI proof

- accepts a synthetic transcript text file
- emits Job Profile draft JSON and review packet JSON
- easiest to validate
- lowest UI and API blast radius

### Backend helper proof

- pure Python helper invoked by tests or dev script
- no route
- no persistence
- suitable for contract tests later

### Dev-only route proof

- accepts synthetic text through a protected dev endpoint
- higher blast radius
- should not be first unless there is a strong reason

Recommendation:

- prefer CLI proof or pure backend helper first
- defer dev-only route until the contract is stable

## Recommended First Proof Path

Recommended sequence for future tasks:

1. synthetic fixture document
2. pure extraction helper or CLI wrapper
3. deterministic validation of output shape
4. no persistence
5. no production route
6. no UI
7. no real transcription
8. review packet emitted as JSON or Markdown artifact

This is a recommendation for future tasks, not implementation in this task.
A docs-local synthetic fixture set now exists at `fixtures/plumbing-three-handle-drip/`. It is not executable, it is not under `tests/`, and it is intended to become source material for a future proof task.

## Minimal Inputs

Future proof inputs:

- synthetic transcript or message text
- optional operator notes
- optional known context:
  - business vertical
  - interaction type
  - source channel
  - existing customer id placeholder
  - existing site id placeholder

All values must be fake or synthetic.
No real names, phone numbers, addresses, or business names.

## Minimal Outputs

Future proof outputs:

- extraction result
- Job Profile draft
- review packet
- lineage reference
- validation report

Future proof outputs should show:

- raw description preserved
- stated facts separated from inferred fields
- unknowns preserved
- policy questions separated
- risk and safety flags factual
- review required
- no subjective customer labels

## Readiness Checklist Before Code

- baseline and scaffold docs exist
- draft Job Profile contract exists
- extraction-pass contract exists
- human-review gate contract exists
- lineage and revision contract exists
- MVP validation scenario exists
- prompt and pipeline planning contract exists
- first proof interface is selected
- synthetic-only fixture policy is accepted
- no persistence requirement is introduced
- no UI requirement is introduced
- no route requirement is introduced
- provider and model boundary remains explicit
- validation expectations are documented

## Prompt and Provider Boundary

The first docs-local extraction prompt template now exists at `prompts/extraction-v0.md`.

Boundary rules for the current lane:

- it remains manual-only and non-runtime
- automated prompt execution remains deferred
- provider and model selection remain deferred
- real customer data remains out of scope
- output remains illustrative until a separate proof task defines validation expectations

The current prompt file is a planning aid, not a runtime contract.

If an LLM is used later, prompt files and model-bound behavior must be introduced in a separate atomic task.
Local-first supported posture must remain respected unless a separate architecture-impact task changes that posture.

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
- use the docs-local extraction-output validator for extraction-shaped JSON shape and safety checks without executing prompts or registering runtime behavior

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

## Proof Evidence Required Later

Future implementation proof must include:

- command used to run the proof
- synthetic input path
- generated output path
- validation result
- confirmation that no real customer data was used
- confirmation that raw source text was preserved or referenced
- confirmation that review packet was generated
- confirmation that no persistence occurred unless explicitly introduced by a later task
- confirmation that no production route or UI was added unless explicitly introduced by a later task

## Architecture Boundaries for First Code Task

The first future code task should avoid:

- migrations
- database models
- production routes
- customer-facing UI
- transcription and audio
- external messaging
- pricing automation
- dispatch automation
- export and restore changes
- runtime token registry changes

The first future code task may consider one of:

- a pure helper module
- a local CLI script
- docs-local synthetic fixture
- contract test for deterministic assembly behavior

Actual file paths must be chosen in the future implementation task.

## Validation Strategy for Future Proof

### Shape validation

- required top-level fields exist
- output includes extraction result, draft object, review packet, and lineage reference

### Safety validation

- no subjective customer labels appear
- risk and safety notes remain factual and non-stigmatizing

### Reviewability validation

- low-confidence or unknown fields appear in the review packet
- generated versus inferred distinctions remain visible

### Lineage validation

- source interaction id or source reference exists
- draft output references extraction source

### Non-goal validation

- no persistence side effect occurs
- no production route or UI side effect occurs

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
- Should the first executable proof be a CLI or pure backend helper?
- Should deterministic assembly come before model extraction?
- Should synthetic fixtures live under docs first or tests first?
- Should review packet output be JSON, Markdown, or both?
- Which fields are required for the first proof?
- What level of lineage proof is enough without persistence?
- What proof justifies moving from docs-only planning to code?
