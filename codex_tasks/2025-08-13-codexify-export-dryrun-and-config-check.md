You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add dry_run and configuration checks to /codexify/export-gdrive

GOAL

- Add `dry_run: bool = False` to the request model.
- If Google Drive isn’t configured, return HTTP 400 with a clear message.
- If `dry_run=True`, validate payload and return a summary without hitting GDrive.

PATCH
***Begin Patch
*** Update File: guardian/server/codexify_api.py
@@
-from pydantic import BaseModel
+from pydantic import BaseModel
+import os
@@
-class GDriveExportRequest(BaseModel):

- records: list[dict]
- format: str = "md"
- folder: Optional[str] = None
+class GDriveExportRequest(BaseModel):

+ records: list[dict]
- format: str = "md"
- folder: Optional[str] = None
- dry_run: bool = False
@@
 @router.post("/export-gdrive")
 def export_gdrive(req: GDriveExportRequest):
     try:

-        result = export_to_gdrive(req.records, format=req.format, folder_id=req.folder)
-        return {"result": result}

+        # Basic config checks
-        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GDRIVE_OAUTH_TOKEN")
-        if not creds and not req.dry_run:
-            raise HTTPException(status_code=400, detail="Google Drive not configured: set GOOGLE_APPLICATION_CREDENTIALS or provide OAuth token.")
-        # Dry-run: validate only
-        if req.dry_run:
-            count = len(req.records or [])
-            return {"ok": True, "dry_run": True, "records": count, "format": req.format, "folder": req.folder}
-        # Real call
-        result = export_to_gdrive(req.records, format=req.format, folder_id=req.folder)
-        return {"ok": True, "result": result}
     except HTTPException:
         raise
     except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
*** End Patch
