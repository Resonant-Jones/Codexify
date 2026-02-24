# guardian/routes/tools_manifest.py
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Request

from guardian.command_bus.manifest import build_manifest
from guardian.tools.derive import derive_tools_from_command_manifest

router = APIRouter()


@router.get("/api/tools/manifest")
def tools_manifest(request: Request):
    command_manifest = build_manifest(request.app).model_dump(mode="json")
    stable_manifest = dict(command_manifest)
    stable_manifest.pop("generated_at", None)
    tools = derive_tools_from_command_manifest(command_manifest)
    manifest_hash = hashlib.sha256(
        json.dumps(
            stable_manifest, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return {
        "tool_manifest_version": "2.0",
        "manifest_version": command_manifest.get("manifest_version", "1.0"),
        "generated_at": command_manifest.get("generated_at"),
        "command_manifest_hash": manifest_hash,
        "tools": [t.model_dump(mode="json") for t in tools],
        "openai_tools": [t.to_openai_function_tool() for t in tools],
    }
