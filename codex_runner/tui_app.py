from __future__ import annotations

import copy
import shlex
import subprocess
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Static

try:
    from .tui_commands import (
        BOOLEAN_KEYS,
        VALUE_KEYS,
        ParsedCommand,
        apply_change,
        available_commands,
        coerce_value,
        filter_suggestions,
        parse_bool,
        parse_command,
        snapshot_summary,
        suggestion_pool,
    )
    from .tui_state import (
        PRESET_ALLOWED_KEYS,
        ProfileData,
        RunnerSettings,
        list_to_csv,
        load_profile_data,
        parse_csv_list,
        save_profile_data,
        settings_to_dict,
        to_cli_args,
    )
except ImportError:
    from tui_commands import (  # type: ignore
        BOOLEAN_KEYS,
        VALUE_KEYS,
        ParsedCommand,
        apply_change,
        available_commands,
        coerce_value,
        filter_suggestions,
        parse_bool,
        parse_command,
        snapshot_summary,
        suggestion_pool,
    )
    from tui_state import (  # type: ignore
        PRESET_ALLOWED_KEYS,
        ProfileData,
        RunnerSettings,
        list_to_csv,
        load_profile_data,
        parse_csv_list,
        save_profile_data,
        settings_to_dict,
        to_cli_args,
    )


PATH_FIELDS = [
    "repo_root",
    "audit_prompt_file",
    "audit_schema_file",
    "compiler_prompt_file",
    "campaign_set_schema_file",
    "task_result_schema_file",
]


class PreviewScreen(ModalScreen[bool]):
    CSS = """
    #preview {
        width: 80%;
        max-width: 120;
        height: 65%;
        border: tall $accent;
        background: $surface;
        padding: 1 2;
    }
    #preview-command {
        border: round $panel;
        padding: 1;
        height: 1fr;
        overflow: auto;
    }
    #preview-actions {
        margin-top: 1;
        height: auto;
    }
    """

    def __init__(self, command: str, allow_run: bool) -> None:
        super().__init__()
        self.command = command
        self.allow_run = allow_run

    def compose(self) -> ComposeResult:
        with Container(id="preview"):
            yield Static("Command Preview")
            yield Static(self.command, id="preview-command")
            with Horizontal(id="preview-actions"):
                if self.allow_run:
                    yield Button("Run", id="preview-run", variant="success")
                yield Button("Close", id="preview-close")

    def key_escape(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "preview-run")


