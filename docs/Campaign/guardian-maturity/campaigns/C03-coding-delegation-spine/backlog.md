# C03 Task Queue

| Task ID | Lane | Status | Files | Validation | Commit | Proof Artifact |
|---------|------|--------|-------|------------|--------|----------------|
| C03-T001 | proof | complete | — (read-only) | Route availability verification | `a5ad0349d` | C03-PROOF-001 |
| C03-T002 | config | complete | `config/supported_profiles/v1-local-core-web-mcp.yaml` | Route posture enablement + runtime proof | `fbb17ace7` | C03-PROOF-002 |
| C03-T003 | audit | complete | `guardian/agents/work_orders.py`, `guardian/db/models.py` | Work-order artifact contract audit | `8efdf59ee` | C03-PROOF-003 |
| C03-T004 | proof | complete | `guardian/routes/command_bus.py`, `guardian/command_bus/` | Command bus adjacency and invocation boundary proof | `2aa77d41c` | C03-PROOF-004 |
| C03-T005 | proof | complete | `guardian/command_bus/manifest.py` | Command bus manifest discovery + health invocation proof | `0cac2ec7b` | C03-PROOF-005 |
| C03-T006 | implementation | complete | `guardian/command_bus/contracts.py`, `guardian/command_bus/invoke.py`, `guardian/routes/command_bus.py`, `tests/routes/test_command_bus_work_order_linkage.py` | Work-order command-run linkage + fail-closed repair + 13 tests | `01cd0fa17` | C03-PROOF-006 |
| C03-T007 | audit | complete | — (read-only) | Result-return seam audit | `f03e5bf69` | C03-PROOF-007 |
| C03-T008 | implementation | complete | `guardian/routes/command_bus.py`, `tests/routes/test_command_bus_run_readback.py` | CommandRun readback route + 5 tests | `7850b39d9` | C03-PROOF-008 |
| C03-T009 | implementation | complete | `guardian/routes/coding_work_orders.py`, `tests/routes/test_coding_work_order_latest_run_readback.py` | Work-order latest-run readback bridge + 6 tests | `cc9bdea9f` | C03-PROOF-009 |
| C03-T010 | docs | complete | `docs/Campaign/.../work-order-result-receipt-contract.md` | Work-order result receipt contract | — | C03-PROOF-010 |
| C03-T011 | docs | complete | `docs/Campaign/.../work-order-result-receipt-persistence-design.md` | Receipt persistence seam design | — | C03-PROOF-011 |
| C03-T012 | backend | complete | `guardian/db/models.py`, `guardian/db/migrations/`, `guardian/routes/coding_work_orders.py`, `tests/routes/test_work_order_result_receipts.py` | Receipt persistence implementation + 4 tests | `TBD` | C03-PROOF-012 |
| C03-T013 | backend | complete | `guardian/routes/coding_work_orders.py`, `tests/routes/test_work_order_result_receipt_readback.py` | Receipt readback routes + 11 tests | `a5bebe592` | C03-PROOF-013 |
| C03-T014 | backend | complete | `guardian/agents/work_order_store.py`, `guardian/routes/coding_work_orders.py`, `tests/routes/test_work_order_latest_receipt_linkage.py` | `set_latest_receipt()` fail-closed linkage + 7 tests (R1–R4) | `e3681ac51` | C03-PROOF-014 |
| C03-T015 | frontend | complete | `frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx`, `.../__tests__/CodingWorkOrdersPanel.test.tsx` | Operator receipt display + 3 tests | `TBD` | C03-PROOF-015 |

## Lane Definitions

- **proof**: Proof collection only; no implementation changes.
- **audit**: Read-only inspection of existing surfaces.
- **config**: Supported-profile or configuration changes.
- **implementation**: Backend route, contract, or store changes.
- **docs**: Documentation-only — no code changes.
- **backend**: Backend schema, route, or persistence work.
- **frontend**: Frontend component, state, or UI work.
- **blocked**: Task cannot proceed due to dependencies.
