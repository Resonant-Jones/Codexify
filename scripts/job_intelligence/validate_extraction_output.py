from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.job_intelligence.validate_fixture import validate_fixture

REQUIRED_TOP_LEVEL_KEYS = {
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

REQUIRED_NON_EMPTY_FIELDS = {
    "fixture_id",
    "fixture_kind",
    "source_interaction_id",
    "interaction_type",
    "service_vertical",
    "directly_stated_facts",
    "policy_questions",
    "review_recommendations",
    "confidence",
    "metadata",
}

TEXT_FIELD_KEYS = {
    "fixture_id",
    "fixture_kind",
    "source_interaction_id",
    "interaction_type",
    "service_vertical",
}

PRICING_COMMITMENT_PHRASES = [
    "final price",
    "guaranteed price",
    "will cost exactly",
    "price confirmed",
    "no diagnostic fee unless",
]

SCHEDULING_COMMITMENT_PHRASES = [
    "technician scheduled",
    "dispatch confirmed",
    "appointment confirmed",
    "we will arrive",
    "guaranteed appointment",
]

SUBJECTIVE_LABEL_PHRASES = [
    "difficult customer",
    "problem customer",
    "neurotic",
    "crazy",
    "argumentative",
    "bad attitude",
]

SENSITIVE_TRAIT_PHRASES = [
    "mental illness",
    "diagnosis",
    "political",
    "religious",
    "sexual orientation",
    "gender identity",
]

RAW_LANGUAGE_KEY_MARKERS = (
    "raw",
    "source",
    "customer_language",
    "customer_phrasing",
    "source_phrasing",
    "raw_description",
    "description_raw",
    "source_text",
)

UNCERTAINTY_MARKERS = [
    "unknown",
    "low",
    "medium",
    "review",
    "unconfirmed",
    "not confirmed",
    "ambiguous",
    "uncertain",
    "missing",
    "needs review",
]


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


def serialized_contains(value: Any, phrases: list[str]) -> list[str]:
    try:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        serialized = str(value)

    normalized = serialized.casefold()
    return [phrase for phrase in phrases if phrase.casefold() in normalized]


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _key_matches_marker(key: str) -> bool:
    normalized_key = key.casefold().replace("-", "_").replace(" ", "_")
    return any(marker in normalized_key for marker in RAW_LANGUAGE_KEY_MARKERS)


def _contains_raw_language_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if _key_matches_marker(str(key)) and _is_non_empty(item):
                return True
            if _contains_raw_language_field(item):
                return True
    elif isinstance(value, list):
        return any(_contains_raw_language_field(item) for item in value)
    return False


def _validate_required_keys(payload: dict[str, Any], errors: list[str]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(payload))
    if missing:
        errors.append(
            "Extraction output is missing required top-level keys: "
            + ", ".join(missing)
        )


def _validate_required_non_empty_fields(
    payload: dict[str, Any], errors: list[str]
) -> None:
    for key in sorted(REQUIRED_NON_EMPTY_FIELDS):
        if key not in payload:
            continue
        if not _is_non_empty(payload.get(key)):
            errors.append(f"Extraction output field {key!r} must be non-empty.")

    for key in sorted(TEXT_FIELD_KEYS):
        value = payload.get(key)
        if key in payload and not isinstance(value, str):
            errors.append(f"Extraction output field {key!r} must be a string.")


def _validate_collection_fields(
    payload: dict[str, Any], errors: list[str]
) -> None:
    for key in (
        "ambiguities",
        "missing_information",
        "policy_questions",
        "review_recommendations",
        "risk_signals",
    ):
        if key in payload and not isinstance(payload.get(key), list):
            errors.append(f"Extraction output field {key!r} must be a list.")

    for key in ("directly_stated_facts", "inferred_fields", "confidence", "metadata"):
        if key in payload and not isinstance(payload.get(key), dict):
            errors.append(f"Extraction output field {key!r} must be an object.")


def _append_phrase_errors(
    payload: dict[str, Any],
    errors: list[str],
    phrases: list[str],
    label: str,
) -> None:
    for phrase in serialized_contains(payload, phrases):
        errors.append(f"Extraction output contains prohibited {label}: {phrase!r}")


def _validate_source_text(source_text_path: Path, errors: list[str]) -> None:
    try:
        source_text = source_text_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"Source text file does not exist: {source_text_path}")
        return
    except OSError as exc:
        errors.append(f"Could not read source text file {source_text_path}: {exc}")
        return

    if not source_text.strip():
        errors.append(f"Source text file must be non-empty: {source_text_path}")


