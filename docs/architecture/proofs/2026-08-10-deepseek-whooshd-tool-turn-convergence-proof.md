# DeepSeek and Whoosh'd tool-turn semantic convergence proof

**Date:** 2026-08-10
**Execution lane:** architecture-impact
**Task kind:** cross-provider semantic convergence proof
**Conclusion:** test-proven for the exact two transports and bounds below; not live-provider or release proof.

## Purpose

Prove that DeepSeek native tool calls and the exact Stage 2D-qualified Whoosh'd strict-structured transport are different provider representations of the same bounded Codexify semantic tool action.

## Scope

The proof uses a synthetic read-only `op::lookup_widget` action with `{"widget_id":"alpha"}` and a mocked Command Bus result. It makes no live provider call, starts no Whoosh'd process, and performs no Command Bus side effect.

## Starting Revision

| Item | Value |
| --- | --- |
| Codexify branch / starting `HEAD` | `codex/correct-whooshd-model-identity` / `14f9699e1b6955f96bd28eba6dafe114ab500d30` |
| Stage 2G / Stage 2F.1b / tokenizer ancestors | `14f9699e1` / `930dfdc14` / `7f20c79ba` — verified |
| Whoosh'd reference | Read-only `d08e3261d8ed2217b9c258bb783138fc6a06df9f`; pre-existing `.venv311/` untouched |

## Governing Contracts

- `provider-tool-turn-boundary-contract.md`
- `agent-tool-loop-contract.md`
- `whooshd-model-tool-capability-boundary.md`
- `whooshd-runtime-qualification-attestation-contract.md`
- `runtime-protocol-token-contract.md`
- Stage 1 advertised-subset authority

## Provider Transports Under Proof

DeepSeek starts with a native Chat-Completions-shaped function call. The real `normalize_tool_calls` adapter step resolves its opaque `codexify_tool_0` alias to Codexify's canonical command. Whoosh'd starts with the exact strict ModelTurn for `gemma-4-12b-it-qat-4bit`; the real parser validates response shape, arguments, matching runtime provenance, and Stage 2F.1b attestation before the decision enters the shared carrier.

## Canonical Semantic Core

The shared carrier is `guardian.core.ai_router.NormalizedCompletionOutput`; no production `ModelTurn` type was added. The asserted tuple is:

```python
(kind, command_id, arguments)
== ("tool_decision", "op::lookup_widget", {"widget_id": "alpha"})
```

## Provider-Specific State Boundary

DeepSeek retains `tool_call_id`, raw assistant envelope, and `reasoning_content`. Whoosh'd retains runtime provenance and qualification attestation with no native call ID. Those fields are distinct, excluded from semantic equality, and never Guardian authority inputs.

## DeepSeek Native Mapping

`build_tool_definitions` produces an opaque alias; `parse_response` preserves the native call; `normalize_tool_calls` maps it back to `op::lookup_widget` before `NormalizedCompletionOutput`. The continuation replays the original assistant envelope, including `reasoning_content`, plus a `role: tool` message correlated by `tool_call_id`.

## Whoosh'd Strict-Structured Mapping

`parse_structured_response` receives the schema-valid decision, canonical command, arguments, and matching Stage 2F.1b evidence. Provenance is required transport qualification evidence, not permission. Continuation uses adapter-owned structured decision/result messages without inventing a native call ID.

## Semantic Convergence Matrix

| Surface | DeepSeek native | Qualified Whoosh'd structured | Result |
| --- | --- | --- | --- |
| Semantic tuple | alias resolves to canonical command | strict ModelTurn supplies canonical command | equal |
| Authorized execution | one Stage 1-approved invoke | one Stage 1-approved invoke | same command/body |
| Command result | mocked `run-convergence`, `{"status":"green"}` | same mocked result | equal |
| Final answer | `Widget alpha is green.` | same | equal |
| Observability | completed / `tool_turn_completed` | same | same shape |
| Continuation | native envelope + `role: tool` | structured assistant/user context | intentionally distinct |

## Guardian Authority Convergence

Both proposals enter `chat_completion_service._execute_bounded_tool_turn_completion`. The Stage 1 gate derives the nonempty set through `_authorized_tool_command_ids`, compares the normalized canonical command, and permits the same `execute_invoke` seam once with equivalent `InvokeArguments.body`.

## Command Bus Execution Convergence

Both paths receive the same mocked result:

```json
{"run_id":"run-convergence","status":"completed","inline_result":{"status":"green"}}
```

## Tool Result Semantics

The result means `op::lookup_widget` with `{"widget_id":"alpha"}` returned `{"status":"green"}`. No provider-private state changes it before adapter translation.

