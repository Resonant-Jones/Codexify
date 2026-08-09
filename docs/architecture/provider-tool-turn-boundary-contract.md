Purpose: Define the canonical provider-neutral architecture boundary that separates semantic model/tool intent from provider-specific wire representation, so DeepSeek, OpenAI Chat Completions, OpenAI Responses, Whoosh'd/local providers, and future providers can all participate in the same Codexify tool-turn contract without driving different Guardian agent runtimes or tool executors.
Last updated: 2026-08-09
Source anchors:
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/provider-capability-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/canonical-token-philosophy.md
- docs/architecture/flows.md
- guardian/core/chat_completion_service.py
- guardian/core/ai_router.py
- guardian/providers/deepseek_adapter.py
- guardian/command_bus/invoke.py
- guardian/tools/spec.py
- guardian/tools/derive.py
- guardian/tasks/types.py
- Stage 0 commit f7a11746da86ae7bdd67c9aafbd60d885fb4e324
- Stage 1 commit ea87dc0e8c6832de49aa663e53ff9c34ac8d5dca

## Scope

This note is the canonical architecture contract for the seam between provider transport and Codexify's semantic model/tool-turn boundary.

It governs:

- what the model may semantically output;
- what Codexify must normalize that output into;
- where Guardian grants authority;
- where Codexify executes the authorized action;
- what the provider adapter must and must not do on the way back into the provider.

It does not implement transport. It does not select any provider. It does not authorize any specific capability. It does not change the existing one-tool-turn runtime contract. It does not change Command Bus authority.

## Governing Principle

Models propose actions.
Guardian grants authority.
Codexify executes actions.
Provider adapters translate model conversation and continuation state.

No provider wire format is canonical Codexify agent semantics.

## 1. Purpose and Scope

This contract defines the provider/tool boundary as the canonical seam between:

```
Provider API
-> Provider Adapter
-> Canonical Codexify model/tool semantics
-> Guardian authorization
-> Command Bus execution
-> Canonical tool result
-> Provider Adapter
-> Provider continuation request
```

It governs semantic boundaries and adapter responsibilities. It does not implement transport.

The contract is intentionally low-fidelity on Python shapes; it documents the semantic seam. Type-level wiring is a follow-up concern, not a precondition for this contract.

## 2. Canonical Separation of Concerns

Codexify must normatively distinguish the four concerns below. They may not collapse into one provider-specific abstraction.

A. Semantic model action
The model proposes one of two semantic outcomes:
- assistant text, or
- one bounded tool decision.

A bounded tool decision is exactly one proposed Codexify command invocation, not a free-form execution plan.

B. Guardian authority
Guardian determines whether the proposed command is actually advertised and authorized for that exact invocation. The Stage 1 advertised-subset gate is the canonical pre-execution authority seam for the current bounded tool turn.

C. Codexify execution
The Command Bus, or another separately governed execution substrate, performs the approved action. The execution substrate must not redefine the model/tool semantics and must not inspect provider-private state.

D. Provider continuation representation
The provider adapter converts the canonical result into whatever continuation representation its provider requires. This is a translation concern, not a Codexify semantic concern.

The four concerns are deliberately not the same as any one provider's wire shape. Any provider whose canonical wire shape can be expressed as these four concerns may participate in the canonical tool-turn contract.

## 3. Canonical Model-Turn Concept

The contract canonically defines a provider-neutral conceptual `ModelTurn`.

A `ModelTurn` semantically carries:

- optional assistant text;
- zero or one normalized tool decision under the current bounded runtime;
- a completion / finish interpretation when needed by the runtime;
- an adapter-owned continuation-state reference when the provider requires it.

The contract does not require an exact Python implementation in this task. The semantic carrier is the contract; the wire-level shape is the adapter's job.

This contract explicitly preserves the current one-tool-turn limitation:

- The bounded runtime permits at most one model-selected tool turn per `MessageTurn` (an authored user turn plus its assistant turn).
- Parallel or recursive tool calls are not implied by this contract.
- If a provider returns multiple tool calls while the runtime only supports one, they must not all execute. The adapter/runtime must preserve the existing bounded failure/limit doctrine. The exact implementation of "preserve" is deferred; the doctrine is not.

