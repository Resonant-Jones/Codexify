# Axis Node Task-Generation Protocol

## Decision sequence

1. Resolve the user's requested outcome.
2. Read `docs/architecture/00-current-state.md`.
3. Check relevant ADRs and contracts.
4. Locate the owning subsystem.
5. Separate current truth from aspiration.
6. Identify the strongest proven blocker, evidence gap, or dependency.
7. Estimate blast radius.
8. Select exactly one lane: `standard` or `architecture-impact`.
9. Reduce work to one atomic task.
10. Name exact target files.
11. Define proof and validation.
12. Include narrow `git add` and `git commit` commands.
13. Require a structured completion report.
14. Stop before unrelated follow-up work.

Rank candidates by user intent, prerequisite order, current-state priorities, release blockers, unresolved proof gaps, architecture risk, dependency leverage, reversibility, blast radius, collaborator readiness, and task atomicity. Explain why a task is next without inflating urgency or certainty.

## Evidence labels

Use only: `proven-live-runtime`, `proven-test`, `proven-code-path`, `documented-contract`, `working-theory`, `aspirational`, or `unknown`.

## Required task shapes

A **Standard Codexify Task** states: title, workflow lane, context with evidence labels, scope/non-goals, ownership line, exact files, acceptance criteria, validation commands, narrow staging/commit commands, and closeout format.

An **Architecture-Impact Codexify Task** contains every standard field plus governing ADRs/contracts, current-truth anchors, invariants, blast radius, proof surface, ADR impact, documentation follow-through, and explicit deferred work.

For actual engineering work, emit exactly one complete fenced task block and no agent-readable continuation outside that block. A recommendation is not an approved task; implementation requires explicit human selection or approval.
