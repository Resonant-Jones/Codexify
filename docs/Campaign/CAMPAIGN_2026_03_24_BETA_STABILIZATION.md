

Task 1: Release composer/thread lock on all terminal paths

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Fix the chat composer/thread lock lifecycle so the active thread is always released when a turn terminates, regardless of whether the turn ends in success, error, timeout, dropped stream, aborted request, or provider switch.

Perform the described edit only in the specified files.

This change belongs in:
 • frontend/src/features/chat/... chat send/request lifecycle files
 • any shared chat state store/reducer used for in-flight composer locking
 • tests near existing GuardianChat/session/chat lifecycle coverage

Goal

The composer must not remain unusable after backend or stream failure.
The thread lock must be treated like a lease with deterministic cleanup, not a one-way gate.

Required behavior
 1. When a chat turn starts:
 • mark the thread/request as in-flight
 • disable composer as currently intended
 2. When a chat turn ends for any terminal reason:
 • success
 • backend error
 • network error
 • timeout
 • dropped SSE/stream
 • abort/cancel
 • provider switch while request is active
the composer lock must be cleared.
 3. If provider is changed during an active request:
 • current in-flight state must be unwound
 • composer becomes usable again
 • thread must not stay locked behind stale request state
 4. If the frontend has a “give up” or abort path, ensure it also clears:
 • thread lock
 • pending indicator
 • any request-scoped abort/controller handles
 5. Avoid double-unlock bugs:
 • cleanup should be idempotent
 • repeated terminal events must not throw or corrupt state

Files to modify

List all files before changes. Likely candidates include:
 • frontend/src/features/chat/...
 • frontend/src/features/chat/__tests__/...
 • any chat store/reducer file that owns in-flight state

Tests

Run the correct test suite based on scope:

pnpm test

Add or update tests for:
 • lock clears on successful completion
 • lock clears on backend error
 • lock clears on dropped stream / aborted request
 • provider change during active request clears lock
 • cleanup is idempotent

Git commands

If checks pass:

git add <modified files>
git commit -m "Release chat thread lock on all terminal states"

Output must include
 • Summary of changes
 • files modified
 • reducer/store/hooks/components touched
 • Test results
 • Git commit hash

⸻

Task 2: Default thinking mode to Fast and persist per thread

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Implement thread-scoped thinking mode persistence so FAST is the default for threads with no explicit selection, and the selected mode does not reset after each sent message.

Perform the described edit only in the specified files.

This change belongs in:
 • frontend/src/features/chat/... thinking mode UI/state files
 • any thread metadata/state persistence layer used by chat preferences
 • tests near existing GuardianChat catalog/session/profile coverage

Required behavior
 1. Default behavior:
 • new thread or thread with no stored mode defaults to FAST
 2. Allowed selectable modes:
 • FAST
 • AUTO
 • DEEP
or the repo’s exact canonical equivalents if naming differs
 3. After user selects a mode for a thread:
 • selection persists for that thread
 • sending a message must not reset it
 • re-rendering the composer must not reset it
 4. Switching threads:
 • each thread restores its own stored thinking mode
 • threads with no saved value still default to FAST
 5. Provider/profile integration:
 • if request assembly depends on thinking mode, ensure the persisted value is what gets sent
 • do not silently downgrade selected mode during normal submit flow
 6. Preserve future profile support:
 • this change should not block thread-level model/profile-specific overrides later

Files to modify

List all files before changes. Likely candidates include:
 • frontend/src/features/chat/...
 • any thread state model/store
 • tests for session tabs, shortcuts, catalog options, or chat preferences

Tests

Run:

pnpm test

Add or update tests for:
 • default mode is FAST
 • selection persists after submit
 • selection persists across re-render
 • thread A and thread B can hold different selections
 • restored thread without saved setting defaults to FAST

Git commands

If checks pass:

git add <modified files>
git commit -m "Persist thread thinking mode with fast default"

Output must include
 • Summary of changes
 • files modified
 • components/hooks/state touched
 • Test results
 • Git commit hash

⸻

Task 3: Reconcile frontend health polling to actual backend contract

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Remove or reconcile frontend polling of health endpoints that do not exist in the active backend contract. Frontend health checks must target real backend routes only.

Perform the described edit only in the specified files.

This change belongs in:
 • frontend health/polling/readiness code
 • any backend route declarations only if needed to align contract
 • tests covering offline banner, readiness checks, or health polling

Goal

Stop repeated polling of dead endpoints such as /api/health and /api/health/chat if those routes are not part of the current backend contract.

