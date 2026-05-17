# Codexify Agentic Task Orchestration Spec

## Working Name

**Execution Ledger**

A durable, repo-aware task orchestration layer for AI-assisted software development. It converts human intent into bounded, reviewable, executable artifacts that agents can safely consume, update, verify, and complete.

---

## 1. Purpose

The purpose of this system is to prevent agent drift, context-window exhaustion, scope bleed, and undocumented implementation decisions by moving task cognition out of transient chat context and into durable project artifacts.

The core principle:

> Move cognition from transient context windows into durable, reviewable, executable artifacts.

This system treats every meaningful unit of agent work as a structured execution contract, not as a loose prompt.

---

## 2. Conceptual Alignment

This workflow is conceptually aligned with Backlog.md’s model of storing atomic markdown tasks in the repository, exposing task workflows through MCP, and using review checkpoints before code execution.

The Codexify version extends that pattern into a broader stack-level architecture:

- Local-first task artifacts
- Agent-readable execution contracts
- Persona-aware agent assignment
- Acceptance criteria as semantic constraints
- Git-aware rollback and auditability
- Optional graph indexing
- Optional MCP/CLI/API access
- Long-term memory linkage through IDDB / GraphWrag

---

## 3. Design Goals

### Primary Goals

1. **Constrain agent work into bounded units**
   - Prevent agents from implementing too much at once.
   - Keep each task small enough to fit inside model context.

2. **Make intent reviewable before execution**
   - Agents must prove they understand the task before writing code.

3. **Make plans reviewable before mutation**
   - Agents must produce an implementation plan before editing files.

4. **Make completion verifiable**
   - Tasks are only complete when acceptance criteria and definition of done are satisfied.

5. **Preserve durable cognitive state**
   - Task history, plans, implementation notes, reviews, and completion records persist outside chat.

6. **Support multiple agent runtimes**
   - Claude Code, OpenAI Codex, Gemini, local agents, MCP tools, CLI tools, or future Codexify-native agents.

---

## 4. Non-Goals

This system does not attempt to:

- Replace Git.
- Replace project management tools entirely.
- Grant agents unrestricted repo authority.
- Treat chat history as the canonical source of truth.
- Store private identity/persona state inside public task artifacts unless explicitly authorized.
- Collapse all project memory into one global context blob.

---

## 5. Core Architecture

```txt
Human Intent
  ↓
Intent Capture
  ↓
Execution Contract Artifact
  ↓
Review Gate 1: Intent / Scope Validation
  ↓
Implementation Plan Artifact
  ↓
Review Gate 2: Architecture / Blast Radius Validation
  ↓
Agent Execution
  ↓
Verification + Tests
  ↓
Review Gate 3: Completion Validation
  ↓
Task Closure + Memory / Graph Indexing
```

---

## 6. Artifact Storage

### Recommended Directory Structure

```txt
.codexify/
  tasks/
    todo/
    in_progress/
    blocked/
    review/
    done/
  plans/
  reviews/
  execution-logs/
  agent-notes/
  definitions/
    done.md
    workflow.md
    task-schema.md
    agent-guide.md
```

Alternative repo-root structure:

```txt
backlog/
  tasks/
  plans/
  logs/
  reviews/
```

The `.codexify/` namespace is preferred for Codexify-native integration because it can later hold graph metadata, persona permissions, embeddings, and runtime adapters without polluting the project root.

---

## 7. Task State Machine

### Valid States

```txt
draft
ready
in_progress
blocked
needs_review
changes_requested
done
archived
```

### State Semantics

| State | Meaning |
|---|---|
| `draft` | Task exists but is not ready for agent execution. |
| `ready` | Task has passed intent/scope review and can be planned. |
| `in_progress` | Agent or human is actively implementing it. |
| `blocked` | Cannot proceed due to missing dependency, decision, or external constraint. |
| `needs_review` | Work is complete enough for human or automated review. |
| `changes_requested` | Review failed and the agent must revise. |
| `done` | Acceptance criteria and definition of done are satisfied. |
| `archived` | Task is no longer active but preserved for history. |

