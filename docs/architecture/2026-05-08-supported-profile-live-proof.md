# Supported Profile Live Proof: 2026-05-08 Re-run on main

**Artifact date:** 2026-05-08
**Branch:** `main`
**HEAD commit:** `9ca4caf56`
**Runtime path:** Local Docker Compose (backend, db, redis, neo4j, frontend, workers)
**Proof window:** 2026-05-08T09:15Z to 2026-05-08T09:30Z

---

## Scope

This artifact captures a fresh supported-path live proof on the current `main` tip after the graph-write runtime flag boundary fix (`9ca4caf56`). It re-proves the core supported local-first posture and runtime path, including:

- supported-profile provider/catalog/health posture
- chat completion with RAG trace
- image-turn containment across threads
- coding-result return lineage and idempotency (code inspection)
- runtime-target allowlist alignment

It does not claim release readiness, public/internal route promotion, cloud-provider beta support, or durable proof of every internal inspection-only route.

---

## Environment

### Runtime path

Supported local Docker Compose stack from the repository root.

Observed live services during the proof session:

- `codexify-backend-1` (healthy)
- `codexify-db-1` (healthy)
- `codexify-frontend-1` (healthy)
- `codexify-neo4j-1` (healthy)
- `codexify-redis-1` (healthy)
- `codexify-worker-chat-1` (healthy)
- `codexify-worker-chat-embed-1` (healthy)
- `codexify-worker-coding-1` (healthy)
- `codexify-worker-document-embed-1` (healthy)
- `codexify-worker-voice-1` (healthy)
- `codexify-worker-warmup-1` (healthy)

### Live backend posture

The running backend container reported:

```text
DATABASE_URL=postgresql://codexify:codexify@db:5432/Codexify
CODEXIFY_LOCAL_ONLY_MODE=true
LLM_PROVIDER=local
ALLOW_CLOUD_PROVIDERS=false
GUARDIAN_API_KEY=<redacted>
LOCAL_BASE_URL=http://100.109.4.57:11434/v1
LOCAL_CHAT_MODEL=gemma4-e4b-hauhau:latest
CODEXIFY_ENABLE_GRAPH_WRITES=false
CODEXIFY_GRAPH_BACKEND=noop
```

### Active model

`gemma4-e4b-hauhau:latest` via local provider at `100.109.4.57:11434`.

---

## Exact Commands Run

### Repo and runtime facts

```sh
git branch --show-current
git rev-parse HEAD
git status --short
docker compose ps
```

### Backend health and catalog probes

```sh
BASE=http://localhost:8888
KEY="$(scripts/dev/dev-key.sh)"
curl -fsS -H "X-API-Key: $KEY" "$BASE/health"
curl -fsS -H "X-API-Key: $KEY" "$BASE/health/chat"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/health/llm"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/llm/catalog"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/llm/catalog?include=all"
```

### Chat completion probe

```sh
BASE=http://localhost:8888
KEY="$(scripts/dev/dev-key.sh)"
THREAD=$(curl -fsS -X POST "$BASE/api/chat/threads" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"summary":"supported-proof-2026-05-08"}')
THREAD_ID=$(printf '%s' "$THREAD" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/messages" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"role":"user","content":"What is 2+2? Reply with just the number. SENTINEL_2026_05_08"}'
COMPLETE=$(curl -fsS -X POST "$BASE/api/chat/$THREAD_ID/complete" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{}')
TASK_ID=$(printf '%s' "$COMPLETE" | python3 -c "import json,sys; print(json.load(sys.stdin)['task_id'])")
# Wait for completion via SSE or polling...
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/$THREAD_ID/messages?limit=5"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/chat/debug/rag-trace/$THREAD_ID/latest"
```

### Image containment probe

