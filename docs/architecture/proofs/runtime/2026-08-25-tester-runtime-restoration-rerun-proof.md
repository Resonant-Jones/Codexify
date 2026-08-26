# Tester runtime restoration rerun proof

## Result

`TESTER_RUNTIME_RESTORED_MODEL_UNAVAILABLE`

The canonical Tester backend and normal `worker-chat` restored from the
existing durable state after migrator-image coherence was repaired. The
infrastructure path is healthy, but the exact operator-selected local model
`gemma-4-12b-it-qat-4bit` is not advertised by the reachable Whoosh'd runtime.
Guardian correctly remains fail closed; no model was substituted or invoked.

This is a branch-local live-runtime receipt. It does not establish
current-`main` release readiness, a chat completion, or Watchdog/Gemma
qualification.

## Runtime identity and authority

- Source HEAD: `17aebb8d8724998510578c188fc9af73a7f248fb`.
- Branch: `codex/diagnose-tester-fresh-chroma-failure`.
- Required coherence, prior-failure, and authenticated-Gemma proof commits
  were verified ancestors.
- Compose project: `codexify_tester`.
- Compose inputs: `docker-compose.yml`, `docker-compose.tester.yml`, and
  `docker-compose.whooshd-deepseek.yml`, with ignored `.env.tester`.
- Repaired backend/migrator image:
  `sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf`.

The non-secret Tester authority was read only and unchanged:

| Setting | Value |
| --- | --- |
| `LLM_PROVIDER` | `local` |
| `LOCAL_CHAT_MODEL` | `gemma-4-12b-it-qat-4bit` |
| `ALLOW_CLOUD_PROVIDERS` | `true` |
| `CODEXIFY_LOCAL_ONLY_MODE` | `false` |
| `CODEXIFY_EGRESS_ALLOWLIST` | `deepseek` |

The canonical Compose render passed. Its sanitized backend/worker values kept
local provider selection, the one forwarded `LOCAL_CHAT_MODEL` selection,
bounded DeepSeek cloud posture, and canonical `db`/`redis` references. It
emitted only the pre-existing optional-unset `LOCAL_VISION_MODEL` and
`LOCAL_GGUF_MODEL` warnings.

## Migration, durable-state, and pre-start gates

Source Alembic `heads`, the repaired canonical migrator runtime, and live
Tester PostgreSQL all agreed on `6e9f0a1b2c3`. The repaired runtime resolved
that revision before startup; no image rebuild was needed in this task.

| Component | State before the one backend start |
| --- | --- |
| `db` | running and Docker healthy |
| `redis` | running and reachable |
| `migrator` | exited `1` on the prior stale image |
| `backend` | created on the prior stale image |
| `worker-chat` | created on the prior stale image |

Redis returned `PONG`; `codexify:queue:chat` was absent (`TYPE=none`) and
depth `0`; the chat heartbeat did not yet exist. Durable pre-start counts were
`5137` chat threads, `113328` chat messages, and zero Watchdog attempts,
dispatches, and results. No queue was inspected, cleared, popped, or modified
manually.

Pre-start active Chroma was
`/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main/.chroma`: five files,
`42,588,516` bytes, with `chroma.sqlite3` SHA-256
`602eca12546c7bc177e801f065df87afa6713c3b1a61693450a455fc464a5e46`.
Both preservation generations remained read-only.

## One canonical backend start

`TESTER_BACKEND_START_ATTEMPTS=1`

The sole start command was:

```text
docker compose --env-file .env.tester -p codexify_tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml up -d backend
```

Compose naturally recreated the backend dependency set using the repaired
image while preserving named durable volumes. The normal migrator exited `0`,
resolved `/app/backend/alembic.ini` to the Guardian migration graph, and ran
its normal `seed_defaults.py` follow-through. The backend then started once on
the repaired image; it remained running, Docker healthy, and restart count
`0`. The backend log confirmed `alembic_version=6e9f0a1b2c3`.

One non-model health request returned `HTTP 200` with `status=ok`,
`service=core`, `selected_provider=local`, valid
`v1-whooshd-deepseek-web` profile, and `release_hold=true`.

No database stamp, manual PostgreSQL update, migration-history rewrite, or
manual Redis/Chroma operation occurred. The normal startup seed/default path
is distinct from such manual mutation.

