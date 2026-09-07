# UMS-03C Canonical Memory Persistence Schema Proof

Date: 2026-09-07

Status: **PASSED — ARCHITECTURE-CONTRACT FREEZE**

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: architecture-contract
- Evidence posture: documentation/inventory based; no live
  runtime qualification; no SQL table created; no ORM model
  changed; no Alembic migration added
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-03C
- Starting HEAD: `3346086d838036207f0204d21892a181608fe039`
- UMS-03B prerequisite commit: `3346086d838036207f0204d21892a181608fe039`
- UMS-03: OPEN
- UMS-03D: AUTHORIZED TO START
- UMS-04: NOT AUTHORIZED

## Inspected persistence prerequisites

The contract freeze is grounded in the following inspected
persistence surfaces, all read-only:

- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/adr/081-project-ownership-authority.md`
- `docs/architecture/adr/082-persona-profile-manifest-and-binding-authority.md`
- `docs/architecture/adr/084-unified-account-owned-memory-store.md`
- `docs/architecture/unified-memory-store-contract.md` (this
  slice extends it with §4.16)
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/Campaign/unified-memory-store/README.md` (extended by
  this slice)
- `docs/architecture/proofs/runtime/2026-09-07-ums03a-canonical-memory-envelope-contract-proof.md`
- `docs/architecture/proofs/runtime/2026-09-07-ums03a-reverification-proof.md`
- `docs/architecture/proofs/runtime/2026-09-07-ums03a-a-memory-species-token-spelling-proof.md`
- `docs/architecture/proofs/runtime/2026-09-07-ums03b-memory-envelope-token-proof.md`
- `guardian/protocol_tokens.py` (`MemorySemanticSpecies`,
  `MemoryPersonaLinkKind`, `MEMORY_SEMANTIC_SPECIES_VALUES`,
  `MEMORY_PERSONA_LINK_KIND_VALUES`)
- `guardian/db/models.py` (the `User`, `Project`,
  `PersonaSubject`, `PersonaSubjectBinding`, `MemoryEntry`,
  `PersonalFact`, `PersonalFactEvidence`, and
  `PersonalFactRevision` ORM models)

### Relational-prerequisite summary

| Surface | Identifier convention | Account ownership | Delete behavior |
|---|---|---|---|
| `users.id` | `String(255)` PK | self | (deletable) |
| `projects.id` | `Integer` autoincrement PK | `user_id String(255)` FK CASCADE | CASCADE on user delete |
| `projects` composite | — | `(user_id, system_role)` partial unique | n/a |
| `persona_subjects.persona_subject_id` | `String(36)` PK | `user_id String(255)` FK CASCADE | CASCADE on user delete; `lifecycle` is `active`/`retired` (UMS-02B canonical) |
| `persona_subjects` composite | — | `(persona_subject_id, user_id)` UNIQUE | n/a |
| `persona_subject_bindings` composite FK | — | `[persona_subject_id, subject_user_id] → [persona_subjects.persona_subject_id, persona_subjects.user_id]` plus `CHECK source_account_id = subject_user_id` | RESTRICT on Persona subject; CASCADE on user |
| `persona_subject_bindings` partial unique | — | `(ref_kind, ref_id) WHERE valid_until IS NULL` | n/a |
| `memory_entries.id` | `BigInteger` autoincrement PK | `user_id String(255)` FK CASCADE | CASCADE on user delete |
| `memory_entries` CHECK | — | `silo IN ('ephemeral', 'midterm', 'longterm')` | n/a |
| `personal_facts.id` | `BigInteger` autoincrement PK | `user_id String(255)` NOT NULL (no DB-level FK; UMS-03B follow-up obligation) | application authority |
| `personal_facts` CHECK | — | `status IN ('candidate', 'verified', 'disputed', 'archived')` and `confidence BETWEEN 0.0 AND 1.0` | n/a |
| `personal_fact_evidence.source_message_id` | `BigInteger` FK `chat_messages.id` | — | `SET NULL` on chat-message delete (preserves the evidence row) |
| timestamp convention | — | `TIMESTAMP(timezone=True)` with `server_default=func.now()`, `onupdate=func.now()` | n/a |
| JSON convention | — | `JSONB` used only for auxiliary metadata (`guardrail_metadata`, `evidence_meta`); never for ownership, scope, identity, or activation | n/a |

