# Claim Truth Contract (V1)

## Required Claim Fields

Every generated `claims[]` item must include:

- `claim`: the statement itself
- `candidate_class`: `marketable_claim` | `internal_evidence` | `risk_or_blocker` | `task_instruction` | `metadata_reference`
- `channel_eligible`: boolean suitability gate (`true` only for `marketable_claim`)
- `risk_flags`: per-item risk flag list (empty list when none apply)
- `proof_tier`: `implemented` | `verified` | `live-proven`
- `evidence_paths`: one or more repo-relative source paths
- `status`: mirrors proof tier in V1
- `channel`: target output channel (`core`, `website`, `social`, `community`, `ads`, `infographic`)
- `approval_state`: always `draft` in V1

The ledger includes `schema_version: "marketing_evidence_ledger.v2"` for this normalized item-level shape.
`channel_eligible` must always be a JSON boolean (`true`/`false`), never `null`.
`risk_flags` must always be a JSON array, with empty state serialized as `[]`, never `null`.

## Canonical Audit View

`claims[]` is the canonical item-level audit surface.

- `marketable_claims` and `non_marketable_claims` are derived grouped views for convenience.
- `claim_summary` is a derived count projection.
- These grouped/projection fields must stay consistent with filtering `claims[]`.

## Claim Types (Suitability Layer)

Truth and marketing suitability are separate:

- `marketable_claim`: evidence-backed and eligible for external-facing draft copy.
- `internal_evidence`: evidence-backed, useful for operator context, not eligible for channel copy.
- `risk_or_blocker`: evidence-backed blocker/failure/readiness signal, must never be used in channel copy.
- `task_instruction`: evidence-backed task/process instruction, must never be used in channel copy.
- `metadata_reference`: evidence-backed pointer/reference (for example `Proof artifact: docs/...`), must never be used in channel copy.

An evidence-backed statement can still be non-marketable.

## No-Evidence, No-Claim Gate

Claims are invalid when:

- evidence list is empty
- evidence paths do not exist
- claim language contradicts known release-truth constraints

## Channel Copy Eligibility Rule

Only `marketable_claim` candidates may be consumed by:

- `core-brief.md` external-facing claims section
- `channel-website.md`
- `channel-social.md`
- `channel-community.md`
- `ad-copy.md`

Evidence-backed blocker/failure/task-log lines must be preserved for audit, but must not appear in public-facing channel copy.

## Risk Flags

Generated outputs must carry risk flags when detected:

- `overclaim_risk`
- `unsupported_readiness_risk`
- `path_collapsing_risk`
- `failed_proof_risk`
- `blocked_run_risk`
- `missing_runtime_artifact_risk`
- `task_failure_risk`

## Review Checklist (Required)

Before external use:

1. Confirm every claim has evidence paths.
2. Confirm proof tier is not inflated.
3. Confirm supported-path language is not collapsed.
4. Confirm approval state remains `draft` until human sign-off.
