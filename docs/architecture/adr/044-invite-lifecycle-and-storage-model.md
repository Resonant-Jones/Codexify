# ADR-044: Invite Lifecycle and Storage Model

## Status

**Status:** Proposed

## Context

[Contacts, Circles, and Collaboration Identity](../contacts-circles-and-collaboration-identity.md) defines the social vessel — Contacts, Circles, Invites, Spaces, trust states, discovery paths, and capability grants — as proposal-only architecture semantics.

[ADR-043: Contact and Circle Storage Model](./043-contact-and-circle-storage-model.md) defines where Contacts and Circles should live: account-scoped, exportable, private-by-default, with sync deferred.

Invites define how relationship intent becomes a bounded access request or participant transition. An invite bridges the gap between "I have a relationship record" (Contact) and "we share a context" (permission grant, Space participant, collaborative session). Without an explicit invite contract, invites risk collapsing into raw tokens, shared links, permission rows, or ambient identity leaks.

This ADR is required before invite schema, invite UI, invite routes, permission mutation, Circle sharing, Space participant resolution, or collaborative-tool mounting.

## Decision frame

The invite model must be designed across these axes. These are design dimensions, not implementation fields.

| Axis | Core question |
|---|---|
| **Lifecycle state** | What states does an invite transition through, and what rules govern each transition? |
| **Storage ownership** | Who owns the invite record — sender, recipient, or both? |
| **Target scope** | What can an invite target — a Contact, Unknown Recipient, artifact, Circle, Space? |
| **Capability scope** | What capabilities can be requested or granted through an invite? |
| **Delivery method** | How is the invite transported to the recipient? |
| **Recipient resolution** | How does an Unknown Recipient become a known identity? |
| **Expiry and revocation** | How does an invite expire or get revoked? |
| **Contact promotion** | How does invite acceptance create or update a Contact? |
| **Permission mapping** | How does invite acceptance map to runtime permission grants? |
| **Privacy and export behavior** | How are invites treated as sensitive data? |

## Recommended default posture

- Invites should be **account-scoped, private-by-default, lineage-preserving, expiry-aware, revocable, and exportable as sensitive account data**.
- Invite delivery should be **transport-agnostic** — the invite record does not require a specific delivery mechanism.
- Invite tokens should be **transport artifacts, not identity** — a token does not prove account ownership, consent, or trust.
- **Sync should be deferred** behind a future ADR.
- The first runtime implementation may support only local/manual invite records, but it must preserve the lifecycle and lineage model defined here.

## Invite lifecycle state machine

| State | Meaning | Allowed user expectations | Must not imply | Possible next states |
|---|---|---|---|---|
| `draft` | Prepared locally but not sent. | The user may edit, discard, or send the draft. | That any recipient has been notified or that delivery will succeed. | `sent`, `revoked`, or discarded |
| `sent` | Issued through an explicit delivery path. | The user may see the delivery path, target, expiry, and pending outcome. | Delivery, opening, acceptance, identity verification, or capability use. | `opened`, `accepted`, `declined`, `expired`, `revoked`, `blocked` |
| `opened` | The recipient or delivery surface has opened it, if the path can prove that event. | The user may see that the invite was opened. | Acceptance, consent, identity verification, or capability use. | `accepted`, `declined`, `expired`, `revoked`, `blocked` |
| `accepted` | The requested relationship or context action was accepted. | The user may see the acceptance and use the accepted resolution within its declared scope. | Broad trust, permanent availability, access to unrelated contexts, or blanket future permission. | Terminal for that invite attempt |
| `declined` | The recipient declined the request. | The user may reissue a new invite with lineage to the previous attempt. | That the recipient is unreachable, blocked, or that the relationship is broken. | Terminal for that invite attempt |
| `expired` | The invite passed its declared expiry without acceptance. | The user may reissue a new invite with lineage. | That the recipient saw or declined the invite. | Terminal for that invite attempt |
| `revoked` | The sender or governing authority withdrew it. | The user may reissue a new invite with lineage. | Erasure of already-seen data or proof that a remote party forgot the invite. | Terminal for that invite attempt |
| `blocked` | Delivery or acceptance is prohibited by a block or policy boundary. | The user must explicitly unblock before a new invite can reach the recipient through that path. | Erasure of historical records or a claim that the other party is malicious. | Terminal for that invite attempt |

