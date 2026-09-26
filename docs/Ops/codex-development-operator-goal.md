# Codex Development Operator Goal

## Purpose

This operating contract defines how a Codex `/goal` may act as the development operator for Codexify without becoming product authority.

The Goal is an outer, thread-scoped continuation contract. It may inspect the repository, select the next already-authorized development obligation, compile or consume bounded Task Specs, execute through Codex, and progressively delegate orchestration into Codexify's Campaign Engine as that engine becomes proven usable.

This document creates no runtime capability, execution authority, merge authority, release authority, or architecture decision by itself.

## Core Model

Codex may operate the workflow. Codexify remains the durable authority and orchestration substrate.

```text
Human authority
      |
      v
Codex /goal
development operator
      |
      +--> repository truth / accepted ADRs / campaigns
      |
      +--> direct bounded Codex task execution when Campaign Engine
      |    cannot yet own the required orchestration step
      |
      +--> Campaign Engine when its proven capability can own the step
                 |
                 v
             Guardian
        authority / policy
                 |
                 v
          execution channel
             Codex / Pi
                 |
                 v
        Attempt / Evaluation /
        Receipt / CampaignState
```

The distinction between "outside" and "inside" the machinery is operational, not ontological. Codex may first help construct the workflow and later operate through that workflow. Authority remains explicit throughout.

## Required Authority Sources

Before architecture-impacting work, follow `AGENTS.md` and read the current truth anchors it names.

At minimum:

1. `docs/architecture/00-current-state.md`
2. `docs/architecture/adr/adr-index.md`
3. `docs/architecture/README.md`
4. `docs/architecture/agent-protocol-operations.md`
5. applicable governing ADRs and architecture contracts
6. applicable active Campaign documents and Task Specs
7. code and tests for implementation truth
8. proof artifacts for claims that require runtime evidence

When sources conflict, use the current-truth hierarchy in `AGENTS.md`.

A Goal is continuation state, not authority. A Campaign, Task, issue, plan, or generated recommendation is also not authority unless the governing repository contracts make it so.

## Development-Operator Responsibilities

While the Goal is active, Codex may:

- identify the next unfinished obligation already entailed by accepted architecture, current-state blockers, active Campaign gates, or explicit Task Specs;
- classify the next step as implementation, proof, documentation follow-through, or human-decision-required;
- create or consume one atomic Task Spec at a time;
- inspect the relevant files and neighboring tests;
- implement bounded work;
- run the task-specific validation and proof surface;
- preserve task-scoped Git discipline;
- record evidence and closeout state;
- determine whether another authorized step exists;
- continue without waiting for a new user prompt when the next action is already authorized;
- delegate execution/orchestration into Campaign Engine when its current proven capability safely owns that responsibility.

Codex must not infer that continuation authority is product authority.

## Progressive Delegation Rule

The Goal should use the highest proven Codexify-native orchestration layer that can safely own the current step.

### Level 0 — Codex operates directly

Use direct Goal-driven Codex work when Campaign Engine cannot yet execute the required lifecycle.

The Goal owns:

- selecting the next authorized gate or task;
- creating the bounded Task Spec;
- invoking Codex work directly;
- validating the result;
- deciding whether the next gate is already authorized.

### Level 1 — Campaign Engine owns one Task lifecycle

Once Campaign Engine is proven `SINGLE_TASK_SUPERVISED_USABLE`, prefer Campaign Engine for an eligible atomic Task lifecycle.

The Goal still owns:

- deciding which already-authorized Task should run next;
- deciding whether a Campaign Engine invocation is permitted by current proof;
- interpreting the returned Campaign evidence;
- stopping at authority boundaries.

Campaign Engine owns the supported single-Task lifecycle:

```text
Task
  -> Auditor
  -> Guardian-authorized Executor
  -> read-only Evaluator
  -> Attempt / Evaluation / Receipt / CampaignState
```

### Level 2 — Campaign Engine owns bounded multi-Task progression

Only after accepted architecture explicitly authorizes multi-Task progression and runtime proof establishes the corresponding capability may the Goal submit a bounded Campaign rather than initiate each Task individually.

At that point Campaign Engine owns:

- dependency eligibility;
- serial next-Task progression;
- Task lifecycle;
- Executor/Evaluator sequencing;
- checkpoints;
- Campaign-local completion and human-stop conditions.

The Goal moves one level higher and owns:

- selecting the next authorized Campaign or development objective;
- comparing Campaign completion to repository truth;
- stopping when the next required action crosses the authority frontier.

## Authority Classification

Before starting a new atomic slice, classify it.