This contract does not change `agent-tool-loop-contract.md`'s one-tool-turn runtime contract. It does not introduce a recursive planner, a parallel tool step, or a multi-turn tool loop.

## 4. Identity Rules

The contract distinguishes canonical Codexify identities from provider-private identifiers and from runtime-loop identifiers.

### 4.1 Canonical command identity

`canonicalCommandId` (in code: `command_id`) identifies the Codexify capability the model is invoking. It is the canonical authority token and matches the canonical command bus manifest entry.

The canonical command identity is:

- provider-neutral;
- declared by Codexify, not by the model;
- the only field that the Guardian authority gate is allowed to compare against the advertised/authorized set.

### 4.2 Tool-call correlation identity

`toolCallCorrelationId` (in code: `tool_call_id`) identifies this particular model-requested invocation of a canonical capability. It correlates:

- the model-side tool call to the Codexify execution result, and
- the Codexify execution result back to the provider-side continuation message.

Identity rules:

- provider-native tool-call identifiers may supply or map to the correlation identity;
- tool-call correlation identity is not canonical command identity;
- tool-call correlation identity is not `requestId`;
- tool-call correlation identity is not `task_id`;
- tool-call correlation identity is not `toolTurnId`.

### 4.3 Bounded runtime tool-turn identity

`toolTurnId` remains the Codexify bounded runtime tool-turn identity. It is the canonical observability marker for the one bounded tool turn on the runtime side, separate from provider wire identifiers.

### 4.4 Other distinct identities

- `requestId` is the completion attempt / execution attempt identity.
- `task_id` is the queued execution identity.
- `messageId` is the authored turn identity.
- `commandRunId` is the canonical command-bus run identity.

This contract does not create a new durable persistence requirement for `toolCallCorrelationId`. It only states that the correlation identity exists and is distinct from the other identities already enumerated in `agent-tool-loop-contract.md` and `chat-runtime-contract.md`.

## 5. Normalized Tool-Call Concept

A provider-neutral tool decision semantically carries, at minimum:

- tool-call correlation identity (see §4.2);
- canonical Codexify command identity (see §4.1);
- structured command arguments;
- optional non-authoritative rationale, when the current normalized behavior already carries it.

The structured arguments are the command-bus-compatible invocation payload. They are not free-form prose and they are not provider-specific syntax.

The normalized tool decision is the only shape that the Guardian authority gate is allowed to inspect. The authority gate must not branch on provider-private identifiers, provider-private payloads, or unparsed provider text.

## 6. Normalized Tool-Result Concept

A provider-neutral tool result semantically carries:

- tool-call correlation identity (so the continuation can be paired to the right tool call);
- canonical command identity, where useful for continuation shaping;
- a structured result or a bounded error representation.

The provider-neutral tool result must not contain provider-specific continuation syntax. It must not be conflated with the durable assistant-message transcript, with retrieval evidence, with memory emissions, or with arbitrary user-visible artifacts.

This contract does not redesign the Command Bus result contracts. It states only the seam through which a Codexify execution result must exit toward the provider adapter.

## 7. Provider Continuation State

Provider Continuation State is an explicit architectural category.

Definition. Provider Continuation State is:

- provider-owned;
- opaque to the generic tool executor;
- adapter-managed;
- request/attempt-scoped unless another contract explicitly requires broader persistence;
- separate from user-visible assistant text;
- separate from Codexify memory;
- separate from retrieval context;
- separate from canonical command authority.

Prohibitions. Generic Guardian/tool components must not branch on provider-private fields. Concretely:

- The Guardian authority gate must not read or branch on provider-private continuation state.
- The Command Bus execution path must not read or branch on provider-private continuation state.
- The generic tool executor must not inspect a provider's reasoning payload, its response identifiers, or any other vendor-private field beyond the canonical normalized tool-decision shape.

Examples. Non-normative examples of provider-continuation state include:

- DeepSeek reasoning continuation data such as `reasoning_content`;
- OpenAI Responses continuation identifiers or typed output items beyond the canonical tool-decision shape;
- future local-runtime state required to continue inference.

