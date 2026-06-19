# C05 Tool-Turn Observability Seam Audit

## Gate Decision

**`go`**

## Scope

This is a docs-only audit task. No runtime behavior changed. No release claim widened. It classifies existing tool-turn and command-run observability seams to prepare C05-T002 (define the tool-turn observability read model contract).

## Inputs Read

- `docs/architecture/00-current-state.md`
- `docs/architecture/agent-tool-loop-contract.md`
- `docs/architecture/tech-debt-and-risks.md`
- `docs/Campaign/guardian-maturity/wave-2-selection.md`
- `docs/Campaign/guardian-maturity/campaigns/C03-coding-delegation-spine/closeout.md`
- `guardian/protocol_tokens.py`
- `guardian/core/chat_completion_service.py`
- `guardian/workers/chat_worker.py`
- `guardian/command_bus/contracts.py`
- `guardian/routes/command_bus.py`
- `guardian/db/models.py`

## Current Truth Boundary

Per `00-current-state.md` (2026-06-16): local-first beta hardening, local-only posture, Docker Compose supported path. Guardian delegation and Pi/Coder execution are not release-supported. This audit does not widen release claims.

## C03 Carry-Forward

C03 surfaces now available to C05:
- Command bus manifest (106 commands).
- Command bus invocation with `run_id` returned.
- `GET /api/guardian/commands/runs/{run_id}` readback with `result_json`, `error_text`, actor metadata, timestamps.
- Work-order-to-command-run linkage via `latest_run_id`.
- Receipt persistence, creation, readback, and latest-receipt linkage.
- Operator receipt evidence UI in CodingWorkOrdersPanel.

## Bounded Tool-Turn Contract Summary

Per the Agent Tool Loop Contract:
- Exactly one model-chosen command-bus invocation per completion.
- Command result reinjected into completion messages as bounded context.
- Exactly one final assistant answer after reinjection.
- **No recursive loop**, no planner loop, no second tool turn.
- This is bounded observability, not autonomous agent observability.

## Existing Observability Fields

| Field | Status | Location |
|-------|--------|----------|
| `messageId` | **Persisted in assistant extra_meta** | `chat_worker.py:275-295` (`_persist_message_extra_meta`) |
| `requestId` | **Persisted in assistant extra_meta** | Same as above |
| `toolTurnId` | **Persisted in assistant extra_meta** | Generated at `chat_completion_service.py:170` (`_tool_loop_identity_fields`) |
| `toolTurnState` | **Persisted in assistant extra_meta** | Canonical tokens in `protocol_tokens.py:135` (`ToolTurnState` enum: idle, decision_received, command_dispatched, result_reinjected, completed, failed, limit_reached) |
| `loopStopReason` | **Persisted in assistant extra_meta** | Canonical tokens in `protocol_tokens.py:145/155` (`LoopStopReason`, `ToolLoopStopReason`) |
| `commandRunId` | **Persisted in assistant extra_meta** | Set at `chat_completion_service.py:1189` after command bus invoke returns `run_id` |

All six fields are defined, generated at runtime, and persisted in `chat_messages.extra_meta` via `_persist_message_extra_meta()`. They are also emitted in `task.state` COMPLETED callback at `chat_worker.py:2085-2096`.

## Backend Seam Inventory

| Source | Seam | What It Provides |
|--------|------|-----------------|
| `guardian/protocol_tokens.py:135-166` | `ToolTurnState`, `LoopStopReason`, `ToolLoopStopReason` | Canonical token vocabulary |
| `guardian/core/chat_completion_service.py:170-199` | `_tool_loop_identity_fields()` | Generates observability payload (toolTurnId, commandRunId, toolTurnState, loopStopReason, messageId, requestId) |
| `guardian/workers/chat_worker.py:176-183` | `_TOOL_LOOP_OBSERVABILITY_FIELDS` | Defines the six canonical fields extracted for persistence |
| `guardian/workers/chat_worker.py:645-662` | `_tool_loop_observability_payload()` | Extracts observability fields from completion result |
| `guardian/workers/chat_worker.py:2081-2110` | COMPLETED state callback | Emits observability data in task state events + persists to `chat_messages.extra_meta` |
| `guardian/workers/chat_worker.py:275-295` | `_persist_message_extra_meta()` | Writes tool-loop + provider metadata to `chat_messages.extra_meta` (JSONB merge) |
| `guardian/routes/command_bus.py:246-261` | `GET /api/guardian/commands/runs/{run_id}` | Durable CommandRun readback with `result_json`, `error_text`, actor metadata (C03-T008) |

## Event and Persistence Surface Inventory

| Surface | Classification | Notes |
|---------|---------------|-------|
| Task events (COMPLETED callback) | **Durable** — emitted in SSE stream | Contains `toolTurnId`, `commandRunId`, `toolTurnState`, `loopStopReason` in the COMPLETED state payload |
| `chat_messages.extra_meta` | **Durable** — persisted in Postgres | Contains all six observability fields + provider metadata (`attempted_provider`, `attempted_model`, `final_provider`, `final_model`, etc.) |
| CommandRun records | **Durable** — `command_runs` table | Contains `run_id`, `command_id`, `status`, `result_json`, `error_text`, actor metadata. Readable via C03-T008 route |
| CommandRun events | **Durable** — `command_run_events` table | SSE stream with `run.created`, `run.started`, `run.completed` |
| Logs | **Ephemeral** — diagnostic only | Not an operator truth surface |
| Receipt records | **Durable** — `work_order_result_receipts` table | C03-T012. Contains `observed_command_id`, `observed_run_status`, `observed_result_summary`, not raw tool-turn state |

## Frontend Surface Inventory

