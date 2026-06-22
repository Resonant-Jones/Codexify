# C05 Tool-Turn Observability Read Model Contract

## Gate Decision

**`go`**

## Scope

This is a docs-only read-model contract. No runtime behavior changed. No release claim widened. It defines how existing tool-turn and command-run evidence should be read by future operator surfaces.

## Inputs Read

- `docs/architecture/00-current-state.md`
- `docs/architecture/agent-tool-loop-contract.md`
- `docs/Campaign/guardian-maturity/campaigns/C05-command-bus-tool-turn-observability/seam-audit.md`
- `guardian/protocol_tokens.py`
- `guardian/core/chat_completion_service.py`
- `guardian/workers/chat_worker.py`
- `guardian/routes/command_bus.py`
- `guardian/db/models.py`

## Current Truth Boundary

Per `00-current-state.md`: local-first beta hardening, local-only posture. Guardian delegation and Pi/Coder execution are not release-supported. C05 does not make delegation release-supported.

## Purpose

Define exactly which fields constitute the read model for operator-visible tool-turn observability, where each field comes from, whether it is durable, how it relates to CommandRun readback and receipt evidence, and what redaction rules apply. The read model is observation-only — it reads existing data, it does not mutate, execute, or create.

## Non-Goals

- No new runtime behavior
- No new route
- No new frontend component
- No tool execution change
- No command bus change
- No recursive tool loop
- No autonomous delegation
- No Pi/Coder execution
- No release support expansion

## Canonical Read Model Fields

| Field | Source | Required? | Durable? | Safe to display? | Notes |
|-------|--------|-----------|----------|-----------------|-------|
| `messageId` | `chat_messages.extra_meta` | Yes | Yes (Postgres) | Yes | Stable public message identity |
| `requestId` | `chat_messages.extra_meta` | Yes | Yes (Postgres) | Yes | Request/attempt identity |
| `toolTurnId` | `chat_messages.extra_meta` | Yes | Yes (Postgres) | Yes | Generated at `_tool_loop_identity_fields()` |
| `toolTurnState` | `chat_messages.extra_meta` | Yes | Yes (Postgres) | Yes | Canonical tokens: idle, decision_received, command_dispatched, result_reinjected, completed, failed, limit_reached |
| `loopStopReason` | `chat_messages.extra_meta` | Yes | Yes (Postgres) | Yes | Canonical tokens from `LoopStopReason` / `ToolLoopStopReason` |
| `commandRunId` | `chat_messages.extra_meta` | Yes | Yes (Postgres) | Yes | Bridges to `GET /api/guardian/commands/runs/{run_id}` |
| `commandId` | `command_runs.command_id` | Yes | Yes (Postgres) | Yes | The invoked command identity |
| `commandStatus` | `command_runs.status` | Yes | Yes (Postgres) | Yes | queued, running, completed, failed, blocked |
| `commandResultSummary` | `command_runs.result_json` → summarized | Yes | Yes (Postgres) | **Summarized only** | Never display raw `result_json` |
| `commandErrorSummary` | `command_runs.error_text` | Optional | Yes (Postgres) | Yes | Display directly — already text |
| `commandBlockedReason` | Policy evaluation / `command_runs` | Optional | No (ephemeral) | Yes | Policy decision reason codes |
| `createdAt` | `command_runs.created_at` | Yes | Yes (Postgres) | Yes | Command execution timestamp |
| `receiptIds` | `work_order_result_receipts` | Optional | Yes (Postgres) | Yes | Linked receipt IDs for work-order context |
| `latestReceiptId` | `coding_work_orders.latest_receipt_id` | Optional | Yes (Postgres) | Yes | Latest receipt pointer |

## Source Priority

Read priority for future UI/API composition:

1. `chat_messages.extra_meta` — canonical tool-turn identity and loop-stop metadata (C05-T001 proven)
2. `command_runs` — durable command execution status, result, and error evidence (C03-T008 proven)
3. `command_run_events` — ordered command lifecycle details (SSE stream, C03-T005 proven)
4. `work_order_result_receipts` — reviewed/linked observation records when work-order context exists (C03-T012/T013 proven)
5. Task events — live diagnostic context only (SSE, ephemeral)
6. Logs — diagnostic-only fallback, not durable operator truth

## Field Mapping

| Read model field | Primary source | Fallback source | Display form | Redaction rule |
|---|---|---|---|---|
| `toolTurnId` | `chat_messages.extra_meta.toolTurnId` | None | Raw ID string | None — safe ID |
| `toolTurnState` | `chat_messages.extra_meta.toolTurnState` | None | Canonical token label | None — safe token |
| `loopStopReason` | `chat_messages.extra_meta.loopStopReason` | None | Canonical token label | None — safe token |
| `commandRunId` | `chat_messages.extra_meta.commandRunId` | None | Raw ID string | None — safe ID |
| `commandId` | `command_runs.command_id` | `chat_messages.extra_meta` | Raw ID string | None — safe ID |
| `commandStatus` | `command_runs.status` | None | Canonical token label | None — safe token |
| `commandResultSummary` | `command_runs.result_json` → summarize | Receipt `observed_result_summary` | Human-readable summary | **Never raw JSON** |
| `commandErrorSummary` | `command_runs.error_text` | None | Raw text (already safe) | Display directly |
| `commandBlockedReason` | Policy decision reason codes | `command_run_events` | Token label + detail | None — safe codes |
| `receiptIds` | `work_order_result_receipts.receipt_id` | None | Raw ID string | None — safe ID |
| `latestReceiptId` | `coding_work_orders.latest_receipt_id` | None | Raw ID string | None — safe ID |

