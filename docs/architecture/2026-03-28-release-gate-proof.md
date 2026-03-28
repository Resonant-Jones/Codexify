# 2026-03-28 Release Gate Proof

## Scope

This artifact records one fresh operator-run release-gate verification against the local `main` branch on the supported Docker Compose path.

- Validation source of truth: live Compose runtime on current local `main`
- Automated tests: none apply for this docs/evidence task
- Repository edits in this task: this file only

## Environment

- Evidence captured: `2026-03-28T21:51:33Z`
- Branch under test: local `main`
- Commit under test: `06eea11472633542731db407c08329016cccc5ad`
- Working checkout used for runtime evidence: `/tmp/codexify-main-release-proof-20260328`
- Compose env file used: `/tmp/codexify-main-release-proof.env`
- API base: `http://127.0.0.1:8888`
- Probe location:
  - Host: all HTTP route probes
  - Inside running containers: effective env checks and vector-store inspection

Local `main` was checked out into a detached temporary worktree so the runtime evidence was captured against the actual local `main` commit, not this task branch:

```bash
git log --oneline --decorate -1 main
git worktree add --detach /tmp/codexify-main-release-proof-20260328 06eea11472633542731db407c08329016cccc5ad
```

Observed result:

```text
06eea1147 (origin/main, origin/HEAD, main) Merge origin/main
Preparing worktree (detached HEAD 06eea1147)
HEAD is now at 06eea1147 Merge origin/main
```

Temp env preparation used for the supported profile:

```bash
cp .env.example /tmp/codexify-main-release-proof.env
perl -0pi -e 's/^GUARDIAN_API_KEY=.*/GUARDIAN_API_KEY=release-gate-proof-20260328/m; s/^NEO4J_PASS=.*/NEO4J_PASS=codexify/m; s/^CODEXIFY_BETA_CORE_ONLY=.*/CODEXIFY_BETA_CORE_ONLY=true/m' /tmp/codexify-main-release-proof.env
printf '\nCODEXIFY_RUNTIME_ENV_FILE=/tmp/codexify-main-release-proof.env\nLOCAL_CHAT_MODEL=library2/ministral-3:8b\nAI_BACKEND=ollama\n' >> /tmp/codexify-main-release-proof.env
```

Supported-path startup command:

```bash
docker compose --env-file /tmp/codexify-main-release-proof.env up -d --force-recreate \
  db neo4j redis graph-init migrator model-prep backend \
  worker-chat worker-document-embed worker-chat-embed worker-warmup frontend
```

Post-start service state:

```bash
docker compose --env-file /tmp/codexify-main-release-proof.env ps -a
```

Observed result:

```text
codexify-backend-1                 Up (healthy)
codexify-db-1                      Up (healthy)
codexify-frontend-1                Up
codexify-graph-init-1              Exited (0)
codexify-migrator-1                Exited (0)
codexify-model-prep-1              Exited (0)
codexify-neo4j-1                   Up (healthy)
codexify-redis-1                   Up (healthy)
codexify-worker-chat-1             Up
codexify-worker-chat-embed-1       Up
codexify-worker-document-embed-1   Up
codexify-worker-warmup-1           Up
codexify-tts-1                     Up (healthy)
codexify-worker-voice-1            Up
```

Repo smoke command executed against the same env:

```bash
GUARDIAN_API_KEY=release-gate-proof-20260328 \
BETA_ENV_SOURCE_FILE=/tmp/codexify-main-release-proof.env \
bash scripts/verification/smoke_beta1.sh
```

Observed result:

```text
[2026-03-28T21:53:18Z] Checking Beta-1 quarantined routes
[2026-03-28T21:53:18Z] Checking Beta-1 core routes remain mounted
[2026-03-28T21:53:18Z] PASS: Beta-1 smoke completed in 29s
```

Operator note: `tts` and `worker-voice` containers were still present in the Compose project during this run, but the supported-profile HTTP surface below still returned `404` for quarantined media TTS/image-generation routes.

## Supported-Profile Flag Verification

Compose-level flag resolution:

```bash
docker compose --env-file /tmp/codexify-main-release-proof.env config | rg -n 'ALLOW_CLOUD_PROVIDERS|CODEXIFY_BETA_CORE_ONLY|CODEXIFY_LOCAL_ONLY_MODE|CODEXIFY_RUNTIME_ENV_FILE'
```

