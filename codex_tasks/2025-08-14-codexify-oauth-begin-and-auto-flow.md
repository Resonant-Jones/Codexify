You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add Google OAuth helper, `/codexify/oauth-begin`, and auto-run OAuth on export

GOAL

- Ensure that when using OAuth, if no token is present, the server runs the browser consent flow and saves `<repo_root>/secrets/token.json`.
- Add POST /codexify/oauth-begin to trigger-only the OAuth ritual.
- Keep service-account behavior unchanged.
- Backward compat: if legacy token.pickle exists, migrate to token.json.

PATCH
***Begin Patch
*** Add File: guardian/integrations/google_oauth.py
+from __future__ import annotations
+import os
+from pathlib import Path
+from typing import Optional
+
+SCOPES = ["https://www.googleapis.com/auth/drive.file"]
+
+def_default_token_path() -> Path:
- # repo_root = guardian/integrations/ -> parents[2]

+ return Path(__file__).resolve().parents[2] / "secrets" / "token.json"
-

+def _resolve_paths() -> tuple[Optional[Path], Path]:
- creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
- token_env = os.environ.get("GDRIVE_OAUTH_TOKEN")
- token_path = Path(token_env) if token_env else_default_token_path()
- token_path.parent.mkdir(parents=True, exist_ok=True)
- return (Path(creds_path) if creds_path else None, token_path)
-

+def ensure_oauth_credentials() -> str:
- """
- Ensures an OAuth token exists at the resolved token path.
- - If token.json already exists and is valid, returns its path.
- - If legacy token.pickle exists next to it, migrates content to token.json.
- - Otherwise runs the Installed App flow using GOOGLE_APPLICATION_CREDENTIALS.
- Returns the token file path as string.
- """
- # Lazy imports (optional deps)

+ import json
- from google.auth.transport.requests import Request
- from google.oauth2.credentials import Credentials
- from google_auth_oauthlib.flow import InstalledAppFlow
-
- creds_path, token_path = _resolve_paths()
- # Migrate legacy token.pickle → token.json if present

+ legacy_pickle = token_path.with_suffix(".pickle")
- if legacy_pickle.exists() and not token_path.exists():
-        try:
-            # Load pickle → write JSON (minimal fields)
-            import pickle
-            with legacy_pickle.open("rb") as f:
-                old = pickle.load(f)
-            data = {
-                "token": getattr(old, "token", None),
-                "refresh_token": getattr(old, "refresh_token", None),
-                "token_uri": getattr(old, "token_uri", "https://oauth2.googleapis.com/token"),
-                "client_id": getattr(old, "client_id", None),
-                "client_secret": getattr(old, "client_secret", None),
-                "scopes": getattr(old, "scopes", SCOPES),
-            }
-            token_path.write_text(json.dumps(data))
-        except Exception:
-            # ignore migration errors; we'll just run flow below
-            pass
-
- creds = None
- if token_path.exists():
-        try:
-            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
-        except Exception:
-            creds = None
- if creds and creds.expired and creds.refresh_token:
-        try:
-            creds.refresh(Request())
-            token_path.write_text(creds.to_json())
-            return str(token_path)
-        except Exception:
-            creds = None
- if not creds:
-        if not creds_path or not Path(creds_path).exists():
-            raise RuntimeError("OAuth client secret missing. Set GOOGLE_APPLICATION_CREDENTIALS to your client_secret JSON.")
-        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
-        # local server flow opens browser
-        creds = flow.run_local_server(port=0)
-        token_path.write_text(creds.to_json())
- # Ensure env is set so downstream libs can see it

+ os.environ["GDRIVE_OAUTH_TOKEN"] = str(token_path)
- return str(token_path)
***End Patch
*** Begin Patch
*** Update File: guardian/server/codexify_api.py
@@
-from pathlib import Path
+from pathlib import Path
+from guardian.integrations.google_oauth import ensure_oauth_credentials
@@
 @router.post("/export-gdrive")
 def export_gdrive(req: GDriveExportRequest):
     try:
         # Basic config checks
         creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GDRIVE_OAUTH_TOKEN")
         if not creds and not req.dry_run:
             raise HTTPException(status_code=400, detail="Google Drive not configured: set GOOGLE_APPLICATION_CREDENTIALS or provide OAuth token.")
-        # If we are using OAuth (client secret present) and not a dry run,
-        # ensure the OAuth token exists (runs browser flow if needed).
-        if not req.dry_run and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
-            try:
-                ensure_oauth_credentials()
-            except Exception as e:
-                raise HTTPException(status_code=400, detail=f"OAuth setup failed: {e}")

@@
         # Real call
         result = export_to_gdrive(req.records, format=req.format, folder_id=folder_id)
         if req.return_links:
             enriched =_with_links(result)
             return {"ok": True, **enriched}
         return {"ok": True, "result": result}
***End Patch
*** Begin Patch
*** Update File: guardian/server/codexify_api.py
@@
 @router.get("/oauth-status")
 def oauth_status():
@@
     if tpath.exists():
         return {"status": "oauth_ready", "credentials": creds, "token": str(tpath)}
     return {"status": "oauth_no_token", "credentials": creds, "token": str(tpath)}
+
<+@router.post>("/oauth-begin")
+def oauth_begin():
- """
- Kick off the OAuth browser flow and persist token.json in secrets/.
- Returns token path on success.
- """
- try:
-        path = ensure_oauth_credentials()
-        return {"ok": True, "token": path}
- except Exception as e:
-        raise HTTPException(status_code=400, detail=str(e))

*** End Patch
