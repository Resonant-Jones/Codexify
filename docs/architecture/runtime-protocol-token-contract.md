# Runtime Protocol Token Contract

## Purpose
Define a single canonical source for runtime protocol tokens (statuses, event
names, and machine-readable error codes). This is the runtime analogue of the
Codexify UI token system, so the backend exposes a stable truth surface instead
of ad hoc literals.

## Scope
This contract remains anchored to the core chat loop, while explicitly
including frontend and shared-runtime interpretation tokens. It governs the
observable runtime truth surface across the stack, not just backend literals,
and does not attempt a full-repo migration.

## What counts as a protocol token
Runtime values that are part of the system truth surface, including:
- Status strings returned by routes or workers.
- Task event names carried over queues or streams.
- Machine-readable error codes used for failure classification.

## Core rule
New runtime literals must be added to a canonical protocol-token module before
use. Routes, queues, and workers must import tokens from that module and avoid
inline literals.

## Current token domains

- Acceptance statuses:
  `accepted`, `accepted_degraded`

- Task event types:
  `task.created`, `task.completed`, `task.failed`,
  `task.cancelled`, `task.event`

- Error codes:
  `QUEUE_ENQUEUE_FAILED`, `CHAT_COMPLETE_ENQUEUE_FAILED`,
  `TASK_EVENT_PUBLISH_FAILED`, `CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED`

- Bounded tool-loop states:
  `idle`, `decision_received`, `command_dispatched`,
  `result_reinjected`, `completed`, `failed`, `limit_reached`

- Bounded tool-loop stop reasons:
  `plain_answer`, `tool_turn_completed`, `tool_decision_invalid`,
  `tool_command_failed`, `tool_command_blocked`,
  `tool_turn_limit_reached`, `cancelled`

- Provider runtime states:
  Canonical states used for frontend/shared-runtime interpretation of provider
  availability and readiness (for example: `offline`, `connecting`,
  `runtime_available`, `model_warming`, `ready`, `generating`, `degraded`,
  `error`). These are normatively defined in
  `docs/architecture/chat-runtime-contract.md`.

- Request lifecycle states:
  Canonical states describing the lifecycle of a single completion attempt (for
  example: `queued`, `dispatching`, `awaiting_ack`, `awaiting_model`,
  `awaiting_first_token`, `streaming`, `completed`, `cancelled`, `timed_out`,
  `failed_retryable`, `failed_fatal`, `orphaned`, `replayed`). These are
  normatively defined in `docs/architecture/chat-runtime-contract.md`.

- Frontend runtime-health and failure-kind tokens:
  Governed by `frontend/src/contracts/runtimeTokens.ts`.

- Identity note:
  Fields such as `messageId` and `requestId` are identity primitives rather
  than protocol tokens, but vocabulary describing replay, orphaning, attempt
  semantics, and bounded tool-loop state is considered part of the runtime
  protocol surface.

## Interpretation caveat
Canonical token definitions establish a shared vocabulary for runtime meaning.
They do not by themselves prove that every state is already emitted end-to-end
in the live runtime. Runtime behavior must be verified against current-state
artifacts and supported-path proofs.

## Registry boundaries
Protocol tokens must remain scoped to runtime truth surfaces:
- statuses
- lifecycle states
- event types
- machine-readable error codes

This contract does not attempt to canonicalize all literals in the repo.
Token registries should remain bounded by semantic domain and operational
meaning.

## Change process
- Add the new token to `guardian/protocol_tokens.py`.
- Update the call sites to import and use the canonical token.
- Extend `tests/contracts/test_protocol_tokens.py` to lock in the value.

## Non-goals
- No route/queue contract redesigns or new semantics.
- No migration of unrelated subsystems (collaboration, federation, tools).
- No full-repo refactor of existing literals in this task.
