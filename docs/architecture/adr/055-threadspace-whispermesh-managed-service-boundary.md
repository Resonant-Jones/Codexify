# ADR-055: ThreadSpace ↔ WhisperMesh Managed-Service Boundary

## Status

Proposed — architecture review required. This is a documentation-only decision. It authorizes no runtime implementation, protocol deployment, hosted service, release claim, or change to [00 Current State](../00-current-state.md).

## Context

Codexify is a local-first system in beta hardening. Its current collaboration, federation, sync, and relay seams are code-path evidence, not supported ThreadSpace behavior. The HomeBase, Space, Room, and participant-node architecture establishes a sovereignty direction: a Room is a bounded collaboration context, participant nodes retain participant-private intelligence, and durable Codexify state remains under Codexify authority.

WhisperMesh has conceptual and local control-plane groundwork for node registration, discovery, and session reasoning. Its documented connection-lifecycle and metadata-only platform postures are contracts, not proof of production signature verification, durable service authorization, NAT traversal, TURN fallback, opaque relay operation, or interoperability.

ThreadSpace needs a connectivity path, but a managed connectivity provider must not become an accidental authority over identity, Room membership, Room capabilities, private context, durable Room state, local tools, provider choice, participant-private intelligence, or cryptographic content keys.

## Decision

1. **Codexify and ThreadSpace remain the sovereignty authority.** A Codexify HomeBase or Vault owns local identity binding, Room policy, capability authority, private context, durable collaboration state, artifact lineage, and user-facing sovereignty. A Room or explicitly delegated Vault authority issues scoped collaboration grants.
2. **WhisperMesh Protocol is the provider-neutral compatibility contract.** It defines interoperable schemas and bounded token domains. It is not an identity provider, service operator, or source of Room authority.
3. **WhisperMesh Network Assist is an optional managed implementation.** It may provide privacy-minimized discovery, signaling, STUN/TURN assistance, scoped relay allocation, expiring relay leases, and diagnostics after verifying a valid Codexify collaboration grant.
4. **WhisperMesh Hosted Rooms are a separate future product.** They are not a dependency of the initial ThreadSpace launch and require a separate ADR, threat model, privacy/retention decision, migration plan, and proof.
5. **Direct paths are preferred and must remain available without WhisperMesh.** Managed relay is fallback infrastructure. Network Assist cannot be a required plaintext relay or a prerequisite for known direct peer authority.

The proposed initial foundation target is direct-private and assisted-private connectivity. No session may silently change from opaque or end-to-end-encrypted transport into managed processing.

## Codexify Authority Hierarchy

HomeBase or Vault is the local sovereign authority. A Space is the bounded user
experience and application container; it does not acquire independent identity
or network-provider authority. A Room is the bounded shared collaboration
context, policy boundary, and grant issuer under HomeBase/Vault authority. A
Thread or Chat is durable conversation state inside its authorized local/Room
context; it is not a network credential, service lease, or service-controlled
source of authority.

WhisperMesh may assist an authorized connection between these contexts. It must
not reorder that hierarchy or use the existence of a Space, Room, Thread, or
Chat as an implied grant.

## Authority Matrix

| Component | May authoritatively own or decide | Must not own or decide |
| --- | --- | --- |
| Vault or HomeBase | local identity binding, key custody/recovery posture, local policy, private context, durable local state, user sovereignty | managed-service identity, another node's private state, or ambient global membership |
| Room | bounded Room policy, participant admission under local authority, scoped RoomCapabilityGrants, Room-local collaboration state | service leases, public discovery, or another participant node's private intelligence |
| Participant node | participant-private intelligence, local tools, local provider choice, locally held credentials, and data not explicitly shared | Room authority merely because it attaches, or authority over another node's local state |
| WhisperMesh Protocol | versioned, provider-neutral schema and compatibility requirements | a deployed service, identity issuance, Room policy, or runtime authority |
| WhisperMesh Network Assist | grant verification, privacy-minimized discovery/signaling, STUN/TURN assistance, scoped relay allocation, expiring ServiceLeases, and service diagnostics | Room membership, Room-capability expansion, canonical Codexify identity, private context, durable Room state, content keys, content processing, or durable identity issuance |
| Future Hosted Room infrastructure | only authority expressly granted in a later Hosted Rooms decision | inherited authority from Network Assist or this ADR |
| Future managed processing | only content/processing access under a later explicit grant and participant consent | inferred access from connectivity, a relay lease, or the presence of encrypted traffic |

