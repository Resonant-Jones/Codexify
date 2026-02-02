# TASK-2026-01-15-008 — Inject ContextBroker output into chat worker messages

## Task Prompt
- **Context:** Ensure RAG context assembled by ContextBroker is injected into the chat worker message stream in the local Codexify repo.
- **Instructions:** Edit only `guardian/workers/chat_worker.py` and `guardian/cognition/prompts.py`. Run `pytest -v`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Build and insert a system context message from ContextBroker bundles in the chat worker.
- **Expected Output:** Chat worker inserts RAG context system messages alongside the main system prompt, with passing `pytest -v`.

## Summary
- Changed files: `guardian/cognition/prompts.py` (added context system message builder), `guardian/workers/chat_worker.py` (injected bundle context into messages).
- Tests: `pytest -v` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit mode: two-phase
- Implementation hash: `190e807234ace3560312aa0256589703a2292804`
- Finalize-artifact hash: `b01710d99c71cca41999a3f9c9152087e9605989`