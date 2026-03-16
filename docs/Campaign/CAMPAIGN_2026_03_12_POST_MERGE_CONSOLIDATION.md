## Recommended Task Order

### PMC-001
Audit and classify the current `xpassed` tests.

Goal:
- identify the tests currently reporting as `xpassed` in the latest full `pytest -v` run
- classify each one as:
  - stale `xfail` marker, likely safe to normalize
  - passing but needs confirmation before marker removal
  - unclear, requires deeper investigation
- document the likely reason each one is now passing
- produce a repo-local audit artifact instead of changing test code in this task

### PMC-002
Record merge/worktree operating procedure.

Goal:
- write a concise internal runbook for:
  - worktree ownership of `main`
  - identifying the true integration branch when branch names and carried commits diverge
  - confirming which branch contains final task/campaign commits
  - handling merge conflicts when `main` is owned by another worktree
  - validation order across backend, frontend, and desktop/Tauri lanes
  - push discipline after merge completion
- capture the concrete command patterns proven during the stabilization merge

### PMC-003
Map frontend package-root structure.

Goal:
- document the current relationship among:
  - root `package.json`
  - `frontend/package.json`
  - `frontend/src/package.json`
  - `src-tauri/tauri.conf.json`
- explain which directory is the actual frontend package root used by build and test tooling
- explain the current role of `frontend/package.json` as a wrapper or pass-through layer if that is what inspection confirms
- classify the current structure as:
  - keep as-is
  - keep for now but document clearly
  - simplify in a future campaign

### PMC-004
Branch and PR absorption audit.

Goal:
- identify branches and PR-aligned branches already materially absorbed into `main`
- distinguish among:
  - branches fully merged into `main`
  - branches not formally merged but whose substantive commits are already present in `main`
  - branches that still contain unique work not present in `main`
- classify each reviewed branch as:
  - safe to close
  - safe to delete locally
  - keep alive for real pending work
  - unclear, needs manual review
- explicitly account for the Beta Stabilization merge cycle, including cases where the final integration branch differed from the earlier assumed branch name

### PMC-005
Canonical current-state update.

Goal:
- update architecture/current-state docs so repo truth reflects:
  - the successful Beta Stabilization merge into `main`
  - the final integration branch `codex/apply-campaign-task-execution-rules`
  - the validated backend result of `878 passed`, `15 skipped`, `33 xfailed`, `11 xpassed`, `0 failed`
  - the successful desktop/Tauri bundle outcome including `Codexify.app`
- distinguish clearly between resolved stabilization blockers and remaining non-blocking consolidation work
