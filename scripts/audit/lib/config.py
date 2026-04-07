"""Configuration loader for audit infrastructure."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASELINE_PATH = (
    REPO_ROOT / "scripts" / "audit" / "data" / "risk_matrix_baseline.json"
)
DEFAULT_CONFIG_PATH = (
    REPO_ROOT / "scripts" / "audit" / "data" / "audit_config.json"
)


@dataclass
class AuditConfig:
    """Audit configuration container."""

    version: str
    repo_name: str
    description: str
    risky_path_patterns: list[str]
    test_path_patterns: list[str]
    migration_path_patterns: list[str]
    high_blast_radius_paths: list[str]
    subsystems: dict[str, dict[str, Any]]
    tool_contract_patterns: dict[str, Any]
    identity_marker_patterns: dict[str, Any]
    queue_worker_patterns: dict[str, Any]
    gate_checks: dict[str, Any]
    exit_codes: dict[str, int]

    @classmethod
    def from_file(cls, path: Path | None = None) -> AuditConfig:
        """Load configuration from JSON file."""
        config_path = path or DEFAULT_CONFIG_PATH
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return cls(
            version=data["version"],
            repo_name=data["repo_name"],
            description=data["description"],
            risky_path_patterns=data["risky_path_patterns"],
            test_path_patterns=data["test_path_patterns"],
            migration_path_patterns=data["migration_path_patterns"],
            high_blast_radius_paths=data["high_blast_radius_paths"],
            subsystems=data["subsystems"],
            tool_contract_patterns=data["tool_contract_patterns"],
            identity_marker_patterns=data["identity_marker_patterns"],
            queue_worker_patterns=data["queue_worker_patterns"],
            gate_checks=data["gate_checks"],
            exit_codes=data["exit_codes"],
        )

    def get_subsystem_for_path(self, path: str) -> str | None:
        """Determine which subsystem a path belongs to."""
        import fnmatch

        for name, config in self.subsystems.items():
            for pattern in config.get("patterns", []):
                if fnmatch.fnmatch(path, pattern):
                    return name
        return None

    def is_test_file(self, path: str) -> bool:
        """Check if path matches test file patterns."""
        import fnmatch

        for pattern in self.test_path_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def is_migration_file(self, path: str) -> bool:
        """Check if path matches migration file patterns."""
        import fnmatch

        for pattern in self.migration_path_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def is_high_blast_radius(self, path: str) -> bool:
        """Check if path is classified as high blast radius."""
        import fnmatch

        for pattern in self.high_blast_radius_paths:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False
