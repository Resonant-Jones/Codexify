# Beta Changelog

Evidence-led beta readiness changes only.

## 2026-05-13

### Evidence

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

### Blockers

- Coding results return through Guardian into the source thread without duplicate delivery.
- Workspace-local Obsidian retrieval has fresh current-tip proof that survives supersession review.
- No internal-only or quarantined surface is part of the release claim.

### Warnings

- Platform readiness audit did not return valid JSON.
- Worktree is dirty; release evidence should use a clean tree.

## 2026-05-15

### Evidence

- docs: update beta artifacts
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
- Document heartbeat review as safety gate before scheduling/publication
- Add heartbeat review script with Makefile target, tests, and docs
- Add heartbeat operator wrapper
- Add heartbeat Makefile target, pnpm script, and docs for orchestrator
- Add local heartbeat orchestrator
- Add shared symlink-aware write path guard primitive
- Verify supported profile catalog health alignment
- Align supported profile health and catalog truth
- Record supported profile catalog health drift proof
- Add Resonant Constructs daily insight generator
- Update current state after workspace Obsidian proof
- Repair workspace Obsidian retrieval injection
- Record workspace-local Obsidian retrieval proof attempt
- Fix migrator bcrypt import
- fix: handle data URLs in _encode_image_url_to_base64 for Ollama local path
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
- Add Flow Builder semantic step contract
- Add Flow Builder validation issue taxonomy
- Add VariableChip typed output contract
- Add FlowDraft schema proposal
- Add Flow Builder token domain inventory
- Add Flow Builder typed surface campaign

### Blockers

- None.

### Warnings

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
