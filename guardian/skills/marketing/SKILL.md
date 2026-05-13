# Marketing Skill (Codexify V1)

## Intent

Transform canonical Codexify progress artifacts into draft marketing assets for Local-First AI Builders.

## Non-Negotiables

- Draft-only output (`approval_state = draft`)
- No-evidence, no-claim
- No release-readiness inflation
- No collapsing desktop and Docker-supported paths into one claim
- Claim suitability pass before any channel/ad rendering
- No blocker/failure/task-log lines in channel copy

## Canonical Inputs (in precedence order)

1. `docs/Campaign/`
2. `docs/architecture/00-current-state.md` and release/beta truth docs
3. `docs/DEV_LOG/`

## Required Outputs

- Evidence ledger JSON
- Core brief
- Channel variants
- Ad copy set
- Infographic spec + prompt pack
- Review notes for non-marketable evidence

Evidence-ledger inspection rule:
- Use `claims[]` as the canonical audit list.
- `marketable_claims` and `non_marketable_claims` are convenience groupings derived from `claims[]`.
- Verify required item fields are non-null and correctly typed:
  - `candidate_class`: non-null string
  - `channel_eligible`: non-null boolean
  - `risk_flags`: non-null array (empty list must serialize as `[]`)

## Validation Gates

1. Every claim must include evidence paths.
2. Every claim must include a proof tier.
3. Only `marketable_claim` items may flow into website/social/community/ad sections.
4. `risk_or_blocker`, `task_instruction`, and `metadata_reference` entries must route to review notes and risk flags.
5. Every `claims[]` item must expose `candidate_class`, `channel_eligible`, and `risk_flags`.
6. Banned phrasing/overclaim checks must pass.
7. Approval state must remain `draft`.

## Templates

Templates for output rendering live in `guardian/skills/marketing/templates/`.
