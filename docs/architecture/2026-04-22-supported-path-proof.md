# Supported Path Proof: Current `main` Live Compose Re-run

**Artifact date:** 2026-04-22T17:35:00Z
**Branch:** `main`
**HEAD commit:** `54d0eb3a3a3bb20f8377b92e87e6a342323724ee`
**Runtime path:** Local Docker Compose (backend, db, redis, neo4j, frontend, workers)
**Active provider/model:** local / `gemma4-e4b-hauhau:latest` via `http://100.109.4.57:11434`
**Proof window:** 2026-04-22T17:26:28Z to 2026-04-22T17:33:36Z

---

## Scope

This artifact re-runs the supported local Docker Compose beta proof on the exact current `main` tip.

It covers:
- supported-profile posture
- health surface reconciliation
- chat completion acceptance and persistence
- single-user ownership canonicalization on the chat path
- upload -> embed -> retrieve
- bounded tool-loop behavior

It does not claim graph writes, delegation, multi-user auth, autonomous orchestration, or non-Compose deployment support.

---

## Environment

### Runtime path

Supported local Docker Compose stack from the repository root.

Live probes were issued against the backend container loopback at `http://127.0.0.1:8888` because that is the runtime surface the Compose stack exposed in this session.

Observed services during the proof session:
- `codexify-backend-1` healthy
- `codexify-db-1` healthy
- `codexify-frontend-1` up
- `codexify-neo4j-1` healthy
- `codexify-redis-1` healthy
- `codexify-worker-chat-1` up
- `codexify-worker-chat-embed-1` up
- `codexify-worker-document-embed-1` up
- `codexify-worker-warmup-1` up
- `codexify-worker-voice-1` up

### Live backend posture

The running backend container reported:

```text
CODEXIFY_BETA_CORE_ONLY=false
CODEXIFY_LOCAL_ONLY_MODE=false
ALLOW_CLOUD_PROVIDERS=true
LLM_PROVIDER=local
LOCAL_CHAT_MODEL=gemma4-e4b-hauhau:latest
LOCAL_BASE_URL=http://100.109.4.57:11434
```

That is not the supported local-only beta posture.

---

## Exact Commands Run

### Repo and container state

```sh
git branch --show-current
git rev-parse HEAD
docker compose ps
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup frontend
```

### Backend seam evals

```sh
pytest -q tests/golden
pytest -q tests/identity/test_identity_boundary_contract.py
pytest -q tests/routes/test_chat_source_mode.py tests/routes/test_chat_profile_trace.py
```

### Live health and catalog probes

```sh
docker compose exec -T backend sh -lc 'env | grep -E "(CODEXIFY_BETA_CORE_ONLY|CODEXIFY_LOCAL_ONLY_MODE|ALLOW_CLOUD_PROVIDERS|LLM_PROVIDER|LOCAL_CHAT_MODEL|LOCAL_BASE_URL)"'

docker compose exec -T backend sh -lc 'python - <<'"'"'PY'"'"'
import urllib.request
for path in ["/health", "/health/chat", "/api/health/llm", "/api/health/retrieval", "/api/llm/catalog?include=all"]:
    with urllib.request.urlopen(f"http://127.0.0.1:8888{path}") as response:
        print(path)
        print(response.read().decode())
PY'
```

### Chat completion and ownership proof

```sh
docker compose exec -T backend sh -lc 'python - <<'"'"'PY'"'"'
import os, requests
base = "http://127.0.0.1:8888"
headers = {"X-API-Key": os.environ["GUARDIAN_API_KEY"]}
create = requests.post(base + "/api/chat/threads", headers=headers, json={"title": "proof-ownership", "user_id": "Resonant Jones"})
thread_id = create.json()["id"]
message = requests.post(base + f"/api/chat/{thread_id}/messages", headers=headers, json={"role": "user", "content": "Reply with exactly ping.", "user_id": "Resonant Jones"})
complete = requests.post(base + f"/api/chat/{thread_id}/complete", headers=headers, json={"depth_mode": "normal"})
print(create.status_code, create.text)
print(message.status_code, message.text)
print(complete.status_code, complete.text)
PY'
```

### Upload / embed / retrieve probe

