# Codexify.Space Event Spine Proposal

## Purpose

The event spine is an append-only chronological record of coordination events across Codexify.Space and its connected local nodes.

It does not replace either local Codexify system, centralise private memory, or absorb local files. Local nodes remain authoritative over their own models, data, tools, agents, and compute.

Codexify.Space records the shared coordination layer between them.

## What it provides

The event spine gives us a common source for:

- node connection and disconnection history
- authentication and pairing receipts
- room membership and presence
- messages and delivery state
- file uploads and node-owned file references
- permission requests and decisions
- tool requests and execution receipts
- structural decisions
- synchronisation and relay failures
- changelogs
- activity feeds
- bounded continuity context for agents

The portal does not need to store everything to know what happened. It needs a trustworthy record of coordination events and pointers to the resources involved.

## Local and portal ownership

There should be two related event layers.

### Local event spine

Each Codexify node records its own complete local history. Private events can remain entirely local.

### Portal event spine

Codexify.Space records only events relevant to shared coordination:

- shared rooms
- connected nodes
- authentication
- permissions
- messages
- shared files
- node-owned resource references
- relay and delivery state

A local event that crosses into the portal should retain its original identity:

```json
{
  "local_event_id": "local_8841",
  "portal_event_id": "evt_01JXYZ..."
}
```

This preserves provenance and makes it clear whether an event originated on a node or at the portal.

## Event structure

Every portal event should contain:

- globally unique event ID
- event type
- schema version
- timestamp
- actor
- scope
- origin node
- visibility
- payload or payload reference
- provenance
- optional causal reference

Example:

```json
{
  "event_id": "evt_01JXYZ...",
  "type": "file.updated",
  "schema_version": 1,
  "timestamp": "2026-07-13T22:00:00+12:00",
  "actor": "node:zac-macstudio",
  "scope": "room:codexify-core",
  "visibility": "room-members",
  "origin": {
    "node_id": "node:zac-macstudio",
    "local_event_id": "local_8841"
  },
  "payload": {
    "resource_type": "file",
    "resource_id": "file:codexify-spec",
    "change": "modified",
    "content_hash": "sha256:..."
  },
  "payload_ref": {
    "uri": "node://zac-macstudio/projects/codexify/spec.md",
    "availability": "node-required"
  }
}
```

The event records that the file changed without placing the file itself on the portal.

## Initial event types

The first version only needs a focused set.

```text
identity.authenticated
node.paired
node.connected
node.disconnected
node.heartbeat
node.capabilities.updated

room.created
room.member.added
room.member.removed

message.created
message.delivered
message.failed

file.uploaded
file.referenced
file.updated

permission.requested
permission.granted
permission.denied
permission.revoked

tool.requested
tool.approved
tool.denied
tool.executed
tool.failed

decision.recorded
document.revision.created

sync.started
sync.completed
sync.failed
relay.fallback.started
```

## Data boundaries

Every resource should declare its ownership.

### Shared file

Explicitly uploaded or synchronised to the portal.

```text
owner: shared workspace
content location: portal
availability: portal-dependent
```

### Node-owned file

Remains on the local machine.

```text
owner: originating node
content location: local node
availability: node must be online
```

### Metadata-only reference

The portal knows the resource exists but does not possess its content.

```text
owner: originating node
content location: local node
availability: metadata available
content access: explicit request required
```

Connecting a node must never imply access to its entire filesystem.

A node explicitly exposes selected folders, projects, agents, knowledge bases, tools, or capabilities.

## Permissions

Permissions should be explicit, scoped, and revocable.

```json
{
  "event_id": "evt_01JPERM...",
  "type": "permission.granted",
  "actor": "identity:zac",
  "scope": "room:codexify-core",
  "payload": {
    "subject": "agent:luna",
    "resource": "knowledgebase:codexify-design",
    "actions": ["search", "read"],
    "expires_at": null
  }
}
```

The event spine records the permission history. The node still enforces access locally before returning any content.

## Append-only behaviour

Events should not be silently edited or deleted.

If something changes, append a new event:

```text
permission.granted
permission.revoked
```

rather than mutating the original grant.

This allows the current state to be derived from the history and preserves an auditable record.

## Derived views

The following portal features can be projections of the event spine:

- activity feed
- changelog
- node online/offline state
- room state
- permission state
- delivery state
- project history
- agent continuity packet

The raw event spine is the chronological source. The UI and APIs consume derived views rather than repeatedly interpreting the entire history.

## Agent continuity

Agents should receive a bounded, permission-aware continuity packet, not the complete raw event history.

A packet may include:

- current room
- current project or objective
- active participants
- connected nodes
- recent relevant events
- recent decisions
- unresolved questions
- pending permissions
- available capabilities
- links to evidence

Example:

```text
Room: Codexify Core
Objective: Validate node pairing and scoped routing
Participants: Zac, Christopher, Luna
Connected nodes: 2
Recent decision: Local nodes remain authoritative
Pending request: Agent access to shared design documents
Latest event: Christopher node heartbeat received
```

This provides continuity and presence without creating context bloat or leaking unrelated private history.

## WebSocket integration

A node connecting through the outbound WebSocket should be able to:

1. authenticate
2. announce its node identity
3. announce capabilities and exposed resources
4. send heartbeat events
5. join approved rooms
6. submit eligible local events
7. receive room events
8. acknowledge delivery
9. resume from its last confirmed portal event after reconnecting

On reconnection, the node reports its last acknowledged event so missed events can be identified and resent.

## Failure behaviour

If Codexify.Space goes offline:

- local Codexify systems continue operating
- local private events continue recording
- local agents continue within local permissions
- shared delivery may be delayed
- node discovery and relay are unavailable
- local work and data remain intact

If a node goes offline:

- metadata may remain visible
- node-owned content is marked unavailable
- the interface shows that the node is required
- portal-owned shared files remain available

The system should distinguish unavailable from deleted. Important difference. Otherwise we invent data loss every time someone closes a laptop.

## Suggested MVP

The first implementation could be:

1. User authentication.
2. Explicit node pairing.
3. Outbound WebSocket connection.
4. Node heartbeat and online/offline state.
5. Portal-side append-only event store.
6. One shared room.
7. Basic message routing.
8. One shared uploaded file.
9. One node-owned file reference.
10. One scoped permission request.
11. Activity feed derived from events.
12. Reconnect and missed-event handling.
13. Local operation during portal outage.

## Non-goals for the first version

- unrestricted filesystem browsing
- arbitrary remote command execution
- full-node synchronisation
- universal agent access
- centralised private memory
- multi-relay federation
- autonomous permission decisions
- complete semantic search across private nodes
- complex offline conflict resolution

## Core principle

Codexify.Space should coordinate independently owned Codexify nodes without becoming the place where everything has to live.

The event spine supports that by separating:

```text
local ownership
shared coordination
resource access
derived state
```

The portal records what happened. The node retains authority over what it owns. Permissions determine what may cross the boundary. Agents receive curated continuity rather than unrestricted memory.

That gives Codexify.Space a durable protocol foundation without turning it into a centralised replacement for the local systems.
