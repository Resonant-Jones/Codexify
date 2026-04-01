# Supported Path Proof: Current `main` HEAD After Retrieval-Boundary Changes

**Artifact window:** 2026-04-01T23:49:05Z to 2026-04-01T23:51:09Z  
**Branch:** `main`  
**HEAD commit:** `2226d833a9098a80808a179467f42b17009eaf46`  
**Runtime path:** current worktree Docker Compose stack, relaunched from this checkout  
**Active provider/model:** `local` / `qwen3.5:0.8b`  
**Vector backend:** `chroma` / `codexify_vault_supported`  
**Startup note:** the stack was relaunched with `/tmp/codexify-supported.env` via `CODEXIFY_RUNTIME_ENV_FILE=/tmp/codexify-supported.env`. Host port `127.0.0.1:8888` briefly refused immediately after restart, so the stable probes below were taken container-local against `codexify-backend-1` on the same live runtime.

---

## 1. Scope

This artifact validates the current supported local Docker Compose path on current `main` `HEAD`.

It specifically re-runs the supported path after the retrieval-boundary changes referenced in `docs/architecture/00-current-state.md`.

This proof covers:

- supported-profile flag activation
- quarantined cloud-provider route unavailability
- health-surface reconciliation
- chat completion acceptance versus persisted completion
- upload -> embed -> retrieve sentinel validation on the mounted retrieval-equivalent surface
- the retrieval-boundary distinction between the legacy standalone route and the current query-based retrieval seam

---

## 2. Environment

| Item | Value |
|---|---|
| Evidence capture time | `2026-04-01T23:49:05Z` through `2026-04-01T23:51:09Z` |
| Branch | `main` |
| HEAD commit | `2226d833a9098a80808a179467f42b17009eaf46` |
| Runtime path | current worktree Docker Compose stack |
| Compose project working dir | `/Users/resonant_jones/.codex/worktrees/461c/Codexify` |
| Compose env file | `/tmp/codexify-supported.env` |
| Active provider | `local` |
| Active model | `qwen3.5:0.8b` |
| Vector backend | `chroma` |
| Vector collection | `codexify_vault_supported` |
| Observed backend health | `backend`, `db`, `neo4j`, and `redis` healthy; `frontend`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`, `worker-voice`, and `worker-warmup` running; `graph-init`, `migrator`, and `model-prep` exited `0` |

Container-level runtime labels on the fresh stack confirm the relaunch used this worktree and the supported-profile env file:

```text
com.docker.compose.project.working_dir=/Users/resonant_jones/.codex/worktrees/461c/Codexify
com.docker.compose.project.environment_file=/tmp/codexify-supported.env
```

Supported-profile startup command:

```bash
CODEXIFY_RUNTIME_ENV_FILE=/tmp/codexify-supported.env \
docker compose --env-file /tmp/codexify-supported.env up -d --force-recreate \
  db redis backend worker-chat worker-document-embed worker-chat-embed \
  worker-warmup worker-voice frontend neo4j
