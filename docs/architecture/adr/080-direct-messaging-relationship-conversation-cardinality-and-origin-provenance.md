# ADR-080: Direct Messaging Relationship, Conversation Cardinality, and Origin Provenance

**Status:** Accepted

**Date:** 2026-08-31

## Context

ADR-079 established the Node-addressed profile identity and direct
messaging boundary with one canonical `direct_message_conversations` row
per unordered profile-address pair.  That one-pair-one-conversation
cardinality is too restrictive for the intended Codexify
social/workspace model: a peer pair needs one durable relationship that
may hold several distinct discussions, and the UI groundwork (Inbox and
person filtering) requires a person-centric projection before it can be
built.

This ADR refines ADR-079's conversation cardinality rule and adds two
bounded new concepts: immutable Conversation-origin provenance and
participant-local Project placement.  It deliberately does NOT implement
Project membership changes, Project invitations, Guardian retrieval,
ambient context injection, shared-context grants, agent authorship, or
federation.

## Decision

Codexify adopts the corrected conceptual hierarchy:

```text
Node_ID
  └── Profile_ID
        └── Relationship_ID
              └── Conversation_ID
                    └── Message_ID
```

One unordered addressed Profile pair has exactly one canonical
Relationship.  A Relationship may own zero or more Conversations.

The old rule — one unordered profile pair = one canonical Conversation —
is superseded.  Pair uniqueness, `participant_pair_key`, and the
accompanying unique constraint move from Conversation to Relationship.

### Relationship

A Relationship means: "These two addressed Profiles have a direct
messaging relationship."  It does NOT mean friendship, trust, Contact
membership, Circle membership, Project membership, context sharing,
Guardian authorization, or inference permission.  Relationship existence
implies no authority of any kind beyond "these two actors can hold
direct conversations with each other."

`direct_message_relationships` holds the canonical pair identity
(`participant_pair_key`, unique) plus timestamps.
`direct_message_relationship_participants` is the canonical membership
authority: exactly two `Node_ID + Profile_ID` participant rows for V1,
unique on `(relationship_id, profile_id)`.

Relationship membership replaces the former conversation-participant
rows as the authorization surface for every Conversation and Message.
No competing membership truth is maintained: the obsolete
`direct_message_conversation_participants` table is removed by the
migration after all backfills land.

### Conversation

A Conversation is one particular discussion inside a Relationship.
Conversation identity remains stable regardless of Project placement,
username changes, display-name changes, title changes, or context
changes.  Each explicit creation returns a new `Conversation_ID`;
Conversations never auto-merge.

### Conversation origin provenance

A Conversation may carry durable creation provenance:

```text
ConversationOrigin
├── created_by_profile_id
├── origin_project_id   nullable
├── origin_thread_id    nullable
└── created_at
```

Origin records where the Conversation was CREATED.  It is immutable
historical provenance after creation, except where existing Project/Thread
lifecycle doctrine nulls a stale source reference (`ON DELETE SET NULL` —
a deleted Project/Thread never cascades into the DM Conversation or its
Messages).  Moving a Conversation does not rewrite its origin.

Origin validation at creation time:

- `origin_project_id` must be accessible to the creating profile/account
  (existing Project ownership authority; nothing new is invented).
- `origin_thread_id` must be accessible to the creating profile/account.
- If both are supplied, the Thread must belong to the supplied Project;
  a mismatched pair is rejected.
- An origin reference grants the peer NO access to the source Project or
  Thread.
- Existing conversations migrated from ADR-079 receive NULL origin —
  historical creation provenance is unknown and is never fabricated.

### Participant-local placement

Project organization is participant-local:

```text
ConversationPlacement
├── conversation_id
├── profile_id
├── project_id  nullable
├── created_at
└── updated_at
```

`direct_message_conversation_placements` is unique on
`(conversation_id, profile_id)`.  Placement Profiles must participate in
the Conversation's Relationship.  One participant's placement never
alters another's; `project_id = null` means unscoped.

Creation defaults:

- From General: origin NULL, creator placement NULL unless the caller
  explicitly chooses a local placement.
- From Project: caller provides `origin_project_id`; creator placement
  defaults to that Project; recipient placement stays unscoped.
- From a Thread inside a Project: caller provides both; both are
  preserved as origin; creator placement defaults to the origin Project;
  recipient stays unscoped.

Moving placement (PATCH) validates Project authority for the caller and
modifies ONLY the caller's placement.  It never rewrites origin, never
touches the peer's placement, never changes Relationship membership,
never adds messages to a Project KB, and never triggers context
ingestion.

### The five-way distinction

These are different concepts and are kept separate:

```text
placement
  != origin
  != Project membership
  != retrieval permission
  != ambient context authority
  != disclosure authority
```

This slice implements only origin provenance, participant-local
placement, and normal direct-message visibility.  No retrieval policy,
no disclosure policy, and no context-grant state exist.  No premature
columns are added for those future concepts.

### Project/Thread authority

