# 2026-09-04 Project Ownership Runtime Convergence Proof

## Conclusion

`UMS_01A_RUNTIME_AUTHORITY_TEST_PROVEN`

The covered Project and Media runtime paths now use `projects.user_id` as the
sole Project ownership authority. New Project writes persist plain human
descriptions, matching legacy envelopes provide description recovery only, and
conflicting envelope/column values fail closed with
`project_ownership_authority_conflict`.

Revision `c3d9e4f6a8b1` implements classify-before-mutate cleanup for matching
envelopes. Its always-on migration-unit proof passes. Disposable PostgreSQL
integration cases are present but could not execute in this harness because
PostgreSQL bootstrap was denied its shared-memory syscall. No live database was
contacted or changed. UMS-01 therefore remains open for legacy `local` owner
reconciliation and the remaining deployment-grade migration proof.

## Scope and lineage

- Workflow classification: `architecture-impact`
- Task: `UMS-01A`
- Starting Git SHA: `9f1277cd40104ce6f74ac8554736fe71e7f22e23`
- Canonical remote base: `862940b5cb688d728ba101fbaad44b96324799c2`
- Final Git SHA: recorded in the task closeout after the repository transaction
- Prior migration head: `b2c8d0e3f5a7`
- New migration revision: `c3d9e4f6a8b1`
- New migration head count: one
- Live private-preview migration: not authorized and not performed

The unrelated pre-existing Pi fixture remained outside task scope.

## ADR impact

This slice implements accepted doctrine without changing it:

- ADR-005: authenticated account/user isolation remains the authority boundary.
- ADR-076: Project IDs, built-in roles, and lifecycle semantics remain stable.
- ADR-081: `projects.user_id` becomes the sole authority in the covered runtime
  paths; description metadata is compatibility evidence only.
- ADR-084: this advances, but does not close, the Project-ownership prerequisite
  for Project-scoped unified memory.

No ADR was created, renumbered, superseded, or edited.

## Runtime changes

The shared classifier in `guardian/core/project_ownership.py` is consumed by:

- `guardian/routes/projects.py` for list visibility, direct lookup, patch, and
  delete authorization plus compatibility description recovery;
- `guardian/routes/media.py` for every Media route that passes through the
  shared Project-account guard; and
- revision `c3d9e4f6a8b1` for persisted-row classification and safe cleanup.

The machine classifications are:

| Classification | Meaning | Runtime posture |
| --- | --- | --- |
| `canonical_column_only` | no valid legacy envelope | canonical column governs |
| `matching_legacy_envelope` | embedded owner matches a non-local canonical owner | description recovery only |
| `project_ownership_authority_conflict` | embedded and canonical owners differ | fail closed |
| `legacy_local_owner` | canonical owner remains `local` | preserve and defer reconciliation |

`legacy_local_owner` also carries an orthogonal envelope state. A matching
`local` envelope is safe to unwrap while ownership remains `local`; a
conflicting `local` envelope is still classified as the blocking authority
conflict.

## Authority and isolation behavior

- Multi-user creation passes the authenticated account identity through the
  existing `user_id` persistence parameter and stores the submitted
  description directly.
- Single-user creation preserves its existing database-adapter call shape; the
  adapter persists its canonical default `user_id`. It no longer writes an
  ownership envelope.
- A client-supplied cross-account `user_id` remains rejected.
- Embedded owner metadata cannot grant visibility or mutation access.
- Embedded owner metadata cannot override or deny by precedence; disagreement
  blocks the record instead.
- Conflicted Projects are suppressed from list results with bounded logging of
  record identity and classification only.
- Direct conflicted operations return HTTP 409 with the bounded conflict token.
- Canonical cross-account Projects return HTTP 403 on direct Project and Media
  guards.
- Matching envelopes recover exact human description text without changing
  authorization.

Focused tests cover ordinary Project records, both stale-envelope directions,
matching-envelope display recovery, Project mutation guards, and the Media
Project-account guard used by upload, association, read/detail, and related
Project-scoped Media paths.

## Migration behavior and preservation

The migration performs two ordered passes in one Alembic transaction:

1. select and classify every Project without issuing any update;
2. only if no conflict exists, update descriptions for matching envelopes.

The always-on fake-connection proof places a safely matching row before a
conflicting row and asserts zero updates after the conflict. This proves the
implementation's classify-before-mutate ordering independently of database
rollback behavior.

Executable PostgreSQL integration fixtures additionally assert, when a
disposable PostgreSQL target is supplied:

- canonical column-only rows are unchanged;
- matching account and `local` envelopes unwrap exactly;
- `local` canonical owners remain `local`;
- Project IDs remain unchanged;
- thread IDs, thread `user_id`, and thread-to-Project relationships remain
  unchanged;
- current-head repetition is a no-op;
- conflicts leave the Alembic ledger at the previous revision and commit no
  partial cleanup; and
- downgrade is a non-fabricating no-op.

Description preservation is checked using equality, character length, and
SHA-256 digest in the PostgreSQL fixture. No private description content is
included in this receipt.

Downgrade intentionally does not reconstruct the forbidden ownership envelope.
The removed metadata was redundant under ADR-081, so a no-op is safer than
fabricating a second durable authority representation.

## Validation evidence

Completed in this harness:

```text
DATABASE_URL= TEST_DATABASE_URL= .venv/bin/pytest -q \
  tests/core/test_project_ownership.py \
  tests/routes/test_projects_account_scope.py \
  tests/routes/test_media_routes.py \
  tests/migration/test_project_ownership_runtime_convergence.py
50 passed, 2 skipped

DATABASE_URL= TEST_DATABASE_URL= .venv/bin/pytest -q \
  tests/routes/test_projects_routes.py \
  tests/routes/test_project_lifecycle.py \
  tests/identity/test_user_ownership_consistency.py \
  tests/routes/test_owner_resolution_bearer_compat.py
30 passed

DATABASE_URL= TEST_DATABASE_URL= .venv/bin/pytest -q \
  tests/test_migrations.py
1 skipped: disposable PostgreSQL URL not supplied

.venv/bin/python -m alembic -c backend/alembic.ini heads
c3d9e4f6a8b1 (head)
```

The two focused migration integration tests skipped when database URLs were
deliberately removed. A subsequent attempt to bootstrap a proof-only local
PostgreSQL 17 cluster under `/private/tmp` failed before test execution because
the sandbox denied `shmget`. `initdb` removed each incomplete data directory.
Docker was also unavailable because the sandbox denied its socket. The live
private-preview database and its containers were never used.

`alembic current` cannot run without a configured database URL and was not
redirected to any live database. Documentation validation and final diff checks
are recorded in closeout after this receipt is added.

## Residual gate

```text
UMS-01 PROJECT OWNERSHIP RUNTIME AUTHORITY: PROVEN IN UMS-01A
UMS-01 MATCHING-ENVELOPE MIGRATION: UNIT-PROVEN; DISPOSABLE POSTGRES EXECUTION BLOCKED BY HARNESS SHARED-MEMORY POLICY
UMS-01 LEGACY LOCAL OWNER RECONCILIATION: PENDING
UMS-01 CAMPAIGN GATE: OPEN
UMS-02: NOT AUTHORIZED TO START
```

No Unified Memory Store schema, API, Vault, command, classifier, recall grant,
importer, persona-subject, Personal Facts, or MemoryOS implementation is part of
this slice.
