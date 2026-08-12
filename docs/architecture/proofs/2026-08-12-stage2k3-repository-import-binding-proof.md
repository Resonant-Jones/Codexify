# Stage 2K.3 Explicit Repository Import and Project Binding Proof

## Date

2026-08-12

## Verdict

PASS — the explicit, authenticated import path is established as a bounded
Guardian/API mutation. It grants no model, tool, provider, Workspace, or
runtime authority beyond the durable external_linked Project binding.

## Diagnostic Outcome

EXPLICIT_REPOSITORY_IMPORT_ESTABLISHED

## Base Commit

aeb286e5b8b5ea582fa10e1c3aeb8576211ee813 (origin/main at task start).

## Branch/Worktree

- Branch: codex/stage2k3-repository-import-binding
- Worktree: /private/tmp/codexify-stage2k3-repository-import-binding

## Governing ADRs

- ADR-065, Guardian-Managed Repository Onboarding Boundary — primary.
- ADR-061, Capability-Oriented Mesh Architecture.
- ADR-005, account scoping and user isolation.
- ADR-020 and ADR-024, Guardian-issued filesystem scope and evidence versus
  authority boundaries.

## ADR Impact

Aligned with existing ADR(s). No ADR changed. The implementation executes the
explicit import/link transition selected by ADR-065 without changing discovery
doctrine, binding doctrine, capability advertisement, or execution.

## Stage 2K.1 Prerequisite

The unchanged Stage 2K.1 authority seam still owns exact Git-root validation,
account/Project checks, one-active-binding enforcement, bounded provenance,
and external_linked binding creation without commit.

## Stage 2K.2 Prerequisite

The unchanged Stage 2K.2 seam still requires an AuthorizedDiscoveryRoot, uses
bounded read-only discovery, and returns only ephemeral discovery_candidate
observations.

## Current Truth Before

RepositoryBinding storage and typed candidate discovery existed, but no
authenticated API could promote a candidate to Project authority. Workspace
had no accepted durable Project-membership seam.

## Explicit Authentication Boundary

POST /api/projects/repository-import resolves ownership only through
RequestUserScope and the existing canonical account helper. Client-provided
account or user identity is neither accepted nor used.

## Import API Surface

The API-only route accepts discovery_root, candidate_relative_path, optional
project_id, optional project_name, and optional project_description. Its
response contains only ok, opaque binding and Project IDs, created/reused
flags, and the fixed external_linked class.

## Discovery Root Authority

The service authorizes only the explicitly selected authenticated-user root
through authorize_explicit_discovery_root(...). It has no default root, cwd,
home, worktree, or nearest-Git fallback.

## Candidate Relative Selection

The selector is a normalized POSIX relative token. A root-dot selector and
safe nested paths are supported; absolute, empty, backslash, and traversal
selectors fail closed. It is compared only with fresh candidate
root_relative_path values.

## Fresh Discovery Proof

Every import reruns discover_repository_candidates(...) after root
authorization and selects exactly one candidate. Missing or ambiguous
candidate selection fails closed.

## Import-Time Revalidation

The selected candidate must retain discovery_candidate source class and the
authenticated actor. The service reruns Stage 2K.1
validate_git_working_tree_root(...) and requires exact equality with the
candidate's observed canonical root.

## Project Target Modes

Exactly one mode is valid: an owned existing project_id, or a trimmed,
non-empty new project_name. Ambiguous, absent, and blank targets are rejected.

## New Project Ownership

New Projects are inserted directly in the caller-owned SQLAlchemy Session with
Project.user_id set to the authenticated account. Names are bounded, and
descriptions are bounded and reject the canonical repository path.

## Existing Project Ownership

Existing targets are loaded in the same Session and must belong to the
authenticated account; cross-account Project targets fail with the bounded
403 route outcome.

## RepositoryBinding Creation

The service creates the binding only through unchanged
create_repository_binding(...), after fresh discovery/revalidation and
duplicate-root checks. The core service does not commit.

## External Linked Source Class

Every new binding uses only the Stage 2K.1 canonical external_linked source
class. No request field can select or override it.

## Duplicate Canonical Root Behavior

Active bindings are checked by exact canonical working-tree root before any
Project or binding creation. A different owned Project, another account, or
multiple existing active bindings fails closed.

## Idempotency Behavior

