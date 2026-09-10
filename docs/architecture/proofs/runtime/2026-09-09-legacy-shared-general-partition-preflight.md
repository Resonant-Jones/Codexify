# Legacy Shared General Project `1` — Account Partition Preflight

## Result

```text
LEGACY_SHARED_GENERAL_PARTITION: BLOCKED_ON_PROJECT_1_OWNER
```

The live private-preview database confirms a deterministic thread-level partition, but it does not contain durable evidence that allows Project `1` itself to be assigned to exactly one account. Project `1` is therefore not selected as any account's General in this proof.

| Account identifier (`chat_threads.user_id`) | Thread IDs | Threads | Existing account-owned General | Target classification |
| --- | --- | ---: | --- | --- |
| `jones@resonantconstructs.ai` | `3, 4, 5, 71, 72` | 5 | none | new General required |
| `maatariki@resonantconstructs.ai` | `1, 69` | 2 | none | new General required |
| `kristaearthmage@yahoo.com` | `70` | 1 | none | new General required |

No Project, thread, message, or dependency row was changed. No General Project was created. No migration was executed or stamped.

## Scope and authority

- Evidence date: `2026-09-10`.
- Authorized artifact: this file only.
- Execution lane: architecture-impact, read-only data-repair preflight.
- Database authority: PostgreSQL private-preview database; Postgres is canonical and Chroma is out of scope.
- Governing decisions: ADR-076 (`general` is a durable built-in Project role, unique per owning user) and ADR-081 (`projects.user_id` is the sole canonical Project ownership authority; ambiguous legacy `local` ownership fails closed). ADR-084 makes canonical Project authority a prerequisite for Project-scoped memory.
- Evidence classes: repository and migration facts are `proven-code-path` or `documented-contract`; database observations below are time-bounded `proven-live-runtime` read-only observations. They do not qualify the private-preview application or release readiness.
- Content boundary: no message body, document body, description text, prompt, trace payload, or credential was read into this packet. Only bounded structural identifiers, ownership fields, lifecycle fields, timestamps, counts, and lineage metadata are recorded.

## Repository and migration state

| Check | Result |
| --- | --- |
| Repository root | `/Volumes/Dev_SSD/Codexify-main` |
| Branch | `main` |
| Repository HEAD | `e77b84cf9edfa28494e576d8e88332e0b2074177` |
| Static Alembic head | `f6b0d3e8c5a2` (`.venv/bin/python -m alembic -c backend/alembic.ini heads`) |
| Target database container | `codexify_private_preview-db-1` (`postgres:15`, healthy) |
| Target database | `Codexify` |
| Target database Alembic revision | `d4e0f2a5b7c9` |
| Revision status | matches the incident checkpoint; database has not advanced during this proof |

Initial repository state was inspected before the artifact was created:

```text
git status --short
D  docs/DEV_LOG/2026-09-10/Dev Log - 2026-09-10.md
```

The Dev Log deletion was pre-existing, staged, unrelated work. It was not edited, unstaged, staged for this task, or included in this task's commit.

## Read-only database posture

The target connection was established with PostgreSQL transaction-level read-only protection:

```sql
BEGIN TRANSACTION READ ONLY;
SELECT current_setting('transaction_read_only');
SELECT current_database();
SELECT version_num FROM alembic_version;
ROLLBACK;
```

Observed session evidence:

```text
transaction_read_only = on
database              = Codexify
alembic_revision      = d4e0f2a5b7c9
```

All data-inspection queries in this packet used the same `BEGIN TRANSACTION READ ONLY` / `ROLLBACK` posture. The only Alembic command run was the static `heads` query shown above. No `upgrade`, `stamp`, direct version-table edit, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, or `CREATE` was issued. Chroma was not accessed.

## Project `1` structural record

| id | user_id | name | system_role | archived_at | created_at | updated_at |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `local` | `General` | `general` | `NULL` | `2026-07-30 12:21:59.367966+00` | `2026-07-30 12:21:59.367966+00` |

Required confirmation:

```text
project_id = 1
system_role = general
```

Project `1` is a built-in General by structural role, not by display name. Its persisted owner is the legacy `local` value. The built-in role is not a global cross-account container, and ADR-076 does not permit archiving or deleting it as a shortcut.

## Account-owned General inventory

The live query over every row with `system_role = 'general'` returned exactly one row:

