# Campaign Brief: CAMPAIGN_2026_05_11_MARKETING_V1

## Audience

Local-First AI Builders

## Positioning

Codexify is local-first AI operations infrastructure with explicit boundaries, evidence-linked claims, and human-governed release posture.

## Core Narrative

This draft campaign translates real campaign receipts and architecture truth into public-facing messaging for builders who prioritize reliability over hype.

## Claims (Evidence-Bound)

- [implemented] **Depends on**: ADR-020 (Guardian Mediated Coding Agent Execution Contract) (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] 1. Define the coding-task envelope schema (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] 3. Wire into existing Guardian queue infrastructure (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] ADR-020 defines Guardian as identity/persistence owner (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [verified] Codex Runner provides campaign/audit infrastructure (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] docs/architecture/ - ADR for integration contract (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] Existing queue: Redis-backed with task events via SSE (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] guardian/queue/ - Task definitions for delegation (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] 1. **Queue**: codexify:queue:coding-execution (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] 1dae1662d TASK-2026-05-01-003: Connect delegation to queue/worker system (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] 207c850ab TASK-2026-05-01-001_pi_adapter.md: Pi adapter skeleton (task file) (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] 7fdb0c63d TASK-2026-05-01-002: Wire adapter into agent orchestration routes (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] 9a280aead TASK-2026-05-01-004: Implement result ingestion and thread injection (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Full 9-target live rerun was executed (artifact section appended in docs/architecture/2026-05-05-coding-result-return-path-live-proof.md). (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Per ADR-020 contract: (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)

## Governance

- approval_state: `draft`
- mode: `human-approval-required`

## Review Checklist

- [ ] Evidence paths exist for every claim
- [ ] Proof tiers are not inflated
- [ ] Supported-path language is accurate and separated
- [ ] No banned overclaim phrasing

## Risk Flags

- blocked_run_risk
- failed_proof_risk
- missing_runtime_artifact_risk
- task_failure_risk
- unsupported_readiness_risk
