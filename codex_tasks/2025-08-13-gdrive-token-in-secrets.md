You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Store Google OAuth token.json in `secrets/` by default and ensure directory exists

GOAL

- When using OAuth (GOOGLE_APPLICATION_CREDENTIALS points to a client_secret JSON),
  save/reuse the OAuth token at `<repo_root>/secrets/token.json` by default.
- Keep behavior with service accounts unchanged.
- Remain backward-compatible: if env var GDRIVE_OAUTH_TOKEN is already set, use it as-is.
- Create the `secrets/` directory automatically if missing.
- Keep tests passing.

PATCH
***Begin Patch
*** Update File: guardian/server/codexify_api.py
@@
-from pydantic import BaseModel
+from pydantic import BaseModel
 import os
 import re
 from typing import Optional, List, Dict, Any
+from pathlib import Path
@@
 def export_gdrive(req: GDriveExportRequest):
     try:
         # Basic config checks

-        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GDRIVE_OAUTH_TOKEN")

+        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GDRIVE_OAUTH_TOKEN")
         if not creds and not req.dry_run:
             raise HTTPException(status_code=400, detail="Google Drive not configured: set GOOGLE_APPLICATION_CREDENTIALS or provide OAuth token.")
-        # If using OAuth client secret and no explicit token path is provided,
-        # default the token storage to <repo_root>/secrets/token.json
-        # (Backward compatible: if GDRIVE_OAUTH_TOKEN is already set, do nothing.)
-        if not req.dry_run:
-            if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and not os.environ.get("GDRIVE_OAUTH_TOKEN"):
-                # repo root is two levels up from this file: guardian/server/ -> repo root
-                repo_root = Path(__file__).resolve().parents[2]
-                secrets_dir = repo_root / "secrets"
-                try:
-                    secrets_dir.mkdir(parents=True, exist_ok=True)
-                except Exception as _e:
-                    # Do not fail the request for a directory error; fall back to current working directory
-                    secrets_dir = Path.cwd() / "secrets"
-                    secrets_dir.mkdir(parents=True, exist_ok=True)
-                token_path = secrets_dir / "token.json"
-                os.environ["GDRIVE_OAUTH_TOKEN"] = str(token_path)

@@
         # Resolve folder from URL if needed (ID wins if both provided)
         folder_id = req.folder
***End Patch
*** Begin Patch
*** Update File: README.md
@@

### Codexify: Google Drive export

- Set credentials (pick one):
  - Service Account: `GOOGLE_APPLICATION_CREDENTIALS=/abs/path/service-account.json`
  - OAuth (desktop): `GOOGLE_APPLICATION_CREDENTIALS=/abs/path/client_secret_oauth.json`
- Install deps: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`
- Test with dry run:
curl -s -X POST localhost:8888/codexify/export-gdrive
-H ‘content-type: application/json’
-d ‘{“records”:[{“title”:“Hello”}],“format”:“md”,“dry_run”:true}’
+- **Token storage (OAuth only):**

+ - By default, if `GOOGLE_APPLICATION_CREDENTIALS` points to an OAuth client secret and `GDRIVE_OAUTH_TOKEN` is not set, the server will save/reuse the OAuth token at:
- - `<repo_root>/secrets/token.json`
- - To override, set `GDRIVE_OAUTH_TOKEN=/abs/path/to/token.json`.
- - The `secrets/` directory is created automatically if it doesn’t exist.
*** End Patch
