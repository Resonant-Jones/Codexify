# ADR-091: Durable Chat Completion Attempt Authority

**Status:** Accepted for this bounded implementation — 2026-09-26

## Context

The shared `enqueue_chat_completion` service accepts ordinary chat, Hosted Room owner, and Hosted Room guest completions. A Redis task ID previously had no durable pre-execution binding to the chat resource that governs access. This blocks task-event authorization: knowledge of a task ID is not permission to read its events. ADR-003 already separates authored message identity from per-attempt request identity.

## Decision

Each new chat completion has a Postgres `chat_completion_attempts` row keyed by its canonical `request_id`, with a unique subordinate `backend_task_id` and a foreign key to its canonical chat thread. The shared acceptance service commits this row after acquiring its turn lock and before publishing the task to Redis. Queue failure retains the row with null `accepted_at`; successful enqueue records `accepted_at`. Failure to record that timestamp after enqueue degrades the acceptance receipt and is logged without denying already accepted work.

The thread is the authorization resource. Future task-scoped readers resolve `backend_task_id -> attempt -> thread` and then apply the existing thread or Hosted Room access policy. Ordinary thread ownership may resolve through `chat_threads.user_id`; a Hosted Room guest is not recast as that owner. Initiator metadata, if later retained, is provenance rather than authority.

Redis queues, locks, event streams and payloads, replaceable debug fields, and ephemeral acceptance participants do not establish ownership. A missing durable mapping must fail closed for protected task-scoped reads. Historical tasks are not backfilled from those sources.

## Scope and consequences

The shared service owns this invariant for all current completion producers. This decision does not implement task-event SSE authorization, the complete replay/orphan/request-state model, or additional account identity. The public-ingress proof remains HOLD, and no release support claim changes.
