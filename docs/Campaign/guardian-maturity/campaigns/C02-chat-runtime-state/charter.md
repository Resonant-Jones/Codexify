# C02: Chat Runtime State and Transcript Integrity

## Metadata

- **Campaign ID**: C02
- **Title**: Chat Runtime State and Transcript Integrity
- **Wave**: 1
- **Status**: `in-progress`
- **Owner**: resonant_jones
- **Risk**: MED
- **Architecture Impact**: yes
- **Governing ADRs/Contracts**:
  - [00-current-state.md](../../../architecture/00-current-state.md)
  - [Config and Ops](../../../architecture/config-and-ops.md)
  - [Chat Runtime Contract](../../../architecture/chat-runtime-contract.md)
  - [Runtime Protocol Token Contract](../../../architecture/runtime-protocol-token-contract.md)
  - [Completion Pipeline](../../../architecture/completion_pipeline.md)
  - [Flows](../../../architecture/flows.md)
  - [ADR-002 Dual State Machine Model](../../../architecture/adr/002-dual-state-machine-model.md)
  - [ADR-003 Message Identity vs Request Identity](../../../architecture/adr/003-message-identity-vs-request-identity.md)

## Purpose

Prove and later surface the authenticated Codexify backend chat runtime path and request lifecycle states in Guardian's UI. Fix UI interpretation of local runtime delay, request lifecycle, retry, replay, and orphaned attempts.

## Current Truth Anchors

What is true now:
- C00 is `go` — all health/catalog/model inventory surfaces agree.
- C11 is `go` — route topology confirmed.
- C01 has a visible read-only "Can I run?" verdict.
- Authenticated backend chat completion is proven in C02-T001.
- Task lifecycle states (QUEUED, AWAITING_MODEL, AWAITING_FIRST_TOKEN, STREAMING, COMPLETED) are observable via SSE.
- Transcript persistence is proven — assistant messages are persisted to the thread.
- The Chat Runtime Contract defines canonical provider and request states.

What is not yet true:
- Provider runtime state UI does not show granular states (CONNECTING, MODEL_WARMING, READY, GENERATING, DEGRADED, ERROR).
- Retry/replay/orphan handling is not yet surfaced in the UI.
- The UI does not distinguish message identity from attempt identity.
- Slow local warmup is not visually distinguished from offline.

## Non-Goals

- No UI implementation in the proof phase.
- No endpoint creation.
- No auth redesign.
- No provider routing changes.
- No Pi/Coder behavior.
- No coding delegation.

## Invariants

- Do not collapse provider runtime state and request state into a single concept.
- Do not label slow local warmup as "offline."
- Do not create fake new messages for retries — new attempt, not new message.
- Do not treat task acceptance as completion.
- Do not treat event publication as UI receipt.

## Dependencies

- C00 (Truth Gate) — `go` — health/catalog/model inventory proven
- C11 (API Route Audit) — `go` — route topology confirmed

Campaigns this enables:
- C03 (Coding Delegation Spine) — needs request state awareness
- C10 (Recovery) — needs request state tracking for orphan/stale detection

## Backend/API Surfaces

- `POST /api/chat/threads` — thread creation
- `POST /api/chat/{thread_id}/messages` — message send
- `POST /api/chat/{thread_id}/complete` — completion trigger
- `GET /api/tasks/{task_id}/events` — SSE task event stream
- `GET /api/chat/{thread_id}/messages` — message/transcript retrieval
- `/health/chat` — worker/queue/provider health

## Frontend Surfaces

- `frontend/src/features/chat/hooks/useInferenceRequestState.ts` — lifecycle state tracking
- `frontend/src/contracts/runtimeTokens.ts` — canonical state tokens
- `frontend/src/shared/runtimeVisualState.ts` — visual state mapping
- `frontend/src/features/chat/GuardianChat.tsx` — chat UI

## Proof Gates

| Category | Required Evidence |
|----------|-------------------|
| Docs proof | C02 charter, backlog, proof-pack, decision-log exist |
| Backend seam proof | Authenticated backend chat completion through Codexify backend |
| Backend seam proof | Task lifecycle states observable via SSE |
| Backend seam proof | Transcript persistence proven |
| Live supported-path proof | Chat completion on local Docker Compose with local provider |
| Operator usability proof | Request lifecycle states inspectable (deferred to UI task) |

## Done-When

The campaign is done when:
1. Authenticated backend chat completion proof is recorded.
2. Lifecycle states are mapped to the current contract.
3. Transcript persistence is proven.
4. Retry/replay/orphan proof seams are identified.
5. Granular provider runtime state is surfaced in the UI.
6. Slow warmup is not labeled offline.
7. Guardian shows `awaiting_model`, `awaiting_first_token`, `orphaned`, `replayed`, and related states.

## Risks

- **Provider state collapse**: The frontend currently collapses provider state to ONLINE/DEGRADED/OFFLINE. Fixing this requires backend to emit granular provider state to the frontend.
- **Orphan/replay detection**: Orphaned and replayed requests require backend task/attempt tracking. SSE gaps can cause false negatives.

## Task Queue

Tasks are tracked in [`backlog.md`](./backlog.md).
