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

* Local-first task artifacts
* Agent-readable execution contracts
* Persona-aware agent assignment
* Acceptance criteria as semantic constraints
* Git-aware rollback and auditability
* Optional graph indexing
* Optional MCP/CLI/API access
* Long-term memory linkage through IDDB / GraphWrag

---

## 3. Design Goals

### Primary Goals

1. **Constrain agent work into bounded units**

   * Prevent agents from implementing too much at once.
   * Keep each task small enough to fit inside model context.

2. **Make intent reviewable before execution**

   * Agents must prove they understand the task before writing code.

3. **Make plans reviewable before mutation**

   * Agents must produce an implementation plan before editing files.

4. **Make completion verifiable**

   * Tasks are only complete when acceptance criteria and definition of done are satisfied.

5. **Preserve durable cognitive state**

   * Task history, plans, implementation notes, reviews, and completion records persist outside chat.

6. **Support multiple agent runtimes**

   * Claude Code, OpenAI Codex, Gemini, local agents, MCP tools, CLI tools, or future Codexify-native agents.

---

## 4. Non-Goals

This system does not attempt to:

* Replace Git.
* Replace project management tools entirely.
* Grant agents unrestricted repo authority.
* Treat chat history as the canonical source of truth.
* Store private identity/persona state inside public task artifacts unless explicitly authorized.
* Collapse all project memory into one global context blob.

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

| State               | Meaning                                                                     |
| ------------------- | --------------------------------------------------------------------------- |
| `draft`             | Task exists but is not ready for agent execution.                           |
| `ready`             | Task has passed intent/scope review and can be planned.                     |
| `in_progress`       | Agent or human is actively implementing it.                                 |
| `blocked`           | Cannot proceed due to missing dependency, decision, or external constraint. |
| `needs_review`      | Work is complete enough for human or automated review.                      |
| `changes_requested` | Review failed and the agent must revise.                                    |
| `done`              | Acceptance criteria and definition of done are satisfied.                   |
| `archived`          | Task is no longer active but preserved for history.                         |

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

* Does the task correctly capture intent?
* Are acceptance criteria testable?
* Is the scope small enough?
* Are out-of-scope boundaries clear?
* Is the blast radius acceptable?

Pass condition:

```txt
review_gates.intent_review = approved
status = ready
```

---

### Gate 2: Plan Review

Occurs after implementation plan generation and before code mutation.

The reviewer checks:

* Is the agent touching the right files?
* Is the plan technically sane?
* Are risks identified?
* Are tests appropriate?
* Is rollback possible?
* Is the agent avoiding scope creep?

Pass condition:

```txt
review_gates.plan_review = approved
status = in_progress
```

---

### Gate 3: Completion Review

Occurs after implementation and test execution.

The reviewer checks:

* Were all acceptance criteria met?
* Did tests pass?
* Were implementation notes recorded?
* Were unrelated changes avoided?
* Should the result be indexed into memory / graph?

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

* What Execution Ledger is.
* How tasks move through states.
* Which resources/tools are available.

### Resource: `codexify://workflow/create-task`

Explains:

* How to convert human intent into a task.
* Required fields.
* How to define acceptance criteria.
* How to identify scope boundaries.

### Resource: `codexify://workflow/plan-task`

Explains:

* How to inspect the repo.
* How to produce an implementation plan.
* How to estimate blast radius.
* How to define a test plan.

### Resource: `codexify://workflow/execute-task`

Explains:

* How to begin work.
* How to update status.
* How to stay within scope.
* How to record implementation notes.

### Resource: `codexify://workflow/complete-task`

Explains:

* How to validate acceptance criteria.
* How to run tests.
* How to produce completion summaries.
* How to request final review.

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

* Task link
* Acceptance criteria checklist
* Implementation summary
* Test results
* Known limitations
* Reviewer notes

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

* Architecture decisions
* Implementation summaries
* File relationships
* Task outcomes
* Known limitations

Do not index:

* Private user reflections
* Persona identity fragments
* Sensitive credentials
* Temporary emotional context
* Unapproved personal memory

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

* Why the extra file was touched.
* Whether it was necessary.
* Whether the scope should be amended.

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

| Failure                          | Mitigation                                         |
| -------------------------------- | -------------------------------------------------- |
| Agent misunderstands intent      | Gate 1 catches it.                                 |
| Agent chooses wrong architecture | Gate 2 catches it.                                 |
| Agent edits too much             | Blast radius validation catches it.                |
| Agent marks incomplete work done | Acceptance criteria validation catches it.         |
| Context window runs out          | Atomic task size limits reduce it.                 |
| Task becomes stale               | Updated task metadata and review status expose it. |
| Multiple agents conflict         | Git branches and dependency metadata isolate work. |

---

## 21. Minimal MVP Implementation

### Phase 1: File-Based Ledger

Implement:

* `.codexify/tasks/`
* Markdown task schema
* Manual task creation
* Manual review gates
* Git branch convention
* Basic CLI commands

### Phase 2: Agent-Readable Workflow

Implement:

* `agent-guide.md`
* `workflow.md`
* Task creation prompt template
* Implementation plan template
* Definition of done template

### Phase 3: MCP Server

Implement:

* MCP resources
* MCP task tools
* Agent task search/read/create/update
* Plan creation
* Gate updates

### Phase 4: Codexify UI Integration

Implement:

* Task board view
* Task detail view
* Review gate controls
* Acceptance criteria checklist
* Agent execution log panel
* Git diff / blast radius display

### Phase 5: GraphWrag Integration

Implement:

* Task indexing
* Decision nodes
* Code-change nodes
* Retrieval by feature/task/file/persona

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