| Surface | Status |
|---------|--------|
| Command run ID display | **Not surfaced** — CommandRun readback exists but no frontend viewer |
| Tool turn ID display | **Not surfaced** |
| Tool turn state display | **Not surfaced** |
| Loop stop reason display | **Not surfaced** |
| Command result summary | **Partially surfaced** — receipt evidence UI shows `observed_result_summary` for work-order-linked receipts |
| Command failure reason | **Not surfaced** |
| Command blocked reason | **Not surfaced** |
| Receipt evidence | **Surfaced** — C03-T015 CodingWorkOrdersPanel |
| CommandRun readback | **Backend only** — no frontend consumer |

## Observability Gap Table

| Signal | Current source | Durable? | Frontend visible? | Risk if absent | Recommended follow-up |
|--------|---------------|----------|-------------------|----------------|---------------------|
| `toolTurnId` | `chat_messages.extra_meta` | Yes | No | Operator cannot trace tool-turn identity | Add tool-turn ID to chat message display |
| `toolTurnState` | `chat_messages.extra_meta` | Yes | No | Operator cannot see tool execution progress | Surface tool-turn state in chat or Command Center |
| `loopStopReason` | `chat_messages.extra_meta` | Yes | No | Operator cannot understand why loop stopped | Surface loop-stop reason |
| `commandRunId` | `chat_messages.extra_meta` + `command_runs` | Yes | No | Operator cannot cross-reference tool turn with CommandRun | Add commandRunId display with link to CommandRun readback |
| Command result summary | `command_runs.result_json` | Yes | Partially (receipts) | Operator cannot inspect command output without receipt | Surface `result_json` summary in Command Center |
| Command failure reason | `command_runs.error_text` | Yes | No | Operator cannot diagnose failed commands | Surface `error_text` in Command Center |
| Command blocked reason | Policy evaluation | No | No | Operator cannot understand blocked invocations | Surface policy decision in Command Center |
| Task event visibility | SSE stream | Ephemeral | No | Operator misses lifecycle events after disconnect | Add task-event summary to chat message |
| Assistant metadata | `chat_messages.extra_meta` | Yes | No | Tool-loop data exists but is invisible | Surface `extra_meta` tool-loop fields |
| CommandRun readback | `GET .../runs/{run_id}` | Yes | No | Backend route exists, no frontend consumer | Add Command Center CommandRun viewer |
| Receipt evidence linkage | `work_order_result_receipts` + `latest_receipt_id` | Yes | Yes (C03-T015) | Low — already surfaced for work orders | Extend to show tool-turn context if receipt is tool-turn observation |

## Operator Questions C05 Must Answer

1. Did the model request a tool turn?
2. Which command was selected?
3. Was the command dispatched?
4. Was the command blocked, failed, or completed?
5. Which CommandRun corresponds to the tool turn?
6. Was the command result reinjected?
7. Why did the loop stop?
8. Is the result durable or only diagnostic?
9. What can the operator safely inspect without seeing raw args or secrets?

**Findings**: Questions 1-7 have durable answers in `chat_messages.extra_meta` — they are stored but not surfaced. Question 8: the result is durable (both in `extra_meta` and `command_runs.result_json`). Question 9: `result_json` and `observed_result_summary` are the safe surfaces; raw args are redacted in `args_redacted`.

## Safety and Redaction Boundaries

Must not be surfaced:
- Raw args (stored as `args_redacted` in command runs)
- Secrets, credentials, API keys
- Hidden prompts, system prompts
- Unredacted command payloads
- Local surrogate database IDs where stable public IDs exist (`run_id`, `receipt_id`, `message_id`)

Safe to surface:
- `toolTurnId`, `commandRunId`, `messageId`, `requestId`
- `toolTurnState`, `loopStopReason`
- `observed_result_summary` (from receipt or CommandRun)
- `error_text` (from CommandRun)
- `args_redacted` summary
- Policy decision metadata (mode, decision, reason codes)

## Recommended C05 Implementation Order

1. **C05-T002: Define tool-turn observability read model contract** — specify exactly which fields from `extra_meta` and `command_runs` constitute the read model, their redaction boundaries, and their relationship to existing CommandRun readback and receipt evidence.
2. **C05-T003: Add tool-turn context to assistant message display** — surface `toolTurnId`, `commandRunId`, `toolTurnState`, `loopStopReason` in the chat message UI when a tool turn occurred.
3. **C05-T004: Add CommandRun viewer to Command Center** — frontend component that reads `GET /api/guardian/commands/runs/{run_id}` and displays `result_json`, `error_text`, actor metadata.
4. **C05-T005: Add tool-turn state timeline** — surface the sequence: `decision_received` → `command_dispatched` → `result_reinjected` → `completed`/`failed`/`limit_reached`.
5. **C05-T006: Add boundedness proof** — prove that the one-turn limit is enforced and visible, and that the UI does not imply recursive or autonomous execution.

## Gate Decision Rationale

**`go`** — The audit found all six canonical observability fields (`toolTurnId`, `commandRunId`, `toolTurnState`, `loopStopReason`, `messageId`, `requestId`) are defined, generated at runtime, and durably persisted in `chat_messages.extra_meta`. CommandRun records provide durable result/error storage with API readback (C03-T008). The gap is frontend surfacing — the data exists, it's just not visible. C05 can safely proceed to C05-T002 (define the read model contract) because the backend seams are proven and the redaction boundaries are clear.

## Release Boundary

- No runtime behavior changed by this audit.
- No release claim widened.
- No autonomous delegation claim added.
- No Pi/Coder execution claim added.
- No recursive tool loop claim added.
- `docs/architecture/00-current-state.md` remains authoritative.
