# Claim Truth Contract (V1)

## Required Claim Fields

Every generated claim must include:

- `claim`: the statement itself
- `proof_tier`: `implemented` | `verified` | `live-proven`
- `evidence_paths`: one or more repo-relative source paths
- `status`: mirrors proof tier in V1
- `channel`: target output channel (`core`, `website`, `social`, `community`, `ads`, `infographic`)
- `approval_state`: always `draft` in V1

## No-Evidence, No-Claim Gate

Claims are invalid when:

- evidence list is empty
- evidence paths do not exist
- claim language contradicts known release-truth constraints

## Risk Flags

Generated outputs must carry risk flags when detected:

- `overclaim_risk`
- `unsupported_readiness_risk`
- `path_collapsing_risk`

## Review Checklist (Required)

Before external use:

1. Confirm every claim has evidence paths.
2. Confirm proof tier is not inflated.
3. Confirm supported-path language is not collapsed.
4. Confirm approval state remains `draft` until human sign-off.
