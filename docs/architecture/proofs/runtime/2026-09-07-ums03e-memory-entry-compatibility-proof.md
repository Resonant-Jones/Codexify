# UMS-03E — Memory-Entry Compatibility Projection Proof

- **Slice:** UMS-03E
- **Date:** 2026-09-07
- **Execution lane:** Architecture-Impact
- **Reconciliation:** UMS-03E-R — see "Reconciliation provenance" below
- **Final commit base:** `4c3d6c57e363d8fad568d20e8048caf41b7b417a` (UMS-03D)
- **Local safety ref for the abandoned conflated commit:**
  `recovery/ums03e-conflated-71fd9f4d5` → `71fd9f4d5f4f2d05eb97c829a0097039c5fb0cae`
- **PR #794 merge head that was aborted:**
  `bd5be33ef8762c81f6e0183388040e26a0919fa1` (unmerged; remains unmerged)

## Reconciliation provenance

UMS-03E execution was interrupted by an unrelated conflated local
commit and an unresolved PR merge.

The conflated local commit `71fd9f4d5` "Restore fake Pi package
fixture metadata" had been created on top of UMS-03D during the
UMS-03E authoring session. Its file set was:

```text
guardian/core/memory_compatibility.py          (UMS-03E implementation)
tests/core/test_memory_compatibility.py        (UMS-03E tests)
tests/pi/fixtures/fake_pi_package/package.json (unrelated WIP)
```

The commit message described only the Pi fixture, conflating two
independent intents. The Pi fixture was explicitly outside UMS-03E
scope.

In parallel, an unresolved merge of PR #794 "Restore current-state
release contract" (`bd5be33ef8762c81f6e0183388040e26a0919fa1`) had
been left in the worktree with `<<<<<<<` / `=======` / `>>>>>>>`
conflict markers in `docs/architecture/00-current-state.md`.

The reconciliation steps were:

```text
1. capture contaminated state (HEAD, MERGE_HEAD, status, log)
2. create external recovery bundle under /tmp
3. create local safety branch
   recovery/ums03e-conflated-71fd9f4d5
   at 71fd9f4d5
4. confirm no remote-tracking branch contains 71fd9f4d5
5. abort the in-progress merge (git merge --abort /
   cleared MERGE_HEAD)
6. rewind local main to 4c3d6c57e (git reset --mixed)
7. leave the Pi fixture dirty/unstaged again
8. reconstitute only the six UMS-03E paths
9. rebuild 00-current-state.md from the clean 4c3d6c57e
   base plus the UMS-03E state change and narrative
   (the conflicted reference was NOT copied wholesale)
10. revalidate focused tests, adjacent regressions,
    alembic topology, runtime-consumer surface
11. commit exactly the six UMS-03E paths with the
    honest subject
```

The final main lineage after reconciliation:

```text
4c3d6c57e  Add canonical memory persistence schema  (UMS-03D, base)
+<new>      Add legacy memory compatibility projection (UMS-03E)
```

The conflated `71fd9f4d5` commit is no longer in `main` history. It
remains recoverable through the local safety ref
`recovery/ums03e-conflated-71fd9f4d5` until the user chooses to
discard it. Nothing was pushed and PR #794 remains unmerged.

The Pi fixture is excluded from the UMS-03E commit. PR #794
release-contract changes are excluded. No unrelated WIP was staged.


- **Task kind:** runtime compatibility implementation (read-only)
- **Starting HEAD:** `4c3d6c57e363d8fad568d20e8048caf41b7b417a` (UMS-03D)
- **UMS-03D prerequisite SHA:** `4c3d6c57e363d8fad568d20e8048caf41b7b417a`
- **Alembic head before / after:** `f6b0d3e8c5a2` / `f6b0d3e8c5a2` (unchanged)
- **Source family covered:** legacy `memory_entries` only

## Objective

Implement the first read-only compatibility reader per the frozen
UMS-03A §4.13 matrix: project authoritative legacy `memory_entries`
rows into the canonical memory envelope without writing the canonical
tables, without changing authority, and without inferring Project
scope or Persona attribution.

## Frozen §4.13 mapping used

