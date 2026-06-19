# C05 Decision Log

## Decision Index

| ID | Date | Decision | Status |
|----|------|----------|--------|
| C05-D001 | 2026-06-19 | `go` — tool-turn observability seam audit complete; all 6 fields durably persisted, frontend gap identified | active |
| C05-D002 | 2026-06-19 | `go` — read model contract defined; 15 fields, source priority, redaction, CommandRun/receipt relationships | active |

---

### Decision: C05-D001

- **Decision ID**: C05-D001
- **Date**: 2026-06-19
- **Decision**: Gate decision is `go`. Tool-turn observability seam audit found all six canonical fields defined, generated, and durably persisted. Backend seams are proven. Frontend surfacing is the gap.
- **Reason**:
  - `toolTurnId`, `commandRunId`, `toolTurnState`, `loopStopReason`, `messageId`, `requestId` are all generated in `chat_completion_service.py:_tool_loop_identity_fields()`.
  - Persisted durably in `chat_messages.extra_meta` via `chat_worker.py:_persist_message_extra_meta()`.
  - Emitted in task state COMPLETED callback via SSE.
  - CommandRun records provide durable result/error storage with API readback (C03-T008).
  - Canonical token vocabulary defined in `protocol_tokens.py` (ToolTurnState, LoopStopReason, ToolLoopStopReason).
  - Frontend has no surfacing of any tool-turn field.
  - Safety boundaries: raw args redacted, `result_json` and `observed_result_summary` are safe surfaces.
- **Evidence**:
  - `guardian/protocol_tokens.py:135-166` — canonical tokens.
  - `guardian/core/chat_completion_service.py:170-199` — identity fields generation.
  - `guardian/workers/chat_worker.py:176-183` — observability fields tuple.
  - `guardian/workers/chat_worker.py:275-295` — `_persist_message_extra_meta()`.
  - `guardian/workers/chat_worker.py:2081-2110` — COMPLETED callback with observability data.
- **Consequence**:
  - C05-T001 advances to `go`. C05 can proceed to C05-T002 (define read model contract).
  - Frontend implementation tasks (T003-T005) are planned but not started.
  - No runtime behavior changed — audit only.
- **Revisit Trigger**:
  - C05-T002 read model contract is defined — verify alignment with seam audit.
  - New tool-turn fields are added — re-audit.
  - CommandRun readback route changes — verify frontend compatibility.

---

### Decision: C05-D002

- **Decision ID**: C05-D002
- **Date**: 2026-06-19
- **Decision**: Gate decision is `go`. Read model contract defined with 15 canonical fields, source priority, field mapping, redaction rules, CommandRun/receipt relationships, and state interpretation. C05-T003 can proceed.
- **Reason**:
  - Defined 15 read model fields across 4 source layers (`extra_meta`, `command_runs`, command events, receipts).
  - Source priority: `extra_meta` → `command_runs` → events → receipts → task events → logs.
  - All redaction boundaries documented: raw args, secrets, prompts, unredacted payloads must not be surfaced.
  - State interpretation defined for all `ToolTurnState` and `LoopStopReason` tokens.
  - CommandRun relationship: `commandRunId` bridges to C03-T008 readback route.
  - Receipt relationship: `latestReceiptId` bridges to C03-T013 readback routes.
  - 4 unknowns recorded for follow-up in C05-T003.
- **Evidence**:
  - `tool-turn-read-model-contract.md` — 18 sections.
- **Consequence**:
  - C05-T002 advances to `go`. Read model contract established.
  - C05-T003 (backend read-model helper) can proceed with clear field definitions.
- **Revisit Trigger**:
  - C05-T003 discovers fields not defined in the contract.
  - New tool-turn or command-run fields are added to `extra_meta` or `command_runs`.
