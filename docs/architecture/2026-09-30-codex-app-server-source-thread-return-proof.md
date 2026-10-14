# Codex App Server source-thread result return — 2026-09-30

## Classification

**`PROVEN_LIVE_RUNTIME`**, bounded to one read-only App Server v2 turn in isolated Guardian/Postgres/Redis infrastructure and a fresh-process delivery-only replay. Execution, durable source-thread return, and replay idempotency passed. This is branch-local proof, not supported-Compose qualification or a public release claim.

## Scope and prerequisites

- Branch: `docs/native-execution-channel-routing`.
- Starting HEAD: `e6cdbe6fa80f1901be6d063149d696f023f58053`; clean worktree before edits.
- Both `028f90340208b23e36a0b6a42eadf084b806afd8` and `e6cdbe6fa80f1901be6d063149d696f023f58053` are in ancestry; checks passed before editing and at closeout.
- ADR-093 remains **Proposed**. Aligned with ADR-003, ADR-020, ADR-048, and ADR-093; no ADR or identity semantics changed.
- The [September 29 proof receipt](./2026-09-29-codex-app-server-durable-round-trip-proof.md) remains unchanged historical evidence of the missing message.
- Runtime code changes are limited to `guardian/agents/store.py`, `guardian/core/delegation_service.py`, and `guardian/workers/delegation_worker.py`. Test changes are limited to the worker and Phase 3 delivery test files. Documentation changes are this receipt, the runtime contract, and operator manual. No schema/migration, executor, protocol registry, routing, Campaign Runner, composer, native-session reuse, Auto routing, or release-claim change; no push.

## Root cause and repair

The new worker normalized the executor result, persisted the completed `DelegationService` job/summary, and published `delegation.completed`, but never traversed Guardian's source-thread delivery seam. Calling the older `store_coding_result` unchanged would require unrelated legacy run/intent state. No such records were manufactured.

The smallest shared insertion/lookup primitive, `_store_source_thread_result`, was extracted from the established intent result-return path in `AgentStore`. Its original caller retains legacy guards, stale/cancelled suppression, message shape, and commit behavior. The new packet/job caller reuses that primitive, the existing message lookup, and the canonical bounded/sanitized renderer. Renderer identity display labels are adapted to Delegation/Task; no legacy identities or records are invented.

The deterministic key is `delegation:<delegation_id>:thread_result`. A Postgres `FOR UPDATE` lock on the existing delegation job serializes all delivery attempts through this seam. Persisted packet/job/summary identities are checked against the source thread/message and project/account ownership; conflicting source-ID aliases also fail closed. Thread/source/project rows are locked during validation and insertion. The assistant `coding_result` message and summary delivery metadata commit together. No uniqueness migration is needed for this transaction boundary. Direct out-of-band writers are not covered by a database uniqueness constraint on JSON metadata.

Ordering is executor return -> Guardian normalization -> existing terminal job/summary persistence -> source-thread delivery -> terminal publication. The existing job and summary persistence transactions remain separate; delivery requires both completed records. A missing accepted summary is reported as degraded delivery, never reconstructed from progress or raw transport. The repair does not close unrelated earlier terminal-persistence crash gaps.

`summary.metadata` separates `delivery_ok`, `delivery_status`, `delivery_reason`, `delivery_key`, `result_message_id`, and `visibility_status` from execution status. Failed delivery leaves inference completed and retains its normalized evidence. `DelegationService.deliver_completed_result(delegation_id)` retries only delivery; completed worker-task replay also bypasses executor resolution/inference. If storage is unavailable for the delivery receipt itself, the worker can return bounded degraded-delivery metadata without claiming it persisted. No new public retry endpoint is introduced.

Transcript content is built from the normalized summary, not raw protocol output. Canonical rendering bounds summary length and rejects hidden-context/credential text or source/task prompt echoes; the new caller additionally suppresses absolute worker paths and environment assignments. Extra metadata is a bounded identity whitelist. Native IDs remain subordinate; provider/model values are included only if safe and observed. Configured-only model identity and unknown funding are not promoted into actual-model or entitlement claims.

## Isolated live environment

- Host CLI: `codex-cli 0.153.3`; native interface: `app-server --stdio`, v2, sandbox `read-only`, worker timeout 180 seconds.
- Fresh `postgres:15` container `codexify-appserver-return-pg`, random loopback port `49861`, disposable database `codexify_proof` with trust auth on that loopback-only port.
- Fresh `redis:7-alpine` container `codexify-appserver-return-redis`, random loopback port `49863`, Redis DB `0`.
- Repository Alembic migrations reached head. Postgres and Redis were real services; no in-memory store/queue/publisher substituted.
- Setup, worker, ordinary readback, first-message verification, and delivery-only retry ran in separate Python processes with actual `GuardianDB`, `DelegationService`, Redis transport/events, and `delegation_worker.run_once`.
- Operator HTTP authorization/routes were not exercised; the permitted direct-service proof used isolated disposable records. Existing user runtimes/data were untouched.
- Only disposable proof containers were stopped after readback; their `--rm` configuration removed them. Temporary scripts and bounded readback files remain outside the repository.

