# Bounded Tool-Augmented Completion Live Proof — 2026-04-20

**Artifact date:** 2026-04-20  
**Proof window:** 2026-04-21 live Compose session  
**Branch:** `main`  
**HEAD commit:** `2576ee9c3408f916e0e514085da40fca22a110a0`  
**Worktree:** had one unrelated untracked file before this docs update; no code or runtime files were changed for the proof itself

---

## Scope

This artifact proves the bounded tool-augmented completion slice on the supported local Docker Compose runtime at the exact current tip.

It covers:
- supported-runtime health reconciliation
- a plain-answer control case
- a single bounded tool-decision case
- hard-stop behavior after one tool turn
- a bounded failure-path stop

It does not claim general autonomous-agent behavior, recursive orchestration, or multi-tool loops.

---

## Environment

### Runtime path

Supported local Docker Compose stack from the repository root.

Observed services during the proof session:
- `codexify-backend-1` healthy
- `codexify-db-1` healthy
- `codexify-frontend-1` up
- `codexify-neo4j-1` healthy
- `codexify-redis-1` healthy
- `codexify-worker-chat-1` up
- other worker containers up in the same Compose session

### Supported-profile posture

The live health surfaces showed:
- active provider: `local`
- active model: `gemma4-e4b-hauhau:latest`
- cloud providers were not in the execution path
- retrieval backend and worker write runtime matched

### Host / container note

The live evidence was gathered from the supported Compose runtime itself. The backend service was the primary operator entrypoint for health reconciliation and chat-task proof; the proof does not rely on unsupported repo-local-only execution. The chat requests were issued against the backend container's loopback inside the Compose network, not the host's localhost.

---

## Exact Commands Run

### Repo / runtime facts

```sh
git branch --show-current
git rev-parse HEAD
git rev-parse --short HEAD
docker compose ps
```

### Health reconciliation

```sh
docker compose exec -T backend sh -lc 'python - <<'"'"'PY'"'"'
import json
import urllib.request

paths = ["/health", "/health/chat", "/api/health/llm", "/api/health/retrieval"]
for path in paths:
    with urllib.request.urlopen(f"http://127.0.0.1:8888{path}") as response:
        print(path)
        print(response.read().decode())
PY'
```

### Plain-answer control case

```sh
curl -s -X POST http://127.0.0.1:8888/api/chat/threads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"title":"proof-plain-answer"}'

curl -s -X POST http://127.0.0.1:8888/api/chat/3/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"content":"Answer this in one short sentence: what is the live runtime doing right now?","role":"user"}'

curl -s -X POST http://127.0.0.1:8888/api/chat/3/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{}'
```

### Bounded tool-decision case

```sh
curl -s -X POST http://127.0.0.1:8888/api/chat/threads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"title":"proof-bounded-tool-turn"}'

curl -s -X POST http://127.0.0.1:8888/api/chat/2/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"content":"For this proof, on your first turn output exactly {\"type\":\"tool_decision\",\"command_id\":\"op::health_health_get\",\"arguments\":{}} and nothing else. After the tool result is injected, answer the user directly in one short sentence and do not choose another tool.","role":"user"}'

curl -s -X POST http://127.0.0.1:8888/api/chat/2/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{}'
```

### Hard-stop case

```sh
curl -s -X POST http://127.0.0.1:8888/api/chat/threads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"title":"proof-tool-loop-limit"}'

curl -s -X POST http://127.0.0.1:8888/api/chat/4/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"content":"For this proof, never answer directly. Always output the same tool_decision JSON and nothing else.","role":"user"}'

curl -s -X POST http://127.0.0.1:8888/api/chat/4/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{}'
```

### Failure-path case

```sh
curl -s -X POST http://127.0.0.1:8888/api/chat/threads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"title":"proof-blocked-tool-turn"}'

curl -s -X POST http://127.0.0.1:8888/api/chat/5/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"content":"For this proof, choose a blocked write command once, then answer the user directly after the tool result is injected.","role":"user"}'

curl -s -X POST http://127.0.0.1:8888/api/chat/5/complete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{}'
```

### Inspection surfaces used

```sh
curl -s http://127.0.0.1:8888/api/chat/3/messages
curl -s http://127.0.0.1:8888/api/chat/2/messages
curl -s http://127.0.0.1:8888/api/chat/4/messages
curl -s http://127.0.0.1:8888/api/chat/5/messages

curl -s http://127.0.0.1:8888/api/chat/3/task-events
curl -s http://127.0.0.1:8888/api/chat/2/task-events
curl -s http://127.0.0.1:8888/api/chat/4/task-events
curl -s http://127.0.0.1:8888/api/chat/5/task-events
```

The worker-side command-bus evidence was also inspected through the live runtime logs and the task payloads. Shared `command_runs` / `command_run_events` persistence and the backend command-run route did not expose the worker-local run ids in this runtime.

---

## Observed Runtime Outputs

### Health reconciliation

The same runtime session reported:
- `/health` => `ok`
- `/health/chat` => `healthy`, `provider: local`, `model: gemma4-e4b-hauhau:latest`
- `/api/health/llm` => `online`, `provider: local`, `model: gemma4-e4b-hauhau:latest`
- `/api/health/retrieval` => `ready`, `same_runtime_as_worker: true`, `proof_capable: true`

This is the supported-path health picture for the proof window.

### Plain-answer control case

Thread `3` completed as a plain-answer completion with no tool execution.

