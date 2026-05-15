# CAMPAIGN_2026_05_11_MARKETING_V1 Review

## Verdict

Mechanically safe, but not yet publishable.

The campaign pipeline correctly preserves evidence, separates blocker/risk material, and keeps external-facing artifacts draft-only. However, the core brief still exposes implementation breadcrumbs as marketable claims. These are evidence-backed, but they need translation into human-facing product language before publication.

## Approve

- Positioning: "Codexify is local-first AI operations infrastructure with explicit boundaries, evidence-linked claims, and human-governed release posture."
- Core narrative direction: reliability over hype.
- Governance posture: draft, human approval required.
- Risk flags preserved and visible.

## Rewrite

These claims are true but too implementation-flavored:

- "**Depends on**: ADR-020 (Guardian Mediated Coding Agent Execution Contract)"
- "1. Define the coding-task envelope schema"
- "3. Wire into existing Guardian queue infrastructure"
- "docs/architecture/ - ADR for integration contract"
- "guardian/queue/ - Task definitions for delegation"
- "1. **Queue**: codexify:queue:coding-execution"
- task commit references such as `1dae1662d`, `207c850ab`, `7fdb0c63d`, `9a280aead`

Suggested translation direction:

- Instead of exposing ADR/task/file-path language, describe the product capability:
  - "Codexify routes coding-agent work through Guardian-owned task envelopes."
  - "Delegated execution is queue-backed rather than prompt-only."
  - "Work claims are tied to implementation receipts and reviewable evidence."
  - "The system separates task acceptance from proof of completion."

## Reject / Internal Only

Do not use raw implementation breadcrumbs directly in public copy.

Keep these as evidence anchors, not campaign prose:

- commit hashes
- task IDs
- internal queue names
- file paths
- ADR dependency fragments
- proof artifact path references

## Follow-up Recommendation

Patch the Marketing pipeline with a second editorial layer:

1. Keep `marketable_claim` as the safety/eligibility class.
2. Add a copy-readiness or presentation role:
   - `public_copy_seed`
   - `supporting_evidence`
   - `internal_anchor`
3. Public channel artifacts should use `public_copy_seed`.
4. `supporting_evidence` should remain available as proof, but not appear verbatim in prose.