These examples are provider-specific and non-canonical. The contract does not claim their current implementation status beyond what repository inspection proves. They are listed only to make the category concrete.

## 8. Adapter Responsibilities

The provider adapter is responsible for both directions of translation.

### 8.1 Outbound toward the provider

The adapter must:

- translate canonical advertised `ToolSpec`s / capabilities into whatever tool representation the provider/model supports;
- preserve provider-specific formatting requirements (for example, OpenAI-style function blocks, OpenAI Responses typed tool items, or strict structured-output envelopes);
- attach or restore any required provider continuation state when the provider requires it.

### 8.2 Inbound from the provider

The adapter must:

- translate provider output into the canonical `ModelTurn` / tool-decision representation;
- validate provider response shape before normalization, and surface malformed output as a transport/normalization failure rather than as a Command Bus request;
- preserve any required opaque continuation state, separately, for the next outbound request;
- never execute commands itself.

### 8.3 Continuation after execution

The adapter must:

- translate the normalized tool result into the provider-specific continuation syntax;
- restore any required provider continuation state;
- request the final provider continuation.

The adapter must never become the authority gate or the tool executor. It must never grant command authority. It must never read Codexify memory or retrieval context on its own.

## 9. Authority Boundary

This contract normatively incorporates the Stage 1 invariant:

A normalized tool decision may execute only when:

- the request has a nonempty advertised/authorized tool set; and
- the normalized canonical `command_id` belongs to that exact set.

This invariant is currently enforced at `guardian/core/chat_completion_service.py::_authorized_tool_command_ids` and `_execute_bounded_tool_turn_completion` (the Stage 1 advertised-subset gate, commit `ea87dc0e8c6832de49aa663e53ff9c34ac8d5dca`).

This contract states the same invariant in architecture terms:

- Provider-native calls and structured/non-native calls receive no bypass.
- Provider compatibility must never mean provider text equals authority.
- Three identities are non-negotiable:
  - Model output = proposal.
  - Guardian authorization = authority.
  - Command execution = side effect.

Empty advertised capability set means zero model-callable command authority. The Stage 1 gate is the canonical expression of this invariant today. This contract does not recreate that gate; it documents the invariant above it.

## 10. Provider Capability Relationship

This contract is cross-cutting with `provider-capability-contract.md` and not subordinate to it.

Provider capability records may describe how a provider/model can satisfy this contract through declarative categories such as:

- native tool transport;
- strict structured transport;
- unavailable tool transport;
- native continuation/replay behavior;
- structured-output capability.

However:

- those capability classifications do not redefine `ModelTurn`;
- they do not redefine `ToolCall`;
- they do not redefine `ToolResult`;
- they do not grant command authority;
- they do not become provider-specific branches in Guardian core semantics.

The Provider Capability Contract remains a planning surface for capability discovery and routing, not a competing agent protocol. Current capability records describe what a provider can transport; they do not define what a tool turn is.

This contract does not add runtime capability tokens in this task. If existing Provider Capability vocabulary (`declared_capabilities`, `verified_capabilities`, `effective_capabilities`, `tool_calling`, `structured_output`) is sufficient, it is reused. If it is not, expansion is a future token-domain decision under `runtime-protocol-token-contract.md` and `canonical-token-philosophy.md`.

## 11. Native vs Structured Transport

The contract must allow both native and non-native transports without declaring them semantically different agent systems.

### 11.1 Native transport

Native transport uses provider-native functions or tool calls. The wire format belongs to the provider. The semantic shape is the canonical `ModelTurn` / tool-decision.

### 11.2 Structured transport

Strict structured transport may only qualify as a satisfying implementation if it can reliably:

- receive the authorized tool definitions (or a schema-validated equivalent);
- return a schema-valid bounded tool decision;
- preserve required correlation data;
- pass through the same Guardian advertised-subset authority gate.

### 11.3 Disallowed ambiguity

The contract explicitly does not treat loosely prompted free-form JSON as equivalent to structured transport merely because it can be parsed. A real structured transport must be envelope-validated, not text-mined.

This contract does not implement a structured transport in this task. It states the classification rule for future structured-transport adapters.

