# ADR-053: Node-Hosted Room Access Boundary

## Status

Proposed

This ADR defines future architecture behavior only. It does not implement or claim an implemented Hosted Room runtime, persistence model, room session, invitation exchange, Contacts workflow, or RoomShell.

## Context

Codexify needs a canonical authority boundary before the existing chat prototype evolves into a durable private collaboration product. The target experience is:

1. A Codexify owner hosts a durable room from their own node.
2. The owner may select intended guests from Contacts.
3. The owner separately provides any required private-network access, initially through the existing manual Tailscale path.
4. Codexify issues a room invitation that grants access only to the intended room.
5. Humans may exchange messages inside the room.
6. Enabled resident agents such as Guardian or Luna may respond from the node.
7. The owner's browser does not need to remain open.
8. The Codexify node, backend, queue, worker, and required model runtime must remain available for agent responses.
9. Guests must not gain general access to the host's projects, threads, documents, Contacts, Settings, Persona Studio, diagnostics, or administrative surfaces.

The existing `webui-basic/index.html` prototype proves useful interaction behavior: multiple display labels can share one persisted chat thread, ordinary human messages can be posted without model invocation, polling can reveal new messages, and mentions can trigger Guardian or Luna completion requests. It does not establish the canonical identity, persistence, invitation, session, or authorization contract. In particular, its general Guardian API-key posture cannot become the Hosted Room security model.

Existing `/api/share` thread links retrieve explicitly shared content through a read-only route. They are semantically separate from future write-capable Hosted Room invitations and must remain separate.

## Decision

### 1. Hosted Room

A Hosted Room is:

- owned by one Codexify account on one hosting node;
- backed by exactly one canonical chat thread;
- durable across browser refreshes and host absence;
- explicitly open, closed, or otherwise lifecycle-governed;
- isolated from unrelated Codexify resources;
- capable of containing human and agent participants; and
- not equivalent to a Contact, Circle, Share link, account, thread, project, or future Space.

The Hosted Room owns collaboration and access semantics.

The backing chat thread owns transcript persistence.

A Hosted Room must not create or maintain a parallel transcript store.

### 2. Initial topology

V1 assumes:

- one hosting Codexify node;
- one room owner;
- zero or more invited human guests;
- zero or more explicitly enabled resident agents;
- private network reachability handled outside the room contract; and
- manual Tailscale invitation as an acceptable initial network path.

V1 explicitly defers:

- cross-node rooms;
- federation;
- transcript merging;
- cloud relay hosting;
- public room discovery; and
- automatic Tailscale administration.

The hosting node is the authoritative node for room lifecycle, participant state, invitation state, authorization decisions, canonical transcript persistence, and agent invocation.

### 3. Network reachability versus room authority

The governing invariant is:

`Network reachability is not application authority.`

Tailscale or another Network Profile may allow a device to reach the hosting node. That reachability must not independently authorize access to a Hosted Room or any other Codexify resource.

Room access must be independently authorized by Codexify. Network admission and room admission remain two separate onboarding and revocation boundaries.

### 4. Invitation boundary

A Hosted Room invitation must:

- belong to exactly one Hosted Room;
- have a non-plaintext stored credential representation;
- have an explicit lifecycle;
- support pending, accepted, revoked, and expired semantics;
- be independently revocable;
- not function as a general Guardian API key;
- not authorize arbitrary thread IDs;
- not authorize unrelated room IDs;
- not become a reusable account credential; and
- preserve the distinction between intended recipient and verified identity.

The broader invite lineage and delivery distinctions defined by [[044-invite-lifecycle-and-storage-model|ADR-044]] remain applicable. Room access must still fail closed for the room-specific pending, revoked, and expired states even if a later implementation preserves additional invite lifecycle detail.

Opening an invitation may create a room-scoped session. After a successful exchange, the invitation credential should not need to remain in browser-visible URLs.

### 5. Room-scoped session

A future room-scoped guest session must:

- resolve to exactly one room;
- resolve to exactly one participant;
- authorize only Hosted Room operations;
- be rejected by general account-authenticated routes;
- be unable to enumerate other rooms or threads;
- be invalidatable when the invitation is revoked, the participant is removed, the room closes, or the session expires;
- use secure, HTTP-only browser storage when represented as a cookie; and
- fail closed when its room, participant, invitation, or lifecycle state is invalid.

A room-scoped session is not an account session, Guardian API key, operator credential, Network Profile, Contact identity, or global participant identity.

This ADR does not prescribe a final token library or cryptographic implementation.

### 6. Participants

A Hosted Room Participant is a room-scoped identity record.

Participant kinds:

