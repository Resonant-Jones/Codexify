---

tags:

* architecture
* adr
* chat-runtime
* transport-visibility
* stream-recovery
  aliases:
* ADR-038
* Chat Transport Visibility and Adaptive Stream Recovery Contract

---

# ADR-038: Chat Transport Visibility and Adaptive Stream Recovery Contract

## Status

Accepted

## Date

2026-06-30

## Context

Codexify already distinguishes provider runtime state from request execution state. That split is necessary, but it is still incomplete for variable network conditions.

When a user is connected over a hotspot, roaming link, or otherwise unstable transport, the visible chat stream can appear to drop even when the backend continues processing successfully. A later user action may cause the earlier completion to appear, which means the failure may have been in stream visibility rather than provider execution or request success.

This ambiguity is not solved by provider state alone:

- the provider may still be reachable and generating
- the request may still be accepted and running
- the frontend may have lost visibility of the stream or terminal event

ADR-002 explicitly notes that if Codexify later introduces a third state plane for lifecycle visibility, that should come in as a new ADR rather than by mutating the dual-state model in place. This ADR is that third plane.

## Decision

Codexify defines a third conceptual plane for chat turns: **transport visibility state**.

Transport visibility state describes whether the frontend can still observe the stream for a specific attempt. It is distinct from:

- provider runtime state, which answers whether the provider lane is reachable, warming, ready, or degraded
- request execution state, which answers what the specific attempt is doing after acceptance

The canonical transport visibility states are:

- `connected`
- `suspected_stalled`
- `recovering`
- `recovered`
- `failed`

These states describe observation, not execution. A stream can be suspected stalled while the provider is still healthy. A stream can recover while the underlying request was never retried. A stream can fail visibly while the backend still finishes and persists the assistant result.

## Recovery Meaning

Adaptive stream recovery is observation recovery, not request replay.

If transport visibility degrades:

- the frontend may attempt to re-establish observation of the existing attempt
- the backend must not be silently asked to create a new assistant turn
- any late terminal result must remain tied to the original request and message identity
- duplicate assistant messages must be suppressed rather than emitted again

Transport recovery therefore preserves transcript integrity by rejoining the existing completion path instead of inventing a new one.

## Rationale

This is the smallest state split that keeps the runtime honest under partial failure.

Without transport visibility state, Codexify can collapse several different realities into one user-visible story:

- backend still processing
- model waiting for first token
- transport stalled
- client missed a chunk or terminal event
- request completed but the UI did not observe it
- network recovered only after a subsequent user action

That collapse is exactly how a visible completion can look "dropped" while the backend still completed successfully.

## Non-Goals

This ADR does not:

- implement retry logic
- define exact timeout values
- define the transport protocol mechanics for reconnect
- change provider routing
- change message persistence
- introduce duplicate assistant messages
- turn stream recovery into a recursive completion retry loop
- claim any transport recovery behavior is already shipped on `main`

## Future Follow-Up Specs

The following belong in separate implementation tasks or follow-up specs:

1. first-token expectation windows
2. model/profile-specific TTFT tuning
3. stream stall timers and heartbeat or keepalive policy
4. reconnect or resubscribe behavior
5. duplicate suppression rules for late terminal events
6. transcript-safe recovery UI states such as `reconnecting` or `response delayed`

## Invariants

- A stalled or recovering stream does not automatically mean the provider is offline.
- A stalled or recovering stream does not automatically mean the request failed.
- Recovery must preserve the original `messageId` / `requestId` linkage.
- Recovery must not synthesize a new assistant message for the same turn.
- Model/profile-specific timing remains a future implementation concern, not a fixed doctrine in this ADR.

## Consequences

### Positive

- Gives the frontend a distinct transport-state vocabulary
- Lets the UI distinguish recoverable visibility loss from provider failure
- Preserves transcript integrity under network-variable conditions
- Clarifies why a later visible assistant turn may belong to an earlier request

### Tradeoffs

- Adds another conceptual plane to keep aligned
- Requires follow-up specs before any runtime recovery implementation
- Increases the need for duplicate-suppression discipline in terminal handling

## Links

- [[ADR Index]]
- [[002-Dual-State-Machine-Model|ADR-002 Dual State Machine Model]]
- [[003-Message-Identity-vs-Request-Identity|ADR-003 Message Identity vs Request Identity]]
- [[chat-runtime-contract|Chat Runtime Contract]]
- [[chat-runtime-gap-analysis|Chat Runtime Gap Analysis]]
- [[completion_pipeline|Completion Request Pipeline]]
- [[flows|Critical Flows]]
- [[00-current-state]]

## Notes

This ADR is docs-only and does not widen the supported beta surface.
