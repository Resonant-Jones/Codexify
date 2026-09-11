# Private Preview legacy Persona Profile retirement proof

Date: 2026-09-11

Result: PASS

Execution lane: architecture-impact / EXECUTE
Authority: ADR-086, aligned with ADR-082 and ADR-084

## Scope and authority

This task qualified and retired the exact historical globally seeded, unbound
Persona Profile batch `profile-1`, `profile-2`, and `profile-3` under ADR-086.
No owner was inferred or assigned. No binding, Persona Subject, ownerless runtime
class, system-profile conversion, deletion API, runtime code, migration, model,
test, configuration, ADR, or current-state file was changed.

The operation used only the authorized quiesced Private Preview PostgreSQL
database and an isolated restored PostgreSQL copy. It did not invoke a provider,
external service, live executor, OAuth flow, token refresh, Chroma mutation,
application startup, or live Alembic upgrade.

## Orientation and Git boundary

- Host: `VaultNode.local`
- Repository: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `main`
- Start HEAD: `980b090203f109bfbccbcdccf34bdcc12bf984f1`
- Initial live Alembic revision: `d4e0f2a5b7c9`
- Initial staged paths, preserved as unrelated work:
  - `docs/DEV_LOG/2026-09-10/Dev Log - 2026-09-10.md` (staged deletion)
  - `docs/DEV_LOG/2026-09-11/Dev Log - 2026-09-11.md` (staged deletion)
- Initial staged binary patch SHA-256:
  `4e96d8c7155e327f03f15d311ddfbf03c32dc2d86129e184b4f7a6bb29b7560e`

Private Preview application writers were quiesced before qualification. The
database container alone remained healthy; backend, workers, frontend, and
origin were not started by this task. Project `1` was absent.

## Candidate provenance

The historical `b7c8` seed migration creates these exact three identifiers as
one global seed set. The live rows matched the migration's non-sensitive seed
projection exactly and shared the original unchanged `created_at` / `updated_at`
timestamp. Each row remained at current revision 1. The later `c3d9` migration
created one immutable revision per legacy profile and did not create an account
binding for these rows.

This is distinct from the current account-scoped persistence path, which creates
the profile registry row, immutable revision, and canonical
`PersonaProfileBinding.owner_account_id` binding together. ID or profile content
was not used as ownership evidence.

The candidate query returned exactly these three profiles and no additional
globally seeded unbound Persona Profile. The pre-retirement database contained
no other Persona Profile.

## Per-profile eligibility ledger

| Profile | Global seed | Bindings | Owner evidence | Thread/runtime refs | Owned revisions | Required dependencies | Unresolved dependencies | Eligible |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `profile-1` | true | 0 | 0 | 0 | 1 | 0 | 0 | true |
| `profile-2` | true | 0 | 0 | 0 | 1 | 0 | 0 | true |
| `profile-3` | true | 0 | 0 | 0 | 1 | 0 | 0 | true |

Canonical-owner inspection covered the binding table, durable account-scoped
creation evidence, durable control-plane/audit ownership evidence, and bounded
binding-bearing preservation/export evidence. The account-export path is
binding-scoped, so these unbound profiles are excluded; the restore path requires
canonical binding coverage and owner agreement. A bounded search found no local
binding-bearing archive for the candidates. Chronology, profile content,
Project ownership, operator identity, and ordinary usage were not treated as
owner evidence.

Thread/runtime inspection covered the compound active-profile revision foreign
key, `active_profile_id`, active revision state, profile-override metadata, and a
database-wide semantic scan of public text, JSON, array, and user-defined
columns. All candidate reference counts were zero.

## PostgreSQL FK dependency census

The census came from PostgreSQL catalogs at `d4e0f2a5b7c9`, not from a fixed
application table list. It found four constraints and zero triggers on the three
Persona Profile tables:

| Constraint | Referencing table | Delete action | Candidate rows | Classification |
| --- | --- | --- | ---: | --- |
| `fk_chat_threads_persona_profile_revision` | `chat_threads` | NO ACTION | 0 | external relation, no dependency |
| `fk_persona_profile_bindings_owner_account` | `persona_profile_bindings` | CASCADE from account | 0 | external relation, no dependency |
| `fk_persona_profile_bindings_profile` | `persona_profile_bindings` | CASCADE from profile | 0 | safe local state, empty |
| `fk_persona_profile_revisions_profile` | `persona_profile_revisions` | CASCADE from profile | 1 per candidate | `OWNED_PROFILE_REVISION`; safe profile-local cascade |

