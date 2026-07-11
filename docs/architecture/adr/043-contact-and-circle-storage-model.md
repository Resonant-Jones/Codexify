# ADR-043: Contact and Circle Storage Model

## Status

**Status:** Proposed

## Context

The [Contacts, Circles, and Collaboration Identity Contract](../contacts-circles-and-collaboration-identity.md) has defined the social vessel — Contacts, Circles, Invites, Spaces, trust states, discovery paths, and capability grants — as proposal-only architecture semantics. Users collaborate with Contacts, Circles, or Spaces, not raw IDs, emails, permission rows, or tokens.

The next unanswered question is where that relationship state lives and how private, portable, recoverable, and future-syncable it should be. Before any schema, UI, invite, Circle, or Space implementation can proceed, Codexify needs an explicit storage decision frame for ownership, account scope, exportability, privacy defaults, and future sync posture.

This ADR is required before schema, UI, invite, Circle, or Space implementation.

## Decision frame

The storage posture for Contacts and Circles must reconcile five axes. These are not mutually exclusive implementation flags. They are design postures that must be reconciled into one coherent storage model.

| Axis | Core question |
|---|---|
| **Local-only** | Is Contact/Circle state disposable device-only state? |
| **Account-scoped** | Is Contact/Circle state attached to the user's Codexify account boundary? |
| **Exportable** | Can Contacts and Circles be exported and restored as user-owned data? |
| **Syncable** | Should Contacts and Circles synchronize across devices or nodes? |
| **Private-by-default** | Is Contact and Circle data treated as sensitive by default? |

## Recommended default posture

Contacts and Circles should be **account-scoped, exportable, and private-by-default**. Syncability should be deferred as a future opt-in capability behind a follow-up ADR. The first runtime implementation may remain local-first, but it must not define Contacts and Circles as disposable device-only state unless the user explicitly chooses that mode.

Rationale:

- **Account-scoped** gives the user durable recovery of relationship state across device loss or reinstall, without requiring sync topology.
- **Exportable** gives the user ownership and portability — their relationship data is not trapped in a single database or device.
- **Private-by-default** treats Contact and Circle data as sensitive from day one, which it is — relationship notes, trust state, block state, invite history, and external handles are not public metadata.
- **Sync deferred** avoids committing to a conflict-prone sync topology before the network model, identity binding, and trust policy are proven.

## Storage-axis tradeoff table

| Consideration | Local-only | Account-scoped | Exportable | Syncable | Private-default |
|---|---|---|---|---|---|
| **Simplicity** | ✅ Highest — no account boundary needed | ✅ Low — attach to existing account | ⚠️ Medium — needs export schema and sensitive-data handling | ❌ Complex — topology, conflict, encryption, revocation | ✅ Straightforward — deny by default |
| **Offline-first** | ✅ Native — no network dependency | ✅ Cacheable — account scope works offline | ✅ Via export — but export is user-driven, not automatic | ⚠️ Conflict-prone — requires merge policy | ✅ No leak risk by default |
| **Portability** | ❌ None — lost on device loss | ❌ Tied to account — survives device loss within account | ✅ Yes — user can move between instances | ✅ Implied — sync is a form of portability | ✅ With encrypted export |
| **Collaboration readiness** | ❌ No — no durable relationship state | ⚠️ Partial — account scope anchors identity | ⚠️ Partial — exportable state can seed a new instance | ✅ Yes — sync enables multi-device collaboration | ⚠️ Requires explicit grant model |
| **Recovery path** | ❌ Lost on device loss | ✅ Account restore — data survives reinstall | ✅ Via export file — user-initiated recovery | ✅ Via sync — automatic recovery | ✅ Encrypted at rest |
| **Privacy risk** | ✅ Low — never leaves device | ⚠️ Medium — account boundary must be secured | ⚠️ Medium — export file must be protected | ❌ Higher — sync multiplies exposure surfaces | ✅ Low — deny by default |
| **Migration complexity** | ✅ None — no migration needed | ⚠️ Low — schema additions only | ⚠️ Medium — export schema, integrity, versioning | ❌ High — conflict, merge, topology, encryption | ✅ High — but sets correct baseline |
| **Future sync readiness** | ❌ None — no structure to sync | ⚠️ Medium — account scope anchors sync | ✅ Good — export schema is a natural sync shape | ✅ Native — designed for sync | ⚠️ Medium — privacy must survive sync |

