You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add console script `guardian-api` to launch FastAPI app

GOAL

- Provide a convenient launcher for the unified server via uvicorn.

PATCH
***Begin Patch
*** Update File: pyproject.toml
@@
 [project.scripts]
 guardian = "guardian.cli.memoryos_cli:cli"
 guardian-diag = "guardian.tui.diag_app:main"
 guardian-main = "guardian.guardian_main:app"
+guardian-api = "guardian.server.app:app"
*** End Patch
