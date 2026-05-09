from __future__ import annotations

from guardian.agents.test_results import (
    NormalizedTestResult,
    normalize_subprocess_test_result,
    not_run_test_result,
)


def test_passing_command_normalizes_to_passed() -> None:
    result = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=0,
        stdout="1 passed in 0.03s",
        stderr="",
        duration_seconds=1.25,
    )

    assert result.status == "passed"
    assert result.command == "pytest -q"
    assert result.exit_code == 0
    assert result.tests_total == 1
    assert result.tests_passed == 1
    assert result.tests_failed == 0
    assert result.fail_signature is None
    assert result.duration_seconds == 1.25


def test_failing_command_normalizes_to_failed() -> None:
    result = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=(
            "=========================== short test summary info ===========================\n"
            "FAILED tests/test_widget.py::test_widget - AssertionError: widget broke\n"
            "1 failed, 2 passed in 0.20s"
        ),
        stderr="E   AssertionError: widget broke",
    )

    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.tests_total == 3
    assert result.tests_passed == 2
    assert result.tests_failed == 1
    assert result.failing_tests == ["tests/test_widget.py::test_widget"]
    assert result.fail_signature is not None


def test_stdout_and_stderr_previews_are_bounded() -> None:
    result = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout="x" * 10_000,
        stderr="y" * 12_000,
    )

    assert len(result.stdout_preview) <= 2048
    assert len(result.stderr_preview) <= 2048


def test_repeated_equivalent_failures_have_same_signature() -> None:
    result_a = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=(
            "FAILED tests/test_api.py::test_round_trip - AssertionError: "
            "value mismatch\n"
            "=========================== short test summary info ===========================\n"
            "FAILED tests/test_api.py::test_round_trip - AssertionError: "
            "value mismatch\n"
        ),
        stderr=(
            "E   AssertionError: value mismatch\n"
            "E   File /tmp/pytest-of-alice/pytest-12/test_round_trip0/test_api.py:41"
        ),
    )
    result_b = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=(
            "FAILED tests/test_api.py::test_round_trip - AssertionError: "
            "value mismatch\n"
            "=========================== short test summary info ===========================\n"
            "FAILED tests/test_api.py::test_round_trip - AssertionError: "
            "value mismatch\n"
        ),
        stderr=(
            "E   AssertionError: value mismatch\n"
            "E   File /var/folders/xy/pytest-12/test_round_trip0/test_api.py:99"
        ),
    )

    assert result_a.fail_signature == result_b.fail_signature


def test_volatile_temp_paths_do_not_change_fail_signature() -> None:
    base_stdout = "FAILED tests/test_api.py::test_round_trip - AssertionError"
    result_a = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=base_stdout,
        stderr="E   File /tmp/pytest-of-alice/pytest-12/test_round_trip0/test_api.py:41",
    )
    result_b = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=base_stdout,
        stderr="E   File /tmp/pytest-of-bob/pytest-99/test_round_trip0/test_api.py:104",
    )

    assert result_a.fail_signature == result_b.fail_signature


def test_pytest_style_failing_test_identifiers_are_captured() -> None:
    result = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=(
            "=========================== short test summary info ===========================\n"
            "FAILED tests/test_widget.py::test_widget[alpha] - AssertionError\n"
        ),
        stderr="",
    )

    assert result.failing_tests == ["tests/test_widget.py::test_widget[alpha]"]


def test_not_run_test_result_does_not_pretend_success_or_failure() -> None:
    result = not_run_test_result("skipped by policy", command="pytest -q")

    assert result.status == "not_run"
    assert result.command == "pytest -q"
    assert result.exit_code is None
    assert result.fail_signature is None
    assert result.error_message == "skipped by policy"


def test_pydantic_model_serialization_and_round_trip() -> None:
    result = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout="FAILED tests/test_widget.py::test_widget - AssertionError",
        stderr="E   AssertionError",
    )

    payload = result.model_dump()
    rebuilt = NormalizedTestResult.model_validate(payload)

    assert payload["status"] == "failed"
    assert rebuilt == result
