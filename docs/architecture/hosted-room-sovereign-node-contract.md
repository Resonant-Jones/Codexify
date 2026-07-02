# Hosted Room and Sovereign Node Participation Contract

> Classification: architecture contract / proposal boundary
> Status: proposed docs-only contract
> Normative language: "must", "must not", "may", "should", "non-goal", and "invariant" are intentional contract terms.

Purpose: Define how Codexify hosted chat rooms can support ordinary guests who do not run Codexify, hosted/private rooms for friends or collaborators, participant-owned Guardian nodes attached to a hosted room, room-scoped shared knowledge, participant-local intelligence, mention routing across host-side assistants and attached participant nodes, and explicit document ingestion into Shared Room KB or a participant's own Guardian node.

Last updated: 2026-06-30

## 1. Title and Classification

- Title: `Hosted Room and Sovereign Node Participation Contract`
- Classification: architecture contract / proposal boundary
- Status: proposed docs-only contract
- Scope: hosted rooms, participant classes, node attachment, shared room KB, mention routing, document handoff, and provenance

No runtime implementation is added by this document.

This document defines the proposal boundary only. Runtime implementation must later be aligned to a future ADR or explicitly opened as an architecture-impact implementation slice.

## 2. Purpose

Codexify rooms should let anyone join a conversation, while Codexify nodes let participants bring their own intelligence.

The north-star distinction this contract preserves:

- the hosted room owns the meeting surface
- participant nodes own participant intelligence

A hosted room may coordinate conversation, scheduling, membership, shared artifacts, and a room-scoped knowledge corpus. It must not silently absorb, merge, or impersonate the private intelligence of participants who have attached their own Guardian nodes.

## 3. Problem Statement

### Current failure mode

In the current hosted WebUI room, a non-host participant (for example Chris) can participate as a chat user, but all assistant invocations route through the host's hosted backend.

- When Chris invokes `@luna`, it resolves to Zac's hosted Luna.
- When Chris invokes `@guardian`, it currently still resolves through Zac's host-side chat backend.
- Chris has no attached Guardian node, no local KB access, and no ability to bring his own assistant intelligence into the room except through external ChatGPT/Atlas side chat.

### Why this matters

- Mention routing becomes misleading. An invocation that appears to call the speaker's own assistant actually runs against host-owned infrastructure.
- Participant identity appears present while participant intelligence is absent. The room reads as if Chris's own assistant is responding when only Zac's backend is executing.
- Host-side assistants can accidentally appear to represent non-host participant intelligence. A host Luna or host Guardian answering on behalf of a guest is not the same as the guest's own assistant answering.
- Document RAG can become host-owned or silently unavailable. Documents uploaded into a room may be indexed only by the host, with no path for a participant to ingest them into their own sovereign KB.

This contract exists to make the boundary between room-owned meeting surface and participant-owned intelligence explicit before any runtime implementation is attempted.

## 4. Core Principle

Contract language:

- A hosted room may coordinate conversation.
- A hosted room must not silently own, merge, crawl, or index participant-private intelligence.
- A participant may attach a sovereign Guardian node.
- A participant node owns its KB, documents, assistant profiles, tools, memory, retrieval policy, and disclosure rules.
- Room-visible outputs from participant nodes must carry provenance.

These principles are non-negotiable. Any future implementation that violates them is out of contract and requires a new ADR that explicitly revises this boundary.

## 5. Participant Classes

A hosted room recognizes exactly three participant classes.

### `guest`

- no Codexify install
- no attached node
- can participate through host-provided room permissions

A guest is a human (or human-driven client) present in the room without any Codexify node of their own. All intelligence available to a guest comes from host-approved room capabilities.

### `hosted_user`

- may have an account/profile on the host
- no attached sovereign node
- uses host-provided assistants and room capabilities

A hosted user has a richer identity footprint than a guest (for example a profile, preferences, or a host-side account) but still has no sovereign Guardian node attached. They use host-provided assistants and room capabilities under host policy.

