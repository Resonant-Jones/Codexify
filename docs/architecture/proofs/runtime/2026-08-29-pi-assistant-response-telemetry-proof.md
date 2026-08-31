# 2026-08-29 — Bounded Pi 0.82.1 Assistant-Response Telemetry Proof

## Status

PASS / canonical (instrumentation-only; non-inference)

## Causal boundary

`UNRESOLVED_ASSISTANT_TOOL_CALL_EMISSION_BOUNDARY`

## Gate

CE-L1

## Campaign

`CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE`

## Scope

This proof records the bounded, content-free assistant-response
telemetry instrumentation added between R2 and R3 of the CE-L1 live
qualification.  It does NOT record a CE-L1 live attempt, does NOT
execute any provider-backed prompt, and does NOT inspect operator
credentials.

## Why R2 required this instrumentation

The R2 CE-L1 live Executor attempt (recorded in
`2026-08-26-campaign-engine-ce-l1-live-executor-proof.md`) observed:

- `effective_tool_names = ["read", "bash", "edit", "write"]`
- `write_tool_available = true`
- `assistant_tool_call_count = 0`
- `tool_execution_start_count = 0`
- `tool_execution_end_count = 0`
- `executed_tool_names = []`
- `diagnostic_stage = post_invocation`
- `failure_reason = zero_mutation_executor_turn`

