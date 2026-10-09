# Natural Account Import-to-Recall Proof (R6)

**Overall result: FAIL for natural recall on the evaluated source/runtime.** The synthetic import and embedding prerequisites passed, and ordinary local chat completed and persisted an assistant answer. However, the requested `personal_knowledge` posture resolved to effective `project`; the broker trace contained no selected evidence, and the captured provider input contained no imported sentinel. The answer therefore did not use imported history. The account B ordinary-chat negative control was not run because the positive account A gate failed, as required by the stop conditions. Release posture remains **HOLD**.

## Source and isolated environment

- Application source: Goal 05 commit `7e8f0c284b0a9ddf284c5582cf8d3309852ea1e7`, branch `codex/synthetic-account-import-recall-qualification`. At the initial source audit, local `origin/main` was `d89459b6dbff08e8bdf0f030fc459d4c207fdb95` and Goal 05 was 8 commits ahead / 124 behind it, merge base `187573380270683816da9b3dcc0d4c2433b75a4e`. At final audit, the locally available `origin/main` ref resolved to `567f3e153612a2ed21b7c5b99fd61e9bad52de2d`; Goal 05 was then 3 commits ahead / 130 behind it, merge base `4eb460449096fefc5098ff700ef75034efeac521`. The runtime image remained frozen at the task-designated Goal 05 commit; this is not current-main qualification.
- The authorized proof worktree was `/Volumes/Dev_SSD/offload/codex/worktrees/synthetic-import-recall/Codexify-main`, clean before the artifact update. A disposable source archive was reconstructed at the Goal 05 SHA under `/private/tmp/codexify-goal06-src`; its five tracked model-profile LFS payloads were fetched to task-temporary LFS storage and verified against pointer SHA-256 and size. The repository checkout was not modified to restore LFS content.
- Runtime: task-owned Compose project `codexify_natural_import_recall_r6_20261009`, fresh PostgreSQL 15 database and named volumes, Redis 7 with persistence disabled, task-owned Chroma volume, task-owned import/media/app-data volumes, and migration head `17b23052da6a`. PostgreSQL was loopback-bound to port `15433`, Guardian to `18888`; no existing project or volume was reused, stopped, reset, or pruned.
- The backend image `codexify-natural-import-r6:7e8f0c2` was built from the disposable Goal 05 source archive. Backend and chat worker used the same named Chroma volume at `/app/.chroma`, collection `goal06_synthetic_import_recall_20261009`, and read-only local `bge-large-en-v1.5` model mount. A task-owned transparent HTTP capture sidecar forwarded to the host local inference service; the supported profile URL remained `http://host.docker.internal:8000/v1`.
- Runtime profile was `v1-local-core-web-mcp`, `LLM_PROVIDER=local`, `LOCAL_PROVIDER_VENDOR=whooshd`, `LOCAL_BASE_URL=http://host.docker.internal:8000/v1`, `LOCAL_CHAT_MODEL=local-chat`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, and `CODEXIFY_MULTI_USER_ENABLED=false`. Synthetic account-purpose sessions were issued and held only in task Redis / process memory. Secrets are omitted.
- The import and embedding workers were explicitly stopped after their jobs completed and before the chat attempt. Docker later reported exit code `137` with `OOMKilled=false` for both stopped worker containers; PostgreSQL, Redis, backend, and the chat worker remained healthy during the natural-chat attempt.

## Synthetic import and embedding prerequisite

No private archive was accessed. Two synthetic authenticated accounts were created in the isolated database. The exports used distinct workspace-scoped conversation and message IDs, deliberately untrusted export `user_id` values, and distinct factual sentinels. The user's question in the later chat did not include the sentinel.

| Account | Canonical account ID | Import job | Source conversation | Canonical thread / messages | Synthetic sentinel |
|---|---|---|---|---|---|
| A | `goal06-a-169994EC` | `e6163cde-1754-42eb-9c67-b531caf5099e` | `g06-argo-169994EC` | project `2`, thread `1`; messages `1, 2`, roles user then assistant | `ORBIT-A00C423CB4` |
| B | `goal06-b-169994EC` | `a2eb2a57-b503-4dbd-9ea6-6d676b253450` | `g06-greenhouse-169994EC` | project `3`, thread `2`; messages `3, 4`, roles user then assistant | `GLASS-7585695919` |

