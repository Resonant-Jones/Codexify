# Beta Smoke Run - 2026-03-11

Date: 2026-03-11
Branch tested: `main`
Commit tested: `5b5a85a0fe552674412a273efb60555026f6b71f`
Operator: Codex
Environment:
- Local Docker Compose against a temporary `main` worktree at `/tmp/codexify-main-smoke-20260311`
- Local `.env` copied into the temporary worktree
- Existing non-`main` stack on standard ports was stopped before the `main` run
- Backend API evidence was collected from inside the backend container because host-side port access was unreliable in this Codex environment

Overall result:
- Fail

Failing steps:
- 1. Boot the supported stack
- 2. Verify frontend availability
- 6. Verify assistant completion
- 7. Verify turn/task flow does not stall
- 10. Verify retrieval from uploaded content
- 11. Verify core beta control surfaces do not break the core loop
- 12. Restart sanity check

Key blockers found:
- `main` did not complete a clean supported-stack boot. The full `docker compose up` path still needed manual recovery after the first run hit a `neo4j` dependency failure and the `migrator` needed a second start before it completed successfully.
- The `frontend` container did not bootstrap in this environment because startup attempted to fetch `pnpm` from `https://registry.npmjs.org/...` via Corepack at runtime.
- `/health/llm` reported the configured local provider path offline, and the chat worker logged `500 Server Error` from `http://host.docker.internal:11434/api/chat` for the first smoke completion task.
- Document upload and embedding reached `ready`, but retrieval was not proven on the supported chat path. The latest RAG trace for the smoke thread showed `"documents": []`, and no assistant turn was produced.

## Per-step results

| Step | Result | Notes | Blockers |
|---|---|---|---|
| 1. Boot the supported stack | Fail | After stopping the pre-existing non-`main` stack, `db` and `redis` became healthy, but the first full `docker compose up` on `main` did not complete cleanly. `migrator` only succeeded on a second run, and core backend/workers only came up after bypassing optional deps with `--no-deps`. | Full supported-path boot on `main` is not clean or repeatable enough to count as a release pass. |
| 2. Verify frontend availability | Fail | `frontend` never became usable. Its logs show Corepack attempting a runtime download of `pnpm@9.12.1` and failing the request to `registry.npmjs.org`. | Supported WebUI path was unavailable. |
| 3. Verify backend health surfaces | Degraded | In-container probes returned `200` for `/health`, `/health/chat`, and `/health/vector`. `/health/chat` reported `redis_reachable=true`, `enqueue_test_ok=true`, and a fresh worker heartbeat. `/health/llm` returned `status=offline` for provider `local` / model `qwen3.5:27b` with a timeout against `host.docker.internal:11434`. | Backend health was not acceptable enough for the beta promise because the configured completion provider was offline. |
| 4. Create a thread | Degraded | Backend fallback via `POST /api/chat/threads` succeeded and created thread `1` titled `2026-03-11 beta smoke`. | Supported UI path was unavailable, so this was not proven through the WebUI. |
| 5. Send a user message | Degraded | Backend fallback via `POST /api/chat/1/messages` succeeded and persisted the user message. | Supported UI path was unavailable, so this was not proven through the WebUI. |
| 6. Verify assistant completion | Fail | Two completion attempts were enqueued successfully (`task_id` `7a6ca98e-4004-4cec-83a0-dca3929bf2b5` and `9747be02-b110-45d4-8e1a-bcb18bfcf7b5`), but neither produced an assistant message. The first task emitted `task.failed` after about 52 seconds with `500 Server Error` from `http://host.docker.internal:11434/api/chat`. | Supported completion path is not working on the configured local provider path in this environment. |
| 7. Verify turn/task flow does not stall | Fail | The first completion task reached `task.failed`. The second remained without an assistant message through the observation window, and the task-event stream did not yield a clean terminal success. | Turn/task flow is not reliably reaching `task.completed` on the smoke path. |
| 8. Upload a document | Degraded | Backend fallback via `POST /api/media/upload/document` succeeded for `beta-smoke.txt`. The uploaded document was linked to thread `1`. | Supported UI path was unavailable, so this was not proven through the WebUI. |
| 9. Verify embedding lifecycle | Degraded | The uploaded document reached `embedding_status=ready` quickly, with `embedding_started_at=2026-03-11T16:02:30.893135+00:00` and `embedding_completed_at=2026-03-11T16:02:32.265124+00:00`. | Embedding success did not rescue the overall supported path because retrieval still could not be verified. |
| 10. Verify retrieval from uploaded content | Fail | A retrieval question was sent after the document reached `ready`, but no assistant turn was ever produced. The latest `/api/chat/debug/rag-trace/1/latest` response showed `"documents": []`. | Retrieval through the supported chat/RAG path was not demonstrated. |
| 11. Verify core beta control surfaces do not break the core loop | Fail | The supported UI/control surface path never loaded, so there was no credible way to verify beta-facing controls without drifting into unsupported API-only substitutions. | Frontend bootstrap failure blocked this regression check. |
| 12. Restart sanity check | Fail | After restarting backend and workers on the `main` smoke stack, `/health` returned `200`, `/health/chat` still showed Redis and worker heartbeat healthy, and thread `1` plus its two user messages persisted. However, the WebUI remained unavailable and assistant completion capability had already failed. | Persistence survived restart, but the supported local workflow still did not recover to a smoke-pass state. |

## Notes

- The local `main` branch did not contain the newer release docs that exist on this working branch, so the runtime was executed from the local `main` checkout and the results were recorded here afterward.
- The configured local provider path is outside the Docker Compose network (`LOCAL_BASE_URL=http://host.docker.internal:11434`), so chat completion on `main` currently depends on that external node being healthy.
- The smoke run found a meaningful split between backend subsystem health and actual release truth: queue health, worker heartbeat, document upload, and embedding were all observable, but the user-facing beta promise still failed because the WebUI and assistant-turn path were not green.
