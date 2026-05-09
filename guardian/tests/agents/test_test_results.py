from __future__ import annotations

from guardian.agents.retry_policy import build_fail_signature
from guardian.agents.test_results import (
    NormalizedTestResult,
    _extract_failing_tests,
    _scrub_volatile_text,
    normalize_subprocess_test_result,
    not_run_test_result,
)


def test_passing_command_normalizes_to_passed() -> None:
    result = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=0,
        stdout="2 passed in 0.12s\n",
        stderr="",
        duration_seconds=0.12,
    )

    assert result.status == "passed"
    assert result.command == "pytest -q"
    assert result.exit_code == 0
    assert result.tests_total == 2
    assert result.tests_passed == 2
    assert result.tests_failed == 0
    assert result.fail_signature is None
    assert result.error_message is None


def test_failing_command_normalizes_to_failed() -> None:
    result = normalize_subprocess_test_result(
        command="pytest tests/unit/test_alpha.py",
        exit_code=1,
        stdout=(
            "FAILED tests/unit/test_alpha.py::TestThing::test_works - "
            "AssertionError: boom\n"
            "= 1 failed, 3 passed in 0.23s =\n"
        ),
        stderr=(
            "E   AssertionError: boom\n"
            "tests/unit/test_alpha.py:12: AssertionError\n"
        ),
        duration_seconds=0.23,
    )

    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.tests_total == 4
    assert result.tests_failed == 1
    assert result.tests_passed == 3
    assert result.failing_tests == [
        "tests/unit/test_alpha.py::TestThing::test_works"
    ]
    assert result.fail_signature is not None
    assert result.error_message == "E AssertionError: boom"


def test_stdout_and_stderr_previews_are_bounded() -> None:
    result = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout="x" * 10_000,
        stderr="y" * 10_000,
    )

    assert len(result.stdout_preview) <= 2048
    assert len(result.stderr_preview) <= 2048
    assert result.stdout_preview.endswith("…")
    assert result.stderr_preview.endswith("…")


def test_repeated_equivalent_failures_share_signature() -> None:
    first = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=(
            "FAILED tests/unit/test_alpha.py::TestThing::test_works - "
            "AssertionError: boom\n"
        ),
        stderr="E AssertionError: boom\n/tmp/pytest-of-user/pytest-1/test.log:12\n",
    )
    second = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=(
            "FAILED tests/unit/test_alpha.py::TestThing::test_works - "
            "AssertionError: boom\n"
        ),
        stderr="E AssertionError: boom\n/private/var/folders/ab/cd/test.log:19\n",
    )

    assert first.fail_signature == second.fail_signature


def test_volatile_temp_paths_do_not_change_fail_signature() -> None:
    first = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout="",
        stderr="/tmp/pytest-of-user/pytest-1/test_alpha.py:41: AssertionError\n",
    )
    second = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout="",
        stderr=(
            "/private/var/folders/ab/cd/pytest-2/"
            "test_alpha.py:87: AssertionError\n"
        ),
    )

    assert first.fail_signature == second.fail_signature


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


def test_fail_signature_matches_retry_policy_helper() -> None:
    result = normalize_subprocess_test_result(
        command="pytest -q",
        exit_code=1,
        stdout=(
            "FAILED tests/unit/test_alpha.py::TestThing::test_works - "
            "AssertionError: boom\n"
        ),
        stderr="AssertionError: boom\n",
    )

    scrubbed = _scrub_volatile_text(
        "FAILED tests/unit/test_alpha.py::TestThing::test_works - "
        "AssertionError: boom\nAssertionError: boom\n"
    )
    expected = build_fail_signature(
        ["tests/unit/test_alpha.py::TestThing::test_works"],
        scrubbed.splitlines(),
    )

    assert result.fail_signature == expected
    assert _extract_failing_tests(
        "FAILED tests/unit/test_alpha.py::TestThing::test_works - "
        "AssertionError: boom\n",
        "AssertionError: boom\n",
    ) == ["tests/unit/test_alpha.py::TestThing::test_works"]
