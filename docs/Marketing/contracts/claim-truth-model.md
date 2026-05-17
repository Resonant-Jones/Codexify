# Claim Truth Contract (V1)

## Required Claim Fields

Every generated `claims[]` item must include:

- `claim`: the statement itself
- `candidate_class`: `marketable_claim` | `internal_evidence` | `risk_or_blocker` | `task_instruction` | `metadata_reference`
- `channel_eligible`: boolean suitability gate (`true` only for `marketable_claim`)
- `presentation_role`: `public_copy_seed` | `supporting_evidence` | `internal_anchor` | `risk_note` | `metadata_reference`
- `copy_ready`: boolean presentation gate (`true` only when the claim may appear verbatim in public-facing prose)
- `risk_flags`: per-item risk flag list (empty list when none apply)
- `proof_tier`: `implemented` | `verified` | `live-proven`
- `evidence_paths`: one or more repo-relative source paths
- `status`: mirrors proof tier in V1
- `channel`: target output channel (`core`, `website`, `social`, `community`, `ads`, `infographic`)
- `approval_state`: always `draft` in V1

The ledger includes `schema_version: "marketing_evidence_ledger.v2"` for this normalized item-level shape.
`channel_eligible` must always be a JSON boolean (`true`/`false`), never `null`.
`presentation_role` must always be a non-null string from the allowed role set.
`copy_ready` must always be a JSON boolean (`true`/`false`), never `null`.
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

## Presentation Layer

Suitability and presentation are separate:

- `candidate_class` answers whether the item is a marketable claim, internal evidence, risk/blocker evidence, task instruction, or metadata reference.
- `channel_eligible` answers whether the item may support external-facing artifacts.
- `presentation_role` answers how the item may be used in generated artifacts.
- `copy_ready` answers whether the item may appear verbatim in public-facing prose.

Allowed presentation roles:

- `public_copy_seed`: clean product-facing statement that may appear verbatim in public draft copy.
- `supporting_evidence`: evidence-backed implementation breadcrumb that may support public copy indirectly, but must not appear verbatim.
- `internal_anchor`: internal contract, task, ADR, or implementation anchor for audit and review use.
- `risk_note`: blocker/failure/readiness evidence for internal review only.
- `metadata_reference`: evidence pointer or path-like reference for audit only.

Evidence-backed implementation breadcrumbs may be channel-eligible as support without being copy-ready. Public-facing channel artifacts must not print non-copy-ready claims verbatim.

## No-Evidence, No-Claim Gate

Claims are invalid when:

- evidence list is empty
- evidence paths do not exist
- claim language contradicts known release-truth constraints

## Channel Copy Eligibility Rule

Only `marketable_claim` candidates with `presentation_role: "public_copy_seed"` and `copy_ready: true` may be consumed as visible prose by:

- `core-brief.md` external-facing claims section
- `channel-website.md`
- `channel-social.md`
- `channel-community.md`
- `ad-copy.md`

Evidence-backed blocker/failure/task-log lines must be preserved for audit, but must not appear in public-facing channel copy.
Evidence-backed implementation breadcrumbs such as commit hashes, task IDs, file paths, queue names, and ADR dependency fragments may remain in the ledger as evidence, but must not appear verbatim in public-facing channel copy.
Public rendered artifacts must consume filtered `public_copy_claims`, not raw `marketable_claims`.

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
4. Confirm public-facing prose only uses `public_copy_seed` items with `copy_ready: true`.
5. Confirm approval state remains `draft` until human sign-off.
