---
tags:
* architecture
* adr
* campaign-engine
* execution-ledger
* guardian
* governance
aliases:
* ADR-100
* Campaign Continuation Authority Contract
---

# ADR-100: Campaign Continuation Authority Contract

## Status

Accepted

## Date

2026-10-05

## Context

Codexify has durable Campaign and Goal state, canonical atomic coding work orders, durable execution attempts, Guardian-mediated execution, bounded provider and harness adapters, validation and proof surfaces, and recommendation-only next-work-order selection. Campaign Engine contracts already assign campaign state, sequencing, attempts, evaluation, retry/escalation decisions, and closure to the orchestration layer. These mechanisms do not themselves delegate authority to continue from one work order to another.

The current control posture requires human approval before a subsequent atomic work order is authorized. A provider, harness, thread, completed task, recommendation, or successful earlier approval cannot infer that authority. Reconstructing a broader rule from those mechanisms would collapse capability, evidence, and authority, so delegated continuation requires an explicit architecture contract.

This decision defines **Campaign Continuation Authority**: a human-approved, durable, Campaign-scoped envelope under which Codexify may evaluate evidence and authorize bounded retries or downstream work-order dispatch. It is a control-plane authority contract, not an execution implementation. Acceptance of this ADR alone does not enable automatic retries or dispatch.

## Current-Truth Anchors

- `coding_work_orders` remain the canonical atomic work-order identity; `campaign_execution_attempts` and Guardian run/attempt records provide durable execution evidence.
- `/api/coding/orchestrator/next` and Campaign detail's `next_recommended_work_order` are recommendation surfaces. A recommendation is a candidate, not dispatch authority.
- Guardian-mediated coding execution remains the governed execution lane. Guardian controls execution authorization and result ingestion.
- Campaign Engine schemas and contracts preserve distinct Campaign, Task, Attempt, Evaluation, Receipt, Decision Gate, State, and Role Binding identities.
- Existing work-order review fields retain their present meanings. They do not create Campaign Continuation Authority.
- The current runtime remains human-mediated between atomic work orders. This accepted ADR records an architecture contract only; runtime implementation requires separate authorization and proof.
- `docs/architecture/00-current-state.md` remains the release-truth source. No release or runtime claim changes here.

## Decision

Codexify defines explicit, durable, bounded Campaign Continuation Authority. It permits only the actions and scope stated in an active envelope attached to one Campaign, and only while all governing evidence, policy, and stop conditions pass.

### 1. Authority is explicit, durable, scoped, and revocable

An authorized human operator may approve an authority envelope for one identified Campaign. The durable authority record is owned by Codexify/Guardian control-plane state and must retain approval provenance and current validity. Its conceptual contents bind:

- Campaign identity and objective;
- approving actor and approval time;
- allowed task classes, execution lanes, and repository/workspace scope;
- permitted validation and proof classes;
- spend posture and applicable limits;
- whether retry is permitted and its ceiling;
- whether automatic downstream dispatch is permitted;
- explicit stop and escalation reasons;
- revocation state; and
- optional expiry or Campaign terminal boundary.

This ADR does not prescribe final schema fields or storage layout. A future runtime design must use the existing canonical Campaign and Guardian control-plane seams rather than add a competing control plane.

Authority is not global, permanent, inherited by another Campaign, inferred from chat language, implied by a successful prior task, or granted by provider, harness, model, credential, or thread state. An external assistant may act as an operator interface only when a human action is authenticated and recorded through Guardian policy; it cannot mint or widen authority.

### 2. Recommendation is a candidate, not authorization

The continuation path is:

```text
recommend next work order
  -> evaluate active Campaign authority
  -> evaluate proof, dependencies, spend, and stop conditions
  -> record authorization or human escalation
  -> dispatch through the existing Guardian execution lane
```

Existing recommendation behavior remains recommendation-only. The system may authorize the recommended work order only after independently evaluating it against the active envelope and all progression gates below. A recommendation, ranking, or `limit=1` response does not itself authorize dispatch.

### 3. Gates for automatic downstream continuation

Automatic progression is eligible only when every condition is true:

