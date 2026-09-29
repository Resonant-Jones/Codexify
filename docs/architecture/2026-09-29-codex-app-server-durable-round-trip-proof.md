# Codex App Server durable round-trip proof — 2026-09-29

## Classification

**`NEXT_PROOF_NEEDED` at source-thread result return.** One authenticated Codex App Server v2 turn completed through the real Guardian delegation service, Redis queue, `delegation_worker.run_once`, and Postgres-backed terminal summary. The response was durably recovered and contained the exact proof token. The source Codexify Thread still held only its original user message after completion; no result message was injected into that thread. The [Delegation Runtime Contract](./delegation-runtime.md) identifies result injection as missing. This proof therefore does not claim a complete source-thread round trip or public runtime support.

## Scope and starting state

| Item | Observed value |
| --- | --- |
| Branch | `docs/native-execution-channel-routing` |
| Starting HEAD | `028f90340208b23e36a0b6a42eadf084b806afd8` (`Prove Codex App Server execution`) |
| Implementation ancestry | Starting HEAD is the implementation commit; `git merge-base --is-ancestor 028f90340208b23e36a0b6a42eadf084b806afd8 HEAD` passed. |
| Worktree before proof | Clean (`git status --short` produced no paths). |
| ADR-093 | Present and **Proposed**; no ADR status change. ADR-048 remains the accepted authority boundary. |
| Codex CLI | `codex-cli 0.153.3` |
| Date | 2026-09-29 EDT (2026-09-29 UTC for persisted timestamps) |

This was a branch-local, verification-only run aligned with ADR-003, ADR-020, Accepted ADR-048, and Proposed ADR-093. It did not use the supported Compose qualification profile and does not change [`00-current-state.md`](./00-current-state.md), Beta, or release claims.

## Isolated runtime and model selection

The proof used fresh, disposable `postgres:15` and `redis:7-alpine` containers, each published only on a random `127.0.0.1` port. Repository Alembic migrations reached `head` in that Postgres database. A fresh Python process using `GuardianDB` and `DelegationService` created the account, project, thread, message, packet, and job. The actual `redis_queue.enqueue` helper accepted the task; `delegation_worker.run_once` consumed it in a separate process; a third process independently read Postgres and Redis. Neither an in-memory delegation store nor an in-memory Redis/event substitute was used. The route handler and HTTP authorization layer were not exercised; the task's permitted direct-service path was used.

The authenticated first-party Codex App Server `model/list` response contained `gpt-6-astra` with `isDefault=true`. That inventory, rather than a public API model catalog or a guessed tag, selected the model. The worker used an ephemeral `CODEXIFY_CODEX_BIN='codex -c model=gpt-6-astra'` override; global Codex configuration was not edited. The resulting native `thread/start` response reported configured model `gpt-6-astra` and provider `openai`. The successful turn shows that the authenticated runtime accepted that configuration. The App Server did not emit per-turn model identity evidence, so **actual model identity remains unobserved** (`configured_only`), despite the successful response.

| Identity dimension | Durable evidence |
| --- | --- |
| Execution channel | `codex` (`result.execution_channel` and `executor_id`) |
| Execution interface | `app_server` in packet context and normalized result/metadata; App Server v2 native IDs were returned. No `codex exec`, Pi, or other harness fallback was observed. |
| Requested model | `gpt-6-astra`, selected from authenticated `model/list` and applied as a process-local CLI configuration override. |
| Configured model | `gpt-6-astra`, from `thread/start`; evidence status `configured_only`. |
| Actual per-turn model | `unknown`; no `model/rerouted` or other actual-model signal was emitted. |
| Inference route | Provider ID `openai`, observed in `thread/start`. No more specific inference endpoint was established. |
| Funding / entitlement route | `unknown`; the App Server exchange did not establish who funds or owns the entitlement. |

The App Server sandbox remained `read-only`; the worker's proof timeout was 180 seconds. Native-session resume, Auto routing, composer selection, and Campaign Engine integration were outside this run.

## Fixture and identifiers

The disposable workspace contained exactly one file, `proof-token.txt`, whose bytes were `CODEXIFY_APP_SERVER_DURABLE_PROOF_2026_09_29` with no trailing newline. The delegated prompt requested that Codex read the file, return the exact token, make no file changes or commit, and avoid unrelated work.

| Identifier | Value |
| --- | --- |
| Disposable account | `appserver-proof-df4adfead388` |
| Codexify project | `1` |
| Codexify source thread | `1` |
| Codexify source message | `1` |
| Packet | `c1a38c3c-e270-4f92-af35-8aad5a9f2ae8` |
| Codexify request / delegation | `a6ae8733-7dfa-4bcc-858b-0799a6b91596` |
| Codexify task | `7e9d512f-701f-4cec-af2b-1cb605345ba7` |
| Native Codex thread / session | `01a0ef18-aee1-7172-8596-3d186fbae119` |
| Native Codex turn | `01a0ef18-afa2-7ed1-af77-10214e199ba6` |

The native IDs were stored in the normalized result and metadata under the Codexify delegation and task IDs. They did not replace the Codexify Thread identity.

## Transport, worker, and durable readback