| Project ID | `user_id` | Name | Role | Lifecycle |
| ---: | --- | --- | --- | --- |
| 1 | `local` | `General` | `general` | active (`archived_at = NULL`) |

The database also exposes the account-scoped partial unique index `uq_projects_user_id_system_role` over `(user_id, system_role)` for non-null roles. Among the three non-local thread owners from Project `1`:

| Account | Account-owned General count | Classification |
| --- | ---: | --- |
| `jones@resonantconstructs.ai` | 0 | missing General; new General required |
| `maatariki@resonantconstructs.ai` | 0 | missing General; new General required |
| `kristaearthmage@yahoo.com` | 0 | missing General; new General required |

There is no duplicate General condition for any affected account. The only existing General is the legacy `local` row and is not treated as an account-owned General for any of the three affected accounts.

## Exact Project `1` thread partition

The eight canonical thread rows were captured without titles, summaries, or message content:

| Thread ID | Canonical thread owner | Project ID | Archived | Created at | Updated at |
| ---: | --- | ---: | --- | --- | --- |
| 1 | `maatariki@resonantconstructs.ai` | 1 | `NULL` | `2026-09-02 10:30:22.242755+00` | `2026-09-02 10:31:15.658331+00` |
| 3 | `jones@resonantconstructs.ai` | 1 | `NULL` | `2026-09-02 12:26:28.399608+00` | `2026-09-02 12:26:34.554294+00` |
| 4 | `jones@resonantconstructs.ai` | 1 | `NULL` | `2026-09-02 12:37:09.133213+00` | `2026-09-02 12:37:13.050810+00` |
| 5 | `jones@resonantconstructs.ai` | 1 | `NULL` | `2026-09-02 12:45:02.860029+00` | `2026-09-02 12:45:26.033002+00` |
| 69 | `maatariki@resonantconstructs.ai` | 1 | `NULL` | `2026-09-04 01:48:25.247524+00` | `2026-09-04 01:48:31.555143+00` |
| 70 | `kristaearthmage@yahoo.com` | 1 | `NULL` | `2026-09-04 12:18:06.656016+00` | `2026-09-04 12:18:11.464137+00` |
| 71 | `jones@resonantconstructs.ai` | 1 | `NULL` | `2026-09-04 12:56:20.465941+00` | `2026-09-05 10:14:43.603328+00` |
| 72 | `jones@resonantconstructs.ai` | 1 | `NULL` | `2026-09-04 12:56:50.529952+00` | `2026-09-04 16:05:02.795715+00` |

Aggregate checks:

```text
total threads                 = 8
distinct thread IDs           = 8
distinct canonical owners     = 3
local-owned threads           = 0
threads with project_id NULL  = 0
owner distribution             = Jones 5 / Maatariki 2 / Krista 1
```

There are 20 `chat_messages` rows under these threads. The bounded `chat_messages.user_id` check found zero message-owner mismatches with the owning thread. Message content was not selected.

## Direct Project dependency inventory

The following list was derived from the live PostgreSQL catalog by joining `information_schema.table_constraints`, `key_column_usage`, `referential_constraints`, and `constraint_column_usage` for foreign keys referencing `public.projects(id)`. It found 15 direct foreign-key columns.

