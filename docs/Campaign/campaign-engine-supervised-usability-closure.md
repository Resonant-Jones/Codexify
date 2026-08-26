# Campaign Engine Supervised-Usability Closure

## Purpose

This document freezes the dependency order between the current provider-free
Campaign Engine runtime and a future bounded live Campaign Engine that can run
three dependency-ordered real Tasks without admitting unrelated autonomy
work. It records what is already true, what remains to be proven, and the
sequence of gates required to cross from the present one-Task provider-free
lifecycle to a supervised Campaign Engine that an operator can use on real
Codexify work.

It is a planning artifact only. It does not modify Campaign Engine runtime
behavior, schemas, Guardian authority, the Pi invocation boundary, providers,
worker/queue scheduling, database persistence, UI surfaces, test posture, or
release claims. No runtime, schema, Guardian, provider, Pi, worker, database,
API, frontend, or test file is authorized for modification by this document.

## Scope

In scope:

- the dependency chain from the current `main` provider-free Campaign Engine
  runtime to a three-Task supervised live Campaign proof;
- the two usability milestones (single-task supervised utility and
  multi-task supervised campaign utility) and the gates between them;
- the relationship to the existing accepted ADR-066 and ADR-068 contracts;
- the stopping conditions that close this closure Campaign.

Out of scope (explicitly parked until after the second milestone passes, and
not introduced by this document):

- automatic retry;
- automatic repair;
- provider failover;
- dynamic provider/model rebinding;
- parallel Task execution;
- background / overnight execution;
- worker / queue scheduling;
- database-backed Campaign persistence unless a future gate proves it
  necessary for the minimum checkpoint contract;
- automatic commit, push, PR creation, merge, or deployment;
- generalized arbitrary-repository execution;
- a Campaign Engine UI;
- a visual DAG editor;
- advanced budget optimization or provider arbitrage;
- unattended architecture decisions.

## Campaign Metadata

- Campaign ID: `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE`
- Slug: `campaign_engine_supervised_usability_closure`
- Date: 2026-08-26
- Sequence: 001
- Owner: resonant_jones
- Risk: MED
- Branch strategy: docs-only planning on the current `main`; no code
  branches opened until a gate slice is authorized.
- Depends on:
  - ADR-066 Campaign Engine Runtime Recovery Contract (accepted 2026-08-13)
  - ADR-068 Campaign Engine Live Role Execution Contract (accepted 2026-08-14)
  - Pi Invocation Boundary Contract (`docs/architecture/pi-invocation-boundary-contract.md`)
  - the current provider-free Campaign Engine runtime already on `main`

## Current Truth (What Is Already Real)

These statements are anchored to existing contracts and merged code on the
current `main`. They are not aspirations.

