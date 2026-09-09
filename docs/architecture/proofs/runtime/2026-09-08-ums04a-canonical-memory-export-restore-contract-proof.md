# UMS-04A — Canonical Memory Export / Restore Contract Proof

- **Slice:** UMS-04A (architecture contract freeze)
- **Date:** 2026-09-08
- **Execution lane:** Architecture-Impact
- **Task kind:** architecture-contract freeze (docs only)
- **Starting HEAD:** `e21887fb4f7de0d40d7fb5ea2b8af6aa245a4f3a` (UMS-03I / UMS-03 closure)
- **UMS-03 prerequisite SHA:** `e21887fb4f7de0d40d7fb5ea2b8af6aa245a4f3a`
- **Alembic head before / after:** `f6b0d3e8c5a2` / `f6b0d3e8c5a2` (unchanged)
- **Local safety ref preserved:** `recovery/ums03e-conflated-71fd9f4d5`
  → `71fd9f4d5f4f2d05eb97c829a0097039c5fb0cae` (untouched)
- **Runtime changes:** none
- **Schema changes:** none
- **Export/restore implementation changes:** none

## Objective

Extend the normative
[Account Export + Restore Contract](../../account-export-restore-contract.md)
with one UMS-specific section that freezes canonical memory
export and restore semantics, so the UMS-04 implementation
slices can be built mechanically without reopening
architecture questions.

## Current implementation inventory

### Export implementation

- `guardian/services/account_export.py` (lines 1–634+
  read in UMS-04A preflight)
- Defines `OMITTED_FAMILIES`, `PAYLOAD_ORDER`, `PAYLOAD_FAMILIES`,
  `PAYLOAD_ORDER_BY_SCHEMA`, `BINARY_FAMILIES`
- Current manifest schema version: `account-export.v3`

### Restore implementation

- The current account-restore code path is governed by the same
  normative contract; implementation is consumed via the
  `guardian/services/account_export.py` `fetch_account_export_*_for_user`
  reader functions and the corresponding restore-side parsing
  inside the same service family.
- The exact implementation/test paths used by current restore
  were located during this preflight and recorded here; this
  task does not modify them.

### Current export tests

- `tests/services/test_account_export_extension_bindings.py`
- `tests/services/test_account_export_extension_proposals.py`
- `tests/services/test_account_export_extension_registry.py`
- `tests/services/test_account_export_persona_profiles.py`

These tests cover the existing `account-export.v3` payload
families. They do not currently cover UMS canonical memory.

## Current memory-related export coverage matrix

| Family | Current status | Evidence |
| --- | --- | --- |
| `memory_entries` | `OMITTED_FAMILIES` (line 142) | `guardian/services/account_export.py:142` |
| `personal_facts` | `OMITTED_FAMILIES` (line 144) | `guardian/services/account_export.py:144` |
| `personal_fact_evidences` | `OMITTED_FAMILIES` (line 145) | `guardian/services/account_export.py:145` |
| `personal_fact_revisions` | `OMITTED_FAMILIES` (line 146) | `guardian/services/account_export.py:146` |
| `persona_profiles` | `EXPORTED_AND_RESTORED` (v3 payload family) | `PAYLOAD_ORDER` line 16 |
| `persona_profile_revisions` | `EXPORTED_AND_RESTORED` (v3 payload family) | `PAYLOAD_ORDER` line 17 |
| `persona_profile_bindings` | `EXPORTED_AND_RESTORED` (v3 payload family) | `PAYLOAD_ORDER` line 18 |
| `persona_subjects` | **NOT_COVERED** (not in OMITTED, not in PAYLOAD_ORDER) | grep result: empty |
| `persona_subject_bindings` | **NOT_COVERED** (not in OMITTED, not in PAYLOAD_ORDER) | grep result: empty |
| `memory_records` | **NOT_COVERED** (canonical UMS substrate) | not present in `account_export.py` |
| `memory_persona_links` | **NOT_COVERED** (canonical UMS substrate) | not present in `account_export.py` |
| `memory_provenance` | **NOT_COVERED** (canonical UMS substrate) | not present in `account_export.py` |