1. The current work order has reached the successful, proven terminal state defined by its governing contract. A status label or executor assertion by itself is insufficient.
2. Required validation and durable proof evidence exist, are attributable to the correct work order and attempt, and satisfy the applicable completion/proof gate.
3. No unresolved blocker, contradictory evidence, or unresolved policy result is attached to the Campaign or work order.
4. Dependencies for the candidate next work order are satisfied under their governing contract.
5. Exactly one next work order is eligible, or an already-governing deterministic policy resolves to exactly one candidate without materially ambiguous choices.
6. That candidate is inside the approved Campaign objective, task classes, lane, repository/workspace scope, proof classes, and spend posture.
7. Downstream dispatch is explicitly permitted by the active envelope.
8. The envelope remains valid, unexpired, and unrevoked at the authorization decision, and no human-only stop boundary applies.

If these conditions do not resolve to one authorized next action, continuation stops for human review. A recommendation policy may rank candidates, but cannot turn an unresolved choice among materially different tasks into authority unless its deterministic selection rule is already governing and unambiguous for that Campaign.

### 4. Proof gate and outcome distinctions

Automatic continuation requires durable evidence sufficient for the applicable acceptance gate. Depending on the work order, evidence may include attempt status, validation commands and results, changed-file scope, commit identity where applicable, runtime proof, completion receipt, evaluator verdict, invariant checks, and required documentation follow-through. Evidence must be linked to canonical Campaign, work-order/task, and attempt identities.

The evaluator and execution contracts continue to govern what evidence is sufficient. “Executor says done” is not proof. The system must keep these outcomes distinct:

- implementation complete;
- validation complete;
- runtime proven;
- Campaign slice complete; and
- release supported.

Satisfying an atomic work-order acceptance gate does not accept an ADR, establish release readiness, or widen a release claim. Architecture acceptance and release readiness remain human-owned.

### 5. Work-order identity survives execution failure

The durable identity chain remains:

```text
Campaign
  -> Work Order / Task
      -> Attempt 1
      -> Attempt 2
      -> Attempt N
```

A Codex thread, Pi invocation, provider session, model call, or harness process is an execution attempt or its transport context, not work-order identity. A mechanical execution failure does not permanently fail or redefine the work order by itself.

Where the active envelope permits retries and the retry ceiling and spend posture allow another attempt, recoverable mechanical failures may receive a new attempt identity against the same durable work-order identity. Examples include provider temporary unavailability, process or thread termination, transport interruption, executor timeout, and recoverable infrastructure failure. Usage or credit exhaustion is retryable only when another attempt remains within the approved spend posture; it never authorizes a new funding route.

Before retry, the future runtime must ingest and reconcile evidence from prior attempts, preserve source lineage, inspect any partial or durable side effects, and continue from durable state when safe. It must not blindly replay side effects already proven to have occurred. If side-effect state is uncertain, evidence conflicts, or safe resumption cannot be established, it must stop for human review. Retry exhaustion also stops for human review.

Validation failure, evaluator `repair_required` or `blocked`, policy denial, scope mismatch, or rejected proof is not a mechanical retry signal. It does not authorize an automatic repair task or a redefinition of the work order. Any repair or scope change must pass its separately governed decision path.

### 6. Retry does not authorize rebinding or substitution

Retries preserve existing routing and binding contracts. Campaign Continuation Authority does not authorize silent provider, model, harness, credential-owner, funding-route, or execution-placement substitution. A retry uses the existing binding unless substitution is already permitted by an applicable routing/binding policy with explicit, auditable rules. Otherwise, substitution requires a human stop and any separately required approval. A new attempt identity is not permission to rebind.

### 7. Human-only stop boundaries

The system must stop and request human review whenever any of these conditions applies:

- a new ADR is required, an existing ADR would be superseded, or accepted architecture meaning would change;
- authority-policy, identity, provenance, persistence, canonical-token, or command boundaries would change beyond the approved Campaign;
- release readiness, support, or release claims would widen;
- spend would exceed the approved budget or posture;
- a new credential or permission grant requires operator action;
- a destructive or irreversible action is required;
- commit, push, merge, release, deployment, publication, deletion, migration, production mutation, or other external mutation is not expressly included as a separate authority in the active envelope and permitted by all governing contracts;
- multiple materially different next tasks are eligible and no deterministic governing policy resolves them unambiguously;
- evidence contradicts the Campaign plan, proof is incomplete or ambiguous, or an unresolved blocker exists;
- the task scope must widen beyond its approved atomic outcome;
- provider or harness rebinding is required but not previously authorized by governing policy;
- the retry ceiling or spend limit is exhausted;
- applicable policy or authority cannot be resolved; or
- the Campaign stopping or terminal condition is reached.

