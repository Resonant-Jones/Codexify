

# TASK-2026-01-17-002 — Frontend loads .env via docker-compose env_file

## Task Prompt

Context:
You’re operating on the local Codexify repo. The backend has `GUARDIAN_API_KEY` set, but the frontend container is currently starting with `VITE_GUARDIAN_API_KEY` empty, causing unauthorized API key attempts after restarts. We want the frontend service to load `.env` so `VITE_*` variables are available in the container.

This change belongs in `docker-compose.yml` because container environment injection is defined there.

Instructions:
1. Perform the described edit only in the specified files.
2. Run the appropriate checks/tests:
   - Validate compose file:
     - `docker compose config -q`
   - Quick verification of env propagation:
     - `docker compose up -d frontend`
     - `docker compose exec -T frontend printenv | grep -E "^VITE_GUARDIAN_API_KEY="`
   - Confirm clean state:
     - `git status --porcelain`
3. Two-phase commit per `docs/reference/operator/ops/Runner_Protocol.md`:
   - Commit A (implementation)
   - Commit B (docs finalize) updating this artifact with both hashes.
4. Output:
   - Summary of what changed (files touched)
   - Checks run and results
   - `git status --porcelain` output
   - Mapping: `TASK-ID -> [impl_hash, finalize_hash]`

🧩 Task Description
- Update `docker-compose.yml` for the `frontend` service to load `.env` by adding:
  - `env_file: .env`
- Keep the existing explicit `environment:` block; `.env` should provide values (especially `VITE_GUARDIAN_API_KEY`) without removing current defaults.
- Remove any stray whitespace-only changes introduced near `environment:` (avoid blank lines that show up as diff noise).

✅ Acceptance Criteria
- Frontend container receives `.env` variables at runtime.
- `docker compose exec -T frontend printenv | grep -E "^VITE_GUARDIAN_API_KEY="` prints a non-empty value when `.env` defines it.
- `docker compose config -q` passes.
- Working tree is clean after the finalize commit.

Files allowed to edit (only):
- `docker-compose.yml`
- `docs/work/tasks/TASK-2026-01-17-002_FRONTEND_ENV_FILE.md`

Git steps
Commit A — Implementation:
```bash
git add docker-compose.yml
git commit -m "TASK-2026-01-17-002: load frontend env from .env"
```

Commit B — Finalize task artifact:
```bash
git add docs/work/tasks/TASK-2026-01-17-002_FRONTEND_ENV_FILE.md
git commit -m "docs(task): finalize TASK-2026-01-17-002 summary"
```

## Summary
- Changed files: docker-compose.yml
- Checks:
  - `docker compose config -q`: pass
  - `docker compose up -d frontend`: pass
- `docker compose exec -T frontend printenv | grep -E "^VITE_GUARDIAN_API_KEY="`: `VITE_GUARDIAN_API_KEY=<dev-only-same-as-backend>`
- git status: clean
- Commit mode: two-phase
- Implementation hash: 58fe9b5493ed998c0fd6f43c7ab540940ed8f943
- Finalize-artifact hash: reported in final mapping
