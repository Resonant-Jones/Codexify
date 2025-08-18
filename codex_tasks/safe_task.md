from __future__ import annotations
import io
import json
from contextlib import redirect_stdout
import click

from textual.app import App, ComposeResult
from textual import on
from textual.widgets import ListView, ListItem, Label, Input

# Textual log widget compatibility: TextLog (older) → Log (Textual ≥5)
try:
    from textual.widgets import TextLog as _LogWidget
except Exception:  # Textual ≥5.x
    from textual.widgets import Log as _LogWidget

# Tool routing & enumeration
from guardian.runtime.tools.invoker import invoke_tool, _resolve
from guardian.runtime.tools.registry import ROOTS


def _write_log(log_widget, text: str):
    """Write text to the log widget across Textual versions."""
    for method_name in ("write", "write_line", "update"):
        fn = getattr(log_widget, method_name, None)
        if callable(fn):
            try:
                return fn(text)
            except TypeError:
                continue
    print(text)


def list_all_commands() -> list[str]:
    names: list[str] = []

    def walk_group(group, prefix: str = ""):
        ctx = click.Context(group)
        for name in group.list_commands(ctx):
            sub = group.get_command(ctx, name)
            fq = f"{prefix}:{name}" if prefix else name
            if hasattr(sub, "list_commands"):  # group
                walk_group(sub, fq)
            else:
                names.append(fq)

    for prefix, root in ROOTS:
        if hasattr(root, "list_commands"):
            walk_group(root, prefix)
        else:
            # single command root (rare)
            names.append(prefix or getattr(root, "name", "root"))

    return sorted(names)


def get_param_info(fq_name: str) -> tuple[list[dict], dict]:
    """Return (params, default_args) for a command.
    Each param dict has: name, required(bool), default(any or None), type(str)
    default_args: JSON-serializable dict of defaults (omit None).
    """
    cmd, _canonical = _resolve(fq_name)
    params: list[dict] = []
    defaults: dict = {}
    for p in cmd.params:
        pname = getattr(p, "name", None)
        if not pname:
            continue
        required = getattr(p, "required", False)
        default = getattr(p, "default", None)
        # crude type tag
        ptype = "string"
        if getattr(p, "is_flag", False):
            ptype = "boolean"
        else:
            pt = getattr(p, "type", None)
            if pt is not None:
                tn = type(pt).__name__.lower()
                if "int" in tn:
                    ptype = "integer"
                elif "float" in tn:
                    ptype = "number"
        params.append({"name": pname, "required": bool(required), "default": default, "type": ptype})
        if default is not None:
            defaults[pname] = default
    return params, defaults


class DiagApp(App):
    CSS = """
    Screen { layout: grid; grid-size: 2 2; }
    #left  { grid-column: 1; grid-row: 1 / span 2; }
    #log   { grid-column: 2; grid-row: 1; }
    #input { grid-column: 2; grid-row: 2; }
    """

    def compose(self) -> ComposeResult:
        self.cmds = ListView(id="left")
        for n in list_all_commands():
            self.cmds.append(ListItem(Label(n)))
        self.log = _LogWidget(id="log")
        self.arg_input = Input(placeholder="JSON args (e.g. {\"use_openai\": false}) — Leave empty for defaults", id="input")
        yield self.cmds
        yield self.log
        yield self.arg_input

    @on(ListView.Highlighted)
    def on_highlight(self, event: ListView.Highlighted) -> None:
        name = event.item.children[0].renderable
        _write_log(self.log, f"Selected: {name}")

    @on(ListView.Selected)
    def on_selected(self, event: ListView.Selected) -> None:
        fq_name = event.item.children[0].renderable
        # Show params & prefill defaults JSON
        try:
            params, defaults = get_param_info(fq_name)
            self.log.clear()
            _write_log(self.log, f"[bold]Command[/bold]: {fq_name}")
            if params:
                _write_log(self.log, "[bold]Params[/bold]:")
                for p in params:
                    req = "*" if p["required"] else " "
                    _write_log(self.log, f"  {req} {p['name']} ({p['type']}) default={p['default']}")
            else:
                _write_log(self.log, "(no parameters)")
            self.arg_input.value = json.dumps(defaults) if defaults else ""
        except Exception as e:
            _write_log(self.log, f"[error]Param introspection failed: {e}[/error]")
            self.arg_input.value = ""

    @on(Input.Submitted)
    def on_submit(self, event: Input.Submitted) -> None:
        # Run the currently highlighted command with provided JSON args
        item = self.cmds.highlighted_child
        if not item:
            _write_log(self.log, "[error]No command selected[/error]")
            return
        fq_name = item.children[0].renderable
        raw = (event.value or "").strip()
        try:
            if raw:
                args = json.loads(raw)
                if not isinstance(args, dict):
                    raise ValueError("Top-level JSON must be an object of param→value")
            else:
                # If empty, use defaults
                _params, defaults = get_param_info(fq_name)
                args = defaults
        except Exception as e:
            _write_log(self.log, f"[error]Bad JSON: {e}[/error]")
            return

        buf = io.StringIO()
        try:
            _write_log(self.log, f"Running: {fq_name} with args: {args}")
            with redirect_stdout(buf):
                result = invoke_tool(fq_name, args=args)
            out = buf.getvalue()
            if out.strip():
                _write_log(self.log, out)
            if result is not None:
                _write_log(self.log, f"Result: {result}")
        except Exception as e:
            _write_log(self.log, f"[error]{e}[/error]")


def main():
    DiagApp().run()


if __name__ == "__main__":
    main()
