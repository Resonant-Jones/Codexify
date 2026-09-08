# 2026-09-04 Project Ownership Local Reconciliation Proof

## Conclusion

`UMS_01B_IMPLEMENTED_UNIT_PROVEN_POSTGRES_BLOCKED`

Revision `d4e8f1a2b6c9` implements the second ADR-081 Project-ownership
convergence slice. It reconciles a legacy `projects.user_id = 'local'` Project
only when every canonical referencing thread names the same exact non-local
owner, that owner exists as a canonical user, and reassignment preserves
account-scoped built-in Project-role uniqueness.

The migration is self-contained, classifies every candidate before any owner
mutation, and fails closed when one or more candidates are unresolved. Twelve
always-on UMS-01B unit tests and all 77 required Project/Media runtime
regressions pass. The 12 UMS-01A/UMS-01B PostgreSQL integration cases and the
general migration test could not execute because this harness cannot provision
a disposable PostgreSQL database. UMS-01 therefore remains open and UMS-02 is
not authorized to start.

## Scope and lineage

- Workflow classification: `architecture-impact`
- Task: `UMS-01B`
- Starting Git SHA: `bb8e877a55c78c2ede9be31c6bf9d7c54b40b9a9`
- Canonical `origin/main` SHA at the start gate:
  `862940b5cb688d728ba101fbaad44b96324799c2`
- UMS-01A commit: `bb8e877a55c78c2ede9be31c6bf9d7c54b40b9a9`
- Previous migration revision: `c3d9e4f6a8b1`
- New migration revision and sole repository head: `d4e8f1a2b6c9`
- Final Git SHA: unavailable; the harness denied creation of `.git/index.lock`,
  so the validated packet remains uncommitted
- Live private-preview inspection: not performed
- Live private-preview mutation: not authorized and not performed

The unrelated pre-existing Pi fixture remained outside task scope.

## ADR impact

This slice implements accepted doctrine without changing it:

- ADR-005: account/user isolation remains the authority boundary.
- ADR-076: Project identity, lifecycle, and account-scoped built-in roles remain
  stable.
- ADR-081: canonical `projects.user_id` is reconciled only from its accepted
  durable thread-relationship evidence rule.
- ADR-084: this advances, but does not close, the Project-ownership prerequisite
  for Project-scoped unified memory.

No ADR was created, renumbered, superseded, or edited.

## Evidence algorithm

The migration reads all Projects first and rejects any surviving
`__codexify_project_owner__` description envelope with
`project_ownership_reconciliation_precondition_failed`. Such an envelope means
the UMS-01A authority cleanup has not converged, so UMS-01B does not reinterpret
it as ownership evidence.

It then selects every Project whose exact canonical owner value is `local` and
reads every persisted `chat_threads` row whose `project_id` references one of
those Projects. Request-time visibility, archive, active-thread, logged-in-user,
UI, and frontend filters do not participate.

A candidate is reconcilable exactly when:

```text
referencing thread count >= 1
AND distinct exact chat_threads.user_id values == {one value}
AND that value != 'local'
AND that value exists in users.id
AND the proposed (user_id, system_role) does not collide
    with an existing or simultaneously proposed built-in role
```

The migration does not trim, case-fold, vote, order, infer from names or roles,
or use request/operator identity. Multiple threads are acceptable only when all
carry the same exact owner value.

## Classifications and failure tokens

The exact classifications are:

| Token | Meaning |
| --- | --- |
| `reconcilable_single_thread_owner` | one exact non-local canonical owner across one or more referencing threads |
| `unresolved_no_referencing_threads` | no persisted thread relationship supplies owner evidence |
| `unresolved_local_thread_owner` | every referencing thread still names `local` |
| `unresolved_mixed_local_and_non_local_thread_owners` | `local` and at least one non-local owner both occur |
| `unresolved_multiple_thread_owners` | multiple distinct non-local owners occur |
| `unresolved_invalid_thread_owner` | an owner value is non-string, empty, or not exact because of surrounding whitespace |
| `unresolved_missing_target_user` | the sole non-local owner is absent from `users.id` |
| `unresolved_project_constraint_conflict` | reassignment would collide with account-scoped built-in role uniqueness |

Any unresolved candidate aborts with
`project_ownership_reconciliation_unresolved`. Diagnostic payloads contain only
bounded reason counts and Project IDs; they do not include descriptions,
messages, thread content, credentials, or unrelated account data.

## Atomicity and constraint safety

The migration has two logical phases in one Alembic transaction:

1. classify every `local` candidate and preflight the complete owner/role map;
2. only when all candidates are reconcilable, update each row with both its ID
   and `user_id = 'local'` in the predicate.

The always-on test places a reconcilable candidate before an unresolved one and
proves that the failure occurs with zero updates. A changed candidate produces
a non-one row count and aborts, allowing the migration transaction to roll back.
The final assertion requires zero remaining `local` Project owners.

Role preflight checks both canonical non-local Projects and all proposed
reassignments for duplicate `(user_id, system_role)` values when `system_role`
is non-null. It does not merge, rename, delete, or alter either Project to evade
a conflict.

## Preservation and isolation

The migration statement changes only `projects.user_id`. Its PostgreSQL fixtures
are prepared to compare and preserve:

- Project IDs, exact descriptions, and archive/lifecycle state;
- thread IDs and exact thread owners;
- thread-to-Project relationships;
- canonical Projects belonging to a second account; and
- the absence of fabricated target users.

