"""Tests for the heartbeat schedule manifest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    ROOT / "config" / "heartbeat" / "heartbeat.schedule.example.json"
)


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# file is valid JSON
# ---------------------------------------------------------------------------


def test_manifest_is_valid_json() -> None:
    d = _load_manifest()
    assert isinstance(d, dict)


# ---------------------------------------------------------------------------
# schema_version
# ---------------------------------------------------------------------------


def test_schema_version_is_heartbeat_schedule_v1() -> None:
    d = _load_manifest()
    assert d["schema_version"] == "heartbeat.schedule.v1"


# ---------------------------------------------------------------------------
# schedules is a non-empty array
# ---------------------------------------------------------------------------


def test_schedules_is_non_empty_array() -> None:
    d = _load_manifest()
    assert isinstance(d["schedules"], list)
    assert len(d["schedules"]) >= 1


# ---------------------------------------------------------------------------
# each schedule has required keys
# ---------------------------------------------------------------------------

_REQUIRED_SCHEDULE_KEYS = [
    "id",
    "label",
    "cadence",
    "enabled",
    "activation_mode",
    "run_command",
    "review_after",
    "review_command",
    "required_inputs",
    "generated_artifacts",
    "publication",
]


def test_each_schedule_has_required_keys() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        for key in _REQUIRED_SCHEDULE_KEYS:
            assert key in s, f"schedule {s.get('id')} missing key: {key}"


# ---------------------------------------------------------------------------
# activation_mode is one of the allowed values
# ---------------------------------------------------------------------------

ALLOWED_ACTIVATION_MODES = {
    "manual_only",
    "local_scheduler_ready",
    "future_codexify_cron_ready",
}


def test_activation_mode_is_allowed() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        assert (
            s["activation_mode"] in ALLOWED_ACTIVATION_MODES
        ), f"schedule {s['id']}: activation_mode={s['activation_mode']} not in {ALLOWED_ACTIVATION_MODES}"


# ---------------------------------------------------------------------------
# the example schedule uses manual_only and enabled: false
# ---------------------------------------------------------------------------


def test_example_schedule_is_manual_only_and_disabled() -> None:
    d = _load_manifest()
    example = d["schedules"][0]
    assert example["activation_mode"] == "manual_only"
    assert example["enabled"] is False


# ---------------------------------------------------------------------------
# publication is disabled with empty targets
# ---------------------------------------------------------------------------


def test_publication_is_disabled_with_empty_targets() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        pub = s["publication"]
        assert pub["enabled"] is False
        assert pub["targets"] == []


# ---------------------------------------------------------------------------
# run_command points to make heartbeat
# ---------------------------------------------------------------------------


def test_run_command_points_to_make_heartbeat() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        assert (
            "make heartbeat" in s["run_command"]
        ), f"schedule {s['id']}: run_command does not contain 'make heartbeat'"


# ---------------------------------------------------------------------------
# review_command points to make heartbeat-review
# ---------------------------------------------------------------------------


def test_review_command_points_to_make_heartbeat_review() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        assert (
            "make heartbeat-review" in s["review_command"]
        ), f"schedule {s['id']}: review_command does not contain 'make heartbeat-review'"


# ---------------------------------------------------------------------------
# generated_artifacts includes all expected families
# ---------------------------------------------------------------------------

EXPECTED_ARTIFACT_FAMILIES = [
    "heartbeat",
    "beta-sentinel.md",
    "beta-sentinel.json",
    "dev-blog",
    "daily-insights",
]


def test_generated_artifacts_include_all_families() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        artifacts = " ".join(s["generated_artifacts"])
        for family in EXPECTED_ARTIFACT_FAMILIES:
            assert (
                family in artifacts
            ), f"schedule {s['id']}: missing artifact family '{family}'"


# ---------------------------------------------------------------------------
# required_inputs describes DATE, DEV_BLOG_SOURCE, INSIGHT_SOURCE, FORCE
# ---------------------------------------------------------------------------

EXPECTED_INPUTS = {"DATE", "DEV_BLOG_SOURCE", "INSIGHT_SOURCE", "FORCE"}


def test_required_inputs_describes_all_expected_inputs() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        actual = set(s["required_inputs"].keys())
        assert (
            actual == EXPECTED_INPUTS
        ), f"schedule {s['id']}: expected inputs {EXPECTED_INPUTS}, got {actual}"


# ---------------------------------------------------------------------------
# each input has description and required fields
# ---------------------------------------------------------------------------


def test_each_input_has_description_and_required() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        for key, val in s["required_inputs"].items():
            assert "description" in val, f"input {key} missing description"
            assert "required" in val, f"input {key} missing required"


# ---------------------------------------------------------------------------
# inputs are all optional (required: false)
# ---------------------------------------------------------------------------


def test_all_inputs_are_optional() -> None:
    d = _load_manifest()
    for s in d["schedules"]:
        for key, val in s["required_inputs"].items():
            assert (
                val["required"] is False
            ), f"input {key} should be optional in manual_only mode"


# ---------------------------------------------------------------------------
# timezone is present
# ---------------------------------------------------------------------------


def test_timezone_is_present() -> None:
    d = _load_manifest()
    assert "timezone" in d
    assert d["timezone"] == "America/New_York"


# ---------------------------------------------------------------------------
# cadence is daily
# ---------------------------------------------------------------------------


def test_cadence_is_daily() -> None:
    d = _load_manifest()
    assert d["cadence"] == "daily"
    for s in d["schedules"]:
        assert s["cadence"] == "daily"


# ---------------------------------------------------------------------------
# review_gate has STRICT input
# ---------------------------------------------------------------------------


def test_review_gate_has_strict_input() -> None:
    d = _load_manifest()
    rg = d.get("review_gate", {})
    inputs = rg.get("inputs", {})
    assert "STRICT" in inputs
    assert inputs["STRICT"]["required"] is False
