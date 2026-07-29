# P2P Video POC Contract

## Purpose

This document defines a **proposed, experimental** proof of concept for one-to-one human audio/video calling in Codexify. It asks one bounded question:

> Can two authenticated Codexify users establish and maintain a direct browser-to-browser audio/video session while Codexify acts only as the authorization, invitation, and signaling plane?

It is intentionally operational enough to guide a later implementation task, but it does not establish that the POC or any video runtime exists.

## Status

- **Proposed architecture contract; documentation-only.**
- **Not current release truth.** [`00-current-state.md`](./00-current-state.md) remains the short-horizon release authority and is unchanged by this contract.
- Runtime implementation requires a later ADR-aligned task before any route, protocol, UI, persistence, or media behavior is added.
- This contract does not change [Collab Chat Identity Contract](./collab-chat-identity-contract.md): video remains deferred and outside collab V1.

## Product Boundary

One-to-one direct calling is a candidate built-in Codexify capability. This POC is limited to the direct-only, two-human case.

Managed multi-participant meetings are a separate, future hosted service. Directionally, only a meeting host **may** eventually require a paid entitlement for that managed service; guests may be permitted by host policy. That directional business model is not implemented, specified as a pricing plan, or exercised by this POC.

This POC MUST NOT be represented as:

- current release truth;
- collab V1 video support;
- production-ready one-to-one calling;
- TURN-backed reliability;
- a managed group-meeting service;
- Guardian-to-human video interaction;
- transcription, recording, billing, or paid-service behavior.

## Core Decision

The POC supports exactly two authenticated human participants. Codexify provides authorization, invitation, and signaling. When network conditions permit, the browsers exchange encrypted WebRTC audio/video directly.

- Guardian is not a media endpoint, on-camera participant, or voice participant.
- No server-side media relay is included.
- No group calling is included.
- A network that needs TURN MAY fail cleanly; it is not a POC success path.

## Plane Separation

### Control plane

Codexify owns the authenticated control plane:

- call creation and authorization;
- invitation, acceptance, decline, cancellation, and end control;
- signaling-message forwarding;
- bounded call-lifecycle state; and
- minimal diagnostic receipts.

The control plane MUST NOT forward audio or video bytes as media transport.

### Media plane

The browsers own the media plane:

- microphone and camera capture;
- `RTCPeerConnection` creation and lifecycle;
- ICE negotiation;
- STUN-assisted direct connectivity;
- encrypted browser-to-browser audio/video when connectivity succeeds.

Guardian MUST NOT process media. FastAPI request handlers, chat workers, and model providers MUST NOT receive the media stream.

### Intelligence plane

The intelligence plane is entirely deferred from this POC.

- A future transcript may become an authorized evidence source.
- A future Guardian invocation may retrieve bounded transcript slices.
- Transcript processing MUST NOT be required for direct P2P calling to function.

## POC Data Flow

1. Authenticated participant A creates a call invitation for authenticated participant B.
2. Codexify verifies both principals and creates an ephemeral call/session identity.
3. Participant B accepts or declines.
4. On acceptance, both browsers request camera and microphone permissions.
5. Participant A creates an `RTCPeerConnection` and an SDP offer.
6. The offer and ICE candidates pass through Codexify signaling.
7. Participant B creates and returns an SDP answer and ICE candidates.
8. The browsers establish a direct encrypted media path when possible.
9. Codexify observes only control-plane events and privacy-minimized diagnostic metadata.
10. Either participant can end the call.
11. The session terminates and ephemeral signaling authority expires.

```mermaid
sequenceDiagram
    participant A as Participant A browser
    participant C as Codexify signaling/control plane
    participant B as Participant B browser
    participant S as STUN

    A->>C: authenticated invitation for B
    C->>C: authorize principals; create ephemeral call identity
    C->>B: incoming invitation
    B->>C: accept or decline
    alt accepted
        A->>A: request camera/microphone permission
        B->>B: request camera/microphone permission
        A->>S: ICE gathering assistance
        B->>S: ICE gathering assistance
        A->>C: SDP offer + ICE candidates
        C->>B: forward authorized signaling
        B->>C: SDP answer + ICE candidates
        C->>A: forward authorized signaling
        A-->>B: direct encrypted WebRTC audio/video
        B-->>A: direct encrypted WebRTC audio/video
        A->>C: lifecycle/diagnostic control events
        B->>C: lifecycle/diagnostic control events
    else declined
        C-->>A: invitation declined
    end
```

The diagram shows signaling through Codexify and media directly between browsers; it MUST NOT be read as runtime proof.

## Proposed Call State Model

The primary proposed states are:

- `idle`
- `inviting`
- `ringing`
- `accepted`
- `connecting`
- `connected`
- `ending`
- `ended`

Explicit terminal or failure outcomes are:

- `declined`
- `cancelled`
- `permission_denied`
- `peer_unreachable`
- `negotiation_failed`
- `connection_failed`
- `disconnected`
- `expired`