Description equality is additionally checked by character length and SHA-256
digest in the successful synthetic chain fixture. No private description,
message, Project name, or real account identifier is reproduced here.

All 77 required runtime regressions passed, including Project list/direct
authorization, Project lifecycle, Media's Project guard, authenticated account
ownership consistency, and bearer-compatibility coverage. This is focused
account-isolation proof; it is not live private-preview migration proof.

## Downgrade posture

Downgrade is an explicit non-fabricating no-op. Once canonical evidence has
resolved ownership, the migration does not rewrite the owner to `local`, rebuild
a description envelope, or change thread ownership. Reintroducing ambiguity
would contradict ADR-081 rather than restore valid historical state.

## Validation evidence

Completed in this harness:

```text
.venv/bin/python -m py_compile \
  guardian/db/migrations/versions/d4e8f1a2b6c9_reconcile_legacy_local_project_owners.py \
  tests/migration/test_project_ownership_local_reconciliation.py
PASS

.venv/bin/ruff check \
  guardian/db/migrations/versions/d4e8f1a2b6c9_reconcile_legacy_local_project_owners.py \
  tests/migration/test_project_ownership_local_reconciliation.py
PASS

DATABASE_URL= TEST_DATABASE_URL= .venv/bin/pytest -v \
  tests/migration/test_project_ownership_runtime_convergence.py \
  tests/migration/test_project_ownership_local_reconciliation.py
15 passed, 12 skipped

DATABASE_URL= TEST_DATABASE_URL= .venv/bin/pytest -v tests/test_migrations.py
1 skipped

.venv/bin/pytest -v \
  tests/core/test_project_ownership.py \
  tests/routes/test_projects_account_scope.py \
  tests/routes/test_media_routes.py \
  tests/routes/test_projects_routes.py \
  tests/routes/test_project_lifecycle.py \
  tests/identity/test_user_ownership_consistency.py \
  tests/routes/test_owner_resolution_bearer_compat.py
77 passed

.venv/bin/python -m alembic -c backend/alembic.ini heads
d4e8f1a2b6c9 (head)

python scripts/validate_docs.py
PASS

git diff --check -- <the two tracked UMS-01B documentation paths>
PASS

rg trailing-whitespace scan across all five UMS-01B-owned paths
PASS
```

The ownership-migration command contains three always-on UMS-01A unit tests,
12 always-on UMS-01B unit tests, two UMS-01A PostgreSQL cases, and ten UMS-01B
PostgreSQL cases. All 15 unit tests passed. All 12 PostgreSQL cases skipped only
because no disposable database URL was available. The general migration test
also skipped for that reason. A skip is not counted as migration proof.

## Disposable PostgreSQL limitation

Both permitted local provisioning paths were attempted:

- Docker 29.7.2 reported permission denied for the user Docker socket.
- Homebrew PostgreSQL 17.6 `initdb` under `/private/tmp` failed during its
  bootstrap because the sandbox denied `shmget`. A second attempt requested
  both `shared_memory_type=mmap` and `dynamic_shared_memory_type=mmap`; bootstrap
  still selected System V shared memory and failed at the same syscall.

`initdb` removed each incomplete data directory, and the empty temporary parent
directories were removed. No live or persistent database was used as a
substitute. `alembic current` was not run because no disposable target existed
and it was not redirected to any live database.

To complete the residual proof in a database-capable environment, set either
`TEST_DATABASE_URL` or `DATABASE_URL` to an explicitly disposable PostgreSQL
server on which the test principal may create and drop temporary databases,
then run:

```bash
.venv/bin/pytest -v \
  tests/migration/test_project_ownership_runtime_convergence.py \
  tests/migration/test_project_ownership_local_reconciliation.py

.venv/bin/pytest -v tests/test_migrations.py

.venv/bin/python -m alembic -c backend/alembic.ini heads
.venv/bin/python -m alembic -c backend/alembic.ini current
```

The ownership command must report zero environment-driven PostgreSQL skips,
the general migration test must execute rather than skip, `heads` must report
only `d4e8f1a2b6c9`, and `current` must report that same revision on the
disposable target.

Documentation validation, the path-scoped tracked diff check, and a
trailing-whitespace scan across all five task-owned paths passed. The three new
paths could not enter Git's staged diff because exact-path staging then failed:
Git could not create `.git/index.lock` under this harness. No file was staged,
no commit was created, and the unrelated Pi fixture remains unstaged and
unmodified by this task.

## Residual gate

```text
UMS-01 PROJECT OWNERSHIP RUNTIME AUTHORITY: PROVEN IN UMS-01A
UMS-01 MATCHING-ENVELOPE MIGRATION: UNIT-PROVEN; DISPOSABLE POSTGRES EXECUTION BLOCKED BY HARNESS SHARED-MEMORY POLICY
UMS-01 LEGACY LOCAL OWNER RECONCILIATION: IMPLEMENTED; UNIT-PROVEN
UMS-01 MIGRATION CHAIN: REAL POSTGRESQL EXECUTION BLOCKED BY HARNESS
UMS-01 CAMPAIGN GATE: OPEN
UMS-02: NOT AUTHORIZED TO START
```

No Unified Memory Store schema, API, Vault, command, classifier, recall grant,
importer, persona-subject, Personal Facts, or MemoryOS implementation is part of
this slice.
