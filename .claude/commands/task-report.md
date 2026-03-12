# task-report

Standardized end-of-task reporting format for Codexify work.

## Required Output Sections

### What Changed
Brief description of the modification and the reasoning behind it.

### Why It Changed
The problem being solved or the feature being added.

### Files Touched
List each file modified, created, or deleted:
- `path/to/modified/file.py` - brief note on what changed
- `path/to/new/file.ts` - created for X purpose
- `path/to/deleted/file.py` - removed (reason)

### Test Command(s) Run
State the exact commands executed:
```
pytest -v tests/<relevant_path>
pnpm test -- <pattern>
```

### Test Result Summary
- Backend tests: X passed, Y failed
- Frontend tests: X passed, Y failed
- Or: **No automated tests apply** (for docs-only changes)

### Commit Hash
The git commit containing these changes:
```
<commit-hash>
```

## Example (Docs-Only Task)

**What Changed:** Added Claude Code workspace guidance files.

**Why It Changed:** Provide consistent guidance for AI-assisted coding sessions aligned with Codexify architecture.

**Files Touched:**
- `CLAUDE.md` - created, repo-root guidance file
- `.claude/commands/repo-map.md` - created, repo orientation command
- `.claude/commands/task-report.md` - created, reporting template
- `.claude/commands/runtime-check.md` - created, runtime verification command

**Test Command(s) Run:** None

**Test Result Summary:** No automated tests apply (docs-only scaffolding).

**Commit Hash:**
```
a1b2c3d4
```