The `persona_subjects` / `persona_subject_bindings` gap is
particularly important for the UMS-04A contract: they are
**neither** in `OMITTED_FAMILIES` (the explicit non-coverage
list) **nor** in `PAYLOAD_ORDER` (the explicit coverage list).
The UMS-04A contract resolves this explicitly below.

## Stable Persona-subject dependency verdict

`memory_persona_links.persona_subject_id` is a foreign key into
`persona_subjects(persona_subject_id, user_id)`. The current
export code does not export `persona_subjects` or
`persona_subject_bindings`. Therefore UMS-04 implementation
must extend export coverage to include those supporting
families, OR restore must fail closed for any
`memory_persona_links` row whose target Persona subject is
not otherwise recoverable.

The UMS-04A contract adopts option (A): UMS-04 implementation
must extend export coverage to `persona_subjects` and
`persona_subject_bindings` (and document the corresponding
restore-side reconstruction) before any
`memory_persona_links` row can be restored. The
`persona_profile_*` families are NOT a substitute.

## Canonical UMS export families

Frozen in
[Account Export + Restore Contract](../../account-export-restore-contract.md)
section "Unified Memory Store (UMS) Export + Restore" —
"UMS families included in the export":

```text
memory_records
memory_persona_links
memory_provenance
```

These are the physical canonical table names and the
export entity-family keys. No alias mapping is created.

## Required field coverage (frozen)

### `memory_records`

`memory_id`, `user_id` (logical owner), `project_id` (nullable),
`semantic_species` (closed `MemorySemanticSpecies` token),
`text_content`, `fact_key`, `fact_value`, `fact_confidence`,
`reviewed_at`, `activated_at`, `pinned`, `held`,
`extensions`, `created_at`, `updated_at`.

### `memory_persona_links`

`link_id`, `memory_id`, `user_id`, `persona_subject_id`,
`persona_user_id`, `link_kind` (closed `MemoryPersonaLinkKind`
token), `created_at`.

### `memory_provenance`

`provenance_id`, `memory_id`, `user_id`, `source_system`
(closed vocabulary), `source_record_id`, `source_thread_id`,
`source_message_id`, `source_import_job_id`,
`source_export_fingerprint`, `source_subject_kind`,
`source_subject_id`, `is_imported`, `extensions`,
`created_at`.

## Canonical identity behavior

Exported `memory_id` is the stable canonical memory identity.
On a successful restore, the same `memory_id` must appear in
the restored `memory_records` row. `memory_id` is portable
across restore operations; it is never remapped merely
because restore occurs on another database instance.

`memory_persona_links.link_id`, `memory_provenance.provenance_id`,
and any future stable UMS identity follow the same rule.

## Collision and conflict behavior

- Same `memory_id` + semantically identical exported record:
  treated idempotently.
- Same `memory_id` + conflicting canonical record: fail closed.
  Restore report enumerates the conflict by stable identity.
  No silent overwrite is allowed.
- Missing owner / Project / Persona-subject mapping: fail closed
  per the family-specific mapping rules.

## Account-owner remapping rule

The exported raw local `user_id` is not authorization. Canonical
memory ownership is rewritten only through the existing account
restore owner map. No independent UMS account map is introduced.

## Project reference remapping rule

Project-scoped memories require explicit Project identity mapping
through the existing Project restore identity map. Missing
Project mapping fails closed or reports explicit loss.
The restore must never silently widen `project_id` to `NULL`,
and must never move a memory from one Project to another.

## Persona-subject reconstruction rule

`memory_persona_links.persona_subject_id` is restored only
through stable Persona-subject identity. The target Persona
subject must be resolvable in the restore-target account and
must belong to the same restore-target account. Missing,
ambiguous, or cross-account resolution fails closed for that
link row. Display-name matching, prompt matching, similarity,
and current Persona configuration are never used. PersonaProfile
IDs are never substituted for stable Persona-subject identity.

## Provenance reference behavior

