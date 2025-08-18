You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Show allowed choices inline in TUI parameter list

GOAL

- When listing params in guardian/tui/diag_app.py, append choices like:
  `name (choice: [opt1|opt2], default=...)`

PATCH
***Begin Patch
*** Update File: guardian/tui/diag_app.py
@@

-            if params:
-                _write_log(self.log_widget, "[bold]Params[/bold]:")
-                for p in params:
-                    req = "*" if p["required"] else " "
-                    _write_log(self.log_widget, f"  {req} {p['name']} ({p['type']}) default={p['default']}")

+            if params:
-                _write_log(self.log_widget, "[bold]Params[/bold]:")
-                for p in params:
-                    req = "*" if p["required"] else " "
-                    ptype = p.get("type","string")
-                    extra = ""
-                    if ptype == "choice" and p.get("choices"):
-                        opts = "|".join(map(str, p["choices"]))
-                        extra = f": [{opts}]"
-                    _write_log(
-                        self.log_widget,
-                        f"  {req} {p['name']} ({ptype}{extra}) default={p['default']}"
-                    )

*** End Patch
