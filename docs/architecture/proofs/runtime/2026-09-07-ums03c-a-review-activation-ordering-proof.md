# UMS-03C-A Review/Activation Ordering Proof

Date: 2026-09-07

Status: **PASSED — DOCUMENTATION-ONLY CONTRACT AMENDMENT**

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: architecture-contract amendment
- Evidence posture: documentation-only; no SQL table, no ORM
  model, no Alembic migration, no runtime writer / reader /
  retrieval / export behavior, no new ADR
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-03C-A
- Starting HEAD: `417025ac8bc1ffa47c4f3ce6cd2f4170f139db69`
- UMS-03C prerequisite commit: `417025ac8bc1ffa47c4f3ce6cd2f4170f139db69`
- UMS-03D current state: was BLOCKED before implementation; is
  now AUTHORIZED TO RESUME
- UMS-03: OPEN
- UMS-03E: NOT AUTHORIZED
- UMS-04: NOT AUTHORIZED

## UMS-03D STOP reason (recorded from this session)

The UMS-03D implementation preflight (step 2a) found that
`docs/architecture/unified-memory-store-contract.md`
§4.16.2 contained two mutually inconsistent normative
claims about the review-before-activation ordering:

- the prose claimed "Activation is a strictly later event
  than review" (lines 1084–1086 and again at lines
  1273–1277 of the pre-amendment file);
- the frozen SQL CHECK was the weaker
  `NOT (reviewed_at IS NULL AND activated_at IS NOT NULL)`,
  which proves only that activation requires review but
  does **not** prove temporal ordering.

A row with `reviewed_at = '2026-01-15 10:00:00+00'` and
`activated_at = '2026-01-15 10:00:00+00'` (same instant)
would pass the frozen CHECK and violate the prose. A row
with `reviewed_at = '2026-01-15'` and `activated_at =
'2026-01-14'` (genuinely earlier activation) would be
rejected by the CHECK — that is the only thing the
weaker CHECK proves.

The UMS-03D spec explicitly forbade choosing one
interpretation in implementation; UMS-03D BLOCKED
before any code was written. No `MemoryRecord` ORM
class, no `f6b0d3e8c5a2` Alembic migration, no migration
test file, and no UMS-03D commit was created. The Alembic
head remained `e5a9c2f7b4d1` throughout.

The provenance preflight (step 2b) passed independently.
Source identity is preserved in the typed opaque
columns `source_record_id` (`String(255)`) and
`source_subject_id` (`String(255)`); the closed
`source_system` and `source_subject_kind` vocabularies
only classify the kind of source; `extensions JSONB` is
explicitly forbidden from carrying authority.

## Previous ordering prose

`docs/architecture/unified-memory-store-contract.md`
(pre-amendment):

- §4.16.2 field table, lines 1084–1086:

  > `CHECK (NOT (reviewed_at IS NULL AND activated_at IS
  > NOT NULL))` — a row may not be activated before it is
  > reviewed. Activation is a strictly later event than
  > review.

- §4.16.6 governance representation, lines 1273–1277:

  > `activated` — represented by `activated_at TIMESTAMPTZ
  > NULL`. `NULL` means not activated; non-NULL is the
  > activation timestamp. The CHECK constraint
  > `NOT (reviewed_at IS NULL AND activated_at IS NOT NULL)`
  > enforces that activation is strictly later than review.

## Previous CHECK

```sql
CHECK (
    NOT (
        reviewed_at IS NULL
        AND activated_at IS NOT NULL
    )
)
```

## Exact contradiction

The previous CHECK admits the following rows that the
previous prose rejects:

```text
reviewed_at  = T
activated_at = T
```

(same instant — prose says "strictly later," CHECK says
nothing about the value of `activated_at` once
`reviewed_at` is non-null).

The previous CHECK also admits the following row that the
previous prose does not explicitly reject but that
contradicts the prose's intent of forbidding
earlier-than-review activation:

