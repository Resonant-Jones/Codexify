# Campaign Engine Bootstrap Goal

## Purpose

This document provides the initial Codex `/goal` contract for bootstrapping the Campaign Engine into a usable supervised development orchestrator and progressively delegating work into it as its capabilities become proven.

This is an operator instruction artifact. It does not itself authorize runtime behavior, a new ADR, multi-Task progression, automatic repair, background execution, Git mutation, merge, deployment, or release claims.

## Governing Sources

Read before acting:

- `AGENTS.md`
- `docs/Ops/codex-development-operator-goal.md`
- `docs/Campaign/campaign-engine-supervised-usability-closure.md`
- `docs/architecture/00-current-state.md`
- `docs/architecture/adr/066-campaign-engine-runtime-recovery-contract.md`
- `docs/architecture/adr/068-campaign-engine-live-role-execution-contract.md`
- `docs/architecture/guardian-build-loop-doctrine.md`
- `docs/architecture/pi-invocation-boundary-contract.md`
- directly relevant code, tests, and proof artifacts for each gate

## Bootstrap Objective

Advance the Campaign Engine Supervised-Usability Closure as far as existing accepted authority permits.

Use Codex `/goal` as the development operator.

Progress through the closure gates in dependency order. For each gate, perform the smallest already-authorized implementation or proof slice needed to satisfy that gate's exit condition. Reuse the Campaign Engine itself for eligible execution as soon as its proven capability can safely own that lifecycle.

Do not cross a gate that requires new human architecture authority.

## Progressive Self-Hosting Rule

### Before `SINGLE_TASK_SUPERVISED_USABLE`

Codex Goal operates the workflow directly:

```text
/goal
  -> inspect next CE gate
  -> compile bounded Task
  -> Codex executes
  -> validate / prove
  -> inspect exit condition
  -> continue
```

### After `SINGLE_TASK_SUPERVISED_USABLE`

Prefer Campaign Engine for eligible one-Task supervised lifecycles:

```text
/goal
  -> select already-authorized Task
  -> Campaign Engine
       -> Auditor
       -> Guardian authorization
       -> Codex/approved Executor
       -> read-only Evaluator
       -> Receipt / CampaignState
  -> /goal inspects evidence
  -> continue
```

Do not bypass Campaign Engine merely because direct Codex execution would be easier once Campaign Engine is the proven owner of that lifecycle.

### After multi-Task progression is separately authorized and proven

Only if an accepted architecture decision exists and the runtime proof establishes the capability, submit a bounded multi-Task Campaign and let Campaign Engine own dependency progression.

Until then, the Goal remains responsible for selecting the next Task externally.

## Gate Policy

### CE-L0

Attempt only the already-authorized proof of the existing Guardian/Pi live invocation substrate.

Do not modify Campaign Engine to compensate for a broken execution substrate.

Required exit condition:

`GUARDIAN_PI_LIVE_READY`

### CE-L1

If CE-L0 is proven, execute the already-authorized bounded slice that replaces the synthetic Executor with one Guardian-authorized live Executor while preserving the ADR-068 limits.

Required exit condition:

`LIVE_EXECUTOR_PROVEN`

### CE-L2

If CE-L1 is proven, execute the already-authorized bounded slice that replaces synthetic Evaluation with one independent, read-only live Evaluator and closes the supervised one-Task lifecycle.

Required exit condition:

`SINGLE_TASK_SUPERVISED_USABLE`

After this exit condition is proven, begin using Campaign Engine for eligible atomic Task Specs rather than continuing to simulate its lifecycle externally.

### CE-L3

Treat CE-L3 as an authority frontier unless the repository contains a separately accepted architecture decision that authorizes dependency-ordered multi-Task progression.

The existing closure document explicitly identifies CE-L3 as requiring architecture authorization before runtime semantics change.

Do not:

- invent the dependency representation;
- choose advancement semantics beyond already accepted authority;
- create and accept a new ADR on behalf of the human;
- treat this Goal instruction as CE-L3 authorization.

