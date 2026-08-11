# Stage 2J-R5 — Capability Advertisement Observability Live Proof

## Date

2026-08-10

## R5 Task Verdict

`FAIL`

## Stage 2J Verdict

`FAIL`

## Diagnostic Outcome

`OBSERVABILITY_MISSING`

The one authorized ordinary completion was accepted and dequeued, but the
worker failed before the initial provider-router call. The new live
`toolExposure` evidence was therefore never persisted. This is a runtime
contradiction in the R5 implementation path, not evidence that DeepSeek
declined an advertised capability.

## Scope

R5 adds bounded observability for the existing Stage 2I automatic health
capability. It does not change capability authority, provider eligibility,
provider selection, tool-selection semantics, the Command Bus, DeepSeek's
adapter, Compose, supported profiles, or Whoosh'd source.

## Proof History R1-R4

- R1-R3 established the current-source Tester and clarified worktree and
  dual-provider topology constraints.
- R4 proved one ordinary DeepSeek completion on the approved per-thread lane,
  with a valid plain answer, `toolTurnState=idle`, `loopStopReason=plain_answer`,
  `commandRunId=null`, and zero Command Bus executions.
- R4 could not determine whether Stage 2I had advertised the health capability
  before that plain answer. R5 was authorized solely to make that seam durable
  and observable.

## R4 Plain-Answer Interpretation

A plain answer remains legal when a capability is advertised. R4 was not proof
of a plumbing failure. It left one observational question: whether the exact
canonical capability reached the initial DeepSeek dispatch.

## Frozen Source Identity

| Item | Value |
| --- | --- |
| `TARGET_MAIN` | `bad5e41f764bb33a68a4628b17f4775d650fbc03` |
| R4 base commit | `ce74a5500a0de9f80e7e8d48cfa9fc67ffa54cd2` |
| implementation commit | `68fce47694348e98eace6879803307f36c5cfaa5` |
| R5 branch | `codex/stage2j-r5-tool-exposure-observability` |
| Tester root | `/Volumes/Dev_SSD/Codexify-main` |

`TARGET_MAIN` is an ancestor of R4. The Tester was recreated from the R5
implementation commit before the live replay.

## Runtime Source Identity

Backend and `worker-chat` both bind-mounted the canonical Tester root. The host,
backend, and worker SHA-256 values matched for both required source files:

| File | SHA-256 |
| --- | --- |
| `guardian/core/chat_completion_service.py` | `ae7de8e1869070f903ede24e5e84308b9af6f32f4ffa5bcd96ef436139f1a434` |
| `guardian/tools/chat_exposure.py` | `627effb46c8a9f8e63efa6feaaeb37f94a60a94494ef3591d3689a617dca3086` |

## Runtime Health

Immediately before and after the replay, `make tester-status` reported the
Tester enabled and healthy: backend, Redis, database, Neo4j, frontend, and all
required workers were running; `worker-chat` had a fresh heartbeat and the chat
queue was empty.

## Global Provider / Model

- Supported profile: `v1-whooshd-deepseek-web`.
- Global provider: local Whoosh'd.
- Global model: `gemma-4-12b-it-qat-4bit`.
- DeepSeek: egress-allowed, credential-present, and available as the approved
  `deepseek-v4-flash` per-thread lane.

No global provider change, provider-environment mutation, or Whoosh'd
load/warm/unload action occurred.

## DeepSeek Thread Configuration

A new ordinary proof thread was created, then the normal durable thread-config
endpoint stored and read back:

```json
{"providerId":"deepseek","modelId":"deepseek-v4-flash"}
```

The complete durable snapshot retained existing defaults only:
`inferenceMode=fast`, `retrievalSource=project`, and `personaId=null`.

## Caller Tool Input

The normal completion route received exactly `{}`. The caller supplied no
`tools` and no `tool_choice`.

## Automatic Exposure Evidence

Not emitted. The task failed before the worker's direct bounded-completion call
could build or persist `toolExposure`.

## Provider Dispatch Evidence

Not emitted. The failure occurred before `_execute_completion_attempt` and
therefore before the exact initial `chat_with_ai` / provider-router dispatch.

## Deterministic DeepSeek Native Request Proof

Passed before live replay. The R5 router test proves that the canonical health
tool becomes exactly one native DeepSeek function named `codexify_tool_0`,
retains the strict empty-object parameter schema, does not use the canonical
command ID as the provider function name, adds no `tool_choice`, and accepts a
plain provider answer.

## DeepSeek Live Response Type

None. Exactly one ordinary completion task was accepted, but zero DeepSeek HTTP
inference calls completed: the terminal event reports `executed=false` and the
worker raised before `chat_with_ai` could run. Lifecycle markers
`AWAITING_MODEL` and `AWAITING_FIRST_TOKEN` are not evidence of a provider
response.

## Normalized Model Turn

Absent; no provider response reached normalization.

## Stage 1 Evidence

