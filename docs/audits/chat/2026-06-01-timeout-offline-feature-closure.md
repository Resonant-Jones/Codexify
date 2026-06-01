# Timeout vs Offline Feature Closure

## Scope

This closes the scoped timeout-vs-offline proof arc for provider first-output
timeout semantics across backend classification, runtime tokens,
registry/catalog-adjacent validation, frontend presentation, GuardianChat test
coverage, synthetic slow-provider proof, and retry/replay linkage proof.

This is a docs-only checkpoint. It does not change runtime behavior, frontend
behavior, provider policy, timeout defaults, supported profiles, protocol
tokens, database schema, migrations, Obsidian behavior, or release posture.

## Closure Verdict

Verdict: `COMPLETE FOR CURRENT FEATURE SCOPE`

Future durable attempt IDs, first-class replay semantics, or browser-level
proofs are hardening work. They are not blockers for this scoped
timeout-vs-offline arc.

## Repository Safety

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD commit before edit:
  `73dcfb12c075edf4487abc153cae0e822d6717bf`
- Dirty/untracked files before edit: none; `git status --short` was empty.
- Git root matched `/Volumes/Dev_SSD/Codexify-main`; the `codexify.space`
  checkout was not touched.

Recent commit surface verification:

- `3dff6c5ffd08e97e92f52e08cd80781e5a79e8c0` changed provider first-token
  timeout classification surfaces:
  - `guardian/core/ai_router.py`
  - `guardian/workers/chat_worker.py`
  - `tests/core/test_ai_router.py`
  - `tests/routes/test_health_endpoints.py`
  - `tests/workers/test_chat_worker_first_token_timing.py`
  - `tests/workers/test_chat_worker_lifecycle_events.py`
  - `tests/workers/test_chat_worker_streaming_chunks.py`
- `4c0440299b58f9b59266ae8824612e4ade4ae001` added only
  `docs/audits/chat/2026-05-30-provider-first-token-timeout-containment-review.md`.
- `ffff2f30788e326fa43e5d4594c686e603833a87` changed provider/runtime token,
  router, health, worker, and focused token/provider tests:
  - `guardian/core/ai_router.py`
  - `guardian/protocol_tokens.py`
  - `guardian/routes/health.py`
  - `guardian/workers/chat_worker.py`
  - `tests/contracts/test_protocol_tokens.py`
  - `tests/core/test_ai_router.py`
  - `tests/workers/test_chat_worker_first_token_timing.py`
- `e500ac1ec80e28290111e35b9c5cb596c4284a96` repaired provider
  registry/catalog token coverage in:
  - `guardian/core/provider_registry.py`
  - `guardian/tests/core/test_provider_registry.py`
  - `tests/routes/test_llm_catalog.py`
- `52cba4819280a99f7fc0be5357bcbbce7c3bc3a3` updated only
  `docs/audits/chat/2026-05-30-provider-tokenization-containment-review.md`.
- `bc33d1de01fe1b4648833fdd9858f033c8d383e2` changed frontend runtime-token,
  request-failure presentation, chat component, hook, and focused test
  surfaces:
  - `frontend/src/contracts/__tests__/runtimeTokens.test.ts`
  - `frontend/src/contracts/runtimeTokens.ts`
  - `frontend/src/features/chat/ChatView.tsx`
  - `frontend/src/features/chat/GuardianChat.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.lifecycle-timing.test.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.offline-banner.test.tsx`
  - `frontend/src/features/chat/hooks/useInferenceRequestState.ts`
  - `frontend/src/features/chat/requestFailurePresentation.ts`
- `f66f8e50ff0c7eec75eb48fe1d330f9a76c95b66` added only
  `docs/audits/chat/2026-05-30-frontend-timeout-offline-containment-review.md`.
- `9dd9883da0b55962453a79256b97351265ea8003` repaired only GuardianChat
  frontend test fixtures:
  - `frontend/src/features/chat/__tests__/GuardianChat.catalog-options.test.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.lifecycle-latency.test.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.session-shortcuts.test.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.test.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.thread-config.test.tsx`
  - `frontend/src/features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx`
- `2ec2144cb9df605b7896402a6b667dfc7acd0aa4` added only
  `docs/audits/chat/2026-06-01-synthetic-slow-provider-warmup-proof.md`.
- `73dcfb12c075edf4487abc153cae0e822d6717bf` added only
  `docs/audits/chat/2026-06-01-retry-replay-linkage-proof.md`.

No reviewed commit showed vault files, raw note text, real vault paths,
supported-profile edits, database migrations, or release-truth widening.

## Commit Ledger