### `node_participant`

- has an attached Guardian node
- can invoke participant-local assistants, KB retrieval, document ingest, and tool capabilities according to declared policy

A node participant brings sovereign intelligence into the room. Their attached node owns its own KB, documents, assistant profiles, tools, memory, retrieval policy, and disclosure rules. The room may see outputs from that node only after the node chooses to disclose them.

## 6. Room Ownership Model

### What the hosted room may own

- room id
- room membership
- message timeline
- live updates
- room-visible artifacts
- Shared Room KB
- room retention policy
- guest access controls
- room-visible receipts

### What the hosted room must not own by default

- private participant KB
- participant documents
- participant memory
- participant identity state
- participant assistant profile registry
- participant tool permissions
- participant-local retrieval output before disclosure

The room is the meeting surface, not a silent aggregation layer over participant intelligence. Anything in the "must not own" list may become room-visible only through an explicit, receipt-backed disclosure or transfer action defined later in this contract.

## 7. Participant Node Ownership Model

A participant Guardian node owns:

- assistant aliases and profiles
- default Guardian gateway configuration
- local KB and retrieval policy
- private documents and artifacts
- document ingest policy
- tools and capability grants
- memory and identity boundaries
- disclosure policy for room-visible outputs

The node, not the room, is the authority over these surfaces. The room may request contribution or disclosure, but the node decides whether, what, and how much to disclose.

This mirrors the existing Codexify sovereignty doctrine: chat history is not durable identity, deep identity is opt-in, and personas borrow identity rather than owning it. The same rule applies across the room/node boundary.

## 8. Participant Node Attachment Contract

A future participant node attachment is described by a manifest. The manifest advertises possible capabilities; actual invocation still requires policy checks. The manifest is not permission by itself.

### Required manifest fields

- `participantId`
- `displayName`
- `nodeId`
- `nodeEndpoint`
- `connectionState`
- `guardianAlias`
- `defaultAssistantAlias`
- `assistantAliases`
- `capabilities`
- `roomContributionPolicy`
- `documentIngestPolicy`

### Example manifest shape

```json
{
  "participantId": "chris.example",
  "displayName": "Chris",
  "nodeId": "guardian-chris-01",
  "nodeEndpoint": "https://guardian.chris.example/room",
  "connectionState": "attached",
  "guardianAlias": "guardian",
  "defaultAssistantAlias": "axis",
  "assistantAliases": ["axis", "luna", "scout"],
  "capabilities": [
    "assistant_invocation",
    "kb_retrieval",
    "document_offer",
    "document_receive",
    "shared_room_kb_query",
    "artifact_contribution"
  ],
  "roomContributionPolicy": {
    "discloseRetrievalCitations": true,
    "discloseArtifactSummaries": true,
    "disclosePrivateKbContents": false
  },
  "documentIngestPolicy": {
    "allowIngest": true,
    "requireExplicitAccept": true,
    "dedupeBeforeIngest": true
  }
}
```

### Required capability examples

- `assistant_invocation`
- `kb_retrieval`
- `document_offer`
- `document_receive`
- `shared_room_kb_query`
- `artifact_contribution`

### Manifest is advertisement, not authorization

The manifest advertises what a node can do. It does not authorize the room to do it. Every actual invocation, retrieval, contribution, or transfer must still pass the node's own policy checks and the room's contribution policy. A capability present in the manifest may still be denied for a specific turn by either side.

## 9. Mention Routing Model

Mention resolution for hosted rooms follows this priority order.

1. **Explicit node-qualified mention.**
   Examples: `@chris/axis`, `@zac/luna`, `@chris/guardian`.
   A node-qualified mention names both the participant and the assistant/profile on that participant's node. It resolves directly to that target.

2. **Speaker-local assistant/profile exact match.**
   `@luna` resolves inside the author's attached node first when the author has a node attached and that node advertises an assistant alias matching the mention exactly.

