# Atlas V0.1 Room and Collaboration Discovery Audit

## 1. Audit metadata

| Field | Value |
| --- | --- |
| Date | 2026-08-12 |
| Audit mode | Read-first discovery; no runtime, schema, or accepted-contract change |
| Branch | `codex/audit-atlas-room-surfaces` |
| Audited HEAD | `abaf6141e39e8d93ae1bc34fcd84a35f023e18d4` |
| `00-current-state.md` declared audited tip | `c4787236e48a1791f477d50a863a063f87f3e8b5` (2026-08-11) |
| Does current HEAD match the documented tip? | No. `c4787236e` is an ancestor of this HEAD, but the document does not describe this exact tip. |

This audit treats `docs/architecture/00-current-state.md` as the release-truth authority. It says Hosted Room work is outside the supported beta/release promise. Code, migrations, focused tests, and older proof packets below establish narrower implementation evidence only.

Primary current-code seams inspected include `guardian/db/models.py`, migrations `b2c3d4e5f6a8` and `7a91c4e2f6b8`, the Hosted Room owner/guest routes and services, the chat worker, frontend Workspace components, federation routes/services, their focused tests, and the tester supported-profile configuration.

## 2. Executive finding

Atlas V0.1 should build on the existing **account-owned Hosted Room projection**: a durable `hosted_rooms` row has exactly one canonical `chat_threads` backing thread; `chat_messages` remain the only transcript; participants, invitation lineage, guest-session authorization, and host-resident Guardian provenance already attach to that single-thread surface.

It should not recreate a Room model, transcript, guest authorization system, or Guardian completion pipeline. None of that is currently release-qualified, and the repository has no Hosted Room React client or Room-scoped Workspace/resource model.

## 3. Current-truth matrix

`Runtime-qualified` means qualified for the current supported beta/release posture, not merely present in code or focused tests.

| Concept | Code exists | Runtime-qualified | UI exists | Canonical owner/source | Atlas relevance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Hosted Room | Yes | No | No Hosted Room client | Postgres `hosted_rooms` | Reuse/project | Account-owned durable boundary; default profile quarantines routes. |
| Room persistence | Yes | No | N/A | `HostedRoom` + Alembic migration | Reuse | Durable status, owner, unique backing-thread and slug constraints. |
| Room participant | Yes | No | No Room participant view | `hosted_room_participants` | Reuse data, new UI | Human owner/member and resident-agent rows; no public human-removal route found. |
| Room invitation | Yes | No | No invite UI | `hosted_room_invites` | Reuse service, new UI | Hash-only credential verifier; owner creation/revocation and guest exchange exist. |
| Guest session | Yes | No | No guest UI | Signed purpose-scoped cookie + persisted invite/participant state | Reuse service, new UI | Cookie binds one room, participant, and invitation; each request revalidates DB truth. |
| Room authorization | Yes | No | No | Owner scope and guest-session validation in routes/services | Reuse | Reachability is not accepted as authorization in these paths. |
| Canonical Room thread | Yes | No | Generic thread UI only | `HostedRoom.backing_thread_id -> chat_threads.id` | Direct projection seam | Unique constraint makes one backing thread belong to at most one Room. |
| Multi-thread Room | No | No | No | No relationship table/model | Future extension | Current Room is not a container for multiple threads. |
| Room messages | Yes | No | No Room transcript UI | `chat_messages` | Reuse | No Room transcript table; participant provenance is paired metadata on canonical messages. |
| Room Guardian invocation | Yes | No | No invocation control | Existing completion enqueue/worker path | Reuse backend, new UI | Explicit owner/guest routes invoke exactly one enabled resident `guardian`; worker revalidates before generation and persistence. |
| Personal Guardian-per-participant binding | No | No | No | None | Do not assume | No participant-node or personal-Guardian routing exists in the bounded runtime. |
| Room Workspace/resources | No direct model | No | Generic active Workspace drawer | Thread/project document and media relationships | Compose only | Resources can be indirect through backing thread/project; no Room resource ownership or ACL surface. |
| Shared semantic Room KB | No | No | No | None | Future extension | No Room-specific retrieval corpus, ingestion, or memory boundary found. |
| Remote Room projection | No | No | No | None | Future extension | No Room packet/projection endpoint or remote Room schema found. |
| Cross-node Room posting | No | No | No | None | Future extension | Federation does not carry canonical Hosted Room messages. |
| Cross-node Guardian invocation | No | No | No | None | Future extension | Invocation accepts only the host-resident Guardian actor. |
| Atlas | No runtime implementation | No | No | Planning documents only | New presentation work | `architecture-atlas.md` is an architecture KB entrypoint, not an Atlas product surface. |
| HomeBase | No runtime implementation | No | No | Planning vocabulary | Do not model as existing state | Proposed in ThreadSpace planning, not a current persistence/API/UI object. |
| Spaces | No runtime implementation | No | No | Planning vocabulary | Do not model as existing state | No first-class Space model or Room directory in code. |
| Galaxy | No runtime implementation | No | No | Planning vocabulary | Deferred | Proposed discovery renderer only. |

