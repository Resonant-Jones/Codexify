# Runtime Protocol Token Contract

## Purpose
Define a single canonical source for runtime protocol tokens (statuses, event
names, and machine-readable error codes). This is the runtime analogue of the
Codexify UI token system, so the backend exposes a stable truth surface instead
of ad hoc literals.

## Scope
This contract covers the current core chat loop in the backend. It does not
attempt a full-repo migration.

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
- Acceptance statuses: `accepted`, `accepted_degraded`.
- Task event types: `task.created`, `task.completed`, `task.failed`,
  `task.cancelled`, `task.event`.
- Error codes: `QUEUE_ENQUEUE_FAILED`, `CHAT_COMPLETE_ENQUEUE_FAILED`,
  `TASK_EVENT_PUBLISH_FAILED`, `CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED`.
- Frontend live-events connection states are governed by
  `frontend/src/contracts/runtimeTokens.ts`.

## Change process
- Add the new token to `guardian/protocol_tokens.py`.
- Update the call sites to import and use the canonical token.
- Extend `tests/contracts/test_protocol_tokens.py` to lock in the value.

## Non-goals
- No route/queue contract redesigns or new semantics.
- No migration of unrelated subsystems (collaboration, federation, tools).
- No full-repo refactor of existing literals in this task.
