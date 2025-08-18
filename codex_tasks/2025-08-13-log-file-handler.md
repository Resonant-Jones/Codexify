You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add rotating file logging via env vars

GOAL

- Allow logging to a file in addition to console, configurable by:
  - GUARDIAN_LOG_FILE (path; if unset, file logging disabled)
  - GUARDIAN_LOG_LEVEL (default INFO)
  - GUARDIAN_LOG_MAX_MB (default 5)
  - GUARDIAN_LOG_BACKUPS (default 3)

PATCH
***Begin Patch
*** Update File: guardian/server/app.py
@@
-from fastapi import FastAPI
+from fastapi import FastAPI
+import logging, os
+from logging.handlers import RotatingFileHandler
@@
 app = FastAPI()
 app.include_router(tools_router)
 app.include_router(codexify_router)

+# --- Logging to file (optional via env) ---
+_log_file = os.environ.get("GUARDIAN_LOG_FILE")
+_log_level = os.environ.get("GUARDIAN_LOG_LEVEL", "INFO").upper()
+_max_mb = int(os.environ.get("GUARDIAN_LOG_MAX_MB", "5"))
+_backups = int(os.environ.get("GUARDIAN_LOG_BACKUPS", "3"))
+logging.getLogger().setLevel(getattr(logging, _log_level, logging.INFO))
+if _log_file:
- try:
-        fh = RotatingFileHandler(_log_file, maxBytes=_max_mb*1024*1024, backupCount=_backups)
-        fh.setLevel(getattr(logging, _log_level, logging.INFO))
-        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
-        logging.getLogger().addHandler(fh)
- except Exception:
-        # Don’t crash server on log setup failure
-        pass

***End Patch
*** Begin Patch
*** Update File: README.md
@@

- **CORS Configuration**
  - `GUARDIAN_CORS_ORIGINS`, `GUARDIAN_CORS_ALLOW_CREDENTIALS`, `GUARDIAN_CORS_METHODS`, `GUARDIAN_CORS_HEADERS`

+ - **Logging (optional)**
- - `GUARDIAN_LOG_FILE` — if set, logs also written here (rotating)
- - `GUARDIAN_LOG_LEVEL` — INFO (default), DEBUG, WARNING, etc.
- - `GUARDIAN_LOG_MAX_MB` — rotate size (default 5 MB)
- - `GUARDIAN_LOG_BACKUPS` — number of backups to keep (default 3)
