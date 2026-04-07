# Import Runtime Concurrent Catch-up Proof - 2026-04-07

## A. Scope

### What this proof covers

1. The import embedding worker was healthy enough to stay running while it drained a real backlog.
2. The backlog was actively changing during the proof window, not merely present.
3. Normal chat remained usable during the same live window.
4. Canonical chat data still persisted to Postgres first, with enrichment deferred to background work.
5. Graph projection stayed optional and non-blocking from the chat path.

### What this proof does not prove

1. It does not prove a fresh import upload or retry invocation was required in this run. A live backlog already existed and was already draining when the proof started.
2. It does not prove low latency or low resource pressure. The import worker was very CPU-heavy during the window.
3. It does not prove the `/backfill/status` snapshot fields are fresh. That surface still carried stale snapshot values from an older run, so live Redis / SQL counts were used as the authoritative progress signal.
4. It does not prove graph projection health. It only proves graph noise did not block the core runtime.

## B. Environment

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD | `60bf174a546276ed3346bc8750c3d10636e16b97` |
| Proof on current `main` | Yes |
| Docker memory limit | `11.67 GiB` reported by `docker stats --no-stream` |
| Neo4j | Enabled and running in Compose; `docker compose ps` showed `neo4j` as `Up 23 hours (healthy)` |
| Runtime path | Local Docker Compose stack in the current checkout |
| Pre-run state | `backend` healthy, `worker-chat` running, `worker-chat-embed` running, `worker-document-embed` running, `worker-voice` running, `worker-warmup` running, live import backlog already present |
| Known prior failure modes | Not seen in the sampled live worker logs for this run; the worker stayed up and processed messages continuously |

### Compose services

- `backend` - Up 19 hours (healthy)
- `db` - Up 23 hours (healthy)
- `frontend` - Up 23 hours
- `neo4j` - Up 23 hours (healthy)
- `redis` - Up 23 hours (healthy)
- `worker-chat` - Up 19 hours
- `worker-chat-embed` - Up 23 hours
- `worker-document-embed` - Up 23 hours
- `worker-voice` - Up 23 hours
- `worker-warmup` - Up 19 hours

### Pre-run live state

- Import queue depth: `2001` on `codexify:queue:chat-import-embed`
- Retryable ChatGPT-import rows in Postgres: `1873`
- The embed worker log stream was already showing `embedded message_id=...` lines before the chat proof started

## C. Exact Commands Run

### Runtime and service inspection

```bash
git branch --show-current
git rev-parse HEAD
docker compose ps
docker stats --no-stream
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:chat-import-embed
docker exec codexify-db-1 psql -U codexify -d Codexify -tAc "SELECT COUNT(*) FROM chat_messages m JOIN chat_threads t ON t.id = m.thread_id WHERE COALESCE(t.metadata->>'import_source','') = 'chatgpt' AND (COALESCE(m.extra_meta->>'embedding_status','') = '' OR COALESCE(m.extra_meta->>'embedding_status','') IN ('pending','failed'));"
```

### Health and backfill probes

```bash
API_KEY=$(sed -n 's/^GUARDIAN_API_KEY=//p' .env | head -n1)
docker exec -i -e GUARDIAN_API_KEY="$API_KEY" codexify-backend-1 python3 - <<'PY'
import os
import urllib.request

base = 'http://127.0.0.1:8888'
key = os.environ['GUARDIAN_API_KEY']
paths = ['/health', '/health/chat', '/api/health/llm', '/api/health/retrieval', '/backfill/status']
for path in paths:
    req = urllib.request.Request(base + path, headers={'X-API-Key': key})
    with urllib.request.urlopen(req, timeout=20) as resp:
        print(f'== {path} {resp.status} ==')
        print(resp.read().decode())
PY
```

### Chat verification

