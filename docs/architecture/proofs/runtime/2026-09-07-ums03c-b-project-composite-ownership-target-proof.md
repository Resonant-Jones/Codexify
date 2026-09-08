# UMS-03C-B Project Composite Ownership Target Proof

Date: 2026-09-07

Status: **PASSED — DOCUMENTATION-ONLY CONTRACT AMENDMENT**

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: architecture-contract amendment
- Evidence posture: documentation-only; no SQL was added, no
  ORM model was changed, no Alembic migration was added, no
  runtime writer / reader / retrieval / export behavior was
  changed, and no new ADR was created
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-03C-B
- Starting HEAD: `6508920fa9243c18195618356907a46fe8d874e5`
- UMS-03C prerequisite commit: `417025ac8bc1ffa47c4f3ce6cd2f4170f139db69`
- UMS-03C-A prerequisite commit: `6508920fa9243c18195618356907a46fe8d874e5`
- UMS-03D current state: was BLOCKED; is now AUTHORIZED TO RESUME
- UMS-03: OPEN
- UMS-03E: NOT AUTHORIZED
- UMS-04: NOT AUTHORIZED

## UMS-03D PostgreSQL STOP reason (recorded)

The UMS-03D pre-execution stage produced three ORM models
(`MemoryRecord`, `MemoryPersonaLink`, `MemoryProvenance`) in
`guardian/db/models.py` and the Alembic migration
`f6b0d3e8c5a2_add_canonical_memory_persistence.py` with the
`IMPLIES` → `NOT (...) OR ...` PostgreSQL-safe form already
applied. PostgreSQL qualification of the resulting migration
returned:

```text
psycopg.errors.InvalidForeignKey:
  there is no unique constraint matching given keys for
  referenced table "projects"
```

The error blocked the upgrade at the first composite foreign
key declaration. No UMS-03D code was committed, no UMS-03D
WIP was modified, and no runtime authority changed.

## Repository investigation (proven)

`docs/architecture/unified-memory-store-contract.md`
§4.16.2 (column table) and §4.16.7 (cross-table integrity
invariants) freeze the composite FK
`(project_id, user_id) → projects (id, user_id)` with
`ON DELETE RESTRICT`.

`guardian/db/models.py` lines 879–928 define `Project`:

- `id: Mapped[int] = mapped_column(Integer, primary_key=True,
  autoincrement=True)` — primary key on `id` alone.
- `user_id: Mapped[str] = mapped_column(String(255),
  ForeignKey("users.id", ondelete="CASCADE"), nullable=False)`
  — the canonical Project account authority field.
- The `__table_args__` block contains two CHECK constraints
  and one **partial** unique index:
  `Index("uq_projects_user_id_system_role", "user_id",
  "system_role", unique=True, postgresql_where=text("system_role
  IS NOT NULL"))`. This partial index is unrelated to
  `(id, user_id)` and cannot serve as a composite FK target.

A repository-wide search for any
`UniqueConstraint(... id ... user_id ...)` or
`uq_projects_id_user_id` returns no result. The target
`(projects.id, projects.user_id)` is not currently
uniqueness-constrained.

The corresponding `persona_subjects` table already carries
the required target at lines 4268–4272 of `models.py`:
`UniqueConstraint("persona_subject_id", "user_id",
name="uq_persona_subjects_subject_user")`. The
`memory_persona_links` composite FK target therefore
exists. The blocker is isolated to the `projects` side.

## Required proof statements

```text
CURRENT PROJECT IDENTITY:
  PRIMARY KEY (id)

CURRENT PROJECT OWNERSHIP:
  user_id

MISSING RELATIONAL TARGET:
  UNIQUE (id, user_id)

POSTGRESQL FAILURE:
  no unique constraint matching given keys for
  referenced table "projects"

FROZEN ENABLING CONSTRAINT:
  CONSTRAINT uq_projects_id_user_id
  UNIQUE (id, user_id)

UMS-03D TOPOLOGY:
  e5a9c2f7b4d1
      ↓
  f6b0d3e8c5a2

PROJECT DATA MUTATION:
  NONE

RUNTIME AUTHORITY CHANGE:
  NONE
```