| Table | FK column | Delete rule | Rows referencing Project `1` | Owner/lineage fields observed | Classification and repair posture |
| --- | --- | --- | ---: | --- | --- |
| `chat_threads` | `project_id` | NO ACTION | 8 | `user_id` | owner-specific; Project-level owner is ambiguous because the eight rows have three owners; each thread needs a future target Project remap, while `user_id` is immutable |
| `direct_message_conversation_placements` | `project_id` | SET NULL | 0 | `profile_id` | participant-local placement; no Project `1` rows |
| `direct_message_conversations` | `origin_project_id` | SET NULL | 0 | `origin_thread_id`, `created_by_profile_id` | origin metadata, not Project membership or owner authority; no Project `1` rows |
| `eval_trace_snapshots` | `project_id` | SET NULL | 4 | `thread_id`; no owner column | thread-inherited derived snapshot with a direct Project reference; stable thread lineage remains, but the four direct Project references require conditional remap if their threads move |
| `generated_documents` | `project_id` | CASCADE | 0 | `user_id`, `thread_id` | owner-specific/thread-linked; no Project `1` rows |
| `generated_images` | `project_id` | CASCADE | 0 | `user_id`, `thread_id` | owner-specific/thread-linked; no Project `1` rows |
| `guardian_delegation_intents` | `project_id` | SET NULL | 0 | `thread_id` | thread-inherited; no Project `1` rows |
| `media_assets` | `project_id` | CASCADE | 0 | nullable `user_id`, `thread_id`, `source_thread_id` | owner-specific/thread-linked; no Project `1` rows |
| `project_document_links` | `project_id` | CASCADE | 0 | nullable `attached_by` | Project-only link; `attached_by` is actor metadata, not Project ownership evidence; no Project `1` rows |
| `repository_bindings` | `project_id` | CASCADE | 0 | no account/owner field | Project-owned binding state; no Project `1` rows |
| `thread_moves` | `from_project_id` | SET NULL | 0 | `thread_id`, `user_id` | ownership-neutral audit/history row; no Project `1` rows |
| `thread_moves` | `to_project_id` | SET NULL | 0 | `thread_id`, `user_id` | ownership-neutral audit/history row; no Project `1` rows |
| `tts_outputs` | `project_id` | CASCADE | 0 | nullable `user_id`, `thread_id` | owner-specific/thread-linked; no Project `1` rows |
| `uploaded_documents` | `project_id` | CASCADE | 0 | `user_id`, `thread_id` | owner-specific/thread-linked; no Project `1` rows |
| `uploaded_images` | `project_id` | CASCADE | 0 | `user_id`, `thread_id` | owner-specific/thread-linked; no Project `1` rows |

Only the eight canonical threads and four evaluation snapshots have direct Project `1` foreign-key rows. No direct document, media, repository, delegation, messaging-placement, move, or TTS row references Project `1`.

### Non-FK Project-shaped columns

As a guard against schema references that have not been declared as foreign keys, the live catalog was also queried for every public column whose name contains `project`. Thirty Project-shaped columns were found: the 15 FK columns above plus the following 15 non-FK columns. Counts use the exact integer value `1`, or the text value `'1'` for the opaque continuity columns.

| Table.column | Rows with value `1` | Other bounded owner/thread fields | Classification |
| --- | ---: | --- | --- |
| `agent_extension_install_bindings.project_id` | 0 | `account_id`, `profile_id`, `source_thread_id` | account-specific/source-thread metadata; no rows |
| `agent_extension_proposals.project_id` | 0 | `account_id`, `profile_id`, `source_thread_id` | account-specific/source-thread metadata; no rows |
| `agent_extension_registry_entries.project_id` | 0 | `account_id`, `profile_id`, `source_thread_id` | account-specific/source-thread metadata; no rows |
| `continuity_context_packets.project_id` | 0 | `user_id`, `thread_id`; opaque varchar Project field | account/thread-scoped continuity metadata; no rows with value `'1'`; not proven to reference `projects.id` |
| `continuity_reality_commits.project_id` | 0 | `user_id`, `thread_id`; opaque varchar Project field | account/thread-scoped continuity metadata; no rows with value `'1'`; not proven to reference `projects.id` |
| `continuity_reality_states.project_id` | 0 | `user_id`, `thread_id`; opaque varchar Project field | account/thread-scoped continuity metadata; no rows with value `'1'`; not proven to reference `projects.id` |
| `delegation_jobs.project_id` | 0 | `thread_id` | thread-linked delegation metadata; no rows |
| `delegation_packets.project_id` | 0 | `thread_id` | thread-linked delegation metadata; no rows |
| `event_graph_events.project_id` | 16 | `actor_user_id`, `thread_id` | ownership-neutral audit/lineage; all rows are thread-linked and actor-matching, but the non-FK Project field needs future partition treatment if historical Project context must follow a moved thread |
| `imprint_fold_states.project_id` | 0 | `user_id` | account-specific presentation state; no rows |
| `imprint_observations.project_id` | 0 | `user_id` | account-specific observation state; no rows |
| `imprints.project_id` | 0 | `user_id` | account-specific relational state; no rows |
| `personas.project_id` | 0 | `user_id` | account-specific Persona state; no rows |
| `system_doc_links.project_id` | 0 | `user_id` | account-specific Project/document link; no rows |
| `system_docs.project_id` | 0 | `owner_user_id` | owner-specific system-document state; no rows |

The non-FK scan therefore adds one non-zero surface: 16 event-graph rows. It does not add a second canonical owner for Project `1`.

### Non-zero direct and Project-shaped rows

The four direct `eval_trace_snapshots` rows are bounded as follows:

