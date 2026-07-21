---
tags:
* architecture
* adr
* guardian
* delegation
* execution-system
* provenance
  aliases:
* ADR-048
* Guardian Three-Channel Delegation Topology
---

# ADR-048: Guardian Three-Channel Delegation Topology

## Status

Accepted as the architecture-record portion of GitHub Issue #609. This ADR
records the target topology and its ownership boundaries only. It does not
implement any channel, adapter, migration, runtime behavior, or release claim.

## Date

2026-07-21

## Classification

Requires new ADR.

## Context

Codexify has a Guardian-owned coding-worker execution substrate with adjacent
Pi invocation, Campaign Runner, Codex Runner, provider-adapter, queue, worker,
validation, lineage, and result-return surfaces. Those surfaces currently
describe related parts of a governed build loop, but they do not yet establish
whether Pi, Codex, and Claude are execution systems with distinct identities or
provider choices behind one runner.

That distinction matters for authority, routing, evidence, migration, and
failure handling. The deterministic campaign/build loop needs one explicit
owner. Native execution systems need room to use their own threads, tools,
subagents, and internal plans without acquiring Guardian authority. Model or
provider selection must remain metadata and capability context rather than
silently changing the identity of the execution system that Guardian selected.

The governing context is the Guardian Build Loop doctrine, the Pi Invocation
Boundary Contract, the delegation runtime and operator contracts, the
current-state release truth doctrine, and the existing authority, identity,
provenance, and result-return invariants.

## Decision

Guardian adopts three independent, peer execution channels:

1. **Pi channel** — owns the deterministic campaign/build loop, including gate
   sequencing, bounded retries, validation, receipts, and evidence posture.
2. **Codex channel** — receives a canonical Task Spec from Guardian and
   executes through native Codex threads, tools, and subagents. Codex owns its
   internal execution strategy within the bounded Task Spec.
3. **Claude channel** — receives a canonical Task Spec from Guardian and
   executes through native Claude Code capabilities. Claude owns its internal
   execution strategy within the bounded Task Spec.

Pi, Codex, and Claude are peer execution systems under Guardian. They are not
interchangeable provider flags behind one generic Runner abstraction.

Guardian remains responsible for delegation policy, execution-channel
selection, authority boundaries, source and result lineage, review posture,
normalized result return, and durable recordkeeping. An execution channel may
receive bounded authority to perform work, but it never owns Guardian authority
or the durable truth of the delegation.

## Canonical topology

```text
Human authority
  -> Guardian
       -> Pi channel
       -> Codex channel
       -> Claude channel
  <- normalized result envelopes, evidence, and review posture
```

The outbound relationship is a Guardian-governed delegation decision. The
return relationship is a Guardian-owned review and recordkeeping path. It does
not mean that a native channel may publish directly into the originating
thread, alter acceptance, or promote its own evidence into authority.

## Responsibilities by layer

| Layer | Responsibility | Boundary |
|---|---|---|
| Human authority | Defines or approves the governing intent and retains final authority for architecture, consequential mutation, and release claims. | Human approval is not replaced by channel output, a commit, a receipt, or a passing validation command. |
| Guardian | Creates or validates the canonical Task Spec; selects the execution channel; enforces policy, identity, scope, lineage, review, return, and durable recordkeeping. | Guardian delegates bounded authority and retains authority ownership. |
| Pi channel | Runs the deterministic campaign/build loop; sequences gates; applies bounded retries; coordinates validation; and maintains receipts and evidence posture. | Pi is a peer execution system, not the universal broker or the owner of Guardian policy. |
| Codex channel | Consumes the canonical Task Spec and executes through native Codex threads, tools, and subagents using its own internal strategy. | Codex may not widen scope, redefine acceptance, self-promote trust, or claim release readiness. |
| Claude channel | Consumes the canonical Task Spec and executes through native Claude Code capabilities using its own internal strategy. | Claude may not widen scope, redefine acceptance, self-promote trust, or claim release readiness. |
| Underlying model or provider | Supplies model capability selected or recorded within the channel execution context. | Model identity does not establish execution-system identity, Guardian authority, or release status. |
| Result and evidence boundary | Carries native records, receipts, commits, patches, artifacts, validation output, and review posture back to Guardian for normalization and durable lineage. | Evidence remains evidence; it is not authority without Guardian review and the applicable human gate. |

