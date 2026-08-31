# Direct Messaging Contract

> Classification: architecture contract / implemented same-node boundary
> Status: implemented for same-node V1; federation transport deferred
> Normative language: "must", "must not", "may", "should", "non-goal", and "invariant" are intentional contract terms.
> Governing ADR: [ADR-077](./adr/077-node-addressed-profile-identity-and-direct-messaging-boundary.md)

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
        └── Conversation_ID
              └── Message_ID
```

The protocol-level social address is `Node_ID + Profile_ID`.  In V1 both
participants share one local Node_ID.

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
| `direct_message_conversations` | one canonical conversation per unordered participant-address pair | unique `participant_pair_key` enforced database-side; kind is `direct`; `latest_activity_at` tracks durable activity |
| `direct_message_conversation_participants` | explicit participant social addresses | one row per `Node_ID + Profile_ID`; unique per conversation/profile; no roles, groups, mute, read state, or delivery state |
| `direct_messages` | durable plain-text messages | stable `id`; `conversation_id`; `sender_node_id` + `sender_profile_id`; `content_type` is `text/plain`; non-blank bounded body; unique `(conversation_id, sender_profile_id, client_message_key)` for idempotency |

Conversation identity must not depend on username, display name, email,
or current endpoint.

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
| Resolve conversation | `POST /api/direct-messages/conversations` | `destination_node_id` + `destination_profile_id`; nonlocal Node_ID rejected as unsupported (no federation); self-DM rejected; canonical one-to-one resolution |
| List conversations | `GET /api/direct-messages/conversations` | participant-scoped, ordered by durable activity |
| Read conversation | `GET /api/direct-messages/conversations/{conversation_id}` | participants only |
| Read messages | `GET /api/direct-messages/conversations/{conversation_id}/messages` | deterministic `(created_at, id)` ascending, bounded pagination via `before_id` |
| Send message | `POST /api/direct-messages/conversations/{conversation_id}/messages` | `body` + optional `client_message_key`; synchronous persistence; idempotent replay returns the original message |

Clients that discovered a profile by username MUST address conversations
using the returned `Node_ID + Profile_ID`; username is never addressing
authority.

## 7. Authorization invariants

- `user_id` remains canonical private account ownership identity.
- Authentication authority remains
  `authenticated user_id -> authorized/owned Profile_ID`.
- Sender authority is derived from the authenticated user's owned profile
  only; caller-supplied sender identity is never trusted.
- A conversation may be read only by its participants; nonparticipant
  reads receive `conversation_not_found` (no existence leak).
- A message may be created only by an authorized participant.
- Foreign profile impersonation is denied.
- Self-DM is rejected.
- Nonlocal destinations are rejected as unsupported; no federation
  request is attempted.
- No prompt logic makes authorization decisions.

## 8. Isolation invariants

- Message receipt performs no model inference.
- No ChatCompletionTask, provider call, embedding job, memory mutation,
  ordinary Guardian chat thread, Hosted Room row, federation request, or
  project association is created as a side effect of any DM operation.
- Private messages do not automatically become Guardian/project/retrieval
  context.

## 9. Route posture

Registered under the `direct_messages` route label.  Enabled only on the
hosted/private test profile (`v1-friends-family-web`); every other
supported profile leaves the label unlisted and route governance treats
it as quarantined.  Federation and general collaboration routes remain
quarantined.

## 10. Deferred (explicitly not implemented)

Frontend Inbox; realtime delivery (WebSocket/SSE); attachments;
cross-node transport; node discovery/resolution; endpoint negotiation;
node trust handshake; signatures and key rotation; node/profile
migration; global username uniqueness; username history; verification
badges; group messaging; reactions; read receipts; presence; blocking/
muting; Guardian messaging (all directions); autonomous replies;
inference budgets; notification delivery; memory/retrieval ingestion;
IDDB mutation; Beta/release-claim expansion.

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

1. Inbox/frontend projection
2. realtime same-node delivery
3. attachment references
4. remote Node_ID resolution/trust contract
5. cross-node transport adapter
6. delivery/receipt semantics
7. Guardian communication authority
8. Cognitive QoS / recipient inference budgets
9. passive local/cloud Guardian routing
