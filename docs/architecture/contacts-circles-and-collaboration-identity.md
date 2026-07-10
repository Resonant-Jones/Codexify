# Contacts, Circles, and Collaboration Identity Contract

## Purpose

Codexify needs a human relationship layer before it adds more collaborative tools. Current collaboration can resolve a low-level `user_id`, document ID, shared-link token, permission row, or WebSocket session, but those values do not answer the human question: who is this user collaborating with?

This contract defines the future user-facing model for Contacts, Circles, invitations, discovery, trust, and bounded collaboration Spaces. It is intended to let a user choose a person-shaped relationship once and let a future runtime resolve that choice into the appropriate permission, link, session, local-node participant, or remote-node participant. Users should not have to repeatedly type raw user IDs, emails, backend permission rows, or transport tokens as the primary collaboration experience.

The contract answers:

- who a user is collaborating with;
- how users contact one another without requiring a single identity carrier;
- how discovery is facilitated without making people globally discoverable;
- what replaces repeated manual entry of IDs, emails, and tokens; and
- what social vessel can later contain collaborative tools.

The social vessel is a user-owned Contact, a reusable Circle of Contacts, or a bounded collaboration Space. These are human relationship and context concepts. They are not replacements for current backend authorization primitives and do not change the current release boundary.

## Status

- Status: Proposal / architecture contract.
- Runtime implementation: Not implemented.
- Schema implementation: Not implemented.
- UI implementation: Not implemented.
- ADR: Required before runtime adoption.

This contract requires a new ADR before adding storage, routes, sync behavior, hosted rooms, remote identity, public discovery, cross-node trust, or production collaboration Spaces.

## Core thesis

Users collaborate with Contacts, Circles, or Spaces, not raw IDs, raw emails, permission rows, or tokens.

Raw IDs, emails, permission rows, shared-link tokens, and WebSocket identities remain implementation or transport values. They may be resolved behind a user-facing relationship, but they are not the relationship model itself.

## Current-truth boundary

The current supported posture remains local-first beta hardening. Current document collaboration is built around explicit `SharedLink` access, `CollaborationPermission` rows, document-scoped WebSocket sessions, and runtime `user_id` values. Current presence, typing, cursor, broadcast, and federation seams do not establish a social graph or a person-to-person identity model.

This contract therefore does not claim:

- hosted social networking or hosted collaboration rooms;
- global identity, public profiles, or a public user directory;
- global user search or federated discovery;
- automatic address-book import;
- cross-node identity or remote trust;
- a direct-messaging product;
- a shipped Space abstraction; or
- any widening of the supported beta release promise.

## 1. Definitions

### Contact

A **Contact** is a user-owned relationship record representing someone or something the local user may want to reach or collaborate with. A Contact is not necessarily an account, and it is not proof that the represented person has accepted an invitation or controls any particular identity.

A Contact can resolve, with explicit user action and an allowed path, to:

- a local Codexify user;
- an email invite recipient;
- a shared-link recipient;
- a remote-node participant; or
- a future hosted participant.

The Contact remains the local user's relationship and preference surface even when a runtime resolution changes, expires, or is revoked.

### Contact Card

A **Contact Card** is the user-facing representation of a Contact. It combines the local display name, optional relationship context, reachable handles, trust state, and collaboration defaults without making any one handle authoritative by itself.

### Circle

A **Circle** is a reusable, user-owned grouping of Contacts, such as `Stewards`, `Beta Testers`, or `Family`. A Circle is a convenience for selection, policy drafting, and repeated collaboration intent. A Circle is not itself an automatic permission grant.

### Space

A **Space** is a future bounded collaboration context in which selected participants can work against one or more shared artifacts, tools, conversations, or live surfaces. A Space is the likely future mount point for collaboration tools, but it is not currently implemented.

### Invite

An **Invite** is the transition object between an unknown recipient and a known Contact or participant. It records what was requested, for which context, through which delivery path, under what expiry and capability scope, and with what provenance. An invite token may transport an invite, but the token is not the relationship model.

### Participant

A **Participant** is a runtime-resolved actor in a specific Space or collaboration session. A participant may be human, AI-mediated, local-node, remote-node, or another explicitly governed actor. Participant status is context-specific and does not rewrite the underlying Contact or durable identity.

### Capability Grant