Observed excerpt:

```text
ALLOW_CLOUD_PROVIDERS: "false"
CODEXIFY_BETA_CORE_ONLY: "true"
CODEXIFY_LOCAL_ONLY_MODE: "true"
CODEXIFY_RUNTIME_ENV_FILE: /tmp/codexify-main-release-proof.env
```

Live backend-container verification:

```bash
docker compose --env-file /tmp/codexify-main-release-proof.env exec -T backend sh -lc \
  'printf "CODEXIFY_BETA_CORE_ONLY=%s\nCODEXIFY_LOCAL_ONLY_MODE=%s\nALLOW_CLOUD_PROVIDERS=%s\nCODEXIFY_RUNTIME_ENV_FILE=%s\n" \
  "$CODEXIFY_BETA_CORE_ONLY" "$CODEXIFY_LOCAL_ONLY_MODE" "$ALLOW_CLOUD_PROVIDERS" "$CODEXIFY_RUNTIME_ENV_FILE"'
```

Observed result:

```text
CODEXIFY_BETA_CORE_ONLY=true
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_RUNTIME_ENV_FILE=/tmp/codexify-main-release-proof.env
```

Conclusion:

- `CODEXIFY_BETA_CORE_ONLY=true` was active in the live backend runtime.
- `CODEXIFY_LOCAL_ONLY_MODE=true` was active in the live backend runtime.
- `ALLOW_CLOUD_PROVIDERS=false` was active in the live backend runtime.
- This run used the supported-profile flag set in the running backend, not just in the temp env file.

## Route Quarantine Posture

Probe command:

```bash
while IFS='|' read -r method path payload; do
  tmp=$(/usr/bin/mktemp)
  if [ -n "$payload" ]; then
    code=$(/usr/bin/curl -sS -o "$tmp" -w '%{http_code}' -X "$method" \
      -H "X-API-Key: release-gate-proof-20260328" \
      -H "Content-Type: application/json" \
      --data "$payload" \
      "http://127.0.0.1:8888$path")
  else
    code=$(/usr/bin/curl -sS -o "$tmp" -w '%{http_code}' -X "$method" \
      -H "X-API-Key: release-gate-proof-20260328" \
      "http://127.0.0.1:8888$path")
  fi
  body=$(/bin/cat "$tmp")
  /bin/rm -f "$tmp"
  printf 'METHOD %s\nPATH %s\nSTATUS %s\nBODY %s\n\n' "$method" "$path" "$code" "$body"
done <<'EOF'
GET|/api/connectors|
GET|/api/guardian/commands/manifest|
GET|/api/cron/jobs|
GET|/api/tools/manifest|
POST|/api/media/generate/image|{"prompt":"release-gate-proof"}
POST|/api/media/tts/synthesize|{"text":"release-gate-proof"}
EOF
```

Observed live results:

- `GET /api/connectors` -> `404` `{"detail":"Not Found"}`
- `GET /api/guardian/commands/manifest` -> `404` `{"detail":"Not Found"}`
- `GET /api/cron/jobs` -> `404` `{"detail":"Not Found"}`
- `GET /api/tools/manifest` -> `404` `{"detail":"Not Found"}`
- `POST /api/media/generate/image` -> `404` `{"detail":"Not Found","request_id":"574459eb-9465-4b56-b80e-56cb8f23322d"}`
- `POST /api/media/tts/synthesize` -> `404` `{"detail":"Not Found","request_id":"5ebee678-ee11-4b5d-997d-c443a83f5bc7"}`

Conclusion:

- The non-core routes above were actually unavailable in the running supported profile.
- I did not normalize away the `404`s: the live stack returned literal `{"detail":"Not Found"}` bodies.
- The running Compose project still had extra containers present, but the operator-visible HTTP surface remained quarantined for these non-core routes.

## Release-Gate Surface Reconciliation

Probe command:

```bash
for path in /health /api/health /health/chat /api/health/chat /health/llm /api/health/llm /api/llm/catalog; do
  tmp=$(/usr/bin/mktemp)
  code=$(/usr/bin/curl -sS -o "$tmp" -w '%{http_code}' \
    -H "X-API-Key: release-gate-proof-20260328" \
    "http://127.0.0.1:8888$path")
  body=$(/bin/cat "$tmp")
  /bin/rm -f "$tmp"
  printf 'PATH %s\nSTATUS %s\nBODY %s\n\n' "$path" "$code" "$body"
done
```

Observed live behavior:

- `/health` -> `200` `{"status":"ok"}`
- `/api/health` -> `404` `{"detail":"Not Found"}`
- `/health/chat` -> `200` and a full chat-health payload with `completion_service.ok=true`, `redis="ok"`, `queue.depth=0`, `provider="local"`, `provider_runtime.default_model="library2/ministral-3:8b"`
- `/api/health/chat` -> `404` `{"detail":"Not Found"}`
- `/health/llm` -> `200` and an LLM-health payload with `provider="local"`, `model="library2/ministral-3:8b"`, `status="online"`, `checked_endpoint="/api/tags"`
- `/api/health/llm` -> `200` and materially the same LLM-health payload as `/health/llm`
- `/api/llm/catalog` -> `200` and a catalog payload that exposed only provider `local`, with enabled model `qwen3.5:0.8b`

Exact route spelling reconciliation:

- Working only at root: `/health`, `/health/chat`
- Missing at `/api` alias: `/api/health`, `/api/health/chat`
- Working at both spellings: `/health/llm`, `/api/health/llm`
- Catalog working: `/api/llm/catalog`

Operator conclusion:

- `/health` proves only that the backend process responds to a basic liveness probe.
- `/health/chat` proves Redis reachability, worker heartbeat freshness, queue progression, and that the chat-health route can resolve a local provider payload.
- `/health/llm` and `/api/health/llm` prove the LLM health probe can reach a local endpoint and report an online local model.
- `/api/llm/catalog` proves what the catalog surface currently exposes as enabled/selectable to API clients.
- These surfaces do not prove actual turn completion.
- These surfaces do not agree closely enough for release-gate signoff:
  - the chat/LLM health routes reported `library2/ministral-3:8b`
  - the catalog route exposed enabled local model `qwen3.5:0.8b`
  - the live completion proof below failed on `library2/ministral-3:8b` with local inference endpoint `404`s

## Fresh Supported-Path Happy-Path Proof

Final happy-path attempt used the current live message-body contract after one earlier rejected request shape.

Command sequence:

```bash
POST /api/chat/threads
POST /api/chat/3/messages
POST /api/chat/3/complete
GET  /api/chat/3/messages?limit=50
GET  /api/chat/debug/rag-trace/3/latest
docker compose --env-file /tmp/codexify-main-release-proof.env logs --tail=200 worker-chat
```

Observed thread creation result:

```json
{"ok":true,"id":3,"thread":{"id":3,"user_id":"release-gate-proof-user-20260328-happy-2","title":"release-gate-happy-20260328-2","summary":"","project_id":null,"parent_id":null,"archived_at":null,"is_diary":false,"diary_mode":false,"exclude_from_identity":false,"modeling_excluded":false,"metadata":{},"active_profile_id":null,"created_at":"2026-03-28T22:08:29.621505+00:00","updated_at":"2026-03-28T22:08:29.621505+00:00"}}
```

Observed user message result:

```json
{"ok":true,"message":{"id":11,"thread_id":3,"role":"user","content":"Reply with exactly: RELEASE-GATE-HAPPY-20260328"}}
```

Observed completion accept result:

```json
{"ok":true,"acceptance_status":"accepted","acceptance_warnings":[],"task_id":"81e2f953-572e-4ad6-a477-b00d73832141","turn_id":"6f0847ef-52eb-4c1d-93e9-b77aeb9178e1","thread_id":3,"depth_mode":"normal","requested_depth_mode":"deep","effective_depth_mode":"light","depth_downgrade_reason":"no_project","messages_url":"/api/chat/3/messages","trace_url":"/api/chat/debug/rag-trace/3/latest"}
```

Observed persisted messages after polling:

```json
{"ok":true,"total":1,"messages":[{"id":11,"thread_id":3,"role":"user","content":"Reply with exactly: RELEASE-GATE-HAPPY-20260328","created_at":"2026-03-28T22:08:29.732737+00:00","kind":"chat"}]}
```

