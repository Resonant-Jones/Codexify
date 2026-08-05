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
- No behavior changes are introduced in this task.
- This document defines future direction only.

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

Classification: Requires new ADR

Reason:
This introduces a new orchestration authority model and role-binding semantics that affect future runtime behavior and system design.

---

## Documentation Follow-through

Deferred:
- No updates to existing architecture docs in this task.
- Follow-up tasks will align related documents.