A **Capability Grant** is an explicit, scoped authorization for a Contact, Circle-derived recipient, or Participant to perform a named action in a named context. A capability grant is not ambient authority and does not follow automatically from a friendly relationship, favorite status, or trust label.

### Preferred Contact Method

A **Preferred Contact Method** is the local user's selected first-choice delivery or resolution path for a Contact, such as a local handle, email, invite link, QR code, or node handle. It is a preference, not proof of ownership, availability, or authorization.

### Trust State

A **Trust State** is a local, user-visible relationship posture describing what the local user may reasonably expect from a Contact and what remains unproven. It is not a cryptographic attestation unless a future ADR explicitly defines one.

### Discovery Path

A **Discovery Path** is the explicit route by which a Contact or Invite becomes known to the local user, such as manual entry, a user-generated link, QR code, or promotion from a recent collaboration. Discovery is consent-first and does not imply acceptance or trust.

### Relationship Note

A **Relationship Note** is private, user-authored context about a Contact. It is local memory for the relationship, not a public profile field and not automatically shared with the Contact, a Circle, a Space, Guardian, or another node.

### External Identity Handle

An **External Identity Handle** is an optional identifier outside the local Codexify account boundary, such as an email address, username, invite address, or service-specific handle. It is one resolution hint among several and is not the canonical Contact identity.

### Local Node Identity

A **Local Node Identity** is the identity of a Codexify node controlled by the local user or local deployment. It identifies a node boundary, not necessarily a human relationship or account.

### Remote Node Identity

A **Remote Node Identity** is the identity of a separate Codexify node participating through an explicitly governed remote or federation path. It is not automatically a person identity, trust relationship, or authorization to access local state.

### Unknown Recipient

An **Unknown Recipient** is a target for an invite or share action for whom the local user has not yet established a Contact relationship. An Unknown Recipient may receive a bounded invite through an allowed delivery path without becoming globally discoverable or automatically becoming a trusted Contact.

## 2. Proposed user-facing model

The future user-facing model has six related surfaces:

- **Contacts** — a local user's relationship cards and explicit reachability choices.
- **Circles** — reusable user-owned groups of Contacts for repeated selection.
- **Preferred Contacts** — a view or filter over Contacts the user has marked as preferred for routine sharing; this is a convenience, not a trust escalation.
- **Recent Collaborators** — a derived local view of Contacts or unresolved participants encountered in recent explicit collaboration; recency does not imply consent, friendship, or trust.
- **Invites** — pending and historical transitions to a Contact or participant, including expiry and revocation state.
- **Spaces** — future bounded contexts where selected Contacts, Circle members, and resolved Participants can work together.

These surfaces let the user express intent in relationship language:

- “Share with Zac.”
- “Invite Stewards.”
- “Open this workspace with Paul.”
- “Start live session with Beta Testers.”
- “Send this artifact to Preferred Contacts.”

The system may later resolve those choices into a shared link, a permission grant, a session participant, or a node-bound route. The resolution must remain inspectable, explicit, scoped, and revocable.

## 3. Contact Card conceptual shape

A future Contact Card may conceptually contain:

```text
contact_id
display_name
local_alias
relationship_notes
preferred_contact_method
external_handles
node_id
email
trust_state
capability_defaults
last_invited_at
last_collaborated_at
blocked_at
archived_at
created_at
updated_at
```

This is a conceptual contract, not a database schema. Fields are illustrative and do not establish nullability, normalization, indexing, encryption, retention, ownership, or synchronization behavior. A future schema must be introduced through a separate architecture-impact task and ADR.

The conceptual shape must preserve the distinction between:

- the local relationship (`contact_id`, alias, notes, preference);
- optional resolution hints (email, external handles, node ID);
- trust and safety state; and
- context-specific capability grants.

No field by itself proves that a Contact is an account, that an external handle is controlled by the intended person, or that the Contact can access any artifact.

## 4. Circle conceptual shape

A future Circle may conceptually contain:

```text
circle_id
name
description
members
default_capability_policy
created_by
created_at
updated_at
archived_at
```

This is a conceptual shape, not a database schema. A Circle is user-owned by default. Shared or organization-owned Circles are future work and require a separate authority, membership, synchronization, and conflict policy.

Circle rules:

- Circle membership does not automatically grant access to every artifact.
- Granting access to a Circle creates scoped grants or invites per target context.
- A Contact's block, revoke, or safety state must be evaluated when a Circle is used.
- A Circle's default capability policy is a proposal or selection convenience until a target context explicitly accepts it.
- Circle expansion must be deterministic and auditable for a given target context.
- A Circle does not become a global directory, public social graph, or organization roster by being selected.

