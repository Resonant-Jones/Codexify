# ADR-079: Node-Addressed Profile Identity and Direct Messaging Boundary

**Status:** Accepted

**Date:** 2026-08-31

## Context

Codexify needs a first-class private messaging substrate between human
profiles.  The first implementation is intentionally same-node, but its
persisted identity and message contracts must not assume that all
participants will always live on the same node.  This ADR establishes the
social identity/addressing hierarchy, the durable same-node human-to-human
plain-text messaging domain, and the private account boundary around both.

This ADR does not implement federation, cross-node delivery, node
discovery, Guardian messaging, attachments, or a frontend Inbox, and it
does not widen the supported Beta release promise.

## Decision

Codexify adopts the canonical conceptual hierarchy:

```text
Node_ID
  └── Profile_ID
        └── Conversation_ID
              └── Message_ID
```

The protocol-level social address is the composition `Node_ID + Profile_ID`.
For V1 both participants share one local Node_ID; the schema and contract
nevertheless preserve the Node_ID boundary so a future transport adapter
can handle `source_node_id != destination_node_id` without redefining
message identity, profile identity, conversation semantics, or
authorization.

### Address hierarchy

The four levels are distinct and must not be collapsed:

- `Node_ID` identifies the Codexify node authority hosting/addressing a profile.
- `Profile_ID` identifies the durable social actor within that authority.
- `Conversation_ID` identifies one canonical private conversation.
- `Message_ID` identifies one durable message.

### Node identity

`Node_ID` identifies a Codexify node authority.  It is NOT an IP address,
hostname, domain name, URL, WebSocket ID, Docker/container identity,
deployment name, account ID, or profile ID.  Network endpoints are
routing/location information associated with a node, not the node's
durable identity.

Canonical Node_ID storage reuses the existing ThreadSpace node-membership
foundation: the `threadspace_nodes` table
(`node_id` primary key, migration `d6f7a8b9c0d1`).  A bounded local-node
resolver in `guardian/messaging/service.py` ensures one stable canonical
local node row, created on first use and persisted in Postgres, so the
local Node_ID is stable across backend restarts without deriving from
hostname, IP, endpoint, or container identity.

Out of scope for this decision: remote-node registry, DNS discovery, node
directory, endpoint discovery, key exchange, remote trust negotiation,
remote node authentication, node migration, node key rotation, and relay
infrastructure.  Those belong to federation tasks.

### Profile identity

`Profile_ID` identifies the durable social actor within a node authority.
It is NOT `user_id`, email, username, display name, avatar, a Persona
Studio persona ID, or a current network endpoint.

Canonical Profile_ID reuses and extends the existing person-facing
profile: `user_profiles` gains `profile_id` (a durable random social
token minted once per row), `node_id` (anchor to the host node),
`username`, and `username_state`.  Presentation fields (`display_name`,
`avatar_url`) remain mutable and never participate in addressing.

### Absolute social address

The protocol-level social address is `Node_ID + Profile_ID`.  Durable
social addressing is based on this pair only.  For V1,
`source.node_id == destination.node_id == local_node_id`.  The schema and
contract preserve the Node_ID boundary throughout.

### Human-facing alias

`username` is a deliberate human-facing discovery alias.  It is:

- unique within its owning Node_ID namespace;
- case-insensitively unique (the stored form is the lowercase canonical form);
- mutable under future policy;
- safe to expose socially.

It is NOT durable authorization authority.  Changing a username must not
invalidate existing conversations or messages because those records bind
to `Profile_ID`, not username.

V1 grammar: lowercase ASCII letters, digits, underscore, hyphen;
3–32 characters; must start and end with a letter or digit; reserved
system names rejected.  No Unicode username normalization is introduced.
No username history, aliases, rename cooldowns, verification badges, or
federation-wide uniqueness exists in this slice.

Existing users without usernames remain `unset`/unconfigured until they
deliberately choose one.  A username is never silently generated from the
email local-part.

### Private account boundary

The following remain private account/internal identity state:

- `user_id`
- authentication email
- credentials
- account-recovery information
- provider credentials
- IDDB/private identity state
- private Guardian/persona configuration
- memory
- unrelated projects/threads/documents/media

Email must never be required for social discovery, must never appear in
peer-facing DM payloads, and must never be used as a social handle,
conversation identity, sender identity, participant identity, or remote
address.

### Direct messaging domain

Direct messaging is a first-class communication domain.  It is NOT a
Hosted Room alias, ordinary Guardian chat, Persona Studio state, a
project thread, federation transport, or a collaboration-room alias.

Dedicated durable entities exist for it:

- `direct_message_conversations` — one canonical conversation per
  unordered participant-address pair, enforced database-side by a unique
  `participant_pair_key`;
- `direct_message_conversation_participants` — explicit
  `Node_ID + Profile_ID` participant records;
- `direct_messages` — plain-text messages with sender address, canonical
  content type, timestamp, and optional client idempotency key.