These labels describe the intended POC model only. Exact runtime tokens, transitions, retry/replay rules, persistence, and compatibility behavior require ADR review before implementation. In particular, call identity is distinct from chat-message and chat-attempt identity.

## Identity and Authorization Boundary

- A call MUST contain exactly two authenticated principals.
- The POC MUST NOT offer anonymous guest links.
- There is no room-global Guardian.
- A participant MUST NOT invoke another participant's Guardian through the call plane.
- Signaling messages MUST be scoped to both the call identity and authorized participant identity.
- Free-form identifiers and display names MUST NOT grant call authority.
- Unknown, revoked, expired, or mismatched signaling participants MUST fail closed.
- Call authorization MUST expire after termination or timeout.

Codexify remains the authorization authority. The POC MUST NOT introduce a second identity authority, a reusable guest credential, or ambient call access.

## Signaling Boundary

The minimum conceptual signaling message classes are:

- `invitation_created`
- `invitation_accepted`
- `invitation_declined`
- `invitation_cancelled`
- `sdp_offer`
- `sdp_answer`
- `ice_candidate`
- `peer_ready`
- `call_end`
- `connection_status`

These are proposed message classes, not frozen canonical wire tokens.

- Signaling messages are control data, not chat messages.
- Signaling MUST NOT be persisted as ordinary Guardian conversation content.
- The backend MAY forward signaling over an authenticated WebSocket or equivalent bounded channel.
- Exact protocol tokens, schema/versioning, ordering, idempotency, replay rules, timeout policy, and persistence rules require the implementation ADR.

## Media Boundary

- Audio/video streams MUST remain browser-to-browser when direct ICE succeeds.
- Guardian, FastAPI handlers, chat workers, and model providers MUST NOT receive the media stream.
- The POC MUST NOT add server-side recording, media-object persistence, transcoding, SFU, TURN relay, transcription, or screen sharing.
- The browser MUST stop camera and microphone capture when the call ends.
- Browser permission denial MUST fail cleanly.
- A relay candidate MUST NOT be treated as direct P2P success.

## Minimal POC UI

The POC UI is limited to:

- outgoing invitation state;
- incoming invitation state;
- accept and decline;
- local preview and remote video;
- microphone mute/unmute;
- camera on/off;
- input-device selection;
- end call;
- visible connection state; and
- bounded diagnostic details.

The following are explicitly deferred: chat redesign, group grid, reactions, hand raising, backgrounds, recording controls, transcription controls, Guardian summon controls, screen sharing, and paid-host controls.

## Diagnostic Proof Surface

Future implementation MUST provide observable evidence for:

- opaque call identity;
- both authenticated participant identities;
- state transitions;
- camera and microphone permission results;
- ICE gathering state, ICE connection state, and peer connection state;
- selected ICE candidate-pair type and candidate protocol;
- whether relay was used;
- audio/video track active state;
- call duration; and
- termination reason.

An implementation may emit a privacy-minimized receipt such as:

```text
call_id=<opaque id>
participant_count=2
caller_authenticated=true
callee_authenticated=true
connection_state=connected
selected_candidate_pair=<host|srflx|prflx|relay>
relay_used=false
audio_active=true
video_active=true
duration_seconds=<number>
termination_reason=<reason>
```

- `relay_used` MUST remain `false` for a valid direct-only POC proof.
- A relay candidate MUST NOT be represented as direct P2P success.
- A successful UI render alone is insufficient proof.
- Diagnostic evidence MUST NOT include raw media payloads, secrets, long-lived credentials, or unnecessary private-network details.

## Acceptance Criteria

The future implementation is acceptable only when all of the following are demonstrated:

1. Two authenticated Codexify users can create and accept a one-to-one call.
2. Both users can grant microphone and camera access.
3. SDP and ICE signaling travel through an authenticated Codexify control channel.
4. Audio and video travel directly between browsers on a compatible network.
5. The selected candidate pair proves that TURN relay was not used.
6. Both users can mute audio and disable video.
7. Both users can end the call.
8. Disconnect and permission-denied states are visible and bounded.
9. Guardian does not receive, route, transcribe, or process media.
10. No group-call, recording, transcript, billing, or managed-service claim is introduced.
11. Existing Guardian chat and collab V1 behavior remain unchanged.
12. The implementation remains classified as experimental until a later runtime task produces proof.

## Failure Semantics

The POC MUST fail visibly and cleanly for invitation timeout, invitation decline, caller cancellation, browser permission denial, missing camera, missing microphone, unsupported browser APIs, signaling-socket loss, ICE failure, peer disconnect, page refresh, duplicate acceptance, and expired call identity.

- The POC MUST NOT silently downgrade into an unproven relay path.
- The POC MUST NOT claim universal connectivity.
- Failure on networks requiring TURN is an accepted limitation of the direct-only POC.
- Duplicate, replayed, out-of-order, cross-call, or expired control messages MUST fail closed or produce a bounded idempotent outcome defined by the later ADR.

