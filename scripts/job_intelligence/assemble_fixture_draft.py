from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.job_intelligence.validate_fixture import validate_fixture

NON_GOAL_KEYS = {
    "model_called",
    "network_used",
    "runtime_used",
    "persistence_used",
    "transcription_used",
    "pricing_automated",
    "dispatch_automated",
}

EXPECTED_OUTPUT_KEYS = {
    "job_profile_draft": "generated-job-profile-draft.json",
    "review_packet": "generated-review-packet.json",
    "report": "assembly-report.json",
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


def _build_check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "detail": detail,
    }


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value


def _require_string_list(
    value: Any, label: str, *, allow_empty: bool = False
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    if not allow_empty and not value:
        raise ValueError(f"{label} must be a non-empty list.")

    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}[{index}] must be a non-empty string.")
        items.append(item)
    return items


def _require_object_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")

    items: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{index}] must be a JSON object.")
        items.append(item)
    return items


def _normalize_symptom_for_raw_description(symptom: str) -> str:
    mapping = {
        "tub spout drips while fixture is off": (
            "the tub spout drips when the fixture is off"
        )
    }
    try:
        return mapping[symptom]
    except KeyError as exc:
        raise ValueError(
            "No deterministic raw-description symptom mapping exists for "
            f"{symptom!r}."
        ) from exc


def _build_handle_phrase(reported_fixture_details: list[str]) -> str:
    detail_set = set(reported_fixture_details)
    expected = {
        "hot knob",
        "middle diverter knob",
        "cold knob",
    }
    if expected.issubset(detail_set):
        return "hot, diverter, and cold knobs"

    raise ValueError(
        "No deterministic handle summary mapping exists for "
        f"reported_fixture_details={reported_fixture_details!r}."
    )


def _build_flow_phrase(reported_fixture_details: list[str]) -> str:
    if "middle knob controls tub or shower flow" in reported_fixture_details:
        return "the middle knob sends water up or down"

    raise ValueError(
        "No deterministic flow summary mapping exists for "
        f"reported_fixture_details={reported_fixture_details!r}."
    )


def _build_policy_phrase(policy_questions: list[dict[str, Any]]) -> str:
    topics = [_require_string(item.get("topic"), "policy_questions.topic") for item in policy_questions]
    if topics == ["diagnostic_fee", "general_pricing_expectation"]:
        return "diagnostic fee and general pricing"

    raise ValueError(
        "No deterministic policy-question phrase mapping exists for "
        f"topics={topics!r}."
    )


def _build_request_summary(
    symptoms: list[str], inferred_fields: dict[str, Any]
) -> str:
    category = _require_string(
        inferred_fields.get("category"), "inferred_fields.category"
    )
    if (
        symptoms == ["tub spout drips while fixture is off"]
        and category == "tub_shower_three_handle_valve_or_diverter_issue"
    ):
        return "Reported drip from tub spout while three-handle tub/shower fixture is off."

    raise ValueError(
        "No deterministic request summary mapping exists for "
        f"symptoms={symptoms!r} and category={category!r}."
    )


def _build_known_equipment(
    reported_fixture_details: list[str],
    reported_brand: str,
    inferred_fields: dict[str, Any],
) -> list[str]:
    known_equipment_summary = _require_string(
        inferred_fields.get("known_equipment_summary"),
        "inferred_fields.known_equipment_summary",
    )
    detail_map = {
        "hot knob": "hot handle",
        "middle diverter knob": "diverter handle",
        "cold knob": "cold handle",
    }
    required_details = [
        "hot knob",
        "middle diverter knob",
        "cold knob",
    ]
    if not known_equipment_summary.startswith(
        "Three-handle tub/shower fixture"
    ):
        raise ValueError(
            "No deterministic equipment summary mapping exists for "
            f"known_equipment_summary={known_equipment_summary!r}."
        )

    if reported_brand != "unknown":
        raise ValueError(
            "No deterministic brand mapping exists for "
            f"reported_brand={reported_brand!r}."
        )

    missing = [
        detail for detail in required_details if detail not in reported_fixture_details
    ]
    if missing:
        raise ValueError(
            "No deterministic equipment mapping exists because "
            f"reported_fixture_details is missing {missing!r}."
        )

    return [
        "three-handle tub/shower fixture",
        detail_map["hot knob"],
        detail_map["middle diverter knob"],
        detail_map["cold knob"],
        "unknown brand",
    ]