This proved the historical Pi 0.82.1 tool-activation defect
(`PI_0821_TOOL_OPTIONS_TYPE_MISMATCH_PROVEN`; landed as `TOOL_ACTIVATION_REPAIR
= PASS_CANONICAL` in PR #774) is **no longer** the active CE-L1
blocker.

It did NOT prove which of the following boundaries is the active
blocker:

- the model;
- OpenAI Codex Responses translation;
- Pi-AI provider translation;
- tool schema serialization;
- assistant-event normalization;
- final-message normalization;
- refusal handling.

The existing six-field tool telemetry observed only:

1. Which tools were advertised (`effective_tool_names`).
2. Whether the assistant emitted a final normalized `toolCall`
   content block (`assistant_tool_call_count`).

It did NOT observe:

- The assistant message-update event vocabulary (streaming).
- The final assistant content-block kinds beyond `toolCall`.
- Whether tool-call lifecycle events were observed but disappeared
  from the final normalized messages.

Therefore the smallest next prerequisite was observational
instrumentation that adds bounded, content-free assistant-response
telemetry covering those gaps without altering execution semantics.

## R2 observed evidence (verbatim from R2 proof entry)

| Field | Value |
| --- | --- |
| `effective_tool_names` | `["read", "bash", "edit", "write"]` |
| `write_tool_available` | `true` |
| `assistant_tool_call_count` | `0` |
| `tool_execution_start_count` | `0` |
| `tool_execution_end_count` | `0` |
| `executed_tool_names` | `[]` |
| `diagnostic_stage` | `post_invocation` |
| `failure_reason` | `zero_mutation_executor_turn` |

## Instrumentation contract (added by this task)

Four bounded assistant-response telemetry fields are added under the
existing `tool_telemetry` envelope.  The fields are observational
only; they confer no execution authority and do not affect CE-L1
acceptance.

### Field semantics

| Field | Type | Source | Records | Does NOT record |
| --- | --- | --- | --- | --- |
| `assistant_message_count` | `int >= 0` | `session.agent.state.messages` | count of assistant-role messages | text, tokens |
| `assistant_content_block_types` | `tuple[str, ...]` | `session.agent.state.messages[i].content[].type` | ordered unique block-type names (`text`, `thinking`, `toolCall`) | text, reasoning, args, IDs, payloads |
| `assistant_message_event_types` | `tuple[str, ...]` | `event.assistantMessageEvent.type` on `message_update` events | ordered unique event-type names | deltas, text, thinking content, tool-call IDs, tool arguments, partial JSON, provider payload fragments |
| `assistant_tool_call_event_count` | `int >= 0` | count of `message_update` events with `toolcall_*` event type | integer count | anything else |

### Type-list invariants

- First-observation order is preserved.
- Type names are deduplicated.
- Empty/non-string values are filtered.
- Empty tuples are returned when none are observed.
- No sorting is applied.

### Failure classification

A successful live authorized task with missing, wrong-type, negative,
or structurally malformed assistant-response telemetry fails closed
as `wrapper_protocol_failed` at stage `wrapper_protocol`.  No new
failure token is created.

### Readiness exemption

Preflight readiness does NOT require the four new fields.
`preflight_authorized` is non-inference and creates no model session
or prompt.  Only `execute_authorized` (which runs `session.prompt`)
requires valid assistant-response telemetry alongside valid existing
tool telemetry.

### Adapter parser behavior

`_parse_tool_telemetry` in
`guardian/agents/adapters/pi_codex_runner.py` parses and validates:

- `assistant_message_count` must be `int >= 0` or `None`.
- `assistant_tool_call_event_count` must be `int >= 0` or `None`.
- `assistant_content_block_types` must be a `list` (or `tuple`) whose
  members are all non-empty strings; the parser does NOT silently
  filter non-string members; if any member is non-string, the field
  surfaces as `None` and the wrapper fails closed as
  `wrapper_protocol_failed`.
- `assistant_message_event_types` must be a `list` (or `tuple`) whose
  members are all non-empty strings; same fail-closed posture.

This fail-closed posture matches the spec requirement §9.

### Propagation path

```
wrapper tool_telemetry (10 fields)
  -> PiCodexRunnerAdapter._parse_result(require_tool_telemetry=True)
  -> PiHarnessRuntimeEvidence
  -> _run_with_pi_adapter (copy directly, no recompute)
  -> PiLiveInvocationOutcome
  -> PiInvocationReceipt.validation_metadata["tool_telemetry"]
  -> PiHarnessResult.validation_metadata["tool_telemetry"]
  -> LiveExecutorRunResult + to_dict()
  -> CampaignLiveExecutorError + to_payload()["tool_telemetry"]
```

The `tool_telemetry` envelope name is preserved.  No new evidence
store is introduced.

## Deterministic fixture cases

The instrumentation is verified by four deterministic cases that do
NOT exercise Pi SDK code, do NOT call any provider, do NOT inspect
credentials, and do NOT retain prompt or response content.

### Case 1 — Text-only assistant (synthetic)

Synthetic `message_update` events:

```
{"type": "message_update", "assistantMessageEvent": {"type": "start"}}
{"type": "message_update", "assistantMessageEvent": {"type": "text_start"}}
{"type": "message_update", "assistantMessageEvent": {"type": "text_delta"}}
{"type": "message_update", "assistantMessageEvent": {"type": "text_end"}}
{"type": "message_update", "assistantMessageEvent": {"type": "done"}}
```

Final session messages:

```
[{"role": "assistant", "content": [{"type": "text"}]}]
```

Expected output (after helper extraction):

```
{
  "assistant_message_count": 1,
  "assistant_content_block_types": ["text"],
  "assistant_message_event_types": ["start", "text_start", "text_delta", "text_end", "done"],
  "assistant_tool_call_event_count": 0,
}
```

### Case 2 — Tool-call lifecycle (synthetic)

Synthetic `message_update` events (text-only preamble, then
`toolcall_*` lifecycle, then `done`):

```
{"type": "message_update", "assistantMessageEvent": {"type": "text_start"}}
{"type": "message_update", "assistantMessageEvent": {"type": "text_delta"}}
{"type": "message_update", "assistantMessageEvent": {"type": "text_end"}}
{"type": "message_update", "assistantMessageEvent": {"type": "toolcall_start"}}
{"type": "message_update", "assistantMessageEvent": {"type": "toolcall_delta"}}
{"type": "message_update", "assistantMessageEvent": {"type": "toolcall_end"}}
{"type": "message_update", "assistantMessageEvent": {"type": "done"}}
```

Final session messages:

```
[{"role": "assistant", "content": [{"type": "text"}, {"type": "toolCall", "id": "x", "name": "write", "arguments": {"path": "x", "content": "y"}}]}]
```

Expected output (after helper extraction):

```
{
  "assistant_message_count": 1,
  "assistant_content_block_types": ["text", "toolCall"],
  "assistant_message_event_types": ["text_start", "text_delta", "text_end", "toolcall_start", "toolcall_delta", "toolcall_end", "done"],
  "assistant_tool_call_event_count": 1,
}
```

Note: tool arguments, IDs, names are NOT retained in the serialized
output.  The fixture only verifies the *types* are counted.

### Case 3 — Tool-call execution (synthetic)

Synthetic `message_update` events followed by `tool_execution_start`
and `tool_execution_end`:

```
<message_update events from Case 2>
{"type": "tool_execution_start", "toolName": "write"}
{"type": "tool_execution_end", "toolName": "write"}
```

Expected output (after helper extraction; existing six fields
unchanged):

```
{
  "effective_tool_names": ["read", "bash", "edit", "write"],
  "write_tool_available": True,
  "tool_execution_start_count": 1,
  "tool_execution_end_count": 1,
  "executed_tool_names": ["write"],
  "assistant_tool_call_count": 1,
  "assistant_message_count": 1,
  "assistant_content_block_types": ["text", "toolCall"],
  "assistant_message_event_types": [..., "toolcall_start", ...],
  "assistant_tool_call_event_count": 1,
}
```

### Case 4 — Empty/no-tool (synthetic)

No `message_update` events and no assistant messages.

Expected output:

```
{
  "assistant_message_count": 0,
  "assistant_content_block_types": [],
  "assistant_message_event_types": [],
  "assistant_tool_call_event_count": 0,
}
```

## Verification

- `codex_runner/src/assistant-telemetry.js` exposes two pure helper
  functions: `observeAssistantMessageEvent(toolTelemetry, event)` and
  `observeFinalAssistantMessages(toolTelemetry, session)`.
- `tests/ops/test_pi_assistant_response_telemetry.py` runs the four
  deterministic cases against the helpers via Node subprocess and
  asserts:
  - All four cases produce the expected field values.
  - The serialized JSON output contains no occurrence of
    `"content":`, `"text":`, `"args":`, `"id":`, `"path":`,
    `"tool_call_id"`, `"result":`, `"name":`, `"key":`, or
    `"ignored-arg"`.
  - Zero provider calls (`provider_request_count = 0`).
  - Zero prompt calls (`prompt_count = 0`).
  - Zero operator credential access
    (`operator_credential_access_count = 0`).

## Malformed-telemetry tests

The adapter parser fails closed on the following malformed inputs:

- missing `assistant_message_count`;
- negative `assistant_message_count`;
- negative `assistant_tool_call_event_count`;
- non-string member in `assistant_content_block_types`;
- non-string member in `assistant_message_event_types`;
- non-list `assistant_content_block_types`.

Each case asserts `failure_classification == "wrapper_protocol_failed"`
at `failure_stage == "wrapper_protocol"`.  Readiness remains valid
without the four new fields.

## Pi 0.82.1 assistant event vocabulary (derived from vendored sources)

The vendored Pi 0.82.1
`@earendil-works/pi-ai/dist/types.d.ts` exposes
`AssistantMessageEvent` as a discriminated union whose `type` field
takes one of:

- `start`
- `text_start`
- `text_delta`
- `text_end`
- `thinking_start`
- `thinking_delta`
- `thinking_end`
- `toolcall_start`
- `toolcall_delta`
- `toolcall_end`
- `done`
- `error`

The wrapper observes exactly the `type` field; it does NOT read
`delta`, `text`, `thinking`, `toolCall`, `partialJson`, or any other
content-bearing field.

The `MessageContent` union (final assistant content blocks) exposes
`type` taking one of:

- `text`
- `thinking`
- `toolCall`

The wrapper observes exactly the `type` field; it does NOT read
`text`, `thinking`, `id`, `name`, `arguments`, or any other
content-bearing field.

`StopReason` is exposed as an enum
(`stop`, `length`, `toolUse`, `error`, `aborted`).  No new field is
added for `StopReason` in this task because:

- It is not strictly necessary for the bounded observational
  outcome (the existing `failure_classification` already covers
  protocol-level failures).
- Its values are not yet observed at the wrapper level via the
  maintained Pi 0.82.1 `message_update` event vocabulary.
- The spec §4 defers adding any such field until source inspection
  proves it is required for the same observational outcome.

`StopReason` is reported here for documentation only; its potential
inclusion is a future-task decision.

## What was NOT changed

- `codex_runner/vendor/pi-coding-agent/**` — no vendor modification.
- `guardian/pi/tokens.py` — no failure token changes.
- Campaign JSON schemas — no schema changes.
- Provider catalog/registry — no change.
- Model routing — no change.
- Package manifests — no change.
- Lockfiles — no change.
- Executor prompt — no change.
- ADRs — no change.
- `docs/architecture/00-current-state.md` — no change.
- Existing CE-L1 proof ledger — no change.
- Operator credential storage — not inspected or modified.

## No provider calls

This task did NOT execute any provider-backed prompt.  Zero provider
calls were authorized or performed.  No OAuth readiness check was
performed.  No operator credential store access was performed.

## Invariants check

- Guardian remains authorization authority. **PASS.**
- Pi remains invocation substrate. **PASS.**
- Campaign Engine remains gate/evidence authority. **PASS.**
- Telemetry is observational only. **PASS.**
- No assistant content is persisted through this telemetry. **PASS.**
- No credential material is inspected or persisted. **PASS.**
- Tool names remain bounded to the existing session truth surface.
  **PASS.**
- Target readback remains mutation authority. **PASS.**
- No retry, no fallback, no rebinding. **PASS.**
- Provider/model remain exact. **PASS.**
- Historical CE-L1 evidence remains immutable. **PASS.**
- No live attempt is spent during instrumentation. **PASS.**
- Release claims remain unchanged. **PASS.**

## Conformance to Task Spec

| Spec section | Result |
| --- | --- |
| §1 Start from current remote main | PASS (c7d6c5e95) |
| §2 Preserve existing six telemetry fields | PASS |
| §3 Add four bounded assistant-response fields | PASS |
| §4 No speculative refusal_reason capture | PASS |
| §5 No raw tool-schema echo | PASS |
| §6 Capture at maintained wrapper boundary | PASS (`session.subscribe` + `session.agent.state.messages`) |
| §7 Preserve event-order semantics safely | PASS |
| §8 Extend AgentRunEnvelope | PASS |
| §9 Parser fail-closed on malformed | PASS |
| §10 Propagate through Guardian evidence | PASS |
| §11 Propagate into receipt/result metadata | PASS (`validation_metadata["tool_telemetry"]`) |
| §12 Propagate through Campaign live result/error | PASS |
| §13 Preserve zero-mutation semantics | PASS |
| §14 Preserve provider/model/tool behavior | PASS (`["read","bash","edit","write"]` unchanged) |
| §15 Deterministic wrapper regression coverage | PASS |
| §16 Malformed-telemetry adapter tests | PASS |
| §17 Guardian propagation tests | PASS |
| §18 Campaign propagation tests | PASS |
| §19 Causal language discipline | PASS |
| §20 Documentation update | PASS |
| §21 No live CE-L1 attempt | PASS (provider call count = 0) |

## Acceptance result

PASS — bounded Pi 0.82.1 assistant-response telemetry instrumentation
qualifies for landing on remote main.  This proof records only
instrumentation correctness; it does NOT prove any cause for the R2
`assistant_tool_call_count=0` observation.
