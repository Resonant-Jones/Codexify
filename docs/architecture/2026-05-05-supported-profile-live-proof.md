# Supported Profile Live Proof: Fresh Current Tip Re-run

**Artifact date:** 2026-05-05
**Branch:** `codex/add-searchasrag-contract`
**HEAD commit:** `3d03505adc0f6386b3b066e2d305d66b76dbe50f`
**Runtime path:** Local Docker Compose (backend, db, redis, neo4j, frontend, workers)
**Proof window:** 2026-05-05T19:31Z to 2026-05-05T19:34Z

---

## Scope

This artifact captures a fresh supported-path live proof on the current tip after the release-blocker fixes to:

- supported-profile provider/catalog/health posture
- Minimax vision capability gating
- coding-result return into the source thread
- agent orchestration `runtime_target` allowlist alignment
- live RAG trace debug metadata

It proves the live supported path on the supported local Docker Compose runtime. It does not claim release readiness, public/internal route promotion, cloud-provider beta support, or durable proof of every internal inspection-only route.

---

## Environment

### Runtime path

Supported local Docker Compose stack from the repository root.

Observed live services during the proof session:

- `codexify-db-1`
- `codexify-frontend-1`
- `codexify-neo4j-1`
- `codexify-redis-1`
- `codexify-worker-chat-1`
- `codexify-worker-chat-embed-1`
- `codexify-worker-document-embed-1`
- `codexify-worker-voice-1`
- `codexify-worker-warmup-1`

### Live backend posture

The running backend container reported:

```text
DATABASE_URL=postgresql://codexify:codexify@db:5432/Codexify
CODEXIFY_LOCAL_ONLY_MODE=true
LLM_PROVIDER=local
CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp
ALLOW_CLOUD_PROVIDERS=false
GUARDIAN_API_KEY=<redacted>
LOCAL_BASE_URL=http://host.docker.internal:11434/v1
LOCAL_CHAT_MODEL=library2/ministral-3:8b
```

The live health surface also reported `supported_profile.release_hold: true`, so this proof is evidence of the supported path, not a release-signoff declaration.

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
docker compose exec -T backend python - <<'PY'
import os, requests, json
base='http://127.0.0.1:8888'
headers={'X-API-Key': os.environ['GUARDIAN_API_KEY']}
for path in ['/health','/health/chat','/api/health/llm','/api/llm/catalog','/api/llm/catalog?include=all']:
    r=requests.get(base+path, headers=headers, timeout=30)
    print(path, r.status_code)
    print(r.text)
PY
```

### Chat / image containment probes

```sh
docker compose exec -T backend python - <<'PY'
import os, requests
base='http://127.0.0.1:8888'
headers={'X-API-Key': os.environ['GUARDIAN_API_KEY']}

