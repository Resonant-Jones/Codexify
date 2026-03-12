# Merge and Worktree Operating Procedure

**Version:** 1.0
**Date:** 2026-03-12
**Scope:** Codexify repository merge operations and worktree management

---

## Overview

This runbook documents the operating procedure for managing merge campaigns in the Codexify repository, with particular attention to worktree ownership, branch identification, and validation order. These patterns were proven during the Beta Stabilization merge cycle.

---

## 1. Worktree Ownership of `main`

### Principle

The `main` branch should be checked out in its own dedicated worktree, separate from feature branches and integration work. This prevents:
- Uncommitted merge state from blocking other work
- Accidental commits to `main` during integration testing
- Lock contention when `main` is owned by another process

### Current Worktree Layout

```
/Users/resonant_jones/Keep/Resonant_Constructs/Codexify                d3a27344e [codex/apply-campaign-task-execution-rules]
/private/tmp/codexify-main-smoke-20260311                              c76b1333d [main]
```

### Commands

List all worktrees:
```bash
git worktree list
```

Create a new worktree for `main` (if needed):
```bash
git worktree add /path/to/worktree main
```

Remove a worktree when done:
```bash
git worktree remove /path/to/worktree
```

---

## 2. Integration-Branch Identification

### The Problem

During long-running campaigns, the assumed integration branch name may diverge from the actual branch carrying final commits. Branches may be rebased, renamed, or superseded.

### Identification Procedure

**Step 1:** Identify candidate integration branches:
```bash
git branch -a | grep codex/
```

**Step 2:** Confirm which branch contains the final campaign commits:
```bash
git branch --contains <commit-hash>
```

Example from Beta Stabilization:
```bash
git branch --contains 6659fb6e0
# Output: codex/apply-campaign-task-execution-rules
```

**Step 3:** Verify the branch HEAD matches expected state:
```bash
git log --oneline -5 codex/apply-campaign-task-execution-rules
```

### Warning Signs of Branch Confusion

- Branch names differ between local and remote (`codex/foo` vs `origin/codex/foo` with different SHAs)
- Multiple branches exist with similar names (`codex/fix-thing` vs `codex/fix-thing-v2`)
- Commits exist on one branch but not another despite similar purposes
- `git branch --contains` returns unexpected branches

---

## 3. Confirming Final Task/Campaign Commits

### Procedure

Before merging, confirm the integration branch contains:

1. **All expected commits:**
   ```bash
   git log --oneline codex/integration-branch | head -20
   ```

2. **Specific task commits:**
   ```bash
   git log --oneline --grep="BS-" codex/integration-branch
   git log --oneline --grep="PMC-" codex/integration-branch
   ```

3. **No unexpected divergence from main:**
   ```bash
   git log --oneline main..codex/integration-branch
   ```

### Example from Beta Stabilization

The final integration branch was `codex/apply-campaign-task-execution-rules`, not earlier candidate branches. This was confirmed by:

```bash
# Confirmed the branch contained the final task commit
git branch --contains 6659fb6e0
# Output: codex/apply-campaign-task-execution-rules

# Confirmed expected commits were present
git log --oneline --grep="BS-" codex/apply-campaign-task-execution-rules
# Output: test: align duplicate-turn integrity expectation with idempotent completion
```

---

## 4. Merge Conflict Handling When `main` Is Owned by Another Worktree

### Scenario

You're working in worktree A (feature branch) and need to merge into `main`, but `main` is checked out in worktree B.

### Options

**Option A: Merge from feature worktree (recommended)**

You don't need `main` checked out to merge into it. From the feature worktree:

```bash
# Fetch latest main
git fetch origin main

# Merge main into feature branch (if needed for conflict resolution)
git merge origin/main

# Then switch to main worktree for the final merge
```

**Option B: Worktree-switch workflow**

```bash
# In main worktree:
git merge codex/integration-branch

# If conflicts arise:
git diff --name-only --diff-filter=U
# Shows: files with unresolved conflicts
```

### Resolving Conflicts

1. Identify conflicted files:
   ```bash
   git diff --name-only --diff-filter=U
   ```

2. Edit each file to resolve conflicts (look for `<<<<<<<`, `=======`, `>>>>>>>` markers)

3. Mark as resolved:
   ```bash
   git add <file>
   ```

4. Complete merge:
   ```bash
   git commit -m "Merge branch 'codex/integration-branch'"
   ```

### Understanding Merge States

| State | Indicator | Meaning |
|-------|-----------|---------|
| Successful merge commit | `git log --oneline -1` shows "Merge branch..." | Two branches combined, no conflicts |
| Paused merge (conflicts) | `git status` shows "You have unmerged paths" | Conflicts need resolution |
| Successful push | `git log origin/main..main` is empty | Local main matches remote |

---

## 5. Validation Order After Merge

