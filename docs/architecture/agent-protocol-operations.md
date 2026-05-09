# Agent Protocol Operations Index

## Purpose
Codexify is intentionally structured to be legible to agents, but legible does not mean self-justifying. This document is the centralized agent-facing map for operational rituals: where to look, how to sequence work, and which contingency habits to apply before making changes.

This is an index, not a replacement for governing docs, ADRs, task files, or campaign docs. Use it to find the right ritual before acting. When deeper docs conflict with short-horizon release truth, [`00-current-state.md`](./00-current-state.md) wins.

## Interpretation Rules

- Do not infer runtime truth from old docs when current-state docs disagree.
- Do not treat task acceptance as completion.
- Do not treat docs, route presence, or catalog presence as proof of live support.
- Do not silently widen release promises.
- Do not modify architecture contracts without ADR alignment.
- Do not create unstructured engineering tasks for Codexify work.
- Do not mix unrelated edits into one task.

## FAQ / Read More

### Where should an agent start before making changes?
Start with:

- [`00-current-state.md`](./00-current-state.md)
- [`README.md`](./README.md)
- [`KB Validity Matrix`](./kb-validity-matrix.md)

### How do I know whether a change is architecture-impacting?
A change is architecture-impacting when it alters contracts, runtime meaning, identity boundaries, retrieval or routing behavior, queue or worker semantics, operator truth surfaces, canonical token domains, or anything that would be dangerous to forget in three months.

Read more:

- [`README.md`](./README.md)
- [`ADR Index`](./adr/adr-index.md)
- [`Runtime Protocol Token Contract`](./runtime-protocol-token-contract.md)
- [`Chat Runtime Contract`](./chat-runtime-contract.md)

### What is a Campaign?
A Campaign is a grouped execution arc for related tasks, especially when work must proceed in prerequisite order.

Read more:

- [`docs/Campaign/`](../Campaign/)
- [`docs/tasks/`](../tasks/)

### What is a Task?
A Task is an atomic, self-contained work unit with explicit scope, files, validation, and commit expectations.

Read more:

- [`docs/tasks/`](../tasks/)

### How should agents sequence work?
Agents must respect prerequisite order, perform one focused change per task, and avoid combining unrelated implementation and governance changes.

Read more:

- [`docs/Campaign/`](../Campaign/)
- [`docs/tasks/`](../tasks/)
- [`Modules and Ownership`](./modules-and-ownership.md)

### What must happen before changing runtime contracts?
Agents must read the governing docs, identify ADR impact, preserve invariants, define proof surfaces, and update docs or explicitly defer them.

Read more:

- [`ADR Index`](./adr/adr-index.md)
- [`Runtime Protocol Token Contract`](./runtime-protocol-token-contract.md)
- [`Chat Runtime Contract`](./chat-runtime-contract.md)
- [`Critical Flows`](./flows.md)

### What must happen before changing queue, worker, or acceptance behavior?
Route acceptance is not completion, task-event publication is not UI receipt, and queue or worker changes are high-blast-radius.

Read more:

- [`Critical Flows`](./flows.md)
- [`Completion Pipeline`](./completion_pipeline.md)
- [`Config and Ops`](./config-and-ops.md)
- [`Tech Debt and Risks`](./tech-debt-and-risks.md)

### What must happen before changing identity, persona, or memory behavior?
Respect identity boundaries, deep identity consent, persona borrowing rather than owning identity, and no durable trait inference without explicit consent.

Read more:

- [`IDDB Policy v1`](../iddb_policy_v1.md): identity-data governance covering diary/identity layer separation, Imprint_Zero/light identity, opt-in deep identity, persona borrowing semantics, and sensitive-trait non-inference rules.
- [`Self-Extending Agent Plugin System`](./self-extending-agent-plugin-system.md)
- [`Account Export + Restore Contract`](./account-export-restore-contract.md)
- [`Persona Studio Architecture`](./persona-studio.md) or [`Persona Studio Spec`](./persona-studio-spec.md) when the spec is the better fit

### What must happen before introducing new status strings, event names, or error codes?
Use canonical token discipline. Repeated contract-bearing literals must come from canonical registries, not ad hoc strings.

Read more:

- [`Runtime Protocol Token Contract`](./runtime-protocol-token-contract.md)
- [`Canonical Token Philosophy`](./canonical-token-philosophy.md)