3. **Reserved Guardian gateway alias.**
   `@guardian` resolves to the author's local Guardian gateway when the author has an attached node.

4. **Host/room assistant fallback.**
   If the speaker has no attached node, route to host-side room assistants according to room policy.

5. **Single-assistant fallback.**
   If only one eligible assistant exists in the relevant scope, it may be selected.

6. **Ambiguous resolution.**
   Ask the author to choose rather than guessing. Ambiguity must never be silently resolved to a host-side assistant that then appears to speak for a participant.

### `@guardian` clarification

- `@guardian` is a reserved default invocation alias, not durable identity.
- If an assistant/profile literally named `Guardian` exists in the relevant scope, exact-match profile resolution may win.
- Otherwise `@guardian` proxies to the configured default Guardian gateway on the author's attached node.
- The alias does not grant cross-node KB access.
- The alias does not merge participant memory.
- The alias does not imply the room owns participant intelligence.

## 10. Assistant Provenance Display

Room-visible assistant outputs must carry provenance so participants can tell whose intelligence is actually responding.

### Expected provenance labels

- assistant alias
- source participant or host
- source node when applicable
- invocation id
- retrieval scope used:
  - `host_room`
  - `shared_room_kb`
  - `participant_local_kb`
  - `mixed_disclosed_context`
- disclosure scope

### Examples

- `Luna via Zac host`
- `Axis via Chris Guardian`
- `Guardian routed to Chris default assistant`
- `Room Assistant via Shared Room KB`

Provenance is not decorative metadata. A response that looks like it came from a participant's own assistant but actually ran on the host backend is an out-of-contract failure of this document.

## 11. Shared Room KB

Shared Room KB is a room-scoped coordination corpus, not an identity or private-memory corpus.

### It may store

- documents explicitly added to the room
- room-generated summaries
- room-visible artifacts
- agreed working notes
- retrieval citations and receipts
- document lifecycle metadata

### It must not store by default

- private participant KB contents
- participant memory
- assistant/persona identity state
- cross-node private documents
- hidden crawls of participant nodes
- anything not explicitly shared or generated within room policy

### Candidate document statuses

- `not_added`
- `uploaded`
- `parsing`
- `chunking`
- `embedding`
- `ready`
- `failed`
- `removed`

These are candidate statuses only until implemented as canonical tokens under the Runtime Protocol Token Contract. They must not be used as ad hoc runtime literals before tokenization.

## 12. Document Fingerprint and Dedupe Model

### Required future metadata

- `documentId`
- `contentHash`
- `normalizedTextHash`
- `filename`
- `mimeType`
- `sizeBytes`
- `uploadedBy`
- `sourceNodeId`
- `roomId`
- `createdAt`

### Participant-local dedupe outcomes

- `present_exact`
- `present_near_duplicate`
- `not_present`
- `unknown`
- `node_not_attached`

These values must become canonical tokens before runtime implementation. They are candidate vocabulary only.

## 13. Document Ingestion and Handoff Lifecycle

Document handling must distinguish separate participant intents. These are distinct actions, not aliases for the same operation.

### Participant-facing actions

- Add document to Shared Room KB.
- Ingest document into my Guardian.
- Send document directly to another Guardian.
- Use document temporarily for a room answer.
- Ignore document.

### Room-level lifecycle

- `document_uploaded`
- `document_room_ingest_requested`
- `document_room_ingested`
- `document_room_ingest_failed`
- `document_room_removed`

### Participant-level lifecycle

- `document_participant_ingest_available`
- `document_participant_ingest_requested`
- `document_participant_ingested`
- `document_participant_ingest_failed`
- `document_participant_ignored`

### Guardian-to-Guardian handoff lifecycle

- `document_offer_created`
- `document_offer_received`
- `document_offer_accepted`
- `document_offer_declined`
- `document_transfer_started`
- `document_transfer_completed`
- `document_transfer_failed`
- `document_ingest_ready`