- The `campaign-engine/v0` schemas exist under `codex_runner/schemas/campaign_engine/`.
- The deterministic provider-free Campaign Engine runtime exists on `main`
  (merged 2026-08-13 via PR #709) and emits one runnable Task, a synthetic
  Executor Attempt, a synthetic Evaluation, an evidence Receipt, and a final
  CampaignState snapshot.
- Auditor / Executor / Evaluator RoleBindings are locked per Campaign;
  exactly three canonical roles exist; no silent provider/model switching or
  runtime rebinding is authorized.
- Source-selection lineage support exists; lineage grants no execution
  permission.
- ADR-066 reconciles Campaign Engine placement between DLG/ARP
  source-selection lineage and Guardian-authorized bounded execution seams.
- ADR-068 authorizes exactly one bounded live Campaign Engine lifecycle:
  provider-free Auditor, one live Executor invocation, one live Evaluator
  invocation, one isolated proof target, with Guardian permission resolution,
  immutable invocation authorization, exact binding-to-provider/model
  identity verification, and explicit fail-closed boundaries.
- The Guardian-owned one-shot Pi invocation rail (`guardian/pi/invocation.py`,
  `guardian/pi/contracts.py`) provides permission validation, target-posture
  enforcement, provider/model identity attestation, bounded receipts, and no
  silent fallback.

## Current Constraints (What Is Not Yet Authorized)

ADR-068 explicitly does not yet authorize any of the following. This document
does not amend ADR-068, does not implement any of them, and does not widen
release claims.

- multi-task scheduling or progression;
- automatic retry;
- automatic repair;
- background execution;
- queue or worker integration;
- database persistence of Campaign state;
- UI or API surface for Campaign Engine;
- automatic commit, push, merge, PR creation, or deployment;
- generalized arbitrary-repository execution.

The current Campaign Engine runtime still deliberately executes exactly one
runnable Task and synthesizes its Executor Attempt and Evaluation. That
is by design, not a defect.

## Usability Milestones

The closure Campaign splits into two usability milestones so that operator
friction is observed before adding scheduling semantics.

### Milestone A — Single-task supervised utility

A predefined Campaign containing exactly one Task can invoke:

1. the provider-free Auditor;
2. one Guardian-authorized live Executor invocation;
3. one independent read-only live Evaluator invocation;
4. one final Evaluation, Receipt, and CampaignState;

and return control to the operator on `repair_required` or `blocked` without
requiring the operator to feed the Task in by hand. At this point Campaign
Engine becomes useful for individual Task Specs even though the operator
still feeds Tasks one at a time.

Milestone A does not authorize multi-task execution. It does not introduce
scheduling. It does not introduce any new autonomy.

### Milestone B — Multi-task supervised campaign utility

A bounded Campaign containing multiple dependency-ordered Tasks can:

1. determine the next eligible Task deterministically;
2. run its live Executor;
3. run its live Evaluator;
4. publish Attempt / Evaluation / Receipt evidence;
5. checkpoint CampaignState;
6. advance only after an acceptable verdict;
7. stop safely on human-intervention conditions;
8. preserve enough campaign evidence to explain what happened;
9. complete a three-Task disposable-worktree proof without the operator
   manually initiating each Task.

This is the target for calling Campaign Engine "usable as a campaign runner."

### Milestone stopping posture

- At the Milestone A stopping condition, stop and use the system there.
  Run several real but disposable Codexify Task Specs through the
  one-task lifecycle. The purpose is to discover operational friction
  from actual use before adding scheduling semantics.
- Do not interpret Milestone A as autonomous Campaign support.
- Only after Milestone B closes does this closure Campaign end.

## Dependency Chain

The last leg executes in this order:

```text
Guardian/Pi live execution proof
        |
        v
Campaign live Executor
        |
        v
Campaign live Evaluator
        |
        +------> Milestone A: useful for single Task Specs
        |
        v
Multi-task architecture decision
        |
        v
Dependency-ordered runtime
        |
        v
Three-Task live proof
        |
        +------> Milestone B: usable Campaign Engine
```

The closure Campaign has six gates, ordered CE-L0 through CE-L5.

## Gates

### CE-L0 — Qualify the existing live invocation substrate

Purpose:

Prove the already-merged Guardian/Pi execution seam independently before
coupling Campaign Engine to it. If this gate fails, repair the provider /
Guardian / Pi seam only. Do not modify Campaign Engine to compensate for a
broken execution substrate.

Required proof:

- current `main`;
- one operator-selected provider/model;
- Guardian authorization resolves successfully;
- actual provider/model/harness identity is captured;
- actual identity matches the requested locked identity;
- exactly one provider invocation occurs;
- isolated disposable target only;
- no fallback;
- no retry;
- no main-worktree mutation;
- no secret material in proof artifacts;
- a bounded receipt/result survives validation.

Exit condition: `GUARDIAN_PI_LIVE_READY`.

### CE-L1 — Replace the synthetic Executor with one Guardian-authorized live Executor

Purpose:

Introduce the first real Campaign Engine execution without changing
sequencing yet.

Required behavior:

- retain exactly one runnable Campaign Task;
- retain the provider-free Auditor;
- derive expected provider/model/harness identity from the locked Executor
  RoleBinding;
- construct or reference an immutable Guardian authorization;
- dispatch exactly one bounded Executor invocation through the existing
  approved execution seam;
- operate only on an isolated disposable proof target;
- enforce declared allowed file paths;
- capture actual runtime identity;
- fail closed on identity mismatch or missing identity;
- record the live Attempt using the existing `campaign-engine/v0` live-mode
  schema fields authorized by ADR-068;
- record changed-file evidence and validation evidence where mutation occurs;
- keep:
  - `commit_performed=false`
  - `merge_performed=false`
  - `durable_ingestion_performed=false`
- perform no automatic retry or fallback.

Proof gate:

A single predefined Task produces a schema-valid live Executor Attempt and
Guardian/Pi receipt backed by one real provider invocation.

Exit condition: `LIVE_EXECUTOR_PROVEN`.

### CE-L2 — Replace the synthetic Evaluation with one independent live Evaluator

Purpose:

Close the first real Executor -> Evaluator lifecycle.

Required behavior:

- Evaluator uses its own locked RoleBinding;
- exact expected provider/model identity is enforced;
- Evaluator is Guardian-authorized read-only;
- Evaluator receives only bounded evidence:
  - Task objective;
  - acceptance criteria;
  - source-context reference;
  - Executor Attempt;
  - changed-file list;
  - bounded diff/snapshot;
  - validation command and output;
  - Executor identity evidence;
- Evaluator receives no write permission;
- Evaluator cannot repair;
- Evaluator cannot trigger retry;
- Evaluator cannot change RoleBindings;
- Evaluator returns one current canonical verdict:
  - `passed`
  - `passed_with_advisories`
  - `repair_required`
  - `blocked`
- `repair_required` and `blocked` return control to the operator;
- live Evaluation records:
  - `read_only_assertion=true`
  - `mutation_performed=false`
  - `independent_model_judgment=true`
- Receipt and CampaignState bind Executor and Evaluator evidence together.

Proof gate:

One real disposable Task completes:

```text
Campaign -> live Executor -> live Evaluator -> Receipt -> CampaignState
```

with exact identity evidence and no operator intervention during the
successful path.

Exit condition: `SINGLE_TASK_SUPERVISED_USABLE`.

### Milestone A stopping condition

Stop and use the system here before adding more autonomy. Run several real
but disposable Codexify Task Specs through the one-task lifecycle. The
purpose is to discover operational friction from actual use before adding
scheduling semantics.

Do not interpret Milestone A as autonomous Campaign support.

### CE-L3 — Authorize dependency-ordered multi-task progression

Purpose:

Create the minimum architecture decision required to move beyond ADR-068's
explicitly single-Task proof boundary. This must be an architecture-impact
decision before implementation.

The decision must define:

- Task dependency representation;
- eligibility rules for the next runnable Task;
- campaign progression rules;
- Task terminal states;
- what Evaluation verdict permits advancement;
- what verdict requires human intervention;
- campaign stop conditions;
- campaign completion semantics;
- campaign checkpoint semantics;
- restart/resume expectations;
- whether intermediate state remains filesystem-backed or requires another
  durable control-plane seam;
- exact relationship to ADR-028 / ADR-050 rather than creating a parallel
  campaign truth store.

Initial posture carried into the decision:

- `passed` -> advance;
- `passed_with_advisories` -> advance while retaining advisory evidence;
- `repair_required` -> stop for operator;
- `blocked` -> stop for operator;
- no automatic retry;
- no automatic repair;
- no silent provider/model rebinding.

Do not authorize background/overnight execution, provider failover, or
automatic Git mutation as part of this decision.

This gate is intentionally identified as the future point where a new ADR
or explicit accepted amendment will be required before multi-task runtime
semantics change.

Exit condition: `MULTI_TASK_PROGRESSION_AUTHORIZED`.

### CE-L4 — Implement dependency-ordered supervised Campaign progression

Purpose:

Turn Campaign Engine from a one-Task lifecycle into an actual bounded
campaign runner.

Required behavior:

Given multiple Tasks with declared dependencies:

1. determine the next eligible Task deterministically;
2. run its live Executor;
3. run its live Evaluator;
4. publish Attempt / Evaluation / Receipt evidence;
5. checkpoint CampaignState;
6. advance only when policy allows;
7. stop on human-gate conditions;
8. never run a dependent Task before its prerequisites pass;
9. never silently rebind provider/model identities;
10. never perform an automatic retry.

The first implementation must remain serial. Do not implement parallel DAG
execution yet.

Proof gate:

A deterministic fixture with at least three dependency-ordered Tasks
advances correctly through all three while preserving ordered Attempt,
Evaluation, Receipt, and CampaignState lineage.

Exit condition: `MULTI_TASK_RUNTIME_PROVEN`.

### CE-L5 — Run the three-Task real Campaign proof

Purpose:

Cross the usability threshold with real work.

Proof shape:

- current `main` source;
- isolated disposable Codexify worktree or repository copy;
- one bounded Campaign;
- three atomic Task Specs;
- explicit dependency order;
- locked Auditor / Executor / Evaluator bindings;
- real provider-backed Executor;
- real independent Evaluator;
- no manual Task initiation between successful Tasks;
- bounded file scopes;
- exact validation for every Task;
- durable/readable Campaign evidence;
- no auto-commit, push, merge, PR creation, or deployment.

Required successful-path proof:

```text
Campaign starts
    |
Task 1 -> Executor -> Evaluator -> PASS
    |
Task 2 -> Executor -> Evaluator -> PASS
    |
Task 3 -> Executor -> Evaluator -> PASS
    |
Campaign completed
```

Required safe-interruption proof:

```text
Task N -> Evaluator -> REPAIR_REQUIRED
    |
Campaign stops
    |
Operator intervention required
```

Exit condition: `CAMPAIGN_ENGINE_SUPERVISED_USABLE`.

When CE-L5 passes, stop the closure Campaign. At that point Campaign Engine
is considered usable for supervised development campaigns.

Do not immediately expand Campaign Engine into unattended autonomy. Use the
system for real Codexify work and collect friction before admitting further
capabilities.

## Acceptance Criteria

The closure Campaign is acceptable only when all of the following hold:

- this document exists at `docs/Campaign/campaign-engine-supervised-usability-closure.md`;
- it freezes two usability milestones (Milestone A and Milestone B);
- it freezes gates CE-L0 through CE-L5 in dependency order;
- current provider-free runtime truth is stated accurately;
- ADR-068's single-Task live proof boundary is preserved;
- Guardian remains the authorization boundary;
- Pi / provider execution remains a substrate rather than an orchestration
  authority;
- automatic retry and repair remain explicitly deferred;
- multi-task execution is not treated as already authorized;
- CE-L3 requires architecture authorization before multi-task implementation;
- the final supervised usability proof requires three dependency-ordered real
  Tasks;
- the successful path requires no manual initiation between Tasks;
- `repair_required` and `blocked` remain human gates;
- no auto-commit / push / merge / PR / deploy capability is introduced;
- no Beta / release claim is widened;
- the stopping condition is explicit: close this Campaign after CE-L5 passes;
- the only file modified is `docs/Campaign/campaign-engine-supervised-usability-closure.md`;
- `docs/architecture/00-current-state.md` is unchanged;
- no ADR is modified, added, or superseded.

## Invariants (Preserved By This Document)

- Guardian remains the authority boundary.
- Campaign Engine owns orchestration, not provider execution.
- Providers own no Campaign state.
- RoleBindings remain locked.
- No silent rebinding or fallback.
- DLG / ARP lineage grants no execution permission.
- Receipts are evidence, not approval.
- Evaluator remains read-only.
- Human authority remains required for `repair_required` / `blocked` and for
  architecture decisions.
- Release claims follow `docs/architecture/00-current-state.md`.

## Explicitly Excluded From This Closure Campaign

The following items do not belong in this chain and must not enter as new
work unless they:

1. block one of the gates above;
2. reveal an architectural inconsistency;
3. materially simplify one of the gates above; or
4. prove the dependency order above is wrong.

Everything else is parked.

- automatic retry;
- automatic repair;
- provider failover;
- dynamic rebinding;
- parallel Task execution;
- background / overnight execution;
- worker / queue scheduling;
- database-backed Campaign persistence unless CE-L3 proves it necessary for
  the minimum checkpoint contract;
- automatic commit, push, PR creation, merge, or deployment;
- generalized arbitrary-repository execution;
- Campaign Engine UI;
- visual DAG editor;
- advanced budget optimization;
- provider arbitrage;
- unattended architecture decisions.

These are maturation capabilities, not prerequisites for first usefulness.

## ADR Alignment

This document is aligned with the existing accepted contracts:

- ADR-066 Campaign Engine Runtime Recovery Contract (accepted 2026-08-13);
- ADR-068 Campaign Engine Live Role Execution Contract (accepted 2026-08-14);
- the Pi Invocation Boundary Contract (`docs/architecture/pi-invocation-boundary-contract.md`).

This document does not modify, supersede, or amend any accepted ADR. It does
not implement any new runtime behavior. It does not widen any release claim.
It is a planning artifact only.

## Documentation Follow-Through

- This document is the single source of truth for the closure Campaign.
- `docs/architecture/00-current-state.md` is unchanged by this planning
  task because this document changes no runtime or release posture.
- ADRs are unchanged by this planning task because no accepted architecture
  changed.
- Future runtime slices (CE-L0 onward) require their own live proof and may
  not cite this planning document as implementation evidence.
- A separate ADR or accepted amendment will be required at CE-L3 before
  multi-task runtime semantics change.

## Closing Condition

The closure Campaign closes only when CE-L5 passes. Until then, this
document is the active gating plan for Campaign Engine supervised usability.

No other Campaign Engine work enters this closure Campaign unless it meets
one of the four inclusion conditions above.