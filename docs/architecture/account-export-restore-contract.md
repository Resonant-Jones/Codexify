# Codexify Account Export + Restore Contract

> Classification: architecture contract
> Status: normative
> Normative language: "must", "must not", "should", "non-goal", "guarantee", and "failure policy" are intentional contract terms.

Purpose: Define the canonical, versioned, user-owned export artifact that can rehydrate a full Codexify account without losing provenance, project membership, thread/message structure, media/document linkage, metadata, artifact relationships, or imported-source lineage.

Last updated: 2026-04-01

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
| Codex/artifact entries | Stable artifact IDs, artifact type, payload reference, source thread or message links, generation metadata, version, timestamps, tags/flags, and provenance. |
| Thread-linked artifacts and related metadata | Stable artifact IDs, thread ID, relationship metadata, timestamps, tags/flags, and provenance. |
| User-authored tags / flags / timestamps relevant to restore | Stable target IDs, tag or flag namespace, value, actor or owner where relevant, timestamps, and provenance if imported. |

Every record family must preserve stable identifiers, owner or account scoping, and restore-relevant timestamps. If an object is derived from another object, the derivation link must be exported explicitly.

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