Focused route, model, migration, and worker tests provide strong code-path evidence for the Hosted Room row, authorization, transcript provenance, and invocation seam. They do not close current-tip supported-path proof. The older R2 proof packet records a live invocation run against transplanted implementation files and manually created Room tables, so it is not proof for this audited checkout/HEAD.

## 4. Canonical object relationships

```text
User (owner_account_id)
  └── HostedRoom (id, active|closed)
        ├── backing_thread_id ──> ChatThread (one unique canonical thread)
        │                         └── ChatMessage (only transcript rows)
        │                               └── optional hosted_room_participant_id
        ├── HostedRoomParticipant
        │     ├── owner: bound_account_id = owner account
        │     ├── member: optional bound_account_id; normally originates from invite
        │     └── agent: resident/local-persona binding, no account binding
        └── HostedRoomInvite
              └── optional one originating participant
```

The Room model is durable. It has no transcript table, no `RoomThread` collection, and no direct resource table. The owner can read the same backing `ChatThread` through the ordinary account-scoped thread surface; a guest only receives the dedicated Room transcript projection.

Canonical identifiers are distinct:

- `HostedRoom.id` is a UUID-like string and the Room identity.
- `HostedRoom.backing_thread_id` / `ChatThread.id` is an integer conversation identity.
- `ChatMessage.id` is the canonical message identity.
- `HostedRoomParticipant.id` and `HostedRoomInvite.id` are Room metadata identities.
- request, queued task, turn, and assistant-message identities remain distinct in the explicit Guardian invocation path.

## 5. Backend ownership map

| Path | Relevant seam | Responsibility | Qualification status |
| --- | --- | --- | --- |
| `guardian/db/models.py` | `HostedRoom`, `HostedRoomInvite`, `HostedRoomParticipant`, `ChatMessage` | Canonical storage shape, lifecycle/token-domain constraints, unique one-thread binding, paired message provenance | Implemented; migration/model tests; not release-qualified |
| `guardian/db/migrations/versions/b2c3d4e5f6a8_add_hosted_room_persistence.py` | `upgrade`/`downgrade` | Creates Room, invite, and participant tables and constraints | Migration-tested; not current-tip deployment proof |
| `guardian/db/migrations/versions/7a91c4e2f6b8_add_hosted_room_message_provenance.py` | `upgrade`/reconciliation checks | Adds participant provenance to canonical `chat_messages` | Migration-tested; not current-tip deployment proof |
| `guardian/routes/hosted_rooms.py` | `create_room`, owner CRUD/close, invite endpoints, owner message and invoke routes | Authenticated owner lifecycle and explicit Guardian acceptance | Implemented/focused-tested; tester-only profile configuration; not supported beta |
| `guardian/routes/hosted_room_guest.py` | `exchange_invitation`, session inspection/logout, guest messages/invoke | Invitation exchange, session-protected guest projection and explicit invocation | Implemented/focused-tested; not supported beta |
| `guardian/core/hosted_room_session.py` | issue/decode/extract cookie helpers | HMAC-signed, purpose-separated, room/participant/invite-bound session claims | Implemented/focused-tested; no server-side session table |
| `guardian/core/hosted_room_messages.py` | access validators, `list_room_messages`, `create_human_room_message` | Reads/writes canonical `ChatMessage` rows and safe Room projection | Implemented/focused-tested; not release-qualified |
| `guardian/core/hosted_room_invocation.py` | `prepare_hosted_room_guardian_invocation` | Route-neutral construction of canonical `ChatCompletionTask` metadata | Implemented/focused-tested; not release-qualified |
| `guardian/core/hosted_room_completion_context.py` | `validate_hosted_room_completion_context` | Fail-closed revalidation of Room, message, actor, requester, invite, and thread | Implemented/focused-tested; not release-qualified |
| `guardian/workers/chat_worker.py` | Hosted Room context validation and assistant `create_message` call | Revalidates before model execution and before canonical assistant persistence, then writes Guardian provenance atomically | Implemented/focused-tested; no current-tip supported-path proof |
| `guardian/routes/threads.py` | account-scoped list/get thread routes | Ordinary owner access to the backing thread; does not make it guest-readable | Existing generic route; Hosted Room integration unqualified |
| `guardian/routes/federation.py` and `guardian/routes/federation_context.py` | manifest/session/relay, document diff/graph/context endpoints | Experimental peer trust, relay, diff, graph, and context search | Experimental; not a Room protocol or release surface |
| `guardian/federation/manifest.py` | `NodeManifest`, Ed25519 key and signature helpers | Node key/manifest identity seam | Code-path only/experimental; no Room authority grant |
| `guardian/realtime/collaboration.py` | document collaboration manager | Document presence/permission WebSocket behavior | Separate document collaboration surface; not Hosted Room runtime |

