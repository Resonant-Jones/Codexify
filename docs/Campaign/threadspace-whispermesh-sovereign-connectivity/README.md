# ThreadSpace ↔ WhisperMesh Sovereign Connectivity Foundation

- Campaign ID: TS-WM-001
- Status: proposed campaign and governance plan; no runtime implementation or release claim
- Governing decision: [ADR-055: ThreadSpace ↔ WhisperMesh Managed-Service Boundary](../../architecture/adr/055-threadspace-whispermesh-managed-service-boundary.md)
- Architecture review: required before any implementation task opens

## Objective

Make WhisperMesh Network Assist operational enough to support a trustworthy ThreadSpace launch without transferring Codexify sovereignty. Network Assist may assist authorized nodes with discovery, signaling, NAT traversal, scoped relay allocation, and diagnostics. It must not become the authority for a Codexify identity, Room, capability, private context, durable collaboration state, content key, tool, provider, or participant-private intelligence.

This campaign is a governance and delivery frame, not evidence that ThreadSpace, WhisperMesh Network Assist, hosted Rooms, federation, or a relay service is currently available.

## Current Truth And Evidence Posture

Codexify remains local-first beta hardening. Postgres is its durable application system of record, and Redis is operational coordination infrastructure. Existing federation, sync, collaboration, and relay seams are code-path evidence only; they do not establish supported ThreadSpace behavior.

WhisperMesh contains conceptual and local control-plane groundwork for node registration, discovery, and session reasoning. Its current Spine is an in-memory, metadata-first implementation slice. It does not prove persistent service authorization, production signature verification, TURN fallback, relay opacity, a managed service, or node interoperability.

The governing current-state source remains [00 Current State](../../architecture/00-current-state.md). This campaign must not modify or widen it.

## Boundary To Preserve

| Layer | Authority and limit |
| --- | --- |
| Codexify HomeBase or Vault | Owns local identity binding, local policy, private context, durable local state, and user-facing sovereignty. |
| Codexify Room | Owns bounded collaboration policy and issues scoped RoomCapabilityGrants. |
| Participant node | Owns participant-private intelligence, local credentials, local tools, and private data not explicitly shared under Room policy. |
| WhisperMesh Protocol | Is the open, provider-neutral compatibility contract; it does not operate a service or own an identity. |
| WhisperMesh Network Assist | Is an optional managed implementation for discovery, signaling, STUN/TURN, relay leases, and diagnostics. It verifies grants and may issue narrower, expiring ServiceLeases. |
| WhisperMesh Hosted Rooms | Is a future separately governed product, not an initial ThreadSpace dependency. |

Direct operation remains the preferred path and must work without WhisperMesh. Managed relay is fallback infrastructure. A Network Assist outage may block new managed discovery, signaling, or relay leases, but it must not invalidate known direct peer authority.

## Workstreams

1. **Architecture and governance** — maintain the authority split, protocol ownership, metadata budget, negative requirements, and decision records.
2. **Codexify sovereign edge** — define the Room-side grant, local enforcement, explicit path state, revocation behavior, and operator-visible consent.
3. **WhisperMesh control plane** — define compatible discovery, signaling, grant verification, expiring lease issuance, diagnostics, and abuse controls.
4. **WhisperMesh relay plane** — prove scoped opaque fallback relay behavior, quota/backpressure handling, and lease-bound metering without content capture.
5. **Integration, proof, and pilot** — maintain shared fixtures, exercise negative cases, run a bounded private pilot, and measure support/economics.

## Foundation Hard Limits

The foundation explicitly excludes:

- public people directory or global identity;
- Hosted Rooms, SFU, group-video scaling, recording, transcription, or managed Room AI;
- cross-node private-memory retrieval;
- database replication or multi-master Room state;
- generic arbitrary-traffic relay or a public federation directory;
- multi-region production orchestration, a formal SLA, unlimited-bandwidth pricing, or a mature billing engine; and
- any release-claim expansion.

The foundation does not silently reclassify an existing JSON collaboration relay as an opaque encrypted relay. That would require new implementation and proof.

## Phase Plan

### Phase 0 — Boundary Freeze

**Purpose:** establish one reviewed authority boundary before protocol or runtime work begins.

**Deliverables:**