The relational-prerequisite summary confirms the UMS-03C
preconditions:

- The canonical account FK target is `users.id` (a
  `String(255)`).
- The canonical Project authority is `projects.id` plus
  the composite `(user_id, system_role)` partial unique.
  A composite FK `(project_id, user_id) → projects(id,
  user_id)` is the standard DB-enforced same-account
  mechanism.
- The canonical stable identifier precedent is the
  `String(36)` UUID style used by
  `persona_subjects.persona_subject_id`. The same shape
  suits `memory_records.memory_id` and is portable for
  export / restore.
- The canonical same-account enforcement precedent is the
  composite FK on `persona_subject_bindings` plus the
  `CHECK source_account_id = subject_user_id`. The same
  pattern (composite FK + same-account CHECK) enforces the
  `memory_persona_links` same-account rule.
- The canonical token-derived CHECK precedent is
  `silo IN ('ephemeral', 'midterm', 'longterm')` on
  `memory_entries` and `status IN ('candidate', 'verified',
  'disputed', 'archived')` on `personal_facts`. The new
  `memory_records_semantic_species_check` and
  `memory_persona_links_link_kind_check` follow the same
  shape.
- The canonical timestamp / JSONB conventions are
  established and used by every relevant existing model.

## Canonical table plan (frozen by §4.16.1)

| Table | Purpose | Multiplicity |
|---|---|---|
| `memory_records` | canonical envelope row | one row per canonical memory atom |
| `memory_persona_links` | typed stable-Persona attribution relationships | zero or more rows per memory record |
| `memory_provenance` | first-class durable lineage | one or more rows per memory record |

The three names were verified to be unclaimed in
`guardian/db/models.py` at the start of UMS-03C. The
`memory_records` name is preferred by the UMS-03C spec and
is accepted here. No alternative name is admitted by this
contract.

## Envelope field contract (frozen by §4.16.2)

