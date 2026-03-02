from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_PATH = Path.home() / ".config" / "campaign_runner" / "settings.toml"

PRESET_ALLOWED_KEYS = {
    "provider",
    "passes",
    "execute_mode",
    "verify",
    "branch_per_campaign",
    "allow_discovery_fallback",
    "base_ref",
    "codex_model",
    "codex_model_audit",
    "codex_model_compiler",
    "codex_model_task",
    "claude_model",
    "claude_model_audit",
    "claude_model_compiler",
    "claude_model_task",
}


@dataclass
class RunnerSettings:
    provider: str = "codex"

    repo_root: str = ""
    audit_prompt_file: str = ""
    audit_schema_file: str = ""
    compiler_prompt_file: str = ""
    campaign_set_schema_file: str = ""
    task_result_schema_file: str = ""

    passes: int = 1
    base_ref: str = "HEAD"
    execute_mode: str = "dry-run"

    branch_per_campaign: bool = True
    allow_discovery_fallback: bool = False
    auto_commit: bool = True
    verify: bool = False
    debug: bool = False

    codex_model: str = ""
    codex_model_audit: str = ""
    codex_model_compiler: str = ""
    codex_model_task: str = ""
    codex_config: list[str] = field(default_factory=list)

    claude_model: str = ""
    claude_model_audit: str = ""
    claude_model_compiler: str = ""
    claude_model_task: str = ""
    claude_settings: list[str] = field(default_factory=list)


@dataclass
class ProfileData:
    settings: RunnerSettings
    presets: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def default_verify(ci_env: str | None) -> bool:
    if not ci_env:
        return False
    return ci_env.strip().lower() in {"1", "true", "yes", "on"}


def default_repo_root(cwd: Path | None = None) -> str:
    probe = (cwd or Path.cwd()).expanduser().resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(probe),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return str(probe)
    if result.returncode == 0 and result.stdout.strip():
        return str(Path(result.stdout.strip()).expanduser().resolve())
    return str(probe)


def default_settings(cwd: Path | None = None) -> RunnerSettings:
    root = default_repo_root(cwd)
    return RunnerSettings(
        provider="codex",
        repo_root=root,
        audit_prompt_file=str(SCRIPT_DIR / "prompts" / "mega_audit.md"),
        audit_schema_file=str(
            SCRIPT_DIR / "schemas" / "mega_audit_output.schema.json"
        ),
        compiler_prompt_file=str(
            SCRIPT_DIR / "prompts" / "audit_report_to_campaign_runner.md"
        ),
        campaign_set_schema_file=str(
            SCRIPT_DIR / "schemas" / "campaign_set.schema.json"
        ),
        task_result_schema_file=str(
            SCRIPT_DIR / "schemas" / "task_result.schema.json"
        ),
        passes=1,
        base_ref="HEAD",
        execute_mode="dry-run",
        branch_per_campaign=True,
        allow_discovery_fallback=False,
        auto_commit=True,
        verify=default_verify(os.environ.get("CI")),
        debug=False,
    )


def _coerce_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return fallback


