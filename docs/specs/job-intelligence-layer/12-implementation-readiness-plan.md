# Implementation Readiness Plan

This is a planning document.
It is not an implementation plan for production.
It is not executable.
It does not create prompt files, schema files, tests, fixtures, routes, UI, persistence, workers, or runtime behavior.
It defines the readiness boundary for a future first executable proof.

## Purpose

This document defines what must be true before Job Intelligence Layer moves from docs-only incubation to a first executable proof.

It defines:

- the smallest useful proof
- the implementation surfaces that should remain out of scope
- the safety and architecture boundaries that must be preserved
- the proof evidence future implementation must produce

## First Executable Proof Thesis

The first executable proof should validate only:

```text
synthetic source text
-> structured extraction output
-> Job Profile draft object
-> review packet
```

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

## Provider and Prompt Boundary

- no provider or model is chosen yet
- no actual prompt file exists yet
- first proof may begin with deterministic assembly before model extraction
- if an LLM is used later, prompt files and model-bound behavior must be introduced in a separate atomic task
- local-first supported posture must remain respected unless a separate architecture-impact task changes that posture

## Validation Strategy for Future Proof

### Shape validation

- required top-level fields exist
- output includes extraction result, draft object, review packet, and lineage reference

The first deterministic docs-local fixture validation harness now exists at `scripts/job_intelligence/validate_fixture.py`. It validates synthetic fixture shape and safety invariants only, does not call a model, does not create runtime behavior, does not validate extraction quality, does not prove production readiness, and keeps runtime, prompt, schema, persistence, review UI, transcription, consent, retention, pricing, and dispatch deferred.

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

- no code implementation
- no prompt files
- no JSON schema files
- no tests
- no fixtures
- no CLI script
- no API route
- no worker
- no database migration
- no persistence model
- no UI
- no transcription pipeline
- no consent policy
- no retention policy
- no pricing automation
- no dispatch automation
- no export and restore update
- no runtime token registry update
- no ADR update

## Open Questions

- Should the first executable proof be a CLI or pure backend helper?
- Should deterministic assembly come before model extraction?
- Should synthetic fixtures live under docs first or tests first?
- Should review packet output be JSON, Markdown, or both?
- Which fields are required for the first proof?
- What level of lineage proof is enough without persistence?
- What provider and model constraints are acceptable for a local-first proof?
- What future task should introduce actual prompt files?
- What proof justifies moving from docs-only planning to code?
