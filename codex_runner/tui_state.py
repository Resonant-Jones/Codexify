from __future__ import annotations

import json
import os
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
    "pi_provider",
    "pi_route",
    "pi_model",
    "pi_model_audit",
    "pi_model_compiler",
    "pi_model_task",
    "pi_thinking",
    "require_backend_receipt",
}


@dataclass
class RunnerSettings:
    provider: str = "pi"
    legacy_provider: str | None = None

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

    pi_provider: str = "anthropic"
    pi_route: str = "default"
    pi_model: str = "claude-sonnet-4-20250514"
    pi_model_audit: str = ""
    pi_model_compiler: str = ""
    pi_model_task: str = ""
    pi_thinking: str = "medium"
    require_backend_receipt: bool = True


@dataclass
class ProfileData:
    settings: RunnerSettings
    presets: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def default_verify(ci_env: str | None) -> bool:
    if not ci_env:
        return False
    return ci_env.strip().lower() in {"1", "true", "yes", "on"}


def default_settings(cwd: Path | None = None) -> RunnerSettings:
    root = str((cwd or Path.cwd()).resolve())
    return RunnerSettings(
        provider="pi",
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
        pi_provider=os.environ.get("PI_PROVIDER", "anthropic"),
        pi_route=os.environ.get("CAMPAIGN_RUNNER_PI_ROUTE", "default"),
        pi_model=os.environ.get("PI_MODEL", "claude-sonnet-4-20250514"),
        pi_thinking=os.environ.get("PI_THINKING", "medium"),
        require_backend_receipt=_coerce_bool(
            os.environ.get("CAMPAIGN_RUNNER_REQUIRE_BACKEND_RECEIPT"),
            True,
        ),
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
    if provider in {"pi", "unsupported"}:
        return provider
    if provider in {"codex", "claude"}:
        return "unsupported"
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
        legacy_provider=(
            _coerce_str(raw.get("legacy_provider"), "").strip() or None
        ),
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
        pi_provider=_coerce_str(raw.get("pi_provider"), base.pi_provider),
        pi_route=_coerce_str(raw.get("pi_route"), base.pi_route),
        pi_model=_coerce_str(raw.get("pi_model"), base.pi_model),
        pi_model_audit=_coerce_str(
            raw.get("pi_model_audit"), base.pi_model_audit
        ),
        pi_model_compiler=_coerce_str(
            raw.get("pi_model_compiler"), base.pi_model_compiler
        ),
        pi_model_task=_coerce_str(raw.get("pi_model_task"), base.pi_model_task),
        pi_thinking=_coerce_str(raw.get("pi_thinking"), base.pi_thinking),
        require_backend_receipt=_coerce_bool(
            raw.get("require_backend_receipt"),
            base.require_backend_receipt,
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
    raw_provider = _coerce_str(merged_raw.get("provider"), "").strip().lower()
    if raw_provider in {"codex", "claude"}:
        warnings.append(
            f"Legacy provider '{raw_provider}' is unsupported. "
            "Direct Codex/Claude execution is unsupported for Campaign Runner. "
            "Use provider=pi."
        )
        merged_raw["provider"] = "unsupported"
        merged_raw["legacy_provider"] = raw_provider
    for legacy_key in (
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
    ):
        if legacy_key in merged_raw and merged_raw.get(legacy_key):
            warnings.append(
                f"Ignored legacy direct-provider setting '{legacy_key}'. "
                "Use Pi broker settings instead."
            )
    settings = settings_from_dict(merged_raw, base)
    return ProfileData(
        settings=settings, presets=normalized_presets, warnings=warnings
    )


def settings_to_dict(settings: RunnerSettings) -> dict[str, Any]:
    return {
        "provider": settings.provider,
        "legacy_provider": settings.legacy_provider,
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
        "pi_provider": settings.pi_provider,
        "pi_route": settings.pi_route,
        "pi_model": settings.pi_model,
        "pi_model_audit": settings.pi_model_audit,
        "pi_model_compiler": settings.pi_model_compiler,
        "pi_model_task": settings.pi_model_task,
        "pi_thinking": settings.pi_thinking,
        "require_backend_receipt": settings.require_backend_receipt,
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


def to_cli_args(settings: RunnerSettings) -> list[str]:
    args: list[str] = [
        "--provider",
        settings.provider,
        "--repo-root",
        settings.repo_root,
        "--audit-prompt-file",
        settings.audit_prompt_file,
        "--audit-schema-file",
        settings.audit_schema_file,
        "--compiler-prompt-file",
        settings.compiler_prompt_file,
        "--campaign-set-schema-file",
        settings.campaign_set_schema_file,
        "--task-result-schema-file",
        settings.task_result_schema_file,
        "--passes",
        str(max(1, settings.passes)),
        "--base-ref",
        settings.base_ref or "HEAD",
    ]

    if settings.execute_mode == "execute":
        args.append("--execute")
    else:
        args.append("--dry-run")

    if settings.branch_per_campaign:
        args.append("--branch-per-campaign")
    else:
        args.append("--no-branch-per-campaign")

    if settings.allow_discovery_fallback:
        args.append("--allow-discovery-fallback")

    args.append("--auto-commit")

    if settings.verify:
        args.append("--verify")
    else:
        args.append("--no-verify")

    if settings.pi_provider:
        args.extend(["--pi-provider", settings.pi_provider])
    if settings.pi_route:
        args.extend(["--pi-route", settings.pi_route])
    if settings.pi_model:
        args.extend(["--pi-model", settings.pi_model])
    if settings.pi_model_audit:
        args.extend(["--pi-model-audit", settings.pi_model_audit])
    if settings.pi_model_compiler:
        args.extend(["--pi-model-compiler", settings.pi_model_compiler])
    if settings.pi_model_task:
        args.extend(["--pi-model-task", settings.pi_model_task])
    if settings.pi_thinking:
        args.extend(["--pi-thinking", settings.pi_thinking])
    if settings.require_backend_receipt:
        args.append("--require-backend-receipt")
    else:
        args.append("--allow-missing-backend-receipt")

    if settings.debug:
        args.append("--debug")

    return args