- human;
- agent.

Initial roles:

- owner;
- member;
- agent.

Initial role behavior:

**Owner**

- read room messages;
- post room messages;
- manage room lifecycle;
- create and revoke invitations;
- remove participants; and
- enable or disable resident agents.

**Member**

- read room messages;
- post room messages; and
- invoke enabled agents.

**Agent**

- read only the room context required for authorized completion;
- write assistant messages to the room's backing thread; and
- hold no room-management authority.

Display names are presentation labels, not global identity proof. A display label must not grant authority or be treated as proof that the participant is the intended Contact.

### 7. Contacts relationship

A Contact represents the owner's private relationship record and invitation intent.

Selecting a Contact for a room may:

- prefill an intended display name;
- associate an invitation with a local Contact record; and
- help the owner manage who was invited.

Selecting a Contact must not:

- authenticate the guest;
- automatically grant room access;
- expose presence;
- create a global account; or
- imply that the invitation opener has cryptographically proven they are the selected Contact.

This preserves [[043-contact-and-circle-storage-model|ADR-043]]'s distinction between user-owned relationship state and runtime identity, [[044-invite-lifecycle-and-storage-model|ADR-044]]'s distinction between invitation transport and identity, and the [Contacts, Circles, and Collaboration Identity Contract](../contacts-circles-and-collaboration-identity.md)'s consent-first discovery posture.

### 8. Agent participation

Guardian, Luna, or another future agent must be an explicit room participant or an explicitly enabled room capability.

For the first implementation:

- ordinary human messages may persist without invoking a model;
- mention-driven invocation is permitted;
- disabled agents must not be invokable;
- agent responses must return to the same backing thread;
- the existing queue-backed completion pipeline remains authoritative; and
- the host browser is not the execution engine.

Hosted Rooms must not define a new agent runtime or parallel completion pipeline. Request acceptance, worker execution, model completion, assistant persistence, and browser visibility remain distinct proof surfaces.

### 9. Share links remain separate

**Read-only Share Link**

- retrieves explicitly shared thread or document content;
- does not permit posting; and
- does not permit agent invocation.

**Hosted Room Invitation**

- may permit bounded room participation;
- has participant and lifecycle semantics;
- may permit message posting; and
- may permit invocation of enabled room agents.

Existing `/api/share` semantics must not be silently widened.

### 10. Presence

V1 may expose room-bounded operational states such as:

- joined;
- disconnected;
- agent generating; and
- participant removed.

V1 must not claim:

- global Contact presence;
- general account availability;
- activity outside the room;
- that an invited person is currently watching; or
- cross-node presence.

Ambient presence remains deferred.

### 11. Data posture

Future Hosted Room persistence must be:

- account-scoped;
- exportable with the owning account where applicable;
- private by default;
- revocable;
- lifecycle-explicit;
- compatible with clean-start, upgrade, downgrade, and restore semantics;
- free from plaintext invitation-token persistence; and
- linked to the canonical chat thread rather than duplicating messages.

The export and restore posture must preserve or explicitly govern the Hosted Room, participant, invitation, lifecycle, and backing-thread relationships without silently reactivating revoked access or closed rooms. Exact SQLAlchemy models and migration columns belong to a later implementation task.

### 12. Initial capability bundle

The initial member capability bundle is conceptually:

- `room.read`;
- `room.post`;
- `room.invoke_enabled_agents`.

It explicitly excludes:

- project enumeration;
- arbitrary thread access;
- document enumeration;
- Contacts access;
- Settings access;
- Persona Studio access;
- diagnostics access;
- operator controls; and
- administrative controls.

These values are conceptual architecture vocabulary. This docs-only task does not introduce canonical runtime token constants.

### 13. Room lifecycle

The minimum Hosted Room lifecycle is:

- active;
- closed.

A future implementation may add lifecycle states only when their meanings, transitions, authorization effects, migration behavior, and restore behavior are explicit.

Closing a room must:

- stop new guest participation;
- invalidate or reject room-scoped sessions;
- stop new member messages; and
- preserve the owner's durable history according to normal thread and account lifecycle policy.

Room closure must not silently delete the backing transcript.

## Current-truth anchors

### What is true now

- Codexify has canonical persisted chat threads and messages.
- Chat completion uses the existing backend, queue, worker, and model-runtime path.
- Existing thread Share links are read-only.
- `webui-basic/index.html` demonstrates a collaborative polling UI and mention-based Guardian/Luna interaction.
- Contacts UI concepts and governing ADRs exist.
- Manual Tailscale-based reachability is already used for private node access.

### What is not yet true

