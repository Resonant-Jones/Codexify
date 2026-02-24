# guardian/routes/tools_manifest.py
from __future__ import annotations

from fastapi import APIRouter, Request

from guardian.tools.registry import ToolRegistry

router = APIRouter()

# In real code: attach to app.state.tool_registry
_registry = ToolRegistry()


@router.get("/api/tools/manifest")
def tools_manifest(request: Request):
    return {
        "tool_manifest_version": "1.0",
        "tools": [t.model_dump() for t in _registry.list()],
    }
