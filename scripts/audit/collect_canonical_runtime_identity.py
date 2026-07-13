#!/usr/bin/env python3
"""Collect static, secret-safe supported-runtime identity.

This collector reads the supported profile, selected Compose definitions, and
repository migration metadata. It never contacts Docker or a database and
does not produce a canonical evidence manifest or live-proof claim.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import sys
from pathlib import Path, PureWindowsPath
from typing import Any, Sequence

import yaml

# Keep the CLI importable when invoked by absolute path from outside the repo.
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from guardian.core.supported_profile import (  # noqa: E402 - CLI bootstrap adds the source root.
    SupportedProfileError,
    load_supported_profile,
)


RESULT_SCHEMA_VERSION = "canonical_audit_runtime_identity_result.v1"
COLLECTOR_VERSION = "canonical_audit_runtime_identity_collector.v1"
DEFAULT_PROFILE_NAME = "v1-local-core-web-mcp"
DEFAULT_PROFILES_DIR = "config/supported_profiles"
DEFAULT_MIGRATIONS_DIR = "guardian/db/migrations/versions"
PROJECT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SECRET_INPUT_RE = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|private[_-]?key|database[_-]?url|"
    r"postgres(?:ql)?://|mysql://|redis://|://)"
)


class RuntimeIdentityError(Exception):
    """A bounded, machine-readable collector failure."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_absolute(value: str) -> bool:
    return Path(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _has_parent_traversal(value: str) -> bool:
    return ".." in value.replace("\\", "/").split("/")


def _safe_project_input(value: str, *, field: str) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized or SECRET_INPUT_RE.search(normalized):
        raise RuntimeIdentityError("forbidden_secret_input", f"Invalid {field} input.")
    if not PROJECT_NAME_RE.fullmatch(normalized):
        raise RuntimeIdentityError("compose_project_identity_ambiguous", f"Invalid {field} input.")
    return normalized


def _relative_file(
    raw: str,
    repo_root: Path,
    *,
    missing_code: str,
    label: str,
) -> tuple[str, Path]:
    value = str(raw or "").strip()
    if not value:
        raise RuntimeIdentityError(missing_code, f"{label} is missing.")
    if _is_absolute(value):
        raise RuntimeIdentityError("compose_path_absolute", f"{label} must be relative.")
    if _has_parent_traversal(value):
        raise RuntimeIdentityError(
            "compose_path_parent_traversal", f"{label} contains parent traversal."
        )
    candidate = (repo_root / value).resolve()
    try:
        relative = candidate.relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeIdentityError(
            "compose_path_outside_repository", f"{label} is outside the repository."
        ) from exc
    try:
        mode = candidate.stat().st_mode
    except OSError as exc:
        raise RuntimeIdentityError(missing_code, f"{label} is unavailable.") from exc
    if not stat.S_ISREG(mode):
        raise RuntimeIdentityError("compose_file_missing", f"{label} is not a regular file.")
    return relative, candidate


def _load_yaml_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise RuntimeIdentityError("compose_parse_failed", "YAML could not be parsed safely.") from exc
    if not isinstance(payload, dict):
        raise RuntimeIdentityError("compose_parse_failed", "Compose root is not a mapping.")
    return payload


def _normalized_names(raw: Any, *, label: str) -> list[str]:
    if not isinstance(raw, list):
        raise RuntimeIdentityError("supported_profile_invalid", f"{label} is invalid.")
    names = [str(item).strip().lower() for item in raw]
    if any(not name for name in names):
        raise RuntimeIdentityError("supported_profile_invalid", f"{label} is invalid.")
    return sorted(set(names))


def _profile_identity(
    profile_name: str,
    repo_root: Path,
    profiles_dir: str | Path | None,
) -> tuple[dict[str, Any], list[str]]:
    directory = Path(profiles_dir or DEFAULT_PROFILES_DIR)
    if not directory.is_absolute():
        directory = repo_root / directory
    directory = directory.resolve()
    try:
        directory.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RuntimeIdentityError("supported_profile_invalid", "Profile directory is outside the repository.") from exc
    profile_path = directory / f"{str(profile_name or '').strip()}.yaml"
    try:
        relative_path = profile_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeIdentityError("supported_profile_invalid", "Profile path is outside the repository.") from exc
    if not profile_path.is_file():
        raise RuntimeIdentityError("supported_profile_missing", "Supported profile file is missing.")
    try:
        manifest = load_supported_profile(str(profile_name or ""), profiles_dir=str(directory))
    except SupportedProfileError as exc:
        code = "supported_profile_missing" if "not found" in str(exc).lower() else "supported_profile_invalid"
        raise RuntimeIdentityError(code, "Supported profile could not be resolved.") from exc
    return (
        {
            "name": manifest.name,
            "version": manifest.version,
            "surface": manifest.surface,
            "path": relative_path,
            "sha256": _sha256(profile_path),
            "required_services": _normalized_names(list(manifest.required_services), label="required_services"),
            "optional_services": _normalized_names(list(manifest.optional_services), label="optional_services"),
        },
        [],
    )


def _compose_file_identity(relative_path: str, path: Path) -> dict[str, Any]:
    payload = _load_yaml_file(path)
    declared_name = payload.get("name")
    if declared_name is not None:
        if not isinstance(declared_name, str) or not declared_name.strip():
            raise RuntimeIdentityError("compose_parse_failed", "Compose project name is invalid.")
        declared_name = declared_name.strip().lower()
        if not PROJECT_NAME_RE.fullmatch(declared_name):
            raise RuntimeIdentityError("compose_project_identity_ambiguous", "Compose project name is invalid.")
    services = payload.get("services")
    if not isinstance(services, dict):
        raise RuntimeIdentityError("compose_parse_failed", "Compose services are invalid.")
    normalized: dict[str, str] = {}
    for raw_name in services:
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise RuntimeIdentityError("service_identity_conflict", "Compose service name is invalid.")
        name = raw_name.strip().lower()
        if name in normalized and normalized[name] != raw_name:
            raise RuntimeIdentityError("service_identity_conflict", "Compose service names collide after normalization.")
        normalized[name] = raw_name
    return {
        "path": relative_path,
        "sha256": _sha256(path),
        "declared_name": declared_name,
        "services": sorted(normalized),
    }


def _migration_literal(tree: ast.Module, name: str) -> tuple[bool, Any]:
    found = False
    value: Any = None
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            found = True
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError):
                return True, None
    return found, value