### Current authority checks

- **Owner metadata, messages, invitations, close/update, and invocation:** normal authenticated account scope, then `_require_room_ownership`; cross-account lookups return non-disclosing `404`.
- **Guest metadata/messages/invocation:** an HTTP-only, HMAC-signed session cookie is purpose-separated from account sessions, then the Room, invitation, and member participant are loaded and checked for matching IDs, active Room/member state, accepted/non-expired invite, and active session expiry.
- **Posting:** the server derives Room, backing thread, participant, and message provenance. It does not accept these as client-controlled message fields. Guest message rows use the thread owner for `ChatMessage.user_id` while preserving guest authorship in Room participant provenance.
- **Invitation revocation:** owner-only; it preserves the participant record but causes persisted invite lineage to fail guest session/message/invocation revalidation. Human removal exists as a model state, but no owner-facing human-removal endpoint was found.
- **Guardian invocation:** owner or a revalidated guest session can target only the one active `resident` / `guardian` participant. The worker repeats validation immediately before model execution and immediately before assistant insertion.

## 6. Frontend ownership map

No `hosted-room`, `hosted_room`, invitation, guest-session, or Room API client reference was found in `frontend/src` or `frontend/tests`. There is therefore no active Hosted Room page, RoomShell, participant UI, invite flow, guest flow, Room composer, or Room navigation to extend.

| Path | Relevant component/hook/store | Responsibility | Atlas posture |
| --- | --- | --- | --- |
| `frontend/src/components/persona/layout/AppShell.tsx` | shared Workspace drawer composition and responsive shell | Active application shell; mounts generic Workspace surfaces in Dashboard/Guardian/Documents contexts | Compose; do not treat it as a Room shell |
| `frontend/src/components/sidebar/ThreadList.tsx` and `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` | thread navigation/sidebar | Active generic chat-thread navigation | Reuse navigation patterns, add Room data only after an accepted binding/UI task |
| `frontend/src/features/guardian/components/Composer.tsx` | generic message composition | Active canonical chat-composer interaction | Reuse only after Room route/API integration; no Hosted Room client contract exists |
| `frontend/src/features/workspace/components/WorkspaceDrawer.tsx` | `WorkspaceDrawer` | Active generic shelf/scratchpad/inspector shell with responsive layout state | Compose for a future Room Workspace shell, not direct Room resource proof |
| `frontend/src/features/workspace/components/WorkspaceShelfPanel.tsx` | `WorkspaceShelfPanel` | Fetches documents/images by generic `thread_id` and/or `project_id` | Reuse against backing-thread/project projection; not shared Room resources |
| `frontend/src/features/workspace/components/WorkspaceInspectorPanel.tsx` | `WorkspaceInspectorPanel` | Phase-1 document metadata preview; image preview remains unavailable | Reuse presentation only; extend for actual resource semantics |
| `frontend/src/features/workspace/components/WorkspaceScratchpadPanel.tsx` | scratchpad | Browser-local, thread-keyed draft aid | Ignore as shared Room state; it must not become collaborative state implicitly |
| `frontend/src/features/workspace/state/useWorkspaceUiState.ts` | Workspace UI localStorage state | Drawer/tab presentation state | Reuse responsive UI behavior only; local UI state is not Room state |

## 7. Room/thread semantic finding

**Current Room = one canonical thread.** `HostedRoom.backing_thread_id` is non-null and unique (`uq_hosted_rooms_backing_thread_id`), and Room creation atomically creates one `ChatThread`, then its owner participant. The generic owner thread routes can open that canonical thread outside the Room projection.

**One Room cannot contain multiple threads today.** There is no Room-to-many-thread table, collection, API, or test seam; the unique backing-thread constraint excludes even sharing one thread between Rooms.

