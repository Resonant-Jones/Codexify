# Campaign Intelligence Layer (Internal)

`docs/Marketing/campaign-intelligence/` is Codexify's proof-aware marketing intelligence layer.

It reads live product truth, repository and audit signals, brand doctrine, and campaign fragments, then produces review-ready campaign packets.

This layer is internal operating infrastructure, not public copy.

## Internal Use Only

- Use for internal strategy, planning, and draft generation workflows.
- Treat all outputs as `draft` until human approval.
- Do not use this folder as a standalone truth source for external claims.

## Source Priority Order

Use sources in this order. Higher layers override lower layers.

1. Current truth and claim boundary gates:
   - `docs/architecture/00-current-state.md`
   - `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`
   - `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
2. Claim and automation contracts:
   - `docs/Marketing/contracts/claim-truth-model.md`
   - `docs/Marketing/contracts/automation-wrapper.md`
   - `docs/Marketing/contracts/skill-contract.md`
3. Positioning and campaign doctrine:
   - `docs/Marketing/chatgpt-project-bundle/02-positioning-core.md`
   - `docs/Marketing/chatgpt-project-bundle/03-imagination-framework.md`
   - `docs/Marketing/chatgpt-project-bundle/09-audience-map.md`
   - `docs/Marketing/chatgpt-project-bundle/10-language-bank.md`
   - `docs/Marketing/chatgpt-project-bundle/12-campaign-fragment-wall.md`
   - `docs/Marketing/messaging/pillars.md`
4. Brand and audience context:
   - `docs/Marketing/brand/constitution.md`
   - `docs/Marketing/audience/local-first-ai-builders.md`
5. Campaign and audit signal surfaces:
   - `docs/Marketing/generated/*/run-metadata.json`
   - `docs/Marketing/generated/*/evidence-ledger.json`
   - `docs/Marketing/generated/*/review-notes.md`
   - `docs/Marketing/generated/history/run-history.jsonl`
   - `docs/Campaign/`, `docs/audits/`, `docs/Website/` (when relevant to the run)

Hard rule: current truth and claim-boundary docs override mood, philosophy, and campaign ambition.

## Output Expectations

Every run should produce one completed packet using `campaign-packet-template.md` with:

- a clear "what changed and why now" pulse
- explicit source list with paths
- claim posture split into `Safe`, `Caution`, `Future-Facing`, and `Rejected / Do Not Say`
- one selected audience, one positioning method, and one visual lane
- concrete draft assets for review
- explicit proof assets still needed
- explicit do-not-say lines that block overclaim

## Relationship to `master-campaign-brief.md`

`docs/Marketing/master-campaign-brief.md` is the strategic narrative anchor.
This folder operationalizes that strategy into per-run packet generation rules.

If `master-campaign-brief.md` is missing in a checkout, do not invent replacement doctrine.
Flag the gap in packet `Source Inputs`, then fall back to existing positioning and claim-boundary docs.

## Relationship to `generated/` Campaign Folders

- `docs/Marketing/campaign-intelligence/` stores reusable operating doctrine and templates.
- `docs/Marketing/generated/CAMPAIGN_*/` stores run-specific outputs and evidence receipts.
- Generated outputs should cite this layer's rules, but this layer must not be rewritten per campaign run.