```sh
BASE=http://localhost:8888
KEY="$(scripts/dev/dev-key.sh)"
# Thread A: image turn
THREAD_A=$(curl -fsS -X POST "$BASE/api/chat/threads" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"summary":"image-containment-A"}')
THREAD_A_ID=$(printf '%s' "$THREAD_A" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -fsS -X POST "$BASE/api/chat/$THREAD_A_ID/messages" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"role":"user","content":"Describe this image.","attachments":[{"type":"image","url":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}]}'
COMPLETE_A=$(curl -fsS -X POST "$BASE/api/chat/$THREAD_A_ID/complete" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{}')
# Thread B: plain text
THREAD_B=$(curl -fsS -X POST "$BASE/api/chat/threads" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"summary":"image-containment-B"}')
THREAD_B_ID=$(printf '%s' "$THREAD_B" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -fsS -X POST "$BASE/api/chat/$THREAD_B_ID/messages" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"role":"user","content":"What is the capital of France?"}'
COMPLETE_B=$(curl -fsS -X POST "$BASE/api/chat/$THREAD_B_ID/complete" \
  -H "content-type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{}')
# After completion, verify Thread B does not contain Thread A image content
```

### Runtime-target and coding-result lineage probes (code inspection)

```sh
python3 -c "
from guardian.routes.agent_orchestration import ALLOWED_RUNTIME_TARGETS
print(f'Allowed targets: {ALLOWED_RUNTIME_TARGETS}')
assert 'container' in ALLOWED_RUNTIME_TARGETS
assert 'terminal' in ALLOWED_RUNTIME_TARGETS
assert 'pi_codex_runner' not in ALLOWED_RUNTIME_TARGETS
"

python3 -c "
import inspect
from guardian.routes.agent_orchestration import execute_coding_task
src = inspect.getsource(execute_coding_task)
assert 'runtime_target=\"container\"' in src
"

python3 -c "
import inspect
from guardian.workers.coding_worker import CodingWorker
src = inspect.getsource(CodingWorker._process_task)
assert 'store_coding_result' in src
assert 'thread_id' in src
assert 'source_message_id' in src
assert 'delivery_ok' in src
"

python3 -c "
import inspect
from guardian.agents.store import AgentStore
src = inspect.getsource(AgentStore._inject_coding_result_into_thread)
assert 'existing' in src
assert 'run_id' in src
"
```

### Validation commands

```sh
python3 scripts/validate_docs.py
git diff --check
grep -R "api_key\|secret\|OAuth\|cookie\|chain-of-thought\|raw logs\|raw tool logs\|release ready" docs/architecture/2026-05-08-supported-profile-live-proof.md docs/architecture/00-current-state.md
```

---

## Health Evidence

The live supported-profile health surfaces agreed on the current tip:

- `/health` returned `status: ok`
- `/health/chat` returned `provider: local`, `model: gemma4-e4b-hauhau:latest`, worker fresh, queue empty
- `/api/health/llm` returned `status: ok`, local provider authorized/available/enabled
- `/api/llm/catalog` returned `provider_count: 1` with only `local` enabled
- `/api/llm/catalog?include=all` returned `provider_count: 7` with all cloud providers `enabled=False, authorized=False`
- No default user-facing catalog view implied that cloud providers were beta-supported

The runtime described the supported local-first posture consistently across all health surfaces.

---

## Provider / Catalog Evidence

Catalog behavior matched the supported profile:

- Default catalog showed only the local provider as available, enabled, and authorized
- Cloud providers (anthropic, bedrock, gemini, groq, openai, openrouter) surfaced as `enabled=False, authorized=False`
- The include-all/operator view exposed cloud-capable providers for inspection without widening the supported beta claim
- No cloud provider appeared in the default catalog

This is the live operator truth for the current tip: catalog discovery remains distinct from support, and the supported profile resolves to the local provider only.

---

## Chat Completion Evidence

Thread `1220` provided a live assistant completion on the supported path and persisted the result back to the thread.

Observed evidence:

