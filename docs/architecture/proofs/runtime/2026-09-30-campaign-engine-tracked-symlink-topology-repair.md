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

## Completion audit: physical Git directory coverage

After the first live rerun completed with `passed_with_advisories`, a
provider-free completion audit reproduced one remaining boundary gap: the
symlink-identity scan excluded ordinary `.git` directories. A newly created
link under `.git` or a nested physical Git directory could evade identity
comparison. Reproduction evidence is preserved at
`/private/tmp/ce_symlink_git_scan_audit.json`; no provider was invoked.

The metadata-only scan now also visits physical Git directories without
traversing any symlink. Such links cannot be committed repository symlinks and
therefore fail closed. The regular `.git` pointer in a disposable worktree is
not traversed. Physical file hashing retains its existing Git-scope choices.
Executor and read-only Evaluator regressions cover both root and nested Git
symlink creation. This closes the existing safety requirement without changing
Guardian permissions, Task scope, or the canonical specimen.

The completed Campaign `campaign-milestone-a-makefile-fddb937b3c13` and its
uncommitted target remain preserved. Its six evidence-coverage advisories are
recorded in `/private/tmp/ce_milestone_a_tracked_symlinks_0fc1c24b/operator-closeout.json`.
They do not constitute a clean per-criterion Evaluator pass. Independent
operator readback passed the remaining Task checks; the live verdict was not
modified. This audit correction is provider-free and does not resume that
Campaign or commit any Task edit.

Completion-audit validation:

- 18 focused symlink regressions passed.
- Final current-source aggregate Executor, Evaluator, and schema suite:
  **186 passed in 53.49 seconds**.
- Root and nested Git aliases are rejected before any Git subprocess in
  shared snapshot, Executor preparation, and Evaluator fingerprint checks.
- Ruff passed on all audit-correction Python surfaces.
- `PYTHON=.venv/bin/python make docs` and `git diff --check` passed.
- Audit repair provider calls: **0**; no binding/permission/schema/ADR changes.

A fresh single-Task Campaign using the unchanged canonical fixture is required
for the final corrected commit. Its artifacts must remain distinct from the
already completed Campaign and all earlier failed trials. Stop after its final
Evaluation/Receipt/CampaignState, preserve advisories as returned, and do not
commit its disposable Makefile edit or enter CE-L3.
