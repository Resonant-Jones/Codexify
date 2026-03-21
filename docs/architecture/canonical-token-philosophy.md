# Canonical Token Philosophy

Purpose: define how Codexify decides when a repeated concept must become a canonical token, and constrain how agents and humans extend the codebase without reintroducing semantic drift.

Last updated: 2026-03-21

---

## 1. Why this exists

Codexify already treats UI design tokens as a canonical law: one source of truth, no ad hoc literals, no local improvisation, and no silent divergence from AppShell-defined values. The same discipline is required anywhere repeated literals carry contract meaning in runtime behavior, event transport, error reporting, storage lifecycle, or operator truth surfaces.

This matters because Codexify’s runtime already depends on precise distinctions that are easy to blur if strings are invented locally. Route acceptance is not eventual completion, task-event publication is not downstream UI receipt, and queue progress is not proof that a worker dequeued a specific task. Those are not naming preferences. They are system truths that must remain stable across routes, workers, logs, tests, docs, and UI surfaces.

---

## 2. Core principle

If a concept appears repeatedly and carries contract meaning, it must graduate from ad hoc literal to canonical token.

A concept has **contract meaning** when any of the following are true:

- code branches on it
- tests assert it
- logs depend on it for diagnosis
- API responses expose it
- UI surfaces render or interpret it
- docs describe it as part of current behavior
- operators use it to distinguish healthy, degraded, failed, pending, or terminal states

Canonical tokens are the runtime and architecture analogue of UI tokens. UI tokens govern visual truth. Protocol and domain tokens govern semantic truth.

---

## 3. What counts as a token

In Codexify, a “token” is not limited to CSS variables. A token is any canonical symbolic value that represents a repeated and meaningful system concept.

### 3.1 UI tokens

Examples:

- spacing
- radii
- glass geometry
- color variables
- responsive layout values

These already follow a constitution model: AppShell-level declaration, token-only usage, and prohibition on arbitrary local hardcoding.

### 3.2 Protocol tokens

Examples:

- acceptance statuses
- runtime health states
- connection states
- event types
- machine-readable error codes

These define observable runtime truth surfaces, especially in the queue-coupled chat path and task-event flow.

### 3.3 Domain tokens

Examples:

- embedding lifecycle states
- document processing states
- release gate labels
- command bus run states
- supported-profile posture labels

These often originate in storage constraints, route behavior, or docs and must remain stable across layers. For example, uploaded documents already depend on constrained `embedding_status` values (`pending|processing|ready|failed`), which makes them an obvious token domain rather than a place for local string invention.

### 3.4 Function tokens

Examples:

- named workflow phases
- canonical operation identifiers
- reusable lifecycle step names
- execution-stage labels

These are useful when the same operation is implemented repeatedly by different agents or across separated work sessions and starts to pick up duplicate names, partial variants, or local aliases.

---

## 4. Canonical Token Rule

All repeated contract-bearing literals must come from a canonical token registry before they spread.

### 4.1 Required rule

Routes, workers, queues, stores, frontend components, and tests must not invent ad hoc literals inline for concepts that already have contract meaning.

If a needed token does not exist, the correct action is:

1. extend the canonical registry
2. document the meaning
3. update typed exports
4. migrate the consumer code
5. add or update tests

### 4.2 Disallowed pattern

- local strings that duplicate an existing token
- nearby synonyms with slightly different names
- one-off status values added for convenience
- log codes invented only in one file
- UI branching on literals not exported from a canonical module

### 4.3 Allowed pattern

- bounded canonical registries per domain
- explicit import of shared tokens
- narrow and typed exports
- documented semantics and scope
- temporary adapters only when migrating old contracts

This matches the existing UI constitution model, where local hardcoded values are forbidden and tokenized values are the only approved source of truth for rendering behavior.

---

## 5. Why bounded registries matter

Codexify should not use one giant enum swamp.

Token registries must stay bounded by semantic domain.

Recommended registry shapes:

- UI tokens
- protocol tokens
- event types
- error codes
- storage lifecycle states
- health/degradation states
- release/audit vocabulary
- workflow or function tokens

A bounded registry keeps meanings local and reduces accidental cross-domain coupling. This is especially important in Codexify because the runtime already has several distinct truth surfaces: queue acceptance, task-event transport, provider execution, ingestion lifecycle, and UI/operator interpretation.

---

## 6. Decision test: when should a literal become a token?

A literal should be promoted to a canonical token when **two or more** of the following are true:

- it appears in more than one file
- it appears in more than one layer (backend, frontend, tests, docs, logs)
- it distinguishes system state or lifecycle stage
- it would be dangerous to rename casually
- it is likely to be invented again by another agent
- it is used to explain operator truth or release readiness
- it is part of a constrained storage or API surface

### 6.1 Promote immediately

Promote immediately when the literal is:

- user-visible state
- API-visible state
- event name
- machine-readable error code
- storage lifecycle state
- release gate label
- health/degradation status

### 6.2 Leave local for now

A value may remain local if it is:

- truly file-private
- implementation-only
- not branched on elsewhere
- not surfaced in logs, docs, APIs, or UI
- unlikely to be reused

The standard is not “tokenize everything.” The standard is “tokenize repeated meaning.”

---

## 7. Semantic categories Codexify should protect

The following categories should be treated as token candidates by default.

### 7.1 State tokens

Examples:

- accepted
- accepted_degraded
- pending
- processing
- ready
- failed
- cancelled

These matter because current runtime docs already warn that acceptance, progress, event visibility, and completion are distinct truths, not interchangeable signals.

### 7.2 Event tokens

Examples:

- task.created
- task.completed
- task.failed
- task.cancelled

The completion pipeline explicitly relies on task-event publication as part of the worker-backed flow, even while warning that publication itself is not proof of downstream UI receipt.

### 7.3 Error-code tokens

Examples:

- queue enqueue failure
- task-event publish failure
- runtime degraded failure kinds

These are essential for diagnostics because Codexify’s current risks include queue coupling, runtime ambiguity, and degraded truth surfaces that need grep-friendly, stable observability labels.

### 7.4 Lifecycle tokens

Examples:

- embedding status
- upload processing state
- command run state
- sync posture state

These should not drift, because they often sit at the seam between storage invariants, route contracts, and UI interpretation.

### 7.5 Health tokens

Examples:

- healthy
- degraded
- disconnected
- stale
- unavailable

These are especially important in the packaged runtime because operator truth must reflect queue/worker/model dependency reality rather than just API uptime.

---

## 8. Design constraints

### 8.1 One canonical source per token domain

Every token domain must have exactly one canonical source of truth.

### 8.2 No ad hoc aliases without intent

Aliases are only allowed for backward compatibility or staged migration, and they must be documented as aliases rather than silent duplicates. The UI token constitution already preserves legacy pointer aliases explicitly, which is the right model: compatibility is allowed, hidden drift is not.

### 8.3 Semantics first, implementation second

A token should exist because the meaning is stable, not because a language feature makes it easy to define.

### 8.4 Human-readable, grep-friendly names

Tokens must optimize for:

- readability
- searchability
- low ambiguity
- low synonym pressure

### 8.5 Typed where practical

Canonical tokens should be exported in a typed form appropriate to the language and layer so they are harder to misuse.

### 8.6 Tests protect the registry

Every canonical registry should have focused contract tests that verify exact exported values and expected membership.

---

## 9. Change process

When adding a new canonical token:

1. Identify the domain.
2. Confirm the value carries contract meaning.
3. Add it to the domain registry.
4. Document its meaning and scope.
5. Migrate consumers off local literals.
6. Add or update contract tests.
7. Update docs if the token is externally meaningful.

For any new token, define:

- name
- domain
- meaning
- scope (`internal`, `api-visible`, `ui-visible`, `log-visible`, or multiple)
- allowed transitions if it is a lifecycle state
- backward-compatibility notes if relevant

---

## 10. Non-goals

This philosophy does **not** mean:

- tokenize every string in the repo
- collapse all domains into one mega-registry
- force package refactors just to create a registry
- replace local implementation details that do not carry contract meaning
- let architecture paperwork outrun runtime reality

Codexify already has enough coupling in its primary chat loop and config surfaces. Tokenization should reduce ambiguity, not create ceremony for its own sake.

---

## 11. Practical heuristics for agents

When an agent touches Codexify, it should ask:

1. Is this literal repeated or likely to repeat?
2. Does it carry state, protocol, lifecycle, or diagnostic meaning?
3. Would renaming it casually break understanding across layers?
4. Is there already a canonical token for it?
5. If not, should this task extend a bounded registry before adding more usage?

Preferred bias:

- extend an existing registry before inventing a new local literal
- create a new bounded registry before letting a domain sprawl
- keep migration scope small and atomic

---

## 12. The working motto

**Prefer canonical tokens over ad hoc literals in every domain that carries contract meaning.**

That is the governing rule.

UI tokens gave Codexify a visual spine.  
Protocol and domain tokens should give it a semantic spine.
