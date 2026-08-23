# ADR-073: GitHub Watchdog Review and Dispatch Control Plane

## Status

Accepted.

## Date

2026-08-23

## Classification

Architecture-impacting, documentation-only decision.

## Decision owners

- Human architecture authority accepts future implementation slices and any
  change to merge or release policy.
- Guardian owns policy resolution, durable lineage, authorization, execution
  handoff, result ingestion, and audit evidence.
- The GitHub App is the authenticated GitHub event and API adapter.
- A selected provider, model, or coding harness is an execution dependency;
  none is an authority owner.

## Supersession and relationship to ADR-050

This decision does not supersede ADR-050. ADR-050 remains the GitHub-native,
read-only, deterministic GitHub Actions foundation for campaign packet
validation, PR lineage, eligibility evidence, and dry-run receipts.

ADR-073 accepts the separate future GitHub Watchdog control plane required for
model-backed advisory review and explicitly governed mutation handoff. It
extends the GitHub event/control-plane architecture without changing ADR-050's
deterministic eligibility semantics, read-only workflow implementation, or
merge boundary. A model review cannot repair, replace, or override a failed
deterministic Campaign Control Plane decision.

## Context

Codexify has two adjacent, intentionally distinct rails:

1. ADR-050 evaluates GitHub issue/PR evidence deterministically and performs
   no model invocation, agent dispatch, repository mutation, or merge.
2. The Guardian Build Loop and ADR-020 define the existing Guardian-owned
   coding-worker substrate: bounded intake, Redis queue transport, adapter
   selection, validation and mutation-scope controls, optional isolated
   worktrees, patch artifacts, durable result evidence, and source-lineage
   return.

A first-party Watchdog needs to observe GitHub activity, conduct advisory PR
review, respond to explicit GitHub commands, and eventually request bounded
work from the Build Loop. That work cannot create a second agent authority,
provider router, queue, transcript store, command universe, or GitHub truth
surface. It also must give the operator inspectable, provider-neutral control
of provider/model selection and spending.

## Decision

### 1. Canonical topology

The future Watchdog topology is:

```text
GitHub App
  -> authenticated webhook intake
  -> delivery/event normalization
  -> durable receipt and idempotency boundary
  -> Guardian-owned Watchdog policy evaluation
  -> deterministic Observe | model-backed Review | explicit Mutate dispatch
  -> GitHub Check / bounded review publication
  -> durable Watchdog attempt and result evidence
```

Guardian owns the control plane and all durable semantic decisions. GitHub is
an ingress/event-and-API adapter. A model, provider, adapter, or harness may
perform approved work but cannot define identity, policy, merge authority, or
durable truth.

The webhook route must validate and durably accept a delivery quickly before
acknowledging it. It must not synchronously run a model, a coding harness, or
untrusted repository code inside the delivery request.

### 2. GitHub App is the intended integration family

The first implementation shall use a GitHub App, not a user token or a
browser-side credential as the Watchdog integration family. Its future
webhook boundary requires:

- HTTPS delivery;
- a server-side webhook secret;
- verification of `X-Hub-Signature-256` over the unmodified raw request body
  before any event processing;
- `X-GitHub-Delivery` (or the canonical GitHub delivery identifier) as an
  idempotency input;
- installation, repository, event, action, and triggering-actor identity;
- PR/issue and comment identity when applicable; and
- an immutable target/head SHA for a PR review attempt.

Initial event support is deliberately narrow:

- `pull_request`: `opened`, `synchronize`, and `reopened`;
- `issue_comment`, only when its issue is a pull request and a parsed comment
  matches an approved Watchdog command grammar.

`pull_request_review_comment`, `check_run`, `check_suite`, and `push` are
deferred event families. Their absence must not be papered over by an
implementation that reacts to every GitHub event.

### 3. Three authority classes

The Watchdog has three non-interchangeable operation classes.

