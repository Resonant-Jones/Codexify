````
# <TASK-ID>: <Title>

## Metadata
- Task-ID: <TASK-ID>
- Campaign-ID: <CAMPAIGN-ID>
- Branch: <current-branch>
- Repo root: <REPO_ROOT>
- Task artifact: <docs/tasks/TASK_YYYY_MM_DD_NNN_lower_snake_slug.md>
- Owner: resonant_jones
- Risk: HIGH | MED | LOW
- Commit mode: two-phase | one-commit (docs-only)

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

## **Commit plan (MANUAL; index.lock workaround)**

### **Commit mode rules**

- **two-phase** (default): Commit A = implementation/config/tests. Commit B = docs finalize + campaign mapping update.

- **one-commit** (docs-only tasks): implementation/docs are committed together once.

---

### **Commit A (implementation) — two-phase only**

- Commit message (EXACT):

  - “: ”

- Manual commands (explicit paths only):

```
cd <REPO_ROOT>

git status --porcelain -uall
git add <explicit allowed file paths ONLY (no docs/tasks, no campaign doc unless explicitly required)>
git commit --no-verify -m "<TASK-ID>: <short action>"
git log -1 --oneline
git status --porcelain -uall
```

- Record the implementation hash here (source of truth for Commit A):

  - Commit A hash: <FILL_AFTER_COMMIT_A>

---

### **Commit B (docs finalize + mapping) — two-phase only**

- Purpose:

  - Update **this task artifact** with completion summary (including Commit A hash),

  - Update the **campaign doc mapping line** with both hashes.

- Commit message (EXACT):

  - “: docs finalize + mapping”

- Manual commands:

```
cd <REPO_ROOT>

git status --porcelain -uall
git add docs/tasks/<this task artifact filename> docs/Campaign/<this campaign filename>
git commit --no-verify -m "<TASK-ID>: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall
```

- Recording rule (avoids ouroboros/self-referential hash loop):

  - **Commit B hash is recorded in the CAMPAIGN mapping line (source of truth).**

  - (Optional) You may also paste Commit B hash below after the commit is complete.

---

### **One-commit mode (docs-only tasks)**

- Commit message (EXACT):

  - “: ”

- Manual commands:

```
cd <REPO_ROOT>

git status --porcelain -uall
git add <explicit allowed file paths including docs changes>
git commit --no-verify -m "<TASK-ID>: <short action>"
git log -1 --oneline
git status --porcelain -uall
```

- Record the hash here:

  - Commit hash: <FILL_AFTER_COMMIT>

---

## **Campaign mapping (SOURCE OF TRUTH)**

> This line must exist in the campaign doc and must be updated during Commit B (two-phase) or the single commit (one-commit).

 -> [, ]

Notes:

- For **two-phase**, put Commit A and Commit B hashes in this mapping line.

- For **one-commit**, set  to the single hash and  to “n/a” (or repeat the same hash—pick one convention and keep it consistent across the campaign).

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

- Commit info:

  - Commit mode: two-phase | one-commit

  - Commit A hash (impl): <…>  (two-phase)

  - Commit B hash (docs finalize): recorded in campaign mapping (two-phase)

  - Single commit hash: <…> (one-commit)

- Campaign mapping updated: yes/no

- Notes / gotchas:

```
<anything important for future runs>
```