def _coerce_str(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    return str(value)


def _coerce_list(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return list(fallback)
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _coerce_provider(value: Any, fallback: str) -> str:
    provider = _coerce_str(value, fallback).strip().lower()
    if provider in {"codex", "claude"}:
        return provider
    return fallback


def _coerce_execute_mode(value: Any, fallback: str) -> str:
    mode = _coerce_str(value, fallback).strip().lower()
    if mode in {"dry-run", "execute"}:
        return mode
    return fallback


def settings_from_dict(
    raw: dict[str, Any], base: RunnerSettings
) -> RunnerSettings:
    passes_raw = raw.get("passes", base.passes)
    try:
        passes_value = int(passes_raw)
    except (TypeError, ValueError):
        passes_value = base.passes
    if passes_value < 1:
        passes_value = 1

    return RunnerSettings(
        provider=_coerce_provider(raw.get("provider"), base.provider),
        repo_root=_coerce_str(raw.get("repo_root"), base.repo_root),
        audit_prompt_file=_coerce_str(
            raw.get("audit_prompt_file"), base.audit_prompt_file
        ),
        audit_schema_file=_coerce_str(
            raw.get("audit_schema_file"), base.audit_schema_file
        ),
        compiler_prompt_file=_coerce_str(
            raw.get("compiler_prompt_file"), base.compiler_prompt_file
        ),
        campaign_set_schema_file=_coerce_str(
            raw.get("campaign_set_schema_file"), base.campaign_set_schema_file
        ),
        task_result_schema_file=_coerce_str(
            raw.get("task_result_schema_file"), base.task_result_schema_file
        ),
        passes=passes_value,
        base_ref=_coerce_str(raw.get("base_ref"), base.base_ref),
        execute_mode=_coerce_execute_mode(
            raw.get("execute_mode"), base.execute_mode
        ),
        branch_per_campaign=_coerce_bool(
            raw.get("branch_per_campaign"), base.branch_per_campaign
        ),
        allow_discovery_fallback=_coerce_bool(
            raw.get("allow_discovery_fallback"),
            base.allow_discovery_fallback,
        ),
        auto_commit=True,
        verify=_coerce_bool(raw.get("verify"), base.verify),
        debug=_coerce_bool(raw.get("debug"), base.debug),
        codex_model=_coerce_str(raw.get("codex_model"), base.codex_model),
        codex_model_audit=_coerce_str(
            raw.get("codex_model_audit"), base.codex_model_audit
        ),
        codex_model_compiler=_coerce_str(
            raw.get("codex_model_compiler"), base.codex_model_compiler
        ),
        codex_model_task=_coerce_str(
            raw.get("codex_model_task"), base.codex_model_task
        ),
        codex_config=_coerce_list(raw.get("codex_config"), base.codex_config),
        claude_model=_coerce_str(raw.get("claude_model"), base.claude_model),
        claude_model_audit=_coerce_str(
            raw.get("claude_model_audit"), base.claude_model_audit
        ),
        claude_model_compiler=_coerce_str(
            raw.get("claude_model_compiler"), base.claude_model_compiler
        ),
        claude_model_task=_coerce_str(
            raw.get("claude_model_task"), base.claude_model_task
        ),
        claude_settings=_coerce_list(
            raw.get("claude_settings"), base.claude_settings
        ),
    )


def load_profile(cwd: Path | None = None) -> RunnerSettings:
    base = default_settings(cwd=cwd)
    profile = load_profile_data(cwd=cwd)
    return profile.settings


def _normalize_preset_map(
    raw_presets: Any,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not isinstance(raw_presets, dict):
        return {}, []
    normalized: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for name, value in raw_presets.items():
        if not isinstance(name, str):
            warnings.append("Skipped preset with non-string name.")
            continue
        if not isinstance(value, dict):
            warnings.append(
                f"Skipped preset '{name}' because it is not a table."
            )
            continue
        filtered: dict[str, Any] = {}
        for key, preset_value in value.items():
            if key not in PRESET_ALLOWED_KEYS:
                warnings.append(
                    f"Ignored unknown preset key '{key}' in preset '{name}'."
                )
                continue
            filtered[key] = preset_value
        normalized[name] = filtered
    return normalized, warnings


def load_profile_data(cwd: Path | None = None) -> ProfileData:
    base = default_settings(cwd=cwd)
    if not PROFILE_PATH.exists():
        return ProfileData(settings=base)

    try:
        try:
            import tomllib  # type: ignore
        except ModuleNotFoundError:  # pragma: no cover
            import tomli as tomllib  # type: ignore
        with PROFILE_PATH.open("rb") as handle:
            raw = tomllib.load(handle)
    except Exception:
        return ProfileData(settings=base)

    if not isinstance(raw, dict):
        return ProfileData(settings=base)

    raw_presets = raw.get("presets", {})
    normalized_presets, warnings = _normalize_preset_map(raw_presets)

    merged_raw = dict(raw)
    merged_raw.pop("presets", None)
    settings = settings_from_dict(merged_raw, base)
    return ProfileData(
        settings=settings, presets=normalized_presets, warnings=warnings
    )


def settings_to_dict(settings: RunnerSettings) -> dict[str, Any]:
    return {
        "provider": settings.provider,
        "repo_root": settings.repo_root,
        "audit_prompt_file": settings.audit_prompt_file,
        "audit_schema_file": settings.audit_schema_file,
        "compiler_prompt_file": settings.compiler_prompt_file,
        "campaign_set_schema_file": settings.campaign_set_schema_file,
        "task_result_schema_file": settings.task_result_schema_file,
        "passes": settings.passes,
        "base_ref": settings.base_ref,
        "execute_mode": settings.execute_mode,
        "branch_per_campaign": settings.branch_per_campaign,
        "allow_discovery_fallback": settings.allow_discovery_fallback,
        "auto_commit": True,
        "verify": settings.verify,
        "debug": settings.debug,
        "codex_model": settings.codex_model,
        "codex_model_audit": settings.codex_model_audit,
        "codex_model_compiler": settings.codex_model_compiler,
        "codex_model_task": settings.codex_model_task,
        "codex_config": list(settings.codex_config),
        "claude_model": settings.claude_model,
        "claude_model_audit": settings.claude_model_audit,
        "claude_model_compiler": settings.claude_model_compiler,
        "claude_model_task": settings.claude_model_task,
        "claude_settings": list(settings.claude_settings),
    }


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


def save_profile(settings: RunnerSettings) -> None:
    save_profile_data(ProfileData(settings=settings, presets={}, warnings=[]))


def save_profile_data(profile: ProfileData) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = settings_to_dict(profile.settings)
    lines = ["# Codexify Campaign Runner persisted settings"]
    for key in sorted(payload.keys()):
        lines.append(f"{key} = {_toml_value(payload[key])}")
    if profile.presets:
        for preset_name in sorted(profile.presets.keys()):
            lines.append("")
            lines.append(f"[presets.{preset_name}]")
            preset_values = profile.presets[preset_name]
            for key in sorted(preset_values.keys()):
                if key not in PRESET_ALLOWED_KEYS:
                    continue
                lines.append(f"{key} = {_toml_value(preset_values[key])}")
    PROFILE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_csv_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def list_to_csv(items: list[str]) -> str:
    return ", ".join(item for item in items if item)


def to_cli_args(
    settings: RunnerSettings,
    *,
    minimal: bool = True,
    cwd: Path | None = None,
) -> list[str]:
    """Render CLI args for runner.py.

    By default we emit a *minimal* argument list (only flags that differ from
    `default_settings()`), so common runs don't require managing many flags.

    Set `minimal=False` to force the full, explicit flag set.
    """
    base = default_settings(cwd=cwd)

    def differs(value: object, base_value: object) -> bool:
        return value != base_value

    args: list[str] = []

    # Only include provider when it differs from the default.
    if not minimal or differs(settings.provider, base.provider):
        args.extend(["--provider", settings.provider])

    # repo-root: if omitted, runner defaults should take over (typically CWD).
    if not minimal or differs(settings.repo_root, base.repo_root):
        args.extend(["--repo-root", settings.repo_root])

    # Path fields: only include if they differ from defaults.
    if not minimal or differs(
        settings.audit_prompt_file, base.audit_prompt_file
    ):
        args.extend(["--audit-prompt-file", settings.audit_prompt_file])
    if not minimal or differs(
        settings.audit_schema_file, base.audit_schema_file
    ):
        args.extend(["--audit-schema-file", settings.audit_schema_file])
    if not minimal or differs(
        settings.compiler_prompt_file, base.compiler_prompt_file
    ):
        args.extend(["--compiler-prompt-file", settings.compiler_prompt_file])
    if not minimal or differs(
        settings.campaign_set_schema_file, base.campaign_set_schema_file
    ):
        args.extend(
            ["--campaign-set-schema-file", settings.campaign_set_schema_file]
        )
    if not minimal or differs(
        settings.task_result_schema_file, base.task_result_schema_file
    ):
        args.extend(
            ["--task-result-schema-file", settings.task_result_schema_file]
        )

    # passes: only include when >1 (or differs from defaults).
    if not minimal or differs(max(1, settings.passes), max(1, base.passes)):
        args.extend(["--passes", str(max(1, settings.passes))])

    # base-ref: default HEAD.
    effective_base_ref = settings.base_ref or "HEAD"
    if not minimal or differs(effective_base_ref, base.base_ref or "HEAD"):
        args.extend(["--base-ref", effective_base_ref])

    # execute mode: default dry-run.
    if not minimal:
        if settings.execute_mode == "execute":
            args.append("--execute")
        else:
            args.append("--dry-run")
    else:
        if (
            settings.execute_mode == "execute"
            and base.execute_mode != "execute"
        ):
            args.append("--execute")
        # If both are dry-run, omit.

    # branch-per-campaign: default true.
    if not minimal:
        if settings.branch_per_campaign:
            args.append("--branch-per-campaign")
        else:
            args.append("--no-branch-per-campaign")
    else:
        if differs(settings.branch_per_campaign, base.branch_per_campaign):
            args.append(
                "--branch-per-campaign"
                if settings.branch_per_campaign
                else "--no-branch-per-campaign"
            )

    # discovery fallback: default false.
    if not minimal:
        if settings.allow_discovery_fallback:
            args.append("--allow-discovery-fallback")
    else:
        if (
            settings.allow_discovery_fallback
            and not base.allow_discovery_fallback
        ):
            args.append("--allow-discovery-fallback")

    # auto-commit: default true today; keep explicit in full mode only.
    if not minimal:
        args.append("--auto-commit")

    # verify: default false (unless CI says otherwise). In minimal mode,
    # emit only when it differs from the computed default.
    if not minimal:
        args.append("--verify" if settings.verify else "--no-verify")
    else:
        if differs(settings.verify, base.verify):
            args.append("--verify" if settings.verify else "--no-verify")

    # Models/config: only emit if non-empty.
    if settings.codex_model:
        args.extend(["--codex-model", settings.codex_model])
    if settings.codex_model_audit:
        args.extend(["--codex-model-audit", settings.codex_model_audit])
    if settings.codex_model_compiler:
        args.extend(["--codex-model-compiler", settings.codex_model_compiler])
    if settings.codex_model_task:
        args.extend(["--codex-model-task", settings.codex_model_task])
    for config in settings.codex_config:
        args.extend(["--codex-config", config])

    if settings.claude_model:
        args.extend(["--claude-model", settings.claude_model])
    if settings.claude_model_audit:
        args.extend(["--claude-model-audit", settings.claude_model_audit])
    if settings.claude_model_compiler:
        args.extend(["--claude-model-compiler", settings.claude_model_compiler])
    if settings.claude_model_task:
        args.extend(["--claude-model-task", settings.claude_model_task])
    for setting in settings.claude_settings:
        args.extend(["--claude-settings", setting])

    # debug: default false.
    if not minimal:
        if settings.debug:
            args.append("--debug")
    else:
        if settings.debug and not base.debug:
            args.append("--debug")

    return args