| Class | Permitted action | Forbidden action |
| --- | --- | --- |
| Observe | Deterministic GitHub/repository inspection and ADR-050-compatible evidence evaluation. | Model invocation, repository mutation, coding dispatch. |
| Review | Model-backed analysis of an immutable PR snapshot; publish a Check Run and bounded advisory review findings. | Push, branch modification, merge, arbitrary repository-code execution, or allowing PR content to grant authority. |
| Mutate | After explicit authorization, create Guardian execution lineage and dispatch bounded work through the existing Guardian Build Loop. | Direct webhook-to-harness invocation, a parallel coding worker, auto-merge, or implicit release approval. |

An accepted webhook receipt is not a completed review. A completed review is
not a completed mutation. A coding-worker result is not merge approval, and a
GitHub publication is not release proof.

### 4. Provider-neutral model policy and cost control

Model selection is policy-driven, provider-neutral, and inspectable. The
Watchdog architecture does not name or require a concrete provider or model.
At minimum, configuration must distinguish `automated_review`,
`requested_review`, `fix`, and `escalation` policy classes and later permit
repository-specific or installation/account-specific configuration without a
code change.

For every selected attempt, Guardian resolves and persists an immutable policy
snapshot containing at least the policy identifier and version, provider ID,
model ID, supported reasoning/inference posture, maximum attempt count,
fallback policy, escalation policy, model-selection source, triggering
event/command, and repository scope.

The deterministic selection precedence is:

1. authorized invocation override;
2. repository Watchdog policy;
3. installation/account Watchdog policy;
4. system Watchdog default.

An override is valid only after Guardian has authenticated and authorized the
invocation and resolved an allowlisted policy/model alias. It is recorded in
the immutable attempt snapshot. Prompt text, PR content, repository files,
and model output can never select a provider, model, adapter, policy, or
precedence level.

**No silent expensive-model escalation.** A fallback or escalation may use a
different or more expensive model only when an explicit configured escalation
rule or authorized human override permits it. A provider failure must not jump
to an unrestricted premium model. Attempts retain both attempted and final
provider/model identities; when trustworthy provider usage or cost metadata is
available, it is preserved as evidence without inventing cost data for a
provider that does not expose it.

Provider/model identity remains distinct from the execution harness/adapter
identity and from the Guardian run identity. Selecting a model is not
selecting a coding adapter, and selecting an adapter is not an authority grant.

### 5. Idempotency, snapshot binding, and supersession

GitHub delivery identity and Watchdog attempt identity are separate.

- A deterministic delivery identity combines the GitHub delivery identifier
  with installation, repository, event, and action context.
- The durable receipt records whether that delivery was accepted, duplicated,
  rejected, or malformed.
- Redelivery of an accepted delivery may update receipt metadata but must not
  create duplicate semantic work or another model attempt.
- One accepted delivery may produce a bounded set of downstream attempts,
  each with its own `watchdogRunId` and `attemptNumber`.
- An explicit authorized rerun creates a distinguishable new attempt and
  preserves its relationship to the earlier event/attempt; it is not hidden as
  a duplicate delivery.

Every PR Review attempt is bound to the immutable `headSha` it inspected. On
`pull_request.synchronize`, an older queued attempt is cancelled or marked
superseded where cancellation is unavailable. A running attempt that cannot
be safely cancelled completes only as stale/superseded evidence. Its findings
must retain the reviewed SHA and must never become current truth for the new
head. The current Check surface makes reviewed SHA and stale/superseded state
legible.

### 6. Durable evidence and output

Postgres is the canonical durable Watchdog audit and correlation authority.
Redis may be used for queue transport, locks, cancellation, transient
coordination, and progress visibility; it is not the durable Watchdog audit
store. No independent SQLite or file-backed Watchdog truth surface is allowed.

The preferred canonical review publication is a GitHub Check Run tied to the
reviewed SHA. It may show queued/in-progress/completed state, conclusion,
summary, bounded annotations, reviewed SHA, Watchdog attempt identity, an
operator-permitted model identity, and staleness/supersession. Targeted PR
review comments are allowed only for bounded findings. The Watchdog must not
flood a PR with one top-level comment for every internal event or overwrite
human review truth.

### 7. Mutation handoff and human gates

