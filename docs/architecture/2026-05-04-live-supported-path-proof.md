# 2026-05-04 Live Supported-Path Proof

## Scope

Fresh live proof on the exact current `main` tip. This is evidence capture only.

In scope:

- supported-profile posture on the live Compose stack
- provider catalog and health alignment
- chat completion acceptance -> worker execution -> assistant persistence
- upload -> embed -> retrieve on the live stack
- coding-result return path through Guardian back into the source thread

Out of scope:

- graph persistence redesign
- retrieval redesign
- UI work
- architecture contract edits
- current-state doc edits

## Environment

- branch: `main`
- exact HEAD commit at proof time: `232b3ad3dea56fd4e2d9e4e14b36b83d0e28f2d1`
- compose services used:
  - `db`
  - `redis`
  - `neo4j`
  - `backend`
  - `worker-chat`
  - `worker-document-embed`
  - `worker-chat-embed`
  - `worker-warmup`
  - `worker-coding`
  - `migrator`
- auth/env loading ritual:
  - the repo env file could not be sourced directly because four model-pin lines in `.env` contained a leading space after `=`
  - I used a sanitized temp copy at `/tmp/codexify-live-proof.env` for the authenticated proof run
  - the proof run still follows the repo's documented `set -a; source ...; set +a` pattern, but with the sanitized copy

Observed runtime posture from the backend container:

- `ALLOW_CLOUD_PROVIDERS=true`
- `CODEXIFY_BETA_CORE_ONLY=false`
- `CODEXIFY_LOCAL_ONLY_MODE=false`
- `LLM_PROVIDER=local`
- `LOCAL_BASE_URL=http://100.109.4.57:11434`
- `LOCAL_CHAT_MODEL=gemma4-e4b-hauhau:latest`

That posture does not strictly match the supported local-only beta contract.

## Exact Commands

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main

set -a; source /tmp/codexify-live-proof.env; set +a
BASE=http://localhost:8888

docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-document-embed worker-chat-embed worker-warmup
docker compose up -d worker-coding
docker compose ps

curl -s "$BASE/health" | jq
curl -s "$BASE/health/chat" | jq
curl -s "$BASE/api/health/llm" | jq
curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "$BASE/api/llm/catalog" | jq
curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "$BASE/api/llm/catalog?include=all" | jq
curl -s "$BASE/api/health/retrieval" | jq

