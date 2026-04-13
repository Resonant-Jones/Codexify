from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

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
    InstallerBootstrapState,
    default_env_target,
    default_installer_state_path,
    detect_core_dependencies,
    write_env_file,
    write_installer_state_file,
)

logger = __import__("logging").getLogger(__name__)


@dataclass
class WizardState:
    mode: str  # "fast" | "custom"
    deps: dict[str, DepStatus]
    openai_api_key: str = ""
    allow_cloud_providers: bool = True
    runtime_profile: str = "docker"  # "docker" | "external"
    enable_notion: bool = False
    enable_github: bool = False

    notion_api_key: str = ""
    notion_target_mode: str = "database"  # "database" | "page"
    notion_databases: str = ""
    notion_default_database: str = ""
    notion_parent_page_id: str = ""
    github_token: str = ""
    guardian_database_url: str = ""
    redis_url: str = ""
    neo4j_url: str = ""

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
    .hidden { display: none; }
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
            yield Static(
                "Runtime Profile (Custom only)",
                id="runtime_profile_title",
                classes="row hidden",
            )
            with RadioSet(
                classes="row hidden",
                id="runtime_profile",
            ):
                yield RadioButton(
                    "Docker stack (recommended)",
                    value=True,
                    id="runtime_docker",
                )
                yield RadioButton(
                    "External services (advanced)",
                    value=False,
                    id="runtime_external",
                )
            yield Static(
                "GUARDIAN_DATABASE_URL (required for external profile)",
                id="external_db_label",
                classes="row hidden",
            )
            yield Input(
                placeholder="postgresql://user:pass@host:5432/codexify",
                id="external_db_url",
                classes="row hidden",
            )
            yield Static(
                "External Postgres must be a dedicated Codexify database.\n"
                "Codexify will run migrations to create/upgrade tables.",
                id="external_db_note",
                classes="row muted hidden",
            )
            yield Input(
                placeholder="REDIS_URL (optional)",
                id="external_redis_url",
                classes="row hidden",
            )
            yield Input(
                placeholder="NEO4J_URL (optional)",
                id="external_neo4j_url",
                classes="row hidden",
            )

            yield Static(
                "Connectors (Custom only)",
                id="connectors_title",
                classes="row hidden",
            )

            yield Checkbox(
                "Enable Notion connector",
                value=False,
                id="chk_notion",
                classes="row hidden",
            )
            yield Input(
                placeholder="Notion API key (required if enabled)",
                password=True,
                id="notion_key",
                classes="row hidden",
            )
            with RadioSet(
                id="notion_target_mode",
                classes="row hidden",
            ):
                yield RadioButton(
                    "Target existing database(s) (recommended)",
                    value=True,
                    id="notion_target_database",
                )
                yield RadioButton(
                    "Codexify-managed page (advanced)",
                    value=False,
                    id="notion_target_page",
                )
            yield Input(
                placeholder="NOTION_DATABASES (csv: name:id,name2:id2 or id1,id2)",
                id="notion_databases",
                classes="row hidden",
            )
            yield Input(
                placeholder="NOTION_DEFAULT_DATABASE (optional name or id)",
                id="notion_default_database",
                classes="row hidden",
            )
            yield Input(
                placeholder="NOTION_PARENT_PAGE_ID (required in page mode)",
                id="notion_parent_page_id",
                classes="row hidden",
            )

            yield Checkbox(
                "Enable GitHub connector",
                value=False,
                id="chk_github",
                classes="row hidden",
            )
            yield Input(
                placeholder="GitHub token (required if enabled)",
                password=True,
                id="github_token",
                classes="row hidden",
            )

            yield Static(
                "Connector credentials are stored in .env. Treat it as a secret file.",
                id="connectors_note",
                classes="row muted hidden",
            )

            with Horizontal(classes="row"):
                yield Button("Re-scan deps", id="rescan", variant="default")
                yield Button("Continue", id="continue", variant="warning")
                yield Button("Write .env", id="write", variant="primary")
                yield Button("Cancel", id="cancel", variant="error")

            yield Static("", id="status", classes="row")

        yield Footer()

    def on_mount(self) -> None:
        self._apply_mode_visibility()
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
                    f"[danger][MISSING][/danger] {dep.name} not found. {dep.help_text}"
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

    def _apply_mode_visibility(self) -> None:
        is_custom = self.state.mode == "custom"

        for widget_id in (
            "#docker_path",
            "#ollama_path",
            "#allow_cloud_providers",
        ):
            self.query_one(widget_id).disabled = not is_custom

        for widget_id in (
            "#runtime_profile_title",
            "#runtime_profile",
            "#connectors_title",
            "#chk_notion",
            "#notion_target_mode",
            "#chk_github",
            "#connectors_note",
        ):
            widget = self.query_one(widget_id)
            widget.set_class(not is_custom, "hidden")
            if isinstance(widget, Checkbox):
                widget.disabled = not is_custom

        if not is_custom:
            self.query_one("#allow_cloud_providers", Checkbox).value = True
            self.query_one("#chk_notion", Checkbox).value = False
            self.query_one("#chk_github", Checkbox).value = False

            self.state.enable_notion = False
            self.state.enable_github = False
            self.state.notion_api_key = ""
            self.state.notion_target_mode = "database"
            self.state.notion_databases = ""
            self.state.notion_default_database = ""
            self.state.notion_parent_page_id = ""
            self.state.github_token = ""
            self.state.runtime_profile = "docker"
            self.query_one("#runtime_docker", RadioButton).value = True
            self.query_one("#runtime_external", RadioButton).value = False
            self.query_one("#notion_target_database", RadioButton).value = True
            self.query_one("#notion_target_page", RadioButton).value = False
            self.state.guardian_database_url = ""
            self.state.redis_url = ""
            self.state.neo4j_url = ""

        self._apply_runtime_profile_visibility()
        self._apply_connector_credential_visibility()

    def _apply_runtime_profile_visibility(self) -> None:
        is_custom = self.state.mode == "custom"
        is_external = is_custom and self.state.runtime_profile == "external"

        for widget_id in (
            "#external_db_label",
            "#external_db_url",
            "#external_db_note",
            "#external_redis_url",
            "#external_neo4j_url",
        ):
            widget = self.query_one(widget_id)
            widget.set_class(not is_external, "hidden")

        if not is_external:
            self.state.guardian_database_url = ""
            self.state.redis_url = ""
            self.state.neo4j_url = ""

    def _apply_connector_credential_visibility(self) -> None:
        is_custom = self.state.mode == "custom"

        notion_input = self.query_one("#notion_key")
        notion_target_mode = self.query_one("#notion_target_mode")
        notion_databases_input = self.query_one("#notion_databases")
        notion_default_database_input = self.query_one(
            "#notion_default_database"
        )
        notion_parent_page_input = self.query_one("#notion_parent_page_id")
        github_input = self.query_one("#github_token")

        notion_enabled = is_custom and self.state.enable_notion
        notion_database_mode = (
            notion_enabled and self.state.notion_target_mode == "database"
        )
        notion_page_mode = (
            notion_enabled and self.state.notion_target_mode == "page"
        )

        notion_input.set_class(not notion_enabled, "hidden")
        notion_target_mode.set_class(not notion_enabled, "hidden")
        notion_databases_input.set_class(not notion_database_mode, "hidden")
        notion_default_database_input.set_class(
            not notion_database_mode, "hidden"
        )
        notion_parent_page_input.set_class(not notion_page_mode, "hidden")
        github_input.set_class(
            not (is_custom and self.state.enable_github), "hidden"
        )

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        radio_set_id = event.radio_set.id if event.radio_set else ""
        pressed_id = event.pressed.id if event.pressed else ""

        if radio_set_id == "mode":
            self.state.mode = "fast" if pressed_id == "mode_fast" else "custom"
            self._apply_mode_visibility()
            self._scan_dependencies()
            self._render_deps()
            self._set_status(f"Mode selected: {self.state.mode}")
            return

        if radio_set_id == "runtime_profile":
            self.state.runtime_profile = (
                "docker" if pressed_id == "runtime_docker" else "external"
            )
            self._apply_runtime_profile_visibility()
            self._set_status(f"Runtime profile: {self.state.runtime_profile}")
            return

        if radio_set_id == "notion_target_mode":
            self.state.notion_target_mode = (
                "database" if pressed_id == "notion_target_database" else "page"
            )
            self._apply_connector_credential_visibility()
            self._set_status(
                f"Notion target mode: {self.state.notion_target_mode}"
            )

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox_id = event.checkbox.id
        if checkbox_id == "chk_notion":
            self.state.enable_notion = bool(event.value)
        elif checkbox_id == "chk_github":
            self.state.enable_github = bool(event.value)
        else:
            return

        self._apply_connector_credential_visibility()

    def _validate_custom_inputs(self) -> str | None:
        if self.state.mode != "custom":
            return None

        guardian_database_url = self.query_one(
            "#external_db_url", Input
        ).value.strip()
        redis_url = self.query_one("#external_redis_url", Input).value.strip()
        neo4j_url = self.query_one("#external_neo4j_url", Input).value.strip()

        if (
            self.state.runtime_profile == "external"
            and not guardian_database_url
        ):
            return "External services profile requires GUARDIAN_DATABASE_URL."

        self.state.guardian_database_url = (
            guardian_database_url
            if self.state.runtime_profile == "external"
            else ""
        )
        self.state.redis_url = (
            redis_url if self.state.runtime_profile == "external" else ""
        )
        self.state.neo4j_url = (
            neo4j_url if self.state.runtime_profile == "external" else ""
        )

        notion_key = self.query_one("#notion_key", Input).value.strip()
        notion_databases = self.query_one(
            "#notion_databases", Input
        ).value.strip()
        notion_default_database = self.query_one(
            "#notion_default_database", Input
        ).value.strip()
        notion_parent_page_id = self.query_one(
            "#notion_parent_page_id", Input
        ).value.strip()
        github_token = self.query_one("#github_token", Input).value.strip()

        if self.state.enable_notion and not notion_key:
            return "Notion is enabled but Notion API key is missing."
        if (
            self.state.enable_notion
            and self.state.notion_target_mode == "database"
            and not notion_databases
        ):
            return "Notion database target mode requires NOTION_DATABASES."
        if (
            self.state.enable_notion
            and self.state.notion_target_mode == "page"
            and not notion_parent_page_id
        ):
            return "Notion page target mode requires NOTION_PARENT_PAGE_ID."
        if self.state.enable_github and not github_token:
            return "GitHub is enabled but GitHub token is missing."

        self.state.notion_api_key = notion_key
        self.state.notion_databases = (
            notion_databases if self.state.enable_notion else ""
        )
        self.state.notion_default_database = (
            notion_default_database if self.state.enable_notion else ""
        )
        self.state.notion_parent_page_id = (
            notion_parent_page_id if self.state.enable_notion else ""
        )
        self.state.github_token = github_token
        return None

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
            self.state.runtime_profile = (
                "docker"
                if self.query_one("#runtime_docker", RadioButton).value
                else "external"
            )
            self.state.notion_target_mode = (
                "database"
                if self.query_one("#notion_target_database", RadioButton).value
                else "page"
            )
            self.state.enable_notion = self.query_one(
                "#chk_notion", Checkbox
            ).value
            self.state.enable_github = self.query_one(
                "#chk_github", Checkbox
            ).value
        else:
            self.state.allow_cloud_providers = True
            self.state.runtime_profile = "docker"
            self.state.enable_notion = False
            self.state.enable_github = False
            self.state.notion_api_key = ""
            self.state.notion_target_mode = "database"
            self.state.notion_databases = ""
            self.state.notion_default_database = ""
            self.state.notion_parent_page_id = ""
            self.state.github_token = ""
            self.state.guardian_database_url = ""
            self.state.redis_url = ""
            self.state.neo4j_url = ""

        missing_deps = [
            dep for dep in self.state.deps.values() if not dep.is_present
        ]
        if missing_deps and not self.state.deps_acknowledged:
            self._set_status(
                "Missing dependencies detected. Choose Continue to accept "
                "this state, or Re-scan after installing."
            )
            return

        validation_error = self._validate_custom_inputs()
        if validation_error:
            self._set_status(f"[danger]{validation_error}[/danger]")
            return

        kv: dict[str, str] = {
            "ALLOW_CLOUD_PROVIDERS": "true"
            if self.state.allow_cloud_providers
            else "false",
            "OPENAI_API_KEY": self.state.openai_api_key,
            "CONNECTOR_NOTION_ENABLED": "true"
            if self.state.enable_notion
            else "false",
            "CONNECTOR_GITHUB_ENABLED": "true"
            if self.state.enable_github
            else "false",
            "NOTION_API_KEY": self.state.notion_api_key
            if self.state.enable_notion
            else "",
            "NOTION_TARGET_MODE": self.state.notion_target_mode
            if self.state.enable_notion
            else "",
            "NOTION_DATABASES": (
                self.state.notion_databases
                if self.state.enable_notion
                and self.state.notion_target_mode == "database"
                else ""
            ),
            "NOTION_DEFAULT_DATABASE": (
                self.state.notion_default_database
                if self.state.enable_notion
                and self.state.notion_target_mode == "database"
                else ""
            ),
            "NOTION_PARENT_PAGE_ID": (
                self.state.notion_parent_page_id
                if self.state.enable_notion
                and self.state.notion_target_mode == "page"
                else ""
            ),
            "NOTION_DATABASE_ID": "",
            "GITHUB_TOKEN": self.state.github_token
            if self.state.enable_github
            else "",
        }

        if (
            self.state.enable_notion
            and self.state.notion_target_mode == "database"
        ):
            entries = [
                part.strip()
                for part in self.state.notion_databases.split(",")
                if part.strip()
            ]
            single_default_empty = (
                not self.state.notion_default_database.strip()
            )
            if len(entries) == 1 and single_default_empty:
                token = entries[0]
                notion_database_id = (
                    token.split(":", 1)[1].strip() if ":" in token else token
                )
                kv["NOTION_DATABASE_ID"] = notion_database_id

        for name, value in self._current_custom_paths().items():
            if name == "docker":
                kv["DOCKER_BIN"] = value
            if name == "ollama":
                kv["OLLAMA_BIN"] = value

        if (
            self.state.mode == "custom"
            and self.state.runtime_profile == "external"
        ):
            if self.state.guardian_database_url:
                kv["GUARDIAN_DATABASE_URL"] = self.state.guardian_database_url
            if self.state.redis_url:
                kv["REDIS_URL"] = self.state.redis_url
            if self.state.neo4j_url:
                kv["NEO4J_URL"] = self.state.neo4j_url

        env_path = default_env_target(self.repo_root)
        # Newer setup flow seeds from template at repo_root (if supported by write_env_file)
        try:
            write_env_file(env_path, kv, repo_root=self.repo_root)
        except TypeError:
            # Back-compat with older signature
            write_env_file(env_path, kv)

        installer_state_path = default_installer_state_path(self.repo_root)
        installer_state = InstallerBootstrapState(
            setup_complete=True,
            runtime_profile=self.state.runtime_profile,
            allow_cloud_providers=self.state.allow_cloud_providers,
            env_path=str(env_path),
            last_updated_at=datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
        )
        write_installer_state_file(installer_state_path, installer_state)

        self.exit(
            result=(
                f"Wrote {env_path}.\n"
                f"Saved bootstrap state to {installer_state_path}.\n"
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


def write_wizard_env(
    *, repo_root: Path, selections: Mapping[str, str], env_name: str = ".env"
) -> Path:
    """Programmatic helper to write the wizard .env.

    The caller provides wizard selections; these values overlay template defaults
    when `write_env_file` supports `repo_root`.
    """
    root = Path(repo_root)
    env_path = root / env_name
    overrides = {k: str(v) for k, v in selections.items()}
    try:
        return write_env_file(env_path, overrides, repo_root=root)
    except TypeError:
        write_env_file(env_path, overrides)
        return env_path