| Trace snapshot ID | Thread ID | Thread owner | Project ID | User message ID | Assistant message ID |
| --- | ---: | --- | ---: | ---: | ---: |
| `1402cd1c-01a4-4988-9f62-3a62e1bca83c` | 72 | `jones@resonantconstructs.ai` | 1 | 802 | 803 |
| `1d9a3d4a-0b01-4405-bdeb-60497b58c55a` | 72 | `jones@resonantconstructs.ai` | 1 | 800 | 801 |
| `363ef62e-ec83-4386-850c-bc5452732ea0` | 5 | `jones@resonantconstructs.ai` | 1 | 7 | 8 |
| `a106ed6e-6f95-4e68-a640-efb4621cda28` | 72 | `jones@resonantconstructs.ai` | 1 | 796 | 797 |

The repository path that builds these snapshots takes `project_id` from the thread record (`guardian/evals/spine.py`, `build_trace_snapshot`). The table has no independent owner column. These rows are therefore derived, thread-inherited evidence, not authority that can select Jones as Project owner.

The 16 non-FK `event_graph_events` rows are all `thread.update` records. They cover all eight Project `1` threads; all 16 have a non-null `thread_id` and all 16 `actor_user_id` values match the corresponding canonical thread owner:

| Thread owner | Thread IDs | Event rows |
| --- | --- | ---: |
| `jones@resonantconstructs.ai` | 3, 4, 5, 71, 72 | 11 |
| `maatariki@resonantconstructs.ai` | 1, 69 | 4 |
| `kristaearthmage@yahoo.com` | 70 | 1 |

Event-graph rows are audit/lineage state. Actor identity is not Project ownership authority, and no event payload was read.

## Indirect thread-linked containment

The live catalog found 17 foreign-key columns referencing `chat_threads(id)`. Counts below are rows whose thread reference points to one of the eight Project `1` threads.

| Table | Thread FK column | Delete rule | Rows | Result if `chat_threads.project_id` changes |
| --- | --- | --- | ---: | --- |
| `agent_deployments` | `thread_id` | SET NULL | 0 | no rows |
| `agent_runs` | `thread_id` | SET NULL | 0 | no rows |
| `chat_messages` | `thread_id` | CASCADE | 20 | remains attached through stable thread identity; no message rewrite |
| `chat_threads` | `parent_id` | NO ACTION | 0 | no rows |
| `direct_message_conversations` | `origin_thread_id` | SET NULL | 0 | no rows |
| `eval_trace_snapshots` | `thread_id` | CASCADE | 4 | stable thread lineage remains; separate direct `project_id` refs are handled above |
| `eval_verdicts` | `thread_id` | CASCADE | 0 | no rows |
| `generated_documents` | `thread_id` | CASCADE | 0 | no rows |
| `generated_images` | `thread_id` | CASCADE | 0 | no rows |
| `guardian_delegation_intents` | `thread_id` | CASCADE | 0 | no rows |
| `hosted_rooms` | `backing_thread_id` | CASCADE | 0 | no rows |
| `media_assets` | `thread_id` | CASCADE | 0 | no rows |
| `thread_documents` | `thread_id` | CASCADE | 0 | no rows |
| `thread_moves` | `thread_id` | CASCADE | 0 | no rows |
| `tts_outputs` | `thread_id` | CASCADE | 0 | no rows |
| `uploaded_documents` | `thread_id` | CASCADE | 0 | no rows |
| `uploaded_images` | `thread_id` | CASCADE | 0 | no rows |

The 20 messages and four evaluation snapshots remain related to their source threads by stable thread ID. No indirect thread-linked row needs a rewrite merely because a thread's Project is changed. The four evaluation snapshots also carry a direct Project FK and therefore cannot be treated as purely indirect for a future partition.

## Project `1` owner-evidence analysis

| Candidate evidence | Observed result | Authority outcome |
| --- | --- | --- |
| `projects.user_id` | `local` | legacy owner value; does not identify one of the three non-local account owners |
| Canonical thread owners | three distinct owners, distribution 5 / 2 / 1 | ADR-081's exact single-owner reconciliation rule fails closed |
| Canonical message owners | all 20 match their thread owner | confirms thread/account preservation; does not collapse Project ownership |
| Evaluation snapshots | four derived rows, all inherited from Jones threads | not an independent Project owner authority |
| Event graph rows | 16 actor/thread-matching audit rows, no FK | audit lineage, not Project owner authority |
| Existing `system_role='general'` | only Project `1`, owned by `local` | role is structural and account-scoped; it is not global ownership evidence |
| Project display name `General` | present | presentation text is not ownership evidence |
| Majority account | Jones owns five threads | explicitly rejected by ADR-081 and this proof |
| Oldest/newest thread | timestamps are present | chronology alone is not an accepted owner rule |
| Current login, operator, machine, deployment account | not used | prohibited authority sources |