## 12. Transcript and Persistence Boundary

Provider continuation state is not automatically:

- user-visible transcript content;
- assistant reasoning text;
- durable memory;
- Personal Facts;
- retrieval evidence;
- an exported user artifact.

The durable transcript remains governed by existing Chat Runtime and Agent Tool Loop contracts. The bounded tool-turn slice continues to record observability fields (`messageId`, `requestId`, `toolTurnId`, `toolTurnState`, `loopStopReason`, `commandRunId`) inside the assistant-message `extra_meta` payload, not as a separate provider-state record.

This contract does not introduce a new persistence or export contract in this task.

If future crash recovery requires durable provider continuation state, that decision must be a separate architecture-impact slice. Mixing durable continuation state into the user-visible transcript or into Codexify memory is forbidden by this contract.

## 13. Error-Boundary Doctrine

The contract distinguishes, at the architectural seam, the following failure categories:

- provider transport/normalization failure — the adapter cannot translate provider output into the canonical shape;
- invalid tool decision — the canonical shape is malformed (missing required field, schema violation, etc.);
- Guardian command authorization block — the canonical shape is valid but the canonical `command_id` is not in the advertised set;
- command execution failure — the Command Bus invoked the approved action and the action failed;
- continuation failure — the adapter cannot translate the canonical result back into the provider's continuation syntax.

Existing canonical runtime/tool-loop failure vocabulary already covers most of these categories (`tool_decision_invalid`, `tool_command_blocked`, `tool_command_failed`, `tool_turn_limit_reached`, `tool_turn_completed`). Reuse those tokens where they apply.

The contract does not invent new protocol tokens in this task. If a future transport failure class cannot be cleanly expressed with current tokens, that is a deferred token-domain question under `runtime-protocol-token-contract.md` and `canonical-token-philosophy.md`, not a reason to invent terminology locally.

## 14. Provider Examples (Non-Normative)

These are conceptual mappings, not implementation claims. They illustrate how different provider styles can fit the same semantic contract. They do not claim current runtime implementation.

### 14.1 DeepSeek / OpenAI Chat-Completions-shaped native flow

```
provider tools
-> native tool call
-> normalized ModelTurn / tool decision
-> Guardian authority gate
-> Codexify command-bus execution
-> normalized tool result
-> provider-native tool result message
-> continuation
```

### 14.2 OpenAI Responses-style conceptual flow

```
typed provider output item
-> normalized ModelTurn / tool decision
-> Guardian authority gate
-> Codexify command-bus execution
-> normalized tool result
-> provider-specific function_call_output / continuation representation
-> continuation
```

### 14.3 Local / Whoosh'd / provider-specific flow

```
provider-supported native or strict structured transport
-> same normalized ModelTurn / tool decision
-> same Guardian authority gate
-> same execution semantics
```

These examples show that the same four Codexify concerns (model action, authority, execution, continuation) are present for every provider style. They differ only in the adapter's translation work.

## 15. Explicit Invariants

This contract asserts the following invariants. Any provider transport, agent runtime, or tool executor that violates these is out of contract.

- Provider wire formats are not canonical Codexify agent semantics.
- Provider adapters translate; they do not grant execution authority.
- Models propose actions; Codexify executes them.
- Canonical command identity remains provider-neutral.
- Provider-private continuation state remains opaque outside the adapter boundary.
- The generic tool executor must not inspect provider-private reasoning or continuation fields.
- A model-selected command must pass the advertised-subset gate before execution.
- Empty advertised capability set means zero model-callable command authority.
- Provider-native and structured tool decisions obey the same authorization rule.
- User-visible transcript semantics do not depend on a provider's private wire representation.
- Current runtime remains bounded to at most one tool turn.
- No provider transport mechanism widens the supported beta promise without separate runtime proof.

## 16. Non-Goals

This contract explicitly does not:

