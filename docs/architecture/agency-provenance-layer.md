# Agency Provenance Layer

Purpose: define a reusable provenance contract for human-agent identity boundaries, delegated authority, authorship metadata, auditability, and external communication etiquette across Codexify surfaces. This is architecture/specification only. It is a Draft. It does not describe current runtime support, does not widen the supported beta surface, and does not override [`00-current-state.md`](./00-current-state.md).

Status: Draft
Owner: Codexify Core
Last updated: 2026-06-27
Scope: human-agent identity boundaries, delegated authority, authorship metadata, auditability, and external communication etiquette.

Source anchors:
- docs/architecture/identity-precedence-contract.md
- docs/architecture/delegation-runtime.md
- docs/architecture/delegation-operator-manual.md
- docs/architecture/guardian-delegation-loop-contract.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/canonical-token-philosophy.md
- docs/architecture/web-evidence-intake-gate-contract.md
- guardian/protocol_tokens.py (canonical registry home for candidate tokens introduced below)

## Relationship to Existing Codexify Contracts

This layer is proposed as an umbrella over concepts that already partially exist as narrower contracts. It does not supersede them; it is intended to reference and unify them.

- [Identity Precedence Contract](./identity-precedence-contract.md): defines who may claim first-person identity. Guardian is the only stable first-person actor; personas and imprints are borrowed layers, not principals. This layer's rule that "a persona is not a principal" and "delegation is not impersonation" extends that contract.
- [Delegation Runtime Contract](./delegation-runtime.md): the current delegation seam and source-thread provenance rules. Any durable delegation grant modeled here must stay compatible with that runtime.
- [Delegation Operator Manual](./delegation-operator-manual.md): operator procedure for supervised delegation.
- [Guardian Delegation Loop Contract](./guardian-delegation-loop-contract.md): Phase 1 docs-only contract for the hybrid Guardian intake bridge.
- [Account Export + Restore Contract](./account-export-restore-contract.md): provenance and lineage semantics that durable artifacts and imported state must already satisfy. Any provenance envelope here must survive export and restore.
- [Web Evidence Intake Gate Contract](./web-evidence-intake-gate-contract.md): a sibling provenance/lineage gate whose `WebEvidenceProvenance` shape is the closest existing precedent for an evidence/lineage envelope.
- [Runtime Protocol Token Contract](./runtime-protocol-token-contract.md) and [Canonical Token Philosophy](./canonical-token-philosophy.md): govern how the candidate tokens below must graduate before use.

## Why This Layer Exists

Codexify supports collaboration between humans, assistants, agents, personas, workers, and external tools.

As agentic systems gain the ability to draft, route, summarize, recommend, and act, the system must preserve a clear boundary between:

- what a human personally authored
- what an agent generated
- what a human reviewed or approved
- what an agent inferred from available context
- what a system emitted automatically
- what authority was delegated for the action

The Agency Provenance Layer exists to prevent ambiguity around authorship, authorization, accountability, and consent.

The core principle:

> Delegation is not impersonation.

Agents may act under delegated authority, but they must not blur who authored, approved, inferred, or executed an action.

## Goals

- Preserve trust in human-agent collaboration.
- Make authorship and delegation visible.
- Distinguish personal human communication from agentic/system communication.
- Support auditable action trails.
- Prevent agents from silently impersonating users.
- Provide a reusable provenance contract for email, chat, documents, tasks, pull requests, notifications, and future agent surfaces.
- Keep identity boundaries load-bearing across the product.

## Non-Goals

This spec does not define:

- a full permissions system
- a general auth model
- agent memory ingestion rules
- provider routing logic
- UI copy for every product surface
- legal compliance language
- automated reputation scoring

Those may depend on this layer, but they are separate specs.

## Candidate Tokens and Conceptual Shapes

The vocabularies and data shapes below (provenance modes, review states, actor types, audit event types, and the TypeScript-style type blocks) are **docs-only and conceptual**. They describe the contract a future implementation should satisfy without prescribing code structure, and they do not yet exist in the canonical registry.

Per the [Canonical Token Philosophy](./canonical-token-philosophy.md), any repeated contract-bearing value here must graduate into `guardian/protocol_tokens.py` (or a bounded sibling registry) with documented meaning, typed exports, and contract tests before any runtime use. Until then these remain candidate tokens, not runtime tokens.

## Definitions

### Principal

The human or organization on whose behalf an agent may operate.

