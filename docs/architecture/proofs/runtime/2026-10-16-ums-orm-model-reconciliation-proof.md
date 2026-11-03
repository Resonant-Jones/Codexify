# UMS ORM Model Reconciliation Proof

- **Date:** 2026-10-16 (America/New_York)
- **Disposition:** FAIL_CODE — restored mappings verified; an unchanged test has a stale head assertion
- **Evaluated base:** `8e3b2f8ae03bed56e81e33a26c6bf78dfd8dc82d`
- **Branch:** `codex/restore-ums-orm-models-20261016`
- **Release:** HOLD
- **ADR impact:** aligned restoration; no ADR change

## 1. Evaluated baseline and branch

Task worktree:
`/Volumes/Dev_SSD/offload/codex/worktrees/restore-ums-orm-models-20261016`.
It was created with:

```sh
git worktree add -b codex/restore-ums-orm-models-20261016 /Volumes/Dev_SSD/offload/codex/worktrees/restore-ums-orm-models-20261016 8e3b2f8ae03bed56e81e33a26c6bf78dfd8dc82d
```

Exit 0. Initial `git status --short --branch` exited 0, clean. The base and
the [Chronicle blocker receipt](./2026-10-16-chronicle-http-regression-baseline-proof.md)
were verified present before editing. Local `main` was
`097503798b3d821877a6e82cf06ba34ed07f2d20`; stored `origin/main` was
`42e86cb6a76954effa86ab83fc7634e8c9a14a61`. No fetch or assumption of remote
freshness was made. Neither ref was modified.

The original checkout remained detached at
`f9c60923115d8e48bd62f44194790cfb89a369b0`, with existing staged profile,
architecture README and direct-message test changes, unresolved current-state
and direct-messaging-contract conflicts, and untracked `Codexify.Space/`.
Those files and the previous proof worktree were not edited.

Before editing, AST inspection confirmed all four target classes absent.
All four governing migrations matched their bytes at the required base:

| Revision | SHA-256 |
| --- | --- |
| `c3d9f4e6a1b2` | `32c8134035f9bd6d384b93733ad4372a05a28394ef348b8abc5ab9dbdfbc8ae7` |
| `a7c3e91d4b60` | `83d625c56046fae0ac890013c4af40349a0f276045451071f46f5f8a566a0fcf` |
| `b8e2f4a6c901` | `ae6f2cea6e709e9c59445546bd1ee368b13cad841fc03c8121d640a96fa5f984` |
| `c7f4a9b2e6d1` | `42cef2105bb0622262ea5a5b417d4fcfe1db99ee349046ffdb2c002b34ecd5ca` |

The evaluated modified `guardian/db/models.py` SHA-256 is
`f73bab412f27cbc252dd532979f325d9494383bb3cc2b1a6785c7319b3bb581c`.
No source other than this models file was modified. The receipt-carrying
commit is reported in the closeout; its parent is the evaluated base above.

## 2. Original import failure

Reproduced again in this new worktree before the edit:

```sh
env PYTHONDONTWRITEBYTECODE=1 CODEXIFY_DISABLE_DOTENV=1 CODEXIFY_CONFIG_SOURCE=core CODEXIFY_EMBEDDINGS_BACKEND=mock /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -c 'import guardian.services.memory_purge'
```

Exit 1:

```text
guardian/services/memory_purge.py:89: from guardian.db.models import (...)
ImportError: cannot import name 'MemoryLifecycleRevision' from 'guardian.db.models'
```

The traceback resolved both files inside this task worktree, not another
checkout. `MemoryRevision`, `MemoryReviewRevision`,
`MemoryLifecycleRevision`, and `MemoryPurgeTombstone` were all absent.

## 3. Four restored mappings

Exactly four classes were inserted beside the existing UMS mappings, plus
the `PrimaryKeyConstraint` import needed to preserve explicit PK names:

