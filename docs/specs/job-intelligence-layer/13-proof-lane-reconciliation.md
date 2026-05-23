# Proof Lane Reconciliation

- This is a docs-only reconciliation note.
- It records current branch state.
- It is not an implementation task.
- It does not restore missing files.
- It does not create runtime behavior.
- It does not define canonical schema, prompt execution, persistence, UI, transcription, consent, pricing, or dispatch behavior.

## Purpose

This document reconciles the Job Intelligence Layer proof lane after discovering that some previously referenced synthetic proof-helper paths are missing from the current checkout while the docs-local extraction prompt template is already present.

## Current Observed Branch State

| Path | Observed state | Meaning |
| --- | --- | --- |
| `docs/specs/job-intelligence-layer/prompts/extraction-v0.md` | `present` | The docs-local extraction prompt template exists in this checkout. |
| `scripts/job_intelligence/validate_fixture.py` | `missing` | The previously referenced fixture validator is not available in this checkout. |
| `scripts/job_intelligence/run_fixture_proof.py` | `missing` | The previously referenced proof runner is not available in this checkout. |
| `scripts/job_intelligence/assemble_fixture_draft.py` | `missing` | The previously referenced deterministic assembly helper is not available in this checkout. |
| `tests/job_intelligence/test_validate_fixture.py` | `missing` | The previously referenced fixture-validator test is not available in this checkout. |
| `tests/job_intelligence/test_run_fixture_proof.py` | `missing` | The previously referenced proof-runner test is not available in this checkout. |
| `tests/job_intelligence/test_assemble_fixture_draft.py` | `missing` | The previously referenced deterministic-assembly test is not available in this checkout. |
| `docs/specs/job-intelligence-layer/fixtures/plumbing-three-handle-drip/` | `present` | The docs-local synthetic fixture directory exists in this checkout. |

## Confirmed Boundaries

- Existing prompt template does not imply runtime prompt execution.
- Missing proof-helper scripts do not invalidate the docs-only concept lane.
- Missing proof-helper scripts do mean proof-lane readiness is not complete in this checkout.
- No extraction quality is proven by docs alone.
- No runtime surface is added by docs or fixtures.
- No release promise changes.

## Missing Proof-Helper Paths

### Scripts

- `scripts/job_intelligence/validate_fixture.py`
- `scripts/job_intelligence/run_fixture_proof.py`
- `scripts/job_intelligence/assemble_fixture_draft.py`

### Tests

- `tests/job_intelligence/test_validate_fixture.py`
- `tests/job_intelligence/test_run_fixture_proof.py`
- `tests/job_intelligence/test_assemble_fixture_draft.py`

## Restoration Decision Boundary

A future task may choose one of two paths.

### Option A: Restore from known branch/history

Use this only if the missing files can be found in local git history, another branch, or a known patch source.

Requirements for a future restoration task:

- restore only the missing proof-helper files
- preserve their synthetic-only and docs-local boundary
- rerun all Job Intelligence proof validations
- commit restoration separately

### Option B: Recreate from current contracts

Use this only if no reliable prior implementation exists.

Requirements for a future recreation task:

- recreate the validator first
- then proof runner
- then deterministic assembly helper
- add tests with each helper
- avoid combining all proof helpers into one oversized task unless explicitly approved

## Recommended Next Task

- inspect git history and available branches for the missing proof-helper files
- if found, restore the smallest coherent missing proof-helper slice
- if not found, recreate the validator first as the first proof-helper slice

Restoration or recreation is deferred.
No files are restored by this reconciliation note.

## Non-Goals

- no script restoration
- no test restoration
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

- Did the missing proof helpers live on another branch?
- Were they intentionally omitted from this checkout?
- Should proof helpers live under `scripts/job_intelligence/` or a different dev-only location?
- Should tests live under `tests/job_intelligence/` or a docs validation suite?
- Should fixture validation be restored before prompt execution work continues?
- Should the docs-local fixture set be revalidated before any script restoration?
- What proof is required before the lane moves beyond docs-local validation?
