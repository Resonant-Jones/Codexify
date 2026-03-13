# Deterministic Async RAG Loop Validation

This artifact codifies the audit requirement `FINDING-2026-02-16-003`: prove that the asynchronous RAG loop (thread creation → message enqueue → worker completion → trace retrieval) works end-to-end with deterministic commands and explicit pass/fail signals.

## Validation Script

- Path: `scripts/verification/rag_loop_validation.sh`
- Nature: deterministic, read/write only through public HTTP endpoints plus docker compose bring-up.
- Exit codes:
  - `0` with three `PASS` banners → validation succeeded.
  - Non-zero with `[FAIL] <reason>` → stop and remediate before retrying.

### Required Inputs

| Variable | Default | Description |
| --- | --- | --- |
| `GUARDIAN_API_KEY` | _(none)_ | Mandatory API key for all protected calls. Script aborts if missing. |
| `GUARDIAN_API_BASE` | `http://localhost:8888` | Root URL for Guardian API/health/OpenAPI. |
| `GUARDIAN_USER_ID` | `default` | Injected when posting the seed message. |
| `GUARDIAN_RAG_PROVIDER` | `local` | Provider argument sent to `/complete`. Override if you need a remote model. |
| `GUARDIAN_RAG_DEPTH_MODE` | `normal` | Depth request passed through to `/complete`. |
| `GUARDIAN_RAG_PROMPT` | `RAG validation ping <UTC timestamp>` | Message content to post before triggering completion. |
| `GUARDIAN_RAG_POLL_SECONDS` | `2` | Interval between polls for assistant output and trace. |
| `GUARDIAN_RAG_POLL_ATTEMPTS` | `30` | Maximum polls (default 60 seconds). |
| `GUARDIAN_RAG_CURL_TIMEOUT` | `5` | Per-request curl timeout. |

### Tooling Prereqs

The script fails fast if any of these are missing:

```
docker, docker compose, curl, jq, rg, git
```

## Execution Flow

Run from a clean repository root:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
export GUARDIAN_API_KEY=...
./scripts/verification/rag_loop_validation.sh
```

The script performs the following deterministic steps (each surfaces `[STEP] …` logging and halts on failure):

1. **Preflight**  
   - Verifies repo cleanliness via `git status --porcelain -uall` (audit STOP condition).  
   - Confirms required binaries are installed.

2. **Bring-up**  
   - Runs `docker compose up -d db redis backend worker-chat`.  
   - Hits `GET ${GUARDIAN_API_BASE}/health` to ensure the stack is reachable.  
   - Fetches `openapi.json` and `rg`s for `/api/chat/threads`, `/chat/{thread_id}/complete`, `/api/chat/debug/rag-trace/{thread_id}/latest` to prove the documented endpoints exist.

3. **Loop validation**  
   - `POST /api/chat/threads` (with `X-API-Key`) → captures `thread_id`.  
   - `POST /api/chat/{thread_id}/messages` with a user prompt.  
   - `POST /api/chat/{thread_id}/complete` to enqueue the worker task; parses `task_id`, `messages_url`, `trace_url`.  
   - Polls `messages_url` until an assistant message is persisted.  
   - Polls `trace_url` until `.documents` or `.graph` contains at least one element.

## Pass/Fail Signals

- **PASS**: Script prints both of these banners before exiting:
  - `PASS Assistant reply persisted (message_id=…)`
  - `PASS RAG trace available (documents=X, graph=Y)`
  - Followed by `PASS Async RAG completion loop validated (task_id=…, thread_id=…)`
- **FAIL**: Any unmet condition yields `[FAIL] <context>` and a non-zero exit. Examples:
  - Missing Docker permissions (e.g., `permission denied while trying to connect to the Docker daemon socket`).
  - Backend not running or `curl` timeout when fetching health/OpenAPI.
  - No assistant message within the configured polling window.
  - Trace endpoint never surfaces documents/graph.

All failure cases include actionable text; rerun after fixing the reported prerequisite.

## Manual Command Breakdown

If you prefer to run steps by hand (or to debug a failing script), execute the same sequence explicitly:

```bash
docker compose up -d db redis backend worker-chat
curl -fsS "$GUARDIAN_API_BASE/health"
curl -fsS "$GUARDIAN_API_BASE/openapi.json" \
  | rg -n '/api/chat/threads|/chat/\{thread_id\}/complete|/api/chat/debug/rag-trace'

create_resp=$(curl -fsS -H "X-API-Key: $GUARDIAN_API_KEY" \
  -H 'Content-Type: application/json' -d '{"title":"RAG validation","user_id":"default"}' \
  "$GUARDIAN_API_BASE/api/chat/threads")
thread_id=$(jq -r '.id' <<<"$create_resp")

curl -fsS -H "X-API-Key: $GUARDIAN_API_KEY" -H 'Content-Type: application/json' \
  -d '{"role":"user","content":"RAG validation ping"}' \
  "$GUARDIAN_API_BASE/api/chat/$thread_id/messages"

complete_resp=$(curl -fsS -H "X-API-Key: $GUARDIAN_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"provider":"local","depth_mode":"normal"}' \
  "$GUARDIAN_API_BASE/api/chat/$thread_id/complete")
messages_url=$(jq -r '.messages_url' <<<"$complete_resp")
trace_url=$(jq -r '.trace_url' <<<"$complete_resp")
```

Then poll `messages_url` and `trace_url` (adding `X-API-Key`) until both indicate success, mirroring the script’s logic.

## Troubleshooting Notes

- **Docker socket permissions**: If you see `permission denied … /docker.sock`, ensure the Docker daemon is running and that your shell user has access (on macOS, open Docker Desktop first). The script surfaces this clearly and exits at the bring-up step.
- **Queue latency**: Increase `GUARDIAN_RAG_POLL_ATTEMPTS` or `GUARDIAN_RAG_POLL_SECONDS` if your worker takes longer than ~60 seconds to process the completion.
- **Trace empties**: If `/api/chat/debug/rag-trace/{thread_id}/latest` returns an empty body despite completion, confirm workers emit `task.completed` payloads with `trace` data. The script treats empty `documents` and `graph` arrays as a failure so trace regressions are caught early.

This doc + script combination is the canonical artifact auditors will look for. Keep both updated if endpoint paths or queue semantics change.