---

## 8. Execution Contract Schema

Each task is a Markdown file with YAML front matter.

### Filename Convention

```txt
TASK-{id}-{slug}.md
```

Example:

```txt
TASK-0316-terminal-kanban-move-mode.md
```

### Markdown Schema

```md
---
id: TASK-0316
title: Terminal Kanban Move Mode
status: ready
priority: medium
created_at: 2026-05-15T00:00:00Z
updated_at: 2026-05-15T00:00:00Z
created_by: human
assigned_agent: null
persona_scope: engineering
repo: codexify
branch: null
labels:
  - frontend
  - terminal-ui
  - agent-task
risk_level: medium
blast_radius:
  - src/ui/kanban
  - src/tasks
related_files: []
dependencies: []
blocked_by: []
review_gates:
  intent_review: pending
  plan_review: pending
  completion_review: pending
memory_links: []
graph_nodes: []
---

# Summary

Short, human-readable description of the task.

# Purpose

Why this task exists. What user/system problem it solves.

# Scope

## In Scope

- Explicitly allowed changes.

## Out of Scope

- Explicitly forbidden or deferred changes.

# Acceptance Criteria

- [ ] Criterion 1 is specific and testable.
- [ ] Criterion 2 is specific and testable.
- [ ] Criterion 3 is specific and testable.

# Definition of Done

- [ ] Code compiles.
- [ ] Relevant tests pass.
- [ ] No unrelated files changed.
- [ ] Implementation notes are written.
- [ ] Acceptance criteria are checked.

# Implementation Notes

Reserved for agent or human notes after execution.

# Review Notes

Reserved for human review comments.

# Completion Record

Reserved for final completion summary.
```

---

## 9. Implementation Plan Schema

Before editing files, the agent must generate a plan artifact.

### Plan File Convention

```txt
.codexify/plans/TASK-0316-plan.md
```

### Plan Schema

```md
---
task_id: TASK-0316
created_at: 2026-05-15T00:00:00Z
created_by: agent
agent_runtime: codex | claude | gemini | local
status: pending_review
risk_level: medium
estimated_blast_radius:
  - file/path/example.ts
---

# Task Understanding

The agent restates the task purpose in its own words.

# Proposed Approach

Step-by-step implementation strategy.

# Files Expected to Change

| File | Expected Change | Risk |
|---|---|---|
| `path/to/file.ts` | Add behavior | Medium |

# Files Expected to Read

- `path/to/context/file.ts`

# Dependencies / Unknowns

- Any missing decisions, unclear requirements, or external dependencies.

# Test Plan

- Tests to run.
- Manual checks to perform.

# Rollback Plan

How to revert safely if the implementation fails.

# Out-of-Scope Confirmation

Explicit statement of what the agent will not touch.
```

---

## 10. Review Gates

### Gate 1: Intent Review

Occurs after task creation and before implementation planning.

The reviewer checks:

- Does the task correctly capture intent?
- Are acceptance criteria testable?
- Is the scope small enough?
- Are out-of-scope boundaries clear?
- Is the blast radius acceptable?

Pass condition:

```txt
review_gates.intent_review = approved
status = ready
```

---

### Gate 2: Plan Review

Occurs after implementation plan generation and before code mutation.

The reviewer checks:

- Is the agent touching the right files?
- Is the plan technically sane?
- Are risks identified?
- Are tests appropriate?
- Is rollback possible?
- Is the agent avoiding scope creep?

Pass condition:

```txt
review_gates.plan_review = approved
status = in_progress
```

---

### Gate 3: Completion Review

Occurs after implementation and test execution.

The reviewer checks:

- Were all acceptance criteria met?
- Did tests pass?
- Were implementation notes recorded?
- Were unrelated changes avoided?
- Should the result be indexed into memory / graph?

Pass condition:

```txt
review_gates.completion_review = approved
status = done
```

---

