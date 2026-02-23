import logging
import traceback
from typing import Any, Dict, List

import click
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from guardian.command_bus.manifest import build_manifest
from guardian.runtime.tools.invoker import invoke_tool
from guardian.runtime.tools.policy import require_confirm
from guardian.runtime.tools.registry import ROOTS, generate_tools_manifest
from guardian.server.codexify_api import SaveEntryRequest, save_entry

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/tools", tags=["tools"])
DEPRECATION_PHASE = "1.5"
MANIFEST_REPLACED_BY = "/api/guardian/commands/manifest"


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = {}


def _manifest_deprecation_headers() -> dict[str, str]:
    return {
        "X-Codexify-Deprecated": "true",
        "X-Codexify-Deprecation-Replaced-By": MANIFEST_REPLACED_BY,
        "X-Codexify-Deprecation-Phase": DEPRECATION_PHASE,
    }


def _legacy_manifest_from_command_bus(request: Request) -> List[Dict[str, Any]]:
    manifest = build_manifest(request.app)
    payload: List[Dict[str, Any]] = []
    for command in manifest.commands:
        payload.append(
            {
                "name": command.command_id,
                "description": f"{command.method} {command.path_template}",
                "command_id": command.command_id,
                "aliases": list(command.aliases),
                "method": command.method,
                "path_template": command.path_template,
                "operation_id": command.operation_id,
                "risk": command.risk,
                "effect": command.effect,
                "idempotency": command.idempotency,
                "approval_mode": command.approval_mode,
                "args_schema": command.input_schema,
            }
        )
    return payload


@router.get("/manifest")
def manifest(request: Request, response: Response) -> List[Dict[str, Any]]:
    for key, value in _manifest_deprecation_headers().items():
        response.headers[key] = value
    subject = request.headers.get("X-User-Id", "").strip() or "-"
    logger.info(
        "legacy_tools_shim path=%s subject=%s command_id=%s",
        request.url.path,
        subject,
        "-",
    )
    try:
        return _legacy_manifest_from_command_bus(request)
    except Exception:
        # Keep fallback behavior if command bus manifest generation fails.
        logger.exception(
            "legacy_tools_shim manifest fallback to runtime registry"
        )
        return generate_tools_manifest()


@router.post("/call")
def call(payload: ToolCall):
    try:
        # Special-case HTTP-backed tool
        if payload.name == "codexify.save_entry":
            try:
                req = SaveEntryRequest(**(payload.arguments or {}))
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid arguments: {e}"
                )
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
                raise HTTPException(
                    status_code=400, detail=f"Invalid arguments: {e}"
                )
            result = save_entry(req)
            if not confirm:
                return {
                    "ok": True,
                    "result": result,
                    "message": "Preview generated. Call again with confirm:true to save.",
                }
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
                    params.append(
                        {
                            "name": pname,
                            "required": required,
                            "default": default,
                        }
                    )
                expected = params
        except Exception:
            expected = None

        # Log server-side traceback for debugging
        logger.error(
            "/tools/call error for %s: %s\n%s",
            payload.name,
            e,
            traceback.format_exc(),
        )

        detail: Dict[str, Any] = {"error": str(e)}
        if expected is not None:
            detail["expected_params"] = expected
        raise HTTPException(status_code=400, detail=detail)
