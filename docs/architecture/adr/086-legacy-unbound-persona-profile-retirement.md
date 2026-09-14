# ADR-086: Legacy Unbound Persona Profile Retirement

**Status:** Accepted

**Date:** 2026-09-11

**Approver:** Resonant Jones

## Approval and execution boundary

Resonant Jones explicitly dispatched the task "Define retirement authority for
globally seeded unbound Persona Profiles" for execution. This records
acceptance of the bounded disposition policy below. It authorizes no runtime,
database, migration, provider, or Private Preview operation. Every candidate
must be qualified individually, and every eventual retirement requires a
separately authorized operator reconciliation task.

```text
DISPOSITION_POLICY_AUTHORIZED=true
SPECIFIC_PROFILE_RETIREMENT_ELIGIBILITY_UNPROVEN=true
```

This decision is a legacy-data reconciliation exception aligned with
[ADR-082](./082-persona-profile-manifest-and-binding-authority.md) and
[ADR-084](./084-unified-account-owned-memory-store.md). It adopts the
preservation, restored-copy rehearsal, dependency-census, and fail-closed
governance pattern used by [ADR-085](./085-legacy-shared-built-in-project-retirement-exception.md),
but ADR-085 does not govern Persona Profiles and supplies no Persona retirement
authority by itself.

## Context

The canonical Alembic path is stopped at
`e5a9c2f7b4d1_add_persona_subject_identity`. The migration correctly rejects an
unbound Persona Profile because an account-owned Persona subject may be created
only from a source with established canonical account ownership.

The stopped ownership investigation found three historical globally seeded
Persona Profile rows with no `PersonaProfileBinding`:

- `profile-1`
- `profile-2`
- `profile-3`

For `profile-1`, bounded current and historical evidence found no canonical
owner candidate: there is no binding or owner field, no thread reference, no
relevant durable audit/control-plane record, no binding-bearing account export,
and no preserved same-lineage snapshot satisfying the accepted single-user
legacy condition. Chronology and operator association are non-authoritative.
No authoritative binding-validity timestamp can be reconstructed.

The historical seed migration created all three rows as global compatibility
state rather than through the later account-scoped authored-profile path.
`profile-2` and `profile-3` are likewise unbound, but their complete retirement
eligibility and the complete dependency census for all three rows remain
unproven.

Fabricating an owner would violate ADR-082. Silently skipping an unbound source
in `e5a9c2f7b4d1` would violate ADR-084's account-owned stable Persona-subject
contract. Keeping obsolete global seed rows as a permanent ownerless runtime
class would create a third authority state that neither decision accepts.

## Decision

### Canonical Persona Profiles remain account-bound

A canonical runtime-bearing `PersonaProfile` participating in account-scoped
Persona Studio or Unified Memory Store semantics must have a valid,
server-owned `PersonaProfileBinding`. The binding remains the sole canonical
profile-to-account authority.

An ownerless historical seed row is legacy migration debt. It is not a new
permanent `global`, `local`, `operator`, `unowned`, or other ownerless Persona
Profile class. It is also not system-owned merely because it was seeded.
Codexify therefore retains only the existing authority distinction:

```text
account-owned Persona Profile -> valid PersonaProfileBinding
system-owned runtime profile  -> independently governed system-profile source
```

Historical global seed state establishes neither branch by itself.

### Ownership must not be fabricated

No binding may be created from:

- current operator identity;
- current logged-in user;
- Project ownership;
- majority thread usage;
- chronology alone;
- profile name;
- prompt, model, manifest, or other profile content;
- email similarity;
- the current number of accounts;
- arbitrary account selection; or
- historical existence alone.

The legacy backfill in `c3d9e1f4a6b8` remains an accepted, narrow historical
rule: that migration could bind legacy profiles only when the migration itself
observed exactly one canonical user. That rule is not a current fallback and
must not be applied retroactively when preserved evidence shows multiple users
or cannot prove the exact single-user condition.

If canonical owner evidence exists for a candidate, the candidate must leave
this retirement lane and enter a separately authorized binding reconciliation.
If ownership evidence is ambiguous, do not assign an owner and do not retire
the row under this exception.

### Legacy global seed classification

Retirement evaluation begins with provenance, before dependency or deletion
reasoning. Durable repository and/or preserved-database evidence must prove
that the row originated from the historical global seed path rather than an
account-scoped authored Persona Profile operation.

```text
LEGACY_GLOBAL_SEED_PROFILE=true
```

The profile identifier, display name, contents, timestamps, or absence of a
binding cannot establish this classification alone. If provenance is
ambiguous, the reconciliation stops with:

```text
RESULT=BLOCKED
REASON=AMBIGUOUS_LEGACY_PERSONA_PROFILE_PROVENANCE
```

### Retirement eligibility