```text
reviewed_at  = T2
activated_at = T1        where T1 < T2
```

(earlier activation — the CHECK does not compare the two
timestamps).

The preflight's two-claim test (one meaning at a time)
correctly returned BLOCKED. The implementation was halted
before any code edit.

## Canonical ordering rule (frozen by UMS-03C-A)

```text
Review and activation are distinct governance states.

An activated memory must be reviewed.

Activation may be recorded at the same instant as review,
including when both governance transitions are applied
atomically by a single user-authoritative action.

Activation must never be recorded before review.
```

The canonical relational predicate is the SQL
semantic-equivalent of:

```sql
CHECK (
    activated_at IS NULL
    OR (
        reviewed_at IS NOT NULL
        AND activated_at >= reviewed_at
    )
)
```

The constraint name in the resulting PostgreSQL schema is
`memory_records_review_activation_order_check`.

## Canonical CHECK

```sql
CHECK (
    activated_at IS NULL
    OR (
        reviewed_at IS NOT NULL
        AND activated_at >= reviewed_at
    )
)
```

This CHECK replaces the previous weaker
`NOT (reviewed_at IS NULL AND activated_at IS NOT NULL)`.
The phrase "strictly later" is no longer normative in §4.16.

## Valid boundary cases (this is the direct UMS-03D
migration-test contract)

```text
reviewed_at  = NULL
activated_at = NULL

reviewed_at  = T
activated_at = NULL

reviewed_at  = T
activated_at = T          (same instant)

reviewed_at  = T1
activated_at = T2         where T2 > T1
```

## Invalid boundary cases

```text
reviewed_at  = NULL
activated_at = T          (activated without review)

reviewed_at  = T2
activated_at = T1         where T1 < T2   (activated before review)
```

## Equal-timestamp posture

The governance states are logically distinct but need not
occupy different wall-clock instants. Atomic
review-and-activate operations may persist one timestamp
for both transitions. Artificial timestamp offsets
(for example, an artificial `+1 microsecond` separation)
are forbidden as a way to satisfy the schema. Timestamp
equality does not collapse the two governance states into
one state.

## Earlier-activation posture

Activation earlier than review is forbidden at the
relational boundary by the new CHECK. The database
rejects any row where `activated_at < reviewed_at` and
any row where `activated_at IS NOT NULL AND reviewed_at
IS NULL`.

## Governance-state independence preserved

The UMS-03A distinction
`stored != reviewed != activated != explicitly retrievable
!= ambiently influential` remains authoritative and
unchanged. The new CHECK enforces the activation-vs-review
boundary; the other four boundaries are computed at read
time per §3.5 and §6.1. Activation alone (even when
correctly ordered) does not confer ambient influence.

## Preservation of the other UMS-03C decisions

UMS-03C-A changed only the review/activation ordering
contract. All other UMS-03C decisions remain unchanged:

- table names (`memory_records`, `memory_persona_links`,
  `memory_provenance`);
- canonical memory identity representation
  (`String(36)` UUID);
- account ownership representation
  (`String(255)` FK CASCADE);
- optional Project scope representation
  (nullable `Integer` FK RESTRICT plus composite FK
  `(project_id, user_id) → projects(id, user_id)`);
- semantic-species constraints
  (`memory_records_semantic_species_check` accepting
  exactly the three `MemorySemanticSpecies` values and
  rejecting all four spec-forbidden aliases);
- payload strategy (typed species-appropriate columns;
  `extensions JSONB` non-authority);
- Persona-link schema
  (`memory_persona_links_link_kind_check` accepting
  exactly the three `MemoryPersonaLinkKind` values, plus
  composite FKs and same-account CHECK);
- provenance schema (one-to-many, opaque
  `source_record_id` / `source_subject_id` columns,
  closed `source_system` / `source_subject_kind`
  vocabularies);
- FK delete behavior (RESTRICT on Project, RESTRICT on
  Persona subject, CASCADE on user, SET NULL on chat
  message);
