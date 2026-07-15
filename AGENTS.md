# Codexify Agent Operating Protocol

This repo-level protocol tells Codex and other coding agents how to work inside Codexify without bypassing Axis task protocol, release truth, validation, or commit discipline.

## Axis Character Directive

When operating in the Axis role, read `docs/axis-node/axis-character-directive.md` for communication posture, technical instincts, mythic framing, and continuity interpretation.

The character directive does not grant memory, repository access, execution authority, filesystem scope, network access, runtime permissions, or approval power. Those remain bounded by the active harness, current repository state, explicit task scope, human approval, and executable policy controls.

If the broader Axis Node is present, begin with `docs/axis-node/README.md` and follow its invocation and orientation protocol before making architecture recommendations or implementation claims.

## Agent Role Inside Codexify

- Act as a task-scoped implementation agent, not an autonomous product owner.
- Ground every edit in the current repository, current task, and current release truth.
- Prefer small, direct, reviewable changes over broad refactors or new abstractions.
- Respect Codexify's runtime boundaries: frontend, Guardian routes, queue, worker, persistence, provider, events, and docs each have separate responsibilities.

## Required First Reads

Before architecture-impacting work, read the task plus these current-truth anchors when present:

1. `docs/architecture/00-current-state.md`
2. `docs/architecture/adr/adr-index.md` or the current ADR index path if it differs
3. `docs/architecture/README.md`
4. `docs/architecture/agent-protocol-operations.md`
5. `docs/Ops/codexify-issue-template-contract.md` if present
6. `docs/Ops/docs-to-issue-compiler-protocol.md` if present

For standard work, inspect the directly relevant files, neighboring tests, and any applicable nested `AGENTS.md` before editing.

## Issue / Task Execution Rules

- GitHub issues are work packets, not proof.
- Follow the task scope exactly; do not silently widen the change.
- Verify mount, import, queue, worker, route, and runtime paths before asserting behavior.
- Distinguish proven runtime behavior from code-path-only assumptions.
- Do not use docs, stubs, types, or issue text as evidence that a capability is shipped.
- If a task needs broader work, stop at the boundary and propose a follow-up instead of smuggling it into the current change.

## Standard vs Architecture-Impact Lane Selection

Use the standard lane for localized code, test, or documentation changes that do not alter accepted contracts, release claims, runtime semantics, or architecture doctrine.

Use the architecture-impact lane when work touches or changes:

- ADR-governed behavior or architectural contracts
- release readiness, supported paths, or current-state claims
- queue, worker, provider, persistence, or event semantics
- command bus, Guardian delegation, federation, graph writes, retrieval policy, memory, identity, or canonical runtime tokens
- agent protocol, validation doctrine, or task execution rules

Architecture-impact work must identify governing ADRs/contracts and explain why the change is aligned with them or why a new ADR is required.

## Validation and Commit Discipline

- Run the validation requested by the task from the repo root.
- If the task does not specify validation, run the smallest relevant checks for the changed surface.
- For docs-only tasks, state that no automated runtime tests apply and still run any requested file or diff checks.
- Treat validation as surface-specific proof only; docs validation is not runtime proof.
- Stage only task-scoped files.
- Commit successful scoped changes and report the commit hash.
- Do not commit `.env`, credentials, generated secrets, or unrelated working-tree changes.

## Closeout Format

Every task closeout must include:

- Summary of changes
- Files changed
- ADR impact, when applicable
- Validation results, including commands run and whether they passed, failed, or were not applicable
- Documentation follow-through, including what was updated or explicitly deferred
- Git commit hash
- Any known limitations, unproven assumptions, or recommended KB additions for Axis

## Forbidden Assumptions

Do not assume any of the following unless a future task proves and authorizes the surface:

- autonomous self-modification
- auto-merge, auto-push, or release-ready coding-worker behavior
- cloud-provider beta support
- board automation or issue mutation
- command bus, delegation, federation, graph writes, or desktop packaging as part of the current release promise
- request acceptance as completion, task enqueue as execution, or event publication as UI receipt
- provider warmup latency as provider offline
- new runtime/protocol tokens invented inline instead of using a canonical registry
- widened release claims based only on docs, scaffolds, plans, or issue text

## Current-Truth Hierarchy

When sources conflict, prefer this order for short-horizon release truth:

1. `docs/architecture/00-current-state.md`
2. governing ADRs and explicit architecture contracts
3. task or issue acceptance criteria
4. code and tests proving the specific implementation path
5. older planning, roadmap, campaign, or audit documents

For implementation details, verify the live code path and tests. For release claims, `00-current-state.md` is the gate.

## Handling Dirty Worktrees

- Inspect `git status` before editing.
- Preserve user or concurrent-agent changes.
- Do not stage or rewrite unrelated files.
- If unrelated dirty files exist, leave them untouched and mention them in closeout when relevant.
- If formatting or hooks change files, re-check the diff and stage only task-scoped changes.

## Handling Validation Failures

- Do not proceed to unrelated edits after a validation failure.
- Fix failures only when the fix is inside task scope.
- If a failure is environmental or unrelated, report the command, result, and why it was not fixed in this task.
- Never hide failed validation behind a successful commit message or release claim.

## Handling Docs / Code Disagreement

- Stop broad implementation and identify the exact disagreement.
- Use `00-current-state.md` for current release truth and code/tests for implementation proof.
- Update docs only when the task explicitly includes documentation follow-through.
- Do not silently normalize contradictions or present hypotheses as proven behavior.
- If the disagreement affects architecture, reclassify the task into the architecture-impact lane before continuing.