## Provider Continuation Differences

DeepSeek uses provider-native correlation replay; Whoosh'd uses a structured semantic decision/result envelope. Both encode the same command, arguments, and result, without requiring byte-identical messages.

## Final Answer Convergence

After one mocked execution, both loops return `Widget alpha is green.`.

## Observability Convergence

Both success paths emit `toolTurnState=completed`, `loopStopReason=tool_turn_completed`, `commandRunId=run-convergence`, and present `toolTurnId`, `messageId`, and `requestId`. Independent identity values are not compared across runs.

## Unadvertised Command Proof

At the valid normalized authority seam, both providers block an unadvertised canonical command before `execute_invoke`, with `failed`, `tool_command_blocked`, and no command run ID. Because Whoosh'd strict schema binds the single prepared command, its case is an authority-seam proof—not a claim that it can emit DeepSeek's invalid wire behavior.

## Malformed Output Proof

Unknown DeepSeek aliases, multiple native calls, invalid Whoosh'd arguments, and a Whoosh'd qualification mismatch all fail before `execute_invoke`. Their provider-specific errors are not forced into one exception type.

## One-Tool Limit Proof

DeepSeek multiple native calls execute zero commands. A second decision after one execution is contained for both transports with `limit_reached`, `tool_turn_limit_reached`, and exactly one total invoke.

## Plain-Answer Proof

DeepSeek plain output has no invoke and `idle` / `plain_answer`. Whoosh'd ordinary no-tools chat retains its streaming path with the same no-invoke observability. Ordinary production `task.tools` remains `None`.

## Provider-Private State Isolation

Changing a DeepSeek correlation ID cannot authorize an unadvertised canonical command. Whoosh'd qualification `MATCH` can permit a structured proposal to reach Stage 1 but cannot authorize that command. Guardian uses canonical command identity, not DeepSeek correlation/reasoning/raw state, Whoosh'd provenance, or qualification digest.

## Stage 2F.1b Qualification Boundary

The exact qualified target and expected digest are used. A mismatch or insufficient evidence fails during Whoosh'd transport validation before Guardian authority; qualification stays evidence, not command authority.

## Stage 2G Capability Boundary

Stage 2G is not invoked to authorize execution. It remains a pre-request evidence projection; this proof creates no `task.tools` producer, capability advertisement, or exposure-policy change.

## Explicit Exclusion of Loose JSON

Legacy generic/free-form JSON normalization is excluded. This proof covers only DeepSeek native transport and the exact qualified Whoosh'd strict-structured transport.

## What This Proves

DeepSeek native tool calls and the exact qualified Whoosh'd strict-structured transport are different provider representations of the same bounded Codexify semantic tool action. For the exercised synthetic action, both reach the same normalized semantic core, Guardian authority gate, Command Bus seam, one-tool limit, and canonical observability semantics.

## What This Does Not Prove

This does not qualify OpenAI, Anthropic, generic OpenAI-compatible providers, arbitrary Whoosh'd models, GGUF, llama.cpp, other MLX targets, loosely prompted JSON, recursive execution, parallel execution, live provider behavior, or a release claim.

## Validation

- `.venv/bin/pytest -q tests/providers/test_tool_turn_transport_convergence.py` — 21 passed.
- Focused provider/core suite — 140 passed; this includes the convergence,
  DeepSeek, Whoosh'd qualification/capability, bounded tool-loop, and router
  tests.
- `python3 scripts/validate_docs.py`, `make docs PYTHON=python3`, and Ruff for
  the new test passed; `git diff --check` passed.
- Full `.venv/bin/pytest -q` did not collect because the existing environment
  lacks `jsonschema`, `cryptography`, `jwt`, `neo4j`, `typer`, `orjson`,
  `alembic`, and `python-multipart` (40 collection errors). This proof adds no
  failure within its focused surface.

## Repository State

Only the four Stage 2H paths are intended for this atomic commit. No production Python file or Whoosh'd file is changed; Whoosh'd's pre-existing `.venv311/` remains untouched.

## ADR Impact

Aligned with existing contracts; no new ADR. This is executable proof of the existing provider-neutral semantic boundary, not new provider/tool architecture.

## Next Atomic Slice

If separately authorized, Stage 2I may decide whether and how to advertise one ordinary read-only Guardian capability. It must retain Stage 1, exact provider eligibility, the one-tool limit, and fail-closed behavior. This task does not begin Stage 2I.

## Commit

Atomic commit: `Prove provider tool turn convergence` (hash recorded in the task closeout).
