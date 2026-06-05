from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_FILES = (
    "README.md",
    "source-interaction.txt",
    "expected-extraction.json",
    "expected-job-profile-draft.json",
    "expected-review-packet.json",
)

EXTRACTION_KEYS = {
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
}

JOB_PROFILE_KEYS = {
    "job_profile_id",
    "version",
    "status",
    "source",
    "customer",
    "site",
    "request",
    "classification",
    "scheduling",
    "policy_questions",
    "risk_and_safety",
    "events",
    "review",
    "lineage",
    "metadata",
}

REVIEW_PACKET_KEYS = {
    "review_packet_id",
    "job_profile_id",
    "requires_review",
    "attention_fields",
    "missing_information",
    "low_confidence_fields",
    "policy_questions",
    "human_action_recommendation",
    "field_review_notes",
    "lineage",
    "metadata",
}

PROHIBITED_PHRASES = (
    "difficult customer",
    "problem customer",
    "neurotic",
    "crazy",
    "argumentative",
    "bad attitude",
)

CONTACT_PATTERNS = {
    "phone number": re.compile(
        r"\b\d{3}-\d{3}-\d{4}\b|\(\d{3}\)\s*\d{3}-\d{4}\b|\b\d{10}\b"
    ),
    "email address": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "street address": re.compile(
        r"\b\d{1,6}\s+(?:[A-Za-z0-9.'-]+\s+){1,4}"
        r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln)\b\.?",
        re.IGNORECASE,
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.name} is not valid JSON: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a top-level JSON object.")

    return data


def _missing_keys(payload: dict[str, Any], required_keys: set[str]) -> list[str]:
    return sorted(required_keys - set(payload))


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return bool(value)
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _append_missing_file_errors(
    errors: list[str], fixture_dir: Path
) -> dict[str, Path]:
    file_paths = {name: fixture_dir / name for name in REQUIRED_FILES}
    for name, path in file_paths.items():
        if not path.is_file():
            errors.append(f"Missing required file: {name}")
    return file_paths


def _validate_source_interaction(path: Path, errors: list[str]) -> None:
    source_text = path.read_text(encoding="utf-8")
    if not source_text.strip():
        errors.append("source-interaction.txt must be non-empty.")
        return

    for label, pattern in CONTACT_PATTERNS.items():
        match = pattern.search(source_text)
        if match:
            errors.append(
                "source-interaction.txt appears to contain a "
                f"{label}: {match.group(0)!r}"
            )


def _validate_required_keys(
    payload: dict[str, Any],
    required_keys: set[str],
    label: str,
    errors: list[str],
) -> None:
    missing = _missing_keys(payload, required_keys)
    if missing:
        errors.append(f"{label} is missing required keys: {', '.join(missing)}")


def _validate_no_subjective_labels(
    payload: dict[str, Any], label: str, errors: list[str]
) -> None:
    serialized = json.dumps(payload, sort_keys=True).lower()
    for phrase in PROHIBITED_PHRASES:
        if phrase in serialized:
            errors.append(
                f"{label} contains prohibited subjective label: {phrase!r}"
            )


def _validate_policy_questions(
    payload: dict[str, Any], label: str, errors: list[str]
) -> None:
    if not _is_non_empty(payload.get("policy_questions")):
        errors.append(f"{label} must include non-empty policy_questions.")


def _validate_lineage(
    payload: dict[str, Any], label: str, errors: list[str]
) -> None:
    if not _is_non_empty(payload.get("lineage")):
        errors.append(f"{label} must include non-empty lineage.")


def validate_fixture(fixture_dir: Path) -> list[str]:
    errors: list[str] = []

    if not fixture_dir.exists():
        return [f"Fixture directory does not exist: {fixture_dir}"]

    if not fixture_dir.is_dir():
        return [f"Fixture path is not a directory: {fixture_dir}"]

    file_paths = _append_missing_file_errors(errors, fixture_dir)

    source_path = file_paths["source-interaction.txt"]
    if source_path.is_file():
        _validate_source_interaction(source_path, errors)

    extraction_payload: dict[str, Any] | None = None
    job_profile_payload: dict[str, Any] | None = None
    review_packet_payload: dict[str, Any] | None = None

    for name in (
        "expected-extraction.json",
        "expected-job-profile-draft.json",
        "expected-review-packet.json",
    ):
        path = file_paths[name]
        if not path.is_file():
            continue
        try:
            payload = load_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if name == "expected-extraction.json":
            extraction_payload = payload
        elif name == "expected-job-profile-draft.json":
            job_profile_payload = payload
        else:
            review_packet_payload = payload

    if extraction_payload is not None:
        _validate_required_keys(
            extraction_payload,
            EXTRACTION_KEYS,
            "expected-extraction.json",
            errors,
        )
        _validate_no_subjective_labels(
            extraction_payload, "expected-extraction.json", errors
        )
        _validate_policy_questions(
            extraction_payload, "expected-extraction.json", errors
        )

    if job_profile_payload is not None:
        _validate_required_keys(
            job_profile_payload,
            JOB_PROFILE_KEYS,
            "expected-job-profile-draft.json",
            errors,
        )
        _validate_no_subjective_labels(
            job_profile_payload, "expected-job-profile-draft.json", errors
        )
        _validate_policy_questions(
            job_profile_payload, "expected-job-profile-draft.json", errors
        )
        _validate_lineage(
            job_profile_payload, "expected-job-profile-draft.json", errors
        )

        review = job_profile_payload.get("review")
        if not isinstance(review, dict) or review.get("required") is not True:
            errors.append(
                "expected-job-profile-draft.json must set review.required to true."
            )

    if review_packet_payload is not None:
        _validate_required_keys(
            review_packet_payload,
            REVIEW_PACKET_KEYS,
            "expected-review-packet.json",
            errors,
        )
        _validate_no_subjective_labels(
            review_packet_payload, "expected-review-packet.json", errors
        )
        _validate_policy_questions(
            review_packet_payload, "expected-review-packet.json", errors
        )
        _validate_lineage(
            review_packet_payload, "expected-review-packet.json", errors
        )

        if review_packet_payload.get("requires_review") is not True:
            errors.append(
                "expected-review-packet.json must set requires_review to true."
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "Usage: python3 scripts/job_intelligence/validate_fixture.py "
            "<fixture_dir>",
            file=sys.stderr,
        )
        return 2

    fixture_dir = Path(args[0])
    errors = validate_fixture(fixture_dir)
    if errors:
        print(f"Fixture validation failed for: {fixture_dir}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Fixture validation passed for: {fixture_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