### State transition rules

- `draft` may move to `sent`, `revoked`, or be discarded.
- `sent` may move to `opened`, `accepted`, `declined`, `expired`, `revoked`, or `blocked`.
- `opened` may move to `accepted`, `declined`, `expired`, `revoked`, or `blocked`.
- `accepted` is terminal for that invite attempt, but may create follow-up permission or Contact actions.
- `declined`, `expired`, `revoked`, and `blocked` are terminal for that invite attempt.
- Reissuing an invite creates a new invite attempt with lineage to the previous one.
- Delivery, opening, acceptance, and permission activation are distinct events and must not be collapsed into one success state.

## Invite payload conceptual shape

A future invite payload may conceptually contain:

```text
invite_id
invite_attempt_id
sender_contact_id
sender_account_id
recipient_contact_id
unknown_recipient
target_type
target_id
target_display_name
requested_capabilities
granted_capabilities
delivery_method
delivery_address_hash
token_ref
expires_at
state
provenance
source_circle_id
source_space_id
accepted_contact_id
created_at
updated_at
opened_at
accepted_at
declined_at
expired_at
revoked_at
blocked_at
```

This is a conceptual contract, not a database schema. Fields are illustrative and do not establish nullability, normalization, indexing, encryption, retention, ownership, or synchronization behavior. A future schema must be introduced through a separate architecture-impact implementation task and proof.

Sensitive fields must be classified before export or sync. Notably:
- `delivery_address_hash` — delivery targets are sensitive.
- `token_ref` — token references must not expose raw tokens.
- `requested_capabilities` / `granted_capabilities` — may reveal intent or permission boundaries.
- `provenance` — may reveal discovery path and relationship context.
- `source_circle_id` — must not leak Circle membership.

## Invite storage posture

- Invites should be **account-scoped** — owned by the sender's account boundary.
- Invites should be **private by default** — not globally discoverable, not leaked through ambient API surfaces.
- Invites should be **exportable as sensitive account data** in a future export model.
- Invite state transitions should **preserve lineage** — no overwriting of prior attempts.
- Invite delivery artifacts (tokens, links, references) should **not be treated as durable identity**.
- Invite records must be **separate from Contact records** — an invite is not a Contact.
- Invite records must be **separate from permission grants** — an accepted invite is not yet an active permission.
- Invite records must be **separate from Space participant records** — an invited participant is not yet a Space member.
- Invite storage must support future references to Contacts, Circles, Spaces, and target artifacts without collapsing those concepts.

## Invite lineage and provenance

Each invite attempt should preserve the following provenance:

- Original authoring action
- Target artifact or Space
- Selected Contact or Circle, if any
- Unknown recipient information, if any
- Delivery method
- Capability request/grant posture
- Token or transport reference
- Timestamps for each lifecycle transition
- Reissue lineage (parent invite attempt reference)
- Revocation reason, where available
- Block reason category, where available

Rules:
- Invite lineage is required for auditability and user trust.
- Reissued invites must not overwrite previous attempts.
- Revocation must not delete historical provenance unless a future retention/privacy policy explicitly allows it.

## Invite-to-Contact relationship

- An invite may target an existing Contact.
- An invite may target an Unknown Recipient (no existing Contact).
- Accepting an invite may offer to create or update a Contact Card, depending on user choice and trust posture.
- Accepting an invite must not automatically mark a Contact as `trusted`.
- Declining, expiring, or revoking an invite must not delete the Contact.
- Blocking a recipient may affect future invite eligibility but must be represented as a trust/safety state, not silent deletion.
- Acceptance of one invite must not silently accept unrelated future invites from the same sender.