Local Codexify foreign keys (`source_thread_id`,
`source_message_id`) must use the existing thread and message
ID maps produced by the rest of full-account restore. Opaque
external references (`source_record_id`,
`source_import_job_id`, `source_export_fingerprint`,
`source_subject_id`) must be preserved exactly as exported; the
restore engine must not reinterpret them as Codexify-local IDs.
`source_system` must be preserved as the exact closed vocabulary
value.

## Restore dependency order

```text
account / user mapping
    ↓
Projects (existing)
    ↓
stable Persona subjects / bindings (existing or UMS-04)
    ↓
memory_records
    ↓
memory_persona_links
memory_provenance
```

UMS-04 must express this ordering in the existing multi-phase
restore pipeline rather than inventing a parallel restore
engine.

## Legacy + canonical coexistence prohibition

The export may contain both authoritative legacy memory state
and canonical UMS state. Both restore according to their own
persistence contracts, side by side, in the same export.

Explicitly prohibited:

- Constructing canonical `memory_records` rows from
  `memory_entries` content
- Constructing canonical `memory_records` rows from
  `personal_facts` content
- Constructing legacy rows from canonical memory
- Merging by text
- Merging by fact key
- Merging by provenance similarity
- Deduplicating canonical memory by content

## Compatibility-projection exclusion

`MemoryCompatibilityProjection`,
`MemoryCompatibilitySourceRef`, and
`MemoryCompatibilitySourceKind` are runtime read objects
defined by UMS-03E/F/G/I. They are not durable export families
and are never serialized as independent account-export
entities. They are reconstructed from restored legacy state at
read time.

## Semantic and lifecycle preservation

Round-trip must preserve exactly:

- `semantic_species` (closed `MemorySemanticSpecies` token)
- `reviewed_at` (nullable; exact timestamp or NULL)
- `activated_at` (nullable; exact timestamp or NULL)
- The `reviewed_at IS NULL OR (reviewed_at IS NOT NULL AND
  activated_at >= reviewed_at)` governance invariant
- Equal `reviewed_at == activated_at` timestamps are valid
- `pinned` (boolean)
- `held` (boolean)
- All fact payload fields (`text_content`, `fact_key`,
  `fact_value`, `fact_confidence`)

Restore must NOT infer review, activation, or lifecycle state.
Restore must NOT promote an inactive memory to active. Restore
must NOT change a pending review posture into approved.

## Extension non-authority policy

`extensions` is non-authoritative auxiliary metadata. The
export must preserve extension payload subject to the existing
schema-version compatibility policy for unknown extension
keys. Unknown extension keys must not alter ownership, Project
scope, Persona attribution, semantic species, or activation
authority.

## Manifest accounting

For schema versions that include UMS, `manifest.entity_counts`
must include:

- `memory_records`
- `memory_persona_links`
- `memory_provenance`

Plus, if UMS-04 implementation requires them:

- `persona_subjects`
- `persona_subject_bindings`

The existing integrity / checksum policy applies: per-file
checksums for every payload and manifest integrity verification
before restore proceeds. `entity_counts` validation compares
declared, serialized, and restored counts; mismatches fail
closed.

## Restore idempotency

Restoring the same export archive into the same restore-target
account is idempotent. A second restore does not create
duplicate `memory_records` rows for stable `memory_id` values,
does not create duplicate `memory_persona_links` rows for the
same `(memory_id, persona_subject_id, link_kind)`, and does not
collapse `memory_provenance` rows. Restore may use the existing
restore receipt / map mechanism. Content-based dedupe is
NEVER used.

## Conflict and fail-closed cases

Fail closed for:

- Duplicate `memory_id` with conflicting canonical content or
  state
- Missing account-owner mapping
- Missing Project mapping for a Project-scoped memory
- Missing or ambiguous Persona-subject mapping
- Cross-account Persona subject on `memory_persona_links`
- Unknown `semantic_species` value
- Unknown `link_kind` value
- Unknown `source_system` value
- Malformed `source_subject_kind` value
- Dangling parent `memory_id` reference in
  `memory_persona_links` or `memory_provenance`
