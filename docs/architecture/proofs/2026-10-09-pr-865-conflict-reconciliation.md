# PR #865 conflict reconciliation and focused integration proof

Date: 2026-10-09

Evidence class: focused local code and test proof; no release qualification.

## Merge custody

PR: https://github.com/Resonant-Jones/Codexify/pull/865

The repair preserves PR head `208b84c92b944fe6a03a58c05ca8a1f4427fb872` and merges main `4939e2881c884073f5b820f281d9e322558349f1`. It resolves the twelve conflicted files without replacing either history. The PR's other checkout was not edited. Publication targets only `codex/chat-postgres-terminal-deadline-20261003`; main and deployment are outside this repair.

## Changes and governing contracts

- Preserve account-scoped project selection and route initialization in GuardianChatWithSidebar, alongside durable terminal message refresh.
- Preserve lazy VectorStore construction and immutable accepted-work admission. Optional document embeddings remain deferred; explicitly required embeddings initialize in the bounded child before intake.
- Reconcile the two Alembic lineages with no-op merge revision `2e865c4a9b10`, parents `f1a6d83b9024` and `17b23052da6a`. Regression tests prove upgrade traversal from either installed lineage.
- Remove committed conflict markers from current-state and two knowledge-graph JSON nodes. Preserve historical runtime proof links, refresh exact content hashes, and mark graph freshness stale pending full anchor review.
- Forward the immutable accepted deadline through all five non-local non-streaming provider dispatches. Read the complete response inside owned cancellable HTTP I/O, close it before returning, and retain existing provider parsing.
- Find an active durable attempt beyond the newest 100 receipts through at most three older pages per poll. Advance the cursor between polls and discard results after identity/lifetime changes.
- Replace 50 ms idle RPOP polling with one-second BRPOP under an owned two-second physical transport bound.
- Update integration fixtures for current lazy embeddings, durable task authorization, bounded stream reads, account-scoped project selection, and the canonical migration head.

ADR-087 governs the accepted 720-second work and 60-second terminalization envelope. ADR-091 governs durable completion-attempt authority. ADR-069 governs the release interpretation. These fixes conform to those contracts and require no new ADR. PostgreSQL remains durable authority; Redis and UI observations do not become authorization or completion authority. Non-local HTTP targets remain subject to existing egress policy. No cloud-provider support claim is added.

## Repair files

The merge also includes main's already committed changes. The directly reconciled or additionally repaired files are:

- `docs/architecture/00-current-state.md`, `docs/architecture/README.md`
- `docs/knowledge-graph/nodes/codexify:doc:architecture:current-state.json`, `docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json`
- `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` and its `__tests__/GuardianChatWithSidebar.mobile-nav.test.tsx`
- `frontend/src/features/chat/components/ThreadAttemptObservation.tsx` and `__tests__/ThreadAttemptObservation.test.tsx`
- `guardian/core/ai_router.py`, `guardian/core/accepted_deadline_transport.py`
- `guardian/vector/store.py`, `guardian/workers/document_embed_worker.py`, `guardian/queue/document_embed_queue.py`
- `guardian/db/migrations/versions/2e865c4a9b10_merge_chat_deadlines_and_campaign_authority.py`
- `tests/migration/test_agent_extension_schema_consistency.py`, `test_alembic_revision_uniqueness.py`, `test_d6_compatibility_bridge.py`, `test_github_watchdog_review_attempts.py`, `test_github_watchdog_review_dispatches.py`, `test_github_watchdog_review_input_snapshots.py`, `test_github_watchdog_review_results.py`
- `tests/core/test_cloud_accepted_deadline.py`, `tests/queue/test_document_embed_bounded_dequeue.py`, `tests/queue/test_chat_redis_deadline.py`
- `tests/routes/test_chat_task_event_stream_bounds.py`, `tests/identity/test_task_event_stream_authorization.py`, `tests/vector/test_vector_accepted_work_admission.py`
- `tests/workers/test_document_embed_worker.py`, `tests/workers/test_document_worker_shutdown.py`
- This proof record.

