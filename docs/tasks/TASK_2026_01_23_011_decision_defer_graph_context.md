# TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT: Defer graph context for core loop

## Task Prompt

### Context
Campaign: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP.

### Instructions
- Follow docs/Ops/Runner_Protocol.md exactly.
- Execute ONLY TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT.
- Create/update this task artifact under docs/tasks using underscore naming.
- Do not touch files outside the task's Allowed Files list.
- Run the required checks before committing.
- Commit in two phases using the specified commit messages (manual commits; index.lock workaround).

### Task Description
Make the CORE LOOP decision explicit:

Decision: Defer graph context (Neo4j) for CORE LOOP closure.
Outcome:
- Graph context remains disabled by default.
- UI/trace references remain accurate and do not imply graph is active unless enabled.
- Docs explicitly mark graph context as deferred/experimental.

### Expected Output
- Clear code + docs statement: graph context is deferred for CORE LOOP closure.
- No misleading "graph is active" implication in UI/trace unless flag is enabled.

## Allowed Files
- guardian/context/broker.py
- guardian/routes/chat.py (only if needed to align trace/flags)
- docs/reports/audit-mvp-codexify-2026-01-23.md (only if updating the audit is allowed; otherwise don’t touch)
- docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_011_decision_defer_graph_context.md
- README.md (optional; only if docs drift is real and small)

Note: The campaign text references `docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md`; using the actual file `docs/Campaign/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`.

## Checks to Run
- rg -n "graph|Neo4j|GUARDIAN_ENABLE_GRAPH_CONTEXT" guardian/context/broker.py guardian/routes/chat.py README.md -S
- git status --porcelain -uall

## Commit Mode
- Two-phase

## Commit Messages
- Commit A: TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT: defer graph context for core loop
- Commit B: TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT: finalize task summary

## Summary
- Clarified in code that graph context is opt-in and deferred for CORE LOOP by default.
- Updated README to state graph backfill runs only when Neo4j is enabled.
- Normalized Task 011 campaign path references to the canonical filename.

## Checks Run
- `rg -n "graph|Neo4j|GUARDIAN_ENABLE_GRAPH_CONTEXT" guardian/context/broker.py guardian/routes/chat.py README.md -S`
- `git status --porcelain -uall`

## Git Status
- `git status --porcelain -uall` shows README.md, guardian/context/broker.py, the task artifact, and the campaign file pending commits.

## Commits
- Commit A (implementation): `eae38a7d`
- Commit B (finalize docs): TBD

## Mapping
- TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT -> [eae38a7d, ]
