# Stage 2J-R5D — Canonical Chat Capability-Preparation Seam Proof

## Date

2026-08-11

## Verdict

`PASS`

## Scope

This narrow orchestration repair removes the parallel capability-preparation
truth surface between shared completion and queued worker execution. It does
not add a capability, provider adapter behavior, selection semantics,
`tool_choice`, Command Bus behavior, a live inference attempt, or a release
claim.

## R5 Failure Context

R5 added bounded `toolExposure` evidence to the shared bounded-completion
executor. Its one authorized live DeepSeek replay failed before provider
dispatch because the worker's direct invocation omitted the new required
`tool_exposure` argument. No provider response, Command Bus invocation,
assistant message, or capability execution occurred.

## Blocked R5F Discovery

The initial R5F inspection correctly stopped before editing. The worker did not
have an existing canonical `tool_exposure` object to forward: it bypassed the
shared preparation block where ordinary automatic exposure is resolved and R5
evidence is constructed. A worker-local reconstruction would have created a
second policy and evidence truth surface.

## Architectural Defect

The shared and worker paths converged at bounded execution but not at
capability preparation. The shared path owned automatic-versus-explicit
determination, Stage 2I resolution, and bounded evidence construction; the
worker had none of those inputs.

## Canonical Preparation Seam

`guardian/core/chat_completion_service.py::_prepare_chat_tool_exposure` is the
single preparation helper. Given the already resolved task/provider/model and
settings, it captures whether `task.tools` was unset, resolves ordinary Stage
2I exposure only for that automatic case, and returns the existing bounded R5
evidence for the post-resolution subset. Its only mutation is the pre-existing
canonical `task.tools` assignment.

## Shared Path Before / After

Before R5D, `run_chat_completion_task` contained the preparation logic inline.
After R5D, it calls `_prepare_chat_tool_exposure` and passes that returned object
unchanged into `_execute_bounded_tool_turn_completion`.

## Worker Path Before / After

Before R5D, `_run_chat_completion_task_compat` entered
`_execute_bounded_tool_turn_completion` without any preparation or
`tool_exposure` argument. After R5D, it calls the same service-owned helper
with its resolved provider/model and passes the exact returned object into the
same bounded executor.

## Capability Authority Preservation

Preparation only determines the model-visible advertised subset and bounded
observation. Stage 1 still requires a normalized canonical command to match
that exact subset before execution. The Command Bus remains the only execution
path.

## Automatic Exposure Preservation

For an automatic DeepSeek task, the helper resolves exactly
`op::health_health_get`, assigns the resulting ToolSpec list to `task.tools`,
and records `automatic=true`, count `1`, and that canonical ID. It does not
force selection.

## Explicit Tool-List Preservation

Explicit `task.tools=[]` remains explicit zero authority without invoking the
automatic resolver. Explicit nonempty subsets remain the caller-supplied object
and are observed as `automatic=false`.

## ToolExposure Preservation

The helper retains the R5 schema unchanged: automatic flag, bounded advertised
and provider-dispatch counts/command IDs, and truncation flag only. It contains
no schemas, descriptions, arguments, prompts, credentials, raw provider
payloads, or continuation state.

## Worker Parity Proof

The focused worker semantics test intercepts the service-owned preparation
helper and bounded executor for an automatic DeepSeek task. It proves that the
worker uses the helper, receives the health ToolSpec on `task.tools`, and passes
the exact same evidence object by identity into bounded execution. The
plain-answer fixture retains `toolTurnState=idle`,
`loopStopReason=plain_answer`, `commandRunId=null`, and zero Command Bus calls.

## No Parallel Exposure Logic Proof

The worker test replaces the service resolver with a failing guard while the
prepared helper is intercepted. The worker succeeds through the helper and
never calls the resolver directly. No manifest projection or evidence-dict
construction was added to worker code.

## Stage 1 Preservation

No Stage 1 code changed. The bounded executor still derives authority from the
post-preparation `task.tools` subset and rejects unadvertised canonical
commands before `execute_invoke`.

## Command Bus Preservation

No Command Bus code changed. The worker plain-answer parity fixture records no
Command Bus invocation.

## Provider Adapter Preservation

No provider adapter or provider router file changed. Preparation is
provider-neutral orchestration before adapter translation.

## Selection-Semantics Non-Change

R5D does not add `tool_choice`, forcing, or automatic/required selection
semantics. An advertised capability may still be declined by the model.

## ADR Impact

Aligned with ADR-061 Capability-Oriented Mesh Architecture and supported by
ADR-052's approved DeepSeek lane. No new ADR or runtime token is required.

## Diagram Freshness Review

The change to `modules-and-ownership.md` required a diagram freshness review
because it belongs to the Runtime Diagram Source Set. The existing Chat
completion lane row in `module-diagram-coverage-matrix.md` remains correct:
the lane remains high blast radius, global topology and sequence coverage still
exists, module-level failure/ownership coverage remains partial, and the
module-level diagram set remains planned. No new or modified runtime diagram is
required for this bounded ownership/dataflow seam.

The matrix review marker was updated to:

```text
Diagram Review Marker: 2026-08-11 (Stage 2J-R5D canonical chat capability-preparation seam review; no diagram coverage change)
```

## Validation

- `tests/core/test_chat_tool_exposure.py` — `21 passed`.
- `tests/core/test_chat_completion_service_tool_loop.py` — `16 passed`.
- `guardian/tests/workers/test_chat_worker_completion_semantics.py` — `23 passed`.
- `python3 scripts/validate_docs.py` — passed.
- `make docs PYTHON=python3` — passed after the matrix marker update, including
  the diagram freshness check.
- `git diff --check` — passed.
- `tests/architecture` — `392 passed`, with the same two pre-existing DLG
  failures in untouched knowledge-graph JSON/ancestry metadata.

An additional legacy test file, `tests/workers/test_chat_worker_tool_loop.py`,
was inspected as an adjacent regression surface. Its two tool-decision fixtures
expect an unadvertised `op::echo` command to execute. R5D correctly blocks that
command at Stage 1 after preparation; changing that out-of-scope test or
widening capability authority is not authorized here.

## Documentation Follow-Through

`completion_pipeline.md` now identifies the shared preparation seam and
prohibits worker-local exposure derivation. `modules-and-ownership.md` assigns
preparation ownership to the completion service and queued lifecycle ownership
to the worker. `module-diagram-coverage-matrix.md` records the no-coverage-change
review marker required for that material ownership update.

## What Was Proven

- Shared and worker paths consume one service-owned preparation implementation.
- Automatic, explicit-empty, explicit-nonempty, and ineligible-target
  preparation semantics are deterministic and covered.
- Worker forwarding preserves the exact prepared R5 evidence object.
- No provider adapter, Command Bus, profile, or capability-selection behavior
  changed.

## What Was Not Proven

- No provider inference was performed.
- No Tester restart or runtime mutation was performed.
- Stage 2J remains not live-runtime complete.
- `ADVERTISED_PLAIN_ANSWER` remains unproven.
- The R5F live DeepSeek diagnostic replay remains required.

## Commit

The final task commit introducing this receipt is recorded in the task
closeout.
