# Campaign Engine Contract (v0)

## Purpose

Campaign Engine is the orchestration authority responsible for planning, executing, evaluating, and closing bounded development campaigns within Codexify.

It separates:
- planning (Auditor)
- execution (Executor)
- evaluation (Evaluator)
- authority (Human / Guardian)

Providers (Codex, DeepSeek, etc.) are execution substrates only and do not own orchestration state or decisions.

---

## Governing Decision

This contract is governed by two accepted decisions:

- [ADR-066: Campaign Engine Runtime Recovery Contract](./adr/066-campaign-engine-runtime-recovery-contract.md), accepted 2026-08-13, fixes the current Campaign Engine placement between DLG/ARP source-selection lineage (lineage only) and Guardian-authorized bounded execution seams.
- [ADR-067: Campaign Engine Live Role Execution Contract](./adr/067-campaign-engine-live-role-execution-contract.md), accepted 2026-08-14, authorizes exactly one bounded live Campaign Engine role-execution lifecycle under Guardian permission resolution and fail-closed identity verification, with backward-compatible conditional live-mode branches added to RoleBinding, Attempt, Evaluation, and Receipt.

The current Campaign Engine placement (ADR-066):

```text
DLG / Agent Reading Packet
        |
        | source-selection lineage only
        v
Campaign Engine
        |
        | campaign/task/role orchestration
        v
Guardian authority and policy
        |
        | authorized bounded execution
        v
Pi / Coding Loop / Tool Capability seams
        |
        | execution evidence
        v
Attempt -> Evaluation -> Receipt
```

Reading: DLG/ARP supplies source-selection lineage only and grants no execution authority; Campaign Engine owns campaign/task/role orchestration; Guardian remains the authority and policy boundary; Pi, Coding Loop, and tool-capability seams provide authorized bounded execution; Attempt -> Evaluation -> Receipt carries execution evidence.

---

## Execution Modes

Campaign Engine operates in two bounded execution modes, both under the same Guardian authority boundary:

1. **Provider-free mode** (current implementation, merged via PR #709): every Attempt, Evaluation, and Receipt is a synthetic record; zero provider calls, zero source mutations, zero decision gates. The `execution_mode` discriminator on Attempt and the `evaluation_mode` discriminator on Evaluation default to `provider_free` if absent; all provider-free fixtures validate unchanged.
2. **Authorized live mode** (authorized by ADR-067, not yet implemented): one bounded live Executor invocation through an approved execution seam under Guardian permission resolution; one bounded live Evaluator invocation; exact binding-to-provider/model identity verification; fail-closed on identity mismatch, capability ineligibility, target-path escape, mutation outside allowed paths, unauthorized Evaluator mutation, malformed provider result, harness transport failure, or secret leakage.

Campaign Engine never bypasses Guardian authority or policy. Campaign Engine may request; Guardian grants or denies. Mode selection is operator/Guardian policy, never a Campaign Engine self-decision.

---

## Core Entities

Define the following canonical entities:

### Campaign
A bounded execution arc around a single objective.

### Task
An atomic, independently testable unit of work.

### Attempt
A single execution or evaluation pass by a provider.

### Evaluation
A structured verdict against defined criteria.

### Receipt
A durable record of execution or evaluation.

### Decision Gate
A point requiring operator or policy intervention.

---

## Role Model

Campaign Engine defines three roles:

- Auditor
- Executor
- Evaluator

Rules:
- Each role binds to exactly one model at runtime.
- Maximum of three distinct models per campaign.
- Roles may share a model.
- Bindings are locked for the duration of a campaign.
- Rebinding requires explicit operator approval and creates a new binding revision.

---

## Model Binding Invariants

- No silent provider or model switching during retries.
- All attempts inherit the role’s locked binding.
- Rebinding must be recorded with lineage.

---

## Lifecycle Ownership

Campaign Engine owns:

- campaign state
- task sequencing
- execution attempts
- evaluation results
- retry and escalation decisions
- campaign closure

Providers do not own state.

---

## Relationship to Codex Runner

- Existing `codex_runner/` remains the execution harness.
- Campaign Engine is the orchestration layer above it.
- Campaign Engine composes with, and does not duplicate, the existing execution seams: the Guardian Build Loop umbrella, the Pi Invocation Boundary and ADR-063 Pi Loop Manager receipt-as-evidence boundary, the Coding Loop execution substrate, the Agent Tool Loop / command-bus lane, and the Provider Tool-Turn / Provider Capability seams.
- No behavior changes are introduced in this task.
- This document defines future direction only.

---

## Source-Selection Lineage

Campaign runs record source-selection lineage: which sources were selected, resolved, excluded, stale, or contradictory for the campaign and its tasks, using the Agent Reading Packet contract (or an equivalent bounded receipt). DLG document identity, graph metadata, and ARPs provide lineage only and grant no execution permission, runtime authority, or approval.

---

## Invariants

- Tasks remain atomic.
- Repository must be clean before execution.
- Allowed file scopes must be enforced.
- Receipts are required for all execution and evaluation steps.
- Human authority is required for irreversible or architectural decisions.

---

## Proof Surface

For this task:

- Document must exist and be readable.
- No runtime behavior is changed.
- Existing tests must continue to pass.

---

## ADR Impact

Classification: Governed by accepted ADR-066.

Reason:
ADR-066 (Campaign Engine Runtime Recovery Contract) reconciles the Campaign Engine contract with the current DLG/ARP source-selection lineage, Guardian authority, and Pi / Coding Loop / tool-capability execution seams, and establishes the provider-free lifecycle as the next authorized implementation slice. This contract documents that placement; it does not implement runtime behavior.

---

## Documentation Follow-through

This change aligns the contract with accepted ADR-066:

- Adds the governing-decision reference and the current placement diagram.
- Adds the source-selection lineage requirement (Agent Reading Packet or equivalent bounded receipt).
- Adds composition obligations with the existing execution seams.
- Does not change Campaign Engine schemas, runtime code, or release claims.

Deferred:

- The provider-free runtime implementation slice is the next authorized implementation slice under ADR-066, but requires a separately approved task with its own proof surface.
- A `docs/architecture/README.md` entry for ADR-066 is deferred to a follow-up task.
