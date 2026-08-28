# ADR-076: Round-Trip-Stable Governed-Schema Equivalence

**Status:** Accepted

**Acceptance gate:** Accepted after the explicitly authorized ADR-index DLG
preflight and Phase 3 validation passed on 2026-08-28.  Final source-commit
lineage is bound by the separate local DLG metadata commit required by the
reconciliation task.

**Date:** 2026-08-28

## Context

The accepted Google Drive migration-convergence evidence established a
PostgreSQL 15 governed-schema signature for the Watchdog and Connections
surface.  A later post-hoc adoption proof found that a fresh schema and its
first `pg_dump --schema-only` restore had identical columns, indexes, keys,
foreign-key actions, and CHECK meaning, but twelve rendered CHECK definitions
differed in PostgreSQL's type-cast presentation.  Treating those two physical
representations as unequal blocks a safe restored-database comparison.

The defect is in the proof boundary, not in the migration graph or in the
qualifying database.  The comparison must establish the representation that
PostgreSQL itself produces after restoration, while still detecting a real
governed schema mutation.  A text simplifier would make the proof less
trustworthy by deciding semantic equivalence outside the database engine.

## Decision

Codexify adopts `governed-schema-equivalence/v1` as an evidence-only contract
for comparing the governed PostgreSQL schema after canonicalization.  The
canonical representation is the descriptor collection read from a fresh
disposable database after exactly one controlled schema-only dump and restore
on the same PostgreSQL major.

The contract is implemented by
`scripts/governed_schema_equivalence.py`.  It has no authority to run Alembic,
stamp a version, mutate a source database, contact a qualifying database, or
promote release support.  The identifier is not a runtime or wire protocol
token.

## Evidence contract version

The exact contract identifier is:

```text
governed-schema-equivalence/v1
```

Each snapshot envelope binds that identifier to the expected PostgreSQL major,
the source Alembic revision, the normalized governed descriptor document, and
the SHA-256 of the exact serialized envelope without the digest field.

## Governed schema surface

The governed relations are exactly:

- `github_watchdog_delivery_receipts`
- `github_watchdog_review_attempts`
- `github_watchdog_review_input_snapshots`
- `github_watchdog_review_results`
- `github_watchdog_review_dispatches`
- `notion_connection_credentials`

The descriptor document contains four sections: `relations`, `columns`,
`constraints`, and `indexes`.

Each relation descriptor contains `schema` and `name`.

Each column descriptor contains `schema`, `relation`, `ordinal`, `name`,
`type`, `not_null`, `default`, `identity`, `generated`, and `collation`.

Each constraint descriptor contains `schema`, `relation`, `name`, `type`,
`deferrable`, `initially_deferred`, `on_delete`, `on_update`, `definition`,
`local_columns`, `referenced_relation`, and `referenced_columns`.  This
preserves primary, unique, CHECK, and foreign-key identity, including
referenced table/columns and update/delete behavior.

Each index descriptor contains `schema`, `relation`, `name`, `unique`,
`primary`, `definition`, and `predicate`.

Catalog object identifiers are used only to join PostgreSQL catalog rows; no
OID is emitted.  Names and rendered definitions are the descriptor identity.

## PostgreSQL canonicalization procedure

For every source schema the tool:

1. reads and verifies source PostgreSQL-major and Alembic identity using
   read-only catalog queries;
2. verifies a separately named, explicitly disposable empty target on the
   same PostgreSQL major;
3. runs exactly one controlled command class:

   ```text
   pg_dump --schema-only --no-owner --no-privileges --dbname=<source>
   ```

4. restores that output into the target with `psql --no-psqlrc`,
   `ON_ERROR_STOP`, and one transaction;
5. runs no Alembic command, version stamp, or manual DDL after restore; and
6. collects the governed descriptors from the restored target.

The target name must be explicitly supplied and use the proof-only
`codexify_gse_` prefix.  The tool also checks `current_database()` against that
name.  It never uses `--clean` or `--create`, and it never drops or rewrites a
source database.  A subsequent canonicalization of a schema-only restore may
carry forward the previously verified source revision explicitly; an observed
wrong version row always fails closed.

## Alembic revision boundary

The required source revision is `9c66e490a42b`, the metadata-only merge of
`6e9f0a1b2c3` and `d2e3f4a5b6c7`.  The source revision is captured before the
dump and is part of the comparison envelope.  Because a schema-only dump does
not preserve Alembic table data, the second canonicalization may use the
previously validated revision as explicit lineage for that restored schema.

An observed missing, multiple, or different source revision raises the typed
`ALEMBIC_REVISION_MISMATCH` error unless the caller has explicitly supplied the
validated carry-forward revision for a known schema-only source.  The tool
does not fabricate an `alembic_version` row in the digest.

## CHECK-constraint treatment

CHECK definitions are collected from the restored database through
PostgreSQL's rendered constraint descriptor.  The tool performs no regex
simplification, parenthesis removal, cast removal, token sorting, AST
rewriting, or constraint-specific exception.  A real change to a literal,
accepted value, operator, or referenced column changes the descriptor and
must fail comparison.

