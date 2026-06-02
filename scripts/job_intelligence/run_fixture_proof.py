from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.job_intelligence.validate_fixture import validate_fixture

REQUIRED_REPORT_KEYS = {
    "proof_id",
    "fixture_path",
    "status",
    "checks",
    "artifacts",
    "non_goals_confirmed",
    "metadata",
}

ARTIFACT_KEYS = {
    "source_interaction",
    "expected_extraction",
    "expected_job_profile_draft",
    "expected_review_packet",
}

NON_GOAL_KEYS = {
    "model_called",
    "network_used",
    "runtime_used",
    "persistence_used",
    "transcription_used",
    "pricing_automated",
    "dispatch_automated",
}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a top-level JSON object.")
    return data


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return bool(value)
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _policy_questions_non_empty(value: Any) -> bool:
    if isinstance(value, dict):
        items = value.get("items")
        if items is not None:
            return _is_non_empty(items)
    return _is_non_empty(value)


def _raw_description_from_draft(draft: dict[str, Any]) -> str:
    source = draft.get("source")
    if not isinstance(source, dict):
        return ""

    for key in ("raw_description", "raw_text", "source_text", "description_raw"):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return ""


def _build_check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "detail": detail,
    }


def _deterministic_generated_at(
    extraction: dict[str, Any],
    draft: dict[str, Any],
    review_packet: dict[str, Any],
) -> str:
    candidates: list[str] = []
    for payload in (extraction, draft, review_packet):
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            created_at = metadata.get("created_at")
            if isinstance(created_at, str) and created_at.strip():
                candidates.append(created_at)
    if candidates:
        return sorted(candidates)[0]
    return "1970-01-01T00:00:00Z"


def _artifacts_for_fixture(fixture_dir: Path) -> dict[str, str]:
    return {
        "source_interaction": str(fixture_dir / "source-interaction.txt"),
        "expected_extraction": str(fixture_dir / "expected-extraction.json"),
        "expected_job_profile_draft": str(
            fixture_dir / "expected-job-profile-draft.json"
        ),
        "expected_review_packet": str(
            fixture_dir / "expected-review-packet.json"
        ),
    }


def run_fixture_proof(fixture_dir: Path) -> dict[str, Any]:
    artifacts = _artifacts_for_fixture(fixture_dir)
    checks: list[dict[str, str]] = []

    validation_errors = validate_fixture(fixture_dir)
    if validation_errors:
        for error in validation_errors:
            checks.append(
                _build_check(
                    "fixture_validator",
                    False,
                    error,
                )
            )
        return {
            "proof_id": f"job_intelligence_fixture_proof_{fixture_dir.name}",
            "fixture_path": str(fixture_dir),
            "status": "failed",
            "checks": checks,
            "artifacts": artifacts,
            "non_goals_confirmed": {
                "model_called": False,
                "network_used": False,
                "runtime_used": False,
                "persistence_used": False,
                "transcription_used": False,
                "pricing_automated": False,
                "dispatch_automated": False,
            },
            "metadata": {
                "generated_at": "1970-01-01T00:00:00Z",
                "runner": "scripts.job_intelligence.run_fixture_proof",
                "synthetic_only": True,
            },
        }

    extraction = _load_json(Path(artifacts["expected_extraction"]))
    draft = _load_json(Path(artifacts["expected_job_profile_draft"]))
    review_packet = _load_json(Path(artifacts["expected_review_packet"]))
    source_text = Path(artifacts["source_interaction"]).read_text(encoding="utf-8")

    extraction_source_id = extraction.get("source_interaction_id")
    draft_lineage = draft.get("lineage")
    draft_source_id = (
        draft_lineage.get("source_interaction_id")
        if isinstance(draft_lineage, dict)
        else None
    )
    checks.append(
        _build_check(
            "extraction_source_matches_draft_lineage",
            bool(extraction_source_id and extraction_source_id == draft_source_id),
            (
                f"Extraction source_interaction_id={extraction_source_id!r}; "
                f"draft lineage source_interaction_id={draft_source_id!r}."
            ),
        )
    )

    draft_job_profile_id = draft.get("job_profile_id")
    review_job_profile_id = review_packet.get("job_profile_id")
    checks.append(
        _build_check(
            "job_profile_id_matches_review_packet",
            bool(
                draft_job_profile_id
                and draft_job_profile_id == review_job_profile_id
            ),
            (
                f"Draft job_profile_id={draft_job_profile_id!r}; "
                f"review packet job_profile_id={review_job_profile_id!r}."
            ),
        )
    )

    review = draft.get("review")
    checks.append(
        _build_check(
            "draft_requires_review",
            isinstance(review, dict) and review.get("required") is True,
            "expected-job-profile-draft.json review.required must be true.",
        )
    )

    checks.append(
        _build_check(
            "review_packet_requires_review",
            review_packet.get("requires_review") is True,
            "expected-review-packet.json requires_review must be true.",
        )
    )

    policy_questions_ok = all(
        (
            _policy_questions_non_empty(extraction.get("policy_questions")),
            _policy_questions_non_empty(draft.get("policy_questions")),
            _policy_questions_non_empty(review_packet.get("policy_questions")),
        )
    )
    checks.append(
        _build_check(
            "policy_questions_present_across_artifacts",
            policy_questions_ok,
            "Extraction, draft, and review packet must all contain non-empty policy questions.",
        )
    )

    lineage_ok = _is_non_empty(draft.get("lineage")) and _is_non_empty(
        review_packet.get("lineage")
    )
    checks.append(
        _build_check(
            "lineage_present_across_artifacts",
            lineage_ok,
            "Draft and review packet must both contain non-empty lineage.",
        )
    )

    raw_description = _raw_description_from_draft(draft)
    checks.append(
        _build_check(
            "raw_description_preserved",
            bool(raw_description.strip()),
            "Draft must preserve a non-empty raw description.",
        )
    )

    request = draft.get("request")
    summary = request.get("summary") if isinstance(request, dict) else None
    summary_is_separate = (
        isinstance(summary, str)
        and summary.strip()
        and summary.strip() != raw_description.strip()
    )
    checks.append(
        _build_check(
            "draft_summary_is_separate_from_raw_description",
            bool(summary_is_separate),
            "Draft must include a non-empty interpreted summary distinct from the raw description.",
        )
    )

    attention_fields = review_packet.get("attention_fields")
    checks.append(
        _build_check(
            "review_packet_has_attention_fields",
            isinstance(attention_fields, list) and len(attention_fields) > 0,
            "Review packet must include at least one attention field.",
        )
    )

    checks.append(
        _build_check(
            "source_interaction_is_non_empty",
            bool(source_text.strip()),
            "source-interaction.txt must be non-empty for proof execution.",
        )
    )

    report = {
        "proof_id": f"job_intelligence_fixture_proof_{fixture_dir.name}",
        "fixture_path": str(fixture_dir),
        "status": (
            "passed"
            if all(check["status"] == "passed" for check in checks)
            else "failed"
        ),
        "checks": checks,
        "artifacts": artifacts,
        "non_goals_confirmed": {
            "model_called": False,
            "network_used": False,
            "runtime_used": False,
            "persistence_used": False,
            "transcription_used": False,
            "pricing_automated": False,
            "dispatch_automated": False,
        },
        "metadata": {
            "generated_at": _deterministic_generated_at(
                extraction, draft, review_packet
            ),
            "runner": "scripts.job_intelligence.run_fixture_proof",
            "synthetic_only": True,
        },
    }
    return report