## Privacy and Consent

- Camera and microphone activation require normal browser permission.
- The call UI MUST visibly indicate active microphone and camera state.
- Media capture MUST stop when the call ends.
- No recording or transcription occurs.
- No raw media is retained.
- Minimal lifecycle and diagnostic metadata MAY be retained only if a later ADR authorizes it.
- Diagnostic output MUST be privacy-minimized.

## Security Boundary

- WebRTC transport encryption remains mandatory.
- Signaling requires authenticated principals.
- Call/session identifiers MUST be opaque and unguessable.
- Signaling authorization MUST expire.
- Cross-call signaling injection MUST fail closed.
- The POC MUST NOT expose reusable media credentials.
- The POC MUST NOT rely on display names for authorization.
- The POC MUST NOT open unauthenticated public signaling routes.

This contract does not claim application-level end-to-end encryption beyond the guarantees actually provided by the selected WebRTC transport.

## Dependency Model

The conceptual POC dependencies are:

- browser `MediaDevices` / `getUserMedia` support;
- browser `RTCPeerConnection` support;
- authenticated Codexify signaling channel;
- STUN service;
- HTTPS or a secure local-development context as required by browser media APIs; and
- frontend diagnostics through WebRTC statistics APIs.

The POC does not include coturn/TURN production service, SFU, MCU, media recorder, speech-to-text worker, billing provider, or managed-meeting control plane.

## Deferred Production Path

### Stage 1 — Experimental direct-only P2P POC

Exactly two authenticated humans, Codexify control/signaling, direct browser media when possible, STUN assistance, and clean failure on TURN-required networks.

### Stage 2 — Built-in production one-to-one calling

Direct P2P remains preferred, with TURN fallback for network reliability and production consent, identity, lifecycle, observability, compatibility, and operational contracts.

### Stage 3 — Optional paid managed group meetings

An optional hosted service with host entitlement, non-paying guests permitted by host policy, SFU-backed multi-party routing, TURN fallback, and optional recording/transcription only under separate contracts.

Stage 2 and Stage 3 require separate architecture and implementation tasks. Neither is implied by this POC.

## Guardian Relationship

- Guardian remains invocable for normal Codexify tasks outside the media path.
- Guardian is not a video participant and does not continuously inspect audio or video.
- Transcript-aware Guardian invocation is deferred.
- Future transcript access SHOULD use bounded retrieval tools rather than injecting an entire transcript by default.
- None of that future behavior is part of this POC.

## Invariants

1. Exactly two human participants.
2. Both participants are authenticated.
3. Codexify owns call authorization and signaling, not media forwarding.
4. Direct browser-to-browser media is the only accepted successful media path in this POC.
5. Guardian never becomes a media endpoint.
6. No transcript, recording, or raw-media persistence.
7. Video remains outside collab V1 release truth.
8. Existing personal Guardian threads remain unchanged.
9. No managed-meeting or paid-service runtime claim.
10. No silent introduction of TURN, SFU, or media-server dependencies.
11. Signaling identity and chat-message identity remain distinct.
12. Experimental proof remains distinguishable from production capability.

## Non-Goals

- group calling;
- guest links;
- TURN;
- SFU;
- recording;
- transcription;
- Guardian voice/video participation;
- screen sharing;
- push notifications;
- mobile background calling;
- billing;
- subscription management;
- production SLA;
- geographic media infrastructure; and
- production launch readiness.

## Proof Surface

A future implementation task requires:

- focused backend signaling tests;
- focused frontend state-machine tests;
- two-browser end-to-end call proof;
- explicit selected-candidate diagnostics;
- forced permission-denial proof;
- forced ICE-failure proof;
- disconnect and teardown proof;
- proof that media tracks stop after termination;
- proof that no media bytes enter Guardian/backend request handling; and
- proof that existing Guardian and collab tests remain unchanged.

This documentation-only contract does not fabricate any of those results.

## Documentation Follow-through

- This document is listed in [`README.md`](./README.md) as a proposed/future contract.
- [`00-current-state.md`](./00-current-state.md) remains unchanged because this task establishes no runtime truth.
- The collab V1 contract continues to state that video is deferred and outside V1.
- Implementation diagrams MUST NOT be updated as though this runtime exists.
- The ADR Index MUST NOT change unless an ADR is actually created; ADR creation is out of scope here.

## Future Task Decomposition

1. Create the P2P calling ADR.
2. Define signaling protocol and call-state tokens.
3. Implement backend authorization and signaling.
4. Implement frontend two-party WebRTC POC.
5. Add browser-based proof harness and diagnostics.
6. Evaluate TURN-backed production reliability separately.
7. Evaluate hosted SFU group meetings separately.
8. Define transcript and Guardian retrieval contracts separately.

This ordered list is future decomposition, not implementation instruction for this documentation-only task.