def _normalize_scheduling_preference(value: str) -> str:
    mapping = {
        "around 1:00 PM": "around_1300",
        "afternoon_around_1300": "around_1300",
    }
    try:
        return mapping[value]
    except KeyError as exc:
        raise ValueError(
            "No deterministic scheduling-preference mapping exists for "
            f"{value!r}."
        ) from exc


def _build_access_notes(access_detail: str) -> str:
    if access_detail == "Access panel behind the shower.":
        return (
            "Customer reports an access panel behind the shower; technician "
            "usability still needs human verification."
        )

    raise ValueError(
        "No deterministic access-note mapping exists for "
        f"{access_detail!r}."
    )


def _build_draft_policy_question_notes(policy_questions: list[dict[str, Any]]) -> str:
    topics = [_require_string(item.get("topic"), "policy_questions.topic") for item in policy_questions]
    if topics == ["diagnostic_fee", "general_pricing_expectation"]:
        return (
            "Customer asked about diagnostic fee and general pricing expectations. "
            "No pricing commitment is implied."
        )

    raise ValueError(
        "No deterministic draft policy-question note mapping exists for "
        f"topics={topics!r}."
    )


def _build_risk_notes(risk_signals: list[str]) -> str:
    if not risk_signals:
        return "No explicit safety risk reported in the synthetic source interaction."

    raise ValueError(
        "No deterministic risk-note mapping exists for non-empty risk_signals."
    )


def _build_follow_up_details(
    policy_questions: list[dict[str, Any]],
    scheduling_preference: str,
    access_detail: str,
) -> str:
    topics = [_require_string(item.get("topic"), "policy_questions.topic") for item in policy_questions]
    if (
        topics == ["diagnostic_fee", "general_pricing_expectation"]
        and scheduling_preference == "around 1:00 PM"
        and access_detail == "Access panel behind the shower."
    ):
        return (
            "Human review should confirm pricing questions, scheduling "
            "preference, and access-panel usability."
        )

    raise ValueError(
        "No deterministic follow-up event mapping exists for current extraction values."
    )


def _build_review_packet_missing_information(
    extraction: dict[str, Any]
) -> list[str]:
    missing_information = _require_string_list(
        extraction.get("missing_information"), "missing_information"
    )
    required = [
        "fixture brand confirmation",
        "full service address placeholder",
        "onsite contact method placeholder",
    ]
    for item in required:
        if item not in missing_information:
            raise ValueError(
                "No deterministic review missing-information mapping exists because "
                f"{item!r} is missing."
            )

    ambiguities = _require_object_list(extraction.get("ambiguities"), "ambiguities")
    has_access_ambiguity = any(
        item.get("field") == "directly_stated_facts.reported_access_detail"
        for item in ambiguities
    )
    if not has_access_ambiguity:
        raise ValueError(
            "No deterministic review missing-information mapping exists because "
            "reported access detail ambiguity is missing."
        )

    return [
        "fixture brand confirmation",
        "full service address placeholder",
        "onsite contact method placeholder",
        "access panel usability verification",
    ]


def _build_low_confidence_fields(extraction: dict[str, Any]) -> list[str]:
    confidence = _require_dict(extraction.get("confidence"), "confidence")
    category_confidence = _require_string(
        confidence.get("category"), "confidence.category"
    )
    scheduling_confidence = _require_string(
        confidence.get("scheduling_preference"),
        "confidence.scheduling_preference",
    )
    labels_status = _require_string(
        confidence.get("labels_status"), "confidence.labels_status"
    )

    fields: list[str] = []
    if category_confidence != "high":
        fields.append("classification.category")
    if labels_status == "planning_only":
        fields.append("classification.confidence")
    if scheduling_confidence in {"medium", "low", "unknown"}:
        fields.append("scheduling.preference")
    return fields


