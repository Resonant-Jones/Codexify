# Codexify Account Export + Restore Contract

> Classification: architecture contract
> Status: normative
> Normative language: "must", "must not", "should", "non-goal", "guarantee", and "failure policy" are intentional contract terms.

Purpose: Define the canonical, versioned, user-owned export artifact that can rehydrate a full Codexify account without losing provenance, project membership, thread/message structure, media/document linkage, metadata, artifact relationships, or imported-source lineage.

Last updated: 2026-09-04

## Purpose

This contract exists for:

- full-account portability
- disaster recovery and lost-device recovery
- upgrade safety and pre-update backups
- future third-party migration normalization

The export artifact defined here is an application-level data product. It is not a deployment snapshot and it is not a UI surface.

## Non-Goals

This contract is not:

- a Docker volume snapshot spec
- a UI design spec
- an implementation plan
- a one-off ChatGPT export format

## Core Guarantee

The export and restore path must satisfy all of the following:

- Export must preserve canonical Codexify state.
- Export must preserve source provenance.
- Restore must faithfully rehydrate saved state.
- Restore must not silently drop lineage, ownership, project context, or relationship structure.
- Restore must preserve semantic equivalence even if underlying local persistence IDs are remapped.

If a restore cannot preserve one of those guarantees, it must fail or report the loss explicitly. Silent degradation is not allowed.

## Canonical Artifact

The primary user-facing export artifact must be a single archive. The canonical default name is `Codexify-Export.zip`.

The archive must contain, at minimum:

- `manifest.json`
- machine-readable entity payloads
- explicit relationship payloads
- media/document binaries, or explicit binary references only when the manifest declares that mode
- integrity metadata
- restore compatibility metadata

`manifest.json` is the source of truth for the archive. Payload grouping and internal filenames may evolve across schema versions, but every payload must be enumerated by the manifest.

If the archive uses binary references instead of bundled binaries, the manifest must state that choice explicitly and must include the resolution policy, declared content hashes, and any restore prerequisites needed to resolve the references.

## Schema and Version Contract

The export format is versioned. Versioning applies to the archive format itself, not just the Codexify app release that produced it.

`manifest.json` must include at minimum:

- export schema version
- Codexify app/runtime version
- export creation timestamp
- export kind
- counts by entity family
- checksum or integrity section
- compatibility fields for future restore logic

Required manifest behavior:

- `schema_version` must identify the archive schema, including payload and relationship semantics.
- `app_version` must identify the Codexify runtime that created the archive.
- `created_at` must be explicit and machine-readable.
- `export_kind` must identify the intended export class; the canonical value for this contract is `full_account`.
- `entity_counts` must be grouped by entity family and used for validation during restore.
- `integrity` must describe the checksum or hash algorithm and the digest for every file that restore depends on.
- `compatibility` must declare restore reader expectations, blob mode, required feature flags, and any explicitly declared migration path.

Versioned restore behavior must be intentional. A newer or incompatible schema must not be guessed at. If restore support does not exist for a schema version, the restore path must fail closed unless the manifest declares a migration path that the restore engine explicitly supports.

Forward migration behavior must be designed and tested as a first-class path, not an accidental side effect of permissive parsing.

### Current archive compatibility

New full-account exports use `account-export.v3`. The v3 family contract adds
`persona_profiles`, `persona_profile_revisions`, and
`persona_profile_bindings` as three required, integrity-covered payloads.
Restore retains explicit readers for historical `account-export.v1` and
`account-export.v2` archives using their historical family set; those archives
do not contain and must not fabricate Persona Profile state. Required-file,
family, count, and checksum validation is selected by schema version and remains
fail-closed.

## Required Export Surface

All IDs, metadata, and relationships in the following families must be explicit in the export. No family may depend on implicit joins during restore.