## Provider inventory and exact-model classification

All observations below were non-inference health/catalog/inventory requests.

- `/api/health/llm`: `HTTP 200`, selected provider `local`, configured model
  `gemma-4-12b-it-qat-4bit`, reachable local runtime, and
  `configured_model_available=false`.
- `/api/llm/catalog`: `HTTP 200`; local Whoosh'd provider was authorized and
  reachable but `enabled=false`, `selectable=false`, and `executable=false`
  with `configured_model_not_advertised_by_whooshd`.
- Whoosh'd `/v1/models`: `HTTP 200`; advertised exactly
  `mlx-community/Llama-3.2-3B-Instruct-4bit` and
  `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`.
- The exact Gemma string was absent from that inventory. No Qwen or Llama
  substitution was made.

Classification: `TESTER_CONFIGURED_MODEL_UNAVAILABLE`.

This is not `TESTER_PROVIDER_RUNTIME_UNAVAILABLE`: Whoosh'd inventory was
reachable and cataloged. It is an exact configured-model/inventory mismatch,
which ADR-074 requires Guardian to report fail closed.

## One normal chat-worker start and infrastructure proof

Before worker startup, backend health was `healthy` with restart count `0`,
Redis returned `PONG`, and the normal chat queue depth was still `0`.

`TESTER_CHAT_WORKER_START_ATTEMPTS=1`

The sole worker command was:

```text
docker compose --env-file .env.tester -p codexify_tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml up -d --no-deps worker-chat
```

`worker-chat` remained running on the repaired image with restart count `0`.
Its bounded log reached the normal idle queue loop
`codexify:queue:chat` at concurrency `2`; it did not dequeue a payload. Redis
reported a fresh heartbeat with `worker=chat`, `status=idle`, the normal queue
name, and TTL `40` seconds.

`/health/chat` returned `HTTP 200` with `status=unhealthy` and `ok=false`
solely because the configured Gemma is not advertised. Its infrastructure
fields were healthy: `redis=ok`, worker `status=fresh` (age `4.46` seconds),
queue depth `0` / `progressing`, and `completion_service.ok=true`. The
post-worker `/api/health/llm` likewise recorded fresh worker heartbeat,
reachable Redis, and `provider_truth.attempted=false`, `executed=false`, and
`completed=false` for the local provider.

## Closeout boundaries

Post-proof queue depth remained `0`. PostgreSQL remained at revision
`6e9f0a1b2c3`; chat-thread and chat-message counts remained exactly `5137` and
`113328`; Watchdog attempts, dispatches, and results remained zero. No thread,
chat message, chat task, completion task, or assistant output was created by
this proof.

The normal backend startup naturally seeded one global system document into
the current derived Chroma state. The post-start path still had five files, but
grew by `24,576` bytes to `42,613,092`; `chroma.sqlite3` became
`8432982a1a9f39f375a07abb07cde88f847e3e967f714089a31b0843efff1cec`.
This was the observed natural startup delta, not a manual Chroma reset,
restore, or replacement. Both preservation generations remained read-only.

`MODEL_INVOCATIONS_DURING_RESTORE=0` and
`DEEPSEEK_REQUESTS_DURING_RESTORE=0`. The provider/catalog truth surfaces
recorded no attempted, executed, or completed local or DeepSeek provider call.
No Watchdog worker or lineage ran; GitHub I/O, Command Bus, and Build Loop
activity were all `0`.

## ADR impact and validation

**No ADR change — existing Tester runtime/provider/migration authority proven
only.**

- Required ancestry, clean-worktree, and `.env.tester` ignore checks passed.
- Source/runtime/live-db migration identity checks passed at `6e9f0a1b2c3`.
- Canonical Tester Compose render, Redis/queue gates, one backend start, one
  worker start, bounded container/log checks, and all non-inference health,
  catalog, and inventory requests completed.
- `docs/architecture/00-current-state.md` remains untouched; this receipt does
  not widen release or support posture.

## Deferred next slice

Reconcile the Tester's configured local-model authority with currently
available Whoosh'd inventory or restore the selected Gemma runtime. Keep
Watchdog authority untouched until the exact Tester model authority is
resolved.
