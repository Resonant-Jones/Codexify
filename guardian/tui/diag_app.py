from __future__ import annotations
import io
from contextlib import redirect_stdout
import json
import os
import click
from textual.app import App, ComposeResult
try:
    # Textual < 1.0 used TextLog; 5.x provides Log
    from textual.widgets import ListView, ListItem, Label, TextLog as LogWidget
except ImportError:  # Textual 5.x
    from textual.widgets import ListView, ListItem, Label, Log as LogWidget
from textual.widgets import Input
from textual import on

from guardian.runtime.tools.invoker import invoke_tool, _resolve  # type: ignore
from guardian.runtime.tools.registry import ROOTS  # for listing
import os
import requests

def list_all_commands():
    names = []
    for prefix, root in ROOTS:
        ctx = click.Context(root)
        for n in root.list_commands(ctx):
            sub = root.get_command(ctx, n)
            fq = f"{prefix}:{n}" if prefix else n
            if isinstance(sub, click.MultiCommand):
                # Walk recursively
                stack = [(sub, fq)]
                while stack:
                    grp, pfx = stack.pop()
                    cctx = click.Context(grp)
                    for nn in grp.list_commands(cctx):
                        s2 = grp.get_command(cctx, nn)
                        fq2 = f"{pfx}:{nn}"
                        if isinstance(s2, click.MultiCommand):
                            stack.append((s2, fq2))
                        else:
                            names.append(fq2)
            else:
                names.append(fq)
    return sorted(names)

