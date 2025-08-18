You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add folder_url support and return Drive web links in /codexify/export-gdrive

GOAL

- Accept `folder_url` as an alternative to `folder` ID; parse the ID from common Google Drive URL styles.
- Add `return_links` flag (default True) to return clickable Drive links for created files.
- Preserve existing behavior; keep dry_run working; keep tests passing.

PATCH
***Begin Patch
*** Update File: guardian/server/codexify_api.py
@@
-from pydantic import BaseModel
+from pydantic import BaseModel
 import os
+import re
+from typing import Optional, List, Dict, Any
@@
-class GDriveExportRequest(BaseModel):

- records: list[dict]
- format: str = "md"
- folder: Optional[str] = None
- dry_run: bool = False
+class GDriveExportRequest(BaseModel):

+ records: list[dict]
- format: str = "md"
- # Accept either explicit folder ID or a full folder URL. If both are provided, `folder` (ID) wins

+ folder: Optional[str] = None
- folder_url: Optional[str] = None
- # Return clickable links for created items (default True)

+ return_links: bool = True
- dry_run: bool = False
@@
<-@router.post>("/export-gdrive")
+# --- Helpers ---
+_FILE_LINK = "<https://drive.google.com/file/d/{id}/view>"
+_FOLDER_LINK = "<https://drive.google.com/drive/folders/{id}>"
-

+def _extract_drive_id(url: str) -> Optional[str]:
- """
- Extracts a Drive file/folder id from common URL shapes:
-      - https://drive.google.com/drive/folders/<FOLDER_ID>
-      - https://drive.google.com/file/d/<FILE_ID>/view
-      - https://drive.google.com/open?id=<ID>
- Returns None if no id can be parsed.
- """
- if not url:
-        return None
- # file URLs

+ m = re.search(r"/file/d/([A-Za-z0-9_-]{10,})", url)
- if m:
-        return m.group(1)
- # folder URLs

+ m = re.search(r"/folders/([A-Za-z0-9_-]{10,})", url)
- if m:
-        return m.group(1)
- # open?id=ID

+ m = re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", url)
- if m:
-        return m.group(1)
- return None
-

+def _with_links(result: Any) -> Dict[str, Any]:
- """
- Normalize exporter result into { files: [{id, webViewLink}], count }.
- - If result items already include webViewLink / id, keep them.
- - Otherwise, construct a web link from id using a generic template.
- """
- files: List[Dict[str, Any]] = []
- # Accept a variety of shapes: list[str], list[dict], dict with 'files'

+ items = None
- if isinstance(result, dict) and "files" in result:
-        items = result["files"]
- else:
-        items = result
- if not isinstance(items, list):
-        items = [items] if items is not None else []
- for it in items:
-        if isinstance(it, dict):
-            _id = it.get("id")
-            _link = it.get("webViewLink") or (_FILE_LINK.format(id=_id) if _id else None)
-            files.append({"id": _id, "webViewLink": _link, **{k: v for k, v in it.items() if k not in ("id", "webViewLink")}})
-        else:
-            # assume string id
-            _id = str(it)
-            files.append({"id": _id, "webViewLink": _FILE_LINK.format(id=_id)})
- return {"files": files, "count": len(files)}
-
<+@router.get>("/folder-id")
+def resolve_folder_id(url: str):
- """
- Utility endpoint: resolve folder/file id from a Google Drive URL.
- """
- _id =_extract_drive_id(url)
- if not _id:
-        raise HTTPException(status_code=400, detail="Could not parse an id from the provided URL.")
- return {"id": _id, "webLink": (_FOLDER_LINK.format(id=_id))}
-
<+@router.post>("/export-gdrive")
 def export_gdrive(req: GDriveExportRequest):
     try:
         # Basic config checks

-        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GDRIVE_OAUTH_TOKEN")

+        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GDRIVE_OAUTH_TOKEN")
         if not creds and not req.dry_run:
             raise HTTPException(status_code=400, detail="Google Drive not configured: set GOOGLE_APPLICATION_CREDENTIALS or provide OAuth token.")

-        # Dry-run: validate only

+        # Resolve folder from URL if needed (ID wins if both provided)
-        folder_id = req.folder
-        if not folder_id and req.folder_url:
-            folder_id = _extract_drive_id(req.folder_url)
-            if not folder_id:
-                raise HTTPException(status_code=400, detail="Invalid folder_url: could not parse an id.")
-        # Dry-run: validate only
         if req.dry_run:
             count = len(req.records or [])

-            return {"ok": True, "dry_run": True, "records": count, "format": req.format, "folder": req.folder}

+            return {
-                "ok": True,
-                "dry_run": True,
-                "records": count,
-                "format": req.format,
-                "folder": folder_id or req.folder,
-                "folder_url": req.folder_url,
-            }
         # Real call

-        result = export_to_gdrive(req.records, format=req.format, folder_id=req.folder)
-        return {"ok": True, "result": result}

+        result = export_to_gdrive(req.records, format=req.format, folder_id=folder_id)
-        if req.return_links:
-            enriched = _with_links(result)
-            return {"ok": True, **enriched}
-        return {"ok": True, "result": result}
     except HTTPException:
         raise
     except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
*** End Patch
