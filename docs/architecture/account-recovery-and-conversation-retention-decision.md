# Account Recovery and Conversation Retention — Decision Brief

> Status: Decision requested; proposals below are not accepted architecture.
> Scope: Reconcile account export/restore and conversation lifecycle on the
> current `origin/main` tip. No runtime implementation or R2 work is authorized
> by this brief.

## Current-state discrepancy report

### Repository and release truth

This review is on branch `codex/persistence-export-archive-contracts-20261007`
at `62abe7890b5011e787848589a1530ffbc614e01f`, verified against the live
`origin/main` ref. The supplied handoff SHA `ec6312bb` is stale. The working
tree is clean. `docs/architecture/00-current-state.md` is dated 2026-10-06 and
describes local `main` as 3 ahead / 34 behind `origin/main`; that statement is
not a description of the live remote tip reviewed here. The file continues to
hold release truth: Compose qualification remains HOLD. This task establishes
no release-readiness claim.

The separately maintained Goal #1 checkout is clean at
`07cb77de17b50578916e5c13bab4b9e057e1f535` on
`codex/chat-stop-diagnostic-mainline`, 63 commits ahead of its tracking ref.
It was inspected read-only and was not changed. This brief does not change
chat execution or restart semantics.

### Export versions, emitted families, and omissions

The only public full-account download route is the authenticated
`GET /account.zip` route in `guardian/routes/api_exports.py`; it calls
`build_account_export_zip` without a schema override, so it emits v3. The
filename is `Codexify-Export.zip`. The separate `/chatgpt.zip` endpoint is a
transcript-format export, not the canonical account artifact.

The actual family sets in `guardian/services/account_export.py` and
`guardian/core/pgdb.py` are:

| Schema | Export behavior |
| --- | --- |
| v1 / v2 | Historical 15-family set: v3's 18 families minus `persona_profiles`, `persona_profile_revisions`, and `persona_profile_bindings`. |
| v3 | Default 18-family set: `projects`, `chat_threads`, `chat_messages`, `uploaded_documents`, `generated_documents`, `uploaded_images`, `generated_images`, `media_assets`, `media_aliases`, `thread_documents`, `project_document_links`, `extension_proposals`, `extension_install_gate_decisions`, `extension_registry_entries`, `extension_install_bindings`, `persona_profiles`, `persona_profile_revisions`, `persona_profile_bindings`. |
| v4 | Staged 23-family set: the v3 set plus `persona_subjects`, `persona_subject_bindings`, `memory_records`, `memory_persona_links`, and `memory_provenance`. The normal download route does not select v4. |

The code's `OMITTED_FAMILIES` names `memory_entries`, `oauth_connections`,
`personal_facts`, `personal_fact_evidences`, `personal_fact_revisions`,
`tts_outputs`, `message_audio_assets`, `connector_configs`, `connector_runs`,
`raw_documents`, `sync_jobs`, `agent_deployments`, `agent_runs`,
`agent_run_steps`, `agent_run_attempts`, `agent_run_artifacts`,
`agent_confidence_reports`, and `events_outbox`. A comment excludes
`candidate_trace` as noncanonical diagnostics but does not put it in the
manifest list. `user_profiles` and Hosted Room tables are neither emitted nor
listed as omitted. The contract requires User Profile metadata and Hosted Room
families, while explicitly describing Hosted Room export as deferred. These
are visible coverage gaps, not complete recovery.

The required User Profile minimum in the contract is display name, avatar URL,
timezone, ownership, and timestamps. The actual `user_profiles` row also holds
`profile_id`, `node_id`, `username`, `username_state`, and accent color. Any
future export needs a field-level privacy decision; exporting the whole row
would expose social identity fields beyond the contract's stated minimum.

Family names alone also overstate coverage. The `projects` reader currently
selects `id`, `user_id`, name/description/icon, identity depth, and timestamps,
but omits canonical `system_role` and `archived_at`; those fields govern the
renamable General/Imports roles and reversible Project lifecycle. The
`chat_messages` reader omits `hosted_room_participant_id` and
`sender_display_name_snapshot`, which are paired Hosted Room provenance fields
in the current model. The contract also names Codex/artifact and
thread-linked-artifact data, but no corresponding artifact family is present
in the emitted family sets; `agent_run_artifacts` is explicitly omitted and
must not be assumed equivalent without a semantic mapping.

### Blobs and integrity

The exporter attempts to resolve bytes for uploaded/generated documents,
uploaded/generated images, and media assets. Resolved bytes are bundled under
content-hash paths; unresolved rows remain in JSON with `status=unresolved`,
and the manifest reports coverage. Generated document content is serialized
from its database field. Thus the archive can contain bytes but can also be
incomplete.

