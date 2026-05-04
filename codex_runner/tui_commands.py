from __future__ import annotations

from dataclasses import dataclass

from tui_state import RunnerSettings

BOOLEAN_KEYS = {
    "verify": "verify",
    "branch": "branch_per_campaign",
    "branch_per_campaign": "branch_per_campaign",
    "fallback": "allow_discovery_fallback",
    "allow_discovery_fallback": "allow_discovery_fallback",
    "debug": "debug",
}

VALUE_KEYS = {
    "provider",
    "passes",
    "execute_mode",
    "base_ref",
    "repo_root",
    "audit_prompt_file",
    "audit_schema_file",
    "compiler_prompt_file",
    "campaign_set_schema_file",
    "task_result_schema_file",
    "codex_model",
    "codex_model_audit",
    "codex_model_compiler",
    "codex_model_task",
    "codex_config",
    "claude_model",
    "claude_model_audit",
    "claude_model_compiler",
    "claude_model_task",
    "claude_settings",
}


@dataclass
class ParsedCommand:
    name: str
    args: list[str]


def parse_command(text: str) -> ParsedCommand | None:
    value = text.strip()
    if not value:
        return None
    if value.startswith("/"):
        value = value[1:]
    parts = [part for part in value.split() if part]
    if not parts:
        return None
    return ParsedCommand(name=parts[0].lower(), args=parts[1:])


def available_commands() -> list[str]:
    return [
        "set",
        "toggle",
        "preset",
        "apply",
        "discard",
        "preview",
        "run",
        "save",
        "edit-paths",
        "help",
        "quit",
    ]


def suggestion_pool(
    settings: RunnerSettings,
    staged: dict[str, object],
    preset_names: list[str],
) -> list[str]:
    _ = settings
    _ = staged
    rows: list[str] = [
        "/set provider codex",
        "/set provider claude",
        "/set passes 1",
        "/set execute_mode dry-run",
        "/set execute_mode execute",
        "/set base_ref HEAD",
        "/toggle verify",
        "/toggle branch",
        "/toggle fallback",
        "/toggle debug",
        "/apply",
        "/discard",
        "/preview",
        "/run",
        "/save",
        "/edit-paths",
        "/help",
        "/quit",
    ]
    for name in sorted(preset_names):
        rows.append(f"/preset {name}")
    return rows


def filter_suggestions(items: list[str], query: str) -> list[str]:
    text = query.strip().lower()
    if not text:
        return items[:25]
    tokens = text.split()
    output: list[str] = []
    for item in items:
        lowered = item.lower()
        if all(token in lowered for token in tokens):
            output.append(item)
    return output[:25]


def parse_bool(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return None


def coerce_value(key: str, raw: str) -> object:
    value = raw.strip()
    if key == "provider":
        lowered = value.lower()
        if lowered not in {"codex", "claude"}:
            raise ValueError("provider must be codex or claude")
        return lowered
    if key == "passes":
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError("passes must be an integer") from exc
        if parsed < 1:
            raise ValueError("passes must be >= 1")
        return parsed
    if key == "execute_mode":
        lowered = value.lower()
        if lowered not in {"dry-run", "execute"}:
            raise ValueError("execute_mode must be dry-run or execute")
        return lowered
    if key in {"codex_config", "claude_settings"}:
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


def apply_change(settings: RunnerSettings, key: str, value: object) -> None:
    if not hasattr(settings, key):
        raise ValueError(f"unknown setting: {key}")
    setattr(settings, key, value)


def snapshot_summary(settings: RunnerSettings) -> dict[str, object]:
    return {
        "provider": settings.provider,
        "passes": settings.passes,
        "execute_mode": settings.execute_mode,
        "verify": settings.verify,
        "branch_per_campaign": settings.branch_per_campaign,
        "allow_discovery_fallback": settings.allow_discovery_fallback,
        "debug": settings.debug,
    }
