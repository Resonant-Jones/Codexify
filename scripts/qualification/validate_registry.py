#!/usr/bin/env python3
"""Validate the Codexify qualification registry against its schema and contract.

The registry schema (`docs/qualification/schemas/qualification-registry.schema.json`)
constrains the *shape* of the document. It cannot express the rules that make
a registry trustworthy, so this validator enforces both:

Schema-level:

* the document validates against the Draft 2020-12 registry schema.

Contract-level, from `docs/qualification/README.md`:

* every declared rubric file exists and declares the qualification ID it is
  filed under;
* every cited run receipt exists and declares the qualification ID and
  verdict the registry projects for it;
* every cited evidence path resolves to a file in the repository;
* every `PASS` carries a tested commit, a run receipt, and evidence;
* a qualification surface with no run receipt is never projected as `PASS`;
* the registry projects exactly the surfaces the rubrics declare — no extra
  surfaces, no missing ones;
* the registry is free of the ambiguous status words the README forbids.

The validator is read-only. It never edits the registry or any evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = Path("docs/qualification/registry.json")
SCHEMA_PATH = Path("docs/qualification/schemas/qualification-registry.schema.json")

RESULT_SCHEMA_VERSION = "qualification_registry_validation_result.v1"
VALIDATOR_VERSION = "qualification_registry_validator.v1"

# The README forbids ambiguous overall statuses.
FORBIDDEN_STATUS_WORDS = (
    "mostly passed",
    "partial pass",
    "basically working",
    "good enough",
    "seems fine",
    "probably fixed",
)

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_SCHEMA_ERROR = 2


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


def _json_path(parts: Any) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else "." + str(part)
        for part in parts
    )


def _resolve(repo_root: Path, relative: str) -> Path | None:
    """Resolve a repository-relative path, refusing escapes from the root."""
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except (OSError, ValueError):
        return None
    return candidate


def _validate_evidence(
    entry_id: str,
    entry: dict[str, Any],
    repo_root: Path,
    issues: list[dict[str, str]],
) -> None:
    evidence = entry.get("evidence")
    if not isinstance(evidence, list):
        return
    for index, reference in enumerate(evidence):
        location = f"$.qualifications.{entry_id}.evidence[{index}]"
        if not isinstance(reference, str) or not reference.strip():
            issues.append(
                _issue(
                    "error",
                    "evidence_reference_invalid",
                    location,
                    "Evidence references must be non-empty strings.",
                    "Cite a repository-relative proof path.",
                )
            )
            continue
        resolved = _resolve(repo_root, reference)
        if resolved is None or not resolved.is_file():
            issues.append(
                _issue(
                    "error",
                    "evidence_missing",
                    location,
                    f"Evidence path '{reference}' does not resolve to a file in "
                    "the repository.",
                    "Cite an existing proof artifact, or remove the reference.",
                )
            )


def _validate_rubric(
    entry_id: str,
    entry: dict[str, Any],
    repo_root: Path,
    issues: list[dict[str, str]],
) -> None:
    rubric_ref = entry.get("rubric")
    location = f"$.qualifications.{entry_id}.rubric"
    if not isinstance(rubric_ref, str) or not rubric_ref.strip():
        return
    resolved = _resolve(repo_root, f"docs/qualification/{rubric_ref}")
    if resolved is None or not resolved.is_file():
        issues.append(
            _issue(
                "error",
                "rubric_missing",
                location,
                f"Rubric '{rubric_ref}' does not resolve to a file in the "
                "repository.",
                "Cite an existing rubric, or run the generator to refresh the "
                "registry.",
            )
        )
        return

    text = resolved.read_text(encoding="utf-8")
    if f"qualification_id: {entry_id}" not in text:
        issues.append(
            _issue(
                "error",
                "rubric_qualification_id_mismatch",
                location,
                f"Rubric '{rubric_ref}' does not declare qualification_id "
                f"'{entry_id}'.",
                "Make the rubric declare the qualification ID it is filed "
                "under.",
            )
        )


def _validate_latest_run(
    entry_id: str,
    entry: dict[str, Any],
    repo_root: Path,
    issues: list[dict[str, str]],
) -> None:
    run_ref = entry.get("latest_run")
    location = f"$.qualifications.{entry_id}.latest_run"
    if run_ref is None:
        if entry.get("status") == "PASS":
            issues.append(
                _issue(
                    "error",
                    "pass_without_run",
                    location,
                    "A PASS qualification must cite the run receipt that "
                    "established it.",
                    "Cite the run receipt, or project the run's actual verdict.",
                )
            )
        return

    resolved = _resolve(repo_root, f"docs/qualification/{run_ref}")
    if resolved is None or not resolved.is_file():
        issues.append(
            _issue(
                "error",
                "latest_run_missing",
                location,
                f"Run receipt '{run_ref}' does not resolve to a file in the "
                "repository.",
                "Cite an existing run receipt, or run the generator to refresh "
                "the registry.",
            )
        )
        return

    text = resolved.read_text(encoding="utf-8")
    if f"qualification_id: {entry_id}" not in text:
        issues.append(
            _issue(
                "error",
                "latest_run_qualification_id_mismatch",
                location,
                f"Run receipt '{run_ref}' does not declare qualification_id "
                f"'{entry_id}'.",
                "Make the receipt declare the qualification ID it qualifies.",
            )
        )

    status = entry.get("status")
    if isinstance(status, str) and f"verdict: {status}" not in text:
        issues.append(
            _issue(
                "error",
                "latest_run_verdict_mismatch",
                location,
                f"Registry projects status '{status}' but run receipt "
                f"'{run_ref}' does not declare that verdict.",
                "Project the run's declared verdict.",
            )
        )


def _validate_status_evidence(
    entry_id: str, entry: dict[str, Any], issues: list[dict[str, str]]
) -> None:
    status = entry.get("status")
    location = f"$.qualifications.{entry_id}"
    if status == "PASS":
        if not entry.get("tested_commit"):
            issues.append(
                _issue(
                    "error",
                    "pass_without_tested_commit",
                    location,
                    "A PASS qualification must record the commit it tested.",
                    "Record the tested commit.",
                )
            )
        if not entry.get("last_qualified_at"):
            issues.append(
                _issue(
                    "error",
                    "pass_without_qualification_date",
                    location,
                    "A PASS qualification must record when it was qualified.",
                    "Record the qualification date.",
                )
            )
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            issues.append(
                _issue(
                    "error",
                    "pass_without_evidence",
                    location,
                    "A PASS qualification must cite supporting evidence.",
                    "Cite the proof artifact that established the result.",
                )
            )


def _validate_surfaces(
    registry: dict[str, Any],
    repo_root: Path,
    issues: list[dict[str, str]],
) -> None:
    qualifications = registry.get("qualifications")
    if not isinstance(qualifications, dict):
        return

    declared: set[str] = set()
    rubrics_dir = repo_root / "docs/qualification/rubrics"
    if rubrics_dir.is_dir():
        for rubric_path in sorted(rubrics_dir.glob("*.md")):
            if rubric_path.name == "README.md":
                continue
            text = rubric_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("qualification_id:"):
                    declared.add(stripped.split(":", 1)[1].strip())
                    break

    projected = set(qualifications)
    for missing in sorted(declared - projected):
        issues.append(
            _issue(
                "error",
                "surface_not_projected",
                f"$.qualifications.{missing}",
                f"Qualification surface '{missing}' has a rubric but is not "
                "projected into the registry.",
                "Run scripts/qualification/generate_registry.py.",
            )
        )
    for extra in sorted(projected - declared):
        issues.append(
            _issue(
                "error",
                "surface_not_declared",
                f"$.qualifications.{extra}",
                f"Qualification surface '{extra}' is projected but has no "
                "rubric declaring it.",
                "Add a rubric, or remove the surface from the registry.",
            )
        )


def _validate_status_vocabulary(
    registry: dict[str, Any], issues: list[dict[str, str]]
) -> None:
    qualifications = registry.get("qualifications")
    if not isinstance(qualifications, dict):
        return
    for entry_id, entry in qualifications.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status")
        if not isinstance(status, str):
            continue
        lowered = status.strip().lower()
        for phrase in FORBIDDEN_STATUS_WORDS:
            if phrase in lowered:
                issues.append(
                    _issue(
                        "error",
                        "ambiguous_status",
                        f"$.qualifications.{entry_id}.status",
                        f"Status '{status}' uses ambiguous language the "
                        "qualification README forbids.",
                        "Use PASS, HOLD, or FAIL.",
                    )
                )


def validate_registry(
    registry_path: str | Path,
    schema_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Validate one qualification registry without mutating repository state."""
    registry_file = Path(registry_path)
    schema_file = Path(schema_path)
    root = Path(repo_root)
    issues: list[dict[str, str]] = []
    registry: dict[str, Any] | None = None

    try:
        raw = registry_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        issues.append(
            _issue(
                "error",
                "registry_read_error",
                "$",
                "Qualification registry could not be read as UTF-8.",
                "Provide a readable UTF-8 JSON registry.",
            )
        )
        raw = ""

    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            issues.append(
                _issue(
                    "error",
                    "registry_json_invalid",
                    "$",
                    "Qualification registry is not valid JSON.",
                    "Correct the JSON syntax.",
                )
            )
        else:
            if not isinstance(parsed, dict):
                issues.append(
                    _issue(
                        "error",
                        "registry_root_invalid",
                        "$",
                        "Qualification registry root must be a JSON object.",
                        "Use an object as the document root.",
                    )
                )
            else:
                registry = parsed

    schema: dict[str, Any] | None = None
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeDecodeError):
        issues.append(
            _issue(
                "error",
                "schema_read_error",
                "$",
                "Qualification registry schema could not be read as UTF-8.",
                "Provide a readable schema.",
            )
        )
    except Exception:
        issues.append(
            _issue(
                "error",
                "schema_invalid",
                "$",
                "Qualification registry schema is invalid.",
                "Repair the schema before validating the registry.",
            )
        )

    schema_valid = True
    if registry is not None and schema is not None:
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in sorted(
            validator.iter_errors(registry),
            key=lambda err: (_json_path(err.absolute_path), err.message),
        ):
            schema_valid = False
            issues.append(
                _issue(
                    "error",
                    "schema_validation_error",
                    _json_path(error.absolute_path),
                    error.message,
                    "Correct the registry to satisfy the Draft 2020-12 schema.",
                )
            )

    contract_valid = True
    if registry is not None:
        qualifications = registry.get("qualifications")
        if isinstance(qualifications, dict):
            for entry_id, entry in qualifications.items():
                if not isinstance(entry, dict):
                    issues.append(
                        _issue(
                            "error",
                            "entry_not_object",
                            f"$.qualifications.{entry_id}",
                            "Each qualification entry must be an object.",
                            "Project the entry with the generator.",
                        )
                    )
                    continue
                _validate_rubric(entry_id, entry, root, issues)
                _validate_latest_run(entry_id, entry, root, issues)
                _validate_evidence(entry_id, entry, root, issues)
                _validate_status_evidence(entry_id, entry, issues)
        _validate_surfaces(registry, root, issues)
        _validate_status_vocabulary(registry, issues)

    contract_valid = not any(
        issue["code"]
        in {
            "rubric_missing",
            "rubric_qualification_id_mismatch",
            "latest_run_missing",
            "latest_run_qualification_id_mismatch",
            "latest_run_verdict_mismatch",
            "evidence_missing",
            "evidence_reference_invalid",
            "pass_without_run",
            "pass_without_tested_commit",
            "pass_without_qualification_date",
            "pass_without_evidence",
            "surface_not_projected",
            "surface_not_declared",
            "ambiguous_status",
            "entry_not_object",
        }
        for issue in issues
    )

    issues = _finalize_issues(issues)
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "result": "pass" if not issues else "fail",
        "schema_valid": schema_valid,
        "contract_valid": contract_valid,
        "issue_count": len(issues),
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Codexify qualification registry."
    )
    parser.add_argument(
        "registry_path",
        nargs="?",
        default=None,
        help="registry to validate (default: docs/qualification/registry.json)",
    )
    parser.add_argument("--schema", default=None)
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    registry_file = (
        Path(args.registry_path)
        if args.registry_path
        else repo_root / REGISTRY_PATH
    )
    schema_file = (
        Path(args.schema) if args.schema else repo_root / SCHEMA_PATH
    )

    result = validate_registry(registry_file, schema_file, repo_root)
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif not args.quiet:
        print(
            f"Qualification registry validation {result['result']}: "
            f"{registry_file} ({result['issue_count']} issue(s))"
        )
        for issue in result["issues"]:
            print(
                f"  [{issue['severity']}] {issue['code']} at {issue['path']}: "
                f"{issue['message']}"
            )

    if any(issue["code"] in {"schema_read_error", "schema_invalid"} for issue in result["issues"]):
        return EXIT_SCHEMA_ERROR
    return EXIT_OK if result["result"] == "pass" else EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
