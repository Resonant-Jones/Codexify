You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Improve /tools/call error responses (detail + expected params)

GOAL

- When a tool call fails, return a 400 with a clear message and (if possible) expected params.
- Log the original exception for debugging.

PATCH
***Begin Patch
*** Update File: guardian/server/tools_api.py
@@
-from fastapi import APIRouter, HTTPException
+from fastapi import APIRouter, HTTPException
 from pydantic import BaseModel
 from typing import Any, Dict, List
@@
-from guardian.runtime.tools.manifest_service import get_manifest
-from guardian.runtime.tools.call_router import call_tool
+from guardian.runtime.tools.manifest_service import get_manifest
+from guardian.runtime.tools.call_router import call_tool
+from guardian.runtime.tools.registry import ROOTS
+import traceback, logging
+logger = logging.getLogger(__name__)
@@
 @router.post("/call")
 def tools_call(payload: ToolCall):
     try:
         result = call_tool(payload.name, payload.arguments)
         return {"ok": True, "result": result}
     except Exception as e:

-        raise HTTPException(status_code=400, detail=str(e))

+        # Try to look up expected params for nicer errors
-        expected = None
-        try:
-            import click
-            name = payload.name
-            def walk(group, prefix=""):
-                ctx = click.Context(group)
-                for nm in group.list_commands(ctx):
-                    sub = group.get_command(ctx, nm)
-                    fq = f"{prefix}:{nm}" if prefix else nm
-                    if fq == name:
-                        return sub
-                    if hasattr(sub, "list_commands"):
-                        found = walk(sub, fq)
-                        if found: return found
-                return None
-            cmd = None
-            for prefix, root in ROOTS:
-                target = walk(root, prefix)
-                if target:
-                    cmd = target
-                    break
-            if cmd:
-                params = []
-                for p in cmd.params:
-                    pname = getattr(p, "name", None)
-                    if not pname: continue
-                    required = bool(getattr(p, "required", False))
-                    default = getattr(p, "default", None)
-                    params.append({"name": pname, "required": required, "default": default})
-                expected = params
-        except Exception:
-            pass
-        # Log traceback server-side
-        logger.error("tools_call error: %s\n%s", e, traceback.format_exc())
-        detail = {"error": str(e)}
-        if expected is not None:
-            detail["expected_params"] = expected
-        raise HTTPException(status_code=400, detail=detail)

*** End Patch
