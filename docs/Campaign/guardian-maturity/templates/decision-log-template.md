# Decision Log Template

Copy this template to `<campaign-folder>/decision-log.md` and record architectural and operational decisions as they are made.

---

## Decision Entry Format

Each decision entry uses the format below. Add new entries at the top.

---

### Decision: `<decision-id>`

- **Decision ID**: `<CAMPAIGN>-DEC-<NNN>`
- **Date**: `<YYYY-MM-DD>`
- **Decision**: `<one-sentence summary of the decision>`
- **Reason**: `<why this decision was made>`
- **Evidence**: `<what evidence supported the decision>`
- **Consequence**: `<what changes as a result of this decision>`
- **Revisit Trigger**: `<conditions under which this decision should be revisited>`

---

## Example Entry

### Decision: C00-DEC-001

- **Decision ID**: C00-DEC-001
- **Date**: 2026-06-16
- **Decision**: Classify current worktree as clean and proceed to truth gate proof collection.
- **Reason**: `git status` shows no modified tracked files and no untracked files that affect the supported path.
- **Evidence**: `git status --short --branch --untracked-files=all` output.
- **Consequence**: Truth gate proof collection can begin without worktree concerns.
- **Revisit Trigger**: Any uncommitted change to tracked files in `guardian/`, `frontend/src/`, or `config/`.

---

## Decision Index

| ID | Date | Decision | Status |
|----|------|----------|--------|
| `<CAMPAIGN>-DEC-001` | `<date>` | `<summary>` | `active` / `superseded` / `revisited` |