The Pi channel may use different underlying models without changing its channel
identity. The same separation applies to Codex and Claude: the native
execution-system identity remains distinct from any underlying model identity.

## Execution-system identity versus model identity

Execution-system identity answers **which governed execution system was
selected**: Pi, Codex, or Claude. Model identity answers **which model or
provider capability was used inside that system**. These are separate fields of
architecture and provenance.

- Guardian routes to an execution channel, not to an untyped model flag.
- A model substitution within an allowed channel does not turn Pi into Codex,
  Codex into Claude, or Claude into Pi.
- Channel-native tools, threads, subagents, receipts, and internal control
  behavior belong to the selected execution system even when model capability
  changes.
- Result records must preserve both identities when implementation defines the
  corresponding envelope fields.
- An adapter represents an execution-system boundary and its native contract;
  it must not collapse peer channel identity into generic provider selection.

## Common Task Spec boundary

Guardian is the authority for the canonical Task Spec. The Task Spec is the
bounded handoff contract and defines, at minimum:

- goal;
- scope;
- acceptance criteria;
- validation requirements;
- non-goals;
- review posture; and
- source and result lineage.

Guardian snapshots or otherwise binds the Task Spec to the authorized request
before delegation. Each channel may choose its own internal execution plan,
thread layout, tool sequence, subagent strategy, retry interpretation, or
intermediate artifacts, subject to the Task Spec and Guardian policy. No channel
may silently widen the Task Spec, redefine acceptance, or convert an internal
plan into new authority.

The canonical Task Spec is a shared boundary, not a demand that the three
execution systems expose identical native APIs or internal workflows.

## Result normalization boundary

Each channel may produce native session records, receipts, commits, patches,
artifacts, validation results, and other evidence. Guardian owns the boundary
that interprets those outputs, checks lineage and scope, applies review posture,
and returns a normalized result to the originating system or human authority.

The future shared `Guardian Delegation Result Envelope` is the intended
normalization contract. Its schema is not finalized by this ADR and is deferred
to follow-up issue 1. The boundary must preserve, at minimum, the selected
execution-system identity, underlying model identity when available, Task Spec
and lineage references, outcome, changed artifacts, validation and receipt
evidence, review posture, and remaining human action.

A native result is not complete merely because a channel returned, a session
ended, a commit exists, or validation passed. Guardian must reject, block, or
escalate results whose scope, lineage, provenance, or review requirements are
ambiguous. Normalization must not erase the fact that evidence came from a
delegated execution system.

## Current truth

The following remains true after accepting this ADR:

- Codexify has a Guardian-owned coding-worker execution substrate.
- The current adapter registry exposes the Pi lane and the legacy
  `pi_codex_runner` alias.
- Direct Codex and Claude delegation channels are not currently supported
  runtime truth.
- Codex-Runner currently contains deterministic campaign execution, Pi Loop
  Manager, provider adapters, and Guardian preflight surfaces.
- Guardian does not yet route to three production-ready peer channels.
- Native Codex delegation is not yet integrated.
- Native Claude delegation is not yet integrated.
- The Pi-owned deterministic runner has not been renamed or separated from
  Codex and Claude provider code.
- No shared Guardian Delegation Result Envelope has been finalized.
- No Codex-Runner migration has occurred.
- Existing runtime and release claims remain unchanged by this ADR.

In particular, this accepted architecture decision is not evidence that native
Codex or Claude delegation is shipped, that the three-channel topology is
runtime-supported, or that Guardian delegation is part of the current release
promise.

## Deferred implementation

Implementation is intentionally deferred to separate atomic issues and
commits. This ADR does not:

- add adapters or routing;
- change queue, worker, acceptance, persistence, provider, or runtime
  behavior;