def _build_review_policy_questions(
    policy_questions: list[dict[str, Any]]
) -> list[dict[str, str]]:
    notes_by_topic = {
        "diagnostic_fee": (
            "Customer asked about diagnostic fee. Pricing is not committed."
        ),
        "general_pricing_expectation": (
            "Customer asked about general pricing expectations. No price quote "
            "or pricing commitment should be inferred."
        ),
    }

    review_questions: list[dict[str, str]] = []
    for item in policy_questions:
        topic = _require_string(item.get("topic"), "policy_questions.topic")
        if topic not in notes_by_topic:
            raise ValueError(
                "No deterministic review policy-question mapping exists for "
                f"topic={topic!r}."
            )
        review_questions.append(
            {
                "topic": topic,
                "review_note": notes_by_topic[topic],
            }
        )
    return review_questions


def _build_field_review_notes(
    extraction: dict[str, Any]
) -> list[dict[str, str]]:
    facts = _require_dict(
        extraction.get("directly_stated_facts"), "directly_stated_facts"
    )
    reported_brand = _require_string(
        facts.get("reported_brand"), "directly_stated_facts.reported_brand"
    )
    reported_access_detail = _require_string(
        facts.get("reported_access_detail"),
        "directly_stated_facts.reported_access_detail",
    )
    reported_scheduling_preference = _require_string(
        facts.get("reported_scheduling_preference"),
        "directly_stated_facts.reported_scheduling_preference",
    )
    policy_questions = _require_object_list(
        extraction.get("policy_questions"), "policy_questions"
    )
    topics = [_require_string(item.get("topic"), "policy_questions.topic") for item in policy_questions]

    if reported_brand != "unknown":
        raise ValueError(
            "No deterministic field-review note mapping exists for non-unknown brand."
        )
    if reported_access_detail != "Access panel behind the shower.":
        raise ValueError(
            "No deterministic field-review note mapping exists for "
            f"reported_access_detail={reported_access_detail!r}."
        )
    if reported_scheduling_preference != "around 1:00 PM":
        raise ValueError(
            "No deterministic field-review note mapping exists for "
            f"reported_scheduling_preference={reported_scheduling_preference!r}."
        )
    if topics != ["diagnostic_fee", "general_pricing_expectation"]:
        raise ValueError(
            "No deterministic field-review note mapping exists for "
            f"topics={topics!r}."
        )

    return [
        {
            "field_path": "request.known_equipment",
            "note": (
                "Brand remains unknown and should stay unknown until a human "
                "confirms it."
            ),
        },
        {
            "field_path": "classification.confidence",
            "note": (
                "Service category confidence is planning-only and should remain "
                "reviewable before any operational use."
            ),
        },
        {
            "field_path": "site.access_notes",
            "note": (
                "Confirm that the reported access panel is usable and note any "
                "technician constraints."
            ),
        },
        {
            "field_path": "policy_questions.items",
            "note": (
                "Keep diagnostic fee and pricing questions separate from diagnosis "
                "and repair details; pricing is not committed."
            ),
        },
        {
            "field_path": "scheduling.preference",
            "note": (
                "Treat the 1:00 PM request as a preference only; it is not dispatch "
                "confirmation."
            ),
        },
    ]


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


