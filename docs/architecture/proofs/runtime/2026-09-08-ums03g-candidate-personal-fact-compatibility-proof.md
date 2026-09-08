# UMS-03G — Candidate Personal-Fact Compatibility Projection Proof

- **Slice:** UMS-03G
- **Date:** 2026-09-08
- **Execution lane:** Architecture-Impact
- **Task kind:** runtime compatibility implementation (read-only)
- **Original UMS-03F prerequisite:** `37daa66be10593029ded65897f5e2c8d2308be84`
- **First accepted governance base:** `ba318cbb8761f6754bc940d1d2c0b537dd66c6c2` — `Reconcile unissued ADR-083 allocation`
- **Final accepted starting HEAD:** `a6b6a5e1b4dbe280a60ea39eb540de80000dda78` — `Record ADR-083 disposition`
- **Alembic head before / after:** `f6b0d3e8c5a2` / `f6b0d3e8c5a2` (unchanged)
- **Source family covered:** candidate / unreviewed `personal_facts` only
- **Local safety ref preserved:** `recovery/ums03e-conflated-71fd9f4d5`
  → `71fd9f4d5f4f2d05eb97c829a0097039c5fb0cae` (UMS-03E reconciliation
  artifact, untouched)

## Governance-base reconciliation provenance

UMS-03F closed at `37daa66be`. Before UMS-03G implementation began,
`main` advanced through two clean architecture-governance commits:

```text
37daa66be   UMS-03F: Add verified personal fact compatibility projection
    ↓
ba318cbb8   Reconcile unissued ADR-083 allocation
    ↓
a6b6a5e1b   Record ADR-083 disposition
```

Both intervening commits were inspected before any UMS-03G code change:

```text
$ git diff --name-only 37daa66be a6b6a5e1b
docs/architecture/adr/adr-index.md
docs/architecture/proofs/runtime/2026-09-07-adr-083-allocation-reconciliation-proof.md
docs/architecture/proofs/runtime/2026-09-08-adr-083-disposition-proof.md
```

No UMS contract, runtime, persistence, Personal Fact, protocol-token,
Campaign, or current-state file changed in the intervening delta.

`git merge-base --is-ancestor 37daa66be a6b6a5e1b` returned exit 0;
UMS-03F remains in ancestry.

The `ba318cbb8` allocation reconciliation and the `a6b6a5e1b` disposition
proof receipts both explicitly state:

```text
ADR-083: UNISSUED / RETIRED
ADR-083 ARCHITECTURE AUTHORITY: NONE
PERSONA STUDIO GOVERNING ADR: ADR-082
UNIFIED MEMORY GOVERNING ADR: ADR-084
```

ADR-084 remained the controlling Unified Memory Store architecture
throughout. The intervening commits are governance bookkeeping only;
no UMS semantics drifted.

The reconciliation did not require a rewind or rebase. Valid governance
history was preserved.

## Objective

Add the third read-only compatibility reader per the frozen
UMS-03A §4.13 matrix: project authoritative candidate / unreviewed
`personal_facts` rows into the canonical memory envelope without
writing the canonical tables, without changing authority, and
without conflating Personal Fact `is_active` (lifecycle authority)
with the candidate review posture (pending / unapproved).

## Frozen §4.13 mapping used

For `personal_facts` rows that are NOT verified + active, i.e. the
natural complement of the UMS-03F predicate:

```text
status IN ('candidate', 'disputed', 'archived')
OR
is_active = FALSE
```

| Field | Mapping |
| --- | --- |
| Envelope species | `candidate_unreviewed_fact` |
| Owner derivation | `user_id` |
| Project scope | absent (account scope) |
| Persona attribution | zero links |
| Provenance | `source_system='codexify'`, `source_record_id='personal_facts:<id>'`; primary `source_type` / `source_message_id` / `evidence_meta` / `modality` / `excerpt` from latest `personal_fact_evidence` |
| Activation / review posture | pending / unapproved (carried by the species); Personal Fact `is_active` is preserved on the source row as the lifecycle authority but does NOT upgrade the candidate's review posture |
| Ambient posture | excluded (`ambient_eligible = False`) |
| Lossless fields | `id, user_id, key, value, status, confidence, is_active, last_confirmed_at, guardrail_metadata, created_at, updated_at`; full evidence rows; revisions |
| Fields that cannot yet be represented | Project scope; Persona attribution; canonical `source_thread_id` for facts whose evidence lacks `source_message_id` |
| Fail-closed | evidence `source_type` outside the closed vocabulary; `evidence_meta` self-referential on the parent fact id |

The candidate species boundary INCLUDES `disputed` and `archived` per
§4.13 line 901 and §4.10 line 725 exactly:

```text
personal_facts row where
  status ∈ {candidate, disputed, archived}
  OR
  is_active = false
```