The owned revisions matched each registry row's current revision and manifest
identity, revision, and API version. No external row required any candidate
revision. Pre- and post-operation Persona FK orphan counts were zero.

## Semantic/application dependency census

| Surface | Result | Classification |
| --- | --- | --- |
| Thread selection and active revisions | 0 per candidate | no required dependency |
| Profile override metadata | 0 per candidate | no required dependency |
| Persona Subjects / subject bindings | schema absent at `d4e0f2a5b7c9` | not applicable at execution revision |
| Memory attribution and provenance | database-wide semantic matches: 0 | no required dependency |
| Audit/event records | database-wide semantic matches: 0 | no required dependency |
| Task/job payloads | database-wide semantic matches: 0 | no required dependency |
| Document/Codex provenance | database-wide semantic matches: 0 | no required dependency |
| Persisted system-profile references | database-wide semantic matches: 0 | no required dependency |
| Account export/restore | binding-scoped; candidates absent | no required dependency |
| Candidate revision rows | 1 per candidate | historical non-blocking evidence and safe local cascade |

The semantic scan found zero candidate identifiers outside the candidate-owned
profile and revision rows. Required dependency count and unresolved dependency
count were therefore zero for each candidate. The all-or-nothing batch gate
passed before any mutation.

## Preservation boundary

The earlier post-Project-1 artifact was preserved unchanged:

- Path: `/Volumes/Dev_SSD/Codexify-preservation/post-project1-alembic-20260911T123821Z/private-preview-post-project1-pre-migration.dump`
- SHA-256: `c1a83bab43095667eaf0ef43e38aa52460dabb9d230dfb10f3b03b612ffce664`
- Size: 3,339,449 bytes

After eligibility was frozen and immediately before rehearsal/live mutation, a
fresh complete custom-format dump was created outside the repository:

- Path: `/Volumes/Dev_SSD/Codexify-preservation/persona-retirement-20260911T145217Z/private-preview-pre-persona-retirement.dump`
- SHA-256: `faae285a09293716f5252ff84e3c8ada02e79c0a2376d5f5ee78d57708f4cacc`
- Size: 3,339,449 bytes
- Mode: `0400`
- `pg_restore --list`: PASS

This is the authoritative rollback source for the retirement.

## Restored-copy rehearsal

The fresh pre-retirement dump was restored into a new PostgreSQL container with
a separate volume, no external network, and no published ports. The restored
copy began at `d4e0f2a5b7c9`. Its eligibility ledger matched live source exactly;
the complete table manifest matched the source SHA-256
`b2c05e78d1351f5ececab68a13b81b9ca4795b23c31d866724c47b63f782e05c`.

The exact retirement script SHA-256 was
`3ed79cb82ee4c46e82b2064d2ec7dc2ad370a3996fd94aa30de643be65f5bca1`.
It used one `SERIALIZABLE` transaction, bounded lock and statement timeouts,
`SHARE ROW EXCLUSIVE` table locks, row locks for the targets and revisions, and
reasserted the frozen candidate set, seed provenance, ownership, runtime,
semantic, Project-1, and row-count gates inside the transaction. Any mismatch
raised an exception and rolled back.

Rehearsal committed exactly:

- Persona Profiles deleted: 3
- Owned profile revisions deleted by proven profile-local cascade: 3
- Persona Profile bindings deleted: 0
- Unexpected Persona Profile deletes: 0
- Unexpected revision deletes: 0
- Unexpected binding deletes: 0

All three profiles, revisions, and bindings were absent afterward. Semantic
residuals and Persona FK orphans were zero. Every non-Persona table was
byte-canonically unchanged across retirement, with manifest SHA-256
`87b0cd85b19f8df5aa972418221449b35c753faf1ba6c394278ced2c0e115416`.
Users remained 6, Projects 6, threads 72, messages 805, Project `1` absent,
repaired threads 8, and affected messages 20.

## Normal rehearsal traversal to `e5a9c2f7b4d1`

Normal Alembic traversal ran from `d4e0f2a5b7c9` to exactly
`e5a9c2f7b4d1` using the repository Alembic environment; migration functions
were not invoked directly and traversal did not continue to repository head.

- Exit: 0
- Final revision: `e5a9c2f7b4d1`
- Unbound Persona Profile classification errors: 0
- Contradictory canonical binding errors: 0
- Retired-profile Persona Subjects: 0
- Synthetic retired-profile bindings: 0
- Retired profile/revision residuals: 0
- Persona/Profile FK and semantic orphans: 0

