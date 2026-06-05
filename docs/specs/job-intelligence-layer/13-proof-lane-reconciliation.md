# Proof Lane Reconciliation

- This is a docs-only reconciliation note.
- It records current branch state.
- It is not an implementation task.
- It does not restore missing files.
- It does not create runtime behavior.
- It does not define canonical schema, prompt execution, persistence, UI, transcription, consent, pricing, or dispatch behavior.

## Purpose

This document records the reconciled Job Intelligence Layer proof-helper state for the current checkout after the previously missing deterministic assembly seam was restored.

## Current Observed Branch State

| Path | Observed state | Meaning |
| --- | --- | --- |
| `docs/specs/job-intelligence-layer/prompts/extraction-v0.md` | `present` | The docs-local extraction prompt template exists in this checkout. |
| `scripts/job_intelligence/validate_fixture.py` | `present` | The deterministic fixture validator is available in this checkout. |
| `scripts/job_intelligence/run_fixture_proof.py` | `present` | The deterministic proof-report runner is available in this checkout. |
| `scripts/job_intelligence/assemble_fixture_draft.py` | `present` | The deterministic assembly helper is available in this checkout. |
| `tests/job_intelligence/test_validate_fixture.py` | `present` | The focused validator test is available in this checkout. |
| `tests/job_intelligence/test_run_fixture_proof.py` | `present` | The focused proof-runner test is available in this checkout. |
| `tests/job_intelligence/test_assemble_fixture_draft.py` | `present` | The focused deterministic-assembly test is available in this checkout. |
| `docs/specs/job-intelligence-layer/fixtures/plumbing-three-handle-drip/` | `present` | The docs-local synthetic fixture directory exists in this checkout. |

## Confirmed Boundaries

- Existing prompt template does not imply runtime prompt execution.
- Proof-helper scripts remain synthetic-only and docs-local.
- The proof-helper lane is now reconciled in this checkout.
- No extraction quality is proven by docs alone.
- No runtime surface is added by docs or fixtures.
- No release promise changes.

## Missing Proof-Helper Paths

No previously missing proof-helper paths remain in this checkout for the current synthetic fixture lane.

## Restoration Decision Boundary

A future task may choose one of two paths.

The remaining work is no longer about restoring missing proof-helper seams in this checkout.
Future tasks should focus on expanding proof depth without widening into runtime behavior.

## Recommended Next Task

- use the reconciled helper set to rerun deterministic synthetic proof
- keep future work scoped to validation depth, not runtime integration
- preserve synthetic-only and docs-local boundaries

The previously missing assembly helper seam is restored.

## Non-Goals

- no fixture edits
- no prompt edits
- no model call
- no runtime implementation
- no API route
- no persistence model
- no database migration
- no UI
- no transcription pipeline
- no consent policy
- no retention policy
- no pricing automation
- no dispatch automation
- no canonical JSON Schema
- no canonical runtime tokens
- no ADR update

## Open Questions

- Should proof helpers live under `scripts/job_intelligence/` or a different dev-only location?
- Should tests live under `tests/job_intelligence/` or a docs validation suite?
- Should the docs-local fixture set be expanded or revalidated before deeper proof work continues?
- What proof is required before the lane moves beyond docs-local validation?