Example:

```text
Resonant Jones
Catalyst Design Labs
```

### Agent

A bounded software actor capable of generating, transforming, routing, or executing work.

Example:

- Guardian
- Luna
- a Persona Studio assistant
- a scheduler agent

### Persona

A presentation and interaction layer used by an agent or assistant.

Personas may borrow voice, tone, style, or role context, but they do not own identity. A persona is not a principal. This is consistent with the [Identity Precedence Contract](./identity-precedence-contract.md), where persona is a borrowed role layer over the stable Guardian actor.

### Delegation

A grant of limited authority from a principal to an agent.

Delegation must have:

- scope
- allowed actions
- review requirements
- expiration or revocation path
- audit trail

### Authorship

The entity responsible for composing the substantive content of a message, document, action, or recommendation.

Authorship may be:

- human
- agent
- mixed
- system-generated

### Approval

A human act confirming that content or an action may proceed.

Approval is separate from authorship. A human may approve content they did not author. An agent may draft content it is not authorized to send.

### Inference

A generated conclusion, summary, recommendation, or message derived from context rather than direct human instruction.

Inference must not be presented as personal human intent unless reviewed and approved.

## Provenance Modes

Every outward-facing or persistent agentic artifact should carry one of the following provenance modes.

### `human_authored`

The content was written directly by a human.

Allowed representation:

```text
From: Chris
```

Use when the system is only transporting, storing, or rendering human-authored content.

### `ai_assisted_human_approved`

The content was drafted, edited, summarized, or improved by an assistant or agent, then explicitly reviewed and approved by a human.

Allowed representation:

```text
Drafted with Guardian.
Reviewed and approved by Chris.
```

### `agent_sent_under_delegation`

The agent generated and sent/executed the artifact under standing authority without per-item human approval.

Allowed representation:

```text
Sent by Guardian for Chris.
Human review: Not performed before sending.
Authority: Weekly status update automation.
```

### `agent_inferred`

The content contains an inferred summary, interpretation, recommendation, or proposed action.

Allowed representation:

```text
Generated by Guardian from available project context.
This may not represent Chris's direct intent unless approved.
```

### `system_notice`

The artifact was emitted automatically by infrastructure, jobs, workers, schedulers, or monitoring systems.

Allowed representation:

```text
System notice from Codexify.
No human authorship implied.
```

### `human_override`

A human changed, corrected, revoked, or superseded a prior agentic artifact.

Allowed representation:

```text
Human override applied by Chris.
This supersedes the previous Guardian-generated item.
```

## Required Provenance Fields

Any durable or externally visible agentic artifact should be representable with the following envelope. The shapes below are docs-only and conceptual (see Candidate Tokens and Conceptual Shapes above).

```ts
type ProvenanceMode =
  | "human_authored"
  | "ai_assisted_human_approved"
  | "agent_sent_under_delegation"
  | "agent_inferred"
  | "system_notice"
  | "human_override";

type ReviewState =
  | "not_required"
  | "not_reviewed"
  | "human_reviewed"
  | "human_approved"
  | "human_rejected"
  | "human_overridden";

type ActorType =
  | "human"
  | "agent"
  | "persona"
  | "system"
  | "external_tool";

type ProvenanceActor = {
  id: string;
  type: ActorType;
  display_name: string;
};

type DelegationReference = {
  id: string;
  principal_id: string;
  agent_id: string;
  scope: string;
  allowed_actions: string[];
  review_required: boolean;
  expires_at?: string;
  revoked_at?: string;
};

type ProvenanceEnvelope = {
  artifact_id: string;
  artifact_type: string;

  mode: ProvenanceMode;
  review_state: ReviewState;

  principal?: ProvenanceActor;
  author?: ProvenanceActor;
  sender?: ProvenanceActor;
  executor?: ProvenanceActor;
  approving_actor?: ProvenanceActor;

  delegation?: DelegationReference;

  source_context_ids?: string[];
  generated_from_artifact_ids?: string[];

  confidence?: "low" | "medium" | "high";
  human_intent_claimed: boolean;

  created_at: string;
  updated_at?: string;

  notes?: string;
};
```

## Critical Invariant

If `human_intent_claimed` is `true`, then one of the following must also be true:

- `mode` is `human_authored`
- `review_state` is `human_approved`
- `review_state` is `human_reviewed`

Agents must not claim human intent solely from inferred context.

