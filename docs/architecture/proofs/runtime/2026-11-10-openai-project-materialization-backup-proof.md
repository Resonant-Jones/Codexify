# Private Preview online PostgreSQL recovery checkpoint

**VERIFIED_POSTGRESQL_ONLY** for the November 10, 2026 checkpoint at 12:00:29 p.m. EST (17:00:29 UTC).
The recovery archive and private verification manifest are stored outside the repository.

## Restore evidence

| Evidence | Verified result |
| --- | --- |
| Source | `Codexify` application database on PostgreSQL 15.19, Alembic `ab71d5ce9604`, extensions `plpgsql` 1.0 and `pgcrypto` 1.3 |
| Archive | `postgres.dump`, 140,542,143 bytes, SHA-256 `50a6b8c30d659691c8667f878a91589930c165d45e5e0f30dbbc62b2007c619d` |
| Dump and archive inspection | Custom-format `pg_dump` exited 0 with empty stderr. `pg_restore --list` exited 0 with 1,245 catalog lines and the expected table-data entries. An independent `shasum -a 256 -c` passed. |
| Isolated restore | Full `pg_restore --exit-on-error` exited 0 with empty stderr. The disposable container used the same immutable PostgreSQL image, a uniquely labeled scratch volume, network mode `none`, no published ports, and no production mounts or credentials. Both disposable resources were identity-checked and removed. |
| Restored census | 15 users, 19 Projects, 5,146 threads, and 113,570 messages. Alembic and extension inventory matched. Project ownership, thread membership and metadata, and message relationship digests matched the source. |
| Audited OpenAI account | 5,043 canonical OpenAI threads with distinct source IDs, 52 source groups, 2,824 grouped threads, 2,219 ungrouped threads, and zero materialization markers. |

The live migration guard found no active migration or DDL matching its query, and the migrator
container had exited successfully. The source census ran in a read-only repeatable-read transaction.
`pg_dump --snapshot` consumed the exact exported snapshot used for the census. The restored census
matched the dump-time source census, and a later live census also matched.

The relationship checks found no missing essential relationships or unvalidated foreign keys.
Six pre-existing thread-to-Project owner mismatches were present in both the source snapshot and
the restore. All 5,043 audited OpenAI threads had matching Project owners. They remained in the
account's named Imports Project, which lacked the structural `imports` role.

## Private Preview observations

The production PostgreSQL container identity, image, start time, and volume identity matched before
and after. The full Preview container inventory, desired-up marker, and serving pin also matched.
The backend and database were healthy, and local `/ping` returned HTTP 200. The checkpoint ran
without stopping Preview services or writing to the production database. No Project materialization ran.

Earlier freeze attempts stopped at the reconciliation or serving identity checks. The running backend
image and bind-mounted source had diverged. A first online attempt then timed out on the read-only
migration guard before opening a snapshot. The successful retry verified recovery at the PostgreSQL
boundary while the application image and mounted source still had mixed identities.
[November 10 Dev Log](../../../DEV_LOG/2026-11-10/Dev%20Log%20-%202026-11-10.md)

## Scope and limits

This dated logical checkpoint covers the PostgreSQL application database. Media, cluster-wide roles
and grants, and a coherent application deployment are outside the restore proof. Deployed
materialization writers still require verification and any live apply requires separate authorization.
Before a later materialization, refresh the checkpoint or reconcile intervening writes. Restoring the
entire database over a newer live state can discard subsequent writes across accounts.

Release disposition remains `HOLD`.