Lifecycle names are candidate protocol events only and must be tokenized before code use. They must not be added to the Runtime Protocol Token Contract by this document.

## 14. Guest-Hosted Private Room Mode

In this mode, a Codexify operator hosts a private room for friends who do not run Codexify.

### Guests may

- chat
- upload files if allowed
- view room-visible artifacts if allowed
- invoke host-approved assistants if allowed

### Guests must not

- query the host's private KB directly
- silently enter the host's memory/identity layer
- receive participant-node capabilities without an attached node
- trigger cross-node ingest flows

A guest-hosted private room is a hosted meeting surface with explicit, bounded guest capabilities. It is not a path into the host's private intelligence, and it is not federation.

## 15. Multi-Node Hosted Room Mode

In this mode, a host room coordinates one or more attached Guardian nodes.

### Examples

- Chris hosts room, Zac attaches node.
- Zac hosts room, Chris attaches node.
- Third-party relay hosts room, Chris and Zac both attach nodes.
- Guest joins a room where other participants have nodes.

The room remains the meeting surface. Each attached node retains sovereignty over its own KB, documents, assistants, memory, and disclosure policy. The room sees only what nodes choose to disclose, and every disclosed output carries provenance.

A guest in a multi-node room is still a guest: no attached node, no participant-node capabilities. The presence of other participants' nodes does not upgrade a guest into a node participant.

## 16. Retrieval Rules

### Retrieval scopes

- `room_timeline`
- `shared_room_kb`
- `host_kb`
- `speaker_local_kb`
- `explicit_remote_node`
- `temporary_document_context`

### Invariants

- Speaker-local retrieval must run on the speaker's attached node.
- Host-side retrieval must not impersonate a participant's local KB.
- Explicit remote-node retrieval requires explicit node target and policy allowance.
- Shared Room KB retrieval must be limited to room-consented corpus.
- Retrieval outputs become room-visible only after disclosure by the responding node/assistant.

`temporary_document_context` is explicitly not a persistence path. It lets a document inform one room answer without being ingested into any KB. It must not silently become durable context.

## 17. Security, Consent, and Sovereignty Invariants

- No silent cross-node KB access.
- No silent document ingestion into participant nodes.
- No private participant memory writes from room activity unless explicitly governed by that participant node.
- No assistant/profile identity ownership by the room.
- No hidden crawling of participant endpoints.
- No automatic indexing of arbitrary host files.
- No transfer without offer/accept receipt.
- No invocation without provenance.
- No broad "federation" claim from room hosting alone.

Room hosting and federation are different surfaces. A hosted room with attached participant nodes is not, by itself, federation. Federation claims remain governed by existing federation/trust-policy doctrine and must not be widened by this document.

## 18. Failure Modes

The contract requires honest UI/runtime states for each of the following. None of these may be silently masked as a successful host-side response.

- participant node not attached
- participant node unreachable
- assistant alias ambiguous
- assistant alias not found
- shared room KB unavailable
- document ingest failed
- document already present in participant KB
- participant denied ingest
- transfer declined
- transfer failed
- retrieval unavailable
- host fallback used because speaker has no attached node

The last case is important: when a speaker has no attached node, host fallback is a legitimate, honest state only when it is labeled as host fallback. It must not be presented as the speaker's own assistant responding.

## 19. Non-Goals

This document does not:

- implement hosted rooms
- implement guest auth
- implement node attachment
- implement federation
- implement shared room KB
- implement document transfer
- implement message pagination
- implement live thread sync
- change provider routing
- change chat completion semantics
- change export/restore behavior
- add runtime protocol tokens
- widen current beta release claims

## 20. Future Implementation Slices

Candidate future atomic implementation slices, each requiring its own ADR-aligned task:

