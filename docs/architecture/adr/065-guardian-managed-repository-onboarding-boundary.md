# ADR-065: Guardian-Managed Repository Onboarding Boundary

## Status

Accepted

## Date

2026-08-11

## Scope and evidence posture

This is an architecture-impacting, docs-only Stage 2K-R1 decision. It defines
repository ownership, onboarding, and ordinary-chat authority before
repository storage, discovery, database work, Command Bus capability, or chat
exposure is implemented. It does not create a directory, scan a repository,
alter a runtime, or widen the supported beta promise.

At `5842019444a9782256cd75252a97e1539140465e`, current source establishes
account-scoped Projects and thread-to-Project association, but no canonical
Project-to-repository binding. Existing root detection and worktree code are
convenience or coding-campaign machinery, not ordinary-chat authority.

## Context

Stage 2K's intended first capability is a bounded repository search. Before a
request such as "Find where `_prepare_chat_tool_exposure` is implemented in
this project" can search, Guardian must resolve one already-authorized
repository for the current Project. A model must not select host paths, cwd,
or a nearby checkout as that authority.

Codexify must support repositories it creates under a Guardian-controlled root
and existing repositories users explicitly link without moving. Without an
explicit durable binding, discovery and operator path helpers could become
ambient tool authority.

## Decision

The canonical doctrine is:

> Discovery finds. Import registers. Guardian binds. Workspace projects. Tools
> consume only the binding.

A repository is available to Guardian only through an explicit,
account/project-owned `RepositoryBinding`. The binding resolves one authorized
working-tree root and is Guardian-owned durable authority state, never model
input or conversational context. Initial cardinality is one active binding per
Project. Projects may remain repository-less; `General` gets no implicit
repository or filesystem authority.

## Guardian Projects Directory

`Guardian Projects Directory` is the one logical parent root for repositories
created by Codexify or Guardian. It is internal authority data, not a model,
caller, Workspace, or provider parameter.

Current configuration has `DATA_STORAGE_PATH=./data`, vector-path
canonicalization, and application-local Compose storage, but no repository-root
setting or verified persistent host repository mount. This ADR therefore does
not invent a platform path or reuse the source checkout.

Stage 2K.1 shall add the logical operator/instance key
`CODEXIFY_GUARDIAN_PROJECTS_DIR` with this fail-closed rule:

1. A nonempty configured value is expanded, canonicalized to a real absolute
   host path, and validated as persistent and Guardian-managed before use.
2. A deployment may derive and explicitly configure it from a future persistent
   data-root policy. Relative/container-local `DATA_STORAGE_PATH` is not enough.
3. If no verified path is configured, repository-backed Project creation is
   unavailable with `needs_configuration`; no cwd, checkout, home, or
   container fallback exists.

Future Guardian code creates/manages only the selected root. Child directories
remain beneath it after canonicalization; traversal and symlink escape fail
closed. Opaque stable identity, not mutable Project display name, determines a
child path. A rename never relocates a repository.

## Repository-backed Projects and bindings

A **repository-backed Project** is a first-class Project with an active
RepositoryBinding. An ordinary Project remains valid without one. Project
identity and repository path are separate concepts.

```text
Account
  -> Project
  -> RepositoryBinding
  -> authorized working-tree root
```

The future durable binding must represent opaque binding identity; owning
account and Project; source class; canonical repository and working-tree root;
binding status; provenance and import/creation time; and stale/missing state.
This is semantic contract only, not a schema or migration. Repository paths do
not belong in Project description JSON.

## Repository source classes

| Source class | Meaning | Tool eligibility |
| --- | --- | --- |
| `guardian_managed` | Created under Guardian Projects Directory. | Only through an active binding. |
| `external_linked` | Explicitly imported existing repository, left in place. | Only through an active binding. |
| `discovery_candidate` | Read-only discovery result. | Never binding or tool-eligible. |

No runtime token module is added by this ADR.

## External discovery and candidate validation

Discovery is local, read-only, bounded, provenance-aware, and non-authorizing.
It must not crawl `/`, `/Users`, `/Volumes`, or an entire home directory by
default. A root is usable only when it is Guardian Projects Directory, a
bounded directory explicitly selected by the authenticated user, a separately
verified coding-agent project/worktree location, or a future provider with an
equivalent authority contract.

Known root, discovered candidate, and imported authorized repository remain
different states. Candidate validation may use `.git` directory/worktree-file
evidence and read-only `git rev-parse` to resolve a canonical working-tree
root. It may not execute project code, install dependencies, contact remotes,
fetch, pull, checkout, mutate the index or branches, or read arbitrary source
just to discover a repository.