| Field | Mapping |
| --- | --- |
| Envelope species | `episodic_semantic_memory` |
| Owner derivation | `user_id` |
| Project scope | absent (account scope) |
| Persona attribution | zero links |
| Provenance | `source_system='codexify'`, `source_record_id='memory_entries:<id>'`; no `source_thread_id` / `source_message_id` |
| Activation / review posture | ambient-eligible by default |
| Lossless fields | `id`, `user_id`, `silo`, `content`, `tags`, `pinned`, `created_at`, `updated_at` |
| Fail-closed | malformed `silo`, missing `user_id`, `user_id` not resolvable, content not losslessly representable |

## Actual legacy schema verified

`guardian/db/models.py` `MemoryEntry` (lines 2291–2323):

- `id: BigInteger` PK autoincrement
- `user_id: String(255) NOT NULL` FK `users.id` ON DELETE CASCADE
- `silo: String(64) NOT NULL` CHECK in `(ephemeral, midterm, longterm)`
- `content: Text` nullable
- `tags: Text` nullable
- `pinned: Boolean` default false NOT NULL
- `created_at`, `updated_at`: TIMESTAMP(timezone=True) NOT NULL

No Project column. No Persona column. No `source_system` /
`source_record_id` / `source_thread_id` / `source_message_id`. The
actual schema agrees with the frozen mapping — no contract gap, no
implementation invention required.

## Implementation

- New module: `guardian/core/memory_compatibility.py`
- Public reader: `read_memory_entry_projection(session, *, authenticated_account_id, memory_entry_id) -> MemoryCompatibilityProjection | None`
- Projection type: `MemoryCompatibilityProjection` (frozen dataclass)
- Provenance type: `MemoryCompatibilityProvenance`
- Persona-link placeholder type: `MemoryCompatibilityPersonaLink` (always empty for `memory_entries`)
- Fail-closed signal: `MemoryCompatibilityReadError`
- Closed vocabulary constants: `MEMORY_ENTRY_ENVELOPE_SPECIES`, `MEMORY_ENTRY_LEGACY_SOURCE_FAMILY`, `MEMORY_ENTRY_LEGACY_SOURCE_SYSTEM`, `MEMORY_ENTRY_VALID_SILOS`

### Canonical-identity posture

The projection type deliberately does **not** expose a canonical durable
`memory_id`. Legacy source identity is preserved on
`legacy_source_family` + `legacy_source_record_id` (frozen
`memory_entries:<id>` shape). A test asserts the absence of
`memory_id` and `canonical_memory_id` fields on the projection
dataclass.

### Account authorization

Account authority is enforced by a single SQLAlchemy query that
filters on both `MemoryEntry.id == memory_entry_id` and
`MemoryEntry.user_id == authenticated_account_id`. Not-found and
not-owned return `None` (concealed per existing repository posture).
A separate `MemoryCompatibilityReadError` is reserved for source rows
that cannot be losslessly projected (per §4.14).

### Project-scope posture

`projection.project_id` is always `None` for `memory_entries` per the
frozen "absent today → account scope" mapping. No inference from
thread, current Project selection, related documents, retrieval
context, or caller parameters.

### Persona-attribution posture

`projection.persona_links` is always `[]` per the frozen "absent today
→ zero links" mapping. No inference from current Persona,
`PersonaProfile`, thread pin, display name, historical prompt text,
or Project.

### Governance posture