| Class / table | Existing migration | Meaning preserved |
| --- | --- | --- |
| `MemoryRevision` / `memory_revisions` | `c3d9f4e6a1b2` | authored content history; parent text remains current authority |
| `MemoryReviewRevision` / `memory_review_revisions` | `a7c3e91d4b60` | independent review history; typed state changes and same-account actor |
| `MemoryLifecycleRevision` / `memory_lifecycle_revisions` | `b8e2f4a6c901` | independent lifecycle history; no new retirement/restore policy |
| `MemoryPurgeTombstone` / `memory_purge_tombstones` | `c7f4a9b2e6d1` | non-content suppression survives parent-memory erasure |

Each mapping has eager server-default loading consistent with neighboring
models. No client-generated identifiers, client defaults, update-time
callbacks, relationships, transition policies, or synthetic history were
introduced. An AST comparison against the base verified **every existing
class unchanged**, with exactly these four class additions.

## 4. Migration-to-ORM parity matrix

The committed migrations are physical-schema authority. Existing contracts
govern meaning; future candidate-authority schema amendments were not
implemented by this restoration.

### Columns and defaults

All columns below are non-nullable unless explicitly marked nullable.
`created_at` / `purged_at` are timezone-aware PostgreSQL timestamps with
server default `now()`. The only other server default is
`suppress_reimport = true`. All remaining defaults are absent.

| Table | Exact columns and PostgreSQL types |
| --- | --- |
| `memory_revisions` | `revision_id varchar(36)`, `memory_id varchar(36)`, `user_id varchar(255)`, `revision_number integer`, `old_text_content text`, `new_text_content text`, `created_at timestamptz` |
| `memory_review_revisions` | `review_revision_id varchar(36)`, `memory_id varchar(36)`, `user_id varchar(255)`, `revision_number integer`, `old_review_state varchar(32)`, `new_review_state varchar(32)`, `actor_account_id varchar(255)`, `created_at timestamptz` |
| `memory_lifecycle_revisions` | `lifecycle_revision_id varchar(36)`, `memory_id varchar(36)`, `user_id varchar(255)`, `revision_number integer`, `old_lifecycle_state varchar(32)`, `new_lifecycle_state varchar(32)`, `created_at timestamptz` |
| `memory_purge_tombstones` | `purge_receipt_id varchar(36)`, `user_id varchar(255)`, `purged_record_fingerprint varchar(128)`, nullable `source_system varchar(32)`, nullable `source_entity_kind varchar(32)`, nullable `source_atom_fingerprint varchar(128)`, `purged_at timestamptz`, `suppress_reimport boolean` |

### Keys, checks and indexes

| Table | Exact named structure |
| --- | --- |
| `memory_revisions` | PK `pk_memory_revisions(revision_id)`; FK `fk_memory_revisions_memory_account(memory_id,user_id)` → `memory_records(memory_id,user_id) ON DELETE CASCADE`; unique `uq_memory_revisions_memory_number(memory_id,revision_number)`; checks `memory_revisions_number_check` (`revision_number >= 1`), `memory_revisions_change_check` (`old_text_content <> new_text_content`); index `ix_memory_revisions_memory_id(memory_id)` |
| `memory_review_revisions` | PK `pk_memory_review_revisions(review_revision_id)`; FK `fk_memory_review_revisions_memory_account(memory_id,user_id)` → same-account parent, CASCADE; unique `uq_memory_review_revisions_memory_number(memory_id,revision_number)`; index `ix_memory_review_revisions_memory_id(memory_id)`; five checks described below |
| `memory_lifecycle_revisions` | PK `pk_memory_lifecycle_revisions(lifecycle_revision_id)`; FK `fk_memory_lifecycle_revisions_memory_account(memory_id,user_id)` → same-account parent, CASCADE; unique `uq_memory_lifecycle_revisions_memory_number(memory_id,revision_number)`; index `ix_memory_lifecycle_revisions_memory_id(memory_id)`; four checks described below |
| `memory_purge_tombstones` | PK `pk_memory_purge_tombstones(purge_receipt_id)`; FK `fk_memory_purge_tombstones_user(user_id)` → `users(id) ON DELETE CASCADE`; unique `uq_memory_purge_tombstones_account_record(user_id,purged_record_fingerprint)`; index `ix_memory_purge_tombstones_user_id(user_id)`; partial unique index `uq_memory_purge_tombstones_account_source_atom(user_id,source_atom_fingerprint) WHERE source_atom_fingerprint IS NOT NULL`; three checks described below |