## Nodes, Trust Boundaries, And Threat Model

The initial topology includes a Codexify HomeBase or Vault, its Room authority, participant nodes, an optional Network Assist operator, STUN/TURN or relay infrastructure, and compatible alternative/self-hosted operators.

- **Device and node boundary:** each node protects its own keys, local tools, private context, and participant-private intelligence.
- **User and Room boundary:** Room authority evaluates admission and collaboration capability; a friendly relationship, a display label, or discovery result does not grant access.
- **Network and operator boundary:** Network Assist is untrusted for Room plaintext, cryptographic content keys, private memory, and durable collaboration state. Metadata exposure is a first-class risk.
- **Protocol boundary:** a compatible provider implementation must not gain authority merely by speaking the protocol.

The design must tolerate honest-but-buggy peers, malicious or replaying peers, compromised nodes, a compromised Network Assist service, metadata harvesting, confused-deputy attempts, service outage, partition, retry, duplicate delivery, and rate/relay exhaustion.

## Grant And Lease Split

### RoomCapabilityGrant

A RoomCapabilityGrant is a Codexify-issued, signed, scoped collaboration authorization. It is the only object in this boundary that can authorize Room participation or collaboration action.

Its future versioned shape must include at least:

| Field or rule | Requirement |
| --- | --- |
| Issuer | the authorized Codexify Room authority or explicitly delegated Vault authority, bound to its HomeBase/Vault identity |
| Audience | one participant identity, participant node, or a narrowly defined set of both |
| Scope | Room identifier or opaque Room authority reference, permitted collaboration actions, target participant, path allowance, and explicit limits |
| Lifetime | issued-at, expiry, and renewal behavior; never unbounded by default |
| Replay posture | unique grant identifier, nonce or proof-of-possession rule where appropriate, audience binding, idempotent verification result, and replay rejection |
| Revocation | signed revocation or authoritative current-state check, local enforcement, audit fact, and a defined partition/convergence posture |
| Versioning | protocol/schema version and explicit compatibility requirements |

A grant does not disclose private Room name, participant names, artifact names, private activity, private context, or durable Room state to Network Assist. Opaque references are preferred where a service needs correlation.

### ServiceLease

A ServiceLease is a separate, WhisperMesh Network Assist-issued authorization for a narrow managed connectivity operation after the service verifies a valid RoomCapabilityGrant. It is not a Room grant, identity credential, or durable membership record.

Its future versioned shape must include at least:

| Field or rule | Requirement |
| --- | --- |
| Issuer | the named Network Assist operator or compatible self-hosted operator |
| Audience | the requesting node and, where required, the bounded service/relay allocation |
| Scope | discovery, signaling, STUN/TURN, relay allocation, byte/time quota, and path-specific constraints only |
| Lifetime | short explicit expiry; renewal requires fresh grant verification and policy evaluation |
| Replay posture | lease identifier, nonce, audience and allocation binding, bounded idempotency, and replay rejection |
| Revocation | service-side revocation for service access; no implied revocation of the underlying Room grant |
| Versioning | protocol/schema version, key identifier, and explicit compatibility and rollback behavior |

Network Assist must never mint Room membership, broaden a Room capability, convert a relay lease into a general credential, or infer a collaboration right from a service account, a node registration, or a discovery record. A grant and lease remain distinct objects with distinct issuers, audiences, scopes, lifetimes, revocation paths, and audit events.

## Plane Separation

