# UMS-04B-PG Disposable PostgreSQL Test Authority Proof

Date: 2026-09-10

Status: **PASSED — DISPOSABLE POSTGRESQL TEST AUTHORITY PROVEN**

Final verdict:

```text
UMS04B_POSTGRES_TEST_AUTHORITY_PROVEN
```

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: runtime-proof closeout and Campaign-state reconciliation
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-04B-PG-CLOSE
- Branch at the proof checkpoint: `main`
- Proof-bound HEAD: `40e538cfd232bb30692dde1f9008e3fdeda3562b`
- `origin/main` at the proof checkpoint:
  `40e538cfd232bb30692dde1f9008e3fdeda3562b`
- Synchronized before runtime proof: yes
- `HEAD == origin/main` at the proof checkpoint: PASS
- Initial index state: empty
- Unrelated Pi fixture present: yes
- Unrelated Pi fixture staged: no
- Git reconciliation performed by this proof-closeout task: no
- Local recovery ref preserved:
  `recovery/ums03e-conflated-71fd9f4d5` at
  `71fd9f4d5f4f2d05eb97c829a0097039c5fb0cae`

This receipt binds the PostgreSQL result to the proof checkpoint above. The
later local documentation commit created by this closeout is not represented
as synchronized with `origin/main`.

## Evidence boundaries

This receipt distinguishes three evidence sources:

1. The successful PostgreSQL and fixture qualification below is
   operator-executed evidence from the ordinary macOS host shell.
2. The earlier managed-Codex connection failure is negative evidence about the
   managed execution boundary, not a PostgreSQL server failure.
3. The creation of this receipt and the Campaign-state update are
   documentation-only closeout work performed by managed Codex after the
   operator supplied the successful host-shell results.

No runtime command output is attributed to managed Codex when it was observed
only in the operator's host shell.

## Host PostgreSQL authority

The operator-provided prerequisite and qualification evidence records:

```text
PostgreSQL version: 17.6
authority class: dedicated host-local test cluster
endpoint: 127.0.0.1:55432
runner role: codexify_test_runner
authentication: PASS
database: postgres
LOGIN: proven
CREATEDB authority: previously operator-proven
SUPERUSER: false

TEST_DATABASE_URL configured: yes
TEST_DATABASE_URL recorded: no
password recorded: no
```

The operator had previously proven direct disposable-database creation,
connection, and deletion with this role. The qualification recorded here used
the repository's existing fixture rather than adding, changing, or bypassing a
fixture.

## Managed execution boundary

The earlier managed-Codex evidence was:

```text
managed Codex inherited TEST_DATABASE_URL: yes
managed Codex host-loopback connection: denied
observed error: Operation not permitted
classification: execution-environment restriction, not PostgreSQL failure
```

The managed execution environment could not open the required host-loopback
TCP connection. Final PostgreSQL qualification was therefore performed from
the ordinary macOS host shell. The connection string and password were not
printed or recorded.

## Canonical fixture proof — first invocation

Operator-executed command:

```bash
.venv/bin/python -m pytest -v -rs \
  tests/migration/test_canonical_memory_persistence_migration.py::test_fresh_replay_creates_canonical_tables_with_frozen_constraints
```

Observed result:

```text
1 passed
0 skipped
1 warning
6.13s
```

Result: **PASS**

## Fixture teardown proof — first invocation

After the first fixture lifecycle, the operator queried `pg_database` for
database names matching:

```text
codexify_ums03d_%
```

Observed result: no rows.

Teardown result: **PASS**

No manual database removal was used to obtain this result.

## Canonical fixture proof — second invocation

Operator-executed command:

```bash
.venv/bin/python -m pytest -v -rs \
  tests/migration/test_canonical_memory_persistence_migration.py::test_fresh_replay_creates_canonical_tables_with_frozen_constraints
```

Observed result:

```text
1 passed
0 skipped
1 warning
5.91s
```

Result: **PASS**

## Fixture teardown proof — second invocation

After the second fixture lifecycle, the operator again queried `pg_database`
for database names matching `codexify_ums03d_%`.

Observed result: no rows.

Teardown result: **PASS**

No manual database removal was used to obtain this result.

## Alembic topology

The operator executed the repository Alembic-head command from the proof-bound
checkout and observed:

```text
f6b0d3e8c5a2 (head)
```

```text
Alembic head count: 1
Alembic head: f6b0d3e8c5a2
```

Incidental FAISS informational log lines were non-failing diagnostic noise and
did not alter the topology result.

## Scope preservation

```text
production code changes: none
test changes: none
fixture changes: none
ORM changes: none
migration changes: none
account-export implementation changes: none
account-restore implementation changes: none
runtime/retrieval changes: none
ADR changes: none
release-boundary changes: none
```

The dedicated PostgreSQL instance is proof infrastructure only. This proof
does not create a Codexify runtime dependency on that cluster, change canonical
memory authority, implement account-export v4, implement restore, or widen the
Beta release boundary.

## Campaign consequence

```text
UMS-04: OPEN
UMS-04A: CLOSED
UMS-04B-PG DISPOSABLE POSTGRESQL TEST AUTHORITY: CLOSED
UMS-04B CANONICAL MEMORY EXPORT SERIALIZATION: AUTHORIZED TO RESUME
UMS-04C: NOT AUTHORIZED
UMS-04D: NOT AUTHORIZED
UMS-05+: NOT AUTHORIZED
```

UMS-04B is neither implemented nor closed by this proof. The next authorized
engineering slice is the already-frozen UMS-04B canonical-memory export
serialization task.