Review checks preserve the exact migration names:
`memory_review_revisions_number_check`, `_old_state_check`, `_new_state_check`,
`_change_check`, and `_actor_account_check` (each suffix uses the same
`memory_review_revisions` prefix). They require positive numbering, each
state in `pending/approved/rejected/disputed`, unequal old/new states, and
`actor_account_id = user_id`. They encode no legal transition graph.

Lifecycle checks use the same complete `memory_lifecycle_revisions` prefix
with `_number_check`, `_old_state_check`, `_new_state_check`, and
`_change_check`. They require positive numbering, each state in
`active/dormant/retired`, and unequal old/new states. The three revision
families share no numbering sequence.

Tombstone checks are
`memory_purge_tombstones_source_system_check` (NULL or
`codexify/openai/anthropic/future_registered`),
`memory_purge_tombstones_source_entity_kind_check` (NULL or
`chat/vault/importer/classifier/future_registered`), and
`memory_purge_tombstones_suppress_reimport_check` (boolean must be true).
There is no `memory_id`, parent-memory FK, content, excerpt, plaintext source
identity, or extensions column. Manual-memory source fingerprints remain
nullable; account and source-atom uniqueness remain enforced.

### Executable supplementary comparisons

An external, temporary verifier evaluated the four migrations' `op.create_table`
and `op.create_index` arguments into SQLAlchemy metadata, without executing
migrations or patching production modules. Its descriptor compared every
column's type, nullability and default; PK names/columns; FK names, local and
remote columns and delete action; unique constraints; exact CHECK SQL; and
index names, columns, uniqueness and partial predicate. All four descriptors
matched. `configure_mappers()` succeeded.

A second comparison created task database `ums_orm_full_parity`, migrated it
to head, and rendered only the four ORM tables into a separate
`orm_reference` schema, referencing the same canonical public parents.
PostgreSQL/SQLAlchemy reflection of the migrated public tables and the ORM
tables matched for **all four tables** across columns/types/nullability/defaults,
named PK/FK/unique/CHECK constraints, and indexes/predicates. The comparator
treated an omitted reflected parent schema as `public`; CHECK expressions
were compared after PostgreSQL rendering on both sides, without rewriting
expressions. The temporary database was dropped in `finally`.

Executed commands, each exit 0:

```sh
env PYTHONDONTWRITEBYTECODE=1 CODEXIFY_DISABLE_DOTENV=1 CODEXIFY_CONFIG_SOURCE=core CODEXIFY_EMBEDDINGS_BACKEND=mock /Volumes/Dev_SSD/Codexify-main/.venv/bin/python /private/tmp/codexify-ums-orm-01a14577-20261016/parity.py static
env PYTHONDONTWRITEBYTECODE=1 CODEXIFY_DISABLE_DOTENV=1 CODEXIFY_CONFIG_SOURCE=core CODEXIFY_EMBEDDINGS_BACKEND=mock /Volumes/Dev_SSD/Codexify-main/.venv/bin/python /private/tmp/codexify-ums-orm-01a14577-20261016/parity.py live
```

The temporary helper is investigative tooling, not a new repository test or
runtime component. Its comparison surface is described above and the mapping
matrix is retained here; rerunning the committed tests in §8 remains the
durable repository test entrypoint. This is focused relation parity evidence,
not a claim of complete ADR-083 dump/restore qualification.

## 5. Direct import results

Backend interpreter: `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`,
Python 3.12.13; SQLAlchemy 2.0.44, Alembic 1.17.0, psycopg 3.2.10,
psycopg2-binary 2.9.12, pytest 8.4.2, pytest-asyncio 1.2.0.
No dependency installation, manifest, or lockfile edit occurred. This is the
existing backend environment; it is not a freshly rebuilt Compose image.

All commands ran from the task root with these explicit common settings:

```text
PYTHONDONTWRITEBYTECODE=1
CODEXIFY_DISABLE_DOTENV=1
CODEXIFY_CONFIG_SOURCE=core
CODEXIFY_EMBEDDINGS_BACKEND=mock
```

