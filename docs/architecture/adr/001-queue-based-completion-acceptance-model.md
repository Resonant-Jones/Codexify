---

tags:

* architecture
* adr
* queue
* chat-runtime
  aliases:
* ADR-001
* Queue Acceptance Model

---

# ADR-001: Queue-Based Completion Acceptance Model

## Status

Accepted

## Date

2026-04-13

## Context

Codexify's chat completion path is queue-backed.

The runtime shape is:

1. user message is persisted
2. completion route validates and acquires turn ownership
3. a `ChatCompletionTask` is enqueued
4. a worker later dequeues and executes
5. assistant output is persisted
6. task events expose progress and terminal visibility

This means the API route cannot truthfully treat acceptance as completion.

Without an explicit decision here, the system drifts toward one of two bad states:

* pretending synchronous guarantees exist when they do not
* leaking ambiguous “success” semantics into UI, logs, and operator surfaces

## Decision

A successful completion-route response means:

* the per-thread turn lock was acquired
* the completion task was successfully enqueued

It does **not** mean:

* the worker has dequeued the task
* the provider has started generation
* assistant output has been persisted
* the UI has received task lifecycle events
* the request will complete successfully

This is an **acceptance model**, not a synchronous completion model.

## Rationale

The system already separates:

* route acceptance
* worker execution
* provider execution
* event visibility
* persistence

That separation is not incidental. It is required by the local-first, worker-backed runtime.

Codexify must therefore preserve a stable truth:

> acceptance is queue acceptance plus turn ownership, not eventual success

This decision protects:

* runtime honesty
* transcript integrity
* observability clarity
* future retry semantics

## Alternatives considered

### 1. Treat route success as completion success

Rejected.

This would make the API lie about reality and create false assumptions in UI and ops surfaces.

### 2. Block until the worker finishes

Rejected.

This would collapse the queue model, increase latency, and behave poorly under local-model warmup and slow inference.

### 3. Acceptance-based queue model

Chosen.

This matches the runtime topology and preserves the distinction between admission and execution.

## Consequences

### Positive

* preserves truthful API semantics
* aligns route behavior with worker-backed execution
* enables retries, fallback, and delayed execution without semantic drift
* improves operator reasoning during incidents

### Negative

* UI must model non-terminal accepted states
* task visibility becomes important
* operators must interpret multiple surfaces together
* success language must stay precise

## Invariants created by this decision

* route acceptance must not imply completion
* queue acceptance must remain distinguishable from task visibility
* event publication must not be treated as proof of UI receipt
* worker success must remain distinct from route success

## Links

* [[ADR Index]]
* [[002-Dual-State-Machine-Model|ADR-002 Dual State Machine Model]]
* [[003-Message-Identity-vs-Request-Identity|ADR-003 Message Identity vs Request Identity]]
* [[flows|Critical Flows]]
* [[completion_pipeline|Completion Request Pipeline]]
* [[00-current-state]]

## Notes

If Codexify later adds a synchronous degraded execution lane, that must be documented as a **new ADR** rather than silently weakening this one.