## 11. Agent Runtime Rules

Agents must follow these rules when operating on tasks.

### Required Agent Behavior

1. Search existing tasks before creating a new one.
2. Read workflow guidance before modifying task state.
3. Never begin implementation without a task artifact.
4. Never edit code before producing an implementation plan.
5. Never mark a task done unless acceptance criteria are checked.
6. Record implementation notes after code changes.
7. Record unresolved questions in the task artifact.
8. Avoid modifying files outside declared blast radius unless explicitly approved.
9. Preserve user identity/persona boundaries.
10. Do not write private memory into repo artifacts unless explicitly allowed.

---

## 12. MCP Resource Design

Expose the following resources to agents via MCP.

### Resource: `codexify://workflow/overview`

Explains:

- What Execution Ledger is.
- How tasks move through states.
- Which resources/tools are available.

### Resource: `codexify://workflow/create-task`

Explains:

- How to convert human intent into a task.
- Required fields.
- How to define acceptance criteria.
- How to identify scope boundaries.

### Resource: `codexify://workflow/plan-task`

Explains:

- How to inspect the repo.
- How to produce an implementation plan.
- How to estimate blast radius.
- How to define a test plan.

### Resource: `codexify://workflow/execute-task`

Explains:

- How to begin work.
- How to update status.
- How to stay within scope.
- How to record implementation notes.

### Resource: `codexify://workflow/complete-task`

Explains:

- How to validate acceptance criteria.
- How to run tests.
- How to produce completion summaries.
- How to request final review.

---

## 13. MCP Tool Design

Expose these tools to agents.

```txt
search_tasks(query, filters)
read_task(task_id)
create_task(task_payload)
update_task(task_id, patch)
move_task(task_id, status)
create_plan(task_id, plan_payload)
read_plan(task_id)
approve_gate(task_id, gate_name, reviewer)
request_changes(task_id, reason)
append_execution_log(task_id, log_entry)
complete_task(task_id, completion_payload)
```

Optional tools:

```txt
link_memory(task_id, memory_id)
link_graph_node(task_id, node_id)
get_related_context(task_id)
validate_acceptance_criteria(task_id)
check_blast_radius(task_id, git_diff)
```

---

## 14. CLI Design

Recommended CLI commands:

```bash
codexify task list
codexify task show TASK-0316
codexify task create
codexify task plan TASK-0316
codexify task start TASK-0316
codexify task block TASK-0316
codexify task review TASK-0316
codexify task done TASK-0316
codexify task move TASK-0316 ready
codexify task log TASK-0316 "Implemented keyboard move mode"
```

Review commands:

```bash
codexify gate approve TASK-0316 intent_review
codexify gate approve TASK-0316 plan_review
codexify gate approve TASK-0316 completion_review
codexify gate request-changes TASK-0316 plan_review
```

---

## 15. Git Integration

### Branch Convention

```txt
task/TASK-0316-terminal-kanban-move-mode
```

### Commit Convention

```txt
TASK-0316: implement terminal kanban move mode
```

### Pull Request Convention

PR body should include:

- Task link
- Acceptance criteria checklist
- Implementation summary
- Test results
- Known limitations
- Reviewer notes

---

## 16. Graph / Memory Integration

When a task is completed, Codexify may optionally index it into GraphWrag / IDDB.

### Suggested Nodes

```txt
Task
Feature
Decision
AcceptanceCriterion
ImplementationPlan
CodeChange
Review
Agent
Repository
Branch
Commit
```

### Suggested Edges

```txt
Task IMPLEMENTS Feature
Task HAS_CRITERION AcceptanceCriterion
Task HAS_PLAN ImplementationPlan
Task MODIFIED CodeChange
CodeChange TOUCHES File
Review APPROVED Task
Agent EXECUTED Task
Task PRODUCED Commit
Task RELATED_TO MemoryFragment
```

### Memory Policy

Only durable technical facts should be indexed by default.

Examples safe to index:

- Architecture decisions
- Implementation summaries
- File relationships
- Task outcomes
- Known limitations