| Command after the common environment prefix | Exit / result |
| --- | --- |
| `PYTHONPYCACHEPREFIX=/private/tmp/codexify-ums-orm-01a14577-20261016/pycache /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m py_compile guardian/db/models.py` | 0 |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -c 'from guardian.db.models import MemoryRevision, MemoryReviewRevision, MemoryLifecycleRevision, MemoryPurgeTombstone; from sqlalchemy import inspect; print({m.__name__:inspect(m).local_table.name for m in [MemoryRevision,MemoryReviewRevision,MemoryLifecycleRevision,MemoryPurgeTombstone]})'` | 0; all four expected table names |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -c 'import guardian.services.memory_purge; print(guardian.services.memory_purge.__file__)'` | 0; task-worktree module path |
| `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -c 'import guardian.services.memory_vault_mutation; print(guardian.services.memory_vault_mutation.__file__)'` | 0; task-worktree module path |

## 6. HTTP test-collection results

With the common environment prefix above:

```sh
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest --collect-only -q tests/routes/test_migration_routes.py tests/routes/test_imported_history_inspection.py tests/routes/test_chronicle_interpretation_authorization.py tests/routes/test_chronicle_preview.py -o addopts= -o cache_dir=/private/tmp/codexify-ums-orm-01a14577-20261016/pytest-cache
```

**Exit 0: 160 tests collected in 10.00 seconds.** `addopts` was cleared to
expose the count instead of inheriting the second quiet flag. No test-source
or import substitution was used. No HTTP cases executed. Successful collection
removes the observed import blocker but does not prove Chronicle HTTP behavior.

## 7. PostgreSQL environment and isolation

Only one task-owned disposable container was created:

| Property | Verified value |
| --- | --- |
| Name | `codexify-ums-orm-20261016-01a14577` |
| Container ID | `6bee8e869e25ddebc30195d7ad3eafd82fff818af390775af3b948099c667ef6` |
| Image | `postgres:15-alpine`, locally present |
| Image ID / repo digest | `sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81` |
| Server | PostgreSQL **15.19**, aarch64 Linux |
| Binding | **127.0.0.1:52730 → 5432**, no other published address |
| Storage | tmpfs `/var/lib/postgresql/data`, 1 GiB; no volume/bind mounts |
| Initial database / role | `ums_orm_proof` / `umsproof` |
| Task label | `codexify.proof=ums-orm-20261016-01a14577` |

Equivalent Docker invocation used by the external harness:

```sh
docker run -d --rm --name codexify-ums-orm-20261016-01a14577 --label codexify.proof=ums-orm-20261016-01a14577 -e POSTGRES_USER=umsproof -e POSTGRES_DB=ums_orm_proof -e POSTGRES_PASSWORD -p 127.0.0.1::5432 --tmpfs /var/lib/postgresql/data:rw,size=1g postgres:15-alpine
```

The password was generated only for this container, passed through the
subprocess environment, never printed, and held in a mode-0600 temporary state
file inside a mode-0700 directory. The Docker port allocator selected 52730.
The exact container identity, label, mounts, published address, role, database,
and `server_version_num` major 15 were checked before tests.

Presence-only inspection found ambient `TEST_DATABASE_URL`, `DATABASE_URL`,
`GUARDIAN_DATABASE_URL`, `GUARDIAN_DB_URL`, and libpq host/port/database/user/
password/service variables unset. The harness also removed these keys from
each child environment before setting all four application/test URL aliases
to the verified disposable instance. Dotenv loading was explicitly disabled.
No live environment file was read for credentials or modified.

Migration fixtures created `codexify_ums03d_<uuid>` databases inside this
cluster; service fixtures created `ums11svc_<uuid>` and `ums05c1_<uuid>`
databases. The common `temporary_postgres` fixture deliberately uses this
cluster's `postgres` administrative database. After each full suite,
`pg_database` contained exactly `postgres`, `template0`, `template1`, and
`ums_orm_proof`: all fixture-created databases were gone. The supplementary
parity database was separately dropped afterward. No existing operator,
Preview, or production database was contacted.

