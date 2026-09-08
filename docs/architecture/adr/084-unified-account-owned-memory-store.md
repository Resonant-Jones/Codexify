# ADR-084: Unified Account-Owned Memory Store

**Status:** Accepted — design frozen

**Date:** 2026-09-04

## Context

Codexify currently has several adjacent but non-equivalent memory surfaces:

- `memory_entries` and MemoryOS retention/heat behavior;
- Personal Facts with candidate, verified, disputed, archived, active,
  evidence, revision, and guardrail semantics;
- thread-first and retrieval-based context assembly;
- imported conversations and provenance-aware account import; and
- accepted Continuity doctrine for activation, decay, imported-history
  treatment, inspection, and user governance.

These surfaces do not yet form one user-legible memory system. In particular,
the current runtime does not provide one governed loop for explicit memory
writes, automatic suggestions, after-the-fact inspection and correction,
outside-chat import, persona-aware recall, portable export/restore, and
permanent erasure.

ADR-005 already places memory entries inside the user's `AccountBoundary`,
requires `user_id` isolation in multi-user mode, and requires an account export
that does not query other users. ADR-013 permits only verified, active,
user-scoped Personal Facts to enter provider-ready context. ADR-015 and ADR-016
define non-destructive decay, recallable imported archives, provenance, and a
user-governed continuity surface. ADR-039 distinguishes product-user authority
from infrastructure Operator authority. ADR-081 establishes
`projects.user_id` as Project ownership authority while recording that runtime
and legacy-data convergence remain unfinished.

A unified memory design must extend those doctrines without creating a second
authority for Personal Facts, allowing a mutable persona configuration to own
history, confusing rank with approval, or letting explicit-recall parameters
become a model-controlled bypass around context exclusions.

## Decision

Codexify adopts one logical, account-owned Memory Store.

### Ownership and physical naming

The authenticated account user/principal owns and governs their memory. An
infrastructure Operator, host, administrator, provider, model, classifier,
importer, persona, or runtime process does not gain memory inspection,
approval, mutation, recall, or erasure authority merely by operating or hosting
the instance.

“Account-owned” is the semantic ownership model. It does not require renaming
every existing physical `user_id` column to `account_id`. Existing column names
may remain when they correctly and consistently bind the authenticated account
principal. Nomenclature alone is not sufficient reason for a schema migration.

Durable memory may be account-scoped or Project-scoped. Project scope is valid
only through the canonical Project authority established by ADR-081.

### Persona attribution without ownership

Personas may be associated with a memory as provenance or retrieval context,
but they never own memory and never become account principals.

**Durable persona attribution targets a stable account-owned persona subject,
not a mutable `PersonaProfile`.** Runtime profile versions and configuration may
change without severing or transferring historical attribution.

Cross-persona recall remains available to the authenticated account principal
through explicit, bounded scope widening. A retrieved memory retains its source
attribution; the active persona must not claim authorship or experiential
continuity from another persona's attributed history.

### Approval, lifecycle, and context influence

Storage, approval, lifecycle, context posture, ranking, and decay control are
separate dimensions.

- Explicit user-authored memory statements may constitute approval.
- Ambiguous references, imports, classifier suggestions, assistant inferences,
  and external/tool claims remain candidates, dormant records, or quarantined
  evidence until the account principal performs the applicable explicit action.
- Explicit recall is a request-scoped retrieval grant. It does not permanently
  approve, activate, restore, or change the context posture of a record.
- Pinning changes ranking among already eligible records only.
- Holding suspends decay; pinning does not.
- Decay may reduce ambient influence without deleting canonical content.

Only records that pass a backend-computed eligibility policy may enter ambient
provider context. Models and clients cannot write an `ambient_eligible` result.

### Personal Facts remain specialized

Personal Facts remain a specialized memory subtype with one authority per
dimension.

- `personal_facts.status` remains authoritative for Personal Fact review
  meaning until an intentionally governed migration changes it.
- `personal_facts.is_active` remains authoritative for Personal Fact activation
  until an intentionally governed migration changes it.
- Any unified Memory Store view of Personal Fact review or activation is
  derived from the Personal Facts service and is not independently editable.
- Personal Fact transitions, evidence, revisions, and guardrails remain
  transactionally governed by the Personal Facts service.

One logical Memory Store does not require one physical table or duplicated
mutable truth.

### Canonical and derived state

Canonical memory holds content, account ownership, scope, lifecycle authority,
approval authority, provenance, and user-authored governance choices. Heat,
usage counters, recent-use timestamps, vectors, and ranking scores are derived
projections. Derived state may be rebuilt or discarded without changing memory
truth, approval, ownership, or direct retrievability.

### Recall authority and untrusted evidence

Guardian derives a bounded recall grant from authenticated user intent. Models
may request recall but cannot mint or broaden that grant. Retrieval policy is
applied by the backend control plane before context construction.