`projection.ambient_eligible` is the frozen default
`True` ("ambient-eligible by default; promotion to ambient must still
pass §3.5 gates"). The reader describes the record; it does not
perform routing policy.

### Provenance posture

`projection.provenance` is a typed opaque read projection carrying
`source_system='codexify'` and
`source_record_id='memory_entries:<id>'` exactly as the frozen
mapping prescribes. `source_thread_id` and `source_message_id` are
`None` because the legacy row has no such column. Provenance is
preserved; it does not confer ownership and is not a row in
`memory_provenance`.

## Write / mutation proof

### No canonical write

The test `test_compatibility_read_writes_no_canonical_rows` listens
on `before_cursor_execute`, captures every SQL statement the session
executes during a read, and asserts that no `INSERT` / `UPDATE` /
`DELETE` / `TRUNCATE` / `MERGE` was issued against
`memory_records`, `memory_persona_links`, or `memory_provenance`. The
canonical tables are PostgreSQL-typed (`JSONB`, `UUID`, etc.) and
cannot be materialized in SQLite, so the SQL-event layer is the
DB-agnostic way to prove the no-write contract.

### No legacy mutation

The test `test_compatibility_read_does_not_mutate_legacy_row`
snapshots the source `memory_entries` row before and after the
compatibility read. The fields `id`, `user_id`, `silo`, `content`,
`tags`, `pinned` are unchanged. `session.expire_all()` is called
between snapshots to bypass SQLAlchemy identity-map caching.

## Runtime-consumer surface

`rg MemoryCompatibilityProjection\|read_memory_entry_projection` over
`guardian tests docs` returned references only in:

- `guardian/core/memory_compatibility.py` (implementation)
- `tests/core/test_memory_compatibility.py` (focused tests)

No consumer in `guardian/context/`, `guardian/memoryos/`, or
`completion/runtime`. The reader is proven before being wired into
live retrieval, per the UMS-03E design.

## ORM metadata proof

`Base.metadata.tables` does not contain any compatibility-projection
table. The test `test_projection_type_is_not_registered_in_orm_metadata`
asserts the absence of `memory_compatibility_projection`,
`memory_compatibility_provenance`,
`memory_compatibility_persona_links`, and
`memory_entries_projection`.

## Migration proof

`git status --short` shows no new files under
`guardian/db/migrations/versions/`. Alembic head is unchanged
(`f6b0d3e8c5a2`). The compatibility reader is purely a runtime
projection, not a persistence change.

## Test results

### Focused suite

```
tests/core/test_memory_compatibility.py  15 passed in 0.46s
```

Coverage:

1. Owned legacy memory-entry projects successfully (full field matrix).
2. Cross-account read returns `None` (concealed like not-found).
3. Missing source returns `None` (not a fail-closed exception).
4. Empty `authenticated_account_id` raises
   `MemoryCompatibilityReadError` (fail-closed).
5. Projection does not invent Project scope.
6. Projection has zero Persona links.
7. Projection has no canonical `memory_id` field.
8. No canonical-table write (SQL-event proof).
9. No legacy-row mutation (before/after snapshot).
10. Projection type not registered in `Base.metadata`.
11–13. All three retention silos project successfully
    (`ephemeral`, `midterm`, `longterm`).
14. Null content projects as `None`.
15. Provenance carries source identity only; does not confer ownership.

### Adjacent regressions

```
tests/contracts/test_protocol_tokens.py  35 passed
tests/core/test_persona_subjects.py     11 passed
                                        46 passed in 0.43s
```

## ADR impact

Aligned with ADR-081, ADR-082, and ADR-084. No new ADR.

- ADR-081 — account / Project authority: the reader derives ownership
  only from the legacy `user_id`; no Project authority is invented.
- ADR-082 — `PersonaProfile` boundary: the projection never
  references `PersonaProfile` and reports zero Persona links for
  `memory_entries`.
- ADR-084 — canonical memory authority: legacy `memory_entries`
  remains the durable authority for the legacy record; the projection
  is a read-only normalized view.

## ADR-083

ADR-083 remains absent from the canonical registry and is not created
in this slice.

## Confirmed non-claims

- No compatibility ORM table exists.
- No Alembic migration is added.
- No ORM models are modified.
- No retrieval / router / runtime consumer is modified.
- No `personal_facts` or `personal_fact_evidence` projection exists
  (deferred to UMS-03F).
- No canonical runtime writer is introduced.
- No export / restore behavior changes.
- No release / Beta claim changes.
- Nothing is pushed or merged.

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
UMS-03: OPEN
UMS-03F: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: INTERNAL COMPATIBILITY READ ONLY

AUTHORITY:
  memory_entries remains durable authority
  compatibility projection is read-only
  canonical memory tables remain non-authoritative

RETRIEVAL:
  no live retrieval integration yet

GIT RECONCILIATION (UMS-03E-R):
  unrelated PR #794 merge aborted
  conflated 71fd9f4d5 removed from main
  conflated commit preserved at local recovery ref
  Pi fixture excluded from UMS-03E
  corrected UMS-03E commit contains exactly six owned paths
```