| Column | Type | Null | Default | Authority meaning |
|---|---|---|---|---|
| `memory_id` | `String(36)` UUID PK | NOT NULL | — | Stable canonical memory identity (export-stable, portable) |
| `user_id` | `String(255)` FK `users.id` | NOT NULL | — | Account ownership; CASCADE on user delete |
| `project_id` | `Integer` FK `projects.id` | NULL | NULL | Optional Project scope; ON DELETE RESTRICT |
| `semantic_species` | `String(32)` | NOT NULL | — | Closed `MemorySemanticSpecies` value |
| `text_content` | `Text` | NULL | NULL | Episodic-species free-text content |
| `fact_key` | `String(255)` | NULL | NULL | Personal-fact species identifier |
| `fact_value` | `Text` | NULL | NULL | Personal-fact species value |
| `fact_confidence` | `Float` (0.0–1.0) | NULL | NULL | Personal-fact species confidence |
| `reviewed_at` | `TIMESTAMPTZ` | NULL | NULL | Review event timestamp |
| `activated_at` | `TIMESTAMPTZ` | NULL | NULL | Activation event timestamp |
| `pinned` | `Boolean` | NOT NULL | `false` | Priority flag |
| `held` | `Boolean` | NOT NULL | `false` | Decay-suspension flag |
| `extensions` | `JSONB` | NULL | NULL | Auxiliary non-authority metadata |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now() + onupdate` | Row last-modified timestamp |

DB-enforced invariants:

- `UNIQUE (memory_id, user_id)` — binds memory identity to
  its account for composite FKs.
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE
  CASCADE`.
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON
  DELETE RESTRICT`.
- `FOREIGN KEY (project_id, user_id) REFERENCES
  projects(id, user_id)` — DB-enforced cross-account
  prevention when `project_id IS NOT NULL`.
- `CHECK (semantic_species IN ('episodic_semantic_memory',
  'verified_personal_fact', 'candidate_unreviewed_fact'))`
  — derived from `MemorySemanticSpecies`; named
  `memory_records_semantic_species_check`. Rejects all
  aliases.
- `CHECK (fact_confidence IS NULL OR (fact_confidence
  BETWEEN 0.0 AND 1.0))`.
- `CHECK ((project_id IS NULL) OR (text_content IS NOT
  NULL OR fact_key IS NOT NULL))`.
- `CHECK (semantic_species = 'episodic_semantic_memory'
  IMPLIES (text_content IS NOT NULL AND fact_key IS NULL
  AND fact_value IS NULL AND fact_confidence IS NULL))`.
- `CHECK (semantic_species IN ('verified_personal_fact',
  'candidate_unreviewed_fact') IMPLIES (fact_key IS NOT
  NULL AND fact_value IS NOT NULL AND text_content IS
  NULL))`.
- `CHECK (NOT (reviewed_at IS NULL AND activated_at IS
  NOT NULL))` — activation is strictly later than review.

## Identity representation

`memory_records.memory_id` is a server-generated
`String(36)` UUID. The choice is justified by:

- alignment with the existing `persona_subjects.persona_subject_id`
  precedent (same shape, same export-stable pattern);
- rejection of the autoincrement `BigInteger` pattern used
  by `memory_entries.id` and `personal_facts.id`, which
  is a poor fit for export / restore portability and which
  §4.1 expressly forbids silent remapping;
- stability of the foreign key from `memory_persona_links`
  and `memory_provenance` across instances.

## Project-account integrity

Project scope is nullable. When non-null, the composite FK
`FOREIGN KEY (project_id, user_id) REFERENCES projects(id,
user_id)` DB-enforces that the Project belongs to the same
account as the memory. Cross-account Project scope cannot be
silently permitted. `ON DELETE RESTRICT` ensures Project
deletion does not silently convert Project-scoped memory
into account-wide memory.

## Semantic-species enforcement

`memory_records.semantic_species` is `String(32) NOT NULL`
and constrained by
`memory_records_semantic_species_check` to the exact three
values from `MemorySemanticSpecies`:

- `episodic_semantic_memory`
- `verified_personal_fact`
- `candidate_unreviewed_fact`

No aliases are accepted. The CHECK rejects
`episodic_memory`, `semantic_memory`, `candidate_fact`, and
`unreviewed_fact` at the database layer.

## Payload strategy (frozen by §4.16.5)

- Authority-bearing data lives in typed relational columns.
- Species-specific non-authority content lives in typed
  columns on the canonical envelope (`text_content`,
  `fact_key`, `fact_value`, `fact_confidence`).
- The species-vs-payload-implication CHECK constraints
  ensure each species uses only its own payload columns.
- Auxiliary non-authority metadata lives in `extensions
  JSONB` and is explicitly forbidden from carrying any
  authority question's answer.

Rejected alternatives:

- Single `content JSONB` per row — rejected because it
  would force the three species to share one payload shape
  and erase the UMS-03A semantic distinction.
- Separate relational table per species — rejected because
  the three species share envelope doctrine and FK targets.

## Governance representation (frozen by §4.16.6)

The UMS-03A distinctions
`stored != reviewed != activated != explicitly retrievable
!= ambiently influential` are physically represented as:

- `stored` — row presence.
- `reviewed` — `reviewed_at TIMESTAMPTZ NULL`.
- `activated` — `activated_at TIMESTAMPTZ NULL`, with
  `NOT (reviewed_at IS NULL AND activated_at IS NOT NULL)`
  enforcing review-before-activation.
- `explicitly retrievable` — computed at read time per
  §3.5 and §6.1; not stored.
- `ambiently influential` — computed at read time per
  §3.5; not stored.

`pinned` and `held` are independent booleans that affect
priority and decay only; they do not change ownership,
scope, or Persona attribution. No monolithic lifecycle
enum is introduced.

## Persona-link schema (frozen by §4.16.3)

| Column | Type | Null | Default | Authority |
|---|---|---|---|---|
| `link_id` | `String(36)` UUID PK | NOT NULL | — | Stable link identity |
| `memory_id` | `String(36)` FK | NOT NULL | — | Memory record being annotated |
| `user_id` | `String(255)` FK `users.id` | NOT NULL | — | Memory's account; CASCADE on user delete |
| `persona_subject_id` | `String(36)` FK | NOT NULL | — | Stable Persona subject |
| `persona_user_id` | `String(255)` FK `users.id` | NOT NULL | — | Persona's account; covered by CASCADE |
| `link_kind` | `String(32)` | NOT NULL | — | Closed `MemoryPersonaLinkKind` value |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Link creation timestamp |

DB-enforced invariants:

- `FOREIGN KEY (memory_id, user_id) REFERENCES
  memory_records(memory_id, user_id) ON DELETE CASCADE`.
- `FOREIGN KEY (persona_subject_id, persona_user_id)
  REFERENCES persona_subjects(persona_subject_id, user_id)
  ON DELETE RESTRICT`.
- `CHECK (user_id = persona_user_id)` — same-account
  integrity between the memory and the attributed Persona
  subject.
- `CHECK (link_kind IN ('captured_under', 'suggested_by',
  'associated_with'))` — derived from
  `MemoryPersonaLinkKind`.
- `UNIQUE (memory_id, persona_subject_id, link_kind)` —
  per-(memory, persona, kind) dedup.

`persona_user_id` is a denormalized copy of
`persona_subjects.user_id`. It exists so the same-account
CHECK can be expressed at the relational boundary without a
sub-select. No `PersonaProfile` FK is present.

## Provenance schema (frozen by §4.16.4)

| Column | Type | Null | Default |
|---|---|---|---|
| `provenance_id` | `String(36)` UUID PK | NOT NULL | — |
| `memory_id` | `String(36)` FK | NOT NULL | — |
| `user_id` | `String(255)` FK `users.id` | NOT NULL | — |
| `source_system` | `String(32)` | NOT NULL | — |
| `source_record_id` | `String(255)` | NULL | NULL |
| `source_thread_id` | `BigInteger` FK `chat_threads.id` | NULL | NULL |
| `source_message_id` | `BigInteger` FK `chat_messages.id` | NULL | NULL |
| `source_import_job_id` | `String(36)` | NULL | NULL |
| `source_export_fingerprint` | `String(128)` | NULL | NULL |
| `source_subject_kind` | `String(32)` | NULL | NULL |
| `source_subject_id` | `String(255)` | NULL | NULL |
| `is_imported` | `Boolean` | NOT NULL | `false` |
| `extensions` | `JSONB` | NULL | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` |

