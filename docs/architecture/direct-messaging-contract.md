# Direct Messaging Contract

> Classification: architecture contract / implemented same-node boundary
> Status: implemented for same-node V1; federation transport deferred
> Normative language: "must", "must not", "may", "should", "non-goal", and "invariant" are intentional contract terms.
> Governing ADRs: [ADR-077](./adr/077-node-addressed-profile-identity-and-direct-messaging-boundary.md) (identity/addressing), [ADR-078](./adr/078-direct-messaging-relationship-conversation-cardinality-and-origin-provenance.md) (Relationship cardinality, origin, placement)

## Purpose

Define the normative addressing, privacy, persistence, authorization, and
transport-neutrality boundary for node-addressed profile-to-profile
private messaging.  V1 implements the complete same-node path; the
contract is written so a future transport adapter can handle cross-node
delivery without redefining message identity, profile identity,
conversation semantics, or authorization.

Last updated: 2026-08-31

## 1. Address hierarchy

```text
Node_ID
  └── Profile_ID
        └── Relationship_ID
              └── Conversation_ID
                    └── Message_ID
```

The protocol-level social address is `Node_ID + Profile_ID`.  In V1 both
participants share one local Node_ID.

One unordered addressed Profile pair has exactly one canonical
Relationship; that Relationship may own zero or more Conversations
(ADR-078 refines ADR-077's one-pair-one-conversation rule).

### Node identity

`Node_ID` identifies a Codexify node authority.  It is NOT an IP address,
hostname, domain name, URL, WebSocket ID, Docker/container identity,
deployment name, account ID, or profile ID.  Endpoints are
routing/location information, not durable identity.

The local node has exactly one stable canonical Node_ID, persisted in
`threadspace_nodes` (migration `d6f7a8b9c0d1`).  The bounded local-node
resolver creates it on first use; the identity is Postgres-durable and
stable across restarts.

### Profile identity

`Profile_ID` identifies the durable social actor within a node authority.
It is NOT `user_id`, email, username, display name, avatar, a Persona
Studio persona ID, or a network endpoint.

`profile_id` is minted once per canonical `user_profiles` row
(migration `a1b7c9d2e4f6`) and never changes.  Presentation changes and
username renames must not alter `profile_id`.

## 2. Username

A deliberate human-facing discovery alias:

- unique within its owning Node_ID namespace;
- case-insensitively unique — the stored value is the lowercase canonical
  form, so normalization is construction, not comparison;
- mutable under future policy;
- safe to expose socially;
- never durable authorization authority.

Grammar (V1): 3–32 characters of lowercase ASCII letters, digits,
underscore, and hyphen; must start and end with a letter or digit;
reserved system names rejected; no Unicode normalization.

State: `unset` (no deliberate selection) or `active` (claimed).  Existing
users remain `unset` until they deliberately choose a username.  Username
is never derived from the email local-part.

## 3. Private account boundary

Email is private account metadata.  No social API may expose another
user's email.  Email must not appear in username search responses,
participant payloads, message payloads, conversation responses, public
social profile payloads, transport-neutral envelopes, peer-facing error
messages, or peer-visible audit payloads.

Email must not serve as social handle, conversation identity, sender
identity, participant identity, or remote address.  Authentication may
continue to use email internally per account doctrine.

The following never cross the profile boundary: `user_id`, credentials,
recovery information, provider credentials, IDDB/private identity state,
private Guardian/persona configuration, memory, unrelated
projects/threads/documents/media.

## 4. Persistence domain

Dedicated durable entities; not Guardian `chat_threads`, not Hosted
Rooms, not project threads.

| Entity | Purpose | Key invariants |
|---|---|---|
| `direct_message_relationships` | one canonical Relationship per unordered participant-address pair | unique `participant_pair_key` enforced database-side; `created_at`/`updated_at` |
| `direct_message_relationship_participants` | canonical membership authority (exactly two `Node_ID + Profile_ID` rows for V1) | unique `(relationship_id, profile_id)`; no roles, groups, mute, read state, or delivery state |
| `direct_message_conversations` | one discussion inside a Relationship | `relationship_id` required FK (cascade); `kind` is `direct`; immutable origin provenance `created_by_profile_id` / `origin_project_id` / `origin_thread_id` (nullable, `SET NULL` on source deletion); `latest_activity_at` tracks durable activity; multiple Conversations per Relationship |
| `direct_message_conversation_placements` | participant-local Project organization | unique `(conversation_id, profile_id)`; `project_id` nullable (`SET NULL` on source deletion); placement Profile must be a Relationship participant |
| `direct_messages` | durable plain-text messages | stable `id`; `conversation_id`; `sender_node_id` + `sender_profile_id`; `content_type` is `text/plain`; non-blank bounded body; unique `(conversation_id, sender_profile_id, client_message_key)` for idempotency |

Conversation identity must not depend on username, display name, email,
Project placement, origin provenance, or current endpoint.

### Conversation origin vs placement

Conversation origin records where the Conversation was CREATED; it is
immutable after creation except where existing Project/Thread lifecycle
doctrine nulls a stale source reference.  Placement records where each
participant currently ORGANIZES it and is participant-local.

The five-way distinction is normative:

```text
placement
  != origin
  != Project membership
  != retrieval permission
  != ambient context authority
  != disclosure authority
```

This slice implements origin provenance and placement only.  Origin
does not grant the peer Project or Thread access; placement does not
grant Project membership or retrieval authority; no source transcript is
copied and no DM embedding/KB is created.  Future retrieval and future
disclosure authority remain separate concepts with no state today.

Postgres owns durable conversation/message truth.  Transport, WebSocket
delivery, realtime notification, federation relay, and frontend state do
not own message truth.  HTTP success for send means durable persistence.

## 5. Transport-neutral envelope

Logical shape:

```json
{
  "protocol_version": "1.0",
  "message_id": "<stable id>",
  "conversation_id": "<stable id>",
  "source": {"node_id": "<Node_ID>", "profile_id": "<Profile_ID>"},
  "destination": {"node_id": "<Node_ID>", "profile_id": "<Profile_ID>"},
  "content": {"type": "text/plain", "body": "<plaintext>"},
  "created_at": "<timestamp>"
}
```

V1: `source.node_id == destination.node_id == local_node_id`; no remote
network call occurs.

Future transport adapters may add source/destination endpoints,
signatures, node public-key references, relay metadata, session metadata,
delivery receipts, and transport metadata.  Those additions MUST NOT
redefine `Message_ID`, `Conversation_ID`, `Profile_ID`, `Node_ID`,
participant authority, or message authorship.

## 6. HTTP surface

All endpoints use the existing authenticated current-user scope; the
caller may act only through a profile they own.

| Operation | Route | Notes |
|---|---|---|
| Claim username | `PUT /api/profile/social-identity` | normalize → grammar/reserved validation → Node-scoped uniqueness → persist `active`; never derived from email |
| Own social identity | `GET /api/profile/social-identity` | caller's `node_id`, `profile_id`, `username`, `username_state`, presentation fields |
| Discover profiles | `GET /api/direct-messages/profiles?q=` | authenticated, username-prefix, bounded (max 20), social fields only |
| Resolve relationship | `POST /api/direct-messages/relationships` | `destination_node_id` + `destination_profile_id`; nonlocal Node_ID rejected as unsupported (no federation); self-DM rejected; reverse direction resolves the same Relationship; no Conversation is required to establish a Relationship |
| List relationships | `GET /api/direct-messages/relationships` | caller-participating Relationships, safe peer social identity, ordered by durable `updated_at` |
| List relationship conversations | `GET /api/direct-messages/relationships/{relationship_id}/conversations` | participants only; every Conversation in the Relationship; stable activity ordering; caller-local placement and caller-visible origin only (peer's private placement never revealed) |
| Create conversation | `POST /api/direct-messages/relationships/{relationship_id}/conversations` | optional `origin_project_id` / `origin_thread_id` / explicit creator-local `project_id` override; origin validated against existing Project/Thread authority; creator placement defaults to origin Project; recipient placement unscoped; each creation returns a NEW Conversation_ID |
| List conversations | `GET /api/direct-messages/conversations` | participant-scoped global list, ordered by durable activity |
| Read conversation | `GET /api/direct-messages/conversations/{conversation_id}` | participants only (Conversation → Relationship → RelationshipParticipant); response includes caller-visible origin and caller-local placement |
| Read messages | `GET /api/direct-messages/conversations/{conversation_id}/messages` | deterministic `(created_at, id)` ascending, bounded pagination via `before_id` |
| Send message | `POST /api/direct-messages/conversations/{conversation_id}/messages` | `body` + optional `client_message_key`; synchronous persistence; idempotent replay returns the original message |
| Move placement | `PATCH /api/direct-messages/conversations/{conversation_id}/placement` | `project_id` or `null`; caller-local only; validates Project authority; never rewrites origin, peer placement, or Relationship membership |

The legacy `POST /api/direct-messages/conversations` one-pair-one-conversation
resolve endpoint is removed (no runtime consumers outside the DM seam);
pair resolution is Relationship-first.

Clients that discovered a profile by username MUST address relationships
using the returned `Node_ID + Profile_ID`; username is never addressing
authority.

## 7. Authorization invariants

- `user_id` remains canonical private account ownership identity.
- Authentication authority remains
  `authenticated user_id -> authorized/owned Profile_ID`.
- Sender authority is derived from the authenticated user's owned profile
  only; caller-supplied sender identity is never trusted.
- Relationship membership is the canonical participant authority:
  Conversation and Message authorization flows
  `Conversation → Relationship → RelationshipParticipant`.  No competing
  membership truth exists.
- A relationship or conversation may be read only by its participants;
  nonparticipant reads receive `relationship_not_found` /
  `conversation_not_found` (no existence leak).
- A conversation may be created only by a Relationship participant;
  every explicit creation returns a new Conversation_ID.
- A message may be created only by an authorized participant.
- Origin references may point only at Projects/Threads accessible to the
  creating profile; supplying an origin grants the peer nothing.
- Placement is participant-local; moving placement validates the
  caller's Project authority and touches only the caller's row.
- Foreign profile impersonation is denied.
- Self-DM is rejected.
- Nonlocal destinations are rejected as unsupported; no federation
  request is attempted.
- No prompt logic makes authorization decisions.

## 8. Isolation invariants

- Message receipt performs no model inference.
- No ChatCompletionTask, provider call, embedding job, memory mutation,
  ordinary Guardian chat thread, Hosted Room row, federation request,
  Project KB mutation, or Project membership change is created as a side
  effect of any DM operation — including Project/Thread-origin
  Conversation creation and placement moves.
- No source Project/Thread transcript is copied into the DM domain and
  no DM embedding is created from an origin source.
- Private messages do not automatically become Guardian/project/retrieval
  context.
- Origin provenance and placement are metadata only; they confer no
  retrieval, disclosure, or ambient-context authority.

## 9. Route posture

Registered under the `direct_messages` route label.  Enabled only on the
hosted/private test profile (`v1-friends-family-web`); every other
supported profile leaves the label unlisted and route governance treats
it as quarantined.  Federation and general collaboration routes remain
quarantined.

## 10. Deferred (explicitly not implemented)

Frontend Inbox; Share Sheet UI; person-filter UI; Conversation summary
modals; Project invitation acceptance / Project Scope Offers; shared
Project context grants; Guardian Conversation retrieval; Guardian
origin-Thread/Project retrieval; retrieval-scope vs disclosure-scope
policy; ambient DM context; realtime delivery (WebSocket/SSE);
attachments; cross-node transport; node discovery/resolution; endpoint
negotiation; node trust handshake; signatures and key rotation;
node/profile migration; global username uniqueness; username history;
verification badges; group messaging; reactions; read receipts; presence;
blocking/muting; Guardian messaging (all directions); agent/Guardian
authorship; autonomous replies; inference budgets; notification
delivery; memory/retrieval ingestion; IDDB mutation;
Beta/release-claim expansion.

## 11. Unresolved federation contract questions

Recorded in ADR-077; they must not block the same-node implementation:

1. How does another node resolve a Node_ID to current network endpoint(s)?
2. Who/what establishes Node_ID provenance?
3. How does a remote node prove possession/control of its Node_ID?
4. How are node signing keys represented and rotated?
5. Can a Node_ID advertise multiple endpoints/transports?
6. How are unavailable nodes represented?
7. How does profile migration between nodes preserve identity continuity?
8. How are username + node aliases presented to humans across nodes?
9. What trust/policy gate exists before accepting remote messages?
10. What transport adapters are supported?

## 12. Future dependency order

1. Inbox/global Conversation projection and person filter
2. Share Sheet / Project-origin interaction UX
3. explicit Project Scope Offer / invitation contract
4. provisional Conversation "summary so far" modal + export
5. explicit Guardian Conversation navigation/retrieval contract
6. origin Thread/Project retrieval binding
7. retrieval-scope vs disclosure-scope policy
8. realtime same-node delivery
9. attachments
10. agent/human message authorship and delegated-send authority
11. remote Node_ID resolution/trust
12. cross-node transport
13. delivery receipts
14. Cognitive QoS / autonomous Guardian communication
