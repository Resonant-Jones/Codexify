# ADR-045: Space Participant Resolution Model

## Status

**Status:** Proposed

## Context

[Contacts, Circles, and Collaboration Identity](../contacts-circles-and-collaboration-identity.md) defines the social vessel — Contacts, Circles, Invites, Spaces, trust states, discovery paths, and capability grants — as proposal-only architecture semantics.

[ADR-043: Contact and Circle Storage Model](./043-contact-and-circle-storage-model.md) defines where Contacts and Circles should live: account-scoped, exportable, private-by-default, with sync deferred.

[ADR-044: Invite Lifecycle and Storage Model](./044-invite-lifecycle-and-storage-model.md) defines how an Unknown Recipient becomes invited, opened, accepted, declined, expired, revoked, or blocked through a bounded lifecycle state machine.

The next unanswered question is who sits inside a future Space after social selection, invite acceptance, runtime resolution, and capability scoping. Without an explicit participant resolution contract, Spaces risk collapsing Contacts into Participants, Invites into active sessions, Circle membership into broad permission, or runtime identity into human identity.

This ADR is required before Space schema, Space UI, participant rosters, Space presence, collaborative tool mounting, hosted rooms, or cross-node participant behavior.

## Decision frame

The Space participant resolution model must be designed across these axes. These are design dimensions, not implementation fields.

| Axis | Core question |
|---|---|
| **Participant source** | Where does a candidate participant come from — Contact, Circle, Invite, manual entry, local account, remote node, AI agent? |
| **Participant identity binding** | How does the system resolve a source into a participant identity for a Space? |
| **Space roster membership** | What does it mean to be on a Space roster, and what states can a roster entry have? |
| **Role and capability posture** | What can a participant do in the Space, and how are capabilities scoped? |
| **Invite acceptance mapping** | How does an accepted Invite become a Participant? |
| **Contact and Circle reference mapping** | How does a Contact or Circle selection resolve into participant entries? |
| **Local account mapping** | How does a local Codexify account map to a Participant? |
| **Local node mapping** | How does a local node identity map to a Participant? |
| **Remote node mapping** | How does a remote node identity map to a Participant? |
| **AI-mediated actor mapping** | How does an AI or agent-mediated actor appear as a Participant? |
| **Presence visibility** | What presence does a Participant expose, and to whom? |
| **Mixed-trust handling** | How does a Space handle participants with different trust states? |
| **Export and restore behavior** | How are participant records exported and restored? |
| **Sync and conflict behavior** | How are participant rosters kept consistent across devices or nodes? |

## Recommended default posture

- Space Participants should be **Space-scoped, explicit, provenance-backed, capability-scoped, private-by-default, and presence-bounded**.
- A Participant is a **runtime/context role inside a Space**, not a Contact, Circle, Invite, account, node, or token.
- Participant resolution should be **inspectable** — a user or operator must be able to trace from the selected Contact or Circle, through invite acceptance, into a Space roster entry with scoped capabilities.
- **Presence should be scoped to active Space contexts only** — not ambient across the app.
- Sync and hosted room semantics should be **deferred behind future ADRs**.
- The first implementation may remain **local-only and manual**, but it must preserve the separation between Contact, Invite, Participant, permission grant, and presence.

## Core definitions

| Term | Definition |
|---|---|
| **Space** | A future bounded collaboration context in which selected participants can work against one or more shared artifacts, tools, conversations, or live surfaces. Not currently implemented. |
| **Participant** | A runtime/context actor resolved into a specific Space roster. A Participant is not a Contact, Circle, Invite, account, node, or token. |
| **Participant Source** | The origin of a candidate participant — a Contact, Circle, Invite, manual entry, local account, remote node, or AI-mediated actor. |
| **Participant Roster** | The bounded list of Participants for a Space. |
| **Participant Role** | A convenience label or bundle of capabilities that applies to a Participant in a Space. Roles are not a substitute for explicit scoped capability grants. |
| **Capability Posture** | The set of capabilities granted to a Participant in a Space, scoped to target contexts. |
| **Presence Scope** | The bounded visibility of a Participant's activity within a Space. Not ambient across the app. |
| **Local Participant** | A Participant resolved from a local Codexify account. |
| **Remote Participant** | A Participant resolved from a remote Codexify node through an explicitly governed federation or trust path. |
| **Guest Participant** | A Participant without a durable Codexify account, pending future guest identity definitions. |
| **AI-Mediated Participant** | A Participant that is an AI actor or agent-mediated entity, not a human. |
| **Observer Participant** | A Participant with observation-only capability — may view activity but not act. |
| **Pending Participant** | A candidate participant for whom resolution or acceptance is in progress. |
| **Resolved Participant** | A Participant whose identity and capability posture have been determined for the Space. |
| **Suspended Participant** | A Participant temporarily disabled by policy, owner action, or unresolved safety state. |
| **Removed Participant** | A Participant no longer on the Space roster. |

