# Agent Tool Loop Contract

Purpose: define the canonical bounded contract for the one-turn tool-augmented completion slice so runtime semantics and transcript integrity keep one stable vocabulary while the broader loop remains bounded.

Last updated: 2026-04-21

Source anchors:
- guardian/core/chat_completion_service.py
- guardian/core/ai_router.py
- guardian/workers/chat_worker.py
- guardian/command_bus/contracts.py
- guardian/command_bus/invoke.py
- guardian/protocol_tokens.py
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md

## Scope

- This is the contract for the implemented first bounded tool-augmented completion slice.
- The current runtime can still return a plain assistant answer with no tool turn, but it can now also execute exactly one model-chosen command-bus invoke, reinject the result, and request one final assistant answer.
- This document is about runtime semantics and transcript integrity, not UI design.
- It intentionally avoids any claim that the supported beta ships recursive or autonomous coding-agent execution.

## Implemented Runtime Truth

The completion service now normalizes provider output into one of two bounded outcomes:

1. Plain assistant output.
2. A structured tool decision.

If the provider returns plain output, the existing completion path continues.

If the provider returns a structured tool decision:

1. The runtime generates a `toolTurnId`.
2. The runtime executes exactly one command through the command bus.
3. The resulting `commandRunId` is captured.
4. The command result is re-injected into the completion messages as bounded context.
5. The runtime requests one final assistant answer.
6. The runtime hard-stops after that final answer.

No recursive retry choreography, planner loop, or second tool turn is part of this slice.

## Canonical Observability Fields

The bounded slice records these runtime fields at the backend seam and on task events:

- `messageId`
- `requestId`
- `toolTurnId`
- `toolTurnState`
- `loopStopReason`
- `commandRunId`

These fields are surfaced as explicit observability data, not hidden in prose or inline literals.

## Canonical Token Domains

Tool-turn states are canonical tokens in `guardian/protocol_tokens.py`:

- `idle`
- `decision_received`
- `command_dispatched`
- `result_reinjected`
- `completed`
- `failed`
- `limit_reached`

Loop stop reasons are canonical tokens in `guardian/protocol_tokens.py`:

- `plain_answer`
- `tool_turn_completed`
- `tool_decision_invalid`
- `tool_command_failed`
- `tool_command_blocked`
- `tool_turn_limit_reached`
- `cancelled`

## Failure Rules

- If the first provider response is malformed as a tool decision, the runtime stops with `tool_decision_invalid`.
- If command-bus execution fails, the runtime stops with `tool_command_failed`.
- If the model tries to request a second tool turn, the runtime stops with `tool_turn_limit_reached`.
- The runtime does not recurse on tool failure.
- The runtime does not silently downgrade a structured tool decision into an undefined loop.

## Contract Shape

The normalized provider result is intentionally small:

- `assistant`
  - plain text answer
- `tool_decision`
  - `command_id`
  - `arguments`
  - optional rationale text

The bounded command-bus result is equally small:

- `tool_turn_id`
- `request_id`
- `command_run_id`
- `tool_turn_state`
- `loop_stop_reason`
- `command_status`
- `command_error`

## Transcript Integrity Rules

- One authored turn.
- One request attempt.
- Optional one bounded tool turn.
- One final assistant answer.
- `messageId` stays the authored/persisted message identity.
- `requestId` stays the execution-attempt identity.
- Tool result reinjection must be explicit in the backend assembly path.
- No second tool turn is allowed in this slice.