## State Interpretation

Operator interpretation for tool-turn state and loop-stop reason:

| Token | Meaning |
|-------|---------|
| `idle` | No tool decision received yet |
| `decision_received` | Model requested a bounded tool turn |
| `command_dispatched` | Command bus invocation was attempted |
| `result_reinjected` | Command result was reinjected into assistant context |
| `completed` | Bounded tool turn completed successfully |
| `failed` | Bounded tool turn failed |
| `limit_reached` | Runtime prevented additional tool turns (one-turn limit) |

| Token | Meaning |
|-------|---------|
| `plain_answer` / `model_final_answer` | No tool turn — final assistant answer |
| `tool_turn_completed` | Tool turn finished and result reinjected |
| `tool_decision_invalid` | Model output was malformed as a tool decision |
| `tool_command_failed` | Command bus execution failed |
| `tool_command_blocked` | Command blocked by policy or validation |
| `tool_turn_limit_reached` | Runtime enforced the one-turn limit |
| `cancelled` | Turn cancelled before tool execution completed |

## Relationship to CommandRun Readback

- `commandRunId` is the bridge from tool-turn metadata (`chat_messages.extra_meta`) to CommandRun readback (`GET /api/guardian/commands/runs/{run_id}`).
- CommandRun readback provides durable execution evidence: `result_json`, `error_text`, `status`, actor metadata, timestamps.
- CommandRun readback must not expose raw args or secrets.
- Future UI should link from tool-turn evidence to CommandRun details through safe summaries only.

## Relationship to Receipt Evidence

- Receipts are observation records (C03-T010).
- Receipts are not artifacts, do not mark work orders complete, and do not prove autonomous coding-agent execution.
- `latestReceiptId` may summarize a CommandRun result in work-order context.
- Receipt evidence (`observed_result_summary`, `observed_error_text`, `integrity_hash`) can enrich the tool-turn read model when a work order is linked.

## Redaction and Safety Rules

**Must not be surfaced:**
- Raw args (`args_redacted` is stored; raw args are not)
- Secrets, credentials, API keys
- Hidden prompts, system prompts
- Unredacted command payloads
- Local surrogate database IDs where stable public IDs exist (`run_id`, `receipt_id`, `message_id`)

**Safe to display:**
- Stable IDs: `toolTurnId`, `commandRunId`, `messageId`, `requestId`, `receiptId`
- Status tokens: `toolTurnState`, `commandStatus`
- Loop-stop reason tokens
- `commandId`
- Safe result summary (summarized from `result_json`, not raw)
- Safe error summary (`error_text` — already text)
- Redaction summary from receipt
- Integrity hash from receipt

## Operator Questions Answered

The read model must answer:

1. Did the model request a tool turn? → `toolTurnState ≠ idle`
2. Which command was selected? → `commandId`
3. Was the command dispatched? → `commandStatus ≠ queued`
4. Was the command blocked, failed, or completed? → `commandStatus` + `loopStopReason`
5. Which CommandRun corresponds to the tool turn? → `commandRunId`
6. Was the result reinjected? → `toolTurnState = result_reinjected`
7. Why did the loop stop? → `loopStopReason`
8. Is the evidence durable or diagnostic only? → Durable (Postgres)
9. Is there a linked work-order receipt? → `latestReceiptId`
10. What can the operator inspect safely? → Summaries, tokens, IDs; never raw args/secrets

## Unknowns and Follow-Up

- Whether `commandBlockedReason` exists as a durable field on `command_runs` or is only in policy evaluation (ephemeral). If ephemeral, C05-T003 should capture it in the read-model helper.
- Whether `commandResultSummary` needs a dedicated summarization helper, or if the receipt creation route's `_summarize_result()` can be reused/extracted.
- Whether frontend has a central type location for future read-model types (`frontend/src/features/commandCenter/types.ts` is a candidate).
- Whether `chat_messages.extra_meta` is directly accessible via existing message readback routes (`GET /api/chat/{thread_id}/messages`) or needs a dedicated readback endpoint.

## Recommended Next Task

**C05-T003: Add backend read-model helper for tool-turn observability**

## Release Boundary

- No runtime behavior changed.
- No release claim widened.
- No autonomous delegation claim added.
- No Pi/Coder execution claim added.
- No recursive tool loop claim added.
- `docs/architecture/00-current-state.md` remains authoritative.