## Decision details

- Contact and Circle records are **user-owned relationship records**. They belong to the authenticated/local account boundary, not to a global directory.
- Once implemented, they should be stored as **private account-scoped state**.
- They should be **exportable as sensitive user-owned data** in a future export model.
- They must **not be globally discoverable**.
- They must **not be synced** unless a future ADR defines sync topology, conflict policy, encryption, revocation, and remote trust.
- The following fields must be treated as **sensitive**: relationship notes, blocked state, archived state, invite history, and external handles.
- **Circle membership must be private by default**. Circle selection may later expand into scoped grants or invites, but Circle membership is not itself authority.

## Data classification

The following Contact and Circle data elements are classified as **sensitive**:

- Display names when user-authored as relationship labels
- Relationship notes
- External handles
- Email addresses
- Node handles
- Trust state
- Blocked state
- Archived state
- Invite history
- Last collaborated timestamps
- Circle membership
- Capability defaults

Sensitive data must be handled with the same care as chat content and personal facts. It must not be leaked through ambient API surfaces, default export scopes, or incidental UI exposure. Future implementation must define explicit handling for each sensitive class.

## Ownership model

The following ownership boundaries must remain inspectably separate:

| Boundary | Meaning |
|---|---|
| **Local user ownership of Contact relationship metadata** | The local user owns aliases, relationship notes, preferences, and default choices about a Contact. |
| **Account boundary for future persisted storage** | The Codexify account owns the durable storage and authorization boundary for Contact and Circle state when persisted. |
| **Runtime participant identity** | A participant in a Space or session is a resolved runtime actor; it is not the same as a Contact record. |
| **External identity handles** | Email addresses, node handles, and service-specific handles are resolution hints, not canonical identity. |
| **Local node identity** | The identity of the Codexify node; it is not a human relationship. |
| **Remote node identity** | The identity of a separate Codexify node reached through an explicitly governed path; it is not automatically a trusted contact. |

These boundaries must not collapse. A Contact is not necessarily an account. A node identity is not a human relationship. A participant identity is not a Contact record.

## Account-scope meaning

- **Account-scoped does not mean hosted cloud account by default.**
- In the local-first beta context, account-scoped means attached to the local Codexify user/account boundary and protected by that boundary.
- Hosted or remote account semantics remain future work and require a separate ADR.
- The account scope ensures that Contact and Circle state survives device loss or reinstall when the account boundary is preserved.
- Account scope must not be misinterpreted as global discoverability, cross-node sync, or hosted identity.

## Export and restore posture

- Contacts and Circles should be exportable in a future account export model, consistent with the [Account Export + Restore Contract](../account-export-restore-contract.md).
- Export must treat them as **sensitive** data.
- Future export must decide whether to include:
  - blocked contacts
  - revoked contacts
  - archived contacts
  - expired invites
  - external handles
  - relationship notes
  - invite history
- Export scope may offer explicit opt-in options for sensitive subsets.
- Restore must **preserve identity lineage** and avoid silent merging of human relationships.
- Restore must detect potential duplicate Contacts and present them for user resolution rather than silently merging.
- No export behavior is implemented by this ADR.

## Sync posture

- **Sync is deferred.**
- Sync requires a future ADR before any implementation.
- Future sync must define:
  - topology (device-to-device, device-to-relay, relay-to-device)
  - conflict handling
  - encryption at rest and in transit
  - revocation semantics
  - remote trust policy
  - merge policy
  - deletion semantics
  - split-brain detection
- No sync behavior is implemented by this ADR.
- The first runtime implementation may remain local-only, but must not define Contacts and Circles as disposable device-only state unless the user explicitly chooses that mode.

## Privacy defaults

- Contacts private by default.
- Circles private by default.
- Relationship notes private by default.
- Presence not ambient.
- Circle membership not revealed to recipients by default.
- Blocked contacts cannot receive new invites or grants unless explicitly unblocked.
- Discovery must remain invite-first and consent-first.
- No Contact or Circle data is globally discoverable by default.
- Privacy defaults must be enforceable at the storage layer, not just the UI layer.

## Relationship to Contacts, Circles, Invites, and Spaces