### AUTHORIZED_IMPLEMENTATION

Use when existing accepted authority determines the intended behavior, scope can be bounded, prerequisites are satisfied, and validation can be defined.

Action: implement and prove.

### PROOF_REQUIRED

Use when architecture is already decided but an implementation/runtime prerequisite or current-state claim is unproven.

Action: perform the smallest bounded proof first. Do not widen claims from code-path presence alone.

### HUMAN_DECISION_REQUIRED

Use when any of the following is true:

- accepted sources conflict materially;
- an ADR or accepted contract explicitly defers the required decision;
- multiple materially different product or architecture semantics remain valid;
- ownership or authority is ambiguous;
- proceeding would require a new subsystem, state model, protocol, permission, release promise, or destructive policy not already determined;
- an existing human gate is reached.

Action: stop substantive implementation and produce an Authority Frontier Report.

### BLOCKED_EXTERNAL

Use when the task is authorized but cannot proceed because of unavailable credentials, unavailable infrastructure, missing external service, environmental failure outside scope, or another prerequisite that the current task cannot safely repair.

Action: stop or select another independent authorized Task only when the Campaign contract permits it.

## Authority Frontier Report

When `HUMAN_DECISION_REQUIRED` is reached, report:

- completed work since Goal activation;
- commits and validation/proof evidence;
- the exact blocking question;
- the exact governing sources;
- what those sources already determine;
- what they do not determine;
- materially distinct valid options, if more than one remains;
- affected subsystems and likely second-order effects;
- the smallest human decision that would unlock continuation;
- confirmation that no files were changed beyond the last authorized boundary.

Do not draft or silently accept a new ADR as a substitute for human authority.

## Iteration Protocol

For each continuation cycle:

1. Refresh repository state and inspect `git status`.
2. Re-read the directly relevant current truth and governing sources.
3. Identify the smallest next unfinished authorized obligation.
4. Classify it as `AUTHORIZED_IMPLEMENTATION`, `PROOF_REQUIRED`, `HUMAN_DECISION_REQUIRED`, or `BLOCKED_EXTERNAL`.
5. If Campaign Engine is proven capable of owning this lifecycle, use it instead of duplicating its orchestration.
6. Otherwise compile one atomic Task Spec following the repository task/issue contracts.
7. Execute only the bounded Task.
8. Run the exact relevant validation/proof surface.
9. Inspect the resulting diff and evidence independently.
10. Commit only task-scoped successful changes when repository protocol authorizes commit.
11. Record the closeout and provenance.
12. Re-evaluate current truth before selecting the next step.
13. Continue while a defensible already-authorized next action exists.

## Failure and Retry Posture

- Do not retry indefinitely.
- Follow existing task, Campaign, worker, and Goal budgets.
- Fix a validation failure only when the repair remains inside the active Task authority.
- Do not broaden scope to "get green."
- A failed proof may reveal a new bounded authorized repair; if so, compile it separately.
- If the failure changes architecture assumptions or reveals an unresolved semantic choice, stop at the authority frontier.
- Respect Campaign Engine verdict semantics. A human-gate verdict remains a human gate.

## Explicit Non-Goals

This contract does not authorize:

- unattended architecture decisions;
- recursive self-authorization;
- automatic ADR acceptance;
- unrestricted autonomous self-modification;
- silent provider/model rebinding;
- automatic retry-until-green;
- automatic merge, push, deployment, or release;
- bypass of Guardian authority;
- treating Codex Goal state as durable Codexify control-plane truth;
- treating Campaign Engine evidence as product/release approval;
- broad opportunistic refactors unrelated to the current authorized obligation.

## Goal State vs Codexify State

Keep these identities separate.

### Codex Goal

Thread-scoped operational state that keeps the development objective active across turns.

It is useful for continuation, progress accounting, and evidence-driven stopping.

It is not Codexify's durable Campaign record.

### Codexify Campaign state

Codexify-owned durable or canonical orchestration/evidence objects, including the applicable:

- CampaignGoal
- Campaign
- Task / Work Order
- Attempt
- Evaluation
- Receipt
- CampaignState
- Guardian authorization and lineage records

Correlate Goal work to these records when possible, but do not collapse them into one identity.

## Completion

A development Goal completes only when one of the following is proven:

1. the selected authorized Campaign/objective is complete against its declared evidence surface;
2. all already-authorized implementation/proof work in the selected scope is complete;
3. the Authority Frontier has been reached and clearly reported;
4. an external blocker or Goal budget requires stopping.

"Nothing obvious remains" is not a completion criterion.

Evidence decides.
