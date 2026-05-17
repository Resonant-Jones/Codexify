# Campaign Intelligence Source Map (Internal)

This map defines what the campaign intelligence system reads and how each source class is allowed to influence output.

Hard precedence rule:
Current truth and claim boundary docs override mood, philosophy, and campaign ambition.

## Product Truth Sources

Path examples:
- `docs/architecture/00-current-state.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/flows.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/*live-proof*.md`

What questions it answers:
- What is currently supported?
- What is local-first default versus optional or constrained?
- What behavior is implemented, verified, or live-proven?

How it should influence campaign output:
- Sets the outer boundary for all public-facing claims.
- Determines whether a claim is `safe`, `caution`, `future`, or `reject`.

What it must not override:
- Must not be replaced by aspirational messaging or visual preference.

## Marketing Doctrine Sources

Path examples:
- `docs/Marketing/README.md`
- `docs/Marketing/contracts/claim-truth-model.md`
- `docs/Marketing/contracts/automation-wrapper.md`
- `docs/Marketing/contracts/skill-contract.md`
- `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`
- `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`

What questions it answers:
- How are claims classified and gated?
- What is copy-eligible versus internal-only evidence?
- What run governance is required before publish?

How it should influence campaign output:
- Enforces suitability, proof-tier labeling, and draft-only governance.
- Blocks unsupported readiness language from leaving internal drafts.

What it must not override:
- Must not override product truth.
- Must not turn internal evidence into public claims without current-state support.

## Brand Surface Sources

Path examples:
- `docs/Marketing/brand/constitution.md`
- `docs/Marketing/messaging/pillars.md`
- `docs/Marketing/chatgpt-project-bundle/02-positioning-core.md`
- `docs/Marketing/chatgpt-project-bundle/10-language-bank.md`

What questions it answers:
- What tone and worldview should copy use?
- Which terms are approved versus banned?
- How should identity, governance, and failure visibility be framed?

How it should influence campaign output:
- Shapes voice, lexical choices, and framing.
- Improves coherence across website, social, ads, and educational content.

What it must not override:
- Must not escalate claim strength beyond evidence.
- Must not bypass caution and reject categories from the claim gate.

## Founder and Philosophy Sources

Path examples:
- `docs/Marketing/master-campaign-brief.md` (if present)
- `docs/Marketing/chatgpt-project-bundle/03-imagination-framework.md`
- `docs/Marketing/chatgpt-project-bundle/04-status-flip.md`
- `docs/Marketing/chatgpt-project-bundle/05-myth-map.md`
- `docs/Marketing/chatgpt-project-bundle/06-hidden-door-literacy.md`
- `docs/Marketing/chatgpt-project-bundle/07-ritual-design.md`
- `docs/Marketing/chatgpt-project-bundle/08-superpower-promise.md`

What questions it answers:
- What identity transformation are we inviting?
- Which positioning method fits this moment?
- Which education narrative is most useful now?

How it should influence campaign output:
- Selects campaign angle and narrative shape.
- Helps choose one primary method per packet.

What it must not override:
- Must not override current truth boundaries.
- Must not convert myth language into unsupported product promises.

## Market and Campaign Signal Sources

Path examples:
- `docs/Marketing/chatgpt-project-bundle/09-audience-map.md`
- `docs/Marketing/chatgpt-project-bundle/12-campaign-fragment-wall.md`
- `docs/Marketing/audience/local-first-ai-builders.md`
- `docs/Marketing/reviews/*.md`
- `docs/Website/dev-blog/generated/*.md`

What questions it answers:
- Which audience pain is highest-signal now?
- Which objections are recurring?
- Which channels and fragments are performing or failing?

How it should influence campaign output:
- Selects one audience target and one best channel.
- Prioritizes practical, audience-fit messaging over generic brand statements.

What it must not override:
- Must not override truth gating.
- Must not introduce claims that are only market-desired but not evidence-backed.

## Generated Audit Outputs

Path examples:
- `docs/Marketing/generated/CAMPAIGN_*/core-brief.md`
- `docs/Marketing/generated/CAMPAIGN_*/evidence-ledger.json`
- `docs/Marketing/generated/CAMPAIGN_*/review-notes.md`
- `docs/Marketing/generated/CAMPAIGN_*/run-metadata.json`
- `docs/Marketing/generated/history/run-history.jsonl`
- `docs/audits/latest.json`

What questions it answers:
- What changed since the previous campaign packet?
- Which claims were blocked, risky, or downgraded?
- Which proof assets are still missing?

How it should influence campaign output:
- Drives campaign pulse and "what changed" reporting.
- Identifies proof gaps before drafting public-facing assets.

What it must not override:
- Must not be treated as automatic publish approval.
- Must not override current truth and claim-boundary doctrine.
