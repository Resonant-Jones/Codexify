
TASK 3 — CLI Sandboxed Project Execution (Workspace-Root + Command Catalog)

Objective

Harden Codexify’s CLI execution surface so “terminal capabilities” become capability-scoped, project-root sandboxed actions.

This task establishes the Project Sandbox boundary:
- Every CLI run is bound to a workspace root.
- All file paths are validated to remain within that root.
- Only allowlisted commands can execute.
- Network egress from CLI runs is disabled by default.

Scope

Backend/CLI only.
Do not modify frontend UI.
Do not implement container-based sandboxing in this task.
Do not introduce flow blueprints or sharing here.

Security Invariants (Must Hold)

1) Workspace Root Boundary
- Any path that resolves outside the workspace root must be rejected (including symlink escapes).

2) No Arbitrary Shell
- CLI execution must not accept raw shell strings.
- Execution must use command_id lookups from a command registry.

3) Deterministic CWD
- All commands run with cwd set to workspace root.

4) Network Egress Default-Deny
- CLI commands must run with network egress disabled by default (policy layer).
- If the codebase lacks a runtime egress control, implement a policy gate that prevents any command entries marked requires_network unless explicitly enabled.

System Model

Introduce two core components:

A) WorkspaceRootManager
- register_root(path) -> WorkspaceRoot
- resolve_under_root(path) -> resolved_path | raises
- validate_read(path)
- validate_write(path)
- validate_exec(path)

Rules:
- Use realpath/resolve to normalize.
- Reject .. traversal.
- Reject symlinks that escape root.

B) CommandCatalog
- CommandDefinition:
  - id: str
  - executable: str
  - args_template: list[str]
  - allowed_params: schema (typed) or minimal validation
  - timeout_seconds: int
  - max_output_kb: int
  - requires_network: bool (default false)
  - allowed_paths: list[str] (optional, relative to root)

- CommandRegistry:
  - get(command_id) -> CommandDefinition | raises

Execution Path:
- CLI parses high-level request
- Resolves workspace root
- Validates requested command_id exists
- Validates params
- Validates any filesystem args under root
- Enforces policy gates (network, output caps)
- Executes command with cwd=root

Files Likely Affected

This change belongs in the Codexify CLI runner and any execution wrappers.
Likely locations include:
- codex_runner/* (if this is where execution orchestration lives)
- guardian/cli/* (if CLI commands live here)
- any shared “runner” utilities

This change belongs in the CLI execution layer (not frontend).

Codexify Task Prompt

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1) Workspace Root Detection
- Implement project root detection using one of:
  - an existing repo marker (e.g. .git)
  - a Codexify marker file (preferred) created by `codexify init` if it exists
  - fallback: current working directory
- Document the chosen rule in code comments.

2) Implement WorkspaceRootManager
- Add a module/class implementing:
  - root registration
  - safe resolution under root
  - read/write/exec validation helpers
- Ensure symlink escape is blocked:
  - create an explicit test that a symlink inside root pointing outside root is rejected.

3) Implement CommandCatalog + Registry
- Add a command registry with a minimal initial set (safe, dev-focused):
  - git_status
  - git_diff
  - pytest
  - pnpm_test (only if pnpm is present in repo conventions)
- Do NOT add generic “shell” or interpreter commands.
- Ensure CLI execution accepts command_id only.

4) Enforce Default-Deny Network Policy
- Add `requires_network` to command definitions.
- Block commands requiring network unless an explicit flag/config enables network.
- Default: network disabled.

5) Sandbox Validator Layer
- Wire validations into the execution path so:
  - path args are validated under root
  - command_id must exist
  - execution cwd is root
  - timeouts and output caps enforced

6) Tests (Required)
Add tests that fail before and pass after:

- Attempted path traversal (../) is rejected.
- Absolute path outside root is rejected.
- Symlink escape outside root is rejected.
- Valid in-root path is accepted.
- Unknown command_id is rejected.
- Command execution uses cwd=root (verify via a harmless command that prints cwd, or via instrumentation).
- Command marked requires_network is rejected by default.

7) Validation
Run backend/CLI tests as appropriate:

pytest -v

If CLI tests are separate, run the repo-defined command for CLI tests.
If no dedicated CLI tests exist, note explicitly that pytest covers the new modules.

8) Commit
Stage only modified files.
Commit message:

"Sandbox CLI execution by workspace root and command registry"

Output (Required)

- Summary of changes (files + key functions/classes).
- Test results summary.
- Git commit hash.

Constraints

- Do not implement container sandboxing in this task.
- Do not implement flow pre-auth here (that is Task 2).
- Do not add frontend UI.
- Do not add arbitrary shell execution.

This task creates the minimal safe substrate for project-scoped terminal work.

---

Execution Notes (2026-02-16)

- Added sandboxed CLI execution primitives in `guardian/core/orchestrator/cli_sandbox.py`:
  - `WorkspaceRootManager` with root detection precedence:
    - `.codexify_root` marker file
    - nearest `.git` ancestor
    - fallback to cwd
  - `WorkspaceRoot` registration and path validation helpers:
    - `resolve_under_root`, `validate_read`, `validate_write`, `validate_exec`
  - `CommandDefinition`, `CommandCatalog`, and `CommandExecutor`
  - default command registry:
    - `git_status`
    - `git_diff`
    - `pytest`
    - `pnpm_test` only when `pnpm-lock.yaml` exists at root
- Wired execution boundary into `WorkspaceManager.run_in_worktree`:
  - command_id-only execution path
  - deterministic `cwd=workspace_root`
  - params validation through command catalog
  - network default-deny gate for commands marked `requires_network`
  - timeout and max-output policy enforcement
- Updated orchestrator exports in `guardian/core/orchestrator/__init__.py` to include new sandbox classes.
- Added tests covering:
  - traversal/absolute/symlink escape rejection
  - valid in-root path acceptance
  - unknown command_id rejection
  - cwd root enforcement
  - default-deny network policy
