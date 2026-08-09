Purpose: Define the implemented bounded tool-augmented chat completion contract so the backend exposes one honest tool turn without implying a general autonomous agent loop.
Last updated: 2026-04-22
Source anchors:
- guardian/core/chat_completion_service.py
- guardian/core/ai_router.py
- guardian/workers/chat_worker.py
- guardian/command_bus/contracts.py
- guardian/command_bus/invoke.py
- guardian/protocol_tokens.py
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/provider-tool-turn-boundary-contract.md

## Adjacent Governing Contract

Provider wire translation is governed by
[`provider-tool-turn-boundary-contract.md`](./provider-tool-turn-boundary-contract.md).
That contract defines the canonical semantic seam between provider transport
and Codexify model/tool-turn semantics. The bounded runtime described in this
file consumes provider-normalized semantic outcomes; it does not consume
provider wire formats directly. The Stage 1 advertised-subset authorization
gate remains the pre-execution authority seam, and the one-tool-turn runtime
contract in this file is unchanged.

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
2. The runtime derives the canonical command IDs from the nonempty tool set authorized and advertised through `ChatCompletionTask.tools` for that request.
3. The selected canonical `command_id` must belong to that exact set; missing or nonmatching advertised authority stops with `tool_command_blocked` before `execute_invoke`, with `toolTurnState=failed` and no `commandRunId`.
4. Plaintext/JSON-normalized tool decisions pass through this same provider-neutral authority check and receive no bypass.
5. The runtime executes exactly one authorized command through the command bus.
6. The resulting `commandRunId` is captured.
7. The command result is re-injected into the completion messages as bounded context.
8. The runtime requests one final assistant answer.
9. The runtime hard-stops after that final answer.

No recursive retry choreography, planner loop, or second tool turn is part of this slice.

## Canonical Observability Fields

The bounded slice records these runtime fields at the backend seam, on task events, and in the durable assistant-message `extra_meta` payload:

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

`messageId` and `requestId` remain distinct identities.

The outer provider fallback `execution` remains authoritative for the completion attempt, while bounded tool-loop details are carried additively in `tool_loop_execution` so debug surfaces can inspect the tool turn without shadowing provider rescue truth.

The persisted assistant message keeps the same observability fields in `extra_meta`, so finished-run reads do not depend on transient worker memory to recover the tool-turn boundary.

## Non-Goals

- No general autonomous agent runtime.
- No recursive planner.
- No multi-tool orchestration.
- No bypass of the command bus for tool execution.
- No widening of the supported beta promise to autonomous coding.
