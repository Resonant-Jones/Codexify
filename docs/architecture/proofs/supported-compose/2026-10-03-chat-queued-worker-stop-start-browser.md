# Queued ordinary browser chat across idle worker stop/start

Date: 2026-10-03. Evaluated code: active Goal branch commit
`97c1cb346dc296401d3efd0785aacab74284f69b`. Classification:
`PROOF_REQUIRED`; no source behavior changed. Complete supported-Compose
qualification remains `HOLD`.

## Atomic Task Spec

Use the real browser on the supported local Compose profile. Stop only an idle
`worker-chat`, submit one new ordinary chat turn, and prove acceptance remains
pending in Redis, the durable attempt, and the user interface. Restart the same
worker container and prove exactly one successful assistant completion through
raw terminal events, Postgres attempt binding, transcript readback, Redis
queue/lock cleanup, and browser reload. Preserve unrelated service and queue
state. Do not infer active-worker crash recovery or full-stack restart
behavior.

## Preconditions and test boundary

Project: `codexify_chat_branch_proof_896387ad2`; API
`http://127.0.0.1:18889`; browser frontend served from this checkout at
`http://localhost:5181`. Before stopping the worker:

- `/health` returned HTTP 200; profile `v1-local-core-web-mcp` was valid,
  local provider was selected, and cloud-capable configuration was absent.
- Backend, Postgres, Redis, Neo4j, and `worker-chat` were running; backend and
  Postgres healthchecks were healthy.
- The chat queue length was 0, canonical `turn_lock:*` scan was empty, and the
  chat worker heartbeat said `idle` with 42.9 seconds of TTL remaining.
- Unrelated eval/system queues held 19/1 entries. Only `worker-chat` was
  stopped and restarted. The eval queue later read 20 and the system queue
  remained 1; no command in this proof read, cleared, or consumed those queues.

## Accepted while the worker was stopped

`docker compose stop worker-chat` stopped only the idle chat worker. The real
browser submitted `Reply with exactly this marker:
QUEUED_CHAT_RESTART_RECOVERY_20261003` on a new thread.

| Surface | Observed while worker stopped |
| --- | --- |
| Thread / authored message | `23` / `42` |
| Request / task / turn | `req_f3a93e14fed04fe8b3b6d5f02c0d15b5` / `c74f9d31-141c-4d98-88ab-b0a1acbcf8da` / `db7b8dad-6d5f-458b-820d-460f06fdd64e` |
| Durable task receipt | `nonterminal`; exact task/request/thread/turn bound; no completed-message ID |
| Redis chat queue / lock | `1` / `turn_lock:23` present |
| Browser | Authored prompt visible, with no assistant response |

This established queue acceptance and persisted authorship while execution was
unavailable; it did not present acceptance as completion.

## Worker restart and completion

`docker compose start worker-chat` did not start the service: Compose reported
`backend is missing dependency migrator` because the one-shot migrator
container was absent. Backend, database, and Redis were already healthy. To
preserve the queued attempt and avoid rerunning migrations, the already-created
Compose worker container was started directly with
`docker start codexify_chat_branch_proof_896387ad2-worker-chat-1`. The worker
became running and consumed the queued task.

| Evidence | Result |
| --- | --- |
| Task receipt | `task.completed`, `completed_message_id=43`, reason `durable_completion_recorded` |
| Raw terminal event | `task.completed`; request, task, thread, turn, and `message_id=43` matched |
| Provider/model | Event and assistant metadata both reported `local` / `local-chat`; selection source `requested_model`; resolved model matched |
| Durable attempt | Postgres row bound the same request/task/thread/turn to completed assistant ID `43` |
| Transcript | User row `42`; one assistant row `43` contained exactly `QUEUED_CHAT_RESTART_RECOVERY_20261003` |
| Queue / lock / worker | Chat queue `0`; no canonical turn locks; worker heartbeat fresh and idle |
| Browser reload | Same authored prompt and one exact-marker assistant reply appeared; no second send occurred |

## Limits

This is fresh branch-local browser and durable proof of a queued task surviving
an idle chat-worker stop and restart. It does not prove the Compose `start`
wrapper succeeds in this project because its migrator dependency container was
missing. It also does not prove Redis/Postgres/backend restart durability,
active-worker crash recovery, graceful shutdown while work is active, the
complete supported-Compose bundle, or current-main behavior. The changed eval
queue depth during the test is treated as concurrent unrelated activity; its
entries were left untouched. Release readiness remains `HOLD`.
