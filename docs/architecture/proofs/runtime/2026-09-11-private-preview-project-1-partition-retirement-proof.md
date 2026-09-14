# Private Preview Project 1 partition and retirement proof

Date: 2026-09-11. Execution lane: architecture-impact. Evidence: isolated restored-copy repair rehearsal and live PostgreSQL transaction/readback. Operator authorization: Resonant Jones, the explicit Project 1 partition/retirement task.

## Authority and scope

ADR-076, ADR-081, and ADR-085 govern canonical ownership, partition, and the narrow obsolete shared-source retirement exception. Project ownership remains `projects.user_id`; thread routing authority is `chat_threads.user_id`. Historical local/general Project 1 was created 2026-07-30 12:21:59.367966+00, remained unarchived, and held threads owned by three canonical accounts. No single-owner reassignment was permissible.

The latest explicit task separates repair from Alembic and prohibits all migration execution. Accordingly, ADR-085's broader normal-migration-traversal rehearsal gate was **not exercised**. This proof establishes partition and retirement only; it does not establish full migration qualification or service readiness. No ADR or current-state document was changed.

## Initial repository and operational boundary

Host: VaultNode.local. Repository: `/Volumes/Dev_SSD/Codexify-main`, local main. Start HEAD: `e85be2dfa80e1d5d8a4e11efca944e810e87768e`.

The initial staged paths, preserved without modification, are:

- `docs/DEV_LOG/2026-09-10/Dev Log - 2026-09-10.md` (deletion)
- `docs/DEV_LOG/2026-09-11/Dev Log - 2026-09-11.md` (deletion)

Initial cached binary-patch SHA-256: `4e96d8c7155e327f03f15d311ddfbf03c32dc2d86129e184b4f7a6bb29b7560e`.

Live target: Compose project `codexify_private_preview`, service `db`, container `codexify_private_preview-db-1`, database `Codexify`, volume `codexify_private_preview_pg_data`, PostgreSQL 15. Pre/post Alembic revision: `d4e0f2a5b7c9` (unchanged).

The existing GUI reconciler `gui/501/com.resonant.codexify-private-preview` was unloaded and the desired-up marker preserved outside the repository. All Compose services except PostgreSQL were stopped using the canonical two-file Private Preview configuration. Only the database remained running; no other database sessions were present at precondition verification. No application startup was attempted. The maintenance boundary remains in place.

## Preservation and restore

External recovery directory: `/Volumes/Dev_SSD/Codexify-preservation/project-1-retirement-20260911T101719Z`.

Native `pg_dump --format=custom --no-owner --no-acl -U codexify -d Codexify` produced `private-preview-source.dump` there. Size: 3,339,768 bytes. SHA-256: `9fa50f7a00d4e6ac178144f2d9a862c95806add5195f5d19ce46d850e2a02098`. The dump was made read-only (0400), successfully listed with `pg_restore --list`, and restored with `pg_restore --exit-on-error --no-owner --no-acl`.

Rehearsal database: `CodexifyProject1Rehearsal`; container: `codexify-project1-rehearsal-20260911t101719z`; separate volume: `codexify_project1_rehearsal_20260911t101719z`. Isolation: `--network none`, no published ports, separate storage, same existing PostgreSQL image ID `sha256:3b0d656f5fff31c7d8a64f500a703dcf3f35e98ce78f602831a73059a5e6a012`, `--pull never`. No data was sent remotely.

All 114 tables / 5,599 rows matched source-to-restore by full-row count and SHA-256, including the migration ledger. Raw catalog equality initially failed during read-only planning: native restore changes CHECK-expression rendering and removes a dropped-column ordinal gap in an unrelated table. Named columns, non-CHECK constraints, indexes, and triggers were separately compared. Distinct raw fingerprints were retained and guarded without schema normalization: source `f166ac6ee76c59ca256a2ccd9272148a22b440d31b1b0288828a5ddbc727b3f3`; restore `9fbf614203774429673d421a13de995968406164ecc0e8907d8e46c1cd36b7d5`. This is not a claim of full migration/schema qualification. Both actual repair transactions subsequently passed.