### Important constraints

- A Contact is not a Participant.
- A Circle is not a Participant.
- An Invite is not a Participant.
- A Participant is not necessarily a Codexify account.
- A remote node identity is not a human identity.
- A participant role is not broad trust.
- Presence is not ambient identity.

## Participant resolution lifecycle

| State | Meaning | Allowed user expectations | Must not imply | Possible next states |
|---|---|---|---|---|
| `proposed` | Selected for possible participation but not yet invited or added. | The user may view, edit, or discard the proposal before any action. | That any invite has been sent or that participation is imminent. | `invited`, `removed`, or discarded |
| `invited` | An invite exists but participation is not active. | The user may see the invite state, delivery path, and expiry. | Acceptance, resolution, activation, presence, or capability use. | `pending_acceptance`, `accepted`, `revoked`, `blocked` |
| `pending_acceptance` | Acceptance or resolution is in progress. | The user may wait, resend where allowed, or revoke. | That the recipient can already enter or act. | `accepted`, `resolved`, `revoked`, `blocked` |
| `accepted` | The invite or join request was accepted. | The user may see that acceptance occurred. | Runtime participant activation, presence, or capability use. | `resolved`, `active`, `inactive`, `suspended`, `removed`, `revoked` |
| `resolved` | The system can map the participant to the required account/node/session identity for the target Space. | The user may see the resolved identity binding. | That the participant is actively present or capable. | `active`, `inactive`, `suspended`, `removed`, `revoked` |
| `active` | The participant is currently allowed in the Space under scoped capabilities. | The participant may use granted capabilities within the Space. | Access to unrelated Spaces, data, or capabilities. | `inactive`, `suspended`, `removed`, `revoked`, `blocked` |
| `inactive` | Rostered but not currently present or active. | The user may see the participant as inactive. | That the participant has been removed or cannot reactivate. | `active`, `removed`, `revoked` |
| `suspended` | Temporarily disabled by policy, owner action, or unresolved safety state. | The user may see the suspension reason category. | Permanent removal or that the participant is blocked. | `active`, `removed`, `revoked`, `blocked` |
| `removed` | No longer in the roster. | The user may see that removal occurred and the reason category. | Deletion of historical provenance or that the relationship is broken. | Terminal |
| `revoked` | Prior participation path was withdrawn. | The user may see revocation reason. | Future use of the revoked path. | Terminal |
| `blocked` | Safety posture prevents participation through that relationship path. | The user must explicitly unblock before new participation through that path. | Erasure of historical records. | Terminal |

### State transition rules

- `proposed` may move to `invited`, `removed`, or be discarded.
- `invited` may move to `pending_acceptance`, `accepted`, `revoked`, or `blocked`.
- `pending_acceptance` may move to `accepted`, `resolved`, `revoked`, or `blocked`.
- `accepted` may move to `resolved`, `active`, `inactive`, `suspended`, `removed`, or `revoked`.
- `resolved` may move to `active`, `inactive`, `suspended`, `removed`, or `revoked`.
- `active` may move to `inactive`, `suspended`, `removed`, `revoked`, or `blocked`.
- `inactive` may move to `active`, `removed`, or `revoked`.
- `suspended` may move to `active`, `removed`, `revoked`, or `blocked`.
- `removed`, `revoked`, and `blocked` are terminal for that participant entry.
- Acceptance, resolution, activation, presence, and permission are distinct events and must not be collapsed into one success state.

