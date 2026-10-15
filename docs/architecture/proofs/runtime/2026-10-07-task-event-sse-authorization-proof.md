# Task-Event SSE Authorization Proof

> Classification: runtime proof receipt / bounded authorization repair
> Evaluated change: commit subject `Authorize task event streams by canonical thread`; parent `d4d6a71276694a104f0955a497981b2100236209`
> (The evaluated commit's own hash is intentionally not self-referenced here, because amending it to embed its hash would change that hash.)
> Governing decisions: [ADR-091](../adr/091-durable-chat-completion-attempt-authority.md), [ADR-092](../adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md)
> Release posture after this proof: `PUBLIC_INGRESS_AUTH_BOUNDARY=HOLD` (unchanged)

## 1. What this proves

`GET /api/tasks/{task_id}/events` no longer treats a caller-selected `task_id`
or a generic API key as resource authority. The route now binds the caller to
the canonical durable task resource before any Redis task-event transport can
be created.

This receipt qualifies **only** that route. It does not qualify the public
internet-facing authentication boundary, and it does not authorize an
Access-free canary.

## 2. Pre-repair authorization path

```text
caller supplies task_id
  -> Depends(require_api_key)          # generic, non-resource authority
  -> StreamingResponse constructed
  -> event_stream() generator starts
  -> task_events.read_events(task_id)  # Redis read, no ownership check
```

The generic key established *that a credential existed*, never *that the caller
owned the task*. This is the authority defect class reproduced by the
2026-09-25 public-ingress proof (matrix rows 8 and 9), where an approved
Account B session read an Account A task event by supplied task ID.

## 3. Post-repair authorization path

```text
credential presence classified across account / guest / operator lanes
  -> mixed lanes rejected (HTTP 400 mixed_principal_credentials) before lookup
  -> exactly one typed principal resolved (no cross-lane fallback)
  -> get_chat_completion_attempt_by_task_id(task_id)   # ADR-091 durable lineage
       missing attempt -> fail closed, no Redis
  -> require_thread_read_access(thread_id, principal)  # canonical thread policy
       account -> canonical chat thread ownership
       guest  -> room lifecycle + backing-thread match
  -> StreamingResponse constructed
  -> event_stream() generator starts
  -> task_events.read_events(task_id)   # first Redis read, authorization already complete
```

Implementation:

- `guardian/core/task_event_access.py` — principal classification, mixed-lane
  rejection, durable lineage resolution, and the authorization entry point.
- `guardian/guardian_api.py` — `stream_task_events` drops the
  `Depends(require_api_key)` parameter and calls
  `authorize_task_event_stream(...)` before creating any transport object.

The route holds no FastAPI auth dependency at all; authority is resolved
in-body because the credential to validate depends on the durable task lineage.

## 4. Authority matrix

| Caller credential | Task | Result | Redis reads |
|---|---|---|---|
| None (anonymous) | any | 401 | 0 |
| Malformed single selector | any | 401 | 0 |
| Valid `account_session`, unexpired | Account A task | 200 | authorized |
| Valid `account_session` (Account B) | Account A task | 403 | 0 |
| Valid `account_session` (Account A) | Account B task | 403 | 0 |
| Expired `account_session` | own task | 401 | 0 |
| Purpose-less signed legacy token | any | 401 | 0 |
| `operator_session` | any | 401 | 0 |
| Raw `X-API-Key` (remote posture) | any | 401 | 0 |
| Raw `X-Guardian-Key` (remote posture) | any | 401 | 0 |
| Guest token in account lane | any | 401 | 0 |
| `account_session` + guest selector | any | 400 mixed | 0 |
| `account_session` + raw key | any | 400 mixed | 0 |
| `account_session` + `operator_session` | any | 400 mixed | 0 |
| Guest selector + malformed signed material | any | 400 mixed | 0 |
| Valid guest, same room, task on room backing thread | room task | 200 | authorized |
| Valid guest, other room | room task | 401 | 0 |
| Valid guest, account-owned task | account task | 401 | 0 |
| Guest with removed participant | room task | 401 | 0 |
| Guest in inactive/closed room | room task | 401 | 0 |
| Expired guest session | room task | 401 | 0 |
| Guest with revoked invitation | room task | 401 | 0 |
| Any valid principal, task without durable attempt | unknown task | 404 | 0 |
| Any valid principal, attempt with absent canonical thread | unknown thread | 404 | 0 |

## 5. Zero-Redis-read denial evidence

Denial is proven structurally by ordering, not only by assertion:

- `authorize_task_event_stream` raises before `StreamingResponse` is
  constructed, so no retry frame, heartbeat, or event body can be emitted.
- The event generator, which is the only caller of `task_events.read_events`,
  is only reached after authorization returns.
- Tests instrument `task_events.read_events` with a call recorder and assert
  `calls == []` for every denied row in the matrix above.

`tests/identity/test_task_event_sse_authorization.py` also asserts that a task
with no durable attempt never reaches the canonical thread lookup, proving
ownership is never inferred from Redis payloads, task IDs, event contents,
debug fields, request IDs, or frontend state.

## 6. SSE transport compatibility

Preserved unchanged after authorization succeeds:

- `retry: 3000` initial hint
- `id:` / `event:` / `data:` framing
- `last_id` query handling and `Last-Event-ID` header precedence
- malformed cursor normalization (`garbage` -> `0-0`)
- resume starting from the requested cursor
- terminal-event termination
- Redis read-failure retry and heartbeat behavior (untouched code)

The transport loop was not refactored; only the pre-transport authorization
step was added.

## 7. Validation run

| Suite | Result |
|---|---|
| `tests/identity/test_task_event_sse_authorization.py` | 32 passed |
| `tests/identity/test_thread_read_access.py` | 14 passed, 1 failed (pre-existing) |
| `tests/identity/test_account_purpose_strict_migration.py` | 15 passed |
| `tests/identity/test_operator_session_boundary.py` | 6 passed |
| `tests/auth/test_private_preview_access.py` | 3 passed |
| `tests/auth/test_auth_flow.py` | 5 passed |
| `tests/identity` (full) | failure set identical to pre-change baseline |
| `tests/routes` + `tests/ops` + `tests/auth` + `tests/core` (broad) | diffed against pre-change baseline; no new failures |

The pre-existing failure is
`tests/identity/test_thread_read_access.py::test_account_session_cannot_become_guest_principal`,
which fails on `issue_session_token() missing 1 required keyword-only argument:
'purpose'` in a read-only file. It reproduces identically without this change.

All credentials, tasks, threads, rooms, invitations, and event payloads in the
new suite are deterministic synthetic fixtures. No real account data is read or
asserted.

## 8. Frozen migration accounting

`tests/identity/test_account_purpose_strict_migration.py` needed no change: its
frozen `FROZEN_ACCOUNT_REGISTRATIONS` inventory never listed
`/api/tasks/{task_id}/events`, so the dependency change is not represented
there.

`tests/identity/test_operator_route_auth_migration.py` **did** name this route's
pre-repair dependency, asserting `require_api_key in set(_calls(sse_route))` in
`test_non_operator_sentinels_keep_distinct_auth_dependencies`. That single
expectation was updated to reflect the new canonical seam while preserving the
test's actual sentinel intent — that the route is *not* operator-gated. This is
a required, minimal expansion beyond the initial authorized file list, recorded
here deliberately rather than applied silently.

## 9. Known limitations

- **Local posture leniency is intentional and pre-existing.** In local
  single-user posture, identity resolution follows the local runtime-mode
  contract rather than the remote mixed-lane rule, matching ADR-092's explicit
  carve-out. Local `require_thread_read_access` also does not enforce
  ownership when `multi_user_enabled` is false. This is unchanged behavior, not
  a regression, but it means the isolation matrix above is proven at the
  remote/private-preview boundary only.
- **`POST /api/tasks/{task_id}/cancel` is out of scope and still unbound.** It
  remains a task-resource authorization gap. Its `task_id` is likewise
  caller-selected and is not currently bound to a durable attempt/thread before
  mutation. This is recorded as deferred, not repaired.
- **Generic remote auth debt is untouched.** The `auth_dependencies.py`
  resolver, legacy account-token acceptance, and global mixed-principal
  enforcement outside this route remain open.
- **`tests/routes/test_chat_task_events_lifecycle.py` still passes** through its
  MagicMock chatlog DB. It remains a transport/framing test, not an
  authorization test; the new suite carries the authorization proof.
- **No live-runtime probe.** Evidence is bounded test/code-path proof on the
  current tip, not a public-ingress deployment qualification.

## 10. Cloudflare

Cloudflare Access, Cloudflare Tunnel, DNS, proxy/WAF configuration, and public
route configuration were **not** modified. Cloudflare Access remains enabled.
The Access-free canary was not created or exercised, and no login rate limiting,
cookie transport, session TTL, registration, or activation/recovery behavior
was changed.

## 11. Next gate

The next prerequisite is the **complete current-tip public-ingress
requalification** across the full matrix with Cloudflare Access still in place.
Until that runs, `PUBLIC_INGRESS_AUTH_BOUNDARY=HOLD` remains accurate and no
release claim is widened.