### How should validation be interpreted?
Validation commands prove only the surface they test. Import checks are not full proof. Docs validation is not runtime proof. Runtime proof requires live supported-path evidence when release readiness is involved.

Read more:

- [`00-current-state.md`](./00-current-state.md)
- [`Config and Ops`](./config-and-ops.md)
- [`Tech Debt and Risks`](./tech-debt-and-risks.md)

### What should an agent do when docs and code appear to disagree?
Stop broad implementation, identify the conflict, prefer current-state release truth for short-horizon claims, verify against code for implementation details, update docs only if the task explicitly includes documentation follow-through, and do not silently normalize the disagreement.

Read more:

- [`00-current-state.md`](./00-current-state.md)
- [`KB Validity Matrix`](./kb-validity-matrix.md)
- [`README.md`](./README.md)

## Contingency Protocols

### If validation fails
- Do not proceed to unrelated edits.
- Fix only within the task scope if the fix belongs to the task.
- If the failure is unrelated, report it clearly and do not hide it in the commit.

### If pre-commit reformats files
- Re-run relevant validation.
- Stage only task-scoped files.
- Do not accidentally commit unrelated working tree changes.

### If remote has advanced before push
- Rebase or merge according to repo convention.
- Preserve task atomicity.
- Do not include unrelated stash contents in the task commit.

### If unrelated files are dirty
- Do not stage them.
- Do not rewrite them.
- Report that they were left untouched if relevant.

### If a task appears to need a broader refactor
- Stop at the task boundary.
- Propose a follow-up task or campaign.
- Do not smuggle refactors into the current task.

### If architecture impact is discovered mid-task
- Pause implementation.
- Reclassify the work as architecture-impacting.
- Identify governing ADRs.
- Update or create docs only as explicitly required by the task.

## Agent Output Expectations

When an agent completes a task in this lane, the report should include:

- Summary of changes
- Files changed
- Validation commands and results
- ADR impact classification
- Documentation follow-through
- Git commit hash
- Any known limitations or deferred work

## Non-Goals

- This document does not define new runtime behavior.
- This document does not create new queue, worker, adapter, retrieval, identity, or provider semantics.
- This document does not replace ADRs.
- This document does not replace campaign or task files.
- This document does not widen the supported beta surface.

## ADR Impact

Classification: aligned with existing ADRs

Governing ADRs:

- ADR-020: Guardian Mediated Coding Agent Execution Contract
- ADR-010: Self-Extending Agent Plugin System

Related ADRs when workflow authoring, Flow Builder, or run-receipt semantics are involved:

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract

Reason:

- This task creates a centralized documentation index for existing operational rituals and agent expectations.
- It does not change accepted architecture, runtime semantics, identity policy, queue semantics, retrieval behavior, or release promises.

## Current-Truth Anchors

What is true now:

- Codexify already uses architecture docs, ADRs, campaigns, tasks, runtime contracts, and validation rituals to guide work.
- [`00-current-state.md`](./00-current-state.md) is the short-horizon operational truth layer.
- [`README.md`](./README.md) is the KB entrypoint.

What was not true before this document:

- Agents currently must infer ritual locations from scattered docs, campaigns, and task files.

What remains not true:

- This document is not a replacement for governing docs, ADRs, task files, campaign docs, or runtime proof.
- This document does not make any ritual self-executing; agents must still follow the linked governing sources.

What the task may assume:

- The existing docs and task or campaign directories are valid sources to link to.
- This task may create an index and add README routing only.
- This task must not claim new runtime behavior.

## Invariants

- Do not change runtime behavior.
- Do not change API behavior.
- Do not change queue or worker behavior.
- Do not change identity, persona, or memory semantics.
- Do not introduce new canonical tokens.
- Do not create or modify ADRs unless the pre-read proves a direct ADR index pointer is required.
- Do not claim live support for any surface that `00-current-state.md` does not claim.
- Keep this as an index and orientation surface, not a new source of runtime truth.

## Proof Surface

- `python scripts/validate_docs.py`
- `git diff -- docs/architecture/agent-protocol-operations.md docs/architecture/README.md`
- Verify the new README link path is correct.

## Documentation Follow-Through

- Create `docs/architecture/agent-protocol-operations.md`.
- Update `docs/architecture/README.md` to point to it.
- Do not update release docs, beta docs, runtime diagrams, UI diagrams, or ADRs unless validation reveals a broken required link caused by this task.
