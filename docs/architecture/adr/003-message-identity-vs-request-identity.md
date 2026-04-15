---

tags:

* architecture
* adr
* identity
* transcript-integrity
  aliases:
* ADR-003
* Message vs Request Identity

---

# ADR-003: Message Identity vs Request Identity

## Status

Accepted

## Date

2026-04-13

## Context

Codexify supports asynchronous execution and must tolerate:

* retries
* timeouts
* orphans
* replays
* delayed completions

Under those conditions, one user-authored message can correspond to multiple execution attempts.

If the system models only one identity, it cannot cleanly distinguish:

* “same user turn, retried”
* “new user turn, new completion”

That ambiguity damages transcript integrity and operator reasoning.

## Decision

Codexify defines two distinct identities:

### Message identity

Represents the authored user turn.

`messageId`

Properties:

* stable
* user-authored
* does not change across retries or replays

### Request identity

Represents one execution attempt for that message.

`requestId`
`attemptNumber`

Properties:

* per-attempt
* changes on retry or replay
* attached to provider and runtime execution details

One `messageId` may therefore have many associated `requestId` values.

## Rationale

Without this split:

* retries can look like duplicate turns
* delayed responses can attach to the wrong logical event
* replay behavior becomes ambiguous
* transcript integrity degrades

With this split:

* the transcript remains stable
* execution history remains inspectable
* retry and replay semantics are explicit

## Alternatives considered

### 1. Single identity for both message and execution

Rejected.

Cannot represent retries or replay safely.

### 2. Overwrite message state on retry

Rejected.

Destroys attempt history and increases ambiguity.

### 3. Stable message + per-attempt request identity

Chosen.

This preserves authored truth and execution truth simultaneously.

## Consequences

### Positive

* transcript integrity remains stable
* retries and replays become modelable
* observability improves
* future tooling can inspect attempts without mutating the message record

### Negative

* more data relationships
* more UI/runtime bookkeeping
* more contracts to keep aligned

## Invariants created by this decision

* `messageId` must remain stable across retries
* `requestId` must identify only one attempt
* replay must preserve linkage to the original message
* no downstream layer may collapse these identities back into one

## Links

* [[ADR Index]]
* [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]]
* [[002-Dual-State-Machine-Model|ADR-002 Dual State Machine Model]]
* [[chat-runtime-contract|Chat Runtime Contract]]
* [[completion_pipeline|Completion Request Pipeline]]
* [[flows|Critical Flows]]

## Notes

If Codexify later introduces user-visible attempt history or replay inspection in Command Center, it should build on this decision instead of redefining identity semantics.