## Authenticated model selection

A first-party App Server process completed `initialize`, `initialized`, and `model/list`. Its catalog reported `gpt-6-astra` with `isDefault=true`; other returned model tags were `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, and `gpt-5.5`; `nextCursor=null`. The probe exited with code `0` without starting an inference turn. This existing discovery method selected the model without guessing or using a public API catalog. Inventory can be cached; the live successful response establishes that this configuration worked at execution time.

Requested model: `gpt-6-astra`, using process-local `CODEXIFY_CODEX_BIN='codex -c model=gpt-6-astra'`. Global configuration was untouched. Persisted thread response reported configured model `gpt-6-astra`, evidence `configured_only`; actual per-turn model remains **unknown** (`actual_model_id=null`). Provider `openai` was **observed**; a specific endpoint was not established. Entitlement/funding remains **unknown**. No model-selection, inference-route, or entitlement behavior changed.

## Live identities

| Identity | Value |
| --- | --- |
| Disposable account | `appserver-proof-898f418db41b` |
| Packet | `0d8a180e-3228-4699-98f2-c25636b8428d` |
| Codexify request / delegation | `50e7d32a-0ab8-4c02-b344-03027a06df08` |
| Codexify task | `9fe0b10b-1e57-4620-afe1-99b81206f94b` |
| Project / source thread / source message | `1` / `1` / `1` |
| Result message | `2` |
| Delivery key | `delegation:50e7d32a-0ab8-4c02-b344-03027a06df08:thread_result` |
| Native Codex thread / session | `01a0f280-0d55-70c1-bec1-5dc5db83296f` |
| Native Codex turn | `01a0f280-0e7a-7640-9c06-2444c360e5cf` |

## Durable and transport evidence

| Boundary | Independent readback / bounded observation |
| --- | --- |
| Pre-execution persistence | Source account/project/thread/message committed; setup asserted packet and approved job existed in another SQLAlchemy session before Redis enqueue. |
| Before execution | Independent `psql` found exactly message `1`, thread `1`, role `user`, kind `chat`; message count `1`. |
| Enqueue | Redis delegation queue length `1`; successful created event `1790774847636-0`. |
| Worker consumption | Real worker returned `worker_dequeue=delegation_task`, `status=completed`, `token_present=true`, no error; post-worker queue length `0`. |
| Running event | `delegation.running` at `1790774873294-0`. |
| Terminal event | `delegation.completed` at `1790774882120-0`, with delivered result-message ID `2` in metadata. |
| Postgres completion | Job and summary both `completed`; job completed at `2026-09-30 13:28:01.957713+00:00`, summary completed at `2026-09-30 13:28:02.010919+00:00`. |
| Normalized result | Summary and `result.final_text` exactly `CODEXIFY_APP_SERVER_DURABLE_PROOF_2026_09_29`; original Codexify identities and subordinate native IDs recovered. |
| First source-thread return | Exactly one assistant `coding_result`, ID `2`, with source-message ID `1`, source-thread ID `1`, project ID `1`, and matching request/delegation/task/key/native lineage. Total thread count `2`. |
| Delivery posture | `delivery_ok=true`, `delivery_status=delivered`, `delivery_reason=null`, `visibility_status=result_posted`, `result_message_id=2`. |
| No fallback | Packet context, result, and message metadata retain `execution_interface=app_server`, channel/executor `codex`; persisted protocol contains initialization, native thread start, native turn start and completion. `65` protocol events, no truncation; no `codex exec`, Pi, or other executor observed. Executor files/routing are unchanged. |
| Replay without inference | Separate process called only `deliver_completed_result`; same message ID `2`, same key, one matching result, total count `2`. Native thread/turn IDs, event count, Redis events, and job/summary completion timestamps remained unchanged. |
| Fixture | `/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/codexify-appserver-proof-8a3v5myw` contained only `proof-token.txt`, deterministic token without trailing newline. Before/after SHA-256 `dc0da192dabdf5a0378958a4398f532b020653d606cb97c2379d949f7108c504` matched. |
| Process shutdown | Persisted `process_exit_code=0`, `shutdown_status=clean_exit`; no fixture changes. |

The assistant content was:

```text
## Guardian Delegation Result

**Status**: COMPLETED

**Delegation ID**: `50e7d32a-0ab8-4c02-b344-03027a06df08`

**Task ID**: `9fe0b10b-1e57-4620-afe1-99b81206f94b`

