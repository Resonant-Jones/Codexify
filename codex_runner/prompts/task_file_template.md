# <TASK-ID>: <Title>

## Metadata
- Task-ID: <TASK-ID>
- Campaign-ID: <CAMPAIGN-ID>
- Branch: <current-branch>
- Repo root: <REPO_ROOT>
- Task artifact: <docs/tasks/TASK_YYYY_MM_DD_NNN_lower_snake_slug.md>
- Owner: resonant_jones
- Risk: HIGH | MED | LOW
- Commit policy: Runner auto-commits after clean-tree invariants; tasks must not include git add/commit steps.

## Objective
One sentence describing what will be true when this task is done.

## Scope
### In-scope
- List the exact behaviors/files to change.

### Out-of-scope
- Explicitly list what must not be touched.

## Allowed files (STRICT)
> Do not modify files outside this list.

- <exact/path/or/tight/glob-1>
- <exact/path/or/tight/glob-2>
- docs/tasks/<this task artifact filename>
- docs/Campaign/<this campaign filename>

## Preconditions (NO GUESSING)
```bash
cd <REPO_ROOT>

# Preflight: must be clean
git status --porcelain -uall
# EXPECTED: (no output)
````

## **Execution plan (copy/paste)**

```
cd <REPO_ROOT>

# 1) confirm clean scope
git status --porcelain -uall

# 2) implement + verify (ONLY allowed files)
<commands>

# 3) confirm only allowed files changed
git status --porcelain -uall
```

## **Expected results (explicit)**

- <Concrete success signal: exact string, exit code, test name, endpoint response, file content, etc.>

- <If tests: include command and what “pass” looks like>

## **Rollback / cleanup**

```
cd <REPO_ROOT>

# Revert changes in tracked files (only those you touched)
git checkout -- <path1> <path2>

# Remove generated/untracked artifacts (only if produced by this task)
git clean -fd -- <path-or-dir>
```

## **Runner commit & receipt policy (AUTOMATIC)**

- **No manual commits.** Do not include `git add` / `git commit` instructions in this task artifact.
- The runner enforces clean-tree invariants:
  - Preflight: `git status --porcelain -uall` must be empty before starting.
  - Scope guard: only **Allowed files (STRICT)** may be modified.
  - Post-task: the tree must be clean after the runner commits.
- The runner will create commits automatically for:
  1) Initial receipt generation (campaign + task artifact creation)
  2) Task implementation changes
  3) Receipt updates (completion summary + commit hashes)

## **Campaign mapping (RUNNER-OWNED SOURCE OF TRUTH)**

- The runner will update the campaign doc with a mapping line for this task in this format:

  `<TASK-ID> -> [<implementation_commit_hash>, <receipt_update_commit_hash>]`

- For no-op tasks, the runner may use a single hash for both fields or set the receipt hash to `n/a` (runner policy).

## **Completion Summary (fill after completion)**

- Status: DONE | BLOCKED | DEFERRED

- What changed:

```
<bullets>
```

-

- Commands run:

```
<commands>
```

-

- Tests:

  - <commands + pass/fail>

- Scope check:

  - git status --porcelain -uall was clean before starting: yes/no

  - Only allowed files were modified: yes/no

- Commit info (Runner):

  - Implementation commit hash: <…>

  - Receipt update commit hash: <…>

  - Campaign mapping updated by runner: yes/no

- Notes / gotchas:

```
<anything important for future runs>
```
