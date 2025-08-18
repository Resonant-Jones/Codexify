You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Use token.json via GDRIVE_OAUTH_TOKEN and accept folder IDs in export

GOALS

- Stop referring to legacy token.pickle; rely on token.json located via GDRIVE_OAUTH_TOKEN.
- In /codexify/export-gdrive:
  - If GOOGLE_APPLICATION_CREDENTIALS is set, call ensure_oauth_credentials() before export.
  - Ensure os.environ["GDRIVE_OAUTH_TOKEN"] is set to the resolved token.json so downstream code sees it.
- Accept both folder URLs and bare folder IDs (and strip /u/{n}/ in Drive URLs).
- Keep service-account behavior unchanged.

PATCH
***Begin Patch
*** Update File: guardian/server/codexify_api.py
@@
-from typing import Optional, List, Dict, Any
+from typing import Optional, List, Dict, Any
 from pathlib import Path
-from guardian.integrations.google_oauth import ensure_oauth_credentials
+from guardian.integrations.google_oauth import ensure_oauth_credentials
@@
-_FOLDER_RE = re.compile(r"(?:/folders/|/drive/folders/|id=)([A-Za-z0-9_-]{10,})")
+_FOLDER_RE = re.compile(r"(?:/folders/|/drive/folders/|id=)([A-Za-z0-9_-]{10,})")
+
+def_normalize_folder_id(folder_or_url: Optional[str]) -> Optional[str]:
- if not folder_or_url:
-        return None
- s = folder_or_url.strip()
- # Accept bare IDs directly

+ if re.fullmatch(r"[A-Za-z0-9_-]{10,}", s):
-        return s
- # Tolerate /u/{n}/ variants in the URL

+ s = re.sub(r"/u/\d+/", "/", s)
- m = _FOLDER_RE.search(s)
- return m.group(1) if m else None
@@
 class GDriveExportRequest(BaseModel):
     records: List[Dict[str, Any]]
     format: str = "md"

- folder: Optional[str] = None
- folder_url: Optional[str] = None

+ folder: Optional[str] = None
- folder_url: Optional[str] = None
     return_links: bool = False
     dry_run: bool = False
@@
 @router.post("/export-gdrive")
 def export_gdrive(req: GDriveExportRequest):
     try:

-        # Basic config checks
-        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GDRIVE_OAUTH_TOKEN")
-        if not creds and not req.dry_run:
-            raise HTTPException(status_code=400, detail="Google Drive not configured: set GOOGLE_APPLICATION_CREDENTIALS or provide OAuth token.")
-        # If we are using OAuth (client secret present) and not a dry run,
-        # ensure the OAuth token exists (runs browser flow if needed).
-        if not req.dry_run and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
-            try:
-                ensure_oauth_credentials()
-            except Exception as e:
-                raise HTTPException(status_code=400, detail=f"OAuth setup failed: {e}")

+        # Configuration: Service Account OR OAuth token.json
-        if not req.dry_run:
-            if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
-                # Ensure OAuth token and expose it to downstream libs
-                try:
-                    token_path = ensure_oauth_credentials()
-                    os.environ["GDRIVE_OAUTH_TOKEN"] = token_path
-                except Exception as e:
-                    raise HTTPException(status_code=400, detail=f"OAuth setup failed: {e}")
-            elif not os.environ.get("GDRIVE_OAUTH_TOKEN"):
-                # Neither service-account nor OAuth token available
-                raise HTTPException(status_code=400, detail="Google Drive not configured: set GOOGLE_APPLICATION_CREDENTIALS (OAuth or SA) or GDRIVE_OAUTH_TOKEN (token.json).")

@@

-        # Resolve folder from URL if needed (ID wins if both provided)
-        folder_id = req.folder
-        if not folder_id and req.folder_url:
-            m = _FOLDER_RE.search(req.folder_url)
-            if not m:
-                raise HTTPException(status_code=400, detail="Invalid folder_url: could not parse an id.")
-            folder_id = m.group(1)

+        # Resolve folder: accept either raw ID or URL (including /u/{n}/ variants)
-        folder_id = req.folder or _normalize_folder_id(req.folder_url)
-        if req.folder_url and not folder_id:
-            raise HTTPException(status_code=400, detail="Invalid folder_url: could not parse an id.")

@@

-        # Real call
-        result = export_to_gdrive(req.records, format=req.format, folder_id=folder_id)

+        # Real call
-        # Ensure downstream exporter can find token.json via env (GDRIVE_OAUTH_TOKEN)
-        result = export_to_gdrive(req.records, format=req.format, folder_id=folder_id)
         if req.return_links:
             enriched = _with_links(result)
             return {"ok": True, **enriched}
         return {"ok": True, "result": result}

*** End Patch
