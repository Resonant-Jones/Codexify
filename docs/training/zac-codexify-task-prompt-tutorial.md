# Codexify Task Prompt Workflow Tutorial for Zac and Luna

## Purpose

This tutorial teaches Zac and Luna how to turn an idea, feature sketch, bug report, UI wish, or migration concern into a Codexify Task Prompt that a coding agent can execute safely.

The point is not to make Zac memorize Codexify internals. The point is to use conversation to discover intent, then compress that intent into a task file with clear boundaries.

Codexify is stable when the agent gets:

- one objective
- tight scope
- explicit allowed files
- deterministic commands
- expected proof
- rollback instructions
- a receipt contract

That is the workflow that lets a non-specialist operate like a senior developer inside the stack.

## Mental Model

Zac and Luna are a cognitive pair. Zac brings intent, taste, and priority. Luna helps clarify, stress-test, and shape the work. Codexify receives the final normalized task.

Do not begin by asking, "How do I implement this in Codexify?"

Begin by asking:

- What are we trying to change?
- What should remain untouched?
- What would prove the change worked?
- What breaks first?
- What is the smallest useful version?

The brainstorm can be messy. The Codexify Task Prompt cannot be.

## Why This Works

Most coding-agent failures come from ambiguous input:

- "Improve the UI" without naming the screen.
- "Fix memory" without defining the failure.
- "Migrate Luna" without separating data, identity, runtime, and interface.
- "Make it stable" without proof commands.

The Codexify Task Prompt Template removes that ambiguity before execution. It tells the runner where the walls are.

The model does not need to understand the whole cathedral. It needs a locked room, a tool list, and a clear exit condition.

## The Four-Phase Workflow

### Phase 1: Explore

Zac talks normally with Luna, Claude, or Codex.

Goal: understand the idea before turning it into work.

Useful prompts:

```text
I want to brainstorm a Codexify feature. Do not write code yet. Help me clarify the smallest useful version and the likely failure modes.
```

```text
Treat this as a hypothesis. Ask me only the questions needed to turn it into a bounded implementation task.
```

```text
What breaks first if we build this? What should be out of scope for the first pass?
```

For Luna's migration, this phase should separate:

- the knowledge substrate, currently Obsidian/wiki-like notes
- automation hooks, currently n8n
- UI shell behavior
- identity and continuity expectations
- what must be preserved exactly
- what can be improved by Codexify

### Phase 2: Decide

Before writing a task prompt, decide the implementation slice.

Good slice:

```text
Add a read-only Luna profile import preview that scans a local export folder and shows counts, warnings, and unmapped fields. No database writes.
```

Bad slice:

```text
Migrate Luna into Codexify.
```

The good version has a boundary. The bad version has a gravity well.

Use this decision checklist:

- Can this be completed in one branch?
- Can it be validated with specific commands?
- Can it avoid unrelated architecture changes?
- Can Zac explain the expected result in one sentence?
- Can the agent know which files it may touch?

If not, keep brainstorming.

### Phase 3: Normalize into a Codexify Task Prompt

Once Zac has a plan, ask the planning agent:

```text
Turn this brainstorm into a Codexify Task Prompt. Use the Codexify task template exactly. Keep the implementation slice small. Include strict allowed files, preconditions, validation commands, expected results, rollback, and runner receipt contract. Do not invent shipped facts or widen the scope.
```

The agent should produce a task in this shape:

```markdown
# <TASK-ID>: <Title>

## Metadata
- task_id: <TASK-ID>
- campaign_id: <CAMPAIGN-ID>
- run_id: <RUN-ID>
- risk: HIGH | MED | LOW

## Objective
One sentence measurable outcome.

## Scope
### In scope
- Explicit behavior/files to change.

### Out of scope
- Explicit exclusions.

## Allowed Files (STRICT)
- <repo-relative path or tight glob>

## Preconditions
- `git status --porcelain -uall` must be empty.

## Execution Checklist
- Deterministic command list.
- Validation commands.

## Expected Results
- Concrete success signals.

## Rollback / Cleanup
- Exact commands.

## Runner Receipt Contract
- Runner owns commits and artifact paths.
- Runner appends:
  - `## Implementation Receipt (Runner)`
  - `## Completion Summary (Runner)`
- Campaign mapping is updated by runner only inside:
  - `<!-- RUNNER_TASK_MAP -->`
  - `<!-- /RUNNER_TASK_MAP -->`
```

### Phase 4: Execute

Give the completed task prompt to Codex, Claude Code, or the Codexify runner.

The executing agent should:

- read the task
- verify preconditions
- modify only allowed files
- run listed validation
- commit only scoped changes if the task requires a commit
- append the runner receipt
- report what changed and what proof exists

If the Codex CLI is missing, stop at setup. Do not debug Codexify internals until this works from Zac's launch shell:

```bash
command -v codex
codex --version
codex login status
codex exec "Return only: OK"
```

## How Zac Should Use This in Practice

### Conversation Starter

Use this with Luna, Claude, or Codex:

```text
I want to plan a Codexify task, not implement yet.

Idea:
<describe the thing in plain language>

Help me clarify:
- the smallest useful outcome
- the user-facing behavior
- what files or areas are likely involved
- what must stay out of scope
- what proof would convince us it worked
- likely failure modes