V1 is exactly two human social profiles per conversation, same-node only.

> **Refined by ADR-080.** The one-pair-one-conversation cardinality
> described above was superseded by
> [[080-direct-messaging-relationship-conversation-cardinality-and-origin-provenance|ADR-080]]:
> one unordered addressed Profile pair now yields one canonical
> Relationship which may own zero or more Conversations.  Pair uniqueness
> moved from Conversation to Relationship; Relationship membership is the
> canonical participant authority; and ADR-080 added durable
> Conversation-origin provenance plus participant-local Project placement.
> Everything else in this ADR remains in force: Node_ID, Profile_ID,
> username non-authority, email privacy, transport neutrality, Postgres
> authority, same-node-first implementation, no Guardian execution, no
> implicit retrieval/memory, and federation deferral.

### Persistence

Postgres owns durable conversation/message truth.  Transport, WebSocket
delivery, realtime notification, federation relay, and frontend state do
not own message truth.  An HTTP success for send means the message is
durably persisted.

### Federation compatibility

Future cross-node transport MUST preserve:

```text
source_node_id
source_profile_id

destination_node_id
destination_profile_id
```

Transport may change.  Address semantics may not silently change with it.
Future transport additions (endpoints, signatures, relay metadata,
receipts) MUST NOT redefine `Message_ID`, `Conversation_ID`, `Profile_ID`,
`Node_ID`, participant authority, or message authorship.

### Guardian boundary

Receiving a human message must not trigger model inference.  Guardian
participation remains explicitly deferred.

### Context boundary

Private messages do not implicitly enter Guardian retrieval, memory,
project context, embeddings, IDDB, identity inference, or document
context.

## Current-truth anchors

True now:

- Codexify has authenticated account boundaries; every authenticated
  account has a canonical internal `user_id`.
- Postgres is authoritative durable application state.
- Hosted multi-user infrastructure exists.
- Hosted Room/collaboration machinery provides adjacent
  participant/authentication patterns.
- ThreadSpace doctrine distinguishes account, profile, message,
  invocation, execution-attempt, and agent identities.
- Collaboration/federation access is explicit rather than ambient.

Implemented by this decision and test-proven:

- stable local social addressing at `Node_ID + Profile_ID`;
- deliberate Node-scoped usernames;
- peer-facing DM discovery that never exposes account email;
- same-node plain-text direct-message persistence with idempotent
  retries;
- participant-scoped listing/readback authorization;
- nonlocal destinations rejected as unsupported without federation.

Not proven / deferred:

- cross-node private messaging;
- node discovery/resolution for this messaging protocol;
- Guardian-to-human, human-to-Guardian, or Guardian-to-Guardian
  messaging;
- passive inference routing;
- DM attachments;
- Inbox frontend.

## Unresolved federation contract questions

These must not block today's same-node implementation; they are
intentionally separated from the stable addressing invariant
`Node_ID + Profile_ID`:

1. How does another node resolve a Node_ID to current network endpoint(s)?
2. Who/what establishes Node_ID provenance?
3. How does a remote node prove possession/control of its Node_ID?
4. How are node signing keys represented and rotated?
5. Can a Node_ID advertise multiple endpoints/transports?
6. How are unavailable nodes represented?
7. How does profile migration between nodes preserve identity continuity,
   if supported?
8. How are username + node aliases presented to humans across nodes?
9. What trust/policy gate exists before accepting remote messages?
10. What transport adapters are supported?

## Consequences

- Positive: a durable, privacy-bounded social addressing substrate and
  direct-messaging domain exist under the existing account authority, with
  no Guardian execution, no retrieval, and no federation coupling.
- Positive: conversation identity is stable across username renames and
  presentation changes.
- Negative: same-node only; cross-node delivery remains unproven and must
  not be claimed.
- Negative: no realtime delivery, no Inbox UI, no attachments in this
  slice.

## Governing and related ADRs / contracts

- [[../00-current-state|00 Current State]] remains release truth.
- [[053-node-hosted-room-access-boundary|ADR-053 Node-Hosted Room Access
  Boundary]] — adjacent participant/authentication doctrine; DMs are not
  Hosted Rooms.
- [[055-threadspace-whispermesh-managed-service-boundary|ADR-055
  ThreadSpace ↔ WhisperMesh Managed-Service Boundary]] — sovereignty
  boundary preserved.
- [[043-contact-and-circle-storage-model|ADR-043 Contact and Circle
  Storage Model]] and [[../contacts-circles-and-collaboration-identity|
  Contacts, Circles, and Collaboration Identity Contract]] — identity
  vocabulary precedent.
- [[../collab-chat-identity-contract|Collab Chat Identity Contract]] —
  participant authority precedent; DMs are not collab threads.
- [[../data-and-storage|Data and Storage]] — persistence invariants.
- [[../account-export-restore-contract|Account Export Restore Contract]] —
  private account state remains private.
- [[../direct-messaging-contract|Direct Messaging Contract]] — normative
  contract companion.