## 5. Trust states

Trust states are local relationship labels with bounded expectations. They must not be presented as universal claims about the other party.

| State | Meaning | Allowed user expectations | Must not imply |
|---|---|---|---|
| `unknown` | The target is not yet a known Contact relationship, or its identity has not been resolved. | The user may prepare or send a bounded invite through an allowed path. | Account ownership, consent, delivery, trust, or access. |
| `draft` | The user has started a Contact or invite record locally but has not sent or confirmed it. | The user may edit, discard, or inspect the draft. | That any recipient has been notified or that a Contact exists for another user. |
| `invited` | An invite or contact request was explicitly issued. | The user may see the requested context, delivery path, expiry, and pending outcome. | Delivery, opening, acceptance, identity verification, or capability use. |
| `pending` | A response, resolution, or participant binding is awaiting completion. | The user may wait, resend where allowed, revoke, or choose another path. | That the recipient can already enter, act, or see presence. |
| `connected` | An explicit path has resolved the Contact to a reachable account, node, or session participant. | The user may reuse the resolved path within its declared scope. | Broad trust, permanent availability, or access to unrelated contexts. |
| `trusted` | The local user has explicitly chosen a higher-confidence relationship posture. | The user may use approved defaults and reduced repetition within declared scopes. | All capabilities, remote-node safety, identity attestation, or automatic access. |
| `favorite` | The local user prefers this Contact for quick selection. | The Contact may appear in Preferred Contacts and quick actions. | Trust, consent, priority for the other party, or any capability. |
| `blocked` | The local user has prohibited new contact, invite, or grant activity through this relationship. | New outbound actions should be prevented or require explicit unblocking. | Erasure of historical records, revocation of already-observed data, or a claim that the other party is malicious. |
| `archived` | The relationship is retained for historical context but removed from active selection by default. | Past provenance and collaboration history may remain inspectable according to policy. | Deletion, revocation, or permission changes in past contexts. |
| `revoked` | A previously issued invite, resolution, trust posture, or capability path has been explicitly withdrawn. | Future use of that path should fail closed or require a new explicit action. | Erasure of copied artifacts, proof that a remote party forgot data, or automatic blocking of every other path. |

These states may need separate axes in a future implementation. In particular, `favorite`, `blocked`, `archived`, and `revoked` are not necessarily mutually exclusive with relationship progress. The future ADR must define the state machine and precedence rather than treating this table as a schema enum.

## 6. Capability scopes

Future conceptual capabilities include:

- `can_message`
- `can_collaborate_documents`
- `can_view_presence`
- `can_receive_invites`
- `can_join_spaces`
- `can_use_voice`
- `can_exchange_files`
- `can_receive_artifacts`
- `can_comment`
- `can_edit`

Capability rules:

- Capabilities are explicit and scoped.
- Capabilities are not ambient.
- Capabilities may be defined per Contact, per Circle, per Space, or per artifact.
- A Contact becoming `trusted` must not automatically grant all future capabilities.
- Circle defaults must be narrowed or confirmed for each target context.
- A capability grant must identify its issuer, subject, target scope, requested or granted capability, creation time, expiry or revocation posture, and provenance in a future contract.
- A participant may be present without holding control, edit, message, or file capabilities.
- A capability does not bypass current authentication, authorization, document ownership, or node-trust boundaries.

## 7. Discovery policy

Discovery is invite-first and consent-first. Codexify should help a user reach a known target without turning the product into a public identity directory.

Allowed early discovery paths:

- manual Contact creation;
- a user-generated invite link;
- a QR code;
- promotion of a recent collaborator after an explicit user action; and
- explicit import from a user-selected source in the future.

The local user must be able to create a Contact without knowing whether the target has a Codexify account. An unresolved Contact can remain an Unknown Recipient or an invite target until a later resolution path succeeds.

Future discovery paths requiring an ADR:

- address book import;
- local network discovery;
- remote node discovery;
- public directory;
- organization directory; and
- federation directory.

Non-goals:

- no global search by default;
- no public user directory by default;
- no automatic address-book harvesting;
- no ambient “people nearby” behavior;
- no silent friend graph; and
- no public follower model.

