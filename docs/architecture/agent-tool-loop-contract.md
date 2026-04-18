# Agent Tool Loop Contract

Purpose: define the canonical bounded contract for future ReAct / function-calling orchestration so runtime semantics and transcript integrity have one stable vocabulary before any live loop is implemented.

Last updated: 2026-04-17

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/system-overview.md
- docs/architecture/flows.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/modules-and-ownership.md
- guardian/core/chat_completion_service.py
- guardian/core/ai_router.py
- guardian/tools/spec.py
- guardian/routes/tools.py
- guardian/command_bus/contracts.py
- guardian/command_bus/invoke.py

## Scope

- This is a contract for future bounded tool-calling orchestration.
- The current runtime is still queue-backed single-pass completion and does not yet emit this loop contract.
- This document is about runtime semantics and transcript integrity, not UI design.
- It intentionally avoids live provider tool-calling, loop execution, or any claim that the supported beta already ships autonomous coding-agent execution.

## Current Truth Anchors

### What is true now

- Chat completion is still single-pass. `run_chat_completion_task()` assembles one provider-ready bundle, calls one provider path, and persists one assistant message when persistence is enabled. (`guardian/core/chat_completion_service.py`)
- Provider execution currently returns assistant content, not a looped tool-turn runtime object. `chat_with_ai()` returns the provider response text (or a provider response wrapper), and `run_chat_completion_task()` persists that assistant text. (`guardian/core/ai_router.py`, `guardian/core/chat_completion_service.py`)
- The command bus already exists as the durable execution substrate for command-style work, with persisted runs, run events, idempotency, and policy gating. (`guardian/command_bus/contracts.py`, `guardian/command_bus/invoke.py`)
- `/tools` is a compatibility shim over command-bus-backed behavior, not the canonical execution contract. (`guardian/routes/tools.py`)
- Policy, approval, and idempotency semantics already exist at the command bus and tools layers. (`guardian/command_bus/contracts.py`, `guardian/command_bus/invoke.py`, `guardian/routes/tools.py`, `guardian/tools/spec.py`)

### What is not yet true

- Bounded ReAct-style orchestration is not part of the current supported beta promise. The supported current release state still describes queue-backed completion, not autonomous tool-loop execution. (`docs/architecture/00-current-state.md`)
- The current supported runtime does not yet emit `AgentLoopRun` or `ToolCallTurn` objects.
- There is no live provider tool-calling loop in the current backend path.
- `/tools` behavior is not the canonical long-term execution semantics for future agent loops.

### What this task may assume

- The future loop contract may reuse the existing command bus, tool registry, policy layer, approval vocabulary, and runtime token philosophy instead of inventing a parallel execution truth surface.
- Identity and request boundaries remain separate, as already established by the chat runtime contract.
- Canonical loop states and stop reasons must be tokenized, bounded vocabularies rather than ad hoc literals.

## Canonical Entities

### `AgentLoopRun`

Purpose:

- Durable envelope for one assistant attempt that may decide zero or more tool turns before emitting a final answer or stopping for a bounded reason.

Ownership / parent relationship:

- Owned by one assistant authored message identity (`messageId`).
- Executed by one provider request attempt identity (`requestId`).
- Contains zero or more child `ToolCallTurn` records.
- Sits under one logical chat turn, but it is not the chat turn itself.

Required fields:

- `messageId`
- `requestId`
- `attemptNumber`
- `loopIndex`
- `state`
- `toolTurns`
- `createdAt`
- `updatedAt`

Optional fields:

- `provider`
- `model`
- `providerRuntimeState`
- `stopReason`
- `startedAt`
- `completedAt`
- `cancelledAt`
- `errorPayload`

Identity rules:

- `messageId` is the stable authored-message identity.
- `requestId` is the execution attempt identity.
- `attemptNumber` increments when the same authored message is replayed or retried.
- `loopIndex` is zero-based and counts the bounded assistant/tool passes inside the run.

Invariants:

- One `AgentLoopRun` maps to one provider request attempt.
- Tool turns cannot outlive their parent `requestId`.
- A terminal run must carry a terminal `state` and, when applicable, a terminal `stopReason`.
- The run record must never collapse message identity into request identity.

