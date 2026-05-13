# Beta Release Sentinel — 2026-05-13

## Repo status
- Branch: `main`
- Head: `9ac50780cb2432d5a0b17911bcbaab1a80d41beb`
- Worktree clean: `False`
- `M  Makefile`
- `M  docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/tasks/TASK-007-run-ledger-inspection-surface.md`
- `A  docs/Marketing/README.md`
- `A  docs/Marketing/audience/local-first-ai-builders.md`
- `A  docs/Marketing/brand/constitution.md`
- `A  docs/Marketing/contracts/automation-wrapper.md`
- `A  docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/ad-copy.md`
- `AM docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/channel-community.md`
- `AM docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/channel-social.md`
- `AM docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/channel-website.md`
- `AM docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/core-brief.md`
- `AM docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/evidence-ledger.json`
- `AM docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/infographic-spec.md`
- `AM docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/run-metadata.json`
- `A  docs/Marketing/generated/history/README.md`
- ` M docs/Marketing/generated/history/run-history.jsonl`
- `A  docs/Marketing/messaging/pillars.md`
- `M  docs/architecture/00-current-state.md`
- `M  frontend/src/features/commandCenter/CommandCenterPage.tsx`
- `M  frontend/src/features/commandCenter/__tests__/CommandCenterPage.test.tsx`
- `M  frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx`
- `M  frontend/src/features/commandCenter/components/CommandCenterBottomDrawer.tsx`
- `M  frontend/src/features/commandCenter/components/CommandCenterShell.tsx`
- `M  frontend/src/features/commandCenter/components/CommandCenterUtilityRail.tsx`
- `M  frontend/src/features/commandCenter/components/__tests__/CodingWorkOrdersPanel.test.tsx`
- `M  frontend/src/features/commandCenter/components/__tests__/CommandCenterBottomDrawer.test.tsx`
- `M  frontend/src/features/commandCenter/components/__tests__/CommandCenterShell.test.tsx`
- `M  frontend/src/features/commandCenter/components/__tests__/CommandCenterUtilityRail.test.tsx`
- `A  generate-marketing`
- `M  guardian/db/migrations/versions/f2b3c4d5e6f9_add_user_password_hash.py`
- `A  guardian/skills/marketing/contract.json`
- `A  guardian/skills/marketing/templates/ad-copy.md`
- `A  guardian/skills/marketing/templates/channel-variant.md`
- `A  guardian/skills/marketing/templates/core-brief.md`
- `A  guardian/skills/marketing/templates/infographic.md`
- `M  package.json`
- `A  run-marketing-automation`
- `A  scripts/marketing/__init__.py`
- `A  scripts/marketing/generate_marketing.py`
- `A  scripts/marketing/run_marketing_automation.py`
- `A  skills/marketing-campaign`
- `A  tests/fixtures/marketing/source/docs/Campaign/CAMPAIGN_SAMPLE.md`
- `A  tests/fixtures/marketing/source/docs/DEV_LOG/Dev-Log-Sample.md`
- `AM tests/fixtures/marketing/source/docs/Marketing/generated/history/run-history.jsonl`
- `A  tests/fixtures/marketing/source/docs/architecture/00-current-state.md`
- `A  tests/fixtures/marketing/source/guardian/skills/marketing/contract.json`
- `A  tests/fixtures/marketing/source/guardian/skills/marketing/templates/ad-copy.md`
- `A  tests/fixtures/marketing/source/guardian/skills/marketing/templates/channel-variant.md`
- `A  tests/fixtures/marketing/source/guardian/skills/marketing/templates/core-brief.md`
- `A  tests/fixtures/marketing/source/guardian/skills/marketing/templates/infographic.md`
- `A  tests/fixtures/marketing/suitability/source/docs/Campaign/CAMPAIGN_SAMPLE.md`
- `A  tests/fixtures/marketing/suitability/source/docs/DEV_LOG/Dev-Log-Sample.md`
- `A  tests/fixtures/marketing/suitability/source/docs/Marketing/generated/history/run-history.jsonl`
- `A  tests/fixtures/marketing/suitability/source/docs/architecture/00-current-state.md`
- `A  tests/fixtures/marketing/suitability/source/guardian/skills/marketing/contract.json`
- `A  tests/fixtures/marketing/suitability/source/guardian/skills/marketing/templates/ad-copy.md`
- `A  tests/fixtures/marketing/suitability/source/guardian/skills/marketing/templates/channel-variant.md`
- `A  tests/fixtures/marketing/suitability/source/guardian/skills/marketing/templates/core-brief.md`
- `A  tests/fixtures/marketing/suitability/source/guardian/skills/marketing/templates/infographic.md`
- `A  tests/scripts/test_marketing_automation_wrapper.py`
- `?? docs/Marketing/generated/CAMPAIGN_2026_05_11_MARKETING_V1/review-notes.md`
- `?? docs/audits/README.md`
- `?? pi-session-2026-05-11T20-04-55-388Z_019e18a4-83dc-771d-9da1-191813f7047a.html`
- `?? scripts/release/beta_release_sentinel.py`
- `?? tests/scripts/test_beta_release_sentinel.py`

## Current beta promise
- Local-first beta hardening.
- Supported path: local Docker Compose.
- Supported beta posture: local-only.
- Primary operator truth surfaces: `/health`, `/health/chat`, `/api/health/llm`, `/api/llm/catalog`.

## Release gates
- `proven` Supported-profile flags match the local-only beta contract. — Checklist item from current state.
- `proven` Fresh live evidence exists on the current `main` tip for the supported path. — Checklist item from current state.
- `proven` Chat completion and upload -> embed -> readback are proven on the supported stack. — Checklist item from current state.
- `warning` Coding results return through Guardian into the source thread without duplicate delivery. — Checklist item from current state.
- `warning` Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review. — Checklist item from current state.
- `warning` No internal-only or quarantined surface is part of the release claim. — Checklist item from current state.
- `warning` Platform readiness audit execution — Platform readiness audit did not return valid JSON.

## Evidence summary
- Platform readiness audit did not return valid JSON.
- Worktree is dirty; release evidence should use a clean tree.

## Changelog draft
- Normalize marketing evidence ledger schema
- Repair coding result return and terminal run state
- Add daily marketing automation run artifacts for 2026-05-13
- docs: refresh weekly current-state override
- Add Runner supervision summary to Agent Command
- Add initial marketing campaign draft artifacts
- Add marketing automation wrapper command
- Add marketing claim suitability gate
- test(marketing): add fixture corpus, golden outputs, and pipeline coverage
- feat(marketing): add deterministic generator CLI and command wiring
- docs(marketing): add truth layer and reusable skill contracts
- Repair Command Center shell ergonomics
- Restore context directive and PI contract test coverage
- Repair Command Center shell blank screen
- alembic upgrade

## Blockers
- Coding results return through Guardian into the source thread without duplicate delivery.
- Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review.
- No internal-only or quarantined surface is part of the release claim.

## Warnings
- Platform readiness audit did not return valid JSON.
- Worktree is dirty; release evidence should use a clean tree.

## Not promised / excluded surfaces
- Cloud-provider beta support.
- Packaged desktop replacing local Compose as supported path.
- Command bus, delegation, federation, graph writes, or worker-control dispatch as public beta promise.
- External publication to email, Substack, or websites.

## Recommended next actions
- Re-run sentinel after runtime changes on current tip.
- Keep supported-profile contract and health/catalog surfaces aligned.
- Treat this artifact as evidence, not release approval.

## Machine-readable JSON artifact path
- `docs/audits/generated/2026-05-13-beta-sentinel.json`