## 8. UMS migration-test results

The harness set the verified disposable URL aliases and common environment,
then executed:

```sh
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/migration/test_memory_revision_persistence_migration.py tests/migration/test_memory_review_revision_persistence_migration.py tests/migration/test_memory_lifecycle_revision_persistence_migration.py tests/migration/test_memory_purge_tombstone_migration.py -o addopts= -o cache_dir=/private/tmp/codexify-ums-orm-01a14577-20261016/pytest-cache --junitxml /private/tmp/codexify-ums-orm-01a14577-20261016/migration.xml
```

**Exit 1: 49 collected, 48 passed, 1 failed, 0 skipped, 0 errors.**
Duration 67.63 seconds. JUnit counts independently matched the console summary.

| Module family | Passed | Failed |
| --- | ---: | ---: |
| Content revisions | 10 | 0 |
| Review revisions | 16 | 0 |
| Lifecycle revisions | 13 | 0 |
| Purge tombstones | 9 | 1 |

The only failure is
`test_fresh_migration_creates_purge_tombstones_with_orm_parity`, at
`tests/migration/test_memory_purge_tombstone_migration.py:258`:

```text
assert len(heads) == 1
> assert heads[0] == UMS_11_REVISION
E AssertionError: assert 'f0d7c4b2a198' == 'c7f4a9b2e6d1'
```

All preceding assertions in that test passed: exact columns, required and
nullable fields, server defaults, PK/unique/FK/CHECK/index presence,
absence of content-bearing columns, ORM/live column parity, account CASCADE,
and exactly one head. The failure asserts a historical revision remains
terminal; it is not a table mismatch or a multiple-head failure.

An independent `ScriptDirectory` load exited 0 and returned
`heads = ['f0d7c4b2a198']`, with `c7f4a9b2e6d1` present in that head's lineage.
The test is unchanged from the required base. Repairing it requires a test
source outside the authorized write set, so it was not altered, bypassed,
excluded, or presented as passing. No migration/head repair is justified by
this assertion. This is the specific remaining test blocker.

The suite also emitted 60 Alembic deprecation warnings about missing
`path_separator` configuration. Configuration changes were outside scope.

## 9. UMS service-test results

With the same verified disposable environment, executed:

```sh
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/services/test_memory_purge.py tests/services/test_memory_vault_mutation.py -o addopts= -o cache_dir=/private/tmp/codexify-ums-orm-01a14577-20261016/pytest-cache --junitxml /private/tmp/codexify-ums-orm-01a14577-20261016/services.xml
```

**Exit 0: 76 collected, 76 passed, 0 failed, 0 skipped, 0 errors.**
Duration 119.90 seconds. Purge: 24 passed; mutation spine: 52 passed. JUnit
counts independently matched the console summary.

Executed purge coverage includes account ownership and cross-account denial,
CAS/confirmation failure, full child deletion with one surviving tombstone,
absence of content-bearing tombstone columns, deterministic import source
fingerprints, fail-closed ambiguous imports, idempotent retry, same-account
re-import suppression, and Personal Facts preservation. Mutation coverage
includes pin/hold, Project scope, Persona attribution, account and ownership
conflicts, shared CAS, receipts, and rollback.

The 76 warnings comprise 75 Alembic `path_separator` warnings and the existing
overlapping `MemoryRecord.user` / `MemoryRecord.project` relationship warning.
Mapper configuration succeeds; those existing class definitions were not
changed. This suite does not execute every content/review/lifecycle mutation
method or qualify HTTP, export/restore, or deployed runtime behavior.

## 10. Cleanup evidence

The external verifier checked the exact task container identity before
cleanup. All migration/service fixture databases and the supplementary parity
database were removed before container deletion. Only this task's container
was selected for `docker rm -f`; no prune or broad cleanup command was used.

`docker rm -f codexify-ums-orm-20261016-01a14577` completed with exit 0.
Docker remained in `removing` with process ID 0 for several minutes; the
same live command was awaited, without restarting Docker or retrying the
mutation. On completion the exact-name and exact-container-ID absence
checks both returned no container. A socket check against loopback port
52730 returned connection-refused (`connect_ex = 61`). All tmpfs database
storage disappeared with the container; no named or anonymous volume had
been created.