## Invite-to-Circle relationship

- A Circle may be used to draft invites to multiple Contacts.
- Circle expansion creates scoped invite attempts or grants per recipient.
- Circle membership is private by default and must not be revealed to recipients unless explicitly shared.
- A Circle is not itself an invite.
- A Circle is not itself a permission grant.
- Blocked or revoked Contacts must be excluded, or require explicit operator confirmation, before invite creation from a Circle.
- Circle-derived invite batches should preserve the source Circle reference for provenance, but must not expose the full membership list to recipients.

## Invite-to-Space relationship

- A future Space may use invites to add participants.
- Space participant resolution is not implemented by this ADR.
- A Space invite must identify the target Space, requested capabilities, and participant posture.
- Accepting a Space invite does not imply access to unrelated Spaces or artifacts.
- Space invite storage and participant resolution require a future ADR.

## Invite-to-permission relationship

- Invites may later create or resolve `SharedLink` records.
- Invites may later create or resolve `CollaborationPermission` records.
- **Permission activation is distinct from invite acceptance.** An invite may be accepted without automatically activating every requested permission.
- Current shared links and permission rows remain implementation primitives.
- Future runtime adapters must remain inspectable so a user or operator can distinguish:
  - selected Contact
  - selected Circle
  - invite
  - token
  - shared link
  - permission grant
  - participant
  - session

## Invite token boundary

- Tokens are transport artifacts.
- Tokens are not Contacts.
- Tokens are not identities.
- Tokens are not broad authority.
- Tokens must be scoped to target, capability, expiry, and issuer.
- Token leakage is high impact.
- Token rotation and revocation need future proof.
- Token hash storage should be preferred over raw token storage if runtime implementation later stores invite tokens.

## Capability request and grant boundary

- **Requested capabilities** and **granted capabilities** are distinct fields.
- A requested capability does not mean an approved capability.
- A granted capability must be scoped to a target (artifact, Space, participant context).
- Future conceptual capabilities may include:

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

- A future canonical token review may be required before runtime implementation if these become contract-bearing storage or API values.

## Privacy and safety defaults

- Invites private by default.
- Invite history sensitive by default.
- Recipient delivery addresses sensitive by default.
- Circle-derived invite batches private by default — Circle membership must not be revealed to recipients.
- Presence must not be exposed merely because an invite exists.
- Blocked recipients must not receive new invite attempts unless explicitly unblocked.
- Unknown recipients must not become globally discoverable.
- Invite delivery must be explicit and user-initiated.
- Invite acceptance must not silently expose relationship notes, Circle membership, or broader Contact data.

## Expiry, revocation, and blocking rules

- Every runtime invite should have an expiry posture.
- Revocation must fail closed for future use where the runtime can enforce it.
- Revocation does not imply remote deletion of already-seen data.
- Blocking prevents future invites and grants through that relationship path.
- Expired invites may be reissued only as new attempts with lineage.
- Blocked and revoked are distinct states: blocked is recipient-level safety state; revoked is invite-level withdrawal.

## Delivery method boundary

Possible future delivery methods:

- manual copy (share a link or code directly)
- QR code
- email
- local network handoff
- remote node handoff
- future notification channel

Rules:
- Delivery methods are transport choices, not identity proof.
- No delivery method is implemented by this ADR.
- Email is optional and must not become the only identity carrier.
- QR, local network, and remote node behavior require future ADRs or tasks.

## Export and restore posture

- Invites should be considered sensitive exportable account data, consistent with the [Account Export + Restore Contract](../account-export-restore-contract.md).
- Future export must decide whether to include:
  - expired invites
  - revoked invites
  - declined invites
  - blocked invites
  - accepted invite history
  - token references
- Future export must decide how to represent token references without making expired or revoked tokens usable.
- Restore must preserve invite lineage and avoid silently activating permissions.
- Restore must not silently resend invites.
- No export or restore behavior is implemented by this ADR.

## Sync posture