def _migration_identity(repo_root: Path, migration_dir: str | Path | None) -> tuple[str | None, dict[str, Any], list[str]]:
    directory = Path(migration_dir or DEFAULT_MIGRATIONS_DIR)
    if not directory.is_absolute():
        directory = repo_root / directory
    directory = directory.resolve()
    try:
        directory.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RuntimeIdentityError("migration_identity_incomplete", "Migration directory is outside the repository.") from exc
    if not directory.is_dir():
        return None, {"path": None, "head": None}, ["migration_head_missing"]
    revisions: dict[str, str] = {}
    down_revisions: dict[str, set[str]] = {}
    for path in sorted(directory.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            return None, {"path": directory.relative_to(repo_root).as_posix(), "head": None}, ["migration_identity_incomplete"]
        revision_found, revision = _migration_literal(tree, "revision")
        down_found, down_revision = _migration_literal(tree, "down_revision")
        if not revision_found or not isinstance(revision, str) or not revision.strip() or not down_found:
            return None, {"path": directory.relative_to(repo_root).as_posix(), "head": None}, ["migration_identity_incomplete"]
        revision = revision.strip()
        if revision in revisions:
            return None, {"path": directory.relative_to(repo_root).as_posix(), "head": None}, ["migration_identity_incomplete"]
        if down_revision is None:
            downs: set[str] = set()
        elif isinstance(down_revision, str):
            downs = {down_revision.strip()} if down_revision.strip() else set()
        elif isinstance(down_revision, (tuple, list)) and all(isinstance(item, str) for item in down_revision):
            downs = {item.strip() for item in down_revision if item.strip()}
        else:
            return None, {"path": directory.relative_to(repo_root).as_posix(), "head": None}, ["migration_identity_incomplete"]
        revisions[revision] = path.name
        down_revisions[revision] = downs
    if not revisions:
        return None, {"path": directory.relative_to(repo_root).as_posix(), "head": None}, ["migration_head_missing"]
    referenced = {item for values in down_revisions.values() for item in values}
    heads = sorted(set(revisions) - referenced)
    if len(heads) == 0:
        return None, {"path": directory.relative_to(repo_root).as_posix(), "head": None}, ["migration_head_missing"]
    if len(heads) > 1:
        return None, {"path": directory.relative_to(repo_root).as_posix(), "head": heads}, ["migration_head_multiple"]
    return heads[0], {"path": directory.relative_to(repo_root).as_posix(), "head": heads[0]}, []


def collect_runtime_identity(
    repo_root: str | Path = ".",
    *,
    profile_name: str = DEFAULT_PROFILE_NAME,
    profiles_dir: str | Path | None = None,
    compose_files: Sequence[str] | None = None,
    audit_project: str | None = None,
    serving_project: str | None = None,
    migration_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Collect static runtime identity without Docker, database, or mutation."""
    root = Path(repo_root).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeIdentityError("runtime_identity_incomplete", "Repository root is unavailable.")
    reasons: set[str] = set()
    try:
        profile, _ = _profile_identity(profile_name, root, profiles_dir)
    except RuntimeIdentityError as exc:
        profile = None
        reasons.add(exc.code)

    selected = list(compose_files or [])
    compose_records: list[dict[str, Any]] = []
    selected_paths: set[str] = set()
    if not selected:
        reasons.add("compose_file_missing")
    else:
        for raw in selected:
            try:
                relative, path = _relative_file(raw, root, missing_code="compose_file_missing", label="Compose file")
            except RuntimeIdentityError as exc:
                reasons.add(exc.code)
                continue
            if relative in selected_paths:
                reasons.add("compose_file_duplicate")
                continue
            selected_paths.add(relative)
            try:
                compose_records.append(_compose_file_identity(relative, path))
            except RuntimeIdentityError as exc:
                reasons.add(exc.code)

    declared_names = sorted({record["declared_name"] for record in compose_records if record["declared_name"]})
    if len(declared_names) > 1:
        reasons.add("compose_project_identity_ambiguous")
    explicit_audit = bool(str(audit_project or "").strip())
    resolved_audit: str | None = None
    if explicit_audit:
        try:
            resolved_audit = _safe_project_input(str(audit_project), field="audit project")
        except RuntimeIdentityError as exc:
            reasons.add(exc.code)
    elif len(declared_names) == 1:
        resolved_audit = declared_names[0]
    else:
        reasons.add("compose_project_identity_ambiguous")
    resolved_serving: str | None = None
    if serving_project is not None and str(serving_project).strip():
        try:
            resolved_serving = _safe_project_input(str(serving_project), field="serving project")
        except RuntimeIdentityError as exc:
            reasons.add(exc.code)
    if resolved_audit and resolved_serving and resolved_audit == resolved_serving:
        reasons.add("serving_audit_project_identity_collision")

    declared_services = sorted({service for record in compose_records for service in record["services"]})
    required_services = profile["required_services"] if profile else []
    optional_services = profile["optional_services"] if profile else []
    missing_required = sorted(set(required_services) - set(declared_services))
    if missing_required:
        reasons.add("required_service_missing")
    migration_head, migration_record, migration_reasons = _migration_identity(root, migration_dir)
    reasons.update(migration_reasons)

    profile_resolved = profile is not None
    compose_complete = bool(compose_records) and not any(
        code in reasons
        for code in (
            "compose_file_missing",
            "compose_path_absolute",
            "compose_path_parent_traversal",
            "compose_path_outside_repository",
            "compose_file_duplicate",
            "compose_parse_failed",
            "compose_project_identity_ambiguous",
            "serving_audit_project_identity_collision",
            "required_service_missing",
            "service_identity_conflict",
        )
    ) and resolved_audit is not None
    migration_complete = migration_head is not None and not any(
        code in reasons for code in ("migration_head_missing", "migration_head_multiple", "migration_identity_incomplete")
    )
    runtime_complete = profile_resolved and compose_complete and migration_complete and not any(
        code in reasons for code in ("forbidden_secret_input",)
    )

    projection: dict[str, Any] | None = None
    effective_config_hash: str | None = None
    if runtime_complete:
        projection = {
            "profile": profile,
            "compose": {
                "files": compose_records,
                "project": resolved_audit,
                "serving_project": resolved_serving,
                "required_services": required_services,
                "optional_services": optional_services,
                "declared_services": declared_services,
            },
            "migration_head": migration_head,
        }
        encoded = json.dumps(projection, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
        effective_config_hash = hashlib.sha256(encoded).hexdigest()
    if not runtime_complete:
        reasons.add("runtime_identity_incomplete")

    reasons_list = sorted(reasons)
    runtime = {
        "supported_profile": profile["name"] if profile else None,
        "effective_config_hash": effective_config_hash,
        "compose_project": resolved_audit,
        "compose_files": [record["path"] for record in compose_records],
        "migration_head": migration_head,
        "service_identities": declared_services,
        "profile_identity": profile,
        "compose_identity": {
            "files": compose_records,
            "project": resolved_audit,
            "serving_project": resolved_serving,
            "required_services": required_services,
            "optional_services": optional_services,
            "declared_services": declared_services,
            "missing_required_services": missing_required,
        },
        "migration_identity": migration_record,
    }
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "observation_complete": runtime_complete,
        "runtime": runtime,
        "eligibility": {
            "supported_profile_resolved": profile_resolved,
            "compose_identity_complete": compose_complete,
            "migration_identity_complete": migration_complete,
            "runtime_identity_complete": runtime_complete,
            "canonical_runtime_candidate": runtime_complete and explicit_audit and not any(
                code in reasons for code in ("serving_audit_project_identity_collision",)
            ),
            "reason_codes": reasons_list,
        },
    }


collect_canonical_runtime_identity = collect_runtime_identity


def _error_result(error: RuntimeIdentityError) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "observation_complete": False,
        "eligibility": {"reason_codes": [error.code]},
        "error": {"code": error.code, "message": error.message},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect static canonical audit runtime identity.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--profile-name", default=DEFAULT_PROFILE_NAME)
    parser.add_argument("--profiles-dir")
    parser.add_argument("--compose-file", action="append")
    parser.add_argument("--audit-project")
    parser.add_argument("--serving-project")
    parser.add_argument("--migration-dir")
    args = parser.parse_args(argv)
    try:
        result = collect_runtime_identity(
            args.repo,
            profile_name=args.profile_name,
            profiles_dir=args.profiles_dir,
            compose_files=args.compose_file,
            audit_project=args.audit_project,
            serving_project=args.serving_project,
            migration_dir=args.migration_dir,
        )
    except RuntimeIdentityError as exc:
        print(json.dumps(_error_result(exc), indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["observation_complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
