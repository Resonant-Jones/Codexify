# Repository Onboarding Authority Contract

## Purpose

Define Codexify's repository onboarding and future repository-tool authority under ADR-065. This is docs-only: it adds no root, scanner, database state, import route, repository search, Command Bus command, or chat exposure.

**Discovery finds. Import registers. Guardian binds. Workspace projects. Tools consume only the binding.**

## Status

Accepted architecture contract under ADR-065, grounded at 5842019444a9782256cd75252a97e1539140465e.

## Current Truth

### What is true now

- Project is a first-class application record with user_id, metadata, and timestamps. Project routes scope operations to the authenticated account in multi-user mode.
- ChatThread.project_id associates a thread with a Project.
- General is a default Project only; it has no repository or filesystem authority.
- No current model, route, or helper establishes RepositoryBinding, a Project repository root, a canonical working-tree root, or a Project-to-repository relation.
- WorkspaceRootManager contains paths under a registered root. Its detect_project_root() order is .codexify_root, nearest .git, then cwd. It is a convenience resolver, never repository authorization.
- WorkspaceManager owns selected-repository campaign worktrees. Worktree visibility accepts explicit, environment, or development-default repo paths. Neither is ordinary-chat Project authority.
- Ordinary chat has only the live-proven read-only, zero-argument op::health_health_get capability. No repository search authority exists.

### What is not yet true

Guardian Projects Directory configuration, RepositoryBinding persistence, candidate discovery, import/linking, Workspace implementation, repository search, Command Bus ID, and ordinary-chat exposure are absent.

### What future implementation may assume

Only ADR-065: an explicit account/Project binding, one selected working tree, non-authorizing discovery, non-moving import, Workspace projection, and fail-closed capability resolution.

## Non-Goals

No scanner, Git action, filesystem creation, schema/migration, API/UI, repository move/copy/clone/adoption/deletion, tool token, provider change, or ordinary-chat capability is implemented here.

## Terminology

| Term | Meaning |
| --- | --- |
| Guardian Projects Directory | Guardian-managed parent root for Guardian-created repositories. |
| repository-backed Project | A Project with one active RepositoryBinding. |
| RepositoryBinding | Guardian-owned durable account/Project/repository/working-tree authority. |
| discovery root | A bounded root authorized only to find candidates. |
| discovery candidate | Read-only repository observation; never a binding. |
| import/link | Explicit user/account registration that creates a binding without moving a repository. |

## Guardian Projects Directory

Current DATA_STORAGE_PATH=./data and Compose application-storage conventions do not select a verified persistent host repository root. The selected future configuration rule therefore avoids inventing a platform path:

| Future key | Rule |
| --- | --- |
| CODEXIFY_GUARDIAN_PROJECTS_DIR | Required explicit operator/instance setting. Expand, canonicalize to a real absolute host path, verify persistence/writability and Guardian management, then create/manage only this directory. |
| unset | Fail closed as needs_configuration. Never infer cwd, source checkout, container path, home directory, or relative DATA_STORAGE_PATH. |

Repository children remain beneath the canonical root. Symlink and traversal escape fail closed. Opaque stable IDs, never Project names, form child directory identity; rename does not relocate a repository. The absolute root remains internal authority data.

## Repository-Backed Projects

Projects are not silently redefined as Git repositories. Existing Projects may remain repository-less, including General. Future Guardian-created repositories live under Guardian Projects Directory; external-linked repositories remain in place.

## RepositoryBinding Concept

~~~
Account -> Project -> RepositoryBinding -> authorized working-tree root
~~~

Initial cardinality is one active binding per Project. Future durable state must represent opaque binding ID, account and Project ownership, source class, canonical repository and working-tree identity, status, provenance, creation/import time, and stale/missing state. It is authority-side data, never Project-description JSON or a model-supplied path. No final schema is selected.

## Repository Source Classes

- guardian_managed: created under Guardian Projects Directory.
- external_linked: explicitly imported existing repository, left in place.
- discovery_candidate: bounded discovery result; never a binding or tool-eligible.

## Repository Identity vs Filesystem Path

Paths can alias through symlinks, spelling, or agent worktrees. Canonicalization is the duplicate-detection seam. Candidate sources converge on repository identity before import; different paths do not create independently authorized bindings. The final database uniqueness method is deferred.

## Working-Tree Identity

A binding identifies both repository identity and exactly one canonical authorized working-tree root. This prevents common Git history from authorizing sibling worktrees, bare repositories, or neighboring filesystems. A missing, changed, or ambiguous worktree fails closed.

## External Discovery

Discovery is local, read-only, bounded, provenance-aware, and non-authorizing. It must not crawl /, /Users, /Volumes, or an entire home directory by default. Future roots may be Guardian Projects Directory, an authenticated user's explicit bounded selection, a separately verified coding-agent root, or a connector with equivalent authority.

## Discovery Root Authority

Record root provenance, authorized actor, canonical root, limits, and time. A known root is not a candidate; a candidate is not an import; an import is not tool eligibility until an active binding exists. Model input cannot carry roots, cwd, mounts, absolute paths, or repoPath.

## Coding-Agent Discovery Evidence Matrix