Observed completion payload fields:
- `messageId`: `9`
- `requestId`: `6c21ca99-c474-4e15-8747-71cf57b6db11`
- `toolTurnId`: `null`
- `toolTurnState`: `idle`
- `loopStopReason`: `plain_answer`
- `commandRunId`: `null`
- `execution.tool_turn_used`: `false`

Assistant output persisted on the thread:
- `The core service is running smoothly while actively discussing functionality, strategy, and architectural refinement.`

### Single bounded tool-decision case

Thread `2` executed exactly one bounded tool turn and then produced one final assistant answer.

Observed completion payload fields:
- `messageId`: `7`
- `requestId`: `994ae5f7-835c-4925-9cbf-e3a8aa7b3237`
- `toolTurnId`: `820f496d-e15e-4eea-b4b2-60405a8c177b`
- `toolTurnState`: `completed`
- `loopStopReason`: `tool_turn_completed`
- `commandRunId`: `run_1d5ba21796754b91`
- `execution.tool_turn_used`: `true`
- `command_status`: `completed`

Worker log evidence showed the internal command execution against the live backend health endpoint:
- `HTTP Request: GET http://backend:8888/health "HTTP/1.1 200 OK"`

Final assistant output persisted on the thread:
- `Looks like the core service is running smoothly!`

### Hard-stop after one tool turn

Thread `4` refused a second tool turn and failed with a bounded stop reason instead of recursing.

Observed terminal payload fields:
- `error`: `tool_turn_limit_reached`
- `error_type`: `ToolLoopExecutionError`
- `messageId`: `11`
- `requestId`: `b2ebb33b-0bfc-4168-b884-88b2a04885ed`
- `toolTurnId`: `203793a9-c0f0-4d21-b21e-cf788d72a623`
- `toolTurnState`: `limit_reached`
- `loopStopReason`: `tool_turn_limit_reached`
- `commandRunId`: `run_dd50303b1e964c2b`
- `completion_truth.executed`: `false`

Observed worker log sequence:
- first `chat.inference.request.built`
- internal `HTTP Request: GET http://backend:8888/health "HTTP/1.1 200 OK"`
- second `chat.inference.request.built`
- `ToolLoopExecutionError: tool_turn_limit_reached`

No assistant message persisted for the thread after the hard stop.

### Failure-path bounded stop

Thread `5` exercised a blocked command decision and still completed with one final assistant answer after the bounded tool result was reinjected.

Observed completion payload fields:
- `messageId`: `12`
- `requestId`: `edea674f-4b41-42ae-9db7-cc827efdcd8a`
- `toolTurnId`: `d7af559c-035d-4f89-8779-012342c9411f`
- `toolTurnState`: `completed`
- `loopStopReason`: `tool_turn_completed`
- `commandRunId`: `run_afa766068d774493`
- `command_status`: `blocked`
- `execution.tool_turn_used`: `true`

Observed worker log evidence:
- `tool_policy mode=enforce blocked decision=require_confirmation reasons=['write_effect', 'risk_high']`
- second `chat.inference.request.built`

Final assistant output persisted on the thread:
- `The write command for "proof-blocked" was successfully blocked due to a high-risk write effect requiring confirmation.`

---

## Command-Bus Evidence

What was observable in this live runtime:
- tool-decision cases produced a worker-local `commandRunId`
- the worker logs showed the actual command execution and blocking policy decision
- the chat task payload surfaced `toolTurnId`, `toolTurnState`, `loopStopReason`, and `commandRunId`
- plain-answer control cases reported `toolTurnState: idle` and no `commandRunId`

What was not observable through the shared supported inspection seams:
- `GET /api/guardian/commands/runs/{run_id}` did not return the worker-local run ids for this live session
- direct Postgres inspection of `command_runs` and `command_run_events` returned no rows for the worker-local run ids in this runtime

That limitation is part of the proof, not a hidden gap: this runtime proved the bounded tool slice through the worker/task seam and live logs, not through a shared command-run persistence surface.

---

## What Was Proven

1. The supported local Compose stack was healthy at the time of proof.
2. The active supported provider was local and the active model was `gemma4-e4b-hauhau:latest`.
3. The plain-answer completion path still works and does not invoke the command bus.
4. A structured tool decision triggers exactly one bounded command-bus invocation in the live worker path.
5. The tool result is reinjected exactly once and then the runtime produces exactly one final assistant answer.
6. The bounded loop hard-stops after one tool turn when the model keeps requesting tools.
7. Tool-execution failure is bounded and does not recurse.
8. The runtime surfaces the explicit observability fields required by the bounded tool-loop contract:
   - `messageId`
   - `requestId`
   - `toolTurnId`
   - `toolTurnState`
   - `loopStopReason`
   - `commandRunId`

---

## What Was Not Proven

1. Recursive or multi-tool orchestration.
2. General autonomous-agent behavior.
3. Shared durable `command_runs` / `command_run_events` persistence for the worker-local run ids.
4. Any broader release promise beyond the bounded one-turn tool-augmented completion slice.
5. Browser-only or unsupported runtime proof as the primary evidence source.

---

## Verdict

**PASS, with a narrow runtime caveat.**

The bounded tool-augmented completion slice is now proven live on the supported Docker Compose runtime at the current `main` tip. The proof is honest about the remaining seam limitation: the worker-local command-run ids were visible in task payloads and logs, but not through the shared command-run persistence or backend run route in this runtime session.