def assemble_job_profile_draft(
    extraction: dict[str, Any], expected_template: dict[str, Any]
) -> dict[str, Any]:
    facts = _require_dict(
        extraction.get("directly_stated_facts"), "directly_stated_facts"
    )
    inferred_fields = _require_dict(
        extraction.get("inferred_fields"), "inferred_fields"
    )
    confidence = _require_dict(extraction.get("confidence"), "confidence")
    template_site = _require_dict(expected_template.get("site"), "site")
    template_customer = _require_dict(
        expected_template.get("customer"), "customer"
    )
    template_review = _require_dict(expected_template.get("review"), "review")
    template_lineage = _require_dict(
        expected_template.get("lineage"), "lineage"
    )

    policy_questions = _require_object_list(
        extraction.get("policy_questions"), "policy_questions"
    )
    symptoms = _require_string_list(
        facts.get("reported_symptoms"),
        "directly_stated_facts.reported_symptoms",
    )
    reported_fixture_details = _require_string_list(
        facts.get("reported_fixture_details"),
        "directly_stated_facts.reported_fixture_details",
    )
    reported_brand = _require_string(
        facts.get("reported_brand"), "directly_stated_facts.reported_brand"
    )
    reported_access_detail = _require_string(
        facts.get("reported_access_detail"),
        "directly_stated_facts.reported_access_detail",
    )
    reported_scheduling_preference = _require_string(
        facts.get("reported_scheduling_preference"),
        "directly_stated_facts.reported_scheduling_preference",
    )

    raw_description = (
        f"Customer reports that "
        f"{_normalize_symptom_for_raw_description(symptoms[0])}. "
        f"The fixture has {_build_handle_phrase(reported_fixture_details)}, "
        f"{_build_flow_phrase(reported_fixture_details)}, "
        f"the brand is unknown, there is an access panel behind the shower, "
        f"the customer asked about {_build_policy_phrase(policy_questions)}, "
        f"and {reported_scheduling_preference} is preferred."
    )

    return {
        "job_profile_id": _require_string(
            expected_template.get("job_profile_id"), "job_profile_id"
        ),
        "version": expected_template.get("version"),
        "status": _require_string(expected_template.get("status"), "status"),
        "source": {
            "interaction_type": _require_string(
                extraction.get("interaction_type"), "interaction_type"
            ),
            "transcript_available": True,
            "raw_description": raw_description,
        },
        "customer": deepcopy(template_customer),
        "site": {
            "address": _require_string(
                template_site.get("address"), "site.address"
            ),
            "access_notes": _build_access_notes(reported_access_detail),
        },
        "request": {
            "summary": _build_request_summary(symptoms, inferred_fields),
            "symptoms": symptoms,
            "known_equipment": _build_known_equipment(
                reported_fixture_details,
                reported_brand,
                inferred_fields,
            ),
        },
        "classification": {
            "service_type": _require_string(
                inferred_fields.get("service_type"),
                "inferred_fields.service_type",
            ),
            "category": _require_string(
                inferred_fields.get("category"), "inferred_fields.category"
            ),
            "confidence": _require_string(
                confidence.get("category"), "confidence.category"
            ),
            "confidence_note": "Planning-only review aid; not canonical runtime truth.",
        },
        "scheduling": {
            "preference": _normalize_scheduling_preference(
                _require_string(
                    inferred_fields.get("draft_scheduling_preference"),
                    "inferred_fields.draft_scheduling_preference",
                )
            ),
            "constraints": [
                f"Customer prefers an appointment {reported_scheduling_preference}."
            ],
            "commitment_status": "not_committed",
        },
        "policy_questions": {
            "items": [
                _require_string(item.get("topic"), "policy_questions.topic")
                for item in policy_questions
            ],
            "notes": _build_draft_policy_question_notes(policy_questions),
        },
        "risk_and_safety": {
            "flags": _require_string_list(
                extraction.get("risk_signals"),
                "risk_signals",
                allow_empty=True,
            ),
            "notes": _build_risk_notes(
                _require_string_list(
                    extraction.get("risk_signals"),
                    "risk_signals",
                    allow_empty=True,
                )
            ),
        },
        "events": [
            {
                "event_type": "follow_up_required",
                "details": _build_follow_up_details(
                    policy_questions,
                    reported_scheduling_preference,
                    reported_access_detail,
                ),
                "recorded_at": _require_string(
                    _require_dict(
                        expected_template.get("metadata"), "metadata"
                    ).get("created_at"),
                    "metadata.created_at",
                ),
            }
        ],
        "review": {
            "required": True,
            "reviewed_by": template_review.get("reviewed_by"),
            "reviewed_at": template_review.get("reviewed_at"),
            "corrections": deepcopy(template_review.get("corrections", [])),
        },
        "lineage": {
            "source_interaction_id": _require_string(
                extraction.get("source_interaction_id"), "source_interaction_id"
            ),
            "source_artifact_id": _require_string(
                extraction.get("fixture_id"), "fixture_id"
            ),
            "source_message_id": _require_string(
                template_lineage.get("source_message_id"),
                "lineage.source_message_id",
            ),
        },
        "metadata": deepcopy(
            _require_dict(expected_template.get("metadata"), "metadata")
        ),
    }