Required behavior
 1. Audit current frontend health polling targets.
 2. Replace or remove calls to nonexistent routes.
 3. Use only routes that currently exist, such as:
 • /api/health/llm
 • /api/health/embedder
 • other actual routes already implemented in repo
 4. If composite app readiness is required, compute it from valid route results only.
 5. Do not leave silent noisy 404 polling loops in place.
 6. If backend contract should include missing routes instead, implement that in a separate task. This task is for contract reconciliation, not speculative route expansion.

Files to modify

List all files before changes. Likely candidates include:
 • frontend polling/offline banner/readiness hooks
 • frontend API client files
 • related tests

Tests

Run based on scope:
 • Frontend-only:

pnpm test

 • If backend route tests are touched too, run both:

pytest -v
pnpm test

Add or update tests for:
 • no polling to removed/nonexistent endpoints
 • readiness banner behavior still works
 • health state derived from valid endpoints only

Git commands

If checks pass:

git add <modified files>
git commit -m "Align health polling with backend routes"

Output must include
 • Summary of changes
 • files modified
 • routes/hooks touched
 • Test results or explicit note if both suites were required
 • Git commit hash

⸻

Task 4: Restore thread deletion end to end

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Fix thread deletion so a user can delete conversations reliably from the UI and the deletion is reflected immediately in thread state.

Perform the described edit only in the specified files.

This change belongs in:
 • frontend thread list / thread actions UI
 • backend thread delete route/handler if needed
 • tests covering thread actions and thread persistence

Required behavior
 1. User can trigger delete from existing thread UI.
 2. The correct backend delete action is called.
 3. On success:
 • thread is removed from visible list
 • if active thread was deleted, UI transitions safely to a valid fallback state
 • composer is not left locked
 • stale deleted thread view is not retained
 4. On failure:
 • user receives clear error feedback
 • UI remains consistent
 • no phantom deletion in local state
 5. If deletion is blocked by active in-flight request:
 • either unwind request first or reject cleanly with clear UX
 • do not deadlock the thread UI

Files to modify

List all files before changes. Likely candidates include:
 • frontend/src/features/chat/...
 • backend thread routes/store if broken there
 • thread action tests

Tests

Run based on scope:
 • frontend-only:

pnpm test

 • if backend thread handlers are modified:

pytest -v
pnpm test

Add or update tests for:
 • delete succeeds and removes thread from UI
 • deleting active thread lands in safe fallback state
 • delete failure preserves consistent UI
 • thread lock is not stranded after delete flow

Git commands

If checks pass:

git add <modified files>
git commit -m "Fix thread deletion flow"

Output must include
 • Summary of changes
 • files modified
 • actions/routes/components touched
 • Test results
 • Git commit hash

⸻

Task 5: Restore project create/delete mutations

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Fix project mutation flows so users can create and delete projects reliably, with immediate and consistent UI updates.

Perform the described edit only in the specified files.

This change belongs in:
 • project management UI
 • frontend API client/state for project mutations
 • backend project create/delete handlers if needed
 • tests covering project CRUD

Required behavior
 1. GET /projects already works. Preserve that.
 2. Project create must:
 • call correct backend route
 • add created project into UI state
 • move to sensible selected/focused state if current UX expects it
 3. Project delete must:
 • call correct backend route
 • remove project from UI state immediately after success
 • safely handle deletion of currently selected project
 4. On create/delete failure:
 • show clear error feedback
 • do not leave ghost state in UI
 5. Avoid stale-cache issues:
 • list should reflect result without requiring full app reload

Files to modify

List all files before changes. Likely candidates include:
 • frontend project feature files
 • backend project route/store files
 • tests for project list and mutations

Tests

Run based on scope:

pytest -v
pnpm test

Add or update tests for:
 • create project success
 • create project failure
 • delete project success
 • delete selected project fallback behavior
 • delete project failure without ghost removal

Git commands

If checks pass:

git add <modified files>
git commit -m "Fix project create and delete flows"

Output must include
 • Summary of changes
 • files modified
 • handlers/components touched
 • Test results
 • Git commit hash

⸻

Task 6: Restore Docker-to-local Ollama accessibility

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Fix local Ollama provider connectivity from the Codexify runtime so “on-my-machine” Ollama is reachable from the app when running in Docker on macOS.

Perform the described edit only in the specified files.

This change belongs in:
 • provider configuration files
 • Docker compose / runtime env files
 • backend provider adapter/config resolution for Ollama
 • tests covering provider base URL resolution where available
 • docs if a runtime note is required

