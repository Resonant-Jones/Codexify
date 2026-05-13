# Infographic Spec: CAMPAIGN_2026_05_11_MARKETING_V1

## Purpose

Show how Codexify maps campaign receipts, runtime truth, and operator governance into a coherent reliability narrative.

## Audience

Local-First AI Builders

## Required Data Points

- [implemented] **Depends on**: ADR-020 (Guardian Mediated Coding Agent Execution Contract)
- [implemented] 3. Wire into existing Guardian queue infrastructure
- [implemented] ADR-020 defines Guardian as identity/persistence owner
- [verified] Codex Runner provides campaign/audit infrastructure
- [implemented] docs/architecture/ - ADR for integration contract
- [implemented] Existing queue: Redis-backed with task events via SSE

## Visual Narrative Arc

Problem ambiguity -> boundary contracts -> evidence-linked claims -> operator confidence

## Prompt Pack

### Prompt A (Diagram-first)

Create a technical infographic for Local-First AI Builders. Show a left-to-right flow: campaign receipts, current-state truth, dev-log context, and draft marketing outputs. Use restrained engineering visuals and explicit proof-tier labels.

### Prompt B (Operator-first)

Design an operator-facing infographic that emphasizes local-first reliability, identity boundaries, and failure visibility. Include badges for implemented, verified, and live-proven claims. Avoid hype language.

## Governance

- approval_state: `draft`
- render_mode: `spec-and-prompt-only`
