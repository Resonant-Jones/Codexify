# UMS-03D Canonical Memory Persistence Proof

Date: 2026-09-07

Status: **PASSED — POSTGRESQL-QUALIFIED STRUCTURAL PERSISTENCE**

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: implementation + persistence qualification
- Evidence posture: SQLAlchemy ORM metadata + Alembic migration +
  disposable PostgreSQL 17 qualification; no live runtime consumer
  introduced; no compatibility reader; no authority cutover
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-03D (resumed after UMS-03C-B)
- Starting committed HEAD: `5fd992f427d80ee2576d7f21255762dc00412eb3` (UMS-03C-B)
- UMS-03C prerequisite commit: `417025ac8bc1ffa47c4f3ce6cd2f4170f139db69`
- UMS-03C-A prerequisite commit: `6508920fa9243c18195618356907a46fe8d874e5`
- UMS-03C-B prerequisite commit: `5fd992f427d80ee2576d7f21255762dc00412eb3`
- Previous committed Alembic head: `e5a9c2f7b4d1`
- New revision: `f6b0d3e8c5a2`
- Migration predecessor: `e5a9c2f7b4d1`
- Final single Alembic head: `f6b0d3e8c5a2`
- UMS-03: OPEN
- UMS-03E: AUTHORIZED TO START
- UMS-04: NOT AUTHORIZED

## Protected UMS-03D WIP fingerprints (verified before resumption)

```text
guardian/db/models.py (modified vs UMS-03C-B HEAD):
  b7e4b14d0da85aa48622ed43ae0ba93fcfcce1eabd0667a2b755d3793eea8cf4

guardian/db/migrations/versions/f6b0d3e8c5a2_add_canonical_memory_persistence.py:
  95885d9dbfa1ba57e410f37db264094ba81fd00da9165f66eb3721e9feb70b2d

tests/migration/test_canonical_memory_persistence_migration.py:
  78185b5a4c6206e63bd64e967fd5bb43a80548399d1c0ae4d7f63fe8d941fcd4
```

The WIP was preserved across the UMS-03D and UMS-03C-B
sessions. UMS-03C-B was a documentation-only amendment that
closed the relational prerequisite. UMS-03D added exactly the
required `uq_projects_id_user_id` precondition to the existing
`Project` ORM model and to the migration upgrade at the top of
the upgrade body.

## ORM classes added

```text
MemoryRecord          → memory_records
MemoryPersonaLink     → memory_persona_links
MemoryProvenance      → memory_provenance
```

All three classes use canonical `String(36)` UUID primary
keys, canonical `String(255)` FK to `users.id`, and CHECK
constraints that derive from the canonical
`MemorySemanticSpecies` and `MemoryPersonaLinkKind` token
registries. The `Project` model gained the UMS-03C-B
`UniqueConstraint("id", "user_id",
name="uq_projects_id_user_id")` on its existing
`__table_args__` block. No existing Project constraint or
index was removed or altered.

## Migration scope

The one Alembic revision `f6b0d3e8c5a2` is additive. Its
upgrade body performs:

```text
1. add uq_projects_id_user_id
2. create memory_records
3. create memory_persona_links
4. create memory_provenance
5. create their frozen indexes / constraints
```

The downgrade removes the canonical memory schema first and
only then drops `uq_projects_id_user_id`, preserving the
foreign-key target during the gap.

## Migration-local string snapshots

The migration contains immutable revision-local string
snapshots for the four closed vocabularies:

- `MemorySemanticSpecies` (`episodic_semantic_memory`,
  `verified_personal_fact`, `candidate_unreviewed_fact`)
- `MemoryPersonaLinkKind` (`captured_under`, `suggested_by`,
  `associated_with`)
- `memory_provenance.source_system` (`codexify`, `openai`,
  `anthropic`, `future_registered`)
- `memory_provenance.source_subject_kind` (`chat`, `vault`,
  `importer`, `classifier`, `future_registered`)

No import from `guardian.protocol_tokens` is present in the
migration. Historical replay remains deterministic regardless
of future application-token mutations.

## PostgreSQL translation of `IMPLIES`

The migration translates the prose-level `IMPLIES` connective
from the UMS-03C contract into the standard PostgreSQL
`NOT (antecedent) OR consequent` form. The `IMPLIES` operator
does not exist in PostgreSQL. The translation is logically
equivalent and is verified by the focused migration suite.

## PostgreSQL version

```text
PostgreSQL 17.6 (Homebrew) on aarch64-apple-darwin25.0.0
```

## Alembic topology before and after UMS-03D

```text
Before: e5a9c2f7b4d1 (head)
After:  f6b0d3e8c5a2 (head)

History tail:
  d4e8f1a2b6c9
      ↓
  e5a9c2f7b4d1
      ↓
  f6b0d3e8c5a2
```