## Frozen deterministic partition

No affected account had an existing General. ADR-081's separately authorized creation rule and ADR-085 permit exactly one replacement General for each affected account in this partition. Three replacements were created with legitimate canonical ownership before moving rows, within the same transaction. No replacement owner or role was rewritten. The old global name uniqueness constraint required deterministic distinct names: `General [Project 1 repair <SHA-256 of canonical account ID>]`. Names grant no authority; later normalization is deferred. Sequence precondition was `[5, true]`, yielding IDs 6, 7, 8.

| Canonical account ID | Replacement Project ID | Thread IDs |
| --- | --- | --- |
| jones@resonantconstructs.ai | 6 | 3, 4, 5, 71, 72 |
| kristaearthmage@yahoo.com | 7 | 70 |
| maatariki@resonantconstructs.ai | 8 | 1, 69 |

Catalog discovery found 15 FK columns to Projects and 15 additional modeled Project reference columns. Each actual row was classified; empty fields have no row to classify. Eight thread rows were THREAD_OWNED_DETERMINISTIC. Four eval snapshots and 16 event-graph rows were DERIVED_FROM_DETERMINISTIC_PARENT through durable thread IDs. Event actors were corroborating metadata only. No account-only, safe-to-retire dependency, or ambiguous row was found. Required non-thread dependencies: 20; total relocated references including threads: 28. Messages remain linked by unchanged thread IDs.

| Reference | FK | Before | After | Classification |
| --- | --- | ---: | ---: | --- |
| `agent_extension_install_bindings.project_id` | false | 0 | 0 | No referencing rows |
| `agent_extension_proposals.project_id` | false | 0 | 0 | No referencing rows |
| `agent_extension_registry_entries.project_id` | false | 0 | 0 | No referencing rows |
| `chat_threads.project_id` | true | 8 | 0 | THREAD_OWNED_DETERMINISTIC |
| `continuity_context_packets.project_id` | false | 0 | 0 | No referencing rows |
| `continuity_reality_commits.project_id` | false | 0 | 0 | No referencing rows |
| `continuity_reality_states.project_id` | false | 0 | 0 | No referencing rows |
| `delegation_jobs.project_id` | false | 0 | 0 | No referencing rows |
| `delegation_packets.project_id` | false | 0 | 0 | No referencing rows |
| `direct_message_conversation_placements.project_id` | true | 0 | 0 | No referencing rows |
| `direct_message_conversations.origin_project_id` | true | 0 | 0 | No referencing rows |
| `eval_trace_snapshots.project_id` | true | 4 | 0 | DERIVED_FROM_DETERMINISTIC_PARENT |
| `event_graph_events.project_id` | false | 16 | 0 | DERIVED_FROM_DETERMINISTIC_PARENT |
| `generated_documents.project_id` | true | 0 | 0 | No referencing rows |
| `generated_images.project_id` | true | 0 | 0 | No referencing rows |
| `guardian_delegation_intents.project_id` | true | 0 | 0 | No referencing rows |
| `imprint_fold_states.project_id` | false | 0 | 0 | No referencing rows |
| `imprint_observations.project_id` | false | 0 | 0 | No referencing rows |
| `imprints.project_id` | false | 0 | 0 | No referencing rows |
| `media_assets.project_id` | true | 0 | 0 | No referencing rows |
| `personas.project_id` | false | 0 | 0 | No referencing rows |
| `project_document_links.project_id` | true | 0 | 0 | No referencing rows |
| `repository_bindings.project_id` | true | 0 | 0 | No referencing rows |
| `system_doc_links.project_id` | false | 0 | 0 | No referencing rows |
| `system_docs.project_id` | false | 0 | 0 | No referencing rows |
| `thread_moves.from_project_id` | true | 0 | 0 | No referencing rows |
| `thread_moves.to_project_id` | true | 0 | 0 | No referencing rows |
| `tts_outputs.project_id` | true | 0 | 0 | No referencing rows |
| `uploaded_documents.project_id` | true | 0 | 0 | No referencing rows |
| `uploaded_images.project_id` | true | 0 | 0 | No referencing rows |

