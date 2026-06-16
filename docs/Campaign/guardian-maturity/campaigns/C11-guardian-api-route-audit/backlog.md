# C11 Task Queue

| Task ID | Lane | Status | Files | Validation | Commit | Proof Artifact |
|---------|------|--------|-------|------------|--------|----------------|
| C11-TASK-001 | audit | planned | `guardian/guardian_api.py`, `guardian/routes/` | Route registration grep + file inspection | — | C11-PROOF-001 |
| C11-TASK-002 | audit | planned | Health routes (`/health`, `/health/chat`, `/health/llm`, `/api/health/llm`, `/api/health/retrieval`) | HTTP request verification | — | C11-PROOF-002 |
| C11-TASK-003 | audit | planned | Provider/catalog routes (`/api/llm/catalog`, `/api/llm/catalog?include=all`) | HTTP request verification | — | C11-PROOF-003 |
| C11-TASK-004 | audit | planned | Work order routes (POST/GET/PATCH) | Route presence inspection | — | C11-PROOF-004 |
| C11-TASK-005 | audit | planned | Command bus routes (run listing, detail, tool turn state) | Route presence inspection | — | C11-PROOF-005 |
| C11-TASK-006 | audit | planned | Pi/Coder invocation routes (validation, preview) | Route presence inspection | — | C11-PROOF-006 |
| C11-TASK-007 | audit | planned | Execution ledger routes | Route presence inspection | — | C11-PROOF-007 |
| C11-TASK-008 | audit | planned | Auth/session operator status routes | Route presence inspection | — | C11-PROOF-008 |
| C11-TASK-009 | audit | planned | Task event / SSE routes (`/api/tasks/<id>/events`) | Route presence inspection | — | C11-PROOF-009 |
| C11-TASK-010 | proof | planned | Gap analysis and dependency mapping | Synthesis of TASK-001 through TASK-009 | — | C11-PROOF-010 |

## Lane Definitions

- **audit**: Read-only inspection of existing route surfaces; no implementation.
- **proof**: Synthesis and documentation of audit findings.

## Status Definitions

- **planned**: Task is defined but not started. All C11 tasks start in this state.