The restore service validates declared payload and blob SHA-256 digests, counts,
and family/path consistency. It treats bundled blobs as validation-only:
`blob_restore_supported` is false and no object-store write-back occurs. The
contract's complete restore guarantee is therefore not met.

The manifest records hashes for payload and blob members, but not for
`manifest.json`. Restore explicitly skips a manifest self-entry. This conflicts
with both the base contract and UMS contract's manifest-integrity requirement.
The requirement needs a non-circular encoding, such as a separately hashed
manifest sidecar or a defined canonical-manifest digest.

### Restore route, support, and ordering

The metadata restore route is exposed as `/imports/account/metadata` and
`/api/imports/account/metadata`. It authenticates a user ID, passes the ZIP to
`AccountRestoreService`, and reports that blob write-back is not implemented.
The v1/v2 readers use the historical family set. v3 and v4 use the restore
order that restores Persona Profile records first, then Projects, threads,
messages, media assets/aliases, documents/images, links, and extension state.
v4 subsequently restores the five UMS families through its canonical
preflight/executor path in a transaction.

There is a direct v4 contradiction: the v4 exporter writes
`compatibility.restore_mode = "unsupported"` and `restore_supported = false`,
while `SUPPORTED_SCHEMA_VERSIONS`, `_restore_order_for_schema`, the UMS-04C
production proof, and UMS-04D round-trip proof show v4 restore is implemented
and exercised at earlier evaluated commits. The restore parser does not use
that compatibility flag as its admission gate. Correcting this is a contract
and artifact-version decision; this task leaves both v3 and v4 untouched.
The current export unit test `test_explicit_v4_serializes_exact_canonical_graph_and_manifest`
asserts those unsupported flags, while the separate restore dispatch and
historical round-trip tests exercise v4 consumption. The test preserves the
manifest assertion; it does not establish that the restore implementation
rejects v4.

The v3 manifest note also says Project ownership is not stored directly and
that Projects are exported by reachability. Current export SQL selects
`projects.user_id`, `guardian/core/pgdb.py` requires that column, and ADR-081
names it the sole ownership authority. The v3 note is stale; the exporter
implementation has already converged on the direct owner column.

### Conversation lifecycle

ADR-076 governs Projects, not conversations. Conversation rows currently have
`archived_at` only. `archive_thread` sets it and `unarchive_thread` clears it;
there is no durable account retention policy, expiry timestamp, or archived
conversation settings surface found in the inspected path.

The ordinary thread DELETE route hard-deletes an active or archived thread.
The Postgres `PgDB.delete_thread` ignores `force`; the ORM fallback requires
archive unless `force=true`. The route's error text claims archive is required,
but the production Postgres path does not enforce that. The sidebar exposes
archive and direct delete operations, and archiving removes the thread from the
active sidebar projection. No Settings → Archived Conversations surface was
found in the inspected frontend.

The persistence graph has important deletion dependencies. Messages and many
thread-owned rows use cascade behavior. `memory_provenance.source_thread_id`
uses `ON DELETE RESTRICT`, so a thread with provenance can block hard delete.
`ChatThread.parent_id` has no delete action, so a parent with child threads
also needs an explicit policy. Deleting database rows alone does not prove
external media bytes or derived indexes have been removed. Account deletion
currently cascades `chat_threads` from the `users` row, which can encounter the
same dependency constraints. These are code-path observations, not a complete
production dependency inventory.

The current thread-delete route emits `thread.deleted` after the database call,
but the repository search found no active `thread.deleted` consumer. The
Postgres delete method does not invoke storage deletion; the only nearby
`delete_file` call found is for import staging. Therefore there is no inspected
proof that hard-deleting a conversation removes external media bytes or
invalidates derived indexes. Treat those cleanup surfaces as unqualified until
an explicit dependency inventory and readback proof exist.

## Decision 1: meaning of “portable”

**Recommendation for review:** define two independently versioned products:

1. **Full-account recovery** is Codexify-to-Codexify, preserves canonical
   ownership, configuration, provenance, relationships, and supported
   application state, and is judged by metadata plus required binary
   round-trip equivalence.
2. **Portable interchange** is an optional application-neutral export for
   consumer implementations. It uses UTF-8 JSON or NDJSON, explicit stable
   identifiers, ISO-8601 timestamps, explicit typed relationships, content
   hashes, and self-contained attachment assets. A small neutral vocabulary
   should cover accounts/owners, collections/projects, conversations,
   ordered messages, attachments, provenance, and lifecycle state. Codexify
   fields outside that vocabulary remain under a namespaced extension object;
   unknown extensions are preserved as opaque data and never grant authority.