Absent; no normalized tool decision reached the advertised-subset authority
gate.

## Command Bus Evidence

No invocation occurred. Read-only database evidence found zero `command_runs`
created after the proof started.

## GET /health Evidence

Absent; no command was selected or dispatched.

## Provider Continuation Evidence

Absent; no tool result existed to reinject.

## Final Assistant Evidence

Absent. The proof thread contains one persisted user message and zero persisted
assistant messages.

## Tool-Turn Observability

No durable `toolExposure`, `toolTurnId`, `toolTurnState`, `loopStopReason`, or
`commandRunId` was produced for the failed task. The task identity was:

```text
threadId=5057
userMessageId=112500
taskId=52565953-7234-4fba-b05e-3c1474e119af
requestId=req_3d5da2dd4e5948afa7abbc03116668ac
turnId=85738113-d0bf-4401-9ea3-576bb00e6c04
```

## Command Execution Count

`0`.

## Write Check

No capability command, read or write, executed. The only durable setup writes
were the permitted proof-only account, thread, configuration, and user message.

## Second-Command Check

`0`. No first command occurred.

## Failure Classification

The failing seam is
`guardian/workers/chat_worker.py::_execute_completion_with_runtime_observability`
at its direct call to
`_execute_bounded_tool_turn_completion`. That parallel worker path omitted the
new required `tool_exposure` keyword and raised:

```text
TypeError: _execute_bounded_tool_turn_completion() missing 1 required keyword-only argument: 'tool_exposure'
```

The standard `run_chat_completion_task` path passed the argument correctly, and
the focused deterministic tests exercised that path. R5 did not authorize a
worker-source change, and production source must not be changed after this live
attempt. No retry was sent.

## Availability vs Selection Conclusion

No conclusion is possible. R5 did not reach either capability advertisement or
provider dispatch, so it cannot distinguish capability availability from model
selection. The failure is before that boundary.

## What Was Proven

- The canonical Tester executed the immutable R5 source, with matching backend
  and worker mounts and hashes.
- The supported dual-provider profile, local global default, DeepSeek
  per-thread configuration, credential presence, and worker health were valid.
- The deterministic R5 implementation and native DeepSeek request assertions
  passed.
- The live worker has a second bounded-completion invocation seam that the R5
  deterministic tests did not cover.

## What Was Not Proven

- Live `toolExposure` advertisement or provider-dispatch evidence.
- A DeepSeek provider response, plain answer, or native tool call.
- Stage 1 admission, Command Bus execution, `GET /health`, continuation, or a
  persisted assistant answer.
- The Stage 2J first ordinary Guardian capability live proof.

## Observability Boundary

The intended R5 object contains only a mode flag, bounded canonical command
IDs, counts, and an optional truncation flag. It never stores tool schemas,
descriptions, arguments, prompts, messages, raw provider payloads, credentials,
or provider-private continuation data. None of those fields was recovered from
the failed live task.

## Privacy / Secret Handling

The proof-only account credential and short-lived session token were generated
in memory and not printed, written, or committed. This receipt contains no
credential, authorization header, provider payload, or private continuation
data.

## ADR Impact

Aligned with ADR-052 and the Capability-Oriented Mesh architecture principle.
No new ADR and no new runtime protocol token are required. This failure receipt
does not widen a release claim.

## Documentation Follow-Through

Updated the Agent Tool Loop Contract, Completion Pipeline, and Provider Tool
Turn Boundary Contract to define the bounded evidence shape and the separation
between capability availability and model selection. The documentation does not
claim live advertisement proof.

## Validation

- `pytest -v tests/core/test_chat_tool_exposure.py tests/core/test_chat_completion_service_tool_loop.py tests/core/test_ai_router.py tests/providers/test_deepseek_adapter.py tests/providers/test_tool_turn_transport_convergence.py` — `90 passed` before live replay.
- `python3 scripts/validate_docs.py` — passed before live replay.
- `make docs PYTHON=python3` — passed before live replay.
- `git diff --check` — passed before live replay.
- Runtime source identity, supported-profile posture, worker heartbeat, thread
  configuration, task-event stream, message persistence, and Command Bus
  readback were collected after the one accepted completion.

## Final Runtime State

Tester remains enabled and healthy on the R5 branch. No retry, source switch,
provider mutation, profile change, or Whoosh'd lifecycle mutation occurred
after the failure.

## Final Repository State

The only uncommitted tracked file after the provisional implementation commit is
this receipt. The pre-existing protected `.worktrees/` directory remains
untouched.

## Final Commit

The amended final commit is recorded in the task closeout rather than in this
self-referential receipt.

## Exact Next Atomic Slice

`Stage 2J-R5F — wire bounded toolExposure through the worker's direct
bounded-completion invocation and add worker-path regression coverage.`

That task must repair only the omitted worker argument and its focused tests,
then run a newly authorized R5 live replay from a new immutable source commit.
It must not introduce provider-specific forced selection semantics.
