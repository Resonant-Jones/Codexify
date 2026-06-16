# C00 Task Queue

| Task ID | Lane | Status | Files | Validation | Commit | Proof Artifact |
|---------|------|--------|-------|------------|--------|----------------|
| C00-TASK-001 | proof | planned | — (read-only) | `git status --short --branch --untracked-files=all` | — | C00-PROOF-001 |
| C00-TASK-002 | proof | planned | — (read-only) | `/health`, `/health/chat`, `/health/llm` | — | C00-PROOF-002 |
| C00-TASK-003 | proof | planned | — (read-only) | `/api/llm/catalog`, `/api/llm/catalog?include=all` | — | C00-PROOF-003 |
| C00-TASK-004 | proof | planned | — (read-only) | Whoosh'd `/v1/models` or equivalent | — | C00-PROOF-004 |
| C00-TASK-005 | proof | planned | — (read-only) | Gate decision synthesis | — | C00-PROOF-005 |

## Lane Definitions

- **proof**: Proof collection only; no implementation changes. All C00 tasks are read-only.

## Status Definitions

- **planned**: Task is defined but not started. All C00 tasks start in this state.
