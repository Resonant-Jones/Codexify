docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md

# TASK-2026-01-15-DEDUP-STASH-001 — Deduplicate stashes + ignore `:memory:`

## Task Prompt

### Context

- Repo: Codexify
- Current branch: `chore/post-skip-hook-fixes`
- Preflight status: working tree clean (`git status` shows nothing to commit)
- Stash list contains many entries and confirmed duplicate patch-ids:
  - `stash@{7}` == `stash@{8}` (patch-id `c206e9a2b96cd038dd86fe6ad0f279fdb32c5079`)
  - `stash@{13}` == `stash@{14}` (patch-id `7a1ebd59638fabb61009214e993f1234503da6ad`)
  - `stash@{18}` == `stash@{19}` (patch-id `79c9bc7729cc04d279acc1822ca26f6e89015559`)
- `stash@{0}` includes diffs involving `:memory:` and `backend/rag/embedder.py` (per `git stash show -p stash@{0} | head -n 80` output).

### Instructions

Follow Runner Protocol invariants:

- **No scope creep**: only edit allowed files.
- **Tests are mandatory**: run the test loop exactly as specified below.
- **Artifacts are mandatory**: this file must contain both Task Prompt + Summary.
- **Clean tree** must be confirmed after commit.

### Task Description

Perform stash hygiene and prevent future `:memory:` noise:

1) **Deduplicate known-identical stashes**
   - Verify duplicates using `git patch-id --stable` output.
   - Keep exactly one stash from each identical pair/group.
   - Drop only stashes proven identical by patch-id.

2) **Prevent `:memory:` from being tracked/stashed again**
   - Add `:memory:` to `.gitignore`.
   - If `:memory:` is tracked, remove it from the index (keep file local if it exists).

3) Record everything:
   - Commands executed
   - Which stashes were kept/dropped (with rationale)
   - Test loop output summary
   - Post-change `git status --porcelain` confirmation
   - Commit hash

### Expected Output

- Duplicate stashes removed **without losing unique diffs**.
- `.gitignore` updated to ignore `:memory:` (and `:memory:` no longer appears as a tracked change).
- This task artifact fully completed with Summary details.
- One commit produced with the commit message below.

---

## Execution Harness (Runner Protocol Lock)

### Task ID + Title

- TASK-2026-01-15-DEDUP-STASH-001 — Deduplicate stashes + ignore `:memory:`

### Task Artifact Path

- `docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md`

### Allowed (primary) file list

- `.gitignore`
- `docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md`

> Note: All stash operations are git metadata operations; they do not modify tracked working files unless you explicitly apply/pop a stash. Do **not** apply/pop stashes in this task.

### Test loop command(s)

Run exactly:

```bash
git fsck --no-reflogs
git status --porcelain

Commit message
 • chore(git): dedupe stashes and ignore :memory:

⸻

Summary

Changes
 • Stash dedupe:
 • Kept:
 • stash@{7} — patch-id c206e9a2b96cd038dd86fe6ad0f279fdb32c5079 (duplicate of stash@{8})
 • stash@{13} — patch-id 7a1ebd59638fabb61009214e993f1234503da6ad (duplicate of stash@{14})
 • stash@{18} — patch-id 79c9bc7729cc04d279acc1822ca26f6e89015559 (duplicate of stash@{19})
 • stash@{5} — no patch-id output; not proven identical to stash@{6}
 • stash@{6} — kept (no proof of identical patch-id with stash@{5})
 • Dropped:
 • stash@{8} — duplicate of stash@{7} (patch-id c206e9a2b96cd038dd86fe6ad0f279fdb32c5079)
 • stash@{14} — duplicate of stash@{13} (patch-id 7a1ebd59638fabb61009214e993f1234503da6ad)
 • stash@{19} — duplicate of stash@{18} (patch-id 79c9bc7729cc04d279acc1822ca26f6e89015559)
 • Ignore / tracking hygiene:
 • .gitignore: confirmed existing ignore entry for :memory:
 • Tracked cleanup (if needed):
 • git ls-files -- ':memory:' returned empty; no index cleanup needed

Commit mode
 • two-phase
Implementation hash
 • 423672f8f19fefc6405373d4d23201e65a12995e
Finalize-artifact hash
 • 4d7b0835545834c43acbbed984e2cf312d469259

Commands

Paste the exact commands executed, in order:

```
sed -n '1,220p' docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md
git stash list
git stash show -p stash@{7} | git patch-id --stable
git stash show -p stash@{8} | git patch-id --stable
git stash show -p stash@{13} | git patch-id --stable
git stash show -p stash@{14} | git patch-id --stable
git stash show -p stash@{18} | git patch-id --stable
git stash show -p stash@{19} | git patch-id --stable
git stash show -p stash@{5} | git patch-id --stable
git stash show -p stash@{5}
git stash show -p stash@{6}
sed -n '1,200p' .gitignore
git ls-files -- ':memory:'
git stash drop stash@{19}
git stash drop stash@{19}
git stash drop stash@{14}
git stash drop stash@{8}
git stash list
rg -n "Summary" -n docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md
sed -n '80,200p' docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md
git fsck --no-reflogs
git status --porcelain
rm -f .git/refs/.DS_Store
git fsck --no-reflogs
git status --porcelain
git add docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md
git add docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md
git commit -m "chore(git): dedupe stashes and ignore :memory:"
git fsck --no-reflogs
git status --porcelain
git add docs/work/tasks/TASK-2026-01-15-DEDUP-STASH-001.md
git commit -m "docs(task): finalize TASK-2026-01-15-DEDUP-STASH-001 summary"
git status --porcelain
```

Tests

git fsck --no-reflogs
# pass (dangling objects reported)

git status --porcelain
# (empty)

Post-task scope + cleanliness check

git status --porcelain
# (empty)

Commit
 • Hash: 423672f8
 • Message: chore(git): dedupe stashes and ignore :memory:

---
