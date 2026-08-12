# Stage 2K.4 Repository Search Command Bus Proof

## Date

2026-08-12

## Verdict

PASS — one bounded read-only repository search Command Bus command is
implemented. It remains a raw API/Command Bus capability and is not exposed to
ordinary-chat models.

## Diagnostic Outcome

REPOSITORY_SEARCH_COMMAND_ESTABLISHED

## Base Commit

a146de133ae2e5e11a2fdc38479ca26b5cab3952, the verified origin/main
baseline at task start.

## Branch/Worktree

- Branch: codex/stage2k4-repository-search
- Worktree: /private/tmp/codexify-stage2k4-repository-search

## Governing ADRs

- ADR-065, Guardian-Managed Repository Onboarding Boundary — primary.
- ADR-005, account/user isolation.
- ADR-020 and ADR-024, Guardian-issued filesystem scope and authorized
  crossing doctrine.
- ADR-061, capability authorization boundaries.
- Current Command Bus and bounded tool-turn contracts.

## ADR Impact

Aligned with existing ADR(s). No ADR, onboarding contract, current-state
document, schema, or migration changed.

## Stage 2K.1 Prerequisite

The unchanged authority seam resolves a Project only through one active binding
and revalidates exact Git working-tree identity, ownership, cardinality,
managed-root containment, and stale/missing failure cases.

## Stage 2K.2 Prerequisite

The unchanged bounded discovery seam remains non-authorizing; a discovery
candidate cannot reach this search path without durable binding authority.

## Stage 2K.3 Prerequisite

The unchanged explicit import seam remains the only candidate-to-binding
transition. Search neither discovers nor imports repositories.

## Current Truth Before

Stage 2K.1 through 2K.3 were canonical, but no repository search engine,
route, or Command Bus command existed. Ordinary chat exposed health only.

## Command Identity

The Projects API declares operation ID repository.search. The current
OpenAPI-backed manifest derives command ID op::repository.search.

## Command Manifest Derivation

The command is not manually registered. Its derived raw alias is
route::GET::/api/projects/{project_id}/repository/search. The manifest proves
GET, read, read_only, safe, and no approval mode.

## Authentication Boundary

The API route derives the account only from RequestUserScope and the existing
account helper. The request contains no account, user, binding, or repository
root parameter.

## Project-to-Binding Resolution

The public search service first calls resolve_project_repository_binding with
the authenticated account and requested Project. No Path-only public authority
entry point exists.

## Root Authority Proof

The internal engine requires a real ResolvedRepositoryBinding and accepts its
canonical root only after Stage 2K.1 revalidation. There is no cwd,
nearest-Git, worktree environment, checkout, or discovery-candidate fallback.

## Query Semantics

Search is literal, case-insensitive Unicode casefold substring matching. It
trims outer whitespace and rejects blank, NUL, CR, LF, and over-256-character
queries. Regex and shell syntax have no special meaning.

## Search Bounds

- Query: 256 Unicode characters.
- Returned matches: 20.
- Candidate file entries: 5,000.
- Git listing output: 2 MiB.
- Individual file: 1 MiB.
- Aggregate bytes read: 32 MiB.
- Snippet: 400 Unicode characters.
- Relative path: 512 Unicode characters.
- Entire authority/search operation: 5.0 seconds.

Only route result limit 1 through 20 is caller-selectable. No public caller can
widen the remaining limits.

## Git Enumeration Strategy

The engine streams argv-only Git ls-files with cached, untracked, standard
ignore, and NUL-output flags. It sets GIT_OPTIONAL_LOCKS=0, uses no shell, and
never uses unbounded captured output.

## Ignored File Behavior

Git standard-ignore enumeration excludes ignored files. Core coverage proves an
ignored matching file produces no result while an untracked non-ignored file
does.

## Secret-Risk Path Behavior

The engine denies .env and .env.* names, standard credential/private-key
basenames, and PEM/key/certificate-style suffixes before opening content.

## Symlink/Containment Behavior

Symlink files are skipped. Strict resolution and relative-to-root verification
reject missing, escaping, non-regular, or outside-root paths before reading.

## Binary/Text Behavior

Files above the individual-size bound, NUL-containing content, and invalid
UTF-8 produce no snippets and increment bounded skip counters.

## Match/Snippet Bounds

Matches carry only relative POSIX path, one-based line number, and at most 400
characters from the matched source line. Long-line windows deterministically
contain the first literal match and no neighboring lines.

## Result Privacy

