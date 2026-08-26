# Guardian Qwen non-inference health/catalog qualification proof

**Result:** `BLOCKED: GUARDIAN_CHAT_INFRA_UNHEALTHY`
**ADR impact:** Aligned with ADR-074 and existing operator-truth doctrine; no ADR change.

## Scope and proof window

This is a bounded, non-inference qualification attempt. The proof window was
`2026-08-26T14:26:37Z` through `2026-08-26T14:27:55Z`.

No Guardian, Whoosh'd, launchd, backend, worker, Redis, Postgres, Chroma,
model-artifact, DeepSeek, or Watchdog configuration was changed. No service
restart was attempted. The task worktree had no unstaged
`guardian/workers/watchdog_review_worker.py` modification at entry; this task
did not edit, stage, restore, or reformat that file.

## Prerequisite and current source identities

- Required prerequisite:
  `6d3cd915eadbb17df8402d43b0cdfbc6174bbd89`
  (`Prove Whooshd bootstrap after teardown`).
- `git cat-file -e` and `git merge-base --is-ancestor` passed before probes.
- Task worktree branch/HEAD:
  `codex/diagnose-tester-fresh-chroma-failure` at
  `c6f2b95dc5cdee090ce581f91b3a8446ef8aaa12`.
- The active Tester project is `codexify_tester`, not this task worktree.
- The active backend is bind-mounted from
  `/Volumes/Dev_SSD/Codexify-main`, at `main`
  `6b383badb1eb5c5301df0c92c88215e605bf9fff`.
- Active backend container/image: `codexify_tester-backend-1`,
  `475bb0079346`, `codexify-backend-runtime:latest`
  (`sha256:2d02eaf6cfca4b50a8abbde718a8bab847a146b86069b9b5d0bac1b8651980b8`).
- Active source mounts include `/Volumes/Dev_SSD/Codexify-main/backend` to
  `/app/backend` and `/Volumes/Dev_SSD/Codexify-main/guardian` to both
  `/app/guardian` and `/app/codexify`.

The active source identity is therefore sufficiently resolved. The block is
runtime availability, not uncertain source/image provenance.

## Fresh Whoosh'd baseline

The prerequisite runtime remained unchanged during this proof:

- `system/com.resonant.whooshd` was `running`, with one active instance and
  PID `50696`.
- PID `50696` was the listener on `127.0.0.1:8000`.
- Whoosh'd `HEAD` remained
  `09e83a8359e3673e7c18a2e0b4733afd334b3bac`.
- Canonical registry blob remained
  `dc70602d29c174560e012943f32b67b14b69d12a`.
- `GET /v1/models` returned exactly `qwen3.8-27b-4bit`, with `mlx_vlm` /
  `mlx` metadata; no raw filesystem-path Qwen identity was returned.
- The unchanged registry maps that ID to
  `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`.
- Current startup evidence still records `adapter=stub`.

```text
WHOOSHD_EXECUTION_ADAPTER=stub
QWEN_REAL_INFERENCE_STATUS=UNPROVEN
```

The identity/inventory facts above do not establish executable Qwen inference.

## Active Tester provider posture

The non-secret backend-container environment resolved:

| Setting | Active value |
| --- | --- |
| `LLM_PROVIDER` | `local` |
| `LOCAL_CHAT_MODEL` | `qwen3.8-27b-4bit` |
| `ALLOW_CLOUD_PROVIDERS` | `true` |
| `CODEXIFY_LOCAL_ONLY_MODE` | `false` |
| `CODEXIFY_EGRESS_ALLOWLIST` | `deepseek` |

Thus the active Tester configuration preserves the expected local/Qwen
authority and bounded DeepSeek lane. These configuration values were read
from the actual container identity and were not changed.

## Canonical route and semantics inspection

The active mounted `guardian/routes/health.py` defines canonical routes:

- `GET /health`;
- `GET /health/llm` and `GET /api/health/llm`;
- `GET /api/llm/catalog` (with optional `include=all`); and
- `GET /health/chat` and `GET /api/health/chat`.

The active source also contains the strict local failure reason
`configured_model_not_advertised_by_whooshd`. This shows that the intended
healthy local posture depends on exact inventory agreement; it does not make
catalog presence a completion receipt. No running Guardian response was
available to assess any stronger `online`, `available`, `ready`, or `healthy`
semantics, so no capability-overclaim conclusion is made.

## First causal blocker

At proof-window start, the actual backend container was already stopped:

```text
backend_state=exited
exit_code=255
finished_at=2026-08-26T10:02:41.971699042Z
restart_count=0
```

The published backend port had no listener. The single canonical direct
Guardian probe was read-only and failed before HTTP transport:

```text
GET http://127.0.0.1:8889/health
curl: (7) Couldn't connect to server
HTTP_STATUS=000
```

Redis was separately still `running` and `healthy`; `worker-chat` was still
`running` with restart count `0`. They cannot make the absent backend health,
LLM-health, catalog, or chat-health routes available.

This is the first causal blocker:

`BLOCKED: GUARDIAN_CHAT_INFRA_UNHEALTHY`

The task permits a backend-only restart only when a healthy, reachable backend
has source-proven stale provider inventory. Here the backend is unavailable
before any inventory observation, so that conditional authority does not
apply. No restart was attempted.

## Deliberately unproven surfaces

Because the canonical Guardian health endpoint was unreachable, the task did
not probe `/api/health/llm`, `/api/llm/catalog`,
`/api/llm/catalog?include=all`, or `/health/chat`. Consequently, the
following remain unproven in this task:

- Guardian's dynamic recognition of exact Qwen inventory;
- local provider authorization/enabled runtime readback;
- absence of `configured_model_not_advertised_by_whooshd`;
- current Guardian health-status semantics;
- worker heartbeat and chat-queue depth readback; and
- any Guardian capability-overclaim question.

## Execution and persistence boundaries

```text
WHOOSHD_RESTARTS_DURING_QUALIFICATION=0
GUARDIAN_BACKEND_RESTARTS_DURING_QUALIFICATION=0
WORKER_CHAT_RESTARTS_DURING_QUALIFICATION=0
MODEL_INVOCATIONS_DURING_GUARDIAN_QUALIFICATION=0
DEEPSEEK_REQUESTS_DURING_GUARDIAN_QUALIFICATION=0
WATCHDOG_ACTIVITY_DURING_GUARDIAN_QUALIFICATION=0
```

The only Whoosh'd request made during the proof was `GET /v1/models`; bounded
access-log inspection showed inventory/health request classes only and no
model-generation route. No chat task, provider warmup, completion, DeepSeek
request, Watchdog work, GitHub I/O, Command Bus action, Build Loop action, or
manual storage mutation occurred.

`docs/architecture/00-current-state.md` and all prior proof receipts remained
unchanged.

## Validation record

```text
git cat-file -e 6d3cd915eadbb17df8402d43b0cdfbc6174bbd89^{commit}
git merge-base --is-ancestor 6d3cd915eadbb17df8402d43b0cdfbc6174bbd89 HEAD
git -C /Volumes/Dev_SSD/Codexify-main rev-parse HEAD
docker compose -p codexify_tester ps --all backend worker-chat redis
docker inspect 475bb0079346
launchctl print system/com.resonant.whooshd
lsof -nP -iTCP:8000 -sTCP:LISTEN
curl --fail http://127.0.0.1:8000/v1/models
curl http://127.0.0.1:8889/health
```

## Deferred next slice

Diagnose and restore the active `/Volumes/Dev_SSD/Codexify-main` Tester backend
startup under its actual mounted source/image configuration. That separate
task must not restart Whoosh'd, invoke Qwen, or use a backend restart merely
as an inventory-refresh experiment. Reattempt Guardian health/catalog
qualification only after direct backend `/health` is reachable.