- Incompatible export schema version
- Manifest integrity failure
- Entity-count mismatch between declared, serialized, and
  restored counts
- Relationship count mismatch where restore validation expects
  exact counts

The restore report must enumerate every skipped, repaired, or
failed entity and relationship by stable identity. Silent
degradation is forbidden.

## UMS-04 implementation slicing

```text
UMS-04A  contract freeze (this section)
UMS-04B  canonical memory export serialization
UMS-04C  canonical memory restore reconstruction
UMS-04D  full export → clean restore → second restore qualification
```

A smaller prerequisite may justify reordering if current
implementation topology proves it. UMS-05+ remain unauthorized
throughout UMS-04.

## Future round-trip qualification contract

UMS-04 implementation does not close from unit serialization
tests alone. The full UMS-04 closure requires a qualification
proof that demonstrates:

- A source account state produces an export archive.
- A clean restore target rehydrates the archive into a separate
  instance.
- A second restore of the same archive into the same target is
  idempotent.
- The qualification compares, for canonical UMS state:
  - `memory_id` equality
  - owner mapping
  - Project scope
  - `memory_persona_links` rows (stable Persona subjects,
    `link_kind`, cardinality)
  - `memory_provenance` multiplicity (no collapse, no merge)
  - `semantic_species` (exact canonical token, no aliases)
  - payload fields (`text_content`, `fact_key`, `fact_value`,
    `fact_confidence`)
  - governance state (`reviewed_at`, `activated_at`, the
    governance invariant, equal timestamps remain valid)
  - `pinned` and `held` boolean state
  - timestamps where the contract requires preservation
  - `extensions` payload preservation (or explicit loss
    reporting)
  - legacy memory preservation (separately, under existing
    doctrine)
  - manifest `entity_counts` and integrity
  - idempotency on second restore

No live retrieval change is required for UMS-04 qualification.
The qualification is a persistence round-trip proof, not a
runtime cutover proof.

## ADR impact

Aligned with ADR-081 (Project / account ownership), ADR-082
(PersonaProfile is configuration, not durable Persona identity),
and ADR-084 (Unified Account-Owned Memory Store). No new ADR
required. The UMS extension extends the existing export/restore
contract to state already accepted by ADR-084.

## Confirmed non-claims

- No production code was changed by UMS-04A.
- No test was changed by UMS-04A.
- No ORM model or migration was changed by UMS-04A.
- No export or restore implementation was changed by UMS-04A.
- No runtime authority was changed.
- No retrieval / router / MemoryOS / ContextBroker behavior was
  changed.
- No canonical `memory_id` was fabricated.
- No legacy-to-canonical inference was performed.
- No export artifact was produced.
- No new semantic species or Persona link kind was introduced.
- No new ADR was created.
- The Pi fixture remains untouched.
- The local safety ref
  `recovery/ums03e-conflated-71fd9f4d5` is preserved.
- Nothing was pushed or merged.

## Required successful state

```
UMS-03 CANONICAL STORAGE + COMPATIBILITY READS: CLOSED

UMS-04 EXPORT / RESTORE BEFORE INGESTION: OPEN
UMS-04A CANONICAL MEMORY EXPORT / RESTORE CONTRACT: CLOSED
UMS-04B CANONICAL MEMORY EXPORT SERIALIZATION: AUTHORIZED TO START
UMS-04C RESTORE RECONSTRUCTION: NOT AUTHORIZED
UMS-04D ROUND-TRIP QUALIFICATION: NOT AUTHORIZED

UMS-05+: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE

EXPORT:
  canonical memory families are defined
  canonical memory identity is preserved
  provenance is preserved
  compatibility projections are not export entities

RESTORE:
  account authority uses the existing restore owner map
  Project scope uses explicit Project mapping
  Persona attribution uses stable Persona subjects
  missing relationships fail closed
  restore is idempotent by stable identity

AUTHORITY:
  legacy memory remains runtime authority
  canonical UMS tables remain non-authoritative
  no authority cutover occurs

NEXT:
  implement canonical memory export serialization in UMS-04B
```