Observed RAG trace after the failed completion:

```json
{"documents":[],"graph":[],"active_profile_id":"default","provider_override":null,"model_override":null,"injection_hash":null,"retrieval_mode":null,"model_mode":"cloud"}
```

Observed worker failure surface:

```text
[task] running type=chat_completion id=81e2f953-572e-4ad6-a477-b00d73832141 ... thread=3 ...
[ContextBroker] thread=3 depth=normal messages=1 semantic=0 obsidian=0 docs(project/thread)=0/0 memory=0 graph=0
[task] failed type=chat_completion id=81e2f953-572e-4ad6-a477-b00d73832141 ... err=502: Local inference request failed for model 'library2/ministral-3:8b'. Attempted endpoints: http://host.docker.internal:11434/api/chat (HTTP 404); http://host.docker.internal:11434/v1/chat/completions (HTTP 404)
```

Conclusion:

- Thread creation worked.
- User message persistence worked.
- Completion acceptance worked.
- Assistant output was not persisted or retrievable from `/api/chat/3/messages`.
- The live happy path failed because the chat worker accepted the task and then failed the local inference call with `502` after both attempted endpoints returned `404`.

## Fresh Ingestion Path Proof

Fresh upload run used a brand-new sentinel document to avoid dedupe with earlier proof attempts.

Command sequence:

```bash
POST /api/chat/threads
POST /api/media/upload/document
GET  /api/media/documents?limit=50
POST /api/retrieve
docker compose --env-file /tmp/codexify-main-release-proof.env logs --tail=200 worker-document-embed
docker compose --env-file /tmp/codexify-main-release-proof.env exec -T backend sh -lc 'printf "CODEXIFY_VECTOR_STORE=%s\nCODEXIFY_CHROMA_PATH=%s\nCODEXIFY_COLLECTION=%s\n" "$CODEXIFY_VECTOR_STORE" "$CODEXIFY_CHROMA_PATH" "$CODEXIFY_COLLECTION"'
docker compose --env-file /tmp/codexify-main-release-proof.env exec -T worker-document-embed sh -lc 'printf "CODEXIFY_VECTOR_STORE=%s\nCODEXIFY_CHROMA_PATH=%s\nCODEXIFY_COLLECTION=%s\n" "$CODEXIFY_VECTOR_STORE" "$CODEXIFY_CHROMA_PATH" "$CODEXIFY_COLLECTION"'
docker compose --env-file /tmp/codexify-main-release-proof.env exec -T backend python -c "from guardian.vector.store import VectorStore; import json; store=VectorStore(); print(json.dumps({'health': store.health()}, ensure_ascii=True))"
docker compose --env-file /tmp/codexify-main-release-proof.env exec -T worker-document-embed python -c "from guardian.vector.store import VectorStore; import json; print(json.dumps({'health': VectorStore().health()}, ensure_ascii=True))"
docker compose --env-file /tmp/codexify-main-release-proof.env exec -T backend python -c "from guardian.vector.store import VectorStore; import json; print(json.dumps(VectorStore().search('ORBITAL-SALT-20260328-FRESH', k=3), ensure_ascii=True))"
```

Observed thread creation result:

```json
{"ok":true,"id":6,"thread":{"id":6,"user_id":"release-gate-proof-user-20260328-ingest-3","title":"release-gate-ingest-20260328-3","summary":"","project_id":null,"parent_id":null,"archived_at":null,"is_diary":false,"diary_mode":false,"exclude_from_identity":false,"modeling_excluded":false,"metadata":{},"active_profile_id":null,"created_at":"2026-03-28T22:19:56.725889+00:00","updated_at":"2026-03-28T22:19:56.725889+00:00"}}
```

Observed upload result:

