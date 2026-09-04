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

## Open Implementation Questions

The following questions are intentionally unresolved by this contract:

- Binary-in-zip vs referenced blob layout
- Export size limits and streaming strategy
- Whether export and restore should be synchronous or job-based
- Whether restore should support partial family selection
- How future encrypted exports should handle key management, rotation, and recovery
- The versioned payload shape and verifier-invalidation mechanism for Hosted Room metadata
