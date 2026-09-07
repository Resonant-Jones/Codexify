# UMS-03F — Verified Personal-Fact Compatibility Projection Proof

- **Slice:** UMS-03F
- **Date:** 2026-09-07
- **Execution lane:** Architecture-Impact
- **Task kind:** runtime compatibility implementation (read-only)
- **Starting HEAD:** `a67b28deffee48b4fe1ad762ff2728781330ab5f` (UMS-03E)
- **UMS-03E prerequisite SHA:** `a67b28deffee48b4fe1ad762ff2728781330ab5f`
- **Alembic head before / after:** `f6b0d3e8c5a2` / `f6b0d3e8c5a2` (unchanged)
- **Source family covered:** verified + active `personal_facts` only
- **Local safety ref preserved:** `recovery/ums03e-conflated-71fd9f4d5`
  → `71fd9f4d5f4f2d05eb97c829a0097039c5fb0cae` (UMS-03E reconciliation
  artifact, untouched)

## Objective

Add the second read-only compatibility reader per the frozen
UMS-03A §4.13 matrix: project authoritative verified + active
`personal_facts` rows into the canonical memory envelope without
writing the canonical tables, without changing authority, and
without inferring Project scope, Persona attribution, evidence
metadata, or canonical durable `memory_id`.

## Frozen §4.13 mapping used

For `personal_facts` with `status='verified'` AND `is_active=true`:

| Field | Mapping |
| --- | --- |
| Envelope species | `verified_personal_fact` |
| Owner derivation | `user_id` |
| Project scope | absent (account scope) |
| Persona attribution | zero links |
| Provenance | `source_system='codexify'`, `source_record_id='personal_facts:<id>'`; primary `source_type` / `source_message_id` / `evidence_meta` / `modality` / `excerpt` from latest `personal_fact_evidence` |
| Activation / review posture | approved, active (no ambient upgrade) |
| Lossless fields | `id, user_id, key, value, status, confidence, is_active, last_confirmed_at, guardrail_metadata, created_at, updated_at`; full evidence rows; revisions |
| Fields that cannot yet be represented | Project scope; Persona attribution; canonical `source_thread_id` for facts whose evidence lacks `source_message_id` |
| Fail-closed | evidence `source_type` outside the closed vocabulary; `evidence_meta` self-referential on the parent fact id |

## Actual legacy schema verified

`guardian/db/models.py` `PersonalFact` (lines 2167–2219):

- `id: BigInteger` PK autoincrement
- `user_id: String(255)` NOT NULL (no DB-level FK; implicit application authority per §4.6)
- `key: String(255)` NOT NULL
- `value: Text` NOT NULL
- `status: String(32)` NOT NULL default `'candidate'`, CHECK
  IN `('candidate', 'verified', 'disputed', 'archived')`
- `confidence: Float` NOT NULL default `0.5`, CHECK `0.0..1.0`
- `is_active: Boolean` NOT NULL default `true`
- `last_confirmed_at: TIMESTAMP(timezone=True)` nullable
- `guardrail_metadata: JSONB` nullable
- `created_at`, `updated_at`: TIMESTAMP(timezone=True) NOT NULL
- Composite index `(user_id, status, is_active)` matches the
  eligibility filter pattern exactly

`PersonalFactEvidence` (lines 2222–2255):

- `id: BigInteger` PK
- `fact_id: BigInteger` FK to `personal_facts.id` ON DELETE CASCADE
- `source_message_id: BigInteger` FK to `chat_messages.id` ON DELETE SET NULL, nullable
- `excerpt: Text` nullable
- `modality: String(64)` NOT NULL default `'text'`
- `confidence: Float` NOT NULL default `0.5`
- `source_type: String(64)` NOT NULL — closed vocabulary per §4.6
  and §4.13: `chatgpt_import`, `runtime_extraction`, `user_stated`,
  `user_corrected`, `claude_import`
- `evidence_meta: JSONB` NOT NULL default `'{}'`
- `created_at: TIMESTAMP(timezone=True)` NOT NULL

`PersonalFactRevision` (lines 2258–2283):

- `id: BigInteger` PK
- `fact_id: BigInteger` FK to `personal_facts.id` ON DELETE CASCADE
- `actor: String(64)` NOT NULL
- `action: String(32)` NOT NULL
- `field_changed: String(64)` nullable
- `old_value: Text` nullable
- `new_value: Text` nullable
- `reason: Text` nullable
- `created_at: TIMESTAMP(timezone=True)` NOT NULL

Canonical `PersonalFactStatus` enum
(`guardian/protocol_tokens.py`):

```text
CANDIDATE  = 'candidate'
VERIFIED   = 'verified'
DISPUTED   = 'disputed'
ARCHIVED   = 'archived'
```

