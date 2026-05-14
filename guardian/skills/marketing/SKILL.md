# Marketing Skill (Codexify V1)

## Intent

Transform canonical Codexify progress artifacts into draft marketing assets for Local-First AI Builders.

## Non-Negotiables

- Draft-only output (`approval_state = draft`)
- No-evidence, no-claim
- No release-readiness inflation
- No collapsing desktop and Docker-supported paths into one claim
- Claim suitability pass before any channel/ad rendering
- Presentation-role pass before any channel/ad rendering
- No blocker/failure/task-log lines in channel copy
- No raw implementation breadcrumbs in channel/ad/infographic copy

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
  - `presentation_role`: non-null string
  - `copy_ready`: non-null boolean
  - `risk_flags`: non-null array (empty list must serialize as `[]`)

Presentation inspection rule:
- `evidence-backed` means the item has source paths and can be audited.
- `marketable` means the item may support external-facing artifacts.
- `public-copy-ready` means the item may appear verbatim in visible public prose.
- Treat non-copy-ready items as evidence anchors, not public language.

## Validation Gates

1. Every claim must include evidence paths.
2. Every claim must include a proof tier.
3. Only `marketable_claim` items with `presentation_role = public_copy_seed` and `copy_ready = true` may flow into website/social/community/ad sections as visible prose.
4. `risk_or_blocker`, `task_instruction`, and `metadata_reference` entries must route to review notes and risk flags.
5. Every `claims[]` item must expose `candidate_class`, `channel_eligible`, `presentation_role`, `copy_ready`, and `risk_flags`.
6. Banned phrasing/overclaim checks must pass.
7. Approval state must remain `draft`.

## Templates

Templates for output rendering live in `guardian/skills/marketing/templates/`.
