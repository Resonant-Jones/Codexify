Campaign Index

Campaign Name: Beta Stabilization Sweep 2026-03-11
Branch Context: codex/add-personalized-signal-digest-agent
Objective: clear the narrow backend regression cluster revealed by the post-merge validation run so the integration branch is fit to merge into main.

Campaign Scope

This campaign addresses the currently failing backend seams:
 1. guardian.routes.tools.configure_db contract drift
 2. guardian.workers.chat_worker legacy monkeypatch seam drift
 3. Alibaba provider config validation gap
 4. Codex runner run_inputs_payload(..., provider=...) signature drift
 5. Chat worker turn-integrity behavior mismatch on missing assistant message
 6. Hermetic RAG loop patch-target drift in chat_worker

Execution Rules
 • One atomic task at a time
 • Do not combine unrelated fixes
 • Run the narrowest validating test lane first
 • Commit each task independently
 • Append an output report into the task file after completion

Recommended Order

Order Task ID Focus Why first
1 BS-001 tools route test seam clears 3 setup errors in one small contract fix
2 BS-002 codex runner provider arg drift tiny blast radius, fast red reduction
3 BS-003 Alibaba config validation isolated config truth fix
4 BS-004 chat worker legacy seam compatibility clears multiple monkeypatch-based failures
5 BS-005 RAG hermetic loop compatibility separate from blank-output tests, same subsystem
6 BS-006 turn-integrity semantic reconciliation only likely product-contract decision point

⸻

Task Prompts

Task BS-001

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Restore the backend tools-route test seam expected by tests/routes/test_tools.py without changing unrelated route behavior.

This change belongs in:
 • /guardian/routes/tools.py

Possibly also, only if strictly required by existing route structure:
 • /tests/routes/test_tools.py

Implement only the smallest compatibility fix needed so the tools route module once again exposes the DB configuration seam expected by the tests. Preserve current runtime behavior and dependency flow. Prefer restoring a thin compatibility wrapper over rewriting tests or altering route semantics.

Be precise about the intended outcome:
 • guardian.routes.tools.configure_db(...) must exist again
 • existing tests in tests/routes/test_tools.py must be able to inject a fake DB
 • do not change unrelated tool execution/job persistence behavior unless required to preserve the current route contract

Run the correct test suite based on scope:

pytest -v tests/routes/test_tools.py

If checks pass:

git add guardian/routes/tools.py tests/routes/test_tools.py
git commit -m "fix: restore tools route db configuration seam"

Output must include:
 • Summary of changes (files + functions/components)
 • Test results
 • Git commit hash

⸻

Task BS-002

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Reconcile the codex runner test with the current run_inputs_payload signature by updating only the affected test call sites.

This change belongs in:
 • /tests/codex_runner/test_runner_v2.py

Do not change runner implementation in this task unless the test clearly proves the implementation signature is accidental and inconsistent within the same module. Default to updating the test to match the now-required provider argument.

Be precise:
 • fix test_run_id_determinism
 • keep the test’s purpose intact: determinism, not provider-behavior expansion
 • use the smallest valid provider value consistent with current runner semantics

Run the correct test suite based on scope:

pytest -v tests/codex_runner/test_runner_v2.py

If checks pass:

git add tests/codex_runner/test_runner_v2.py
git commit -m "test: align codex runner determinism test with provider arg"

Output must include:
 • Summary of changes (files + functions/components)
 • Test results
 • Git commit hash

⸻

Task BS-003

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Fix Alibaba provider config validation so the settings validator rejects Alibaba cloud usage when the required API key is absent.

This change belongs in:
 • /guardian/core/config.py

Possibly also, only if strictly required to keep tests aligned with the canonical validation contract:
 • /tests/core/test_config_coherence.py

Be precise:
 • when LLM_PROVIDER="alibaba" and cloud providers are allowed, missing ALIBABA_API_KEY must raise LLMConfigError
 • preserve the existing validation behavior for other providers
 • do not broaden this task into provider catalog, routing, or inference-path work

Run the correct test suite based on scope:

pytest -v tests/core/test_config_coherence.py

If checks pass:

git add guardian/core/config.py tests/core/test_config_coherence.py
git commit -m "fix: require alibaba api key in config validation"

Output must include:
 • Summary of changes (files + functions/components)
 • Test results
 • Git commit hash

⸻

Task BS-004

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Restore minimal compatibility seams in the chat worker so existing backend tests can patch the worker module without reverting the newer worker architecture.

This change belongs in:
 • /guardian/workers/chat_worker.py

