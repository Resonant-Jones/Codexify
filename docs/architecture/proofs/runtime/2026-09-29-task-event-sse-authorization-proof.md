# Task-Event SSE Authorization Proof — 2026-09-29

## Result

**PASS for the focused route authorization code and test surface.** This is not
a live private-preview or public-ingress proof. The full public-ingress
authentication boundary remains `HOLD`.

## Baseline and implementation

- Branch: `codex/enforce-mixed-principal-boundary`
- Baseline: `d56d9df7dc3a75530388d3d68eaa30169276b08a`
- Implementation commit: `88a596661`
- Route: `GET /api/tasks/{task_id}/events`
- Handler: `guardian.guardian_api.stream_task_events`

The path parameter is the queue-facing `backend_task_id`. The route resolves
only `ChatCompletionAttempt.backend_task_id`, takes the durable `thread_id`,
and passes it with the authenticated principal to `require_thread_read_access`.
It does not look up by `request_id` or use request/event metadata as authority.

## Admission order

1. Reject incompatible principal credential presence through the existing
   `reject_mixed_principal_credentials` boundary.
2. Resolve an existing principal lane: exact remote account session, local
   request-user/API-key behavior, or purpose-scoped Hosted Room guest session.
   A remote operator session or raw operator API key does not resolve a user
   principal.
3. Query the durable attempt by exact `backend_task_id`.
4. Authorize its canonical `thread_id` with `require_thread_read_access`.
5. Only after those checks return the existing SSE response; the generator
   then reads Redis.

An absent attempt returns HTTP 404 before Redis. Account cross-thread access
keeps the shared policy's HTTP 403 denial; Hosted Room guest lifecycle, room,
or thread mismatch keeps its HTTP 401 denial. No denied request gets an SSE
response body. Missing or empty Redis data after an authorized attempt remains
transport behavior; no event is synthesized from Postgres.

## Focused matrix

The focused route tests prove:

- canonical thread owner can subscribe and existing event framing/payloads are
  preserved;
- another account is denied even with the exact backend task ID, with zero
  Redis reads and no event/thread/turn disclosure;
- the Hosted Room backing-thread owner can read its task stream;
- an active same-room guest can read the eligible task stream without becoming
  the canonical thread owner;
- removed, wrong-room, wrong-thread, malformed, and wrong-purpose guest access
  fails before Redis;
- anonymous, invalid account, remote operator-session, and raw operator-key
  requests fail before attempt lookup; mixed account/guest presence returns
  HTTP 400 before lookup;
- unknown and Redis-only backend task IDs return HTTP 404 without Redis reads;
- using a valid `request_id` as the path value does not match the attempt and
  returns HTTP 404;
- a spoofed `X-User-Id` does not override the authenticated remote account;
- `Last-Event-ID` reconnect cursors are passed to Redis only after the same
  authorization decision.

## Validation

Commands and results:

```text
/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/identity/test_task_event_stream_authorization.py \
  tests/routes/test_chat_task_events_lifecycle.py
19 passed

/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/identity/test_mixed_principal_boundary.py \
  tests/identity/test_identity_boundary_contract.py \
  tests/identity/test_account_purpose_strict_migration.py \
  tests/identity/test_operator_session_boundary.py \
  tests/identity/test_operator_route_auth_migration.py \
  tests/identity/test_account_observability_service_capability.py \
  tests/identity/test_websocket_account_session_purpose.py \
  tests/identity/test_thread_read_access.py \
  tests/identity/test_task_event_stream_authorization.py
265 passed

/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/core/test_chat_completion_attempt_persistence.py \
  tests/core/test_chat_completion_enqueue_service.py \
  tests/routes/test_chat_routes.py \
  guardian/tests/routes/test_hosted_rooms.py \
  guardian/tests/routes/test_hosted_room_guest.py \
  tests/routes/test_chat_task_events_lifecycle.py
294 passed, 3 xpassed

/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/identity/test_operator_route_auth_migration.py
16 passed

/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/auth/test_private_preview_access.py
3 passed
```

The runtime-facing tests use deterministic database/Redis instrumentation.
They do not establish live Cloudflare, Tunnel, browser, or private-preview
behavior. Cloudflare Access is unchanged.

## Scope and architecture

Changed runtime files are limited to `guardian/guardian_api.py`,
`guardian/core/dependencies.py`, and the small composition helper
`guardian/core/task_event_access.py`. Tests cover the new route boundary and
update the existing SSE lifecycle fixture to include a durable attempt. The
existing account-session-to-guest negative fixture now uses the canonical
`account_session` purpose; the frozen route-auth assertion records the new
route-specific principal dependency.

No model, migration, queue, Redis event transport, thread-read policy,
WebSocket, frontend, Cloudflare, or public-ingress proof receipt was changed.
The implementation follows ADR-091 durable attempt authority and ADR-092
credential-purpose separation. Global local-first defaults remain unchanged.

## Remaining qualification

This focused route repair does not close the full public-ingress matrix.
Rerun that matrix from the beginning against the repaired runtime with
Cloudflare Access still enabled before considering any Access-free canary.


## PR #848 reconciliation and bounded review follow-up — 2026-10-02

The conflict reconciliation at `6746bbc640fe8241c287a2cce646bc6ab466e5fc`
merges `main` at `b04e0d088e7627f29e4476dcf268ca5f0d78faa5`. It retains
both presence-based mixed-principal rejection and the typed account-session
failure signal from main. Mixed-principal HTTP 400 responses do not carry
`X-Guardian-Auth-Failure: ACCOUNT_SESSION_INVALID`.

The bounded review follow-up gates task-event mixed-principal rejection with
the existing remote/private-preview boundary and offloads synchronous durable
resource authorization from the async SSE event loop. Authorization still
finishes before response construction and Redis consumption. Regression
coverage includes legitimate local guest access with supplemental session
material, single-lane remote guest access, and off-loop authorization queries.

Focused follow-up validation:

```text
/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/identity/test_task_event_stream_authorization.py \
  tests/identity/test_mixed_principal_boundary.py \
  tests/routes/test_chat_task_events_lifecycle.py \
  tests/routes/test_chat_thread_remote_auth.py
34 passed
```

**Merge readiness remains HOLD on the non-chat task-family review finding.**
The generic endpoint has non-chat producers/consumers, while the present
resource guard requires a durable chat completion attempt. Agent runs,
delegation, voice, and warmup need an explicit supported-family inventory and
canonical access/acceptance contract before admitting their streams here.
Neither Redis existence nor caller-supplied task/thread metadata may supply
that missing authority. This follow-up does not introduce such a policy or
claim preserved generic non-chat stream compatibility.

No live deployment, ingress requalification, or Cloudflare mutation occurred.
The original focused proof and public-ingress HOLD remain historically bounded.
