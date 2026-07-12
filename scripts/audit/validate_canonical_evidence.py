#!/usr/bin/env python3
"""Validate one canonical audit evidence manifest without mutating repository state."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PureWindowsPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


RESULT_SCHEMA_VERSION = "canonical_audit_evidence_validation_result.v1"
VALIDATOR_VERSION = "canonical_audit_evidence_validator.v1"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = (
    DEFAULT_REPO_ROOT / "schemas/audit/canonical-audit-evidence.schema.json"
)
_FORMAT_CHECKER = FormatChecker()


def _relative_reference(path: Path, repo_root: Path) -> str:
    """Return a portable reference without exposing an absolute local path."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name or "manifest.json"


def _json_path(parts: Any) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else "." + str(part)
        for part in parts
    )


def _is_absolute(value: str) -> bool:
    return Path(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _has_parent_traversal(value: str) -> bool:
    return ".." in value.replace("\\", "/").split("/")


def _issue(
    severity: str, code: str, path: str, message: str, remediation_hint: str
) -> dict[str, str]:
    return {
        "issue_id": "",
        "severity": severity,
        "code": code,
        "path": path,
        "message": message,
        "remediation_hint": remediation_hint,
    }


def _finalize_issues(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(
        issues,
        key=lambda item: (item["path"], item["code"], item["message"], item["severity"]),
    )
    for number, item in enumerate(ordered, start=1):
        item["issue_id"] = f"issue-{number:04d}"
    return ordered


def _value(manifest: dict[str, Any], *path: str) -> Any:
    current: Any = manifest
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _validate_semantics(manifest: dict[str, Any], issues: list[dict[str, str]]) -> None:
    authority = manifest.get("authority_status")
    machine_id = _value(manifest, "machine", "machine_id")
    machine_role = _value(manifest, "machine", "machine_role")
    if authority == "CANONICAL":
        if machine_id != "vaultnode":
            issues.append(_issue("error", "canonical_machine_id_invalid", "$.machine.machine_id", "Canonical evidence must declare machine_id 'vaultnode'.", "Use the canonical VaultNode machine identifier."))
        if machine_role != "canonical_evidence_host":
            issues.append(_issue("error", "canonical_machine_role_invalid", "$.machine.machine_role", "Canonical evidence must declare role 'canonical_evidence_host'.", "Use the canonical evidence host role."))
        if _value(manifest, "repository", "branch") != "main":
            issues.append(_issue("error", "canonical_branch_invalid", "$.repository.branch", "Canonical evidence must declare branch 'main'.", "Record the evaluated main branch."))
        if _value(manifest, "repository", "dirty") is not False:
            issues.append(_issue("error", "canonical_worktree_dirty", "$.repository.dirty", "Canonical evidence must declare a clean worktree.", "Set dirty to false only for a clean evaluated worktree."))
        if _value(manifest, "repository", "commit_sha") != _value(manifest, "repository", "upstream_sha"):
            issues.append(_issue("error", "canonical_commit_upstream_mismatch", "$.repository", "Canonical evidence requires matching commit_sha and upstream_sha.", "Record matching accepted main commit identities."))

        for field in ("repository_root_identity", "worktree_identity"):
            value = _value(manifest, "repository", field)
            path = f"$.repository.{field}"
            if isinstance(value, str) and _is_absolute(value):
                issues.append(_issue("error", "portable_identity_absolute", path, "Canonical repository identity must be portable and non-absolute.", "Use a repository-relative portable identity."))
            if isinstance(value, str) and _has_parent_traversal(value):
                issues.append(_issue("error", "portable_identity_parent_traversal", path, "Canonical repository identity must not contain parent traversal.", "Use a normalized repository-relative identity."))

    if manifest.get("proof_class") == "CURRENT_LIVE_PROOF":
        runtime = manifest.get("runtime")
        required = ("supported_profile", "effective_config_hash", "compose_project", "compose_files", "migration_head", "service_identities")
        incomplete = not isinstance(runtime, dict)
        if isinstance(runtime, dict):
            incomplete = any(
                runtime.get(field) is None or runtime.get(field) == [] or runtime.get(field) == ""
                for field in required
            )
        if incomplete:
            issues.append(_issue("error", "live_runtime_identity_incomplete", "$.runtime", "CURRENT_LIVE_PROOF requires complete non-empty runtime identity.", "Provide all required supported-profile, configuration, Compose, migration, and service identity fields."))


def _validate_artifacts(
    manifest: dict[str, Any], repo_root: Path, issues: list[dict[str, str]]
) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return
    root = repo_root.resolve()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            continue
        path_value = artifact.get("path")
        location = f"$.artifacts[{index}].path"
        if not isinstance(path_value, str):
            continue
        if _is_absolute(path_value):
            issues.append(_issue("error", "artifact_path_absolute", location, "Artifact paths must be repository-relative.", "Use a repository-relative artifact path."))
            continue
        if _has_parent_traversal(path_value):
            issues.append(_issue("error", "artifact_path_parent_traversal", location, "Artifact paths must not contain parent traversal.", "Use a normalized repository-relative artifact path."))
            continue
        candidate = (root / path_value).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            issues.append(_issue("error", "artifact_path_outside_repo", location, "Artifact path resolves outside the repository root.", "Reference an artifact contained by the selected repository root."))
            continue
        if not candidate.is_file():
            issues.append(_issue("error", "artifact_missing", location, "Declared artifact is missing.", "Add the artifact or correct its repository-relative path."))
            continue
        digest = hashlib.sha256()
        with candidate.open("rb") as artifact_file:
            for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
                digest.update(chunk)
        if artifact.get("sha256") != digest.hexdigest():
            issues.append(_issue("error", "artifact_hash_mismatch", f"$.artifacts[{index}].sha256", "Declared artifact SHA-256 does not match artifact bytes.", "Update the immutable record with the artifact's lowercase SHA-256."))


def validate_manifest(
    manifest_path: str | Path,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    repo_root: str | Path = DEFAULT_REPO_ROOT,
) -> dict[str, Any]:
    """Validate one manifest using only its declared contents and local artifacts."""
    manifest_file = Path(manifest_path)
    schema_file = Path(schema_path)
    root = Path(repo_root)
    issues: list[dict[str, str]] = []
    manifest: dict[str, Any] | None = None
    schema_valid = False

    try:
        raw_manifest = manifest_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        issues.append(_issue("error", "manifest_read_error", "$", "Manifest could not be read as UTF-8.", "Provide a readable UTF-8 JSON manifest."))
    else:
        try:
            parsed = json.loads(raw_manifest)
        except json.JSONDecodeError:
            issues.append(_issue("error", "manifest_json_invalid", "$", "Manifest is not valid JSON.", "Correct the JSON syntax."))
        else:
            if not isinstance(parsed, dict):
                issues.append(_issue("error", "manifest_root_invalid", "$", "Manifest root must be a JSON object.", "Use an object as the JSON document root."))
            else:
                manifest = parsed

    schema: dict[str, Any] | None = None
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeDecodeError):
        issues.append(_issue("error", "schema_read_error", "$", "Canonical schema could not be read as UTF-8.", "Provide the hydrated canonical audit evidence schema."))
    except Exception:
        code = "schema_invalid"
        issues.append(_issue("error", code, "$", "Canonical schema is invalid.", "Repair the schema in its governing task before validation."))

    if manifest is not None and schema is not None:
        validator = Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)
        for error in sorted(validator.iter_errors(manifest), key=lambda err: (_json_path(err.absolute_path), err.message)):
            issues.append(_issue("error", "schema_validation_error", _json_path(error.absolute_path), error.message, "Correct the manifest to satisfy the canonical Draft 2020-12 schema."))
        _validate_semantics(manifest, issues)
        _validate_artifacts(manifest, root, issues)

    issues = _finalize_issues(issues)
    schema_valid = manifest is not None and schema is not None and not any(
        issue["code"] == "schema_validation_error" for issue in issues
    )
    semantic_valid = manifest is not None and not any(
        issue["code"].startswith("canonical_")
        or issue["code"].startswith("portable_identity_")
        or issue["code"] == "live_runtime_identity_incomplete"
        for issue in issues
    )
    artifact_integrity_valid = manifest is not None and not any(
        issue["code"].startswith("artifact_") for issue in issues
    )
    eligibility_reasons: list[str] = []
    if not schema_valid:
        eligibility_reasons.append("schema_invalid")
    if not semantic_valid:
        eligibility_reasons.append("semantic_validation_failed")
    if not artifact_integrity_valid:
        eligibility_reasons.append("artifact_integrity_failed")
    if manifest is None or manifest.get("authority_status") != "CANONICAL":
        eligibility_reasons.append("authority_status_not_canonical")
    if _value(manifest or {}, "machine", "machine_id") != "vaultnode":
        eligibility_reasons.append("machine_not_vaultnode")
    if _value(manifest or {}, "machine", "machine_role") != "canonical_evidence_host":
        eligibility_reasons.append("machine_role_not_canonical_evidence_host")
    if manifest is None or manifest.get("freshness_status") != "CURRENT":
        eligibility_reasons.append("freshness_not_current")
    if manifest is None or manifest.get("disposition") != "ACCEPTED":
        eligibility_reasons.append("disposition_not_accepted")
    canonical_eligible = not eligibility_reasons
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "validated_manifest_ref": _relative_reference(manifest_file, root),
        "result": "pass" if not issues else "fail",
        "schema_valid": schema_valid,
        "semantic_valid": semantic_valid,
        "artifact_integrity_valid": artifact_integrity_valid,
        "canonical_eligible": canonical_eligible,
        "issue_count": len(issues),
        "issues": issues,
        "eligibility_reasons": eligibility_reasons,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one canonical audit evidence manifest.")
    parser.add_argument("manifest_path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    result = validate_manifest(args.manifest_path, args.schema, args.repo_root)
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"Canonical audit evidence validation {result['result']}: {result['validated_manifest_ref']} ({result['issue_count']} issue(s))")
        for issue in result["issues"]:
            print(f"  [{issue['severity']}] {issue['code']} at {issue['path']}: {issue['message']}")
    if any(issue["code"] in {"schema_read_error", "schema_invalid"} for issue in result["issues"]):
        return 2
    return 0 if result["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
