You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add `/codexify/oauth-status` endpoint to check Drive OAuth readiness

GOAL

- Return a simple JSON status describing whether Google Drive export is ready.
- States:
  - "missing_secret"  → no GOOGLE_APPLICATION_CREDENTIALS & no GDRIVE_OAUTH_TOKEN
  - "service_account" → GOOGLE_APPLICATION_CREDENTIALS points to a JSON that looks like a service account
  - "oauth_no_token"  → OAuth client secret present but token file not found yet
  - "oauth_ready"     → OAuth client secret present and token file found
  - "token_only"      → Only GDRIVE_OAUTH_TOKEN set (use as-is)
- Include resolved paths for debugging (if present).

PATCH
***Begin Patch
*** Update File: guardian/server/codexify_api.py
@@
-from typing import Optional, List, Dict, Any
+from typing import Optional, List, Dict, Any
 from pathlib import Path
@@
 _FOLDER_LINK = "<https://drive.google.com/drive/folders/{id}>"
@@
+def_looks_like_service_account(json_path: Path) -> bool:
- try:
-        import json
-        data = json.loads(json_path.read_text())
-        # Service account files have "type":"service_account" at top-level.
-        return isinstance(data, dict) and data.get("type") == "service_account"
- except Exception:
-        return False
-
<+@router.get>("/oauth-status")
+def oauth_status():
- creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
- token = os.environ.get("GDRIVE_OAUTH_TOKEN")
- if not creds and not token:
-        return {"status": "missing_secret"}
- if token and not creds:
-        # Token-only mode; assume caller knows what they’re doing.
-        return {"status": "token_only", "token": token}
- # creds present

+ cpath = Path(creds) if creds else None
- if cpath and cpath.exists() and _looks_like_service_account(cpath):
-        return {"status": "service_account", "credentials": str(cpath)}
- # assume OAuth client secret (desktop)

+ # Where would token live?

+ if token:
-        tpath = Path(token)
- else:
-        repo_root = Path(__file__).resolve().parents[2]
-        tpath = repo_root / "secrets" / "token.json"
- if tpath.exists():
-        return {"status": "oauth_ready", "credentials": creds, "token": str(tpath)}
- return {"status": "oauth_no_token", "credentials": creds, "token": str(tpath)}
*** End Patch