- index strategy;
- first-migration posture (additive only, empty
  canonical tables, no legacy backfill, no source-row
  mutation, no runtime cutover);
- ORM/Alembic parity requirement;
- compatibility-reader posture.

## Provenance preflight still satisfied

The UMS-03D step 2b provenance preflight that passed
before the amendment is unaffected. Actual source
identity is preserved in typed `source_record_id`
(`String(255)`), `source_subject_id` (`String(255)`),
`source_import_job_id` (`String(36)`), and
`source_export_fingerprint` (`String(128)`) columns.
Closed `source_system` and `source_subject_kind`
vocabularies only classify the kind of source.
`extensions JSONB` remains explicitly forbidden from
carrying authority.

## Required proof statements

```text
PREVIOUS CONTRACT:
  prose: activation strictly later than review
  predicate: activation requires reviewed_at non-null

CONTRADICTION:
  predicate allowed activated_at <= reviewed_at

CANONICAL CONTRACT:
  activated_at IS NULL
  OR (
      reviewed_at IS NOT NULL
      AND activated_at >= reviewed_at
  )

EQUAL TIMESTAMPS:
  ALLOWED

ACTIVATION BEFORE REVIEW:
  FORBIDDEN

SEMANTIC GOVERNANCE STATES:
  remain distinct

OTHER UMS-03C SCHEMA CHANGES:
  NONE

RUNTIME IMPLEMENTATION:
  NONE
```

## Alembic head before/after

```bash
.venv/bin/python -m alembic -c backend/alembic.ini heads
e5a9c2f7b4d1 (head)
```

Verified before and after the amendment. The Alembic head
is unchanged. No migration was added.

## ADR impact

- ADR-081 (Project ownership authority): unchanged.
- ADR-082 (Persona Profile manifest and binding authority):
  unchanged.
- ADR-083 (MemoryOS): not present in the canonical ADR
  registry; recorded as known truth, not repaired.
- ADR-084 (Unified Account-Owned Memory Store): unchanged;
  remains controlling. The amendment implements a
  sub-decision of the doctrine ADR-084 already accepts.

No new ADR was created. No existing ADR was modified.

## Files changed

| Path | Kind |
|---|---|
| `docs/architecture/unified-memory-store-contract.md` | normative amendment: §4.16.2 CHECK + new §4.16.2a; §4.16.6 governance paragraph |
| `docs/Campaign/unified-memory-store/README.md` | state block + narrative paragraph |
| `docs/architecture/00-current-state.md` | state block + narrative paragraph |
| `docs/architecture/proofs/runtime/2026-09-07-ums03c-a-review-activation-ordering-proof.md` | new proof receipt |

The original UMS-03C proof receipt
(`docs/architecture/proofs/runtime/2026-09-07-ums03c-canonical-memory-persistence-schema-proof.md`)
is preserved unmodified as historical evidence of the
contract that triggered the UMS-03D preflight stop.

## Release and runtime impact

```text
UMS-03A: REVERIFIED
UMS-03A-A: CLOSED
UMS-03B MEMORY ENVELOPE PROTOCOL TOKENS: CLOSED
UMS-03C CANONICAL MEMORY PERSISTENCE SCHEMA: CLOSED
UMS-03C-A REVIEW/ACTIVATION ORDERING: CLOSED
UMS-03D CANONICAL MEMORY PERSISTENCE: AUTHORIZED TO RESUME
UMS-03: OPEN
UMS-03E: NOT AUTHORIZED
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE

REVIEW / ACTIVATION ORDER:
  activation requires review
  activated_at >= reviewed_at
  equal timestamps are valid
  activation before review is forbidden
```

UMS-03C-A is documentation-only. No SQL table, no ORM
model, no Alembic migration, no runtime writer or reader,
no retrieval behavior, and no export implementation
changed. No runtime or release capability changed. No
Beta claim widened. No canonical memory persistence
implementation exists yet. The Alembic head remains
`e5a9c2f7b4d1`.
