# Beta Release Sentinel — 2026-05-15

## Repo status
- Branch: `codex/p2-worktree-isolation-fixes`
- Head: `0fa121e8f0dae5b29bcf6b16696896c88782e2fd`
- Worktree clean: `False`
- ` M docs/architecture/codexify-platform-readiness-audit.md |  M scripts/audit_platform_readiness.py | ?? CHANGELOG.beta.md | ?? docs/audits/generated/2026-05-15-beta-sentinel.json | ?? docs/audits/generated/2026-05-15-beta-sentinel.md | ?? scripts/release/beta_release_sentinel.py | ?? tests/scripts/test_audit_platform_readiness_json.py | ?? tests/scripts/test_beta_release_sentinel.py`

## Current beta promise
- Local-first beta hardening.
- Supported path: local Docker Compose.
- Supported beta posture: local-only.
- Primary operator truth surfaces: `/health`, `/health/chat`, `/api/health/llm`, `/api/llm/catalog`.

## Release gates
- [checked] Supported-profile flags match the local-only beta contract. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] Fresh live evidence exists on the current `main` tip for the supported path. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [checked] Chat completion and upload -> embed -> readback are proven on the supported stack. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [warning] Coding results return through Guardian into the source thread without duplicate delivery. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [warning] Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [warning] No internal-only or quarantined surface is part of the release claim. — docs/architecture/00-current-state.md (Checklist item from current state.)
- [proven] Platform readiness audit execution — scripts/audit_platform_readiness.py (Audit script executed and returned JSON summary.)

## Evidence summary
- No new commit subjects found for this window.

## Changelog draft
- No new commit subjects found for this window.

## Blockers
- Coding results return through Guardian into the source thread without duplicate delivery.
- Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review.
- No internal-only or quarantined surface is part of the release claim.

## Warnings
- Core Loop Integrity: Architecture docs still flag chat-loop dependency coupling
- Primitive Stability: Repo-local docs warn about contract drift in tool primitives
- Extension Boundary: Architecture docs describe command bus, cron, and coding-agent seams
- Extension Boundary: Legacy /tools compatibility route status
- Observability: Observability docs leave some logging guarantees unverified
- Durability & Recovery: Roadmap docs warn that sync delivery is not yet durable
- Durability & Recovery: Risk register warns about Redis persistence or replay gaps
- Alternate Surface Readiness: Repo-local docs still describe shell-level coupling
- Federation Readiness: Roadmap docs warn that sync subscriptions are process-local
- Federation Readiness: Risk register warns that federation remains security- and config-sensitive
- Governance Readiness: Ownership authority is still informal in the scanned docs

## Not promised / excluded surfaces
- cloud-provider beta support
- public multi-user deployment
- federation durability
- graph-write release expansion
- unsupported provider paths

## Recommended next actions
- Re-run sentinel after runtime changes on current tip.
- Keep supported-profile contract and health/catalog surfaces aligned.
- Treat this artifact as evidence, not release approval.

## Machine-readable JSON artifact path
- `docs/audits/generated/2026-05-15-beta-sentinel.json`
