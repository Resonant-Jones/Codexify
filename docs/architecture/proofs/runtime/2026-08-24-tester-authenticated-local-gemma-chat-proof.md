# Authenticated Tester local/Gemma chat completion proof

## Result

`TESTER_AUTHENTICATED_LOCAL_CHAT_PASS`

One existing proof-only Tester account, authenticated with its normal Guardian
bearer session, created one ordinary thread, persisted one exact user message,
and submitted exactly one ordinary completion request. The normal
`worker-chat` queue path produced the exact assistant output
`local-gemma-runtime-ok`. Durable API, Postgres, and Redis-stream readbacks
identify the execution as `local` / `gemma-4-12b-it-qat-4bit`, with no
fallback, no tool turn, no retry, and no DeepSeek use.

This proves one authenticated ordinary local-model completion on this running
Tester stack. It is not a release claim for `main`, a general provider
qualification, a retrieval proof, or evidence for any additional turn.

## Source, runtime, and authority

- Source HEAD before the proof: `c9ba45643dbb3bb8ff4f726841288f56c5a72ae4`
  (`Prove tester user authentication`).
- Branch: `codex/diagnose-tester-fresh-chroma-failure`.
- Required ancestry checks passed for the dependent authenticated-session and
  worker-readiness proof commits.
- Compose project: `codexify_tester`; backend endpoint:
  `http://127.0.0.1:8889`.
- Backend: `codexify_tester-backend-1`, Docker `healthy`, restart count `0`.
- Worker: `codexify_tester-worker-chat-1`, running, restart count `0`.
- Pre- and post-closeout `/health/chat`: local provider and configured model
  `gemma-4-12b-it-qat-4bit`; Redis `ok`; worker heartbeat `fresh`.
- `.env.tester` remained ignored and unchanged. Its selected ordinary local
  model was `gemma-4-12b-it-qat-4bit`; no provider or mode setting was edited.

The account was the already-qualified proof-only identity, recorded here only
as `codexify-runtime-proof-20260824-…be13`. Its restricted handoff file stayed
outside the repository at mode `0600`. No password, bearer token, cookie,
credential, or unredacted account identifier appears in this artifact. The
session was valid before the mutation window: one scoped read-only
`GET /api/chat/threads?limit=1&user_id=<proof-account-id>` returned `200` and
the account had no existing threads. No re-login was needed.

## Authorized mutation window

The proof window began at `2026-08-25T01:54:11Z`. Before it, the normal chat
queue depth was `0`; global durable high-water marks were `5136` threads and
`113326` messages; the proof identity owned zero threads and messages.

Exactly these three authenticated normal application mutations occurred:

| Operation | Count | Result |
| --- | ---: | --- |
| `POST /api/chat/threads` with title `Tester proof: authenticated local Gemma` | 1 | Created owned thread `5137` |
| `POST /api/chat/5137/messages` with role `user` and the exact required text | 1 | Persisted user message `113327` |
| `POST /api/chat/5137/complete` with `{}` | 1 | Accepted task `d35e3b38-febd-4df6-a47a-6ef12322c28f` |

The only user content was:

```text
Reply with exactly: local-gemma-runtime-ok
```

The completion request body intentionally contained no explicit
`provider`, `model`, tools, or mode field. The saved ordinary thread
configuration resolved to `providerId=local`,
`modelId=gemma-4-12b-it-qat-4bit`, `inferenceMode=fast`, and
`retrievalSource=project`. The terminal task record attributes final model
selection to `LOCAL_CHAT_MODEL`; that is worker resolution, not a caller
override.

The acceptance receipt carried request ID
`req_62d63e993bca483c89544af1bcb0238c` and turn ID
`cf97a866-ece4-47c5-9645-e5c5650c3f03`. No second completion endpoint call,
retry, fallback request, or alternate route was made.

## Queue, worker, and provider execution evidence

The durable Redis stream for task
`d35e3b38-febd-4df6-a47a-6ef12322c28f` contained 18 events. It recorded one
each of `task.created`, `QUEUED`, `task.running`, `AWAITING_MODEL`,
`AWAITING_FIRST_TOKEN`, `STREAMING`, `COMPLETED`, and `task.completed`.

