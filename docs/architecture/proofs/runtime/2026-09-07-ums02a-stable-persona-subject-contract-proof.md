# UMS-02A Stable Persona-Subject Contract Proof

Date: 2026-09-07

Status: **PASSED**

## Qualification identity

- Starting implementation checkpoint: `e8f33aa67b918a67656090e79ced7a7a21517af1`
- Starting checkpoint at UMS-02B BLOCKED; UMS-02A retried from this checkpoint.
- UMS-01 closed checkpoint: `a2e4b5262a1112ec97bab3c3774403bde0a9b7af`
- UMS-01Q PostgreSQL qualification proof: [`2026-09-06-project-ownership-postgresql-qualification-proof.md`](./2026-09-06-project-ownership-postgresql-qualification-proof.md)

## Authority and scope

UMS-02A is the freeze-only slice for the Unified Account-Owned Memory Store
stable Persona-subject mapping. It materializes the conceptual model in
[§4.3 of the Unified Memory Store Contract](../../unified-memory-store-contract.md)
against the current repository truth, freezes an implementation-ready mapping
and enforcement contract in [§4.5](../../unified-memory-store-contract.md),
and explicitly defers the canonical `persona_subjects.lifecycle` token
surface to UMS-02B under option C.

UMS-02A introduces no tables, migrations, ORM models, services, routes, or
memory links. ADR-081, ADR-082, and ADR-084 remain unchanged. UMS-02B
implementation is authorized; UMS-03 remains not authorized.

## Repository identity inventory

The current durable Persona-persistence surfaces at `main` are:

| Durable surface | Table | Model | File | Identity | Authoritative account ownership | Lifecycle / versioning |
| --- | --- | --- | --- | --- | --- | --- |
| `Persona` | `personas` | `guardian.db.models.Persona` | `guardian/db/models.py:4668`; migration `d3b3e9f5d5ab_add_imprint_persona_system_docs.py`; backfill `f2b3c4d5e6f8_add_user_id_to_core_entities.py` | `id` autoincrement int (PK) | `personas.user_id` (FK `users.id`, NOT NULL); partial unique `(user_id, project_id) WHERE is_active` | mutable `is_active`; no immutable revision history; multiple inactive rows may exist per `(user_id, project_id)` |
| `PersonaProfile` | `persona_profiles` | `guardian.db.models.PersonaProfile` | `guardian/db/models.py:4068`; migration `b7c8d9e0f1a2_add_persona_profiles_table.py` | `id` string(128) PK | none on the row; account scope lives in `persona_profile_bindings.owner_account_id` | mutable registry with `current_revision`; CHECK `current_revision > 0`; CHECK `0.0 <= temperature <= 2.0` |
| `PersonaProfileRevision` | `persona_profile_revisions` | `guardian.db.models.PersonaProfileRevision` | `guardian/db/models.py:4126`; migration `c3d9e1f4a6b8_persist_persona_profile_manifest_binding.py` | `(profile_id, revision)` PK | per-row scope via parent `PersonaProfileBinding` | immutable V1 manifest snapshots; CHECK `revision > 0`; index on `(profile_id, created_at)` |
| `PersonaProfileBinding` | `persona_profile_bindings` | `guardian.db.models.PersonaProfileBinding` | `guardian/db/models.py:4169`; migration `c3d9e1f4a6b8_persist_persona_profile_manifest_binding.py` | `profile_id` PK (1:1) | `owner_account_id` FK `users.id`, NOT NULL; index on `owner_account_id` | no lifecycle state column; `created_at` / `updated_at` only |
| Thread Persona/Profile pin | `chat_threads` | `guardian.db.models.ChatThread` | `guardian/db/models.py:1170`; migrations `002_create_chat_threads.sql`, `7f6e5d4c3b2a_add_active_profile_id_to_chat_threads.py`, `d4e0f2a5b7c9_pin_thread_persona_profile_revision.py` | nullable `active_profile_id` (string) + nullable `active_profile_revision` (int) | thread owner is `chat_threads.user_id` (NOT NULL) | CHECK `active_profile_revision IS NULL OR active_profile_revision > 0`; CHECK `active_profile_revision IS NULL OR active_profile_id IS NOT NULL`; FK `(active_profile_id, active_profile_revision) → persona_profile_revisions(profile_id, revision)` |

A durable legacy `Persona` source (`personas`) exists at current `main` and
is therefore migratable under `ref_kind = persona`. The conceptual
mapping between `Persona` and `PersonaProfile` is not currently preserved
by any persistent foreign key or binding row. The thread pin is a runtime
configuration reference and is never authoritative for Persona-subject
identity.

`persona_subjects` and `persona_subject_bindings` do not yet exist in
canonical SQLAlchemy metadata or in any migration. UMS-02B is the bounded
implementation slice that introduces them.

## Source-reference mapping

| `ref_kind` | Canonical source entity / table | Stable source identifier | Account-ownership evidence | Mutable configuration | Replaced / versioned | May establish subject continuity |
| --- | --- | --- | --- | --- | --- | --- |
| `persona` | `personas` | `personas.id` (autoincrement int) | `personas.user_id` (FK `users.id`, NOT NULL) | yes (`body`, `is_active`, `source`) | replaced by insert + activation; no immutable revision history | no |
| `persona_profile` | `persona_profiles` (+ `persona_profile_revisions`) | `persona_profiles.id` (string) | `persona_profile_bindings.owner_account_id` (FK `users.id`, NOT NULL) | yes (manifest revisions; `current_revision` pointer advances on substantive update) | yes (immutable revisions under `(profile_id, revision)`) | yes, only with explicit durable continuity evidence |

## Frozen contract rules

