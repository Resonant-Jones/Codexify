# Stage 2K.1 RepositoryBinding Authority Proof

## Date

2026-08-12

## Verdict

`PROVEN-TEST` — Stage 2K.1 establishes the scoped storage and internal
authority layer only. It does not establish a repository discovery, import,
chat, provider, or supported-runtime capability.

## Diagnostic Outcome

`STAGE2K1_COMPLETED`

## Original Stage 2K-R1 Commit

`ca861c47411c8571aff86125ae52526ecdb4d6f9`

## Stage 2K-R1 Replay Commit

`61ea03c52c75785c7269575ce87cafd67542612a`

## Branch/Worktree

- Branch: `codex/stage2k1-repository-binding-authority`
- Worktree: `/private/tmp/codexify-stage2k1-repository-binding-authority`

## Remote Main at Start

`origin/main` resolved to
`a36a8286e0cd7ca7ac035bd1273b38c804bc6317`, the issuance SHA. The Stage
2K-R1 replay commit has that revision as its merge base.

## Remote Main Reconciliation

`git fetch origin` completed before implementation continuation. `origin/main`
remained at the issuance SHA, with no later relevant authority or storage
boundary change to reconcile. ADR-065 and the repository-onboarding authority
contract are present through the accepted R1 replay rather than a remote-main
advancement.

## Governing ADRs

- ADR-065, Guardian-Managed Repository Onboarding Boundary — primary.
- ADR-061, Capability-Oriented Mesh Architecture — binding storage is not
  capability advertisement or execution authority.
- ADR-005, account scoping and user isolation.
- ADR-020 and ADR-024, Guardian-issued filesystem scope and the distinction
  between connected source evidence and authorized access.

## ADR Impact

`Aligned with existing ADR(s)`. No ADR was changed. The implementation adds
the accepted, internal `Account -> Project -> RepositoryBinding -> working-tree
root` resolution seam without widening any capability or release claim.

## Current Truth Before

- Projects were durable Postgres records with canonical account ownership.
- No durable `RepositoryBinding` table or Project repository authority existed.
- `WorkspaceRootManager.detect_project_root()` and worktree/env paths were
  convenience or campaign machinery, not Project authority.
- `General` was a default Project only, without implicit filesystem authority.
- No repository scanner, import/link route, `repository.search`, ordinary-chat
  repository capability, or model filesystem authority existed.

## Pre-Task Alembic Head

`c1a2b3c4d5e6`

## Ancestral Continuity Revision Confirmation

`e8d1f2a3b4c5` was verified ancestral to the new head. It is not a second
parent of the Stage 2K.1 migration.

## RepositoryBinding Migration Revision

`6e2b9c4a7d1f`

## RepositoryBinding Down Revision

`c1a2b3c4d5e6`

## Post-Task Alembic Head

`6e2b9c4a7d1f` is the sole Alembic head.

## Migration Graph Regression Update

The existing uniqueness/lineage regression retains all historical assertions,
adds the RepositoryBinding direct-parent assertion, and advances the sole-head
assertion from `c1a2b3c4d5e6` to `6e2b9c4a7d1f`. No historical migration was
rewritten and no merge migration was created.

## Guardian Projects Directory Configuration

`guardian.core.config.Settings` now declares exactly the canonical
`CODEXIFY_GUARDIAN_PROJECTS_DIR` operator/instance setting. It has no
compatibility aliases and Settings import creates no directory.

## Guardian Projects Directory Default Resolution

An unset or blank setting resolves to no managed root and callers that need a
managed root fail closed. The resolver requires an explicitly configured
absolute path, expands and canonicalizes it, rejects a file, and only creates
the directory when an authority-side caller explicitly requests creation. It
does not derive a root from cwd, `DATA_STORAGE_PATH`, the application checkout,
home, or a container default.

## RepositoryBinding Schema

The `repository_bindings` table stores an opaque binding ID, non-null
`project_id` with `ON DELETE CASCADE`, constrained `source_class`, canonical
absolute root, active flag, bounded JSONB provenance, and timestamps. It has a
Postgres partial unique index on `project_id WHERE is_active IS TRUE`; inactive
history may coexist. The migration has no backfill or Project mutation.

## Project Ownership Resolution

Internal creation and resolution load the Project, compare its canonical
`user_id` with the authenticated account, and fail closed on a missing Project
or ownership mismatch. The caller transaction is flushed but never committed
by binding creation.

## Managed Root Containment

`guardian_managed` working-tree roots must be canonical children of the
configured Guardian Projects Directory. Equal-to-root, traversal, and symlink
escape cases fail closed. Managed child paths derive only from immutable Project
IDs; names do not participate in filesystem identity.

## External Linked Root Behavior

`external_linked` bindings may validate a canonical Git working-tree root
outside the Guardian Projects Directory. They remain account/Project scoped and
must still be explicitly active bindings.

## Git Working-Tree Validation

