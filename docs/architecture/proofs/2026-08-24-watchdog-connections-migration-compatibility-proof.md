# Watchdog and Connections Migration Compatibility Proof

Proof date: 2026-08-24

## Outcome

**PASS — source lineage and four disposable Postgres shapes converge at one
canonical head.**

This proof restores the deployed GitHub Watchdog Alembic lineage to source and
joins it with the independent Connections migration. It does not migrate the
qualifying database, alter a runtime service, invoke Google OAuth, call a
provider API, mutate a Connection, or execute Command Bus work.

## Source and graph identity

The five restored Watchdog migration files exactly match their recoverable Git
blobs:

| Revision | Blob SHA |
| --- | --- |
| 2a6b7c8d9e0f | 1827f45ea69b392af09bfde9a798068bc23edaf3 |
| 3b7c8d9e0f1a | ad674e7826360fe8cc055badcc117f86a3831cf3 |
| 4c7d8e9f0a1b | 9c5f22f48379a6c87af9a4d8ae24e9976aa05af8 |
| 5d8e9f0a1b2c | 1666cde8b35b1918f4378ab3518f6bdb4dcfe0ba |
| 6e9f0a1b2c3 | 041cf25e22fbf8696eb21c82be6fe58f1dcba5ef |

The restored graph is:

    1c0a2b3c4d5e
      -> 2a6b7c8d9e0f -> 3b7c8d9e0f1a -> 4c7d8e9f0a1b
      -> 5d8e9f0a1b2c -> 6e9f0a1b2c3
      -> d2e3f4a5b6c7

Alembic confirmed exactly those two heads before the merge. The generated
revision 9c66e490a42b has
down_revision = (6e9f0a1b2c3, d2e3f4a5b6c7) and pass-only upgrade and
downgrade functions. AST inspection found no schema operation call. Importing
every restored migration and the merge module succeeded without executing a
migration.

The historical Watchdog effects occupy only github_watchdog_* tables,
constraints, and indexes. The sibling d2 revision creates only
notion_connection_credentials. There is no table, constraint, foreign-key, or
index collision, so the prior Class B repair assumption is valid.

## Disposable-database proof

Each target was a newly created database named
codexify_watchdog_lineage_*_20260824. Alembic was invoked directly from the
source-mounted backend with DATABASE_URL redirected only inside the one-off
process to the named disposable target. The canonical live migrator and the
qualifying database were not used.

| Shape | Starting state | Result after upgrade to head |
| --- | --- | --- |
| A: clean | Empty database | 9c66e490a42b; all five Watchdog tables and notion_connection_credentials present |
| B: historical Watchdog fork | 6e9f0a1b2c3; dispatch table present, Notion table absent | 9c66e490a42b; both dispatch and Notion tables present |
| C: current Connections sibling | d2e3f4a5b6c7; Notion table present, dispatch table absent | 9c66e490a42b; both Notion and dispatch tables present |
| D: preserved backup restore | Backup restored at 6e9f0a1b2c3 | 9c66e490a42b; Watchdog and Notion schema both present |

On the clean path, physical checks confirmed the five historical Watchdog
tables, notion_connection_credentials, the
ix_github_watchdog_review_dispatches_state index, three dispatch foreign keys,
and the Notion user uniqueness constraint.

## Backup preservation evidence

The original backup remains untouched:

    /tmp/codexify-google-drive-pre-schema-reconcile-20260824.sql
    sha256 595906e8af288d810bef7cf5719f8b0017c3f6b5b987b21b0b3fa7aae0e75e61

Its SHA-256 was identical before and after restoring it into the disposable
database. Before and after its upgrade, the copy contained one local user and
one local project, zero authenticated_principals rows, and zero
oauth_connections rows. The proof did not emit application-row contents.

## Validation

| Check | Result |
| --- | --- |
| Byte identity of five restored migration files | passed |
| Restored migration and merge-module import | passed |
| Pre-merge graph | exactly two expected heads |
| Post-merge graph | one head: 9c66e490a42b |
| Focused migration tests | 12 passed |
| Full tests/migration suite | 124 passed, 29 skipped, 1 failed |
| Backup hash before and after disposable restore | identical |

The sole full-suite failure is
tests/migration/test_openai_export_adapter.py::test_sharded_import_is_idempotent_on_reimport.
It is the pre-existing OpenAI import-idempotence failure, outside this
migration-lineage task. The two stale canonical-head failures reported before
this repair are resolved. No new migration-suite failure was introduced.

## Live and product boundaries

The qualifying database was read only for its final state check and remains at
6e9f0a1b2c3. It was not upgraded, downgraded, stamped, reset, or manually
altered. No production or release-support claim changes here.

Google Drive OAuth remains unattempted. No Google credential, OAuth state,
provider request, external content, memory, provenance, Connection mutation,
or Google Command Bus action was created by this task.

The next proof is a separately authorized live migration window using the
canonical migrator, followed by physical-schema, GuardianDB, and protected-read
verification. Only that later proof can establish live Connections storage
readiness.

ADR impact: none. This repair follows the migration-safety doctrine and does
not alter ADR-031, ADR-071, ADR-072, ADR-073, ADR-075, or release truth.
