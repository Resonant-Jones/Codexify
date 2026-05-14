# Beta Release Sentinel — 2026-05-14

## Repo status
- Branch: `main`
- Head: `468c9290f83bd0b03978f5363138e99460999192`
- Worktree clean: `False`
- `A  docs/Heartbeat/generated/2026-05-14-heartbeat.md`
- `A  docs/ResonantConstructs/daily-insights/generated/2026-05-14.md`
- `A  docs/Website/dev-blog/generated/2026-05-14.md`
- `A  docs/audits/generated/2026-05-14-beta-sentinel.json`
- `A  docs/audits/generated/2026-05-14-beta-sentinel.md`

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
- Worktree is dirty; release evidence should use a clean tree.

## Changelog draft
- Add heartbeat Makefile target, pnpm script, and docs for orchestrator
- Add local heartbeat orchestrator
- Add Resonant Constructs daily insight generator
- Update current state after workspace Obsidian proof
- Repair workspace Obsidian retrieval injection
- Record workspace-local Obsidian retrieval proof attempt
- Fix migrator bcrypt import
- fix: handle data URLs in _encode_image_url_to_base64 for Ollama local path
- Add Resonant Constructs daily insight generator
- feat: /obsidian routing, upload Form params, and AGENTS.md
- Add Flow Builder typed surface ADR
- Add Flow Builder surface research application note
- fix: upload button visibility and external provider image routing
- Update current state after coding result live proof
- Add codex adapter kind to coding execution contracts
- Repair supported coding worker live path
- Record coding result return live proof attempt
- Add daily dev blog ingestion script
- clearing worktree for rebase
- marketing Campaign Run Test
- Refine Axis instructions for decentralized network work
- Revert unintended frontend and campaign file carryover
- Add stored coding agent session context artifact
- Add marketing CLI skill and fixture scaffolding
- Add marketing documentation and campaign artifacts
- Populate marketing ledger eligibility fields
- Isolate beta release sentinel changes

## Blockers
- None currently listed.

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
- `/Users/resonant_jones/.codex/worktrees/cd5b/Codexify/docs/audits/generated/2026-05-14-beta-sentinel.json`