| Property | Durable observation |
| --- | --- |
| Unique execution attempts | `1`: `attempt_37a536f14f32442dad85f46d2db2f438` |
| Attempted provider/model | `local` / `gemma-4-12b-it-qat-4bit` |
| Final provider/model | `local` / `gemma-4-12b-it-qat-4bit` |
| Selection source | `LOCAL_CHAT_MODEL` (strict local resolution) |
| Fallback / tool turn | `false` / `false` |
| Terminal state | success; visible output emitted; explicit provider terminal observed |
| Finish / transport | `stop` / cleanly ended |
| Retry permitted | `false` |
| Provider correlation | `whooshd_2a9030aaeb6c4419858be9396769e37a` |

This stream is the strongest available provider-execution evidence: it binds
one Codexify task and one attempt to one Whoosh'd response correlation and a
successful local/Gemma terminal record. A separately mounted raw Whoosh'd
access log was not available, so the proof does not claim an independent
provider-side access-log count. The task-scoped backend/worker log capture was
restricted, counted, and removed; it contained two task-ID lines, zero
DeepSeek markers, and zero task-correlated error/failure markers. It did not
add provider detail beyond the durable terminal record.

Therefore `MODEL_INVOCATION_EVIDENCE_DURING_PROOF=1`: one uniquely identified
normal worker attempt reached one successful local/Gemma terminal event. No
DeepSeek, cloud, alternate provider, retry, tool loop, or fallback execution
appears in the task lineage.

## API and Postgres readback

Authenticated API readback returned exactly two messages for thread `5137`:

| Message ID | Role | Content / execution |
| --- | --- | --- |
| `113327` | user | `Reply with exactly: local-gemma-runtime-ok` |
| `113328` | assistant | `local-gemma-runtime-ok`; attempted and final `local` / `gemma-4-12b-it-qat-4bit`; `fallback_triggered=false` |

The thread readback returned the same resolved thread configuration above.
Postgres independently returned exactly one matching owned `chat_threads` row,
one user `chat_messages` row, one assistant row, and two messages total. The
thread metadata's latest completion task ID was the same accepted task ID.
The persisted assistant response and execution metadata matched the API
readback exactly.

The normal queue was depth `0` after terminal completion. There is no separate
durable `chat_tasks` table in this architecture; task lineage is the queue and
its Redis event stream. The one `task.created` event, one unique attempt ID,
one terminal event, and one persisted assistant row establish that no surprise
task or duplicate assistant response was created for this proof thread.

## Preserved boundaries

No source, test, configuration, provider setting, route, queue implementation,
Redis content, Postgres content outside the three authorized normal chat
mutations, migration, Chroma state, Whoosh'd state, or DeepSeek state was
manually changed or repaired.

| Boundary | Evidence |
| --- | --- |
| Watchdog | Dedicated Redis queue depth `0`; zero matching Redis keys; Postgres delivery receipts, attempts, snapshots, dispatches, and results all remained `0` |
| Chat queue | `0` before and `0` after terminal completion |
| Backend and worker | backend healthy / worker running; both restart counts `0` |
| Chroma preservation | canonical and failed-init preservation directories remain read-only (`dr-xr-xr-x`) |
| Secrets | restricted raw log capture removed; no credential material committed or documented |

The branch-local proof does not alter the current-main release boundary in
`docs/architecture/00-current-state.md`: that document remains correct that
the corresponding current-`main` runtime proof is still open. No current-state
or runbook/configuration update was warranted.

## ADR impact and validation

No ADR change. This is evidence under existing ADR-074 provider/model
authority: the worker resolved the configured local Gemma model through
`LOCAL_CHAT_MODEL`; it neither selected the bounded cloud lane nor expanded
provider authority.

- Required ancestry, clean-worktree, session-validity, and `.env.tester`
  ignore/posture checks passed before the mutation window.
- Pre/post backend health, worker heartbeat, container state, queue-depth, and
  Watchdog-boundary reads passed.
- API, Postgres, and durable Redis-stream task readbacks passed.
- Documentation validation and Git diff checks are recorded at commit closeout.

## Scope boundary

This completed the requested one-turn qualification only. It does not prove
retrieval quality, multi-turn behavior, retries, tool use, cloud-provider
behavior, release readiness on `main`, or any Watchdog capability.
