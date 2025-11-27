🔥 nice — Codex shipped the type-aware validation cleanly and your tests still pass. That log means the JSON args box now checks booleans/ints/floats and skips execution on bad input.

Since you asked for Choice + Path validation too, here’s a ready‑to‑run Codex task that layers those on top of what you already have.

⸻

Paste this file: codex_tasks/2025-08-13-add-choice-and-path-validation.md

You are Codex. Apply the following patch set exactly.

INCLUDE GUARDRAILS

- Also load codex_tasks/safe_task.md and obey all guardrails.

TITLE: Extend TUI validation to support click.Choice and path existence checks

GOAL

- When a command parameter is a Click Choice, reject values not in the allowed set and show the allowed values.
- When a command parameter is a Click Path, check existence on disk (file or dir) per the parameter’s flags; show clear errors and skip execution if missing.
- Keep all existing behavior and tests passing.

PLAN

1) Enhance param introspection (`get_param_info`) to detect:
   - Choice options: collect `choices` into the param dict.
   - Path options: mark `type` as "path" and store flags (file_okay, dir_okay, exists).
2) Extend the validator:
   - If `type == "choice"`, ensure value ∈ choices.
   - If `type == "path"`, if `exists` is True (default in Click Path), `os.path.exists(value)` must be True; if `file_okay`/`dir_okay` are set, verify shape.
3) Keep UI feedback the same (red border + error lines) and do not change any command logic.

PATCH
***Begin Patch
*** Update File: guardian/tui/diag_app.py
@@
-from textual.widgets import ListView, ListItem, Label, Input
+from textual.widgets import ListView, ListItem, Label, Input
+import os
@@
-def get_param_info(fq_name: str) -> tuple[list[dict], dict]:
+def get_param_info(fq_name: str) -> tuple[list[dict], dict]:
@@

- for p in cmd.params:

+ for p in cmd.params:
         pname = getattr(p, "name", None)
         if not pname:
             continue
         required = getattr(p, "required", False)
         default = getattr(p, "default", None)

-        # crude type tag
-        ptype = "string"

+        # crude type tag (+ extras for choice/path)
-        ptype = "string"
-        pextras = {}
         if getattr(p, "is_flag", False):
             ptype = "boolean"
         else:
             pt = getattr(p, "type", None)
             if pt is not None:

-                tn = type(pt).__name__.lower()
-                if "int" in tn:
-                    ptype = "integer"
-                elif "float" in tn:
-                    ptype = "number"
-        params.append({"name": pname, "required": bool(required), "default": default, "type": ptype})

+                # Choice
-                choices = getattr(pt, "choices", None)
-                if choices is not None:
-                    ptype = "choice"
-                    pextras["choices"] = list(choices)
-                else:
-                    # Path (Click Path type has attributes: exists, file_okay, dir_okay)
-                    if hasattr(pt, "name") and getattr(pt, "name", "").lower() == "path" or \
-                       type(pt).__name__ == "Path":
-                        ptype = "path"
-                        pextras["exists"] = bool(getattr(pt, "exists", False))
-                        pextras["file_okay"] = bool(getattr(pt, "file_okay", True))
-                        pextras["dir_okay"] = bool(getattr(pt, "dir_okay", True))
-                    else:
-                        tn = type(pt).__name__.lower()
-                        if "int" in tn:
-                            ptype = "integer"
-                        elif "float" in tn:
-                            ptype = "number"
-        entry = {"name": pname, "required": bool(required), "default": default, "type": ptype}
-        if pextras:
-            entry.update(pextras)
-        params.append(entry)
         if default is not None:
             defaults[pname] = default
     return params, defaults
@@

- def _validate_and_coerce(args: dict, params: list[dict]) -> tuple[bool, dict, list[str]]:

+ def _validate_and_coerce(args: dict, params: list[dict]) -> tuple[bool, dict, list[str]]:
         errors: list[str] = []
         out = {}
         index = {p["name"]: p for p in params}
         # required check
         for name, p in index.items():
             if p.get("required") and name not in args:
                 errors.append(f"Missing required param: {name}")
         # type coercion
         for k, v in args.items():
             p = index.get(k)
             if not p:
                 out[k] = v  # allow extra keys
                 continue
             typ = p.get("type") or "string"

-            coerced = DiagApp._coerce_value(v, typ)

+            # choice validation
-            if typ == "choice":
-                choices = p.get("choices") or []
-                if isinstance(v, str):
-                    vv = v
-                else:
-                    vv = str(v)
-                if vv not in choices:
-                    errors.append(f"Param '{k}' must be one of {choices} (got '{v}')")
-                    out[k] = v
-                    continue
-                coerced = vv
-            # path validation
-            elif typ == "path":
-                path = str(v)
-                exists_flag = bool(p.get("exists", False))
-                file_okay = bool(p.get("file_okay", True))
-                dir_okay = bool(p.get("dir_okay", True))
-                if exists_flag:
-                    if not os.path.exists(path):
-                        errors.append(f"Param '{k}' path does not exist: {path}")
-                    else:
-                        if not file_okay and os.path.isfile(path):
-                            errors.append(f"Param '{k}' must be a directory (got a file): {path}")
-                        if not dir_okay and os.path.isdir(path):
-                            errors.append(f"Param '{k}' must be a file (got a directory): {path}")
-                coerced = path
-            else:
-                coerced = DiagApp._coerce_value(v, typ)
             # if integer expected but coercion failed (e.g., non-numeric string)
             if typ == "integer" and not isinstance(coerced, int):
                 errors.append(f"Param '{k}' must be an integer")
             elif typ == "number" and not isinstance(coerced, (int, float)):
                 errors.append(f"Param '{k}' must be a number")
             elif typ == "boolean" and not isinstance(coerced, bool):
                 errors.append(f"Param '{k}' must be a boolean (true/false)")
             out[k] = coerced
         return (len(errors) == 0), out, errors

*** End Patch

DIFF

- Show `/diff` and wait for approval.

RUN THESE COMMANDS MANUALLY

```bash
python -m pip install -e ".[tui]"
guardian-diag

ACCEPTANCE
 • For a Click.Choice param, entering an invalid value shows allowed options and prevents execution.
 • For a Click.Path param with exists=True, entering a non-existent path shows an error and prevents execution.
 • For Path with file_okay=False, providing a file path errors; likewise for dir_okay=False with a directory path.
 • Existing bool/int/number validation still works; valid input runs.
 • All tests pass: pytest -q.