- ADR-055 and this TS-WM-001 campaign;
- a resolved source-of-truth rule for Codexify sovereignty, WhisperMesh protocol schemas, and shared compatibility fixtures; and
- initial grant/lease, metadata, failure, and stop-condition doctrine.

**Explicit exclusions:** no protocol schema, route, persistence, signature, relay, hosted-Room, deployment, or release change.

**Proof surface:** documentation structure, links, architecture review, and a task-scoped diff.

**Exit gate:** architecture review accepts the boundary and confirms that the current release truth remains unchanged.

### Phase 1 — Versioned Protocol Contracts And Negative Fixtures

**Purpose:** specify interoperable objects before either repository treats cross-repository vocabulary as a runtime fact.

**Deliverables:**

- versioned protocol-object and canonical-token proposal;
- RoomCapabilityGrant and ServiceLease schemas with separate issuer, audience, scope, expiry, nonce, and revocation semantics; and
- shared positive and negative compatibility fixtures for replay, expiry, revocation, audience mismatch, and scope escalation.

**Explicit exclusions:** no production signing service, service credential, relay, network deployment, or claim of interoperability.

**Proof surface:** fixture validation in both repositories and documented forward/backward compatibility and rollback rules.

**Exit gate:** both maintainers accept one compatibility declaration and every negative fixture fails closed.

### Phase 2 — Direct Sovereign Path Proof

**Purpose:** prove that authorized peer collaboration remains possible without WhisperMesh.

**Deliverables:**

- an explicit Codexify direct-path implementation and path-state diagnostics;
- grant verification and local authorization enforcement; and
- direct connection, partition, retry, idempotency, and revocation proof harnesses.

**Explicit exclusions:** no managed discovery dependency, relay fallback, Hosted Rooms, or managed processing.

**Proof surface:** reproducible two-node proof showing direct operation without WhisperMesh and clear path-state reporting.

**Exit gate:** direct connectivity and controlled degradation are proven while private Room metadata stays local.

### Phase 3 — WhisperMesh Signaling Spine

**Purpose:** add an optional, grant-verifying signaling path without relocating Room authority.

**Deliverables:**

- authenticated, privacy-minimized discovery and signaling contracts;
- service-side grant verification, short-lived ServiceLease issuance, and lease/audit event shape; and
- bounded retries, replay protection, rate limits, backpressure, and operator-visible failure states.

**Explicit exclusions:** no durable Room authority, private discovery payload, generic relay, Hosted Rooms, or managed processing.

**Proof surface:** integration tests and a disposable environment proving that invalid, replayed, expired, revoked, or broadened requests fail closed.

**Exit gate:** valid managed signaling can assist a direct path while failure does not remove direct sovereign operation.

### Phase 4 — Network Assist Alpha With STUN/TURN Fallback

**Purpose:** provide a bounded managed fallback for hostile NAT conditions.

**Deliverables:**

- Network Assist Alpha deployment posture with scoped STUN/TURN and lease-bound opaque relay allocation;
- relay metering and diagnostics that do not capture payloads; and
- service lease renewal, expiry, revocation, quota, and abuse-prevention controls.

**Explicit exclusions:** no durable relay credential, general proxy, SFU, recording, transcription, managed AI, Hosted Rooms, or formal SLA.

**Proof surface:** direct-first and hostile-NAT tests, payload-opacity checks, lease-bound relay allocation, and bounded operational telemetry inspection.

**Exit gate:** fallback works only with a valid scoped lease, relay cannot decrypt payloads, and an unavailable relay fails visibly without changing Room authority.

### Phase 5 — Bounded ThreadSpace Connectivity Vertical Slice

**Purpose:** join the sovereign edge and Network Assist Alpha in one small, inspectable ThreadSpace flow.

**Deliverables:**

- one bounded Room/participant connection flow with consent, grant, lease, and actual-path visibility;
- UI and operational diagnostics that distinguish direct, assisted, and relay states without exposing private Room existence; and
- cross-repository compatibility receipt.

**Explicit exclusions:** no public discovery, Room migration, Room-state replication, multi-master writes, hosted collaboration, or generic file/data transport.

**Proof surface:** end-to-end two-node exercise, negative authorization tests, control-plane-loss exercise, and evidence of metadata minimization.

