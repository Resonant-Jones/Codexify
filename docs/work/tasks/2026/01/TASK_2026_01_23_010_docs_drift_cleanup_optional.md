# TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL: Optional docs drift cleanup based on audit

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Optionally correct documentation claims identified in the audit (WebSocket scope, fine-tuning, RBAC, plugin marketplace) to reflect reality and/or clearly label as roadmap.

### Expected Output
- README/docs distinguish implemented vs roadmap clearly (matching audit).
- No code changes.

## Allowed Files
- README.md
- docs/**/*.md (ONLY docs drift corrections)
- docs/work/tasks/2026/01/TASK_2026_01_23_010_docs_drift_cleanup_optional.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "RBAC|fine-tuning|marketplace|WebSocket|real-time" README.md docs || true
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL: align docs with implementation
- Commit B: TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL: finalize task summary

## Summary
- Clarified README roadmap items to scope WebSocket collaboration and label roadmap-only features.
- Updated system spec planned features to reflect limited WebSocket coverage without a completion checkmark.

## Checks Run
- `rg -n "RBAC|fine-tuning|marketplace|WebSocket|real-time" README.md docs || true`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows this task artifact + campaign mapping pending record finalize hash commit.

## Commits
- Commit A (implementation): `69c751e1`
- Commit B (finalize docs): `c9435700`

## Mapping
- TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL -> [69c751e1, c9435700]