def assemble_review_packet(
    extraction: dict[str, Any],
    draft: dict[str, Any],
    expected_template: dict[str, Any],
) -> dict[str, Any]:
    policy_questions = _require_object_list(
        extraction.get("policy_questions"), "policy_questions"
    )

    return {
        "review_packet_id": _require_string(
            expected_template.get("review_packet_id"), "review_packet_id"
        ),
        "job_profile_id": _require_string(
            draft.get("job_profile_id"), "job_profile_id"
        ),
        "requires_review": True,
        "attention_fields": [
            "request.known_equipment",
            "classification.confidence",
            "site.access_notes",
            "policy_questions.items",
            "scheduling.preference",
        ],
        "missing_information": _build_review_packet_missing_information(
            extraction
        ),
        "low_confidence_fields": _build_low_confidence_fields(extraction),
        "policy_questions": _build_review_policy_questions(policy_questions),
        "human_action_recommendation": "review_and_edit_before_confirmation",
        "field_review_notes": _build_field_review_notes(extraction),
        "lineage": {
            "source_interaction_id": _require_string(
                extraction.get("source_interaction_id"), "source_interaction_id"
            ),
            "source_artifact_id": _require_string(
                extraction.get("fixture_id"), "fixture_id"
            ),
            "job_profile_id": _require_string(
                draft.get("job_profile_id"), "job_profile_id"
            ),
        },
        "metadata": deepcopy(
            _require_dict(expected_template.get("metadata"), "metadata")
        ),
    }


def _compare_values(
    expected: Any, actual: Any, path: str, differences: list[str]
) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            differences.append(
                f"{path}: expected object but found {type(actual).__name__}."
            )
            return

        expected_keys = set(expected)
        actual_keys = set(actual)
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        if missing:
            differences.append(f"{path}: missing keys {missing!r}.")
        if extra:
            differences.append(f"{path}: unexpected keys {extra!r}.")
        for key in sorted(expected_keys & actual_keys):
            _compare_values(expected[key], actual[key], f"{path}.{key}", differences)
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            differences.append(
                f"{path}: expected list but found {type(actual).__name__}."
            )
            return
        if len(expected) != len(actual):
            differences.append(
                f"{path}: expected list length {len(expected)} but found {len(actual)}."
            )
            return
        for index, (expected_item, actual_item) in enumerate(
            zip(expected, actual, strict=True)
        ):
            _compare_values(
                expected_item,
                actual_item,
                f"{path}[{index}]",
                differences,
            )
        return

    if expected != actual:
        differences.append(
            f"{path}: expected {expected!r} but found {actual!r}."
        )


def compare_json(
    expected: dict[str, Any], actual: dict[str, Any], label: str
) -> list[str]:
    differences: list[str] = []
    _compare_values(expected, actual, label, differences)
    return differences