### `ToolCallTurn`

Purpose:

- One chosen tool invocation inside an `AgentLoopRun`, from model tool selection through policy, command-bus execution, and terminal result or block payload.

Ownership / parent relationship:

- Child of exactly one `AgentLoopRun`.
- Subordinate to the parent assistant `messageId`, `requestId`, `attemptNumber`, and `loopIndex`.
- May map to one command-bus run, but a chosen tool is not the same thing as an executed tool.

Required fields:

- `toolTurnId`
- `messageId`
- `requestId`
- `attemptNumber`
- `loopIndex`
- `toolId`
- `commandId`
- `providerToolCallId`
- `providerFunctionName`
- `rawArguments`
- `normalizedArguments`
- `policySummary`
- `state`
- `createdAt`
- `updatedAt`

Optional fields:

- `commandBusRun`
- `resultPayload`
- `errorPayload`
- `approvedAt`
- `startedAt`
- `completedAt`
- `blockedAt`
- `failedAt`

Identity rules:

- `toolTurnId` is the stable identity for the specific tool invocation.
- `providerToolCallId` is provider-facing and only stable within the originating provider response.
- `toolTurnId` is subordinate to the parent `requestId`.
- Replays create new `toolTurnId` values even when the authored `messageId` remains stable.

Invariants:

- Tool choice is not tool execution.
- A blocked or denied turn must not be reported as completed.
- A completed turn must carry a result payload.
- A failed turn must carry an error payload.

## Exact Contract Shape

### `AgentLoopRun`

```ts
export const AgentLoopRunState = {
  RUNNING: "running",
  COMPLETED: "completed",
  BLOCKED: "blocked",
  FAILED: "failed",
  CANCELLED: "cancelled",
} as const;

export type AgentLoopRunState =
  (typeof AgentLoopRunState)[keyof typeof AgentLoopRunState];

export const AgentLoopStopReason = {
  MODEL_FINAL_ANSWER: "model_final_answer",
  TOOL_CALL_BLOCKED: "tool_call_blocked",
  TOOL_CALL_DENIED: "tool_call_denied",
  TOOL_CALL_FAILED: "tool_call_failed",
  PROVIDER_ERROR: "provider_error",
  MAX_TURNS_REACHED: "max_turns_reached",
  BUDGET_EXHAUSTED: "budget_exhausted",
  MALFORMED_TOOL_CALL: "malformed_tool_call",
  CANCELLED: "cancelled",
} as const;

export type AgentLoopStopReason =
  (typeof AgentLoopStopReason)[keyof typeof AgentLoopStopReason];

export interface AgentLoopRun {
  messageId: string;
  requestId: string;
  attemptNumber: number;
  loopIndex: number;
  state: AgentLoopRunState;
  stopReason?: AgentLoopStopReason;

  provider?: string;
  model?: string;
  providerRuntimeState?: string;

  toolTurns: ToolCallTurn[];

  createdAt: string;
  updatedAt: string;
  startedAt?: string;
  completedAt?: string;
  cancelledAt?: string;
  errorPayload?: unknown;
}
```

### `ToolCallTurn`

```ts
export const ToolCallTurnState = {
  PLANNED: "planned",
  AWAITING_POLICY: "awaiting_policy",
  RUNNING: "running",
  COMPLETED: "completed",
  BLOCKED: "blocked",
  DENIED: "denied",
  FAILED: "failed",
} as const;

export type ToolCallTurnState =
  (typeof ToolCallTurnState)[keyof typeof ToolCallTurnState];

export interface ToolPolicySummary {
  decision: "allow" | "deny" | "require_confirmation";
  reasons: string[];
  mode: "enforce" | "warn" | "off";
}

export interface ToolBusRunLink {
  runId: string | null;
  eventsUrl: string | null;
}

export interface ToolCallTurn {
  toolTurnId: string;
  messageId: string;
  requestId: string;
  attemptNumber: number;
  loopIndex: number;

  toolId: string;
  commandId: string;
  providerToolCallId: string;
  providerFunctionName: string;

  rawArguments: Record<string, unknown>;
  normalizedArguments: Record<string, unknown>;
  policySummary: ToolPolicySummary;
  commandBusRun?: ToolBusRunLink;

  state: ToolCallTurnState;
  resultPayload?: unknown;
  errorPayload?: unknown;

  createdAt: string;
  updatedAt: string;
  approvedAt?: string;
  startedAt?: string;
  completedAt?: string;
  blockedAt?: string;
  failedAt?: string;
}
```