- implement DeepSeek changes;
- implement OpenAI Responses;
- implement OpenAI Chat Completions changes;
- implement Whoosh'd/local tools;
- change `guardian/core/ai_router.py`;
- change `guardian/core/chat_completion_service.py`;
- change DeepSeek adapter code;
- expose any actual tool to ordinary chat;
- introduce a new `ToolSpec` registry;
- implement effective capability exposure;
- add new canonical runtime tokens;
- allow multi-tool recursion;
- allow parallel tool calls;
- allow arbitrary prompt-emulated tool execution;
- provide terminal or filesystem access;
- wire up Coding Loop delegation;
- change Intent Spine semantics;
- introduce provider-state persistence;
- qualify a release.

It is a docs/architecture contract only. It defines the seam. It does not move the seam.

## 17. Deferred Implementation Questions

These are deliberate documentation-only deferrals. They are not omissions. They are listed so future work does not silently assume them.

- Exact Python shape for `ModelTurn`, `ToolCall`, `ToolResult` (subject to a future code-inspection task).
- Cross-provider replay of provider continuation state across connection or worker boundaries.
- Structured-transport adapter classification rules for non-OpenAI, non-DeepSeek providers.
- New canonical protocol tokens for transport-only failure modes, if and when they become necessary.
- Any durable persistence of provider continuation state for crash recovery.

These questions must each be addressed by a separate architecture-impact slice with its own pre-read and ADR-conflict check. They are not addressed by this contract.


## 18. Implementation Status (Stage 2B)

This contract was first implemented against the DeepSeek provider transport.
The implementation status is:

- **DeepSeek native tool transport is now test-proven against the canonical
  semantic boundary.** The DeepSeek adapter owns the wire translation in both
  directions through build_continuation_messages and the existing
  build_payload / parse_response / normalize_tool_calls /
  build_tool_definitions helpers. The generic Guardian runtime
  (chat_completion_service.py) calls the adapter through the
  provider-neutral NormalizedCompletionOutput dataclass and does not
  inspect DeepSeek-private fields.
- **The Stage 1 advertised-subset gate remains Guardian authority.** No
  authority check is duplicated in the adapter. Provider-native and
  structured non-native calls reach the same gate through the same path.
- **DeepSeek-specific continuation state is adapter-owned and
  request-scoped.** The adapter preserves reasoning_content inside the
  raw assistant message envelope opaquely. Generic Guardian and Command Bus
  code does not branch on reasoning_content. The continuation request
  replays the full assistant message so the provider can continue inference
  (per the DeepSeek Thinking Mode guide).
- **No ordinary chat capability exposure was added.** Production chat
  producers still leave task.tools unset. The Stage 2B implementation
  only proves the DeepSeek transport seam against the contract under
  synthesized test fixtures.
- **Other providers remain unimplemented and unqualified under this
  contract.** OpenAI Chat Completions, OpenAI Responses, Groq, whooshd, and
  local runtimes are not in scope for Stage 2B and have no claim of
  conformance to this contract.
- **No release-support claim follows from this code-path / test proof.**
  This is a code-path and test-proven adapter against the contract only.
  Live DeepSeek execution, deepseek-v4-flash / deepseek-v4-pro runtime
  behavior, and reasoning-mode continuation remain to be proven by a
  separate supported-path proof.

External documentation consulted:

- https://api-docs.deepseek.com/guides/tool_calls (DeepSeek API Docs,
  accessed 2026-08-09 for this commit). Confirmed that the Chat
  Completions API uses the OpenAI-shape native tool call and that
  continuation is achieved by appending the assistant message plus a
  role: tool message with the matching tool_call_id.
- https://api-docs.deepseek.com/guides/thinking_mode (DeepSeek API
  Docs, accessed 2026-08-09). Confirmed that for requests carrying the
  tools parameter, reasoning_content must be fully passed back to
  the API in all subsequent requests, or the API returns a 400 error.
  This is the documented origin of the provider-continuation-state
  requirement that this contract treats as opaque continuation material.

The implementation does not introduce a new shared module. The existing
NormalizedCompletionOutput dataclass in guardian/core/ai_router.py
already carried every required semantic field (canonical command
identity, tool-call correlation identity, structured arguments, opaque
provider envelope), and the DeepSeek adapter reads/writes it without
duplicating the type. Inspecting it confirmed that creating a parallel
tool_turn_contracts module would have split the abstraction without
adding semantics.