| Plane | Owner and responsibility | Boundary |
| --- | --- | --- |
| Identity and policy plane | Codexify HomeBase/Vault and Room | binds identities, keys, Room policy, grants, local consent, and revocation; does not move to Network Assist |
| Protocol plane | WhisperMesh Protocol with cross-repository compatibility governance | defines versioned schemas, token domains, compatibility fixtures, and error semantics; does not operate a provider |
| Control plane | optional Network Assist | performs discovery, signaling, service verification, lease issuance, diagnostics, and abuse control with a metadata budget |
| Direct or relay data plane | peers directly where possible; lease-bound opaque relay only on fallback | carries direct traffic outside Network Assist or opaque relayed bytes; it does not create Room authority |
| Collaboration-state plane | Codexify Room plus participant nodes under Room policy | owns durable collaboration state, artifact lineage, private context, and conflict policy; no service replication or multi-master state is authorized |
| Processing plane | participant node by default; future managed processor only with a separate decision | cannot read or process data merely because it provides connectivity; managed processing requires explicit grant and consent transition |

Future protocol work must define message identifiers, idempotency keys, retry/backoff with jitter, rate limits, backpressure, dead-letter or terminal failure outcomes, audit event shape, and canonical state/event/error token domains. This ADR names no production wire schema.

## Encryption And Processing Modes

The following are proposed canonical mode tokens. They are contract vocabulary only until promoted through the required token and protocol work.

| Mode | Status | Meaning and rule |
| --- | --- | --- |
| direct_private | foundation target | authorized nodes use a direct path; Network Assist is not on the payload path |
| assisted_private | foundation target | Network Assist assists discovery/signaling and may provide lease-bound opaque fallback relay; it does not obtain plaintext or content keys |
| hosted_e2ee_room | deferred | a future Hosted Rooms mode with end-to-end encryption; it requires a separate authority, hosting, key, retention, and migration decision |
| managed_processing | deferred | a future mode in which an approved processor receives authorized data; entry requires an explicit processing grant and participant consent transition |

Transition into managed_processing must be explicit, inspectable, separately authorized, consented to by the applicable participant(s), and reversible where the future contract permits. A path-state change, relay failure, or service default must never be interpreted as consent to processing.

## Metadata Budget

Network Assist metadata is classified before collection. Collection must be bounded to the minimum required for the named service operation and must not be reclassified as harmless merely by calling it metadata.

| Category | Permitted posture |
| --- | --- |
| Required for operation | opaque node/service correlation references, protocol version, bounded capability/path request, lease/grant verification outcome, endpoint candidates only where necessary, and minimal failure code |
| Ephemeral | signaling envelopes, candidate negotiation state, nonce/replay markers, short-lived allocation state, and transient path diagnostics, deleted at the declared TTL |
| Retained for abuse prevention | privacy-minimized rate-limit, quota, abuse, revocation, and security event facts with explicit retention and access policy |
| Retained for billing | lease/allocation identifier, time/byte/quota totals, service plan/account reference where authorized, and invoice/audit linkage without payload capture |
| Aggregated | coarse reliability, NAT/fallback, capacity, and cost metrics that cannot be used as a private Room activity feed |
| Forbidden | private Room names, participant names, participant counts, artifact names, transcripts, private payloads, private memory, private activity details, cryptographic content keys, and unrelated durable Room state |

Discovery responses must not reveal private Room existence, names, participant names, participant counts, artifact names, or private activity summaries. Discovery is an authorization-gated rendezvous result, not a people or Room directory.

## Failure And Partition Semantics