| Family | Must export |
| --- | --- |
| Projects | Stable project IDs, project metadata, memberships, project-level timestamps, tags/flags, and provenance. |
| Chat threads | Stable thread IDs, owning project membership, thread metadata, ordering context, timestamps, tags/flags, and provenance. |
| Chat messages | Stable message IDs, thread ID, explicit ordering index, parent or child references where applicable, content, author/role metadata, edit or deletion metadata when restore-relevant, timestamps, and provenance. |
| Uploaded documents | Stable document IDs, binary hash or binary reference, filename or title, MIME type, size, storage locator when needed, links to threads and projects, timestamps, tags/flags, and provenance. |
| Generated documents | Stable document IDs, binary hash or binary reference, generation metadata, source artifact links, links to threads and projects, timestamps, tags/flags, and provenance. |
| Uploaded images | Stable image IDs, binary hash or binary reference, MIME type, size, links to threads and projects, timestamps, tags/flags, and provenance. |
| Generated images | Stable image IDs, binary hash or binary reference, generation metadata, source artifact links, links to threads and projects, timestamps, tags/flags, and provenance. |
| Media assets / aliases | Canonical asset IDs, alias IDs, storage locator or blob reference, content hash, MIME type, dedupe keys when present, timestamps, and provenance. |
| Thread-document links | Stable link IDs, thread ID, document ID, link role or type, timestamps, and provenance. |
| Project-document links | Stable link IDs, project ID, document ID, link role or type, timestamps, and provenance. |
| Codex/artifact entries | Stable artifact IDs, artifact type, payload reference, source thread or message links, `created_from` (slash_command or semantic_suggestion), `retrieval_enabled` flag, `project_id`, `persona_id`, `trigger_message_id`, generation metadata, version, timestamps, tags/flags, and provenance. |
| Thread-linked artifacts and related metadata | Stable artifact IDs, thread ID, relationship metadata, timestamps, tags/flags, and provenance. |
| User-authored tags / flags / timestamps relevant to restore | Stable target IDs, tag or flag namespace, value, actor or owner where relevant, timestamps, and provenance if imported. |
| User profile metadata | Stable user/profile ownership mapping, display name, avatar URL, timezone, timestamps, and provenance where preserved. |
| Persona Profile registry | Stable profile ID, current immutable revision pointer, and restore-relevant timestamps. The five-field runtime projection is derived from the current manifest rather than archived as canonical truth. |
| Persona Profile revisions | Every immutable revision with profile ID, revision, manifest API version, complete validated `PersonaProfileManifest`, and creation timestamp. |
| Persona Profile bindings | The profile-to-owning-account relationship and timestamps, physically separate from authored manifest content. |
| Hosted Rooms | Stable room ID, owner account, backing-thread relationship, title, slug, lifecycle state, bounded enabled-agent identifiers, and lifecycle timestamps. |
| Hosted Room participants | Stable participant ID, room relationship, optional originating-invitation relationship, optional account binding, display label, constrained kind/role/state, and lifecycle timestamps, subject to sensitive-data treatment. |
| Hosted Room invitations | Stable invitation ID, room relationship, intended display-name snapshot, constrained lifecycle state, expiry and transition timestamps, and privacy-safe verifier disposition; no plaintext credential. |

Every record family must preserve stable identifiers, owner or account scoping, and restore-relevant timestamps. If an object is derived from another object, the derivation link must be exported explicitly.

## Hosted Room Export and Restore Posture

The persistence entities governed by [[adr/053-node-hosted-room-access-boundary|ADR-053]] belong to the owning account's data boundary. A future full-account export must preserve the Hosted Room-to-backing-thread relationship so transcript lineage remains intact without copying messages into a room-specific transcript.

Hosted Room participant and invitation metadata is sensitive. Export policy must explicitly govern display-name snapshots, optional participant account bindings, originating-invitation relationships, lifecycle history, and enabled resident-agent identifiers. Agent participants remain room-scoped agent identities, not Codexify accounts. Guest account bindings remain optional and must not be reconstructed from display labels.

Plaintext invitation credentials are never exportable because they are never stored. A stored invitation token hash or verifier must not become a reusable credential after restore. The safest baseline is to omit or invalidate stored verifiers during export/restore; any future regeneration path must issue new credential material explicitly, preserve lifecycle state, and never silently reactivate a revoked, expired, accepted, or closed-room invitation.

