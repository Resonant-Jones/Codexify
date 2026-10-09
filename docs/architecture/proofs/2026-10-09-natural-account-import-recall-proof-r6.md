# Natural Account Import-to-Recall Proof (R6)

**Result: BLOCKED before the live-chat gate.** The repository code path supports a normal account-scoped retrieval attempt, but this run did not execute a live import-to-chat completion. No provider-context, persisted-answer, or negative-control result is claimed. Release posture remains **HOLD**.

## Source and environment

- Source: `7e8f0c284b0a9ddf284c5582cf8d3309852ea1e7`, branch `codex/synthetic-account-import-recall-qualification`.
- Checkout: `/Volumes/Dev_SSD/offload/codex/worktrees/synthetic-import-recall/Codexify-main`; initially clean. It is 8 commits ahead and 124 commits behind the locally available `origin/main` ref; merge base `187573380270683816da9b3dcc0d4c2433b75a4e`. This qualification uses the task-designated Goal 05 source, not a claim that it is current main.
- Runtime resources: Docker was available (4 CPUs, about 7.75 GiB memory), with unrelated active Compose projects. None were stopped, altered, or reset. No Goal 06 services, volumes, or fixtures were created.
- Test interpreter: existing `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`; no dependency installation or environment mutation. Direct `pytest` from the isolated checkout could not import FastAPI; the existing main-checkout venv supplied dependencies for the focused test attempts.
- Checkout completeness: `git lfs status` reported 809 LFS objects to be committed/pushed, with no locally available LFS payloads in the checkout. Five `config/whooshd/model-profiles/*.json` inputs are LFS pointer text. The focused completion test failed while parsing one such pointer as JSON. The task-owned runtime image and supported-profile configuration could not be treated as a reproducibly complete source environment, so live execution was stopped before creating/importing synthetic records.

## Scope and synthetic data

No Goal 06 fixture data was created or imported. No private archive was accessed. Goal 05's prior synthetic import/embedding proof is supporting evidence only; it does not satisfy this proof's provider-context or answer gates.

## Code-path trace (inspection only)

The inspected path is consistent with the existing contracts:

1. `POST /api/chat/threads` and the normal authored-message route establish the account-authorized chat thread and user turn.
2. `POST /api/chat/{thread_id}/complete` accepts `source_mode` and `depth_mode`; `personal_knowledge` with `normal` is the intended retrieval posture for this test. The route resolves thread execution authority and queues the ordinary completion.
3. `ContextBroker._search_with_widening` first queries the active thread namespace with the resolved `user_id`, then may widen to that user's candidate threads according to the retrieval policy. Broker aggregation filters results against the resolved owner. `router-decision-table.md` requires every retrieval operation to be scoped by `user_id`.
4. `chat_completion_service` builds retrieval context/provenance and appends `retrieved_context_messages` to `messages_for_llm` before invoking the provider. The chat worker performs the normal provider call and persists the assistant result through the canonical chat path.
5. The route exposes a latest RAG trace readback. Trace/code presence alone does not prove that a specific source was selected, included in the executed provider request, or used in a persisted answer.

Relevant inspected files: `guardian/routes/chat.py`, `guardian/context/broker.py`, `guardian/core/chat_completion_service.py`, and `guardian/workers/chat_worker.py`. This is a source trace, not executed retrieval evidence.

## Validation results

Commands ran from the isolated checkout, using the existing venv and `PYTHONDONTWRITEBYTECODE=1`:

| Command | Result | Evidence / boundary |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/test_context_broker_integration.py` | FAIL, 1 failed | `test_context_broker_assemble_integration`: expected the dummy semantic result but received an empty semantic list. No application source was changed. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/workers/test_chat_worker_completion_semantics.py` | FAIL, 22 passed / 1 failed | `test_explicit_provider_failure_does_not_rescue` reached `WhooshdModelProfileError` because `config/whooshd/model-profiles/gemma-4-12b-it-optiq-4bit.json` contains a Git LFS pointer, not JSON. |
| `PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v guardian/tests/workers/test_chat_worker_provider_resolution.py` | PASS, 11 passed | Focused provider-resolution surface only. |
| `pytest -v ...` using the default interpreter | BLOCKED | Collection failed because `fastapi` is not installed in that interpreter. |

No new integration test was added. The existing Goal 05 live integration suite remains evidence for import and embedding only; it does not cover normal chat recall.

## Gate ledger

| Gate | Classification | Exact boundary |
|---|---|---|
| Goal 05 synthetic import and embedding prerequisite | PASS (prior proof only) | Prior artifact records real account import, canonical readback, embedding readiness, and account-scoped vector observations. Not repeated here. |
| Normal-chat retrieval selection | BLOCKED | No isolated Goal 06 runtime was started; no completion attempt or retrieval trace exists. |
| Executed provider-context inclusion | BLOCKED | No provider request was executed or captured. Vector searchability and source-code assembly are insufficient evidence. |
| Persisted assistant answer | BLOCKED | No ordinary chat completion was run; no assistant readback exists. |
| Cross-account provider-context negative control | BLOCKED | Not attempted because the positive account's complete provider-context and persisted-answer gates were not established. |
| Goal 06 live end-to-end acceptance | BLOCKED | Required reproducible source/runtime prerequisite is missing: local LFS model-profile payloads, plus successful focused broker/completion test results. No live pass is claimed. |

The failure boundary is before synthetic fixture creation and before chat execution. There are no Goal 06 job, batch, thread, message, vector, retrieval, provider, or assistant-answer evidence identifiers to report.

## Governing architecture and invariants

This acceptance-only proof is aligned with ADR-004 (retrieval policy as control plane), ADR-005 (runtime mode and account boundary), ADR-013 (verified personal-facts context injection), ADR-069 (Beta runtime support boundary), ADR-081 (canonical Project account authority), and ADR-092 (purpose-scoped credentials), together with the Account Export + Restore Contract, chat runtime contract, and router decision table. No contract semantics or implementation changed. Postgres remains canonical; import metadata remains provenance; authenticated account scope remains the authority; vector presence is not provider-context proof; imported conversations are not promoted to durable personal facts. Release HOLD is unchanged.

## Future qualification procedure and prerequisites

Use a complete isolated checkout of the designated source revision with its required LFS objects available, then rerun the focused broker and completion suites. Create a fresh task-owned Compose project, database, queue, app-data, and vector volume; do not reuse or reset existing project state. Import only synthetic fixtures through the ordinary authenticated account-import route and workers, verify canonical ownership/provenance and embedding readiness, then run one ordinary `personal_knowledge` / `normal` chat for account A. Capture the retrieval trace, selected source lineage, exact executed provider input with credentials redacted, provider response, and canonical assistant readback. Only after all positive gates pass, run the equivalent account B negative control and verify A's source text is absent from both selected evidence and provider input. Clean up only the exact task-owned resources.

Natural recall may be classified PASS only when selected imported evidence appears in the executed provider request, an appropriate answer is persisted, and the second-account negative control excludes the first account's evidence. None of these live gates passed in this run.