```json
{"id":"185e96be-374a-4093-ac88-fffb2304a170","project_id":1,"thread_id":6,"src_url":"/media/documents/20260328-f8a691ae--release-gate-proof-upload-3.txt?sig=LXfzyPkKyOpE6TCMWjVSO4hnjZAL_qoMtnNNm3IOEZk","filename":"release-gate-proof-upload-3.txt","filesize":114,"mime_type":"text/plain","source_tag":"uploaded","parsed_text":"Release gate retrieval proof document.\nSentinel: ORBITAL-SALT-20260328-FRESH\nSecondary token: HARBOR-EMBER-SWITCH\n","embedding_status":"pending","embedding_error":null,"embedding_started_at":null,"embedding_completed_at":null,"created_at":"2026-03-28T22:19:56.849306+00:00"}
```

Observed listing after poll:

```json
{"documents":[{"id":"185e96be-374a-4093-ac88-fffb2304a170","project_id":1,"thread_id":6,"src_url":"/media/documents/20260328-f8a691ae--release-gate-proof-upload-3.txt?sig=LXfzyPkKyOpE6TCMWjVSO4hnjZAL_qoMtnNNm3IOEZk","filename":"release-gate-proof-upload-3.txt","mime_type":"text/plain","filesize":114,"source_tag":"uploaded","embedding_status":"ready","embedding_error":null,"embedding_started_at":"2026-03-28T22:19:56.875689+00:00","embedding_completed_at":"2026-03-28T22:19:57.371457+00:00","created_at":"2026-03-28T22:19:56.835944+00:00"}],"count":2}
```

Observed embed worker log:

```text
[document-embed] embedded doc_id=185e96be-374a-4093-ac88-fffb2304a170 chunks=1
```

Observed exposed retrieval API result:

```text
POST /api/retrieve -> 404
{"detail":"Not Found"}
```

Observed backend vector-store env:

```text
CODEXIFY_VECTOR_STORE=
CODEXIFY_CHROMA_PATH=
CODEXIFY_COLLECTION=
```

Observed document-embed worker vector-store env:

```text
CODEXIFY_VECTOR_STORE=chroma
CODEXIFY_CHROMA_PATH=./.chroma
CODEXIFY_COLLECTION=codexify_vault
```

Observed in-container vector-store health:

```json
backend: {"health":{"status":"ok","backend":"faiss"}}
worker-document-embed: {"health":{"status":"ok","backend":"chroma"}}
```

Observed in-container search from the running backend:

```json
[]
```

Conclusion:

- Upload succeeded.
- Embed lifecycle reached `ready`.
- Retrieval evidence for the uploaded content did not succeed on the supported API surface because `/api/retrieve` was not mounted and returned `404`.
- Retrieval remained unproven even after in-container inspection:
  - the embed worker claimed a successful `chunks=1` write
  - the running backend resolved `VectorStore` to `faiss`
  - the running embed worker resolved `VectorStore` to `chroma`
  - backend search for the fresh sentinel returned `[]`
- This is an exact, live failure surface, not a softened interpretation.

## Final Release-Gate Verdict

| Gate item | Result | Evidence |
| --- | --- | --- |
| Supported-profile flags active in live runtime | Pass | Backend container reported `CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false` |
| Quarantined non-core routes unavailable | Pass | All probed non-core routes returned `404` with concrete `Not Found` bodies |
| Health/catalog route surface reconciled closely enough for signoff | Fail | `/health` and `/health/chat` lack `/api` aliases; health routes reported `library2/ministral-3:8b` while `/api/llm/catalog` exposed `qwen3.5:0.8b` |
| Fresh create-message-complete-persist chat path | Fail | Completion was accepted but no assistant message persisted; worker failed with `502` after local inference endpoint `404`s |
| Fresh upload -> embed lifecycle | Pass | Fresh upload reached `embedding_status=ready`; embed worker logged `chunks=1` |
| Fresh retrieval evidence for uploaded content | Fail | `/api/retrieve` returned `404`; backend search for the fresh sentinel returned `[]` while embed worker used a different vector-store backend |

Release-gate blocker status: **not closed**

This artifact does **not** close the release-gate evidence blocker.

Remaining exact gap:

1. Accepted chat completions on the supported path still fail at execution time because the worker targets `library2/ministral-3:8b` and both attempted local inference endpoints returned `404`.
2. Fresh document embedding can reach `ready`, but retrieval is not proven on the supported path because `/api/retrieve` is missing and the live backend and embed worker resolved different vector-store backends (`faiss` vs `chroma`), leaving the backend unable to return the fresh sentinel content.
