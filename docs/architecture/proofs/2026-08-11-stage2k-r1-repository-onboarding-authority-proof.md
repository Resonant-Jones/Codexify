# Stage 2K-R1 Repository Onboarding Authority Proof

## Verdict

PASS — current mainline has no competing canonical Project-to-repository binding, ADR-065 was unallocated, and the selected contract preserves current authority boundaries without runtime implementation.

## Base Commit

5842019444a9782256cd75252a97e1539140465e

## Remote Main

Fetched origin/main is 5842019444a9782256cd75252a97e1539140465e, identical to checkout HEAD. This reconciles the prior Stage 2K lineage stop at earlier remote base 237d5e2d5a0c17ca2b369e364a35c6598d2287d2.

## Files Inspected

Architecture current-state, README, ADR index, storage, config/ops, ownership, system overview, agent tool-loop, provider tool-turn, completion-pipeline, and flow contracts; Workspace Profile Schema Spec; Project model/route/default helper; root sandbox; campaign workspace manager; worktree service/model; Command Bus manifest; chat exposure; completion service/worker; Stage 2J current-main integration and live-closure receipt.

## Current Project Storage Truth

Project is a first-class SQLAlchemy entity with user ownership, metadata, and timestamps. Project routes enforce authenticated account scoping in multi-user mode. No current model, route, or helper has a canonical repository root, repository identity, working-tree identity, or RepositoryBinding. General is the default Project only, not a repository and not filesystem authority.

## Current Thread-to-Project Truth

ChatThread.project_id references projects.id. Thread-to-Project association exists; no thread-to-Project-to-repository authority path exists.

## Current Workspace Truth

The Workspace Profile Schema Spec is explicitly Draft. Its policy-bound Project projection is compatible direction, not accepted/implemented Workspace truth. ADR-065 preserves that boundary without elevating the draft.

## Existing Repository-Path Mechanisms

WorkspaceRootManager contains paths under a registered root. detect_project_root() uses .codexify_root, nearest .git, and cwd fallback. These are convenience mechanisms for an already-scoped caller, never ordinary-chat authorization. Current DATA_STORAGE_PATH=./data and vector path resolution do not provide a Guardian repository-root key or verified persistent host repository mount.

## Existing Worktree Mechanisms

WorkspaceManager creates campaign task worktrees under a selected repository's .codexify/worktrees. The read-only worktree service accepts explicit repo path, CODEXIFY_WORKTREE_REPO_PATH, or a development default. These are operator/campaign mechanisms, not account/Project bindings or model authority.

## Existing Ordinary-Chat Authority

Current mainline includes Stage 2J worker-exposure reconciliation. The only automatic ordinary-chat capability is the read-only, no-argument op::health_health_get for eligible targets. Current proof establishes one bounded health turn, neither repository search nor general filesystem authority. No repository.search surface was found.

## Guardian Projects Directory Decision

ADR-065 defines one logical Guardian Projects Directory for Guardian-created repositories. It is internal Guardian authority data, resolves to an absolute canonical host path, uses opaque stable child identity, rejects traversal/symlink escape, and is never model input. R1 creates nothing.

## Default Path / Configuration Recommendation

Current source cannot select a safe inferred host root. Future CODEXIFY_GUARDIAN_PROJECTS_DIR is the selected key: its configured value is canonicalized and verified persistent/Guardian-managed; absence fails closed as needs_configuration. DATA_STORAGE_PATH, cwd, container paths, source checkout, and home directory are forbidden fallback roots. This resolution rule avoids inventing a platform path; implementation is Stage 2K.1.

## Coding-Agent Discovery Evidence

Reconnaissance used only command presence/help and safe directory-type/shallow-name checks. No credentials, tokens, prompts, conversation logs, or private agent fields were read.

| Tool | Detected | Verified root | Safe default discovery | Evidence and result |
| --- | --- | --- | --- | --- |
| Codex | Yes | ~/.codex/worktrees hosts observed worktree checkouts. | No | Ephemeral/duplicative, not import authority. |
| Claude Code | Yes | UNVERIFIED | No | Arbitrary --add-dir; state did not prove root. |
| Cursor | No | UNVERIFIED | No | Executable/config root absent. |
| Windsurf | No | UNVERIFIED | No | Executable/config roots absent. |
| OpenCode | Yes | UNVERIFIED | No | Optional project argument; repos state dir not proof. |
| Pi | Yes | UNVERIFIED | No | Agent configuration did not evidence root. |
| Hermes | Yes | UNVERIFIED | No | --in DIR; private state not used as root. |

