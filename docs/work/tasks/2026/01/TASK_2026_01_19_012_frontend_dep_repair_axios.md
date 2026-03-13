Codexify Task Prompt

TASK-ID

TASK_2026_01_19_012_frontend_dep_repair_axios

Context

You’re operating on the local Codexify repo.

The required frontend unit test check is failing:
	•	pnpm --dir frontend/src test fails because Vite cannot resolve import "axios" from:
frontend/src/lib/api.ts

This blocks:
	•	TASK_2026_01_19_011_docker_playwright_e2e_harness (Docker Playwright E2E harness), which requires tests to pass.

Objective

Repair frontend dependencies so:
	•	pnpm --dir frontend/src test passes reliably.

Requirements
	•	Fix the axios resolution error in the minimal, correct way.
	•	Prefer adding the missing dependency rather than refactoring imports.
	•	Do not change app behavior.
	•	Follow docs/reference/operator/ops/Runner_Protocol.md exactly, using two-phase commits.
	•	Include TASK-ID in both commit messages.
	•	Record both hashes in the task artifact (Finalize hash may be “reported in final mapping” per paradox rule).
	•	Keep git clean after running tests.

Files allowed to edit (only)
	•	frontend/src/package.json
	•	frontend/src/pnpm-lock.yaml (OR the actual lockfile pnpm modifies; if pnpm writes elsewhere, use that correct lockfile path instead and report it explicitly in the task artifact)
	•	docs/work/tasks/2026/01/TASK_2026_01_19_012_frontend_dep_repair_axios.md

Checks to run (required)
	•	pnpm --dir frontend/src install
	•	pnpm --dir frontend/src test
	•	pnpm --dir frontend/src lint (warnings ok, errors not ok)
	•	git status --porcelain (must be empty at end)

⸻

Git steps (two-phase)

Commit A (implementation)
	1.	git status --porcelain
	2.	pnpm --dir frontend/src install
	3.	pnpm --dir frontend/src test (must pass)
	4.	pnpm --dir frontend/src lint
	5.	git add frontend/src/package.json <lockfile path>
	6.	git commit -m "TASK_2026_01_19_012_frontend_dep_repair_axios: fix axios dependency for tests"

Commit B (finalize docs artifact)
	1.	Create/update: docs/work/tasks/2026/01/TASK_2026_01_19_012_frontend_dep_repair_axios.md with:
	•	Task Prompt (verbatim)
	•	Summary (files changed, commands run + results, git status confirmation)
	•	Commit mode: two-phase (no amend)
	•	Implementation hash: <hash A>
	•	Finalize-artifact hash: (reported in final mapping)
	2.	git add docs/work/tasks/2026/01/TASK_2026_01_19_012_frontend_dep_repair_axios.md
	3.	git commit -m "TASK_2026_01_19_012_frontend_dep_repair_axios: finalize task summary"

⸻

Output required
	•	Summary of changes
	•	Commands run + pass/fail
	•	git status --porcelain (must be empty)
	•	Mapping:
TASK_2026_01_19_012_frontend_dep_repair_axios -> [<impl_hash>, <finalize_hash>]

⸻

Acceptance Criteria

✅ pnpm --dir frontend/src test passes
✅ No unrelated refactors
✅ Working tree clean after finalize commit

Summary
- Changed files: `frontend/src/package.json` (added axios dependency), `pnpm-lock.yaml` (workspace lockfile updated), `docs/work/tasks/2026/01/TASK_2026_01_19_012_frontend_dep_repair_axios.md`
- Commands run (pass unless noted): `pnpm --dir frontend/src install` (failed without network, succeeded with escalated network), `pnpm --dir frontend/src test` (failed before axios install, passed after), `pnpm --dir frontend/src lint` (warnings only), `git status --porcelain` (clean after implementation commit; only task artifact modified during finalize)
- Commit mode: two-phase (no amend)
- Implementation hash: 02954c2da3056b9297d1e826045a1f8155c2b7af
- Finalize-artifact hash: reported in final mapping
