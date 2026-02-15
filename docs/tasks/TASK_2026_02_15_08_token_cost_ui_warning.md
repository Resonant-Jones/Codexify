TASK 8 — Token Cost UI Warning
Objective

Expose system prompt metadata to frontend and warn if threshold exceeded.

Codexify Task Prompt
Context:
You’re operating on the local Codexify repo.

Instructions:

1. Add endpoint:
   GET /api/system_prompt/summary
2. Return:
   - estimated_tokens
   - docs_count
   - segment sizes
3. Add frontend indicator component.
4. Add tests for threshold behavior.
5. Run full-stack tests.
6. Commit atomically.

Output:

- Summary of UI + backend changes.
- Test results.
- Commit hash.