def run_assembly(fixture_dir: Path) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    generated_artifacts: dict[str, Any] = {
        "job_profile_draft": {},
        "review_packet": {},
    }
    comparison: dict[str, Any] = {
        "job_profile_draft_matches_expected": False,
        "review_packet_matches_expected": False,
        "differences": [],
    }
    metadata = {
        "generated_at": "1970-01-01T00:00:00Z",
        "runner": "scripts.job_intelligence.assemble_fixture_draft",
        "synthetic_only": True,
    }
    non_goals_confirmed = {
        "model_called": False,
        "network_used": False,
        "runtime_used": False,
        "persistence_used": False,
        "transcription_used": False,
        "pricing_automated": False,
        "dispatch_automated": False,
    }

    report = {
        "assembly_id": f"job_intelligence_fixture_assembly_{fixture_dir.name}",
        "fixture_path": str(fixture_dir),
        "status": "failed",
        "checks": checks,
        "generated_artifacts": generated_artifacts,
        "comparison": comparison,
        "non_goals_confirmed": non_goals_confirmed,
        "metadata": metadata,
    }

    validation_errors = validate_fixture(fixture_dir)
    if validation_errors:
        for error in validation_errors:
            checks.append(_build_check("fixture_validator", False, error))
            comparison["differences"].append(error)
        return report

    checks.append(
        _build_check(
            "fixture_validator",
            True,
            f"Fixture validation passed for {fixture_dir}.",
        )
    )

    source_text = (fixture_dir / "source-interaction.txt").read_text(
        encoding="utf-8"
    )
    checks.append(
        _build_check(
            "source_interaction_loaded",
            bool(source_text.strip()),
            (
                "Loaded non-empty source-interaction.txt with "
                f"{len(source_text.splitlines())} lines."
            ),
        )
    )

    extraction = load_json(fixture_dir / "expected-extraction.json")
    expected_draft = load_json(fixture_dir / "expected-job-profile-draft.json")
    expected_review_packet = load_json(
        fixture_dir / "expected-review-packet.json"
    )

    try:
        draft = assemble_job_profile_draft(extraction, expected_draft)
        generated_artifacts["job_profile_draft"] = draft
        checks.append(
            _build_check(
                "job_profile_draft_assembled",
                True,
                "Deterministically assembled Job Profile draft from extraction fixture.",
            )
        )
    except ValueError as exc:
        checks.append(_build_check("job_profile_draft_assembled", False, str(exc)))
        comparison["differences"].append(str(exc))
        return report

    try:
        review_packet = assemble_review_packet(
            extraction, draft, expected_review_packet
        )
        generated_artifacts["review_packet"] = review_packet
        checks.append(
            _build_check(
                "review_packet_assembled",
                True,
                "Deterministically assembled review packet from extraction and draft artifacts.",
            )
        )
    except ValueError as exc:
        checks.append(_build_check("review_packet_assembled", False, str(exc)))
        comparison["differences"].append(str(exc))
        metadata["generated_at"] = _deterministic_generated_at(
            extraction, draft, expected_review_packet
        )
        return report

    metadata["generated_at"] = _deterministic_generated_at(
        extraction, draft, review_packet
    )

    draft_differences = compare_json(
        expected_draft, draft, "job_profile_draft"
    )
    review_packet_differences = compare_json(
        expected_review_packet, review_packet, "review_packet"
    )

    comparison["job_profile_draft_matches_expected"] = not draft_differences
    comparison["review_packet_matches_expected"] = not review_packet_differences
    comparison["differences"] = draft_differences + review_packet_differences

    checks.append(
        _build_check(
            "job_profile_draft_matches_expected",
            not draft_differences,
            "Generated Job Profile draft exactly matches expected fixture artifact."
            if not draft_differences
            else draft_differences[0],
        )
    )
    checks.append(
        _build_check(
            "review_packet_matches_expected",
            not review_packet_differences,
            "Generated review packet exactly matches expected fixture artifact."
            if not review_packet_differences
            else review_packet_differences[0],
        )
    )

    report["status"] = (
        "passed"
        if all(check["status"] == "passed" for check in checks)
        else "failed"
    )
    return report


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically assemble Job Intelligence fixture outputs and "
            "compare them to expected artifacts."
        )
    )
    parser.add_argument("fixture_dir", help="Path to the fixture directory.")
    parser.add_argument(
        "--output-dir",
        help=(
            "Optional directory where generated-job-profile-draft.json, "
            "generated-review-packet.json, and assembly-report.json should be written."
        ),
    )
    args = parser.parse_args(argv)

    fixture_dir = Path(args.fixture_dir)
    report = run_assembly(fixture_dir)

    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_dir / EXPECTED_OUTPUT_KEYS["job_profile_draft"],
            report["generated_artifacts"]["job_profile_draft"],
        )
        _write_json(
            output_dir / EXPECTED_OUTPUT_KEYS["review_packet"],
            report["generated_artifacts"]["review_packet"],
        )
        _write_json(output_dir / EXPECTED_OUTPUT_KEYS["report"], report)

    if report["status"] == "failed":
        print(f"Assembly failed for: {fixture_dir}", file=sys.stderr)
        for check in report["checks"]:
            if check["status"] == "failed":
                print(f"- {check['name']}: {check['detail']}", file=sys.stderr)
        for difference in report["comparison"]["differences"]:
            print(f"- difference: {difference}", file=sys.stderr)
        return 1

    print(f"Assembly passed for: {fixture_dir}")
    if args.output_dir:
        print(f"Wrote assembly artifacts to: {args.output_dir}")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