Human escalation is a valid successful control-plane outcome. The system must not continue merely to avoid a blocked or paused Campaign state.

### 8. Execution and promotion authorities remain separate

These permissions are distinct and must not be inferred from one another:

- execute an approved atomic work order;
- retry an execution attempt;
- dispatch the next work order;
- commit;
- push;
- merge;
- release;
- deploy; and
- widen release claims.

An envelope grants only permissions it expressly names, within its scope and only where governing contracts permit them. Campaign Continuation Authority alone grants no commit, push, merge, release, deployment, publication, or destructive-production-mutation authority. The default for each is no automatic action. Architecture acceptance, release readiness, and release-claim widening remain human-owned even when a Campaign includes architecture-impacting work. The system may prepare a next Architecture-Impact Task Spec and stop for review; an envelope cannot pre-approve unknown future architecture decisions.

### 9. Guardian owns authority; Campaign Engine owns orchestration

Guardian remains the execution authority and policy boundary. The durable envelope and each authorization, retry, or escalation decision belong to Codexify/Guardian control-plane state. Campaign Engine evaluates sequencing, attempts, proof, retry/escalation, and closure using that authority; it may propose but does not grant authority independently. Dispatch continues through the existing Guardian execution lane.

Codex, Pi, Claude, other providers, ChatGPT, Cloudflare, GitHub, threads, and model sessions are not authority owners. They may provide bounded execution, operator interface, or evidence roles only under existing contracts.

### 10. Revocation and expiration

The approving human operator must be able to revoke Campaign Continuation Authority. Revocation and expiry fail closed for every new downstream-dispatch and retry decision. Each future authorization decision must resolve the current durable envelope, Campaign boundary, spend posture, and revocation/expiry state; stale prompts or cached recommendations cannot outlive that check.

Revocation does not silently kill an already-running attempt. Its cancellation behavior follows the existing cancellation contract. Until that contract says otherwise, the running attempt may return through Guardian for evidence ingestion, but no subsequent retry or downstream dispatch may be authorized under the revoked envelope. The system must surface the revoked or expired state to the operator.

### 11. Operator truth

Future runtime surfaces must distinguish at least:

- Campaign exists;
- Campaign active;
- continuation authority configured;
- continuation authority currently valid;
- next work order recommended;
- next work order authorized;
- attempt dispatched;
- attempt running;
- attempt failed retryably;
- retry authorized;
- proof pending;
- proof accepted;
- human review required;
- Campaign blocked;
- Campaign complete; and
- continuation authority revoked or expired.

These states must not collapse into an `autonomous=true` boolean. Recommendation, authorization, dispatch, execution, proof, Campaign completion, and release support are separate facts with attributable durable evidence.

## Relationship to Existing Decisions

### ADR-020: Guardian Mediated Coding Agent Execution Contract

Preserved. Guardian continues to own coding intake, request and task scope, policy, identity, source lineage, and result ingestion. Work-order identity remains distinct from request, thread, provider, and attempt identity. This ADR delegates only bounded Campaign continuation through Guardian; it does not make an execution adapter or external assistant an authority owner.

### ADR-028: Execution Ledger Campaign Runner Contract

Preserved except for a narrow replacement of its absolute prohibition on autonomous downstream dispatch. The existing rule becomes: no **unauthorized** autonomous dispatch and no hidden progression; bounded downstream progression is permitted only under an explicit, valid, durable Campaign Continuation Authority envelope and the evidence gates in this ADR. Each authorization and progression decision must remain durably observable. This supersession does not authorize merge automation. Approved plans still authorize attempts, not completion; ADR-028's canonical Campaign/work-order/attempt semantics, proof requirements, review meaning, and separation of execution from promotion remain in force.

### ADR-036 and ADR-037: Provider Adapter and Pi Broker Contracts

Preserved. Continuation authority does not select a provider or bypass provider-adapter, routing, binding, broker-receipt, or no-silent-fallback requirements. ADR-037's posture of Pi as preferred but not mandatory remains unchanged. Provider or harness substitution remains governed by existing policy and any separately required human approval.

