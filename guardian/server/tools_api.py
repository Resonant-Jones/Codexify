from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List

from guardian.runtime.tools.registry import generate_tools_manifest, ROOTS
from guardian.server.codexify_api import save_entry, SaveEntryRequest
from guardian.runtime.tools.invoker import invoke_tool
from guardian.runtime.tools.policy import require_confirm
import logging
import traceback
import click

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/tools", tags=["tools"])


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = {}


@router.get("/manifest")
def manifest() -> List[Dict[str, Any]]:
    return generate_tools_manifest()


@router.post("/call")
def call(payload: ToolCall):
    try:
        # Special-case HTTP-backed tool
        if payload.name == "codexify.save_entry":
            try:
                req = SaveEntryRequest(**(payload.arguments or {}))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid arguments: {e}")
            result = save_entry(req)
            return {"ok": True, "result": result}
        if payload.name == "codexify.confirm_and_save":
            args = payload.arguments or {}
            try:
                confirm = bool(args.get("confirm", False))
                req_data = {
                    "title": args.get("title"),
                    "body": args.get("body", ""),
                    "format": args.get("format", "md"),
                    "folder": args.get("folder"),
                    "folder_url": args.get("folder_url"),
                    "return_links": bool(args.get("return_links", True)),
                    "dry_run": False if confirm else True,
                }
                req = SaveEntryRequest(**req_data)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid arguments: {e}")
            result = save_entry(req)
            if not confirm:
                return {"ok": True, "result": result, "message": "Preview generated. Call again with confirm:true to save."}
            return {"ok": True, "result": result}
        require_confirm(payload.name, payload.arguments or {})
        result = invoke_tool(payload.name, payload.arguments or {})
        return {"ok": True, "result": result}
    except Exception as e:
        # Try to enrich error with expected params
        expected = None
        try:
            target_name = payload.name

            def walk(group, prefix=""):
                ctx = click.Context(group)
                for nm in group.list_commands(ctx):
                    sub = group.get_command(ctx, nm)
                    fq = f"{prefix}:{nm}" if prefix else nm
                    if fq == target_name:
                        return sub
                    if hasattr(sub, "list_commands"):
                        found = walk(sub, fq)
                        if found:
                            return found
                return None

            cmd = None
            for prefix, root in ROOTS:
                found = walk(root, prefix)
                if found:
                    cmd = found
                    break
            if cmd is not None:
                params = []
                for p in getattr(cmd, "params", []) or []:
                    pname = getattr(p, "name", None)
                    if not pname:
                        continue
                    required = bool(getattr(p, "required", False))
                    default = getattr(p, "default", None)
                    params.append({"name": pname, "required": required, "default": default})
                expected = params
        except Exception:
            expected = None

        # Log server-side traceback for debugging
        logger.error("/tools/call error for %s: %s\n%s", payload.name, e, traceback.format_exc())

        detail: Dict[str, Any] = {"error": str(e)}
        if expected is not None:
            detail["expected_params"] = expected
        raise HTTPException(status_code=400, detail=detail)