```sh
docker compose exec -T backend sh -lc 'python - <<'"'PY'
import os, uuid, requests
base = "http://127.0.0.1:8888"
headers = {"X-API-Key": os.environ["GUARDIAN_API_KEY"]}
sentinel = f"codexify-supported-path-sentinel-{uuid.uuid4().hex}"
text = f"This is the supported-path proof sentinel: {sentinel}."
files = {"file": (f"{sentinel}.txt", text.encode("utf-8"), "text/plain")}
data = {"user_id": "Resonant Jones", "thread_id": "770", "tag": "proof"}
resp = requests.post(base + "/api/media/upload/document", headers=headers, files=files, data=data, timeout=120)
print(resp.status_code)
print(resp.text)
PY'
```

### Bounded tool-loop probe

```sh
docker compose exec -T backend sh -lc 'python - <<'"'"'PY'
import os, requests
base = "http://127.0.0.1:8888"
headers = {"X-API-Key": os.environ["GUARDIAN_API_KEY"]}
create = requests.post(base + "/api/chat/threads", headers=headers, json={"title": "proof-tool-loop", "user_id": "Resonant Jones"})
thread_id = create.json()["id"]
message = requests.post(base + f"/api/chat/{thread_id}/messages", headers=headers, json={"role": "user", "content": "For this proof, on your first turn output exactly {\"type\":\"tool_decision\",\"command_id\":\"op::health_health_get\",\"arguments\":{}} and nothing else. After the tool result is injected, answer the user directly in one short sentence and do not choose another tool.", "user_id": "Resonant Jones"})
complete = requests.post(base + f"/api/chat/{thread_id}/complete", headers=headers, json={"depth_mode": "normal"})
print(create.status_code, create.text)
print(message.status_code, message.text)
print(complete.status_code, complete.text)
PY'
```

---

## Live Proof Verdict Matrix

| Check | Result | Evidence |
|---|---|---|
| Supported-profile posture active | FAIL | Backend container env reported `CODEXIFY_BETA_CORE_ONLY=false`, `CODEXIFY_LOCAL_ONLY_MODE=false`, `ALLOW_CLOUD_PROVIDERS=true` |
| Cloud provider route quarantine | PASS | `GET /api/providers/openai/status`, `/anthropic/status`, `/groq/status`, `/alibaba/status`, `/minimax/status` returned `404` |
| Catalog aligns with local-only posture | FAIL | `/api/llm/catalog?include=all` still shows `groq` enabled and available |
| `/health` green | PASS | `{"status":"ok","service":"core"}` |
| `/health/chat` green | PASS | `status=healthy`, Redis reachable, worker heartbeat fresh, provider local |
| `/api/health/llm` green | PASS | `status=online`, provider local, model `gemma4-e4b-hauhau:latest` |
| `/api/health/retrieval` green | PASS | `status=ready`, `proof_capable=true`, same runtime as worker |
| Chat completion accepted | PASS | Thread `770`, task `9727a463-1538-44ff-8de7-c45e220e56ab`, `acceptance_status=accepted` |
| Assistant output persisted | PASS | Message `28031` persisted with content `ping` |
| Single-user ownership canonical `local` | PASS | Thread `770` and message `28030` both persisted with `user_id=local` even when request body used `user_id="Resonant Jones"` |
| Upload -> embed -> retrieve | FAIL | Direct document upload returned `500` with `{"error":"upload_failed"}`; backend logs show missing `agent_extension_*` tables |
| Bounded tool-loop one-turn | FAIL | Thread `772` accepted, but worker failed with `tool_command_execution_failed` and no assistant message persisted |
| Hard-stop after one tool turn | FAIL | Thread `773` returned a plain answer, with `toolTurnState=idle` and `loopStopReason=plain_answer` |
| Blocked-result behavior | FAIL | Thread `774` returned a plain answer, with `toolTurnState=idle` and `loopStopReason=plain_answer` |

---

## Backend Seam Evals

These are evidence supplements, not replacements for live Compose proof.