DB-enforced invariants:

- `FOREIGN KEY (memory_id, user_id) REFERENCES
  memory_records(memory_id, user_id) ON DELETE CASCADE`.
- `CHECK (source_system IN ('codexify', 'openai',
  'anthropic', 'future_registered'))`.
- `CHECK (source_subject_kind IS NULL OR
  source_subject_kind IN ('chat', 'vault', 'importer',
  'classifier', 'future_registered'))`.
- `extensions JSONB` is non-authority; never the source of
  ownership, scope, activation, review, or Persona
  identity.

## Provenance multiplicity and uniqueness

Provenance is **one-to-many**. Multiple
`memory_provenance` rows per memory are allowed. There is
no `(memory_id, source_system)` UNIQUE constraint: collapsing
multiple lineage records by source would erase the evidence
the table exists to preserve. This mirrors the existing
`personal_fact_evidence` / `personal_fact_revisions`
append-only semantics for the unified envelope.

## Foreign-key delete behavior (frozen by §4.16.8)

| FK reference | On parent delete | Rationale |
|---|---|---|
| `memory_records.user_id → users.id` | CASCADE | aligns with `projects.user_id`, `persona_subjects.user_id` |
| `memory_records.project_id → projects.id` | RESTRICT | prevents Project deletion from silently converting Project-scoped memory into account-wide memory |
| `memory_persona_links.memory_id` (composite) | CASCADE | link follows its memory |
| `memory_persona_links.user_id → users.id` | CASCADE | account teardown removes the account's links |
| `memory_persona_links.persona_subject_id` (composite) | RESTRICT | Persona subject with active memory links cannot be deleted; retirement is governed by UMS-02 |
| `memory_provenance.memory_id` (composite) | CASCADE | provenance follows the memory |
| `memory_provenance.user_id → users.id` | CASCADE | account teardown removes provenance |
| `memory_provenance.source_thread_id → chat_threads.id` | RESTRICT | avoids silently losing source-thread identity |
| `memory_provenance.source_message_id → chat_messages.id` | SET NULL | allows chat-message deletion without losing the memory's existence |