def validate_proof_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = sorted(REQUIRED_REPORT_KEYS - set(report))
    if missing:
        errors.append(
            f"Proof report is missing required top-level keys: {', '.join(missing)}"
        )
        return errors

    status = report.get("status")
    if status not in {"passed", "failed"}:
        errors.append("Proof report status must be 'passed' or 'failed'.")

    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("Proof report checks must be a non-empty list.")
    else:
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
                errors.append(
                    f"Check #{index} status must be 'passed' or 'failed'."
                )
        if status == "passed" and failed_check_count:
            errors.append(
                "Proof report cannot have status 'passed' when failed checks exist."
            )
        if status == "failed" and failed_check_count == 0:
            errors.append(
                "Proof report cannot have status 'failed' without a failed check."
            )

    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("Proof report artifacts must be an object.")
    else:
        missing_artifacts = sorted(ARTIFACT_KEYS - set(artifacts))
        if missing_artifacts:
            errors.append(
                "Proof report artifacts missing keys: "
                + ", ".join(missing_artifacts)
            )
        for key in ARTIFACT_KEYS:
            value = artifacts.get(key)
            if not isinstance(value, str) or not value:
                errors.append(
                    f"Proof report artifact {key!r} must be a non-empty string path."
                )

    non_goals = report.get("non_goals_confirmed")
    if not isinstance(non_goals, dict):
        errors.append("Proof report non_goals_confirmed must be an object.")
    else:
        missing_non_goals = sorted(NON_GOAL_KEYS - set(non_goals))
        if missing_non_goals:
            errors.append(
                "Proof report non_goals_confirmed missing keys: "
                + ", ".join(missing_non_goals)
            )
        for key in NON_GOAL_KEYS:
            if non_goals.get(key) is not False:
                errors.append(
                    f"Proof report non_goals_confirmed[{key!r}] must be false."
                )

    metadata = report.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("Proof report metadata must be an object.")
    else:
        generated_at = metadata.get("generated_at")
        runner = metadata.get("runner")
        if not isinstance(generated_at, str) or not generated_at:
            errors.append(
                "Proof report metadata.generated_at must be a non-empty string."
            )
        if not isinstance(runner, str) or not runner:
            errors.append("Proof report metadata.runner must be a non-empty string.")
        if metadata.get("synthetic_only") is not True:
            errors.append("Proof report metadata.synthetic_only must be true.")

    return errors


def _write_report(output_path: Path, report: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic proof checks for a Job Intelligence fixture."
    )
    parser.add_argument("fixture_dir", help="Path to the fixture directory.")
    parser.add_argument(
        "--output",
        help="Optional path to write the machine-readable proof report.",
    )
    args = parser.parse_args(argv)

    fixture_dir = Path(args.fixture_dir)
    report = run_fixture_proof(fixture_dir)
    report_errors = validate_proof_report(report)

    output_path = Path(args.output) if args.output else None
    if output_path is not None:
        _write_report(output_path, report)

    if report_errors:
        print(
            f"Fixture proof report is invalid for: {fixture_dir}",
            file=sys.stderr,
        )
        for error in report_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if report["status"] != "passed":
        print(f"Fixture proof failed for: {fixture_dir}", file=sys.stderr)
        for check in report["checks"]:
            if check["status"] == "failed":
                print(
                    f"- {check['name']}: {check['detail']}",
                    file=sys.stderr,
                )
        return 1

    if output_path is None:
        print(f"Fixture proof passed for: {fixture_dir}", file=sys.stderr)
        print(json.dumps(report, indent=2))
    else:
        print(
            f"Fixture proof passed for: {fixture_dir} -> {output_path}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