A proven legacy globally seeded Persona Profile may be physically retired from
the active runtime database only when one bounded reconciliation proves every
gate below for that specific row:

```text
LEGACY_GLOBAL_SEED_PROFILE=true
CANONICAL_BINDING_COUNT=0
CANONICAL_OWNER_EVIDENCE_COUNT=0
THREAD_REFERENCE_COUNT=0
REQUIRED_DEPENDENCY_COUNT=0
UNRESOLVED_DEPENDENCY_COUNT=0
PRESERVATION_COMPLETE=true
RESTORED_COPY_REHEARSAL=PASS
```

Zero owner evidence is not ownerless runtime authority. It is one prerequisite
for retiring obsolete seed debt without laundering it into account authority.
Likewise, zero current references is evidence, not execution permission.

The dependency census must derive from both the current PostgreSQL foreign-key
topology and semantic/application references not expressed as foreign keys. It
must include profile registry, revision, binding, thread-selection,
Persona-subject, memory-attribution, import/export, event, audit, and other
runtime relationships present at the execution revision. A stale hard-coded
table list is insufficient.

Revision rows belonging solely to the retired profile may be retired with it
only after their complete preservation and proof that no external relationship
requires them. Delete actions, cascades, triggers, and application semantics
must be included in the rehearsal and dependency proof; a cascade does not
convert a dependency into permission to discard it.

If any dependency cannot be classified or its preservation cannot be proven,
the candidate remains active migration debt and the operation stops with:

```text
RESULT=BLOCKED
REASON=AMBIGUOUS_PERSONA_PROFILE_DEPENDENCY
```

### Referenced, owned, or ambiguous rows fail closed

The disposition is deterministic:

| Candidate condition | Required handling |
| --- | --- |
| Canonical binding or one proven canonical owner | Reconcile through a separately authorized binding task; do not retire. |
| Any runtime reference or required dependency | Preserve the row; do not retire. |
| Ambiguous owner evidence | Assign no owner and do not retire under this rule. |
| Ambiguous provenance | Stop with `AMBIGUOUS_LEGACY_PERSONA_PROFILE_PROVENANCE`. |
| Ambiguous dependency | Stop with `AMBIGUOUS_PERSONA_PROFILE_DEPENDENCY`. |
| Every retirement gate proven | A separately authorized operator repair may retire the obsolete row. |

No profile is duplicated, majority-assigned, operator-assigned, content-matched,
silently skipped, or partially retired to make migration traversal succeed.

### Preservation and restored-copy rehearsal

Historical preservation occurs outside the active runtime database before any
retirement. The subsequent operator reconciliation must retain a verified
complete pre-mutation backup, a bounded source/provenance ledger, the complete
dependency census, profile and revision integrity material, the exact proposed
operation, and enough evidence to restore the pre-retirement state.

The identical candidate disposition must first run on a freshly restored,
network-isolated copy. The rehearsal must:

1. prove the source revision and every candidate precondition;
2. exercise the exact transactional retirement and all database delete effects;
3. prove that registry, revision, thread, account, Project, and unrelated rows
   remain preserved;
4. prove zero unresolved dependencies and no orphaned canonical state;
5. use normal Alembic traversal to confirm that `e5a9c2f7b4d1` accepts the
   reconciled source state; and
6. retain failure and rollback evidence.

A successful rehearsal is proof, not live authority. Live mutation still
requires a separate explicit task, source-state revalidation against the
rehearsal, and rollback on any drift.

### Retirement is not archival into another authority

Retirement under this exception must not:

- assign a temporary, inferred, synthetic, service, or placeholder owner;
- create a fake `PersonaProfileBinding`;
- create a synthetic `PersonaSubject` or subject binding;
- attach the profile to a Project;
- convert it into an account export;
- rewrite its manifest identity or revision history;
- relabel it as an account-owned profile; or
- expose a generic Persona lifecycle or deletion API.

Preservation outside the active runtime database is not an archive that gains
account or execution authority. The retired row does not become portable
account state merely because its bytes were retained.

### Global seed rows are not system profiles

This exception does not classify `profile-1`, `profile-2`, or `profile-3` as
canonical built-in or system Persona identities. It creates, modifies, and
migrates no system-profile definition. Equivalent presets elsewhere, if any,
derive authority independently and neither justify nor block retirement of an
eligible obsolete seed row.

### The Persona-subject migration remains fail-closed

`e5a9c2f7b4d1_add_persona_subject_identity.py` remains correct and unchanged:

```text
missing canonical binding -> migration abort
```

This ADR does not authorize:

```text
missing canonical binding -> silently skip
```

The migration may create account-owned Persona subjects only from sources with
proven canonical account ownership. ADR-086 resolves eligible bad legacy source
state before normal traversal; it does not weaken classification during
traversal, stamp a revision, invoke migration code directly, or create a bypass.

