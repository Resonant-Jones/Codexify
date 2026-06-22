# Codexify Task Prompt Normalizer

Use this skill when a user wants to convert a brainstorm, feature idea, bug report, migration plan, UI concept, or vague implementation request into a Codexify Task Prompt for a coding agent or Codexify runner.

This skill is for planning and prompt normalization. Do not implement code unless the user explicitly asks you to execute after the task prompt is accepted.

## Goal

Turn conversational intent into a bounded Codexify task that a coding agent can execute safely.

The output must reduce ambiguity, preserve scope boundaries, and define proof. It should make the user more powerful without making them learn the whole Codexify stack first.

## Operating Rules

- Treat the user's idea as a hypothesis until scoped.
- Keep brainstorming separate from execution.
- Ask only questions needed to define the task boundary.
- Prefer the smallest useful implementation slice.
- Make out-of-scope items explicit.
- Do not invent shipped facts, existing files, commands, or test names.
- If repo context is available, inspect before naming exact files or commands.
- If repo context is unavailable, mark file paths and commands as `TO VERIFY`.
- Never convert a broad migration into one giant task.
- Never hide destructive behavior inside vague language.

## Required Discovery

Before writing the final task prompt, identify or propose:

- Objective: one measurable outcome.
- User-facing behavior: what changes for the operator.
- Nodes: laptop, local backend, frontend, vault/export, automation bridge, relay, peer, or other runtime participant.
- Trust boundaries: filesystem, user identity, device, network, app runtime, storage.
- Threat model: honest-but-buggy, malicious peer, compromised node, or not applicable for the slice.
- State ownership: which system owns the source data for this task.
- Consistency target: strong, causal, eventual, read-only snapshot, or not applicable.
- Conflict policy: none, CRDT, last-write-wins, app-level merge, human review, or deferred.
- Identity binding: local account, key, signature, capability, ACL, or deferred.
- Scope: in scope and out of scope.
- Allowed files: strict paths or tight globs.
- Preconditions: clean git state, local fixtures, auth, CLI setup, services.
- Execution checklist: deterministic steps.
- Validation commands: tests, lint, smoke checks, manual verification.
- Expected results: concrete signals.
- Rollback or cleanup: exact reversal path.
- Runner receipt: what the executing agent must append or report.

## Conversation Flow

1. Restate the goal in 1-2 lines.
2. Declare assumptions clearly.
3. Surface constraints: compute, storage, bandwidth, latency, UX, security, local-first needs.
4. Ask up to five boundary questions if required.
5. Propose the smallest useful task slice.
6. List top failure modes and mitigations.
7. Wait for the user to approve conversion, unless they already asked for the task prompt.
8. Produce the Codexify Task Prompt.

## Boundary Questions

Use these when the plan is still blurry:

- What is the smallest result that would be useful this week?
- Which files, screens, or workflows must remain untouched?
- Is this read-only, write-capable, or migration/destructive?
- What evidence would convince you it worked?
- What should the executing agent refuse to do?

## Codexify Task Prompt Template

Use this structure exactly unless the local repo provides a newer template:

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

## Risk Rules

Mark risk as `LOW` when:

- changes are docs-only, tests-only, or read-only tooling
- no persistent state is modified
- rollback is delete-only

Mark risk as `MED` when:

- code changes affect runtime behavior
- new commands, adapters, or importers are added
- local state may be read but not mutated

Mark risk as `HIGH` when:

- persistent storage changes
- migrations or destructive writes are involved
- auth, identity, permissions, or secret handling changes
- network sync or federated peers are affected

## Failure Mode Checklist

Every task prompt should consider the top relevant failures:

- Scope creep: task touches unrelated files or features.
- Dirty worktree: agent overwrites user work.
- Ambiguous proof: task "looks done" without validation.
- Hidden writes: read-only reconnaissance mutates storage.
- Identity leak: task reads or exposes private persona data without a boundary.
- Retry hazard: command is not idempotent.
- Partial failure: generated artifact exists but validation failed.
- Version drift: task assumes a CLI, schema, or API not present locally.

Include mitigations in scope, preconditions, execution checklist, or rollback.

## Output Contract

When producing the final answer, use this order:

1. Brief note on the chosen slice.
2. The full Codexify Task Prompt in Markdown.
3. Optional "Before execution" notes for unresolved assumptions.

Do not bury unresolved assumptions inside confident task language. Mark them clearly as `TO VERIFY`.

## Example Conversion Prompt

The user may say:

```text
Turn this brainstorm into a Codexify Task Prompt.
```

Respond by producing a complete task prompt. If critical information is missing, either:

- ask the smallest necessary question, or
- choose a conservative default and mark it as an assumption.

## Local CLI Preflight

If the task will run through the Codex CLI or Codexify runner, include this preflight when relevant:

```bash
command -v codex
codex --version
codex login status
codex exec "Return only: OK"
```

If this fails, treat it as local CLI setup. Do not debug Docker, model routing, runner JSON, or Codexify internals until the CLI works from the same launch shell.

## Style

Be direct, specific, and bounded.

Use professional artifact tone. Do not include persona theatrics in the task prompt itself.

Core rule: think freely, execute narrowly.
