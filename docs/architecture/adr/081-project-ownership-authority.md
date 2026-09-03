# ADR-081: Project Ownership Authority

**Status:** Accepted

**Date:** 2026-09-03

## Context

ADR-005 defines Projects as part of an account boundary and requires explicit,
user-scoped access in multi-user mode. ADR-076 adds account-scoped built-in
Project roles and Project lifecycle rules. Neither record resolves a later
runtime contradiction: Project ownership can currently be obtained from two
durable representations.

- `projects.user_id` is a non-null foreign key to `users.id`. It participates
  in the account-scoped uniqueness of built-in Project roles and was introduced
  by a migration that backfilled legacy rows before making the field required.
- `projects.description` may contain a legacy
  `__codexify_project_owner__` JSON envelope with `owner_user_id`. Current
  Project-route normalization gives that value precedence over
  `projects.user_id`, so user-facing description storage can alter Project
  authorization and visibility.

Live private-preview inspection proved that both patterns exist: one Project
has matching column and envelope owners, another account-owned Project relies
only on the column, and two legacy Projects remain owned by `local` with plain
human descriptions. A related history incident proved that canonical threads
were not lost, but thread owners and their linked legacy Project owners can
disagree.

Maintaining the two values as synchronized co-authorities would preserve the
defect. Every create, update, migration, restore, import, and authorization read
would need a precedence rule and perfect dual-write behavior. Partial upgrades
or stale rows could still diverge, and presentation storage would remain a
security boundary.

Private preview also remains at Alembic revision `f41493d13761`, while the
repository head is `b2c8d0e3f5a7`. Revisions `a1b7c9d2e4f6` and
`b2c8d0e3f5a7`, which introduce and refine the direct-messaging persistence
domain, intervene. This decision does not qualify or cross that migration gap.

## Decision

`projects.user_id` is the sole canonical durable ownership authority for a
Project.

Project authorization, visibility, account-scoped uniqueness, migration
reasoning, export and restore, and future Project operations must converge on
that field. Human-visible description data must never grant, deny, transfer,
select, or override account authority.

Thread ownership remains independently authoritative for threads. This
decision does not rewrite `chat_threads.user_id` to match Project ownership or
rewrite Project ownership merely to match a thread without the bounded
evidence rules below. Project IDs and thread-to-Project relationships remain
stable unless a separately governed migration proves a change necessary.

### Legacy description envelope

The `__codexify_project_owner__` marker and its `owner_user_id` value are
legacy compatibility metadata, not canonical authority.

During a bounded transition they may be read only for:

- migration discovery;
- consistency-conflict detection;
- bounded evidence of historical intent when evaluating a separately governed
  reconciliation.

They must not, in the target state:

- override `projects.user_id`;
- grant or deny Project access;
- select an account;
- transfer ownership;
- be recreated by ordinary Project writes; or
- regain authority during export, import, backup, or restore.

Compatibility metadata may exist temporarily while remediation is incomplete,
but no synchronized dual-authority target is permitted.

### Row classification and transition semantics

Future remediation must classify each Project before changing it.

#### Matching envelope

When `description.owner_user_id == projects.user_id`, remediation may unwrap
the envelope, preserve its complete human-visible description as the ordinary
description value, remove the ownership marker and embedded owner value, and
leave `projects.user_id` unchanged.

Human description preservation is required. Removing the wrapper must not
erase, trim, reinterpret, or replace the user's description merely because it
was stored in the compatibility envelope.

#### Canonical column only

A Project with a valid non-`local` `projects.user_id` and no legacy ownership
envelope is already ownership-canonical. Remediation must not add an envelope
or manufacture a second owner representation.

#### Conflicting owners

When `description.owner_user_id != projects.user_id`, the condition is
classified as:

`project_ownership_authority_conflict`

This is a consistency defect, not a precedence rule. Automated migration must
detect it, report bounded Project and owner evidence without exposing unrelated
content, and fail closed. Neither the legacy envelope nor the column may win by
simple request-time or migration-time precedence. A separately evidenced
reconciliation is required whenever accepted durable authority cannot establish
the canonical owner unambiguously.

The current `_normalize_project_row()` envelope-over-column behavior is
technical debt and must be removed by a later implementation task. This ADR
does not change that runtime code.

#### Legacy `local` owner

A future reconciliation may replace `projects.user_id = 'local'` with a
non-local account owner only when durable canonical relationships prove exactly
one unambiguous owner and no other ownership authority conflicts.

For the identified chat-history seam, sufficient evidence may be established
when all canonical threads referencing the Project have exactly one distinct,
non-`local` `chat_threads.user_id`, and no referencing thread belongs to any
other account. The migration must fail closed or perform no ownership change
when:

- multiple distinct account owners reference the Project;
- no ownership-bearing relationship provides sufficient evidence;
- there are no referencing threads from which this rule can establish an
  owner; or
- another accepted canonical authority conflicts.

