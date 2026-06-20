"""File-backed Whoosh'd local model profile registry."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "config" / "whooshd" / "model-profiles"


class WhooshdModelProfileError(ValueError):
    """Raised when the local Whoosh'd profile registry is malformed."""


def _profile_paths(profile_dir: Path = PROFILE_DIR) -> list[Path]:
    if not profile_dir.exists():
        return []
    return sorted(profile_dir.glob("*.json"))


def _profile_model_repo(profile: dict[str, Any]) -> str:
    model = profile.get("model")
    if not isinstance(model, dict):
        return ""
    return str(model.get("repo") or "").strip()


def _validate_profile(path: Path, profile: dict[str, Any]) -> None:
    label = path.relative_to(ROOT)
    profile_id = str(profile.get("id") or "").strip()
    if not profile_id:
        raise WhooshdModelProfileError(f"{label}: missing id")
    if str(profile.get("provider_id") or "").strip() != "local":
        raise WhooshdModelProfileError(f"{label}: provider_id must be local")
    if str(profile.get("display_vendor") or "").strip() != "Whoosh'd":
        raise WhooshdModelProfileError(
            f"{label}: display_vendor must be Whoosh'd"
        )
    if not _profile_model_repo(profile):
        raise WhooshdModelProfileError(f"{label}: model.repo is required")
    release_posture = profile.get("release_posture")
    if not isinstance(release_posture, dict):
        raise WhooshdModelProfileError(
            f"{label}: release_posture must be an object"
        )
    if release_posture.get("release_supported") is not False:
        raise WhooshdModelProfileError(
            f"{label}: release_posture.release_supported must be false"
        )


@lru_cache(maxsize=1)
def load_whooshd_model_profiles() -> tuple[dict[str, Any], ...]:
    profiles: list[dict[str, Any]] = []
    for path in _profile_paths():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WhooshdModelProfileError(
                f"{path.relative_to(ROOT)}: invalid JSON: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise WhooshdModelProfileError(
                f"{path.relative_to(ROOT)}: profile must be an object"
            )
        _validate_profile(path, payload)
        profiles.append(payload)
    return tuple(profiles)


def whooshd_profile_by_id_or_repo(
    model_id: str | None,
) -> dict[str, Any] | None:
    clean = str(model_id or "").strip()
    if not clean:
        return None
    for profile in load_whooshd_model_profiles():
        if clean == str(profile.get("id") or "").strip():
            return profile
        if clean == _profile_model_repo(profile):
            return profile
    return None


def whooshd_runtime_model_id(model_id: str | None) -> str | None:
    profile = whooshd_profile_by_id_or_repo(model_id)
    if profile is None:
        return None
    return str(profile.get("id") or "").strip() or None


def whooshd_profile_model_repos() -> list[str]:
    repos: list[str] = []
    seen: set[str] = set()
    for profile in load_whooshd_model_profiles():
        repo = _profile_model_repo(profile)
        if not repo or repo in seen:
            continue
        seen.add(repo)
        repos.append(repo)
    return repos
