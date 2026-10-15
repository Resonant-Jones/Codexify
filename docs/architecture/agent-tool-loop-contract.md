Purpose: Define the implemented bounded tool-augmented chat completion contract so the backend exposes one honest tool turn without implying a general autonomous agent loop.
Last updated: 2026-10-14
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
For a task that claims the accepted-chat lifecycle, this plain answer is still
reconciled against the durable checkpoint first, so it can never replace an
already frozen tool decision.

## Checkpoint Scope For Direct Completions

Checkpoint reconciliation is scoped to tasks that claim the accepted-chat
lifecycle, identified by the ADR-087 accepted deadline snapshot that only
`enqueue_chat_completion` mints alongside the durable `ChatCompletionAttempt`.

This distinction exists because not every completion is an accepted chat
attempt. The voice worker constructs a `ChatCompletionTask` directly and calls
`run_chat_completion_task`, so it owns no accepted attempt and no attempt row;
the hosted-room and chat-route paths both go through `enqueue_chat_completion`
and therefore do own one. A missing request id is not the discriminator, because
`ChatCompletionTask.__post_init__` synthesizes a `req_...` id for every task.

The scoping preserves both directions:

- An unbound direct completion is not rejected for lacking a checkpoint it was
  never able to create, so ordinary voice turns still answer and persist.
- A task that claims acceptance must still present a matching durable row and
  fails closed when it does not; a claim is never downgraded to the unchecked
  path because its record is absent or mismatched.
- An unbound completion may not dispatch a replay-protected tool command at all,
  even if tool IDs were advertised to it, because there is no accepted attempt
  against which to freeze a checkpoint.

A present-but-invalid acceptance snapshot is treated as a claim so that a
corrupted acceptance envelope fails closed rather than silently becoming
unbound.

If the provider returns a structured tool decision:

1. Guardian uses the accepted `requestId` and its durable
   `ChatCompletionAttempt` to freeze one tool decision. The checkpoint records
   the stable `toolTurnId`, canonical command ID, canonical arguments hash, and
   creation time. It stores no raw arguments or provider payload.
2. The runtime derives the canonical command IDs from the nonempty tool set authorized and advertised through `ChatCompletionTask.tools` for that request.
3. The selected canonical `command_id` must belong to that exact set; missing or nonmatching advertised authority stops with `tool_command_blocked` before `execute_invoke`, with `toolTurnState=failed` and no `commandRunId`.
4. Plaintext/JSON-normalized tool decisions pass through this same provider-neutral authority check and receive no bypass.
5. After the advertised-subset gate and durable request, task, thread, turn,
   and account binding checks, the first decision wins an atomic checkpoint
   commit. The attempt row is committed before queue enqueue; the checkpoint
   columns on that row are the checkpoint authority, and the row's `accepted_at`
   column may be recorded later without being the checkpoint authority gate.
   A matching retry uses its stored `toolTurnId`; a different command or
   argument hash fails before Command Bus dispatch. A plain answer cannot
   replace a previously frozen decision.
6. The runtime executes exactly one authorized command through the command bus.
   An idempotent Command Bus replay may reuse its existing run only when the
   command identity, key, authorization subject, and canonical arguments hash
   match the original invocation. Conflicting or missing stored identity
   fails closed before returning a prior result or executing another command.
7. The resulting `commandRunId` is captured. `CommandRun` remains the authority
   for command status and result; a queued or running run is not a completed
   tool result. Matching replay reuses its completed result and cannot execute
   the command a second time under the same key.
8. The command result is re-injected into the completion messages as bounded context.
9. The runtime requests one final assistant answer.
10. The runtime hard-stops after that final answer.

No recursive retry choreography, planner loop, or second tool turn is part of this slice.

## Same-Task Reentry Proof

A deterministic PostgreSQL-backed integration test now demonstrates same-task
reentry after a completed `CommandRun` and before assistant-message persistence.
The first provider continuation is interrupted after command completion. A
separate chat database handle reads the accepted attempt checkpoint, and a
separate Command Bus store reads the completed run and its stored result. A
matching replay retains the frozen `toolTurnId`, passes the original command
and canonical arguments through the existing idempotency key, receives the
original `commandRunId` and result, and persists one assistant answer. The
loopback command transport is mocked and counted once; the PostgreSQL-backed
checkpoint and CommandRun persistence are real. The test also confirms that
`running` is rejected as incomplete, `failed` remains a terminal failure, and
secret-bearing arguments are not present in persisted redacted arguments or
assistant metadata.

The durable recovery evidence is limited to the existing accepted
`ChatCompletionAttempt` binding and frozen command ID, argument hash, and
`toolTurnId`, plus the Command Bus `CommandRun` identity, status, authorization
subject, argument hash, and completed result. A replay must use the original
request/task/thread/turn/account binding. Changed command or arguments conflict
before dispatch; a plain answer cannot replace a frozen tool decision; missing
or mismatched ownership fails closed. CommandRun status remains authoritative:
queued/running runs are not reinjected as completed results, and failed or
blocked runs do not trigger an automatic side-effect retry.