Discovery must not silently create a Contact, send an invite, expose presence, or grant access. Every promoted or imported relationship must retain its discovery path and user action in future provenance.

## 8. Invite lifecycle

The conceptual Invite states are:

- `draft` — prepared locally but not sent;
- `sent` — issued through an explicit delivery path;
- `opened` — the recipient or delivery surface has opened it, if the path can prove that event;
- `accepted` — the requested relationship or context action was accepted;
- `declined` — the recipient declined the request;
- `expired` — the invite passed its declared expiry without acceptance;
- `revoked` — the sender or governing authority withdrew it; and
- `blocked` — delivery or acceptance is prohibited by a block or policy boundary.

An invite may carry:

- a target artifact or Space;
- an invited Contact or Unknown Recipient;
- capabilities requested or granted;
- an expiry;
- a sender note;
- provenance;
- a delivery method; and
- a token or future cryptographic proof.

Invite rules:

- Invite tokens are transport artifacts, not the user-facing relationship model.
- A token must not be treated as a durable identity or a blanket capability.
- Accepting an invite may create or update a Contact Card, depending on user choice and trust posture.
- Acceptance of a target artifact invite must not silently accept unrelated future invites from the same recipient.
- Revocation must prevent future use of the revoked path where the runtime can enforce it, while not pretending to erase copies or observations already made.
- Resending or reissuing an invite must preserve lineage and distinguish the new delivery attempt from the prior invite.
- Delivery, opening, and acceptance are different events and must not be collapsed into one success state.

## 9. Space concept

A Space is a future bounded collaboration container. It may eventually contain:

- documents;
- chat;
- artifacts;
- live presence;
- voice;
- shared tools;
- task graph nodes;
- an audit trail; and
- capability grants.

Space rules:

- Space is not currently implemented.
- Space must not be claimed as shipped.
- A Space is the likely future mount point for collaborative tools.
- A Space should resolve participants from Contacts and Circles rather than raw IDs.
- A Space must have an explicit owner or authority boundary, participant roster, capability policy, lifecycle, and provenance model before runtime work begins.
- A Space must support mixed trust states without turning the least-trusted participant into ambient access.
- Presence in a Space must be scoped to that Space or an active collaboration context.
- A Space is not a hosted room by definition; hosted-room support is a separate future decision.

## 10. Boundary and authority model

The future model must preserve the following distinctions:

| Boundary | Future meaning |
|---|---|
| Local user boundary | The user owns Contacts, local aliases, relationship notes, preferences, and default choices. |
| Account boundary | A Codexify account, when present, owns account-scoped authorization and durable application state. A Contact is not necessarily this account. |
| Local node boundary | A local node owns its local runtime and node identity. It does not become a global identity authority. |
| Remote node boundary | A remote node participates only through an explicit, separately governed trust and protocol path. Node identity is not human identity. |
| Space boundary | A Space scopes participant resolution, presence, tools, artifacts, and capability grants. |
| Network/transport boundary | Links, email, QR codes, WebSockets, and future federation transports carry resolution or access artifacts; they do not define the social relationship. |

The default threat model is honest-but-buggy local software and explicit user actions, with stronger checks required for public exposure, malicious recipients, compromised nodes, and remote federation. Enforcement must live in authentication, authorization, capability, cryptographic, and audit boundaries; prompts or display labels cannot provide security.

Future state ownership should be local-first: Contacts and Circles are user-owned local state unless a future ADR explicitly defines device synchronization or shared ownership. The consistency target should be eventual across explicitly paired user devices, if sync is later approved. Conflicts must be visible and resolved through deterministic merge or human review; silent relationship merging is not acceptable.

## 11. Mapping to current runtime primitives

This future layer must map to existing primitives without changing them in this task:

- Contact or Circle selection may create or resolve a `SharedLink`.
- Contact or Circle selection may create or resolve a `CollaborationPermission`.
- Space participant resolution may determine the WebSocket `user_id` used for a document-scoped session.
- Invite acceptance may create or update permission grants.
- Existing collaboration WebSocket sessions remain document-scoped until a future task changes them.

The mapping is a future adapter boundary, not a claim that current code performs these resolutions. Current backend primitives are implementation details from the user perspective. Contacts and Circles should become the user-facing layer above shared links and permission rows while preserving current ownership, authentication, access, and audit semantics.