## Index strategy (frozen by §4.16.9)

Minimum required indexes for the canonical envelope:

- `memory_records (user_id)`
- `memory_records (user_id, project_id)`
- `memory_records (user_id, semantic_species)`
- `memory_records (user_id, activated_at)`
- `memory_persona_links (user_id)`
- `memory_persona_links (persona_subject_id)`
- `memory_provenance (memory_id)`
- `memory_provenance (user_id, source_system)`
- `memory_provenance (source_thread_id)` (partial, when
  `source_thread_id IS NOT NULL`)

Excluded from canonical persistence: ranking, heat,
embedding, recency score, working-set membership, suggestion
ranking, and UI grouping.

## First-migration posture (frozen by §4.16.10)

The UMS-03D migration that introduces the canonical schema
must be:

- additive only;
- the three new tables created empty;
- no legacy backfill performed;
- no legacy source row mutated, deleted, or read;
- no runtime writer redirected to the canonical tables;
- no runtime reader redirected to the canonical tables;
- no compatibility reader implemented by this migration;
- no authority transfer.

Post-migration authority order remains:

```text
legacy source row         = durable authority
memory_records            = structurally available but not
                            yet runtime authority
```

Acceptance criteria for the future migration proof slice:

- `alembic upgrade head` succeeds on a clean disposable
  PostgreSQL 17 instance.
- `alembic upgrade head` succeeds on a disposable PostgreSQL
  17 instance seeded with the current live schema.
- Downgrade behavior is either lossless for the new tables
  (drop the tables) or explicitly forbidden with a
  documented reason.
- All canonical CHECK / UNIQUE / FK constraints are
  present.
- No legacy data was read, mutated, or migrated.

The runtime cutover that promotes canonical tables to
durable authority belongs to a later UMS-03 slice and is
explicitly not in UMS-03D.

## ORM/Alembic parity requirement

UMS-03D must introduce SQLAlchemy ORM metadata and the
Alembic migration together. No migration-only table may be
added without matching `Base` metadata. No ORM-only class
may exist without matching Alembic schema. The future
implementation must preserve the existing generic
PostgreSQL Alembic/ORM parity smoke.

## Compatibility reader relationship

A future compatibility reader will project legacy rows
into the canonical envelope shape without writing to
`memory_records`. The projection must be structurally
compatible with §4.16. The reader must not:

- write canonical rows;
- assign canonical durable authority;
- infer missing ownership, Project scope, or Persona
  attribution;
- upgrade review or activation state;
- destroy provenance;
- bypass the UMS-03A fail-closed rules.

The reader implementation is deferred to a later UMS-03
slice.

## ADR impact

- ADR-081 (Project ownership authority): unchanged. Honored
  by §4.16.2 (Project FK) and §4.16.7 (cross-account
  prevention).
- ADR-082 (Persona Profile manifest and binding authority):
  unchanged. Honored by §4.16.3 (no PersonaProfile FK in
  `memory_persona_links`).
- ADR-083 (MemoryOS): not present in the canonical ADR
  registry; this freeze does not repair that gap.
- ADR-084 (Unified Account-Owned Memory Store): unchanged;
  remains controlling. The schema implements the persistence
  contract that ADR-084 already accepts.

No new ADR was created. No existing ADR was modified.

## Release and runtime impact

```text
UMS-03A: REVERIFIED
UMS-03A-A: CLOSED
UMS-03B: CLOSED
UMS-03C CANONICAL MEMORY PERSISTENCE SCHEMA: CLOSED
UMS-03: OPEN
UMS-03D: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE
```

UMS-03C is documentation-only. No SQL table was created,
no ORM model was changed, no Alembic migration was added,
no runtime writer / reader / retrieval / export behavior
was changed, and no new ADR was created. No runtime or
release capability changed. No Beta claim widened. Legacy
memory / personal-fact stores remain the durable authority.
The Alembic head remains `e5a9c2f7b4d1` (verified before and
after the freeze).
