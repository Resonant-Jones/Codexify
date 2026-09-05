# Chat Runtime State Contract

This file records durable thread profile bindings and retains the lifecycle
compatibility pointer after the merge with `main`.

The normative lifecycle document is `docs/architecture/chat-runtime-contract.md`.

Use that file for:
- canonical provider runtime states
- canonical request lifecycle states
- canonical transport visibility states
- message-versus-attempt identity
- UI status presentation rules
- replay and transition semantics

These lifecycle definitions remain in the canonical contract.

## Durable Persona Profile selection

Under [ADR-082](./adr/082-persona-profile-manifest-and-binding-authority.md),
`chat_threads.active_profile_id` and nullable positive
`active_profile_revision` form one atomic thread binding. The canonical
thread `user_id` anchors account authority; server-owned Persona bindings,
not metadata or manifest text, determine which revisions it can select.

Selecting a persisted Persona by ID pins its server-derived current immutable
revision. Editing that Persona appends a revision without changing existing
thread pins. Explicitly selecting the same ID again advances the pin to the
then-current revision. Ordinary switch requests cannot submit a revision.

Runtime reads the exact account-owned revision and projects only name, system
prompt, provider, model, and temperature. It never substitutes current/latest.
Missing, invalid, foreign-account, or revisionless persisted selections fail
with `system_profile_resolution_unavailable`; completion stops before provider
inference. The pin remains durable. Profile-state output exposes the ID,
revision, and resolution source, including an explicit unavailable result.
Revision provenance is not injected into authored system-prompt text.

Built-in/env profiles and thread-local flow overrides remain revisionless.
Activating one clears any previous revision pin. A non-null Persona pin is
resolved independently of colliding override metadata. A nullable composite
foreign key references `persona_profile_revisions(profile_id, revision)`;
CHECK constraints require a positive revision and a non-null ID when pinned.
No profile deletion API, cascade, or automatic pin clearing is introduced.

Migration pins only account-matched, bound profiles with a valid current
immutable revision; ambiguous/unbound/foreign/override state remains NULL.
This establishes determinism from migration time forward and cannot reconstruct
the historical revision originally selected before pins existed.

This is thread-state reproducibility. Per-request/per-attempt snapshotting is
deferred: a switch after acceptance but before worker resolution can still
change the revision used by that accepted completion. No release claim widens.