Goal

Vault node can remain separate. This task is specifically for the local-machine Ollama path.

Required behavior
 1. Determine the canonical local Ollama URL resolution path used by backend/provider config.
 2. Ensure Dockerized backend can reach host Ollama on macOS.
 3. Support a clear env-configurable base URL for local Ollama.
 4. If host bridge naming is required, implement deterministic fallback behavior appropriate for Docker Desktop on macOS.
 5. On failure, emit clear diagnostics rather than silent provider absence.
 6. Do not conflate local Ollama with remote vault-node Ollama.

Files to modify

List all files before changes. Likely candidates include:
 • docker-compose.yml or related compose/env files
 • backend provider config files
 • provider tests
 • relevant docs

Tests

Run based on scope:

pytest -v

If frontend provider catalog logic is also touched:

pnpm test

Also include a manual verification note in output:
 • local Ollama reachable from backend container
 • provider appears in catalog as expected

Git commands

If checks pass:

git add <modified files>
git commit -m "Fix local Ollama connectivity in Docker runtime"

Output must include
 • Summary of changes
 • files modified
 • config/provider logic touched
 • Test results
 • Manual verification result
 • Git commit hash

⸻

Task 7: Improve provider catalog completeness for Groq

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Fix Groq catalog enumeration so Codexify surfaces the full active model set returned by the provider, instead of only a narrow subset such as Kimi and Llama 3 70B.

Perform the described edit only in the specified files.

This change belongs in:
 • backend provider adapter/catalog normalization for Groq
 • frontend catalog rendering/filtering only if the backend already returns the models correctly
 • tests covering catalog enumeration and filtering

Required behavior
 1. Verify provider adapter reads the full provider catalog response.
 2. Ensure normalization does not discard valid models unintentionally.
 3. Ensure frontend does not hide valid Groq models due to stale filtering or hard-coded allowlists.
 4. Preserve safety/availability filtering only if intentionally specified in code and documented.
 5. Keep output deterministic and deduplicated.

Files to modify

List all files before changes. Likely candidates include:
 • backend provider catalog files
 • frontend catalog rendering/filter files
 • provider catalog tests

Tests

Run based on scope:

pytest -v
pnpm test

Add or update tests for:
 • multiple Groq models returned by adapter
 • normalization preserves valid entries
 • frontend renders returned models without unwanted filtering

Git commands

If checks pass:

git add <modified files>
git commit -m "Expand Groq catalog visibility"

Output must include
 • Summary of changes
 • files modified
 • provider/catalog logic touched
 • Test results
 • Git commit hash

⸻

Task 8: Harden Minimax and Alibaba provider failure handling

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Improve reliability and failure reporting for Minimax and Alibaba provider access so intermittent failures do not leave the chat loop or provider state ambiguous.

Perform the described edit only in the specified files.

This change belongs in:
 • backend provider adapters for Minimax and Alibaba
 • provider routing / timeout / retry policy files
 • tests covering provider error handling and catalog/request stability

Required behavior
 1. Audit current request path for both providers.
 2. Ensure timeouts and error handling are explicit and bounded.
 3. Differentiate:
 • auth/config failure
 • transport/network failure
 • provider timeout
 • provider returned error response
 • empty catalog / empty model result
 4. Ensure provider failures do not strand thread lock state upstream.
 5. Return diagnostics that the frontend can surface cleanly.
 6. Do not add broad speculative retries that amplify latency.

Files to modify

List all files before changes. Likely candidates include:
 • provider adapter files
 • routing/transport helpers
 • provider tests

Tests

Run:

pytest -v

If frontend provider error UI is changed too:

pnpm test

Add or update tests for:
 • timeout path
 • auth/config error path
 • transport failure path
 • provider error payload handling
 • deterministic surfaced diagnostics

Git commands

If checks pass:

git add <modified files>
git commit -m "Harden Minimax and Alibaba provider failures"

Output must include
 • Summary of changes
 • files modified
 • adapters/helpers touched
 • Test results
 • Git commit hash

⸻

Recommended execution order
 1. Task 1: composer/thread lock
 2. Task 2: thinking mode persistence/default
 3. Task 3: health polling contract cleanup
 4. Task 4: thread deletion
 5. Task 5: project create/delete
 6. Task 6: local Ollama in Docker
 7. Task 7: Groq catalog completeness
 8. Task 8: Minimax/Alibaba failure handling

That sequence attacks the core loop first, then the provider perimeter. The house gets its doors back before we repaint the observatory.