make docs
git diff --check
```

Backend-container proof harnesses:

- chat proof: `POST /api/chat/threads`, `POST /api/chat/{thread_id}/messages`, `POST /api/chat/{thread_id}/complete`, poll task events, then `GET /api/chat/threads/{thread_id}`
- upload proof: `POST /api/media/documents/upload`, then `GET /api/media/documents`
- retrieval proof: query the live thread with the uploaded sentinel document in scope, then inspect the persisted assistant message and metadata
- coding-result proof: `POST /api/agents/coding/execute`, poll run/task events, then inspect the source thread for a returned coding result message

Sentinel values used in this proof:

- chat prompt marker: `ack-proof-chat-1777936130`
- uploaded doc sentinel for retrieval: `proof-threadlink-1777936332`
- coding instructions marker: `coding-proof-ok`

## Health + Provider Posture Results

### `/health`

Result: healthy.

Observed value:

- `status: ok`
- `service: core`

### `/health/chat`

Result: healthy and fresh.

Observed value:

- `redis: ok`
- `worker.status: fresh`
- `queue.depth: 0`
- `provider: local`
- `model: gemma4-e4b-hauhau:latest`
- `provider_runtime.id: local`
- `provider_runtime.authorized: true`
- `provider_runtime.available: true`
- `provider_runtime.enabled: true`

### `/api/health/llm`

Result: healthy and online.

Observed value:

- same local provider/model posture as `/health/chat`
- completion-service info reported healthy

### `/api/llm/catalog` and `/api/llm/catalog?include=all`

Result: both surfaces returned successfully.

Observed alignment:

- the live health surfaces are anchored on the local provider path
- the catalog surfaces were reachable and included the local model inventory
- I did not observe an enabled cloud provider in the main health path

Release-contract conclusion:

- the live runtime posture does not cleanly match the supported local-only beta contract because the backend environment still advertises cloud-capable / non-beta-core-only flags
- no unsupported provider was exposed as the active health-path provider, but the broader posture is still too loose for a clean supported-profile claim

### `/api/health/retrieval`

Result: ready.

Observed value:

- `status: ready`
- `ok: true`
- `same_runtime_as_worker: true`
- `proof_capable: true`

## Chat Completion Proof

Thread route proof:

- the live thread route returned thread `3`
- the thread belongs to project `1` (`General`) and user `local`

Route acceptance:

- `POST /api/chat/3/messages` returned `200`
- `POST /api/chat/3/complete` returned `200`
- completion response included:
  - `acceptance_status: accepted`
  - `task_id: f948e71e-2f5b-4b0d-9ee8-7e95001953ce`
  - `trace_url: /api/chat/debug/rag-trace/3/latest`

Worker execution evidence:

- task events reported the progression through:
  - `task.state: QUEUED`
  - `task.running`
  - `task.created`
  - `task.state: AWAITING_MODEL`
  - `task.state: AWAITING_FIRST_TOKEN`
  - `task.state: STREAMING`
  - `task.progress`
  - `task.chunk`
  - `task.state: COMPLETED`

Assistant persistence:

- persisted assistant message `id: 7`
- role: `assistant`
- content: `ack-proof-chat-1777936130`
- kind: `chat`

Task-event visibility:

- the run produced live task events rather than a silent success path
- the task stream is the proof of worker execution, not just route acceptance

## Upload -> Embed -> Retrieve Proof

Upload proof:

- the successful thread-linked upload used thread `3`
- document id: `3450342e-4286-4c8e-8afd-d691d8beadbc`
- project id: `1`
- thread id: `3`
- sentinel: `proof-threadlink-1777936332`
- upload returned `200`

Embedding readiness:

- the document transitioned from `embedding_status: pending` to `embedding_status: ready`
- `embedding_started_at` and `embedding_completed_at` were present

Retrieval proof:

- I queried the live thread for the exact sentinel token in the uploaded proof document
- the assistant response returned the exact sentinel string:
  - `proof-threadlink-1777936332`

Persisted retrieval evidence:

- message `id: 13`
- role: `assistant`
- content: `proof-threadlink-1777936332`
- metadata showed retrieval injection happened:
  - `linked_document_injected: true`
  - `semantic_injected: true`
  - `linked_document_count: 3`

Observed delay / degraded behavior:

- the direct debug trace route `GET /api/chat/debug/rag-trace/3/latest` returned an empty trace object
- despite that empty debug surface, the persisted assistant message and its metadata prove the retrieval path succeeded

Additional upload-note:

- an attempt to use a project-filtered document lookup returned `404 Project not found`
- the unfiltered document list surface was the reliable proof path for the live run

## Coding-Result Return Path Proof

Accepted coding work:

- `POST /api/agents/coding/execute` returned `200`
- the accepted run returned:
  - `run_id: run_b51930499a82459a`
  - `deployment_id: dep_94c195876a904afd`

Execution result:

- the run events reached:
  - `created`
  - `task.running`
  - `task.failed`

Source-thread return path:

- no `kind: coding_result` message landed back in the source thread
- the source thread message count for coding results stayed at `0`

Duplicate delivery:

- duplicate delivery did not occur
- however, that is only because no coding result was delivered at all

Conclusion for this seam:

- the coding-result path is not proven end-to-end on the current `main` tip
- the live seam failed after acceptance and did not return a coding result through Guardian into the source thread

## Observed Failures / Degraded Signals / Unknowns

- the live backend runtime advertises non-local-only posture flags:
  - `ALLOW_CLOUD_PROVIDERS=true`
  - `CODEXIFY_BETA_CORE_ONLY=false`
  - `CODEXIFY_LOCAL_ONLY_MODE=false`
- the proof run required a sanitized temp env copy because `.env` could not be sourced directly due to leading-space model pins
- the direct retrieval debug trace surface returned empty data even though the persisted thread metadata proved retrieval worked
- the project-filtered document lookup returned `404 Project not found`
- the coding-result return path failed after accepted execution and did not produce a returned coding message

## Release-Checklist Mapping

- supported-profile flags match live runtime: `FAIL`
- fresh live evidence exists on current `main`: `PASS`
- chat/retrieval/upload-embed-retrieve proven: `PASS`
- coding results return through Guardian into the source thread without duplicate delivery: `FAIL`
- catalog/health/provider posture agree: `PARTIAL`

Interpretation:

- the health surfaces agree on the active local provider path
- the backend environment still leaks a broader provider posture
- the chat and retrieval path are proven on the live stack
- the coding-result return path is not proven and remains broken in this proof run

## Final Result

`FAIL`

Reason:

- the live runtime posture does not cleanly match the supported local-only beta contract
- the coding-result return path failed to complete end-to-end
- this artifact captures the failure honestly and does not widen the release claim

No architecture contract was changed in this task.