Possibly also, only if strictly required for alignment with the compatibility surface:
 • /tests/test_chat_worker_blank_output.py

Implement only the narrow compatibility layer needed for current tests that expect patchable attributes on the worker module.

Required compatibility targets from the failing suite:
 • stream_local
 • _embed_message
 • get_settings

Rules:
 • preserve the current worker architecture
 • prefer aliases, wrappers, or module-level compatibility shims over invasive rewrites
 • do not broaden this into worker behavior changes beyond restoring the expected monkeypatch seams

Run the correct test suite based on scope:

pytest -v tests/test_chat_worker_blank_output.py

If checks pass:

git add guardian/workers/chat_worker.py tests/test_chat_worker_blank_output.py
git commit -m "fix: restore chat worker compatibility patch seams"

Output must include:
 • Summary of changes (files + functions/components)
 • Test results
 • Git commit hash

⸻

Task BS-005

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Repair the hermetic RAG integration loop test by reconciling its patch target expectations with the current chat worker structure, without weakening the test’s hermetic guarantees.

This change belongs in:
 • /tests/integration/test_rag_integration_loop.py

Possibly also, only if strictly necessary to expose a narrow compatibility seam:
 • /guardian/workers/chat_worker.py

Be precise:
 • the test must still assert that no cloud LLM path or outbound LLM HTTP is used
 • preserve the memory-loop purpose of the test
 • prefer updating the test to patch the current seam if the worker no longer legitimately exposes stream_local
 • only add a compatibility alias in the worker if that is the most stable repo-wide contract

Run the correct test suite based on scope:

pytest -v tests/integration/test_rag_integration_loop.py

If checks pass:

git add tests/integration/test_rag_integration_loop.py guardian/workers/chat_worker.py
git commit -m "test: align rag loop hermetic patches with current worker seams"

Output must include:
 • Summary of changes (files + functions/components)
 • Test results
 • Git commit hash

⸻

Task BS-006

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Reconcile the chat worker turn-integrity behavior for the “missing assistant message” path so the implementation and test agree on the intended contract.

This change belongs in:
 • /guardian/workers/chat_worker.py
 • /tests/test_chat_worker_turn_integrity.py

This is a behavior-contract task, not a compatibility shim. Determine the correct current system behavior by reading the surrounding turn-lock and duplicate-turn logic, then make the smallest change that preserves runtime integrity.

Be precise:
 • investigate why test_missing_assistant_message_marks_task_failed_and_releases_lock currently observes task.completed instead of task.failed
 • preserve turn-lock release guarantees
 • preserve duplicate-turn protection
 • do not silently weaken the invariant just to make the test pass
 • if the newer runtime contract is intentionally different, update the test to reflect the new invariant and explain why
 • if the implementation is wrong, fix the implementation and keep the stronger failure expectation

Run the correct test suite based on scope:

pytest -v tests/test_chat_worker_turn_integrity.py

If checks pass:

git add guardian/workers/chat_worker.py tests/test_chat_worker_turn_integrity.py
git commit -m "fix: reconcile chat worker missing-assistant turn integrity contract"

Output must include:
 • Summary of changes (files + functions/components)
 • Test results
 • Git commit hash

⸻

Optional Campaign Closeout Task

Use only after BS-001 through BS-006 are done.

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Run the full backend validation lane and document the campaign closeout result.

This change belongs in:
 • /docs/release/run/2026-03-11-beta-stabilization-sweep.md

Document:
 • tasks completed
 • commit hashes
 • final backend test result
 • any remaining expected skips/xfails/xpasses
 • any unresolved blockers

Run the correct test suite based on scope:

pytest -v

If checks pass:

git add docs/release/run/2026-03-11-beta-stabilization-sweep.md
git commit -m "docs: record beta stabilization sweep results"

Output must include:
 • Summary of changes
 • Test results
 • Git commit hash

⸻

Suggested Campaign Prompt for Codex

Use this as the wrapper prompt you feed Codex before the index and task files:

You are operating on the local Codexify repo.

Follow the provided Campaign Index and task files exactly.

Rules:

- Execute only one task at a time.
- Treat each task as atomic and self-contained.
- Do not expand scope beyond the named files unless the task explicitly permits it.
- Preserve current architecture and runtime contracts unless the task explicitly asks for a behavior reconciliation.
- After completing a task:
  1. run the task’s required tests
  2. git add only the modified files named by the task
  3. git commit with the provided message
  4. append an Output Report to the task file containing:
     - Summary of changes
     - Test results
     - Git commit hash
- If a task cannot be completed cleanly, state the blocker inside the Output Report instead of performing adjacent speculative edits.