# CAMPAIGN_2026_03_24_BETA_STABILIZATION

## Campaign Metadata

- **Date:** 2026-03-24
- **Status:** Active
- **Objective:** Stabilize Codexify beta core loop and critical provider/runtime pathways for release readiness.
- **Primary release goal:** Achieve a reliable end-to-end chat loop with deterministic recovery and no user-facing lock traps.
- **Owner:** Resonant Jones

## Problem Statement

Codexify is operational but not yet release-stable. Current defects are concentrated in:

- chat composer/thread lock cleanup
- thinking mode defaulting and persistence
- frontend health polling drift
- thread and project mutation failures
- local Ollama connectivity from Docker
- provider catalog and provider error-path reliability

This campaign isolates each issue into a single atomic task so stabilization work can be executed, tested, and committed independently.

## Campaign Scope

### In scope

- chat control loop stabilization
- frontend/backend contract cleanup
- thread and project mutation repair
- provider/runtime stabilization required for beta

### Out of scope

- major architecture refactors
- speculative provider expansion
- non-blocking UX polish unrelated to beta stability

## Execution Order

### Phase 1: Core loop stabilization

1. Task 01: Release composer/thread lock on all terminal paths
2. Task 02: Default thinking mode to Fast and persist per thread
3. Task 03: Reconcile frontend health polling to actual backend contract
4. Task 04: Restore thread deletion end to end
5. Task 05: Restore project create/delete mutations

### Phase 2: Provider/runtime stabilization

6. Task 06: Restore Docker-to-local Ollama accessibility
7. Task 07: Improve provider catalog completeness for Groq
8. Task 08: Harden Minimax and Alibaba provider failure handling

Phase 1 restores the user-visible control loop. Phase 2 improves provider completeness and failure handling.

## Campaign Task Index

1. [TASK_2026_03_24_01_release-composer-thread-lock-on-all-terminal-paths](./Tasks/2026-03-24/TASK_2026_03_24_01_release-composer-thread-lock-on-all-terminal-paths.md)
2. [TASK_2026_03_24_02_default-thinking-mode-to-fast-and-persist-per-thread](./Tasks/2026-03-24/TASK_2026_03_24_02_default-thinking-mode-to-fast-and-persist-per-thread.md)
3. [TASK_2026_03_24_03_reconcile-frontend-health-polling-to-actual-backend-contract](./Tasks/2026-03-24/TASK_2026_03_24_03_reconcile-frontend-health-polling-to-actual-backend-contract.md)
4. [TASK_2026_03_24_04_restore-thread-deletion-end-to-end](./Tasks/2026-03-24/TASK_2026_03_24_04_restore-thread-deletion-end-to-end.md)
5. [TASK_2026_03_24_05_restore-project-create-delete-mutations](./Tasks/2026-03-24/TASK_2026_03_24_05_restore-project-create-delete-mutations.md)
6. [TASK_2026_03_24_06_restore-docker-to-local-ollama-accessibility](./Tasks/2026-03-24/TASK_2026_03_24_06_restore-docker-to-local-ollama-accessibility.md)
7. [TASK_2026_03_24_07_improve-provider-catalog-completeness-for-groq](./Tasks/2026-03-24/TASK_2026_03_24_07_improve-provider-catalog-completeness-for-groq.md)
8. [TASK_2026_03_24_08_harden-minimax-and-alibaba-provider-failure-handling](./Tasks/2026-03-24/TASK_2026_03_24_08_harden-minimax-and-alibaba-provider-failure-handling.md)

## Release Gate

Beta release should proceed only if the following are true:

- [ ] Composer/thread lock reliably clears on all terminal paths
- [ ] Thinking mode defaults to FAST and persists per thread
- [ ] Frontend health polling targets only valid backend routes
- [ ] Thread deletion works end to end
- [ ] Project create/delete works end to end
- [ ] Local Ollama is reachable from Dockerized runtime, or is explicitly excluded from beta claims
- [ ] At least one remote provider path is confirmed reliable in runtime
- [ ] No critical UI deadlock remains in the main chat flow
- [ ] Runtime validation complete
- [ ] Beta release decision recorded

## Progress Tracker

- [ ] Task 01 complete
- [ ] Task 02 complete
- [ ] Task 03 complete
- [ ] Task 04 complete
- [ ] Task 05 complete
- [ ] Task 06 complete
- [ ] Task 07 complete
- [ ] Task 08 complete
- [ ] Runtime validation complete
- [ ] Beta decision made