## Why the constraint is non-destructive

`projects.id` is the canonical primary key. No two rows can
share `id`. Therefore no row can produce a duplicate
`(id, user_id)` pair, and the new `UNIQUE (id, user_id)`
constraint cannot reject any valid existing Project row.
The migration that adds the constraint is a pure schema
operation that:

- does not rewrite any Project field;
- does not backfill any Project row;
- does not delete any Project row;
- does not transfer Project ownership;
- does not change the canonical Project identity
  (`projects.id`) or the canonical Project ownership field
  (`projects.user_id`);
- cannot fail on any existing live `projects` row.

The new constraint exists solely to make
`(projects.id, projects.user_id)` a legal PostgreSQL
composite foreign key target. The composite FK was already
frozen by UMS-03C §4.16.2 and §4.16.7; this amendment
provides the relational prerequisite that PostgreSQL
required to define it.

## Frozen enabling constraint

```sql
ALTER TABLE projects
ADD CONSTRAINT uq_projects_id_user_id
UNIQUE (id, user_id);
```

Canonical constraint name: `uq_projects_id_user_id`.

## Frozen UMS-03D ORM representation

```python
UniqueConstraint(
    "id",
    "user_id",
    name="uq_projects_id_user_id",
)
```

This must live on the existing `Project` table metadata in
`guardian/db/models.py`. UMS-03D must not create a parallel
Project table or shadow ownership surface.

## Frozen UMS-03D migration ordering

The UMS-03D first migration is a single additive
persistence-groundwork revision. Its frozen upgrade scope
is:

```text
1. add uq_projects_id_user_id
2. create memory_records
3. create memory_persona_links
4. create memory_provenance
5. create their frozen indexes / constraints
```

The `memory_records` composite FK
`(project_id, user_id) → projects (id, user_id)` is created
only after step 1 has succeeded.

The UMS-03D downgrade must remove all UMS-03D
canonical-memory schema objects before dropping the
enabling Project constraint, because dropping the
constraint first would leave the memory composite FK
pointing at an unsupported target during the gap. The
frozen downgrade order is:

```text
1. drop memory_provenance
2. drop memory_persona_links
3. drop memory_records
4. drop uq_projects_id_user_id
```

## Rejection of a separate Alembic prerequisite revision

UMS-03C-B explicitly rejects the topology

```text
e5a9c2f7b4d1
    ↓
<project-only precondition revision>
    ↓
f6b0d3e8c5a2
```

unless future evidence proves the combined migration cannot
be safely implemented. The current authorized topology
remains one atomic additive revision:

```text
e5a9c2f7b4d1
    ↓
f6b0d3e8c5a2
```

## Additive-migration doctrine preserved

UMS-03D's expanded upgrade scope remains additive. It may:

- add one relational uniqueness constraint on
  `projects`;
- create three empty canonical memory tables;
- create their constraints and indexes.

It may not:

- rewrite Project ownership;
- modify Project row values;
- backfill Project rows;
- delete Project rows;
- backfill legacy memory;
- mutate legacy memory;
- redirect memory readers;
- redirect memory writers;
- transfer runtime authority.

## Qualification evidence required by UMS-03D

UMS-03D qualification on disposable PostgreSQL must prove
all of the following on a fresh disposable database and on a
seeded legacy-bearing disposable database:

- `uq_projects_id_user_id` exists after the upgrade.
- `memory_records (project_id, user_id) → projects (id,
  user_id)` is accepted by PostgreSQL.
- An account-A memory row referencing an account-A Project
  is accepted.
- An account-A memory row referencing an account-B Project
  is rejected at the relational boundary, with the rejection
  attributable to the composite FK rather than to
  application-only enforcement.
- An existing-schema upgrade preserves every `projects` row
  byte-for-byte. The constraint changes schema only.
- The downgrade round trip preserves legacy
  `memory_entries` and `personal_facts` rows unchanged.