| Boundary | Evidence |
| --- | --- |
| Pre-execution persistence | The Postgres packet and job existed before worker consumption; the job was marked `queued`. |
| Redis enqueue | `codexify:queue:delegation` length was `1` immediately after `enqueue`; `delegation.created` stream event ID was `1790717739549-0`. |
| Worker dequeue | A separate non-pytest process called the real `delegation_worker.run_once`, returned `worker_dequeue=delegation_task`, and ended `completed`; queue length afterward was `0`. |
| App Server execution | Normalized result recorded `execution_channel=codex`, `execution_interface=app_server`, protocol `v2`, native thread and turn IDs, and 74 bounded protocol events without truncation. |
| Native final response | Exactly `CODEXIFY_APP_SERVER_DURABLE_PROOF_2026_09_29`; Guardian worker status `completed`, no error. |
| Terminal event | Redis stream contained `delegation.running`, progress events, and terminal `delegation.completed` at `1790717777348-0` with status `completed`. |
| Postgres terminal state | Fresh-process readback found source thread, source message, packet, job, and summary. Job status and summary status were `completed`; job `completed_at=2026-09-29T21:36:17.616292+00:00`; summary `completed_at=2026-09-29T21:36:17.650538+00:00`. |
| Durable lineage | Summary recovered request/delegation/task IDs above, `thread_id=1`, `source_message_id=1`, `project_id=1`, and `executor_id=codex`. Packet context recovered `source_message_id=1` and `execution_interface=app_server`. |
| Durable result | Summary `summary` and nested `result.final_text` both recovered the exact token; nested result retained the native IDs, configured model, provider evidence, unknown funding posture, and clean shutdown. |
| Source-thread return | **Missing:** independent readback found one message in thread `1`, role `user`; no assistant/result message was added. The normalized delegation summary is durable but was not injected into the source thread. |
| Fixture integrity | SHA-256 before and after: `dc0da192dabdf5a0378958a4398f532b020653d606cb97c2379d949f7108c504`. Directory still contained only `proof-token.txt`. |
| Native process shutdown | `process_exit_code=0`, `shutdown_status=clean_exit`. |

Postgres was the authority for the terminal result and lineage. Redis proved queue transport and event visibility only. The source-thread message gap is the precise missing result-return boundary; this task did not add an injection mechanism.

## Commands and validation

The following is the executed command sequence, with the disposable Postgres connection string redacted. The temporary proof harness lived outside the repository at `/tmp/codexify_appserver_durable_proof.py`; its `setup`, `worker`, and `readback` phases called the repository's real `GuardianDB`, `DelegationService`, `redis_queue.enqueue`, `delegation_worker.run_once`, and `task_events` APIs. No runtime source file was edited.

```text
git status --short
git merge-base --is-ancestor 028f90340208b23e36a0b6a42eadf084b806afd8 HEAD
codex --version
codex app-server --help
python3 <temporary authenticated App Server JSON-RPC model/list probe>
.venv/bin/pytest -v tests/core/test_codex_app_server_executor.py tests/core/test_codex_executor.py tests/core/test_delegation_service.py tests/workers/test_delegation_worker.py tests/contracts/test_protocol_tokens.py
docker run --rm -d --name codexify-appserver-durable-proof-pg <isolated postgres:15 configuration>
docker run --rm -d --name codexify-appserver-durable-proof-redis -p 127.0.0.1::6379 redis:7-alpine
DATABASE_URL=<isolated Postgres DSN> .venv/bin/alembic -c backend/alembic.ini upgrade head
GUARDIAN_DATABASE_URL=<isolated Postgres DSN> REDIS_URL=redis://127.0.0.1:63168/0 PYTHONPATH=. .venv/bin/python /tmp/codexify_appserver_durable_proof.py setup
GUARDIAN_DATABASE_URL=<isolated Postgres DSN> REDIS_URL=redis://127.0.0.1:63168/0 CODEXIFY_CODEX_BIN='codex -c model=gpt-6-astra' CODEXIFY_CODEX_TIMEOUT_SECONDS=180 PYTHONPATH=. .venv/bin/python /tmp/codexify_appserver_durable_proof.py worker
GUARDIAN_DATABASE_URL=<isolated Postgres DSN> REDIS_URL=redis://127.0.0.1:63168/0 PYTHONPATH=. .venv/bin/python /tmp/codexify_appserver_durable_proof.py readback
```

The five focused suites passed together: **66 passed, 2 warnings, 2.51 seconds**. The live fixture processes also emitted the existing SQLAlchemy `MemoryRecord.project` relationship overlap warning; no runtime code was changed for it. `python3 scripts/validate_docs.py` passed. `make PYTHON=.venv/bin/python docs` passed both docs validation and diagram freshness, with the Makefile's existing duplicate-target warning. `git diff --check` passed. `git status --short` showed only this proof receipt and `delegation-runtime.md` changed.

## Next atomic proof or repair

Define and implement an idempotent Guardian-owned result-injection step that writes the normalized delegation summary into the original Codexify Thread with the original source-message, request, delegation, and task lineage. Then repeat independent Postgres readback of both the delegation summary and the new source-thread result message. That work needs a separate authorized implementation task and must preserve Guardian authority and the native-session subordination in ADR-048 and Proposed ADR-093.