- live hosted room thread sync
- message pagination beyond 50 visible messages
- room artifact cards and document lifecycle display
- Shared Room KB ingestion pipeline
- participant node attachment manifest
- mention alias resolver
- assistant provenance labels
- participant-local KB retrieval invocation
- participant document dedupe check
- Guardian-to-Guardian document handoff
- guest private room invite flow
- multi-node room connection health surface

No slice in this list is authorized by this document. Each requires explicit ADR alignment, token-domain review, storage review, provenance review, identity review, and release-boundary verification before runtime code lands.

## ADR Impact

- Classification: Requires future ADR before runtime implementation.
- Governing ADRs/contracts:
  - current-state release boundary (`00-current-state.md`)
  - chat runtime contract (`chat-runtime-contract.md`)
  - runtime protocol token contract (`runtime-protocol-token-contract.md`)
  - account export and restore contract (`account-export-restore-contract.md`)
  - self-extending agent plugin system (`self-extending-agent-plugin-system.md`)
  - Pi invocation boundary contract (`pi-invocation-boundary-contract.md`)
  - agent protocol operations index (`agent-protocol-operations.md`)
  - existing queue/worker/chat runtime contracts where relevant
- Brief reason:
  - Hosted rooms with attached participant nodes introduce new room ownership semantics, participant intelligence boundaries, mention-routing rules, shared room KB semantics, document transfer/ingest lifecycles, and provenance obligations. This task may define the proposal boundary only. Runtime implementation must later be aligned to an ADR or explicitly opened as an architecture-impact implementation slice.

## Current-Truth Anchors

### What is true now

- Codexify is local-first beta hardening.
- The supported path remains local Docker Compose with local-only provider posture.
- The current hosted WebUI behavior observed in the active room routes assistant invocation through the hosting backend.
- A participant can be present as a chat user without having their own Guardian node attached.
- Existing chat/runtime docs distinguish route acceptance, task events, UI receipt, and durable transcript persistence.

### What is not yet true

- Hosted private guest rooms are not established as a supported release surface.
- Participant Guardian node attachment is not implemented.
- Cross-node mention routing is not implemented.
- Shared Room KB is not implemented as a governed room-scoped corpus.
- Participant-local KB retrieval from inside a hosted room is not implemented.
- Guardian-to-Guardian document transfer is not implemented.
- Per-participant document dedupe and ingest status are not implemented.

### What this task may assume

- The product direction should support hosted rooms for guests who do not self-host.
- The product direction should support rooms where one host can coordinate one or more attached Guardian nodes.
- The architecture must preserve participant-local intelligence and avoid silently merging private KBs into the room.
- Shared Room KB is valuable when scoped to explicit room-consented artifacts.
- Document ingestion into a participant node must be explicit and receipt-backed.

## Invariants

- Do not change runtime behavior.
- Do not add routes, workers, migrations, or frontend behavior.
- Do not add runtime protocol tokens.
- Do not claim hosted rooms, node attachment, multi-node routing, shared room KB, or cross-node document transfer are implemented.
- Do not widen the supported beta release surface.
- Participant-private intelligence must never be silently merged into a room.
- Every room-visible participant-node output must carry provenance.
- Every document transfer or ingest must be explicit and receipt-backed.

## Proof Surface

- `test -f docs/architecture/hosted-room-sovereign-node-contract.md`
- `grep -n "Hosted Room and Sovereign Node Participation Contract" docs/architecture/hosted-room-sovereign-node-contract.md`
- `grep -n "hosted-room-sovereign-node-contract.md" docs/architecture/README.md`
- `grep -n "Do not assume hosted rooms" docs/architecture/00-current-state.md || true`
- `git diff --check`

No automated runtime tests apply because this is a docs-only architecture contract.

## Documentation Follow-Through

- Create `docs/architecture/hosted-room-sovereign-node-contract.md`.
- Add a concise doc-map entry to `docs/architecture/README.md`.
- Add a concise note to `docs/architecture/00-current-state.md` clarifying this is future architecture and not current release behavior.
- Do not edit runtime code, ADRs, migrations, routes, or frontend behavior.