## Email Identity Policy

Codexify should distinguish personal mail from delegated agentic mail.

### Personal Human Mail

Example:

```text
chris@domain.com
```

Meaning:

- human-authored, or
- AI-assisted and explicitly approved by the human

Expected recipient interpretation: this message represents Chris personally.

### Guardian Mailbox

Example:

```text
guardian@domain.com
```

Meaning:

- generated or sent by Guardian
- may be automated, inferred, or delegated
- does not automatically imply direct human authorship

Expected recipient interpretation: this message was sent by Guardian under delegated authority.

### Recommended Footer: Human Approved

```text
Drafted with Guardian.
Reviewed and approved by Chris.
Mode: AI-assisted, human-approved correspondence.
```

### Recommended Footer: Agent Sent

```text
Sent by Guardian for Chris.
Mode: Agent-sent under delegated authority.
Human review: Not reviewed before sending.
Authority: [delegation scope]
Reply handling: Replies may be reviewed by Chris or Guardian depending on context.
```

### Recommended Footer: Agent Inferred

```text
Generated by Guardian from available context.
Mode: Agent-inferred.
Human review: Not reviewed before sending.
This message should not be treated as direct personal intent unless confirmed.
```

## Product Surfaces

The provenance layer should eventually apply to:

- email
- chat messages
- task creation
- task completion reports
- pull request comments
- code review comments
- meeting summaries
- calendar actions
- notifications
- generated documents
- Persona Studio outputs
- external integrations
- autonomous worker logs

## UI Requirements

Any user-facing artifact with agentic involvement should expose provenance at one of three levels.

### Compact

For low-risk surfaces.

```text
Sent by Guardian
```

### Standard

For normal collaboration surfaces.

```text
Sent by Guardian for Chris
Human review: Not reviewed
Authority: Weekly project summary
```

### Expanded

For audit/debug surfaces. Should include:

- principal
- author
- sender
- executor
- review state
- delegation scope
- source context
- confidence
- timestamps
- prior artifact references
- override history

## Runtime Requirements

### Agents Must Not

Agents must not:

- silently impersonate a human
- claim personal human intent from inference alone
- mutate durable memory without an approved memory pathway
- hide that content was generated or sent under delegation
- use a persona identity as if it were the principal identity
- collapse author, sender, and approver into one field when they differ

### Agents May

Agents may:

- draft on behalf of a human
- send under explicit delegation
- summarize available context
- make recommendations
- prepare replies for approval
- route messages to the appropriate actor
- escalate when provenance is ambiguous

## Audit Requirements

Every delegated action should produce an audit event. The shape below is docs-only and conceptual (see Candidate Tokens and Conceptual Shapes above).

```ts
type AgencyAuditEvent = {
  id: string;
  artifact_id?: string;
  delegation_id?: string;

  event_type:
    | "artifact_created"
    | "artifact_sent"
    | "artifact_reviewed"
    | "artifact_approved"
    | "artifact_rejected"
    | "artifact_overridden"
    | "delegation_granted"
    | "delegation_revoked"
    | "provenance_updated";

  actor: ProvenanceActor;
  target_actor?: ProvenanceActor;

  prior_state?: Record<string, unknown>;
  next_state?: Record<string, unknown>;

  reason?: string;
  created_at: string;
};
```

## Escalation Rules

The system should require human review when:

- the artifact claims direct human intent
- the content is emotionally personal
- the message creates financial, legal, medical, or employment consequences
- the agent lacks a valid delegation grant
- the source context is incomplete or stale
- the agent is uncertain whether the message is personal or operational
- the recipient is external and the communication is high-trust
- the action cannot be safely undone

## Memory Boundary

Provenance metadata may be stored as durable system memory. Artifact content should not become durable personal memory unless it passes the normal memory ingestion pathway. Agents may generate memory candidates, but they may not self-canonize memory.

## Implementation Sketch

Suggested staged implementation:

### Phase 1: Documentation and Manual Labels

- Add this spec.
- Add manual provenance labels to email/draft workflows.
- Establish footer conventions.
- Treat Guardian as a distinct sender identity.

### Phase 2: Provenance Envelope

- Add a provenance object to generated artifacts.
- Store provenance metadata with drafts, task reports, and agent outputs.
- Add review state tracking.

### Phase 3: Delegation Grants

- Introduce explicit delegation records.
- Require valid delegation for autonomous sending or execution.
- Add revocation and expiration.

