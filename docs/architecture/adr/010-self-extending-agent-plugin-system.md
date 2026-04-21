---
tags:
* architecture
* adr
* plugin-system
* extensions
* persona-studio
* identity
* provenance
  aliases:
* ADR-010
* Self-Extending Agent Plugin System
---

# ADR-010: Self-Extending Agent Plugin System

## Status

Accepted

## Date

2026-04-20

## Context

Codexify already has a command bus, a bounded tool-loop contract, Persona Studio, export/restore lineage rules, and explicit identity boundaries. What it does not yet have is a governed architecture for generated capabilities that can be proposed, forged, sandboxed, reviewed, and registered without silently mutating identity or core runtime law.

The system needs a way to extend itself without becoming a self-modifying agent. Generated capabilities must remain attributable, reversible, and reviewable. They must not silently alter the meaning of identity, provenance, runtime tokens, or queue semantics.

This ADR defines that bounded model.

## Problem Statement

Codexify needs a self-extending system because users will eventually want to grow the system from within the system: new tools, workflows, retrieval behaviors, and persona/UI capability packs.

That need creates risk:

* generated code can blur authorship and runtime authority
* generated capabilities can mutate identity if they are not fenced
* plugin systems can quietly bypass provenance, export/restore lineage, or queue acceptance semantics
* generic tool/plugin systems often treat install and execution as a single undifferentiated act

Codexify must not do that.

The architecture must separate proposal, build, sandboxing, review, registration, and runtime binding. Generated capabilities may extend the system, but they may not rewrite its sovereignty boundaries.

## Decision

Codexify establishes a bounded **Self-Extending Agent System**.

The system is governed by a controlled lifecycle:

1. Extension Proposal
2. Plugin Forge
3. Sandbox Lane
4. Review
5. Registration

The lifecycle is mediated by an **Install Gate** and persisted through a **Capability Registry**. Approved capabilities become live only through explicit **Runtime Binding**. The full provenance path from source turn to registered capability is the **Lineage Spine**.

The system is self-extending, not self-modifying:

* generated capabilities may be proposed
* generated capabilities may be forged inside a bounded lane
* generated capabilities may be sandboxed and reviewed
* generated capabilities may be registered only after an install gate is passed
* generated capabilities may not silently rewrite identity, core runtime tokens, or export lineage

## Canonical Terminology

The following terms are canonical and must be used consistently:

| Term | Canonical meaning |
|---|---|
| Self-Extending Agent System | The bounded architecture for generating, testing, reviewing, and registering extensions without granting freeform self-modification. |
| Extension Proposal | The declarative request for a new extension, including lineage, scope, permissions, and expected behavior. |
| Plugin Forge | The bounded build-and-package lane that turns an approved proposal into an inspectable extension artifact. |
| Sandbox Lane | The isolated evaluation lane where the candidate extension runs against fixtures and proof inputs without live writes. |
| Install Gate | The policy checkpoint that blocks registration until lineage, permissions, tests, and scope checks pass. |
| Capability Registry | The canonical approved catalog of extensions, versions, scopes, permissions, and rollback state. |
| Runtime Binding | The explicit activation record that connects an approved registry entry to a live runtime scope. |
| Lineage Spine | The append-only provenance chain from authored turn to proposal, forge, sandbox, review, registration, and runtime events. |

Repeated contract-bearing values in this architecture must use canonical tokens or registry-backed enumerations, not ad hoc literals.

## Extension Classes

The system permits four extension classes. Each class has a distinct attachment surface and write boundary.

