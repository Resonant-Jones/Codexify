from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    RadioButton,
    RadioSet,
    Static,
)

from guardian.ops.setup_wizard import (
    DepStatus,
    default_env_target,
    detect_core_dependencies,
    write_env_file,
)


@dataclass
class WizardState:
    mode: str  # "fast" | "custom"
    deps: dict[str, DepStatus]
    openai_api_key: str = ""
    allow_cloud_providers: bool = True
    enable_discord: bool = False
    enable_notion: bool = False
    enable_github: bool = False
    deps_acknowledged: bool = False


class SetupWizardApp(App[Optional[str]]):
    CSS = """
    Screen { align: center middle; }
    #root {
      width: 90%;
      max-width: 120;
      height: auto;
      padding: 1;
      border: round $panel;
    }
    .row { height: auto; margin: 1 0; }
    .muted { color: $text-muted; }
    .danger { color: $error; }
    .ok { color: $success; }
    Input { width: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, repo_root: Path | None = None) -> None:
        super().__init__()
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.state = WizardState(mode="fast", deps=detect_core_dependencies())

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Container(id="root"):
            yield Static("Codexify Setup Wizard", classes="row")
            yield Static(
                "Fast setup gets you running quickly. "
                "Custom setup adds dependency paths and connector toggles.",
                classes="row muted",
            )

            with RadioSet(classes="row", id="mode"):
                yield RadioButton("Fast setup", value=True, id="mode_fast")
                yield RadioButton("Custom setup", value=False, id="mode_custom")

            yield Static("Dependency Scan", id="deps_title", classes="row")
            yield Static("", id="deps_body", classes="row")

            yield Static(
                "Custom binary paths (Custom setup only)", classes="row"
            )
            yield Input(
                placeholder="Docker binary path (optional)",
                id="docker_path",
                classes="row",
            )
            yield Input(
                placeholder="Ollama binary path (optional)",
                id="ollama_path",
                classes="row",
            )

            yield Static("OpenAI API Key (optional)", classes="row")
            yield Input(
                placeholder="sk-... (leave blank to skip)",
                password=True,
                id="openai_key",
                classes="row",
            )
            yield Static(
                "Fast setup can skip keys. You can re-run setup later.",
                classes="row muted",
            )

            yield Static("Custom options (Custom setup only)", classes="row")
            yield Checkbox(
                "Allow cloud providers",
                value=True,
                id="allow_cloud_providers",
                classes="row",
            )
            yield Checkbox(
                "Enable Notion connector",
                value=False,
                id="connector_notion",
                classes="row",
            )
            yield Checkbox(
                "Enable Discord connector",
                value=False,
                id="connector_discord",
                classes="row",
            )
            yield Checkbox(
                "Enable GitHub connector",
                value=False,
                id="connector_github",
                classes="row",
            )

            with Horizontal(classes="row"):
                yield Button("Re-scan deps", id="rescan", variant="default")
                yield Button("Continue", id="continue", variant="warning")
                yield Button("Write .env", id="write", variant="primary")
                yield Button("Cancel", id="cancel", variant="error")

            yield Static("", id="status", classes="row")

        yield Footer()

    def on_mount(self) -> None:
        self._apply_mode_ui()
        self._render_deps()

    def _current_custom_paths(self) -> dict[str, str]:
        if self.state.mode != "custom":
            return {}

        docker_path = self.query_one("#docker_path", Input).value.strip()
        ollama_path = self.query_one("#ollama_path", Input).value.strip()
        custom_paths: dict[str, str] = {}
        if docker_path:
            custom_paths["docker"] = docker_path
        if ollama_path:
            custom_paths["ollama"] = ollama_path
        return custom_paths

    def _scan_dependencies(self) -> None:
        self.state.deps = detect_core_dependencies(self._current_custom_paths())
        self.state.deps_acknowledged = False

    def _render_deps(self) -> None:
        body = self.query_one("#deps_body", Static)
        lines = []
        missing = False
        for _, dep in self.state.deps.items():
            if dep.is_present:
                lines.append(
                    f"[ok][OK][/ok] {dep.name} found at {dep.found_path}"
                )
            else:
                missing = True
                lines.append(
                    f"[danger][MISSING][/danger] {dep.name} not found. "
                    f"{dep.help_text}"
                )
        body.update("\n".join(lines))
        if missing:
            self._set_status(
                "Some dependencies are missing. Install them, then Re-scan, "
                "or Continue to write config anyway."
            )
        else:
            self._set_status("All scanned dependencies are available.")

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(msg)

    def _apply_mode_ui(self) -> None:
        custom_mode = self.state.mode == "custom"
        for widget_id in (
            "#docker_path",
            "#ollama_path",
            "#allow_cloud_providers",
            "#connector_notion",
            "#connector_discord",
            "#connector_github",
        ):
            self.query_one(widget_id).disabled = not custom_mode

        if not custom_mode:
            self.query_one("#allow_cloud_providers", Checkbox).value = True
            self.query_one("#connector_notion", Checkbox).value = False
            self.query_one("#connector_discord", Checkbox).value = False
            self.query_one("#connector_github", Checkbox).value = False

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        pressed_id = event.pressed.id if event.pressed else ""
        self.state.mode = "fast" if pressed_id == "mode_fast" else "custom"
        self._apply_mode_ui()
        self._scan_dependencies()
        self._render_deps()
        self._set_status(f"Mode selected: {self.state.mode}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "cancel":
            self.exit()
            return

        if button_id == "rescan":
            self._scan_dependencies()
            self._render_deps()
            self._set_status("Dependency scan refreshed.")
            return

        if button_id == "continue":
            self.state.deps_acknowledged = True
            self._set_status(
                "Continuing with current dependency state. "
                "You can still Re-scan before writing."
            )
            return

        if button_id != "write":
            return

        self.state.openai_api_key = self.query_one(
            "#openai_key", Input
        ).value.strip()

        if self.state.mode == "custom":
            self.state.allow_cloud_providers = self.query_one(
                "#allow_cloud_providers", Checkbox
            ).value
            self.state.enable_notion = self.query_one(
                "#connector_notion", Checkbox
            ).value
            self.state.enable_discord = self.query_one(
                "#connector_discord", Checkbox
            ).value
            self.state.enable_github = self.query_one(
                "#connector_github", Checkbox
            ).value
        else:
            self.state.allow_cloud_providers = True
            self.state.enable_notion = False
            self.state.enable_discord = False
            self.state.enable_github = False

        missing_deps = [
            dep for dep in self.state.deps.values() if not dep.is_present
        ]
        if missing_deps and not self.state.deps_acknowledged:
            self._set_status(
                "Missing dependencies detected. Choose Continue to accept "
                "this state, or Re-scan after installing."
            )
            return

        kv = {
            "ALLOW_CLOUD_PROVIDERS": (
                "true" if self.state.allow_cloud_providers else "false"
            ),
            "OPENAI_API_KEY": self.state.openai_api_key,
            "CONNECTOR_NOTION_ENABLED": (
                "true" if self.state.enable_notion else "false"
            ),
            "CONNECTOR_DISCORD_ENABLED": (
                "true" if self.state.enable_discord else "false"
            ),
            "CONNECTOR_GITHUB_ENABLED": (
                "true" if self.state.enable_github else "false"
            ),
        }
        for name, value in self._current_custom_paths().items():
            if name == "docker":
                kv["DOCKER_BIN"] = value
            if name == "ollama":
                kv["OLLAMA_BIN"] = value

        env_path = default_env_target(self.repo_root)
        write_env_file(env_path, kv)
        self.exit(
            result=(
                f"Wrote {env_path}.\n"
                f"Next steps:\n"
                f"1. Review generated values in {env_path.name}.\n"
                f"2. Start backend and UI when ready."
            )
        )


def run_setup_wizard(repo_root: Path | None = None) -> None:
    app = SetupWizardApp(repo_root=repo_root)
    result = app.run()
    if result:
        print(result)