## Participant conceptual shape

A future participant record may conceptually contain:

```text
participant_id
space_id
participant_source_type     # contact, circle, invite, manual, account, node, agent
participant_source_id
contact_id
circle_id
invite_id
invite_attempt_id
account_id
local_node_id
remote_node_id
display_name
role
capability_posture
presence_scope
trust_snapshot
state
provenance
joined_at
last_active_at
suspended_at
removed_at
revoked_at
blocked_at
created_at
updated_at
```

This is a conceptual contract, not a database schema. Fields are illustrative and do not establish nullability, normalization, indexing, encryption, retention, ownership, or synchronization behavior. A future schema must be introduced through a separate architecture-impact implementation task and proof.

Sensitive fields must be classified before export or sync. Notably:
- `contact_id` — must not leak relationship state.
- `circle_id` — must not leak Circle membership.
- `invite_id` / `invite_attempt_id` — may reveal invite lineage.
- `trust_snapshot` — may contain trust evaluation data.
- `provenance` — may contain source discovery path.

## Space roster conceptual shape

A future Space roster entry may conceptually contain:

```text
space_id
owner_account_id
roster_entries               # collection of participant references
default_role_policy          # default role for new participants
default_capability_policy    # default capability set
presence_policy              # who can see whose presence
join_policy                  # open, invite-only, approval-required
invite_policy                # who can invite
audit_policy                 # what is logged
created_at
updated_at
archived_at
```

This is a conceptual contract, not a database schema.

Rules:
- A Space roster is the bounded participant list for a Space.
- Roster membership does not grant access outside the Space.
- Space owner or authority boundary must be explicit.
- Default policies are not ambient permission; they must resolve into scoped grants per participant and per target context.
- Participant changes must preserve provenance.

## Contact-to-participant relationship

- A Contact may be selected as a candidate participant.
- A Contact may require an Invite before becoming a Participant.
- A Contact may resolve to different participant identities across different Spaces.
- A Contact becoming `trusted` must not automatically make them a Space participant.
- Removing a Participant from a Space must not delete the Contact.
- Blocking a Contact should prevent or suspend participant resolution through that relationship path.

## Circle-to-participant relationship

- A Circle may be used to propose or invite multiple candidate participants from its membership.
- Circle expansion creates per-recipient participant candidates or invite attempts — it does not create a bulk roster entry.
- Circle membership is private by default and must not be revealed to other Space participants unless explicitly shared.
- A Circle is not itself a Participant.
- A Circle is not itself a permission grant.
- Circle defaults must resolve into scoped Space capabilities per participant.
- Blocked, revoked, archived, or unresolved Contacts require explicit handling before roster inclusion.

## Invite-to-participant relationship

- Accepted Invites may create candidate Participant records or trigger participant-resolution actions.
- Invite acceptance is not the same as Space activation — an accepted invite may require further resolution steps.
- Permission activation is distinct from participant activation — a resolved Participant may not yet have active capabilities.
- Revoked, expired, declined, or blocked Invites must not activate participants.
- Reissued invites must preserve lineage into participant resolution.
- Accepted invite lineage should remain inspectable from the Participant record.

## Account and node identity boundary

- Local account identity may back a Participant, but the Participant is still Space-scoped — account identity does not grant automatic Space access.
- Local node identity identifies the runtime/node boundary, not the human relationship.
- Remote node identity identifies a remote runtime boundary, not automatically a trusted human.
- Guest participants may lack a durable account until a future ADR defines guest identity and non-account participant resolution.
- AI-mediated participants require explicit classification and capability limits.
- Participant resolution must keep Contact, account, node, persona, and runtime session identity inspectably separate.

## Participant roles and capability posture

Conceptual roles (not runtime tokens yet):

| Role | Conceptual meaning |
|---|---|
| `owner` | Full authority over Space, roster, capabilities, and lifecycle. |
| `admin` | May manage roster, capabilities, and most Space settings. |
| `member` | Standard participation with configurable capabilities. |
| `editor` | May edit Space artifacts and content. |
| `commenter` | May comment but not edit. |
| `viewer` | May view Space content but not act. |
| `observer` | May observe presence and activity only. |
| `guest` | Time-bound or scope-limited participation. |
| `agent` | AI-mediated participant with explicit capability limits. |

