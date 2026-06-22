# C02 Task Queue

| Task ID | Lane | Status | Files | Validation | Commit | Proof Artifact |
|---------|------|--------|-------|------------|--------|----------------|
| C02-T001 | proof | complete | — (read-only) | Authenticated backend chat completion | `90d54287e` | C02-PROOF-001 |
| C02-T002 | audit | planned | `frontend/src/contracts/runtimeTokens.ts`, `frontend/src/features/chat/hooks/useInferenceRequestState.ts` | Request state mapping audit | — | C02-PROOF-002 |
| C02-T003 | proof | planned | `GET /api/tasks/{id}/events` | SSE/task-event visibility proof | — | C02-PROOF-003 |
| C02-T004 | proof | planned | `GET /api/chat/{thread_id}/messages` | Transcript persistence proof | — | C02-PROOF-004 |
| C02-T005 | audit | planned | `guardian/queue/`, `guardian/workers/`, `frontend/src/features/chat/` | Retry/replay/orphan seam audit | — | C02-PROOF-005 |
| C02-T006 | frontend | blocked | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/shared/runtimeVisualState.ts` | UI state presentation (blocked until proof sufficient) | — | C02-PROOF-006 |

## Lane Definitions

- **proof**: Proof collection only; no implementation changes.
- **audit**: Read-only inspection of existing surfaces.
- **frontend**: Frontend component, state, or hook changes.
- **blocked**: Task cannot proceed due to dependencies.

## Status Definitions

- **planned**: Task is defined but not started.
- **in-progress**: Task is actively being worked on.
- **complete**: Task is done, committed, and proof is recorded.
- **blocked**: Task cannot proceed due to a dependency or discovered gap.
