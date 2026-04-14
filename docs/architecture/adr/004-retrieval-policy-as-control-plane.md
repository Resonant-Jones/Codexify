---

tags:

* architecture
* adr
* retrieval
* control-plane
* policy
  aliases:
* ADR-004
* Retrieval Policy Control Plane

---

# ADR-004: Retrieval Policy as Control Plane

## Status

Accepted

## Date

2026-04-13

## Context

Codexify’s retrieval system already separates:

* route handling
* completion orchestration
* context assembly
* provider execution

At the same time, the system now has explicit control-surface primitives:

* slash intent
* backend interpretation
* retrieval override
* effective retrieval policy
* retrieval posture diagnostics

Without a formal decision here, retrieval logic risks leaking into:

* prompt text
* UI heuristics
* provider-side behavior
* ad hoc route branching

That would reintroduce semantic drift.

## Decision

Codexify treats retrieval policy as a **control plane**, not as prompt logic.

The canonical chain is:

`slash_intent`
→ `retrieval_override`
→ `effective_policy`
→ `ContextBroker` retrieval behavior
→ `retrieval_posture` / trace visibility

Retrieval policy is therefore:

* explicit
* backend-owned
* inspectable
* deterministic

It must be applied before retrieval execution and outside prompt construction.

## Rationale

The system already has doctrine stating that retrieval decisions belong before `ContextBroker` assembly, not in prompt text and not in UI controls.

The retrieval pipeline work confirms that:

* `retrieval_override` is derived from slash intent
* `effective_policy` is formed by merging defaults with the override
* retrieval posture is observable in diagnostics
* routing behavior is constrained without mutating provider or prompt logic

This decision prevents the system from drifting back into hidden retrieval heuristics.

## Alternatives considered

### 1. Prompt-driven retrieval instructions

Rejected.

Hidden, brittle, and hard to trace.

### 2. UI-only control of retrieval scope

Rejected.

Creates duplicate truth surfaces and backend ambiguity.

### 3. Backend policy control plane

Chosen.

This preserves determinism and observability.

## Consequences

### Positive

* retrieval scope becomes explicit
* diagnostics reflect true posture
* policy can evolve independently of prompts
* future Flow Builder integration has a stable control contract

### Negative

* more policy vocabulary to maintain
* more docs and traces to keep aligned
* contributors must understand the control-plane split

## Invariants created by this decision

* retrieval policy must not be derived from prompt text
* `retrieval_override` must be derived only from validated `slash_intent`
* `effective_policy` must be formed by policy merge, not override replacement
* retrieval posture in diagnostics must reflect backend truth, not frontend reconstruction
* `source_mode`, `widen_reason`, and related retrieval posture fields remain operator truth surfaces

## Links

* [[ADR Index]]
* [[router-decision-table|Retrieval Router Decision Table]]
* [[flows|Critical Flows]]
* [[system-overview|System Overview]]
* [[00-current-state]]
* [[tech-debt-and-risks|Tech Debt and Risks]]
* [[Flow Builder Registry]]

## Notes

This ADR establishes the doctrine that **retrieval is governed, not improvised**.

Future work may extend policy with:

* stricter thread-only posture
* widening controls
* explicit memory posture
* Flow Builder policy emission

Those are extensions of this decision, not replacements for it.
