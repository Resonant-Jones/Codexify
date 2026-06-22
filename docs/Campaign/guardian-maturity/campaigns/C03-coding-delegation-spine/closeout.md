# C03 Coding Delegation Spine Closeout

## Gate Decision

**`go`**

Final accepted commit: `f3067c4e8` — test: close Guardian receipt evidence UI proof

## Scope

C03 proves the work-order, command-run, result receipt, readback, linkage, and operator evidence surfaces. This is a **coding delegation spine** — the infrastructure for governed coding work tracking and result observation. It is **not** end-to-end autonomous coding-agent execution. It is **not** Pi/Coder execution. It is **not** a public release claim for Guardian-mediated delegation.

## Proven Surfaces

| Task | Surface | Gate |
|------|---------|------|
| C03-T001 | Route availability verified | `go` |
| C03-T002 | Internal-only posture enabled | `go` |
| C03-T003 | Work-order artifact contract classified (7 ADR-020 fields present, 5 absent) | `go` |
| C03-T004 | Command bus boundary classified (adjacent, not equivalent to coding-agent) | `go` |
| C03-T005 | Command bus manifest discovery + health invocation proven (106 commands) | `go` |
| C03-T006 | Work-order to command-run linkage proven + fail-closed repair + 13 tests | `go` |
| C03-T007 | Result-return seam classified (CommandRun durable, no readback route identified) | `go` |
| C03-T008 | `GET /api/guardian/commands/runs/{run_id}` readback added + 5 tests | `go` |
| C03-T009 | `GET /api/coding/work-orders/{id}/latest-run` bridge added + 6 tests | `go` |
| C03-T010 | Work-order result receipt contract defined (docs-only) | `go` |
| C03-T011 | Receipt persistence seam designed (16-section design doc) | `go` |
| C03-T012 | Receipt persistence: model, migration, `POST .../receipts`, 10 tests | `go` |
| C03-T013 | Receipt readback: `GET .../receipts/{id}`, `GET .../receipts`, 11 tests | `go` |
| C03-T014 | `latest_receipt_id` fail-closed linkage: `set_latest_receipt()`, 7 tests | `go` |
| C03-T015 | Operator receipt evidence UI in CodingWorkOrdersPanel, 16 frontend tests | `go` |

## Current Operator Truth

An operator can now:

1. Create and inspect durable coding work orders (`wo_` IDs, 15-state status DAG).
2. Invoke safe read-only commands through the command bus (106 auto-discovered commands).
3. Link command runs to work orders via `latest_run_id`.
4. Read back durable CommandRun records by `run_id`.
5. Resolve a work order's latest run via `GET .../latest-run`.
6. Create immutable result receipts observing linked CommandRun results.
7. Read back receipts individually or as a list.
8. Inspect the latest receipt pointer on a work order.
9. View receipt evidence (kind, command, status, summary, hash, schema) in the CodingWorkOrdersPanel.
10. See truth-labeling that distinguishes receipt evidence from artifacts, work-order completion, and coding-agent execution.

## Still Not Release-Supported

- End-to-end Guardian-mediated delegation.
- Pi/Coder execution (contracts exist in `guardian/pi/`, zero route registration).
- Autonomous coding-agent execution (command bus is bounded single-command, not multi-step agent).
- Artifact creation (receipts observe; they do not create artifacts).
- Worker orchestration for coding agents (agent worker exists but is not proven by C03).
- Mutation controls in the receipt UI (receipt display is read-only evidence).

## Safety Boundaries Preserved

- Redaction: raw args, secrets, prompts, hidden runtime data not exposed.
- No shell/subprocess/git execution.
- No Pi/Coder invocation.
- No repository mutation.
- No artifact creation.
- Work-order completion not implied by receipt or command run.
- Receipt display is read-only — no create, execute, retry, replay, or approve controls.

## Validation Summary

- **Backend**: 52 tests passing across 6 test files (linkage, readback, persistence, latest-run, CommandRun readback).
- **Frontend**: 16 tests passing (CodingWorkOrdersPanel including receipt evidence).
- **Docs**: `python3 scripts/validate_docs.py` passed. `git diff --check` clean.
- **Migration**: Alembic upgrade/downgrade/re-upgrade cycle clean for `work_order_result_receipts`.

## Next Handoff

**C05/C06 wave selection**: choose the next Guardian Maturity Wave 2 campaign based on current blockers. Candidates: C05 (Command Bus and Tool Turn Observability) or C06 (Guardian Operator Workspace).