### Successful completed tool turn

```json
{
  "toolTurnId": "toolturn_01J9X2N7M5K0Y7Q1",
  "messageId": "msg_01J9X2N4WQ2P3B8A",
  "requestId": "req_01J9X2N5D1Z7Q9C2",
  "attemptNumber": 1,
  "loopIndex": 0,
  "toolId": "tool::search_docs",
  "commandId": "command::search_docs",
  "providerToolCallId": "call_7b82c9f4",
  "providerFunctionName": "search_docs",
  "rawArguments": {
    "query": "bounded tool loop contract"
  },
  "normalizedArguments": {
    "path_params": {},
    "query": {
      "query": "bounded tool loop contract"
    },
    "headers": {},
    "body": null
  },
  "policySummary": {
    "decision": "allow",
    "reasons": [
      "read_only",
      "idempotent"
    ],
    "mode": "enforce"
  },
  "commandBusRun": {
    "runId": "run_01J9X2N9V8H4E2F6",
    "eventsUrl": "/api/guardian/commands/runs/run_01J9X2N9V8H4E2F6/events?after_seq=0"
  },
  "state": "completed",
  "resultPayload": {
    "ok": true,
    "items": [
      {
        "title": "Agent Tool Loop Contract",
        "path": "docs/architecture/agent-tool-loop-contract.md"
      }
    ]
  },
  "errorPayload": null,
  "createdAt": "2026-04-17T12:00:00Z",
  "updatedAt": "2026-04-17T12:00:02Z",
  "approvedAt": "2026-04-17T12:00:00Z",
  "startedAt": "2026-04-17T12:00:01Z",
  "completedAt": "2026-04-17T12:00:02Z"
}
```

### Blocked or approval-required tool turn

```json
{
  "toolTurnId": "toolturn_01J9X2N7M5K0Y7Q2",
  "messageId": "msg_01J9X2N4WQ2P3B8A",
  "requestId": "req_01J9X2N5D1Z7Q9C2",
  "attemptNumber": 1,
  "loopIndex": 0,
  "toolId": "tool::edit_repo_files",
  "commandId": "command::edit_repo_files",
  "providerToolCallId": "call_7b82c9f5",
  "providerFunctionName": "edit_repo_files",
  "rawArguments": {
    "path": "src/app.tsx",
    "patch": "..."
  },
  "normalizedArguments": {
    "path_params": {},
    "query": {},
    "headers": {},
    "body": {
      "path": "src/app.tsx",
      "patch": "..."
    }
  },
  "policySummary": {
    "decision": "require_confirmation",
    "reasons": [
      "mutating",
      "requires_confirmation"
    ],
    "mode": "enforce"
  },
  "commandBusRun": {
    "runId": "run_01J9X2N9V8H4E2F7",
    "eventsUrl": "/api/guardian/commands/runs/run_01J9X2N9V8H4E2F7/events?after_seq=0"
  },
  "state": "blocked",
  "resultPayload": null,
  "errorPayload": {
    "code": "approval_required",
    "message": "User confirmation is required before mutating execution can continue."
  },
  "createdAt": "2026-04-17T12:05:00Z",
  "updatedAt": "2026-04-17T12:05:00Z",
  "blockedAt": "2026-04-17T12:05:00Z"
}
```

## State and Stop Vocabularies

### Tool-turn state

Use a small, explicit tool-turn state machine:

- `planned`: the model has selected a tool and the turn has been recorded, but policy and execution are not finished.
- `awaiting_policy`: the turn is waiting on policy evaluation or human approval.
- `running`: the command bus has accepted the execution and the tool is in flight.
- `completed`: the tool finished successfully and produced a result payload.
- `blocked`: execution stopped before or during command-bus execution because policy or capability prevented it.
- `denied`: the user or policy explicitly refused execution.
- `failed`: the tool or command-bus execution ended in error.