Origin validation reuses the existing Project/Thread ownership model
(`projects.user_id`, `chat_threads.user_id`).  A Conversation originating
from a Project must not silently grant the peer Project or Thread access;
peers do not see private Project/Thread identifiers or names merely
because origin provenance is stored.

### Future seams (documented, not implemented)

- A future Share Sheet / Project-origin UX may interpret "Conversation
  originated from Project X" as an opportunity to present an explicit
  Join Project / Accept Scope action.  That future action must call the
  canonical Project invitation/membership authority; it must not infer
  membership from message receipt.
- Future Guardian retrieval inside a Conversation may assemble context
  in a bounded order (Conversation → explicitly permitted origin Thread
  corpus → explicitly permitted Project KB → separately authorized
  sources).  Origin metadata makes that possible; it does NOT authorize
  it.  Retrieval should reference canonical sources
  (`origin_thread_id` → the existing indexed chat-message corpus) rather
  than copying the source transcript into a duplicated "DM KB".
- Retrieval scope (what Guardian may inspect) and disclosure scope (what
  Guardian may reveal into the Conversation) remain separate future
  authority surfaces.

### API evolution

- `POST /api/direct-messages/relationships` — resolve/create the
  canonical Relationship for an addressed peer pair (nonlocal Node_ID
  rejected as before; self-DM rejected; reverse direction resolves the
  same Relationship).
- `GET /api/direct-messages/relationships` — caller-participating
  Relationships with safe peer social identity.
- `GET /api/direct-messages/relationships/{relationship_id}/conversations`
  — every Conversation in one Relationship, stable activity ordering,
  caller-local placement and caller-visible origin only.  The peer's
  private placement is never revealed.
- `POST /api/direct-messages/relationships/{relationship_id}/conversations`
  — explicit Conversation creation with optional `origin_project_id`,
  `origin_thread_id`, and explicit creator-local placement override.
- `GET /api/direct-messages/conversations/{conversation_id}` — unchanged
  route; authorization now flows Conversation → Relationship →
  RelationshipParticipant; response adds caller-visible origin and
  caller-local placement.
- `GET/POST /api/direct-messages/conversations/{conversation_id}/messages`
  — unchanged; durability and idempotency preserved.
- `PATCH /api/direct-messages/conversations/{conversation_id}/placement`
  — caller-local placement move with `project_id | null`.
- The legacy `POST /api/direct-messages/conversations` pair-resolve
  endpoint is removed; there are no genuine runtime consumers outside
  the DM seam.  `GET /api/direct-messages/conversations` (the global
  participant-scoped list) is retained.

## Migration

One forward migration (`b2c8d0e3f5a7`, chained to `a1b7c9d2e4f6`):

1. creates `direct_message_relationships` with unique
   `participant_pair_key`;
2. backfills one Relationship per distinct existing conversation pair
   key with two canonical participant rows;
3. adds `relationship_id` to Conversations and backfills it;
4. preserves every existing Conversation ID and Message ID/payload/
   timestamp/idempotency key;
5. adds immutable origin columns (NULL backfill — unknown, never
   fabricated);
6. creates participant-local placements backfilled as unscoped (NULL
   Project) for every existing member;
7. removes the obsolete conversation-participant authority table only
   after all backfills;
8. downgrade restores the ADR-079 one-pair-one-conversation shape with
   pair-key, participant-row, and conversation/message data intact.

## Consequences

- Positive: person-centric projection substrate exists ("all
  Conversations with Profile X" = one Relationship listing).
- Positive: existing DM history survives the migration untouched; origin
  remains honestly unknown for it.
- Positive: conversation identity is decoupled from Project organization,
  so Share Sheet-style UX has a stable anchor.
- Negative: no Project invitation flow, no retrieval/disclosure policy,
  no realtime delivery, no Inbox UI in this slice.
- Negative: `uq_direct_message_conversations_participant_pair_key` and
  the one-pair-one-conversation service resolution are gone; a future
  relationship-scoped design change must migrate the Relationship layer
  deliberately rather than dropping uniqueness.

## Governing and related ADRs / contracts

- Refines [[079-node-addressed-profile-identity-and-direct-messaging-boundary|ADR-079]]:
  Node_ID, Profile_ID, username non-authority, email privacy, transport
  neutrality, Postgres authority, same-node-first, no Guardian execution,
  no implicit retrieval/memory, and federation deferral remain in force.
- [[../00-current-state|00 Current State]] remains release truth.
- [[../direct-messaging-contract|Direct Messaging Contract]] — normative
  contract companion, updated for the Relationship hierarchy.
- [[../data-and-storage|Data and Storage]] — persistence invariants for
  the new tables.
- [[../contacts-circles-and-collaboration-identity|Contacts, Circles, and
  Collaboration Identity Contract]] — Relationship is deliberately NOT a
  Contact/friendship semantic.
- [[053-node-hosted-room-access-boundary|ADR-053]] and
  [[055-threadspace-whispermesh-managed-service-boundary|ADR-055]] —
  unchanged boundaries; DMs remain outside Hosted Rooms and federation.
