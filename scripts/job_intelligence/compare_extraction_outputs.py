from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.job_intelligence.validate_extraction_output import (
    validate_extraction_output,
)

KNOWN_EXTRACTION_KEYS = [
    "fixture_id",
    "fixture_kind",
    "source_interaction_id",
    "interaction_type",
    "service_vertical",
    "directly_stated_facts",
    "inferred_fields",
    "ambiguities",
    "missing_information",
    "policy_questions",
    "risk_signals",
    "review_recommendations",
    "confidence",
    "metadata",
]

STABLE_FIELDS = [
    "source_interaction_id",
    "interaction_type",
    "service_vertical",
]

MANUAL_REQUIRED_NON_EMPTY_FIELDS = [
    "directly_stated_facts",
    "inferred_fields",
    "ambiguities",
    "missing_information",
    "policy_questions",
    "review_recommendations",
    "confidence",
]

NON_GOAL_KEYS = [
    "model_called",
    "network_used",
    "runtime_used",
    "prompt_executed",
    "semantic_scoring_used",
    "persistence_used",
    "transcription_used",
    "pricing_automated",
    "dispatch_automated",
]

REQUIRED_REPORT_KEYS = {
    "comparison_id",
    "status",
    "expected_path",
    "actual_path",
    "source_text_path",
    "fixture_dir",
    "checks",
    "field_presence",
    "stable_field_matches",
    "differences",
    "non_goals_confirmed",
    "metadata",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Extraction JSON file does not exist: {path}") from exc
    except OSError as exc:
        raise ValueError(f"Could not read extraction JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.name} is not valid JSON: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a top-level JSON object.")

    return data


def field_presence_summary(
    expected: dict[str, Any], actual: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "field": key,
            "expected_present": key in expected,
            "expected_non_empty": _is_non_empty(expected.get(key)),
            "actual_present": key in actual,
            "actual_non_empty": _is_non_empty(actual.get(key)),
        }
        for key in KNOWN_EXTRACTION_KEYS
    ]