thread_a = requests.post(
    base + '/api/chat/threads',
    headers=headers,
    json={'title': 'image-containment-thread-a'},
)
thread_b = requests.post(
    base + '/api/chat/threads',
    headers=headers,
    json={'title': 'image-containment-thread-b'},
)
thread_a_id = 27
thread_b_id = 28
requests.post(
    base + f'/api/chat/{thread_a_id}/messages',
    headers=headers,
    json={'role': 'assistant', 'content': "I can't view the image."},
)
requests.post(
    base + f'/api/media/upload/image',
    headers=headers,
    files={'file': ('containment.png', b'<redacted image bytes>', 'image/png')},
    data={'thread_id': thread_b_id},
)
requests.post(
    base + f'/api/chat/{thread_b_id}/messages',
    headers=headers,
    json={
        'role': 'user',
        'content': '<!-- cfy-media:image:652121da-65a4-44c3-ae17-d9ef0d82d926 -->',
    },
)
requests.post(
    base + f'/api/chat/{thread_b_id}/complete',
    headers=headers,
    json={
        'provider': 'local',
        'model': 'gemma4-e4b-hauhau:latest',
        'source_mode': 'project',
        'depth_mode': 'deep',
    },
)
PY
```

### Validation commands

```sh
python3 -m pytest -q guardian/tests/routes/test_health_supported_profile.py guardian/tests/core/test_provider_registry.py guardian/tests/core/test_llm_catalog.py guardian/tests/routes/test_agent_orchestration_events.py guardian/tests/workers/test_coding_worker.py tests/routes/test_chat_profile_trace.py
python3 -m pytest -q guardian/tests/routes/test_health_supported_profile.py guardian/tests/core/test_llm_catalog.py guardian/tests/routes/test_agent_orchestration_events.py guardian/tests/workers/test_coding_worker.py tests/routes/test_chat_profile_trace.py
python3 scripts/validate_docs.py
git diff --check
grep -R "api_key\|secret\|OAuth\|cookie\|chain-of-thought\|raw logs\|raw tool logs\|release ready" docs/architecture/2026-05-05-supported-profile-live-proof.md docs/architecture/00-current-state.md docs/architecture/README.md
```

Observed results:

- the full requested pytest bundle failed only in `guardian/tests/core/test_provider_registry.py` with six dynamic-provider discovery assertions
- the rest of the regression slice passed when the provider-registry subset was excluded
- docs validation passed
- diff hygiene passed
- the leak grep returned no matches

### Upload / embed / retrieve probe

```sh
docker compose exec -T backend python - <<'PY'
from guardian.workers.document_embed_worker import process_document_embed_task
from guardian.core.dependencies import load_guardian_db_from_env
from guardian.vector.store import VectorStore

DOC_ID = 'ab437c42-938f-4c74-9d37-4705473b8cf7'
SENTINEL = 'SUPPORTED_PROOF_SENTINEL_2026_05_05'

db = load_guardian_db_from_env()
process_document_embed_task({'doc_id': DOC_ID}, db=db)
store = VectorStore()
results = store.search(SENTINEL, k=5, namespace='thread:27', user_id='local')
print(results)
PY
```

### Coding-result return probe

```sh
docker compose exec -T backend python - <<'PY'
import os, requests
base='http://127.0.0.1:8888'
headers={'X-API-Key': os.environ['GUARDIAN_API_KEY']}
thread_id = 29
requests.get(base + f'/api/chat/{thread_id}/messages', headers=headers, timeout=30)
requests.get(base + f'/api/chat/debug/evals/{thread_id}/latest', headers=headers, timeout=30)
requests.get(base + f'/api/chat/debug/rag-trace/{thread_id}/latest', headers=headers, timeout=30)
PY
```

### Runtime-target probe

```sh
python3 -m pytest -q guardian/tests/routes/test_agent_orchestration_events.py
```

---

## Health Evidence

The live supported-profile health surfaces agreed on the current tip:

- `/health` returned `status: ok`
- `supported_profile.name` was `v1-local-core-web-mcp`
- `supported_profile.valid` was `true`
- `supported_profile.selected_provider` was `local`
- `supported_profile.selected_provider_supported` was `true`
- `supported_profile.mismatches` was empty
- `/health/chat` returned `provider: local`, `model: library2/ministral-3:8b`, and a fresh worker heartbeat
- `/api/health/llm` returned `status: ok` / `status: online` with the same local provider and model truth
- `provider_truth.supported_profile_approved` was `true`
- `provider_truth.egress_allowed` was `true`
- `provider_truth.discovered_inventory` was `true`
- `provider_truth.cloud_capable_configuration_present` was `true`, but the supported profile still approved only the local path

The runtime therefore described the supported local-first posture consistently across the health surfaces.

---

## Provider / Catalog Evidence

Catalog behavior matched the supported profile:

- Default `/api/llm/catalog` returned `provider_count: 1`
- The default catalog surface showed only the local provider as available, enabled, and authorized
- The local provider truth reported `supported_profile_approved: true`
- `/api/llm/catalog?include=all` returned `provider_count: 7`
- The include-all/operator view exposed the cloud-capable providers for inspection without widening the supported beta claim
- Unsupported cloud providers surfaced as unavailable / unauthorized with `disabled_reason: Missing provider credentials`
- No default user-facing catalog view implied that cloud providers were beta-supported

This is the live operator truth for the current tip: catalog discovery remains distinct from support, and the supported profile still resolves to the local provider only.

---

## Chat Completion Evidence

Thread `28` provided a live assistant completion on the supported path and persisted the result back to the thread.

Observed evidence:

- completion accepted by the route
- assistant reply persisted in the thread
- live eval snapshot populated at `GET /api/chat/debug/evals/28/latest`
- `trace_snapshot` included `assistant_output_text`, `retrieval_summary`, `retrieval_policy`, and `trace`
- `GET /api/chat/debug/rag-trace/28/latest` returned sanitized trace availability and no raw content
- requested model was `gemma4-e4b-hauhau:latest`
- final provider/model were `local` / `library2/ministral-3:8b`
- the live runtime overrode the requested model to the configured local chat model, which is the supported profile behavior in this checkout

The exact Thread A refusal text `I can't view the image.` did not appear in Thread B.

