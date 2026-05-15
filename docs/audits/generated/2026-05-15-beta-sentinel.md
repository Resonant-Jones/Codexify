# Beta Release Sentinel — 2026-05-15

## Repo status
- Branch: `main`
- Head: `def1b12a4572a55602d6141ab6d0863508853a42`
- Worktree clean: `True`
- Worktree appears clean.

## Current beta promise
- Local-first beta hardening.
- Supported path: local Docker Compose.
- Supported beta posture: local-only.
- Primary operator truth surfaces: `/health`, `/health/chat`, `/api/health/llm`, `/api/llm/catalog`.

## Release gates
- `proven` Supported-profile flags match the local-only beta contract. — Checklist item from current state.
- `proven` Fresh live evidence exists on the current `main` tip for the supported path. — Checklist item from current state.
- `proven` Chat completion and upload -> embed -> readback are proven on the supported stack. — Checklist item from current state.
- `proven` Coding results return through Guardian into the source thread without duplicate delivery. — Checklist item from current state.
- `proven` Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review. — Checklist item from current state.
- `proven` No internal-only or quarantined surface is part of the release claim. — Checklist item from current state.
- `warning` Platform readiness audit execution — Platform readiness audit did not return valid JSON.

## Evidence summary
- Platform readiness audit did not return valid JSON.

## Changelog draft
- docs: add Codexify consulting capability audit
- Add deny-first external transport policy
- add imagination marketing KB bundle
- Run release candidate audit automation
- Document heartbeat outbox inspection
- Add missing test cases: strict, targets, expected files
- Handle invalid manifest JSON in outbox inspector
- Add heartbeat-outbox Makefile target with STRICT support and status rework
- Add heartbeat outbox inspector with Makefile target and tests
- Add heartbeat outbox inspector script
- Add heartbeat outbox inspector with draft generation fix
- Document heartbeat staging outbox in README
- Add heartbeat-stage Makefile target, pnpm script, and secret scan hardening
- Add heartbeat outbox staging script with content drafts
- Add heartbeat schedule manifest
- Document activation modes and publication-deferred guard in schedule manifest
- Add schedule manifest section to heartbeat docs
- Add schedule manifest validation tests
- Complete schedule manifest: inputs, publication targets, review gate STRICT
- Add heartbeat schedule manifest
- Document heartbeat review as safety gate before scheduling/publication
- Add heartbeat review script with Makefile target, tests, and docs
- Add heartbeat operator wrapper
- Add heartbeat Makefile target, pnpm script, and docs for orchestrator
- Add local heartbeat orchestrator
- Add shared symlink-aware write path guard primitive
- Add Flow Builder semantic step contract
- Verify supported profile catalog health alignment
- Add Flow Builder validation issue taxonomy
- Align supported profile health and catalog truth
- Record supported profile catalog health drift proof
- Add VariableChip typed output contract
- Add FlowDraft schema proposal
- Add Flow Builder token domain inventory
- Add Flow Builder typed surface campaign

## Blockers
- None currently listed.

## Warnings
- Platform readiness audit did not return valid JSON.

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
- `/Users/resonant_jones/.codex/worktrees/cd5b/Codexify/docs/audits/generated/2026-05-15-beta-sentinel.json`