def compare_extraction_outputs(
    expected_path: Path,
    actual_path: Path,
    source_text_path: Path | None = None,
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    differences: list[str] = []
    stable_field_matches: dict[str, bool] = {
        field: False for field in STABLE_FIELDS
    }
    field_presence: list[dict[str, Any]] = []

    expected_errors = validate_extraction_output(
        expected_path,
        source_text_path=source_text_path,
        fixture_dir=fixture_dir,
    )
    actual_errors = validate_extraction_output(
        actual_path,
        source_text_path=source_text_path,
    )
    checks.append(
        _build_check(
            "expected_validation",
            not expected_errors,
            "Expected extraction artifact passed validation."
            if not expected_errors
            else "; ".join(expected_errors),
        )
    )
    checks.append(
        _build_check(
            "actual_validation",
            not actual_errors,
            "Actual extraction artifact passed validation."
            if not actual_errors
            else "; ".join(actual_errors),
        )
    )
    differences.extend(
        f"expected validation: {error}" for error in expected_errors
    )
    differences.extend(f"actual validation: {error}" for error in actual_errors)

    try:
        expected = load_json(expected_path)
        actual = load_json(actual_path)
    except ValueError as exc:
        differences.append(str(exc))
        checks.append(_build_check("load_artifacts", False, str(exc)))
        return _build_report(
            expected_path,
            actual_path,
            source_text_path,
            fixture_dir,
            checks,
            field_presence,
            stable_field_matches,
            differences,
            "1970-01-01T00:00:00Z",
        )

    checks.append(
        _build_check(
            "load_artifacts",
            True,
            "Loaded expected and actual extraction artifacts.",
        )
    )

    field_presence = field_presence_summary(expected, actual)
    missing_expected = _missing_known_fields(expected)
    missing_actual = _missing_known_fields(actual)
    top_level_keys_ok = not missing_expected and not missing_actual
    if missing_expected:
        differences.append(
            "Expected extraction missing top-level fields: "
            + ", ".join(missing_expected)
        )
    if missing_actual:
        differences.append(
            "Actual extraction missing top-level fields: "
            + ", ".join(missing_actual)
        )
    checks.append(
        _build_check(
            "known_top_level_fields_present",
            top_level_keys_ok,
            "Known extraction top-level fields are present in both artifacts."
            if top_level_keys_ok
            else "One or both artifacts are missing known extraction fields.",
        )
    )

    for field in STABLE_FIELDS:
        matches = expected.get(field) == actual.get(field)
        stable_field_matches[field] = matches
        if not matches:
            differences.append(
                f"Stable field {field!r} mismatch: "
                f"expected={expected.get(field)!r}, actual={actual.get(field)!r}"
            )
    stable_fields_ok = all(stable_field_matches.values())
    checks.append(
        _build_check(
            "stable_context_fields_match",
            stable_fields_ok,
            "Stable identity/context fields match."
            if stable_fields_ok
            else "One or more stable identity/context fields differ.",
        )
    )

    missing_or_empty_manual_fields = [
        item["field"]
        for item in field_presence
        if item["field"] in MANUAL_REQUIRED_NON_EMPTY_FIELDS
        and (not item["actual_present"] or not item["actual_non_empty"])
    ]
    for field in missing_or_empty_manual_fields:
        differences.append(
            f"Actual extraction field {field!r} must be present and non-empty."
        )
    manual_required_fields_ok = not missing_or_empty_manual_fields
    checks.append(
        _build_check(
            "manual_required_fields_non_empty",
            manual_required_fields_ok,
            "Manual extraction required safety/review fields are non-empty."
            if manual_required_fields_ok
            else "Manual extraction is missing required non-empty safety/review fields.",
        )
    )

    policy_questions_ok = _is_non_empty(expected.get("policy_questions")) and (
        _is_non_empty(actual.get("policy_questions"))
    )
    if not policy_questions_ok:
        differences.append(
            "Both expected and actual extraction artifacts must include "
            "non-empty policy_questions."
        )
    checks.append(
        _build_check(
            "policy_questions_non_empty",
            policy_questions_ok,
            "Both artifacts include non-empty policy_questions."
            if policy_questions_ok
            else "One or both artifacts are missing non-empty policy_questions.",
        )
    )

    return _build_report(
        expected_path,
        actual_path,
        source_text_path,
        fixture_dir,
        checks,
        field_presence,
        stable_field_matches,
        differences,
        _deterministic_generated_at(expected, actual),
    )


def validate_comparison_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = sorted(REQUIRED_REPORT_KEYS - set(report))
    if missing:
        errors.append(
            "Comparison report is missing required top-level keys: "
            + ", ".join(missing)
        )
        return errors

    status = report.get("status")
    if status not in {"passed", "failed"}:
        errors.append("Comparison report status must be 'passed' or 'failed'.")

    _validate_checks(report, status, errors)
    _validate_field_presence(report, errors)
    _validate_stable_field_matches(report, errors)
    _validate_differences(report, status, errors)
    _validate_paths(report, errors)
    _validate_non_goals(report, errors)
    _validate_metadata(report, errors)

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare docs-local Job Intelligence extraction-shaped JSON artifacts."
        )
    )
    parser.add_argument("expected_json", help="Path to the expected extraction JSON.")
    parser.add_argument(
        "actual_json",
        help="Path to the actual or manual extraction JSON.",
    )
    parser.add_argument(
        "--source-text",
        help="Optional source interaction text path to verify as non-empty.",
    )
    parser.add_argument(
        "--fixture-dir",
        help=(
            "Optional fixture directory used when validating the expected "
            "extraction artifact."
        ),
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the machine-readable comparison report.",
    )
    args = parser.parse_args(argv)

    expected_path = Path(args.expected_json)
    actual_path = Path(args.actual_json)
    source_text_path = Path(args.source_text) if args.source_text else None
    fixture_dir = Path(args.fixture_dir) if args.fixture_dir else None
    output_path = Path(args.output) if args.output else None

    report = compare_extraction_outputs(
        expected_path,
        actual_path,
        source_text_path=source_text_path,
        fixture_dir=fixture_dir,
    )
    report_errors = validate_comparison_report(report)

    if output_path is not None:
        _write_report(output_path, report)

    if report_errors:
        print(
            "Extraction comparison report is invalid.",
            file=sys.stderr,
        )
        for error in report_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if report["status"] != "passed":
        print("Extraction comparison failed.", file=sys.stderr)
        for check in report["checks"]:
            if check["status"] == "failed":
                print(f"- {check['name']}: {check['detail']}", file=sys.stderr)
        for difference in report["differences"]:
            print(f"- difference: {difference}", file=sys.stderr)
        return 1

    if output_path is None:
        print("Extraction comparison passed.", file=sys.stderr)
        print(json.dumps(report, indent=2))
    else:
        print(f"Extraction comparison passed -> {output_path}")
    return 0


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _build_check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "detail": detail,
    }


def _missing_known_fields(payload: dict[str, Any]) -> list[str]:
    return [field for field in KNOWN_EXTRACTION_KEYS if field not in payload]


def _deterministic_generated_at(*payloads: dict[str, Any]) -> str:
    candidates: list[str] = []
    for payload in payloads:
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            created_at = metadata.get("created_at")
            if isinstance(created_at, str) and created_at.strip():
                candidates.append(created_at)
    if candidates:
        return sorted(candidates)[0]
    return "1970-01-01T00:00:00Z"