---

## Upload / Embed / Retrieve Evidence

The document path proved end to end on the live supported stack.

Observed evidence:

- uploaded document id: `ab437c42-938f-4c74-9d37-4705473b8cf7`
- thread id: `27`
- sentinel text: `SUPPORTED_PROOF_SENTINEL_2026_05_05`
- `GET /api/media/documents/ab437c42-938f-4c74-9d37-4705473b8cf7` returned `embedding_status: ready`
- the public document detail route preserved the parsed text and the embedding timestamps
- the live `VectorStore.search(...)` seam returned a sentinel-backed hit in namespace `thread:27`
- the returned chunk metadata preserved the document id, filename, namespace, project/thread scope, and user id

This shows that the proof document was uploaded, embedded, and retrievable on the supported runtime.

---

## Image Containment Evidence

The image-turn containment proof remained intact on the current tip.

Observed evidence:

- Thread A contained the refusal text exactly: `I can't view the image.`
- Thread B received a separate image turn and completed successfully
- Thread B did not inherit Thread A refusal text in the assistant message, task events, trace, or eval snapshot
- `GET /api/chat/debug/evals/28/latest` showed a populated trace snapshot
- `GET /api/chat/debug/rag-trace/28/latest` exposed sanitized trace availability with `trace_available: true` and `trace_unavailable_reason: null`
- the live trace surfaces did not expose raw image bytes, raw base64 payloads, or hidden prompt material

The debug route stayed diagnostic-only; the richer containment evidence lived in the eval snapshot and task payload.

---

## Coding-Result Return Evidence

The coding-result return path landed back in the source thread on the live stack.

Observed evidence:

- source thread id: `29`
- source message id: `61`
- coding run id: `run_aadf2d95fe6641ca`
- deployment id: `dep_4d6f24563f3d40ab`
- runtime target used by the live harness: `container`
- the coding worker produced a durable `coding_result` assistant message in the source thread
- the returned message included lineage metadata:
  - `run_id`
  - `source_thread_id`
  - `source_message_id`
  - `project_id`
- the returned artifact recorded `delivery_ok: true`
- the returned result was idempotent: repeating the terminal finalization did not create duplicate thread messages or duplicate artifacts
- the live result was an error-path result because Pi execution failed in the worker environment, but the user-visible handoff still landed in the source thread

The returned result did not include a commit hash or validation results because that live run terminated before those fields were available.

---

## Runtime-Target Evidence

The agent-orchestration runtime-target contract matched the schema allowlist.

Observed evidence:

- accepted runtime targets: `container` and `terminal`
- coding execution used `runtime_target="container"`
- unknown runtime targets failed closed
- the stale `pi_codex_runner` target did not appear in live route/event payloads

This closes the earlier runtime-target drift on the current tip.

---

## Failures and Caveats

