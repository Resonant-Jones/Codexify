# Collab Chat Identity Contract

## Purpose
Define a proposed `collab` thread layer that reuses the Guardian chat shell while introducing explicit participant permissions, separate collab memory, and structured mention semantics.

## Status
Proposed architecture contract, docs-only.

This contract does not implement runtime behavior.

Runtime implementation requires a later ADR-aligned task.

## Scope
### In scope
- thread mode semantics
- participant model
- author/provenance model
- structured mention semantics
- collab memory boundary
- media visibility boundary
- sidebar classification
- V1 same-principal assistant invocation rule

### Out of scope
- runtime implementation
- database migrations
- frontend implementation
- free-form mention parser implementation
- cross-principal Guardian invocation
- federation/delegation runtime support
- video

## Core Decision
V1 is same-principal only.

Each participant may call only their own assistant/Guardian into the collab thread.

`@Guardian` resolves by the invoking actor, not by a room-global identity.

`@Guardian` written by Alice resolves only to Alice’s own Guardian.

`@Guardian` written by Bob resolves only to Bob’s own Guardian.

No participant may invoke another participant’s Guardian in V1.

Free-text mention strings do not grant authority by themselves.

Unknown, unauthorized, ambiguous, or cross-principal mentions fail closed.

Cross-principal Guardian invocation is deferred until a later ADR-aligned runtime task defines consent, revocation, disclosure, provenance, and memory-isolation rules.

## Thread Modes
`guardian` is the current personal chat mode.

`collab` is the proposed shared-thread mode.

Collab threads may reuse the Guardian shell visually, but they must not reuse personal-thread ownership assumptions.

Collab threads require membership-aware listing, pinning, archive, unread, and search behavior.

## Participant Model
Required participant fields:
- `collab_thread_id`
- `user_id`
- `role`
- `access_state`
- `own_guardian_access_enabled`
- `invited_by`
- `invited_at`
- `accepted_at`
- `revoked_at`

Roles:
- `owner`
- `participant`
- `viewer`

Access states:
- `invited`
- `active`
- `declined`
- `revoked`
- `left`

Default behavior is human-only unless same-principal Guardian access is explicitly enabled for that participant.

The Guardian access flag applies only to the participant’s own Guardian and never grants access to another participant’s Guardian.

## Author and Provenance Model
Distinct author/source classes:
- human participant
- same-principal Guardian invoked by that participant
- system event
- external participant Guardian, deferred

Persisted messages must eventually distinguish:
- who authored the message
- which human principal authorized the message
- which Guardian or assistant produced the message, if any
- which invocation path produced it

Provenance must support future replay, export, audit, revocation review, and memory-boundary inspection.

Guardian-authored messages must never pretend to be the human participant.

## Mention Semantics
Structured mention chips are the preferred model.

Free-text mention strings are display text, not authority.

V1 resolution:
- `@Guardian` resolves to the invoking participant’s own Guardian only.
- `@Name` resolves to a human participant mention only unless a future contract expands it.
- `@NameGuardian`, `@AliceGuardian`, `@BobGuardian`, or equivalent cross-principal assistant mentions are unsupported/deferred.

Fail-closed outcomes:
- unknown target
- unauthorized target
- revoked participant
- Guardian access disabled for the invoking participant
- ambiguous alias
- cross-principal Guardian target
- free-text mention without structured authorization metadata

## Guardian Invocation Policy
V1 allows only same-principal Guardian invocation.

Every participant may invoke only their own Guardian, if enabled.

No participant may invoke another participant’s Guardian.

Cross-principal Guardian invocation is deferred.

Required future prerequisites for cross-principal access:
- explicit consent
- revocation
- disclosure policy
- provenance records
- per-thread access grants
- memory isolation proof
- invocation audit trail
- clear UX for who or what is responding

## Memory and Retrieval Boundary
Separate collab history and collab KB surfaces are required.

Collab memory must not automatically write into personal memory, personal facts, identity mirror, or private Guardian memory.

A participant’s own Guardian may use the collab thread context only within the collab invocation boundary defined by the future runtime task.

Any bridge from collab memory into personal memory must require explicit user action and provenance.

Derived summaries, citations, embeddings, and retrieval traces must remain scoped to the collab thread or collab KB unless explicitly bridged.

## Media Boundary
V1 media support is limited to text, images, and audio.

Attachment visibility follows participant ACLs.

Guardian access to attachments follows the same same-principal invocation policy as message context.

One participant’s Guardian must not receive another participant’s private or non-visible attachments.

Video is deferred because of size, streamability, transcoding, sync, and permission complexity.

Video is out of V1.

## Sidebar and Shell Behavior
Collab threads may reuse the Guardian shell, but they must be visually distinct.

The shell must include a collab-specific label/color treatment.

The shell must expose a separate collab sidebar bucket.

Collab-aware pin/archive/search/unread semantics are required.

Personal Guardian threads must remain unchanged.

## Existing Collaboration Surface Relationship
Existing document collaboration primitives are precedent, not a complete implementation substrate.

Useful precedents:
- permissions
- audit logs
- WebSocket presence
- shared links

What they do not define:
- shared conversational identity
- Guardian invocation
- participant-owned chat memory
- mention authority

## V1 Acceptance Criteria
- Each participant may call only their own assistant/Guardian.
- `@Guardian` resolves by the invoking actor, not by room-global identity.
- No participant may invoke another participant’s Guardian in V1.
- Unauthorized and unknown mentions fail closed.
- Collab memory is isolated from personal memory.
- Participant ACLs govern media visibility.
- Collab threads are classified separately in the sidebar.
- Existing personal Guardian threads remain unchanged.
- Cross-principal Guardian invocation is deferred.
- Video is deferred.

## Future Work
- Runtime schema design
- Participant invitation lifecycle
- Mention resolver
- Same-principal Guardian invocation runtime path
- Collab KB tables and retrieval policy
- Sidebar implementation
- Media ACL enforcement
- Cross-principal Guardian invocation ADR
- Consent/revocation/disclosure UX

## Non-Goals
- No runtime behavior
- No schema migration
- No route implementation
- No frontend implementation
- No cross-principal Guardian access
- No video
- No federation/delegation release claim

## Documentation Follow-through
`docs/architecture/README.md` links to this contract.

`docs/architecture/00-current-state.md` is unchanged by this docs-only slice unless a future task explicitly finds a release-truth contradiction.

ADR creation is deferred to a later architecture task before implementation.