Initial future limits are depth 4 under an authorized root, 128 candidates per
root, ten seconds per root, no symlink traversal, and no recursive descent once
a valid repository root is found. Nested repositories require independent
candidate treatment and inherit no parent authority.

## Repository and working-tree identity

Repository and working-tree identity are both required. Git worktrees may
share history but differ in branch and filesystem state. The initial binding
uses canonical Git evidence for repository identity and selects exactly one
canonical working-tree root. It does not authorize sibling worktrees, a bare
Git directory, or neighboring checkouts.

Canonicalization resolves symlinks and alternate spellings before comparison.
The same repository found through a symlink, user root, or agent root must not
become independently authorized duplicate bindings. The final uniqueness
mechanism is deferred.

## Import, Workspace, and deletion semantics

**Import into Codexify** is metadata/authority work: validate read-only;
create or reuse a Project; create the account-owned binding; optionally project
that Project into a Workspace. It must not move, copy, clone, rename, modify
Git configuration, change branches, or commit. Future `Adopt into Guardian
Projects Directory` is separate explicit filesystem work.

Workspace membership is a projection over Projects, never repository ownership.
The existing Workspace Profile Schema Spec states compatible projection doctrine
but is **Draft**, not runtime truth; this ADR does not promote it. A Project may
be visible in multiple Workspaces without duplicating or transferring its
repository.

Project deletion must not recursively delete repository files. External-linked
deletion/detachment is metadata only. Guardian-managed physical deletion is a
separate explicit destructive operation. R1 implements neither.

## Future ordinary-chat authority

```text
authenticated account
  -> current thread
  -> Project
  -> active RepositoryBinding
  -> authorized working-tree root
  -> bounded repository capability
```

Guardian resolves every link. Missing, stale, ambiguous, or unauthorized links
suppress repository capability advertisement. There is no fallback to cwd,
nearest `.git`, development checkout, environment repository path, worktree
query parameter, or Codexify source checkout. The model never chooses the
root.

`repository.search` remains the preferred first capability: one bounded
read-only command can return bounded repository-relative matches/snippets
within the current one-command limit. It is neither implemented nor assigned a
Command Bus ID here. Repository tooling remains Guardian-to-Command-Bus
mediated.

## Invariants

1. Repository authority is derived, never model-supplied.
2. Guardian-managed repositories live beneath one canonical managed root.
3. External discovery never grants authority.
4. Import requires explicit user/account action.
5. Existing external repositories remain in place by default.
6. Workspace membership does not determine filesystem ownership.
7. Project identity and repository path are separate concepts.
8. `General` receives no implicit filesystem authority.
9. cwd and `.git` discovery are never ordinary-chat authorization.
10. Absolute repository roots never become model-controlled parameters.
11. Missing, stale, or ambiguous bindings fail closed.
12. Repository tooling remains Guardian-to-Command-Bus mediated.

## Rejected shortcuts

Rejected: `Path.cwd()`; `detect_project_root()`; nearest `.git`;
`CODEXIFY_WORKTREE_REPO_PATH`; worktree query paths; defaulting every Project
to the Codexify checkout; model `repoPath`, root, cwd, mount, or host path;
whole-home discovery; auto-import; automatic external copy; Project-description
JSON paths; legacy ToolIntent `fs.search`; and repository search exposure before
a binding exists.

## Governing decisions

- ADR-005 governs account scope and user isolation.
- ADR-020 governs Guardian-issued repository/filesystem scope for coding agents.
- ADR-024 preserves the distinction between a connected source and an
  authorized/consulted crossing.
- ADR-061 governs explicit capability authorization, not infrastructure access.

ADR-039 is Proposed, and the Workspace Profile Schema Spec is Draft; neither
is promoted to accepted runtime truth by this decision.

## Implementation sequence

1. **Stage 2K.1:** Implement Guardian Projects Directory resolution and durable
   Project-to-RepositoryBinding authority, with no scanner or chat capability.
2. **Stage 2K.2:** Implement bounded read-only external discovery from
   explicitly authorized/evidence-backed roots, with no automatic import.
3. **Stage 2K.3:** Implement explicit candidate import/linking into a
   first-class Project and Workspace projection, without moving files.
4. **Stage 2K.4:** Implement bounded read-only `repository.search` against an
   already-authorized RepositoryBinding.
5. **Stage 2K.5:** Expose `repository.search` automatically only when the
   current thread resolves one valid binding.
6. **Stage 2K.6:** Run the live ordinary-chat repository-search proof.

These stages must not be combined.

## Links

- [Repository Onboarding Authority Contract](../repository-onboarding-authority-contract.md)
- [Stage 2K-R1 proof](../proofs/2026-08-11-stage2k-r1-repository-onboarding-authority-proof.md)
- [ADR Index](./adr-index.md)
