#!/usr/bin/env python3
"""
Profile management for Campaign Runner.

Profiles are named configurations that control:
- Model to use
- Thinking level
- Passes/cycles
- Execute mode
- Verification settings

Stored in: ~/.config/campaign_runner/profiles.toml
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

PROFILE_DIR = Path.home() / ".config" / "campaign_runner"
PROFILES_PATH = PROFILE_DIR / "profiles.toml"

# Default profiles
DEFAULT_PROFILES = {
    "default": {
        "model": "claude-sonnet-4-20250514",
        "thinking": "medium",
        "passes": 1,
        "verify": False,
        "execute": False,
    },
    "fast": {
        "model": "claude-sonnet-4-20250514",
        "thinking": "low",
        "passes": 2,
        "verify": False,
        "execute": True,
    },
    "thorough": {
        "model": "claude-opus-4-5",
        "thinking": "high",
        "passes": 3,
        "verify": True,
        "execute": True,
    },
    "review": {
        "model": "claude-sonnet-4-20250514",
        "thinking": "medium",
        "passes": 1,
        "verify": False,
        "execute": False,
    },
}


@dataclass
class Profile:
    name: str
    model: str = "claude-sonnet-4-20250514"
    thinking: str = "medium"
    passes: int = 1
    verify: bool = False
    execute: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "thinking": self.thinking,
            "passes": self.passes,
            "verify": self.verify,
            "execute": self.execute,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> Profile:
        return cls(
            name=name,
            model=data.get("model", "claude-sonnet-4-20250514"),
            thinking=data.get("thinking", "medium"),
            passes=int(data.get("passes", 1)),
            verify=bool(data.get("verify", False)),
            execute=bool(data.get("execute", False)),
            description=str(data.get("description", "")),
        )


@dataclass
class ProfileManager:
    profiles: dict[str, Profile] = field(default_factory=dict)
    active_profile: str = "default"
    warnings: list[str] = field(default_factory=list)

    def load(self) -> ProfileManager:
        """Load profiles from disk or create defaults."""
        if not PROFILES_PATH.exists():
            self._create_default_profiles()

        try:
            with PROFILES_PATH.open("rb") as f:
                data = tomllib.load(f)
        except Exception as exc:
            print(f"Warning: Failed to load profiles: {exc}", file=sys.stderr)
            self._create_default_profiles()
            with PROFILES_PATH.open("rb") as f:
                data = tomllib.load(f)

        self.profiles = {}
        for name, profile_data in data.items():
            if not isinstance(profile_data, dict):
                continue
            # Skip "profiles" wrapper key if it exists
            if name == "profiles":
                for subname, subdata in profile_data.items():
                    if isinstance(subdata, dict):
                        self.profiles[subname] = Profile.from_dict(
                            subname, subdata
                        )
                continue
            self.profiles[name] = Profile.from_dict(name, profile_data)

        # Ensure defaults exist
        for name, defaults in DEFAULT_PROFILES.items():
            if name not in self.profiles:
                self.profiles[name] = Profile.from_dict(name, defaults)

        return self

    def save(self) -> None:
        """Save profiles to disk."""
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Campaign Runner Profiles",
            "# Auto-generated or manually edited",
            "",
        ]

        for name in sorted(self.profiles.keys()):
            profile = self.profiles[name]
            lines.append(f"[{name}]")
            lines.append(f'model = "{profile.model}"')
            lines.append(f'thinking = "{profile.thinking}"')
            lines.append(f"passes = {profile.passes}")
            lines.append(f'verify = {"true" if profile.verify else "false"}')
            lines.append(f'execute = {"true" if profile.execute else "false"}')
            if profile.description:
                lines.append(f'description = "{profile.description}"')
            lines.append("")

        PROFILES_PATH.write_text("\n".join(lines))

    def _create_default_profiles(self) -> None:
        """Create default profiles file."""
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        self.save()

    def get(self, name: str) -> Profile | None:
        """Get a profile by name."""
        return self.profiles.get(name)

    def set_active(self, name: str) -> bool:
        """Set the active profile."""
        if name not in self.profiles:
            return False
        self.active_profile = name
        return True

    def create(self, name: str, **kwargs) -> Profile:
        """Create or update a profile."""
        if not kwargs:
            kwargs = DEFAULT_PROFILES.get("default", {}).copy()

        profile = Profile(name=name, **kwargs)
        self.profiles[name] = profile
        self.save()
        return profile

    def delete(self, name: str) -> bool:
        """Delete a profile."""
        if name in self.profiles:
            del self.profiles[name]
            if self.active_profile == name:
                self.active_profile = "default"
            self.save()
            return True
        return False

    def list_names(self) -> list[str]:
        """List all profile names."""
        return sorted(self.profiles.keys())

    def render(self) -> str:
        """Render a summary of all profiles."""
        lines = ["Available Profiles:", "=" * 50]

        for name in self.list_names():
            p = self.profiles[name]
            active_marker = " ← ACTIVE" if name == self.active_profile else ""
            lines.append(f"\n[{name}]{active_marker}")
            lines.append(f"  model:    {p.model}")
            lines.append(f"  thinking: {p.thinking}")
            lines.append(f"  passes:   {p.passes}")
            lines.append(f"  verify:   {p.verify}")
            lines.append(f"  execute:  {p.execute}")
            if p.description:
                lines.append(f"  desc:     {p.description}")

        return "\n".join(lines)


def _coerce_bool(value: Any, fallback: bool) -> bool:
    """Coerce a value to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return fallback


def main():
    pm = ProfileManager().load()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            print(pm.render())
        elif cmd == "show" and len(sys.argv) > 2:
            profile = pm.get(sys.argv[2])
            if profile:
                print(json.dumps(profile.to_dict(), indent=2))
            else:
                print(f"Profile '{sys.argv[2]}' not found", file=sys.stderr)
                sys.exit(1)
        elif cmd == "create" and len(sys.argv) > 2:
            name = sys.argv[2]
            kwargs = {}
            for arg in sys.argv[3:]:
                if "=" in arg:
                    key, val = arg.split("=", 1)
                    if key in {"passes"}:
                        kwargs[key] = int(val)
                    elif key in {"verify", "execute"}:
                        kwargs[key] = _coerce_bool(val, False)
                    else:
                        kwargs[key] = val
            profile = pm.create(name, **kwargs)
            print(f"Created profile: {profile.name}")
        elif cmd == "delete" and len(sys.argv) > 2:
            if pm.delete(sys.argv[2]):
                print(f"Deleted profile: {sys.argv[2]}")
            else:
                print(f"Profile '{sys.argv[2]}' not found", file=sys.stderr)
                sys.exit(1)
        elif cmd == "activate" and len(sys.argv) > 2:
            if pm.set_active(sys.argv[2]):
                print(f"Activated profile: {sys.argv[2]}")
            else:
                print(f"Profile '{sys.argv[2]}' not found", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: profile.py list|show|create|delete|activate")
    else:
        print(pm.render())


if __name__ == "__main__":
    import json

    main()