## Protected UMS-03D WIP fingerprints (BEFORE the amendment)

These hashes record the exact state of the uncommitted
UMS-03D WIP at the start of UMS-03C-B. The amendment did not
modify any of these files.

```text
guardian/db/models.py (modified vs HEAD, full diff h):
  b7e4b14d0da85aa48622ed43ae0ba93fcfcce1eabd0667a2b755d3793eea8cf4

guardian/db/migrations/versions/f6b0d3e8c5a2_add_canonical_memory_persistence.py:
  95885d9dbfa1ba57e410f37db264094ba81fd00da9165f66eb3721e9feb70b2d

tests/migration/test_canonical_memory_persistence_migration.py:
  78185b5a4c6206e63bd64e967fd5bb43a80548399d1c0ae4d7f63fe8d941fcd4
```

HEAD reference: `6508920fa9243c18195618356907a46fe8d874e5`

## Alembic head before/after

```bash
.venv/bin/python -m alembic -c backend/alembic.ini heads
```

The committed Alembic head is `e5a9c2f7b4d1`. The
uncommitted `f6b0d3e8c5a2` migration file is part of the
UMS-03D WIP and is not committed truth. This amendment does
not change the committed Alembic head.

## ADR impact

- ADR-081 (Project ownership authority): unchanged. The new
  composite uniqueness is a relational prerequisite for
  the same-account FK that ADR-081 already authorizes.
- ADR-082 (Persona Profile manifest and binding authority):
  unchanged. No Persona-attribution decision is altered.
- ADR-083 (MemoryOS): not present in the canonical ADR
  registry; this amendment does not repair that gap.
- ADR-084 (Unified Account-Owned Memory Store): unchanged;
  remains controlling. The new constraint sits inside the
  contract that ADR-084 already accepts.

No new ADR was created. No existing ADR was modified.

## Files changed (4)

| Path | Kind |
|---|---|
| `docs/architecture/unified-memory-store-contract.md` | normative amendment: new §4.16.2b |
| `docs/Campaign/unified-memory-store/README.md` | state block + narrative paragraph |
| `docs/architecture/00-current-state.md` | state block + narrative paragraph |
| `docs/architecture/proofs/runtime/2026-09-07-ums03c-b-project-composite-ownership-target-proof.md` | new proof receipt |

The protected UMS-03D WIP was not modified. The original
UMS-03C, UMS-03A, UMS-03A-A, UMS-03B, and UMS-03A proof
receipts are preserved unmodified as historical evidence.

## Release and runtime impact

```text
UMS-03A: REVERIFIED
UMS-03A-A: CLOSED
UMS-03B MEMORY ENVELOPE PROTOCOL TOKENS: CLOSED
UMS-03C CANONICAL MEMORY PERSISTENCE SCHEMA: CLOSED
UMS-03C-A REVIEW/ACTIVATION ORDERING: CLOSED
UMS-03C-B PROJECT COMPOSITE OWNERSHIP TARGET: CLOSED
UMS-03D CANONICAL MEMORY PERSISTENCE: AUTHORIZED TO RESUME
UMS-03: OPEN
UMS-03E: NOT AUTHORIZED
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE

PROJECT RELATIONAL TARGET:
  projects.id remains PRIMARY KEY
  projects.user_id remains ownership authority
  UNIQUE (id, user_id) enables same-account composite FK
  constraint: uq_projects_id_user_id

UMS-03D MIGRATION TOPOLOGY:
  e5a9c2f7b4d1
      ↓
  f6b0d3e8c5a2
```

UMS-03C-B is documentation-only. No SQL was added, no ORM
model was changed, no Alembic migration was added, no
runtime writer / reader / retrieval / export behavior was
changed, and no new ADR was created. No runtime or release
capability changed. No Beta claim widened. The uncommitted
UMS-03D WIP is preserved by this amendment. The Alembic
committed head remains `e5a9c2f7b4d1`. The new
`uq_projects_id_user_id` constraint will be implemented by
UMS-03D as part of its single additive migration.
