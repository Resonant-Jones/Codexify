# Marketing Knowledge Layer

This directory is the canonical marketing operating layer for Codexify.

It is explicitly downstream from product/runtime truth and campaign receipts.
Marketing artifacts generated from this layer are draft-only until human approval.

## Source-of-Truth Precedence

Claim truth must resolve in this strict order:

1. `docs/Campaign/` campaign files and linked task receipts
2. `docs/architecture/00-current-state.md` plus `docs/beta/` and release-truth artifacts
3. `docs/DEV_LOG/` narrative context

If a statement cannot be backed by the sources above, it must not appear as a claim.

## Proof Tier Vocabulary

Every claim must be tagged as exactly one of:

- `implemented`
- `verified`
- `live-proven`

## V1 Governance

- Output mode is `draft` only.
- Human approval is required before publish.
- Generated assets are derived outputs, not system truth.

## Generator Command

Run the deterministic generator with:

```bash
./generate-marketing --campaign-id CAMPAIGN_YYYY_MM_DD --audience local-first-builders --channels website,social,community --mode draft
```

## Structure

- `brand/`: Resonant Constructs worldview and claim constraints
- `audience/`: target personas and channel posture
- `messaging/`: pillars tied to proof-tiers and evidence
- `contracts/`: machine and operator-facing generation contracts
- `generated/`: generated draft artifacts and append-only run history