| Suite | Result | Notes |
|---|---|---|
| `pytest -q tests/golden` | FAIL | `test_golden_rag_trace_latest_and_isolation` crashed because `chatlog_db` was `None` inside `get_latest_rag_trace` |
| `pytest -q tests/identity/test_identity_boundary_contract.py` | FAIL | 4 failures; `ContextBroker` now requires `user_id` and the fixtures did not provide one |
| `pytest -q tests/routes/test_chat_source_mode.py tests/routes/test_chat_profile_trace.py` | PASS | Source-mode/profile trace regression suite passed |
| `docker compose run --rm migrator` | FAIL | Alembic `RevisionError`: requested revision `e4f5a6b7c8d9` overlaps with `a1b2c3d4e5f6` |

---

## Observed Outputs

### Health and catalog

- `/health` returned `{"status":"ok","service":"core",...}`
- `/health/chat` returned `status=healthy`, `redis=ok`, fresh worker heartbeat, and `provider=local`
- `/api/health/llm` returned `status=online`, `provider=local`, `model=gemma4-e4b-hauhau:latest`
- `/api/health/retrieval` returned `status=ready`, `proof_capable=true`
- `/api/llm/catalog?include=all` still exposed cloud inventory entries, including `groq` as enabled and available, which conflicts with the intended local-only posture

### Chat completion and ownership

- Thread creation with `{"user_id":"Resonant Jones"}` persisted as `user_id="local"`
- Message creation with the same label persisted the thread as `user_id="local"`
- Completion response returned `acceptance_status=accepted`
- The persisted assistant message content was `ping`
- The assistant metadata showed `completion_truth.accepted=true`, `execution.final_provider=local`, `execution.final_model=gemma4-e4b-hauhau:latest`

### Upload / embed / retrieve

- `POST /api/media/upload/document` returned `500`
- Response body: `{"detail":{"error":"upload_failed","message":"Upload failed. Please try again."},...}`
- Backend logs show `RuntimeError: Expected database tables missing: ['agent_extension_install_bindings', 'agent_extension_install_gate_decisions', 'agent_extension_registry_entries']. Apply latest Alembic migrations.`
- Because upload failed, embed and retrieval were not reached on the live path

### Bounded tool-loop

- Thread `772` accepted the completion request, but the worker failed with `tool_command_execution_failed`
- Worker log root cause:
  - `ImportError: cannot import name 'EvalTask' from 'guardian.tasks.types'`
- Thread `773` and `774` both produced assistant messages that were plain answers, not bounded tool decisions:
  - thread `773`: `loopStopReason=plain_answer`, `toolTurnState=idle`
  - thread `774`: `loopStopReason=plain_answer`, `toolTurnState=idle`

---

## What Was Proven

- The live backend can still accept and persist a normal chat completion on this `main` tip.
- Single-user ownership on the chat path still canonicalizes to `local`; browser/display labels did not leak into persisted `user_id` for the chat thread or message.
- The backend health surfaces are alive and internally consistent for the local model path.
- Cloud provider routes are quarantined at the route layer.

---

## What Was Not Proven

- Supported-profile local-only posture was not proven because the live backend container was not running with the supported flag set.
- `upload -> embed -> retrieve` was not proven because document upload failed before embed/retrieve could start.
- Bounded tool-loop support was not proven because the one-turn case failed and the supposed hard-stop / blocked-result cases degraded into plain answers.
- Backend seam evals do not substitute for the live Compose proof; they only narrow uncertainty at the code-seam level.

---

## Limitations

- The live runtime was not in the supported local-only posture during this run.
- `docker compose run --rm migrator` failed before a clean refresh could complete, and the live document path then surfaced missing `agent_extension_*` tables.
- The current backend image lacks `git`, so the host workspace commit was used as the source of `HEAD` truth.
- The proof used the backend container loopback rather than host `localhost`, because that is the route the running Compose stack reliably exposed in this session.

---

## Final Verdict

This is a **failed supported-path proof** for the current `main` tip.

What passed:
- chat acceptance and persistence
- single-user ownership canonicalization on the chat path
- health surfaces
- cloud route quarantine

What failed:
- supported local-only posture
- catalog alignment with the beta contract
- upload -> embed -> retrieve
- bounded tool-loop behavior
- clean migrator refresh

The release should remain blocked until the runtime posture and schema/tool-loop regressions are resolved on the exact current `main` tip.
