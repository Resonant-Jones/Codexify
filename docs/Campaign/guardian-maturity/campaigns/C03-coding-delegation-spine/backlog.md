# C03 Task Queue

| Task ID | Lane | Status | Files | Validation | Commit | Proof Artifact |
|---------|------|--------|-------|------------|--------|----------------|
| C03-T001 | proof | complete | — (read-only) | Coding delegation spine proof pass | `ddaae17f0` | C03-PROOF-001 |
| C03-T002 | audit | planned | `guardian/routes/coding_work_orders.py`, `guardian/agents/`, `frontend/src/features/commandCenter/types.ts` | Work-order artifact contract audit | — | C03-PROOF-002 |
| C03-T003 | audit | planned | `guardian/routes/delegations.py`, `guardian/routes/guardian_delegations.py`, `guardian/workers/delegation_worker.py` | Delegation result-return seam audit | — | C03-PROOF-003 |
| C03-T004 | proof | planned | `guardian/routes/command_bus.py`, `guardian/command_bus/`, `frontend/src/test/api.command-bus.test.ts` | Command bus adjacency and invocation boundary proof | — | C03-PROOF-004 |
| C03-T005 | blocked | planned | `guardian/pi/validation.py`, `guardian/pi/contracts.py` | Pi/Coder validation route scaffold (blocked until C03-T001 confirms exact contract gap) | — | C03-PROOF-005 |
| C03-T006 | blocked | planned | `frontend/src/features/commandCenter/`, `frontend/src/features/chat/` | Operator-visible coding delegation status surface (blocked until backend proof sufficient) | — | C03-PROOF-006 |

## Lane Definitions

- **proof**: Proof collection only; no implementation changes.
- **audit**: Read-only inspection of existing surfaces.
- **blocked**: Task cannot proceed due to dependencies.
