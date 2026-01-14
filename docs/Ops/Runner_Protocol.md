

# Runner Protocol — Sequential Atomic Tasks

## Purpose
This protocol is a strict execution harness for Codexify campaigns.

It enforces:
- **one task = one commit**
- **strict file scope** per task
- **tests before commit**
- **prompt + summary artifacts** recorded in `docs/tasks/`

## Inputs
A campaign file containing an ordered task list with, per task:
- Task ID + title
- Task file path under `docs/tasks/…`
- Allowed (primary) file list
- Test loop command(s)
- Commit message

Example campaign path:
- `docs/Campaign/CAMPAIGN_YYYY_MM_DD.md`

## Global Invariants
1. **No scope creep**
   - Only edit files explicitly allowed by the current task.
   - If a change requires an additional file, stop and report.

2. **No batching**
   - Do not carry changes across tasks.
   - Do not “improve” nearby code unless the task explicitly requires it.

3. **Tests are mandatory**
   - Run the task’s test loop before committing.
   - If tests fail, fix within allowed files only.

4. **Artifacts are mandatory**
   - Every task produces/updates its `docs/tasks/...` file with:
     - Task Prompt
     - Summary (what changed, tests, git status, commit hash)

5. **Clean tree between tasks**
   - `git status --porcelain` must be empty before moving to the next task.

## Per-Task Execution Loop
For each task in the campaign (in order):

### 0) Announce + lock scope
Print:
- Task ID + title
- Allowed file list
- Task artifact path
- Test command(s)
- Commit message

### 1) Preflight check
Run:
```bash
git status --porcelain
```
If anything is dirty, stop and report.

### 2) Implement minimal change
Edit only the allowed files.

### 3) Scope enforcement check
Run:
```bash
git status --porcelain
```
If any modified/untracked file is **not** in the allowed file list **or** the task artifact path:
- Revert/remove it immediately, or
- Stop and report if reverting would lose required work.

### 4) Run tests
Run the task’s test loop exactly as specified.
- If tests fail: fix within allowed files and re-run until passing.
- If passing requires touching a non-allowed file: stop and report.

### 5) Write task artifact
Create/update the task file under `docs/tasks/…` with two sections:

#### Task Prompt
Include the full Codexify Task Template prompt for this task:
- Context
- Instructions
- Task Description
- Expected Output

#### Summary
Include:
- Changed files + key functions/components
- Test command(s) + pass/fail summary
- `git status --porcelain` confirmation (no out-of-scope files)
- Commit hash (after commit)

### 6) Stage + commit
Stage **only**:
- allowed files for this task
- the task artifact file

Then commit using the campaign’s commit message.

### 7) Post-commit clean check
Run:
```bash
git status --porcelain
```
Must be empty before proceeding.

## Campaign Completion Output
After the final task:
- Print a list mapping `TASK-ID -> commit-hash`.
- Do not run a re-audit unless explicitly instructed.

## Stop Conditions
Stop immediately and report if:
- A task requires editing files outside its allowed list.
- Tests cannot pass without violating scope.
- The working tree becomes unexpectedly dirty.

## Notes
- This protocol is intentionally strict. It is designed to prevent "Franken-commits" and preserve auditability.