| Class | What it is | Attaches to | May read | May write | Must never mutate directly |
|---|---|---|---|---|---|
| Tool plugins | Command-oriented extensions that expose bounded actions to the command bus or a tool lane. | Command bus / tool execution surfaces | Allowed task context, declared inputs, scoped project data, approved manifests, runtime diagnostics | Tool outputs, run artifacts, tool-specific cache or metadata, command-bus-visible results | Identity mirror, persona ownership, canonical runtime tokens, message-versus-attempt identity, export/restore lineage, queue/worker acceptance semantics |
| Workflow plugins | Extensions that author or transform structured workflows, checklists, or orchestration graphs. | Flow Builder / workflow-authoring surfaces | Workflow specs, project context, prior approvals, task constraints, validation results | Draft workflow artifacts, compiled workflow specs, validation traces | Identity mirror, persona ownership, canonical runtime tokens, message-versus-attempt identity, export/restore lineage, queue/worker acceptance semantics |
| Retrieval plugins | Extensions that alter or augment retrieval behavior within declared policy boundaries. | Retrieval / context-assembly surfaces | Approved corpora, vector/index metadata, retrieval policy, project scope, diagnostics | Retrieval hints, cache artifacts, trace annotations, derived indexes | Identity mirror, persona ownership, canonical runtime tokens, message-versus-attempt identity, export/restore lineage, queue/worker acceptance semantics |
| UI/persona capability packs | Extensions that alter Persona Studio or shell capabilities without owning identity. | Persona Studio / UI capability surfaces | Persona/profile settings, permission state, diagnostics, preview data, scope metadata | Profile presets, UI capability metadata, display configuration, validation notes | Identity mirror, chat history, canonical runtime tokens, message-versus-attempt identity, export/restore lineage, queue/worker acceptance semantics |

## Sovereignty and Identity Boundaries

Generated extensions must not directly rewrite the following:

* IDDB / Identity Mirror
* persona ownership rules
* canonical runtime tokens
* message-versus-attempt identity semantics
* export/restore lineage guarantees
* queue/worker acceptance semantics

This aligns with existing Codexify doctrine:

* chat history is not durable identity
* deep identity is opt-in
* personas borrow identity; they do not own it

The extension system may reference identity, but it may not claim ownership of identity.

## Lifecycle

### 1. Proposal

Entry conditions:

* a source turn, source thread, or authored request exists
* the user intent can be scoped to a bounded extension class
* the proposal can name its target surface and permissions

Required artifacts:

* extension proposal manifest
* source thread/message lineage reference
* initial scope and permission draft
* human-readable rationale

Allowed side effects:

* draft artifacts only

Prohibited side effects:

* runtime mutation
* installation
* registry registration
* identity writes

Proof expectations:

* proposal is linked to source thread/message
* requested scope is explicit
* lineage spine starts here

### 2. Plugin Forge

Entry conditions:

* proposal approved for forging
* declared permissions are frozen for the forge pass
* target surface is known

Required artifacts:

* forge package or build artifact
* build hash
* dependency manifest
* test plan or proof plan

Allowed side effects:

* writes inside the forge workspace or build sandbox only

Prohibited side effects:

* live runtime registration
* identity mutation
* undocumented permission expansion
* hidden writes to core state

Proof expectations:

* package hash recorded
* dependencies enumerated
* forge output is reproducible or at least inspectable

### 3. Sandbox Lane

Entry conditions:

* forged artifact exists
* sandbox inputs are declared
* sandbox policy is explicit

Required artifacts:

* sandbox runtime logs
* fixture coverage
* permission checks
* compatibility results

Allowed side effects:

* ephemeral sandbox writes only

Prohibited side effects:

* production writes
* registry updates
* identity mutation
* queue acceptance changes

Proof expectations:

* sandbox results are captured
* failures are classified
* runtime behavior is attributable to the candidate artifact

### 4. Review

Entry conditions:

* sandbox proof exists
* lineage spine is intact
* requested versus tested permissions are available for comparison

Required artifacts:

* review notes
* diff summary
* security/permission review
* rollback recommendation

Allowed side effects:

* none beyond review metadata

Prohibited side effects:

* installation
* runtime binding
* silent approval

Proof expectations:

* review outcome recorded
* reviewer identity or policy source recorded
* review is traceable back to proposal and sandbox

### 5. Registration

Entry conditions:

* review approved
* install gate passed
* scope binding resolved
* rollback path is known

Required artifacts:

* capability registry entry
* runtime binding record
* rollback metadata
* permission grant record
* versioned release record

Allowed side effects:

* registry write
* explicit runtime binding

Prohibited side effects:

* silent activation
* identity mutation
* implicit scope widening
* mutation of core runtime law

Proof expectations:

* registry entry exists
* runtime binding is explicit
* rollback is available and documented

## Manifest and Registry Contract

Every extension manifest must, at minimum, declare:

* extension id
* version
* target surface
* requested permissions
* declared dependencies
* source thread/message lineage
* project/persona scope
* rollback metadata
* test evidence metadata

Recommended additional fields:

* extension class
* install gate decision
* sandbox lane outcome
* runtime binding scope
* failure classification
* registry status

Manifest values that carry repeated contract meaning must use canonical tokens rather than freeform text. That includes extension class, lifecycle phase, install outcome, permission scope, and failure classification.

The Capability Registry is the canonical truth surface for approved extensions. It must preserve versioning, approval state, scope binding, rollback state, and lineage spine references.

## Permissions and Binding Model

Extension permissions must bind through existing Persona Studio / runtime-profile style permission surfaces.

Codexify must not create an unrelated second permission universe for extensions.

Scope binding must remain explicit:

* project-scoped
* profile-scoped
* account-scoped

The permission model should follow the current Codexify direction:

* permissions are declared up front
* permissions are reviewed before registration
* runtime binding only reflects approved scope
* scope widening requires a new review event

## Runtime Identity and Execution Semantics

The system must distinguish:

* authored turn identity
* execution-attempt identity
* extension run identity

Authored turn identity identifies the human-authored request.
Execution-attempt identity identifies a specific forge/sandbox/review/registration attempt.
Extension run identity identifies a live registered extension execution or activation.

Those identities must remain replay-safe and attributable. A retry or re-registration may create a new execution-attempt or run identity, but it must preserve the lineage spine and not pretend to be the original authored turn.

## Observability and Proof Surface

Extension observability must expose:

* lineage back to source thread/message
* requested versus granted permissions
* install scope
* test results
* runtime events
* rollback availability
* failure classification

This observability belongs in explicit diagnostics and review surfaces, not in the primary chat loop.

The plugin system must remain inspectable without leaking noisy cognition into the core assistant path.

## Consequences

### Positive

* Generated capabilities become reviewable rather than magical.
* Identity and provenance remain protected by design.
* Extension growth can happen without breaking export/restore or runtime-token contracts.
* Persona Studio can remain a scoped configuration surface instead of becoming an identity rewrite surface.

### Negative

* Extension authorship becomes more structured.
* Install and registration require more proof than a generic plugin loader.
* The system must carry lineage and permission metadata through more phases.

## Non-goals

This ADR does **not**:

* implement the runtime
* approve arbitrary self-rewriting of the core loop
* authorize direct identity mutation by plugins
* redefine existing retrieval/router/runtime contracts
* widen the supported beta surface by itself
* silently add runtime binding or automatic installation

## Recommended first implementation slice

Start with **Tool Plugin Forge** only.

The first slice must be:

* project-scoped only
* no identity writes
* no retrieval-policy mutation
* no automatic UI install
* no silent registration

That slice is the smallest honest entry point into the Self-Extending Agent System.

## Links

* [ADR Index](./adr-index.md)
* [Self-Extending Agent Plugin System](../self-extending-agent-plugin-system.md)
* [System Overview](../system-overview.md)
* [Modules and Ownership](../modules-and-ownership.md)
* [Account Export + Restore Contract](../account-export-restore-contract.md)
* [Persona Studio Spec](../persona-studio-spec.md)
* [Chat Runtime Contract](../chat-runtime-contract.md)
* [Runtime Protocol Token Contract](../runtime-protocol-token-contract.md)

## Notes

This ADR defines a bounded self-extending architecture, not a self-modifying agent.

If a future implementation needs to expand beyond Tool Plugin Forge, it must do so by adding a new reviewable slice rather than by weakening the sovereignty and provenance boundaries defined here.

> If this decision has already been formally ratified in-repo, change **Status** from `Proposed` to `Accepted`.