Do not index:

- Private user reflections
- Persona identity fragments
- Sensitive credentials
- Temporary emotional context
- Unapproved personal memory

---

## 17. Blast Radius Controls

Each task must define expected blast radius.

The runtime should compare actual Git diff against declared blast radius.

### Validation Behavior

If changed files are outside the declared radius:

```txt
status = needs_review
completion_review = blocked
reason = undeclared_file_modification
```

Agent must explain:

- Why the extra file was touched.
- Whether it was necessary.
- Whether the scope should be amended.

---

## 18. Acceptance Criteria Validation

Each acceptance criterion should support one of these validation modes:

```txt
manual
unit_test
integration_test
snapshot_test
lint
typecheck
runtime_check
visual_check
```

Example:

```md
- [ ] User can press `M` to enter move mode.
  validation: manual,runtime_check

- [ ] Moving a task between columns updates its status metadata.
  validation: unit_test
```

---

## 19. Agent Assignment Model

Tasks may be assigned to humans or agents.

```yaml
assigned_agent:
  id: guardian-dev
  runtime: codex
  persona_scope: engineering
  permissions:
    can_read_repo: true
    can_write_repo: true
    can_modify_memory: false
    can_create_branch: true
    can_execute_tests: true
```

This keeps persona identity separate from execution authority.

Agents borrow role context. They do not own identity.

---

## 20. Failure Modes

### Common Failure Modes

| Failure | Mitigation |
|---|---|
| Agent misunderstands intent | Gate 1 catches it. |
| Agent chooses wrong architecture | Gate 2 catches it. |
| Agent edits too much | Blast radius validation catches it. |
| Agent marks incomplete work done | Acceptance criteria validation catches it. |
| Context window runs out | Atomic task size limits reduce it. |
| Task becomes stale | Updated task metadata and review status expose it. |
| Multiple agents conflict | Git branches and dependency metadata isolate work. |

---

## 21. Minimal MVP Implementation

### Phase 1: File-Based Ledger

Implement:

- `.codexify/tasks/`
- Markdown task schema
- Manual task creation
- Manual review gates
- Git branch convention
- Basic CLI commands

### Phase 2: Agent-Readable Workflow

Implement:

- `agent-guide.md`
- `workflow.md`
- Task creation prompt template
- Implementation plan template
- Definition of done template

### Phase 3: MCP Server

Implement:

- MCP resources
- MCP task tools
- Agent task search/read/create/update
- Plan creation
- Gate updates

### Phase 4: Codexify UI Integration

Implement:

- Task board view
- Task detail view
- Review gate controls
- Acceptance criteria checklist
- Agent execution log panel
- Git diff / blast radius display

### Phase 5: GraphWrag Integration

Implement:

- Task indexing
- Decision nodes
- Code-change nodes
- Retrieval by feature/task/file/persona

---

## 22. Minimal Agent Prompt

```txt
You are operating inside the Codexify Execution Ledger workflow.

Before doing any implementation work:
1. Read the task artifact.
2. Restate your understanding.
3. Identify scope and out-of-scope boundaries.
4. Produce an implementation plan.
5. Wait for plan approval before modifying code.

During implementation:
1. Stay within the declared blast radius.
2. Satisfy each acceptance criterion.
3. Run relevant tests.
4. Record implementation notes.

Before marking complete:
1. Verify every acceptance criterion.
2. Summarize changed files.
3. Report tests run and results.
4. Flag any unresolved risks.
```

---

## 23. Canonical Task Prompt Template

```txt
Create an Execution Ledger task for the following feature request.

Feature request:
{{human_request}}

Requirements:
- Convert this into a bounded task.
- Include a clear purpose.
- Define in-scope and out-of-scope boundaries.
- Create testable acceptance criteria.
- Estimate blast radius.
- Identify dependencies and unknowns.
- Do not begin implementation.
```

---

## 24. Canonical Plan Prompt Template