Rules:
- These are conceptual roles, not runtime tokens yet.
- A future canonical token review may be required before implementation.
- Roles are convenience bundles or UI labels, not a substitute for scoped capability grants.
- Capabilities must remain explicit and scoped per participant and per target context.

Possible future capabilities (non-exhaustive):

- `can_view_space`
- `can_join_space`
- `can_view_presence`
- `can_send_message`
- `can_comment`
- `can_edit_documents`
- `can_share_artifacts`
- `can_invite_contacts`
- `can_manage_roster`
- `can_use_voice`
- `can_mount_tools`
- `can_export_space`
- `can_remove_participants`

## Mixed-trust participant handling

- Spaces may include participants with different trust states (trusted, invited, unknown, guest, remote, AI-mediated).
- The least-trusted participant must not become the default access baseline for the Space.
- Capabilities must be computed per participant and per target context — not derived from a single trust label.
- Relationship notes must not be exposed to participants.
- Circle membership must not leak to other participants.
- Presence visibility must be scoped by participant policy — not everyone sees everyone.
- Remote or guest participants should receive minimum viable capabilities until explicitly elevated.
- AI-mediated participants must not inherit human trust by association — they must be explicitly capability-scoped.
- A Space may have multiple trust tiers coexisting without collapsing privacy boundaries.

## Presence scope and visibility rules

- Presence is scoped to the active Space or active collaboration context.
- Presence is not app-wide.
- Being a Contact does not expose presence.
- Being invited does not expose presence.
- Being in a Circle does not expose presence.
- Being on a Space roster may allow scoped presence only if policy grants it.
- Presence events must not reveal unrelated documents, Contacts, Circle membership, relationship notes, or account activity.
- Ambient presence (visibility across Spaces without explicit consent) requires a future ADR and must not be assumed.

## Participant lineage and provenance

Each participant entry should preserve the following provenance:

- Source Contact, Circle, Invite, or manual action
- Selected by whom
- Accepted by whom, where applicable
- Authority that resolved the Participant
- Space target
- Participant role
- Granted capability posture
- State transitions
- Suspension/removal/revocation/block reason category, where available
- Timestamped lifecycle events
- Related shared-link or permission primitive, if later mapped

Rules:
- Participant lineage is required for auditability and user trust.
- Roster changes must not overwrite prior participant attempts.
- Removing or revoking a participant must preserve historical provenance unless a future retention/privacy policy explicitly allows deletion.

## Relationship to current runtime primitives

- Current shared links, `CollaborationPermission` rows, document-scoped WebSocket sessions, and `user_id` values remain implementation primitives.
- This ADR does not change them.
- Future Space participant resolution may map to those primitives through explicit adapters.
- Adapter output must remain inspectable so a user or operator can distinguish:
  - Contact
  - Circle
  - Invite
  - Space
  - Participant
  - runtime account
  - local node
  - remote node
  - token
  - shared link
  - permission grant
  - WebSocket session
  - presence event

## Export and restore posture

- Space participant records are likely sensitive exportable account data in the future, consistent with the [Account Export + Restore Contract](../account-export-restore-contract.md).
- Future export must decide whether to include removed, revoked, blocked, suspended, inactive, and guest participants.
- Future export must preserve participant lineage without reactivating membership.
- Restore must not silently re-add, re-invite, or reactivate participants.
- Restore must not leak prior Circle membership or relationship notes.
- No export or restore behavior is implemented by this ADR.

## Sync posture

- **Sync is deferred.**
- Space participant sync requires a future ADR.
- Future sync must define conflict handling for:
  - roster state
  - role changes
  - capability changes
  - revocation
  - removal
  - suspension
  - presence
  - remote node identity
  - split-brain participant state
- No sync behavior is implemented by this ADR.

## Consequences

