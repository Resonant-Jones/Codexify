# ADR-085: Legacy Shared Built-In Project Retirement Exception

**Status:** Accepted

**Human approver:** Resonant Jones

**Accepted:** 2026-09-11

## Approval and scope

Resonant Jones explicitly dispatched the task "Authorize retirement of
obsolete legacy shared built-in Projects" for execution. Under that task's
human-dispatch rule, this records acceptance of the bounded architecture
decision below. It does not authorize runtime implementation or live database
mutation. Every eventual retirement requires an explicitly authorized repair
task; this ADR and a proof receipt are not executable permission.

This ADR partially supersedes [ADR-076](./076-archive-before-delete-and-built-in-project-roles.md)
only for physical retirement of an evidence-proven obsolete legacy shared
built-in source. It clarifies the partition and retirement gates in
[ADR-081](./081-project-ownership-authority.md). Canonical built-in immutability,
ordinary Project lifecycle rules, and ownership authority remain unchanged.

## Context and evidence

Private Preview recovery stopped at a contract contradiction. ADR-076 forbids
archiving or deleting built-in Projects, and ADR-081's shared-General doctrine
previously preserved that prohibition even after partition and zero-reference
proof. Meanwhile, the unmodified
`d4e8f1a2b6c9_reconcile_legacy_local_project_owners.py` migration rejects an
empty `local` Project as `unresolved_no_referencing_threads`.

The [legacy shared-General preflight and complete account-census addendum](../proofs/runtime/2026-09-09-legacy-shared-general-partition-preflight.md)
record Project `1` as `user_id='local'`, `system_role='general'`, with eight
threads owned by three distinct canonical non-local accounts. The `5 / 2 / 1`
distribution is preservation evidence, not authority to assign the Project to
one account. The full registry census records five non-local accounts plus
the legacy `local` row; the three affected owners are not the whole account
population. These are dated repository proof records, not a fresh live census.

Under ADR-081, the source cannot receive an inferred canonical owner. Leaving
it empty and `local` cannot clear the migration. A separate retirement class
is therefore needed; making canonical built-ins generally deletable is not.

`guardian/core/project_lifecycle.py` correctly rejects ordinary built-in
archive/delete attempts with `project_system_container_immutable`. That
implementation is unchanged and is not an exceptional repair interface.

## Decision

### Canonical built-in Projects remain immutable

A canonical account-owned Project with a non-null built-in `system_role` may
not be archived or deleted through ordinary Project lifecycle behavior. This
applies to account-owned General and Imports Projects, user-facing lifecycle
APIs and UI, `guardian/core/project_lifecycle.py`, and ordinary runtime
behavior. Renaming does not remove built-in protection; the existing
prohibition on restoring built-ins also remains unchanged.

`projects.user_id` remains canonical Project ownership authority, bound to
the canonical account registry. `system_role` remains structural built-in
identity. `chat_threads.user_id` may route a thread to its owner's destination
but never establishes ownership of the legacy source Project.

### Legacy shared built-in source classification

Classification requires durable evidence of historical compatibility state
that cannot satisfy current Project ownership invariants. The exception is
bounded to the legacy shared General class established by this incident;
another built-in role or ownership topology is not admitted by analogy.

For Project `1`, the preserved pre-partition evidence must establish all of:

- the canonical owner field contains the legacy `local` principal;
- the structural role is `general`;
- its canonical contents belong to multiple distinct non-local accounts;
- ADR-081 prohibits selecting any one of those accounts as source owner;
- the source predates the current account-scoped General topology; and
- canonical replacement containers can be created or reused for the affected
  accounts under ADR-081.

Neither `user_id='local'`, a non-null `system_role`, emptiness, nor a display
name is sufficient. The dated preflight supports this classification, not
present retirement eligibility. A repair must revalidate source state and
retain the pre-partition evidence: empty state after partition does not prove
that a Project was a legacy shared source.

### Dedicated operator repair and preservation order

Legacy-source retirement is a dedicated bounded operator repair. It is not
archive, user deletion, REST/API deletion, lifecycle UI behavior, normal
built-in cleanup, garbage collection, or migration inference. A future repair
may physically remove only the eligible obsolete source row through that
dedicated mechanism; it must not expose or reuse a user-facing lifecycle
capability to evade built-in immutability.

The required order is:

```text
backup
  -> source census
  -> restored-copy rehearsal
  -> deterministic partition
  -> dependency relocation
  -> preservation proof
  -> zero-reference proof
  -> legacy-source retirement
  -> migration traversal
```

The restored-copy rehearsal must exercise partition through retirement and
normal migration traversal before any live repair. Revalidate live source
state against the approved census before applying the same proven mechanism;
drift or failed preservation proof blocks application. Use bounded
transactions with rollback on failed invariants, as required by ADR-081.