Account deletion must not orphan authority-bearing Hosted Room state. Room-owned invitations and participants follow the room lifecycle, while the canonical backing thread and its messages continue to follow normal account/thread deletion doctrine. Restore must preserve closed-room state and must not infer participation authority merely from restored metadata.

This contract defines the required posture only. Executable account export and restore code has not been updated for Hosted Rooms, and Hosted Room export/restore remains deferred. The persistence slice does not implement room APIs, invitation exchange, room sessions, authorization, Contacts workflows, or UI behavior; ADR-053 remains `Proposed`.

## Provenance Contract

Provenance is separate from normalized Codexify state.

Every exported entity or relationship that originated outside canonical Codexify should carry provenance fields where applicable, including:

- source_system
- source export type
- source export version
- original conversation, message, document, or artifact IDs where applicable
- import timestamp
- transformation notes or migration metadata
- adapter or importer version when relevant

Imported ChatGPT material, and any future Claude or Claude Code material, becomes canonical Codexify state after successful migration. The original source provenance does not remain authoritative, but it must remain attached for auditability, dedupe, replay safety, and later migration analysis.

Source provenance must survive re-export and restore cycles. Normalization must not erase the fact that the record came from elsewhere.

### Canonical Conversation Origin

Every canonical `chat_threads` row carries exactly one canonical conversation-origin token in the dedicated `origin_system` column. The canonical registry is bounded to exactly three values:

- `codexify` — the conversation was originally created inside Codexify.
- `openai` — the conversation was originally created in ChatGPT or another OpenAI surface.
- `anthropic` — the conversation was originally created in Claude or another Anthropic surface.

`origin_system` answers one question: "Where was this conversation originally created?". It does not answer which provider or model later executes completions inside the conversation, which project currently owns the thread, which persona is active, or which account-import adapter most recently touched it. Provider execution and conversation origin are independent axes.

`origin_system` is immutable under ordinary thread mutation. Title changes, summary changes, project moves, archival, unarchival, persona assignment, retrieval configuration changes, provider switches, and ordinary chat completion activity must never alter `origin_system`. Restore and import internals may set the canonical value at initial canonical creation; every later mutation treats it as lineage.

Filter surfaces, audit surfaces, and export/restore surfaces must use `origin_system` as the authoritative conversation-origin truth surface. The bounded registry is enforced at the storage layer by a CHECK constraint; unsupported canonical values cannot be stored or filtered accidentally. The column is indexed for owner-scoped filtering.

Imported-source product metadata (`import_source`, `import_profile`, `source_thread_id`, source-message identifiers, raw import envelopes) remains subordinate provenance for audit and backward compatibility. It must not be used as the authoritative conversation-origin filter after this invariant is established.

Legacy product names (`chatgpt`, `claude`, `gpt`, `open_ai`, `anthropic_claude`) are recognized only at the migration / import-compatibility boundary. They are mapped onto the canonical bounded registry by the deterministic rule: ChatGPT/OpenAI tokens become `openai`; Claude/Anthropic tokens become `anthropic`; any thread without explicit historical import provenance becomes `codexify`. Free-form strings are never canonical values; unknown external systems must fail closed rather than being silently mapped.

## Relationship and Lineage Contract

The restoreable export must explicitly preserve:

- project membership
- thread membership
- message ordering
- parent/child or DAG relationships where applicable
- message-to-asset links
- thread-to-document links
- project-to-document links
- artifact lineage back to the source thread or message when present
- alias relationships for media assets when present

No relationship may be left implicit if restore depends on it.

Relationship records must include stable endpoint IDs, relationship type, directionality, and any edge metadata required to reconstruct the graph deterministically.

Message ordering must use explicit ordinal or sequence values. Timestamps alone are not sufficient for deterministic restore.

## Restore Semantics

Restore behavior must be explicit for the following scenarios:

- clean import into a new instance
- re-import of the same export
- partial restore failure
- duplicate detection and idempotency
- missing blob detection
- incompatible-version handling
- explicit restore report output

Required behavior:

- Clean import into a new instance must recreate the canonical Codexify state represented by the archive.
- Re-import of the same export must be idempotent wherever feasible. Repeated restore must not create silent duplicates.
- Duplicate detection must use stable IDs, checksums, and provenance fingerprints, not filenames or arrival order.
- Missing blob detection must happen before commit when possible. If a required blob is absent, restore must fail closed or mark the affected entities as failed in the report. It must not drop them silently.
- Incompatible-version handling must fail closed unless the archive declares a supported migration path that the restore engine explicitly implements.
- Partial restore failure must be explicit. If partial restore is allowed, the report must enumerate every skipped, repaired, or failed entity and relationship by stable ID.
- Restore must produce an explicit report output. The report must include counts, migrated items, duplicate hits, missing blobs, warnings, failures, and any export-ID to local-ID mapping if remapping occurs.
- Restore must preserve the canonical `chat_threads.origin_system` exactly as declared by the export. Older archives that pre-date the canonical column must derive origin deterministically from explicit historical import provenance (ChatGPT/OpenAI → `openai`, Claude/Anthropic → `anthropic`, anything else → `codexify`); derivation must not consult runtime model/provider metadata. Archives that declare an unsupported `origin_system` must fail closed rather than silently rewriting it.
- Restore must preserve user profile metadata and the owning account mapping. If local persistence IDs are remapped, profile rows must follow the canonical owner and must not be reassigned by display label.
- Persona Profile restore must validate registry, complete immutable history,
  current-revision pointers, and binding ownership before writes. It restores
  registry, revisions, then bindings; reconstructs the five-field projection
  from the current manifest; and never allocates an authored revision.
- Persona Profile binding rows are full-account recovery metadata, not portable
  persona authority. Their owner must match the validated archive account, and
  the actual binding write uses the authenticated restore target. A mismatch or
  conflicting existing profile, immutable revision, or binding fails closed.
- Persona Profile manifests may not contain account authority, credentials, or
  secrets. Account scoping comes from the server-owned binding, and exports must
  exclude profiles bound to another account as well as unbound legacy profiles.

### Thread Persona revision recovery

The v3 `chat_threads` payload includes nullable `active_profile_revision` alongside
`active_profile_id`. An explicit pin restores the exact immutable revision even
when the archived Persona's current pointer is newer. Restore validates the pin
against the archive's account binding and immutable history before any writes.
Persona registry, revisions, and bindings restore before pinned threads; restore
never allocates a new authored revision or substitutes a newer revision.

Older v3 archives can omit the field. For those rows only, restore derives the
pin from the archived current pointer when the profile and revision exist in the
same archive, the binding and thread match the validated restore account, and
thread-local override metadata does not make the selection revisionless.
Otherwise the pin is NULL. Derivation never consults the receiving database's
current profile state. Explicit NULL remains NULL. V1/v2 archives restore NULL
pins and create no Persona revision state.

This additive nullable field does not introduce account-export.v4. Recovery
preserves thread binding reproducibility; request/attempt profile snapshots
remain deferred. See [Chat Runtime State Contract](./chat-runtime-state-contract.md).

Restore must never produce silent corruption.

## Integrity Requirements

The export and restore contract requires all of the following integrity surfaces:

- per-file checksum or hash for every payload and blob
- checksum coverage for `manifest.json`
- entity count validation against manifest counts
- missing-file detection
- manifest-to-payload consistency checks
- a restore summary or report retained as part of the restore result

The manifest must declare the hash algorithm used for each integrity entry. The algorithm must remain stable within a schema version.

Integrity validation is not optional. Restore is not complete until integrity checks have passed or failed explicitly.

## Failure Policy

The failure policy is:

- fail closed on structural corruption
- report skipped, repaired, and failed entities explicitly
- no silent metadata loss
- no silent lineage loss
- no silent project reassignment
- no silent dedupe collisions
- no silent fallback from bundled blobs to external references

Repair is only allowed when it is explicitly recorded in the restore report and does not erase provenance. If a payload, checksum, count, or relationship set is contradictory, restore must stop instead of guessing.

### Background Account-Import Completion