Exactly one head. No separate Project prerequisite revision
exists.

## Test results

```text
Focused migration suite (tests/migration/test_canonical_memory_persistence_migration.py):
  17 passed, 0 failed, 0 errors, 0 skipped in 26.94s

Generic ORM/Alembic parity (tests/test_migrations.py):
  1 passed, 0 failed, 0 errors, 0 skipped in 5.99s

Adjacent regressions:
  tests/contracts/test_protocol_tokens.py
  tests/core/test_persona_subjects.py
  46 passed, 0 failed, 0 errors in 0.45s
```

## Fresh replay

```bash
DATABASE_URL=postgresql://resonant_jones@localhost:5432/<fresh> \
  .venv/bin/python -m alembic -c backend/alembic.ini upgrade head
```

Result: success. Current head: `f6b0d3e8c5a2 (head)`.

## Repeat upgrade

Second invocation of `alembic upgrade head` against the same
fresh database: success, no duplicate table/index/constraint
error, current head remains `f6b0d3e8c5a2`.

## Actual PostgreSQL schema inspection

`\d memory_records` confirms the live FKs include the composite
`fk_memory_records_project_account FOREIGN KEY (project_id,
user_id) REFERENCES projects(id, user_id) ON DELETE RESTRICT`.
The fact that PostgreSQL accepted this composite FK is the
direct proof that the `uq_projects_id_user_id` target exists
on `projects(id, user_id)`. If the UNIQUE constraint were
missing, PostgreSQL would have refused the FK creation.

Other confirmed FKs:

- `memory_records.user_id → users.id` (CASCADE)
- `memory_records.project_id → projects.id` (RESTRICT)
- `memory_records.(project_id, user_id) → projects(id, user_id)`
  (RESTRICT) — the §4.16.2 composite, enabled by UMS-03C-B
- `memory_persona_links.(memory_id, user_id) →
  memory_records(memory_id, user_id)` (CASCADE)
- `memory_persona_links.(persona_subject_id, persona_user_id) →
  persona_subjects(persona_subject_id, user_id)` (RESTRICT)
- `memory_provenance.source_thread_id → chat_threads.id`
  (RESTRICT)
- `memory_provenance.source_message_id → chat_messages.id`
  (SET NULL)
- `memory_provenance.(memory_id, user_id) →
  memory_records(memory_id, user_id)` (CASCADE)

## Qualification evidence required by §4.16

- ✅ `uq_projects_id_user_id` exists after the upgrade (proven
  by `pg_constraint` query and by the acceptance of the
  composite FK)
- ✅ `memory_records (project_id, user_id) →
  projects (id, user_id)` is accepted by PostgreSQL and live
- ✅ Account-A memory + Account-A Project: accepted
- ✅ Account-A memory + Account-B Project: rejected at the
  composite FK (IntegrityError)
- ✅ Project rows before upgrade byte-equal Project rows after
  upgrade (no Project data mutation)
- ✅ Legacy `memory_entries`, `personal_facts`,
  `personal_fact_evidence`, `personal_fact_revisions` rows
  before upgrade byte-equal same after upgrade (no legacy
  backfill, no legacy row mutation)
- ✅ Canonical tables are empty after upgrading a
  legacy-bearing database
- ✅ Downgrade round trip (upgrade → downgrade) preserves all
  legacy memory rows
- ✅ Downgrade round trip drops the three canonical tables
- ✅ Semantic species: only the three frozen values are
  accepted; aliases (`episodic_memory`, `semantic_memory`,
  `candidate_fact`, `unreviewed_fact`, `unknown`, uppercase)
  are rejected
- ✅ Payload implication CHECKs:
  `episodic_semantic_memory` requires `text_content`,
  forbids `fact_*`; personal-fact species require
  `fact_key`/`fact_value`, forbid `text_content`
- ✅ Review/activation six boundary cases:
  - `(None, None)` valid
  - `(T, None)` valid
  - `(T, T)` valid (equal timestamps, per UMS-03C-A)
  - `(T1, T2 where T2 > T1)` valid
  - `(None, T)` invalid
  - `(T2, T1 where T1 < T2)` invalid
- ✅ Persona same-account rejected when memory and Persona
  subject belong to different accounts
- ✅ Persona link kind: only the three frozen values
  (`captured_under`, `suggested_by`, `associated_with`) are
  accepted
- ✅ Persona link duplicate `(memory_id, persona_subject_id,
  link_kind)` rejected
- ✅ Provenance multiplicity: three distinct provenance rows
  for one memory accepted
- ✅ Typed provenance source identity: `source_record_id`,
  `source_import_job_id`, `source_export_fingerprint`,
  `source_subject_id` all preserved in typed columns
