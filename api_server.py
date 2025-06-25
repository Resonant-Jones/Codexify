import subprocess

from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Codexify API", version="0.1")


class GDriveExportRequest(BaseModel):
    pass  # add options here if needed later


class NotionImportRequest(BaseModel):
    records: str
    fieldmap: str
    aliasmap: str
    parent_id: str
    parent_title: str
    seed: bool = False
    edit_aliases: bool = False


@app.post("/guardian/export-gdrive")
def export_gdrive():
    result = subprocess.run(
        ["python", "guardian/guardian_cli.py", "export_gdrive"],
        capture_output=True,
        text=True,
    )
    return {"stdout": result.stdout, "stderr": result.stderr}


@app.post("/guardian/import-gdrive")
def import_gdrive():
    result = subprocess.run(
        ["python", "guardian/guardian_cli.py", "import_gdrive"],
        capture_output=True,
        text=True,
    )
    return {"stdout": result.stdout, "stderr": result.stderr}


@app.post("/guardian/import-icloud")
def import_icloud():
    result = subprocess.run(
        ["python", "guardian/guardian_cli.py", "import_icloud"],
        capture_output=True,
        text=True,
    )
    return {"stdout": result.stdout, "stderr": result.stderr}


@app.post("/codexify/create")
def codexify_create(req: NotionImportRequest):
    command = ["python", "guardian/codexify.py", "create"]
    if req.records:
        command.extend(["--records", req.records])
    if req.fieldmap:
        command.extend(["--fieldmap", req.fieldmap])
    if req.aliasmap:
        command.extend(["--aliasmap", req.aliasmap])
    if req.parent_id:
        command.extend(["--parent-id", req.parent_id])
    if req.parent_title:
        command.extend(["--parent-title", req.parent_title])
    if req.seed:
        command.append("--seed")
    if req.edit_aliases:
        command.append("--edit-aliases")
    result = subprocess.run(command, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr}