```

The stack was first stopped with:

```bash
docker compose down --remove-orphans
```

---

## 3. Supported-profile flags

Verification command:

```bash
docker exec codexify-backend-1 sh -lc 'printf "CODEXIFY_RUNTIME_ENV_FILE=%s\nCODEXIFY_BETA_CORE_ONLY=%s\nCODEXIFY_LOCAL_ONLY_MODE=%s\nALLOW_CLOUD_PROVIDERS=%s\nLLM_PROVIDER=%s\nLOCAL_CHAT_MODEL=%s\nLOCAL_LLM_MODEL=%s\nDEFAULT_LOCAL_MODEL=%s\nLOCAL_BASE_URL=%s\nVAULTNODE_BASE_URL=%s\nCODEXIFY_VECTOR_STORE=%s\nCHROMA_PATH=%s\nCODEXIFY_COLLECTION=%s\n" "$CODEXIFY_RUNTIME_ENV_FILE" "$CODEXIFY_BETA_CORE_ONLY" "$CODEXIFY_LOCAL_ONLY_MODE" "$ALLOW_CLOUD_PROVIDERS" "$LLM_PROVIDER" "$LOCAL_CHAT_MODEL" "$LOCAL_LLM_MODEL" "$DEFAULT_LOCAL_MODEL" "$LOCAL_BASE_URL" "$VAULTNODE_BASE_URL" "$CODEXIFY_VECTOR_STORE" "$CHROMA_PATH" "$CODEXIFY_COLLECTION"'
```

Observed values:

```text
CODEXIFY_RUNTIME_ENV_FILE=/tmp/codexify-supported.env
CODEXIFY_BETA_CORE_ONLY=true
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
LLM_PROVIDER=local
LOCAL_CHAT_MODEL=qwen3.5:0.8b
LOCAL_LLM_MODEL=qwen3.5:0.8b
DEFAULT_LOCAL_MODEL=qwen3.5:0.8b
LOCAL_BASE_URL=http://100.109.4.57:11434
VAULTNODE_BASE_URL=http://100.109.4.57:11434
CODEXIFY_VECTOR_STORE=chroma
CHROMA_PATH=./chroma
CODEXIFY_COLLECTION=codexify_vault_supported
```

Verdict: **PASS**.

---

## 4. Quarantined route checks

Probe command:

```bash
docker exec codexify-backend-1 python -c "import json, requests; base='http://127.0.0.1:8888'; routes=[('openai','/api/providers/openai/status'),('anthropic','/api/providers/anthropic/status'),('groq','/api/providers/groq/status'),('gemini','/api/providers/gemini/status'),('alibaba','/api/providers/alibaba/status'),('minimax','/api/providers/minimax/status')]; print(json.dumps([{'provider': name, 'path': path, 'status': requests.get(base + path, timeout=10).status_code, 'body': requests.get(base + path, timeout=10).text} for name, path in routes], indent=2))"
```

Observed results:

| Provider | Status | Body |
|---|---:|---|
| openai | 404 | `{"detail":"Not Found"}` |
| anthropic | 404 | `{"detail":"Not Found"}` |
| groq | 404 | `{"detail":"Not Found"}` |
| gemini | 404 | `{"detail":"Not Found"}` |
| alibaba | 404 | `{"detail":"Not Found"}` |
| minimax | 404 | `{"detail":"Not Found"}` |

Catalog excerpt from `GET /api/llm/catalog?include=all`:

| Provider | enabled | available | disabled_reason |
|---|---:|---:|---|
| openai | false | false | Missing provider credentials |
| anthropic | false | false | Missing provider credentials |
| gemini | false | false | Missing provider credentials |
| groq | false | false | Cloud providers disabled by config |
| alibaba | false | false | Cloud providers disabled by config |
| minimax | false | false | Cloud providers disabled by config |
| local | true | true | null |

Verdict: **PASS**.

---

## 5. Health surface reconciliation

All of the following probes were taken against the same fresh runtime session after the relaunch.

| Endpoint | Observed result |
|---|---|
| `GET /health` | `{"status":"ok"}` |
| `GET /health/chat` | `{"ok":true,"status":"healthy","redis":"ok","worker":{"status":"fresh","heartbeat_age_seconds":5.576},"queue":{"depth":0,"status":"progressing"},"provider":"local","model":"qwen3.5:0.8b","completion_service":{"ok":true,...}}` |
| `GET /api/health/llm` | `{"ok":true,"status":"online","provider":"local","model":"qwen3.5:0.8b","checked_endpoint":"/api/tags","cache":"miss",...}` |
| `GET /api/llm/catalog?include=all` | Local provider enabled and available; cloud providers present but disabled by policy/credentials as shown above |
| `GET /health/vector` | `{"ok":true,"status":"ok","backend":"chroma","source":"probe","added":1,"matches":1}` |
| `GET /api/health/embedder` | `{"status":"ok","embedder":{"backend":"local","model":"/models/bge-large-en-v1.5","ready":true,"present":true,"reason":"local embedder preflight passed"}}` |
| `GET /api/health/retrieval?q=current-head-supported-path-sentinel-71eb37f9c20a435c818190e65e5f18e2` | `{"status":"ready","ok":true,"proof_capable":true,"same_runtime_as_worker":true,"worker_write_runtime":{"backend":"chroma","chroma_path":"/app/.chroma","collection":"codexify_vault_supported"},"backend_search_runtime":{"backend":"chroma","chroma_path":"/app/.chroma","collection":"codexify_vault_supported"},"search":{"executed":true,"match_count":1,...}}` |

Reconciliation:

- `health/chat` and `api/health/llm` agree on the active local model: `qwen3.5:0.8b`.
- `health/chat` reports Redis reachable, worker heartbeat fresh, and queue depth `0`.
- `api/llm/catalog` exposes the broader provider inventory, but the active runtime remains policy-shaped to the local provider and quarantined cloud providers.
- `health/vector` and `api/health/retrieval` agree on Chroma as the backend and on the supported collection `codexify_vault_supported`.
- `api/health/retrieval` is the mounted retrieval-equivalent surface in this runtime and returns search matches when queried.

Verdict: **PASS**.

---

## 6. Chat completion proof

Proof script invocation:

```bash
docker exec -i codexify-backend-1 python -u - < /tmp/current_head_supported_path_proof.py
```

Accepted completion response:

```json
{
  "acceptance_status": "accepted",
  "depth_mode": "normal",
  "effective_depth_mode": "light",
  "requested_depth_mode": "deep",
  "source_mode": "project",
  "task_id": "9f5e5f04-e58f-4ca0-a6de-3412d457cda0",
  "thread_id": 1219,
  "turn_id": "6aeddcfc-1a33-4c95-8e82-88e3ee70b0b9",
  "messages_url": "/api/chat/1219/messages",
  "trace_url": "/api/chat/debug/rag-trace/1219/latest"
}
```

Message persistence evidence:

| Phase | Evidence |
|---|---|
| Thread create | `thread_id=1219`, title `current-head-supported-path-proof-39ba2045` |
| User message persist | `message_id=50182`, content `Reply with exactly one word: hello` |
| Accepted, not yet complete | Polls 1-23 showed `assistant_count=0` while `api/health/llm.status=online` stayed unchanged |
| Persisted completion | Poll 24 at `elapsed_seconds=120.5` showed `assistant_count=1`, `assistant_id=50183`, `assistant_content=hello` |

Worker-visible completion stayed honest:

- `accepted` did not mean `completed`.
- The assistant turn did not appear until after the long-running local inference finished.
- The backend stayed `online` during the wait.

Verdict: **PASS** for acceptance and persistence as separate states.

---

## 7. Retrieval-boundary safety note

This live run exercised the supported chat and document flows on current `HEAD`.

It did **not** prove the legacy standalone `POST /api/retrieve` route, because that route still returned `404 Not Found` in this runtime.

The retrieval proof that **did** pass is the mounted query-based retrieval seam:

```http
GET /api/health/retrieval?q=current-head-supported-path-sentinel-71eb37f9c20a435c818190e65e5f18e2
```

That seam returned one match containing the sentinel text.

Backend seam proofs and live supported-path proofs are different evidence classes:

- `api/health/retrieval` proves backend search runtime and trace truth.
- It does not, by itself, prove that every legacy HTTP route is mounted.

I did not infer route mounting from backend search success.

---

## 8. Runtime-contract behavior check

Observed behavior for the selected local model `qwen3.5:0.8b`:

- The completion accepted immediately, but assistant persistence took `120.5s`.
- During the full poll loop, `/api/health/llm` stayed `status: online`.
- The backend did not flip to offline while the model was slow.
- The runtime therefore stayed honest: reachable-but-slow remained `online`, not `offline`.

What was not reproduced cleanly:

- A fully unreachable local provider.
- A cold-start failure where the local provider is absent rather than slow.

The only transient issue observed during relaunch was host port refusal immediately after restart; container-local probes on the same backend runtime showed the service itself was healthy throughout.

Verdict: **PASS** for slow-but-reachable behavior; **NOT TESTED** for an actually unreachable provider.

---

## 9. Upload / embed / retrieve sentinel proof

Upload command and response:

```text
upload_response:
{
  "id": "3682ece8-087b-4a6b-9e7d-904a69dc72e5",
  "filename": "current-head-supported-path-sentinel-71eb37f9c20a435c818190e65e5f18e2.txt",
  "embedding_status": "pending",
  "parsed_text": "current-head-supported-path proof sentinel\ncurrent-head-supported-path-sentinel-71eb37f9c20a435c818190e65e5f18e2\n",
  "thread_id": 1219,
  "source_tag": "uploaded"
}
```

Embedding lifecycle:

| Poll | Status | Observed time |
|---|---|---|
| 1 | pending | 0s |
| 2 | ready | `embedding_started_at=2026-04-01T23:51:06.434556+00:00`, `embedding_completed_at=2026-04-01T23:51:09.637134+00:00` |

Final document state:

```text
document_id=3682ece8-087b-4a6b-9e7d-904a69dc72e5
embedding_status=ready
embedding_started_at=2026-04-01T23:51:06.434556+00:00
embedding_completed_at=2026-04-01T23:51:09.637134+00:00
```

Retrieval evidence:

- `POST /api/retrieve` still returned `404 Not Found` in this runtime.
- `GET /api/health/retrieval?q=current-head-supported-path-sentinel-71eb37f9c20a435c818190e65e5f18e2&k=3` returned `match_count=1`.
- The first returned match contained the sentinel text:

```text
current-head-supported-path proof sentinel
current-head-supported-path-sentinel-71eb37f9c20a435c818190e65e5f18e2
```

Concrete retrieval metadata:

```json
{
  "match_count": 1,
  "same_runtime_as_worker": true,
  "proof_capable": true,
  "worker_write_runtime": {
    "backend": "chroma",
    "chroma_path": "/app/.chroma",
    "collection": "codexify_vault_supported"
  },
  "backend_search_runtime": {
    "backend": "chroma",
    "chroma_path": "/app/.chroma",
    "collection": "codexify_vault_supported"
  }
}
```

Verdict:

- Upload: **PASS**
- Embed lifecycle to terminal ready state: **PASS**
- Standalone `POST /api/retrieve`: **FAIL / still unproven**
- Current mounted retrieval-equivalent query path: **PASS**

---

## 10. Verdict

### What is now proven at current `HEAD`

| Check | Result |
|---|---|
| Supported-profile flags active | **PASS** |
| Quarantined cloud-provider routes unavailable | **PASS** |
| Health surfaces reconcile on the same runtime | **PASS** |
| User message persisted | **PASS** |
| Completion acceptance distinguished from persisted completion | **PASS** |
| Slow local model stayed honest as `online`, not `offline` | **PASS** |
| Upload -> embed lifecycle reached terminal ready state | **PASS** |
| Retrieval-equivalent query path found the sentinel text | **PASS** |

### What remains unproven

| Check | Status |
|---|---|
| Standalone `POST /api/retrieve` | **NOT PROVEN** in this runtime; returned `404` |
| Unreachable-provider / true cold-start scenario | **NOT TESTED** |
| Frontend-visible banner behavior during the slow turn | **NOT OBSERVED** |

### Blocker status for stronger supported-profile claims

The backend/worker retrieval seam is proven through `GET /api/health/retrieval?q=...`, but the legacy standalone `POST /api/retrieve` route remains unmounted in this runtime.

So:

- If the stronger beta claim is scoped to the mounted retrieval-equivalent query path, this proof supports it.
- If the stronger beta claim specifically requires the legacy standalone retrieval endpoint, a blocker remains.

**Proof artifact only; no automated tests apply.**