def _validate_fixture_dir(
    extraction_path: Path, fixture_dir: Path, errors: list[str]
) -> None:
    fixture_errors = validate_fixture(fixture_dir)
    if fixture_errors:
        errors.append(f"Fixture validation failed for: {fixture_dir}")
        errors.extend(f"fixture validator: {error}" for error in fixture_errors)

    expected_extraction_path = fixture_dir / "expected-extraction.json"
    if expected_extraction_path.exists():
        if extraction_path.resolve() != expected_extraction_path.resolve():
            errors.append(
                "Extraction path must match the fixture's expected-extraction.json "
                f"when --fixture-dir is provided: {expected_extraction_path}"
            )


def _validate_raw_language_preservation(
    payload: dict[str, Any], errors: list[str]
) -> None:
    directly_stated_facts = payload.get("directly_stated_facts")
    if not _contains_raw_language_field(directly_stated_facts):
        errors.append(
            "Extraction output must preserve customer/source phrasing under "
            "directly_stated_facts or a clearly named nested raw/source field."
        )


def _validate_uncertainty(payload: dict[str, Any], errors: list[str]) -> None:
    has_reviewable_uncertainty = bool(payload.get("ambiguities")) or bool(
        payload.get("missing_information")
    )
    if not has_reviewable_uncertainty:
        confidence = payload.get("confidence")
        has_reviewable_uncertainty = bool(
            serialized_contains(confidence, UNCERTAINTY_MARKERS)
        )

    if not has_reviewable_uncertainty:
        errors.append(
            "Extraction output must identify reviewable uncertainty through "
            "ambiguities, missing_information, or confidence detail."
        )


def validate_extraction_output(
    extraction_path: Path,
    source_text_path: Path | None = None,
    fixture_dir: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    if source_text_path is not None:
        _validate_source_text(source_text_path, errors)

    if fixture_dir is not None:
        _validate_fixture_dir(extraction_path, fixture_dir, errors)

    try:
        payload = load_json(extraction_path)
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    _validate_required_keys(payload, errors)
    _validate_required_non_empty_fields(payload, errors)
    _validate_collection_fields(payload, errors)

    if "policy_questions" in payload and not _is_non_empty(
        payload.get("policy_questions")
    ):
        errors.append("Extraction output must include non-empty policy_questions.")

    _append_phrase_errors(
        payload,
        errors,
        PRICING_COMMITMENT_PHRASES,
        "pricing commitment phrase",
    )
    _append_phrase_errors(
        payload,
        errors,
        SCHEDULING_COMMITMENT_PHRASES,
        "scheduling or dispatch commitment phrase",
    )
    _append_phrase_errors(
        payload,
        errors,
        SUBJECTIVE_LABEL_PHRASES,
        "subjective durable customer label",
    )
    _append_phrase_errors(
        payload,
        errors,
        SENSITIVE_TRAIT_PHRASES,
        "sensitive-trait inference phrase",
    )

    _validate_raw_language_preservation(payload, errors)
    _validate_uncertainty(payload, errors)

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a docs-local Job Intelligence extraction-shaped JSON artifact."
        )
    )
    parser.add_argument("extraction_json", help="Path to the extraction JSON file.")
    parser.add_argument(
        "--source-text",
        help="Optional source interaction text path to verify as non-empty.",
    )
    parser.add_argument(
        "--fixture-dir",
        help="Optional fixture directory to validate before checking extraction JSON.",
    )
    args = parser.parse_args(argv)

    extraction_path = Path(args.extraction_json)
    source_text_path = Path(args.source_text) if args.source_text else None
    fixture_dir = Path(args.fixture_dir) if args.fixture_dir else None

    errors = validate_extraction_output(
        extraction_path,
        source_text_path=source_text_path,
        fixture_dir=fixture_dir,
    )
    if errors:
        print(
            f"Extraction output validation failed for: {extraction_path}",
            file=sys.stderr,
        )
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Extraction output validation passed for: {extraction_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
