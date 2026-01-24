# TASK-2026-01-23-009_NEO4J_DECISION_DOC: Decide Neo4j status and align docs

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-009_NEO4J_DECISION_DOC.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Make an explicit decision to defer Neo4j post-MVP and align README/docs with actual usage status.

### Expected Output
- README/docs no longer claim active Neo4j-powered context reasoning unless it exists.
- Decision is explicitly stated in docs.

## Allowed Files
- README.md
- docs/**/*.md
- docs/tasks/TASK_2026_01_23_009_neo4j_decision_doc.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Checks to Run
- rg -n "Neo4j|knowledge graph" README.md docs || true
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-009_NEO4J_DECISION_DOC: defer neo4j and align docs
- Commit B: TASK-2026-01-23-009_NEO4J_DECISION_DOC: finalize task summary

## Summary
- Documented Neo4j as optional/experimental and deferred for MVP context in README.
- Softened Neo4j language in docs/Codexify/README.md to reflect opt-in graph tests.

## Checks Run
- `rg -n "Neo4j|knowledge graph" README.md docs || true`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows task artifact + campaign mapping pending finalize commit.

## Commits
- Commit A (implementation): `d37d4788`
- Commit B (finalize docs): TBD

## Mapping
- TASK-2026-01-23-009_NEO4J_DECISION_DOC -> [d37d4788, ]