**Messages are not duplicated.** Owner and guest routes query/write `chat_messages` by `backing_thread_id`; the only Room-specific fields are optional participant provenance and a display-name snapshot. Explicit Guardian output is also an assistant `ChatMessage` in that same thread.

Therefore, Atlas's proposed **Room -> many Threads** model is a **future architecture/runtime extension**, not a current feature. A read-only Atlas could group a current Room and its sole canonical Thread only as a truthful projection. It must not represent that grouping as multi-thread support.

## 8. Workspace/resource finding

What can currently associate indirectly with a Room:

- The Room creation route creates its backing thread under the owner's default project when one can be resolved.
- Existing `thread_documents` link documents to a `chat_threads` ID; generic document/image/media records also carry optional `thread_id` and/or `project_id` fields.
- `project_document_links` and generic Workspace shelf queries can expose resources associated with that thread or its project.

What does **not** exist:

- no `room_id` foreign key on documents, media, artifacts, projects, or repositories;
- no Room-scoped resource table, resource ACL, shared Workspace API, or shared semantic KB;
- no Room resource browser/Inspector or attribution/provenance policy beyond generic thread/project state.

The active generic `WorkspaceDrawer`, `WorkspaceShelfPanel`, and `WorkspaceInspectorPanel` are reusable presentation components. They are not evidence of a Room Workspace: the shelf is explicitly scoped by generic `thread_id`/`project_id`, the scratchpad persists device-local browser state, and the Inspector calls itself a phase-1 shell.

Any Atlas Workspace behavior that makes resources shared, independently Room-visible, room-authorized, participant-attributable, or discoverable outside the backing thread/project would need new runtime semantics and an authority/portability decision.

## 9. Guardian finding

### CURRENT

- A Room can include enabled agent participant rows, but explicit invocation is bounded to one active host-resident Guardian (`actor_source=resident`, `actor_ref=guardian`, display snapshot `Guardian`).
- Owner and guest routes take a source message ID and return asynchronous acceptance through the existing chat-completion enqueue service.
- The queued task carries Room, backing-thread, source-message, actor-participant, requester authority, and optional requester participant metadata. It does not carry credentials.
- The worker revalidates Room lifecycle, backing-thread match, source-message provenance, Guardian participant identity, guest invite lineage, and requester state before model execution and again before assistant persistence.
- Guardian output becomes an assistant message in the canonical backing thread with atomically written participant provenance. Plain mentions are content only and do not invoke it.

### NOT YET TRUE

- There is no personal Guardian binding per human participant, participant-node attachment, remote Guardian route, or cross-principal invocation.
- There is no Room-specific personal-memory ingress/egress policy. Because Room messages use an ordinary canonical thread and task ownership is host-account based, this audit cannot prove an absence of downstream generic memory/retrieval effects; it found no Hosted Room-specific isolation or automatic bridge. A runtime trace is required before making either claim.
- There is no Room Guardian UI, agent roster interaction, streaming/projection proof at this HEAD, or release qualification.

## 10. Federation finding

Federation is an **experimental combination of signed node manifests, trusted relay-session setup, document diff exchange, awareness-graph updates, and local/peer context search**. Its node manifest/key seam uses Ed25519 signing material; its routes require API-key access, federation enablement, signed/allowlisted trust policy, and egress policy checks.

It is not a canonical Room-chat protocol:

- no federation request/model/service references `HostedRoom`, Room participant/invitation identities, or canonical `chat_messages` replication;
- `SessionRequestBody` is document-oriented (with an optional thread field), and diff replication is document-ID based;
- graph snapshots and context-search results are separate experimental projections;
- no current `RoomCapabilityGrant`, cross-node Room grant, remote Room projection, or remote Guardian invocation is implemented.

The inspected bounded paths keep transport/reachability separate from authority: Hosted Room access is authorized by owner scope or revalidated invitation/session state, while federation adds policy/trust/egress controls. Tailscale appears in the isolated tester deployment posture as network reachability, not as a Hosted Room authorization grant. This is code-path evidence, not a broad security proof for every future transport.

## 11. Atlas campaign impact