Both full random sentinels are shown because they are synthetic. Account A's source path was `Workspace-A/conversations__goal06.part-0001/file_0000000000000001.dat`; B used `Workspace-B/conversations__goal06.part-0002/file_0000000000000002.dat`. Each job completed with 1 thread, 2 messages, zero warnings, and zero failures. PostgreSQL readback showed each thread, project, and message owned by the matching authenticated account, `origin_system=openai`, user-before-assistant ordering, and the distinct source message IDs and source paths. The export's untrusted identity field did not become canonical ownership.

The real `worker-chat-embed` processed all four imported messages; canonical `ChatMessage.extra_meta.embedding_status` read back as `ready` for all four. The real Chroma store used the shared task-owned volume and collection. Before chat, `VectorStore.search` for A's Argo question in A's imported thread namespace returned A's assistant sentinel as its top result (score `0.6781`) and the user message as the second result (`0.6313`). B's equivalent query in A's namespace returned zero results when filtered by B's authenticated owner. B's own search returned only B-owned records. These establish account-scoped candidate availability, not ordinary-chat selection.

Vector metadata still carried `embedding_status=processing` in its derived records while canonical PostgreSQL readback was `ready`. This discrepancy was observed and is not treated as canonical readiness; the importer/worker and canonical messages were not modified.

## Account A ordinary-chat attempt

The normal Guardian API created thread `3` under account A, persisted user message `5`, and accepted one completion. The user turn was: “Can you remind me of the calibration code I recorded for the Argo observatory?” It contained no sentinel. The completion request asked for `source_mode=personal_knowledge`, `depth_mode=normal`, and `max_context=12`; no provider/model override, system override, or manually added evidence was supplied.

The API returned HTTP 200 with request `goal06-natural-a-66306ab33d`, task `8db1eedd-7a93-40b8-ac92-5dbfe16bb96f`, turn `7fc8b91e-0a85-4cec-8f0b-5b79ca1ae108`, and thread `3`. Its effective `source_mode` was `project` (while requested source mode in retrieval provenance remained `personal_knowledge`). The new chat thread belonged to project `1`; imported A's thread belonged to project `2`. The completed RAG trace was available and reported normalized/effective mode `project`, boundary `same_user_same_project`, `widen_reason=none`, `retrieval_absence_reason=retrieval_no_candidates`, zero semantic/thread-semantic/memory/graph/document hits, and an empty `contributing_items` list. The retrieval plan's primary scope was local and its escalation order was `thread_messages`, `thread_semantic`, `project_docs`, `adjacent_local`. The observed project boundary excluded the imported conversation in project `2`, even though it was the same account and a pre-chat vector search found the evidence. This ordinary completion did not select A's imported assistant message.

The capture sidecar observed one actual `POST /v1/chat/completions`, status 200, model `local-chat`, correlated by request ID `goal06-natural-a-66306ab33d`, task ID `8db1eedd-7a93-40b8-ac92-5dbfe16bb96f`, and attempt ID `attempt_ac839b1bf53b45aab2d9ebefabfbaeec`. The request-body SHA-256 was `76e0d4f5bc071a3704daf8f30ce80c93977c36cb3290a389ffd60c3430d222d2`. A sanitized request excerpt was `messages=[{role: system, content: "=== BASE SYSTEM === [omitted]"}, {role: user, content: "Can you remind me of the calibration code I recorded for the Argo observatory?"}]`; the two roles were the complete message list. The imported A sentinel `ORBIT-A00C423CB4` and source-message text were absent. The captured local provider response matched the assistant text persisted in PostgreSQL and returned by normal thread readback:

> I don't have access to any recorded calibration codes or specific data regarding the Argo observatory in my memory. If you have a specific document, file, or previous conversation where we might have discussed this, feel free to share those details, and I can help you look through them or organize them.

The task lifecycle endpoint `/chat/threads/3/tasks` returned task `8db1eedd-7a93-40b8-ac92-5dbfe16bb96f` in terminal state with event `task.completed`. Assistant persistence and readback therefore passed, but the answer was unsupported by the imported evidence and did not contain the requested synthetic code.

## Stage results