The private credential-state file was removed after container cleanup.
The exact task temporary directory was then deleted after verifying its
only remaining entries were the task's verifier scripts, bytecode/cache,
sanitized logs and JUnit results. Directory absence and closed port were
verified again, exit 0. No unrelated resource was selected. The active Git
worktree is retained for review and the scoped commit.

## 11. ADR impact and invariants

No new or amended ADR. Canonical current-index titles were checked, including
the ADR-083 renumbering notice; no authority was inferred from a historical
number alone. Relevant sections of ADR-016 (continuity scope/consent),
ADR-031 (storage/write gates), ADR-069 (support versus qualification),
ADR-083 (major-specific schema evidence), and ADR-084 (account-owned memory)
govern this bounded restoration. Axis invocation and current-state sources
read for the prior proof were verified unchanged at this base. Additional
reads covered the UMS, storage, account-export/restore, and Vault contracts.

The authoritative objects are the already-committed physical schemas and
account-owned canonical memory. Prior reports are evidence only. The human
task authorizes these four mappings and this receipt; it grants no new
runtime mutation capability. Only the scoped source and proof become durable.
Completion is bounded by stop condition B and the executable results above.

| Invariant | Evidence |
| --- | --- |
| Canonical PostgreSQL schema unchanged | no migration edits; four descriptors match existing migration DDL |
| Existing memory and present-state authority preserved | no existing DB selected; existing classes/services unchanged |
| Revision families independently ordered | distinct per-memory uniqueness in each table; migration tests pass |
| Account ownership enforced | composite revision FKs, actor equality, account-owned tombstone FK; executed negative tests |
| History does not become current authority | mappings add historical rows only; no mutation-policy code added |
| Purge remains irreversible | no memory-parent FK on tombstone; executed fan-out and survival tests |
| Tombstones minimum non-content | exact eight-column schema; executed column-exclusion checks |
| Suppression cannot silently relax | true default and CHECK; false rejection and suppression tests pass |
| No synthetic history or migration rewrite | populated-upgrade tests pass; four migrations unchanged |
| Release remains HOLD | no release metadata/current-state/ADR changes |

## 12. Remaining gaps and repository validation

One stale terminal-head assertion keeps the specified migration suite red.
The restored four-table schema and import/collection repair are proven, but
the task cannot claim its required full-suite PASS. There are no skipped
database tests hidden in the result. The small next prerequisite is a
separately authorized correction of this historical terminal-head assumption
to verify the intended revision's lineage under the current single head,
followed by the same migration suite. Do not weaken the schema assertions.

Chronicle HTTP execution, supported-Compose qualification, production data,
browser behavior, complete UMS mutation coverage, and complete account
export/restore regression remain untested here. No push, merge, deployment,
main update, provider/model call, or release promotion was performed.

Repository validation from the task root:

- `python3 scripts/validate_docs.py`: exit 0; required architecture docs,
  README links, and source headings verified.
- `git diff --check`: exit 0.
- `git diff --cached --check`: exit 0 after staging the two authorized files.
- `git status --short --ignored=matching`: exit 0; only the modified models
  file and new proof receipt, with no unexpected ignored artifacts.
- The complete staged diff for both files was inspected. The source diff
  adds only one SQLAlchemy import and the four classes (210 added lines),
  with no existing class, migration, service, route, test or config change.

Documentation follow-through is limited to this new receipt; prior proofs,
current-state, ADRs, Campaign records and release metadata are unchanged.

## 13. Final disposition

**FAIL_CODE (unchanged test blocker), not PASS.** Exactly four canonical ORM
mappings are restored and match the committed migrations and PostgreSQL 15
rendered schema. Imports succeed, 160 HTTP cases collect, and 76 UMS service
tests pass. The migration suite has 48 passes and one demonstrated stale
head assertion outside the edit allowlist. The task stops at condition B,
retaining that failure visibly rather than widening scope to test or schema
changes. Release remains **HOLD**.
