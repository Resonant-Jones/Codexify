# Self-Extending Agent Plugin System

This note is the companion architecture reference for ADR-010. It explains the governed shape of Codexify's self-extending model without claiming runtime implementation.

## Purpose

Codexify needs a way to author new capabilities from within the system without turning the assistant into a freeform self-modifying agent.

The contract is intentionally bounded:

* generated extensions may be proposed, forged, sandboxed, reviewed, and registered
* generated extensions may not silently mutate identity, provenance, or core runtime law
* extension installation and binding remain explicit and reviewable
* the supported beta promise is not widened by this note

## Canonical Terms

The following terms are canonical and should be used consistently:

| Term | Meaning |
|---|---|
| `Self-Extending Agent System` | The bounded architecture for generating and governing extensions. |
| `Extension Proposal` | The source request that declares intent, scope, lineage, and permissions for a new extension. |
| `Plugin Forge` | The bounded build lane that turns an approved proposal into a packaged candidate artifact. |
| `Sandbox Lane` | The isolated evaluation lane for running the candidate without live writes. |
| `Install Gate` | The policy checkpoint that determines whether a candidate may be registered. |
| `Capability Registry` | The canonical record of approved extension artifacts, scopes, permissions, and rollback state. |
| `Runtime Binding` | The explicit activation record that connects a registry entry to a live runtime scope. |
| `Lineage Spine` | The append-only provenance chain from authored turn to proposal, forge, sandbox, review, registration, and runtime events. |

Repeated contract-bearing values must use canonical tokens or registry-backed enumerations, not ad hoc literals.

## Extension Classes

Codexify permits four extension classes.

| Class | What it is | Attaches to | May read | May write | Must never mutate directly |
|---|---|---|---|---|---|
| `Tool plugins` | Bounded command-oriented extensions that expose actions through the command bus or tool lane. | Command bus and tool execution surfaces | Scoped task context, approved manifests, runtime diagnostics, declared inputs | Tool outputs, run artifacts, tool-specific metadata, command-bus-visible results | Identity Mirror, persona ownership rules, canonical runtime tokens, message-versus-attempt identity, export/restore lineage, queue/worker acceptance semantics |
| `Workflow plugins` | Extensions that generate, validate, or transform structured workflows. | Flow Builder and workflow-authoring surfaces | Workflow specs, project context, prior approvals, validation results | Draft workflow artifacts, compiled workflow specs, validation traces | Identity Mirror, persona ownership rules, canonical runtime tokens, message-versus-attempt identity, export/restore lineage, queue/worker acceptance semantics |
| `Retrieval plugins` | Extensions that augment retrieval behavior inside declared policy boundaries. | Retrieval and context-assembly surfaces | Approved corpora, index metadata, retrieval policy, project scope, diagnostics | Retrieval hints, cache artifacts, trace annotations, derived indexes | Identity Mirror, persona ownership rules, canonical runtime tokens, message-versus-attempt identity, export/restore lineage, queue/worker acceptance semantics |
| `UI/persona capability packs` | Extensions that alter Persona Studio or shell capability presentation without owning identity. | Persona Studio and UI capability surfaces | Persona/profile settings, permission state, diagnostics, preview data, scope metadata | Profile presets, UI capability metadata, display configuration, validation notes | Identity Mirror, chat history, canonical runtime tokens, message-versus-attempt identity, export/restore lineage, queue/worker acceptance semantics |

## Sovereignty and Identity Boundaries

Generated extensions may not directly rewrite:

* IDDB / Identity Mirror
* persona ownership rules
* canonical runtime tokens
* message-versus-attempt identity semantics
* export/restore lineage guarantees
* queue/worker acceptance semantics

This matches Codexify's identity doctrine:

* chat history is not durable identity
* deep identity is opt-in
* personas borrow identity; they do not own it

Extensions may depend on identity and provenance, but they do not own or redefine them.

## Lifecycle

The canonical lifecycle is:

1. Proposal
2. Forge
3. Sandbox
4. Review
5. Registration

### Proposal

Entry conditions:

* a source thread, source message, or authored request exists
* the extension can be scoped to a bounded class
* the proposal can name its target surface and permissions

Required artifacts:

* `Extension Proposal`
* lineage reference to the source thread/message
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

* proposal is linked to source lineage
* requested scope is explicit
* the `Lineage Spine` begins here

### Forge

Entry conditions:

* proposal approved for forging
* declared permissions are frozen
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
* forge output is inspectable

### Sandbox

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
* candidate behavior is attributable

### Review

Entry conditions:

* sandbox proof exists
* lineage spine is intact
* requested versus tested permissions are available for comparison

Required artifacts:

* review notes
* diff summary
* security and permission review
* rollback recommendation

Allowed side effects:

* review metadata only

Prohibited side effects:

* installation
* runtime binding
* silent approval

Proof expectations:

* review outcome recorded
* reviewer identity or policy source recorded
* review is traceable back to proposal and sandbox

### Registration

Entry conditions:

* review approved
* `Install Gate` passed
* scope binding resolved
* rollback path is known

Required artifacts:

* `Capability Registry` entry
* `Runtime Binding` record
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

Every extension manifest must include:

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
* sandbox outcome
* runtime binding scope
* failure classification
* registry status

Manifest values that carry repeated contract meaning must use canonical tokens rather than freeform text.

The `Capability Registry` is the canonical truth surface for approved extensions. It preserves versioning, approval state, scope binding, rollback state, and `Lineage Spine` references.

## Permissions and Binding

Extension permissions must bind through existing Persona Studio / runtime-profile style permission surfaces.

Codexify must not create an unrelated second permission universe for extensions.

Scope binding must remain explicit:

* project-scoped
* profile-scoped
* account-scoped

The permission model follows current Codexify doctrine:

* permissions are declared up front
* permissions are reviewed before registration
* runtime binding only reflects approved scope
* scope widening requires a new review event

## Runtime Identity

The system must distinguish:

* authored turn identity
* execution-attempt identity
* extension run identity

Authored turn identity identifies the human-authored request.
Execution-attempt identity identifies a specific forge/sandbox/review/registration attempt.
Extension run identity identifies a live registered extension execution or activation.

These identities must remain replay-safe and attributable. A retry or re-registration may create a new execution-attempt or run identity, but it must preserve the `Lineage Spine` and not pretend to be the original authored turn.

## Observability

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

## Recommended First Slice

The smallest honest first implementation slice is:

* `Tool Plugin Forge` only
* project-scoped only
* no identity writes
* no retrieval-policy mutation
* no automatic UI install
* no silent registration

That slice is the minimum viable proof that Codexify can extend itself without crossing sovereignty boundaries.

## Non-goals

This note does **not**:

* implement the runtime
* approve arbitrary self-rewriting of the core loop
* authorize direct identity mutation by plugins
* redefine retrieval/router/runtime contracts
* widen the supported beta surface by itself
* silently add runtime binding or automatic installation

## Relation to the ADR

ADR-010 is the governing decision.
This note is the companion reference for readers who need the contract broken into surfaces, lifecycle phases, and proof requirements.
