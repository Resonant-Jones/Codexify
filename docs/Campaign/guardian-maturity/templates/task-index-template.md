# Task Index Template

Copy this template to `<campaign-folder>/backlog.md` and maintain the task table as tasks are planned and executed.

---

## Task Queue

| Task ID | Lane | Status | Files | Validation | Commit | Proof Artifact |
|---------|------|--------|-------|------------|--------|----------------|
| `<CAMPAIGN>-TASK-001` | `<lane>` | `planned` | `<files>` | `<validation>` | — | — |
| `<CAMPAIGN>-TASK-002` | `<lane>` | `planned` | `<files>` | `<validation>` | — | — |

## Lane Definitions

- **docs**: Documentation-only changes; no runtime, route, or UI impact.
- **backend**: Backend route, service, schema, or worker changes.
- **frontend**: Frontend component, page, state, or hook changes.
- **cross-cutting**: Changes that span backend and frontend or touch shared contracts.
- **proof**: Proof collection only; no implementation changes.
- **audit**: Read-only inspection of existing surfaces; no changes.

## Status Definitions

- **planned**: Task is defined but not started.
- **in-progress**: Task is actively being worked on.
- **complete**: Task is done, committed, and proof is recorded.
- **blocked**: Task cannot proceed due to a dependency or discovered gap.

## Column Guidance

- **Task ID**: Unique identifier within the campaign. Format: `<CAMPAIGN>-TASK-<NNN>`.
- **Lane**: One of the lane definitions above.
- **Status**: One of the status definitions above.
- **Files**: Space-separated list of files touched by this task.
- **Validation**: Commands run to validate the task (e.g., `pytest -v tests/<path>`, `pnpm test -- <pattern>`).
- **Commit**: Git commit hash containing the task's changes.
- **Proof Artifact**: Reference to the proof pack entry for this task.