- ✅ Provenance FK rejection: nonexistent or wrong-account
  memory rejected
- ✅ Index strategy: all §4.16 minimum indexes present
- ✅ No derived heat/ranking/vector/working-set state in
  canonical tables
- ✅ Migration is additive; no Project row backfill; no
  Project row mutation; no legacy memory backfill; no legacy
  memory row mutation; no runtime reader cutover; no runtime
  writer cutover

## Disposable PostgreSQL teardown

All disposable PostgreSQL databases created for qualification
were destroyed at the end of the run. No DSNs, credentials,
container IDs, or temporary database names were committed to
the repository.

## Runtime-consumer inspection

```bash
rg -n "MemorySemanticSpecies|MemoryPersonaLinkKind|MemoryRecord|MemoryPersonaLink|MemoryProvenance|memory_records|memory_persona_links|memory_provenance"
```

Authorized references are limited to:

- `guardian/db/models.py` (implementation)
- `guardian/db/migrations/versions/f6b0d3e8c5a2_add_canonical_memory_persistence.py`
  (implementation)
- `tests/migration/test_canonical_memory_persistence_migration.py`
  (test)
- `docs/architecture/unified-memory-store-contract.md` (normative
  contract)
- `docs/architecture/proofs/runtime/2026-09-07-ums03a-canonical-memory-envelope-contract-proof.md`
  (historical evidence)
- `docs/architecture/proofs/runtime/2026-09-07-ums03a-reverification-proof.md`
  (historical evidence)
- `docs/architecture/proofs/runtime/2026-09-07-ums03a-a-memory-species-token-spelling-proof.md`
  (historical evidence)
- `docs/architecture/proofs/runtime/2026-09-07-ums03b-memory-envelope-token-proof.md`
  (historical evidence)
- `docs/architecture/proofs/runtime/2026-09-07-ums03c-canonical-memory-persistence-schema-proof.md`
  (historical evidence)
- `docs/architecture/proofs/runtime/2026-09-07-ums03c-a-review-activation-ordering-proof.md`
  (historical evidence)
- `docs/architecture/proofs/runtime/2026-09-07-ums03c-b-project-composite-ownership-target-proof.md`
  (historical evidence)
- `docs/architecture/proofs/runtime/2026-09-07-ums03d-canonical-memory-persistence-proof.md` (this file)
- `docs/Campaign/unified-memory-store/README.md` (campaign state)
- `docs/architecture/00-current-state.md` (current state)

No new runtime consumer was introduced. No changes were made
under `guardian/context/`, `guardian/memoryos/`, completion,
runtime paths, personal-fact services, candidate-fact
services, routers, workers, account export, or frontend.

## ADR impact

- ADR-081 (Project ownership authority): unchanged. The new
  `UNIQUE(id, user_id)` constraint is a relational prerequisite
  for the same-account FK that ADR-081 already authorizes.
- ADR-082 (Persona Profile manifest and binding authority):
  unchanged.
- ADR-083 (MemoryOS): not present in the canonical ADR registry;
  recorded as known truth, not repaired.
- ADR-084 (Unified Account-Owned Memory Store): unchanged;
  remains controlling. The implementation sits inside the
  contract that ADR-084 already accepts.

No new ADR was created. No existing ADR was modified.

## Release and runtime impact

```text
UMS-03A: REVERIFIED
UMS-03A-A: CLOSED
UMS-03B MEMORY ENVELOPE PROTOCOL TOKENS: CLOSED
UMS-03C CANONICAL MEMORY PERSISTENCE SCHEMA: CLOSED
UMS-03C-A REVIEW/ACTIVATION ORDERING: CLOSED
UMS-03C-B PROJECT COMPOSITE OWNERSHIP TARGET: CLOSED
UMS-03D CANONICAL MEMORY PERSISTENCE: CLOSED
UMS-03: OPEN
UMS-03E: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: INTERNAL PERSISTENCE ONLY

PROJECT RELATIONAL TARGET:
  uq_projects_id_user_id
  UNIQUE (id, user_id)

CANONICAL TABLES:
  memory_records
  memory_persona_links
  memory_provenance

RUNTIME AUTHORITY:
  legacy sources remain authoritative
  canonical tables are not yet read/write authority
```

UMS-03D introduced SQLAlchemy ORM metadata, one additive
Alembic migration, focused migration tests, and a UMS-03C-B
prerequisite. It did not establish runtime memory authority.
No runtime memory reader, writer, retrieval path, or export
implementation was changed. No Beta claim widened. Legacy
memory sources remain the durable authority for existing
records; the canonical tables are structurally proven and
await the later UMS-03 slice that will establish runtime
authority cutover.