No investigated agent location joins a default discovery set.

## External Discovery Boundary

Future discovery is local, bounded, read-only, provenance-aware, and non-authorizing. It can operate only beneath Guardian Projects Directory, an explicitly user-selected root, a separately verified agent root, or an equivalent provider. It does not crawl broad host roots by default. Candidate validation is restricted to Git/filesystem markers and read-only git rev-parse; it neither executes project code nor mutates Git.

## Import Boundary

Import validates a candidate, creates/reuses a first-class Project, creates an account-owned RepositoryBinding, and may project the Project into a Workspace. It does not move, copy, clone, rename, reconfigure, branch-switch, or commit. Adoption into Guardian Projects Directory is separate work.

## Workspace Projection Boundary

Workspace visibility does not own a repository. A Project and binding remain account-owned; multiple Workspaces may show the same Project without duplicating files or authority.

## RepositoryBinding Authority Chain

~~~
authenticated account
  -> current thread
  -> Project
  -> active RepositoryBinding
  -> authorized working-tree root
  -> bounded repository capability
~~~

Guardian resolves every link. Missing, stale, ambiguous, or unauthorized means no advertisement. Cwd, nearest Git root, development checkout, environment repo path, worktree query path, and source checkout are prohibited fallbacks.

## Worktree Identity Decision

Future bindings record repository identity and one authorized working-tree identity. The capability searches that canonical root only, not sibling worktrees, shared Git directories, or neighboring state. Canonicalization resolves alternate spellings and symlinks before duplicate decisions.

## Rejected Shortcuts

Rejected: cwd/detect_project_root() authority; nearest .git; worktree environment/query paths; source-checkout default; model repoPath/absolute root; whole-home scan; auto-import; automatic external copy; Project-description JSON roots; legacy fs.search; and exposure before valid binding.

## ADR Impact

ADR-065 is required and accepted. It aligns with accepted ADR-005, ADR-020, ADR-024, and ADR-061. Proposed ADR-039 and the Draft Workspace spec were not elevated to accepted runtime facts.

## Governing ADRs

ADR-065, ADR-061, ADR-005, ADR-020, and ADR-024.

## Documentation Follow-Through

Created ADR-065, the onboarding authority contract, and this receipt; updated the ADR index. No runtime, migration, configuration, or tool contract was changed.

## Validation

- Initial pytest -v tests/architecture: 392 passed, 2 failed. The two failing tests were test_current_nine_node_corpus_validates and test_validator_cli_runs_without_runtime_services. Both carried the same content_hash_mismatch for docs/architecture/adr/adr-index.md; the reported Axis Node orphan was a non-fatal generated finding, not a second repair target.
- Authorized repair: the canonical ADR Index DLG node content_hash changed from ab4cee85b3a80ba79079d32da38cad249cac974ad17e12c394fff3bd7f2cfdb3 to the exact current ADR Index byte hash, 20679761fa980daa223aea33e740dfa2d81a77bd1fdc8696efb8dd25dd072c36.
- Focused DLG tests: 2 passed.
- Final pytest -v tests/architecture: 394 passed.
- The ADR Index source change required the canonical DLG node content_hash to be reconciled. The node remained stale according to its pre-existing freshness posture; only source integrity was repaired. No freshness promotion, verified_at change, or verified_commit change occurred.
- python3 scripts/validate_docs.py: passed.
- make docs PYTHON=python3: passed; the existing Makefile emitted two target-override warnings, then docs and diagram freshness passed.
- git diff --check: passed.

## Final Repository State

The five authorized paths are the four Stage 2K-R1 documents plus docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json. The canonical node has only the source-integrity content_hash edit. Diffs for guardian, tests, frontend, config, and the named Compose files are empty. No generated graph projection changed.

## Commit

Staged and committed after final cached scope and whitespace validation; the full SHA is recorded in the task closeout.
