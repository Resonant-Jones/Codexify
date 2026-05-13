# Campaign Brief: CAMPAIGN_2026_05_11_MARKETING_V1

## Audience

Local-First AI Builders

## Positioning

Codexify is local-first AI operations infrastructure with explicit boundaries, evidence-linked claims, and human-governed release posture.

## Core Narrative

This draft campaign translates real campaign receipts and architecture truth into public-facing messaging for builders who prioritize reliability over hype.

## Claims (Evidence-Bound)

- [implemented] **Depends on**: ADR-020 (Guardian Mediated Coding Agent Execution Contract) (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] 3. Wire into existing Guardian queue infrastructure (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] ADR-020 defines Guardian as identity/persistence owner (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [verified] Codex Runner provides campaign/audit infrastructure (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] docs/architecture/ - ADR for integration contract (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] Existing queue: Redis-backed with task events via SSE (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] guardian/queue/ - Task definitions for delegation (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`)
- [implemented] 1. **Queue**: codexify:queue:coding-execution (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] 1dae1662d TASK-2026-05-01-003: Connect delegation to queue/worker system (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Additional runtime drift was observed on docker-compose.runtime.yml exact run --rm checks: migrator failed with missing revision 9d4e1c7b2a6f, which blocked direct execution of the exact packaging probe commands. (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Current outcome remains **not release-ready**: (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Full 9-target live rerun was executed (artifact section appended in docs/architecture/2026-05-05-coding-result-return-path-live-proof.md). (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] No. The live run failed before a returned coding_result reached the source thread, so the coding-result return path is not release-ready. (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Overall result: Release-ready for this path: no (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Proof artifact: docs/architecture/2026-05-05-coding-result-return-path-live-proof.md (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Re-run the live Compose proof after that blocker is fixed. (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] Restore the missing worker runtime artifact or image layer that provides /app/codex_runner/src/agent-wrapper.js. (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] task.failed events are emitted, but agent_runs.status remains queued. (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] ✅ Guardian owns request identity (run_id, deployment_id) (`docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`)
- [implemented] 1. Guardian remains owner of request identity, policy, transcript lineage, worker events, and result receipts. (`docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/00-current-shape.md`)
- [implemented] 1. Worktree lease system (branch/worktree lifecycle contract is not yet runtime-owned). (`docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/00-current-shape.md`)
- [implemented] 2. Canonical token discipline must be preserved for statuses/events/contracts. (`docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/00-current-shape.md`)
- [verified] 2. Coding-worker validation can produce normalized evidence (status, exit code, fail signature, bounded output previews). (`docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/00-current-shape.md`)
- [implemented] 2. Commit-after-green gate (no enforced commit gate contract in worker runtime yet). (`docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/00-current-shape.md`)

## Governance

- approval_state: `draft`
- mode: `human-approval-required`

## Review Checklist

- [ ] Evidence paths exist for every claim
- [ ] Proof tiers are not inflated
- [ ] Supported-path language is accurate and separated
- [ ] No banned overclaim phrasing

## Risk Flags

- none