### Phase 1: Backend Tests

Command:
```bash
pytest -v
```

Expected result:
- `878 passed` (or similar expected count)
- `15 skipped` (expected skipped tests)
- `33 xfailed` (expected failures)
- `11 xpassed` (unexpected passes - known issue)
- `0 failed`

**Run from:** Repository root

### Phase 2: Frontend Tests

Command:
```bash
pnpm --dir frontend/src exec vitest run
```

Or via the frontend wrapper:
```bash
cd frontend && pnpm test
```

**Note:** `frontend/package.json` is a wrapper that delegates to `frontend/src/` where the actual package root lives.

### Phase 3: Desktop/Tauri Build

Commands:
```bash
# Build frontend (required before Tauri build)
cd frontend/src && pnpm build

# Run Tauri tests
cargo test --manifest-path src-tauri/Cargo.toml

# Build release bundle
cd src-tauri && cargo tauri build
```

Expected artifacts:
- `/path/to/target/release/app` (executable)
- `/path/to/target/release/bundle/macos/Codexify.app` (bundled app)

### Validation Failure Protocol

If any phase fails:

1. **Do not push** partial results
2. Fix failures in integration branch first
3. Re-run full validation sequence
4. Only push after all phases pass

---

## 6. Push Discipline After Merge Completion

### Pre-Push Checklist

1. **Working tree is clean:**
   ```bash
   git status
   # Should show: "nothing to commit, working tree clean"
   ```

2. **On main branch:**
   ```bash
   git branch --show-current
   # Output: main
   ```

3. **Merge commit is present:**
   ```bash
   git log --oneline --merges -1
   # Shows: "Merge branch 'codex/integration-branch'"
   ```

4. **All validations passed** (see Section 5)

### Push Command

```bash
git push origin main
```

### Post-Push Verification

1. **Confirm remote update:**
   ```bash
   git log --oneline origin/main..main
   # Should be empty (local matches remote)
   ```

2. **Verify on GitHub/GitLab:**
   Check the repository web interface to confirm commits are visible

---

## 7. Common Failure Modes

### 7.1 Local `main` Owned by Another Worktree

**Symptom:**
```bash
git checkout main
# fatal: 'main' is already checked out at '/private/tmp/codexify-main-smoke-20260311'
```

**Resolution:**
- Use the existing main worktree for main-branch operations
- Or remove the other worktree if it's no longer needed:
  ```bash
  git worktree remove /private/tmp/codexify-main-smoke-20260311
  ```

### 7.2 Source Branch Confusion During Integration

**Symptom:** Multiple branches claim to be the integration branch; commits exist on unexpected branches.

**Resolution:**
- Use `git branch --contains <commit>` to find the true integration branch
- Check the closeout document for the canonical branch name
- When in doubt, ask: "Which branch contains the final task commits?"

### 7.3 Backend Green While Frontend/Tauri Merge State Is Unresolved

**Symptom:** `pytest -v` passes, but frontend tests fail or Tauri build produces errors.

**Resolution:**
- Backend tests are necessary but not sufficient
- Always run all three validation phases (backend, frontend, Tauri)
- Frontend package-root confusion can cause silent failures

### 7.4 Package-Root Confusion

**Symptom:** Commands fail with "cannot find module" or wrong package.json is read.

**Current Structure:**
```
repo-root/
├── package.json           # Root package (minimal)
├── frontend/
│   ├── package.json       # Wrapper (delegates to src/)
│   └── src/
│       └── package.json   # Actual frontend package root
└── src-tauri/
    └── Cargo.toml         # Tauri package
```

**Rule:**
- Build/test commands for frontend should run from `frontend/src/`
- The `frontend/package.json` scripts all delegate with `cd src && ...`
- For Tauri: `src-tauri/` is its own package root

---

## Command Reference

### Git Worktree Commands

| Command | Purpose |
|---------|---------|
| `git worktree list` | Show all worktrees and their branches |
| `git worktree add <path> <branch>` | Create new worktree for branch |
| `git worktree remove <path>` | Remove worktree |

### Branch Identification Commands

| Command | Purpose |
|---------|---------|
| `git branch --contains <commit>` | Find branches containing a commit |
| `git log --oneline main..<branch>` | Show commits in branch but not main |
| `git diff --name-only --diff-filter=U` | Show unmerged (conflicted) files |

### Validation Commands

| Phase | Command |
|-------|---------|
| Backend | `pytest -v` |
| Frontend | `pnpm --dir frontend/src exec vitest run` |
| Tauri Test | `cargo test --manifest-path src-tauri/Cargo.toml` |
| Tauri Build | `cd src-tauri && cargo tauri build` |

---

## See Also

- `docs/release/run/2026-03-12-beta-stabilization-sweep-closeout.md` - Example merge closeout
- `CLAUDE.md` - Repository structure and architectural boundaries
