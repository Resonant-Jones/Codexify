# Marketing Skill Contract (V1)

## Purpose

Generate draft-only marketing artifacts from canonical Codexify truth sources.

## Inputs

- campaign ID
- audience (`local-first-builders` in V1)
- channels (comma list)
- mode (`draft` only)
- source root (optional override for tests)

## Outputs

For each campaign run:

- evidence ledger (`evidence-ledger.json`)
- core brief (`core-brief.md`)
- channel variants (`channel-<name>.md`)
- ad concept set (`ad-copy.md`)
- infographic spec and prompt pack (`infographic-spec.md`)
- internal review notes (`review-notes.md`)
- run metadata (`run-metadata.json`)

## Evidence Ledger Contract

`evidence-ledger.json` must provide an auditable item-level `claims[]` list.

Every `claims[]` entry is required to include:

- `claim`
- `candidate_class`
- `channel_eligible`
- `risk_flags`
- `evidence_paths`
- `proof_tier`
- `status`
- `approval_state`

Grouped fields `marketable_claims` and `non_marketable_claims` are derived convenience views and must remain consistent with filtering `claims[]` by `channel_eligible`.

## Governance

- never publish-ready by default
- `approval_state` is always `draft`
- run history appends to `docs/Marketing/generated/history/run-history.jsonl`
- claim suitability pass is mandatory before draft rendering
- channel variants consume only `marketable_claim` entries
- non-marketable evidence (`risk_or_blocker`, `task_instruction`, `metadata_reference`, `internal_evidence`) must be preserved in review outputs and the evidence ledger

## Future Compatibility Seam

This skill is intentionally file-system and CLI driven in V1.
A future runtime agent can invoke the same contract by passing the same input bundle and expecting the same artifact schema.