R1 used only executable presence/help and safe directory-type/shallow-name checks. It did not read credentials, tokens, prompts, conversation logs, or private agent fields. ~ denotes the local account home directory.

| Tool family | Detected | Verified project-hosting root | Evidence | Confidence | Safe default discovery | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| Codex | Yes | ~/.codex/worktrees hosts observed managed checkouts, not a project library. | codex --help; shallow worktree layout. | High | No | Ephemeral/duplicate worktrees do not prove import intent. |
| Claude Code | Yes | UNVERIFIED | Help offers arbitrary --add-dir; state dirs were not a root. | High | No | Arbitrary repositories are possible. |
| Cursor | No | UNVERIFIED | Executable and known config path absent. | High | No | No local root evidence. |
| Windsurf | No | UNVERIFIED | Executable and known config paths absent. | High | No | No local root evidence. |
| OpenCode | Yes | UNVERIFIED | Optional project argument; local repos state dir not proven hosting root. | Medium | No | State directory is not authority evidence. |
| Pi | Yes | UNVERIFIED | Agent config exists; no root evidenced. | Medium | No | Configuration is not a repository root. |
| Hermes | Yes | UNVERIFIED | Help accepts --in DIR; private state was not inspected as a root. | High | No | Arbitrary directory selection; private state is not default discovery. |

No investigated agent root joins a default discovery set. The observed Codex worktree parent could only become an explicitly authorized, duplicate-aware root after dedicated policy review.

## Candidate Validation

Future validation uses only .git directory/worktree-file evidence and read-only git rev-parse to resolve canonical working-tree/repository facts. Limits: depth 4, at most 128 candidates per root, ten seconds per root, no symlink traversal, and no recursive descent after a valid root. Nested repositories require separate candidates and do not inherit authority.

It must not execute project code, install dependencies, contact remotes, fetch, pull, checkout, mutate the index, modify branches, or read arbitrary source merely to recognize a repository.

## Import Semantics

Import validates read-only, creates/reuses a Project, creates the account-owned binding, and may show that Project in a Workspace. It must not move, copy, clone, rename, configure, branch-switch, or commit. Adoption into Guardian Projects Directory is separate explicit filesystem work.

## Workspace Projection Semantics

Workspace is a projection, not repository ownership. The Workspace Profile Schema Spec describes compatible first-class Project visibility but is Draft, not current runtime truth. A binding belongs to Project/account; one or more Workspaces may show that Project without duplicating files or authority.

## Duplicate Detection

All discovery sources flow through canonicalization before import. If path, repository, or selected worktree identity cannot be resolved unambiguously, import and tool exposure fail closed. The storage uniqueness mechanism remains deferred.

## Stale/Missing Binding Behavior

If a root disappears, ceases to be a repository, escapes the managed root, changes identity, loses account/Project scope, or is ambiguous, suppress every repository capability. Never fall back to sibling worktree, cwd, nearest .git, environment path, development checkout, or source repository.

## Deletion and Detachment Semantics

Project or binding deletion does not recursively delete files. External-linked detachment is metadata only. Guardian-managed physical deletion is a separate explicit destructive operation. R1 implements neither behavior.

## Future Repository Capability Resolution

~~~
authenticated account -> current thread -> Project -> active RepositoryBinding
  -> authorized working-tree root -> bounded repository capability
~~~

Guardian resolves every link; missing, stale, ambiguous, or unauthorized means no advertisement. repository.search is the planned first capability because one bounded search can return repo-relative matches/snippets within the one-command tool turn. It must be Command Bus mediated after binding exists.

## Security and Privacy Boundaries

Absolute roots, mounts, credentials, raw discovery data, and project contents are not model input. Guardian retains authority/provenance; capability advertisement and execution remain independently gated by Stage 1 and Command Bus policy. Operator path configuration and account user import consent are distinct.

## Observability Requirements

Future records are bounded and privacy-safe: binding ID, account/Project IDs, source class, binding status, root-provenance class, canonicalization outcome, candidate count, limits, and rejection codes. Model/user output is repository-relative and bounded; it never exposes arbitrary host paths, mounts, secrets, raw Git config, or unbounded project content.

## Rejected Shortcuts

Rejected: Path.cwd(), detect_project_root(), nearest .git, CODEXIFY_WORKTREE_REPO_PATH, worktree query paths, source checkout defaults, model repoPath, whole-home scans, auto-import, automatic copying, Project-description JSON roots, legacy fs.search, and search exposure without a valid binding.

## Deferred Work

Configuration code, root provisioning, persistence/migration, candidate scanner, Git validation seam, import API/UI, duplicate constraint, Workspace persistence, adoption/deletion, command definition, provider tool schema, chat exposure, and live proof are deferred.

## Implementation Sequence

1. **Stage 2K.1:** Guardian Projects Directory resolution and durable binding; no scanner or chat capability.
2. **Stage 2K.2:** Bounded read-only discovery from authorized/evidence-backed roots; no automatic import.
3. **Stage 2K.3:** Explicit import/linking to a Project and Workspace projection; do not move files.
4. **Stage 2K.4:** Bounded read-only repository.search against a binding.
5. **Stage 2K.5:** Automatic exposure only for a current thread with one valid binding.
6. **Stage 2K.6:** Live ordinary-chat repository-search proof.

Do not combine these stages.