The canonicalization step is the equivalence boundary: source and restored
schemas are each restored once, and the descriptors from those restored
schemas are compared.  This lets PostgreSQL settle its own representation
without treating two historical raw digests as aliases.

## Why `conbin` is diagnostic-only

Internal PostgreSQL parse-tree text is useful when explaining why raw
representations differ, but it is not a stable cross-restoration identity.
The four diagnostic-only differences from the historical proof are:

- `ck_github_watchdog_review_attempts_model_selection_source`
- `ck_github_watchdog_review_attempts_operation`
- `ck_github_watchdog_review_input_snapshots_terminal_shape`
- `ck_github_watchdog_review_results_terminal_shape`

The v1 digest implementation contains no internal parse-tree field.  The
historical raw comparator remains an evidence tool and is not weakened by this
ADR.

## Comparison semantics

Two snapshots are equivalent only when all of the following are equal:

- contract version;
- PostgreSQL major;
- source Alembic revision;
- governed SHA-256 digest; and
- exact normalized descriptor sections.

Digest equality is not sufficient.  The comparator independently checks the
descriptor collections and returns a bounded, human-readable section/item
diff, rather than returning only `digest mismatch`.

Serialization is UTF-8 JSON with sorted keys, deterministic descriptor-row
ordering, compact separators, and one terminal newline.  The digest covers
the envelope containing `contract_version`, `postgres_major`,
`source_revision`, and `descriptors`.  No timestamps, container/database
names, DSNs, secrets, or OIDs are serialized.

## PostgreSQL-version boundary

v1 is deliberately PostgreSQL-major-specific.  The supported proof boundary
is PostgreSQL major `15`, matching the accepted R2 evidence and the repository
PostgreSQL image.  A source or target on another major raises
`POSTGRES_MAJOR_MISMATCH`; the comparator never claims equivalence across
majors.

## Failure semantics

The tool fails closed for:

- `POSTGRES_MAJOR_MISMATCH`;
- `ALEMBIC_REVISION_MISMATCH`;
- `MISSING_GOVERNED_RELATION`;
- `DISPOSABLE_TARGET_REQUIRED`;
- controlled dump/restore command failure; and
- invalid or tampered snapshot envelopes.

Failed comparisons are non-equivalent and include the bounded descriptor diff
when the descriptor collections differ.  A proof receipt may report PASS only
after the raw historical case, repeated canonicalization, real CHECK and
non-CHECK mutations, version/revision failures, and the required static/docs
validators all pass.

## Security / credential handling

Source and target DSNs are inputs to the controlled local process only.  They
are never printed, placed in a snapshot, or included in a diff.  Catalog
queries emit only governed names and definitions; no row data, tokens,
passwords, or provider credentials are collected.  The source is queried
read-only.  Proof databases, dumps, mutation SQL, and logs are disposable and
must be removed at closeout.

## Legacy R2 interpretation

The accepted raw R2 comparator remains the historical baseline.  It correctly
reports the raw fresh digest and the different first-restored digest, with the
same twelve CHECK-only differences.  v1 does not alter that receipt, accept
two raw digests as aliases, or hide a non-CHECK difference.  It defines the
post-restoration descriptor boundary needed to compare independently restored
schemas.

## Non-goals

This ADR does not:

- change an Alembic migration, model, database, or runtime configuration;
- provide a SQL semantic-equivalence engine;
- support multiple PostgreSQL majors;
- rewrite historical receipts or current-state release truth;
- contact or adopt the live qualifying database;
- initiate OAuth, call Google APIs, or invoke the Command Bus; or
- refresh DLG metadata or widen the Beta release boundary.

## Consequences

The previously blocked restored-schema proof can compare two independently
canonicalized PostgreSQL representations without a hand-maintained CHECK
normalizer.  The descriptor boundary is explicit enough to detect constraint,
key, index, nullability, default, and foreign-key changes.  The cost is a
same-major disposable PostgreSQL restore for each source and an explicit
lineage handoff when a schema-only dump has no Alembic data.

The contract remains proof tooling.  It does not make the live Google Drive
database migration-qualified; that requires a separate post-hoc adoption proof
using this contract.

## Proof requirements

The v1 implementation must retain evidence for:

1. the reconciled current-main anchor and drift proof;
2. reproduction of the historical raw R2 digest and exact twelve-CHECK
   mismatch;
3. equal v1 snapshots after first and second canonicalization;
4. a real CHECK semantic mutation failure;
5. a real governed non-CHECK structural mutation failure;
6. PostgreSQL-major and Alembic-revision fail-closed behavior;
7. deterministic serialization and bounded descriptor diffs;
8. source non-mutation; and
9. the focused contract tests, migration regression tests, documentation
   validators, DLG validation, and exact tracked-file immutability checks.

This ADR is evidence governance only.  It does not supersede the current
release truth in `docs/architecture/00-current-state.md`.