class DiagApp(App):
    CSS = (
        "Screen { layout: grid; grid-size: 2 2 }\n"
        "Input.error { border: heavy $error; }\n"
    )

    def on_mount(self) -> None:
        try:
            base = os.environ.get("GUARDIAN_API_BASE", "http://127.0.0.1:8888")

            self._write_log(f"API base: {base}")
            self._write_log(
                "Hint: use /save {\"title\":\"Sample\",\"body\":\"Preview only\",\"format\":\"md\",\"dry_run\":true} to preview."
            )
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        cmds = list_all_commands()
        self.cmds = ListView(*[ListItem(Label(c)) for c in cmds])
        self.log_widget = LogWidget()
        yield self.cmds
        yield self.log_widget
        self.input = Input(placeholder="Enter JSON args and press Enter (or leave blank for defaults)")
        yield self.input

    def _command_params(self, fq_name: str):
        """Return (param_list, defaults_dict) for a command name.
        Each param: {name, required, default, type, ...}
        Includes extra keys for 'choice' (choices) and 'path' (exists,file_okay,dir_okay).
        """
        try:
            cmd, _ = _resolve(fq_name)
            params = []
            defaults = {}
            for p in getattr(cmd, "params", []) or []:
                name = getattr(p, "name", None)
                if not name:
                    continue
                required = getattr(p, "required", False)
                default = getattr(p, "default", None)
                # infer type (+ extras)
                p_type = "string"
                extras = {}
                try:
                    if getattr(p, "is_flag", False):
                        p_type = "boolean"
                    else:
                        pt = getattr(p, "type", None)
                        if pt is not None:
                            # Choice type
                            choices = getattr(pt, "choices", None)
                            if choices is not None:
                                p_type = "choice"
                                try:
                                    extras["choices"] = list(choices)
                                except Exception:
                                    extras["choices"] = [str(c) for c in choices]
                            else:
                                # Path type (Click Path)
                                if (
                                    getattr(pt, "name", "").lower() == "path"
                                    or type(pt).__name__ == "Path"
                                ):
                                    p_type = "path"
                                    extras["exists"] = bool(getattr(pt, "exists", False))
                                    extras["file_okay"] = bool(getattr(pt, "file_okay", True))
                                    extras["dir_okay"] = bool(getattr(pt, "dir_okay", True))
                                else:
                                    tn = type(pt).__name__.lower()
                                    if "int" in tn:
                                        p_type = "integer"
                                    elif "float" in tn:
                                        p_type = "number"
                                    elif "bool" in tn:
                                        p_type = "boolean"
                except Exception:
                    pass
                entry = {
                    "name": name,
                    "required": required,
                    "default": default,
                    "type": p_type,
                }
                if extras:
                    entry.update(extras)
                params.append(entry)
                if default is not None:
                    defaults[name] = default
            return params, defaults
        except Exception:
            return [], {}

    def _write_log(self, text: str) -> None:
        lw = self.log_widget
        if hasattr(lw, "write"):
            lw.write(text)
        elif hasattr(lw, "write_line"):
            lw.write_line(text)
        else:
            # Last resort: update/append content if supported
            try:
                existing = getattr(lw, "renderable", "")
                content = f"{existing}\n{text}" if existing else text
                lw.update(content)
            except Exception:
                pass

    @on(ListView.Selected)
    def run_selected(self, event: ListView.Selected) -> None:
        fq_name = event.item.children[0].renderable
        self._write_log(f"Selected: {fq_name}")
        params, defaults = self._command_params(fq_name)
        self.pending_cmd = fq_name
        if params:
            # Show schema/help
            lines = ["Provide JSON args (name:value). Params:"]
            for p in params:
                dstr = f" default={p['default']!r}" if p.get("default") is not None else ""
                rq = " (required)" if p.get("required") else ""
                ptype = p.get('type', 'string')
                # Append choices inline when available
                extra = ""
                if ptype == "choice" and p.get("choices"):
                    opts = "|".join(map(str, p["choices"]))
                    extra = f": [{opts}]"
                t = f" ({ptype}{extra})"
                lines.append(f"- {p['name']}{t}{dstr}{rq}")
            self._write_log("\n".join(lines))
            self.input.value = json.dumps(defaults) if defaults else ""
            self.input.focus()
            return
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                result = invoke_tool(fq_name, args={})  # extend to prompt for args
            out = buf.getvalue()
            if out.strip():
                self._write_log(out)
            if result is not None:
                self._write_log(repr(result))
        except Exception as e:
            self._write_log(f"[error]{e}[/error]")

    @on(Input.Submitted)
    def _on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        # Special action: /save {json}
        if text.startswith("/save"):
            try:
                _, _, rest = text.partition(" ")
                args = json.loads(rest) if rest else {}
                if not isinstance(args, dict):
                    raise ValueError("Args must be a JSON object")
            except Exception as e:
                self._write_log(f"[error]Invalid /save JSON: {e}[/error]")
                return
            base = os.environ.get("GUARDIAN_API_BASE", "http://127.0.0.1:8080")
            try:
                r = requests.post(f"{base}/codexify/save-entry", json=args, timeout=30)
                if r.status_code >= 400:
                    try:
                        detail = r.json().get("detail")
                    except Exception:
                        detail = r.text
                    self._write_log(f"[error]Save-entry failed ({r.status_code}): {detail}[/error]")
                    return
                data = r.json()
                self._write_log(json.dumps(data, indent=2))
                files = data.get("files") or []
                if files:
                    lines = ["Drive links:"]
                    for f in files:
                        link = f.get("webViewLink") or f.get("webViewURL") or f.get("link")
                        name = f.get("name") or f.get("id")
                        if link:
                            lines.append(f" - {name}: {link}")
                    self._write_log("\n".join(lines))
            except Exception as e:
                self._write_log(f"[error]{e}[/error]")
            finally:
                self.input.value = ""
                return

        fq_name = getattr(self, "pending_cmd", None)
        if not fq_name:
            return
        
        # Standard tool invocation path
        try:
            args = json.loads(text) if text else {}
            if not isinstance(args, dict):
                raise ValueError("Args must be a JSON object")
        except Exception as e:
            self.input.add_class("error")
            self._write_log(f"[error]Invalid JSON: {e}[/error]")
            # Show expected params to help correct input
            try:
                params, _ = self._command_params(fq_name)
                if params:
                    lines = ["Expected params:"]
                    for p in params:
                        dstr = f" default={p['default']!r}" if p.get("default") is not None else ""
                        rq = " (required)" if p.get("required") else ""
                        ptype = p.get('type', 'string')
                        extra = ""
                        if ptype == "choice" and p.get("choices"):
                            opts = "|".join(map(str, p["choices"]))
                            extra = f": [{opts}]"
                        t = f" ({ptype}{extra})"
                        lines.append(f"- {p['name']}{t}{dstr}{rq}")
                    self._write_log("\n".join(lines))
            except Exception:
                pass
            return
        # Validate and coerce
        params, _defaults = self._command_params(fq_name)
        ok, coerced, errors = self._validate_and_coerce(args, params)
        if not ok:
            self.input.add_class("error")
            for err in errors:
                self._write_log(f"[error]{err}[/error]")
            self._write_log("Fix the errors and press Enter again.")
            return
        self.input.remove_class("error")
        # Small convenience: accept bare Google Drive folder IDs for a 'folder_url' arg
        try:
            if isinstance(coerced, dict) and isinstance(coerced.get("folder_url"), str):
                s = coerced["folder_url"].strip()
                import re as _re
                if _re.fullmatch(r"[A-Za-z0-9_-]{10,}", s):
                    coerced["folder_url"] = f"https://drive.google.com/drive/folders/{s}"
        except Exception:
            pass
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                result = invoke_tool(fq_name, args=coerced)
            out = buf.getvalue()
            if out.strip():
                self._write_log(out)
            if result is not None:
                self._write_log(repr(result))
        except Exception as e:
            self._write_log(f"[error]{e}[/error]")
            # Provide expected params to help user adjust args
            try:
                params, _ = self._command_params(fq_name)
                if params:
                    lines = ["Expected params:"]
                    for p in params:
                        dstr = f" default={p['default']!r}" if p.get("default") is not None else ""
                        rq = " (required)" if p.get("required") else ""
                        ptype = p.get('type', 'string')
                        extra = ""
                        if ptype == "choice" and p.get("choices"):
                            opts = "|".join(map(str, p["choices"]))
                            extra = f": [{opts}]"
                        t = f" ({ptype}{extra})"
                        lines.append(f"- {p['name']}{t}{dstr}{rq}")
                    self._write_log("\n".join(lines))
            except Exception:
                pass
        finally:
            self.pending_cmd = None
            self.input.value = ""

    @staticmethod
    def _coerce_value(val, typ: str):
        if typ == "boolean":
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                s = val.strip().lower()
                if s in ("true", "1", "yes", "y", "on"):
                    return True
                if s in ("false", "0", "no", "n", "off"):
                    return False
        if typ == "integer":
            if isinstance(val, int):
                return val
            if isinstance(val, str):
                s = val.strip()
                if s.lstrip("-").isdigit():
                    return int(s)
        if typ == "number":
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                try:
                    return float(val.strip())
                except Exception:
                    pass
        return val

    @staticmethod
    def _validate_and_coerce(args: dict, params: list[dict]) -> tuple[bool, dict, list[str]]:
        errors: list[str] = []
        out: dict = {}
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
            # Handle choice/path specially, else generic coercion
            if typ == "choice":
                choices = p.get("choices") or []
                vv = v if isinstance(v, str) else str(v)
                if vv not in choices:
                    errors.append(f"Param '{k}' must be one of {choices} (got '{v}')")
                coerced = vv
            elif typ == "path":
                path = str(v)
                exists_flag = bool(p.get("exists", False))
                file_okay = bool(p.get("file_okay", True))
                dir_okay = bool(p.get("dir_okay", True))
                if exists_flag:
                    if not os.path.exists(path):
                        errors.append(f"Param '{k}' path does not exist: {path}")
                    else:
                        if not file_okay and os.path.isfile(path):
                            errors.append(f"Param '{k}' must be a directory (got a file): {path}")
                        if not dir_okay and os.path.isdir(path):
                            errors.append(f"Param '{k}' must be a file (got a directory): {path}")
                coerced = path
            else:
                coerced = DiagApp._coerce_value(v, typ)
            # validate
            if typ == "integer" and not isinstance(coerced, int):
                errors.append(f"Param '{k}' must be an integer")
            elif typ == "number" and not isinstance(coerced, (int, float)):
                errors.append(f"Param '{k}' must be a number")
            elif typ == "boolean" and not isinstance(coerced, bool):
                errors.append(f"Param '{k}' must be a boolean (true/false)")
            out[k] = coerced
        return (len(errors) == 0), out, errors


def main():
    # Entry point for console_scripts launcher (guardian-diag)
    DiagApp().run()

if __name__ == "__main__":
    main()