```txt
Create an implementation plan for {{task_id}} according to the Codexify Execution Ledger workflow.

Requirements:
- Read the task artifact.
- Inspect relevant code before planning.
- Restate task understanding.
- Identify files expected to change.
- Identify files expected to read.
- Define implementation steps.
- Define test plan.
- Define rollback plan.
- Confirm out-of-scope boundaries.
- Do not modify code yet.
```

---

## 25. Canonical Execution Prompt Template

```txt
Implement {{task_id}} according to the approved implementation plan.

Requirements:
- Stay within approved scope.
- Modify only files included in the approved blast radius unless absolutely necessary.
- If scope expansion is required, stop and request review.
- Satisfy every acceptance criterion.
- Run relevant tests.
- Update implementation notes.
- Move task to needs_review when complete.
```

---

## 26. Stack Integration Notes

### Codexify Desktop

Use this system as a project-local execution layer.

### Codexify Scout

Scout can read task state and provide summaries, reminders, or lightweight project awareness.

### ThreadPrint / IDDB

Task artifacts can become ThreadPrint-compatible records when exported or shared across agents.

### WhisperMesh

In multi-node scenarios, task artifacts can sync across nodes as signed operational messages.

### Persona System

Personas may provide lensing and tone, but task authority must remain permission-based.

---

## 27. Recommended First Deployable Slice

Build the smallest useful version:

```txt
.codexify/tasks/
.codexify/plans/
.codexify/definitions/workflow.md
.codexify/definitions/done.md
```

Then add:

```bash
codexify task create
codexify task plan
codexify task start
codexify task review
codexify task done
```

Then wire MCP.

The first version does not need a beautiful UI.

It needs to make agent work durable, reviewable, and bounded.

---

## 28. One-Line Summary

Execution Ledger turns AI coding from transient prompt-driven improvisation into durable, scoped, review-gated cognitive infrastructure.

---

# Appendix A: Codex Build Packet — Phase 1

## Purpose

This packet is the first implementation contract for Codex. It narrows the larger Execution Ledger architecture into a small, safe, repo-local vertical slice.

Codex should use the full spec as conceptual context, but **Phase 1 must only implement the file-based ledger foundation**.

The goal is not to build the whole orchestration system yet.

The goal is to create the durable substrate that future agents, CLI commands, MCP tools, UI panels, and graph integrations can build on.

---

## Phase 1 Objective

Implement a project-local, file-based task ledger under `.codexify/` that supports structured task artifacts, basic lifecycle state folders, definitions, and schema conventions.

Phase 1 should make it possible to:

1. Initialize the task ledger structure.
2. Create a structured task artifact.
3. List existing task artifacts.
4. Read/show a task artifact.
5. Move a task between lifecycle states.
6. Create an implementation plan artifact for a task.
7. Preserve workflow documentation for future agents.

---

## Hard Scope Boundary

### In Scope

- File/directory structure under `.codexify/`
- Markdown task schema with YAML front matter
- Basic task lifecycle states
- Minimal CLI or scriptable command surface, depending on existing repo conventions
- Task creation
- Task listing
- Task reading
- Task state movement
- Plan artifact creation
- Basic validation of required fields
- Lightweight tests if the repo has a test framework
- Workflow definition files for future agent usage

### Out of Scope

- No UI work
- No MCP server yet
- No GraphWrag / IDDB indexing yet
- No persona routing yet
- No provider/model routing changes
- No database persistence
- No background workers
- No cloud sync
- No auth or permissions layer
- No multi-agent scheduling
- No task dependency engine beyond simple metadata fields
- No automated code execution by tasks yet

If Codex believes any out-of-scope item is required, it must stop and explain why instead of implementing it.

---

## Preferred Directory Structure

Codex should create or support this structure:

```txt
.codexify/
  tasks/
    draft/
    ready/
    in_progress/
    blocked/
    needs_review/
    changes_requested/
    done/
    archived/
  plans/
  execution-logs/
  agent-notes/
  reviews/
  definitions/
    workflow.md
    done.md
    task-schema.md
    agent-guide.md
```