The following rules are frozen in §4.5 of the Unified Memory Store
Contract:

- **Subject-creation rule.** A migration may create a `persona_subjects`
  row only when both `proven account ownership` and `proven source
  identity` are satisfied. Names, prompts, descriptions, avatars,
  Project membership, profile similarity, active-thread selection,
  provider/model configuration, and model inference are explicitly
  non-authoritative and may not create or coalesce a Persona subject.
- **Coalescing rule.** Four explicit categories: proven same subject;
  proven distinct subjects; ownership-known-but-equivalence-unknown
  (do not merge); ambiguous/contradictory mapping (fail closed). No
  heuristic matching is permitted.
- **Binding-history semantics.** `valid_from` inclusive start;
  `valid_until` exclusive end with `NULL` denoting an active binding;
  unique active binding per `(ref_kind, ref_id)` enforced by partial
  unique index; half-open `[valid_from, valid_until)`; no overlaps.
- **Cross-account enforcement mechanism.** `persona_subjects.user_id`,
  `persona_subject_bindings.subject_user_id`, and a binding-row
  `source_account_id` populated from the source's authoritative account
  at insert time, plus a CHECK `source_account_id = subject_user_id`.
  The polymorphic binding shape cannot enforce account consistency
  without the `source_account_id` column; this is the minimum required
  shape refinement UMS-02B must introduce.
- **Replacement / versioning semantics.** Predecessor binding closed by
  `valid_until = T`; successor opens with `valid_from = T` and
  `valid_until = NULL`; atomic; historical binding retained; stable
  `persona_subject_id` preserved only when explicit durable continuity
  evidence exists.
- **Legacy / ambiguous migration policy.** Valid account-bound sources
  create one subject with one active binding; unbound, cross-account,
  multi-candidate, duplicate, no-account, zero-user, and multi-user
  legacy situations all fail closed and require separately authorized
  reconciliation.

## Lifecycle decision (option C — deferred to UMS-02B)

There is no canonical lifecycle / token domain at current `main` that
governs Persona-subject identity. Request, provider, bounded tool-loop,
and Campaign Runner lifecycle tokens cover runtime and execution
semantics only. Personal Facts and ordinary-memory lifecycle tokens
govern their own domains only. Project `archived_at` and `system_role`
govern Project lifecycle only. The Imprint persona system uses
`personas.is_active` as a runtime toggle, not a canonical lifecycle
token.

Under option C, UMS-02A freezes the contract but explicitly records the
canonical `persona_subjects.lifecycle` surface as the smallest
prerequisite for UMS-02B. UMS-02A does not bind lifecycle values or
transition rules itself. UMS-02B must:

1. Add a bounded `PersonaSubjectLifecycle` (or equivalent canonical
   token class) to `guardian/protocol_tokens.py` with exact values and
   transition meaning for `persona_subjects.lifecycle`.
2. Record the new canonical lifecycle domain in
   `docs/architecture/runtime-protocol-token-contract.md`.
3. Add `persona_subjects` and `persona_subject_bindings` to canonical
   SQLAlchemy metadata only while keeping all other migration, runtime,
   and release semantics unchanged.
4. Qualify the bounded implementation on disposable PostgreSQL without
   widening the existing migration lineage.

`persona_subjects.lifecycle` must not be assigned ad hoc values in
UMS-02A or in any pre-prerequisite code path.

## Export-shape review

The minimum future portable state for stable Persona attribution,
recorded for later exporter/restore authorization, is:

- stable `persona_subject_id`;
- owning account relationship;
- canonical display snapshot / metadata (descriptive only);
- lifecycle state once resolved under the canonical lifecycle
  prerequisite recorded in §4.5.8;
- binding source kind and identifier (`ref_kind`, `ref_id`);
- binding history timestamps (`valid_from`, `valid_until`);
- explicit relationship records required to remap account-local IDs
  safely.

Source IDs and display names are provenance and reference data only,
not authority. UMS-02A does not modify exporter or restore code.

## ADR impact

- ADR-081 — Project Ownership Authority: unchanged.
- ADR-082 — Persona Profile Manifest and Binding Authority: unchanged.
- ADR-084 — Unified Account-Owned Memory Store: unchanged.
- §4.5 of the Unified Memory Store Contract: implementation-ready
  contract added (Persona-subject mapping and enforcement); no ADR
  widening.

## Invariant check

All sixteen UMS-02A invariants were rechecked against the §4.5 contract
text and current repository evidence. The account-owned subject
ownership rule, configuration-vs-identity separation, non-inference rule,
cross-account binding prohibition, durable ownership evidence
consumption, unbound-source fail-closed rule, ambiguous-equivalence
fail-closed rule, name/display non-authority rule, Project orthogonality
rule, explicit continuity rule for replacement, historical attribution
preservation rule, canonical-token-only lifecycle rule, no-memory-link
rule, no-release-widening rule, Pi fixture untouched rule, and the
documentation-only implementation policy are all preserved.

## Proof limits

- This is a documentation-only freeze.
- No runtime, migration, model, test, export, or restore code changed.
- The lifecycle / token decision is documented as a prerequisite for
  UMS-02B; it is not implemented, proven, or exercised here.
- The bounded implementation will be qualified on disposable PostgreSQL
  in UMS-02B.

## Validation and commit

- `scripts/validate_docs.py` passed.
- `git diff --check` passed over the staged documentation files.
- Only the four authorized documentation files were committed.
- The Pi fixture remained untouched and unstaged.
- No push or merge was performed.

## Decision

```text
UMS-02A STABLE PERSONA SUBJECT CONTRACT: PASSED
UMS-02: OPEN
UMS-02B IMPLEMENTATION: AUTHORIZED
UMS-03: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE
```