Result serialization contains no binding ID, account ID, canonical root,
repository root, discovery root, mount, cwd, or remote. Tests recursively
check the response and Command Bus inline result shape for path leakage.

## Repository Isolation

The disposable Postgres proof binds Project A only to repository A while a
second repository has distinct marker text. A Project A search finds only the
bound repository-relative fixture result.

## Cross-Account Denial

The same integration proof rejects account B searching account A's Project;
the route maps ownership mismatch to bounded 403 output.

## Missing/Stale Binding Denial

Repository-less Projects and a binding whose fixture root was moved both fail
closed as repository search unavailable.

## Filesystem Immutability

Core and Postgres fixtures record representative bytes before search and prove
them unchanged afterward.

## Git Mutation Denial

Fixture HEAD and active branch/ref remain unchanged. The implementation invokes
only Stage 2K.1 rev-parse validation and Stage 2K.4 ls-files enumeration; it
does not run status, grep, fetch, pull, checkout, branch, remote, or any
mutating Git command.

## Database Read-Only Proof

The Postgres proof checks no new, dirty, or deleted ORM objects; Project and
binding snapshots and row counts are unchanged after search. The route never
commits or rolls back.

## Command Bus Invocation Proof

The Command Bus test invokes op::repository.search with Project path parameter
42 and query needle/limit 5. Exactly one loopback GET is emitted with those
path/query values, forwarded inbound authentication headers, and no body.

## CommandRun Lifecycle

The read-only invocation records run.created, run.started, and run.completed;
it is completed rather than confirmation-gated.

## Ordinary-Chat Non-Exposure Proof

When a manifest contains both health and repository search commands, the
unchanged ordinary-chat resolver returns health only and never returns
op::repository.search.

## No Legacy fs.search Proof

The final implementation contains no legacy fs.search, ToolIntent,
detect_project_root, cwd, or worktree-environment authority path.

## Alembic Head Result

Before and after this no-schema slice, the sole Alembic head is
6e2b9c4a7d1f.

## Core Test Results

pytest -v tests/core/test_repository_search.py — 22 passed.

## Route Test Results

pytest -v tests/routes/test_project_repository_search.py — 9 passed.

## Command Bus Test Results

pytest -v tests/routes/test_repository_search_command_bus.py — 3 passed.

## Postgres Integration Result

TEST_DATABASE_URL=... pytest -v
tests/integration/test_repository_search_postgres.py — 1 passed against a
dedicated loopback-only disposable Postgres 15 container and unique temporary
database. The test removed its database and the container was stopped/removed.

## Stage 2K.1 Regression Results

pytest -v tests/core/test_repository_authority.py — passed.

## Stage 2K.2 Regression Results

pytest -v tests/core/test_repository_discovery.py — passed.

## Stage 2K.3 Regression Results

pytest -v tests/core/test_repository_import.py and
pytest -v tests/routes/test_project_repository_import.py — passed.

## Command Bus Regression Results

tests/routes/test_command_bus_phase1_manifest.py and
tests/routes/test_command_bus_phase1_invoke.py — 10 passed.

## Architecture Test Results

pytest -v tests/architecture — 394 passed.

## Docs Validation

python3 scripts/validate_docs.py passed. make docs PYTHON=python3 passed,
including the diagram freshness check.

## What Was Proven

Codexify now has one bounded read-only repository.search Command Bus command
that derives its filesystem authority exclusively from the authenticated
Project's active RepositoryBinding and returns only bounded
repository-relative matches/snippets; the command remains unavailable to
ordinary-chat models until a separate Stage 2K.5 exposure decision.

## What Was Not Proven

- repository.search is not automatically advertised to ordinary chat;
- no current-thread-to-Project model argument hydration exists yet;
- no provider receives repository.search in this task;
- no model executed repository.search;
- no multi-command repository agent loop exists;
- no repository write capability exists;
- no repository file read-by-path capability exists;
- no repository mutation capability exists;
- no automatic import exists;
- no Workspace projection change exists;
- no supported runtime repository-search replay was performed;
- no provider inference occurred;
- no supported runtime was restarted.

## Documentation Follow-Through

This proof receipt is the authorized implementation evidence. ADR-065, the
repository-onboarding authority contract, and current-state remain unchanged.

## Final File Scope

Only the seven task-authorized paths are changed: the bounded core engine, the
Projects route, core/route/Command Bus/Postgres tests, and this receipt.

## Commit

The scoped commit hash is recorded in the final task closeout.
