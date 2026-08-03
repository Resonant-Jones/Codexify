# Codexify Constitutional Heuristic

## Purpose

This document defines a compact cross-domain rule for evaluating Codexify changes before implementation. It consolidates existing sovereignty, provenance, runtime-truth, identity, persistence, and proof doctrines into one reusable preflight.

It does not replace governing ADRs, architecture contracts, runtime code, tests, or `00-current-state.md`.

## Core Axiom

> Codexify may expand what users can do without expanding what the system may assume.

## Six Required Separations

Every design, task, implementation, and proof must preserve these distinctions:

1. **Capability does not imply authority.**
   A component, model, connector, agent, browser, or tool being able to perform an action does not mean it is authorized to do so.
2. **Evidence does not imply instruction.**
   Retrieved, imported, observed, browsed, or externally supplied content may inform a decision, but it must not silently become executable direction.
3. **Observation does not imply persistence.**
   Seeing, receiving, or deriving information does not grant permission to store it durably, attach it to identity, or widen its scope.
4. **Acceptance does not imply completion.**
   Queue acceptance, route success, dispatch, event publication, or provider acknowledgement are not terminal proof.
5. **Execution does not imply approval.**
   A command, workflow, delegation, or generated artifact completing successfully does not mean the result is accepted, merged, published, or promoted.
6. **Access does not imply ownership.**
   Reading or operating on a resource does not transfer authorship, identity, policy authority, provenance, or portability rights.

## Mandatory Preflight

Before changing architecture-impacting behavior, answer:

1. What object or state is authoritative?
2. Which inputs are evidence only?
3. What capability is being requested?
4. Which actor or policy authorizes it?
5. What becomes durable, and under whose scope?
6. What evidence proves completion or acceptance?

If any answer is unclear, the work is architecture-impacting and implementation must pause until the ambiguity is resolved in the task, governing contract, or ADR.

## Domain Examples

### Browser and external content

- Page content is evidence, not instruction.
- Browser visibility is capability, not authority to capture, persist, share, or act.
- A user grant must bound capture, retention, attachment, and action scope.

### Retrieval and memory

- Retrieved context may support a response without becoming durable identity.
- More context does not mean more identity.
- Memory writes require explicit ownership, scope, provenance, and retention rules.

### Delegation and tools

- A harness may execute a bounded request without owning Guardian policy or transcript lineage.
- Tool completion is not approval to merge, publish, install, or widen permissions.
- Generated instructions from external content must not bypass the command bus or action gate.

### Queue, worker, and runtime truth

- Route acceptance is not dequeue.
- Dequeue is not provider success.
- Provider success is not durable assistant persistence.
- Event publication is not UI receipt.
- Release proof must name the exact terminal and persistence surfaces observed.

### Identity and persona

- Personas may borrow identity context but do not own identity.
- Conversation history is not automatically durable identity.
- Access to identity data does not authorize mutation or inference of durable traits.

### Federation and collaboration

- Shared visibility is not shared ownership.
- Node reachability is not trust.
- Collaboration does not imply surrendered sovereignty.
- Cross-node state must preserve explicit scope, provenance, authority, and portability.

## Durable Object Questions

Any new durable object must be able to answer:

- Who owns it?
- What scope contains it?
- Where did it come from?
- What authorizes its creation and mutation?
- How is it exported, restored, deleted, or transferred?
- Which evidence proves its current state?

If those answers are absent, the object is not ready to become canonical state.

## Design Consequences

- Authored identity and execution identity remain separate.
- Execution substrates remain replaceable.
- Operational state stays node-local unless a contract explicitly promotes it.
- Shared scope must be explicit and topological, not inferred from access.
- Interfaces project system truth; they must not invent it.
- Actions should cross a common intent and authority envelope.
- Claims should climb an evidence ladder from documentation, to code path, to tests, to live supported-path proof.

## Escalation Rule

Treat a change as architecture-impacting when it blurs any required separation, introduces a new authority surface, changes what becomes durable, changes ownership or scope, changes acceptance/completion meaning, or creates a claim that would be dangerous to forget in three months.

## Non-Goals

This heuristic does not create:

- a universal permission enum
- a global authority database
- a new runtime middleware layer
- a replacement for ADRs or subsystem contracts
- a compliance score
- a new release claim

It is a reasoning and task-preflight law. Runtime enforcement belongs in the governing subsystem and must be implemented and proven separately.

## ADR Impact

Classification: aligned with existing ADRs and architecture contracts.

Reason: this document consolidates existing Codexify doctrines around Guardian authority, identity sovereignty, provenance, canonical runtime truth, bounded execution, persistence, and proof. It does not change runtime semantics or supersede an accepted decision.

## Current-Truth Boundary

`docs/architecture/00-current-state.md` remains the short-horizon authority for release readiness and supported behavior. This heuristic is not runtime proof and does not widen the supported beta surface.