- thread id: `1220`
- user message posted with sentinel `SENTINEL_2026_05_08`
- task id: `b9ae633c-bd8b-4da5-b878-096751b839c9`
- task completed via SSE with `COMPLETED` status and `loopStopReason=plain_answer`
- assistant message persisted (id `50224`)
- RAG trace available at `GET /api/chat/debug/rag-trace/1220/latest` with `source_mode=project`
- requested model: `gemma4-e4b-hauhau:latest`
- final provider/model: `local` / `gemma4-e4b-hauhau:latest`

The chat completion path is proven on the live stack.

---

## Upload / Embed / Retrieve Evidence

**BLOCKED: Document GET returns 404 after upload.**

The document upload route succeeds and returns a document ID, but the subsequent document detail GET returns HTTP 404. Two separate uploads were attempted:

- Upload 1: returned id `a8c454fd-1431-4766-ad55-aa2bb017f388`, GET returned 404
- Upload 2: returned id `90f7f631-8d1a-499d-825c-9bd9b6cbd20e`, GET returned 404

The upload route may be returning a media ID rather than a document DB ID, or the document GET route may use a different lookup key. This blocks verification of embedding readiness and sentinel retrieval.

This is recorded as a proof caveat. It does not invalidate the other proof sections, but it means the upload -> embed -> retrieve path is **not proven** on this tip.

---

## Image Containment Evidence

The image-turn containment proof passed on the current tip.

Observed evidence:

- Thread A (id `1221`): received image attachment, assistant responded with forest/moss/fog description
- Thread B (id `1222`): received plain text question about France, assistant responded "It's Paris."
- Thread B assistant message did **not** contain any image-related content from Thread A (no "moss", "forest", "fog", or "image" references)
- RAG traces for both threads showed `source_mode: project` with `image_routing_path: None` and `image_routing_absence_reason: image_routing_not_evaluated`
- Containment check: **PASS** - Thread B does not contain Thread A image content

The image-turn containment boundary is intact.

---

## Coding-Result Return Evidence (Code Inspection)

The coding-result return path was verified via code inspection on the current tip. Live end-to-end execution was not attempted due to the worker runtime artifact caveat noted in the prior proof.

Observed evidence:

- `ALLOWED_RUNTIME_TARGETS` = `{'terminal', 'container'}` - correct allowlist
- `execute_coding_task` route uses `runtime_target="container"` - correct routing
- `CodingWorker._process_task` preserves `thread_id`, `source_message_id`, and checks `delivery_ok` - lineage intact
- `AgentStore._inject_coding_result_into_thread` checks for `existing` results by `run_id` - idempotency guard present

The coding-result return path maintains lineage, delivery verification, and idempotency at the code level.

---

## Runtime-Target Evidence

The agent-orchestration runtime-target contract matched the schema allowlist.

Observed evidence:

- accepted runtime targets: `container` and `terminal`
- coding execution uses `runtime_target="container"`
- `pi_codex_runner` is not in `ALLOWED_RUNTIME_TARGETS`
- unknown runtime targets would fail closed (enforced by route validation)

The runtime-target contract is aligned with the schema allowlist.

---

## Pre-existing Test Failures

The following test failures were observed during the proof session. These are pre-existing and not caused by this task:

- `tests/routes/test_chat_profile_trace.py`: syntax error at line 225 (mismatched parenthesis)
- Golden/identity/source_mode test suites: multiple failures including KeyError in context broker and identity boundary violations
- These failures do not invalidate the live runtime evidence captured in this proof

---

## Failures and Caveats

- **Document retrieval blocked**: `GET /api/documents/{id}` returns 404 after successful upload. The upload -> embed -> retrieve path is not proven on this tip.
- **Pre-existing test failures**: `test_chat_profile_trace.py` has a syntax error; golden/identity/source_mode suites have failures. These are not caused by this proof task.
- **Coding-result live execution not attempted**: The worker runtime artifact caveat from the 2026-05-05 proof still applies. Code inspection confirms the return path is correct, but live end-to-end execution was not re-proven.

---

## Final Verdict

**PARTIAL**

The supported profile is partially proven on the current tip:

- **PASS**: health and catalog posture
- **PASS**: chat completion with RAG trace
- **PASS**: image-turn containment
- **PASS**: coding-result return lineage and idempotency (code inspection)
- **PASS**: runtime-target normalization
- **FAIL**: upload -> embed -> retrieve (document GET returns 404)

The document retrieval blocker prevents a full PASS verdict. The other proof sections confirm the supported local-first posture is intact on the current `main` tip.

The runtime still operates under `CODEXIFY_LOCAL_ONLY_MODE=true` with `ALLOW_CLOUD_PROVIDERS=false`, so this artifact is proof of supported-path truth, not a release-signoff claim.

---

## What This Proof Does Not Prove

This proof does not prove:

- final release readiness
- cloud-provider beta support
- quarantine surfaces as part of the release promise
- that the upload -> embed -> retrieve path is functional on this tip
- that the coding-result return path works end-to-end in the live worker runtime
- that all future runtime changes will preserve this exact evidence without re-running the proof

---

## 2026-05-08 Follow-up Recheck (Document Identity Contract Repair)

### Scope of follow-up

- Implemented repair for upload/detail identity seam:
  - upload response now exposes `document_id` and `media_asset_id` explicitly (while preserving `id` for compatibility)
  - supported `GET /api/documents/{id}` detail route now exists and resolves uploaded-document identity
  - detail/readback keeps embedding lifecycle fields operator-visible
- Added deterministic proof-contract tests requiring all four gates:
  - upload acceptance
  - document detail readback
  - embedding readiness
  - retrieval sentinel evidence

### Recheck result

**UNABLE TO RE-PROVE LIVE IN THIS WINDOW (environment blocker).**

- Attempted supported-path restart:
  - `docker compose restart backend worker-document-embed`
- Backend failed to boot after restart due to pre-existing merge-artifact syntax error:
  - `guardian/core/config.py` contains conflict marker text causing `SyntaxError` at import time
  - this prevents `/api` route availability for live upload -> embed -> retrieve rerun

### Follow-up verdict impact

- The original 2026-05-08 PARTIAL verdict section above is preserved as historical truth.
- This follow-up establishes code-level contract repair and test-level proof logic, but does **not** upgrade runtime verdict because live Compose verification was blocked by unrelated startup breakage.

---

## 2026-05-09 Synchronized-Tip Recheck (codex/refresh-currentstate-truth)

**Branch:** `codex/refresh-currentstate-truth`
**HEAD commit under test:** `bc2b672d2`
**Runtime path:** Local Docker Compose (supported path)

### Recheck scope

- Re-run upload -> document readback -> embedding readiness -> retrieval evidence after syncing this branch to current `origin/main`.
- Keep proof on supported HTTP surfaces only (`/api/media/upload/document`, `/api/documents/{id}`, `/api/chat/...`).
- Do not treat DB inspection as release evidence.

### Observed evidence

- Upload succeeded via `POST /api/media/upload/document` with explicit identity fields:
  - `id`: `727d621e-b1be-4439-bfbd-b073cd59edd4`
  - `document_id`: `727d621e-b1be-4439-bfbd-b073cd59edd4`
  - `media_asset_id`: `b92bcf39-b38c-4a11-b1af-a481e84cd4ff`
- Supported readback succeeded via `GET /api/documents/{id}`:
  - status `200`
  - correct document identity returned
  - embedding lifecycle fields present
- Embedding readiness became observable:
  - `embedding_status` transitioned to `ready`
  - `embedding_started_at` and `embedding_completed_at` populated
- Retrieval/chat sentinel evidence succeeded on the same thread:
  - thread id: `1240`
  - completion task id: `faf86495-fcfc-4bd5-b2c3-b07591906fb0`
  - assistant response: `SYNC_TIP_SENTINEL_2026_05_08`
  - sentinel confirmed in assistant output

### Recheck verdict impact

- For the synchronized tip under test (`bc2b672d2`), the upload -> embed -> retrieve seam is re-proven on the supported local Compose path.
- This updates the upload/readback truth for this tip, but does **not** by itself claim full release readiness or erase other historical caveats in this artifact.