For the durable OpenAI account-import job, upload acceptance, worker execution,
and terminal completion are separate states. A `completed` or
`completed_with_warnings` result must be written only after the intended
canonical project, thread, message, or media writes have committed and their
bounded result counts are known for the importing account. A worker that
finishes traversal with zero committed canonical entities and no explicit
deduplication outcome must instead record `failed` with the canonical
`account_import_no_committed_entities` error code. The terminal result retains
bounded source conversation discovery, acceptance, skip, failure, and
transaction-commit evidence; it must not include source message content or
uploaded paths.

An all-deduplicated replay is an explicit no-op: it may complete with warnings
and its duplicate count, rather than being presented as a fresh import.

## Migration Normalization Note

Third-party exports are handled by adapters at ingest.

After migration, imported data is normalized into canonical Codexify structures.

There is no permanent external-adapter dependency after successful migration.

Source provenance remains attached even after normalization.

Future exports must be emitted from canonical Codexify state, not from the original third-party schema.

## Unified Memory Store (UMS) Export + Restore

This section extends the export + restore contract to canonical UMS state introduced by UMS-03D and the corresponding compatibility surface introduced by UMS-03A/E/F/G/H/I. It is normative for any UMS-04 implementation slice. It does not authorize UMS-05+.

The contract answers:

- what is exported
- what identity is preserved
- what identity may be remapped
- how relationships are reconstructed
- what order restore uses
- what conflicts mean
- what idempotency means
- what fails closed
- what remains legacy authority

### UMS families included in the export

The export must cover exactly three canonical UMS families, using the physical canonical table names as the export entity-family identifiers:

| Entity family | Source table | Authority role |
| --- | --- | --- |
| `memory_records` | `memory_records` | Canonical envelope row; one row per canonical memory atom |
| `memory_persona_links` | `memory_persona_links` | Typed stable-Persona attribution relationship; zero or more rows per memory |
| `memory_provenance` | `memory_provenance` | First-class durable lineage row; one or more rows per memory |

The export artifact uses the physical table names above as the entity-family keys. No alias mapping is created. The existing `OMITTED_FAMILIES` list remains authoritative for currently-uncovered families. UMS-04 implementation is responsible for moving `memory_records`, `memory_persona_links`, and `memory_provenance` from "not yet covered" to a covered payload family in a future `account-export.v4` schema version.

Supporting tables required to satisfy UMS restore are evaluated in the next subsection.

### Legacy authoritative memory sources

The current contract's `OMITTED_FAMILIES` continues to enumerate the legacy authoritative memory sources that are NOT covered by this section's UMS extension:

- `memory_entries`
- `personal_facts`
- `personal_fact_evidences`
- `personal_fact_revisions`

These legacy sources are governed by the existing account-export doctrine that is documented outside this UMS section. They are not merged, deduplicated against, or reconstructed into canonical UMS rows by export or restore.

### Supporting families required to satisfy UMS restore

`memory_persona_links.persona_subject_id` is a foreign key into `persona_subjects`, and `memory_provenance` may carry `source_thread_id` / `source_message_id` foreign keys into Codexify chat tables. Therefore UMS-04 restore cannot be complete unless the supporting entities are either:

- already part of the existing full-account export payload (verifiable from the `Required Export Surface` table above), OR
- explicitly added to the UMS-04 export in a future schema version

Specifically:

- `persona_subjects` and `persona_subject_bindings` must be present in the export, either by being included in a future UMS-04 schema version, or by being part of the existing full-account payload. PersonaProfile (the `persona_profiles` / `persona_profile_revisions` / `persona_profile_bindings` families) is configuration only and is not a substitute for stable Persona-subject identity. If stable Persona subjects are not restoreable from the export, `memory_persona_links` restore must fail closed per the failure policy below.
- The existing `chat_threads` and `chat_messages` export families must already be present in the export (they are). UMS-04 must not invent a parallel chat-message mapping; it must reuse the existing chat-thread and chat-message ID maps produced by the rest of full-account restore.
- For `memory_provenance.source_thread_id` and `memory_provenance.source_message_id`, the existing thread/message ID maps are reused. Missing or unmapped thread/message references must fail closed rather than be silently dropped.

