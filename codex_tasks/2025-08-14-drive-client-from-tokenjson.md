You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Drive client should use token.json (OAuth) or SA JSON; remove token.pickle dependency

GOALS

- Build Google Drive API client explicitly from either:
  - Service Account JSON (type == "service_account"), OR
  - OAuth token.json (path from GDRIVE_OAUTH_TOKEN, default: <repo>/secrets/token.json).
- Stop any reliance on token.pickle.
- Make /codexify/export-gdrive use this client.
- Add helpful debug logs for which credential path/type was used.

PATCH
***Begin Patch
*** Add File: guardian/integrations/google_drive.py
+from __future__ import annotations
+import json, os
+from pathlib import Path
+from typing import Optional
+
+from googleapiclient.discovery import build
+from google.oauth2.service_account import Credentials as SACredentials
+from google.oauth2.credentials import Credentials as OAuthCredentials
+
+SCOPES = ["https://www.googleapis.com/auth/drive.file"]
+
+def _repo_root() -> Path:
- # guardian/integrations -> repo root is parents[2]

+ return Path(__file__).resolve().parents[2]
-

+def resolve_token_path() -> Path:
- p = os.environ.get("GDRIVE_OAUTH_TOKEN")
- if p:
-        return Path(p)
- return _repo_root() / "secrets" / "token.json"
-

+def is_service_account(creds_path: Path) -> bool:
- try:
-        data = json.loads(creds_path.read_text())
-        return isinstance(data, dict) and data.get("type") == "service_account"
- except Exception:
-        return False
-

+def build_drive_service(logger=None):
- """
- Returns a googleapiclient Drive v3 service using either:
-      - Service Account json at GOOGLE_APPLICATION_CREDENTIALS, or
-      - OAuth token.json at GDRIVE_OAUTH_TOKEN (or secrets/token.json).
- Raises RuntimeError if neither is usable.
- """
- creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
- token_json = resolve_token_path()
-
- if creds_json:
-        cpath = Path(creds_json)
-        if cpath.exists() and is_service_account(cpath):
-            if logger: logger.info("Drive auth: using Service Account at %s", str(cpath))
-            creds = SACredentials.from_service_account_file(str(cpath), scopes=SCOPES)
-            return build("drive", "v3", credentials=creds, cache_discovery=False)
-        # Else: OAuth path — token.json must exist
-        if token_json.exists():
-            if logger: logger.info("Drive auth: using OAuth token at %s (client at %s)", str(token_json), str(cpath))
-            creds = OAuthCredentials.from_authorized_user_file(str(token_json), SCOPES)
-            return build("drive", "v3", credentials=creds, cache_discovery=False)
-        raise RuntimeError("OAuth token not found at %s. Run /codexify/oauth-begin first." % str(token_json))
- # No GOOGLE_APPLICATION_CREDENTIALS => rely on token.json only

+ if token_json.exists():
-        if logger: logger.info("Drive auth: using OAuth token at %s (no client secret provided)", str(token_json))
-        creds = OAuthCredentials.from_authorized_user_file(str(token_json), SCOPES)
-        return build("drive", "v3", credentials=creds, cache_discovery=False)
- raise RuntimeError("No Drive credentials. Set GOOGLE_APPLICATION_CREDENTIALS or provide token.json at %s" % str(token_json))
***End Patch
*** Begin Patch
*** Update File: guardian/server/codexify_api.py
@@
-from guardian.integrations.google_oauth import ensure_oauth_credentials
+from guardian.integrations.google_oauth import ensure_oauth_credentials
+from guardian.integrations.google_drive import build_drive_service, resolve_token_path
+import logging
@@
 def export_gdrive(req: GDriveExportRequest):
     try:

-        # Configuration: Service Account OR OAuth token.json

+        log = logging.getLogger("codexify.export")
-        # Configuration: Service Account OR OAuth token.json
         if not req.dry_run:
             if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                 # Ensure OAuth token and expose it to downstream libs
                 try:

-                    token_path = ensure_oauth_credentials()
-                    os.environ["GDRIVE_OAUTH_TOKEN"] = token_path

+                    token_path = ensure_oauth_credentials()
-                    os.environ["GDRIVE_OAUTH_TOKEN"] = token_path
-                    log.info("OAuth token ready at %s", token_path)
                 except Exception as e:
                     raise HTTPException(status_code=400, detail=f"OAuth setup failed: {e}")
             elif not os.environ.get("GDRIVE_OAUTH_TOKEN"):
                 # Neither service-account nor OAuth token available
                 raise HTTPException(status_code=400, detail="Google Drive not configured: set GOOGLE_APPLICATION_CREDENTIALS (OAuth or SA) or GDRIVE_OAUTH_TOKEN (token.json).")

@@

-        # Real call
-        # Ensure downstream exporter can find token.json via env (GDRIVE_OAUTH_TOKEN)
-        result = export_to_gdrive(req.records, format=req.format, folder_id=folder_id)

+        # Real call: use an explicit Drive service built from token.json or SA
-        if req.dry_run:
-            return {"ok": True, "dry_run": True, "records": len(req.records), "format": req.format, "folder": folder_id}
-        service = build_drive_service(logger=log)
-        result = export_to_gdrive(req.records, format=req.format, folder_id=folder_id, service=service)
         if req.return_links:
             enriched = _with_links(result)
             return {"ok": True, **enriched}
         return {"ok": True, "result": result}

***End Patch
*** Begin Patch
***Update File: guardian/server/codexify_api.py
@@
-def_with_links(result):
+def_with_links(result):
     # existing helper...
*** End Patch