Validation canonicalizes the requested path, requires an existing directory,
and runs only argv-based `git -C <root> rev-parse --show-toplevel` with
`GIT_OPTIONAL_LOCKS=0` and a bounded timeout. It accepts standard checkouts and
valid linked worktrees, while rejecting missing paths, non-Git directories,
stale worktrees, and nested subdirectories whose Git top level differs from the
requested root.

## Active Binding Cardinality

Creation rejects a Project with an existing active binding. The database partial
unique index independently enforces at most one active binding per Project.

## Missing Binding Failure

Repository-less Projects, including `General`, remain valid. Resolution fails
closed when no active binding exists.

## Ambiguous Binding Failure

The resolver rejects more than one active binding instead of selecting one.
The database prevents this state through its partial unique index; resolver
coverage preserves the fail-closed behavior for inconsistent historical or
manually corrupted data.

## Invalid/Stale Root Failure

Resolution fails closed when a stored path is absent, no longer an exact Git
working-tree root, no longer canonical, or escapes the managed root for its
source class.

## Explicit No-Fallback Proof

The authority module contains no `detect_project_root()` or
`WorkspaceRootManager` use and does not read
`CODEXIFY_WORKTREE_REPO_PATH`. Unit coverage proves no cwd fallback and a
relative configured directory is rejected rather than cwd-resolved.

## General Project Behavior

No migration or helper creates a binding for an existing Project or `General`.
Unit coverage confirms a Project named `General` has no implicit authority.

## Unit Test Results

`pytest -v tests/core/test_repository_authority.py` — `32 passed`.

The suite uses temporary Git repositories and linked worktrees, never the
Codexify checkout as test authority. It covers deterministic directory
resolution, identity-derived managed paths, symlink/traversal escape, exact Git
root validation, ownership, source classes, active/inactive/ambiguous binding
states, no-fallback assertions, bounded provenance, and no implicit commit.

## Migration Round-Trip Results

`TEST_DATABASE_URL=... pytest -v tests/migration/test_repository_bindings_migration.py`
— `1 passed` against a newly started disposable Postgres 15 container and a
uniquely named temporary database. The test upgraded from
`c1a2b3c4d5e6`, proved the new table absent at baseline, preserved an existing
User/Project, upgraded to `6e2b9c4a7d1f`, verified columns/FK/check/partial
index/no backfill, exercised active and inactive cardinality behavior,
downgraded to baseline, and upgraded to head again.

## Existing Project Preservation

The round-trip test records the pre-existing Project fields before upgrade,
proves no binding was auto-created, verifies the Project unchanged after
upgrade and after downgrade, and then re-upgrades the schema.

## Alembic Graph Test Results

`pytest -v tests/migration/test_alembic_revision_uniqueness.py` — `1 passed`.

`python -m alembic -c backend/alembic.ini heads` reported only
`6e2b9c4a7d1f (head)`.

## Architecture Test Results

`pytest -v tests/architecture` — `394 passed`.

Scoped Project regressions also passed:

`pytest -v tests/core/test_repository_authority.py tests/migration/test_alembic_revision_uniqueness.py tests/routes/test_projects_routes.py tests/routes/test_projects_account_scope.py tests/routes/test_route_user_scoping_invariant.py`
— `59 passed`.

## Docs Validation

`python3 scripts/validate_docs.py` — passed.

`make docs PYTHON=python3` — passed, including the diagram-freshness check.

## What Was Proven

- Durable, account-scoped Project-to-working-tree binding storage exists with
  a single active-binding invariant.
- Guardian-managed and external-linked source classes remain distinct.
- Internal creation and resolution fail closed across ownership, cardinality,
  path containment, and exact Git-root validation boundaries.
- The migration upgrades and downgrades an existing Project database without
  adding a binding or altering that Project.
- The Alembic graph remains single-headed at the expected revision.

## What Was Not Proven

- No external repository scanner exists.
- No coding-agent discovery exists.
- No automatic import/link flow exists.
- No repository files are moved, copied, cloned, initialized, or deleted.
- No Project creation route creates repositories.
- No `repository.search` command exists.
- No ordinary-chat repository capability exists.
- No model receives filesystem authority.
- No provider inference occurred.
- No supported runtime was restarted.

## Documentation Follow-Through

This receipt is the authorized documentation follow-through. ADR-065, the ADR
index, repository-onboarding contract, `00-current-state.md`, and
`data-and-storage.md` were intentionally not modified.

## Final File Scope

- `guardian/core/config.py`
- `guardian/core/repository_authority.py`
- `guardian/db/models.py`
- `guardian/db/migrations/versions/6e2b9c4a7d1f_add_repository_bindings.py`
- `tests/core/test_repository_authority.py`
- `tests/migration/test_repository_bindings_migration.py`
- `tests/migration/test_alembic_revision_uniqueness.py`
- `docs/architecture/proofs/2026-08-12-stage2k1-repository-binding-authority-proof.md`

## Commit

Implementation commit: `6101fc0ef` (`Establish Project repository binding authority`).
The proof receipt is committed separately after its final documentation
validation.