### Required field coverage for `memory_records`

For every `memory_records` row, the export must preserve the complete set of fields required to restore exact semantic, ownership, scope, attribution, governance, and lifecycle state. The field set is the frozen UMS-03C / UMS-03D schema:

- `memory_id` (UUID)
- `user_id` (logical owner representation as required by account restore; the local raw export `user_id` is not authorization)
- `project_id` (nullable; explicit Project identity map reference when non-null)
- `semantic_species` (closed `MemorySemanticSpecies` token — only the three frozen values; no aliases)
- `text_content` (free-text for `episodic_semantic_memory`; nullable)
- `fact_key`, `fact_value`, `fact_confidence` (for personal-fact species; nullable)
- `reviewed_at` (nullable)
- `activated_at` (nullable)
- `pinned` (boolean, NOT NULL)
- `held` (boolean, NOT NULL)
- `extensions` (JSONB; non-authoritative auxiliary metadata only)
- `created_at` (NOT NULL)
- `updated_at` (NOT NULL)

### Required field coverage for `memory_persona_links`

For every `memory_persona_links` row, the export must preserve:

- `link_id` (UUID, stable link identity)
- `memory_id` (FK to `memory_records.memory_id`)
- `user_id` (FK to `users.id`; account of the memory; CASCADE on user delete)
- `persona_subject_id` (FK to `persona_subjects.persona_subject_id`)
- `persona_user_id` (FK to `users.id`; account of the Persona subject; same-account CHECK)
- `link_kind` (closed `MemoryPersonaLinkKind` token — only the three frozen values; no aliases)
- `created_at`

PersonaProfile is never a Persona-subject substitute during restore. Display names, prompts, similarity, or current configuration are not attribution authority.

### Required field coverage for `memory_provenance`

For every `memory_provenance` row, the export must preserve the full frozen UMS-03C / UMS-03D provenance spine:

- `provenance_id` (UUID, stable provenance identity)
- `memory_id` (FK to `memory_records.memory_id`)
- `user_id` (FK to `users.id`; account of the memory; CASCADE on user delete)
- `source_system` (closed vocabulary: `codexify`, `openai`, `anthropic`, `future_registered`)
- `source_record_id` (opaque, nullable)
- `source_thread_id` (FK to `chat_threads.id`, nullable)
- `source_message_id` (FK to `chat_messages.id`, nullable; `SET NULL` on chat-message delete)
- `source_import_job_id` (opaque, nullable)
- `source_export_fingerprint` (opaque, nullable)
- `source_subject_kind` (closed vocabulary: `chat`, `vault`, `importer`, `classifier`, future-registered; nullable)
- `source_subject_id` (opaque, nullable)
- `is_imported` (boolean, NOT NULL)
- `extensions` (JSONB; non-authoritative auxiliary metadata only)
- `created_at` (NOT NULL)

Multiple provenance rows per memory must NOT be collapsed. Distinct source identities must remain distinct after round-trip.

### Canonical identity behavior

The exported `memory_id` is the stable canonical memory identity. On a successful restore, the same `memory_id` must appear in the restored `memory_records` row.

`memory_id` is NOT remapped merely because restore occurs on another database instance or another user-owned storage area. A `memory_id` is portable across restore operations.

`memory_persona_links.link_id`, `memory_provenance.provenance_id`, and any future stable UMS identity follow the same rule.

### Collision and conflict behavior

Collision policy distinguishes:

- `same memory_id + semantically identical exported record` — treated idempotently by stable identity. No duplicate is created.
- `same memory_id + conflicting canonical record` — fail closed. The restore report must enumerate the conflict by stable identity. No silent overwrite is allowed.
- Missing owner / Project / Persona-subject mapping — fail closed per the family-specific mapping rules below.

### Account-owner remapping

The exported raw local `user_id` is never authorization. Canonical memory ownership is rewritten only through the existing account restore owner map. No independent UMS account map is introduced.

If a `memory_records.user_id` does not resolve to the authenticated restore-target account through the existing owner map, restore fails closed for that row.

### Project reference remapping