## Validation

Backend commands use `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest`, from the repair repository root, with `-q -o addopts='' --tb=short`.

| Surface | Tests / command | Result |
| --- | --- | --- |
| Migration graph, vector resolution, document lifecycle | Six migration modules listed below, `tests/vector/test_vector_store_resolution.py`, and both document worker modules | 48 passed |
| Accepted-work admission, Redis deadline, stream bounds and authorization | `tests/vector/test_vector_accepted_work_admission.py tests/queue/test_chat_redis_deadline.py tests/routes/test_chat_task_event_stream_bounds.py tests/identity/test_task_event_stream_authorization.py` | 107 passed |
| Final document shutdown, lifecycle and bounded intake | `tests/workers/test_document_worker_shutdown.py tests/workers/test_document_embed_worker.py tests/queue/test_document_embed_bounded_dequeue.py` | 26 passed |
| Provider bounds, success parsing and router compatibility | `tests/core/test_cloud_accepted_deadline.py tests/core/test_ai_router.py` | 52 passed |
| Frontend receipt projection and account-scoped shell | Vitest command below | 143 passed across six suites |
| Documentation | `python3 scripts/validate_docs.py` | Passed |
| Scoped whitespace | `git diff origin/main --check` | Passed |
| Reconciled graph nodes | JSON parsing, Draft 2020-12 schema validation, exact referenced content-hash comparison | Passed; freshness explicitly stale |
| Python syntax and scoped Ruff | `compileall` and Ruff on changed Python files; ai_router checked with inherited F811 excluded | Passed with inherited exception below |

The first migration group includes `test_alembic_revision_uniqueness.py`, `test_d6_compatibility_bridge.py`, and the four `test_github_watchdog_review_*` modules under `tests/migration/`.

Frontend command from root:

```sh
pnpm --dir frontend/src exec vitest run --config vitest.pr865.config.ts --configLoader runner --reporter=dot features/chat/components/__tests__/ThreadAttemptObservation.test.tsx components/persona/layout/__tests__/GuardianChatWithSidebar.stability.test.tsx components/persona/layout/__tests__/GuardianChatWithSidebar.terminal-projection.test.tsx components/persona/layout/__tests__/GuardianChatWithSidebar.mobile-nav.test.tsx components/persona/layout/__tests__/AppShell.test.tsx components/sidebar/__tests__/useProjectsCache.test.tsx
```

The temporary Vitest config copied the repository config, provided `__dirname` for the runner loader, and redirected cache to `/private/tmp`; it was removed before commit. Installed dependencies were reused through temporary symlinks without editing the other checkout. Git LFS manifests were materialized for validation without source changes.

Earlier combined checks exposed stale integration fixtures; those were corrected and affected checks rerun. A combined provider/worker run reported two worker readiness timeouts; both probes passed individually, and the full final worker group passed. The first new success-response assertions incorrectly assumed all providers return a `.text` attribute; assertions now use the canonical result normalizer. Existing SQLAlchemy relationship and React act warnings remain.

## Limits and documentation follow-through

Current-state and the reconciled graph nodes were updated. Existing historical proof records remain scoped to their recorded revisions. No fresh supported-Compose, live PostgreSQL migration, live cloud endpoint, desktop distribution, or candidate-adoption qualification was performed; the release gate remains HOLD.

Full graph validation (`python3 scripts/knowledge_graph/validate_and_generate_dlg.py validate`) still reports the pre-existing ADR-index content-hash mismatch and six broken-link warnings. That mismatch was verified in origin/main. Ruff F811 reports a duplicate `normalize_completion_output` definition inherited from the PR head; this repair does not refactor that separate defect. Cached whitespace checking also sees inherited Markdown trailing spaces from main; the PR diff against main passes.

Recommended KB follow-up: a full anchor/freshness audit of current-state, KB entrypoint and ADR-index. That audit and broader release qualification are deferred beyond this conflict repair. The merge commit hash is supplied in task closeout and PR metadata rather than embedded recursively in this record.