Reentry repeats provider inference. For DeepSeek, the continuation uses the
newly returned raw assistant tool call and that response's own `tool_call_id`;
the provider regression test uses a different ID after reentry and confirms
the tool result is correlated to that current ID. Whoosh'd continues through
its existing structured translator, and the generic provider path uses its
existing bounded result message. Provider-private state is not reconstructed
from canonical identity. If inference does not reproduce the frozen canonical
decision, reentry fails closed. Recovery from an opaque provider session that
requires prior private continuation bytes unavailable in the current provider
response remains unsupported; no provider continuation payload is added to
durable storage here.

The persisted assistant message now carries the accepted `requestId`, authored
`turnId`, stable `toolTurnId`, original `commandRunId`, provider/model, and
terminal evidence in its existing `extra_meta`, committed atomically with the
message row on the Postgres chat adapter. Existing worker turn deduplication
prevents a second completion attempt from creating another answer after that
turn is already persisted.

This proof uses fresh database handles and deterministic injected provider
outputs; it is not a full process restart. It does not prove dequeued-task
redelivery, automatic worker resurrection, recovery after arbitrary process
loss, live Compose restart recovery, or multi-step coding execution. Those
remain separate proof requirements.

## Canonical Observability Fields

The bounded slice records these runtime fields at the backend seam, on task events, and in the durable assistant-message `extra_meta` payload:

- `messageId`
- `requestId`
- `turnId`
- `toolTurnId`
- `toolTurnState`
- `loopStopReason`
- `commandRunId`
- `provider`
- `model`
- `terminalEvidence`
- `commandStatus`

These fields are surfaced as explicit observability data, not hidden in prose or inline literals.

## Stage 2J-R5 Exposure Observability

The completion payload summary, persisted assistant metadata, and terminal
completion evidence may carry one nested `toolExposure` object for the initial
provider attempt:

```json
{
  "automatic": true,
  "advertisedToolCount": 1,
  "advertisedToolCommandIds": ["op::health_health_get"],
  "providerDispatchToolCount": 1,
  "providerDispatchToolCommandIds": ["op::health_health_get"],
  "commandIdsTruncated": false
}
```

`automatic` is true only when `task.tools` was unset before ordinary-chat
exposure resolution. Explicit lists, including `[]`, remain authoritative and
record `automatic=false`. The two ID arrays contain sorted canonical command
identities only, are capped at 16 entries, and are accompanied by the real
count; `commandIdsTruncated` is true when either bounded array was truncated.

`toolExposure` is bounded observability, not an authority token. It contains no
tool schema, description, arguments, provider payload, prompt, credentials, or
provider-private continuation state. Stage 1 remains the authority gate: an
advertised capability still requires a matching normalized canonical command
before execution.

Advertisement makes a capability available to a model. It does not require the
model to select it. Under the current contract, an advertised capability and a
plain assistant answer are both valid; no tool-selection policy is introduced
by this evidence surface.

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

## Accepted Turn Identity Through Queue and Persistence

Accepted chat enqueue assigns the server-resolved authored `turn_id` to the
typed `ChatCompletionTask` before queue serialization. The task serializer and
deserializer preserve that value across the Redis boundary; client and provider
output do not choose or replace it. Checkpoint authorization uses the restored
accepted turn identity together with the durable request, task, thread, and
account binding. Historical tasks without the typed field may derive the turn
from the existing canonical `origin` segment, subject to the same durable
authority checks.

Assistant insertion stores canonical snake-case `turn_id` in `extra_meta` in
the same message transaction as the assistant row, while retaining the existing
`turnId` observability field. Worker deduplication queries the snake-case value,
so a fresh database handle can find the assistant immediately after insertion;
the later worker metadata enrichment remains compatible but is not required for
deduplication. This preserves turn correlation when a worker stops after
assistant insertion. It does not establish arbitrary concurrent-writer
exactly-once behavior, full-process restart recovery, or automatic worker
recovery.

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

## Stage 2I Ordinary Read-Only Exposure

After effective provider/model resolution and before the first provider
request, ordinary chat whose `task.tools` is `None` may now receive exactly
one model-visible ToolSpec: `op::health_health_get` (`GET /health`). Its
model-facing schema is an empty object with `additionalProperties=false` and
`maxProperties=0`; the model receives no path, query, header, or body input.

The resolved `task.tools` list is still the exact Stage 1 advertised subset.
Model visibility does not grant execution authority: a normalized command must
still match that list before `execute_invoke`, and the one-command hard limit
is unchanged. Explicit non-empty `task.tools` and explicit `task.tools=[]`
remain untouched and are never merged with automatic exposure.