Project-scoped memories require explicit Project identity mapping. UMS-04 must reuse the existing Project restore identity map.

If Project mapping is unavailable for a `memory_records.project_id`:

- The restore must FAIL CLOSED or report EXPLICIT LOSS for that row.
- The restore must NEVER silently widen `project_id` from a non-null value to `NULL`.
- The restore must NEVER silently move a memory from one Project to another.

The Project mapping is the Project identity map owned by the rest of full-account restore. UMS-04 does not own a parallel Project identity map.

### Persona-subject reconstruction

`memory_persona_links.persona_subject_id` is restored only through stable Persona-subject identity.

Restore rules:

- The target Persona subject must be resolvable in the restore-target account (either pre-existing in the receiving database, or restored as part of the same archive).
- The target Persona subject must belong to the same restore-target account (no cross-account attribution).
- A missing, ambiguous, or cross-account Persona subject resolution must fail closed for that link row.
- Display-name matching, prompt matching, similarity, or current Persona configuration is NEVER used to reconstruct Persona attribution.
- PersonaProfile IDs must NEVER replace stable Persona-subject identity during restore.

### Provenance reference behavior

For `memory_provenance` rows that carry local Codexify foreign keys:

- `source_thread_id` and `source_message_id` must use the existing thread and message ID maps produced by the rest of full-account restore.
- If a local thread or message reference cannot be remapped, the provenance row restore must fail closed for that row.

For opaque external references:

- `source_record_id`, `source_import_job_id`, `source_export_fingerprint`, and `source_subject_id` are preserved exactly as exported.
- The restore engine must NOT reinterpret opaque external identifiers as Codexify-local IDs.

`source_system` must be preserved as the exact closed vocabulary value.

### Restore dependency order

The restore must follow a dependency order that satisfies the foreign-key and same-account invariants. The required order, at minimum, is:

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

UMS-04 must express this ordering in the existing multi-phase restore pipeline rather than inventing a parallel restore engine.

### Legacy + canonical coexistence

The export may contain both authoritative legacy memory state (`memory_entries`, `personal_facts`, and their dependent families) and canonical UMS state.

The two are distinct persistence families. The following are explicitly PROHIBITED in export and restore:

- Constructing canonical `memory_records` rows from `memory_entries` content
- Constructing canonical `memory_records` rows from `personal_facts` content
- Constructing legacy rows from canonical memory
- Merging by text
- Merging by fact key
- Merging by provenance similarity
- Deduplicating canonical memory by content

Until a future authority-cutover migration exists, both families restore according to their own persistence contracts, side by side, in the same export.

### Compatibility-projection exclusion

`MemoryCompatibilityProjection`, `MemoryCompatibilitySourceRef`, and `MemoryCompatibilitySourceKind` are runtime read objects defined by UMS-03E/F/G/I. They are NOT durable export families.

A compatibility projection is reconstructed from restored legacy state at read time. It is never serialized as an independent account-export entity.

### Semantic and lifecycle preservation

Round-trip must preserve exactly:

- `semantic_species` (closed `MemorySemanticSpecies` token; one of the three frozen values)
- `reviewed_at` (nullable; round-trips the exact timestamp or NULL)
- `activated_at` (nullable; round-trips the exact timestamp or NULL)
- The `reviewed_at IS NULL OR (reviewed_at IS NOT NULL AND activated_at >= reviewed_at)` governance invariant
- Equal `reviewed_at == activated_at` timestamps are valid
- `pinned` (boolean)
- `held` (boolean)
- All fact payload fields (`text_content`, `fact_key`, `fact_value`, `fact_confidence`)

Restore must NOT infer review. Restore must NOT infer activation. Restore must NOT change a "pending" review posture into "approved". Restore must NOT promote an inactive memory to active. Restore must NOT alter lifecycle state through inference.

### Extension behavior

`extensions` is non-authoritative auxiliary metadata. The export must preserve extension payload subject to the existing schema-version compatibility policy for unknown extension keys.

Unknown extension keys must not:

- alter ownership
- alter Project scope
- alter Persona attribution
- alter semantic species
- alter activation authority

