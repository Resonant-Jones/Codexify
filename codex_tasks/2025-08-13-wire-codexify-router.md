You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Move root api_server into guardian/server as a router and mount it

GOAL

- Convert the current repo-root api_server.py (Codexify endpoints) into a FastAPI router at /codexify.
- Mount that router inside guardian/server/app.py (which already mounts /tools).
- Do not change endpoint behavior or payload shapes. Keep names and logic identical.
- Keep tests passing.

PATCH
***Begin Patch
*** Add File: guardian/server/codexify_api.py
+from __future__ import annotations
+from fastapi import APIRouter, HTTPException
+from pydantic import BaseModel
+from typing import Optional
+
+from guardian.export_engine import (
- export_to_gdrive,
- import_from_gdrive,
- import_from_icloud,
+)
+from guardian.codexify import create_notion_database_from_records
-

+router = APIRouter(prefix="/codexify", tags=["codexify"])
+
+class GDriveExportRequest(BaseModel):
- records: list[dict]
- format: str = "md"
- folder: Optional[str] = None
-

+class GDriveImportRequest(BaseModel):
- query: Optional[str] = None
- folder: Optional[str] = None
-

+class ICloudImportRequest(BaseModel):
- pattern: str = "*"
- subfolder: str = "Guardian Exports"
-

+class NotionImportRequest(BaseModel):
- records: list[dict]
- parent_id: str
- token: str
- db_title: Optional[str] = None
- with_template: bool = True
-
<+@router.post>("/export-gdrive")
+def export_gdrive(req: GDriveExportRequest):
- try:
-        result = export_to_gdrive(req.records, format=req.format, folder_id=req.folder)
-        return {"result": result}
- except Exception as e:
-        raise HTTPException(status_code=500, detail=str(e))
-
<+@router.post>("/import-gdrive")
+def import_gdrive(req: GDriveImportRequest):
- try:
-        files = import_from_gdrive(query=req.query, folder_id=req.folder)
-        return {"files": files}
- except Exception as e:
-        raise HTTPException(status_code=500, detail=str(e))
-
<+@router.post>("/import-icloud")
+def import_icloud(req: ICloudImportRequest):
- try:
-        files = import_from_icloud(req.pattern, req.subfolder)
-        return {"files": files}
- except Exception as e:
-        raise HTTPException(status_code=500, detail=str(e))
-
<+@router.post>("/create")
+def codexify_create(req: NotionImportRequest):
- try:
-        db_id = create_notion_database_from_records(
-            req.records,
-            req.parent_id,
-            req.token,
-            db_title=req.db_title,
-            with_template=req.with_template,
-        )
-        return {"db_id": db_id}
- except Exception as e:
-        raise HTTPException(status_code=500, detail=str(e))

***End Patch
*** Begin Patch
*** Update File: guardian/server/app.py
@@
-from fastapi import FastAPI
-from guardian.server.tools_api import router as tools_router
+from fastapi import FastAPI
+from guardian.server.tools_api import router as tools_router
+from guardian.server.codexify_api import router as codexify_router
@@
 app = FastAPI()
 app.include_router(tools_router)
+app.include_router(codexify_router)
+
+# Optional tiny health endpoint
<+@app.get>("/healthz")
+def healthz():
- return {"ok": True}
***End Patch
*** Begin Patch
*** Update File: api_server.py
@@
-from fastapi import FastAPI, HTTPException
-from pydantic import BaseModel

-

-from guardian.export_engine import (

- export_to_gdrive,
- import_from_gdrive,
- import_from_icloud,
-)
-from guardian.codexify import create_notion_database_from_records
-

-app = FastAPI(title="Codexify API", version="0.1")
-

-# (models + endpoints...)
-

-# This file is superseded by guardian/server/codexify_api.py.
-# Keeping it to avoid breaking external imports; importing router here would duplicate apps.
-# Please use guardian.server.app:app as the server entrypoint.
+"""
+Deprecated: this module’s endpoints were moved to guardian/server/codexify_api.py
+Use `guardian.server.app:app` as the single FastAPI application.
+"""
*** End Patch