```bash
API_KEY=$(sed -n 's/^GUARDIAN_API_KEY=//p' .env | head -n1)
docker exec -i -e GUARDIAN_API_KEY="$API_KEY" codexify-backend-1 python3 - <<'PY'
import json
import os
import time
import urllib.request

base = 'http://127.0.0.1:8888'
key = os.environ['GUARDIAN_API_KEY']
headers = {
    'X-API-Key': key,
    'Content-Type': 'application/json',
}

def request(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode('utf-8')
        return resp.status, body

status, body = request('POST', '/api/chat/threads', {'title': 'import-catchup-usability-proof-20260407'})
thread = json.loads(body)
thread_id = thread.get('id') or thread.get('thread', {}).get('id')
print(f'[thread.create] status={status} thread_id={thread_id}')
print(body)

status, body = request('POST', f'/api/chat/{thread_id}/messages', {
    'role': 'user',
    'content': 'Reply with exactly one word: hello',
})
message = json.loads(body)
message_id = message.get('message', {}).get('id') if isinstance(message, dict) else None
print(f'[message.create] status={status} message_id={message_id}')
print(body)

status, body = request('POST', f'/api/chat/{thread_id}/complete', {
    'provider': 'local',
    'model': 'qwen3.5:9b',
})
complete = json.loads(body)
print(f'[chat.complete] status={status} acceptance_status={complete.get("acceptance_status")} task_id={complete.get("task_id")} turn_id={complete.get("turn_id")}')
print(body)

for attempt in range(1, 31):
    status, body = request('GET', f'/api/chat/{thread_id}/messages?limit=20')
    payload = json.loads(body)
    messages = payload.get('messages') if isinstance(payload, dict) else payload
    assistant = [m for m in (messages or []) if m.get('role') == 'assistant']
    print(f'[poll {attempt}] status={status} assistant_count={len(assistant)} total={payload.get("total") if isinstance(payload, dict) else len(messages or [])}')
    if assistant:
        print(json.dumps(assistant[-1], sort_keys=True))
        break
    time.sleep(5)
PY
```

### Runtime observation commands

```bash
docker logs --tail=80 codexify-worker-chat-embed-1
docker logs codexify-worker-chat-1 | grep -E "27e44aee|7d6a772f|1215|assistant_message_persisted"
docker logs codexify-backend-1 | grep -E "27e44aee|7d6a772f|1215|POST /api/chat"
python3 - <<'PY'
import subprocess
import time
from datetime import datetime, timezone

sql = "SELECT COUNT(*) FROM chat_messages m JOIN chat_threads t ON t.id = m.thread_id WHERE COALESCE(t.metadata->>'import_source','') = 'chatgpt' AND (COALESCE(m.extra_meta->>'embedding_status','') = '' OR COALESCE(m.extra_meta->>'embedding_status','') IN ('pending','failed'));"
for i in range(4):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    queue = subprocess.check_output([
        'docker', 'exec', 'codexify-redis-1', 'redis-cli', 'LLEN', 'codexify:queue:chat-import-embed'
    ], text=True).strip()
    pending = subprocess.check_output([
        'docker', 'exec', 'codexify-db-1', 'psql', '-U', 'codexify', '-d', 'Codexify', '-tAc', sql
    ], text=True).strip()
    print(f'[{ts}] queue={queue} pending={pending}')
    if i < 3:
        time.sleep(10)
PY
docker logs codexify-worker-chat-embed-1 | sed -n '/2026-04-07 18:20:47/,/2026-04-07 18:20:56/p' | head -n 20
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:chat-import-embed
docker exec codexify-db-1 psql -U codexify -d Codexify -tAc "SELECT COUNT(*) FROM chat_messages m JOIN chat_threads t ON t.id = m.thread_id WHERE COALESCE(t.metadata->>'import_source','') = 'chatgpt' AND (COALESCE(m.extra_meta->>'embedding_status','') = '' OR COALESCE(m.extra_meta->>'embedding_status','') IN ('pending','failed'));"
```

## D. Observed Runtime Evidence

### 1. Baseline backlog and live state

Baseline counts taken before the chat proof started:

- `chat-import-embed` queue depth: `2001`
- Retryable ChatGPT-import rows in Postgres: `1873`

The live `/backfill/status` response was mixed:

- Snapshot fields still showed the older stale state: `items_pending=7580`, `items_remaining=7580`, `last_exit_reason=error`, `last_run_at=2026-01-07T07:56:54.268464+00:00`
- Live count fields showed the current Chroma-derived view: `messages_remaining=0`
- Graph substatus reported `counts_source="neo4j_error"`

That made the snapshot useful as historical context, but not as the primary progress counter for this proof.

Health surface baseline from the same live backend container:

```json
{"status":"ok","service":"core","timestamp":"2026-04-07T18:20:00.773011+00:00","details":{}}
```