If a restore engine cannot preserve an unknown extension field's semantics, the field is dropped or reported as lost in the restore report — never reinterpreted.

### Manifest accounting and integrity

The export must extend the existing `manifest.json` model so that UMS families participate in `entity_counts` and integrity checks.

For schema versions that include UMS, `manifest.entity_counts` must include:

- `memory_records`
- `memory_persona_links`
- `memory_provenance`

Plus, if UMS-04 implementation requires them:

- `persona_subjects`
- `persona_subject_bindings`

The existing integrity / checksum policy applies: per-file checksums for every payload and manifest integrity verification before restore proceeds. `entity_counts` validation compares declared, serialized, and restored counts; mismatches fail closed.

### Restore idempotency

Restoring the same export archive into the same restore-target account is idempotent wherever the source-state remains unchanged. A second restore of the same archive does not create duplicate `memory_records` rows for stable `memory_id` values, does not create duplicate `memory_persona_links` rows for the same `(memory_id, persona_subject_id, link_kind)`, and does not collapse `memory_provenance` rows.

Restore may use the existing restore receipt / map mechanism where the receiving database records which canonical identity was already restored. Content-based dedupe is NEVER used.

### Conflict and fail-closed cases

The following are explicit fail-closed cases:

- Duplicate `memory_id` with conflicting canonical content or state
- Missing account-owner mapping
- Missing Project mapping for a Project-scoped memory
- Missing or ambiguous Persona-subject mapping
- Cross-account Persona subject on `memory_persona_links`
- Unknown `semantic_species` value
- Unknown `link_kind` value
- Unknown `source_system` value
- Malformed `source_subject_kind` value
- Dangling parent `memory_id` reference in `memory_persona_links` or `memory_provenance`
- Incompatible export schema version
- Manifest integrity failure
- Entity-count mismatch between declared, serialized, and restored counts
- Relationship count mismatch where restore validation expects exact counts

The restore report must enumerate every skipped, repaired, or failed entity and relationship by stable identity. Silent degradation is forbidden.

### UMS-04 implementation slicing

UMS-04 is decomposed into the following bounded slices:

```text
UMS-04A  contract freeze (this section)
UMS-04B  canonical memory export serialization
UMS-04C  canonical memory restore reconstruction
UMS-04D  full export → clean restore → second restore qualification
```

A smaller prerequisite may justify reordering if current implementation topology proves it. UMS-05+ remain unauthorized throughout UMS-04.

### Future round-trip qualification contract

UMS-04 implementation does not close from unit serialization tests alone. The full UMS-04 closure requires a qualification proof that demonstrates, at minimum:

- A source account state produces an export archive.
- A clean restore target rehydrates the archive into a separate instance.
- A second restore of the same archive into the same target is idempotent.
- The qualification compares, for canonical UMS state:
  - `memory_id` equality
  - owner mapping
  - Project scope
  - `memory_persona_links` rows (stable Persona subjects, `link_kind`, cardinality)
  - `memory_provenance` multiplicity (no collapse, no merge)
  - `semantic_species` (exact canonical token, no aliases)
  - payload fields (text / fact_key / fact_value / fact_confidence)
  - governance state (`reviewed_at`, `activated_at`, the `reviewed_at IS NULL OR (reviewed_at IS NOT NULL AND activated_at >= reviewed_at)` invariant, equal timestamps remain valid)
  - `pinned` and `held` boolean state
  - timestamps where the contract requires preservation
  - `extensions` payload preservation (or explicit loss reporting)
  - legacy memory preservation (separately, under existing doctrine)
  - manifest `entity_counts` and integrity
  - idempotency on second restore

No live retrieval change is required for UMS-04 qualification. The qualification is a persistence round-trip proof, not a runtime cutover proof.

## Open Implementation Questions

The following questions are intentionally unresolved by this contract:

- Binary-in-zip vs referenced blob layout
- Export size limits and streaming strategy
- Whether export and restore should be synchronous or job-based
- Whether restore should support partial family selection
- How future encrypted exports should handle key management, rotation, and recovery
- The versioned payload shape and verifier-invalidation mechanism for Hosted Room metadata
