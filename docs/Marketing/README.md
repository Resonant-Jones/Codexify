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
- A claim suitability gate is mandatory: only `marketable_claim` items can flow into website/social/community/ad copy.
- A presentation-role gate is mandatory: only `public_copy_seed` items with `copy_ready: true` may appear verbatim in public-facing prose.
- Blocker/failure/task/reference evidence is preserved for audit in `review-notes.md` and classified in `evidence-ledger.json`.

Reviewer note: implementation breadcrumbs such as ADR fragments, task IDs, commit hashes, file paths, and queue names may support claims as evidence, but they should not appear verbatim in generated public-facing copy.

## Generator Command

Run the deterministic generator with:

```bash
./generate-marketing --campaign-id CAMPAIGN_YYYY_MM_DD --audience local-first-builders --channels website,social,community --mode draft
```

Run the automation wrapper (auto-derives campaign ID by date) with:

```bash
./run-marketing-automation --date 2026-05-12 --campaign-suffix MARKETING_V1 --audience local-first-builders --channels website,social,community --mode draft
```

## Structure

- `brand/`: Resonant Constructs worldview and claim constraints
- `audience/`: target personas and channel posture
- `messaging/`: pillars tied to proof-tiers and evidence
- `contracts/`: machine and operator-facing generation contracts
- `campaign-intelligence/`: reusable internal packet templates, source maps, claim gates, visual lanes, and engine prompts
- `generated/`: generated draft artifacts and append-only run history