A verified + inactive row projects as `candidate_unreviewed_fact`
because the `is_active = false` half of the predicate is satisfied.
The review authority (verified) and the activation authority
(inactive) remain independent on the source row; the canonical
species reflects the activation reality, not the historical
review decision.

## Actual legacy schema verified

Same `PersonalFact` / `PersonalFactEvidence` / `PersonalFactRevision`
schemas as UMS-03F, unchanged since the UMS-03F slice. The closed
`status` vocabulary is `{candidate, verified, disputed, archived}`
(enforced by the `personal_facts_status_check` CHECK constraint).
The `is_active` column is `Boolean NOT NULL` defaulting to `true`.

## Implementation

- Extended: `guardian/core/memory_compatibility.py`
- New public reader: `read_candidate_personal_fact_projection(session, *, authenticated_account_id, personal_fact_id) -> MemoryCompatibilityProjection | None`
- New constants: `PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES`,
  `CANDIDATE_PERSONAL_FACT_PREDICATE`,
  `CANDIDATE_PERSONAL_FACT_STATUSES`
- Internal helper refactor: `_project_personal_fact` now takes
  `semantic_species` and `ambient_eligible` as keyword arguments
  with verified values as defaults. The verified reader
  (`read_verified_personal_fact_projection`) is unchanged: it
  still calls `_project_personal_fact(row, evidence, revisions)`
  and the defaults produce the UMS-03F output exactly. The
  candidate reader passes the candidate species and
  `ambient_eligible=False`. No semantic change to the UMS-03F
  adapter.

### Eligibility is enforced in the query

```python
session.query(PersonalFact)
    .filter(PersonalFact.id == personal_fact_id)
    .filter(PersonalFact.user_id == authenticated_account_id)
    .filter(
        or_(
            PersonalFact.status.in_(tuple(CANDIDATE_PERSONAL_FACT_STATUSES)),
            PersonalFact.is_active.is_(False),
        )
    )
    .one_or_none()
```

This is the exact complement of the UMS-03F predicate
(`status == VERIFIED AND is_active IS TRUE`). Together the two
readers cover every `personal_facts` row exactly:

- Verified + active → UMS-03F (returns `None` here)
- Anything else → UMS-03G (returns `None` in the verified reader)

### Canonical-identity posture

The projection type deliberately exposes no `memory_id` or
`canonical_memory_id` field. Legacy source identity is preserved on
`legacy_source_family` + `legacy_source_record_id` (frozen
`personal_facts:<id>` shape).

### Review / activation independence

`projection.semantic_species` carries the review posture
(`candidate_unreviewed_fact` = pending / unapproved). The
`ambient_eligible` field carries the canonical
ambient-influence posture. A test asserts explicitly that an
active candidate reports `ambient_eligible = False` —
`is_active = true` on the source row does NOT upgrade the
candidate to approved. The Personal Fact `is_active` column
remains the Personal Fact lifecycle authority on the source
row; the projection does not reinterpret it as approval.

### Evidence posture

Inherited from the UMS-03F pattern. Multiple evidence rows
remain distinct; primary (latest) evidence `source_type`,
`source_message_id`, `evidence_meta`, `modality`, and
`excerpt` are carried on the projection's provenance.
Unknown `source_type` and self-referential `evidence_meta`
fail closed with `MemoryCompatibilityReadError`.

### Revision posture

Inherited from the UMS-03F pattern. Historical revisions
remain lineage; the current authoritative fact row is never
replaced by an old revision. Revisions never carry
activation authority.

### Project + Persona posture

`projection.project_id` is always `None` and
`projection.persona_links` is always `[]` for candidate
`personal_facts` per the frozen "absent today → account
scope" / "absent today → zero links" mapping. No inference
from thread, current Project selection, related documents,
retrieval context, caller parameters, current Persona,
PersonaProfile, thread pin, display name, historical prompt
text, or Project.

## Write / mutation proof

### No canonical write

The test `test_candidate_fact_read_writes_nothing` listens on
`before_cursor_execute`, captures every SQL statement the
session executes during a read, and asserts that no
`INSERT` / `UPDATE` / `DELETE` / `TRUNCATE` / `MERGE` was
issued against `memory_records`, `memory_persona_links`,
`memory_provenance`, `personal_facts`,
`personal_fact_evidence`, or `personal_fact_revisions`. The
match uses a word-boundary regex so column names like
`updated_at` are NOT mistakenly matched as `UPDATE`.

### No legacy mutation

The test `test_candidate_fact_read_does_not_mutate_legacy_rows`
snapshots the source `personal_facts` row, the related
`personal_fact_evidence` row, and the related
`personal_fact_revisions` row before and after the
compatibility read. The fields are unchanged.

## Runtime-consumer surface

`rg MemoryCompatibilityProjection|read_memory_entry_projection|read_verified_personal_fact_projection|read_candidate_personal_fact_projection`
over `guardian tests docs` returned references only in:

- `guardian/core/memory_compatibility.py` (implementation)
- `tests/core/test_memory_compatibility.py` (focused tests)
- `docs/architecture/unified-memory-store-contract.md` (contract)
- `docs/Campaign/unified-memory-store/README.md` (campaign)
- `docs/architecture/00-current-state.md` (current state)
- `docs/architecture/proofs/runtime/2026-09-07-ums03e-memory-entry-compatibility-proof.md` (UMS-03E proof)
- `docs/architecture/proofs/runtime/2026-09-07-ums03f-verified-personal-fact-compatibility-proof.md` (UMS-03F proof)
- `docs/architecture/proofs/runtime/2026-09-08-ums03g-candidate-personal-fact-compatibility-proof.md` (this proof)

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
(`f6b0d3e8c5a2`).

## Test results

### Focused suite

```
tests/core/test_memory_compatibility.py  52 passed in 0.57s
```

Coverage:

UMS-03E (15 cases) — preserved from the prior slice.
UMS-03F (19 cases) — preserved from the prior slice.
UMS-03G (18 cases) — new this slice:

35. Owned candidate fact projects successfully (full
    field matrix).
36. Candidate + inactive fact projects.
37. Active candidate does NOT become approved.
38. Verified + active fact does NOT pass the candidate
    reader.
39. Verified + inactive fact projects as candidate (per
    §4.13 "OR is_active=false").
40. Disputed fact projects as candidate.
41. Archived fact projects as candidate.
42. Cross-account read returns `None`.
43. Missing fact returns `None`.
44. Empty `authenticated_account_id` fails closed.
45. No canonical-table write and no Personal Fact /
    evidence / revision mutation.
46. No legacy-row mutation on
    `personal_facts` / `personal_fact_evidence` /
    `personal_fact_revisions`.
47. No fabricated canonical `memory_id`.
48. Does not invent Project or Persona.
49. Multiple evidence rows remain distinct.
50. Unknown evidence `source_type` fails closed.
51. Candidate fact without evidence still projects.
52. Exact semantic species is `candidate_unreviewed_fact`.

### Adjacent regressions

```
tests/contracts/test_protocol_tokens.py  35 passed
tests/core/test_persona_subjects.py     11 passed
                                        46 passed in 0.42s
```

## ADR impact

Aligned with ADR-081, ADR-082, and ADR-084. No new ADR.

- ADR-081 — account / Project ownership: the reader derives
  ownership only from the legacy `user_id`; no Project
  authority is invented.
- ADR-082 — `PersonaProfile` authority boundary: the
  projection never references `PersonaProfile` and reports
  zero Persona links for candidate `personal_facts`.
- ADR-084 — canonical memory authority: legacy `personal_facts`
  remains the durable authority for the legacy record; the
  projection is a read-only normalized view. ADR-084 was
  unchanged by the two intervening governance commits.

## ADR-083

ADR-083 remains absent from the canonical registry as a
governing decision. The `a6b6a5e1b` disposition explicitly
retires the number; the `ba318cbb8` allocation
reconciliation explicitly affirms ADR-084 as the sole
controlling UMS memory ADR. UMS-03G does not create or
restore ADR-083.

## Confirmed non-claims

- No compatibility ORM table exists.
- No Alembic migration is added.
- No ORM models are modified.
- No retrieval / router / runtime consumer is modified.
- No candidate review action is taken.
- No verified / approved posture is emitted.
- No ambient influence is granted through the candidate
  reader.
- No Project or Persona authority is inferred.
- No canonical runtime writer is introduced.
- No export / restore behavior changes.
- No release / Beta claim changes.
- Nothing is pushed or merged.
- Local safety ref `recovery/ums03e-conflated-71fd9f4d5`
  remains untouched.
- The Pi fixture remains untouched and unstaged.
- The two ADR-083 governance commits remain in `main`
  history and were not reset or rewritten.

## Required successful state

```
UMS-03D CANONICAL MEMORY PERSISTENCE: CLOSED
UMS-03E MEMORY-ENTRY COMPATIBILITY PROJECTION: CLOSED
UMS-03F VERIFIED PERSONAL-FACT COMPATIBILITY: CLOSED
UMS-03G CANDIDATE PERSONAL-FACT COMPATIBILITY: CLOSED
UMS-03: OPEN
UMS-03H: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: INTERNAL COMPATIBILITY READ ONLY

GOVERNANCE BASE:
  37daa66be remains UMS-03F prerequisite
  ba318cbb8 reconciles ADR-083 allocation
  a6b6a5e1b records ADR-083 disposition
  ADR-084 remains controlling
  valid governance history preserved

PERSONAL FACT AUTHORITY:
  status remains review authority
  is_active remains lifecycle authority
  candidate remains pending/unapproved
  active candidate does not become approved
  candidate compatibility grants no ambient influence

CANONICAL AUTHORITY:
  legacy Personal Facts remains authoritative
  canonical memory tables remain non-authoritative

RETRIEVAL:
  no live compatibility-projection integration yet
```