| Stage | Result | Evidence and failure boundary |
|---|---|---|
| Isolated Goal 05 source/runtime and supported local-only profile | PASS | Exact source SHA, fresh project database/queues/volumes, migration head, local profile, shared Chroma path, and local embedding model verified. |
| Authenticated synthetic account imports | PASS | Two HTTP-created jobs completed through the real account-import worker; four ordered canonical messages retained owner and source provenance. |
| Embedding readiness and account-scoped candidate availability | PASS | Four canonical messages `ready`; real Chroma search returned A's sentinel to A and zero A-namespace hits to B. |
| Account A normal chat selected imported evidence | FAIL | Requested `personal_knowledge` became effective `project`; trace had zero semantic candidates and no contributing items, despite A's pre-chat vector candidate. |
| Selected evidence injected into executed provider request | FAIL | Correlated provider input had only system and user messages; A's sentinel and imported source text were absent. |
| Local provider execution and correlation | PASS | Actual `local-chat` request/response captured with matching request/task/attempt IDs; HTTP 200. |
| Evidence-supported answer and durable assistant persistence | FAIL | Provider answer and PostgreSQL/readback matched, but the answer disclaimed access to the fact and contained no imported sentinel. |
| Account B ordinary-chat negative control | BLOCKED / NOT RUN | Stopped after the positive A retrieval gate failed, per the explicit stop condition. The earlier B-filtered vector query is not provider-context isolation evidence. |
| Overall import-to-natural-recall acceptance | FAIL | Live normal chat did not select or inject the imported history. No account B live-chat claim is made. |

## Regression validation

The existing venv `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python` was used without installing or modifying dependencies. Tests ran from the disposable Goal 05 source archive unless stated otherwise.

| Command | Result |
|---|---|
| `pytest -v guardian/tests/test_context_broker_integration.py` from the proof worktree using its default interpreter | BLOCKED at collection: `ModuleNotFoundError: No module named 'fastapi'`. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/test_context_broker_integration.py` from the proof worktree with LFS pointer stubs | FAIL, 1 failed: expected the dummy semantic result but got an empty list. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/workers/test_chat_worker_completion_semantics.py` from the LFS-incomplete worktree | FAIL, 22 passed / 1 failed: one test tried to parse a model-profile LFS pointer as JSON. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/workers/test_chat_worker_provider_resolution.py` from the proof worktree | PASS, 11 passed. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/test_context_broker_integration.py` from `/private/tmp/codexify-goal06-src` | FAIL, 1 failed with the same empty-semantic-result assertion. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/workers/test_chat_worker_completion_semantics.py` from `/private/tmp/codexify-goal06-src` | PASS, 23 passed. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/workers/test_chat_worker_provider_resolution.py` from `/private/tmp/codexify-goal06-src` | PASS, 11 passed. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/core/test_context_broker_source_mode.py` from the archive | PASS, 3 passed. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/core/test_retrieval_user_isolation_and_widening.py` from the archive | PASS, 4 passed. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v tests/core/test_chat_completion_service_retrieval_plan.py` from the archive | PASS, 16 passed. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/test_auth.py` from the archive | FAIL, 2 failed: unauthenticated `/chat` expectations observed HTTP 200 and 422, respectively. |

No test or application source file was changed. The failing focused broker and auth suites remain visible; they are not masked by the live runtime result.

## Architecture and invariant assessment

The proof remains acceptance-only and aligned with ADR-004, ADR-005, ADR-013, ADR-069, ADR-081, and ADR-092, plus the Account Export + Restore Contract, chat runtime contract, and router decision table. PostgreSQL remained canonical; verified account scope controlled import and vector search; source metadata remained provenance; Chroma was treated as derived; no permanent personal fact was created; no cloud provider or authentication profile change was introduced. The runtime's requested-to-effective source-mode change is recorded as observed behavior, not reinterpreted or repaired here. No ADR, application implementation, current-state declaration, supported-profile declaration, or release claim changed. Release HOLD remains unchanged.

## Stop condition and smallest corrective slice

Qualification stopped after the positive account A completion because ordinary chat did not select the available imported evidence. Do not treat the B-filtered vector query as the required negative provider-context control. The smallest follow-up is to investigate why this authenticated chat request's requested `personal_knowledge` source mode resolved to effective `project`, then authorize a separate live qualification attempt after the contract path and regression failures are understood. No implementation repair or architecture decision is included in this proof.