All threads and messages remained identical across traversal: 72 thread rows
with SHA-256 `9ebece4e3d5eda1873e33996f75158ceade77a554bdc924bf87e5a6d076e85fc`
and 805 message rows with SHA-256
`5988a0332782797bb79df7a98d2a04935b40a2b8b08abdfe0a2d1e26e3022eda`.
Project `1` remained absent, its eight repaired threads and 20 affected messages
remained intact, and users were unchanged. The intervening Project migrations
performed their own expected ownership/description normalization; the
retirement transaction itself changed no Project row.

## Live revalidation and retirement

After rehearsal, the still-quiesced source remained at `d4e0f2a5b7c9`, Project
`1` remained absent, and the complete live table manifest still matched the
frozen pre-rehearsal source SHA-256. Each candidate ledger and the complete FK,
semantic, and orphan census matched rehearsal. There were zero other database
sessions when the transaction began.

The exact same script was then applied live as one explicit transaction. It
committed exactly three target profiles, three owned revisions, and zero
bindings. All three profiles are absent. No unrelated Persona Profile or
revision existed to delete, and no synthetic owner, binding, subject, or runtime
class was created.

Post-retirement live integrity:

- Alembic revision: `d4e0f2a5b7c9`
- Persona Profiles / revisions / bindings: 0 / 0 / 0
- Users / Projects / threads / messages: 6 / 6 / 72 / 805
- Project `1`: absent
- Repaired Project-1 threads: 8, digest
  `be4ab5affdb49361d2109587493a3ad64804860a50cca731b2e9badcc4ec5c03`
- Affected messages: 20, digest
  `d201acd44888dfd48905ce6a9b477eee764332bac39bda4ef745198121d8c0bd`
- Account and replacement-Project ownership digest:
  `c8885dea6b1d6ec40a5a276509ffda11574fd5a73eaa01c8ea32a8c011d2b325`
- Users digest:
  `032908c8232b6a0e5dd5d3bcf271cf9eaaad59f83ed1574cb941a51e7725399b`
- Candidate semantic residuals: 0 each
- Persona/Profile FK orphans: 0
- Complete live post-retirement manifest equals rehearsal post-retirement
  manifest: SHA-256
  `d24f791e9f5eccb1b4000a43830462e2182aff8437acf7d149025f95ad9a12aa`
- All non-Persona tables were unchanged by retirement: SHA-256
  `87b0cd85b19f8df5aa972418221449b35c753faf1ba6c394278ced2c0e115416`

## Post-retirement preservation

A fresh complete custom-format dump was created after live integrity checks:

- Path: `/Volumes/Dev_SSD/Codexify-preservation/persona-retirement-20260911T145217Z/private-preview-post-persona-retirement.dump`
- SHA-256: `0401d5334b34a3b281e1a999732cce6a1ad9ddd12de5c18657d5b1528b2d805d`
- Size: 3,338,690 bytes
- Mode: `0400`
- `pg_restore --list`: PASS

This is the preferred source boundary for the next complete canonical Alembic
rehearsal.

## Validation and prohibited activity

The three focused migration suites ran against real isolated PostgreSQL using
the current repository mounted read-only and no external network:

- `test_persona_profile_manifest_binding_migration.py`: 4 passed
- `test_thread_persona_profile_revision_migration.py`: 2 passed
- `test_persona_subject_identity_migration.py`: 4 passed

Repository validation:

- `python3 scripts/validate_docs.py`: PASS
- `.venv/bin/python scripts/validate_docs.py`: PASS
- `git diff --check`: PASS
- Explicit new-file whitespace check: PASS (no diagnostics)

No application runtime or provider test was required.

Activity counters:

- Provider-backed invocations: 0
- Provider requests: 0
- Live executor run calls: 0
- OAuth logins: 0
- Manual token refreshes: 0
- Chroma mutations: 0
- Task-agent live Alembic attempts: 0
- Task-agent Private Preview startup attempts: 0
- External startup attempts during this task: 0
- Pushes: 0
- Merges: 0

## Result and next boundary

`RESULT=PASS`

`REASON=orphaned_legacy_persona_profiles_retired_under_adr_086`

The live database deliberately remains at `d4e0f2a5b7c9`, and Private Preview
application writers remain quiesced. This proof removes the known unbound
Persona source-data blocker; it does not prove complete restored-copy traversal
or live migration to repository head and does not advance a release claim.

The next recommended architecture-impact task is **Resume canonical Alembic
after legacy Persona retirement**. It must begin from the post-retirement backup,
prove complete restored-copy traversal to current repository head, then obtain
separate authority before any live Alembic resume. Current-state documentation
follow-through remains deferred until that succeeds.
