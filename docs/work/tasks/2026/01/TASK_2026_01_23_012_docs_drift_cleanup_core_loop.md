# TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP: Clean up docs drift for CORE LOOP

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/reference/operator/ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP.
- Create/update this task artifact under docs/work/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Clean up any remaining README/docs claims that conflict with actual CORE LOOP behavior. If any claim is uncertain, add a short “Roadmap / TBD” note rather than inventing implementation.

### Expected Output
- Docs accurately reflect current CORE LOOP behavior.
- Ambiguous or aspirational claims are marked as Roadmap/TBD.

## Allowed Files
- README.md
- docs/**/*.md
- docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/work/tasks/2026/01/TASK_2026_01_23_012_docs_drift_cleanup_core_loop.md

## Checks to Run
- rg -n "graph-backfill|backfill|neo4j|graph context" README.md docs -S
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP: clean docs drift
- Commit B: TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP: finalize task summary

## Summary
- Aligned MVP state map language to reflect optional/deferred Neo4j graph context for CORE LOOP.
- Marked graph-context references as Roadmap/TBD instead of implying default-on behavior.

## Checks Run
- `rg -n "graph-backfill|backfill|neo4j|graph context" README.md docs -S`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows docs/MVP_STATE_MAP.md, the task artifact, and the campaign file pending commits.

## Commits
- Commit A (implementation): `6eba9ec6`
- Commit B (finalize docs): `e8dfb08e`

## Mapping
- TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP -> [6eba9ec6, e8dfb08e]