Dormant imports, rejected or disputed records, classifier candidates, and
external evidence may be used only when a valid grant permits the specific
request. They enter context as delimited, provenance-bearing, non-instructional
evidence. Approval to use content as memory does not turn instruction-shaped
payloads into system, persona, tool, or mutation authority.

### Collection consent

Explicit memory commands remain available. Automatic memory suggestions run
only after the account principal records a consent choice. Storing an inactive
candidate is still durable collection and is not exempt from consent merely
because it is excluded from ambient context. Sensitive identity inference
remains separately governed.

### Portability and erasure

Memory is part of the AccountBoundary and must round-trip through account
export and restore before new automatic or imported memory write paths are
enabled.

Soft retirement is the ordinary reversible lifecycle action. Explicit,
audited permanent erasure is mandatory before the Memory Store becomes a
supported sovereignty feature.

When a purged record originated in an import, its non-content tombstone may
retain only the minimum scoped source identity or fingerprint material needed
to suppress resurrection. Re-importing the same OpenAI, Anthropic, or other
source export must not silently recreate a previously purged imported atom.
Reintroduction requires an explicit authenticated user action such as
“restore/re-import previously purged records.”

## Frozen doctrine

> **Account owns. Project scopes. Persona attributes. User approves. Pinning
> prioritizes. Holding suspends decay. The router widens only on explicit user
> intent. Every borrowed memory keeps its attribution.**

## Consequences

### Positive

- Memory has one semantic ownership boundary and one user-facing governance
  model without flattening Personal Facts into generic blobs.
- Project and persona dimensions remain orthogonal and inspectable.
- Models cannot bypass ambient exclusions by manufacturing broad recall flags.
- Imported and automatically suggested material stays useful without receiving
  unearned authority.
- Portability and erasure become release prerequisites rather than deferred
  cleanup.
- Stable persona attribution survives runtime profile replacement.

### Negative

- The implementation requires staged migrations, a compatibility read model,
  new user-intent and recall-grant enforcement, and cross-subsystem tests.
- Existing MemoryOS, Personal Facts, retrieval, import, and export seams cannot
  be replaced safely in one task.
- Persona subject reconciliation and ADR-081 Project ownership convergence are
  prerequisite work.
- Purge, backup-retention, import suppression, and derived-index cleanup require
  explicit operational proof before release.

## Implementation and release boundary

This ADR freezes architecture only. It does not add tables, routes, UI,
classifiers, imports, exports, recall behavior, persona subjects, purge
behavior, or release support.

Implementation is governed by the
[Unified Memory Store Contract](../unified-memory-store-contract.md) and the
[Unified Memory Store Campaign](../../Campaign/unified-memory-store/README.md).
Each Campaign phase is an independently reviewable architecture-impact task.

Project-scoped memory and Anthropic Project import remain blocked until
ADR-081's runtime normalization and legacy reconciliation are proven. Automatic
and imported memory ingestion remain blocked until export/restore round-trip
proof passes. Supported user-facing release remains blocked until permanent
erasure and re-import suppression are proven.

`docs/architecture/00-current-state.md` remains release truth. This ADR does
not widen the current Beta surface.

## Governing and related records

- Extends [ADR-005: Runtime Mode and Account Boundary
  Invariants](./005-runtime-mode-and-account-boundary-invariants.md) without
  superseding it. Account ownership is semantic and may continue to use
  correctly scoped physical `user_id` columns.
- Extends [ADR-004: Retrieval Policy as Control
  Plane](./004-retrieval-policy-as-control-plane.md) with memory-specific,
  backend-owned recall grants and scope receipts.
- Extends [ADR-013: Verified Personal Facts Context
  Injection](./013-verified-personal-facts-context-injection.md) without
  replacing Personal Facts lifecycle authority.
- Makes the combined implications of [ADR-015: Continuity Engine Working Set
  and Decay](./015-continuity-engine-working-set-and-decay-contract.md) and
  [ADR-016: Continuity Governance Surface
  Contract](./016-continuity-governance-surface-contract.md) concrete for
  memory storage, decay, import posture, and inspection.
- Aligns with the proposed [ADR-039: Operator / User Access
  Boundary](./039-operator-user-access-boundary.md); hosting or administering an
  instance does not confer product-user memory authority.
- Preserves [ADR-076: Archive Before Delete and Built-In Project
  Roles](./076-archive-before-delete-and-built-in-project-roles.md) and depends
  on [ADR-081: Project Ownership
  Authority](./081-project-ownership-authority.md) for Project-scoped writes and
  reads.
- Preserves the [Personal Facts Guardrails
  Contract](../personal-facts-guardrails-contract.md), [Account Export + Restore
  Contract](../account-export-restore-contract.md), and [IDDB Policy
  v1](../../iddb_policy_v1.md).
