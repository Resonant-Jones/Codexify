# Tester chat worker readiness proof

## Result

CHAT_WORKER_READINESS_PASS

One canonical targeted Tester worker-chat start was performed against the already healthy backend and Redis runtime. The worker stayed running, wrote an idle heartbeat, and the permitted /health/chat request recognized it as fresh. No chat work was enqueued or dequeued, no chat lineage changed, and no model/provider invocation was performed.

This proves idle worker readiness only. It does not prove a chat completion, durable completion persistence, retrieval, provider quality, or release readiness.

## Source and runtime identity

- Source HEAD before runtime activity: 9b124086272d502e54071bbf493feef81b1f1ab4 (Observe canonical tester backend startup).
- Branch: codex/diagnose-tester-fresh-chroma-failure.
- Required ancestry passed for both 9b124086272d502e54071bbf493feef81b1f1ab4 and 0644077fd3b6916cd41da8b3276a594b580305f7.
- Compose project: codexify_tester.
- Compose inputs: repository project directory, .env.tester, docker-compose.yml, docker-compose.tester.yml, and docker-compose.whooshd-deepseek.yml.
- .env.tester remained ignored and unchanged.

| Property | Value |
| --- | --- |
| Backend service/container | backend / codexify_tester-backend-1 |
| Backend image | codexify-backend-runtime:latest / sha256:af108ff65ba1d1fde1417ac776be41eacd106aaf77d2800b7c6e40d2359b6288 |
| Worker service/container | worker-chat / codexify_tester-worker-chat-1 |
| Worker command | python -m guardian.workers.chat_worker |
| Normal chat queue | codexify:queue:chat |
| Queue representation | Redis list when populated; none while empty |
| Worker heartbeat key | codexify:worker:chat:heartbeat |

The rendered and running worker posture was LLM_PROVIDER=local, LOCAL_CHAT_MODEL=gemma-4-12b-it-qat-4bit, ALLOW_CLOUD_PROVIDERS=true, and CODEXIFY_LOCAL_ONLY_MODE=false. The canonical Compose render passed through config --quiet; it emitted only the existing optional-unset warnings for LOCAL_VISION_MODEL and LOCAL_GGUF_MODEL, and no secret was printed.

## Startup-path and safety baseline

guardian.workers.chat_worker.run_forever() initializes the database and shared services, writes a starting heartbeat, then loops: it writes an idle heartbeat and blocks on dequeue(QUEUE_NAME, block=True, timeout=5). The Redis wrapper implements that operation with BRPOP. Provider/completion execution is reachable only after a dequeued payload passes the ChatCompletionTask guard. There is no startup warmup, synthetic chat, provider probe, or task replay in this path.

Before starting the worker:

| Property | Observation |
| --- | --- |
| Backend | running, Docker healthy, restart count 0 |
| Backend started | 2026-08-24T19:39:14.796262045Z |
| One bounded /health | status=ok; profile v1-whooshd-deepseek-web, valid and release-held |
| Worker state | absent (no existing worker-chat container) |
| Queue type / depth | none / 0 |
| Existing chat heartbeat | absent (EXISTS=0) |
| Durable chat baseline | chat_threads=5136; chat_messages=113326 |
| Proof-window start | 2026-08-24T21:16:28Z |

No Redis payload was inspected, cleared, popped, moved, acknowledged, or otherwise modified.

## Single worker-start attempt

CANONICAL_CHAT_WORKER_START_ATTEMPTS=1

The healthy backend, Redis, and completed model-preparation dependency were left untouched. The normal Tester Compose path targeted only the absent worker:

    docker compose --project-directory /Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main \
      --env-file .env.tester -p codexify_tester \
      -f docker-compose.yml -f docker-compose.tester.yml \
      -f docker-compose.whooshd-deepseek.yml \
      up -d --no-deps worker-chat

It created and started the one canonical container. It was not retried, and no alternate direct Python command was used.

## Worker, heartbeat, and chat-health proof

| Property | Observation |
| --- | --- |
| Worker after start | running |
| Worker started | 2026-08-24T21:16:44.079997836Z |
| Worker restart count | 0 |
| Queue-loop log | [chat-worker] started queue=codexify:queue:chat present |
| Redis connection | succeeded: worker wrote a heartbeat with TTL 43 seconds |
| Heartbeat payload | worker=chat, status=idle, queue=codexify:queue:chat |
| Queue depth after start | 0 |
| Dequeue count | 0 |
| Bounded worker logs | no task/dequeue/provider/completion marker; raw restricted capture removed |

The idle heartbeat is emitted immediately before the bounded blocking dequeue. Together with the startup log and zero queue depth before and after, it proves ordinary idle queue-loop participation without work consumption.

One permitted non-completion request was made:

    GET http://127.0.0.1:8889/health/chat

It returned ok=true, status=healthy, redis=ok, worker fresh with heartbeat age 4.042 seconds, queue depth 0, queue status progressing, and note queue empty. It reported provider local, resolved/configured model gemma-4-12b-it-qat-4bit, and configured_model_available=true. This was availability-only; no catalog or other LLM health request was needed.

## No-work, no-inference, and preserved boundaries

| Evidence | Baseline / post-window result |
| --- | --- |
| Normal chat queue | 0 / 0 |
| Chat threads | 5136 / 5136 |
| Chat messages | 113326 / 113326 |
| Proof-created threads/messages/requests/tasks | 0 |
| Assistant messages | 0 |
| Worker task/dequeue log evidence | 0 |
| Whoosh'd completions | 0 |
| DeepSeek requests | 0 |
| Other provider invocations | 0 |
| Fallback or escalation | 0 |
| MODEL_INVOCATIONS_DURING_PROOF | 0 |

The unchanged durable counts, empty queue, task-gated source path, and bounded worker-log scan prove no model invocation without creating instrumentation or calling a model. The backend remained the same running/healthy container with restart count 0.

The canonical derived Chroma state remained at five files; chroma.sqlite3 retained SHA-256 602eca12546c7bc177e801f065df87afa6713c3b1a61693450a455fc464a5e46. worker-chat has no canonical .chroma host mount. Both external Chroma preservations remained read-only (dr-xr-xr-x).

No Watchdog Compose profile or worker was started. Since the proof-window start, Postgres recorded 0 new Watchdog review attempts, 0 new dispatches, and 0 newly completed results. No Watchdog configuration, attempt, dispatch, or inference action was performed.

No source, test, config, dependency, migration, Redis content, Postgres content, Chroma, provider configuration, Whoosh'd, DeepSeek, or Watchdog state was repaired or manually modified.

## ADR impact and validation

No ADR impact — existing worker/Redis semantics proven only. ADR-074 provider/model authority remains unchanged: the global worker provider is local, the operator-selected model is Gemma, cloud remains enabled, and the bounded DeepSeek lane remains configured but unused.

- Required ancestry and .env.tester ignore/posture checks passed.
- Canonical Compose render passed with only optional-unset model warnings.
- Backend Docker state and the one bounded /health check passed.
- Queue reads before and after worker start passed without mutation.
- The one worker-start attempt, worker state, Redis heartbeat, and /health/chat infrastructure checks passed with no restart loop.
- Documentation validation and Git diff checks are recorded at commit closeout.

## Deferred next slice

Prove one ordinary default-provider Tester chat completion through the healthy backend and worker-chat path using local gemma-4-12b-it-qat-4bit, with durable API and PostgreSQL readback, no cloud fallback, and no Watchdog activity.