This avoids making recovery lossy to satisfy cross-application simplicity.
Full-account recovery retains Codexify-specific runtime configuration,
Persona/UMS semantics, Hosted Room state when approved, and exact internal
relationships; interchange intentionally does not promise those semantics.
Neither format depends on R2 or provider-specific locators.

Alternatives for the human decision:

- **One Codexify recovery artifact only:** smallest scope and strongest fidelity;
  call it portable only between compatible Codexify readers. Defer neutral
  interchange until a concrete consumer exists.
- **Recovery plus interchange (recommended):** clearer guarantees and clean
  future migration boundary, at the cost of two schemas and test matrices.
- **One artifact for both:** rejected in this proposal because its stable
  neutral contract would either leak Codexify internals or silently omit
  recovery semantics.

## Decision 2: conversation archive, retention, and deletion

**Recommended server-side model, pending approval:**

- Active conversations cannot be permanently deleted from ordinary chat
  surfaces. DELETE fails closed unless the conversation is archived and the
  caller is using the account's permanent-delete workflow.
- Keep `chat_threads.archived_at` as the reversible staging marker. Add a
  durable account-scoped retention setting with `Never` represented explicitly
  (for example, a nullable day count in an account settings row; do not reuse
  the memory-mode value). Default is Never.
- Add nullable `chat_threads.purge_eligible_at`. On archive, set it from the
  then-current policy; Never means NULL. Changing account retention recomputes
  deadlines for already archived threads from each original `archived_at`, in
  one transaction. This makes policy changes apply to existing archives and
  makes the behavior auditable. Restoring before expiry clears both archive and
  purge timestamps atomically. A re-archive establishes a new archive time and
  deadline.
- A server-side expiry worker claims only due, account-owned archived rows,
  uses idempotent transaction/outbox boundaries, and does not infer success
  from enqueue or object deletion alone. User-initiated permanent deletion uses
  the same dependency path through Settings → Archived Conversations.
- Account deletion overrides the conversation retention preference and
  schedules all account conversations and dependent data for the governed
  deletion path. Export/backup retention remains a separate policy.

Permanent deletion must account for messages, child threads, thread/project
links, document and media metadata, object bytes, UMS provenance, and derived
indexes. Postgres remains authority. External-byte and index cleanup should be
idempotent, retryable, and reference-aware; completion should be reported only
when the defined deletion scope is satisfied. This follows ADR-099's boundary:
object storage is bytes only, and object existence or locator does not grant
ownership.

**Human decision still required:** choose what happens to canonical memory
records derived from a deleted conversation. Recommended default is to retain
only separately accepted memory records while severing all thread/message
source references and removing conversation content from provenance; otherwise
delete dependent records. ADR-084's ordinary memory erasure rules do not
automatically settle this conversation-delete case. Also decide whether parent
deletion is blocked until child conversations are handled, or detaches children
while retaining a non-content lineage marker.

## Version recommendation and implementation sequence

Do not mutate v3 or v4 in place. Recommend a new recovery schema version for
the next format that adds missing canonical families, resolves field-level
profile privacy, specifies omission accounting, fixes manifest integrity,
states restore capability accurately, and writes bundled binaries back with
semantic equivalence checks. If neutral interchange is approved, version and
qualify it separately. The exact version token is intentionally pending the
decision on product boundaries.

Bounded sequence after human decisions:

1. Accept the portable-product boundary and the memory/child deletion rules;
   update the normative account export contract and add an accepted
   conversation-lifecycle ADR (allocate its number from the live ADR index).
2. Inventory all account-owned canonical export families and storage
   dependencies; freeze versioned family/field allowlists, sensitive fields,
   omission reasons, compatibility behavior, and integrity encoding.
3. Implement retention schema/service/API and Settings → Archived Conversations
   UI; prove active-delete rejection, archive/restore boundaries, policy change
   behavior, expiry races, retry/idempotency, and account-scope isolation.
4. Implement the selected export schema and binary restore path; prove clean
   account round-trip for every canonical family and required blob, second
   restore idempotency, corruption rejection, and truthful route/manifest
   compatibility.
5. Qualify object-byte and derived-index deletion, account deletion, export
   retention separation, and current supported runtime behavior. Do not infer
   release qualification from focused tests or documentation.

## Validation boundary

This is a read-only architecture reconciliation. No source, schema, runtime,
or R2 changes were made. A focused pytest invocation was attempted for the v4
dispatch test but collection stopped because the active Python environment
lacks `fastapi`; the repository's normal dependency environment was not
available in this checkout. The v4 conflict above is supported by current
source inspection and historical proof receipts, not by a successful test run
at this exact tip.
