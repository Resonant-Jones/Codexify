## Purpose

Codexify now supports two runtime modes:

- `single_user` (implicit identity)
- `multi_user` (explicit identity)

This document defines the invariants that govern identity, isolation, and exportability.

## Runtime Modes

### single_user

- identity is implicit
- system behaves as if all data belongs to one user
- no auth required
- retrieval does not require user filtering

### multi_user

- identity is explicit and required
- every request must resolve a `user_id`
- all data access must be scoped by `user_id`
- retrieval MUST enforce user isolation

## Mode Selection Rule

- Runtime mode MUST be selected at bootstrap
- Runtime mode MUST NOT be switched on a live database
- Transition from `single_user` to `multi_user` requires explicit bootstrap or migration step
- Transition from `multi_user` to `single_user` is NOT supported

## Account Boundary (NEW CORE CONCEPT)

An AccountBoundary is the complete set of data owned by a single user.

It includes:

- projects
- chat_threads
- chat_messages
- documents and media
- personas (private)
- memory entries

It excludes:

- global personas (shared templates)

## Account Isolation Invariants (CRITICAL)

1. Every entity MUST belong to exactly one `user_id` in `multi_user` mode
2. No entity may depend on another user’s private data
3. Retrieval MUST NOT cross user boundaries
4. Context assembly MUST be user-scoped
5. System MUST NOT infer ownership implicitly in `multi_user` mode

## Shared Entities

Global personas are:

- visible to all users
- read-only
- clonable
- MUST NOT contain user-specific memory or state

## Exportability Invariants (CRITICAL)

Based on the account-export-restore contract:

1. A user's AccountBoundary MUST be exportable without querying other users
2. Export MUST preserve:
   - ownership
   - relationships
   - provenance
3. Export MUST NOT require global reconstruction to be valid
4. Restore MUST rehydrate the account as an independent system

## Bootstrap Behavior (Seed Mode)

When `multi_user` mode is first enabled:

- existing data MAY be treated as seed data
- system MUST assign all existing records to a default user
- no backward-compatible migration is required
- this is a one-time bootstrap operation

## Retrieval Enforcement Requirement

The retrieval layer (`ContextBroker`, `MemoryOS`, vector store) MUST accept and enforce `user_id` as a hard filter.

Failure to enforce this breaks multi-tenant safety.

Future auth, session handling, retrieval changes, project scoping, and persona visibility work must reference this document first.
