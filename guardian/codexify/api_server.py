from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from guardian.export_engine import (
    export_to_gdrive,
    import_from_gdrive,
    import_from_icloud,
)
from guardian.codexify import create_notion_database_from_records

app = FastAPI(title="Codexify API", version="0.1")


class GDriveExportRequest(BaseModel):
    records: list[dict]
    format: str = "md"
    folder: str | None = None


class GDriveImportRequest(BaseModel):
    query: str | None = None
    folder: str | None = None


class ICloudImportRequest(BaseModel):
    pattern: str = "*"
    subfolder: str = "Guardian Exports"


class NotionImportRequest(BaseModel):
    records: list[dict]
    parent_id: str
    token: str
    db_title: str | None = None
    with_template: bool = True


@app.post("/guardian/export-gdrive")
def export_gdrive(req: GDriveExportRequest):
    try:
        result = export_to_gdrive(
            req.records, format=req.format, folder_id=req.folder
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/guardian/import-gdrive")
def import_gdrive(req: GDriveImportRequest):
    try:
        files = import_from_gdrive(query=req.query, folder_id=req.folder)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/guardian/import-icloud")
def import_icloud(req: ICloudImportRequest):
    try:
        files = import_from_icloud(req.pattern, req.subfolder)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/codexify/create")
def codexify_create(req: NotionImportRequest):
    try:
        db_id = create_notion_database_from_records(
            req.records,
            req.parent_id,
            req.token,
            db_title=req.db_title,
            with_template=req.with_template,
        )
        return {"db_id": db_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