- No canonical Hosted Room entity exists.
- No Hosted Room invitation exchange exists.
- No room-scoped guest session exists.
- No durable Hosted Room participant roster exists.
- Contacts do not currently authenticate or authorize room guests.
- No supported RoomShell exists.
- No supported room-management UI exists.
- No cross-node room or federation contract exists.
- Hosted Rooms are not a release-qualified feature.

### What future implementation may assume

- One room maps to one canonical chat thread.
- The host node remains authoritative for that room.
- Room authority is separate from network reachability.
- Account and room authorization must be enforced by the backend.
- Existing completion persistence remains canonical.

## Invariants

1. One Hosted Room maps to exactly one canonical chat thread.
2. Messages are not duplicated into a parallel room transcript.
3. Network access does not grant room or account authority.
4. Room authority does not grant general Codexify authority.
5. Invitations are room-scoped and independently revocable.
6. Contacts express relationship and intent, not authentication.
7. Guest display names are not global identity proof.
8. Agent participation is explicit and bounded.
9. Existing Share links remain read-only.
10. Revoked, expired, removed, or closed states fail closed.
11. The host browser is not required for continued room operation.
12. The hosting node and required runtime services are required for room operation.
13. No ambient presence claims are inferred from invitation or Contact state.
14. No future Space or federation semantics are smuggled into V1.
15. Hosted Room implementation must remain compatible with account export, restore, migration, and deletion doctrine.

## Proof surface

A later implementation must prove:

- an invited guest can access the intended room;
- the guest can read and post only within that room;
- the guest cannot enumerate or fetch unrelated threads;
- the guest cannot access projects, documents, Contacts, Settings, Persona Studio, diagnostics, or administrative routes;
- one invitation cannot be replayed against another room;
- revoked invitations fail;
- expired invitations fail;
- removed participants fail;
- closed rooms fail;
- existing read-only Share links remain read-only;
- ordinary human messages do not automatically invoke an agent;
- enabled Guardian or Luna invocation reaches the canonical completion pipeline;
- disabled agents cannot be invoked;
- agent responses persist to the same backing thread;
- the room continues operating after the host browser closes;
- the room stops responding appropriately when the node or required runtime service is unavailable;
- clean-start migration passes;
- existing-instance upgrade passes;
- downgrade passes;
- account export and restore preserve or explicitly govern Hosted Room state; and
- plaintext invitation credentials are absent from database records, logs, and exported artifacts.

None of these proofs currently exists by virtue of this ADR.

## Deferred work

- implementation models and migrations;
- API route design details;
- React RoomShell implementation;
- Contacts persistence implementation;
- Contacts room-creation UI;
- voice rooms;
- collaborative document editing;
- attachment policy;
- granular custom permissions;
- email invitation delivery;
- automatic Tailscale invites;
- federation;
- cloud hosting;
- cross-node identity;
- public discovery;
- ambient presence; and
- Spaces and nested channels.

## Consequences

### Benefits

- A stable authority boundary exists before UI work.
- The prototype can evolve without becoming the security model.
- Contacts can participate without becoming identity proof.
- Existing chat and completion machinery remain reusable.
- Share-link semantics remain safe.
- Future expansion has a clear trunk.

### Costs

- Additional persistence and authorization machinery will be required.
- Room-scoped sessions need dedicated testing.
- Invitation revocation and lifecycle state add complexity.
- Network and application access remain two separate onboarding steps.
- Federation and global identity remain intentionally unresolved.

## ADR impact

Classification:

`Requires new ADR`

Governing and related ADRs:

- [[039-operator-user-access-boundary|ADR-039 Operator / User Access Boundary]]
- [[040-network-profile-topology-resolution-contract|ADR-040 Network Profile Topology Resolution Contract]]
- [[043-contact-and-circle-storage-model|ADR-043 Contact and Circle Storage Model]]
- [[044-invite-lifecycle-and-storage-model|ADR-044 Invite Lifecycle and Storage Model]]
- [[045-space-participant-resolution-model|ADR-045 Space Participant Resolution Model]]

Reason:

Hosted Rooms introduce a new operator-visible and user-visible authorization boundary linking private network reachability, invitations, room-scoped identity, participant lifecycle, canonical chat persistence, and agent invocation. This would be dangerous to leave implicit.

Documentation follow-through:

- Add this ADR to the ordered list and graph in [[adr-index|ADR Index]].
- Add a bounded Hosted Rooms section to the [Contacts, Circles, and Collaboration Identity Contract](../contacts-circles-and-collaboration-identity.md).
- Do not update `docs/architecture/00-current-state.md`; this ADR does not change runtime truth.
