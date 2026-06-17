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

REQUIRED_ACCEPTANCE_CHECKS = {
    "no_prompt_echo",
    "no_thought_channel_leak",
    "guardian_completion_smoke",
}


def _failures_for_profile(path: Path, profile: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    label = path.relative_to(ROOT)

    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - profile.keys())
    for key in missing:
        failures.append(f"{label}: missing required key: {key}")

    if profile.get("provider_id") != "local":
        failures.append(f"{label}: provider_id must be 'local'")

    if profile.get("display_vendor") != "Whoosh'd":
        failures.append(f"{label}: display_vendor must be \"Whoosh'd\"")

    release_posture = profile.get("release_posture")
    if not isinstance(release_posture, dict):
        failures.append(f"{label}: release_posture must be an object")
    elif release_posture.get("release_supported") is not False:
        failures.append(
            f"{label}: release_posture.release_supported must be false"
        )

    guardian_defaults = profile.get("guardian_defaults")
    if not isinstance(guardian_defaults, dict):
        failures.append(f"{label}: guardian_defaults must be an object")
    else:
        if guardian_defaults.get("reject_thought_channel_leaks") is not True:
            failures.append(
                f"{label}: guardian_defaults.reject_thought_channel_leaks must be true"
            )
        if guardian_defaults.get("history_policy") != "final_answer_only":
            failures.append(
                f"{label}: guardian_defaults.history_policy must be 'final_answer_only'"
            )

    acceptance_checks = profile.get("acceptance_checks")
    if not isinstance(acceptance_checks, list):
        failures.append(f"{label}: acceptance_checks must be an array")
    else:
        check_ids = {
            item.get("id")
            for item in acceptance_checks
            if isinstance(item, dict)
        }
        for check_id in sorted(REQUIRED_ACCEPTANCE_CHECKS - check_ids):
            failures.append(
                f"{label}: acceptance_checks missing required id: {check_id}"
            )

    return failures


def validate_profiles() -> int:
    if not PROFILE_DIR.exists():
        print(f"Profile directory not found: {PROFILE_DIR}", file=sys.stderr)
        return 1

    profile_paths = sorted(PROFILE_DIR.glob("*.json"))
    if not profile_paths:
        print(f"No model profiles found in {PROFILE_DIR}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for path in profile_paths:
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
            continue

        if not isinstance(profile, dict):
            failures.append(f"{path.relative_to(ROOT)}: profile must be an object")
            continue

        failures.extend(_failures_for_profile(path, profile))

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(f"Validated {len(profile_paths)} Whoosh'd model profile(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate_profiles())