| Task | Classification | Reason |
| --- | --- | --- |
| A0 — Atlas V0.1 interaction contract | Rewrite | It must distinguish current `HostedRoom -> one ChatThread` from proposed HomeBase/Space/Room/Conversation vocabulary and forbid treating a renderer as authority. |
| A1 — shell entry/navigation | Unchanged | A generic Atlas route/shell can remain a local presentation task, provided it does not claim an existing Room UI or navigation contract. |
| A2 — local Atlas projection | Simplify | Project owner-scoped existing Hosted Rooms and their one backing thread; use visibly derived placeholders for proposed HomeBase/Space only if the contract explicitly labels them. |
| A3 — Room Workspace shell | Split | Generic Workspace UI can be composed now, while shared Room resources, authorization, and data-source semantics are a separate future runtime task. |
| A4 — real Room/thread binding | Simplify | Reuse `HostedRoom.backing_thread_id`; do not add a second binding. A many-thread Room decision must be a later architecture/runtime extension. |
| A5 — interaction qualification | Rewrite | Separate focused test/code evidence, prior non-current proof, tester-profile route posture, missing Room client, and current supported-release proof. |

## 12. Recommended Atlas V0.1 seam

**Atlas should project owner-authorized existing `HostedRoom` records and each record's single canonical backing `ChatThread`, and compose existing AppShell/thread/Workspace presentation patterns; it must not create a second Room model, second transcript, `Room -> many Threads` relation, Room-scoped resource authority, cross-node protocol, or release claim.**

The narrowest safe first slice is read-only local projection with explicit status labels: `code/test present`, `not current supported release`, and `future/derived` where planned topology vocabulary is shown.

## 13. Surprises / architecture hazards

1. **Two Room meanings are already nearby.** Current `HostedRoom` is a durable, account-owned, single-thread collaboration boundary. ThreadSpace documents use Room as a proposed broader authorization context inside a Space. Collapsing them without an ADR would silently change semantics.
2. **Single-thread is enforced, not merely conventional.** The unique backing-thread constraint makes an Atlas many-thread display inaccurate unless it is marked as future/derived.
3. **The transcript has a subtle ownership split.** Guest messages are authored by guest participant provenance but use the Room owner's `ChatMessage.user_id` because the canonical thread is owner-bound. Any future resource/memory/export work must preserve both meanings.
4. **Invite revocation and participant removal differ.** Revocation blocks sessions through revalidation while preserving participant history; a human-removal state exists but no public owner removal flow was found.
5. **Backend capability has no frontend surface.** No Hosted Room React client/API hooks were found. Generic Workspace and thread UI are reusable presentation material, not evidence that Room interactions are shipped.
6. **Current-state lag matters.** `00-current-state.md` declares the prior-day `c4787236e` tip and warns Hosted Room is outside release claims; it does not prove this audited head.
7. **Older live proof is not current-head proof.** The R2 packet documents transplanted source and manual tables, so it cannot qualify this checkout's mounted image, migration, or UI.
8. **Federation nomenclature is hazardous.** Existing manifests/relays/diffs/graphs/context search are not a Room replication protocol or Room authority/grant system.
9. **Portability is contractual but unimplemented for Rooms.** The export/restore contract requires Room metadata and non-reusable invite verifier handling, but executable Hosted Room export/restore remains deferred.

## 14. Deferred questions

- Does a fresh, supported tester runtime built from this exact HEAD migrate Room tables, mount both Room routers, and complete owner/guest message and Guardian flows without manual source/table intervention?
- What is the exact generic-memory/retrieval effect of a backing-thread Room message under host account ownership, and what isolation contract is required before participant-private intelligence is introduced?
- Should future Atlas read normal owner thread APIs, dedicated Hosted Room projections, or a new read-only topology endpoint? That is an API/authority decision, not established by the current frontend.
- Is the future product relationship `HostedRoom == ThreadSpace Room`, a compatibility projection, or an intentionally separate concept? Current code and proposed contracts do not answer it.
- What explicit Room-resource ACL, provenance, export/restore mapping, shared-KB lifecycle, and conflict policy would be required before a Room Workspace becomes shared state?
- What grant, identity, key rotation/revocation, packet versioning, idempotency, and partition-convergence contract would authorize cross-node Room posting or participant-node Guardian execution?
- What current-tip proof and UX/API scope would be required before a Hosted Room could be named a beta preview rather than an unqualified code path?

## ADR impact

No ADR is created or amended. This discovery artifact identifies an implementation/proposal vocabulary collision and the missing decision boundaries; any change that equates current Hosted Rooms with proposed ThreadSpace Rooms, introduces multi-thread Room semantics, shared resources, personal/remote Guardian routing, or cross-node Room transport requires a separate architecture-impact decision before implementation.

## Validation scope

This is a documentation-only audit. No runtime behavior, database model, migration, route, frontend, or accepted architecture contract was changed. Validation must therefore establish only artifact/link/diagram integrity, not Hosted Room runtime qualification.
