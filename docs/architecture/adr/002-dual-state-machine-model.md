---

tags:

* architecture
* adr
* runtime
* provider-state
* request-state
  aliases:
* ADR-002
* Dual State Machine

---

# ADR-002: Dual State Machine Model

## Status

Accepted

## Date

2026-04-13

## Context

Codexify operates across environments where:

* the provider may be reachable but still warming
* a model may be loading into memory
* a request may be accepted but not yet generating
* lifecycle visibility may degrade independently of execution

A single state machine is too crude for this reality.

If the system collapses provider readiness and request execution into one status, it creates ambiguity such as:

* “offline” when the runtime is reachable but warming
* “failed” when the request is only delayed
* “done” when the route only accepted work
* “ghost replies” when an earlier request completes after a timeout or replay

## Decision

Codexify models two separate state machines:

### 1. Provider Runtime State

Describes runtime/provider condition independent of any one request.

Examples:

* `OFFLINE`
* `CONNECTING`
* `RUNTIME_AVAILABLE`
* `MODEL_WARMING`
* `READY`
* `GENERATING`
* `DEGRADED`
* `ERROR`

### 2. Request Execution State

Describes the lifecycle of one completion attempt.

Examples:

* `QUEUED`
* `DISPATCHING`
* `AWAITING_ACK`
* `AWAITING_MODEL`
* `AWAITING_FIRST_TOKEN`
* `STREAMING`
* `COMPLETED`
* `CANCELLED`
* `TIMED_OUT`
* `FAILED_RETRYABLE`
* `FAILED_FATAL`
* `ORPHANED`
* `REPLAYED`

These two machines are related, but not interchangeable.

## Rationale

Provider truth answers:

> Is the runtime reachable and ready?

Request truth answers:

> What is happening to this specific attempt?

They must remain separate because local inference makes “slow” a normal state, not necessarily an error.

This decision prevents the system from collapsing warmup, delay, retry, timeout, and visibility degradation into one false narrative.

## Alternatives considered

### 1. Single unified state machine

Rejected.

Too ambiguous. It cannot cleanly represent provider readiness and request lifecycle at once.

### 2. Binary healthy/unhealthy model

Rejected.

Too crude for local-first inference.

### 3. Dual-state model

Chosen.

This is the smallest structure that preserves runtime truth.

## Consequences

### Positive

* clearer operator and UI semantics
* better handling of local-model warmup
* fewer false “offline” states
* better debugging of delayed and replayed requests

### Negative

* more system vocabulary
* more frontend mapping work
* more diagnostic surfaces to keep aligned

## Invariants created by this decision

* provider state must not be inferred from request state alone
* request state must not be inferred from provider state alone
* UI language must preserve the distinction
* future runtime token changes must keep this split intact

## Links

* [[ADR Index]]
* [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]]
* [[003-Message-Identity-vs-Request-Identity|ADR-003 Message Identity vs Request Identity]]
* [[chat-runtime-contract|Chat Runtime Contract]]
* [[chat-runtime-gap-analysis|Chat Runtime Gap Analysis]]
* [[tech-debt-and-risks|Tech Debt and Risks]]
* [[00-current-state]]

## Notes

If Codexify later introduces a third state plane for lifecycle visibility as a first-class external contract, that should supersede this ADR with a new one rather than mutating this decision in place.
