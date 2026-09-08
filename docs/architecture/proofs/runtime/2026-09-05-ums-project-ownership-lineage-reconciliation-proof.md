# UMS-01R Project Ownership Migration Lineage Reconciliation Proof

Date: 2026-09-05

Evidence class: static migration graph and focused local test proof. This is
not PostgreSQL migration execution, private-preview application, or release
qualification. Git staging and commit are deferred to the operator because
this harness has read-only Git metadata.

## Authority and scope

The authorized continuation reconciles migration lineage only, under
[ADR-081](../../adr/081-project-ownership-authority.md),
[ADR-082](../../adr/082-persona-profile-manifest-and-binding-authority.md), and
[ADR-084](../../adr/084-unified-account-owned-memory-store.md).
[Current state](../../00-current-state.md) remains release authority.

`projects.user_id` remains Project ownership authority; Persona environmental
and account binding remains server-owned. The operator's rebase handoff is
evidence of the manual operation, not proof of database migration execution.
Only repository source and documentation become durable in this slice, through
the operator's eventual scoped commit. No runtime, account, or network authority
changes. No new ADR is required.

## Git reconciliation

Old base: `862940b5cb688d728ba101fbaad44b96324799c2`.

Canonical base: `3410fed3fb376eabc0fd6d03da5ec8b9394d611c`.

| Slice | Old commit | Rebased commit |
| --- | --- | --- |
| UMS-00 | `9f1277cd40104ce6f74ac8554736fe71e7f22e23` | `4d2de549efa7b96a46a26ccf576e1df12fd3cb4d` |
| UMS-01A | `bb8e877a55c78c2ede9be31c6bf9d7c54b40b9a9` | `8c718643880c9b167fc56b06e19debb28a6a9de5` |
| UMS-01B | `97c476002eda9cf358d6e09c15b904e9f0344dc2` | `ea4637e8d21a08c6fa40cfc4759c45a8e747b9ce` |

The operator reports the manual rebase completed with no conflicts and restored
the Pi fixture. Read-only `git rev-parse HEAD origin/main` and
`git log -4 --format='%H %P %s'` verified the current HEAD, canonical base,
and exact parent chain through the three rebased commits. No second rebase,
stash, staging, commit, push, or merge was performed by this continuation.

Reconciliation commit: pending operator handoff; this receipt describes the
working-tree changes on the rebased UMS-01B HEAD above.

## Final migration chain

```text
b2c8d0e3f5a7
    ↓
c3d9e1f4a6b8
    ↓
d4e0f2a5b7c9
    ↓
c3d9e4f6a8b1
    ↓
d4e8f1a2b6c9 (head)
```

Only UMS-01A's predecessor and matching `Revises` header changed. Its migration
body is unchanged. The UMS-01A test's `PREVIOUS_REVISION` and the UMS-01B
full-chain test's `PRE_UMS_01_REVISION` now name `d4e0f2a5b7c9`.
UMS-01B's immediate predecessor remains `c3d9e4f6a8b1`; its migration file is
unchanged. No assertion was weakened, revision renumbered, or merge revision
created. Both Persona migrations and both Persona migration test files remain
unchanged. Historical UMS-01A/01B proof receipts were not rewritten.

## Validation

Commands ran from the repository root using the existing `.venv`.

```bash
.venv/bin/python -m alembic -c backend/alembic.ini heads
.venv/bin/python -m alembic -c backend/alembic.ini history
```

Both passed. Heads returned exactly `d4e8f1a2b6c9 (head)`; history showed the
four consecutive edges above. Earlier historical mergepoints remain unchanged.
These graph commands do not execute migration upgrades or connect to a database.

```bash
DATABASE_URL= TEST_DATABASE_URL= \
.venv/bin/pytest -v \
  tests/migration/test_persona_profile_manifest_binding_migration.py \
  tests/migration/test_thread_persona_profile_revision_migration.py \
  tests/migration/test_project_ownership_runtime_convergence.py \
  tests/migration/test_project_ownership_local_reconciliation.py
```

Passed: **15 passed, 18 skipped in 0.53s**, no failures. By file: Persona
manifest/binding 4 skipped; Persona thread revision 2 skipped; UMS-01A 3 passed
and 2 skipped; UMS-01B 12 passed and 10 skipped. PostgreSQL fixtures skip before
connecting when neither database URL is set. All database-dependent tests were
skipped; this run does not prove PostgreSQL compatibility or Persona migration
execution. UMS-01Q owns that remaining qualification.

```bash
DATABASE_URL= TEST_DATABASE_URL= \
.venv/bin/pytest -v \
  tests/core/test_project_ownership.py \
  tests/routes/test_projects_account_scope.py \
  tests/routes/test_media_routes.py
```

Passed: **47 passed in 5.25s** (8 ownership, 9 Project account scope, 30 Media).
These are focused local tests, not live database or browser proof.

```bash
.venv/bin/python -m py_compile \
  guardian/db/migrations/versions/c3d9e4f6a8b1_remove_project_description_owner_authority.py \
  guardian/db/migrations/versions/d4e8f1a2b6c9_reconcile_legacy_local_project_owners.py
.venv/bin/python scripts/validate_docs.py
git diff --check -- . ':!tests/pi/fixtures/fake_pi_package/package.json'
```

Compilation and documentation validation passed. The diff check passed over
all paths except the unchanged pre-existing Pi fixture. The new receipt was
also checked separately for trailing whitespace and conflict markers.

## Working-tree and database boundary

Full `git status --short` failed because the Pi fixture's Git LFS clean filter
attempted to create `.git/lfs/tmp/...`, denied by the harness. No filter or
permission configuration was changed. Read-only status and diff inspection
exclude that one known fixture to avoid repeating the Git metadata write.
The index is empty (`git diff --cached --name-only`).

The fixture's before/after SHA-256 is
`1589b9d20d0fd6e5865abe5b1f23bd3867a339c7ac3806dac584c2ceacbff93b`.
Its content remains untouched and unstaged. The operator must inspect its
ordinary Git status in a terminal where the LFS clean filter can run.

No live or private-preview database was contacted or migrated. Database URL
variables were empty for both pytest commands, and the repository test defaults
disable dotenv loading. No disposable PostgreSQL service was started. No
private-preview state or supported-release boundary changed.

## Checkpoint

```text
UMS-01A: IMPLEMENTED
UMS-01B: IMPLEMENTED
UMS-01 MIGRATION LINEAGE: RECONCILED WITH PERSONA STUDIO
UMS-01Q POSTGRESQL QUALIFICATION: PENDING
UMS-01 CAMPAIGN GATE: OPEN
UMS-02: NOT AUTHORIZED TO START
```
