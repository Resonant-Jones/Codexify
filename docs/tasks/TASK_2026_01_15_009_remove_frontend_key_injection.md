# TASK-2026-01-15-009 — Remove hardcoded API key from frontend build

## Task Prompt
- **Context:** Prevent shipping secrets in client bundles and enforce config boundaries in the local Codexify repo.
- **Instructions:** Edit only `docker-compose.yml` and `frontend/src/main.tsx`. Run `pytest -v` and `pnpm test`. Record the Task Prompt and Summary with the implementation commit hash.
- **Task Description:** Remove hardcoded frontend API key injection and restrict the frontend to explicit Vite-provided keys.
- **Expected Output:** Frontend build no longer embeds a hardcoded API key, with passing backend + frontend test loops.

## Summary
- Changed files: `docker-compose.yml` (removed hardcoded `VITE_GUARDIAN_API_KEY`), `frontend/src/main.tsx` (only reads `VITE_GUARDIAN_API_KEY` and updates diagnostics).
- Tests: `pytest -v` (pass); `pnpm test` (pass).
- git status: `git status --porcelain` clean; no out-of-scope files.
- Commit mode: two-phase
- Implementation hash: `b2bb22da8d3f2583bd904926da5a4b116b321c8e`
- Finalize-artifact hash: `8033b0b1206adb63d2d000d55e47426de1e32efa`