### Known-candidate scope

The immediate discovered class contains `profile-1`, `profile-2`, and
`profile-3`. One subsequent reconciliation may evaluate all three because
`e5a9c2f7b4d1` requires every source to be classifiable before backfill.

This ADR declares none of the three retirement-eligible. Each requires its own
proven provenance, owner-evidence result, reference and dependency census, and
preservation result inside the common restored-copy rehearsal. One ineligible
or ambiguous row remains a migration blocker and must not be adapted around.

## Relationship to existing decisions

- **ADR-082** remains the governing Persona Profile manifest and binding
  authority. `PersonaProfileBinding` semantics are unchanged.
- **ADR-084** remains the governing account-owned Memory Store and stable
  Persona-subject authority. Account ownership and attribution semantics are
  unchanged.
- **ADR-085** is analogous only in preservation and reconciliation discipline.
  It does not govern Persona Profiles and is not broadened by this decision.
- **ADR-058** continues to classify legacy Persona state as migration debt, not
  a parallel canonical profile authority.
- **ADR-069** continues to separate architecture acceptance from runtime and
  release proof.

```text
ADR_082_SEMANTICS_CHANGED=false
ADR_084_SEMANTICS_CHANGED=false
```

ADR-086 does not supersede another ADR. It defines the missing terminal
disposition for one evidence-bounded legacy data class.

## Rejected alternatives

### Infer an account owner

Rejected. Current user, operator, Project association, chronology, usage,
profile contents, similarity, and arbitrary selection are not
`PersonaProfileBinding` authority.

### Add a permanent ownerless Persona Profile class

Rejected. It would create a third authority state and permit runtime-bearing
configuration or Persona attribution without an account boundary.

### Convert seed rows into system profiles

Rejected. Historical database seeding does not establish canonical
system-profile identity or authority.

### Teach `e5a9c2f7b4d1` to ignore unbound profiles

Rejected. Silent omission would hide unresolved source state and weaken the
account-owned Persona-subject invariant.

### Delete any unbound or unused-looking profile automatically

Rejected. An absent binding or apparent emptiness does not prove global seed
provenance, absence of semantic dependencies, preservation, or operator
authority.

## Current truth and implementation boundary

Proven before this decision:

- `profile-1` originated from the historical global seed path, has zero
  bindings, has no provable canonical owner, and has zero thread references;
- `profile-2` and `profile-3` originated from the same historical global seed
  path and are unbound;
- `e5a9c2f7b4d1` fails closed on an unbound Persona Profile;
- Project `1` has been partitioned and retired under ADR-085;
- the last documented live Private Preview revision remains `d4e0f2a5b7c9`;
  and
- Private Preview application writers remain quiesced.

Not yet proven:

- retirement eligibility for any of `profile-1`, `profile-2`, or `profile-3`;
- the complete current dependency census for all three candidates;
- a restored-copy Persona retirement rehearsal;
- live Persona retirement;
- successful complete Alembic traversal; or
- Private Preview startup or release readiness.

This decision resolves the missing architecture disposition, not the data
repair. It changes no model, migration, route, runtime profile, database row,
Persona subject, system profile, Project, Chroma state, provider behavior,
startup state, or release claim.

## Consequences

### Positive

- Obsolete global seed debt gains a lawful terminal path without fabricated
  account ownership.
- ADR-082 binding authority and ADR-084 account-owned attribution remain intact.
- Dependency ambiguity and preservation remain explicit hard gates.
- Normal Alembic traversal can remain fail-closed.

### Negative

- The three known rows remain unresolved until a separate evidence and repair
  task qualifies them.
- A complete semantic dependency census is more work than checking foreign
  keys alone.
- One ambiguous candidate can continue to block the migration path.

## Invariants

- No Persona Profile owner is fabricated.
- `PersonaProfileBinding` remains canonical account-binding authority.
- Ownerless legacy rows do not become a permanent authority class.
- Project or operator authority is not Persona Profile ownership.
- Profile contents and chronology are not ownership evidence.
- Historical single-user auto-binding is not retroactively broadened.
- `e5a9c2f7b4d1` remains unchanged and fail-closed.
- Legacy retirement requires proven seed provenance, preservation,
  restored-copy rehearsal, and zero external or unresolved dependencies.
- Ambiguity blocks retirement.
- Retirement creates no synthetic binding, Persona subject, or system profile.
- Specific eligibility for the three known candidates remains a subsequent
  proof task.
- No release claim advances.

## Follow-on task

The next separately authorized architecture-impact task is **Qualify and retire
orphaned legacy Persona Profiles**. It must evaluate `profile-1`, `profile-2`,
and `profile-3` individually, preserve the source database, derive both FK and
semantic dependency censuses, rehearse the exact operation on a restored copy,
revalidate live state, and prove any live retirement before Alembic may resume.