| Commit | Purpose | Role in this arc |
| --- | --- | --- |
| `3dff6c5ffd08e97e92f52e08cd80781e5a79e8c0` | Diagnose provider first-token timeout | Implemented structured backend provider timeout classification and worker failure evidence. |
| `4c0440299b58f9b59266ae8824612e4ade4ae001` | Add provider first-token timeout containment review | Proved the backend fix was contained and identified tokenization as follow-up. |
| `ffff2f30788e326fa43e5d4594c686e603833a87` | Tokenize provider timeout classifications | Canonicalized provider failure-kind and transport-classification values. |
| `e500ac1ec80e28290111e35b9c5cb596c4284a96` | Repair provider registry catalog token coverage | Isolated registry/catalog test environment leakage and extended canonical failure-kind usage to adjacent surfaces. |
| `52cba4819280a99f7fc0be5357bcbbce7c3bc3a3` | Update provider tokenization containment review | Superseded the original HOLD state after registry/catalog validation was repaired. |
| `bc33d1de01fe1b4648833fdd9858f033c8d383e2` | Fix frontend provider timeout presentation | Made frontend request-failure presentation show provider timeout as retryable/delayed rather than offline. |
| `f66f8e50ff0c7eec75eb48fe1d330f9a76c95b66` | Add frontend timeout offline containment review | Proved the frontend repair was contained and separated broader fixture drift from product behavior. |
| `9dd9883da0b55962453a79256b97351265ea8003` | Repair GuardianChat fixture drift | Restored the broad GuardianChat frontend test target as a useful regression gate. |
| `2ec2144cb9df605b7896402a6b667dfc7acd0aa4` | Add synthetic slow provider proof | Proved reachable-but-slow first-output timeout classification with a synthetic provider stub. |
| `73dcfb12c075edf4487abc153cae0e822d6717bf` | Add retry replay linkage proof | Proved explicit second-attempt linkage after a timed-out provider attempt. |

## What Converged

- Backend timeout classification now distinguishes reachable provider timeout
  after first-output wait from provider offline/unreachable conditions.
- Provider failure-kind and transport-classification vocabulary is canonicalized
  through protocol-token domains.
- Registry/catalog-adjacent validation now uses canonical provider failure-kind
  values without widening provider policy or catalog visibility.
- Frontend request-failure presentation maps structured timeout evidence to a
  retryable delayed-provider condition rather than provider offline.
- The broad GuardianChat fixture gate is green again after test fixture drift
  was repaired.
- Synthetic slow-provider proof passed with a reachable local stub that accepted
  the request and withheld first output past an isolated timeout.
- Retry/replay linkage proof passed for an explicit later attempt against the
  same authored source turn.

## Current Feature Claim

The current supported claim is:

- A reachable-but-slow provider first-output failure is classified as timeout
  rather than offline.
- Frontend presentation shows that state as a retryable timeout or delayed
  provider condition, not provider offline.
- A failed timeout attempt does not fabricate assistant output.
- An explicit later attempt can persist exactly one assistant reply linked to
  the same source turn.
- A true unreachable provider remains distinct from reachable timeout evidence.

This claim is bounded to the current backend/frontend/proof surfaces recorded
in the artifacts above. It does not convert route acceptance, provider health,
or task-event publication into proof of completion.

## What This Does Not Claim

- It does not claim automatic retry/replay behavior exists.
- It does not claim durable per-attempt database rows exist.
- It does not claim every timeout class is solved.
- It does not claim browser end-to-end proof was performed.
- It does not claim full real-vault proof.
- It does not claim cloud-provider beta support.
- It does not claim release posture was widened.

## Remaining Future Hardening

- Durable per-attempt database rows for stronger attempt forensics.
- First-class replay semantics if retry/replay becomes product behavior rather
  than an explicit second-attempt proof path.
- Browser end-to-end proof if human-visible browser behavior becomes a release
  gate.
- Broader provider warmup taxonomy only if repeated live evidence shows a
  missing class beyond the current timeout/offline distinction.
- Metadata-key formalization only if task-event metadata becomes a formal
  schema rather than stable payload evidence.

## Optimization Boundary

More work on this feature is optimization unless it unlocks a new domain, fixes
a new observed failure, or turns future hardening into an explicitly approved
architecture task.

The next recommended domain move is branch synchronization before release
claims, or a new scoped feature branch for the next independently provable
runtime surface.

## Current-Truth Anchors Preserved

- Local-first beta posture remains unchanged.
- The supported path remains local Docker Compose.
- Provider runtime state and per-message request state remain distinct.
- Source-thread transcript truth is preserved.
- Obsidian retrieval semantics were untouched by this closure task.
- Command bus and MCP separation were preserved.

## Real-Vault Safety

- No real-vault indexing was run.
- No vault contents were read, printed, summarized, or committed.
- No vault files were committed.

## Validation

Docs-only validation for this closure checkpoint:

- `python3 scripts/validate_docs.py`: passed.
- `git diff --check`: passed.

Runtime and frontend tests were not rerun for this docs-only checkpoint. The
implementation and proof artifacts in this arc already record their focused
runtime/frontend validation.

## Final Status

`CLOSED`

Feature completion estimate: `100% for current scoped timeout-vs-offline arc;
future hardening remains optional and separately scoped.`
