# Tester proof-session authentication

## Result

`TESTER_PROOF_SESSION_PASS`

One proof-only Tester identity was registered through the normal Guardian
registration route, then logged in once through the normal login route. Its
genuine bearer session completed one scoped, read-only application request.
No thread, message, completion task, model invocation, provider fallback, or
Watchdog activity occurred.

This is authentication-boundary evidence only. It does not prove a chat
completion, durable assistant output, retrieval, provider quality, or release
readiness.

## Source, runtime, and authority

- Source HEAD: `1cabc22c77279b9a6f9b5c4cbbaed5fbcb453bab` (`Prove tester chat worker readiness`).
- Branch: `codex/diagnose-tester-fresh-chroma-failure`.
- Required ancestors passed: `1cabc22c77279b9a6f9b5c4cbbaed5fbcb453bab` and `9b124086272d502e54071bbf493feef81b1f1ab4`.
- Compose project: `codexify_tester`; the backend remained published at `127.0.0.1:8889`.
- `.env.tester` remained ignored and unchanged.

Tester is configured with `GUARDIAN_AUTH_MODE=remote`. In this mode, Guardian
rejects static `X-API-Key` authentication and accepts a valid bearer session
or `gc_session` cookie. The proven system is native Guardian password
authentication backed by the canonical Postgres `users` row; it is not an
admin-provisioning or third-party-provider flow.

| Contract | Proven implementation |
| --- | --- |
| Registration route | `POST /api/auth/register` |
| Login/session route | `POST /api/auth/login` |
| Logout/revocation route | `POST /api/auth/logout` |
| Registration fields | `username`, `password` |
| Session representation | Guardian-signed bearer token, backed by Redis `session:{token}` |
| Normal session TTL | 86,400 seconds (24 hours) |
| Email verification | Not part of this normal registration implementation; no bypass was used |

The registration route is mounted as a core auth route, accepts ordinary
self-registration outside private-preview mode, creates the canonical `User`
row, and returns its `user_id`. Tester has `GUARDIAN_EXPOSURE_MODE=local_safe`,
not the private-preview mode that disables self-registration.

## Proof-only identity and secret handoff

The account identifier was generated with the proof-only prefix and is
recorded here only in bounded form:

`codexify-runtime-proof-20260824-…be13`

Before registration, the following local-only handoff file was created:

| Property | Value |
| --- | --- |
| Path | `/private/tmp/codexify-tester-proof-session-20260824.env` |
| Permission mode | `0600` |
| Retained values | proof identifier, high-entropy password, canonical user ID, registration/login times, bearer session token, expiry, and endpoint metadata |
| Repository state | outside the repository; not staged or committed |

No password, bearer token, cookie, refresh token, signing secret, provider
credential, or unredacted proof identity appears in this artifact.

## One normal registration and one normal login

| Step | Attempt count | Time (UTC) | Result |
| --- | ---: | --- | --- |
| Normal registration | 1 | `2026-08-24T21:56:50Z` | `200`; returned canonical user ID matched the generated proof identity |
| Normal login | 1 | `2026-08-24T21:57:47Z` | `200`; returned user ID matched the proof identity and a Guardian bearer session was issued |
| Session expiry | — | `2026-08-25T21:57:48Z` | Redis session remained present after qualification, with 86,345 seconds TTL observed |

No existing personal credential, static API key, direct database insertion,
admin API, handcrafted JWT, email-verification bypass, or second account was
used.

## Authenticated non-inference request

Exactly one post-login authenticated application request was made:

```text
GET /api/chat/threads?limit=1&user_id=<proof-account-id>
Authorization: Bearer <normal Guardian session>
```

It returned `200`, `ok=true`, and `threads=[]` at
`2026-08-24T21:58:00Z`.

This endpoint is the narrow read-only list operation. It requires the remote
session boundary and derives `RequestUserScope` from Redis session validation.
In multi-user scope, its `user_id` filter rejects any value that does not
match the authenticated account; the successful scoped request therefore
confirms that the bearer session resolved to the proof identity. It lists
threads only and does not create a thread, message, task, profile, or provider
request.

## Durable linkage and no-work boundary

Read-only Postgres inspection after the request found one canonical `users`
row for the proof identity, with `id == username` and `role=guest`. The proof
identity had zero `chat_threads` and zero `chat_messages` rows.

| Evidence | Before / after proof |
| --- | --- |
| Proof-user `users` rows | 0 / 1 (the one authorized normal registration) |
| Proof-user chat threads | 0 / 0 |
| Proof-user chat messages | 0 / 0 |
| `codexify:queue:chat` depth | 0 / 0 |
| Watchdog delivery receipts | 0 / 0 |
| Watchdog review attempts | 0 / 0 |
| Watchdog review results | 0 / 0 |
| Backend provider-invocation log markers in the proof window | 0 |
| `MODEL_INVOCATIONS_DURING_AUTH_PROOF` | 0 |

Chat completion tasks are queue/event-backed rather than represented by a
separate durable `chat_tasks` table. The only authenticated application route
used was the scoped GET above; its source path reads the thread list after
session resolution and does not construct or enqueue `ChatCompletionTask`.
The auth routes use only the canonical user database and Redis session store.
A mode-restricted backend-log capture from registration through closeout found
zero Whoosh'd-completion, DeepSeek, or chat-completion invocation markers and
was removed after the count check.

## Runtime closeout

| Property | Observation |
| --- | --- |
| Backend | running and Docker `healthy`; restart count `0` |
| `worker-chat` | running; restart count `0` |
| Worker heartbeat | `worker=chat`, `status=idle`, queue `codexify:queue:chat`, age 4 seconds |
| `/health` | `status=ok`, service `core` |
| `/health/chat` | `ok=true`, `status=healthy`, provider `local`, configured/resolved model `gemma-4-12b-it-qat-4bit` |
| Provider fallback / DeepSeek use | none |

The backend, worker, Redis queue, Chroma state, provider/model configuration,
and Watchdog surfaces were not changed. The proof session remains available in
the restricted local handoff file for the dependent completion qualification.
Proof-account cleanup is intentionally deferred until that qualification is no
longer needed.

## ADR impact and validation

**No ADR impact — existing identity/session authority proven only.**

- required ancestry, worktree status, and `.env.tester` ignore checks passed;
- auth-route, session-store, remote-boundary, and scoped-thread-list source
  inspection completed before the runtime action;
- normal registration, normal login, one authenticated non-inference request,
  canonical-user readback, Redis TTL readback, queue/Watchdog checks, and
  backend/worker health checks passed;
- `python3 scripts/validate_docs.py` and Git diff checks are recorded at
  commit closeout.

## Deferred next slice

Use this authenticated proof-only Tester session to prove exactly one ordinary
default-provider chat completion through local
`gemma-4-12b-it-qat-4bit`, with durable API and PostgreSQL readback, no cloud
fallback, no retry, and no Watchdog activity. Do not combine it with
proof-account cleanup.