**Summary**: CODEXIFY_APP_SERVER_DURABLE_PROOF_2026_09_29
```

Counts were **`1 -> 2 -> 2`** (before execution, first delivery, fresh-process retry), with **one** assistant `coding_result` throughout replay. Postgres is durable authority; Redis only proves transport/visibility. Browser receipt/rendering was not exercised.

## Validation and commands

All required focused suites passed together: **69 passed, 2 warnings in 11.30 seconds**:

```bash
TEST_DATABASE_URL=<isolated-disposable-Postgres> .venv/bin/pytest -v tests/workers/test_delegation_worker.py tests/core/test_delegation_service.py tests/contracts/test_guardian_delegation_phase3_delivery_contract.py tests/core/test_codex_app_server_executor.py tests/core/test_codex_executor.py
```

Per-file results: worker **6**, service **8**, Phase 3 contract **39** (including all **14** existing legacy tests), App Server executor **11**, Codex executor **5**. New durable coverage proves fresh-session and concurrent idempotency, lineage/ownership failures, ambiguous aliases, nonterminal suppression, bounded content/sanitization, rollback after insertion failure and successful recovery, worker ordering and replay without executor invocation. A worker exception test preserves execution completion when delivery/readback raises.

Live command sequence, from the repository root:

```bash
git status --short --branch
git rev-parse HEAD
git merge-base --is-ancestor 028f90340208b23e36a0b6a42eadf084b806afd8 HEAD
git merge-base --is-ancestor e6cdbe6fa80f1901be6d063149d696f023f58053 HEAD
python3 /tmp/codexify_appserver_return_runner.py bootstrap
python3 /tmp/codexify_appserver_return_runner.py probe
python3 /tmp/codexify_appserver_return_runner.py setup
docker exec codexify-appserver-return-pg psql -U postgres -d codexify_proof -c 'select id, thread_id, role, kind from chat_messages order by id;'
python3 /tmp/codexify_appserver_return_runner.py worker
python3 /tmp/codexify_appserver_return_runner.py readback
PYTHONPATH=. .venv/bin/python /tmp/codexify_appserver_return_verify.py first
PYTHONPATH=. .venv/bin/python /tmp/codexify_appserver_return_verify.py replay
python3 /tmp/codexify_appserver_return_runner.py cleanup
python3 scripts/validate_docs.py
make PYTHON=.venv/bin/python docs
git diff --check
```

The temporary runner started fresh loopback-only Postgres/Redis containers using `docker run --rm`, discovered ports with `docker port`, checked `pg_isready`, and ran `.venv/bin/alembic -c backend/alembic.ini upgrade head` against the fresh database. It invoked the setup/worker/readback harness in separate `.venv/bin/python` processes with isolated database/Redis bindings. The read-only verification script asserted message shape, content, exact safe lineage, completed summary, native identity, and delivery receipt. In its replay phase it called the service delivery seam, then asserted unchanged message/native/event/timestamp evidence against the first-phase saved readback. Scripts and JSON evidence stayed under `/tmp`; no credentials/auth material were copied into this receipt.

Additional lint check (`.venv/bin/ruff check` on the five touched Python/test files) reported **22 existing findings**. A per-file comparison against starting HEAD normalized shifted line numbers and proved **no introduced findings** (baseline/current: store 5/5, service 2/2, worker 5/5, Phase 3 tests 10/9, worker tests 1/1). Existing findings include duplicate legacy method definitions, unused imports/variables, import ordering, and broad exception warnings. They were not repaired outside this slice. The initial comparison falsely treated a shifted line number in a duplicate-definition message as a new finding; normalized comparison passed. Existing SQLAlchemy `MemoryRecord.project` overlap warnings occurred during live/test processes.

`python3 scripts/validate_docs.py` passed. `make PYTHON=.venv/bin/python docs` passed documentation validation and diagram freshness, with the existing duplicate-target Makefile warnings. `git diff --check` passed. Scope inspection found only the eight authorized implementation/test/documentation files listed above modified; `tests/core/test_delegation_service.py` required no changes. No full backend suite was run; executor protocol/routing and schemas were unchanged.

## Documentation and limitations

`delegation-runtime.md` now records the bounded completed result-return implementation/proof and supersedes the historical missing-return posture. `delegation-operator-manual.md` explains separate execution/delivery status and the safe delivery-only service retry. September 29 evidence and `00-current-state.md` remain unchanged.

This closes successful completed-result return and deterministic retry through Guardian's delivery seam. It does not qualify failed/cancelled result UX, all deployment environments, HTTP authorization, browser/event receipt, public support, session reuse, generalized routing, or recovery of an absent normalized terminal summary. No new schema, enum/protocol token, executor, legacy run/intent, transcript store, or release promise was introduced.
