---

tags:

* architecture
* adr
* identity
* runtime-mode
* export
  aliases:
* ADR-005
* Runtime Mode and Account Boundary Invariants

---

# ADR-005: Runtime Mode and Account Boundary Invariants

## Status

Accepted

## Date

2026-04-19

## Context

Codexify currently runs in an implicit single-user posture, but the architecture now needs a hard boundary contract before multi-user auth, session handling, and user-scoped retrieval are added.

The system already carries `user_id` in schema and related runtime surfaces, and the account export and restore contract requires ownership, provenance, and relationship preservation. Without an explicit runtime-mode decision, future auth work could accidentally widen access, switch semantics on a live database, or make exportability depend on global reconstruction.

## Decision

Codexify defines two runtime modes:

* `single_user`
  * identity is implicit
  * system behaves as if all data belongs to one user
  * no auth required
  * retrieval does not require user filtering
* `multi_user`
  * identity is explicit and required
  * every request must resolve a `user_id`
  * all data access must be scoped by `user_id`
  * retrieval must enforce user isolation

Runtime mode is selected at bootstrap only.

Codexify must not switch runtime mode on a live database.

The transition from `single_user` to `multi_user` requires an explicit bootstrap or migration step.

The transition from `multi_user` to `single_user` is not supported.

An AccountBoundary is the complete set of data owned by a single user.

It includes projects, chat threads, chat messages, documents and media, private personas, and memory entries.

It excludes global personas, which are shared templates.

Global personas are visible to all users, read-only, clonable, and must not contain user-specific memory or state.

## Rationale

This decision makes identity an explicit runtime property rather than an emergent side effect of request routing or data lookup.

That matters because:

* export and restore must remain possible without querying other users
* retrieval must not cross user boundaries in multi-user mode
* context assembly must stay user-scoped
* ownership must not be inferred implicitly once multi-user mode exists
* bootstrap behavior for existing data must be deterministic and one-time

The contract also preserves the current single-user posture without forcing an auth implementation prematurely.

## Alternatives considered

### 1. Infer runtime mode dynamically from the database

Rejected.

That would make semantics mutable on a live database and blur the boundary between bootstrap and steady state.

### 2. Let auth and retrieval decide ownership independently

Rejected.

That splits the source of truth and makes user isolation easier to violate.

### 3. Explicit bootstrap-time runtime modes with account-boundary invariants

Chosen.

This keeps the decision central, auditable, and enforceable.

## Consequences

### Positive

* future auth work has a stable contract to enforce
* retrieval can apply a hard user filter in multi-user mode
* export and restore can be designed around a complete account boundary
* shared templates remain distinct from private user-owned data
* bootstrap semantics for seed data are explicit

### Negative

* more contract vocabulary to maintain
* bootstrap and migration code must honor the mode boundary
* every future persistence or retrieval change must account for account scope

## Invariants created by this decision

* `single_user` and `multi_user` are the only supported runtime modes
* runtime mode is selected at bootstrap
* runtime mode must not be switched on a live database
* `multi_user` mode requires explicit `user_id` resolution on every request
* retrieval must enforce user isolation in `multi_user` mode
* AccountBoundary export must be possible without querying other users
* restore must rehydrate an account as an independent system
* global personas remain shared, read-only templates and may not carry user-specific state

## Links

* [[identity-and-runtime-mode|Identity and Runtime Mode]]
* [[account-export-restore-contract|Account Export + Restore Contract]]
* [[00-current-state]]
* [[data-and-storage|Data and Storage]]

## Notes

This ADR is the pre-auth guardrail for future identity, session, retrieval, project scoping, and persona-visibility work.

Any future change that would relax these invariants should be documented as a new ADR instead of mutating this one in place.