**Exit gate:** the vertical slice satisfies every technical launch-gate criterion below in a reproducible environment.

### Phase 6 — Private Pilot With 10 To 20 Real Groups

**Purpose:** learn whether the bounded design is operable for real voluntary groups without treating pilot use as a public release.

**Deliverables:**

- opt-in pilot enrollment, support, consent, and incident procedures;
- privacy-bounded aggregate usage, reliability, NAT-fallback, cost, and support-burden measurements; and
- a pilot review with evidence gaps and a rollback/exit decision.

**Explicit exclusions:** no public directory, formal SLA, unlimited bandwidth, mature billing, Hosted Rooms, recordings, transcription, or managed processing.

**Proof surface:** audited pilot receipts, aggregate-only operational reports, incident review, and evidence that the direct path remains independently usable.

**Exit gate:** 10 to 20 groups complete a bounded evaluation and the measured economics, privacy posture, reliability, and support burden are accepted by human review.

### Phase 7 — Hosted Rooms Decision Gate

**Purpose:** decide whether a separate Hosted Rooms product is justified after sovereign connectivity proof exists.

**Deliverables:**

- a decision record that accepts, defers, or rejects Hosted Rooms; and
- if accepted, a separate authority, encryption, processing, retention, economics, and migration work packet.

**Explicit exclusions:** Hosted Rooms implementation, SFU deployment, recording, transcription, and managed Room AI.

**Proof surface:** reviewed evidence from prior phases and a new threat, privacy, revenue, operator, and migration analysis.

**Exit gate:** a separate ADR and explicit implementation authorization exist; otherwise Hosted Rooms remain deferred.

## ThreadSpace Launch Gate

ThreadSpace may be considered for a bounded launch only when current, reproducible proof establishes all of the following:

1. direct operation works without WhisperMesh;
2. managed signaling establishes a direct path;
3. hostile NAT can use scoped opaque relay fallback;
4. RoomCapabilityGrants and ServiceLeases are separately enforceable;
5. private discovery avoids existence leaks;
6. the relay cannot decrypt payloads;
7. the actual connection path is visible to the participant and operator;
8. established direct sessions tolerate control-plane loss;
9. usage can be metered without content capture;
10. a self-hosting path is documented; and
11. negative replay, expiry, revocation, and scope-escalation tests pass, while pilot economics and support burden are measured.

The launch dependency is direct sovereign connectivity plus operational Network Assist Alpha. It is not Hosted Rooms, an SFU, recording, transcription, or managed Room AI.

## Stop Conditions

Pause delivery and require immediate architecture review if:

- WhisperMesh must mint Room membership or broaden Room capability;
- the service must persist full Room state or discovery requires private Room identity;
- relay credentials become durable or broadly reusable;
- direct operation requires an active managed-service dependency;
- signature verification remains optional;
- an opaque relay cannot remain opaque;
- Hosted Rooms or processing are being smuggled into the foundation; or
- documentation is being treated as release proof.

## First Atomic Tasks

1. **Task 0.1:** define ADR-055 and TS-WM-001 (this task).
2. **Task 0.2:** create the WhisperMesh companion boundary note in the WhisperMesh repository.
3. **Task 1.1:** create protocol v0.1 objects, canonical token domains, and shared negative fixtures.

This campaign deliberately does not create complete implementation task specs for later phases.

## Ownership And Compatibility Rule

Codexify owns the sovereignty and managed-service-boundary ADR. WhisperMesh owns protocol schemas and service-specific implementation contracts. Shared fixtures and compatibility declarations prevent drift. Normative text must not be copied into both repositories without an explicit source-of-truth rule.

Every future protocol version must declare compatibility, mixed-version behavior, upgrade, rollback, and revocation handling before rollout. No data migration, API compatibility change, token implementation change, runtime rollout, deployment change, or release-support change is authorized by this campaign.

## Documentation Follow-Through

Completed in Task 0.1:

- this campaign;
- ADR-055;
- ADR index routing; and
- architecture README routing.

Deferred:

- the WhisperMesh companion note (Task 0.2);
- protocol schemas, canonical token implementation, and shared fixtures (Task 1.1); and
- runtime, UI, operator, deployment, release-truth, Hosted Room, and managed processing work until later approved tasks provide relevant evidence.
