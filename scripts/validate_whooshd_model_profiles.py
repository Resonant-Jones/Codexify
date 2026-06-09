#!/usr/bin/env python3
"""Validate data-only Whoosh'd local model profile manifests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "config" / "whooshd" / "model-profiles"

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "id",
    "display_name",
    "family",
    "provider_id",
    "display_vendor",
    "runtime",
    "model",
    "guardian_defaults",
    "acceptance_checks",
    "release_posture",
}

REQUIRED_ACCEPTANCE_CHECK_IDS = {
    "no_prompt_echo",
    "no_thought_channel_leak",
    "guardian_completion_smoke",
}


def _load_profile(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"{path}: unable to read profile: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path}: profile root must be a JSON object")

    return data


def _require_mapping(profile: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = profile.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: {key} must be an object")
    return value


def _validate_profile(path: Path) -> None:
    profile = _load_profile(path)
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - profile.keys())
    if missing:
        raise ValueError(f"{path}: missing required keys: {', '.join(missing)}")

    if profile["provider_id"] != "local":
        raise ValueError(f"{path}: provider_id must be 'local'")

    if profile["display_vendor"] != "Whoosh'd":
        raise ValueError(f"{path}: display_vendor must be \"Whoosh'd\"")

    release_posture = _require_mapping(profile, "release_posture", path)
    if release_posture.get("release_supported") is not False:
        raise ValueError(
            f"{path}: release_posture.release_supported must be false"
        )

    guardian_defaults = _require_mapping(profile, "guardian_defaults", path)
    if guardian_defaults.get("reject_thought_channel_leaks") is not True:
        raise ValueError(
            f"{path}: guardian_defaults.reject_thought_channel_leaks must be true"
        )

    if guardian_defaults.get("history_policy") != "final_answer_only":
        raise ValueError(
            f"{path}: guardian_defaults.history_policy must be 'final_answer_only'"
        )

    acceptance_checks = profile.get("acceptance_checks")
    if not isinstance(acceptance_checks, list):
        raise ValueError(f"{path}: acceptance_checks must be an array")

    acceptance_check_ids = {
        item.get("id")
        for item in acceptance_checks
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing_checks = sorted(REQUIRED_ACCEPTANCE_CHECK_IDS - acceptance_check_ids)
    if missing_checks:
        raise ValueError(
            f"{path}: missing acceptance checks: {', '.join(missing_checks)}"
        )


def validate_profiles(profile_dir: Path = PROFILE_DIR) -> int:
    if not profile_dir.is_dir():
        raise ValueError(f"{profile_dir}: profile directory does not exist")

    profile_paths = sorted(profile_dir.glob("*.json"))
    if not profile_paths:
        raise ValueError(f"{profile_dir}: no JSON profiles found")

    for path in profile_paths:
        _validate_profile(path)

    return len(profile_paths)


def main() -> int:
    try:
        count = validate_profiles()
    except ValueError as exc:
        print(f"Whoosh'd model profile validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Validated {count} Whoosh'd model profile(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