If the repo already has a better project-local convention, Codex may recommend adapting the path, but it should default to `.codexify/`.

---

## Required Task States

```txt
draft
ready
in_progress
blocked
needs_review
changes_requested
done
archived
```

A task’s canonical state should be represented both by:

1. Its folder location.
2. Its YAML front matter `status` field.

If these disagree, validation should report a mismatch.

---

## Task Artifact Format

Task files should use this naming convention:

```txt
TASK-{number}-{slug}.md
```

Example:

```txt
TASK-0001-create-file-based-ledger.md
```

The first implementation may use incrementing numeric IDs by scanning existing task files.

---

## Required Task Schema

Each task must be a Markdown file with YAML front matter.

```md
---
id: TASK-0001
title: Create File-Based Execution Ledger
status: draft
priority: medium
created_at: 2026-05-15T00:00:00Z
updated_at: 2026-05-15T00:00:00Z
created_by: human
assigned_agent: null
persona_scope: engineering
repo: null
branch: null
labels: []
risk_level: low
blast_radius: []
related_files: []
dependencies: []
blocked_by: []
review_gates:
  intent_review: pending
  plan_review: pending
  completion_review: pending
memory_links: []
graph_nodes: []
---

# Summary

Short summary of the task.

# Purpose

Why this task exists and what problem it solves.

# Scope

## In Scope

- Explicit allowed work.

## Out of Scope

- Explicit forbidden or deferred work.

# Acceptance Criteria

- [ ] Criterion 1 is specific and testable.

# Definition of Done

- [ ] Required validation passes.
- [ ] Relevant tests pass, if available.
- [ ] No unrelated files changed.
- [ ] Implementation notes are recorded.

# Implementation Notes

Reserved for agent or human implementation notes.

# Review Notes

Reserved for review feedback.

# Completion Record

Reserved for final completion summary.
```

---

## Plan Artifact Format

Implementation plans should be stored in:

```txt
.codexify/plans/TASK-0001-plan.md
```

Required plan schema:

```md
---
task_id: TASK-0001
created_at: 2026-05-15T00:00:00Z
created_by: agent
agent_runtime: codex
status: pending_review
risk_level: low
estimated_blast_radius: []
---

# Task Understanding

Restate the task in plain language.

# Proposed Approach

Step-by-step implementation plan.

# Files Expected to Change

| File | Expected Change | Risk |
|---|---|---|

# Files Expected to Read

- File paths or directories to inspect.

# Dependencies / Unknowns

- Missing information, assumptions, or questions.

# Test Plan

- Tests or validation commands to run.

# Rollback Plan

How to safely undo the work.

# Out-of-Scope Confirmation

What will intentionally not be touched.
```

---

## CLI / Command Surface Recommendation

Codex should inspect the repo before deciding whether this belongs in an existing CLI, package script, command module, or standalone script.

If no CLI exists, implement the thinnest practical command surface using the repo’s existing language and tooling.

Recommended commands:

```bash
codexify task init
codexify task create --title "Create File-Based Execution Ledger"
codexify task list
codexify task show TASK-0001
codexify task move TASK-0001 ready
codexify task plan TASK-0001
codexify task validate TASK-0001
```

If `codexify` is not already a CLI binary, Codex may implement an equivalent script command, for example:

```bash
npm run task:init
npm run task:create -- --title "Create File-Based Execution Ledger"
npm run task:list
```

The chosen command surface should match the current repo architecture.

---

## Required Definitions

Codex should create these definition files.

### `.codexify/definitions/workflow.md`

Should explain:

- What Execution Ledger is.
- The lifecycle states.
- How task artifacts are used.
- How plan artifacts are used.
- The three review gates.

### `.codexify/definitions/done.md`

Should define the default definition of done:

- Acceptance criteria checked.
- Relevant tests run.
- Changed files summarized.
- Implementation notes written.
- No unapproved scope expansion.