Therefore:

```text
PROJECT_1_OWNER_UNRESOLVED
```

No accepted durable relationship identifies exactly one account as the owner of Project `1`. Choosing Jones by majority, selecting an account by ID or chronology, or using the active operator would violate ADR-081.

## Proposed preservation mapping

This is the preservation mapping that is proven at the account/thread level; it is not an execution plan and does not authorize mutation.

| Current Project | Account | Thread IDs | Target General | Target exists? | Direct Project rows requiring future handling | Indirect thread-linked rows |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `jones@resonantconstructs.ai` | 3, 4, 5, 71, 72 | new account-owned General required; Project `1` not selected | no | 5 `chat_threads`; 4 `eval_trace_snapshots`; 11 non-FK event-graph references for review/remap policy | 15 messages; 4 eval thread links |
| 1 | `maatariki@resonantconstructs.ai` | 1, 69 | new account-owned General required; Project `1` not selected | no | 2 `chat_threads`; 4 non-FK event-graph references for review/remap policy | 4 messages |
| 1 | `kristaearthmage@yahoo.com` | 70 | new account-owned General required; Project `1` not selected | no | 1 `chat_threads`; 1 non-FK event-graph reference for review/remap policy | 1 message |

The target Project rows are intentionally not created here. A future repair must preserve every thread ID, thread owner, message ID/content relationship, account boundary, and General containment. It must also make an explicit decision for the four direct evaluation-snapshot Project references and the 16 non-FK event-graph Project references. Stable thread identity preserves their thread lineage; it does not silently rewrite direct or historical Project fields.

## Stop reason and deferred work

The account partition itself is complete and non-arbitrary. The complete Project ownership mapping is not complete because Project `1` has three canonical thread owners and only the legacy `local` Project owner. This is an ADR-081 ownership-authority blocker, not a missing thread or content row.

Deferred until a separately evidenced owner decision or reconciliation:

1. establish whether exactly one account may retain Project ID `1`;
2. create missing account-owned General Projects only under a separate repair authorization;
3. remap each thread's `project_id` without changing `user_id` or content;
4. handle the four direct evaluation-snapshot Project references;
5. define preservation/remap treatment for the 16 non-FK event-graph Project references; and
6. rehearse and separately qualify the repair before any database mutation.

No ADR change is required by this evidence. If future safe resolution would require a global/ownerless General, synthetic service owner, thread-owner rewrite, or weakened multi-owner fail-closed rule, stop and report:

```text
ADR CHANGE REQUIRED — LEGACY SHARED GENERAL PARTITION SEMANTICS
```

## Validation and closeout boundary

No runtime tests apply: this task authorizes no implementation, route, model, migration, or test-source change. The following documentation checks are run after authoring:

```bash
.venv/bin/python scripts/validate_docs.py
git diff --check
git status --short
git diff --name-only
git diff --cached --check
git diff --cached --name-status
```

The only task-owned changed path is:

```text
docs/architecture/proofs/runtime/2026-09-09-legacy-shared-general-partition-preflight.md
```

The pre-existing staged Dev Log deletion remains outside this task and is preserved without repair, restore, staging, or commit.

Observed results for this authoring pass:

- `.venv/bin/python scripts/validate_docs.py`: PASS (`required architecture docs, README links, and source headings verified`).
- `git diff --check`: PASS.
- `git status --short --branch --untracked-files=all`: PASS; before task staging, only the pre-existing staged Dev Log deletion and this proof artifact were reported.
- `git diff --name-only`: PASS; no unstaged tracked paths were reported.
- `git diff --cached --check`: PASS before task staging; no staged whitespace errors were reported.
- `git diff --cached --name-status`: PASS before task staging; only the pre-existing Dev Log deletion was in the index.

The final staged-scope checks are repeated after adding the task-owned proof path. The unrelated staged deletion is expected to remain in the index and is excluded from the commit with an explicit path-limited commit.
