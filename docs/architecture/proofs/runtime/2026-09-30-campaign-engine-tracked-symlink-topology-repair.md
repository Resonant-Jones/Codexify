# Campaign Engine tracked symlink topology repair

## Scope and cause

This provider-free Milestone A friction repair aligns with ADR-068. It does not
change release truth, binding authority, retry policy, or progression semantics.

The fresh canonical fixture trial from `ff7db039` used Campaign
`campaign-milestone-a-makefile-a9ea7e59232c`. Its Executor removed the stale
Makefile recipe, boundary validation passed, and one docs validation passed.
Evaluator preparation then rejected `target_symlink_present`: the repository's
unchanged tracked `backend/migrations -> ../guardian/db/migrations` link resolved
inside the disposable target. Executor calls were one; Evaluator calls were zero.

That failed Campaign and its uncommitted Makefile edit remain preserved at
`/private/tmp/ce_milestone_a_bounded_evidence_ff7db039` and
`/Volumes/Dev_SSD/offload/codex/worktrees/canonical-audit-bounded-evidence-ff7db039-20260930/Codexify-main`.
They were not resumed, repaired, committed, or used as the new Campaign input.

## Repaired invariant

Physical snapshots enumerate regular files without traversing symlink files or
directories. Symlink evidence is separate: committed path, raw link target, and
resolved path inside the disposable worktree. Actual links must match the HEAD
symlink tree before preparation and retain exactly that identity through
pre-invocation, post-Executor, post-validation, and Evaluator checks.

Unchanged tracked internal directory and file links are allowed. New, deleted,
replaced, retargeted, dangling, cyclic, or externally redirected links fail
closed. Resolution gathers metadata only; no alias contents are hashed or
used to broaden Guardian read/write permission. Full identities are stored in
preparation and before/after artifacts, bound to the immutable checkpoint;
the bounded Evaluator packet carries their unchanged identity evidence.

Git HEAD checks apply to physical worktree `.git` pointer files as well as
ordinary Git directories. Full physical file snapshots, changed-path scope,
zero-mutation rejection, validation sequencing, and read-only Evaluator
fingerprints remain enforced. No Task specimen change was made.

## Provider-free proof

Focused Executor, Evaluator, and schema suites cover:

- unchanged tracked internal directory and file symlinks through final lifecycle;
- no alias paths in full physical file evidence;
- creation, retarget, outside redirection, deletion, and replacement rejection;
- rejection before invocation without a provider call;
- rejection after Executor before Task validation;
- rejection after Task validation;
- read-only Evaluator topology-mutation rejection;
- existing file boundary, Git HEAD, binding, one-validation-attempt, packet-size,
  no-retry, no-fallback, and no-rebinding regressions.

Validation results are recorded after execution below. Provider calls for this
repair are **0**. The canonical rerun is separate live evidence and must use a
fresh Campaign and physical disposable worktree from the clean repair commit.

CE-L3 was not entered. No failed disposable Task was committed. The canonical
fixture remains `docs/Campaign/fixtures/milestone-a-ordinary-single-task.md`.

Validated results:

- Focused new symlink regressions: 12 passed.
- Aggregate live Executor, live Evaluator, and schema regressions: 180 passed.
- Ruff on all changed Python files: passed (existing configuration advisory).
- `PYTHON=.venv/bin/python make docs`: passed; pending source Makefile duplicate
  warnings remain because the operational Task is not implemented in source.
- `git diff --check`: passed.

Initial regression runs exposed fixture receipt-prefix and exception-attribute
mistakes; those were corrected before the successful complete suite. No live
provider calls occurred during any repair validation.