### ADR-066: Campaign Engine Runtime Recovery Contract

Extended. Campaign Engine retains ownership of task sequencing, attempts, evaluation, retry/escalation decisions, and Campaign closure, now evaluated within an explicit operator-delegated authority envelope. Guardian remains the authority owner and Campaign Engine may propose but cannot grant. Campaign, Task, Attempt, Evaluation, Receipt, Decision Gate, State, and Role Binding identity semantics remain unchanged; locked binding and no-silent-rebinding rules remain in force.

### ADR-068: Campaign Engine Live Role Execution Contract

Partially superseded only as to its absolute prohibition on automatic retry and automatic downstream continuation. A future runtime may perform those actions only when the active Campaign Continuation Authority expressly permits the action and all proof, retry, binding, routing, spend, and stop gates in this ADR pass. This is architecture permission for a future separately authorized runtime slice, not current runtime behavior. ADR-068's locked binding semantics, no silent provider/model rebinding, evaluator boundary, proof requirements, and prohibition on implicit commit, push, merge, or deployment remain unchanged.

### Guardian Build Loop Doctrine

Extended narrowly. The Human Review Gate remains mandatory at architecture, release, authority, identity, provenance, command, irreversible-action, and other declared escalation boundaries. A human review is not required between every atomic work order when a valid Campaign envelope has delegated that bounded continuation and all gates pass. The doctrine's governed execution lane and review semantics remain intact.

## Non-Goals

This ADR does not:

- implement Campaign Continuation Authority, automatic dispatch, watchers, or automatic retries;
- define final schema fields, tables, migrations, API routes, tokens, or UI;
- change Campaign Runner, Campaign Engine, Guardian, recommendation, dispatch, provider, harness, or execution code;
- create a second task or control plane;
- authorize provider failover, silent rebinding, or credential/funding/placement changes;
- authorize merge, push, release, deployment, or destructive mutation by implication;
- accept architecture, declare release readiness, or widen any support claim;
- modify Campaign Engine schemas, runtime diagrams, Cloudflare Campaign files, release notes, or `docs/architecture/00-current-state.md`; or
- begin CE-03 or any runtime implementation slice.

## Consequences

- A human may delegate bounded continuation once at Campaign scope instead of separately authorizing each eligible atomic task, but only after an implementation enforces this contract.
- Recommendation remains a candidate-selection seam. Guardian-owned authority evaluation must precede every retry or downstream dispatch.
- Mechanical provider/harness failure can be recovered as a new attempt against the same work order only when the approved envelope permits it and the prior attempt is safely reconciled.
- Ambiguous proof, scope, routing, next-task choice, or policy fails closed to human review.
- Architecture and release acceptance and promotion authority remain separate human-owned decisions.
- Acceptance of this ADR records architecture only. It does not make any Campaign self-continuing or alter current runtime truth.

## Next Authorized Slice After Human Acceptance

The next implementation slice establishes the smallest durable runtime representation of Campaign Continuation Authority. It must not implement automatic dispatch or retries. Any subsequent execution slice requires its own authority, proof gates, validation, and review.

## Acceptance Record

Accepted by Resonant Jones on 2026-10-05. This records architecture acceptance only; it does not authorize automatic retries, dispatch, or release-claim changes.

## Related Documents

- [ADR-020: Guardian Mediated Coding Agent Execution Contract](./020-guardian-mediated-coding-agent-execution-contract.md)
- [ADR-028: Execution Ledger Campaign Runner Contract](./028-execution-ledger-campaign-runner-contract.md)
- [ADR-036: Campaign Runner Provider Adapter Contract](./036-campaign-runner-provider-adapter-contract.md)
- [ADR-037: Campaign Runner Pi Provider Broker](./037-campaign-runner-pi-provider-broker.md)
- [ADR-066: Campaign Engine Runtime Recovery Contract](./066-campaign-engine-runtime-recovery-contract.md)
- [ADR-068: Campaign Engine Live Role Execution Contract](./068-campaign-engine-live-role-execution-contract.md)
- [Guardian Build Loop Doctrine](../guardian-build-loop-doctrine.md)
- [Campaign Engine Contract](../campaign-engine-contract.md)
- [Execution Ledger Gate Artifacts Contract](../execution-ledger-gate-artifacts-contract.md)
- [00 Current State](../00-current-state.md)