The authenticated request, frontend selection, Project display name, current
operator, or deployment account must never supply the inferred owner. The
contract must not encode a particular operator account ID. Existing
second-account isolation remains mandatory.

### Project creation and mutation

Future Project creation must resolve the authenticated or otherwise canonical
owner through the governed account boundary and persist it only in
`projects.user_id`. The `description` field stores only the actual human
description. New rows must never receive the legacy ownership envelope.

Ordinary Project updates must not transfer ownership. Any future ownership
transfer requires a separate, explicit authority-changing operation with its
own authorization, audit, consistency, and migration contract.

### Authorization and visibility

The target rule is:

`Project owner = projects.user_id`

All Project visibility and ownership checks must converge on this rule. Runtime
code must not decode description metadata to make an authorization decision.
Until the later convergence task removes the existing route precedence,
current runtime remains inconsistent with this accepted target architecture.

### Export, import, and restore

Exports, imports, backups, and restores must treat `projects.user_id` as
authority-bearing account state. Human description data remains content.
Legacy envelope owner metadata may be retained temporarily for evidence or
cleaned during a governed migration, but a round trip must never promote it
back into authorization authority or use it to replace the canonical Project
owner.

This ADR does not define a new export format.

## Migration sequencing

Implementation must remain split into independently authorized slices:

1. **Project-ownership runtime/data convergence.** Stop new envelope writes,
   make authorization read `projects.user_id`, classify existing envelopes,
   preserve human descriptions, and fail closed on conflicts.
2. **Legacy `local` Project reconciliation.** Reassign only rows that satisfy
   the exact durable-evidence rule, while preserving Project IDs, thread links,
   thread ownership, and account isolation.
3. **Private-preview Alembic lineage qualification.** Review and qualify the
   path from `f41493d13761` through the two direct-messaging migrations to the
   repository head before applying any later ownership migration.

These are separate gates. Private preview must not receive ownership
remediation merely by running `alembic upgrade head` while the intervening
revisions remain unqualified for that instance.

## Rejected alternatives

### Synchronized column and description-envelope co-authority

Rejected. Synchronization does not remove the duplicate truth surface. It
retains divergence risk, precedence-dependent authorization, dual-write and
restore obligations, and security authority in user-facing description text.

### Envelope precedence

Rejected. The envelope is compatibility metadata without schema-level
ownership constraints. Existing request-time precedence is not a migration or
conflict-resolution rule.

### Column precedence for conflicting rows

Rejected as an automatic migration rule. Although `projects.user_id` is the
canonical target field, an already-divergent durable row is evidence of a
consistency defect. Automated remediation must first fail closed rather than
silently discard conflicting historical evidence.

### Rewrite every `local` Project to the active account

Rejected. Session state and operator context are not durable ownership proof
and could violate second-account isolation.

## Consequences

### Positive

- Project ownership has one schema-backed source of truth.
- Presentation text leaves the authorization boundary.
- New writes, account-scoped uniqueness, authorization, and restore semantics
  can converge without permanent dual-write behavior.
- Legacy reconciliation is bounded by durable evidence and fails closed when
  ambiguous.

### Negative

- Runtime and stored data do not yet conform to the decision.
- Existing envelope rows require classification and description-preserving
  cleanup.
- Conflicting rows require evidence and operator-governed reconciliation rather
  than automatic precedence.
- Private-preview deployment is additionally gated by its Alembic lineage gap.

## Current-truth and release boundary

This ADR is architecture doctrine only.

- Current Project routes still allow description-envelope ownership to override
  `projects.user_id` during normalization and visibility checks.
- Current databases still contain legacy owner representations and `local`
  Project ownership.
- Private preview remains at `f41493d13761`; repository Alembic head remains
  `b2c8d0e3f5a7`.
- No runtime code, Project row, thread row, migration state, export format,
  frontend behavior, release support, or current-state claim changes merely
  because this ADR is accepted.

`docs/architecture/00-current-state.md` remains the authority for current
release truth.

## Governing and related records

- Extends [[005-runtime-mode-and-account-boundary-invariants|ADR-005 Runtime
  Mode and Account Boundary Invariants]] by selecting the canonical
  Project-specific owner representation. ADR-005 is not superseded.
- Preserves [[076-archive-before-delete-and-built-in-project-roles|ADR-076
  Archive Before Delete and Built-In Project Roles]], including account-scoped
  built-in role uniqueness, lifecycle rules, and stable Project IDs.
- Aligns with [[../data-and-storage|Data and Storage]] and
  [[../remote-account-access-and-user-profile-contract|Remote Account Access
  and User Profile Contract]] on schema-backed account identity and
  presentation-data non-authority.
- Uses [[../proofs/2026-09-03-chat-history-disappearance-proof|Chat History
  Disappearance Boundary Proof]] as incident evidence; it does not reinterpret
  that proof as runtime remediation.
- Uses [[../proofs/2026-08-24-local-account-mode-reconciliation-proof|Local
  Account-Mode Reconciliation Proof]] as evidence that runtime/session posture
  must not silently redefine durable ownership.