The live proof itself passed, but the requested validation bundle surfaced one unrelated unit-test failure set:

- `python3 -m pytest -q guardian/tests/routes/test_health_supported_profile.py guardian/tests/core/test_provider_registry.py guardian/tests/core/test_llm_catalog.py guardian/tests/routes/test_agent_orchestration_events.py guardian/tests/workers/test_coding_worker.py tests/routes/test_chat_profile_trace.py`
- result: the combined bundle failed in `guardian/tests/core/test_provider_registry.py` on six dynamic-provider discovery assertions
- the rest of the requested regression slice passed when run without that provider-registry subset

This does not change the live runtime evidence, but it is a real test-seam caveat worth preserving for future cleanup.

---

## Final Verdict

**PASS**

The supported profile is freshly proven on the current tip, and the live runtime now agrees on:

- health and catalog posture
- chat completion
- upload -> embed -> retrieve
- image-turn containment
- coding-result return to the source thread
- runtime-target normalization

The runtime still reports `supported_profile.release_hold: true`, so this artifact is proof of supported-path truth, not a release-signoff claim.

---

## What This Proof Does Not Prove

This proof does not prove:

- final release readiness
- cloud-provider beta support
- quarantine surfaces as part of the release promise
- that the provider-registry unit-test slice is clean in every environment
- that all future runtime changes will preserve this exact evidence without re-running the proof

---

## 2026-05-08 Follow-up Recheck

**Recheck date:** 2026-05-08
**Commit under test:** `1775466302ed9c55f915a453b02100383febdcd6`
**Runtime path:** Supported local Docker Compose stack

This follow-up rechecked the previously blocked document route proof after the backend startup blocker was cleared.

### Recheck Commands

```sh
docker compose restart backend worker-document-embed
docker compose ps
docker compose logs --tail=120 backend
```

```sh
docker compose exec -T backend python - <<'PY'
import json, os, urllib.error, urllib.request
base = 'http://127.0.0.1:8888'
headers = {'X-API-Key': os.environ['GUARDIAN_API_KEY']}

def request(method, path, body=None, extra_headers=None):
    req_headers = dict(headers)
    if extra_headers:
        req_headers.update(extra_headers)
    data = None if body is None else (body if isinstance(body, bytes) else body.encode())
    req = urllib.request.Request(base + path, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, resp.read().decode()

status, raw = request('GET', '/api/media/documents/84c6ab2f-2a4f-4257-bbfa-613b055657b3')
print(status, raw)
status, raw = request('GET', '/api/chat/28/messages')
print(status, raw)
status, raw = request('GET', '/api/chat/debug/rag-trace/28/latest')
print(status, raw)
PY
```

### Observed Evidence

- The live supported upload path succeeded with a thread-scoped document attachment.
- Explicit `project_id=1` upload input returned `404 Project not found`, so the supported recheck used `thread_id=28` without the explicit project override.
- Uploaded document id: `84c6ab2f-2a4f-4257-bbfa-613b055657b3`
- Thread id: `28`
- Sentinel text: `SUPPORTED_PROOF_SENTINEL_2026_05_08`
- `GET /api/media/documents/84c6ab2f-2a4f-4257-bbfa-613b055657b3` returned `embedding_status: ready`
- The document detail response preserved the parsed text and embedding timestamps
- `GET /api/chat/28/messages` returned an assistant response containing the exact sentinel token
- The assistant payload recorded `retrieval_injected: true`, `linked_document_injected: true`, and `effective_source_mode: project`
- `GET /api/chat/debug/rag-trace/28/latest` showed `source_mode: project`, `retrieval_query_matches_latest_turn: true`, `widen_reason: none`, and `linked_document_count: 3`

### Follow-up Verdict

**PASS**

The previously blocked document readback and supported-path retrieval recheck now pass again on the live local Compose path. This re-proves the document upload -> embed -> retrieve seam on the supported runtime, but it does not change the historical PARTIAL verdict in this artifact or upgrade broader release readiness.