The frozen §4.13 eligibility predicate
`status='verified' AND is_active=true` is reachable from the
actual legacy schema with the actual canonical `PersonalFactStatus`
token. The candidate / disputed / archived / inactive distinctions
map to the actual schema tokens, not to a separate "denied / rejected
/ superseded" vocabulary; the spec's language reconciles to these
four tokens.

## Implementation

- Extended: `guardian/core/memory_compatibility.py`
- New public reader: `read_verified_personal_fact_projection(session, *, authenticated_account_id, personal_fact_id) -> MemoryCompatibilityProjection | None`
- New helper types: `MemoryCompatibilityEvidence`,
  `MemoryCompatibilityRevision`
- Extended `MemoryCompatibilityProvenance` with optional
  `source_type`, `evidence_meta`, `modality`, `excerpt` fields
- Extended `MemoryCompatibilityProjection` with optional
  `fact_key`, `fact_value`, `confidence`, `last_confirmed_at`,
  `guardrail_metadata`, `evidence`, `revisions` fields
- Closed vocabulary constants:
  `PERSONAL_FACT_EVIDENCE_SOURCE_TYPES`,
  `PERSONAL_FACT_VERIFIED_ENVELOPE_SPECIES`,
  `PERSONAL_FACT_LEGACY_SOURCE_FAMILY`,
  `PERSONAL_FACT_LEGACY_SOURCE_SYSTEM`,
  `VERIFIED_PERSONAL_FACT_PREDICATE`

### Eligibility is enforced in the query

The reader filters on all four conditions in a single SQLAlchemy
query:

```text
PersonalFact.id == personal_fact_id
AND
PersonalFact.user_id == authenticated_account_id
AND
PersonalFact.status == PersonalFactStatus.VERIFIED.value
AND
PersonalFact.is_active.is_(True)
```

Candidate / disputed / archived / inactive rows never enter the
projection path.

### Canonical-identity posture

The projection type deliberately exposes no `memory_id` or
`canonical_memory_id` field. Legacy source identity is preserved on
`legacy_source_family` + `legacy_source_record_id` (frozen
`personal_facts:<id>` shape). A test asserts the absence of
both fields on the projection dataclass.

### Evidence posture

Evidence rows are loaded via the ORM relationship and sorted by
`created_at` DESC. The first row is the "primary" (latest)
evidence whose `source_type`, `source_message_id`,
`evidence_meta`, `modality`, and `excerpt` are carried on the
projection's provenance. All evidence rows are preserved
distinct in the `evidence` list — no deduplication by provider
or `source_type`. An evidence row whose `source_type` is
outside the closed vocabulary fails closed with
`MemoryCompatibilityReadError`. The recursive
self-referential check walks every nested value in
`evidence_meta` and fails closed if a value equals
`int(fact_id)`; substring matches in unrelated fields (e.g.
`"msg-1"` vs fact_id `1`) are NOT flagged.

### Revision posture

Revisions are loaded via the ORM relationship and sorted by
`created_at` ASC. They are historical lineage only. The
current authoritative fact row is never replaced by an old
revision. Revisions never carry activation authority. The
reader does not mutate revision history.

### Project + Persona posture

`projection.project_id` is always `None` and
`projection.persona_links` is always `[]` for verified
`personal_facts` per the frozen "absent today → account
scope" / "absent today → zero links" mapping. No inference
from thread, current Project selection, related documents,
retrieval context, caller parameters, current Persona,
PersonaProfile, thread pin, display name, historical prompt
text, or Project.

### Governance posture

`projection.ambient_eligible` is `True` for verified +
active rows (the frozen §4.10 line 724 "yes" activation).
The reader describes the record; it does not perform
ambient-influence routing decisions.

## Write / mutation proof

### No canonical write

The test `test_verified_fact_read_writes_nothing` listens on
`before_cursor_execute`, captures every SQL statement the
session executes during a read, and asserts that no
`INSERT` / `UPDATE` / `DELETE` / `TRUNCATE` / `MERGE` was
issued against `memory_records`, `memory_persona_links`,
`memory_provenance`, `personal_facts`,
`personal_fact_evidence`, or `personal_fact_revisions`. The
match uses a word-boundary regex so column names like
`updated_at` are NOT mistakenly matched as `UPDATE`. The
canonical tables are PostgreSQL-typed (`JSONB`, `UUID`,
etc.) and cannot be materialized in SQLite, so the
SQL-event layer is the DB-agnostic way to prove the
no-write contract.

### No legacy mutation

The test `test_verified_fact_read_does_not_mutate_legacy_rows`
snapshots the source `personal_facts` row, the related
`personal_fact_evidence` row, and the related
`personal_fact_revisions` row before and after the
compatibility read. The fields are unchanged. `session.expire_all()`
is called between snapshots to bypass SQLAlchemy
identity-map caching.

## Runtime-consumer surface

`rg MemoryCompatibilityProjection|read_memory_entry_projection|read_verified_personal_fact_projection`
over `guardian tests docs` returned references only in:

- `guardian/core/memory_compatibility.py` (implementation)
- `tests/core/test_memory_compatibility.py` (focused tests)
- `docs/architecture/unified-memory-store-contract.md` (contract)
- `docs/Campaign/unified-memory-store/README.md` (campaign)
- `docs/architecture/proofs/runtime/2026-09-07-ums03e-memory-entry-compatibility-proof.md` (UMS-03E proof)
- `docs/architecture/proofs/runtime/2026-09-07-ums03f-verified-personal-fact-compatibility-proof.md` (this proof)

No consumer in `guardian/context/`, `guardian/memoryos/`, or
any runtime / completion / router / worker.

## ORM metadata proof

`Base.metadata.tables` does not contain any compatibility-
projection table. The existing UMS-03E assertion
`test_projection_type_is_not_registered_in_orm_metadata`
continues to pass.

## Migration proof

`git status --short` shows no new files under
`guardian/db/migrations/versions/`. Alembic head is unchanged
(`f6b0d3e8c5a2`). The compatibility reader is purely a
runtime projection, not a persistence change.

## Test results

### Focused suite

```
tests/core/test_memory_compatibility.py  34 passed in 0.56s
```

Coverage:

UMS-03E (15 cases) — preserved from the prior slice:

1. Owned legacy memory-entry projects successfully.
2. Cross-account read returns `None`.
3. Missing source returns `None`.
4. Empty `authenticated_account_id` raises
   `MemoryCompatibilityReadError`.
5. Projection does not invent Project scope.
6. Projection has zero Persona links.
7. Projection has no canonical `memory_id` field.
8. No canonical-table write.
9. No legacy-row mutation.
10. Projection type not registered in `Base.metadata`.
11–13. All three retention silos project successfully.
14. Null content projects as `None`.
15. Provenance carries source identity only; does not confer
    ownership.

UMS-03F (19 cases) — new this slice:

16. Verified + active fact projects successfully (full
    field matrix).
17. Cross-account read returns `None`.
18. Missing fact returns `None`.
19. Empty `authenticated_account_id` fails closed.
20. Candidate fact does not project.
21. Disputed fact does not project.
22. Archived fact does not project.
23. Inactive verified fact does not project.
24. Multiple evidence rows remain distinct; primary is the
    latest.
25. Revisions preserved as historical lineage.
26. Unknown evidence `source_type` fails closed.
27. Self-referential `evidence_meta` fails closed.
28. Verified fact without evidence still projects.
29. No canonical-table write and no personal-fact /
    evidence / revision mutation.
30. Verified + active fact with no evidence still projects.
31. No fabricated canonical `memory_id`.
32. Primary evidence `source_message_id` preserved.
33. Verified fact does not invent Project or Persona.
34. Exact semantic species is `verified_personal_fact`.

### Adjacent regressions

```
tests/contracts/test_protocol_tokens.py  35 passed
tests/core/test_persona_subjects.py     11 passed
                                        46 passed in 0.57s
```

## ADR impact

Aligned with ADR-081, ADR-082, and ADR-084. No new ADR.

- ADR-081 — account / Project ownership: the reader derives
  ownership only from the legacy `user_id`; no Project
  authority is invented.
- ADR-082 — `PersonaProfile` authority boundary: the
  projection never references `PersonaProfile` and reports
  zero Persona links for verified `personal_facts`.
- ADR-084 — canonical memory authority: legacy `personal_facts`
  remains the durable authority for the legacy record; the
  projection is a read-only normalized view.

## ADR-083

ADR-083 remains absent from the canonical registry and is not
created in this slice.

## Confirmed non-claims

- No compatibility ORM table exists.
- No Alembic migration is added.
- No ORM models are modified.
- No retrieval / router / runtime consumer is modified.
- No candidate / unreviewed fact compatibility exists
  (deferred to a later authorization).
- No canonical runtime writer is introduced.
- No export / restore behavior changes.
- No release / Beta claim changes.
- Nothing is pushed or merged.
- Local safety ref `recovery/ums03e-conflated-71fd9f4d5`
  remains untouched.

## Required successful state

```
UMS-03A: REVERIFIED
UMS-03A-A: CLOSED
UMS-03B: CLOSED
UMS-03C: CLOSED
UMS-03C-A: CLOSED
UMS-03C-B: CLOSED
UMS-03D CANONICAL MEMORY PERSISTENCE: CLOSED
UMS-03E MEMORY-ENTRY COMPATIBILITY PROJECTION: CLOSED
UMS-03F VERIFIED PERSONAL-FACT COMPATIBILITY: CLOSED
UMS-03: OPEN
UMS-03G: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: INTERNAL COMPATIBILITY READ ONLY

AUTHORITY:
  memory_entries remains legacy authority
  personal_facts remains legacy authority
  only verified/current personal facts project as verified_personal_fact
  canonical memory tables remain non-authoritative

RETRIEVAL:
  no live compatibility-projection integration yet
```