- rename repositories or runtime surfaces;
- remove or decouple existing provider code;
- change the current adapter registry or aliases;
- finalize a result-envelope schema;
- add native Codex or native Claude integration;
- change command-bus semantics for long-running delegated execution; or
- widen supported-release or release-readiness claims.

The existing runtime remains the compatibility baseline until implementation
work proves a successor path and the migration contracts are accepted.

## Consequences

Positive consequences:

- Guardian routing can distinguish execution-system identity from model or
  provider identity.
- Pi can own deterministic gate execution without making native Codex or
  Claude internal workflows conform to a generic Runner loop.
- Codex and Claude can use native capabilities while remaining bounded by one
  canonical Task Spec and Guardian-owned result return.
- Evidence, provenance, review posture, and durable recordkeeping remain
  comparable across peer channels without pretending their native sessions are
  identical.

Costs and risks:

- Guardian and future adapters must preserve more explicit channel identity and
  provenance fields.
- Compatibility and migration work must separate existing Codex-Runner
  responsibilities before legacy coupling can be removed safely.
- A common Task Spec and result envelope require deliberate contract design;
  normalization cannot be treated as a superficial provider wrapper.
- Three peer channels increase operational and proof surface area. Each channel
  needs independent capability, failure, lineage, and review evidence.

## Rejected alternatives

- **Keep Codex and Claude as interchangeable provider flags behind the
  deterministic Runner.** Rejected because it collapses execution-system
  identity, native capabilities, ownership, and evidence semantics into a
  provider choice.
- **Make Pi the universal broker for all execution systems.** Rejected because
  Pi owns the deterministic campaign/build-loop channel; it does not own the
  identity, internal strategy, or authority boundary of Codex or Claude.
- **Allow native execution systems to own Guardian authority or durable truth.**
  Rejected because delegation grants bounded authority only. Guardian remains
  the policy, lineage, review, normalized-return, and durable-record owner.
- **Rename or delete existing runtime surfaces before migration contracts
  exist.** Rejected because compatibility, alias behavior, proof, rollback, and
  operator recovery would become ambiguous before a successor path is proven.

## Migration posture

Migration is additive and compatibility-first:

1. Define the shared Task Spec and normalized result contract before changing
   existing runtime ownership.
2. Add and prove native Codex and Claude channels behind explicit Guardian
   selection without changing the supported runtime claim.
3. Reframe the Pi adapter around deterministic campaign/build-loop ownership
   while preserving existing aliases during the compatibility window.
4. Produce a Codex-Runner migration and naming plan that identifies ownership,
   import, route, queue, worker, provider, record, and rollback boundaries.
5. Remove legacy provider coupling only after compatibility, migration, and
   proof obligations are complete.

No rename, deletion, alias removal, or provider extraction is authorized by
this ADR alone.

## Invariants

- Guardian owns authority, routing, lineage, review, return, and durable
  records.
- Execution channels receive bounded authority, never authority ownership.
- The canonical Task Spec defines goal, scope, acceptance criteria, validation,
  non-goals, review posture, and lineage.
- Each channel may choose its internal execution plan.
- No channel may silently widen its Task Spec.
- Native session records, receipts, commits, patches, and artifacts remain
  evidence, not authority.
- Direct human use of Codex or Claude is not automatically Guardian-owned
  lineage.
- Command Bus semantics remain separate from long-running delegated execution.
- Current supported runtime behavior must not be described as if this topology
  is already shipped.
- No runtime, queue, worker, adapter, acceptance, persistence, or release
  contract may change in this task.
- Execution-system identity must remain distinct from underlying model
  identity.

## Follow-up issue sequence

1. Define the shared canonical Task Spec and Guardian Delegation Result
   Envelope.
2. Add a native Codex delegation adapter and proof surface.
3. Add a native Claude delegation adapter and proof surface.
4. Reframe the Pi adapter as the deterministic campaign/build-loop channel.
5. Create the Codex-Runner migration and naming plan.
6. Remove legacy provider coupling only after compatibility and proof are
   complete.