class ValidationErrorsScreen(ModalScreen[None]):
    CSS = """
    #validation {
        width: 80%;
        max-width: 120;
        height: 60%;
        border: tall $error;
        background: $surface;
        padding: 1 2;
    }
    #validation-list {
        border: round $panel;
        padding: 1;
        height: 1fr;
        overflow: auto;
    }
    """

    def __init__(self, errors: list[str]) -> None:
        super().__init__()
        self.errors = errors

    def compose(self) -> ComposeResult:
        with Container(id="validation"):
            yield Static("Validation Errors", id="validation-title")
            yield Static(
                "\n".join(f"- {error}" for error in self.errors),
                id="validation-list",
            )
            yield Button("Close", id="validation-close")

    def key_escape(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "validation-close":
            self.dismiss(None)


class PathEditorScreen(ModalScreen[dict[str, str] | None]):
    CSS = """
    #paths {
        width: 85%;
        max-width: 130;
        height: 70%;
        border: tall $accent;
        background: $surface;
        padding: 1 2;
    }
    .path-row {
        margin-bottom: 1;
    }
    .path-label {
        width: 28;
    }
    .path-input {
        width: 1fr;
    }
    #paths-list {
        height: 1fr;
        overflow: auto;
    }
    """

    def __init__(self, values: dict[str, str]) -> None:
        super().__init__()
        self.values = values

    def compose(self) -> ComposeResult:
        with Container(id="paths"):
            yield Static("Edit Paths")
            with Container(id="paths-list"):
                for key in PATH_FIELDS:
                    yield Horizontal(
                        Static(key, classes="path-label"),
                        Input(
                            value=self.values.get(key, ""),
                            id=f"path-{key}",
                            classes="path-input",
                        ),
                        classes="path-row",
                    )
            with Horizontal():
                yield Button(
                    "Apply to Staged", id="paths-apply", variant="success"
                )
                yield Button("Cancel", id="paths-cancel")

    def key_escape(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "paths-cancel":
            self.dismiss(None)
            return
        if event.button.id == "paths-apply":
            payload: dict[str, str] = {}
            for key in PATH_FIELDS:
                payload[key] = self.query_one(
                    f"#path-{key}", Input
                ).value.strip()
            self.dismiss(payload)


class CampaignRunnerTUI(App[list[str] | None]):
    CSS = """
    #main {
        height: 1fr;
        padding: 1;
    }
    .card {
        border: round $panel;
        padding: 1;
        margin-bottom: 1;
    }
    .title {
        text-style: bold;
        margin-bottom: 1;
    }
    #command-bar {
        dock: bottom;
        height: 4;
        border-top: solid $panel;
        padding: 0 1;
    }
    #command-input {
        width: 1fr;
    }
    #suggestions {
        height: 2;
        overflow: hidden;
    }
    #status {
        height: 1;
        text-style: dim;
    }
    """

    BINDINGS = [
        Binding("/", "focus_command", "Command"),
        Binding("ctrl+s", "save_profile", "Save"),
        Binding("ctrl+r", "strict_run", "Run"),
        Binding("meta+enter", "instant_run", "Instant Run"),
        Binding("ctrl+enter", "instant_run", "Instant Run"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self, initial_args: list[str] | None = None) -> None:
        super().__init__()
        self.initial_args = initial_args or []
        profile = load_profile_data(cwd=Path.cwd())
        self.active_settings = self._apply_initial_overrides(
            profile.settings, self.initial_args
        )
        self.staged_settings = copy.deepcopy(self.active_settings)
        self.has_staged_changes = False
        self.presets = dict(profile.presets)
        self.suggestions: list[str] = []
        self._pending_run_args: list[str] | None = None
        self._event_log: list[str] = list(profile.warnings[-3:])

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Container(id="main"):
            with Container(classes="card"):
                yield Static("Codexify Campaign Runner", classes="title")
                yield Static(id="active-summary")
            with Container(classes="card"):
                yield Static("Staged Changes", classes="title")
                yield Static(id="staged-summary")
            with Container(classes="card"):
                yield Static("Cheatsheet", classes="title")
                yield Static(
                    "/set key value | /toggle key | /preset name | /apply | /discard | /preview | /run | /save | /edit-paths | /help"
                )
            with Container(classes="card"):
                yield Static("Recent", classes="title")
                yield Static(id="events")

        with Container(id="command-bar"):
            yield Input(
                placeholder="Type command (e.g., /set provider claude)",
                id="command-input",
            )
            yield Static(id="suggestions")
            yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#command-input", Input).focus()
        self._refresh_view("Ready")

    def _active_view(self) -> RunnerSettings:
        return self.active_settings

    def _staged_deltas(self) -> dict[str, tuple[object, object]]:
        active = settings_to_dict(self.active_settings)
        staged = settings_to_dict(self.staged_settings)
        deltas: dict[str, tuple[object, object]] = {}
        for key in sorted(staged.keys()):
            if active.get(key) != staged.get(key):
                deltas[key] = (active.get(key), staged.get(key))
        return deltas

    def _append_event(self, text: str) -> None:
        self._event_log.append(text)
        self._event_log = self._event_log[-6:]

    def _refresh_view(self, status: str | None = None) -> None:
        deltas = self._staged_deltas()
        self.has_staged_changes = bool(deltas)
        try:
            active_summary = snapshot_summary(self.active_settings)
            active_lines = [
                f"{k}: {active_summary[k]}"
                for k in sorted(active_summary.keys())
            ]
            self.query_one("#active-summary", Static).update(
                "\n".join(active_lines)
            )

            if deltas:
                staged_lines = [
                    f"{key}: {before} -> {after}"
                    for key, (before, after) in deltas.items()
                ]
            else:
                staged_lines = ["(none)"]
            self.query_one("#staged-summary", Static).update(
                "\n".join(staged_lines)
            )

            if self._event_log:
                self.query_one("#events", Static).update(
                    "\n".join(self._event_log[-4:])
                )
            else:
                self.query_one("#events", Static).update("(no events)")

            if status is not None:
                self.query_one("#status", Static).update(status)

            self._refresh_suggestions(
                self.query_one("#command-input", Input).value
            )
        except NoMatches:
            # Some unit tests call command handlers without mounted widgets.
            return

    def _refresh_suggestions(self, query: str) -> None:
        pool = suggestion_pool(
            self.staged_settings,
            settings_to_dict(self.staged_settings),
            list(self.presets.keys()),
        )
        self.suggestions = filter_suggestions(pool, query)
        preview = (
            " | ".join(self.suggestions[:5])
            if self.suggestions
            else "(no suggestions)"
        )
        try:
            self.query_one("#suggestions", Static).update(preview)
        except NoMatches:
            return

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "command-input":
            self._refresh_suggestions(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "command-input":
            self._execute_command(event.value.strip(), instant=False)

    def _coerce_key(self, raw_key: str) -> str:
        key = raw_key.strip().lower()
        if key in BOOLEAN_KEYS:
            return BOOLEAN_KEYS[key]
        return key

    def _validate_settings(self, settings: RunnerSettings) -> list[str]:
        errors: list[str] = []

        if settings.provider not in {"codex", "claude"}:
            errors.append("Provider must be either 'codex' or 'claude'.")
        if settings.passes < 1:
            errors.append("passes must be >= 1")

        repo_root = Path(settings.repo_root).expanduser()
        if not repo_root.exists() or not repo_root.is_dir():
            errors.append(
                f"Repo root does not exist or is not a directory: {repo_root}"
            )
        else:
            try:
                git_check = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=str(repo_root),
                    text=True,
                    capture_output=True,
                    check=False,
                )
            except FileNotFoundError:
                errors.append("git executable not found on PATH.")
            else:
                if git_check.returncode != 0:
                    errors.append(
                        f"Repo root is not a git repository: {repo_root}"
                    )
                else:
                    expected_root = Path(git_check.stdout.strip()).resolve()
                    if expected_root != repo_root.resolve():
                        errors.append(
                            f"Repo root must be git top-level (expected {expected_root}, got {repo_root.resolve()})."
                        )

        required_paths = [
            ("Audit prompt", settings.audit_prompt_file),
            ("Audit schema", settings.audit_schema_file),
            ("Compiler prompt", settings.compiler_prompt_file),
            ("Campaign set schema", settings.campaign_set_schema_file),
            ("Task result schema", settings.task_result_schema_file),
        ]
        for label, raw in required_paths:
            path = Path(raw).expanduser()
            if not path.exists():
                errors.append(f"{label} file not found: {path}")
        return errors

    def _show_validation_errors(self, errors: list[str]) -> None:
        self.push_screen(ValidationErrorsScreen(errors))

    def _commit_staged(self) -> None:
        self.active_settings = copy.deepcopy(self.staged_settings)

    def _apply_staged(self, *, validate: bool) -> bool:
        if not self.has_staged_changes:
            return True
        if validate:
            errors = self._validate_settings(self.staged_settings)
            if errors:
                self._show_validation_errors(errors)
                self._append_event("Apply blocked by validation")
                self._refresh_view("Validation failed")
                return False
        self._commit_staged()
        self._append_event("Applied staged changes")
        self._refresh_view("Applied")
        return True

    def _save_profile(self) -> None:
        profile = ProfileData(
            settings=self.active_settings,
            presets=self.presets,
            warnings=[],
        )
        save_profile_data(profile)
        self._append_event("Saved profile")
        self._refresh_view("Saved profile")

    def _preview_command_text(self, settings: RunnerSettings) -> str:
        runner_path = Path(__file__).resolve().parent / "runner.py"
        args = to_cli_args(settings)
        escaped = " ".join(shlex.quote(part) for part in args)
        return f"python {shlex.quote(str(runner_path))} {escaped}".strip()

    def _try_run(self, *, strict: bool, instant: bool) -> None:
        if strict and self.has_staged_changes:
            self._refresh_view(
                "Run blocked: staged changes present, use /apply"
            )
            return

        run_settings = self.active_settings
        if instant and self.has_staged_changes:
            self._commit_staged()
            run_settings = self.active_settings
            self._append_event("Instant run auto-applied staged changes")

        if strict:
            errors = self._validate_settings(run_settings)
            if errors:
                self._show_validation_errors(errors)
                self._append_event("Run blocked by validation")
                self._refresh_view("Validation failed")
                return

        args = to_cli_args(run_settings)
        if strict:
            preview = self._preview_command_text(run_settings)
            self._pending_run_args = args
            self.push_screen(
                PreviewScreen(preview, allow_run=True),
                callback=self._on_preview_closed,
            )
            return

        self._pending_run_args = None
        self.exit(args)

    def _on_preview_closed(self, should_run: bool) -> None:
        if not should_run:
            self._refresh_view("Run canceled")
            return
        if self._pending_run_args is None:
            self._refresh_view("Run canceled: missing command")
            return
        args = self._pending_run_args
        self._pending_run_args = None
        self.exit(args)

    def _execute_command(self, text: str, *, instant: bool) -> None:
        command = parse_command(text)
        if command is None:
            self._refresh_view("No command")
            return

        try:
            self._dispatch_command(command, instant=instant)
        except ValueError as exc:
            self._append_event(f"Error: {exc}")
            self._refresh_view(str(exc))
            return

        try:
            self.query_one("#command-input", Input).value = ""
            self.query_one("#command-input", Input).focus()
        except NoMatches:
            return

    def _dispatch_command(
        self, command: ParsedCommand, *, instant: bool
    ) -> None:
        if command.name not in available_commands():
            raise ValueError(f"Unknown command: {command.name}")

        if command.name == "help":
            self._append_event(
                "Commands: /set /toggle /preset /apply /discard /preview /run /save /edit-paths /help /quit"
            )
            self._refresh_view("Help shown")
            return

        if command.name == "quit":
            self.action_quit_app()
            return

        if command.name == "set":
            if len(command.args) < 2:
                raise ValueError("Usage: /set <key> <value>")
            key = self._coerce_key(command.args[0])
            if key not in VALUE_KEYS and key not in BOOLEAN_KEYS.values():
                raise ValueError(f"Unknown setting key: {key}")
            raw_value = " ".join(command.args[1:])
            if key in BOOLEAN_KEYS.values():
                parsed_bool = parse_bool(raw_value)
                if parsed_bool is None:
                    raise ValueError(f"{key} expects true/false")
                apply_change(self.staged_settings, key, parsed_bool)
            else:
                value = coerce_value(key, raw_value)
                apply_change(self.staged_settings, key, value)
            self._append_event(f"Staged {key}")
            self._refresh_view("Staged")
            return

        if command.name == "toggle":
            if len(command.args) != 1:
                raise ValueError(
                    "Usage: /toggle <verify|branch|fallback|debug>"
                )
            key = self._coerce_key(command.args[0])
            if key not in BOOLEAN_KEYS.values():
                raise ValueError(f"Not a toggle key: {key}")
            current = bool(getattr(self.staged_settings, key))
            apply_change(self.staged_settings, key, not current)
            self._append_event(f"Toggled {key}")
            self._refresh_view("Toggled")
            return

        if command.name == "preset":
            if len(command.args) != 1:
                raise ValueError("Usage: /preset <name>")
            name = command.args[0]
            preset = self.presets.get(name)
            if preset is None:
                raise ValueError(f"Preset not found: {name}")
            for key, value in preset.items():
                if key in PRESET_ALLOWED_KEYS:
                    apply_change(self.staged_settings, key, value)
            self._append_event(f"Applied preset to staged: {name}")
            self._refresh_view("Preset staged")
            return

        if command.name == "discard":
            self.staged_settings = copy.deepcopy(self.active_settings)
            self._append_event("Discarded staged changes")
            self._refresh_view("Discarded")
            return

        if command.name == "apply":
            self._apply_staged(validate=True)
            return

        if command.name == "save":
            self._save_profile()
            return

        if command.name == "preview":
            preview = self._preview_command_text(self.staged_settings)
            self.push_screen(PreviewScreen(preview, allow_run=False))
            self._refresh_view("Preview opened")
            return

        if command.name == "run":
            self._try_run(strict=True, instant=instant)
            return

        if command.name == "edit-paths":
            values = {
                key: str(getattr(self.staged_settings, key))
                for key in PATH_FIELDS
            }
            self.push_screen(
                PathEditorScreen(values), callback=self._on_paths_closed
            )
            return

    def _on_paths_closed(self, payload: dict[str, str] | None) -> None:
        if not payload:
            self._refresh_view("Path edit canceled")
            return
        for key, value in payload.items():
            if key in PATH_FIELDS:
                apply_change(self.staged_settings, key, value)
        self._append_event("Staged path edits")
        self._refresh_view("Path edits staged")

    def action_focus_command(self) -> None:
        self.query_one("#command-input", Input).focus()

    def action_save_profile(self) -> None:
        self._save_profile()

    def action_strict_run(self) -> None:
        self._try_run(strict=True, instant=False)

    def action_instant_run(self) -> None:
        input_box = self.query_one("#command-input", Input)
        if input_box.value.strip().startswith("/"):
            self._execute_command(input_box.value.strip(), instant=True)
            return
        self._try_run(strict=False, instant=True)

    def action_quit_app(self) -> None:
        self.exit(None)

    def _apply_initial_overrides(
        self, settings: RunnerSettings, args: list[str]
    ) -> RunnerSettings:
        updated = copy.deepcopy(settings)
        i = 0
        while i < len(args):
            part = args[i]
            next_value = args[i + 1] if i + 1 < len(args) else None
            if part == "--provider" and next_value:
                updated.provider = next_value.strip().lower()
                i += 2
                continue
            if part == "--repo-root" and next_value:
                updated.repo_root = next_value
                i += 2
                continue
            if part == "--audit-prompt-file" and next_value:
                updated.audit_prompt_file = next_value
                i += 2
                continue
            if part == "--audit-schema-file" and next_value:
                updated.audit_schema_file = next_value
                i += 2
                continue
            if part == "--compiler-prompt-file" and next_value:
                updated.compiler_prompt_file = next_value
                i += 2
                continue
            if part == "--campaign-set-schema-file" and next_value:
                updated.campaign_set_schema_file = next_value
                i += 2
                continue
            if part == "--task-result-schema-file" and next_value:
                updated.task_result_schema_file = next_value
                i += 2
                continue
            if part == "--passes" and next_value:
                try:
                    updated.passes = max(1, int(next_value))
                except ValueError:
                    pass
                i += 2
                continue
            if part == "--base-ref" and next_value:
                updated.base_ref = next_value
                i += 2
                continue
            if part == "--execute":
                updated.execute_mode = "execute"
                i += 1
                continue
            if part == "--dry-run":
                updated.execute_mode = "dry-run"
                i += 1
                continue
            if part == "--branch-per-campaign":
                updated.branch_per_campaign = True
                i += 1
                continue
            if part == "--no-branch-per-campaign":
                updated.branch_per_campaign = False
                i += 1
                continue
            if part == "--verify":
                updated.verify = True
                i += 1
                continue
            if part == "--no-verify":
                updated.verify = False
                i += 1
                continue
            if part == "--allow-discovery-fallback":
                updated.allow_discovery_fallback = True
                i += 1
                continue
            if part == "--debug":
                updated.debug = True
                i += 1
                continue
            if part == "--codex-model" and next_value:
                updated.codex_model = next_value
                i += 2
                continue
            if part == "--codex-model-audit" and next_value:
                updated.codex_model_audit = next_value
                i += 2
                continue
            if part == "--codex-model-compiler" and next_value:
                updated.codex_model_compiler = next_value
                i += 2
                continue
            if part == "--codex-model-task" and next_value:
                updated.codex_model_task = next_value
                i += 2
                continue
            if part == "--claude-model" and next_value:
                updated.claude_model = next_value
                i += 2
                continue
            if part == "--claude-model-audit" and next_value:
                updated.claude_model_audit = next_value
                i += 2
                continue
            if part == "--claude-model-compiler" and next_value:
                updated.claude_model_compiler = next_value
                i += 2
                continue
            if part == "--claude-model-task" and next_value:
                updated.claude_model_task = next_value
                i += 2
                continue
            if part == "--codex-config" and next_value:
                updated.codex_config = [*updated.codex_config, next_value]
                i += 2
                continue
            if part == "--claude-settings" and next_value:
                updated.claude_settings = [*updated.claude_settings, next_value]
                i += 2
                continue
            i += 1
        if updated.provider not in {"codex", "claude"}:
            updated.provider = "codex"
        return updated


def launch_tui(initial_args: list[str] | None = None) -> list[str] | None:
    app = CampaignRunnerTUI(initial_args=initial_args)
    return app.run()
