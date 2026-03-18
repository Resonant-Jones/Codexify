# Beta-1 Supported Profile Proof

## Scope

This artifact records fresh live-runtime evidence for the Beta-1 supported profile on the local Compose path in the current repo state.

Target proof points:

1. `CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false` are active in the live stack.
2. Quarantined non-core routes are unavailable on that profile.
3. The supported happy path works end to end:
   - thread create
   - assistant completion
   - document upload
   - embed readiness
   - retrieval / RAG evidence

This task changed only this document. No runtime code, tests, scripts, or Compose config were edited.

## Environment

- Evidence captured: `2026-03-18T10:30:47Z`
- Repo: `codex/capture-provider-governance-map`
- Commit under test: `345cd841126c4c4fd1bcbb188521fbfc967c85e1`
- Operator: `Codex`
- API base: `http://localhost:8888`
- Temp env file: `/tmp/codexify-beta.env`

Commands used:

```bash
cat > /tmp/codexify-beta.env <<'EOF'
GUARDIAN_API_KEY=test-dev-key
CODEXIFY_RUNTIME_ENV_FILE=/tmp/codexify-beta.env
CODEXIFY_BETA_CORE_ONLY=true
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
EOF
```

```bash
docker compose --env-file /tmp/codexify-beta.env config
docker compose --env-file /tmp/codexify-beta.env up -d --force-recreate db redis backend worker-chat worker-document-embed
```

Observed on the normal Compose path:

- `docker compose ... config` still warned that `LOCAL_CHAT_MODEL` and `NEO4J_PASS` were unset from the temp env context.
- The normal `up -d --force-recreate` path failed before backend startup because `neo4j` exited with:

```text
neo4j/ is invalid
Invalid value for NEO4J_AUTH: 'neo4j/'
dependency failed to start: container codexify-neo4j-1 exited (1)
```

- To continue evidence gathering after the normal path failed, a recovery-only command was used against the already healthy `db` and `redis` services:

```bash
LOCAL_CHAT_MODEL="$(sed -n 's/^LOCAL_CHAT_MODEL=//p' .env | head -n1)" \
docker compose --env-file /tmp/codexify-beta.env up -d --no-deps --force-recreate backend worker-chat worker-document-embed
```

- Recovery result:
  - `backend`: `Up (healthy)`
  - `worker-chat`: `Up`
  - `worker-document-embed`: `Up`

Repo-defined smoke command also ran:

```bash
GUARDIAN_API_KEY="$(sed -n 's/^GUARDIAN_API_KEY=//p' .env | head -n1)" \
BETA_ENV_SOURCE_FILE=/tmp/codexify-beta.env \
bash scripts/verification/smoke_beta1.sh
```

Smoke result:

```text
[2026-03-18T10:29:48Z] Starting Beta-1 smoke services
...
dependency failed to start: container codexify-neo4j-1 exited (1)
```

## Effective Profile Flags

Config inspection command:

```bash
docker compose --env-file /tmp/codexify-beta.env config | sed -n '/backend:/,/^[^[:space:]]/p'
```

Observed config excerpt:

```text
ALLOW_CLOUD_PROVIDERS: "true"
CODEXIFY_BETA_CORE_ONLY: "false"
CODEXIFY_LOCAL_ONLY_MODE: "false"
LOCAL_CHAT_MODEL: ""
```

Live runtime inspection commands:

```bash
docker compose --env-file /tmp/codexify-beta.env exec -T backend sh -lc 'printf ...'
docker compose --env-file /tmp/codexify-beta.env exec -T worker-chat sh -lc 'printf ...'
docker compose --env-file /tmp/codexify-beta.env exec -T worker-document-embed sh -lc 'printf ...'
```

Observed live container values:

```text
backend beta=false local_only=false cloud=true local_chat_model=qwen3.5:27b temp_api_key=no
worker-chat beta=false local_only=false cloud=true local_chat_model=qwen3.5:27b temp_api_key=no
worker-document-embed beta=false local_only=false cloud=true local_chat_model=qwen3.5:27b temp_api_key=no
```

Result:

- The live stack did not activate the requested Beta-1 flags.
- The temp env API key did not reach the backend or workers.
- The supported profile was not the active runtime profile.

## Quarantined Route Checks

Probe command:

```bash
GET /api/connectors
GET /api/tools/manifest
```

Observed results:

```text
GET /api/connectors -> 200
body: []

GET /api/tools/manifest -> 200
body: manifest envelope returned
```

Expected supported-profile behavior was route quarantine / `404`.

Result:

- `GET /api/connectors` remained mounted.
- `GET /api/tools/manifest` remained mounted.
- Quarantine behavior was not consistent with the Beta-1 runbook.

## Happy-Path Runtime Proof

Fresh runtime commands:

```bash
POST /api/chat/threads
POST /api/chat/3/messages
POST /api/chat/3/complete
GET  /api/chat/3/messages?limit=50
GET  /api/chat/debug/rag-trace/3/latest
```

Observed results:

- Thread create succeeded:

```json
{"ok":true,"id":3,"thread":{"id":3,"user_id":"beta-proof-user-20260317-happy","title":"beta-proof-happy-1773798945", ...}}
```

- First message attempt failed because this route still validates the body as `Dict[str, str]` and rejected numeric `project_id`:

```json
{"detail":[{"type":"string_type","loc":["body","project_id"],"msg":"Input should be a valid string","input":1}]}
```

- Retried without `project_id`; user message persisted as `message_id=23`.
- Completion request succeeded at the enqueue surface and returned:

```text
thread_id=3 user_message_id=23 task_id=6aeb6c4b-33a8-49fe-a0ed-aa2e5f68dc83 turn_id=d160f772-9e23-471c-bd13-17ff756bf511
```

- No assistant message was persisted during the polling window:

```text
assistant_found=False assistant_message_id=None
```

- Task lifecycle was visible in the live task event stream:

```text
task.created
task.running
task.failed
```

- Terminal task failure payload:

```json
{
  "type": "task.failed",
  "data": {
    "duration_ms": 257083,
    "error": "Local inference request failed for model 'qwen3.5:27b' at http://host.docker.internal:11434/api/chat: Response ended prematurely.",
    "thread_id": 3,
    "turn_id": "d160f772-9e23-471c-bd13-17ff756bf511",
    "provider": "local"
  }
}
```

- `worker-chat` logs matched the task event failure and showed a local-provider `502`.
- Latest RAG trace for the thread after the failed completion:

```json
{"documents":[],"graph":[],"active_profile_id":"default","provider_override":null,"model_override":null,"injection_hash":null,"retrieval_mode":null,"model_mode":"cloud"}
```

Result:

- Thread create succeeded.
- Completion lifecycle was visible.
- Assistant completion did not succeed end to end.
- No assistant output was persisted on the tested runtime.

## Upload -> Embed -> Retrieve Proof

Fresh runtime commands:

```bash
POST /api/media/upload/document
GET  /api/media/documents?limit=20&thread_id=3
POST /api/retrieve
POST /search
```

Uploaded document content included the unique marker:

```text
beta-proof-rag-marker-20260317-amber-vault
```

Observed upload result:

```json
{
  "id":"3b33d492-1320-4e9c-bb99-7a3305bf60b3",
  "project_id":1,
  "thread_id":3,
  "filename":"beta-supported-proof-doc.txt",
  "embedding_status":"pending"
}
```

Observed embed lifecycle:

```json
{
  "embedding_status":"failed",
  "embedding_error":"Error in compaction: Failed to apply logs to the hnsw segment writer",
  "embedding_started_at":"2026-03-18T10:19:47.850936+00:00",
  "embedding_completed_at":"2026-03-18T10:19:51.531766+00:00"
}
```

Worker evidence:

```text
[document-embed] embedding failed doc_id=3b33d492-1320-4e9c-bb99-7a3305bf60b3 err=Error in compaction: Failed to apply logs to the hnsw segment writer
```

Retrieval evidence:

- `POST /api/retrieve` returned `404 Not Found` on this runtime.
- Fallback `POST /search` returned a response body of `{"detail":"Missing capability grant", ...}`.
- No successful retrieval output was produced after upload because the document never reached `ready`.

Result:

- Upload succeeded.
- Embed readiness failed.
- Retrieval / RAG availability was not proven on the live runtime.

## Failures Observed

- Normal Compose bring-up with the temp env file failed on the supported path because `neo4j` received invalid auth (`NEO4J_AUTH='neo4j/'`) and blocked `backend` startup through `graph-init`.
- `docker compose --env-file /tmp/codexify-beta.env config` still resolved the stack as `CODEXIFY_BETA_CORE_ONLY=false`, `CODEXIFY_LOCAL_ONLY_MODE=false`, and `ALLOW_CLOUD_PROVIDERS=true`.
- Live backend and worker containers confirmed the same incorrect flags and also showed that the temp API key did not reach runtime.
- Quarantined routes were still mounted:
  - `GET /api/connectors -> 200`
  - `GET /api/tools/manifest -> 200`
- The first message-post attempt exposed a contract mismatch on `project_id` typing for `/api/chat/{thread_id}/messages`.
- The completion task reached `task.failed` after `257083ms` with local provider error: `Response ended prematurely`.
- No assistant message was persisted for the completion attempt.
- The upload path queued correctly, but document embedding failed with `Error in compaction: Failed to apply logs to the hnsw segment writer`.
- Retrieval was not available on the tested runtime:
  - `POST /api/retrieve -> 404`
  - `POST /search -> Missing capability grant`
- The repo-defined `scripts/verification/smoke_beta1.sh` failed on boot with the same `neo4j` dependency break.

## Verdict

`supported-profile proof failed`

The verdict is failed because the requested Beta-1 profile was not actually active in the live Compose runtime, quarantined non-core routes remained available, the normal Beta-1 smoke gate failed on boot, the assistant completion happy path ended in `task.failed` with no persisted assistant output, and the upload -> embed -> retrieve path failed before the document became retrievable.