- This ADR narrows the storage posture for Contact and Circle records only.
- It does not fully decide Invite storage.
- It does not decide Space storage.
- Invite and Space storage need follow-up ADRs.
- Contact and Circle storage must be designed so Invites and Spaces can reference them later without collapsing the concepts.
- A Contact record should be referenceable by an Invite's sender or target.
- A Circle should be referenceable by a Space's participant roster.
- But an Invite is not a Contact, and a Space is not a Circle.

## Relationship to current runtime primitives

- Current shared links, permission rows, WebSocket sessions, and `user_id` values remain implementation primitives.
- This ADR does not change them.
- Future Contact/Circle runtime work may map selections onto those primitives through explicit adapters.
- The adapter boundary must remain inspectable — a user or operator must be able to distinguish the selected Contact or Circle from the resolved account, link, permission grant, participant, or session.
- Current backend primitives are implementation details from the user perspective. Contacts and Circles should become the user-facing layer above shared links and permission rows while preserving current ownership, authentication, access, and audit semantics.

## Consequences

- Future schema work has a recommended direction: account-scoped, private, exportable, with sync deferred.
- Future UI can assume Contacts/Circles are durable account-scoped relationship state, not one-off tokens.
- Export/restore requirements must be considered from the first implementation task.
- Sync is intentionally not bundled into the first storage implementation.
- Privacy and sensitivity are first-order requirements, not afterthoughts.
- The account boundary must be well-defined before schema work proceeds.

## Risks

- Premature schema could encode the wrong identity assumptions (e.g., treating email as canonical).
- Sync could leak sensitive relationship data if introduced too early.
- Account-scoped storage could be misunderstood as hosted/global identity.
- Export could leak relationship notes or blocked-state history if not scoped.
- Circle expansion could accidentally reveal private group membership.
- Treating email as canonical would break the Contact abstraction — a Contact is not an email address.
- Merging export/restore Contact data could silently merge human relationships without user awareness.
- First implementation could accidentally create a de facto sync surface if the storage layer is not designed with privacy boundaries.

## Open questions

- Should the first implementation store Contacts/Circles in Postgres under local account scope?
- Should relationship notes be separately encrypted or redacted from default export?
- Should blocked Contacts be exported by default?
- How should duplicate Contacts be detected without silent merging?
- Should Circle membership support nested Circles?
- How should Contact identity survive account export/restore across machines?
- What is the smallest friends-and-family Contact Card?
- How should future sync resolve divergent trust states?
- Can a Contact be shared between local accounts on the same node?
- What is the boundary between Contact, account, persona, and node?

## Required follow-up ADRs or tasks

- Contact and Circle schema ADR or implementation task
- Contact export/restore privacy ADR
- Invite lifecycle and storage ADR
- Space participant resolution ADR
- Contact sync topology ADR
- Presence scope and ambient visibility ADR
- Contact UI MVP task
- Manual Contact creation task
- Circle selection and scoped grant task

## Non-goals

- No schema implementation
- No migrations
- No runtime storage
- No UI
- No invite implementation
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
- No changes to current shared links, permission rows, WebSocket sessions, or `user_id` primitives

## Validation / proof requirements before runtime adoption

Future implementation must prove, through automated tests or live proof:

- Clean-start migration (Contacts/Circles schema created fresh)
- Existing-instance upgrade (schema added with zero data loss)
- Downgrade or rollback behavior where applicable
- Account-boundary enforcement (Contacts/Circles scoped to the correct account, not cross-account visible)
- Export and restore behavior (Contacts/Circles included, sensitive subsets properly handled)
- Blocked/revoked/private-state handling (blocked contacts cannot receive new invites or grants)
- Circle membership privacy (membership not revealed to recipients by default)
- No public-discovery side effects (no global search, no ambient discovery)
- No ambient presence leakage (presence scoped to active contexts only)
- Tests for Contact/account/node/persona separation (boundaries preserved, not collapsed)

## Governing contracts

- [00-current-state.md](../00-current-state.md)
- [Contacts, Circles, and Collaboration Identity Contract](../contacts-circles-and-collaboration-identity.md)
- [Account Export + Restore Contract](../account-export-restore-contract.md)
- [Data and Storage](../data-and-storage.md)