- Future Space implementation has a participant-resolution decision frame.
- Future UI can represent participant status without guessing from Contacts, Invites, or permission rows.
- Future permission adapters must keep participant activation separate from invite acceptance and grant activation.
- Future presence work has a bounded scope — not ambient, not app-wide.
- Contact, Circle, Invite, Participant, permission, and session concepts stay separated.
- Mixed-trust Spaces can be designed without collapsing privacy boundaries.

## Risks

- Treating Contacts as Participants — collapsing relationship state into runtime roles.
- Treating accepted Invites as active sessions — skipping resolution and activation steps.
- Treating Space membership as broad trust — leaking data across context boundaries.
- Leaking Circle membership through roster creation.
- Leaking relationship notes through participant displays.
- Making presence ambient by accident — presence should be Space-scoped, not app-wide.
- Allowing remote node identity to masquerade as human identity.
- Giving guest or AI-mediated participants broad default capabilities.
- Restoring old participants as active after export/restore.
- Syncing roster changes before conflict and revocation semantics are defined.
- Collapsing permission grants into roles without scoped checks.

## Open questions

- Should first implementation store Space participants in Postgres?
- Is Space storage separate from participant storage?
- What is the smallest friends-and-family Space participant model?
- Can a Space exist with only local participants?
- Can a Participant exist without a Contact?
- How are guest participants upgraded to Contacts?
- Should roles be canonical tokens or UI labels over capability grants?
- How should participant removal interact with historical audit?
- Should blocked Contacts automatically suspend existing Space participant entries?
- How should remote node identity be verified?
- Can AI-mediated participants appear in the same roster as humans?
- How should roster conflicts resolve after restore or future sync?
- What is the boundary between Space participant, direct message recipient, and document collaborator?
- Should presence be visible to all roster members, or require explicit opt-in per participant?

## Required follow-up ADRs or tasks

- Space schema and storage ADR
- Space participant schema implementation task
- Space participant export/restore privacy ADR
- Space participant sync topology ADR
- Space presence scope ADR
- Space role and capability token review
- Invite-to-participant adapter proof task
- Contact-to-participant promotion task
- Circle-to-roster expansion task
- Manual Space participant UI MVP task
- Hosted room boundary ADR
- Remote node participant resolution ADR
- AI-mediated participant capability ADR

## Non-goals

- No schema implementation
- No migrations
- No runtime Space storage
- No participant storage
- No Space UI
- No participant roster UI
- No invite delivery
- No permission mutation
- No shared-link behavior change
- No collaboration permission behavior change
- No WebSocket behavior change
- No presence transport
- No hosted rooms
- No federation
- No remote node attachment
- No direct messaging
- No sync
- No export behavior
- No public directory
- No global identity
- No Guardian memory behavior change
- No collaboration tool mounting

## Validation / proof requirements before runtime adoption

Future implementation must prove, through automated tests or live proof:

- Clean-start migration (Space and participant schema created fresh)
- Existing-instance upgrade (schema added with zero data loss)
- Downgrade or rollback behavior where applicable
- Account-boundary enforcement (participants scoped to the correct account and Space)
- Space roster state transition validation (each transition gated and validated)
- Participant/account/node/persona separation (boundaries preserved)
- Invite-to-participant lineage preservation
- Contact-to-participant separation (Contact deletion does not affect Participant)
- Circle membership privacy (Circle membership not leaked through participant records)
- Role and capability scoping (roles map to explicit capabilities)
- Blocked/revoked/suspended participant handling
- No participant activation from expired, revoked, or declined invites
- No ambient presence leakage
- No unrelated document or Contact leakage from participant records
- Export does not reactivate removed, revoked, or blocked participants
- Restore does not resend invites or rejoin Spaces
- Remote node identity cannot masquerade as verified human identity
- AI-mediated participants remain capability-scoped

## Governing contracts

- [00-current-state.md](../00-current-state.md)
- [Contacts, Circles, and Collaboration Identity Contract](../contacts-circles-and-collaboration-identity.md)
- [ADR-043: Contact and Circle Storage Model](./043-contact-and-circle-storage-model.md)
- [ADR-044: Invite Lifecycle and Storage Model](./044-invite-lifecycle-and-storage-model.md)
- [Account Export + Restore Contract](../account-export-restore-contract.md)
- [Data and Storage](../data-and-storage.md)