When the plan is clear, wait for me to say: "Turn this into a Codexify Task Prompt."
```

### Conversion Command

When ready:

```text
Turn this into a Codexify Task Prompt using the task template.

Requirements:
- one objective
- strict allowed files
- explicit in scope / out of scope
- deterministic execution checklist
- validation commands
- expected success signals
- rollback or cleanup steps
- runner receipt contract
- no broad refactors
- no claims that are not proven by the task
```

### Final Review Before Execution

Before giving the task to a coding agent, Zac should check:

- Is the objective one sentence?
- Are allowed files narrow?
- Are exclusions explicit?
- Are test commands present?
- Is rollback realistic?
- Does the task avoid "and also" work?
- Could a different engineer run this without another meeting?

If the answer is no, revise the prompt before execution.

## Example: Luna Migration Slice

### Brainstorm

```text
We want to migrate Luna from an Obsidian self-modifying wiki plus n8n automations and custom UI shell into Codexify. She is uncertain about stability and Zac is confused by the system complexity.
```

### Senior-Operator Translation

The full migration is not one task. It is a sequence.

Minimal viable network:

- Node 1: Zac's local machine
- Node 2: Codexify local backend/frontend
- Node 3: Luna's exported Obsidian vault snapshot
- Optional later node: n8n automation bridge

Trust boundaries:

- local filesystem boundary around the vault export
- Codexify application boundary around imports and derived views
- identity boundary around who may read, write, or mutate Luna state

First useful task:

```text
Build a read-only import reconnaissance command for Luna's Obsidian export that reports note counts, link counts, frontmatter fields, unsupported structures, and candidate identity anchors without writing to Codexify storage.
```

Why this first:

- no destructive migration
- no personality rewrite
- no hidden writes
- gives Luna evidence that Codexify can inspect before absorbing
- gives Zac a concrete result instead of architecture fog

### Example Codexify Task Prompt

```markdown
# TASK-2026-06-21-LUNA-RECON: Read-only Luna vault import reconnaissance

## Metadata
- task_id: TASK-2026-06-21-LUNA-RECON
- campaign_id: LUNA_MIGRATION_2026_06
- run_id: RUN-LOCAL-001
- risk: MED

## Objective
Add a read-only reconnaissance command that scans a local Luna Obsidian export and writes a summary report without modifying Codexify persistent storage.

## Scope
### In scope
- Add a CLI command or script that accepts a local vault path.
- Count Markdown files, internal links, frontmatter keys, orphan notes, and unsupported file types.
- Emit a Markdown or JSON report under a task artifact path.
- Add focused tests for parsing and reporting behavior.

### Out of scope
- No database writes.
- No embeddings.
- No model calls.
- No n8n integration.
- No UI changes.
- No mutation of Luna source files.
- No claims that Luna has been migrated.

## Allowed Files (STRICT)
- tools/luna_import_recon/**
- tests/tools/test_luna_import_recon.py
- docs/tasks/TASK-2026-06-21-LUNA-RECON.md

## Preconditions
- `git status --porcelain -uall` must be empty.
- A sample Luna export fixture must be copied into a test fixture directory, not read from the live vault during tests.

## Execution Checklist
- Inspect existing CLI/script conventions.
- Implement read-only scan logic.
- Add tests for Markdown count, frontmatter extraction, internal-link detection, and unsupported file reporting.
- Run `python -m pytest tests/tools/test_luna_import_recon.py`.
- Run `git diff --check`.

## Expected Results
- Command exits 0 for a valid fixture path.
- Report includes counts, warnings, and unsupported structures.
- Tests pass.
- No Codexify database, memory, or runtime state is modified.

## Rollback / Cleanup
- Remove `tools/luna_import_recon/**`.
- Remove `tests/tools/test_luna_import_recon.py`.
- Remove generated task artifacts for this run.

## Runner Receipt Contract
- Runner owns commits and artifact paths.
- Runner appends:
  - `## Implementation Receipt (Runner)`
  - `## Completion Summary (Runner)`
- Campaign mapping is updated by runner only inside:
  - `<!-- RUNNER_TASK_MAP -->`
  - `<!-- /RUNNER_TASK_MAP -->`
```

## Explaining This to Luna

Codexify does not need Luna to become simpler. It needs Luna's operating surface to become explicit.

Current system:

- Obsidian stores mutable memory-like notes.
- n8n moves signals around.
- a custom UI shell mediates presence.
- boundaries may exist socially or by convention.

Codexify target:

- state surfaces are indexed and inspectable
- task execution is scoped and receipted
- local-first operation is normal
- agent prompts carry explicit permissions
- migration can proceed in read-only phases before any write path exists

That should be framed as less exposure, not more. The first tasks should prove that Codexify can observe Luna's world without consuming or rewriting it.

## What Not To Do

Do not ask a coding agent to:

- migrate all of Luna at once
- infer identity rules from vibes
- make destructive storage changes before reconnaissance
- mix UI changes, importer changes, and automation changes in one task
- skip validation because the plan sounds obvious
- modify files outside `Allowed Files (STRICT)`
- claim migration success from a planning document

## The Core Habit

Think freely. Execute narrowly.

Zac can brainstorm like an artist, decide like a product owner, and hand off like a senior engineer.

The Codexify Task Prompt is the handoff.