### Loop stop reason

Use a separate stop-reason vocabulary for the overall bounded loop:

- `model_final_answer`
- `tool_call_blocked`
- `tool_call_denied`
- `tool_call_failed`
- `provider_error`
- `max_turns_reached`
- `budget_exhausted`
- `malformed_tool_call`
- `cancelled`

The state and the stop reason are not the same thing. State describes the current or terminal step. Stop reason describes why the overall loop ended.

## Transcript Mapping

One tool turn maps back into the provider transcript in a bounded, identity-preserving way:

1. The assistant tool-call message is appended with role `assistant`, a stable `messageId`, and provider-facing tool-call metadata.
2. The tool-result message is appended with role `tool`, the matching `providerToolCallId`, and the terminal turn payload.
3. The next provider call sees the original conversation history plus the assistant tool-call message plus the tool-result message(s).
4. Reconstruction must preserve message identity versus attempt identity boundaries:
   - `messageId` stays stable for the authored assistant turn.
   - `requestId` changes when the same authored turn is replayed.
   - `toolTurnId` changes for each tool invocation even when the parent message is the same.

Canonical assistant tool-call message shape:

```json
{
  "id": "msg_01J9X2N4WQ2P3B8A",
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_7b82c9f4",
      "type": "function",
      "function": {
        "name": "search_docs",
        "arguments": "{\"query\":\"bounded tool loop contract\"}"
      }
    }
  ]
}
```

Canonical tool-result message shape:

```json
{
  "role": "tool",
  "tool_call_id": "call_7b82c9f4",
  "content": "{\"ok\":true,\"items\":[{\"title\":\"Agent Tool Loop Contract\"}]}"
}
```

For blocked or denied turns, the tool-result message still preserves the tool-call identity and carries the terminal error payload instead of pretending the tool executed successfully.

## Execution-Lane Mapping

The canonical relationship for future bounded orchestration is:

1. Provider tool decision.
2. Tool registry / `ToolSpec` lookup.
3. Raw arguments captured from the provider tool call.
4. Normalized arguments produced from `ToolSpec.to_internal_invoke_args()`.
5. Policy evaluation and approval decision.
6. Command-bus invocation and run creation.
7. Command-bus run events.
8. Turn state update and transcript append.

The tool registry here is the derived, runtime `ToolSpec` map, not a separate ad hoc execution system.

Future execution should anchor on the command bus as the durable execution substrate and should not re-found execution semantics on `/tools` compatibility behavior.

## Approval and Blocked Semantics

Use these canonical meanings:

- `allow`: the tool is permitted to execute. This does not mean the tool has already executed.
- `deny`: execution is refused. The turn is terminal and must not be treated as completed.
- `require_confirmation`: the tool is conditionally permitted, but the run must wait for explicit approval before mutating or otherwise sensitive execution continues.
- `blocked`: execution was prevented by policy, approval, or capability gates.
- `failed`: execution started but ended in error.
- `completed`: execution finished and produced a result payload.

The crucial rule is simple: tool chosen is not equivalent to tool executed.

## Invariants

- Message identity and request identity must remain separate.
- Tool-turn identity must be subordinate to a single assistant attempt.
- Route acceptance is not proof of loop completion.
- Command-bus execution truth must remain separate from transcript truth.
- `/tools` compatibility behavior must not become the canonical execution contract.
- This document must not imply that current `main` already emits these loop objects.
- Repeated loop states and stop reasons are canonical token domains, not ad hoc literals.

## Non-Goals

- No live implementation of ReAct loops.
- No provider request-format changes in this task.
- No command-bus execution changes in this task.
- No UI implementation in this task.
- No claim that the current supported beta already includes autonomous coding-agent execution.

## Naming Discipline

- Use `AgentLoopRun` and `ToolCallTurn` for the durable entities.
- Use the same bounded vocabulary everywhere for states, stop reasons, and policy decisions.
- Do not introduce synonyms such as "agent turn," "tool step," or "tool event" for the same canonical concept unless they are clearly subordinate aliases in explanatory prose.
- Prefer the existing runtime-contract and token-philosophy style for future extensions.