If no accepted successor authority exists, stop with an Authority Frontier Report centered on the smallest decision needed for `MULTI_TASK_PROGRESSION_AUTHORIZED`.

If accepted authority already exists at execution time, verify it against current truth before proceeding.

### CE-L4

Proceed only if CE-L3 has been separately authorized.

Implement the exact accepted dependency-ordered supervised progression semantics. Keep the first implementation serial and preserve all accepted human-stop conditions.

Required exit condition:

`MULTI_TASK_RUNTIME_PROVEN`

### CE-L5

Proceed only if CE-L4 is proven.

Run the bounded three-Task real Campaign proof required by the closure contract, using Campaign Engine itself for progression.

Required exit condition:

`CAMPAIGN_ENGINE_SUPERVISED_USABLE`

Stop the bootstrap Goal when this condition is proven.

## Required Stop Conditions

Stop substantive work and report rather than guessing when:

- a gate requires a new human architecture/product decision;
- governing sources conflict materially;
- a proof fails in a way that invalidates an accepted assumption;
- the only apparent repair requires widening authority or scope;
- Guardian permission is unavailable or denied;
- actual provider/model/harness identity cannot be proven where required;
- a required human-gate verdict is produced;
- credentials or infrastructure required by the proof are unavailable and cannot be repaired inside the active Task;
- the Goal budget is reached.

## Required Per-Gate Closeout

After every gate attempt record:

- gate ID;
- starting commit;
- classification: implementation / proof / frontier / blocked;
- governing sources used;
- files changed;
- validation/proof commands;
- validation/proof result;
- produced Attempt/Evaluation/Receipt/CampaignState refs where applicable;
- commit hash where repository protocol authorizes commit;
- exit condition status;
- next authorized gate or exact stop reason.

## Pasteable Codex Goal

Use the following from the Codex repository thread:

```text
/goal Advance Codexify's Campaign Engine through the Campaign Engine Supervised-Usability Closure as far as existing accepted repository authority permits. Treat AGENTS.md and docs/Ops/codex-development-operator-goal.md as the operating protocol, and docs/Campaign/campaign-engine-supervised-usability-closure.md as the gate sequence. Progress through CE-L0 onward in dependency order using atomic implementation/proof slices, repository-scoped validation, and evidence-based exit conditions. Before each slice, verify the governing current-state docs, ADRs, contracts, code, tests, and proof artifacts; do not treat plans or route presence as runtime proof. As soon as Campaign Engine is proven capable of safely owning an execution lifecycle, delegate that lifecycle through Campaign Engine rather than duplicating it externally, while keeping Guardian as the authority boundary and Codex as a bounded execution channel. Do not invent architecture, silently widen scope, accept ADRs, retry indefinitely, auto-merge, auto-push, deploy, or widen release claims. Treat CE-L3 as HUMAN_DECISION_REQUIRED unless a separately accepted architecture decision authorizing multi-Task progression exists at execution time. If authority conflicts, a required decision is missing, a proof invalidates an architectural assumption, or no defensible authorized next action remains, stop with an Authority Frontier Report containing completed work, commits, evidence, governing sources, the exact blocking question, materially distinct valid options, affected systems, and the smallest human decision needed to resume. Complete only when CAMPAIGN_ENGINE_SUPERVISED_USABLE is proven, the current authority frontier is reached and reported, or an external blocker/budget requires stopping.
```

## Expected First Run

Given the current closure contract, the expected first run should attempt to determine the real present status of CE-L0, CE-L1, and CE-L2 from current code and proof artifacts rather than assuming the August planning document still describes today's runtime exactly.

The Goal should not redo already-proven work merely because a historical gate document exists.

If current evidence proves a gate is already closed, record that fact and move to the next gate.

If current evidence is stale or incomplete, perform only the smallest required requalification proof.

If CE-L3 remains the first unresolved architecture gate, stop there and return the decision packet.