| Condition | Required behavior |
| --- | --- |
| Discovery unavailable | a node may use an already-known direct peer route; no new managed discovery is inferred, and the UI reports a bounded unavailable state |
| Signaling unavailable | new managed negotiation fails visibly or uses an existing direct path if independently available; it does not cause a cloud-authority fallback |
| Relay allocation unavailable | direct-first negotiation remains preferred; if no direct path exists, the connection fails visibly with a retry/backoff policy and no generic proxy fallback |
| Established direct session loses Network Assist control plane | the established direct path continues within its locally enforceable Room authority; loss of service control does not revoke it |
| ServiceLease expires or is revoked | new or renewed managed discovery, signaling, STUN/TURN, and relay activity fails closed; it does not revoke the underlying RoomCapabilityGrant or known direct authority |
| RoomCapabilityGrant expires or is revoked | nodes reject new authorized collaboration action and stop affected activity on locally observed expiry/revocation; a future protocol must define signed revocation distribution, idempotency, and partition convergence rather than promise impossible instantaneous global teardown |
| Network Assist compromise | treat service keys/endpoints and all service leases as revocable, rotate/revoke them, disable managed access, preserve locally verifiable Room grants and direct-path posture, and expose an operator-visible containment state |

Retry must use bounded exponential backoff with jitter. Duplicate signaling, grant, lease, or revocation messages must yield an idempotent outcome or a bounded explicit rejection. A service outage cannot turn Network Assist into a durable identity or authorization authority merely because a peer needs help reconnecting.

## Service Replaceability And Self-Hosting

WhisperMesh Network Assist is optional and replaceable. A self-hosted operator or a compatible alternative implementation must remain architecturally possible without changing Codexify Room authority or the Protocol vocabulary. This ADR does not encode a particular vendor, relay implementation, Tailscale topology, cloud provider, STUN/TURN provider, or deployment platform into protocol law.

The Protocol is the compatibility surface; a provider choice is an operational configuration subject to later security, privacy, support, and proof work.

## Protocol And Repository Ownership

Codexify owns this sovereignty and managed-service-boundary decision. WhisperMesh owns protocol schemas and service-specific implementation contracts. Shared fixtures and compatibility declarations are the cross-repo drift control. Normative text must not be copied into both repositories unless the source-of-truth repository and update process are explicit.

Future protocol versions require explicit forward/backward compatibility, mixed-version behavior, downgrade protection, revocation compatibility, and rollback rules before rollout.

## ThreadSpace Launch Dependency

ThreadSpace launch requires:

- direct sovereign connectivity; and
- operational Network Assist Alpha for discovery, signaling, and scoped opaque relay fallback.

It does not require Hosted Rooms, SFU infrastructure, recording, transcription, managed Room AI, or managed processing. A launch claim remains blocked until relevant current proof demonstrates the campaign launch gates.

## Consequences And Tradeoffs

- The decision preserves sovereignty, direct operation, self-hosting, and compatible-provider replaceability.
- It requires additional protocol design, compatibility work, shared negative fixtures, integration proof, and strict metadata governance.
- It makes authorization, privacy, replay, expiry, revocation, and path-observability testing more demanding.
- It delays Hosted Room revenue and managed processing until connectivity, authority, and privacy proof exists.
- It lowers the risk that a managed service becomes an accidental cloud identity, content, or Room-state authority.

## Rejected Alternatives

The following are rejected:

1. WhisperMesh as the Codexify identity or Room authority.
2. Relay-first architecture.
3. Cloud-only collaboration.
4. One combined Room grant and relay credential.
5. Lifting the existing JSON collaboration relay unchanged and calling it opaque encrypted relay infrastructure.
6. Building Hosted Rooms before direct and relay proof.
7. Globally discoverable people or private Rooms in the foundation phase.

## Non-Goals And Follow-Up

This ADR does not implement a protocol schema, signature verification, node identity, route, queue, worker, WebSocket, sync, relay, TURN/STUN deployment, WebRTC path, Hosted Room, SFU, recording, transcription, moderation, Room AI, public discovery, billing, migration, configuration, or release claim.

The required first follow-up sequence is:

1. Task 0.2 — a WhisperMesh companion boundary note.
2. Task 1.1 — versioned protocol objects, canonical tokens, and shared negative fixtures.
3. Later approved implementation and proof tasks only after architecture review.

No data migration, API compatibility change, token implementation change, runtime rollout, deployment change, or release-support change follows from this decision alone.