def _build_report(
    expected_path: Path,
    actual_path: Path,
    source_text_path: Path | None,
    fixture_dir: Path | None,
    checks: list[dict[str, str]],
    field_presence: list[dict[str, Any]],
    stable_field_matches: dict[str, bool],
    differences: list[str],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "comparison_id": (
            f"job_intelligence_extraction_comparison_"
            f"{expected_path.stem}_to_{actual_path.stem}"
        ),
        "status": (
            "passed"
            if all(check["status"] == "passed" for check in checks)
            and not differences
            else "failed"
        ),
        "expected_path": str(expected_path),
        "actual_path": str(actual_path),
        "source_text_path": str(source_text_path) if source_text_path else None,
        "fixture_dir": str(fixture_dir) if fixture_dir else None,
        "checks": checks,
        "field_presence": field_presence,
        "stable_field_matches": stable_field_matches,
        "differences": differences,
        "non_goals_confirmed": {key: False for key in NON_GOAL_KEYS},
        "metadata": {
            "generated_at": generated_at,
            "runner": "scripts.job_intelligence.compare_extraction_outputs",
            "synthetic_only": True,
        },
    }


def _validate_checks(
    report: dict[str, Any], status: Any, errors: list[str]
) -> None:
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("Comparison report checks must be a non-empty list.")
        return

    failed_check_count = 0
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"Check #{index} must be an object.")
            continue
        for key in ("name", "status", "detail"):
            if key not in check:
                errors.append(f"Check #{index} is missing required key: {key}")
        if check.get("status") == "failed":
            failed_check_count += 1
        elif check.get("status") != "passed":
            errors.append(f"Check #{index} status must be 'passed' or 'failed'.")

    if status == "passed" and failed_check_count:
        errors.append(
            "Comparison report cannot have status 'passed' when failed checks exist."
        )
    if status == "failed" and failed_check_count == 0:
        errors.append(
            "Comparison report cannot have status 'failed' without a failed check."
        )


def _validate_field_presence(report: dict[str, Any], errors: list[str]) -> None:
    field_presence = report.get("field_presence")
    if not isinstance(field_presence, list):
        errors.append("Comparison report field_presence must be a list.")
        return

    required_keys = {
        "field",
        "expected_present",
        "expected_non_empty",
        "actual_present",
        "actual_non_empty",
    }
    for index, item in enumerate(field_presence):
        if not isinstance(item, dict):
            errors.append(f"field_presence[{index}] must be an object.")
            continue
        missing = sorted(required_keys - set(item))
        if missing:
            errors.append(
                f"field_presence[{index}] missing keys: {', '.join(missing)}"
            )


def _validate_stable_field_matches(
    report: dict[str, Any], errors: list[str]
) -> None:
    stable_field_matches = report.get("stable_field_matches")
    if not isinstance(stable_field_matches, dict):
        errors.append("Comparison report stable_field_matches must be an object.")
        return

    for field in STABLE_FIELDS:
        if not isinstance(stable_field_matches.get(field), bool):
            errors.append(
                f"stable_field_matches[{field!r}] must be a boolean."
            )


def _validate_differences(
    report: dict[str, Any], status: Any, errors: list[str]
) -> None:
    differences = report.get("differences")
    if not isinstance(differences, list):
        errors.append("Comparison report differences must be a list.")
        return
    if status == "passed" and differences:
        errors.append("Comparison report cannot pass with differences.")


def _validate_paths(report: dict[str, Any], errors: list[str]) -> None:
    for key in ("expected_path", "actual_path"):
        value = report.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"Comparison report {key} must be a non-empty string.")

    for key in ("source_text_path", "fixture_dir"):
        value = report.get(key)
        if value is not None and (not isinstance(value, str) or not value):
            errors.append(
                f"Comparison report {key} must be null or a non-empty string."
            )


def _validate_non_goals(report: dict[str, Any], errors: list[str]) -> None:
    non_goals = report.get("non_goals_confirmed")
    if not isinstance(non_goals, dict):
        errors.append("Comparison report non_goals_confirmed must be an object.")
        return

    missing = [key for key in NON_GOAL_KEYS if key not in non_goals]
    if missing:
        errors.append(
            "Comparison report non_goals_confirmed missing keys: "
            + ", ".join(missing)
        )
    for key in NON_GOAL_KEYS:
        if non_goals.get(key) is not False:
            errors.append(
                f"Comparison report non_goals_confirmed[{key!r}] must be false."
            )


def _validate_metadata(report: dict[str, Any], errors: list[str]) -> None:
    metadata = report.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("Comparison report metadata must be an object.")
        return

    generated_at = metadata.get("generated_at")
    runner = metadata.get("runner")
    if not isinstance(generated_at, str) or not generated_at:
        errors.append("Comparison report metadata.generated_at must be a string.")
    if not isinstance(runner, str) or not runner:
        errors.append("Comparison report metadata.runner must be a string.")
    if metadata.get("synthetic_only") is not True:
        errors.append("Comparison report metadata.synthetic_only must be true.")


def _write_report(output_path: Path, report: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