### Phase 4: Audit Surface

- Add provenance inspection UI.
- Add audit log views.
- Add human override controls.

### Phase 5: Policy Enforcement

- Block unsafe or ambiguous sends.
- Require approval for high-risk categories.
- Add tests for authorship, approval, and delegation invariants.

## Testing Requirements

Tests should verify:

- agent-sent artifacts cannot claim direct human authorship
- inferred content cannot claim human intent without approval
- revoked delegation blocks execution
- missing delegation blocks autonomous send
- human-approved artifacts preserve both agent author and human approver
- system notices do not imply human authorship
- override events preserve prior state
- memory candidates are not canonized automatically

## Open Questions

- Should provenance footers be mandatory for all external agentic emails?
- Should internal-only agent messages use compact provenance by default?
- Should Guardian have a dedicated mailbox, alias, or both?
- What artifact types require human approval by default?
- How should provenance display in Persona Studio?
- How should replies to Guardian-authored emails route back into Codexify?
- Should delegation scopes be user-configurable in settings?
- Should recipients be able to inspect a public provenance receipt?

## Design Principle

Codexify should not merely make agentic work faster. It should make agentic work legible.

Trust survives when people can tell the difference between:

- A human said this.
- An agent drafted this and a human approved it.
- An agent acted under delegated authority.
- A system emitted this automatically.

That difference is not decorative. It is infrastructure.

## Implementation Readiness Checklist

Future implementation work must satisfy all of the following before any release claim:

- canonical tokens created in `guardian/protocol_tokens.py` (or a bounded sibling registry) for provenance modes, review states, actor types, and audit event types
- contract tests for the provenance envelope and the critical `human_intent_claimed` invariant
- a delegation grant model compatible with [Delegation Runtime Contract](./delegation-runtime.md) and [Delegation Operator Manual](./delegation-operator-manual.md)
- review-state tracking implemented or explicitly deferred
- audit event emission implemented or explicitly deferred
- export and restore compatibility reviewed against [Account Export + Restore Contract](./account-export-restore-contract.md)
- escalation rules implemented or explicitly deferred for high-risk categories
- no durable personal-memory writes outside the approved memory ingestion pathway
- no frontend secrets
- no release claim without live runtime proof on the supported path

## ADR Impact

Classification: aligned with existing ADRs and contracts; no governing ADR is changed by this Draft.

Governing and related contracts:

- [Identity Precedence Contract](./identity-precedence-contract.md)
- [Delegation Runtime Contract](./delegation-runtime.md)
- [Delegation Operator Manual](./delegation-operator-manual.md)
- [Guardian Delegation Loop Contract](./guardian-delegation-loop-contract.md)
- [Account Export + Restore Contract](./account-export-restore-contract.md)
- [Runtime Protocol Token Contract](./runtime-protocol-token-contract.md)
- [Canonical Token Philosophy](./canonical-token-philosophy.md)

Reason:

- This is a Draft spec only. It proposes a future provenance layer and labels all new vocabularies as docs-only candidate tokens.
- It does not change accepted architecture, runtime semantics, identity policy, queue/worker semantics, retrieval behavior, canonical token registries, or release promises.
- Any future runtime implementation requires a new or amended ADR and canonical token registration.

## Current-Truth Anchors

What is true now:

- Codexify has an identity precedence model where Guardian is the only stable first-person actor and personas/imprints are borrowed layers.
- Codexify has a current delegation seam with source-thread provenance rules and an operator manual.
- Durable artifacts and imported state already carry provenance and lineage semantics for export and restore.
- The [Web Evidence Intake Gate Contract](./web-evidence-intake-gate-contract.md) defines a docs-only evidence/lineage envelope as a precedent.

What was not true before this document:

- There was no umbrella spec unifying human-agent authorship, delegation authority, review state, and auditability into a single provenance contract.

What remains not true:

- The Agency Provenance Layer is not implemented. No `ProvenanceEnvelope`, delegation grant record, audit event emission, escalation gate, or provenance footer exists in the runtime.
- The candidate tokens in this doc are not registered canonical tokens.
- This document does not claim live support for any provenance surface. [`00-current-state.md`](./00-current-state.md) remains the release-truth gate.

What the task may assume:

- This task may add the Draft spec and add a README routing line only.
- This task must not claim new runtime behavior, must not register tokens, and must not implement any phase of the Implementation Sketch.