The same canonical root for the same owned Project returns the existing
binding. A new-Project request for a root already linked by that account also
reuses the existing Project/binding without creating a second Project.

## Cross-Account Conflict Behavior

A root bound under another account produces generic 409 conflict output with
no foreign account, Project, or binding information.

## Ambiguous Authority Behavior

Multiple active bindings already resolving to one canonical root raise the
explicit ambiguity error and create no additional authority.

## Transaction Ownership

repository_import.py performs Session flushes only. The Projects API route
opens one chatlog_db.get_session() context and commits exactly once only after
successful import; all known and unexpected failures roll back.

## Commit/Rollback Proof

The disposable Postgres test observed new Project and binding rows before
commit, then observed them from a fresh Session after commit. A separate
import followed by caller rollback left neither generated Project nor binding
in a fresh Session.

## Postgres Integration Proof

TEST_DATABASE_URL=... pytest -v
tests/integration/test_repository_import_postgres.py ran against a dedicated
loopback-only disposable Postgres 15 container and a uniquely named temporary
database. The test passed, then dropped that database; the temporary container
was stopped and removed. No supported, preview, or production database was
used.

## Provenance Boundary

Binding provenance contains only repository_candidate_import, external_link,
discovery provenance class, Git evidence kind, and observed timestamp. It
stores no discovery root, canonical root duplication, selector, remote,
prompt, credential, or source content.

## Filesystem Immutability

Core coverage uses temporary Git fixtures outside the Codexify checkout,
records representative bytes, mtime, HEAD, and branch before import, and
proves all remain unchanged afterward.

## Git Mutation Denial

The import seam delegates only exact Stage 2K.1 Git validation. It contains no
remote, fetch, pull, checkout, clone, init, status, move, copy, or delete
operation.

## Workspace Projection Deferral

WORKSPACE_PROJECT_PROJECTION_DEFERRED — Workspace Project projection is
deferred because no canonical durable Workspace-to-Project membership seam
exists in the current accepted runtime.

## No Automatic Import Proof

Only the new authenticated API route calls the explicit-import entry point.
No startup, Project creation, thread creation, scanner, provider, chat,
Command Bus, or worker path calls it.

## No Tool/Model Exposure Proof

Repository import is absent from capability catalogs, model schemas, provider
adapters, command definitions, ordinary-chat preparation, and completion
services. No model parameter exposes discovery or canonical repository paths.

## Alembic Head Result

Before and after this no-schema slice, alembic -c backend/alembic.ini heads
reported exactly 6e2b9c4a7d1f (head).

## Core Test Results

pytest -v tests/core/test_repository_import.py — 25 passed.

## Route Test Results

pytest -v tests/routes/test_project_repository_import.py — 10 passed.

## Existing Project Regression Results

pytest -v tests/routes/test_projects_account_scope.py — 6 passed.

## Stage 2K.1 Regression Results

pytest -v tests/core/test_repository_authority.py — 32 passed.

## Stage 2K.2 Regression Results

pytest -v tests/core/test_repository_discovery.py — 39 passed.

## Architecture Test Results

pytest -v tests/architecture — 394 passed.

## Docs Validation

python3 scripts/validate_docs.py passed. make docs PYTHON=python3 passed,
including the repository diagram-freshness check.

## What Was Proven

An authenticated Codexify user can now explicitly promote one freshly
rediscovered and revalidated external Git working-tree candidate into durable
Project-to-RepositoryBinding authority, atomically creating or reusing the
owned Project while leaving repository files in place and granting no
repository capability to the model.

## What Was Not Proven

- No automatic coding-agent repository import exists.
- No background repository onboarding exists.
- No repository is moved into Guardian Projects Directory.
- No Guardian-managed repository creation exists.
- No detach, rebind, or replacement flow exists.
- No durable Workspace-to-Project projection was added.
- No repository.search Command Bus capability exists.
- No ordinary-chat repository capability exists.
- No model receives repository/discovery host paths.
- No provider inference occurred.
- No supported runtime was restarted.

## Documentation Follow-Through

This proof receipt is the authorized documentation follow-through. ADR-065,
the repository-onboarding authority contract, current state, and schema/docs
contracts remain intentionally unchanged.

## Final File Scope

Only the six task-authorized paths are changed: the core import service, the
Projects API route, core/route/Postgres tests, and this receipt.

## Commit

The scoped commit is recorded in the final Git closeout for this receipt.
