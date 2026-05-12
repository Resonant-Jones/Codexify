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
- run metadata (`run-metadata.json`)

## Governance

- never publish-ready by default
- `approval_state` is always `draft`
- run history appends to `docs/Marketing/generated/history/run-history.jsonl`

## Future Compatibility Seam

This skill is intentionally file-system and CLI driven in V1.
A future runtime agent can invoke the same contract by passing the same input bundle and expecting the same artifact schema.