The mapping must remain inspectable. A future user or operator should be able to distinguish the selected Contact or Circle from the resolved account, `user_id`, link, permission grant, participant, node, and session. A resolved primitive may expire, be revoked, or be unavailable without deleting the local relationship record.

## 12. Privacy and safety boundaries

- No Contact is globally discoverable by default.
- No user appears in another user's Contacts without an action or invite path.
- Blocked Contacts must not receive new invites or collaboration grants.
- Archived Contacts remain historical only and are excluded from active selection by default.
- Presence must be scoped to active Spaces or collaboration contexts.
- Presence must not be ambient across the whole app.
- Relationship notes are private to the local user unless explicitly shared.
- External handles and email values are sensitive relationship data, not public profile defaults.
- A Contact card must not expose a remote node endpoint, token, or capability grant merely because the Contact exists.
- Circle expansion must not reveal the membership of a private Circle to recipients unless the user explicitly shares that information.
- Future sync/export behavior must account for Contacts and Circles as sensitive user-owned data.
- Capability and invite resolution must fail closed when the target, scope, or trust proof is ambiguous.

## 13. Export and restore implications

Contacts and Circles are likely exportable user-owned state in the future because they carry relationship continuity, local organization, and user intent. They must not be silently omitted if they become part of canonical account state.

Future export/restore must define:

- whether Contact Cards and Circles are included by default or selected by export scope;
- how trust states, blocked state, archived state, relationship notes, and invite history are protected;
- whether invites, revoked Contacts, blocked Contacts, and remote node handles are included;
- whether external handles and email values are encrypted, redacted, or separately consented;
- how stable Contact and Circle identities are preserved when local persistence IDs are remapped;
- how duplicate Contacts are detected without silently merging human relationships;
- how revoked or expired transport artifacts are represented without making them usable; and
- how provenance records preserve the discovery path and prior resolution history.

These implications follow the account export contract's requirements for explicit ownership, stable identifiers, relationship preservation, provenance, integrity, idempotent restore, and explicit failure reporting. No export/restore behavior is implemented by this spec.

## 14. Open questions

- Should Contacts be local-only by default?
- Should Circles sync across devices?
- How are duplicate Contacts merged?
- How does a Contact verify a remote node identity?
- What is the minimum viable Contact Card for friends-and-family beta?
- Should email be optional, required, or only one possible handle?
- How are blocked Contacts represented in export?
- How does a user rotate or revoke an invite?
- How does a future Space handle mixed trusted and untrusted participants?
- What is the boundary between Contact, account, node, and persona?
- Should Guardian maintain relationship memory about Contacts?
- How should Contacts interact with project/workspace scope?
- Which trust claims, if any, can be cryptographically verified rather than locally labeled?
- How should a user see and correct an incorrect Contact-to-runtime resolution?
- What happens when a Circle contains blocked, archived, revoked, or unresolved Contacts?

## 15. Required future ADRs

The following ADRs are required before runtime work:

- Contact and Circle storage model ADR.
- Invite and trust lifecycle ADR.
- Space participant resolution ADR.
- Discovery and directory policy ADR.
- Contact export/restore privacy ADR.
- Presence scope and ambient visibility ADR.

Those ADRs must also resolve schema versioning, device sync, identity binding, key rotation and revocation, capability precedence, conflict policy, remote-node trust, and migration behavior before implementation is treated as architectural adoption.

## 16. Non-goals

- No runtime implementation.
- No UI implementation.
- No schema or migrations.
- No hosted rooms.
- No public directory.
- No global identity provider.
- No automatic address book import.
- No federation.
- No cross-node trust.
- No ambient app-wide presence.
- No direct messaging implementation.
- No Guardian memory behavior change.
- No collaboration tool mounting.
- No document editor behavior change.

## 17. Implementation sequence recommendation

The smallest safe future sequence is:

1. Docs-only contract, this task.
2. ADR for local Contacts and Circles storage.
3. Static fixtures for Contact, Circle, Invite, and Space conceptual examples.
4. Local-only Contact Card UI.
5. Manual Contact creation.
6. Invite-link creation from Contact.
7. Circle selection for scoped grants.
8. Space proposal and ADR.
9. Collaboration tool mounting through Contacts/Circles.

Each later step must retain the current local-first beta boundary until implementation proof, security review, migration proof, and explicit release-truth follow-through exist. This document is the contract and vocabulary seed for that work; it is not authorization to begin any later step.