`fix` is categorically different from `review`. A future fix must authenticate
the GitHub event, authorize the actor, resolve immutable repository/PR/head
context, resolve policy for both model and adapter, create Guardian-owned
execution lineage, and dispatch through the existing Guardian Build Loop.

The webhook handler may request that Guardian create a bounded coding task;
it must not directly invoke a coding harness, receive raw harness authority,
or implement a second coding worker. The existing Build Loop controls retain
their role: bounded scope, adapter resolution, queue transport, validation,
mutation-scope guard, worktree isolation where configured, artifacts, durable
result persistence, and return through Guardian-owned lineage.

Architecture-impacting or release-impacting requests retain the existing human
review gate. A comment, a green review, a passing worker, a patch artifact, or
a successful Check Run never implies merge or release authorization.

### 8. Security, permissions, and credential ownership

Pull-request metadata, comments, diffs, and repository files are untrusted
input. Review must not execute PR code by default, leak GitHub/provider or
production credentials to PR-controlled code, treat model output as authority,
or grant mutation because a comment or repository prompt asks for it. Any
future execution of untrusted PR code requires its own sandbox decision.

The first review-only GitHub App posture is least privilege: read only the
repository/PR data and receive the selected webhook events; write Checks and
bounded review/comment output when configured. It does not require contents
write merely to review, and it grants no administration, secret, workflow,
branch, merge, or repository-settings authority by default. Mutation
permissions are a separately authorized execution-path concern.

Watchdog does not become a second GitHub credential authority. GitHub App
installation and credential ownership must ultimately align with Codexify's
canonical Connections authority when that migration is separately accepted and
implemented. Until then, it may reference only the existing governed GitHub
authorization owner; this ADR neither moves legacy credentials nor creates a
credential store.

### 9. Token and release boundary

Future implementation must promote repeated contract-bearing Watchdog values
into bounded canonical registries before they spread across routes, workers,
storage, GitHub output, tests, and UI. Candidate domains are Watchdog
operation, Watchdog run state, review conclusion, supersession reason,
model-selection source, and escalation reason. This ADR adds no runtime
protocol tokens.

The architecture is accepted, but the GitHub Watchdog is not implemented or
release-supported. This decision does not change `00-current-state.md`, the
supported profile, Beta posture, or any proof claim.

## Consequences

- Future implementation has one Guardian-owned event-to-review-to-dispatch
  control plane rather than parallel GitHub, provider, or coding-agent rails.
- Operators can govern and audit model selection, fallback, escalation, and
  available usage/cost metadata without hardwiring a vendor into the contract.
- GitHub receives bounded advisory evidence while deterministic eligibility and
  human merge/release authority remain superior truth surfaces.
- A runtime implementation requires separately scoped slices for intake,
  policy/persistence, model review, GitHub output, and Build Loop dispatch.

## Non-goals

This decision does not register a GitHub App; add a webhook or FastAPI route;
add a worker, Redis queue, database table, migration, settings UI, provider
call, model invocation, Check Run, PR comment, branch operation, commit, push,
merge, auto-fix, or auto-merge. It also does not modify the current GitHub
connector, provider registry, Connections implementation, runtime protocol
tokens, supported profile, or `00-current-state.md`.

## First implementation prerequisite

Implement authenticated, idempotent GitHub App webhook intake with no model
execution.

## Related sources

- [GitHub Watchdog Control Plane](../github-watchdog-control-plane.md)
- [ADR-050: Event-Driven Campaign Control Plane](./050-event-driven-campaign-control-plane.md)
- [Campaign Control-Plane Contract](../campaign-control-plane-contract.md)
- [Guardian Build Loop Doctrine](../guardian-build-loop-doctrine.md)
- [ADR-020: Guardian Mediated Coding Agent Execution Contract](./020-guardian-mediated-coding-agent-execution-contract.md)
- [ADR-022: Guardian Intent Spine and Cross-Surface Control Plane](./022-guardian-intent-spine-and-cross-surface-control-plane.md)
- [Connections Control Plane](../connections-control-plane.md)
- [ADR-071: Connections Control Plane Boundary](./071-connections-control-plane-boundary.md)
- [Current State](../00-current-state.md)