The external `partition-plan.json` freezes every affected row ID, authority, target, expected count, and preservation digest. SHA-256: `afc379418697af3013e2a35ae6cf1c0fe8af6aaac688a867f3c12d729c7494f9`. The identical read-only frozen `repair.sql` was applied first to rehearsal and then live. SHA-256: `7051f5d357be833b8d73261bb03df8f4a07cc4696a55cb7bafbe29bad33ae1e2`.

## Transaction and integrity evidence

Both executions used one explicit SERIALIZABLE transaction, SHARE ROW EXCLUSIVE locks across all 114 tables, a five-second lock timeout, a 120-second statement timeout, and ON_ERROR_STOP. Guards required the exact source table digests, schema fingerprint, sequence state, source identity, every moved row ID/owner/parent, and exact destination IDs. Live source manifests were independently rechecked immediately before execution and matched all 114 tables exactly. Writers remained stopped.

Each transaction created three valid replacements, updated only `project_id` on eight threads, four snapshots, and 16 event rows, checked preservation, dynamically recensused every Project reference, and required zero references before deleting source Project 1. The source full-row hash was unchanged immediately before deletion; no archive, owner, or role laundering occurred. No canonical account-owned built-in was retired. Both logs record `pre_retirement_reference_census=0; preservation=PASS`, then `retirement_and_integrity_checks=PASS`, and COMMIT with exit zero.

Independent read-only post-commit verification passed on both databases: 117 preservation assertions, 30 zero-reference columns, zero FK orphans, exact eight-thread destination mapping, and Project 1 count zero. Hashes of all non-Project fields on the three relocated tables remained identical. All unrelated rows in those tables and all other tables were hashed in full; original Projects 2, 3, and 4 remained identical. Historical event payloads and provenance were preserved.

| Measure | Before | After |
| --- | ---: | ---: |
| All tables | 114 | 114 |
| All rows | 5,599 | 5,601 |
| Projects | 4 | 6 |
| All threads | 72 | 72 |
| All messages | 805 | 805 |
| Affected threads | 8 | 8 |
| Affected messages | 20 | 20 |
| References to source 1 | 28 | 0 |
| Source Project 1 rows | 1 | 0 |

Digests were computed inside PostgreSQL over newline-separated full JSON rows sorted under C collation, retaining duplicate rows; only counts/digests and bounded IDs leave the database. For relocated rows, only `project_id` was excluded from preservation digests. Newly created Project timestamps can differ between rehearsal and live; their IDs, canonical owners, roles, and deterministic names match.

External evidence retained alongside the dump: `archive.list`, `source-census.json`, `restored-manifest.json`, `partition-plan.json`, `repair.sql`, `all-table-manifest.sql`, `schema-manifest.sql`, `orphan-census.sql`, `rehearsal-transaction.log`, `rehearsal-proof.json`, `live-preconditions.json`, `live-transaction.log`, `live-proof.json`, and `desired-up-marker.before`.

## Validation and closeout boundary

Repository validation: `python3 scripts/validate_docs.py`, `.venv/bin/python scripts/validate_docs.py`, and `git diff --check` all passed. The proof was also checked explicitly with `git diff --no-index --check /dev/null <proof-path>` before staging. No automated runtime tests apply: application code was not changed. Database checks above are live persistence proof, independent of documentation validation.

Only this new proof is authorized for commit. Existing staged Dev Log deletions remain excluded. No push or merge is authorized or performed.

Chroma mutations, provider requests/invocations, live executor calls, OAuth logins, manual token refreshes, runtime source edits, automated runtime tests, and Private Preview startup attempts: all zero. Alembic was not resumed. PostgreSQL remains available and application writers remain quiesced.

Next recommended task: **Resume canonical Alembic after Project 1 retirement**, architecture-impact lane. The shared Project 1 blocker is removed; migration completion, General-name normalization, and subsequent Private Preview startup remain unproven and are not begun here. No release claim advances.