```json
{"ok":true,"status":"healthy","redis":"ok","worker":{"status":"fresh","reason":"ok","heartbeat_age_seconds":0.798},"queue":{"depth":0,"status":"progressing"},"backend":"postgres","provider":"local","model":"qwen3.5:9b"}
```

```json
{"status":"ok","service":"llm","timestamp":"2026-04-07T18:20:02.399844+00:00","details":{"provider":"local","model":"qwen3.5:9b","ok":true,"status":"online"}}
```

```json
{"status":"ready","ok":true,"reason":"backend search runtime matches canonical worker write runtime","worker_write_runtime":{"backend":"chroma","chroma_path":"/app/.chroma","collection":"codexify_vault_supported"},"backend_search_runtime":{"backend":"chroma","chroma_path":"/app/.chroma","collection":"codexify_vault_supported"},"backend_store_source":"shared","same_runtime_as_worker":true,"proof_capable":true}
```

### 2. Active catch-up progress

The import backlog changed measurably while the proof ran:

| Sample | `chat-import-embed` queue depth | Retryable ChatGPT-import rows |
|---|---:|---:|
| Pre-chat sample | `2001` | `1873` |
| Mid-window sample | `1776` | `1648` |
| Post-drain sample | `0` | `0` |

The post-drain sampler ran at `2026-04-07T18:25:59Z`, `2026-04-07T18:26:10Z`, `2026-04-07T18:26:21Z`, and `2026-04-07T18:26:31Z`, and all four samples returned `queue=0 pending=0`.

Representative import-worker log lines from the active drain window:

```text
2026-04-06 19:36:05,636 - __main__ - INFO - [chat-embed] worker started queue=codexify:queue:chat-embed import_queue=codexify:queue:chat-import-embed
2026-04-07 18:20:47,856 - __main__ - INFO - [chat-embed] embedded message_id=50041 thread_id=1209
2026-04-07 18:20:54,376 - __main__ - INFO - [chat-embed] embedded message_id=50060 thread_id=1210
2026-04-07 18:21:05,842 - __main__ - INFO - [chat-embed] embedded message_id=50080 thread_id=1212
2026-04-07 18:21:52,990 - __main__ - INFO - [chat-embed] embedded message_id=50153 thread_id=1213
```

These lines show the worker was not crash-looping. It was actively embedding real backlog items.

### 3. Health during active processing

The live backend stayed reachable while the backlog was draining:

- `GET /health` returned `200`
- `GET /health/chat` returned `200` with `status=healthy`, `worker.status=fresh`, `heartbeat_age_seconds=0.798`, `queue.depth=0`, `backend=postgres`, `provider=local`, `model=qwen3.5:9b`
- `GET /api/health/llm` returned `200` with `status=ok`, `status=online`, `provider=local`, `model=qwen3.5:9b`
- `GET /api/health/retrieval` returned `200` with `status=ready`, `same_runtime_as_worker=true`, `proof_capable=true`

The `queue.depth=0` value in `GET /health/chat` refers to the chat-completion queue, not the import queue. That queue stayed healthy while the import queue was being drained.

### 4. Chat acceptance and persistence during the same window

Thread and message creation succeeded during the active import drain:

```json
{"ok":true,"id":1215,"thread":{"id":1215,"user_id":"default","title":"import-catchup-usability-proof-20260407","project_id":1,"created_at":"2026-04-07T18:25:22.116345+00:00"}}
```

```json
{"ok":true,"message":{"id":50167,"thread_id":1215,"role":"user","content":"Reply with exactly one word: hello"}}
```

The completion request was accepted immediately:

```json
{"ok":true,"acceptance_status":"accepted","acceptance_warnings":[],"task_id":"27e44aee-57f5-4252-a5e5-38f28571f3a5","turn_id":"7d6a772f-61d9-432d-9037-18975bbaaa02","thread_id":1215,"messages_url":"/api/chat/1215/messages","trace_url":"/api/chat/debug/rag-trace/1215/latest"}
```

The assistant turn persisted successfully later in the same live session:

```json
{"ok":true,"total":2,"messages":[{"id":50167,"thread_id":1215,"role":"user","content":"Reply with exactly one word: hello"},{"id":50168,"thread_id":1215,"role":"assistant","content":"hello","created_at":"2026-04-07T18:28:42.645256+00:00"}]}
```

Worker-chat log excerpt for the same turn:

```text
2026-04-07 18:25:22,691 - __main__ - INFO - [task] running type=chat_completion id=27e44aee-57f5-4252-a5e5-38f28571f3a5 run_id=591e8a9eec3f4baeb41d613dd9663afc origin=api:chat.complete|turn_id=7d6a772f-61d9-432d-9037-18975bbaaa02|source_mode=project thread=1215 turn_id=7d6a772f-61d9-432d-9037-18975bbaaa02
2026-04-07 18:25:23,559 - guardian.context.broker - INFO - [ContextBroker] thread=1215 depth=normal messages=1 semantic=0 obsidian=0 docs(project/thread)=0/0 memory=0(skipped) graph=1(contributed)
2026-04-07 18:28:43,105 - __main__ - INFO - [chat-worker] assistant_message_persisted thread_id=1215 turn_id=7d6a772f-61d9-432d-9037-18975bbaaa02 task_id=27e44aee-57f5-4252-a5e5-38f28571f3a5 assistant_message_id=50168
2026-04-07 18:28:43,112 - __main__ - INFO - [task] completed type=chat_completion id=27e44aee-57f5-4252-a5e5-38f28571f3a5 run_id=591e8a9eec3f4baeb41d613dd9663afc thread=1215 turn_id=7d6a772f-61d9-432d-9037-18975bbaaa02 message_id=50168
```

Backend log excerpt for the same turn:

```text
2026-04-07 18:25:22,567 - guardian.routes.chat - INFO - [chat.complete] downgraded depth_mode=deep thread_id=1215 project_id=1 reason=project_identity_depth_light
2026-04-07 18:25:22,585 - guardian.routes.chat - INFO - [task] created type=chat_completion id=27e44aee-57f5-4252-a5e5-38f28571f3a5 origin=api:chat.complete|turn_id=7d6a772f-61d9-432d-9037-18975bbaaa02|source_mode=project thread=1215 acceptance_status=accepted acceptance_warnings=[] task_created_visibility_scope=progress
INFO:     127.0.0.1:35288 - "POST /api/chat/threads HTTP/1.1" 200 OK
INFO:     127.0.0.1:35294 - "POST /api/chat/1215/messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35308 - "POST /api/chat/1215/complete HTTP/1.1" 200 OK
INFO:     127.0.0.1:35316 - "GET /api/chat/1215/messages?limit=20 HTTP/1.1" 200 OK
INFO:     127.0.0.1:35332 - "GET /api/chat/1215/messages?limit=20 HTTP/1.1" 200 OK
```

The chat turn stayed in the normal request lane. It did not require pausing or disabling the import worker.

### 5. Runtime pressure

`docker stats --no-stream` during the proof window showed noticeable but survivable pressure:

| Container | CPU | Memory |
|---|---:|---:|
| `worker-chat-embed` | `504.99%` | `2.034 GiB / 11.67 GiB` |
| `backend` | `0.66%` | `858.5 MiB / 11.67 GiB` |
| `worker-chat` | `0.03%` | `540.3 MiB / 11.67 GiB` |
| `neo4j` | `0.43%` | `610.3 MiB / 11.67 GiB` |
| `db` | `3.21%` | `192.7 MiB / 11.67 GiB` |
| `redis` | `0.41%` | `21.59 MiB / 11.67 GiB` |

Interpretation:

- The import worker was the pressure point.
- The backend stayed responsive.
- Chat remained usable, but the window was not "idle". It was usable under noticeable resource pressure.

## E. Truthful Interpretation

The strongest truthful reading of the live evidence is:

1. The import embedding worker was healthy enough to remain running.
2. It was actively draining a real backlog, with queue depth and retryable row counts both falling to zero during the proof window.
3. The backend health surfaces stayed reachable while that drain was happening.
4. A normal chat turn was accepted and the assistant message persisted successfully during the same window.
5. The graph path was not on the critical request lane. Graph-related noise did not block chat or retrieval.

The main caveat is pressure, not failure:

- `worker-chat-embed` used over 500% CPU in the sampled `docker stats` snapshot.
- The assistant turn took roughly 3 minutes from acceptance to persistence.
- `/backfill/status` still contained stale snapshot fields from an older run, so the live Redis and SQL counts were the better proof signal.

On balance, the runtime stayed usable while healthy active catch-up was running.

## F. Final Verdict

VERDICT: healthy active import catch-up coexisted with normal runtime usability