Partition routes each thread from its existing canonical owner to that
account's General. It preserves thread IDs, owners, messages, content,
ordering, provenance, and dependent lineage. Canonical threads must never be
loose at a committed persistence boundary. No replacement General is created
for `local`. Every dependent must be relocated through accepted authority or
proven independent of the source; retirement may not discard canonical rows.

### Zero-reference and ambiguity gates

Physical retirement is eligible only after preservation proof and all three
conditions:

```text
canonical threads referencing source Project = 0
canonical direct dependencies requiring source Project = 0
unresolved dependencies = 0
```

The census must derive from the relevant current PostgreSQL foreign-key
topology and every explicitly modeled non-FK Project relationship used by
runtime persistence. A stale hard-coded table list is insufficient. Prove
that retirement cannot orphan canonical state or silently discard or null
dependencies through delete actions. An indirect reference through a stable
thread ID needs no rewrite when it remains valid independently of the source.

ADR-081's lineage rules remain in force: thread-bound dependents follow their
authoritative thread; independently account-owned dependents follow accepted
canonical account authority. A Project-only dependent without authoritative
thread/account lineage blocks repair and retirement with
`AMBIGUOUS_PROJECT_ONLY_DEPENDENCY`. Do not duplicate, discard, null,
majority-assign, operator-assign, or arbitrarily assign it to permit retirement.

Partition completion and retirement eligibility remain separate proof states.
Neither classification nor partition completion is permission to delete.

### Preserve source identity; no archive conversion

The source's historical ID, owner, and built-in role remain intact until
retirement. Do not assign Project `1` to Jones, Maatariki, Krista, another
canonical account, or a synthetic/system principal. Do not clear `system_role`
to make ordinary deletion legal. Renaming cannot reclassify the source.

ADR-076's `active -> archived -> permanently deleted` flow continues to apply
to ordinary Projects. Do not convert the legacy source into an ordinary
archived Project. After the exceptional preservation and zero-reference gates
pass, the explicitly authorized operator repair may retire it directly,
without archival. This is the sole partial supersession of ADR-076's absolute
built-in deletion prohibition; canonical built-in lifecycle behavior is not
weakened.

### Durable repair evidence

Every retirement operation must have a durable proof receipt identifying:

- source Project identity and pre-repair database revision;
- retained source backup/checkpoint identity and hash;
- source census, affected accounts, and canonical partition mapping;
- dependency census and lineage classification;
- preservation and zero-reference results;
- retirement result; and
- subsequent normal migration result, including any failure or remaining gate.

The receipt is evidence, not authority. It must not expose credentials or
canonical content unnecessarily. Backup retention and restored-copy rehearsal
must support recovery of the pre-repair state; acceptance of this ADR proves
neither operational readiness nor successful repair.

### No automatic cleanup or migration bypass

Reject `if built-in looks unused -> delete it`. There is no automatic cleanup
rule, generic startup cleanup, new background reconciliation process, or
permission for an agent to retire a built-in merely because it is empty.

Historical migrations remain unchanged and fail closed. In particular,
`d4e8f1a2b6c9` is neither modified nor bypassed, stamped, re-parented, or
manually marked applied. Normal Alembic traversal follows the separately
proven repair.

## Consequences and rejected alternatives

The architecture now permits a legal terminal state for an obsolete source
without inventing its ownership or making canonical built-ins deletable.
Implementation still requires a separate operator utility, exact census,
restored-copy proof, and explicit repair authorization.

Rejected alternatives are assigning the source by majority or operator
identity; laundering its owner, role, or name; retaining an empty `local`
source as though migration were unblocked; dropping ambiguous dependencies;
weakening ordinary lifecycle enforcement; and automatic cleanup of unused
built-ins. None satisfies the preservation and authority boundary.

## Current-truth and implementation boundary

This task establishes `documented-contract` evidence. The existing lifecycle
guard and migration rejection are `proven-code-path` evidence only. No runtime
tests or live inspection are performed by this architecture task.

Project `1` remains untouched, unpartitioned, and unretired. The last
documented live revision is `d4e0f2a5b7c9`; repository account-scoped Project
name support and the account-owned General helper do not prove live upgrade.
Private Preview repair, Alembic traversal, startup, authenticated account
isolation/read proof, and Chroma qualification remain open. Private Preview
is not restored or newly validated by this decision.

No lifecycle/runtime code, route, UI, test, operator script, schema, migration,
Project, General container, thread, backup, or Chroma state changes here. This
ADR does not wire account provisioning or widen Beta/release claims.
[Current state](../00-current-state.md) remains release truth.

The deferred task is to rehearse and apply the Project `1` preservation
partition/retirement repair, resume the canonical Alembic path, and attempt
Private Preview startup. It must not begin automatically on ADR acceptance.