- **Sync is deferred.**
- Invite sync requires a future ADR.
- Future sync must define conflict handling for:
  - invite state transitions
  - expiry clocks
  - revocation
  - recipient resolution
  - token invalidation
- No sync behavior is implemented by this ADR.

## Consequences

- Future invite implementation has a lifecycle and storage decision frame.
- Future UI can show invite state without guessing from token or permission state.
- Future permission adapters must keep invite acceptance separate from grant activation.
- Contact and Circle runtime work can proceed later without turning Contacts into tokens.
- Export/restore and privacy requirements are present from the first implementation task.
- The invite lifecycle state machine provides a shared vocabulary across schema, UI, routes, and permission work.

## Risks

- Treating tokens as identity instead of transport artifacts.
- Collapsing invite acceptance into broad trust.
- Collapsing Circle selection into broad permission.
- Leaking Circle membership through invite batches.
- Exporting raw active tokens.
- Restoring old invites as active.
- Sending invites automatically during restore or sync.
- Treating email as canonical identity.
- Introducing sync before revocation and conflict semantics are defined.
- Confusing accepted invite with active collaboration session.
- Storing invite delivery addresses without hash or encryption.

## Open questions

- Should first implementation store invites in Postgres under the sender's account scope?
- Should invite tokens be stored only as hashes?
- Should expired, revoked, and declined invites be included in default export?
- What is the minimum friends-and-family invite flow?
- Should opening an invite be tracked if the transport cannot prove it?
- Should invite acceptance create a Contact automatically or ask first?
- How long should default invite expiry be?
- Should Circle-derived invite batches have a parent batch record?
- How should blocked contacts affect historical invites?
- How should invite state resolve after restore across machines?
- What is the boundary between invite, notification, message, and permission grant?
- Which invite lifecycle strings need canonical token treatment before runtime implementation?

## Required follow-up ADRs or tasks

- Invite schema implementation task
- Invite token and revocation proof task
- Invite export/restore privacy ADR
- Contact promotion from invite ADR or task
- Circle-derived invite batch ADR or task
- [Space participant resolution ADR](./045-space-participant-resolution-model.md)
- Delivery method policy ADR
- Presence scope and ambient visibility ADR
- Manual invite UI MVP task
- Invite-to-permission adapter proof task

## Non-goals

- No schema implementation
- No migrations
- No runtime invite storage
- No invite UI
- No invite delivery
- No email sending
- No QR generation
- No local network discovery
- No remote node handoff
- No permission mutation
- No shared-link behavior change
- No collaboration permission behavior change
- No Space implementation
- No sync
- No export behavior
- No public directory
- No global identity
- No hosted account semantics
- No federation
- No direct messaging
- No Guardian memory behavior change
- No collaboration tool mounting

## Validation / proof requirements before runtime adoption

Future implementation must prove, through automated tests or live proof:

- Clean-start migration (invite schema created fresh)
- Existing-instance upgrade (schema added with zero data loss)
- Downgrade or rollback behavior where applicable
- Account-boundary enforcement (invites scoped to the correct account)
- Invite state transition validation (each transition gated and validated)
- Token hash or token secrecy behavior (raw tokens not stored in plaintext)
- Expiry enforcement (expired invites cannot be accepted)
- Revocation enforcement (revoked invites cannot be used)
- Blocked-recipient enforcement (blocked contacts cannot receive new invites)
- No permission activation before acceptance and explicit grant
- No raw token leakage in export
- Restore does not reactivate expired or revoked invites
- Restore does not resend invites
- Circle membership privacy (membership not leaked through invite batches)
- No ambient presence leakage
- Contact/invite/permission/session separation boundaries preserved

## Governing contracts

- [00-current-state.md](../00-current-state.md)
- [Contacts, Circles, and Collaboration Identity Contract](../contacts-circles-and-collaboration-identity.md)
- [ADR-043: Contact and Circle Storage Model](./043-contact-and-circle-storage-model.md)
- [Account Export + Restore Contract](../account-export-restore-contract.md)
- [Data and Storage](../data-and-storage.md)