### `.codexify/definitions/task-schema.md`

Should document:

- Required front matter fields.
- Required Markdown sections.
- State/folder consistency rules.
- Naming convention.

### `.codexify/definitions/agent-guide.md`

Should instruct agents:

- Search/read tasks before acting.
- Do not implement before a plan exists.
- Do not exceed scope.
- Record implementation notes.
- Keep private/persona memory out of repo artifacts unless explicitly authorized.

---

## Validation Requirements

Phase 1 validation should check:

- Task file has YAML front matter.
- Required fields exist.
- `id` matches filename prefix.
- `status` is one of the allowed states.
- Task folder matches `status`.
- Required Markdown sections exist.
- Review gate fields exist.

Validation does not need to prove semantic correctness yet.

No LLM-based validation is required in Phase 1.

---

## Suggested Internal API

If the repo architecture supports internal modules, Codex should prefer a small library API over command-only logic.

Suggested functions:

```ts
initializeLedger(rootPath): void
createTask(input): TaskRecord
listTasks(filters?): TaskRecord[]
readTask(taskId): TaskRecord
moveTask(taskId, nextStatus): TaskRecord
createPlan(taskId, input?): PlanRecord
validateTask(taskId): ValidationResult
```

If the repo is not TypeScript, adapt the same shape to the project language.

---

## Definition of Done for Phase 1

Phase 1 is complete when:

- `.codexify/` structure can be initialized.
- A valid task artifact can be created.
- Existing tasks can be listed.
- A task can be shown/read by ID.
- A task can be moved between valid states.
- Moving a task updates both folder location and front matter status.
- A plan artifact can be created for a task.
- Task validation reports missing fields or state/folder mismatch.
- Definition files exist and explain workflow usage.
- Tests or manual validation steps are documented.
- No UI, MCP, graph, or persona-routing work was added.

---

## Codex Reconnaissance Prompt

Use this prompt first. Codex should not implement anything yet.

```txt
You are working inside my Codexify codebase.

I am designing a project-local agentic task orchestration layer called Execution Ledger.

Read the attached Execution Ledger spec and Appendix A: Codex Build Packet carefully.

Important:
- Do not implement anything yet.
- Do not create files yet.
- Do not modify code.
- First inspect the repository structure.
- Identify the smallest safe Phase 1 implementation.
- Prefer file-based storage under `.codexify/`.
- Avoid UI work for now.
- Avoid MCP, GraphWrag, IDDB, persona-routing, provider routing, background workers, and cloud sync for now.

Your output should include:

1. Repository observations
2. Proposed Phase 1 architecture
3. Exact files/directories to create
4. Existing files likely to modify
5. CLI/API design recommendation
6. Data schema recommendation
7. Risks and unknowns
8. Definition of done for Phase 1
9. Follow-up implementation prompt I can give you after review
```

---

## Codex Implementation Prompt

Use this only after reviewing and approving Codex’s repo-specific plan.

```txt
Implement Phase 1 of Execution Ledger according to the approved plan.

Constraints:
- Stay within the approved file list.
- Create or support the `.codexify/` task ledger structure.
- Add the task artifact schema.
- Add basic task lifecycle commands or scripts.
- Add task validation.
- Add plan artifact creation.
- Add tests if this repo has an existing test framework.
- Do not add UI.
- Do not add MCP.
- Do not add GraphWrag or IDDB integration.
- Do not add persona routing.
- Do not add provider/model routing changes.
- Do not add database persistence.
- Do not expand scope without stopping and explaining why.

When complete, report:

1. Changed files
2. New files/directories
3. Example usage
4. Tests or validation commands run
5. Any limitations
6. Recommended Phase 2
```

---

## Phase 2 Preview

Phase 2 should not begin until Phase 1 works.

Likely Phase 2 scope:

- Review gate commands
- Execution logs
- Task dependency metadata
- Git branch/commit conventions
- Blast radius validation against Git diff
- Better tests
- Optional Codexify UI discovery, but not full UI implementation yet

